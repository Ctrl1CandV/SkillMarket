"""First-run environment bootstrap.

The skill itself stays dependency-free.  Heavy OCR runtimes are installed into
explicit conda prefixes (or isolated uv venvs), never into the skill folder.
"""

from __future__ import annotations

import shutil
import json
import copy
from pathlib import Path

from . import config, doctor, setup_history, util
from .base import DocVisionError

MINERU_SPEC = "mineru>=4.0,<4.1"
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
    """Inspect a configured runtime; installation never uses it as a target."""
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
                 extra_args: list[str] | None = None,
                 prefix: Path | None = None) -> tuple[Path, list[list[str]]]:
    # Even updates build a new candidate. Never pip-upgrade a working runtime.
    prefix = prefix or util.app_dir() / "envs" / f"{name}-{setup_history.new_id()}"
    if prefix.exists():
        raise SystemExit(f"Candidate environment already exists; nothing was installed: {prefix}")
    commands: list[list[str]] = []
    if manager == "conda":
        conda = _conda()
        if not conda:
            raise SystemExit("conda is not on PATH; use --manager uv or install Miniconda.")
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


def _sample_path(sample: str | None, sample_page: int, *, required: bool) -> Path | None:
    if sample_page < 1:
        raise SystemExit("--sample-page must be a positive physical page number.")
    if not sample:
        if required:
            raise SystemExit("OCR installation requires --sample <local PDF/image> for single-page validation before activation.")
        return None
    path = Path(sample).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() not in {'.pdf', '.png', '.jpg', '.jpeg', '.webp', '.bmp'}:
        raise SystemExit("--sample must name an existing local PDF or single-frame image.")
    if path.suffix.lower() != '.pdf' and sample_page != 1:
        raise SystemExit("Image validation accepts only --sample-page 1.")
    return path


# This exercises PDF writing, text extraction, rendering, and Pillow in the new
# core environment. A blank PDF would not validate the fast reading route.
_CORE_SMOKE = r'''
import json, sys
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
import pypdfium2
from PIL import Image
sys.path.insert(0, sys.argv[1])
from dv.base import Options
from dv.providers.text_local import convert
path = Path(sys.argv[2])
writer = PdfWriter()
page = writer.add_blank_page(width=300, height=200)
font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
    NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):
    DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
stream = DecodedStreamObject()
stream.set_data(b'BT /F1 14 Tf 20 100 Td (Docvision setup validation) Tj ET')
page[NameObject('/Contents')] = writer._add_object(stream)
writer.write(path)
doc, _ = convert(str(path), Options(tier='fast', provider='text-local'))
if len(doc.pages) != 1 or 'Docvision setup validation' not in doc.markdown:
    raise RuntimeError('Core text extraction failed')
pdf = pypdfium2.PdfDocument(str(path))
try:
    page = pdf[0]
    try:
        bitmap = page.render(scale=1)
        try:
            image = bitmap.to_pil()
            if not isinstance(image, Image.Image) or image.width <= 0:
                raise RuntimeError('Core page rendering failed')
            image.close()
        finally:
            bitmap.close()
    finally:
        page.close()
finally:
    pdf.close()
print(json.dumps({'provider': 'text-local', 'state': 'done', 'pages': 1}))
'''


