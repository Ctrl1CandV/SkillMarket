"""PaddleOCR-VL local adapter (PaddleOCR 3.7 CLI, GPU or CPU)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .. import config, util
from ..base import DocVisionError, Options, RawBlock, RawDoc, RawPage, block_markdown
from ..detect import inspect_input
from .common import map_block_type, page_markdown


def _subprocess_env(engine) -> dict[str, str]:
    """Isolated interpreter plus the fixed model cache so weights never float."""
    env = dict(util.isolated_python_env())
    env["PADDLE_PDX_CACHE_HOME"] = str(engine.extra.get("paddlex_home") or config.model_home("paddlex"))
    return env


def _device(engine, opts: Options) -> str:
    if opts.device and opts.device != "auto":
        return opts.device
    gpu = (engine.extra.get("gpu") or {})
    if engine.extra.get("device"):
        return engine.extra["device"]
    if gpu.get("cuda") == "True":
        return engine.extra.get("device") or "gpu:0"
    return "cpu"


def _command(engine, source: Path, out_dir: Path, opts: Options, device: str) -> list[str]:
    cmd = [engine.exe, "doc_parser", "-i", str(source), "--save_path", str(out_dir),
           "--pipeline_version", config.PADDLE_PIPELINE_VERSION, "--device", device,
           "--use_doc_orientation_classify", "False",
           "--use_doc_unwarping", "False"]
    if opts.mode == "chart":
        cmd += ["--use_chart_recognition", "True"]
    task = opts.extra.get("refine_task")
    if opts.extra.get("refine_is_region") and task in {"formula", "table"}:
        # Verified against PaddleOCR v3.7.0's doc_parser CLI executor:
        # https://github.com/PaddlePaddle/PaddleOCR/blob/v3.7.0/paddleocr/_pipelines/paddleocr_vl.py
        installed = (engine.extra.get("package_versions") or {}).get("paddleocr", "")
        if not re.match(r"^3\.7\.\d+(?:$|[.+-])", installed):
            raise DocVisionError(
                "Local formula/table region recognition requires a verified PaddleOCR 3.7.x runtime; "
                f"detected {installed or 'unknown version'}.",
                hint="Configure a compatible isolated Paddle environment, or use --provider packet to inspect the crop.",
            )
        cmd += ["--use_layout_detection", "False", "--prompt_label", task,
                "--format_block_content", "True"]
    return cmd


def _read_pages(out_dir: Path, *, page_map: list[int] | None, source: Path,
                source_page_base: int = 0) -> list[RawPage]:
    pages: list[RawPage] = []
    json_files = sorted(out_dir.glob("*_res.json"))
    if not json_files:
        json_files = sorted(out_dir.glob("*.json"))
    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        local_idx = data.get("page_index")
        if local_idx is None:
            local_idx = 0
        local_idx = int(local_idx)
        page_no = (page_map[local_idx] + 1) if page_map and local_idx < len(page_map) else local_idx + 1
        width, height = data.get("width"), data.get("height")
        rp = RawPage(page=page_no, width=width, height=height)
        # Matching Markdown produced by PaddleOCR for this page.
        stem = jf.name[:-9] if jf.name.endswith("_res.json") else jf.stem
        md_file = out_dir / f"{stem}.md"
        page_md = md_file.read_text(encoding="utf-8", errors="replace") if md_file.is_file() else ""
        for b_idx, block in enumerate(data.get("parsing_res_list") or []):
            if not isinstance(block, dict):
                continue
            label = str(block.get("block_label") or "text")
            mapped = map_block_type(label)
            text = block.get("block_content") or ""
            bbox = util.normalize_bbox_pixels(block.get("block_bbox"), width, height)
            md = text.strip() if mapped == "table" else block_markdown(mapped, text)
            rp.blocks.append(RawBlock(
                type=mapped, markdown=md, text=text, page=page_no, bbox=bbox,
                meta={"provider_type": label, "local_page_index": local_idx},
            ))
        # Defer block-based assembly until crops have received their asset URLs.
        rp.markdown = page_md.strip()
        if rp.markdown:
            # Paddle's Markdown export can omit a recognized footnote or chart
            # table. Keep the original layout and append only missing content.
            for block in rp.blocks:
                if block.type == "chart" or block.meta.get("provider_type") == "footnote":
                    content = block.markdown.strip()
                    if content and "".join(content.split()) not in "".join(rp.markdown.split()):
                        rp.markdown += "\n\n" + content
        pages.append(rp)
    pages.sort(key=lambda p: p.page)
    return pages


def _crop_image_blocks(pages: list[RawPage], source: Path, out_dir: Path,
                       page_map: list[int] | None) -> dict[str, bytes]:
    """Render page images only when a block needs an image crop."""
    assets: dict[str, bytes] = {}
    for page in pages:
        if not any(b.type in {"image", "chart"} and not b.asset for b in page.blocks):
            continue
        local_idx = None
        for block in page.blocks:
            if block.meta.get("local_page_index") is not None:
                local_idx = block.meta["local_page_index"]
                break
        if local_idx is None:
            local_idx = page.page - 1
        try:
            if source.suffix.lower() == ".pdf":
                page_png = util.render_pdf_page(source, local_idx)
            else:
                page_png = source.read_bytes()
        except Exception:
            continue
        for block in page.blocks:
            if block.type not in {"image", "chart"} or block.asset or not block.bbox:
                continue
            name = f"page-{page.page:04d}-{block.type}-{len(assets) + 1}.png"
            tmp = out_dir / name
            if util.crop_image(page_png, block.bbox, tmp):
                assets[name] = tmp.read_bytes()
                block.asset = name
                image_md = f"![{block.type}]({name})"
                # A chart may contain recognized HTML/data; retain it beside
                # the source crop rather than replacing the recognition.
                content = block.markdown.strip()
                if content == "![image]()":
                    content = ""
                block.markdown = "\n\n".join(x for x in (content, image_md) if x)
    return assets


def _export_images(out_dir: Path) -> dict[str, bytes]:
    """Keep Paddle's original relative links; the output writer remaps them."""
    root = out_dir.resolve()
    return {path.relative_to(out_dir).as_posix(): path.read_bytes()
            for path in out_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in util.SUPPORTED_IMAGE_EXT
            and not path.stem.endswith("_layout_det_res")
            and path.resolve().is_relative_to(root)}


