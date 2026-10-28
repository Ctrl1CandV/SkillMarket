"""Provider registry.  Importing this module has no side effects.

Local: MinerU 4, PaddleOCR-VL, and an optional OpenAI-compatible VLM that runs
on this machine.  Remote: PaddleOCR's official API only — the single upload
route the skill is designed and tested around.
"""

from __future__ import annotations

from . import mineru_local, openai_compat, paddle_cloud, paddle_local


def run(provider: str, source: str, opts):
    if provider == "mineru-local":
        return mineru_local.convert(source, opts)
    if provider == "paddleocr-local":
        return paddle_local.convert(source, opts)
    if provider == "paddleocr-cloud":
        return paddle_cloud.convert(source, opts)
    if provider == "local-vlm":
        return openai_compat.convert(source, opts)
    from ..base import DocVisionError
    raise DocVisionError(f"Unknown provider: {provider}")


PROVIDERS = {
    "mineru-local": {"layer": "local", "label": "MinerU 4 local", "quality": "high"},
    "paddleocr-local": {"layer": "local", "label": "PaddleOCR-VL 1.6 local", "quality": "high"},
    "local-vlm": {"layer": "local", "label": "Local OpenAI-compatible VLM", "quality": "medium"},
    "paddleocr-cloud": {"layer": "remote", "label": "PaddleOCR official API (account free quota)", "quality": "high"},
}
