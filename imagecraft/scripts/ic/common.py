from __future__ import annotations

from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import urllib.parse

from download_models import ModelError, file_lock, sha256

SKILL = Path(__file__).resolve().parents[2]


class Error(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def home() -> Path:
    if os.environ.get("IMAGECRAFT_HOME"):
        return Path(os.environ["IMAGECRAFT_HOME"]).expanduser().resolve()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "imagecraft"
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "imagecraft"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise Error(f"Refusing a symlink: {path}")
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def endpoint(value: str) -> str:
    try:
        p = urllib.parse.urlsplit(value)
        host = p.hostname
        if host == "localhost":
            host = "127.0.0.1"
        if (p.scheme != "http" or not host or not ipaddress.ip_address(host).is_loopback
                or p.username or p.password or p.query or p.fragment or p.path not in ("", "/")):
            raise ValueError()
        port = 8188 if p.port is None else p.port
        if not 1 <= port <= 65535:
            raise ValueError()
        host = f"[{host}]" if ":" in host else host
        return f"http://{host}:{port}"
    except ValueError:
        raise Error("Only explicit loopback HTTP endpoints are allowed (e.g. http://127.0.0.1:8188)") from None


def external_path(value: str | Path) -> Path:
    raw = Path(value).expanduser()
    if not raw.is_absolute():
        raise Error("Use an absolute path for local state, models and outputs")
    path = raw.resolve()
    boundary = SKILL
    for parent in SKILL.parents:
        if (parent / ".git").exists():
            boundary = parent
            break
    if path == boundary or boundary in path.parents:
        raise Error("Keep private configuration, inputs and generated outputs outside the skill repository")
    return path


def safe_child(root: Path, relative: str) -> Path:
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise Error("Path escapes its approved directory or is a symlink")
    return path


def config(path: Path) -> dict:
    if not path.is_file():
        raise Error("Not configured. Run discover, then configure with explicitly selected existing paths")
    data = read_json(path)
    if data.get("schema") != "imagecraft.config/1":
        raise Error("Unsupported configuration schema")
    data["url"] = endpoint(data["url"])
    if data.get("machine") != platform.node():
        raise Error("Configuration belongs to another machine; discover and configure again, do not copy a venv")
    for key in ("comfy_root", "python", "models_root", "runtime_root"):
        if not Path(data[key]).is_absolute():
            raise Error(f"Configuration requires an absolute {key}")
    return data


def comfy_version(root: Path) -> str | None:
    import re
    path = root / "comfyui_version.py"
    if not path.is_file():
        return None
    match = re.search(r'__version__\s*=\s*[\'"]([^\'"]+)', path.read_text(encoding="utf-8"))
    return match[1] if match else None


def discover(roots: list[str]) -> dict:
    """Bounded, read-only discovery, never a whole-disk scan or installer."""
    candidates, interpreters = set(), set()
    seeds = [Path(p).expanduser() for p in roots]
    if not roots:
        seeds = [Path.cwd(), Path.home(), Path.home() / "Desktop", Path.home() / "Documents"]
        if os.name == "nt":
            seeds += [Path(f"{letter}:/") for letter in "CDEFG" if Path(f"{letter}:/").is_dir()]
        else:
            seeds += [Path("/opt")]
    for seed in seeds:
        if not seed.is_dir():
            continue
        options = [seed, seed / "ComfyUI"]
        try:
            options += [p for p in list(seed.iterdir())[:512] if p.is_dir() and "comfy" in p.name.lower()]
        except OSError:
            pass
        for p in list(options):
            options.append(p / "ComfyUI")
        for p in options:
            if (p / "main.py").is_file() and (p / "nodes.py").is_file():
                candidates.add(p.resolve())
    envs = Path.home() / ".conda/environments.txt"
    if envs.is_file():
        for line in envs.read_text(encoding="utf-8").splitlines():
            if "comfy" in line.lower():
                p = Path(line) / ("python.exe" if os.name == "nt" else "bin/python")
                if p.is_file():
                    interpreters.add(p.resolve())
    for root in candidates:
        for base in (root, root.parent):
            for relative in (".venv/Scripts/python.exe", "venv/Scripts/python.exe", "python_embeded/python.exe", ".venv/bin/python", "venv/bin/python"):
                if (base / relative).is_file():
                    interpreters.add((base / relative).resolve())
    return {"schema": "imagecraft.discovery/1", "comfyui": [{"root": str(p), "version": comfy_version(p)} for p in sorted(candidates)],
            "python_candidates": [str(p) for p in sorted(interpreters)],
            "searched_roots": [str(p) for p in seeds],
            "note": "Not found does not mean not installed. Supply --root or ask the owner for the installation path. No environment was executed or modified."}


def gpu_info() -> dict:
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv,noheader,nounits"],
                                capture_output=True, text=True, timeout=10, check=True)
        return {"nvidia_smi": result.stdout.strip().splitlines(), "memory_unit": "MiB", "scope": "whole GPU, not this job's allocation"}
    except (OSError, subprocess.SubprocessError):
        return {"available": False, "note": "nvidia-smi unavailable; this does not prove no GPU exists"}