def convert(source: str, opts: Options) -> tuple:
    engine = config.discover_paddle()
    if not engine.available:
        raise DocVisionError(
            "PaddleOCR-VL local engine is not installed.",
            hint="Run `docvision setup --profile paddle --sample <local PDF/image> --yes`, then `docvision doctor`.",
        )
    if util.is_url(source):
        raise DocVisionError("The local PaddleOCR adapter expects a local file; download the URL first.")
    info = inspect_input(source, opts)
    if info["suffix"] not in util.SUPPORTED_EXT:
        raise DocVisionError(f"PaddleOCR does not accept {info['suffix']} here.")
    device = _device(engine, opts)
    tmp = util.staging_dir("paddle", base=opts.staging)
    try:
        return _parse(engine, source, opts, info, device, tmp)
    finally:
        util.release_staging(tmp)


def _parse(engine, source: str, opts, info: dict, device: str, tmp: Path):
    work_source = Path(source)
    page_map: list[int] | None = None
    if opts.pages and info["is_pdf"]:
        work_source, page_map = util.split_pdf_pages(work_source, opts.pages, tmp)
    out_dir = util.ensure_dir(tmp / "out")
    cmd = _command(engine, work_source, out_dir, opts, device)
    if opts.dry_run:
        return None, {"command": cmd, "provider": "paddleocr-local", "engine": engine.exe,
                      "device": device}
    proc = util.run(cmd, timeout=opts.timeout, env=_subprocess_env(engine))
    pages = _read_pages(out_dir, page_map=page_map, source=work_source)
    if not pages:
        raise DocVisionError(
            f"PaddleOCR produced no page JSON (exit {proc.returncode}).\n{util.tail_text(proc)}",
            hint="Check `paddleocr doc_parser --help`, the CUDA/cuDNN versions, and whether models downloaded.",
        )
    # PaddleOCR's save_all can fail on a missing export dependency after writing
    # JSON/Markdown; keep the usable result and report the tail as a warning.
    warnings: list[str] = []
    if proc.returncode != 0:
        warnings.append("PaddleOCR exited non-zero after writing page results; inspect the tail below.")
        warnings.append(util.tail_text(proc, 1000))
    assets = _export_images(out_dir)
    assets.update(_crop_image_blocks(pages, work_source, out_dir, page_map))
    markdown = "\n\n".join(
        f"<!-- page: {p.page} -->\n\n{page_markdown(p)}".strip()
        for p in pages if page_markdown(p).strip()
    ).strip()
    if not markdown:
        warnings.append("All page Markdown bodies were empty; inspect content.json and the page images.")
    model = "PaddleOCR-VL-1.6"
    return (
        RawDoc(
            markdown=markdown, pages=pages, assets=assets, provider="paddleocr-local",
            model=model, warnings=warnings, usage={"command": " ".join(cmd), "device": device},
        ),
        {"provider": "paddleocr-local", "engine": engine.exe, "version": engine.version,
         "device": device, "pages": len(pages)},
    )
