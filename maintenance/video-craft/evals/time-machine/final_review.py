"""Let the same pi session review its first cut with the final video-craft files."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess

from run_exam import digest, save_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exam", type=Path)
    parser.add_argument("skill", type=Path)
    args = parser.parse_args()
    root = args.exam.resolve()
    recording = json.loads((root / "log/run.json").read_text(encoding="utf-8"))
    if recording["status"] != "finished" or recording["exit_code"] != 0:
        parser.error("complete the initial pi commission before requesting final review")
    final = root / "task/output/final.mp4"
    if not final.is_file() or not (args.skill / "SKILL.md").is_file():
        parser.error("the first cut and final skill entry point are required")
    snapshot, logs = root / "video-craft-final", root / "review"
    if snapshot.exists() or logs.exists():
        parser.error("a final review already exists; check its log")
    logs.mkdir()
    shutil.copy2(final, logs / "first-cut.mp4")
    shutil.copy2(root / "log/session.jsonl", logs / "first-session.jsonl")
    shutil.copytree(args.skill, snapshot, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules", ".git"))
    files = {p.relative_to(snapshot).as_posix(): digest(p) for p in sorted(snapshot.rglob("*")) if p.is_file()}
    save_json(logs / "snapshot.json", files)
    previous = json.loads((root / "log/snapshot.json").read_text(encoding="utf-8"))
    changed = sorted(path for path in set(previous) | set(files) if previous.get(path) != files.get(path))
    command = recording["command"][:]
    command[command.index("--skill") + 1] = str(snapshot)
    command[-1] = ("请使用补齐参考样片的最终版 video-craft（../video-craft-final/SKILL.md），"
                   "对你交付的整部 MV 复查，交付最终 output/final.mp4。原命题不变。"
                   "首版文件在 Windows 的另一读取账号下遇到访问权限问题。"
                   "收尾时请用最终版 kit/mux_original.py 将你的最终画面与原录音重新合片，"
                   "让输出文件正常继承目标目录权限。")
    report = {"model": recording["model"], "command": command, "snapshot_changes": changed,
              "first_cut_sha256": digest(final), "start": datetime.now(timezone.utc).isoformat()}
    save_json(logs / "run.json", report)
    with (logs / "events.jsonl").open("wb") as events, (logs / "stderr.log").open("wb") as errors:
        result = subprocess.run(command, cwd=root / "task", stdin=subprocess.DEVNULL, stdout=events, stderr=errors)
    report.update(exit_code=result.returncode, end=datetime.now(timezone.utc).isoformat(),
                  final_cut_sha256=digest(final) if final.is_file() else None)
    save_json(logs / "run.json", report)
    print(f"pi review exit={result.returncode}, final={report['final_cut_sha256']}")
    raise SystemExit(result.returncode or (0 if final.is_file() else 1))


if __name__ == "__main__":
    main()
