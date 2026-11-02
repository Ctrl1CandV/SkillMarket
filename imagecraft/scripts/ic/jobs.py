from __future__ import annotations

import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
import time
import uuid

from download_models import inventory
from .client import Client, HTTPFailure
from .common import Error, SKILL, atomic_json, now, read_json, safe_child, sha256
from .workflow import build, open_image, reference_png, validate


def fingerprint(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def prepare_request(prompt, width, height, seed, intent, references):
    for path in references:
        reference_png(path)  # Validate every reference before a plan or submission.
    return {"prompt": prompt, "width": width, "height": height, "seed": seed, "intent": intent,
            "references": [{"path": str(p), "sha256": sha256(p)} for p in references],
            "model_manifest_sha256": sha256(SKILL / "models/flux-klein-4b.json"),
            "workflow_template_sha256": sha256(SKILL / "workflows/flux-klein-4b.api.json")}


def load_job(root: Path) -> dict:
    job = read_json(safe_child(root, "job.json"))
    if job.get("schema") != "imagecraft.job/1":
        raise Error("Unsupported job schema")
    uuid.UUID(job["job_id"])
    if job.get("prompt_id"):
        uuid.UUID(job["prompt_id"])
    return job


def save_job(root: Path, job: dict):
    job["updated_at"] = now()
    atomic_json(safe_child(root, "job.json"), job)


def observe(client: Client, job: dict) -> tuple[str, dict | None]:
    if job["state"] in {"prepared", "input_uncertain", "rejected", "failed", "downloaded"}:
        return job["state"], None
    history = client.history(job["prompt_id"])
    if history:
        status = history.get("status", {})
        if status.get("status_str") == "error":
            return "failed", history
        if status.get("completed") and status.get("status_str") == "success":
            return "completed", history
        return "running", history
    queue = client.request("/queue")
    for key, state in (("queue_running", "running"), ("queue_pending", "queued")):
        for item in queue.get(key, []):
            if item[1] == job["prompt_id"]:
                return state, None
            # Older ComfyUI versions may ignore the client-supplied prompt_id.
            if len(item) > 3 and item[3].get("client_id") == job["client_id"]:
                job["prompt_id"] = item[1]
                return state, None
    recent = client.request("/history?max_items=100")
    for prompt_id, entry in recent.items():
        prompt = entry.get("prompt", [])
        if len(prompt) > 3 and prompt[3].get("client_id") == job["client_id"]:
            job["prompt_id"] = prompt_id
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                return "failed", entry
            if status.get("completed") and status.get("status_str") == "success":
                return "completed", entry
            return "running", entry
    return "unknown", None  # Never interpret lost history/POST timeout as safe to resubmit.


def verify_artifacts(root: Path, job: dict) -> list[dict]:
    artifacts = job.get("artifacts", [])
    if not artifacts:
        raise Error("No locally verified artifacts are recorded")
    for item in artifacts:
        path = safe_child(root, item["file"])
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise Error(f"Artifact missing or changed: {item['file']}")
        image = open_image(path)
        if list(image.size) != [item["width"], item["height"]]:
            raise Error("Artifact dimensions changed")
    return artifacts


def fetch(client: Client, root: Path, job: dict, history: dict):
    images = history.get("outputs", {}).get("13", {}).get("images", [])
    if len(images) != 1:
        raise Error("Expected one final SaveImage output; previews are not accepted")
    raw = client.view(images[0])
    image = open_image(raw)
    request = job["request"]
    if image.size != (request["width"], request["height"]):
        raise Error("Generated dimensions do not match the request")
    path = safe_child(root, "image.png")
    output = io.BytesIO()
    image.save(output, format="PNG")  # Strip embedded workflow/prompt metadata from deliverable.
    data = output.getvalue()
    digest = hashlib.sha256(data).hexdigest()
    if path.exists():
        if sha256(path) != digest:
            raise Error("Output path contains a different image; not overwriting")
    else:
        fd, name = tempfile.mkstemp(prefix=".imagecraft-image-", suffix=".tmp", dir=root)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(name, path)  # Atomic publication, never overwrite another output.
            except FileExistsError:
                if sha256(path) != digest:
                    raise Error("Output appeared during retrieval; not overwriting") from None
        finally:
            os.unlink(name)
    from importlib import import_module
    variation = max(import_module("PIL.ImageStat").Stat(image).stddev)
    job["artifacts"] = [{"file": "image.png", "sha256": digest, "bytes": len(data),
                         "width": image.width, "height": image.height,
                         "technical_warning": "near-uniform image; inspect" if variation < 1 else None}]
    job["state"], job["downloaded_at"] = "downloaded", now()
    job["visual_review"] = {"status": "required", "note": "Decoded PNG and matching dimensions do not establish visual quality or diagram correctness"}
    messages = history.get("status", {}).get("messages", [])
    timings = {kind: value.get("timestamp") for kind, value in messages if isinstance(value, dict)}
    started, finished = timings.get("execution_start"), timings.get("execution_success")
    if isinstance(started, (int, float)) and isinstance(finished, (int, float)):
        job["server_execution_seconds"] = (finished - started) / 1000
    atomic_json(safe_child(root, "history.json"), history)
    save_job(root, job)
    verify_artifacts(root, job)


def summary(root: Path, job: dict, state=None) -> dict:
    return {"schema": "imagecraft.result/1", "state": state or job["state"], "job": str(root),
            "prompt_id": job.get("prompt_id"), "seed": job["request"]["seed"],
            "artifacts": [{**a, "path": str(root / a["file"])} for a in job.get("artifacts", [])],
            "server_execution_seconds": job.get("server_execution_seconds"), "visual_review": job.get("visual_review"),
            "note": "unknown/submitting means inspect or resume; never resubmit automatically"}


def submit(cfg: dict, root: Path, request: dict) -> dict:
    job_path = safe_child(root, "job.json")
    if job_path.exists():
        job = load_job(root)
        if job["request_fingerprint"] != fingerprint(request) or job["endpoint"] != cfg["url"]:
            raise Error("This job directory belongs to a different request or endpoint; choose a new directory")
        if job["state"] != "prepared":
            return job
    else:
        unknown = [p for p in root.iterdir() if p.name != ".imagecraft.lock"]
        if unknown:
            raise Error("Use a new/empty output directory; existing files will not be overwritten")
        job_id = str(uuid.uuid4())
        job = {"schema": "imagecraft.job/1", "job_id": job_id, "prompt_id": job_id, "client_id": str(uuid.uuid4()),
               "state": "prepared", "created_at": now(), "endpoint": cfg["url"], "request": request,
               "request_fingerprint": fingerprint(request), "uploads": []}
        save_job(root, job)
    client = Client(cfg["url"])
    queue = client.request("/queue")
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise Error("ComfyUI is busy; nothing submitted. Wait for the existing H3/image job to finish")
    info = client.request("/object_info")
    graph = build(request["prompt"], request["width"], request["height"], request["seed"],
                  f"imagecraft/{job['job_id']}", [f"reference-{i}.png" for i in range(len(request["references"]))])
    validate(graph, info)
    # Full hashes at new submission; don't mistake matching filenames or sizes for integrity.
    models = inventory(Path(cfg["models_root"]), verify=True)
    if any(f["status"] != "verified" for f in models["files"]):
        raise Error("Pinned models are missing or differ; run models check --verify, do not auto-download")
    job["verified_models"] = [{k: f[k] for k in ("role", "sha256", "bytes", "path")} for f in models["files"]]
    job["server"] = client.request("/system_stats")
    for index, reference in enumerate(request["references"]):
        if index < len(job["uploads"]):
            continue
        path = Path(reference["path"])
        if sha256(path) != reference["sha256"]:
            raise Error("Reference changed after planning")
        content = reference_png(path)
        try:
            uploaded = client.upload(content, job["job_id"], index)
        except Error:
            job["state"] = "input_uncertain"
            save_job(root, job)
            raise
        job["uploads"].append(uploaded)
        save_job(root, job)
    graph = build(request["prompt"], request["width"], request["height"], request["seed"],
                  f"imagecraft/{job['job_id']}", job["uploads"])
    atomic_json(safe_child(root, "workflow.json"), graph)
    queue = client.request("/queue")
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise Error("ComfyUI became busy during preflight; nothing submitted. Reuse this prepared job later")
    job["workflow_sha256"] = sha256(root / "workflow.json")
    job["state"], job["submitted_at"] = "submitting", now()
    save_job(root, job)  # Durable identity BEFORE the only POST /prompt.
    try:
        response = client.request("/prompt", {"prompt": graph, "prompt_id": job["prompt_id"], "client_id": job["client_id"],
                                              "extra_data": {"imagecraft_job_id": job["job_id"]}})
    except HTTPFailure as exc:
        if exc.status in {400, 401, 403, 404, 405, 413, 415, 422, 429}:
            job["state"], job["error"] = "rejected", str(exc)
            save_job(root, job)
        raise
    prompt_id = response.get("prompt_id")
    try:
        uuid.UUID(prompt_id)
    except (ValueError, TypeError, AttributeError):
        raise Error("No valid prompt_id receipt; outcome uncertain, use status/resume, not a new submission") from None
    job["prompt_id"], job["state"] = prompt_id, "submitted"
    save_job(root, job)
    return job


def wait(cfg: dict, root: Path, job: dict, timeout: float) -> tuple[dict, int]:
    if cfg["url"] != job["endpoint"]:
        raise Error("Job endpoint differs from selected configuration")
    if not math.isfinite(timeout) or timeout < 0 or timeout > 86400:
        raise Error("Wait timeout must be between 0 and 86400 seconds")
    client = Client(cfg["url"])
    deadline = time.monotonic() + timeout
    while True:
        state, history = observe(client, job)
        if state == "downloaded":
            verify_artifacts(root, job)
            return summary(root, job), 0
        if state == "completed":
            if history is None:
                raise Error("Completed job has no history; inspect before retrieving output")
            job["state"] = "completed"
            save_job(root, job)
            fetch(client, root, job, history)
            return summary(root, job), 0
        if state == "failed":
            job["state"] = "failed"
            if history:
                atomic_json(safe_child(root, "history.json"), history)
            save_job(root, job)
            return summary(root, job), 2
        if state in {"rejected", "input_uncertain", "prepared", "unknown"}:
            # Preserve submitting state for ambiguous responses, never reset to prepared.
            save_job(root, job)
            return summary(root, job, state), 2 if state == "rejected" else 3
        save_job(root, job)
        if time.monotonic() >= deadline:
            return summary(root, job, state), 3
        time.sleep(min(2, max(0, deadline - time.monotonic())))
