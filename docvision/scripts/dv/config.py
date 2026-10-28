"""Configuration and engine discovery.

Only paths and public settings live in config.json.  API keys stay in
environment variables; the skill never writes credentials to disk.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from . import util

DEFAULT_CONFIG = {
    "version": 1,
    "engines": {
        "mineru": {"env": "docvision-mineru", "exe": None, "python": None,
                   "mineru_home": None, "tier": "standard"},
        "paddleocr": {"env": "docvision-paddle", "exe": None, "python": None,
                      "device": "gpu:0"},
        "vlm": {"base_url": "http://127.0.0.1:11434/v1", "model": "",
                "api_key_env": "DOCVISION_VLM_API_KEY"},
    },
    "remote": {
        "default": "mineru-cloud",
        "glm_base": "https://open.bigmodel.cn/api/paas/v4",
        "mistral_base": "https://api.mistral.ai/v1",
        "gemini_base": "https://generativelanguage.googleapis.com/v1beta",
        "gemini_model": "",
    },
    "output": {"default_dir": "docvision-out"},
}


@dataclass
class Engine:
    name: str
    exe: str | None = None
    python: str | None = None
    env: str | None = None
    version: str | None = None
    available: bool = False
    detail: str = ""
    extra: dict = field(default_factory=dict)


def load() -> dict:
    path = util.config_path()
    data = util.read_json(path, None)
    result = json.loads(json.dumps(DEFAULT_CONFIG))
    if isinstance(data, dict):
        _merge(result, data)
    return result


def _merge(base: dict, override: dict) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value


def save(data: dict) -> Path:
    path = util.config_path()
    util.write_json(path, data)
    return path


def set_engine(name: str, **values) -> dict:
    data = load()
    data.setdefault("engines", {}).setdefault(name, {}).update(values)
    save(data)
    return data


def env_value(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _exe_version(exe: str, *, args: list[str] | None = None) -> tuple[str | None, str]:
    if not exe or not Path(exe).is_file():
        return None, "not found"
    try:
        proc = util.run([exe] + (args or ["--version"]), timeout=20)
        text = (proc.stdout or "").strip() or (proc.stderr or "").strip()
        first = text.splitlines()[0] if text else ""
        if proc.returncode != 0:
            return first[:120] or None, f"exit {proc.returncode}"
        # MinerU's Windows console may emit Chinese in the local code page;
        # keep the version number, not mojibake, and never print a secret.
        if "MinerU" in first or "mineru" in first:
            import re
            match = re.search(r"\d+\.\d+\.\d+", first)
            if match:
                return f"MinerU {match.group(0)}", "ok"
        if "�" in first:
            first = "".join(ch for ch in first if ch.isascii()).strip()
        return first[:120] or None, "ok"
    except Exception as exc:
        return None, str(exc)[:160]


def discover_mineru(cfg: dict | None = None) -> Engine:
    cfg = cfg or load()
    ecfg = cfg.get("engines", {}).get("mineru", {})
    exe = ecfg.get("exe")
    if not exe or not Path(exe).is_file():
        exe = util.resolve_env_exe("mineru-kit", ecfg.get("env"))
    version, detail = _exe_version(exe, args=["--help"])
    # `mineru-kit --version` may not exist; derive version from mineru if possible.
    mineru_exe = str(Path(exe).with_name("mineru.exe" if util.IS_WINDOWS else "mineru")) if exe else None
    if mineru_exe and Path(mineru_exe).is_file():
        v, _ = _exe_version(mineru_exe)
        if v:
            version = v
    python = ecfg.get("python")
    if not python and exe:
        python = str(util.env_python(Path(exe).parent.parent)) if "Scripts" in exe or "/bin/" in exe.replace("\\", "/") else None
    return Engine(
        name="mineru",
        exe=exe,
        python=python if python and Path(python).is_file() else None,
        env=ecfg.get("env"),
        version=version,
        available=bool(exe),
        detail=detail if exe else "mineru-kit not found",
        extra={"mineru_home": ecfg.get("mineru_home") or os.environ.get("MINERU_HOME")
               or str(Path.home() / ".mineru")},
    )


def discover_paddle(cfg: dict | None = None) -> Engine:
    cfg = cfg or load()
    ecfg = cfg.get("engines", {}).get("paddleocr", {})
    exe = ecfg.get("exe")
    if not exe or not Path(exe).is_file():
        exe = util.resolve_env_exe("paddleocr", ecfg.get("env"))
    version, detail = _exe_version(exe)
    python = ecfg.get("python")
    if not python and exe:
        prefix = Path(exe).parent.parent
        py = util.env_python(prefix)
        python = str(py) if py.is_file() else None
    gpu = None
    if python:
        try:
            proc = util.run([python, "-c",
                             "import paddle;print(paddle.__version__);print(paddle.device.get_device());print(paddle.device.is_compiled_with_cuda())"],
                            timeout=30)
            lines = [x.strip() for x in (proc.stdout or "").splitlines() if x.strip()]
            if proc.returncode == 0 and lines:
                gpu = {"version": lines[0], "device": lines[1] if len(lines) > 1 else "",
                       "cuda": lines[2] if len(lines) > 2 else ""}
                if not version:
                    version = lines[0]
        except Exception:
            pass
    return Engine(
        name="paddleocr",
        exe=exe,
        python=python,
        env=ecfg.get("env"),
        version=version,
        available=bool(exe),
        detail=detail if exe else "paddleocr not found",
        extra={"gpu": gpu, "device": ecfg.get("device") or ("gpu:0" if gpu and gpu.get("cuda") == "True" else "cpu")},
    )


def discover_vlm(cfg: dict | None = None) -> Engine:
    cfg = cfg or load()
    vcfg = cfg.get("engines", {}).get("vlm", {})
    base = vcfg.get("base_url") or ""
    model = vcfg.get("model") or ""
    return Engine(
        name="vlm",
        available=bool(base and model),
        detail=("configured" if base and model else "set engines.vlm.base_url and model"),
        extra={"base_url": base, "model": model,
               "api_key": util.env_value(vcfg.get("api_key_env") or "DOCVISION_VLM_API_KEY", "OPENAI_API_KEY")},
    )


def engine_status(cfg: dict | None = None) -> dict[str, Engine]:
    return {
        "mineru": discover_mineru(cfg),
        "paddleocr": discover_paddle(cfg),
        "vlm": discover_vlm(cfg),
    }


def remote_keys() -> dict[str, str | None]:
    return {
        "mineru": util.env_value("DOCVISION_MINERU_TOKEN", "MINERU_TOKEN", "MINERU_API_KEY"),
        "glm": util.env_value("DOCVISION_GLM_API_KEY", "ZHIPU_API_KEY", "GLM_API_KEY"),
        "mistral": util.env_value("DOCVISION_MISTRAL_API_KEY", "MISTRAL_API_KEY"),
        "gemini": util.env_value("DOCVISION_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "openai": util.env_value("DOCVISION_OPENAI_API_KEY", "OPENAI_API_KEY"),
    }


def masked_keys() -> dict[str, str]:
    result = {}
    for name, value in remote_keys().items():
        result[name] = "set" if value else "not set"
    return result
