from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import urllib.parse

import download_models
from . import __version__
from .client import Client
from .common import (Error, atomic_json, comfy_version, config, discover, emit, endpoint,
                     external_path, file_lock, gpu_info, home, safe_child)
from . import jobs
from .workflow import build, dimensions, validate


def configure(args, path: Path):
    root, python = Path(args.comfy_root).expanduser().resolve(), Path(args.python).expanduser().resolve()
    if not (root / "main.py").is_file() or not (root / "nodes.py").is_file():
        raise Error("Selected directory is not an existing ComfyUI installation; no installer is run")
    if not python.is_file() or any(p.lower() == "windowsapps" for p in python.parts):
        raise Error("Selected interpreter is missing or a WindowsApps alias; select the existing environment's Python")
    models = download_models.checked_root(args.models_root or root / "models")
    runtime = external_path(args.runtime_root or home() / "comfy-runtime")
    path = external_path(path)
    if path.exists() and not args.replace:
        raise Error("Configuration already exists; inspect it, then explicitly use --replace if intended")
    value = {"schema": "imagecraft.config/1", "machine": platform.node(), "url": endpoint(args.url),
             "comfy_root": str(root), "python": str(python), "models_root": str(models), "runtime_root": str(runtime)}
    atomic_json(path, value)
    emit({"config": str(path), "selected": value,
          "note": "Only this private config was written. No ComfyUI/core/venv/node/launcher changes."})


def doctor(cfg: dict, verify=False):
    report = {"schema": "imagecraft.doctor/1", "client_version": __version__, "gpu": gpu_info(),
              "comfyui_source_version": comfy_version(Path(cfg["comfy_root"])),
              "models": download_models.inventory(Path(cfg["models_root"]), verify=verify)}
    try:
        client = Client(cfg["url"], timeout=5)
        report["server"] = client.request("/system_stats")
        report["queue"] = {k: len(v) for k, v in client.request("/queue").items()}
        graph = build("preflight only; not submitted", 1024, 1024, 42, "imagecraft/plan", ["reference.png"])
        validate(graph, client.request("/object_info"))
        report["native_workflow_compatible"] = True
    except Error as exc:
        report["native_workflow_compatible"], report["server_error"] = False, str(exc)
    report["ready"] = (report["native_workflow_compatible"] and
                       all(f["status"] in {"size_match", "verified"} for f in report["models"]["files"]))
    report["integrity"] = "full_hashes" if verify else "sizes_only; new submissions hash all three files"
    report["note"] = "Ready means prerequisites appear available, not a promise of generation speed, quality or free GPU memory"
    return report


def serve(cfg: dict) -> int:
    """Foreground child only. The terminal/job owner controls its lifetime."""
    root, python = Path(cfg["comfy_root"]), Path(cfg["python"])
    if not (root / "main.py").is_file() or not python.is_file():
        raise Error("Configured ComfyUI/Python is missing; rediscover, do not reinstall automatically")
    url = urllib.parse.urlsplit(cfg["url"])
    try:
        with socket.create_connection((url.hostname, url.port), timeout=1):
            raise Error("Selected port is occupied; inspect/reuse the existing service, do not replace it")
    except (ConnectionRefusedError, TimeoutError, OSError):
        pass
    # Known local ports only. This is a guard, not a complete GPU process detector.
    for port in (8188, 8189):
        if port == url.port:
            continue
        try:
            other = Client(f"http://127.0.0.1:{port}", timeout=1).request("/system_stats")
        except Error:
            continue
        if "system" in other:
            raise Error(f"Another ComfyUI is live on {port}. Reuse it or ask its owner to stop it; no second GPU service started")
    runtime = external_path(cfg["runtime_root"])
    for name in ("input", "output", "temp", "user"):
        safe_child(runtime, name).mkdir(parents=True, exist_ok=True)
    paths = {"base_path": str(Path(cfg["models_root"])).replace("\\", "/"), "is_default": True,
             "diffusion_models": "diffusion_models", "text_encoders": "text_encoders", "vae": "vae"}
    mapping = safe_child(runtime, "model-paths.yaml")
    # JSON is valid YAML, avoids a client-side YAML dependency and safely quotes Windows paths.
    atomic_json(mapping, {"imagecraft": paths})
    command = [str(python), "-B", "-s", str(root / "main.py"), "--listen", url.hostname, "--port", str(url.port),
               "--disable-auto-launch", "--disable-all-custom-nodes", "--disable-api-nodes", "--disable-metadata",
               "--extra-model-paths-config", str(mapping), "--input-directory", str(runtime / "input"),
               "--output-directory", str(runtime / "output"), "--temp-directory", str(runtime / "temp"),
               "--user-directory", str(runtime / "user"), "--disable-pinned-memory", "--disable-async-offload",
               "--reserve-vram", "2.5", "--lowvram", "--cache-classic"]
    source = (root / "comfy/cli_args.py").read_text(encoding="utf-8")
    missing = [flag for flag in command if flag.startswith("--") and flag not in source]
    if missing:
        raise Error(f"Existing version lacks safety/compatibility flags {missing}; ask before changing environment")
    env = os.environ.copy()
    env.update(PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
               HF_HUB_DISABLE_TELEMETRY="1", DO_NOT_TRACK="1")
    print(json.dumps({"foreground_server": command, "note": "Stop only this owned process; never kill another ComfyUI"}), file=sys.stderr, flush=True)
    return subprocess.run(command, cwd=root, env=env, check=False).returncode