def _validate_candidate(data: dict, profiles: list[str], directory: Path, *,
                        sample: Path | None, sample_page: int, timeout: int) -> list[dict]:
    """Validate using candidate settings without touching the active config."""
    candidate_path = directory / 'candidate.json'
    util.write_json(candidate_path, data)
    env = dict(util.isolated_python_env())
    # util.run merges its env argument into the process environment; an empty
    # value disables a user's transient override for this candidate only.
    env.update({'DOCVISION_CONFIG': str(candidate_path), 'DOCVISION_MODELS': '',
                'DOCVISION_CORE_ACTIVE': '1'})
    scripts = Path(__file__).resolve().parents[1]
    reports = []
    for profile in profiles:
        if profile == 'core':
            command = [data['core']['python'], '-s', '-c', _CORE_SMOKE,
                       str(scripts), str(directory / 'core-sample.pdf')]
        else:
            engine_name = 'mineru' if profile == 'mineru' else 'paddleocr'
            engine = data['engines'][engine_name]
            # Smoke-test each new engine's own interpreter, including its core
            # dependencies, so an old configured core cannot mask missing ones.
            output = Path.cwd() / 'docvision-out' / '.setup-validation' / directory.name / profile
            command = [engine['python'], '-s', str(scripts / 'docvision.py'),
                       'convert', str(sample), '--provider', engine_name + '-local',
                       '--mode', 'ocr',
                       '--output', str(output), '--timeout', str(timeout), '--json']
            if sample and sample.suffix.lower() == '.pdf':
                command += ['--pages', str(sample_page)]
            env['MINERU_HOME' if profile == 'mineru' else 'PADDLE_PDX_CACHE_HOME'] = engine['model_home']
        proc = util.run(command, timeout=timeout, env=env)
        util.atomic_write(directory / f'{profile}-validation.stdout.log', proc.stdout or '')
        util.atomic_write(directory / f'{profile}-validation.stderr.log', proc.stderr or '')
        if proc.returncode != 0:
            raise DocVisionError(f'{profile} single-page validation failed; previous runtime remains active. '
                                 f'Logs: {directory}\n{util.tail_text(proc, 1500)}')
        try:
            payload = json.loads(proc.stdout)
            results = [payload] if profile == 'core' else payload['results']
            result = results[0]
            valid = (len(results) == 1 and result['state'] == 'done' and result['pages'] == 1
                     and (profile == 'core' or result.get('qa') == 'pass'))
        except (ValueError, KeyError, IndexError, TypeError):
            valid = False
        if not valid:
            raise DocVisionError(f'{profile} validation did not produce one verified page; inspect {directory}.')
        reports.append(result)
    return reports


def history() -> list[dict]:
    return setup_history.entries()


def rollback(snapshot_id: str, *, dry_run: bool = False, yes: bool = False) -> int:
    _, record = setup_history.read(snapshot_id)
    print(f"Restore runtime settings before {snapshot_id}: {', '.join(record['fields'])}")
    print("Existing environments and models are retained.")
    if dry_run:
        return 0
    if not yes:
        print("Re-run with --yes to restore this snapshot.")
        return 2
    checkpoint = setup_history.restore(snapshot_id)
    print(f"Restored. Undo snapshot: {checkpoint}")
    return 0


