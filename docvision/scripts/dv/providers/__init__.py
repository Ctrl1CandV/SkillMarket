"""Provider registry.  Importing this module has no side effects.

Local: MinerU 4, PaddleOCR-VL, and an optional OpenAI-compatible VLM that runs
on this machine.  Remote: PaddleOCR's official API only — the single upload
route the skill is designed and tested around.
"""

from __future__ import annotations

from . import mineru_local, openai_compat, paddle_cloud, paddle_local, text_local


def run(provider: str, source: str, opts):
    if (PROVIDERS.get(provider) or {}).get('layer') == 'remote':
        from .. import config
        from ..base import DocVisionError
        if config.remote_consent() != 'remote':
            raise DocVisionError('Remote upload is not enabled for this OS user.',
                                 hint='Confirm upload is acceptable and run `docvision setup --remote`.')
        if not opts.allow_remote:
            raise DocVisionError('Remote upload requires --allow-remote on this call.')
    if provider == "text-local":
        return text_local.convert(source, opts)
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
    "text-local": {"layer": "local", "label": "PDF text layer (no OCR/model)", "quality": "text-only"},
    "mineru-local": {"layer": "local", "label": "MinerU 4 local", "quality": "high"},
    "paddleocr-local": {"layer": "local", "label": "PaddleOCR-VL 1.6 local", "quality": "high"},
    "local-vlm": {"layer": "local", "label": "Local OpenAI-compatible VLM", "quality": "medium"},
    "paddleocr-cloud": {"layer": "remote", "label": "PaddleOCR official API (account free quota)", "quality": "high"},
}
