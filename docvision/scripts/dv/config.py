"""Configuration and engine discovery.

Only paths and public settings live in config.json. API keys are managed
separately by the credentials module and environment variables.
"""

from __future__ import annotations

import json
import os
import copy
import re
import time
from functools import lru_cache
from dataclasses import dataclass, field
from pathlib import Path

from . import util

DEFAULT_CONFIG = {
    "version": 1,
    "core": {"env": "docvision-core", "python": None},
    "models_dir": None,
    "engines": {
        "mineru": {"env": "docvision-mineru", "exe": None, "python": None,
                   "mineru_home": None, "tier": "standard"},
        "paddleocr": {"env": "docvision-paddle", "exe": None, "python": None,
                      "device": None},
        "vlm": {"base_url": "http://127.0.0.1:11434/v1", "model": "",
                "api_key_env": "DOCVISION_VLM_API_KEY"},
    },
    # consent: unset | remote | local-only. Local-only is sticky: it refuses
    # every remote call until the user explicitly re-enables it.
    "remote": {
        "default": "paddleocr-cloud",
        "consent": "unset",
        "paddle_base": "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
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


# Short lived, process-local only. A doctor always refreshes detailed checks;
# installs/config changes never rely on an indefinitely cached diagnosis.
_DISCOVERY: dict[tuple, tuple[float, Engine]] = {}
DISCOVERY_TTL = 60
PADDLE_PIPELINE_VERSION = "v1.6"


def _cached(name, cfg, refresh, discover):
    key = (name, json.dumps(cfg, sort_keys=True), os.environ.get("PATH"),
           str(util.config_path()), str(model_home("mineru", cfg)),
           str(model_home("paddlex", cfg)), os.environ.get("PYTHONNOUSERSITE"))
    now = time.monotonic()
    previous = _DISCOVERY.get(key)
    if not refresh and previous and now - previous[0] < DISCOVERY_TTL:
        return copy.deepcopy(previous[1])
    result = discover(cfg)
    _DISCOVERY[key] = (now, copy.deepcopy(result))
    return result


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


def _stored_path(value: str) -> Path:
    """Old relative settings are anchored to the configuration, never the project."""
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = util.config_path().parent / path
    return path.resolve()


def models_root(cfg: dict | None = None, *, use_environment: bool = True) -> Path:
    """Fixed model root: config override, then DOCVISION_MODELS, then app data."""
    cfg = load() if cfg is None else cfg
    configured = (cfg.get("models_dir") or "").strip()
    return _stored_path(configured) if configured else (util.models_dir() if use_environment else util.app_dir() / 'models')


def model_home(name: str, cfg: dict | None = None, *, use_environment: bool = True) -> Path:
    """Fixed per-engine model folder, reusing an existing legacy install.

    A machine that already downloaded weights to ~/.mineru or ~/.paddlex keeps
    using them instead of re-downloading gigabytes; a fresh install gets the
    fixed application-data path.  An explicit models_dir/DOCVISION_MODELS
    disables the legacy fallback. Transactional installs may pin an engine's
    active model_home within that root; DOCVISION_MODELS explicitly overrides it.
    """
    cfg = load() if cfg is None else cfg
    if use_environment and os.environ.get('DOCVISION_MODELS'):
        return util.models_dir() / name
    engine_name = {'mineru': 'mineru', 'paddlex': 'paddleocr'}.get(name)
    active_home = cfg.get('engines', {}).get(engine_name, {}).get('model_home')
    if active_home:
        return _stored_path(active_home)
    configured = (cfg.get("models_dir") or "").strip()
    explicit = bool(configured) or (use_environment and bool(os.environ.get("DOCVISION_MODELS")))
    root = models_root(cfg, use_environment=use_environment) / name
    if explicit:
        return root
    if name == "mineru":
        engine_home = cfg.get("engines", {}).get("mineru", {}).get("mineru_home")
        if engine_home:
            return _stored_path(engine_home)
    variable = {"mineru": "MINERU_HOME", "paddlex": "PADDLE_PDX_CACHE_HOME"}.get(name)
    inherited = os.environ.get(variable) if variable and use_environment else None
    if inherited:
        return util._absolute_storage(inherited, variable)
    legacy = {"mineru": Path.home() / ".mineru", "paddlex": Path.home() / ".paddlex"}.get(name)
    if legacy and not root.exists() and legacy.exists():
        return legacy
    return root


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


def discover_mineru(cfg: dict | None = None, *, refresh: bool = False) -> Engine:
    return _cached("mineru", cfg or load(), refresh, _discover_mineru)


def _discover_mineru(cfg: dict) -> Engine:
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
        available=bool(exe and detail == "ok"),
        detail=detail if exe else "mineru-kit not found",
        extra={"mineru_home": str(model_home("mineru", cfg))},
    )


def discover_paddle(cfg: dict | None = None, *, refresh: bool = False,
                    detailed: bool = False) -> Engine:
    cfg = cfg or load()
    # Executable lookup is cached, while isolated package metadata is checked
    # cheaply on every call so an in-place upgrade invalidates resume promptly.
    paths = _cached("paddleocr-paths", cfg, refresh, _discover_paddle)
    versions, fingerprint = _paddle_metadata(paths.python)
    engine = paths
    if detailed:
        engine = _cached("paddleocr-detailed:" + str(fingerprint), cfg, refresh,
                         lambda data: _discover_paddle(data, detailed=True))
    engine.version = (f"PaddleOCR {versions['paddleocr']} / PaddleX {versions['paddlex']} / "
                      f"Paddle {versions['paddle']} / pipeline {PADDLE_PIPELINE_VERSION}") if fingerprint else None
    engine.extra.update({"package_versions": versions, "pipeline_version": PADDLE_PIPELINE_VERSION,
                         "cache_fingerprint": fingerprint})
    return engine


@lru_cache(maxsize=128)
def _metadata_header(path: str, modified_ns: int, size: int) -> tuple[str, str]:
    """The stat values key the small header cache; no runtime imports needed."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as stream:
            header = stream.read(65536).split("\n\n", 1)[0]
        name = re.search(r"(?m)^Name:\s*(.+)$", header)
        version = re.search(r"(?m)^Version:\s*(.+)$", header)
        return (name.group(1).strip().lower().replace("_", "-"), version.group(1).strip()) if name and version else ("", "")
    except OSError:
        return "", ""


def _paddle_metadata(python: str | None) -> tuple[dict, str | None]:
    if not python:
        return {}, None
    parent = Path(python).parent
    prefix = parent.parent if parent.name.lower() in {"scripts", "bin"} else parent
    sites = [prefix / "Lib" / "site-packages"]
    sites.extend((prefix / "lib").glob("python*/site-packages"))
    found: dict[str, list[str]] = {}
    stamps = []
    for site in sites:
        for metadata in sorted(site.glob("paddle*.dist-info/METADATA")):
            try:
                stat = metadata.stat()
            except OSError:
                continue
            name, version = _metadata_header(str(metadata), stat.st_mtime_ns, stat.st_size)
            if name in {"paddleocr", "paddlex", "paddlepaddle", "paddlepaddle-gpu"} and version:
                normalized = "paddle" if name.startswith("paddlepaddle") else name
                found.setdefault(normalized, []).append(version)
                stamps.append((str(metadata), stat.st_mtime_ns, stat.st_size, version))
    versions = {name: values[0] for name, values in found.items() if len(values) == 1}
    if not all(name in versions for name in ("paddleocr", "paddlex", "paddle")):
        return versions, None
    return versions, util.sha256_bytes(json.dumps({"metadata": stamps, "pipeline": PADDLE_PIPELINE_VERSION},
                                                 sort_keys=True).encode())


PADDLE_CHECK = r'''
import importlib.metadata as m, json
from packaging.requirements import Requirement
missing = []
for package, extras in [('paddlex', ['ocr', 'genai-client']), ('paddleocr', ['doc-parser'])]:
    for item in m.requires(package) or []:
        req = Requirement(item)
        if req.marker and not any(req.marker.evaluate({'extra': x}) for x in extras):
            continue
        try:
            version = m.version(req.name)
            if req.specifier and not req.specifier.contains(version, prereleases=True):
                missing.append(str(req))
        except m.PackageNotFoundError:
            missing.append(req.name)
gpu = None
try:
    import paddle, paddleocr
    gpu = {'version': paddle.__version__, 'device': paddle.device.get_device(),
           'cuda': str(paddle.device.is_compiled_with_cuda())}
except Exception as exc:
    missing.append('import: ' + str(exc))
print(json.dumps({'version': m.version('paddleocr'), 'gpu': gpu,
                  'dependencies': {'ok': not missing, 'missing': sorted(set(missing))}}))
'''


def _discover_paddle(cfg: dict, *, detailed: bool = False) -> Engine:
    cfg = cfg or load()
    ecfg = cfg.get("engines", {}).get("paddleocr", {})
    exe = ecfg.get("exe")
    if not exe or not Path(exe).is_file():
        exe = util.resolve_env_exe("paddleocr", ecfg.get("env"))
    version, detail = None, "executable found; runtime not checked"
    python = ecfg.get("python")
    if not python and exe:
        prefix = Path(exe).parent.parent
        py = util.env_python(prefix)
        python = str(py) if py.is_file() else None
    gpu, dependencies = None, {"ok": None, "detail": "not checked"}
    if python and detailed:
        try:
            proc = util.run([python, "-s", "-c", PADDLE_CHECK], timeout=120,
                            env={**util.isolated_python_env(),
                                 "PADDLE_PDX_CACHE_HOME": str(model_home("paddlex", cfg))})
            if proc.returncode == 0:
                payload = json.loads((proc.stdout or "").strip().splitlines()[-1])
                version, gpu = payload.get("version"), payload.get("gpu")
                dependencies = payload["dependencies"]
                detail = "dependencies/imports OK; pipeline and inference not tested" if dependencies["ok"] else (
                    "missing/incompatible dependencies: " + ", ".join(dependencies.get("missing") or []))
            else:
                dependencies = {"ok": False, "detail": util.tail_text(proc, 1500)}
                detail = "isolated runtime check failed: " + util.tail_text(proc, 300)
        except Exception as exc:
            dependencies = {"ok": False, "detail": str(exc)}
            detail = "isolated runtime check failed: " + str(exc)[:250]
    elif detailed:
        dependencies = {"ok": False, "detail": "engine Python not found"}
        detail = "engine Python not found"
    return Engine(
        name="paddleocr",
        exe=exe,
        python=python,
        env=ecfg.get("env"),
        version=version,
        available=bool(exe and dependencies.get("ok") is not False),
        detail=detail if exe else "paddleocr not found",
        extra={"gpu": gpu, "installed": bool(exe), "dependencies": dependencies,
               "isolation": "user site disabled for Paddle subprocess only",
               "paddlex_home": str(model_home("paddlex", cfg)),
               "device": ecfg.get("device") or ("gpu:0" if gpu and gpu.get("cuda") == "True" else "cpu")},
    )


def effective_vlm_config(extra: dict | None = None, cfg: dict | None = None) -> dict:
    """Resolve public VLM settings consistently for discovery, execution and cache.

    Explicit call options win over environment variables, which win over stored
    settings. Return the credential variable's name, never its secret value.
    """
    cfg = load() if cfg is None else cfg
    vcfg = cfg.get("engines", {}).get("vlm", {})
    extra = extra or {}
    return {
        "base_url": extra.get("base_url") or util.env_value("DOCVISION_OPENAI_BASE_URL", "OPENAI_BASE_URL")
                    or vcfg.get("base_url") or "",
        "model": extra.get("model") or util.env_value("DOCVISION_OPENAI_MODEL", "OPENAI_MODEL")
                 or vcfg.get("model") or "",
        "api_key_env": vcfg.get("api_key_env") or "DOCVISION_VLM_API_KEY",
    }


def discover_vlm(cfg: dict | None = None) -> Engine:
    vcfg = effective_vlm_config(cfg=cfg)
    base, model = vcfg["base_url"], vcfg["model"]
    local = False
    if base and model:
        from .base import DocVisionError
        try:
            util.validate_local_http_url(base)
            local = True
        except DocVisionError:
            pass
    return Engine(
        name="vlm",
        available=local,
        detail=("configured" if local else "set a loopback HTTP endpoint and vision model"),
        extra={"base_url": base, "model": model,
               "api_key": util.env_value(vcfg.get("api_key_env") or "DOCVISION_VLM_API_KEY", "OPENAI_API_KEY")},
    )


def engine_status(cfg: dict | None = None, *, refresh: bool = False) -> dict[str, Engine]:
    return {
        "mineru": discover_mineru(cfg, refresh=refresh),
        "paddleocr": discover_paddle(cfg, refresh=refresh, detailed=True),
        "vlm": discover_vlm(cfg),
    }


def remote_keys() -> dict[str, str | None]:
    """Only PaddleOCR is a remote OCR route; local VLM stays local."""
    return {
        "paddle": util.env_value("DOCVISION_PADDLE_TOKEN", "PADDLEOCR_ACCESS_TOKEN",
                                 "PADDLEOCR_API_TOKEN", "AI_STUDIO_TOKEN", "PADDLEAPIKEY"),
    }


def remote_consent() -> str:
    """unset | remote | local-only; an unrecognized value is treated as unset."""
    value = (load().get("remote", {}) or {}).get("consent")
    return value if value in {"remote", "local-only"} else "unset"


def set_consent(mode: str) -> Path:
    if mode not in {"remote", "local-only"}:
        raise ValueError(f"unsupported consent mode: {mode}")
    data = load()
    data.setdefault("remote", {})["consent"] = mode
    return save(data)


def masked_keys() -> dict[str, str]:
    result = {}
    for name, value in remote_keys().items():
        result[name] = "set" if value else "not set"
    return result
