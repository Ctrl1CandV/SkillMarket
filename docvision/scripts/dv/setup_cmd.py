"""First-run environment bootstrap.

The skill itself stays dependency-free.  Heavy OCR runtimes are installed into
explicit conda prefixes (or isolated uv venvs), never into the skill folder.
"""

from __future__ import annotations

import shutil
import json
from pathlib import Path

from . import config, doctor, util

MINERU_SPEC = "mineru>=4.0,<5"
PADDLE_SPEC = "paddleocr[doc-parser]>=3.7,<3.8"
PADDLE_GPU = "paddlepaddle-gpu==3.2.1"
PADDLE_CPU = "paddlepaddle==3.2.1"
PADDLE_INDEX = "https://www.paddlepaddle.org.cn/packages/stable/cu126/"
CORE_SPECS = ["pypdfium2>=4,<6", "pillow>=10,<13", "pypdf>=5,<7"]


def _conda() -> str | None:
    return shutil.which("conda")


def _uv() -> str | None:
    return shutil.which("uv")


def _prefix_for(name: str) -> Path | None:
    """Reuse only an explicitly configured runtime, not an arbitrary named env."""
    data = config.load()
    section = data.get("core", {}) if name == "docvision-core" else data.get("engines", {}).get(
        {"docvision-mineru": "mineru", "docvision-paddle": "paddleocr"}.get(name, ""), {})
    python = section.get("python")
    if python and Path(python).is_absolute() and Path(python).is_file():
        parent = Path(python).parent
        return parent.parent if parent.name.lower() in {"scripts", "bin"} else parent
    return None


def _install_env(name: str, packages: list[str], *, manager: str,
                 channel: str = "conda-forge", index: str | None = None,
                 dry_run: bool = False, timeout: int = 3600,
                 extra_args: list[str] | None = None) -> tuple[Path, list[list[str]]]:
    commands: list[list[str]] = []
    if manager == "conda":
        conda = _conda()
        if not conda:
            raise SystemExit("conda is not on PATH; use --manager uv or install Miniconda.")
        prefix = _prefix_for(name) or util.app_dir() / "envs" / name
        if not util.env_python(prefix).is_file():
            cmd = [conda, "create", "-y", "-p", str(prefix), "python=3.12",
                   "-c", channel, "--override-channels"]
            commands.append(cmd)
            if not dry_run:
                proc = util.run(cmd, timeout=timeout, env=util.isolated_python_env())
                if proc.returncode != 0:
                    raise SystemExit(f"conda create failed:\n{util.tail_text(proc)}")
        python = util.env_python(prefix)
        if not python.is_file():
            if dry_run:
                # The env does not exist yet; still print the commands that
                # would run after `conda create`.
                pip = [str(python), "-s", "-m", "pip", "install", "--no-user", "--upgrade", "pip"]
                install = [str(python), "-s", "-m", "pip", "install", "--no-user"] + (["-i", index] if index else []) + packages
                if extra_args:
                    install += extra_args
                return prefix, commands + [pip, install]
            raise SystemExit(f"Could not find Python in conda env {name}: {prefix}")
        pip = [str(python), "-s", "-m", "pip", "install", "--no-user", "--upgrade", "pip"]
        commands.append(pip)
        if not dry_run:
            proc = util.run(pip, timeout=600, env=util.isolated_python_env())
            if proc.returncode != 0:
                raise SystemExit(f"pip bootstrap failed for {name}:\n{util.tail_text(proc, 4000)}")
        install = [str(python), "-s", "-m", "pip", "install", "--no-user"] + (["-i", index] if index else []) + packages
        if extra_args:
            install += extra_args
        commands.append(install)
        if not dry_run:
            proc = util.run(install, timeout=timeout, env=util.isolated_python_env())
            if proc.returncode != 0:
                raise SystemExit(f"pip install failed for {name}:\n{util.tail_text(proc, 4000)}")
        return prefix, commands

    uv = _uv()
    if not uv:
        raise SystemExit("uv is not on PATH; use --manager conda or install uv.")
    prefix = _prefix_for(name) or util.app_dir() / "envs" / name
    if not (util.env_python(prefix)).is_file():
        cmd = [uv, "venv", "--python", "3.12", str(prefix)]
        commands.append(cmd)
        if not dry_run:
            proc = util.run(cmd, timeout=timeout, env=util.isolated_python_env())
            if proc.returncode != 0:
                raise SystemExit(f"uv venv failed:\n{util.tail_text(proc)}")
    python = util.env_python(prefix)
    install = [uv, "pip", "install", "--python", str(python)]
    if index:
        install += ["--index-url", index]
    if extra_args:
        has_extra_index = any(arg == "--extra-index-url" or arg.startswith("--extra-index-url=")
                              for arg in extra_args)
        has_strategy = any(arg == "--index-strategy" or arg.startswith("--index-strategy=")
                           for arg in extra_args)
        if has_extra_index and not has_strategy:
            # Match pip's candidate selection across the configured indexes.
            install += ["--index-strategy", "unsafe-best-match"]
    install += packages
    if extra_args:
        install += extra_args
    commands.append(install)
    if not dry_run:
        proc = util.run(install, timeout=timeout, env=util.isolated_python_env())
        if proc.returncode != 0:
            raise SystemExit(f"uv pip install failed for {name}:\n{util.tail_text(proc, 4000)}")
    return prefix, commands


