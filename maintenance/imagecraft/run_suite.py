#!/usr/bin/env python3
"""Run an explicitly selected, bounded image suite; never retry or cherry-pick."""
from __future__ import annotations

import argparse
import hashlib
from importlib import import_module
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

from benchmark import memory_sample

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "imagecraft/scripts"))
# Load the selected source-tree CLI helpers, not an unrelated installed package.
_common = import_module("ic.common")
Error, atomic_json, now = _common.Error, _common.atomic_json, _common.now
dimensions = import_module("ic.workflow").dimensions


def load_suite(path: Path) -> dict:
    if path.stat().st_size > 256 * 1024:
        raise ValueError("Suite exceeds 256 KiB")
    suite = json.loads(path.read_text(encoding="utf-8"))
    if suite.get("schema") != "imagecraft.eval-suite/1":
        raise ValueError("Unsupported suite schema")
    cases = suite.get("cases")
    if not isinstance(cases, list) or not 1 <= len(cases) <= 32:
        raise ValueError("Explicit suites must contain 1–32 cases")
    seen = set()
    for case in cases:
        name = case.get("id", "")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name) or name in seen:
            raise ValueError("Case IDs must be unique, bounded lowercase names, not paths")
        if case.get("intent") not in {"general", "portrait", "anime", "ui", "diagram"}:
            raise ValueError(f"Invalid intent: {name}")
        prompt = case.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 12000:
            raise ValueError(f"Invalid prompt: {name}")
        seed = case.get("seed")
        if type(seed) is not int or not 0 <= seed <= 2**64 - 1:
            raise ValueError(f"Invalid seed: {name}")
        if any(type(case.get(k)) is not int for k in ("width", "height")):
            raise ValueError(f"Explicit integer dimensions are required: {name}")
        dimensions(case["width"], case["height"])
        if any(not isinstance(case.get(k), str) or not case[k].strip() for k in ("group", "label")):
            raise ValueError(f"A group and label are required: {name}")
        references = case.get("references", [])
        if not isinstance(references, list) or len(references) > 2 or any(not isinstance(x, str) or x not in seen for x in references):
            raise ValueError(f"References must name earlier cases, never external files: {name}")
        if not isinstance(case.get("checks"), list) or not case["checks"] or not all(isinstance(x, str) and x for x in case["checks"]):
            raise ValueError(f"Explicit review checks are required: {name}")
        seen.add(name)
    return suite


def plan(suite: dict) -> dict:
    return {"schema": "imagecraft.suite-plan/1", "suite": suite["name"], "total_jobs": len(suite["cases"]),
            "text_to_image": sum(not c.get("references") for c in suite["cases"]),
            "reference_edits": sum(bool(c.get("references")) for c in suite["cases"]),
            "cases": [{k: c[k] for k in ("id", "label", "group", "width", "height", "seed", "checks")} for c in suite["cases"]],
            "policy": "one attempt each; no new weights; no cloud calls; all outputs retained; visual review required"}


def execute(base: list[str], command: list[str], output: Path, case: dict) -> dict:
    samples: list[dict] = []
    done = threading.Event()
    def sample():
        while not done.is_set():
            samples.append(memory_sample())
            done.wait(1)
    worker = threading.Thread(target=sample)
    worker.start()
    started = time.monotonic()
    try:
        result = subprocess.run(base + command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1200)
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else exc.stdout or ""
        stderr, code = "Client process timed out; GPU job may still be running. Inspect existing job, do not resubmit.", 3
    finally:
        done.set()
        worker.join()
    elapsed = time.monotonic() - started
    name = case["id"]
    (output / f"{name}.stdout.json").write_text(stdout, encoding="utf-8")
    (output / f"{name}.stderr.txt").write_text(stderr, encoding="utf-8")
    atomic_json(output / f"{name}.memory.json", {"samples": samples})
    try:
        payload = json.loads(stdout)
    except ValueError:
        payload = {"error": "No complete JSON receipt; inspect captured output and the existing job directory"}
    gpu = [v for s in samples for v in s.get("gpu_used_mib", [])]
    ram = [s["system_used_mib"] for s in samples if "system_used_mib" in s]
    return {"id": name, "group": case["group"], "label": case["label"], "checks": case["checks"],
            "returncode": code, "wall_seconds": round(elapsed, 3), "result": payload,
            "gpu_peak_mib": max(gpu, default=None), "system_ram_peak_mib": max(ram, default=None)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--suite", type=Path, required=True)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--config", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    try:
        suite = load_suite(args.suite)
        if args.dry_run:
            print(json.dumps(plan(suite), ensure_ascii=False, indent=2))
            return 0
        if not args.config or not args.config.is_file() or not args.output or not args.output.is_absolute():
            raise ValueError("A selected private config and a new absolute output directory are required")
        output = args.output.resolve()
        if output == REPO or REPO in output.parents:
            raise ValueError("Keep real samples and evidence outside the repository")
        output.mkdir(parents=True, exist_ok=False)
        atomic_json(output / "suite.json", suite)
        report = {"schema": "imagecraft.suite-result/1", "suite": suite["name"], "started_at": now(), "state": "running",
                  "suite_source_sha256": hashlib.sha256(args.suite.read_bytes()).hexdigest(), "planned_jobs": len(suite["cases"]),
                  "memory_scope": "approximately 1-second whole-GPU and whole-system RAM samples, not process/PyTorch peaks", "cases": []}
        atomic_json(output / "report.json", report)
        base = [args.python, "-B", str(REPO / "imagecraft/scripts/imagecraft.py"), "--config", str(args.config.resolve())]
        for case in suite["cases"]:
            name = case["id"]
            prompt_file = output / f"{name}.prompt.txt"
            prompt_file.write_text(case["prompt"], encoding="utf-8")
            command = ["generate", "--prompt-file", str(prompt_file), "--width", str(case["width"]), "--height", str(case["height"]),
                       "--seed", str(case["seed"]), "--intent", case["intent"], "--output", str(output / name), "--wait", "900"]
            for source_id in case.get("references", []):
                source = output / source_id / "image.png"
                if not source.is_file():
                    raise ValueError(f"Earlier reference output missing: {source_id}; stopping without submission")
                command.extend(["--reference", str(source)])
            entry = execute(base, command, output, case)
            report["cases"].append(entry)
            atomic_json(output / "report.json", report)
            print(json.dumps({"id": name, "returncode": entry["returncode"], "state": entry["result"].get("state"),
                              "server_seconds": entry["result"].get("server_execution_seconds"), "wall_seconds": entry["wall_seconds"],
                              "gpu_peak_mib": entry["gpu_peak_mib"]}, ensure_ascii=False), flush=True)
            if entry["returncode"] != 0 or entry["result"].get("state") != "downloaded":
                report["state"] = "stopped_for_inspection"
                atomic_json(output / "report.json", report)
                return 2
        report["state"], report["finished_at"] = "technical_checks_completed_visual_review_required", now()
        atomic_json(output / "report.json", report)
        return 0
    except (OSError, ValueError, KeyError, Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")
    raise SystemExit(main())
