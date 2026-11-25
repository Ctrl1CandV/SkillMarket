"""Objective audit & anonymized blind-pack builder for 2026-11-26 STEM 3-way evaluation.

Usage:
    python audit_runs.py <eval_root_dir>

Collects:
  1. pi session metrics (duration, tool calls, images read, skill/reference files read, cost/tokens)
  2. ffprobe stream verification (resolution, fps, video/audio/subtitle codecs, duration)
  3. ffmpeg ebur128 integrated loudness (LUFS) & true peak (dBFS)
  4. shotlist.py metrics (default mode & --mode lesson)
  5. 4 representative 1080p frames (15%, 42%, 68%, 88% of duration) + randomized blind bundle (blind_pack/)
"""
from datetime import datetime
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
SHOTLIST = REPO_ROOT / "video-craft/kit/shotlist.py"


def parse_events(events_path: Path):
    tool_calls = 0
    images_read = 0
    files_read = []
    cost = 0.0
    in_tok = 0
    out_tok = 0
    if not events_path.is_file():
        return {}
    for raw in events_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = raw.strip()
        if not raw.startswith("{"):
            continue
        try:
            ev = json.loads(raw)
        except Exception:
            continue
        etype = ev.get("type", "")
        if etype == "tool_execution_start":
            tool_calls += 1
            tname = ev.get("toolName", "")
            args = ev.get("args") or {}
            p = str(args.get("path") or args.get("file_path") or "")
            if tname == "read" and p:
                files_read.append(p.replace("\\", "/"))
                if re.search(r"\.(png|jpg|jpeg|webp)$", p, re.I):
                    images_read += 1
        elif etype == "message_end":
            usage = (ev.get("message") or {}).get("usage") or {}
            in_tok += int(usage.get("input", 0) or 0)
            out_tok += int(usage.get("output", 0) or 0)
            c = usage.get("cost")
            if isinstance(c, dict):
                cost += float(c.get("total", 0.0) or 0.0)
            elif isinstance(c, (int, float)):
                cost += float(c)
    read_skill = any("SKILL.md" in f for f in files_read)
    read_stem_ref = any("course-and-stem.md" in f for f in files_read)
    read_scenic_refs = [Path(f).name for f in files_read if any(k in f for k in ("music-video.md", "cinematography.md", "drawing.md"))]
    return {
        "tool_calls": tool_calls,
        "images_read": images_read,
        "read_skill": read_skill,
        "read_course_and_stem": read_stem_ref,
        "scenic_refs_read": sorted(set(read_scenic_refs)),
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "cost_usd": round(cost, 4),
    }


