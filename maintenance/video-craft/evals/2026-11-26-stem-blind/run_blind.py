"""Three-way unattended blind evaluation runner for video-craft STEM lessons (No-Skill vs 0.9.0 vs 1.0.0).

Usage:
    python run_blind.py <problem: snell|tcp> <arm: noskill|v090|v100> <model> <out_dir>

All runtime workspaces & outputs live outside the git repository (e.g. %LOCALAPPDATA%/vc-eval/2026-11-26-stem/).
Prompt in REQUEST.md is 100% identical across all three arms and never names any skill or internal tool.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
SKILL_V100 = REPO_ROOT / "video-craft"
PY_ENV = Path(os.environ["USERPROFILE"]) / ".conda/envs/videovoice"

PROBLEMS = {
    "snell": (
        "请为正在学习《高等数学》与《大学物理》的大学生制作一段 50–80 秒的横屏（1920×1080，30 fps）课程例题精讲视频，"
        "讲透「费马最短时间原理推导光的折射定律（Snell's Law）」。\n\n"
        "题设：光从空气中的点 A(0, 4) 射向水面 y = 0 进入水中，到达水下点 B(10, -3)（单位：米，水平总跨度 d = 10 m，"
        "h₁ = 4 m，h₂ = 3 m）。光在空气与水中的传播速度之比为 v₁ : v₂ = 4 : 3（相对折射率 n = 4/3）。\n"
        "请讲清核心直觉反差与完整推导：为什么连接 A、B 的直线路径并不是耗时最短的路径？设入水点为 P(x, 0)，"
        "总传播时间函数 T(x) 如何随 x 变化、对 x 求导令 dT/dx = 0 如何自然导出几何正弦比等于波速比 "
        "sin θ₁ / v₁ = sin θ₂ / v₂（并算出本题精确极值入水点或角度关系）？\n\n"
        "要求配有自然的中文讲解配音，画面、数学公式、几何光线与函数图像动画及节奏由你自主设计。"
        "交付可直接播放的 output/final.mp4 和可继续编辑的工程，并在回复中简要说明你实际验证过的内容。"
    ),
    "tcp": (
        "请为备考计算机 408《计算机网络》的学生制作一段 50–80 秒的横屏（1920×1080，30 fps）核心机制与例题精讲视频，"
        "讲透「TCP 拥塞窗口 cwnd 的演化规律与两种丢包响应的本质差异」。\n\n"
        "题设案例：设连接初始慢启动阈值 ssthresh = 8（单位 MSS），拥塞窗口 cwnd 从 1 出发：\n"
        "1. 慢启动阶段每经过 1 个 RTT 指数翻倍直至到达 ssthresh = 8；\n"
        "2. 转入拥塞避免阶段线性加 1，增长到 cwnd = 12 时收到「3 个重复 ACK」（触发快重传与快恢复：ssthresh 与 cwnd 调整为 6 后继续线性增长）；\n"
        "3. 随后增长到 cwnd = 9 时发生「重传计时器超时（Timeout）」（ssthresh 更新为 4，cwnd 直接降回 1 重新慢启动）。\n"
        "请把每个 RTT 轮次的精确数值算对画准，并讲透核心考点：为什么同样怀疑丢包，收到 3 个重复 ACK 只把窗口减半，"
        "而超时却把 cwnd 一棒子打回 1？\n\n"
        "要求配有自然的中文讲解配音，画面、公式/状态流转、cwnd-RTT 动态曲线与节奏由你自主设计。"
        "交付可直接播放的 output/final.mp4 和可继续编辑的工程，并在回复中简要说明你实际验证过的内容。"
    ),
}

ENV_SKILL = (
    "当前目录是独立的工作区，上一层的 video-craft 是可用的技能目录。可在当前目录内制作、渲染与取帧，"
    "任务文件、检查结果与中间产物都放在当前目录。已有 Node、Python、FFmpeg 和 FFprobe；渲染用的浏览器和 "
    "Playwright 已由 VC_CHROME、VC_NODE_MODULES 指好。命令行里的 python 已装 NumPy、Pillow、faster-whisper "
    "和 VoxCPM（PATH 中亦有 edge-tts），转写和配音模型已在本机缓存，不需要联网下载。"
    "这次没有人在线回答问题：需要确认的地方自己判断，写进任务单后接着做完。\n"
)

ENV_NOSKILL = (
    "当前目录是独立的工作区。可在当前目录内制作、渲染与取帧，任务文件、检查结果与中间产物都放在当前目录。"
    "已有 Node、Python、FFmpeg 和 FFprobe；无头浏览器 Chrome 路径在环境变量 VC_CHROME 中，"
    "playwright-core 安装在环境变量 VC_NODE_MODULES 指向的目录（可用 createRequire 从 VC_NODE_MODULES 加载）。"
    "命令行里的 python 已装 NumPy、Pillow、faster-whisper 和 VoxCPM，系统 PATH 中亦有 edge-tts 命令行工具，"
    "模型已在本机缓存，不需要联网安装新包。你看不到也听不到视频，检查画面时可截图或抽帧再用读文件工具查看。"
    "这次没有人在线回答问题：需要确认的地方自己判断并直接做完交付。\n"
)

COMPACT_AT = {"deepseek/deepseek-flash": 180_000}
LISTED_WINDOW = {"deepseek/deepseek-flash": 1_000_000}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def export_v090_snapshot(dest: Path):
    """Export exact 0.9.0 video-craft directory from git HEAD on dev before 1.0.0 commit."""
    raw = subprocess.check_output(["git", "archive", "--format=tar", "HEAD", "video-craft"], cwd=REPO_ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tar:
        tar.extractall(path=dest.parent)
    ver_line = ""
    for line in (dest / "SKILL.md").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("version:"):
            ver_line = line.strip()
            break
    if "0.9.0" not in ver_line:
        raise RuntimeError(f"Expected 0.9.0 in HEAD:video-craft/SKILL.md, got: {ver_line!r}")


def pi_project_settings(task: Path, model: str):
    if model not in COMPACT_AT:
        return []
    settings = {"compaction": {"modelOverrides": {model: {"reserveTokens": LISTED_WINDOW[model] - COMPACT_AT[model]}}}}
    (task / ".pi").mkdir(exist_ok=True)
    save(task / ".pi/settings.json", settings)
    return ["--approve"]


def pi_env():
    env = dict(os.environ)
    node_mods = str(Path(os.environ["LOCALAPPDATA"]) / "video-craft-kit")
    env.update(
        VC_CHROME="C:/Program Files/Google/Chrome/Application/chrome.exe",
        VC_NODE_MODULES=node_mods,
        NODE_PATH=str(Path(node_mods) / "node_modules"),
        VC_PYTHON=str(PY_ENV / "python.exe"),
        PYTHONNOUSERSITE="1",
        HF_HUB_OFFLINE="1",
        PYTHONIOENCODING="utf-8",
        PATH=os.pathsep.join([
            str(PY_ENV),
            str(PY_ENV / "Scripts"),
            str(PY_ENV / "Library/bin"),
            env.get("PATH", ""),
        ]),
    )
    return env


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("problem", choices=sorted(PROBLEMS))
    ap.add_argument("arm", choices=["noskill", "v090", "v100", "v110"])
    ap.add_argument("model", help="e.g. openai/gpt-6.1-sol or deepseek/deepseek-flash")
    ap.add_argument("out", type=Path)
    args = ap.parse_args()

    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        ap.error(f"Output directory is not empty: {out}")
    task, logs = out / "task", out / "log"
    task.mkdir(parents=True)
    logs.mkdir()

    skill_flags = []
    if args.arm == "v090":
        snapshot = out / "video-craft"
        export_v090_snapshot(snapshot)
        skill_flags = ["--skill", str(snapshot)]
        save(logs / "snapshot.json", {p.relative_to(snapshot).as_posix(): digest(p) for p in sorted(snapshot.rglob("*")) if p.is_file()})
        (task / "ENV.md").write_text(ENV_SKILL, encoding="utf-8")
    elif args.arm in ("v100", "v110"):
        snapshot = out / "video-craft"
        shutil.copytree(SKILL_V100, snapshot, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules", ".git"))
        skill_flags = ["--skill", str(snapshot)]
        save(logs / "snapshot.json", {p.relative_to(snapshot).as_posix(): digest(p) for p in sorted(snapshot.rglob("*")) if p.is_file()})
        (task / "ENV.md").write_text(ENV_SKILL, encoding="utf-8")
    else:
        (task / "ENV.md").write_text(ENV_NOSKILL, encoding="utf-8")

    (task / "REQUEST.md").write_text(PROBLEMS[args.problem] + "\n", encoding="utf-8")

    cli = Path(shutil.which("pi.cmd") or shutil.which("pi")).parent
    entry = cli / "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
    command = [
        "node", str(entry),
        "--print", "--offline", "--mode", "json",
        "--session", str(logs / "session.jsonl"),
        "--no-context-files", "--no-skills", "--no-extensions", "--no-mcp", "--no-prompt-templates",
        "--tools", "read,bash,powershell,edit,write",
        *pi_project_settings(task, args.model),
        *skill_flags,
        "--model", args.model,
        "--",
        "请阅读当前目录的 REQUEST.md 和 ENV.md，完成这次委托。",
    ]

    env = pi_env()
    meta = {
        "problem": args.problem,
        "arm": args.arm,
        "model": args.model,
        "command": command,
        "status": "running",
        "start": datetime.now(timezone.utc).isoformat(),
    }
    save(logs / "run.json", meta)
    with (logs / "events.jsonl").open("wb") as events, (logs / "stderr.log").open("wb") as errors:
        result = subprocess.run(command, cwd=task, env=env, stdin=subprocess.DEVNULL, stdout=events, stderr=errors)

    final = task / "output/final.mp4"
    # Automatic 1-time session resume on transient API transport disconnect before delivery
    if not final.is_file() and (logs / "session.jsonl").is_file():
        resume_cmd = command[:]
        resume_cmd[-1] = (
            "上次运行尚未写出 output/final.mp4（可能连接中断或提前停止）。请在当前会话继续已完成的工作，"
            "完成渲染与检查，确保交付可播放的 output/final.mp4。"
        )
        with (logs / "events-resume.jsonl").open("wb") as ev2, (logs / "stderr-resume.log").open("wb") as err2:
            r2 = subprocess.run(resume_cmd, cwd=task, env=env, stdin=subprocess.DEVNULL, stdout=ev2, stderr=err2)
        result = r2
        meta["resumed"] = True

    meta.update(
        status="finished",
        exit_code=result.returncode,
        end=datetime.now(timezone.utc).isoformat(),
        final_bytes=final.stat().st_size if final.is_file() else 0,
    )
    save(logs / "run.json", meta)
    print(f"[{args.problem} | {args.arm} | {args.model}] exit={result.returncode}, final.mp4={meta['final_bytes']} bytes", flush=True)


if __name__ == "__main__":
    main()
