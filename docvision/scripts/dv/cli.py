"""Command-line interface for docvision."""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import config, detect, doctor, read as read_mod, setup_cmd, util, verify as verify_mod
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


def _find_existing(out_root: Path, info: dict) -> Path | None:
    sha = info.get("sha256")
    if not sha or not out_root.is_dir():
        return None
    for meta_file in out_root.glob("*/meta.json"):
        meta = util.read_json(meta_file, {}) or {}
        if (meta.get("source") or {}).get("sha256") == sha:
            return meta_file.parent
    return None


def _convert_one(source: str, opts: Options, out_root: Path, *, quiet: bool = False) -> dict:
    started = time.monotonic()
    result = {"input": source, "state": "failed", "provider": None, "privacy": None,
              "output_dir": None, "markdown_path": None, "pages": None,
              "elapsed": None, "error": None, "warnings": []}
    try:
        info = detect.inspect_input(source, opts)
        provider = detect.choose_provider(source, opts, info)
        route = detect.describe_route(provider)
        result["provider"] = provider
        result["privacy"] = route["privacy"]
        if provider in REMOTE and not opts.allow_remote:
            raise DocVisionError(
                f"{provider} uploads the document to a remote service, which was not authorized.",
                hint="Re-run with --allow-remote only after confirming the document is not sensitive.",
            )
        if opts.pages and provider in {"mineru-agent"} and "," in opts.pages:
            raise DocVisionError("This provider cannot handle comma-separated page ranges.")
        if opts.dry_run:
            doc, raw_meta = run_provider(provider, source, opts)
            result.update({"state": "planned", "raw": raw_meta,
                           "route": route, "info": info})
            return result
        if getattr(opts, "resume", False):
            existing = _find_existing(out_root, info)
            if existing:
                result.update({"state": "skipped", "output_dir": str(existing),
                               "markdown_path": str(existing / f"{existing.name}.md")})
                return result
        doc, raw_meta = run_provider(provider, source, opts)
        if doc is None:
            result.update({"state": "failed", "error": "Provider did not return a document."})
            return result
        elapsed = time.monotonic() - started
        docdir = write_document(doc, source, opts, out_root=out_root, route=route,
                                elapsed=elapsed, info=info, raw_meta=raw_meta)
        result.update({
            "state": "done",
            "output_dir": str(docdir),
            "markdown_path": str(docdir / f"{docdir.name}.md"),
            "pages": len(doc.pages or []),
            "elapsed": round(elapsed, 2),
            "warnings": list(doc.warnings),
        })
    except DocVisionError as exc:
        result["error"] = str(exc)
        if exc.hint:
            result["hint"] = exc.hint
        result["elapsed"] = round(time.monotonic() - started, 2)
    except Exception as exc:  # one malformed provider response must not abort a batch
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["elapsed"] = round(time.monotonic() - started, 2)
    return result


