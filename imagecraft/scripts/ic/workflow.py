from __future__ import annotations

import io
import json
import math
from pathlib import Path
import warnings

from download_models import DEFAULT_MODEL, load_manifest, workflow_path
from .common import Error

CORE_NODES = {
    "UNETLoader", "CLIPLoader", "VAELoader", "CLIPTextEncode", "ConditioningZeroOut",
    "EmptySD3LatentImage", "ModelSamplingAuraFlow", "KSampler",
    "EmptyFlux2LatentImage", "RandomNoise", "CFGGuider", "KSamplerSelect", "Flux2Scheduler",
    "SamplerCustomAdvanced", "VAEDecode", "SaveImage", "LoadImage", "VAEEncode", "ReferenceLatent",
}
CORE_MODULES = {"nodes", "comfy_extras.nodes_flux", "comfy_extras.nodes_custom_sampler", "comfy_extras.nodes_edit_model",
                "comfy_extras.nodes_sd3", "comfy_extras.nodes_model_advanced"}


def pillow():
    try:
        from importlib import import_module
        Image = import_module("PIL.Image")
    except ImportError:
        raise Error("Pillow is required for reference/output verification; select the existing ComfyUI Python, or explicitly install Pillow in a separate client environment") from None
    return Image


def open_image(path_or_bytes):
    Image = pillow()
    from importlib import import_module
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            opened = Image.open(io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, bytes) else path_or_bytes)
        except (Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise Error("Image exceeds Pillow's pixel safety limit") from None
        with opened as source:
            if source.format not in ("PNG", "JPEG", "WEBP") or getattr(source, "n_frames", 1) != 1:
                raise Error("Only still PNG, JPEG and WebP images are accepted")
            if source.width * source.height > 24_000_000:
                raise Error("Image exceeds the 24-megapixel input limit")
            source.load()
            image = import_module("PIL.ImageOps").exif_transpose(source)
            if image.mode in ("RGBA", "LA") or "transparency" in image.info:
                rgba = image.convert("RGBA")
                canvas = Image.new("RGB", rgba.size, "white")
                canvas.paste(rgba, mask=rgba.getchannel("A"))
                return canvas
            return image.convert("RGB")


def check_reference(path: Path):
    if not path.is_file() or path.stat().st_size > 32 * 1024 * 1024:
        raise Error("Reference must be a local file no larger than 32 MiB")


def dimensions(width=None, height=None, reference: Path | None = None) -> tuple[int, int]:
    if (width is None) != (height is None):
        raise Error("Provide both --width and --height, or neither")
    if width is None:
        if reference:
            check_reference(reference)
            image = open_image(reference)
            ratio = max(256 / min(image.size), min(1.0, 1536 / max(image.size), math.sqrt(1024 * 1024 / (image.width * image.height))))
            width, height = (max(256, int(x * ratio) // 16 * 16) for x in image.size)
        else:
            width = height = 1024
    if (not isinstance(width, int) or not isinstance(height, int) or width % 16 or height % 16
            or not 256 <= width <= 1536 or not 256 <= height <= 1536 or width * height > 1_572_864):
        raise Error("Use multiples of 16, 256–1536 per side and at most 1,572,864 pixels; batch size is fixed at 1")
    return width, height


def reference_png(path: Path) -> bytes:
    check_reference(path)
    image = open_image(path)
    if max(image.size) / min(image.size) > 6:
        raise Error("Reference aspect ratio exceeds 6:1; prepare a suitable crop instead of silently distorting it")
    ratio = min(1.0, 1536 / max(image.size), math.sqrt(1_048_576 / (image.width * image.height)))
    size = tuple(max(16, round(x * ratio / 16) * 16) for x in image.size)
    image = image.resize(size, pillow().Resampling.LANCZOS)
    output = io.BytesIO()
    image.save(output, format="PNG")  # No EXIF, comments, original filenames or PNG text.
    return output.getvalue()


def build(prompt: str, width: int, height: int, seed: int, prefix: str, references=(), model: str = DEFAULT_MODEL) -> dict:
    dimensions(width, height)
    if not prompt.strip() or len(prompt) > 12000:
        raise Error("Prompt must contain 1–12,000 characters")
    if not 0 <= seed <= 2**64 - 1:
        raise Error("Seed must be an unsigned 64-bit integer")
    if len(references) > 2:
        raise Error("At most two reference images are supported")
    if references and model != "flux-klein-4b":
        raise Error("Z-Image Turbo is text-to-image only; select --model flux-klein-4b for reference editing")
    graph = json.loads(workflow_path(model).read_text(encoding="utf-8"))
    files = {f["role"]: Path(f["destination"]).name for f in load_manifest(model)["files"]}
    graph["1"]["inputs"]["unet_name"] = files["diffusion_model"]
    graph["2"]["inputs"]["clip_name"] = files["text_encoder"]
    graph["3"]["inputs"]["vae_name"] = files["vae"]
    graph["4"]["inputs"]["text"] = prompt
    graph["13"]["inputs"]["filename_prefix"] = prefix
    graph["6"]["inputs"].update(width=width, height=height)
    if model != "flux-klein-4b":
        graph["10"]["inputs"]["seed"] = seed
        return graph
    graph["10"]["inputs"].update(width=width, height=height)
    graph["7"]["inputs"]["noise_seed"] = seed
    positive, negative = ["4", 0], ["5", 0]
    for i, filename in enumerate(references):
        base = 20 + 4 * i
        load, encode, pos, neg = map(str, range(base, base + 4))
        graph[load] = {"class_type": "LoadImage", "inputs": {"image": filename}}
        graph[encode] = {"class_type": "VAEEncode", "inputs": {"pixels": [load, 0], "vae": ["3", 0]}}
        graph[pos] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": positive, "latent": [encode, 0]}}
        graph[neg] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": negative, "latent": [encode, 0]}}
        positive, negative = [pos, 0], [neg, 0]
    graph["8"]["inputs"].update(positive=positive, negative=negative)
    return graph


def validate(graph: dict, object_info: dict):
    """Conservative local validation. The server still performs authoritative validation."""
    for node_id, node in graph.items():
        kind = node["class_type"]
        if kind not in CORE_NODES or kind not in object_info:
            raise Error(f"Required native node unavailable: {kind}; do not auto-install custom nodes")
        info = object_info[kind]
        module = info.get("python_module")
        if module and module not in CORE_MODULES:
            raise Error(f"Node {kind} was supplied by an unexpected module: {module}")
        required = info.get("input", {}).get("required", {})
        for name, spec in required.items():
            if name not in node["inputs"]:
                raise Error(f"Missing node input: {node_id}.{name}")
            value = node["inputs"][name]
            if isinstance(value, list):
                if len(value) != 2 or value[0] not in graph or not isinstance(value[1], int):
                    raise Error(f"Broken workflow link: {node_id}.{name}")
                continue
            if isinstance(spec[0], list) and value not in spec[0]:
                # LoadImage enumerations may be stale just after an upload.
                if not (kind == "LoadImage" and name == "image"):
                    raise Error(f"Unavailable model/choice: {kind}.{name}={value}")
