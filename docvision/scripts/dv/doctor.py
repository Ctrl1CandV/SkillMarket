"""Environment and provider self-check.  Never prints secrets."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from . import config, util
from .providers.mineru_cloud import probe_token


def _module(name: str) -> dict:
    import importlib.util
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):
        spec = None
    if not spec:
        return {"ok": False, "detail": "not installed"}
    try:
        mod = __import__(name)
        version = getattr(mod, "__version__", "")
        return {"ok": True, "detail": version or "installed"}
    except Exception as exc:
        return {"ok": False, "detail": f"import failed: {exc}"}


def _models(engine) -> dict:
    if engine.name == "mineru":
        home = Path(engine.extra.get("mineru_home") or (Path.home() / ".mineru"))
        std = [home / "models" / "MinerU2.5-Pro-2605-1.2B-GGUF",
               home / "models" / "MinerU-4_models_onnx"]
        present = [p.name for p in std if p.exists()]
        return {"dir": str(home / "models"), "standard_present": len(present) == len(std),
                "detail": ", ".join(present) if present else "standard models not downloaded"}
    if engine.name == "paddleocr":
        cache = Path.home() / ".paddlex" / "official_models"
        found = []
        if cache.is_dir():
            found = [p.name for p in cache.iterdir() if p.is_dir()]
        return {"dir": str(cache), "standard_present": any("PaddleOCR-VL" in n for n in found),
                "ready": None, "validation": "not run",
                "detail": ", ".join(found[:8]) if found else "models download on first run"}
    return {}


def _remote_probe(name: str, key: str | None) -> dict:
    if not key:
        return {"ok": False, "detail": "key not set"}
    try:
        if name == "paddle":
            return {"ok": None, "detail": "key present; authentication and inference not tested (no non-billable probe)"}
        if name == "mineru":
            return probe_token(key)
        if name == "mistral":
            base = (config.load().get("remote", {}).get("mistral_base")
                    or "https://api.mistral.ai/v1").rstrip("/")
            status, body = util.get_json(base + "/models", timeout=20,
                                         headers={"Authorization": "Bearer " + key})
            return {"ok": status < 400, "detail": f"HTTP {status}"}
        if name == "gemini":
            base = (config.load().get("remote", {}).get("gemini_base")
                    or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
            status, body = util.get_json(base + "/models?key=" + key, timeout=20)
            return {"ok": status < 400, "detail": f"HTTP {status}"}
        if name == "openai":
            base = util.env_value("DOCVISION_OPENAI_BASE_URL", "OPENAI_BASE_URL") or "https://api.openai.com/v1"
            status, body = util.get_json(base.rstrip("/") + "/models", timeout=20,
                                         headers={"Authorization": "Bearer " + key})
            return {"ok": status < 400, "detail": f"HTTP {status}"}
        if name == "glm":
            # Zhipu has no free models endpoint; presence is the only non-billable check.
            return {"ok": True, "detail": "key present (not called)"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:200]}
    return {"ok": False, "detail": "unknown provider"}


def collect(*, probe: bool = False) -> dict:
    engines = config.engine_status(refresh=True)
    core = {name: _module(name) for name in ("pypdfium2", "PIL", "pypdf")}
    core_python = config.load().get("core", {}).get("python")
    if not all(item.get("ok") for item in core.values()) and core_python and Path(core_python).is_file():
        try:
            script = ("import importlib.util,json; "
                      "print(json.dumps({name: {'ok': importlib.util.find_spec(name) is not None, "
                      "'detail': 'configured core Python'} for name in ('pypdfium2','PIL','pypdf')}))")
            proc = util.run([core_python, "-s", "-c", script], timeout=20,
                            env=util.isolated_python_env())
            checked_core = json.loads(proc.stdout.strip()) if proc.returncode == 0 else {}
            if checked_core and all(item.get("ok") for item in checked_core.values()):
                core = checked_core
        except Exception:
            pass
    keys = config.remote_keys()
    remotes = {}
    for name, key in keys.items():
        item = {"configured": bool(key)}
        if key:
            item["probe"] = _remote_probe(name, key) if probe else {"ok": None, "detail": "not probed"}
        remotes[name] = item
    gpu = util.gpu_summary()
    local_available = any(e.available for e in engines.values() if e.name != "vlm") or engines["vlm"].available
    remote_available = any(bool(v) for v in keys.values())
    remote_usable = remote_available
    if probe:
        checked = [item["probe"] for item in remotes.values()
                   if item.get("configured") and (item.get("probe") or {}).get("ok") is not None]
        remote_usable = any(p.get("ok") for p in checked) if checked else False
    engine_data = {}
    for name, engine in engines.items():
        engine_data[name] = {
            "available": engine.available,
            "exe": engine.exe,
            "python": engine.python,
            "env": engine.env,
            "version": engine.version,
            "detail": engine.detail,
            "models": _models(engine) if engine.available else {},
            "extra": {k: v for k, v in engine.extra.items() if k != "api_key"},
        }
    actions = []
    if not engines["mineru"].available:
        actions.append("Install the default local engine: docvision setup --profile mineru --yes")
    if engines["mineru"].available and not (engine_data["mineru"]["models"] or {}).get("standard_present"):
        actions.append("Download MinerU standard models: mineru-kit models download --tier standard")
    if not all(item.get("ok") for item in core.values()):
        actions.append("For page rendering/cropping: docvision setup --profile core --yes")
    if not remote_available:
        actions.append("Optional region refinement: set PADDLEOCR_ACCESS_TOKEN for official OCR quota, or GEMINI_API_KEY for diagram interpretation (never commit keys).")
    elif probe and not remote_usable:
        actions.append("No configured remote route has a successful authentication probe; inspect probe details or use local OCR.")
    paddle = engines["paddleocr"]
    if paddle.extra.get("installed") and not paddle.available:
        actions.append("Repair Paddle's isolated dependencies: docvision setup --profile paddle --yes; then test one page.")
    if not local_available and not remote_available:
        actions.append("No OCR route is ready; install a local engine or configure one remote key.")
    return {
        "schema": "docvision.doctor/1",
        "platform": util.platform_summary(),
        "ram_gb": util.total_ram_gb(),
        "gpu": gpu,
        "config_path": str(util.config_path()),
        "core_python_modules": core,
        "configured_core_python": core_python,
        "engines": engine_data,
        "remote": remotes,
        "local_available": local_available,
        "remote_available": remote_available,
        "remote_usable": remote_usable,
        "healthy": local_available or remote_usable,
        "next_actions": actions,
        "note": "Installed availability does not prove OCR accuracy; run a real sample and inspect page images.",
    }


def render(report: dict) -> str:
    mark = lambda ok: "OK" if ok else "--"
    lines = [
        "docvision doctor",
        f"  platform: {report['platform']['os']} {report['platform']['release']} / Python {report['platform']['python']}",
        f"  RAM: {report.get('ram_gb') or 'unknown'} GB",
    ]
    gpu = report.get("gpu") or {}
    if gpu.get("available"):
        for g in gpu.get("gpus", []):
            lines.append(f"  GPU: {g['name']} ({g['vram']}, driver {g['driver']})")
    else:
        lines.append(f"  GPU: {gpu.get('detail', 'not detected')}")
    lines.append("  core modules:")
    for name, item in report["core_python_modules"].items():
        lines.append(f"    [{mark(item['ok'])}] {name}: {item['detail']}")
    lines.append("  local engines:")
    for name, item in report["engines"].items():
        lines.append(f"    [{mark(item['available'])}] {name}: {item.get('version') or item.get('detail')}")
        if item.get("exe"):
            lines.append(f"         {item['exe']}")
        models = item.get("models") or {}
        if models:
            label = "cache present; pipeline/inference not validated" if models.get("standard_present") else models.get("detail")
            lines.append(f"         models: {label}")
    lines.append("  remote keys (values never printed):")
    for name, item in report["remote"].items():
        probe = item.get("probe") or {}
        detail = "set" if item["configured"] else "not set"
        if probe.get("detail"):
            detail += f"; probe: {probe.get('detail')}"
        lines.append(f"    [{mark(item['configured'])}] {name}: {detail}")
    lines.append(f"  health: {'OK' if report['healthy'] else 'NOT READY'}")
    if report.get("next_actions"):
        lines.append("  next actions:")
        for action in report["next_actions"]:
            lines.append(f"    - {action}")
    lines.append(f"  note: {report['note']}")
    return "\n".join(lines)