def cmd_convert(args) -> int:
    opts = _options(args)
    sources = util.expand_inputs(args.inputs)
    if not sources:
        _err("No supported inputs found.")
        return 1
    out_root = Path(args.output).expanduser() if args.output else Path(config.load().get("output", {}).get("default_dir", "docvision-out"))
    util.ensure_dir(out_root)
    results: list[dict] = []
    workers = max(1, min(opts.workers, len(sources)))
    if workers == 1:
        for source in sources:
            res = _convert_one(source, opts, out_root, quiet=args.quiet)
            results.append(res)
            if not args.json:
                _print_result(res, quiet=args.quiet)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_convert_one, s, opts, out_root, quiet=args.quiet): s
                       for s in sources}
            for future in as_completed(futures):
                res = future.result()
                results.append(res)
                if not args.json:
                    _print_result(res, quiet=args.quiet)
    if args.json:
        _out(json.dumps({"total": len(results),
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
    for warning in res.get("warnings") or []:
        _out(f"      warning: {warning}")
    if res.get("state") == "planned" and res.get("raw"):
        _out("      " + json.dumps(res["raw"], ensure_ascii=False)[:1200])


def cmd_read(args) -> int:
    docdir = read_mod.resolve_docdir(args.path)
    text = read_mod.read(
        docdir, page=args.page, block_id=args.block,
        fmt=args.format, context=args.context, max_chars=args.max_chars,
        as_json=args.json,
    )
    _out(text)
    return 0


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
    rows = []
    for name, meta in PROVIDERS.items():
        if name == "local-vlm":
            available = engines["vlm"].available
        elif name.endswith("-local"):
            key = "mineru" if name.startswith("mineru") else "paddleocr"
            available = engines[key].available
        elif name == "mineru-cloud" or name == "mineru-agent":
            available = bool(keys["mineru"])
        elif name == "glm-cloud":
            available = bool(keys["glm"])
        elif name == "mistral":
            available = bool(keys["mistral"])
        elif name == "gemini":
            available = bool(keys["gemini"])
        elif name == "openai":
            available = bool(keys["openai"])
        else:
            available = False
        rows.append({**meta, "name": name, "ready": available})
    if args.json:
        _out(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            _out(f"[{'OK' if row['ready'] else '--'}] {row['name']:15} {row['layer']:6} {row['label']}")
    return 0


def cmd_env(args) -> int:
    data = config.load()
    engines = config.engine_status()
    info = {
        "config": str(util.config_path()),
        "app_dir": str(util.app_dir()),
        "cache_dir": str(util.cache_dir()),
        "engines": {name: {"available": e.available, "exe": e.exe, "python": e.python,
                           "version": e.version, "env": e.env, "detail": e.detail}
                    for name, e in engines.items()},
        "remote_keys": config.masked_keys(),
    }
    if args.json:
        _out(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        _out(f"config: {info['config']}")
        _out(f"app:    {info['app_dir']}")
        for name, item in info["engines"].items():
            _out(f"{name}: {'ready' if item['available'] else 'not installed'}"
                 + (f" · {item['exe']}" if item.get("exe") else ""))
        for name, value in info["remote_keys"].items():
            _out(f"{name} key: {value}")
    return 0


def cmd_usage(args) -> int:
    data = {
        "mineru": {"free": "1000 pages/day highest-priority quota; beyond that lower priority, not a permanent free guarantee",
                   "limits": "200 MB / 200 pages per file; batch up to 50 files (docs say up to 200)",
                   "source": "https://mineru.net/apiManage/docs"},
        "glm": {"price": "0.2 CNY per million tokens (input/output), as of 2026-10",
                "limits": "10 MB image / 50 MB PDF / 100 pages",
                "source": "https://docs.bigmodel.cn/cn/guide/models/vlm/glm-ocr"},
        "mistral": {"price": "OCR 4.1 $4 / 1,000 pages; OCR 3 $2 / 1,000 pages",
                    "limits": "per provider docs",
                    "source": "https://docs.mistral.ai/inference/pricing"},
        "paddle": {"free": "200 pages personal / 1000 pages enterprise trial; then about 0.05-0.09 CNY/page",
                   "source": "https://ai.baidu.com/ai-doc/OCR/tlrzzplc1"},
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


def cmd_setup(args) -> int:
    return setup_cmd.run(args.profile, manager=args.manager, device=args.device,
                         models=args.models, yes=args.yes, dry_run=args.dry_run,
                         channel=args.conda_channel, index=args.index,
                         timeout=args.timeout, home=args.mineru_home)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="docvision",
        description="Turn PDFs, scans and screenshots into AI-readable Markdown with local OCR or remote APIs.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("convert", help="convert files/directories/URLs")
    c.add_argument("inputs", nargs="+")
    c.add_argument("-o", "--output", help="output directory (default: ./docvision-out)")
    c.add_argument("--provider", choices=PROVIDER_CHOICES, default="auto")
    c.add_argument("--tier", choices=["fast", "standard", "quality"], default="standard")
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
    c.add_argument("--resume", action="store_true", help="skip inputs already converted (same SHA-256)")
    c.add_argument("--force", action="store_true", help="reuse the same output directory")
    c.add_argument("--dry-run", action="store_true", help="print the planned provider/command")
    c.add_argument("--extra", help="provider options, e.g. model_version=pipeline")
    c.add_argument("--json", action="store_true")
    c.add_argument("--quiet", action="store_true")

    d = sub.add_parser("doctor", help="check engines, models, GPU and credentials")
    d.add_argument("--json", action="store_true")
    d.add_argument("--probe", action="store_true", help="make free authentication checks (MinerU/Mistral/Gemini/OpenAI)")

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
    s.add_argument("--mineru-home", help="MinerU model/config home (default: ~/.mineru)")
    s.add_argument("--timeout", type=int, default=3600)

    r = sub.add_parser("read", help="read a converted document by page/block")
    r.add_argument("path")
    r.add_argument("--page", type=int)
    r.add_argument("--block", help="block id, e.g. p3-b2")
    r.add_argument("--list", action="store_true", help="list pages and headings")
    r.add_argument("--format", choices=["text", "image"], default="text")
    r.add_argument("--context", type=int, default=0, help="neighbouring pages to include")
    r.add_argument("--max-chars", type=int, default=12000)
    r.add_argument("--json", action="store_true")

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
        if args.command == "convert":
            return cmd_convert(args)
        if args.command == "doctor":
            return cmd_doctor(args)
        if args.command == "setup":
            return cmd_setup(args)
        if args.command == "read":
            return cmd_read(args)
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
