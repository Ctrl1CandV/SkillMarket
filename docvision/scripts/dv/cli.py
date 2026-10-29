"""Command-line interface for docvision."""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path

from . import cache, config, credentials, detect, doctor, portability, read as read_mod, refine, setup_cmd, util, verify as verify_mod
from .base import DocVisionError, Options
from .output import write_document
from .providers import PROVIDERS, run as run_provider

PROVIDER_CHOICES = ["auto"] + list(PROVIDERS)
REMOTE = {name for name, meta in PROVIDERS.items() if meta["layer"] == "remote"}


def _out(s: str = "") -> None:
    print(s)


def _err(s: str) -> None:
    print(s, file=sys.stderr)


def _options(args) -> Options:
    return Options(
        provider=args.provider,
        tier=args.tier,
        mode=args.mode,
        pages=args.pages,
        lang=args.lang,
        device=args.device,
        timeout=args.timeout,
        allow_remote=args.allow_remote,
        keep_raw=args.keep_raw,
        force=args.force,
        resume=args.resume,
        dry_run=args.dry_run,
        workers=args.workers,
        max_mb=args.max_mb,
        output=Path(args.output) if args.output else None,
        extra=util.parse_kv_list(getattr(args, "extra", None)),
    )


def _cache_context(provider: str, extra: dict | None = None) -> dict:
    return cache.provider_context(provider, extra=extra)


def _guard_remote(provider: str, allow_remote: bool) -> None:
    """Two independent gates: a stored install-level consent and a per-call flag."""
    if provider not in REMOTE:
        return
    if config.remote_consent() == 'local-only':
        raise DocVisionError(
            f"{provider} uploads the document to a remote service, and remote upload was declined for this installation.",
            hint="Run `docvision setup --remote` to re-enable it after confirming the document is not sensitive.",
        )
    if config.remote_consent() != 'remote':
        raise DocVisionError(
            'Remote upload consent has not been recorded for this OS user.',
            hint='After confirming remote upload is acceptable, run `docvision setup --remote`; each call still needs --allow-remote.',
        )
    if not allow_remote:
        raise DocVisionError(
            f"{provider} uploads the document to a remote service, which was not authorized.",
            hint="Re-run with --allow-remote only after confirming the document is not sensitive.",
        )


