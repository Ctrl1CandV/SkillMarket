"""Provider registry.  Importing this module has no side effects."""

from __future__ import annotations

from . import gemini_cloud, glm_cloud, mineru_cloud, mineru_local, mistral_cloud, openai_compat, paddle_local, paddle_cloud


def run(provider: str, source: str, opts):
    if provider == "mineru-local":
        return mineru_local.convert(source, opts)
    if provider == "paddleocr-local":
        return paddle_local.convert(source, opts)
    if provider == 'paddleocr-cloud':
        return paddle_cloud.convert(source, opts)
    if provider == "mineru-cloud":
        return mineru_cloud.convert_standard(source, opts)
    if provider == "mineru-agent":
        return mineru_cloud.convert_agent(source, opts)
    if provider == "glm-cloud":
        return glm_cloud.convert(source, opts)
    if provider == "mistral":
        return mistral_cloud.convert(source, opts)
    if provider == "gemini":
        return gemini_cloud.convert(source, opts)
    if provider == "openai":
        return openai_compat.convert(source, opts, local=False)
    if provider == "local-vlm":
        return openai_compat.convert(source, opts, local=True)
    from ..base import DocVisionError
    raise DocVisionError(f"Unknown provider: {provider}")


PROVIDERS = {
    "mineru-local": {"layer": "local", "label": "MinerU 4 local", "quality": "high"},
    "paddleocr-local": {"layer": "local", "label": "PaddleOCR-VL 1.6 local", "quality": "high"},
    'paddleocr-cloud': {'layer': 'remote', 'label': 'PaddleOCR official API (account free quota)', 'quality': 'high'},
    "local-vlm": {"layer": "local", "label": "Local OpenAI-compatible VLM", "quality": "medium"},
    "mineru-cloud": {"layer": "remote", "label": "MinerU Standard API", "quality": "high"},
    "mineru-agent": {"layer": "remote", "label": "MinerU Agent API (preview)", "quality": "preview"},
    "glm-cloud": {"layer": "remote", "label": "Zhipu GLM-OCR", "quality": "high"},
    "mistral": {"layer": "remote", "label": "Mistral OCR", "quality": "high"},
    "gemini": {"layer": "remote", "label": "Google Gemini", "quality": "high"},
    "openai": {"layer": "remote", "label": "OpenAI-compatible vision", "quality": "custom"},
}
