"""Compact and resume timed-out runs in-place without modifying model-authored scene files, then run audit_runs.py."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import run_blind

ROOT = Path(os.environ["LOCALAPPDATA"]) / "vc-eval/2026-11-26-stem"
ENV = run_blind.pi_env()


def compact_and_resume(run_name: str):
    run_dir = ROOT / "runs" / run_name
    task, logs = run_dir / "task", run_dir / "log"
    meta = json.loads((logs / "run.json").read_text(encoding="utf-8"))
    cmd = meta["command"][:]

    rpc = cmd[:cmd.index("--")]
    rpc.remove("--print")
    rpc[rpc.index("--mode") + 1] = "rpc"
    t0 = time.time()
    proc = subprocess.Popen(
        rpc, cwd=task, env=ENV,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, encoding="utf-8",
    )
    try:
        proc.stdin.write(json.dumps({"type": "compact"}) + "\n")
        proc.stdin.flush()
        for line in proc.stdout:
            if not line.strip().startswith("{"):
                continue
            ev = json.loads(line)
            if ev.get("type") == "response" and ev.get("command") == "compact":
                ok = ev.get("success")
                print(f"[COMPACT] {run_name} ok={ok} ({time.time() - t0:.1f}s)", flush=True)
                break
    finally:
        proc.stdin.close()
        proc.terminate()
        proc.wait()

    cmd[-1] = (
        "前次运行因达到 50 分钟上限停在收尾阶段。请直接复用当前目录已写好的代码与配音完成最终渲染合并，"
        "写出可播放的 output/final.mp4 并简要汇报，不要再连续读取多张原尺寸大图。"
    )
    with (logs / "events-post50m.jsonl").open("wb") as out_f, (logs / "stderr-post50m.log").open("wb") as err_f:
        r = subprocess.run(cmd, cwd=task, env=ENV, stdin=subprocess.DEVNULL, stdout=out_f, stderr=err_f, timeout=660)
    mp4 = task / "output/final.mp4"
    meta["resumed_after_50m_timeout"] = True
    meta["status"] = "finished_after_resume"
    meta["exit_code"] = r.returncode
    meta["final_bytes"] = mp4.stat().st_size if mp4.is_file() else 0
    run_blind.save(logs / "run.json", meta)
    print(f"[RESUMED_DONE] {run_name} rc={r.returncode} bytes={meta['final_bytes']} ({(time.time() - t0) / 60:.1f}m)", flush=True)


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(compact_and_resume, ["tcp-noskill", "tcp-v090"]))
    subprocess.run([sys.executable, str(Path(__file__).with_name("audit_runs.py")), str(ROOT)], check=True)
    print("[AUDIT_ALL_6_DONE]", flush=True)