def _save_engine(name: str, prefix: Path, *, extra: dict | None = None, data: dict | None = None) -> None:
    exe_name = {"mineru": "mineru-kit", "paddleocr": "paddleocr"}.get(name, name)
    exe = util.env_bin(prefix) / (exe_name + (".exe" if util.IS_WINDOWS else ""))
    save_now = data is None
    data = config.load() if data is None else data
    engine = data.setdefault("engines", {}).setdefault(name, {})
    engine.update({
        "env": prefix.name,
        "exe": str(exe) if exe.is_file() else None,
        "python": str(util.env_python(prefix)),
    })
    if extra:
        engine.update(extra)
    if save_now:
        config.save(data)


def _verify_mineru(prefix: Path, *, models: bool, timeout: int, dry_run: bool, home: str | None = None) -> list[str]:
    exe = util.env_bin(prefix) / ("mineru-kit.exe" if util.IS_WINDOWS else "mineru-kit")
    mineru = util.env_bin(prefix) / ("mineru.exe" if util.IS_WINDOWS else "mineru")
    home = home or str(config.model_home("mineru"))
    notes = []
    if dry_run:
        notes.append(f"MinerU model home: {home}")
        notes.append(f"verify: {exe} --help")
        notes.append(f"verify: {mineru} --version")
        if models:
            notes.append(f"download: {exe} models download --tier standard")
        return notes
    if not exe.is_file():
        raise SystemExit(f"mineru-kit was not created at {exe}")
    proc = util.run([str(exe), "--help"], timeout=60, env={"MINERU_HOME": home})
    if proc.returncode != 0:
        raise SystemExit("MinerU executable check failed: " + util.tail_text(proc, 1200))
    proc = util.run([str(mineru), "--version"], timeout=60) if mineru.is_file() else None
    if proc:
        if proc.returncode != 0:
            raise SystemExit("MinerU version check failed: " + util.tail_text(proc, 1200))
        lines = (proc.stdout or proc.stderr).strip().splitlines()
        if lines:
            notes.append(lines[0])
    if models:
        notes.append("Downloading MinerU standard models (~2 GB, first run only)...")
        proc = util.run([str(exe), "models", "download", "--tier", "standard"], timeout=timeout,
                        env={"MINERU_HOME": home})
        if proc.returncode != 0:
            raise SystemExit("Model download failed: " + util.tail_text(proc, 1200))
        proc = util.run([str(exe), "models", "verify", "--tier", "standard"], timeout=timeout,
                        env={"MINERU_HOME": home})
        if proc.returncode != 0:
            raise SystemExit("Model verification failed: " + util.tail_text(proc, 1200))
        notes.append("MinerU standard models downloaded and verified.")
    return notes


def _verify_paddle(prefix: Path, *, timeout: int, dry_run: bool, home: str | None = None) -> list[str]:
    python = util.env_python(prefix)
    if dry_run:
        return [f"verify: {python} -s -c <Paddle imports and OCR extra dependency checks>",
                "Pipeline/model readiness requires a real single-page conversion."]
    env = dict(util.isolated_python_env())
    env["PADDLE_PDX_CACHE_HOME"] = home or str(config.model_home("paddlex"))
    proc = util.run([str(python), "-s", "-c", config.PADDLE_CHECK], timeout=min(timeout, 120), env=env)
    if proc.returncode != 0:
        raise SystemExit("PaddleOCR import check failed: " + util.tail_text(proc, 1200))
    lines = [x.strip() for x in (proc.stdout or "").splitlines() if x.strip()]
    try:
        payload = json.loads(lines[-1]) if lines else {}
    except (ValueError, TypeError):
        raise SystemExit("PaddleOCR dependency check returned an invalid report.") from None
    dependencies = payload.get("dependencies") if isinstance(payload, dict) else None
    if not isinstance(dependencies, dict) or dependencies.get("ok") is not True:
        raise SystemExit("PaddleOCR dependency check failed; repair the isolated environment before conversion.")
    return ["Paddle isolated dependency check: " + " / ".join(lines[-1:]),
            "Pipeline/model readiness is unverified; run a real single-page conversion."]