def probe_media(mp4: Path):
    if not mp4.is_file():
        return {"exists": False}
    try:
        raw = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(mp4)],
            text=True, encoding="utf-8",
        )
    except subprocess.CalledProcessError as e:
        return {"exists": True, "corrupt": True, "bytes": mp4.stat().st_size, "error": str(e)}
    info = json.loads(raw)
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    a = next((s for s in streams if s.get("codec_type") == "audio"), {})
    subs = [s for s in streams if s.get("codec_type") == "subtitle"]
    dur = float((info.get("format") or {}).get("duration", 0.0) or 0.0)

    # Measure integrated LUFS via ebur128
    lufs, peak = None, None
    if a:
        p = subprocess.run(
            ["ffmpeg", "-nostdin", "-i", str(mp4), "-af", "ebur128=peak=true", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="ignore",
        )
        m_i = re.findall(r"I:\s*(-?\d+\.\d+)\s*LUFS", p.stderr)
        m_p = re.findall(r"Peak:\s*(-?\d+\.\d+)\s*dBFS", p.stderr)
        if m_i:
            lufs = float(m_i[-1])
        if m_p:
            peak = float(m_p[-1])

    # Run shotlist in both default and lesson modes
    sl_lesson = subprocess.run(
        [sys.executable, str(SHOTLIST), str(mp4), "--mode", "lesson"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
    ).stdout.strip()
    sl_default = subprocess.run(
        [sys.executable, str(SHOTLIST), str(mp4)],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
    ).stdout.strip()

    return {
        "exists": True,
        "bytes": mp4.stat().st_size,
        "duration_s": round(dur, 2),
        "width": v.get("width"),
        "height": v.get("height"),
        "fps": v.get("r_frame_rate"),
        "vcodec": v.get("codec_name"),
        "acodec": a.get("codec_name") if a else None,
        "soft_subtitles": len(subs),
        "lufs": lufs,
        "true_peak_dbfs": peak,
        "shotlist_lesson_tail": sl_lesson.splitlines()[-1] if sl_lesson else "",
        "shotlist_lesson": sl_lesson,
        "shotlist_default_tail": sl_default.splitlines()[-1] if sl_default else "",
    }


def extract_frames(mp4: Path, out_dir: Path, dur: float):
    out_dir.mkdir(parents=True, exist_ok=True)
    if dur <= 1.0:
        return []
    out_paths = []
    for tag, frac in [("f1_hook", 0.15), ("f2_mid1", 0.42), ("f3_mid2", 0.68), ("f4_end", 0.88)]:
        ts = round(dur * frac, 2)
        dst = out_dir / f"{tag}_t{ts:05.2f}.png"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(ts), "-i", str(mp4), "-frames:v", "1", str(dst), "-loglevel", "error"],
            check=False,
        )
        if dst.is_file():
            out_paths.append(str(dst))
    return out_paths


def main():
    root = Path(sys.argv[1]).resolve()
    runs_dir = root / "runs"
    audit_dir = root / "audit"
    blind_dir = root / "blind_pack"
    audit_dir.mkdir(parents=True, exist_ok=True)
    blind_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(20261126)
    records = []
    by_problem = {}

    for run_path in sorted(runs_dir.iterdir()):
        meta_file = run_path / "log/run.json"
        if not meta_file.is_file():
            continue
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        t0 = datetime.fromisoformat(meta["start"])
        t1 = datetime.fromisoformat(meta["end"]) if meta.get("end") else t0
        wall_min = round((t1 - t0).total_seconds() / 60.0, 2)
        ev_stats = parse_events(run_path / "log/events.jsonl")
        mp4 = run_path / "task/output/final.mp4"
        media = probe_media(mp4)
        frames = extract_frames(mp4, audit_dir / run_path.name, media.get("duration_s", 0.0)) if media.get("exists") else []
        rec = {
            "id": run_path.name,
            "problem": meta["problem"],
            "arm": meta["arm"],
            "model": meta["model"],
            "exit_code": meta.get("exit_code"),
            "wall_minutes": wall_min,
            **ev_stats,
            "media": media,
            "frames": frames,
        }
        records.append(rec)
        by_problem.setdefault(meta["problem"], []).append((rec, mp4))

    # Build randomized blind pack (A / B / C per problem)
    blind_key = {}
    for prob, items in by_problem.items():
        shuffled = items[:]
        rng.shuffle(shuffled)
        blind_key[prob] = {}
        for label, (rec, mp4) in zip(["A", "B", "C"], shuffled):
            blind_name = f"{prob}-{label}.mp4"
            if mp4.is_file():
                shutil.copy2(mp4, blind_dir / blind_name)
                blind_frames_dir = blind_dir / f"{prob}-{label}-frames"
                blind_frames_dir.mkdir(exist_ok=True)
                for fp in rec["frames"]:
                    shutil.copy2(fp, blind_frames_dir / Path(fp).name)
            blind_key[prob][label] = {"arm": rec["arm"], "model": rec["model"], "run_id": rec["id"]}

    (audit_dir / "summary.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    (blind_dir / "SEALED_KEY.json").write_text(json.dumps(blind_key, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Audited {len(records)} runs -> {audit_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
