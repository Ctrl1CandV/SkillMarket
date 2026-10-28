"""First-run environment bootstrap.

The skill itself stays dependency-free.  Heavy OCR runtimes are installed into
named conda environments (or isolated uv venvs), never into the skill folder.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from . import config, util

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
    return util.conda_envs().get(name)


def _install_env(name: str, packages: list[str], *, manager: str,
                 channel: str = "conda-forge", index: str | None = None,
                 dry_run: bool = False, timeout: int = 3600,
                 extra_args: list[str] | None = None) -> tuple[Path, list[list[str]]]:
    commands: list[list[str]] = []
    if manager == "conda":
        conda = _conda()
        if not conda:
            raise SystemExit("conda is not on PATH; use --manager uv or install Miniconda.")
        prefix = _prefix_for(name)
        if prefix is None:
            cmd = [conda, "create", "-y", "-n", name, "python=3.12",
                   "-c", channel, "--override-channels"]
            commands.append(cmd)
            if not dry_run:
                proc = util.run(cmd, timeout=timeout, env=util.isolated_python_env())
                if proc.returncode != 0:
                    raise SystemExit(f"conda create failed:\n{util.tail_text(proc)}")
            prefix = _prefix_for(name) or Path.home() / ".conda" / "envs" / name
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
            util.run(pip, timeout=600, env=util.isolated_python_env())
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
    prefix = util.app_dir() / "envs" / name
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


def _save_engine(name: str, prefix: Path, *, extra: dict | None = None) -> None:
    exe_name = {"mineru": "mineru-kit", "paddleocr": "paddleocr"}.get(name, name)
    exe = util.env_bin(prefix) / (exe_name + (".exe" if util.IS_WINDOWS else ""))
    data = config.load()
    engine = data.setdefault("engines", {}).setdefault(name, {})
    engine.update({
        "env": prefix.name,
        "exe": str(exe) if exe.is_file() else None,
        "python": str(util.env_python(prefix)),
    })
    if extra:
        engine.update(extra)
    config.save(data)


def _verify_mineru(prefix: Path, *, models: bool, timeout: int, dry_run: bool, home: str | None = None) -> list[str]:
    exe = util.env_bin(prefix) / ("mineru-kit.exe" if util.IS_WINDOWS else "mineru-kit")
    mineru = util.env_bin(prefix) / ("mineru.exe" if util.IS_WINDOWS else "mineru")
    notes = []
    if dry_run:
        notes.append(f"verify: {exe} --help")
        notes.append(f"verify: {mineru} --version")
        if models:
            notes.append(f"download: {exe} models download --tier standard")
        return notes
    if not exe.is_file():
        raise SystemExit(f"mineru-kit was not created at {exe}")
    proc = util.run([str(mineru), "--version"], timeout=60) if mineru.is_file() else None
    if proc and proc.returncode == 0:
        notes.append((proc.stdout or proc.stderr).strip().splitlines()[0])
    if models:
        notes.append("Downloading MinerU standard models (~2 GB, first run only)...")
        env = {"MINERU_HOME": home} if home else None
        proc = util.run([str(exe), "models", "download", "--tier", "standard"], timeout=timeout, env=env)
        if proc.returncode != 0:
            notes.append("Model download failed: " + util.tail_text(proc, 1200))
        else:
            notes.append("MinerU standard models downloaded.")
    return notes


def _verify_paddle(prefix: Path, *, timeout: int, dry_run: bool) -> list[str]:
    python = util.env_python(prefix)
    if dry_run:
        return [f"verify: {python} -s -c <Paddle imports and OCR extra dependency checks>",
                "Pipeline/model readiness requires a real single-page conversion."]
    proc = util.run([str(python), "-s", "-c", config.PADDLE_CHECK], timeout=min(timeout, 120),
                    env=util.isolated_python_env())
    if proc.returncode != 0:
        return ["PaddleOCR import check failed: " + util.tail_text(proc, 1200)]
    lines = [x.strip() for x in (proc.stdout or "").splitlines() if x.strip()]
    return ["Paddle isolated dependency check: " + " / ".join(lines[-1:]),
            "Pipeline/model readiness is unverified; run a real single-page conversion."]


def run(profile: str, *, manager: str = "auto", device: str = "auto",
        models: bool = True, yes: bool = False, dry_run: bool = False,
        channel: str = "conda-forge", index: str | None = None,
        timeout: int = 3600, home: str | None = None) -> int:
    if profile not in {"core", "mineru", "paddle", "all"}:
        raise SystemExit(f"Unknown profile: {profile}")
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
    notes: list[str] = []

    if "core" in profiles:
        prefix, commands = _install_env("docvision-core", CORE_SPECS, manager=manager,
                                        channel=channel, index=index, dry_run=dry_run,
                                        timeout=timeout)
        all_commands.extend(commands)
        if not dry_run:
            data = config.load()
            data["core"] = {"env": prefix.name, "python": str(util.env_python(prefix))}
            config.save(data)
        notes.append(f"core env: {prefix}")

    if "mineru" in profiles:
        prefix, commands = _install_env("docvision-mineru", [MINERU_SPEC], manager=manager,
                                        channel=channel, index=index, dry_run=dry_run,
                                        timeout=timeout)
        all_commands.extend(commands)
        if not dry_run:
            _save_engine("mineru", prefix, extra={"mineru_home": home or str(Path.home() / ".mineru"),
                                                  "tier": "standard"})
        notes.extend(_verify_mineru(prefix, models=models, timeout=timeout, dry_run=dry_run, home=home))
        notes.append(f"mineru env: {prefix}")

    if "paddle" in profiles:
        gpu = device in {"auto", "cuda", "gpu"} and util.gpu_summary().get("available")
        packages = [PADDLE_GPU if gpu else PADDLE_CPU, PADDLE_SPEC, "python-docx", "pypdf"]
        prefix, commands = _install_env(
            "docvision-paddle", packages, manager=manager, channel=channel,
            index=PADDLE_INDEX if gpu else index,
            extra_args=(["--extra-index-url", "https://pypi.org/simple"] if gpu else None),
            dry_run=dry_run, timeout=timeout,
        )
        all_commands.extend(commands)
        if not dry_run:
            _save_engine("paddleocr", prefix, extra={"device": "gpu:0" if gpu else "cpu"})
        notes.extend(_verify_paddle(prefix, timeout=timeout, dry_run=dry_run))
        notes.append(f"paddle env: {prefix} ({'GPU' if gpu else 'CPU'})")
        if gpu:
            notes.append("If Paddle reports a cuDNN mismatch, its compile/runtime versions differ; test one page before batch use.")

    if dry_run:
        print("Planned commands:")
        for cmd in all_commands:
            print("  " + " ".join(str(x) for x in cmd))
    print("\n".join(notes))
    if not dry_run:
        print(f"\nConfig: {util.config_path()}")
        print("Next: docvision doctor --probe")
        print("First real test: docvision convert <file> --provider auto --json")
    return 0
