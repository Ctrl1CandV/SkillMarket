"""Temporary test fixture: fake official CLI exec + stdio JSON-RPC, no network."""
import base64
import json
import os
from pathlib import Path
import struct
import sys
import zlib

scenario = os.environ.get("IMAGECRAFT_FAKE_SCENARIO", "inline")
if "--version" in sys.argv:
    print("codex-cli 0.154.0")
    raise SystemExit(0)
if "login" in sys.argv:
    print("Logged in using an API key: sk-private-test" if scenario == "api" else "Logged in using ChatGPT")
    raise SystemExit(0)


def log(method, types=()):
    path = os.environ.get("IMAGECRAFT_FAKE_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"method": method, "input_types": list(types)}) + "\n")


def send(value):
    print(json.dumps(value), flush=True)


thread, turn = "test-thread-1", "test-turn-1"
if "exec" in sys.argv:
    sys.stdin.read()
    log("exec", ["text"] + (["localImage"] if "--image" in sys.argv else []))
    if scenario == "lost-early":
        raise SystemExit(0)
    send({"type": "thread.started", "thread_id": thread})
    if scenario == "lost":
        raise SystemExit(0)
    send({"type": "turn.started", "turn_id": turn})
    if scenario == "capacity":
        send({"type": "error", "message": "private upstream diagnostic"})
        raise SystemExit(1)
    if scenario == "approval":
        send({"type": "item.started", "item": {"type": "command_execution", "id": "unexpected"}})
    else:
        # CLI 0.154.0 omits image-generation items even when generation succeeded.
        send({"type": "item.completed", "item": {"type": "agent_message", "text": ""}})
        send({"type": "turn.completed"})
    raise SystemExit(0)


def chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff)


raw = b"".join(b"\0" + bytes(v for x in range(16) for v in (x*13, y*13, (x*y) % 256)) for y in range(16))
png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 16, 16, 8, 2, 0, 0, 0))
png += chunk(b"tEXt", b"private\0private prompt") + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
quota_reads = 0


def image_item():
    item = {"type": "imageGeneration", "id": "image-1", "status": "completed", "result": base64.b64encode(png).decode()}
    if scenario == "saved":
        path = Path.cwd()/"native.png"
        path.write_bytes(png)
        item.update(savedPath=str(path), result="")
    elif scenario == "fallback":
        path = Path(os.environ["CODEX_HOME"])/"generated_images"/thread/"native.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png)
        item["result"] = ""
    elif scenario == "unsafe-path":
        item.update(savedPath=str(Path.cwd().parent/"private.png"), result="")
    return item


for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method", "")
    if not method:
        continue
    log(method)
    if "id" not in message:
        continue
    result = {}
    if method == "initialize":
        if scenario == "non-object":
            send([])
            continue
        result = {"userAgent": "fake"}
    elif method == "account/read":
        result = {"account": {"type": "apiKey" if scenario == "api-account" else "chatgpt", "planType": "plus", "email": "private@example.invalid"}}
    elif method == "config/read":
        result = {"config": {"model_provider": "openai"}}
    elif method == "modelProvider/capabilities/read":
        result = {"imageGeneration": scenario != "no-capability"}
    elif method == "account/rateLimits/read":
        quota_reads += 1
        if scenario == "quota-after" and quota_reads > 1:
            send({"id": message["id"], "error": {"code": -32603, "message": "secret failure should not be printed"}})
            continue
        result = {"ordinaryUsageAllowed": scenario != "no-included", "rateLimitsByLimitId": {"codex": {
            "limitId": "codex", "planType": "plus", "primary": {"usedPercent": 10, "windowDurationMins": 300, "resetsAt": 9999999999},
            "secondary": {"usedPercent": 25, "windowDurationMins": 10080, "resetsAt": 9999999999}}}}
    elif method == "model/list":
        result = {"data": [{"isDefault": True, "model": "fake-controller"}]}
    elif method == "thread/read":
        items = [] if scenario == "preview" else [image_item()]
        if scenario == "two-images":
            items.append({**image_item(), "id": "image-2"})
        result = {"thread": {"id": thread, "turns": [{"id": turn, "status": "completed", "items": items}]}}
        if scenario == "capacity":
            result["thread"]["turns"] = [{"id": turn, "status": "failed", "items": [],
                "error": {"codexErrorInfo": "serverOverloaded", "message": "private upstream diagnostic"}}]
    elif method == "turn/interrupt":
        result = {}
    else:
        send({"id": message["id"], "error": {"code": -32601, "message": "unsupported fake method"}})
        continue
    send({"id": message["id"], "result": result})
