"""Input inspection and provider routing hints."""

from __future__ import annotations

from pathlib import Path

from . import config, util
from .base import Options
from .config import remote_keys


def inspect_input(source: str, opts: Options) -> dict:
    info = {
        "source": source,
        "name": Path(source).name if not util.is_url(source) else source,
        "kind": "url" if util.is_url(source) else "file",
        "suffix": util.suffix_of(source),
        "bytes": None,
        "pages": None,
        "sha256": None,
        "pdf_text": {},
        "is_pdf": util.suffix_of(source) == ".pdf",
        "is_image": util.suffix_of(source) in util.SUPPORTED_IMAGE_EXT,
        "needs_ocr": None,
        "warnings": [],
    }
    if not util.is_url(source):
        path = Path(source)
        if not path.is_file():
            from .base import DocVisionError
            raise DocVisionError(f"Input not found: {source}")
        info["bytes"] = path.stat().st_size
        if path.stat().st_size == 0:
            from .base import DocVisionError
            raise DocVisionError(f"Input is empty: {source}")
        if info["bytes"] > opts.max_mb * 1024 * 1024:
            from .base import DocVisionError
            raise DocVisionError(
                f"Input is {util.human_bytes(info['bytes'])}, above the {opts.max_mb} MB limit.",
                hint="Split the file, raise --max-mb only for a provider that allows it, or use the local engine.",
            )
        info["sha256"] = util.sha256_file(path)
        if info["is_pdf"]:
            info["pages"] = util.pdf_page_count(path)
            info["pdf_text"] = util.pdf_text_stats(path)
            chars_per_page = info["pdf_text"].get("chars_per_page")
            if chars_per_page is not None:
                info["needs_ocr"] = chars_per_page < 50
                if chars_per_page < 50:
                    info["warnings"].append(
                        "Little or no embedded text was found; this PDF is probably scanned and needs OCR."
                    )
        elif info["is_image"]:
            info["needs_ocr"] = True
            if info["suffix"] not in {".tif", ".tiff", ".gif"}:
                info["pages"] = 1
            else:
                info["warnings"].append("Multi-frame images are not fully supported; page count is unverified.")
        elif info["suffix"] in util.SUPPORTED_NATIVE_EXT:
            info["needs_ocr"] = False
    else:
        if info["is_image"]:
            info["needs_ocr"] = True
    return info


def choose_provider(source: str, opts: Options, info: dict | None = None) -> str:
    if opts.provider and opts.provider != "auto":
        return opts.provider

    # Local first, always.  A local failure never silently becomes an upload.
    if config.discover_mineru().available:
        return "mineru-local"
    if config.discover_paddle().available:
        return "paddleocr-local"
    if config.discover_vlm().available:
        return "local-vlm"

    if opts.allow_remote:
        keys = remote_keys()
        if keys["paddle"]:
            return "paddleocr-cloud"
        if keys["mineru"]:
            return "mineru-cloud"
        if keys["glm"]:
            return "glm-cloud"
        if keys["mistral"]:
            return "mistral"
        if keys["gemini"]:
            return "gemini"
        if keys["openai"]:
            return "openai"

    from .base import DocVisionError
    raise DocVisionError(
        "No local OCR engine is installed, and remote upload was not authorized.",
        hint=("Install a local engine with `docvision setup --profile mineru --yes`, "
              "or pass `--allow-remote --provider mineru-cloud` after checking that "
              "uploading the document is acceptable."),
    )


def describe_route(provider: str) -> dict:
    local = provider in {"mineru-local", "paddleocr-local", "local-vlm"}
    labels = {
        "mineru-local": "MinerU 4 local",
        "paddleocr-local": "PaddleOCR-VL local",
        "local-vlm": "Local OpenAI-compatible VLM",
        "mineru-cloud": "MinerU Standard API",
        "paddleocr-cloud": "PaddleOCR hosted API",
        "mineru-agent": "MinerU Agent API (preview)",
        "glm-cloud": "Zhipu GLM-OCR API",
        "mistral": "Mistral OCR API",
        "gemini": "Google Gemini",
        "openai": "OpenAI-compatible vision API",
    }
    return {"provider": provider, "label": labels.get(provider, provider),
            "privacy": "local" if local else "uploaded", "remote": not local}


def tier_for(opts: Options, info: dict) -> str:
    if opts.tier in {"fast", "economy", "standard", "quality"}:
        return opts.tier
    return "standard"
