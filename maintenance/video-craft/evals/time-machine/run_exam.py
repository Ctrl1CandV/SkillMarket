"""Run the complete music-video commission in a fresh pi workspace. Python stdlib."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


MODEL = "deepseek/deepseek-flash"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", type=Path)
    parser.add_argument("artist", help="artist and version confirmed by the client")
    parser.add_argument("out", type=Path, help="a new run directory, outside the skill")
    parser.add_argument("--skill", type=Path,
                        default=Path(__file__).resolve().parents[4] / "video-craft")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    out, skill, source = args.out.resolve(), args.skill.resolve(), args.recording.resolve()
    if not source.is_file() or not (skill / "SKILL.md").is_file():
        parser.error("recording and skill entrypoint must exist")
    if out.is_relative_to(skill) or (out.exists() and any(out.iterdir())):
        parser.error("use a fresh, empty output directory outside the skill")
    ffprobe = os.environ.get("VC_FFPROBE", "ffprobe")
    info = subprocess.check_output([ffprobe, "-v", "error", "-select_streams", "a:0",
                                    "-show_entries", "format=duration:stream=codec_name,sample_rate,channels",
                                    "-of", "json", str(source)])
    metadata = json.loads(info)
    if not metadata["streams"] or float(metadata["format"]["duration"]) <= 0:
        parser.error("the supplied file needs a playable audio stream")

    task, logs, snapshot = out / "task", out / "log", out / "video-craft"
    task.mkdir(parents=True)
    logs.mkdir()
    shutil.copytree(skill, snapshot, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules", ".git"))
    recording = task / ("original" + source.suffix.lower())
    shutil.copyfile(source, recording)
    snapshot_id = {p.relative_to(snapshot).as_posix(): digest(p)
                   for p in sorted(snapshot.rglob("*")) if p.is_file()}
    save_json(logs / "snapshot.json", snapshot_id)

    brief = (f"请使用本次提供的 video-craft，为 {args.artist} 的《Time Machine》制作完整 MV。"
             f"原声已放在当前目录的 {recording.name}。保持整首原录音的速度、起止与内容。"
             "创意、画面、设计和剪辑由你决定。交付可播放的 output/final.mp4 和可继续编辑的工程。"
             "请检查交付文件，简要说明你实际验证过的内容。")
    (task / "BRIEF.md").write_text(brief + "\n", encoding="utf-8")
    (task / "ENV.md").write_text(
        "当前目录是独立考核工作区，上一层的 video-craft 是本次快照。可在当前目录内制作、渲染与取帧。"
        "已有 Node、Python、FFmpeg 和 FFprobe；运行包使用 VC_CHROME 和 VC_NODE_MODULES 定位浏览器与 Playwright。"
        "原曲只供本地分析与合片；请使用本地工具处理媒体。模型工具上下文只带分析结果、原创画面与工程文本。"
        "任务文件、检查结果与中间产物均放在当前目录。"
        + ("命令行里的 python 已装 NumPy、Pillow 和 faster-whisper，VC_WHISPER 指向本地转写模型。"
           if os.environ.get("VC_WHISPER") else "") + "\n", encoding="utf-8")

    cli = shutil.which("pi.cmd" if os.name == "nt" else "pi")
    if not cli:
        parser.error("pi is not installed")
    if os.name == "nt":
        # Invoke the same entry point as npm's launcher, without cmd.exe argument quoting.
        entry = Path(cli).parent / "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
        if not entry.is_file():
            parser.error("cannot locate the installed pi CLI entry point")
        launcher = ["node", str(entry)]
    else:
        launcher = [cli]
    command = launcher + ["--print", "--offline", "--mode", "json", "--session", str(logs / "session.jsonl"),
                          "--no-context-files", "--no-skills", "--no-extensions", "--no-mcp",
                          "--no-prompt-templates", "--tools", "read,bash,powershell,edit,write",
                          "--skill", str(snapshot), "--model", MODEL, "--",
                          "请阅读当前目录的 BRIEF.md 和 ENV.md，完成这次委托。"]
    run = {"model": MODEL, "pi_version": subprocess.check_output(launcher + ["--version"], text=True).strip(),
           "artist_version": args.artist, "recording": recording.name, "recording_sha256": digest(recording),
           "recording_probe": metadata, "command": command, "status": "prepared"}
    report = logs / "run.json"
    save_json(report, run)
    if args.prepare_only:
        return
    run.update(status="running", start=datetime.now(timezone.utc).isoformat())
    save_json(report, run)
    with (logs / "events.jsonl").open("wb") as events, (logs / "stderr.log").open("wb") as errors:
        result = subprocess.run(command, cwd=task, stdin=subprocess.DEVNULL, stdout=events, stderr=errors)
    final = task / "output/final.mp4"
    run.update(status="finished", exit_code=result.returncode, end=datetime.now(timezone.utc).isoformat(),
               final_bytes=final.stat().st_size if final.is_file() else 0)
    save_json(report, run)
    print(f"pi exit={result.returncode}, output/final.mp4={run['final_bytes']} bytes")
    raise SystemExit(result.returncode or (0 if run["final_bytes"] else 1))


if __name__ == "__main__":
    main()
