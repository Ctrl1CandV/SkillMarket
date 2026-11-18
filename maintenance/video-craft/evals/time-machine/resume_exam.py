"""Compact pi's existing session after a transport failure, then resume the same job."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess

from run_exam import save_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exam", type=Path)
    args = parser.parse_args()
    exam = args.exam.resolve()
    logs = exam / "log"
    report = json.loads((logs / "run.json").read_text(encoding="utf-8"))
    if report["status"] != "finished" or (exam / "task/output/final.mp4").is_file():
        parser.error("the previous process must have stopped before delivering a final cut")
    dest = logs / ("resume-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    dest.mkdir()
    shutil.copy2(logs / "session.jsonl", dest / "session-before.jsonl")
    command = report["command"][:]
    rpc = command[:command.index("--")]
    rpc.remove("--print")
    rpc[rpc.index("--mode") + 1] = "rpc"
    with (dest / "compact-errors.log").open("wb") as errors:
        proc = subprocess.Popen(rpc, cwd=exam / "task", stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=errors, text=True, encoding="utf-8")
        try:
            proc.stdin.write(json.dumps({"type": "compact"}) + "\n")
            proc.stdin.flush()
            for line in proc.stdout:
                event = json.loads(line)
                if event.get("type") == "response" and event.get("command") == "compact":
                    save_json(dest / "compaction.json", event)
                    if not event.get("success"):
                        raise RuntimeError("pi compaction failed; see compaction.json")
                    print("pi compacted the existing session", flush=True)
                    break
            else:
                raise RuntimeError("pi exited before acknowledging compaction")
        finally:
            proc.stdin.close()
            proc.terminate()
            proc.wait()
    command[-1] = ("原服务连接曾中断。请在原会话里继续原委托，沿用已完成的创意、镜头和工程，"
                   "完成全曲渲染与交付。复查画面时可读缩小的联系表，避免重复传送大量原尺寸图造成连接中断。")
    metadata = {"model": report["model"], "command": command, "start": datetime.now(timezone.utc).isoformat()}
    save_json(dest / "run.json", metadata)
    with (dest / "events.jsonl").open("wb") as events, (dest / "stderr.log").open("wb") as errors:
        result = subprocess.run(command, cwd=exam / "task", stdin=subprocess.DEVNULL, stdout=events, stderr=errors)
    final = exam / "task/output/final.mp4"
    metadata.update(exit_code=result.returncode, end=datetime.now(timezone.utc).isoformat(),
                    final_bytes=final.stat().st_size if final.is_file() else 0)
    save_json(dest / "run.json", metadata)
    print(f"resumed pi exit={result.returncode}, final bytes={metadata['final_bytes']}")
    raise SystemExit(result.returncode or (0 if final.is_file() else 1))


if __name__ == "__main__":
    main()
