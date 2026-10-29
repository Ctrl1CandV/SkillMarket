"""Environment and provider self-check.  Never prints secrets."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from . import config, util


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
        home = Path(engine.extra.get("mineru_home") or config.model_home("mineru"))
        std = [home / "models" / "MinerU2.5-Pro-2605-1.2B-GGUF",
               home / "models" / "MinerU-4_models_onnx"]
        present = [p.name for p in std if p.exists()]
        return {"dir": str(home / "models"), "standard_present": len(present) == len(std),
                "detail": ", ".join(present) if present else "standard models not downloaded"}
    if engine.name == "paddleocr":
        cache = Path(engine.extra.get("paddlex_home") or config.model_home("paddlex")) / "official_models"
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
    # PaddleOCR has no non-billable authentication probe; a real conversion is
    # the only honest check, so presence is all that can be reported here.
    return {"ok": None, "detail": "key present; authentication and inference not tested (no non-billable probe)"}


def storage_status(models: Path | None = None) -> dict:
    """Measure the filesystem that will hold each fixed storage root."""
    roots = {"environment": util.app_dir() / "envs", "models": models or config.models_root()}
    status = {}
    for name, root in roots.items():
        existing = root
        while not existing.exists() and existing.parent != existing:
            existing = existing.parent
        item = {"path": str(root), "checked_path": str(existing), "free_gb": None}
        try:
            item["free_gb"] = shutil.disk_usage(existing).free / (1024 ** 3)
        except OSError:
            item["detail"] = "Disk space could not be measured; check it before downloading."
        status[name] = item
    return status


def hardware_plan(platform: dict, ram_gb: float | None, gpu: dict, storage: dict | None = None) -> dict:
    """Conservative installation advice, not a benchmark or inference claim."""
    system = platform.get("os", "unknown")
    machine = platform.get("machine", "unknown").lower()
    cuda_host = system in {"Windows", "Linux"} and machine in {"amd64", "x86_64", "x64"}
    cuda = bool(cuda_host and gpu.get("available"))
    notes = ["Local inference is unverified on this machine; validate one page with one worker before batch use.",
             "8/16 GB are planning references, not tested memory guarantees; model, page size and runtime affect peak use."]
    caution = ram_gb is not None and ram_gb < 16
    if caution:
        notes.append("Less than 16 GB RAM detected: assess core/page rendering or economy/basic models before standard; 16 GB is only a starting recommendation.")
    elif ram_gb is None:
        notes.append("RAM could not be measured; check available memory before downloading local models.")
    if not cuda:
        notes.append("Paddle installation plan uses CPU; CPU OCR may be slow. No CUDA GPU is selected automatically.")
        notes.append("Without confirmed acceleration, start with economy/basic or text-only/core; verify any non-CUDA backend separately.")
    if system == "Darwin":
        notes.append("macOS/Apple Silicon has no CUDA route; verify engine wheels and any supported local acceleration separately.")
    elif not cuda_host:
        notes.append("This OS/architecture has no verified CUDA installation plan; check engine wheel support before installation.")
    vram = []
    for item in gpu.get("gpus", []):
        match = re.search(r"([\d.]+)\s*(MiB|GiB|MB|GB)", str(item.get("vram", "")), re.I)
        if match:
            value = float(match.group(1)) / (1024 if match.group(2).lower() in {"mib", "mb"} else 1)
            vram.append(value)
    if vram and min(vram) < 8:
        caution = True
        notes.append("A GPU has less than 8 GB VRAM: start with economy/basic models and one page; standard GPU inference is not assured.")
    for name, item in (storage or {}).items():
        free = item.get("free_gb")
        if free is not None and free < 10:
            caution = True
            notes.append(f"{name} storage has less than 10 GB free: select another fixed directory or free disk space before installation.")
        elif free is None:
            notes.append(f"{name} free disk space is unknown; reserve at least 10 GB before downloading.")
    return {"local_feasibility": "caution" if caution else "unverified",
            "paddle_device": "gpu:0" if cuda else "cpu", "workers": 1,
            "recommended_tier": "economy" if caution or not cuda else "standard",
            "gpu_vram_gb": [round(value, 2) for value in vram], "sample_pages": 1, "notes": notes}


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
    platform = util.platform_summary()
    ram_gb = util.total_ram_gb()
    storage = storage_status()
    hardware = hardware_plan(platform, ram_gb, gpu, storage)
    local_available = any(e.available for e in engines.values() if e.name != "vlm") or engines["vlm"].available
    text_local_available = bool(core.get('pypdf', {}).get('ok'))
    remote_available = any(bool(v) for v in keys.values())
    consent = config.remote_consent()
    remote_policy_allowed = consent == "remote"
    remote_usable = remote_available and remote_policy_allowed
    if probe:
        checked = [item["probe"] for item in remotes.values()
                   if item.get("configured") and (item.get("probe") or {}).get("ok") is not None]
        remote_usable = remote_policy_allowed and any(p.get("ok") for p in checked) if checked else False
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
    if text_local_available:
        actions.append('PDF text-layer reading is ready: docvision convert <paper.pdf> --tier fast --resume. This does not perform OCR or verify formulas/tables.')
    if hardware["local_feasibility"] == "caution":
        actions.append("Assess the limited-memory/disk local route before installation: docvision setup --profile mineru --no-models --dry-run; consider core or economy/basic models first.")
    if not engines["mineru"].available:
        actions.append("For full OCR when needed, inspect the local installation plan: docvision setup --profile mineru --dry-run")
    if engines["mineru"].available and not (engine_data["mineru"]["models"] or {}).get("standard_present"):
        actions.append("Inspect missing models at the reported MinerU home; prepare economy/basic on limited hardware. For standard after checking resources: docvision setup --profile mineru --sample <local PDF/image> --yes")
    if not all(item.get("ok") for item in core.values()):
        actions.append("For page rendering/cropping: docvision setup --profile core --yes")
    if not remote_available:
        actions.append("Optional region refinement: `docvision credentials set --stdin` for the PaddleOCR official API, or stay local with `docvision setup --local-only` (never commit keys).")
    elif consent == "local-only":
        actions.append("Remote uploads are disabled by your earlier choice; run `docvision setup --remote` only if that changed.")
    elif not remote_policy_allowed:
        actions.append("A remote key is present but the first-use choice is unset; ask whether to enable PaddleOCR uploads or record local-only before use.")
    elif probe and not remote_usable:
        actions.append("No configured remote route has a successful authentication probe; inspect probe details or use local OCR.")
    paddle = engines["paddleocr"]
    if paddle.extra.get("installed") and not paddle.available:
        actions.append("Build and validate a new Paddle environment: docvision setup --profile paddle --sample <local PDF/image> --yes; the previous runtime stays active on failure.")
    if not local_available and not remote_available and not text_local_available:
        actions.append("No OCR route is ready; install a local engine or configure one remote key.")
    return {
        "schema": "docvision.doctor/1",
        "platform": platform,
        "ram_gb": ram_gb,
        "gpu": gpu,
        "hardware_plan": hardware,
        "storage": storage,
        "config_path": str(util.config_path()),
        "credentials_path": str(util.credentials_path()),
        "credentials_present": util.credentials_path().is_file(),
        "models_dir": str(config.models_root()),
        "models_effective": {
            "mineru": str(engines["mineru"].extra.get("mineru_home") or config.model_home("mineru")),
            "paddlex": str(engines["paddleocr"].extra.get("paddlex_home") or config.model_home("paddlex")),
        },
        "remote_consent": consent,
        "core_python_modules": core,
        "configured_core_python": core_python,
        "engines": engine_data,
        "remote": remotes,
        "local_available": local_available,
        "text_local_available": text_local_available,
        "remote_available": remote_available,
        "remote_policy_allowed": remote_policy_allowed,
        "remote_usable": remote_usable,
        "healthy": text_local_available or local_available or remote_usable,
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
    hardware = report.get("hardware_plan") or {}
    lines.append(f"  local feasibility: {hardware.get('local_feasibility', 'unverified')}; Paddle plan: {hardware.get('paddle_device', 'cpu')}")
    lines.extend(f"    - {note}" for note in hardware.get("notes", []))
    for name, item in report.get("storage", {}).items():
        lines.append(f"  {name} storage: {item['path']} ({item.get('free_gb')} GB free)")
    lines.append("  core modules:")
    for name, item in report["core_python_modules"].items():
        lines.append(f"    [{mark(item['ok'])}] {name}: {item['detail']}")
    lines.append("  local engines:")
    lines.append(f"    [{mark(report.get('text_local_available'))}] text-local: PDF text layer only (no OCR)")
    for name, item in report["engines"].items():
        lines.append(f"    [{mark(item['available'])}] {name}: {item.get('version') or item.get('detail')}")
        if item.get("exe"):
            lines.append(f"         {item['exe']}")
        models = item.get("models") or {}
        if models:
            label = "cache present; pipeline/inference not validated" if models.get("standard_present") else models.get("detail")
            lines.append(f"         models: {label}")
    lines.append(f"  models root: {report.get('models_dir')}")
    for engine_name, path in (report.get("models_effective") or {}).items():
        lines.append(f"    {engine_name}: {path}")
    lines.append("  remote keys (values never printed):")
    for name, item in report["remote"].items():
        probe = item.get("probe") or {}
        detail = "set" if item["configured"] else "not set"
        if probe.get("detail"):
            detail += f"; probe: {probe.get('detail')}"
        lines.append(f"    [{mark(item['configured'])}] {name}: {detail}")
    lines.append(f"  remote consent: {report.get('remote_consent')}  (file: {report.get('credentials_path')})")
    lines.append(f"  health: {'OK' if report['healthy'] else 'NOT READY'}")
    if report.get("next_actions"):
        lines.append("  next actions:")
        for action in report["next_actions"]:
            lines.append(f"    - {action}")
    lines.append(f"  note: {report['note']}")
    return "\n".join(lines)