def run(profile: str, *, manager: str = "auto", device: str = "auto",
        models: bool = True, yes: bool = False, dry_run: bool = False,
        channel: str = "conda-forge", index: str | None = None,
        timeout: int = 3600, home: str | None = None,
        models_dir: str | None = None, sample: str | None = None,
        sample_page: int = 1) -> int:
    if profile not in {"core", "mineru", "paddle", "all"}:
        raise SystemExit(f"Unknown profile: {profile}")
    before = config.load()
    data = copy.deepcopy(before)
    if models_dir:
        data['models_dir'] = str(Path(models_dir).expanduser().resolve())
    if home and models_dir:
        raise SystemExit("Use --mineru-home or --models-dir, not both.")
    if manager == "auto":
        manager = "conda" if _conda() else ("uv" if _uv() else "none")
    if manager == "none":
        raise SystemExit("Neither conda nor uv is available. Install one first, or use the remote-only path.")
    if not yes and not dry_run:
        print("This creates a new isolated environment and activates it only after validation.")
        print("Re-run with --yes and --sample <PDF/image> for OCR, or use --dry-run.")
        return 2
    if (manager == 'conda' and not _conda()) or (manager == 'uv' and not _uv()):
        raise SystemExit(f"{manager} was requested but is not on PATH.")
    profiles = ['core', 'mineru'] if profile == 'all' else [profile]
    sample_path = _sample_path(sample, sample_page, required=not dry_run and profile != 'core')
    identifier = setup_history.new_id()
    prefixes = {name: util.app_dir() / 'envs' / f'docvision-{name}-{identifier}' for name in profiles}
    # Pin each engine to a fresh model directory. Updating weights in place
    # would make a configuration rollback insufficient to restore the old setup.
    model_root = (Path(home).expanduser().resolve() if home else config.models_root(data, use_environment=False))
    model_homes = {name: model_root / 'installations' / identifier / ('paddlex' if name == 'paddle' else name)
                   for name in profiles if name != 'core'}
    if any(path.exists() for path in [*prefixes.values(), *model_homes.values()]):
        raise SystemExit('Candidate path already exists; retry to allocate a new isolated installation.')
    fields = [{'core': 'core', 'mineru': 'engines.mineru', 'paddle': 'engines.paddleocr'}[name] for name in profiles]
    if models_dir:
        fields.append('models_dir')
        # A global root change must not redirect another installed engine away
        # from its working weights. Pin its prior effective home in the same
        # atomic switch, and include that pin in the rollback fields.
        for other, engine_name, model_name in (('mineru', 'mineru', 'mineru'),
                                                ('paddle', 'paddleocr', 'paddlex')):
            section = before.get('engines', {}).get(engine_name, {})
            installed = any(section.get(key) for key in ('python', 'exe', 'model_home', 'mineru_home'))
            if other not in profiles and installed and not section.get('model_home'):
                data['engines'][engine_name]['model_home'] = str(config.model_home(model_name, before, use_environment=False))
                fields.append('engines.' + engine_name)
    storage = doctor.storage_status(model_root)
    hardware = doctor.hardware_plan(util.platform_summary(), util.total_ram_gb(), util.gpu_summary(), storage)
    print('\n'.join(hardware['notes']))
    for name, item in storage.items():
        print(f"{name} storage: {item['path']} ({item.get('free_gb')} GB free)")
    gpu = device in {'auto', 'cuda', 'gpu'} and hardware['paddle_device'] == 'gpu:0'
    if 'paddle' in profiles and device in {'cuda', 'gpu'} and not gpu:
        raise SystemExit('CUDA requested but no supported NVIDIA GPU/host was detected; use --device cpu or verify the driver/platform.')
    if util.env_value('DOCVISION_MODELS'):
        print('DOCVISION_MODELS is a transient override; validation disables it and setup does not persist it. '
              'Unset it after setup to use the activated model_home.')
    if profile != 'core' and not models:
        print('--no-models skips pre-download; required single-page validation may download models on first use.')
    print(f'Setup snapshot: {identifier}' + (' (planned; no files written)' if dry_run else ''))
    directory = setup_history.root() / identifier
    record = None
    if not dry_run:
        directory, record = setup_history.begin(identifier, before, fields, profile=profile,
                                                prefixes={k: str(v) for k, v in prefixes.items()})
    activated = False
    try:
        commands = []
        notes = []
        for name in profiles:
            packages = CORE_SPECS if name == 'core' else ([MINERU_SPEC] + CORE_SPECS if name == 'mineru' else
                        [PADDLE_GPU if gpu else PADDLE_CPU, PADDLE_SPEC, 'python-docx', *CORE_SPECS])
            prefix, planned = _install_env(f'docvision-{name}', packages, manager=manager, channel=channel,
                index=PADDLE_INDEX if name == 'paddle' and gpu else index,
                extra_args=['--extra-index-url', 'https://pypi.org/simple'] if name == 'paddle' and gpu else None,
                dry_run=dry_run, timeout=timeout, prefix=prefixes[name])
            commands.extend(planned)
            if name == 'core':
                data['core'] = {'env': prefix.name, 'python': str(util.env_python(prefix))}
            elif name == 'mineru':
                notes.extend(_verify_mineru(prefix, models=models, timeout=timeout,
                                           dry_run=dry_run, home=str(model_homes[name])))
                _save_engine('mineru', prefix, extra={'tier': 'standard', 'model_home': str(model_homes[name])}, data=data)
            else:
                notes.extend(_verify_paddle(prefix, timeout=timeout, dry_run=dry_run, home=str(model_homes[name])))
                _save_engine('paddleocr', prefix, extra={'device': 'gpu:0' if gpu else 'cpu',
                                                       'model_home': str(model_homes[name])}, data=data)
            notes.append(f'{name} candidate env: {prefix}')
        if dry_run:
            print('Planned commands:')
            for command in commands:
                print('  ' + ' '.join(str(x) for x in command))
            print('Activation requires successful single-page validation; OCR execution needs --sample <local PDF/image>.')
            for name, path in model_homes.items():
                print(f'{name} isolated model home: {path}')
        else:
            reports = _validate_candidate(data, profiles, directory, sample=sample_path,
                                          sample_page=sample_page, timeout=timeout)
            setup_history.update(directory, record, state='validated', validation=reports,
                                 candidate=data, versions_after=setup_history.versions(data))
            setup_history.activate(before, data, fields)
            activated = True
            try:
                setup_history.update(directory, record, state='activated')
            except OSError as exc:
                print(f'Configuration activated; journal update failed: {exc}. Snapshot remains at {directory}.')
            print(f'Validated and activated. Config: {util.config_path()}')
            print(f'Rollback: docvision setup --rollback {identifier} --yes')
        print('\n'.join(notes))
    except (Exception, SystemExit, KeyboardInterrupt) as exc:
        if record is not None and not activated:
            try:
                setup_history.update(directory, record, state='failed', error=str(exc))
            except OSError:
                pass  # Preserve the original failure; the pre-install snapshot still exists.
        raise
    return 0
