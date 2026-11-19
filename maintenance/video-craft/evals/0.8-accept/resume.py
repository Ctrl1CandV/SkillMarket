"""Compact pi's session after a transport error, then continue the same job in the same session. Python stdlib.

    python resume.py runs/promo-deepseek

Logs go to <run>/log/resume-<time>/.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess

from run import pi_env, pi_project_settings, save

PROMPT = ("原服务连接曾中断。请在原会话里继续原委托，沿用已完成的创意、镜头和工程，完成渲染与交付。"
          "复查画面时可读缩小的联系表，避免重复传送大量原尺寸图造成连接中断。")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path)
    args = ap.parse_args()
    run = args.run.resolve()
    task, logs = run / "task", run / "log"
    report = json.loads((logs / "run.json").read_text(encoding="utf-8"))
    if report["status"] != "finished" or (task / "output/final.mp4").is_file():
        ap.error("the previous process must have stopped before delivering output/final.mp4")
    dest = logs / ("resume-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    dest.mkdir()
    shutil.copy2(logs / "session.jsonl", dest / "session-before.jsonl")
    env = pi_env()
    command = report["command"][:]
    for flag in pi_project_settings(task, report["model"]):   # runs started before the compaction setting existed
        if flag not in command:
            command.insert(command.index("--skill"), flag)
    rpc = command[:command.index("--")]
    rpc.remove("--print")
    rpc[rpc.index("--mode") + 1] = "rpc"
    with (dest / "compact-errors.log").open("wb") as errors:
        proc = subprocess.Popen(rpc, cwd=task, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=errors, text=True, encoding="utf-8")
        try:
            proc.stdin.write(json.dumps({"type": "compact"}) + "\n")
            proc.stdin.flush()
            for line in proc.stdout:
                event = json.loads(line)
                if event.get("type") == "response" and event.get("command") == "compact":
                    save(dest / "compaction.json", event)
                    if not event.get("success"):
                        raise RuntimeError("pi compaction failed; see compaction.json")
                    print("pi compacted the session", flush=True)
                    break
            else:
                raise RuntimeError("pi exited before acknowledging compaction")
        finally:
            proc.stdin.close()
            proc.terminate()
            proc.wait()
    command[-1] = PROMPT
    meta = {"model": report["model"], "command": command, "start": datetime.now(timezone.utc).isoformat()}
    save(dest / "run.json", meta)
    with (dest / "events.jsonl").open("wb") as events, (dest / "stderr.log").open("wb") as errors:
        result = subprocess.run(command, cwd=task, env=env, stdin=subprocess.DEVNULL, stdout=events, stderr=errors)
    final = task / "output/final.mp4"
    meta.update(exit_code=result.returncode, end=datetime.now(timezone.utc).isoformat(),
                final_bytes=final.stat().st_size if final.is_file() else 0)
    save(dest / "run.json", meta)
    print(f"resumed: exit={result.returncode}, final.mp4={meta['final_bytes']} bytes")


if __name__ == "__main__":
    main()
