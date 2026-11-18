"""Let the same pi session review its first cut with the final video-craft files."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess

from run_exam import digest, save_json


def review_stop_reason(events_path):
    reason = None
    with events_path.open(encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            kind = event["type"]
            if kind in ("agent_start", "auto_retry_start"):
                reason = None
            elif kind == "agent_end":
                messages = event["messages"]
                reason = None
                if messages and messages[-1].get("role") == "assistant" and not event.get("willRetry"):
                    reason = messages[-1].get("stopReason")
            elif kind == "agent_settled" and event.get("aborted"):
                reason = "aborted"
            elif kind == "auto_retry_end" and not event["success"]:
                reason = "error"
    return reason


def validate_movie(path):
    if not path.is_file() or not path.stat().st_size:
        raise ValueError("pi did not deliver a new output/final.mp4")
    data = json.loads(subprocess.check_output([
        os.environ.get("VC_FFPROBE", "ffprobe"), "-v", "error", "-show_entries",
        "stream=codec_type:stream_disposition=attached_pic:format=format_name,duration",
        "-of", "json", str(path)]))
    kinds = {s["codec_type"] for s in data["streams"] if not s["disposition"]["attached_pic"]}
    if ("mp4" not in data["format"]["format_name"].split(",") or not {"video", "audio"} <= kinds
            or float(data["format"]["duration"]) <= 0):
        raise ValueError("review output must be an MP4 with both picture and audio")


def first_cut_completed(logs, recording, final):
    if recording["status"] != "finished" or not final.is_file() or not final.stat().st_size:
        return False
    attempts = sorted(p for p in logs.glob("resume-*") if p.is_dir())
    if not attempts:
        return recording.get("exit_code") == 0
    latest = attempts[-1]
    metadata, events = latest / "run.json", latest / "events.jsonl"
    if not metadata.is_file() or not events.is_file():
        return False
    resumed = json.loads(metadata.read_text(encoding="utf-8"))
    return (resumed.get("exit_code") == 0 and resumed.get("model") == recording["model"]
            and resumed.get("command", [])[:-1] == recording["command"][:-1]
            and resumed.get("final_bytes") == final.stat().st_size
            and review_stop_reason(events) == "stop")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exam", type=Path)
    parser.add_argument("skill", type=Path)
    args = parser.parse_args()
    root = args.exam.resolve()
    recording = json.loads((root / "log/run.json").read_text(encoding="utf-8"))
    final = root / "task/output/final.mp4"
    if not first_cut_completed(root / "log", recording, final):
        parser.error("a completed pi commission with its first cut is required before final review")
    if not (args.skill / "SKILL.md").is_file():
        parser.error("the final skill entry point is required")
    snapshot, logs = root / "video-craft-final", root / "review"
    if snapshot.exists() or logs.exists():
        parser.error("a final review already exists; check its log")
    logs.mkdir()
    shutil.copy2(root / "log/session.jsonl", logs / "first-session.jsonl")
    shutil.copytree(args.skill, snapshot, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules", ".git"))
    files = {p.relative_to(snapshot).as_posix(): digest(p) for p in sorted(snapshot.rglob("*")) if p.is_file()}
    save_json(logs / "snapshot.json", files)
    previous = json.loads((root / "log/snapshot.json").read_text(encoding="utf-8"))
    changed = sorted(path for path in set(previous) | set(files) if previous.get(path) != files.get(path))
    command = recording["command"][:]
    command[command.index("--skill") + 1] = str(snapshot)
    command[-1] = ("请使用补齐参考样片的最终版 video-craft（../video-craft-final/SKILL.md），"
                   "请读取已移至 ../review/first-cut.mp4 的首版成片，复查整部 MV，并重新交付 output/final.mp4。原命题不变。"
                   "首版文件在 Windows 的另一读取账号下遇到访问权限问题。"
                   "收尾时请用最终版 kit/mux_original.py 将你的最终画面与原录音重新合片，"
                   "让输出文件正常继承目标目录权限。")
    report = {"model": recording["model"], "command": command, "snapshot_changes": changed,
              "status": "running", "pi_exit_code": None, "final_cut_sha256": None,
              "first_cut_sha256": digest(final), "start": datetime.now(timezone.utc).isoformat()}
    save_json(logs / "run.json", report)
    first_cut = logs / "first-cut.mp4"
    final.replace(first_cut)
    try:
        events_path = logs / "events.jsonl"
        with events_path.open("wb") as events, (logs / "stderr.log").open("wb") as errors:
            result = subprocess.run(command, cwd=root / "task", stdin=subprocess.DEVNULL, stdout=events, stderr=errors)
        report["pi_exit_code"] = result.returncode
        if result.returncode:
            raise SystemExit(result.returncode)
        reason = review_stop_reason(events_path)
        report["stop_reason"] = reason
        if reason != "stop":
            raise ValueError(f"pi review lacks a completed assistant turn (stop reason {reason!r})")
        validate_movie(final)
        report.update(status="finished", exit_code=0, final_cut_sha256=digest(final),
                      end=datetime.now(timezone.utc).isoformat())
        save_json(logs / "run.json", report)
    except BaseException as error:
        if final.exists():
            final.replace(logs / "rejected-output.mp4")
        first_cut.replace(final)
        shutil.copy2(final, first_cut)
        report.update(status="failed", exit_code=report["pi_exit_code"] or 1, final_cut_sha256=None,
                      error=f"{type(error).__name__}: {error}", end=datetime.now(timezone.utc).isoformat())
        save_json(logs / "run.json", report)
        raise
    print(f"pi review completed, final={report['final_cut_sha256']}")


if __name__ == "__main__":
    main()
