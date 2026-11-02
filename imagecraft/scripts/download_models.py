#!/usr/bin/env python3
"""Download only the pinned, public model files. No package/environment installation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager

SKILL = Path(__file__).resolve().parents[1]
MODEL_IDS = ("flux-klein-4b", "z-image-turbo", "z-image-turbo-fp8")
DEFAULT_MODEL = "flux-klein-4b"  # Paired evaluation: fastest assets/editing default; Z is opt-in for short text.
MANIFEST = SKILL / "models" / "flux-klein-4b.json"
CHUNK = 4 * 1024 * 1024


class ModelError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_path(model: str) -> Path:
    if model not in MODEL_IDS:
        raise ModelError("Unknown model; choose one of: " + ", ".join(MODEL_IDS))
    return SKILL / "models" / f"{model}.json"


def workflow_path(model: str) -> Path:
    manifest_path(model)  # Validate the ID before constructing a path.
    return SKILL / "workflows" / ("flux-klein-4b.api.json" if model == "flux-klein-4b" else "z-image-turbo.api.json")


def load_manifest(model: str = DEFAULT_MODEL) -> dict:
    data = json.loads(manifest_path(model).read_text(encoding="utf-8"))
    if data.get("schema") != "imagecraft.models/1":
        raise ModelError("Unsupported model manifest")
    for item in data["files"]:
        if not re.fullmatch(r"[a-f0-9]{40}", item["revision"]):
            raise ModelError("An immutable model revision is required")
        if not re.fullmatch(r"[a-f0-9]{64}", item["sha256"]):
            raise ModelError("A SHA-256 digest is required")
        if item["repo"] not in {"black-forest-labs/FLUX.2-klein-4b-fp8", "Comfy-Org/Flux-2-Klein-4B", "Comfy-Org/Z-Image-Turbo"}:
            raise ModelError("Model repository is not approved")
        for key in ("source", "destination"):
            p = PurePosixPath(item[key])
            if p.is_absolute() or ".." in p.parts or "\\" in item[key] or ":" in item[key]:
                raise ModelError("Invalid manifest path")
        if not isinstance(item["bytes"], int) or item["bytes"] <= 0:
            raise ModelError("Invalid file size")
    return data


def checked_root(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ModelError("Model root must be an absolute path")
    root = path.resolve()
    # A source checkout must not accumulate weights. An existing ComfyUI model
    # directory may itself be gitignored inside another repository: that is OK.
    boundary = SKILL
    for parent in SKILL.parents:
        if (parent / ".git").exists():
            boundary = parent
            break
    if root == boundary or boundary in root.parents:
        raise ModelError("Keep models outside the skill/source repository")
    return root


def destination(root: Path, item: dict) -> Path:
    target = root.joinpath(*PurePosixPath(item["destination"]).parts)
    for path in (target, target.with_name(target.name + ".imagecraft.part"),
                 target.with_name(target.name + ".imagecraft.part.json")):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ModelError("Model path escapes the approved root or is a symlink")
    return target


@contextmanager
def file_lock(path: Path):
    """OS-held lock; process exit releases it. Never reclaim a PID-based lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ModelError(f"Another process holds {path.name}") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def inventory(root: Path, verify: bool = False, model: str = DEFAULT_MODEL) -> dict:
    files = []
    manifests = {name: load_manifest(name) for name in MODEL_IDS}
    for item in manifests[model]["files"]:
        path = destination(root, item)
        actual = path.stat().st_size if path.is_file() else None
        status = "missing" if actual is None else "size_match" if actual == item["bytes"] else "conflict"
        if status == "size_match" and verify:
            status = "verified" if sha256(path) == item["sha256"] else "conflict"
        shared = [name for name, other in manifests.items() if name != model and any(
            f["destination"] == item["destination"] and f["sha256"] == item["sha256"] for f in other["files"])]
        files.append({**item, "path": str(path), "status": status, "shared_with_models": shared})
    missing = sum(x["bytes"] for x in files if x["status"] == "missing")
    existing = root
    while not existing.exists():
        existing = existing.parent
    return {"schema": "imagecraft.model-plan/1", "model": model, "model_root": str(root), "files": files,
            "missing_bytes": missing, "total_bytes": sum(x["bytes"] for x in files),
            "free_bytes": shutil.disk_usage(existing).free,
            "note": "size_match is not a hash verification; download never overwrites an existing model"}


class HTTPSRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        host = parsed.hostname or ""
        if parsed.scheme != "https" or parsed.username or parsed.password or not any(
            host == suffix or host.endswith("." + suffix)
            for suffix in ("huggingface.co", "hf.co", "xethub.hf.co")
        ):
            raise ModelError("Download redirect outside approved HTTPS model hosts")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def publish_no_clobber(source: Path, target: Path):
    # Windows rename refuses existing destinations. POSIX rename replaces them,
    # so use an atomic hard-link publication there instead.
    if os.name == "nt":
        source.rename(target)
    else:
        os.link(source, target)
        source.unlink()


def download_one(root: Path, item: dict, *, opener=None) -> dict:
    target = destination(root, item)
    if target.exists():
        if not target.is_file() or target.stat().st_size != item["bytes"] or sha256(target) != item["sha256"]:
            raise ModelError(f"Existing file differs; not overwriting: {target}")
        return {"path": str(target), "status": "verified_existing", "sha256": item["sha256"]}
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".imagecraft.part")
    receipt = target.with_name(target.name + ".imagecraft.part.json")
    identity = {k: item[k] for k in ("repo", "revision", "source", "bytes", "sha256")}
    if part.exists():
        if not receipt.is_file() or json.loads(receipt.read_text(encoding="utf-8")) != identity:
            raise ModelError("Unrecognized partial download; leave it untouched and inspect manually")
        if part.stat().st_size > item["bytes"]:
            raise ModelError("Oversized partial download; inspect manually")
    else:
        receipt.write_text(json.dumps(identity), encoding="utf-8")
    url = f"https://huggingface.co/{item['repo']}/resolve/{item['revision']}/{item['source']}?download=true"
    opener = opener or urllib.request.build_opener(HTTPSRedirects())
    for attempt in range(3):
        start = part.stat().st_size if part.exists() else 0
        if start == item["bytes"]:
            break
        headers = {"User-Agent": "imagecraft/0.2.1", "Accept-Encoding": "identity", "Cache-Control": "no-cache"}
        if start:
            headers["Range"] = f"bytes={start}-"
        try:
            with opener.open(urllib.request.Request(url, headers=headers), timeout=90) as response:
                if response.status == 206:
                    match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                    if not match or int(match[1]) != start or int(match[3]) != item["bytes"]:
                        raise ModelError("Invalid download range response")
                elif response.status == 200:
                    start = 0  # Server ignored Range: rewrite our own partial, never append.
                else:
                    raise ModelError(f"Unexpected download status {response.status}")
                done, last_report = start, time.monotonic()
                with part.open("ab" if start else "wb") as stream:
                    while chunk := response.read(CHUNK):
                        done += len(chunk)
                        if done > item["bytes"]:
                            raise ModelError("Download exceeds the pinned size")
                        stream.write(chunk)
                        if time.monotonic() - last_report >= 10:
                            print(f"{target.name}: {done / item['bytes']:.1%}", file=sys.stderr, flush=True)
                            last_report = time.monotonic()
                    stream.flush()
                    os.fsync(stream.fileno())
                if done != item["bytes"]:
                    raise OSError("Incomplete download")
                break
        except urllib.error.HTTPError as exc:
            # Do not log signed redirect URLs, tokens, or response bodies.
            if exc.code < 500 or attempt == 2:
                raise ModelError(f"Download HTTP {exc.code}; partial retained") from None
            time.sleep(2 * (attempt + 1))
        except (OSError, urllib.error.URLError):
            if attempt == 2:
                raise ModelError("Download interrupted; partial retained, rerun to resume") from None
            time.sleep(2 * (attempt + 1))
    if part.stat().st_size != item["bytes"] or sha256(part) != item["sha256"]:
        raise ModelError("SHA-256/size mismatch; partial retained, nothing installed")
    if target.exists():
        raise ModelError("Destination appeared during download; not overwriting")
    publish_no_clobber(part, target)
    receipt.unlink()
    return {"path": str(target), "status": "downloaded_verified", "sha256": item["sha256"]}