def _convert_one(source: str, opts: Options, out_root: Path, *, quiet: bool = False,
                 resume_index: cache.ResumeIndex | None = None) -> dict:
    started = time.monotonic()
    timings = {}
    result = {"input": source, "state": "failed", "provider": None, "privacy": None,
              "output_dir": None, "markdown_path": None, "pages": None,
              "elapsed": None, "error": None, "warnings": []}
    try:
        opts = replace(opts, staging=out_root / '.staging', output=out_root,
                       extra={k: v for k, v in opts.extra.items() if k != '_cloud_task_id'})
        info = detect.inspect_input(source, opts)
        timings['inspect'] = round(time.monotonic() - started, 4)
        phase = time.monotonic()
        provider = detect.choose_provider(source, opts, info)
        route = detect.describe_route(provider)
        result["provider"] = provider
        result["privacy"] = route["privacy"]
        _guard_remote(provider, opts.allow_remote)
        context = _cache_context(provider, opts.extra)
        timings['route'] = round(time.monotonic() - phase, 4)
        if opts.dry_run:
            doc, raw_meta = run_provider(provider, source, opts)
            result.update({"state": "planned", "raw": raw_meta,
                           "route": route, "info": info})
            return result
        if getattr(opts, "resume", False) and not opts.force:
            phase = time.monotonic()
            existing = None if provider == 'paddleocr-local' and not context['engine_version'] else cache.find_existing(
                out_root, info, opts, provider=provider, context=context, index=resume_index)
            timings['cache'] = round(time.monotonic() - phase, 4)
            if existing:
                result.update({"state": "skipped", "output_dir": str(existing),
                               "markdown_path": str(existing / util.read_json(existing / 'meta.json')['markdown_path'])})
                return result
        phase = time.monotonic()
        doc, raw_meta = run_provider(provider, source, opts)
        timings['provider'] = round(time.monotonic() - phase, 4)
        if doc is None:
            result.update({"state": "failed", "error": "Provider did not return a document."})
            return result
        elapsed = time.monotonic() - started
        raw_meta = dict(raw_meta or {})
        raw_meta['timings_seconds'] = dict(timings)
        raw_meta['cache_request'] = cache.request_signature(info, opts, provider=provider,
                                                          context=context)
        phase = time.monotonic()
        docdir = write_document(doc, source, opts, out_root=out_root, route=route,
                                elapsed=elapsed, info=info, raw_meta=raw_meta)
        if raw_meta.get('cloud_task_id'):
            from . import cloud_jobs
            cloud_jobs.mark_output(raw_meta['cloud_task_id'], docdir)
        timings['write_verify'] = round(time.monotonic() - phase, 4)
        result.update({
            "state": "done",
            "output_dir": str(docdir),
            "markdown_path": str(docdir / f"{docdir.name}.md"),
            "pages": len(doc.pages or []),
            "elapsed": round(elapsed, 2),
            "warnings": list(doc.warnings),
        })
        qa = util.read_json(docdir / 'qa.json', {}) or {}
        result['qa'] = qa.get('status')
        if qa.get('status') == 'fail':
            result.update({'state': 'failed', 'error': 'Output failed structural verification; inspect qa.json.'})
        elif resume_index is not None:
            resume_index.add(docdir)
    except DocVisionError as exc:
        result["error"] = str(exc)
        if exc.hint:
            result["hint"] = exc.hint
        result["elapsed"] = round(time.monotonic() - started, 2)
    except Exception as exc:  # one malformed provider response must not abort a batch
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["elapsed"] = round(time.monotonic() - started, 2)
    finally:
        if opts.extra.get('_cloud_task_id'):
            result['cloud_task_id'] = opts.extra['_cloud_task_id']
        result['elapsed'] = round(time.monotonic() - started, 3)
        result['timings_seconds'] = timings
    return result


def cmd_convert(args) -> int:
    batch_started = time.monotonic()
    opts = _options(args)
    sources = util.expand_inputs(args.inputs)
    if not sources:
        _err("No supported inputs found.")
        return 1
    out_root = Path(args.output).expanduser() if args.output else Path(config.load().get("output", {}).get("default_dir", "docvision-out"))
    util.ensure_dir(out_root)
    results: list[dict] = []
    resume_index = cache.ResumeIndex(out_root) if opts.resume and not opts.force else None
    workers = max(1, min(opts.workers, len(sources)))
    if workers == 1:
        for source in sources:
            res = _convert_one(source, opts, out_root, quiet=args.quiet, resume_index=resume_index)
            results.append(res)
            if not args.json:
                _print_result(res, quiet=args.quiet)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_convert_one, s, opts, out_root, quiet=args.quiet, resume_index=resume_index): s
                       for s in sources}
            for future in as_completed(futures):
                res = future.result()
                results.append(res)
                if not args.json:
                    _print_result(res, quiet=args.quiet)
    if args.json:
        _out(json.dumps({"total": len(results),
                         "elapsed_seconds": round(time.monotonic() - batch_started, 3),
                         "pages_processed": sum(r.get('pages') or 0 for r in results if r['state'] == 'done'),
                         "done": sum(r["state"] == "done" for r in results),
                         "planned": sum(r["state"] == "planned" for r in results),
                         "skipped": sum(r["state"] == "skipped" for r in results),
                         "failed": sum(r["state"] == "failed" for r in results),
                         "results": results}, ensure_ascii=False, indent=2))
    failed = [r for r in results if r["state"] == "failed"]
    if failed and not args.json:
        _out("\nFailed:")
        for r in failed:
            _out(f"  {r['input']}: {r['error']}")
            if r.get("hint"):
                _out(f"    hint: {r['hint']}")
    return 1 if failed else 0


