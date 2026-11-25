"""Read-only NVIDIA GPU capability, free VRAM, and sustained load probe.

Distinguishes three states (matching SkillMarket's imagecraft convention):
- "ok": nvidia-smi succeeded; reports total/used/free MiB and multi-sample utilization.
- "present_but_inaccessible": nvidia-smi exists, but querying the device failed (common in sandboxes).
- "not_detected": nvidia-smi not found on PATH or standard driver locations.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time

NVIDIA_SMI_FALLBACKS = (
    "/usr/lib/wsl/lib/nvidia-smi",
    r"C:\Windows\System32\nvidia-smi.exe",
    r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
)

DEFAULT_BUSY_UTIL = 75       # % average GPU core utilization above which we avoid contending
VOXCPM15_SAFE_MIB = 4096     # ~2 GB weights + KV/activation headroom without squeezing host jobs
VOXCPM2_SAFE_MIB = 7168      # ~5 GB weights + headroom
WHISPER_SAFE_MIB = 3072      # faster-whisper large-v3-turbo float16


def find_nvidia_smi() -> str | None:
    found = shutil.which("nvidia-smi")
    if found:
        return found
    for candidate in NVIDIA_SMI_FALLBACKS:
        if os.path.isfile(candidate):
            return candidate
    return None


def probe_gpu(samples: int = 3, interval: float = 0.3, busy_util: int = DEFAULT_BUSY_UTIL) -> dict:
    exe = find_nvidia_smi()
    if not exe:
        return {
            "available": False,
            "state": "not_detected",
            "note": "nvidia-smi not found on PATH or standard driver paths; does not prove no GPU exists.",
        }

    readings = []
    meta = None
    detail = ""
    for idx in range(max(1, samples)):
        try:
            res = subprocess.run(
                [exe, "--query-gpu=name,driver_version,memory.total,memory.used,memory.free,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=8,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            res, detail = None, str(exc)

        if res is None or res.returncode != 0 or not res.stdout.strip():
            if res is not None:
                detail = (res.stderr or res.stdout or "").strip()[-300:]
            return {
                "available": False,
                "state": "present_but_inaccessible",
                "nvidia_smi_path": exe,
                "detail": detail,
                "note": ("NVIDIA tools are installed but GPU query failed (likely sandbox/container device isolation). "
                         "Ask the user to verify with nvidia-smi in a normal terminal; do not claim 'no GPU'."),
            }

        line = res.stdout.strip().splitlines()[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 6:
            return {"available": False, "state": "present_but_inaccessible", "detail": line}
        name, driver = parts[0], parts[1]
        try:
            total, used, free, util = (float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5]))
        except ValueError:
            return {"available": False, "state": "present_but_inaccessible", "detail": line}
        meta = (name, driver, round(total))
        readings.append((util, used, free))
        if idx + 1 < samples:
            time.sleep(interval)

    avg_util = round(sum(r[0] for r in readings) / len(readings))
    max_used = round(max(r[1] for r in readings))
    min_free = round(min(r[2] for r in readings))
    busy = avg_util >= busy_util
    vox15_ok = (not busy) and (min_free >= VOXCPM15_SAFE_MIB)
    vox2_ok = (not busy) and (min_free >= VOXCPM2_SAFE_MIB)
    whisper_ok = (not busy) and (min_free >= WHISPER_SAFE_MIB)

    reasons = []
    if busy:
        reasons.append(f"GPU utilization is {avg_util}% (>= {busy_util}% busy threshold)")
    if min_free < VOXCPM15_SAFE_MIB:
        reasons.append(f"free VRAM is {min_free} MiB (< {VOXCPM15_SAFE_MIB} MiB safe margin for VoxCPM1.5)")

    return {
        "available": True,
        "state": "ok",
        "name": meta[0],
        "driver_version": meta[1],
        "memory_total_mib": meta[2],
        "memory_used_mib": max_used,
        "memory_free_mib": min_free,
        "utilization_percent": avg_util,
        "busy": busy,
        "voxcpm15_safe": vox15_ok,
        "voxcpm2_safe": vox2_ok,
        "whisper_gpu_safe": whisper_ok,
        "guard_note": "; ".join(reasons) if reasons else "GPU has headroom for local neural voice/transcription.",
    }


def resolve_cached_model(candidates: list[str], weight_exts=(".safetensors", ".bin", ".pt", ".pth")) -> str | None:
    """Find a complete local HuggingFace or ModelScope snapshot directory without network access."""
    home = os.path.expanduser("~")
    roots = [
        os.path.join(home, ".cache", "modelscope", "models"),
        os.path.join(home, ".cache", "modelscope", "hub", "models"),
        os.path.join(home, ".cache", "huggingface", "hub"),
    ]
    has_weights = lambda d: os.path.isfile(os.path.join(d, "config.json")) and any(
        f.endswith(weight_exts) for f in os.listdir(d)
    )
    for root in roots:
        if not os.path.isdir(root):
            continue
        for pat in candidates:
            direct = os.path.join(root, pat)
            for probe_dir in [direct, os.path.join(direct, "snapshots")]:
                if not os.path.isdir(probe_dir):
                    continue
                if probe_dir.endswith("snapshots"):
                    for sub in sorted(os.listdir(probe_dir), reverse=True):
                        full = os.path.join(probe_dir, sub)
                        if os.path.isdir(full) and has_weights(full):
                            return full
                elif has_weights(probe_dir):
                    return probe_dir
    return None


if __name__ == "__main__":
    import json
    print(json.dumps(probe_gpu(), ensure_ascii=False, indent=2))