def download_parallel(root: Path, item: dict, workers: int = 8, *, opener_factory=None, segment_bytes=16 * 1024 * 1024) -> dict:
    """Bounded HTTP ranges, resumable segments and one final pinned hash check."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    target = destination(root, item)
    if target.exists():
        return download_one(root, item)
    segments = root / ".imagecraft-segments" / item["sha256"]
    if segments.is_symlink() or not segments.resolve().is_relative_to(root.resolve()):
        raise ModelError("Unsafe segment cache directory")
    segments.mkdir(parents=True, exist_ok=True)
    opener_factory = opener_factory or (lambda: urllib.request.build_opener(HTTPSRedirects()))
    url = f"https://huggingface.co/{item['repo']}/resolve/{item['revision']}/{item['source']}?download=true"
    ranges = [(start, min(start + segment_bytes, item["bytes"]) - 1) for start in range(0, item["bytes"], segment_bytes)]

    def transfer(bounds):
        start, end = bounds
        path = segments / f"{start}-{end}.bin"
        temporary = path.with_suffix(".part")
        if path.is_symlink() or temporary.is_symlink():
            raise ModelError("Segment is a symlink")
        if path.is_file() and path.stat().st_size == end - start + 1:
            return path
        for attempt in range(3):
            request = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity", "User-Agent": "imagecraft/0.2.1"})
            try:
                with opener_factory().open(request, timeout=90) as response:
                    expected = f"bytes {start}-{end}/{item['bytes']}"
                    if response.status != 206 or response.headers.get("Content-Range") != expected:
                        raise ModelError("Server did not honor the exact download range; use the single-stream transport")
                    done = 0
                    with temporary.open("wb") as stream:
                        while chunk := response.read(CHUNK):
                            done += len(chunk)
                            if done > end - start + 1:
                                raise ModelError("Oversized HTTP range")
                            stream.write(chunk)
                    if done != end - start + 1:
                        raise OSError("Incomplete HTTP range")
                temporary.replace(path)
                return path
            except urllib.error.HTTPError as exc:
                if exc.code < 500 or attempt == 2:
                    raise ModelError(f"Range download HTTP {exc.code}; segments retained") from None
            except (OSError, urllib.error.URLError):
                if attempt == 2:
                    raise ModelError("Range download interrupted; completed segments retained") from None
            time.sleep(2 * (attempt + 1))
        raise ModelError("Range download failed")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = [pool.submit(transfer, bounds) for bounds in ranges]
        done, last_report = 0, time.monotonic()
        try:
            for future in as_completed(pending):
                done += future.result().stat().st_size
                if time.monotonic() - last_report >= 10:
                    print(f"{target.name}: received ranges {done / item['bytes']:.1%} (full SHA-256 pending)", file=sys.stderr, flush=True)
                    last_report = time.monotonic()
        except BaseException:
            for future in pending:
                future.cancel()
            raise
    assembled = segments / "assembled.part"
    if assembled.is_symlink():
        raise ModelError("Assembly path is a symlink")
    digest, written = hashlib.sha256(), 0
    with assembled.open("wb") as output:
        for start, end in ranges:
            with (segments / f"{start}-{end}.bin").open("rb") as source:
                while chunk := source.read(CHUNK):
                    digest.update(chunk)
                    written += len(chunk)
                    output.write(chunk)
        output.flush()
        os.fsync(output.fileno())
    if written != item["bytes"] or digest.hexdigest() != item["sha256"]:
        raise ModelError("Assembled model failed SHA-256/size verification; segments retained")
    target.parent.mkdir(parents=True, exist_ok=True)
    # Atomic no-clobber publication on NTFS/APFS/ext4; never replace a racing file.
    os.link(assembled, target)
    assembled.unlink()
    for start, end in ranges:
        (segments / f"{start}-{end}.bin").unlink()
    return {"path": str(target), "status": "downloaded_verified", "sha256": item["sha256"], "transport": "http_ranges", "workers": workers}


def download_with_hub(root: Path, item: dict) -> dict:
    """Optional acceleration using an ALREADY installed official hub/Xet client."""
    target = destination(root, item)
    if target.exists():
        return download_one(root, item)
    try:
        from importlib import import_module
        hf_hub_download = import_module("huggingface_hub").hf_hub_download
    except ImportError:
        raise ModelError("Optional huggingface_hub is not installed; use --transport urllib or approve a separate client environment") from None
    staging = root / ".imagecraft-fetch" / item["role"]
    if not staging.resolve().is_relative_to(root.resolve()) or staging.is_symlink():
        raise ModelError("Unsafe hub staging directory")
    try:
        source = Path(hf_hub_download(repo_id=item["repo"], filename=item["source"], revision=item["revision"],
                                     local_dir=str(staging), endpoint="https://huggingface.co", token=False))
    except Exception as exc:
        raise ModelError(f"Official hub transport failed ({type(exc).__name__}); cache retained. Inspect privately or use the standard HTTP transport") from None
    if not source.resolve().is_relative_to(staging.resolve()) or source.is_symlink():
        raise ModelError("Unexpected hub download location")
    if source.stat().st_size != item["bytes"] or sha256(source) != item["sha256"]:
        raise ModelError("Hub file failed pinned size/hash verification; nothing installed")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ModelError("Destination appeared during download; not overwriting")
    publish_no_clobber(source, target)
    return {"path": str(target), "status": "downloaded_verified", "sha256": item["sha256"], "transport": "huggingface_hub"}


def main(argv=None) -> int:
    sys.dont_write_bytecode = True
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "check", "download"))
    parser.add_argument("--models-root", required=True)
    parser.add_argument("--model", choices=MODEL_IDS, default=DEFAULT_MODEL)
    parser.add_argument("--verify", action="store_true", help="Hash existing models, not just sizes")
    parser.add_argument("--yes", action="store_true", help="Approve the pinned downloads")
    parser.add_argument("--transport", choices=("urllib", "hf"), default="urllib", help="hf uses an existing huggingface_hub/Xet install; never installs one")
    parser.add_argument("--workers", type=int, choices=range(1, 17), default=1, metavar="1..16", help="Optional bounded parallel HTTP ranges; needs transient space for one extra model file")
    args = parser.parse_args(argv)
    try:
        root = checked_root(args.models_root)
        plan = inventory(root, args.verify, args.model)
        if args.action != "download" or not args.yes:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return 0 if args.action == "plan" else int(any(f["status"] in {"missing", "conflict"} for f in plan["files"]))
        if any(f["status"] == "conflict" for f in plan["files"]):
            raise ModelError("Conflicting existing models; nothing will be overwritten")
        assembly_space = max(f["bytes"] for f in plan["files"]) if args.transport == "urllib" and args.workers > 1 else 0
        if plan["free_bytes"] < plan["missing_bytes"] + assembly_space + 2 * 1024 ** 3:
            raise ModelError("Insufficient free space (includes a 2 GiB reserve)")
        root.mkdir(parents=True, exist_ok=True)
        lock = root / ".imagecraft-download.lock"
        if lock.is_symlink():
            raise ModelError("Download lock is a symlink")
        with file_lock(lock):
            if args.transport == "hf":
                transfer = download_with_hub
            elif args.workers > 1:
                transfer = lambda root, item: download_parallel(root, item, args.workers)
            else:
                transfer = download_one
            result = [transfer(root, item) for item in load_manifest(args.model)["files"]]
        print(json.dumps({"schema": "imagecraft.download/1", "files": result}, ensure_ascii=False, indent=2))
        return 0
    except KeyboardInterrupt:
        print(json.dumps({"error": "Download interrupted; partial files retained"}), file=sys.stderr)
        return 130
    except (ModelError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
