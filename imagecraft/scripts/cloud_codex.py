#!/usr/bin/env python3
"""One authorized image through official Codex subscription auth; never retries generation."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid
from urllib.parse import urlsplit

from ic.common import Error, atomic_json, external_path, file_lock, now, read_json, safe_child, sha256
from ic.codex_rpc import AppServer
from ic.png import decode, LIMIT

INSTRUCTIONS = (
    "You are an image-tool executor, not a coding agent. Use only the native image-generation tool. "
    "Generate exactly ONE image and then stop. No revisions, retries or variants. "
    "Do not use shell, code, patches, search, connectors, plugins or subagents. Do not inspect project files. "
    "Use only the supplied prompt and explicit reference images. Do not use an API key or change providers. "
    "If native image generation is unavailable, stop and report NATIVE_IMAGE_TOOL_UNAVAILABLE. "
    "Return the native artifact; never substitute an SVG/HTML/Pillow drawing."
)


def cli_command() -> list[str]:
    found = shutil.which("codex")
    if not found:
        raise Error("codex is not on PATH; install the official CLI only after user approval")
    path = Path(found)
    if os.name == "nt" and path.suffix.lower() != ".exe":
        # Avoid cmd.exe parsing or an npm wrapper process that can orphan its native child.
        package = path.parent / "node_modules/@openai/codex"
        for relative in (
            "node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe",
            "vendor/x86_64-pc-windows-msvc/bin/codex.exe",
        ):
            native = package / relative
            if native.is_file():
                return [str(native)]
        raise Error("Cannot resolve the official native Codex executable from the PATH wrapper; inspect the installation")
    return [str(path)]


def command_output(command, args):
    result = subprocess.run(command + args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    if result.returncode:
        raise Error("Official Codex CLI check failed; inspect login/network in the official client")
    return (result.stdout + result.stderr)[:16000]


def launch(command, root):
    return AppServer(command + ["-c", 'forced_login_method="chatgpt"', "-c", 'web_search="disabled"',
        "-c", "mcp_servers={}", "--disable", "shell_tool", "--disable", "unified_exec",
        "--disable", "multi_agent", "--disable", "apps", "app-server", "--stdio"], root)


def initialize(server):
    server.rpc("initialize", {"clientInfo": {"name": "imagecraft", "version": "0.2.1"},
                              "capabilities": {"experimentalApi": True}})
    server.send({"method": "initialized", "params": {}})


def preflight(server, command, root):
    status = command_output(command, ["login", "status"])
    if "chatgpt" not in status.lower() or re.search(r"api[ -]?key", status, re.I):
        raise Error("ChatGPT subscription login required; API-key mode is refused")
    account = server.rpc("account/read", {"refreshToken": False}).get("account") or {}
    if account.get("type") != "chatgpt" or (account.get("planType") or "").lower() not in {"plus", "pro", "business", "team", "edu", "enterprise"}:
        raise Error("A supported ChatGPT subscription account is required; no API-key fallback")
    cfg = server.rpc("config/read", {"includeLayers": False, "cwd": str(root)}).get("config", {})
    if (cfg.get("model_provider") or "openai") != "openai":
        raise Error("Only the official OpenAI provider is permitted")
    for value in (cfg.get("chatgpt_base_url"), (cfg.get("model_providers") or {}).get("openai", {}).get("base_url")):
        if value:
            url = urlsplit(value)
            if url.scheme != "https" or url.hostname not in {"chatgpt.com", "api.openai.com"} or url.username or url.password or url.query or url.fragment:
                raise Error("Custom upstream URLs are refused")
    if server.rpc("modelProvider/capabilities/read", {}).get("imageGeneration") is not True:
        raise Error("The current official provider has no imageGeneration capability")
    identity = {k: account.get(k) for k in ("type", "email", "chatgptAccountId")}
    return {"type": "chatgpt", "plan": account.get("planType"),
            "identity_sha256": hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()}


def quota(server, job, phase):
    try:
        data = server.rpc("account/rateLimits/read", {})
        buckets = data.get("rateLimitsByLimitId") or {"legacy": data.get("rateLimits", {})}
        snap = {"state": "observed", "at": now(), "ordinaryUsageAllowed": data.get("ordinaryUsageAllowed"),
                "pools": {key: {k: value.get(k) for k in ("limitId", "planType", "primary", "secondary", "spendControlReached")}
                          for key, value in buckets.items() if isinstance(value, dict)}}
    except Error as exc:
        snap = {"state": "unavailable", "at": now(), "error": str(exc)}
    job["quota"][phase] = snap
    return snap


def check_budget(before):
    if before["state"] != "observed" or before.get("ordinaryUsageAllowed") is not True or not before.get("pools"):
        raise Error("Included-usage headroom could not be confirmed; nothing submitted")
    windows = []
    for pool in before["pools"].values():
        if pool.get("spendControlReached"):
            raise Error("Spend control reached; nothing submitted")
        for slot in ("primary", "secondary"):
            window = pool.get(slot)
            if window:
                windows.append(window)
                used = window.get("usedPercent")
                if not isinstance(used, (int, float)) or not 0 <= used < 90:
                    raise Error("Less than conservative included-usage headroom; nothing submitted")
    if not windows:
        raise Error("No observable included-usage window; nothing submitted")


def codex_home():
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser().resolve()


def thread_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise Error("Invalid thread identifier")
    return value


def final_directory(job):
    return Path(job["codex_home"]) / "generated_images" / thread_id(job["thread_id"])


def allowed_file(path, root, job):
    raw = Path(path)
    if not raw.is_absolute() or raw.is_symlink():
        return None
    candidate = raw.resolve()
    generated = final_directory(job)
    permitted = (candidate.is_relative_to(root.resolve()) or candidate.is_relative_to(generated.resolve()))
    if not permitted or not candidate.is_file() or candidate.stat().st_size > LIMIT:
        return None
    if candidate.stat().st_mtime < job["submitted_epoch"] - 5:
        return None
    return candidate


def publish(root, job, raw, source):
    stripped, width, height = decode(raw)
    digest = hashlib.sha256(stripped).hexdigest()
    target = safe_child(root, "image.png")
    if target.exists():
        if sha256(target) != digest:
            raise Error("A different image already exists; refusing overwrite")
    else:
        with target.open("xb") as stream:
            stream.write(stripped)
            stream.flush()
            os.fsync(stream.fileno())
    job["artifact"] = {"file": "image.png", "width": width, "height": height, "bytes": len(stripped),
                       "sha256": digest, "source_sha256": hashlib.sha256(raw).hexdigest(), "source": source,
                       "format": "PNG", "decoder": "stdlib PNG8; decompressed and scanline-unfiltered"}
    job["retrieval"] = {"state": "decoded", "visual_review": "required"}


def capture(root, job, item):
    ident = item.get("id")
    if not isinstance(ident, str):
        raise Error("Image item has no identifier")
    ids = job.setdefault("image_item_ids", [])
    if ident not in ids:
        ids.append(ident)
    if len(ids) > 1:
        job["policy_violation"] = "More than one native image item observed"
        raise Error(job["policy_violation"])
    if item.get("status") not in ("completed", "succeeded"):
        job["generation"] = {"state": "failed" if item.get("status") == "failed" else "running", "item_id": ident}
        return
    job["generation"] = {"state": "completed", "item_id": ident}
    job["image_item"] = {k: item.get(k) for k in ("id", "status", "savedPath")}
    if job.get("artifact"):
        return
    source = item.get("savedPath")
    if source:
        candidate = allowed_file(source, root, job)
        if candidate:
            publish(root, job, candidate.read_bytes(), "native_saved_path")
            return
    result = item.get("result")
    if isinstance(result, str) and 100 < len(result) <= 48 * 1024 * 1024:
        encoded = result.split(",", 1)[1] if result.startswith("data:image/png;base64,") else result
        try:
            raw = base64.b64decode(encoded, validate=True)
        except ValueError:
            raw = b""
        if raw:
            publish(root, job, raw, "native_inline_base64")
            return
    generated = final_directory(job)
    files = [p for p in generated.glob("*.png") if allowed_file(p, root, job)] if generated.is_dir() else []
    if len(files) == 1:
        publish(root, job, files[0].read_bytes(), "native_generated_images_directory")
    else:
        job["retrieval"] = {"state": "unavailable", "note": "No unique verified final PNG; previews are not artifacts"}


def save(root, job):
    job["updated_at"] = now()
    if job.get("policy_violation"):
        job["state"] = "policy_violation"
    elif job.get("artifact"):
        job["state"] = "downloaded"
    elif job["generation"]["state"] == "completed" or job.get("controller_turn_status") in {"completed", "failed", "interrupted"}:
        job["state"] = "no_verified_image"
        if job["retrieval"]["state"] == "not_started":
            job["retrieval"]["state"] = "unavailable"
    elif job["submission"]["attempts"]:
        job["state"] = "unknown"  # Query the original thread, never reset to prepared.
    else:
        job["state"] = "not_submitted"
    atomic_json(safe_child(root, "job.json"), job)


def exec_once(command, root, job, seconds):
    """Submit exactly one CLI exec; JSONL omits native image items on CLI 0.154.0."""
    args = command + ["-c", 'forced_login_method="chatgpt"', "-c", 'web_search="disabled"',
        "-c", "mcp_servers={}", "--disable", "shell_tool", "--disable", "unified_exec", "--disable", "multi_agent",
        "--disable", "apps", "exec", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check",
        "--sandbox", "read-only", "--model", job["controller_model"], "--json", "-C", str(root)]
    for ref in job["references"]:
        args += ["--image", str(root / ref["file"])]
    args += ["--", "-"]  # End image options before the stdin prompt marker.
    # An attempt is persisted before process creation/stdin write. Even an early loss is never retried.
    job["submission"] = {"state": "unknown", "attempts": 1}
    job["submitted_epoch"] = time.time()
    save(root, job)
    child = AppServer(args, root)  # Bounded JSONL reader, not JSON-RPC input for this child.
    try:
        child.stdin.write("$imagegen " + INSTRUCTIONS + "\n\n" + job["prompt"])
        child.stdin.flush()
        child.stdin.close()
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            event = child.next(end - time.monotonic())
            kind = event.get("type")
            if kind == "thread.started":
                job["thread_id"] = thread_id(event.get("thread_id"))
                job["submission"]["state"] = "accepted"
            elif kind == "turn.started":
                job["generation"]["state"] = "running"
                if event.get("turn_id"):
                    job["turn_id"] = event["turn_id"]
            elif kind in {"item.started", "item.completed"}:
                if event.get("item", {}).get("type") not in {"agent_message", "reasoning", "image_generation"}:
                    job["policy_violation"] = "Unexpected non-image exec tool item refused"
                    raise Error(job["policy_violation"])
            elif kind in {"turn.completed", "turn.failed"}:
                job["controller_turn_status"] = "completed" if kind == "turn.completed" else "failed"
                job["turn_seconds"] = round(time.time() - job["submitted_epoch"], 3)
                save(root, job)
                return
            elif kind == "error":
                raise Error("Codex exec reported an error; inspect the original thread, never resubmit")
            save(root, job)
        raise Error("Image wait timed out; query the original thread with status/resume, never resubmit")
    finally:
        child.close()
        job["exec_cleanup"] = child.cleanup
        job["exec_seconds"] = round(time.time() - job["submitted_epoch"], 3)


def recover(server, root, job):
    response = server.rpc("thread/read", {"threadId": thread_id(job["thread_id"]), "includeTurns": True})
    turns = response.get("thread", {}).get("turns", [])
    if not turns:
        page = server.rpc("thread/turns/list", {"threadId": job["thread_id"], "limit": 100, "itemsView": "full"})
        turns = page.get("data", [])
    done = False
    for turn in turns:
        if job.get("turn_id") and turn.get("id") != job["turn_id"]:
            continue
        if not job.get("turn_id"):
            job["turn_id"] = turn.get("id")
        for item in turn.get("items", []):
            if item.get("type") not in {"imageGeneration", "agentMessage", "reasoning", "userMessage"}:
                job["policy_violation"] = "Unexpected non-image tool item in original thread"
                raise Error(job["policy_violation"])
            if item.get("type") == "imageGeneration":
                capture(root, job, item)
        if turn.get("status") in {"completed", "failed", "interrupted"}:
            job["controller_turn_status"] = turn["status"]
            if job["generation"]["state"] != "completed":
                job["generation"]["state"] = "failed" if turn["status"] == "failed" else "no_image"
                if (turn.get("error") or {}).get("codexErrorInfo") == "serverOverloaded":
                    job["generation"]["failure_code"] = "server_overloaded"
                    job["error"] = "Official controller at capacity; inspect this failed thread. A new submission needs new user approval"
            done = True
    # A persisted native item may have a file now even if its history omitted inline bytes.
    if job.get("image_item") and not job.get("artifact"):
        capture(root, job, job["image_item"])
    return done


def verified(root, job):
    artifact = job.get("artifact")
    if not artifact:
        return False
    path = safe_child(root, artifact["file"])
    if path.stat().st_size != artifact["bytes"] or sha256(path) != artifact["sha256"]:
        raise Error("Cloud artifact changed or disappeared")
    return True


def run(args, command=None):
    root = external_path(args.output if args.action == "generate" else args.job)
    if args.action == "generate":
        if not args.approve_cloud:
            raise Error("Explicit --approve-cloud is required for this authorized prompt/reference upload")
        if root.exists():
            raise Error("Cloud output directory already exists; use status/resume, never overwrite or resubmit")
        prompt = args.prompt_file.read_text(encoding="utf-8-sig") if args.prompt_file.stat().st_size <= 48003 else ""
        if not 1 <= len(prompt.strip()) <= 12000 or len(args.reference) > 2:
            raise Error("Use a 1–12,000 character prompt and at most two explicit PNG references")
        refs = []
        for value in args.reference:
            path = value.expanduser().resolve()
            if not path.is_file() or path.stat().st_size > LIMIT:
                raise Error("Explicit reference must be a PNG no larger than 32 MiB")
            data, _, _ = decode(path.read_bytes())
            refs.append((data, sha256(path)))
        root.mkdir(parents=True, exist_ok=False)
        job = {"schema": "imagecraft.cloud-job/1", "backend": "official-codex-subscription", "created_at": now(),
               "request_id": str(uuid.uuid4()), "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
               "references": [], "output": str(root), "codex_home": str(codex_home()), "image_item_ids": [],
               "submission": {"state": "not_submitted", "attempts": 0}, "generation": {"state": "not_started"},
               "retrieval": {"state": "not_started"}, "quota": {}}
        for i, (data, original_hash) in enumerate(refs):
            path = safe_child(root, f"reference-{i + 1}.png")
            path.write_bytes(data)
            job["references"].append({"file": path.name, "sha256": hashlib.sha256(data).hexdigest(), "source_sha256": original_hash})
        save(root, job)
    else:
        job = read_json(safe_child(root, "job.json"))
        if job.get("schema") != "imagecraft.cloud-job/1" or job.get("output") != str(root):
            raise Error("Not this cloud task directory")
        if verified(root, job):
            return job, 2 if job.get("policy_violation") else 0
        if not job.get("thread_id") or not job["submission"]["attempts"]:
            raise Error("No submitted thread to inspect; nothing will be submitted")
    command = command or cli_command()
    server = None
    with file_lock(safe_child(root, ".imagecraft.lock")):
        try:
            version = command_output(command, ["--version"]).strip()
            job["client_version"] = version if re.fullmatch(r"codex-cli [\w.\-+]+", version) else "unrecognized"
            server = launch(command, root)
            initialize(server)
            account = preflight(server, command, root)
            if args.action != "generate" and account["identity_sha256"] != job["account"]["identity_sha256"]:
                raise Error("Current subscription account differs from this task")
            job["account"] = account
            if args.action == "generate":
                check_budget(quota(server, job, "before"))
                models = server.rpc("model/list", {"includeHidden": False, "limit": 100}).get("data", [])
                model = next((m for m in models if m.get("isDefault")), None)
                if not model:
                    raise Error("No official default controller model advertised")
                job["controller_model"], job["image_model"] = model["model"], None
                exec_once(command, root, job, args.wait)
                if job.get("thread_id"):
                    recover(server, root, job)
                else:
                    raise Error("Exec finished without a thread receipt; inspect the official client, never resubmit")
            else:
                done = recover(server, root, job)
                if not done and args.action == "resume":
                    end = time.monotonic() + args.wait
                    while time.monotonic() < end and not done and not job.get("artifact"):
                        time.sleep(min(3, max(0, end - time.monotonic())))
                        done = recover(server, root, job)
            quota(server, job, "after")  # A failed quota read must not erase a valid image.
        except (Error, OSError, ValueError, KeyError) as exc:
            job["error"] = str(exc) if isinstance(exc, Error) else f"Client failure ({type(exc).__name__}); inspect saved thread"
            if server and job.get("turn_id") and job.get("policy_violation"):
                try:
                    server.rpc("turn/interrupt", {"threadId": job["thread_id"], "turnId": job["turn_id"]}, timeout=10)
                except Error:
                    pass
        finally:
            if server:
                if job["submission"]["attempts"] and "after" not in job["quota"]:
                    quota(server, job, "after")
                server.close()
                job["cleanup"] = server.cleanup
                job["diagnostic_bytes_not_logged"] = server.diagnostic_bytes
            save(root, job)
    return job, 0 if verified(root, job) and not job.get("policy_violation") else 3 if job["state"] == "unknown" else 2


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    g = sub.add_parser("generate", help="One cloud turn only, authorized prompt/reference upload")
    g.add_argument("--prompt-file", required=True, type=Path)
    g.add_argument("--reference", type=Path, action="append", default=[])
    g.add_argument("--output", required=True)
    g.add_argument("--approve-cloud", action="store_true")
    g.add_argument("--wait", type=float, default=600)
    for name in ("status", "resume"):
        s = sub.add_parser(name, help="Inspect the original thread only; never submits another turn")
        s.add_argument("--job", required=True)
        s.add_argument("--wait", type=float, default=0 if name == "status" else 600)
    return p


def main(argv=None, *, command=None):
    args = parser().parse_args(argv)
    try:
        if not math.isfinite(args.wait) or not 0 <= args.wait <= 3600:
            raise Error("--wait must be finite, between 0 and 3600 seconds")
        job, code = run(args, command)
        print(json.dumps({k: job.get(k) for k in ("state", "output", "thread_id", "submission", "generation", "retrieval", "quota", "artifact", "error", "cleanup")}, ensure_ascii=False, indent=2))
        return code
    except (Error, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc) if isinstance(exc, Error) else f"Client failure ({type(exc).__name__})"}))
        return 2


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")
    raise SystemExit(main())
