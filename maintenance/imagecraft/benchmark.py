#!/usr/bin/env python3
"""Opt-in real GPU smoke tests. Outputs and private machine details stay outside git."""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

CASES = [
    ("general-cold", "general", 1024, 1024, 42, "A single matte red ceramic teapot on an oak table, soft daylight from the left, warm neutral studio background, realistic product photograph, clearly formed spout and handle, centered composition, no lettering."),
    ("general-warm", "general", 1024, 1024, 43, "A single matte red ceramic teapot on an oak table, soft daylight from the left, warm neutral studio background, realistic product photograph, clearly formed spout and handle, centered composition, no lettering."),
    ("portrait", "portrait", 832, 1216, 301, "Editorial half-body portrait of an adult ceramic artist in a sunlit studio, plain indigo work apron, natural skin texture, relaxed expression, both hands resting visibly on a wooden workbench, soft side-window light, understated warm colors, realistic photography."),
    ("anime", "anime", 832, 1216, 302, "An original adult courier with short dark hair and an orange utility jacket, standing beside a compact bicycle at a rainy train station, clean anime line art, restrained cel shading, teal and amber palette, clear full-body silhouette, calm cinematic framing."),
    ("ui", "ui", 1216, 832, 303, "Desktop landing-page visual concept for a neighborhood ceramics studio. Warm ivory background, charcoal editorial typography, muted terracotta accents. A quiet left-aligned headline area with generous whitespace, one large pottery photograph on the right, a compact navigation bar and a clear workshop booking action. Below, a restrained three-column class schedule. A coherent full page, not a browser or device mockup. Short English labels only: CLAY STUDIO, Workshops, Visit, Book a class."),
    ("diagram-visual", "diagram", 1216, 832, 304, "A clean flat technical architecture diagram on a white background. Six rounded rectangular nodes with legible labels: Client, API, Queue, Worker, Model, Storage. Arrange Client, API, Queue, Worker in one horizontal row from left to right. Place Model below Worker and Storage below Client. Thin blue arrows connect Client to API, API to Queue, Queue to Worker, Worker to Model, Worker to Storage, and Storage back to Client. Restrained blue and gray palette, generous spacing, no extra nodes."),
]


def memory_sample():
    sample: dict = {"time": time.time()}
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=True)
        sample["gpu_used_mib"] = [int(x) for x in result.stdout.strip().splitlines()]
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                        ("total_physical", ctypes.c_ulonglong), ("available_physical", ctypes.c_ulonglong),
                        ("total_page", ctypes.c_ulonglong), ("available_page", ctypes.c_ulonglong),
                        ("total_virtual", ctypes.c_ulonglong), ("available_virtual", ctypes.c_ulonglong),
                        ("available_extended", ctypes.c_ulonglong)]
        status = MEMORYSTATUSEX()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            sample["system_used_mib"] = round((status.total_physical - status.available_physical) / 1024**2)
    return sample


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--python", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--only", choices=[x[0] for x in CASES])
    args = p.parse_args()
    output = Path(args.output).resolve()
    repo = Path(__file__).resolve().parents[2]
    if output == repo or repo in output.parents:
        raise SystemExit("Keep real benchmark outputs outside the repository")
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "benchmark.json"
    if report_path.exists():
        raise SystemExit("Use a new benchmark directory; existing evidence is never overwritten")
    cli = repo / "imagecraft/scripts/imagecraft.py"
    base = [args.python, "-B", str(cli), "--config", args.config]
    report = {"schema": "imagecraft.benchmark/1", "started_at": datetime.now(timezone.utc).isoformat(), "cases": [],
              "memory_scope": "1-second samples of whole GPU and whole-system RAM, not PyTorch/process peaks; other workloads included"}

    def invoke(name, command):
        samples, done = [], threading.Event()
        def sample():
            while not done.is_set():
                samples.append(memory_sample())
                done.wait(1)
        worker = threading.Thread(target=sample)
        worker.start()
        started = time.monotonic()
        try:
            result = subprocess.run(base + command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1200)
        finally:
            done.set()
            worker.join(timeout=10)
        elapsed = time.monotonic() - started
        (output / f"{name}.stdout.json").write_text(result.stdout, encoding="utf-8")
        (output / f"{name}.stderr.txt").write_text(result.stderr, encoding="utf-8")
        (output / f"{name}.memory.json").write_text(json.dumps(samples), encoding="utf-8")
        try:
            payload = json.loads(result.stdout)
        except ValueError:
            payload = {"error": "Non-JSON CLI output; inspect the saved stdout/stderr"}
        entry = {"name": name, "returncode": result.returncode, "wall_seconds": round(elapsed, 3), "result": payload,
                 "gpu_peak_mib": max((max(s.get("gpu_used_mib", [0])) for s in samples), default=None),
                 "system_ram_peak_mib": max((s.get("system_used_mib", 0) for s in samples), default=None)}
        report["cases"].append(entry)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(entry, ensure_ascii=False), flush=True)
        return entry

    selected = [c for c in CASES if not args.only or c[0] == args.only]
    for name, intent, width, height, seed, prompt in selected:
        target = output / name
        prompt_file = output / f"{name}.prompt.txt"
        prompt_file.write_text(prompt, encoding="utf-8")
        command = ["generate", "--prompt-file", str(prompt_file), "--width", str(width), "--height", str(height),
                   "--seed", str(seed), "--intent", intent, "--output", str(target)]
        first = invoke(name + "-submit", command + ["--wait", "0"])
        if first["returncode"] not in (0, 3):
            return 2
        completed = invoke(name + "-resume", ["resume", "--job", str(target), "--wait", "900"])
        if completed["returncode"] != 0:
            return 2
        if name == "general-cold":
            duplicate = invoke("idempotent-replay", command + ["--wait", "0"])
            if duplicate["returncode"] != 0 or duplicate["result"].get("prompt_id") != completed["result"].get("prompt_id"):
                return 2
    if not args.only:
        source = output / "general-cold/image.png"
        edited = invoke("reference-edit", ["generate", "--prompt", "Change only the ceramic teapot color from red to cobalt blue. Preserve the teapot shape, its spout and handle, the camera angle, background and table.",
                                          "--reference", str(source), "--seed", "42", "--output", str(output / "reference-edit"), "--wait", "900"])
        if edited["returncode"] != 0:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