def run(profile: str, *, manager: str = "auto", device: str = "auto",
        models: bool = True, yes: bool = False, dry_run: bool = False,
        channel: str = "conda-forge", index: str | None = None,
        timeout: int = 3600, home: str | None = None,
        models_dir: str | None = None) -> int:
    if profile not in {"core", "mineru", "paddle", "all"}:
        raise SystemExit(f"Unknown profile: {profile}")
    data = config.load()
    if models_dir:
        data["models_dir"] = str(Path(models_dir).expanduser().resolve())
    if home:
        home = str(Path(home).expanduser().resolve())
        if (data.get("models_dir") or util.env_value("DOCVISION_MODELS")) and home != str(config.model_home("mineru", data)):
            raise SystemExit("--mineru-home conflicts with the explicit model root; choose one location.")
    if manager == "auto":
        manager = "conda" if _conda() else ("uv" if _uv() else "none")
    if manager == "none":
        raise SystemExit("Neither conda nor uv is available. Install one first, or use the remote-only path.")
    if not yes and not dry_run:
        print("This will install packages into a dedicated environment (not into the skill folder).")
        print(f"  profile={profile} manager={manager} device={device} models={models}")
        print("Re-run with --yes to proceed. Use --dry-run to print commands only.")
        return 2
    if manager == "conda" and not _conda():
        raise SystemExit("conda was requested but is not on PATH.")
    if manager == "uv" and not _uv():
        raise SystemExit("uv was requested but is not on PATH.")

    profiles = ["core", "mineru"] if profile == "all" else [profile]
    all_commands: list[list[str]] = []
    storage = doctor.storage_status(config.models_root(data))
    hardware = doctor.hardware_plan(util.platform_summary(), util.total_ram_gb(), util.gpu_summary(), storage)
    print("\n".join(hardware["notes"]))
    for name, item in storage.items():
        print(f"{name} storage: {item['path']} ({item.get('free_gb')} GB free)")
    notes: list[str] = []

    if "core" in profiles:
        prefix, commands = _install_env("docvision-core", CORE_SPECS, manager=manager,
                                        channel=channel, index=index, dry_run=dry_run,
                                        timeout=timeout)
        all_commands.extend(commands)
        if not dry_run:
            data["core"] = {"env": prefix.name, "python": str(util.env_python(prefix))}
        notes.append(f"core env: {prefix}")

    if "mineru" in profiles:
        prefix, commands = _install_env("docvision-mineru", [MINERU_SPEC], manager=manager,
                                        channel=channel, index=index, dry_run=dry_run,
                                        timeout=timeout)
        all_commands.extend(commands)
        mineru_home = home or str(config.model_home("mineru", data))
        notes.extend(_verify_mineru(prefix, models=models, timeout=timeout, dry_run=dry_run, home=mineru_home))
        if not dry_run:
            extra = {"tier": "standard"}
            # Only explicit per-engine overrides are persistent. Derived defaults
            # must continue following later global-root/environment changes.
            if home:
                extra["mineru_home"] = home
            _save_engine("mineru", prefix, extra=extra, data=data)
        notes.append(f"mineru env: {prefix}")

    if "paddle" in profiles:
        gpu = device in {"auto", "cuda", "gpu"} and hardware["paddle_device"] == "gpu:0"
        if device in {"cuda", "gpu"} and not gpu:
            raise SystemExit("CUDA was requested but a supported NVIDIA GPU/host was not detected; use --device cpu or verify the driver/platform first.")
        packages = [PADDLE_GPU if gpu else PADDLE_CPU, PADDLE_SPEC, "python-docx", "pypdf"]
        prefix, commands = _install_env(
            "docvision-paddle", packages, manager=manager, channel=channel,
            index=PADDLE_INDEX if gpu else index,
            extra_args=(["--extra-index-url", "https://pypi.org/simple"] if gpu else None),
            dry_run=dry_run, timeout=timeout,
        )
        all_commands.extend(commands)
        notes.extend(_verify_paddle(prefix, timeout=timeout, dry_run=dry_run,
                                    home=str(config.model_home("paddlex", data))))
        if not dry_run:
            _save_engine("paddleocr", prefix, extra={"device": "gpu:0" if gpu else "cpu"}, data=data)
        notes.append(f"paddle env: {prefix} ({'GPU' if gpu else 'CPU'})")
        if gpu:
            notes.append("If Paddle reports a cuDNN mismatch, its compile/runtime versions differ; test one page before batch use.")

    if dry_run:
        print("Planned commands:")
        for cmd in all_commands:
            print("  " + " ".join(str(x) for x in cmd))
    print("\n".join(notes))
    if not dry_run:
        config.save(data)
        print(f"\nConfig: {util.config_path()}")
        print(f"Models: {config.models_root()}")
        print("Next: docvision doctor --probe")
        print("First real test: docvision convert <file> --provider auto --json")
        print("Optional remote quota: docvision credentials set --stdin (or setup --local-only to stay local)")
    return 0