def _print_result(res: dict, *, quiet: bool = False) -> None:
    if quiet and res["state"] == "done":
        return
    icon = {"done": "OK", "failed": "FAIL", "skipped": "SKIP", "planned": "PLAN"}.get(res["state"], "?")
    label = Path(res["input"]).name
    extra = f" [{res.get('provider')}/{res.get('privacy')}]" if res.get("provider") else ""
    timing = f" ({res.get('elapsed')}s)" if res.get("elapsed") is not None else ""
    _out(f"[{icon}] {label}{extra}{timing}")
    if res.get("output_dir"):
        _out(f"      {res['output_dir']}")
    if res.get("pages"):
        _out(f"      pages={res['pages']}")
    if res.get("error"):
        _out(f"      {res['error']}")
    if res.get("hint"):
        _out(f"      hint: {res['hint']}")
    if res.get('cloud_task_id'):
        _out(f"      cloud task: {res['cloud_task_id']} (jobs resume continues without a new submission)")
    for warning in res.get("warnings") or []:
        _out(f"      warning: {warning}")
    if res.get("state") == "planned" and res.get("raw"):
        _out("      " + json.dumps(res["raw"], ensure_ascii=False)[:1200])


def cmd_read(args) -> int:
    docdir = read_mod.resolve_docdir(args.path)
    text = read_mod.read(
        docdir, page=args.page, block_id=args.block,
        fmt=args.format, context=args.context, max_chars=args.max_chars,
        as_json=args.json, original=args.original,
    )
    records = refine.list_results(docdir, page=args.page, block_id=args.block)
    if records and args.format != 'image':
        summaries = [{k: r.get(k) for k in ('id', 'state', 'provider', 'task', 'source',
                     'accuracy_verified', 'image_path', 'context_path', 'markdown_path', 'record_path')}
                     for r in records]
        if args.json:
            data = json.loads(text)
            data['refinements'] = summaries
            text = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            text += '\n\nSeparate region reviews (compare with original image before adopting):\n'
            for r in summaries:
                text += f"  {r['state']} | {r['task']} | {r['provider']} | {r.get('markdown_path') or r.get('context_path')}\n"
    _out(text)
    return 0