def parser():
    p = argparse.ArgumentParser(description="Local imagecraft: discover/reuse ComfyUI, plan, generate, resume and verify. No automatic installation.")
    p.add_argument("--config", type=Path, default=home() / "config.json")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("discover", help="Bounded read-only discovery; a miss is not proof of absence")
    d.add_argument("--root", action="append", default=[])
    c = sub.add_parser("configure", help="Bind an explicitly selected existing installation; write only private config")
    c.add_argument("--comfy-root", required=True)
    c.add_argument("--python", required=True)
    c.add_argument("--url", default="http://127.0.0.1:8188")
    c.add_argument("--models-root")
    c.add_argument("--runtime-root")
    c.add_argument("--replace", action="store_true")
    d = sub.add_parser("doctor")
    d.add_argument("--verify", action="store_true")
    sub.add_parser("serve", help="Run selected ComfyUI in the foreground; no daemon, install or upgrade")
    m = sub.add_parser("models")
    m.add_argument("action", choices=("plan", "check", "download"))
    m.add_argument("--verify", action="store_true")
    m.add_argument("--yes", action="store_true")
    m.add_argument("--transport", choices=("urllib", "hf"), default="urllib")
    m.add_argument("--workers", type=int, choices=range(1, 17), default=1, metavar="1..16")
    for name in ("plan", "generate"):
        g = sub.add_parser(name)
        source = g.add_mutually_exclusive_group(required=True)
        source.add_argument("--prompt")
        source.add_argument("--prompt-file", type=Path)
        g.add_argument("--width", type=int)
        g.add_argument("--height", type=int)
        g.add_argument("--seed", type=int, default=42)
        g.add_argument("--intent", choices=("general", "portrait", "anime", "ui", "diagram"), default="general")
        g.add_argument("--reference", type=Path, action="append", default=[])
        if name == "generate":
            g.add_argument("--output", required=True, help="Absolute path to a new job directory, outside source control")
            g.add_argument("--wait", type=float, default=600)
    for name in ("status", "resume", "verify", "review"):
        r = sub.add_parser(name)
        r.add_argument("--job", required=True)
        if name == "resume":
            r.add_argument("--wait", type=float, default=600)
        if name == "review":
            r.add_argument("--verdict", required=True, choices=("accepted", "needs-work"))
            r.add_argument("--notes", required=True)
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if hasattr(args, "wait") and (not math.isfinite(args.wait) or not 0 <= args.wait <= 86400):
            raise Error("Wait timeout must be finite and between 0 and 86400 seconds; nothing submitted")
        if args.command == "discover":
            emit(discover(args.root))
            return 0
        if args.command == "configure":
            configure(args, args.config)
            return 0
        if args.command in {"plan", "generate"}:
            if args.prompt_file and (not args.prompt_file.is_file() or args.prompt_file.stat().st_size > 48003):
                raise Error("Prompt file must be a regular UTF-8 file containing at most 12,000 characters")
            prompt = args.prompt if args.prompt is not None else args.prompt_file.read_text(encoding="utf-8-sig")
            references = [p.expanduser().resolve() for p in args.reference]
            width, height = dimensions(args.width, args.height, references[0] if references else None)
            graph = build(prompt, width, height, args.seed, "imagecraft/plan", [f"reference-{i}.png" for i in range(len(references))])
            request = jobs.prepare_request(prompt, width, height, args.seed, args.intent, references)
            if args.command == "plan":
                emit({"schema": "imagecraft.plan/1", "request": request, "workflow": graph,
                      "note": "No files written, images uploaded, GPU jobs queued or models downloaded. intent is a review/prompting hint, not another model."})
                return 0
        if args.command in {"verify", "review"}:
            root = external_path(args.job)
            job = jobs.load_job(root)
            jobs.verify_artifacts(root, job)
            if args.command == "review":
                with file_lock(safe_child(root, ".imagecraft.lock")):
                    job = jobs.load_job(root)
                    jobs.verify_artifacts(root, job)
                    job["visual_review"] = {"status": args.verdict, "notes": args.notes,
                                            "actor": "caller; must actually inspect the image before recording this"}
                    jobs.save_job(root, job)
            emit(jobs.summary(root, job))
            return 0
        cfg = config(args.config.expanduser().resolve())
        if args.command == "doctor":
            report = doctor(cfg, args.verify)
            emit(report)
            return 0 if report["ready"] else 2
        if args.command == "serve":
            return serve(cfg)
        if args.command == "models":
            argv = [args.action, "--models-root", cfg["models_root"], "--transport", args.transport, "--workers", str(args.workers)]
            if args.verify:
                argv.append("--verify")
            if args.yes:
                argv.append("--yes")
            return download_models.main(argv)
        root = external_path(args.output if args.command == "generate" else args.job)
        if args.command == "status":
            job = jobs.load_job(root)
            if cfg["url"] != job["endpoint"]:
                raise Error("Job endpoint differs from selected configuration")
            state, _ = jobs.observe(Client(cfg["url"]), job)
            if state == "downloaded":
                jobs.verify_artifacts(root, job)
            emit(jobs.summary(root, job, state))
            return 0 if state in {"completed", "downloaded"} else 2 if state in {"rejected", "failed"} else 3
        root.mkdir(parents=True, exist_ok=True)
        with file_lock(safe_child(root, ".imagecraft.lock")):
            job = jobs.submit(cfg, root, request) if args.command == "generate" else jobs.load_job(root)
            result, code = jobs.wait(cfg, root, job, args.wait)
        emit(result)
        return code
    except KeyboardInterrupt:
        emit({"error": "Client interrupted. An accepted GPU job can still be running; use status/resume, do not resubmit"})
        return 130
    except (Error, download_models.ModelError, OSError, ValueError, KeyError) as exc:
        emit({"schema": "imagecraft.error/1", "error": str(exc)})
        return 2
