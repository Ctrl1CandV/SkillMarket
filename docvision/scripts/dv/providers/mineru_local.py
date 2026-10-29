"""MinerU 4 local adapter (stateless `mineru-kit`)."""

from __future__ import annotations

import re
from pathlib import Path

from .. import config, util
from ..base import DocVisionError, Options
from ..detect import inspect_input
from .common import raw_from_mineru_zip


def _command(engine, source: str, out_dir: Path, opts: Options, info: dict) -> list[str]:
    if opts.device and opts.device != "auto":
        raise DocVisionError("MinerU 4 mineru-kit does not expose a device option; --device cannot be honored.",
                             hint="Use --device auto for MinerU, or choose paddleocr-local to select CPU/GPU.")
    tier = {"fast": "flash", "economy": "basic", "standard": "standard", "quality": "advanced"}.get(opts.tier, "standard")
    ocr_requested = opts.mode in {"ocr", "formula", "table", "chart"}
    if opts.mode == "text" and info.get("is_image"):
        raise DocVisionError("An image has no embedded text layer for --mode text.",
                             hint="Use --mode ocr with --tier economy, standard or quality.")
    if opts.mode == "text" and info.get("is_pdf"):
        tier = "flash"
    if tier == "flash" and (info.get("is_image") or ocr_requested):
        # Flash is text-layer extraction; a standalone image needs the OCR model.
        tier = "basic"
    cmd = [engine.exe, "parse", source, "-o", str(out_dir),
           "--format", "zip", "--tier", tier]
    if opts.pages:
        cmd += ["--pages", opts.pages]
    if opts.mode == "text" or (tier == "flash" and opts.mode != "ocr"):
        # Flash is the text-layer path; do not silently run the OCR model.
        cmd += ["--ocr-mode", "txt"]
    elif ocr_requested or info.get("needs_ocr"):
        cmd += ["--ocr-mode", "ocr"]
    else:
        cmd += ["--ocr-mode", "auto"]
    return cmd


def convert(source: str, opts: Options) -> tuple:
    engine = config.discover_mineru()
    if not engine.available:
        raise DocVisionError(
            "MinerU local engine is not installed.",
            hint="Run `docvision setup --profile mineru --sample <local PDF/image> --yes`, then `docvision doctor`.",
        )
    if util.is_url(source):
        raise DocVisionError("The local MinerU adapter expects a local file; download the URL first.")
    info = inspect_input(source, opts)
    tmp = util.staging_dir("mineru", base=opts.staging)
    try:
        return _parse(engine, source, opts, info, tmp)
    finally:
        util.release_staging(tmp)


def _parse(engine, source: str, opts, info: dict, tmp: Path):
    out_dir = util.ensure_dir(tmp / "out")
    cmd = _command(engine, source, out_dir, opts, info)
    if opts.dry_run:
        return None, {"command": cmd, "provider": "mineru-local", "engine": engine.exe}
    env = {"MINERU_HOME": str(engine.extra.get("mineru_home") or config.model_home("mineru"))}
    proc = util.run(cmd, timeout=opts.timeout, env=env)
    zips = sorted(out_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not zips:
        raise DocVisionError(
            f"MinerU produced no zip output (exit {proc.returncode}).\n{util.tail_text(proc)}",
            hint="Run `mineru-kit models verify --tier standard`; if the file is huge, reduce --pages.",
        )
    version = engine.version or ""
    match = re.search(r"\d+\.\d+\.\d+", version)
    label = f"MinerU 4 ({match.group(0)})" if match else "MinerU 4"
    doc = raw_from_mineru_zip(zips[0].read_bytes(), provider="mineru-local", model=label)
    if proc.returncode != 0:
        doc.warnings.append("MinerU exited non-zero but a result archive was available; inspect the tail.")
        doc.warnings.append(util.tail_text(proc, 800))
    doc.usage["command"] = " ".join(cmd)
    return doc, {"provider": "mineru-local", "engine": engine.exe, "version": engine.version}