def cmd_triage(args) -> int:
    result = refine.triage(read_mod.resolve_docdir(args.path))
    if args.json:
        _out(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _out(result['note'])
        for item in result['candidates']:
            _out(f"[{item['priority']}] page {item['page']} {item['block']} {item['task']}: {item['reason']}")
        for issue in result['structural_issues']:
            _out(f"[{issue['severity']}] {issue['code']}: {issue['message']}")
    return 0


def cmd_refine(args) -> int:
    result = refine.run(read_mod.resolve_docdir(args.path), page=args.page, block_id=args.block,
                        bbox=args.bbox, task=args.task, provider=args.provider,
                        allow_remote=args.allow_remote, dpi=args.dpi,
                        extra=util.parse_kv_list(args.extra), question=args.question,
                        timeout=args.timeout, dry_run=args.dry_run, force=args.force)
    if args.json:
        _out(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _out(f"{result['state']} | {result['provider']} | {result['task']} | source page {result['source']['page']}")
        for key in ('image_path', 'context_path', 'markdown_path', 'record_path', 'error'):
            if result.get(key):
                _out(f"{key}: {result[key]}")
        if result['state'] == 'review_required':
            _out('Open the image with an actual image viewing tool and follow context.md. No visual review has been completed yet.')
    return 1 if result['state'] in {'failed', 'submitted'} else 0


def cmd_pages(args) -> int:
    out_dir = Path(args.output).expanduser() if args.output else Path("docvision-pages")
    paths = read_mod.pages_command(args.input, out_dir, pages_spec=args.pages, dpi=args.dpi)
    sheet = None
    if args.sheet and paths:
        sheet = util.make_contact_sheet(paths, out_dir / "contact-sheet.png")
    if args.json:
        _out(json.dumps({"pages": [str(p) for p in paths],
                         "contact_sheet": str(sheet) if sheet else None},
                        ensure_ascii=False, indent=2))
    else:
        for path in paths:
            _out(str(path))
        if sheet:
            _out(str(sheet))
    return 0


def cmd_crop(args) -> int:
    docdir = read_mod.resolve_docdir(args.path)
    out = Path(args.output).expanduser() if args.output else None
    path = read_mod.crop(docdir, page=args.page, block_id=args.block,
                         bbox=args.bbox, out=out, dpi=args.dpi)
    if args.json:
        _out(json.dumps({"path": str(path)}, ensure_ascii=False, indent=2))
    else:
        _out(str(path))
    return 0


def cmd_verify(args) -> int:
    path = Path(args.path).expanduser()
    docdirs = [path] if (path / "meta.json").is_file() else sorted(
        [p.parent for p in path.glob("*/meta.json")] if path.is_dir() else []
    )
    if not docdirs:
        _err(f"No docvision output found at {path}")
        return 1
    reports = []
    for docdir in docdirs:
        qa = verify_mod.verify_document(docdir)
        util.write_json(docdir / "qa.json", qa)
        reports.append({"dir": str(docdir), **qa})
    if args.json:
        _out(json.dumps(reports if len(reports) > 1 else reports[0], ensure_ascii=False, indent=2))
    else:
        for qa in reports:
            _out(f"{qa['dir']}: {qa['status']} · pages={qa['pages']} · chars={qa['markdown_chars']}")
            for issue in qa["issues"]:
                _out(f"  [{issue['severity']}] {issue['code']}: {issue['message']}")
    bad = any(r["status"] == "fail" for r in reports)
    if args.strict:
        bad = bad or any(r["status"] == "warn" for r in reports)
    return 1 if bad else 0


def cmd_doctor(args) -> int:
    report = doctor.collect(probe=args.probe)
    if args.json:
        _out(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _out(doctor.render(report))
    return 0 if report["healthy"] else 1


def cmd_providers(args) -> int:
    engines = config.engine_status()
    keys = config.remote_keys()
    consent = config.remote_consent()
    rows = []
    for name, meta in PROVIDERS.items():
        if name == 'text-local':
            import importlib.util
            available = importlib.util.find_spec('pypdf') is not None
        elif name == "local-vlm":
            available = engines["vlm"].available
        elif name.endswith("-local"):
            key = "mineru" if name.startswith("mineru") else "paddleocr"
            available = engines[key].available
        else:
            # A key alone does not authorize this OS user to upload.
            available = bool(keys.get("paddle")) and consent == "remote"
        rows.append({**meta, "name": name, "ready": available})
    payload = {"consent": consent, "credentials_file": str(util.credentials_path()),
               "providers": rows}
    if args.json:
        _out(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            _out(f"[{'OK' if row['ready'] else '--'}] {row['name']:16} {row['layer']:6} {row['label']}")
        _out(f"remote consent: {consent} (credentials: {payload['credentials_file']})")
    return 0


def cmd_env(args) -> int:
    data = config.load()
    engines = config.engine_status()
    info = {
        "config": str(util.config_path()),
        "app_dir": str(util.app_dir()),
        "cache_dir": str(util.cache_dir()),
        "skill_dir": str(util.skill_dir()),
        "credentials": str(util.credentials_path()),
        "models_dir": str(config.models_root()),
        "remote_consent": config.remote_consent(),
        "engines": {name: {"available": e.available, "exe": e.exe, "python": e.python,
                           "version": e.version, "env": e.env, "detail": e.detail}
                    for name, e in engines.items()},
        "remote_keys": config.masked_keys(),
    }
    if args.json:
        _out(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        _out(f"config:      {info['config']}")
        _out(f"credentials: {info['credentials']} ({'present' if Path(info['credentials']).is_file() else 'not created'})")
        _out(f"models:      {info['models_dir']}")
        _out(f"consent:     {info['remote_consent']}")
        for name, item in info["engines"].items():
            _out(f"{name}: {'ready' if item['available'] else 'not installed'}"
                 + (f" - {item['exe']}" if item.get("exe") else ""))
        for name, value in info["remote_keys"].items():
            _out(f"{name} key: {value}")
    return 0


def cmd_usage(args) -> int:
    data = {
        "paddleocr-cloud": {"free": "Official website API advertises 20,000 pages/day (checked 2026-10-28); account quota and service rules apply",
                            "token_env": "PADDLEOCR_ACCESS_TOKEN", "limits": "local upload 50 MB; up to 1000 pages; no automatic resubmission",
                            "source": "https://www.paddleocr.ai/main/index.html"},
        "local": {"mineru": "MinerU 4 standard: ~2 GB models, 8 GB+ VRAM recommended for standard/advanced",
                  "paddle": "PaddleOCR-VL-1.6: 0.9B, tested on RTX 4070 Ti SUPER; CPU is much slower"},
    }
    if args.json:
        _out(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for name, item in data.items():
            _out(name)
            for k, v in item.items():
                _out(f"  {k}: {v}")
    return 0


def cmd_credentials(args) -> int:
    path = util.credentials_path()
    if args.action == "path":
        _out(str(path))
        return 0
    if args.action == "show":
        found = credentials.read_credentials()
        if args.json:
            _out(json.dumps({"path": str(path), "present": path.is_file(),
                             "names": sorted(found), "consent": config.remote_consent()},
                            ensure_ascii=False, indent=2))
        else:
            _out(f"path: {path} ({'present' if path.is_file() else 'not created'})")
            for name in sorted(found):
                _out(f"  {name}: set")
            if not found:
                _out("  no credential set")
            _out(f"remote consent: {config.remote_consent()}")
        return 0
    if args.action == "remove":
        removed = credentials.remove_credentials()
        config.set_consent("local-only")
        _out(f"removed {removed} credential(s) from {path}" if removed else f"no credential present in {path}")
        _out("remote consent: local-only (uploads stay disabled until re-enabled)")
        return 0

    # set: never accept the secret as an argv value (it would land in shell history).
    if not args.stdin and not args.prompt:
        _err("Choose --prompt to enter the token privately, or pipe it on stdin with --stdin.")
        return 2
    if args.prompt:
        import getpass
        import warnings
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                value = getpass.getpass('PaddleOCR API token (hidden): ').strip()
        except (getpass.GetPassWarning, EOFError):
            raise DocVisionError('A private interactive terminal is required for --prompt.',
                                 hint='Run this command in your terminal, or use --stdin without putting the key in argv.') from None
    else:
        value = (sys.stdin.readline() or "").strip()
    if not value:
        _err("No token received on stdin.")
        return 2
    name = args.name or "PADDLEOCR_ACCESS_TOKEN"
    saved = credentials.save_credentials({name: value})
    config.set_consent("local-only" if args.local_only else "remote")
    _out(f"saved {name} to {saved}")
    _out(f"remote consent: {'local-only' if args.local_only else 'remote'}")
    _out("Uploads still require --allow-remote on each call.")
    return 0


def cmd_setup(args) -> int:
    if args.history:
        _out(json.dumps(setup_cmd.history(), ensure_ascii=False, indent=2))
        return 0
    if args.rollback:
        return setup_cmd.rollback(args.rollback, dry_run=args.dry_run, yes=args.yes)
    if args.remote or args.local_only:
        mode = "local-only" if args.local_only else "remote"
        if args.dry_run:
            _out(f"planned remote consent: {mode} (unchanged)")
            return 0
        config.set_consent(mode)
        _out(f"remote consent: {mode}")
        return 0
    return setup_cmd.run(args.profile, manager=args.manager, device=args.device,
                         models=args.models, yes=args.yes, dry_run=args.dry_run,
                         channel=args.conda_channel, index=args.index,
                         timeout=args.timeout, home=args.mineru_home,
                         models_dir=args.models_dir, sample=args.sample, sample_page=args.sample_page)


def cmd_correct(args) -> int:
    from . import corrections
    docdir = read_mod.resolve_docdir(args.path)
    if args.action == 'list':
        result = corrections.list_records(docdir, page=args.page, block_id=args.block)
    elif args.action == 'revoke':
        result = corrections.revoke(docdir, args.id, author=args.author,
                                    reviewer=args.reviewer, reason=args.reason)
    else:
        try:
            replacement = Path(args.text_file).expanduser().read_text(encoding='utf-8-sig')
        except OSError as exc:
            raise DocVisionError(f'Cannot read correction text: {exc}') from exc
        result = corrections.save(docdir, page=args.page, block_id=args.block, bbox=args.bbox,
                                  replacement=replacement, author=args.author, status=args.status,
                                  reviewer=args.reviewer, evidence=args.evidence, unresolved=args.unresolved)
    _out(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_relink(args) -> int:
    result = portability.relink(read_mod.resolve_docdir(args.path), source=args.source, dry_run=args.dry_run)
    _out(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_jobs(args) -> int:
    from . import cloud_jobs
    from .providers import paddle_cloud
    if args.action == 'list':
        result = cloud_jobs.list_jobs()
    else:
        result = paddle_cloud.resume_job(args.id, allow_remote=args.allow_remote, timeout=args.timeout,
                                         source=args.source, out_root=Path(args.output) if args.output else None,
                                         refinement_record=args.record)
    _out(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if isinstance(result, dict) and result.get('state') == 'failed' else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="docvision",
        description="Turn PDFs, scans and screenshots into AI-readable Markdown with local OCR or remote APIs.",
    )
    p.add_argument('--env-file', help='credential file path (before the subcommand); default: DOCVISION_ENV_FILE or cwd/.env')
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("convert", help="convert files/directories/URLs")
    c.add_argument("inputs", nargs="+")
    c.add_argument("-o", "--output", help="output directory (default: ./docvision-out)")
    c.add_argument("--provider", choices=PROVIDER_CHOICES, default="auto")
    c.add_argument("--tier", choices=["fast", "economy", "standard", "quality"], default="standard")
    c.add_argument("--mode", choices=["auto", "text", "ocr", "formula", "table", "chart"], default="auto")
    c.add_argument("--pages", help="1-based page ranges, e.g. 1-5,8 or r3-r1")
    c.add_argument("--lang", default="ch", help="language hint (default: ch)")
    c.add_argument("--device", default="auto", help="auto, cpu, gpu:0, cuda:0")
    c.add_argument("--timeout", type=int, default=900)
    c.add_argument("--workers", type=int, default=1)
    c.add_argument("--max-mb", type=int, default=200)
    c.add_argument("--allow-remote", action="store_true",
                   help="explicitly allow uploading to a remote OCR service")
    c.add_argument("--keep-raw", action="store_true", help="keep provider JSON/Markdown under raw/")
    c.add_argument("--resume", action="store_true", help="reuse matching source, provider and recognition settings")
    c.add_argument("--force", action="store_true", help="reuse the same output directory")
    c.add_argument("--dry-run", action="store_true", help="print the planned provider/command")
    c.add_argument("--extra", help="provider options, e.g. model_version=pipeline")
    c.add_argument("--json", action="store_true")
    c.add_argument("--quiet", action="store_true")

    d = sub.add_parser("doctor", help="check engines, models, GPU and credentials")
    d.add_argument("--json", action="store_true")
    d.add_argument("--probe", action="store_true", help="inspect local readiness; never submits an OCR job or proves cloud authentication")

    s = sub.add_parser("setup", help="build a long-lived isolated environment")
    s.add_argument("--profile", choices=["core", "mineru", "paddle", "all"], default="mineru")
    s.add_argument("--manager", choices=["auto", "conda", "uv"], default="auto")
    s.add_argument("--device", choices=["auto", "cpu", "cuda", "gpu"], default="auto")
    s.add_argument("--models", dest="models", action="store_true", default=True)
    s.add_argument("--no-models", dest="models", action="store_false")
    s.add_argument("--yes", action="store_true")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--conda-channel", default="conda-forge")
    s.add_argument("--index", help="pip index URL (optional mirror)")
    s.add_argument("--mineru-home", help="MinerU model/config home (default: <models_dir>/mineru)")
    s.add_argument("--models-dir", help="fixed model root (default: app data dir/models)")
    s.add_argument("--remote", action="store_true",
                   help="record consent for remote PaddleOCR uploads (no install)")
    s.add_argument("--local-only", action="store_true",
                   help="record that remote uploads must stay disabled (no install)")
    s.add_argument("--timeout", type=int, default=3600)
    s.add_argument('--sample', help='local PDF/image for single-page candidate acceptance before switching OCR')
    s.add_argument('--sample-page', type=int, default=1)
    maintenance = s.add_mutually_exclusive_group()
    maintenance.add_argument('--history', action='store_true', help='list installation snapshots')
    maintenance.add_argument('--rollback', metavar='ID', help='restore an installation snapshot; retain environments')
    s.add_argument('--json', action='store_true', help='machine-readable setup history')

    crd = sub.add_parser("credentials", help="write/read the fixed credential file (values never printed)")
    crd.add_argument("action", choices=["set", "show", "remove", "path"])
    crd.add_argument("--name", default="PADDLEOCR_ACCESS_TOKEN")
    secret_source = crd.add_mutually_exclusive_group()
    secret_source.add_argument("--stdin", action="store_true", help="read the secret from stdin")
    secret_source.add_argument("--prompt", action="store_true", help="enter the secret privately in an interactive terminal")
    crd.add_argument("--local-only", action="store_true", help="store the key but keep uploads disabled")
    crd.add_argument("--json", action="store_true")

    r = sub.add_parser("read", help="read a converted document by page/block")
    r.add_argument("path")
    r.add_argument("--page", type=int)
    r.add_argument("--block", help="block id, e.g. p3-b2")
    r.add_argument("--list", action="store_true", help="list pages and headings")
    r.add_argument("--format", choices=["text", "image"], default="text")
    r.add_argument("--context", type=int, default=0, help="neighbouring pages to include")
    r.add_argument("--max-chars", type=int, default=12000)
    r.add_argument("--json", action="store_true")
    r.add_argument('--original', action='store_true', help='show original OCR without accepted correction overlays')

    correct = sub.add_parser('correct', help='save attributable manual/host corrections without overwriting OCR')
    actions = correct.add_subparsers(dest='action', required=True)
    add = actions.add_parser('add')
    add.add_argument('path')
    add.add_argument('--page', type=int, required=True)
    target = add.add_mutually_exclusive_group()
    target.add_argument('--block')
    target.add_argument('--bbox', help='normalized region; stored as a scoped note')
    add.add_argument('--text-file', required=True, help='UTF-8 replacement or uncertainty note')
    add.add_argument('--author', choices=['human', 'host'], default='human')
    add.add_argument('--status', choices=['candidate', 'accepted', 'unknown'], default='candidate')
    add.add_argument('--reviewer', default='')
    add.add_argument('--evidence', action='append', default=[], help='what was actually inspected; repeatable')
    add.add_argument('--unresolved', action='append', default=[], help='remaining uncertainties; repeatable')
    add.add_argument('--json', action='store_true')
    ls = actions.add_parser('list')
    ls.add_argument('path')
    ls.add_argument('--page', type=int)
    ls.add_argument('--block')
    ls.add_argument('--json', action='store_true')
    revoke = actions.add_parser('revoke')
    revoke.add_argument('path')
    revoke.add_argument('id')
    revoke.add_argument('--author', choices=['human', 'host'], default='human')
    revoke.add_argument('--reviewer', required=True)
    revoke.add_argument('--reason', required=True)
    revoke.add_argument('--json', action='store_true')

    relink = sub.add_parser('relink', help='rebind a moved source with the same SHA-256; normalize internal paths')
    relink.add_argument('path')
    relink.add_argument('--source', help='explicit new PDF/image path; no disk scan')
    relink.add_argument('--dry-run', action='store_true')
    relink.add_argument('--json', action='store_true')

    jobs = sub.add_parser('jobs', help='list or resume cloud jobs without submitting again')
    job_actions = jobs.add_subparsers(dest='action', required=True)
    job_list = job_actions.add_parser('list')
    job_list.add_argument('--json', action='store_true')
    resume = job_actions.add_parser('resume')
    resume.add_argument('id', help='local task id from jobs list or the refinement record')
    resume.add_argument('--allow-remote', action='store_true')
    resume.add_argument('--source', help='explicit relocated source with matching SHA-256')
    resume.add_argument('--record', help='explicit relocated refinement record.json')
    resume.add_argument('-o', '--output')
    resume.add_argument('--timeout', type=int, default=900)
    resume.add_argument('--json', action='store_true')

    tr = sub.add_parser('triage', help='list regions worth reviewing (not an accuracy score)')
    tr.add_argument('path')
    tr.add_argument('--json', action='store_true')

    rf = sub.add_parser('refine', help='review one page/region; retain the local draft and provenance')
    rf.add_argument('path')
    rf.add_argument('--page', required=True, type=int)
    rf.add_argument('--block')
    rf.add_argument('--bbox', help='normalized x0,y0,x1,y1; otherwise selected block or whole page')
    rf.add_argument('--task', choices=['auto', 'transcribe', 'formula', 'table', 'chart', 'figure'], default='auto')
    rf.add_argument('--provider', choices=['auto', 'packet'] + [name for name in PROVIDERS if name != 'text-local'], default='auto')
    rf.add_argument('--allow-remote', action='store_true')
    rf.add_argument('--dpi', type=int, default=300)
    rf.add_argument('--question', default='', help='what to inspect in the selected region')
    rf.add_argument('--extra', help='provider options, e.g. model=...')
    rf.add_argument('--timeout', type=int, default=900)
    rf.add_argument('--dry-run', action='store_true')
    rf.add_argument('--force', action='store_true', help='explicitly create a new attempt, retaining prior evidence')
    rf.add_argument('--json', action='store_true')

    pg = sub.add_parser("pages", help="render PDF pages / copy an image")
    pg.add_argument("input")
    pg.add_argument("-o", "--output")
    pg.add_argument("--pages")
    pg.add_argument("--dpi", type=int, default=150)
    pg.add_argument("--sheet", action="store_true", help="also write a contact sheet")
    pg.add_argument("--json", action="store_true")

    cr = sub.add_parser("crop", help="crop a page region or block")
    cr.add_argument("path")
    cr.add_argument("--page", type=int, required=True)
    cr.add_argument("--block")
    cr.add_argument("--bbox", help="normalised x0,y0,x1,y1")
    cr.add_argument("-o", "--output")
    cr.add_argument("--dpi", type=int, default=200)
    cr.add_argument("--json", action="store_true")

    v = sub.add_parser("verify", help="check output completeness and broken references")
    v.add_argument("path")
    v.add_argument("--json", action="store_true")
    v.add_argument("--strict", action="store_true", help="treat warnings as failure")

    pr = sub.add_parser("providers", help="list providers and readiness")
    pr.add_argument("--json", action="store_true")

    e = sub.add_parser("env", help="show config and engine paths")
    e.add_argument("--json", action="store_true")

    u = sub.add_parser("usage", help="show known limits/prices (dated references, not a billing contract)")
    u.add_argument("--json", action="store_true")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        from .credentials import load_env_file
        # Credential repair/removal and consent changes must work even if an
        # old or foreign installation credential file cannot be loaded safely.
        if (args.command not in {'credentials', 'setup', 'correct', 'relink'}
                and not (args.command == 'jobs' and args.action == 'list')):
            load_env_file(args.env_file)
        if args.command == "convert":
            return cmd_convert(args)
        if args.command == "doctor":
            return cmd_doctor(args)
        if args.command == "setup":
            return cmd_setup(args)
        if args.command == "credentials":
            return cmd_credentials(args)
        if args.command == "read":
            return cmd_read(args)
        if args.command == 'correct':
            return cmd_correct(args)
        if args.command == 'relink':
            return cmd_relink(args)
        if args.command == 'jobs':
            return cmd_jobs(args)
        if args.command == 'triage':
            return cmd_triage(args)
        if args.command == 'refine':
            return cmd_refine(args)
        if args.command == "pages":
            return cmd_pages(args)
        if args.command == "crop":
            return cmd_crop(args)
        if args.command == "verify":
            return cmd_verify(args)
        if args.command == "providers":
            return cmd_providers(args)
        if args.command == "env":
            return cmd_env(args)
        if args.command == "usage":
            return cmd_usage(args)
    except DocVisionError as exc:
        _err(str(exc))
        if exc.hint:
            _err("hint: " + exc.hint)
        return 1
    except KeyboardInterrupt:
        _err("Interrupted.")
        return 130
    parser.print_help()
    return 2
