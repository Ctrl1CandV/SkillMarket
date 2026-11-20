"""Acceptance run for video-craft 0.8 and later: one task, one model, in a fresh pi workspace. Python stdlib.

    python run.py mv deepseek/deepseek-flash runs/mv-deepseek
    python run.py promo qwen-token-plan-cn/qwen3.8-flash runs/promo-qwen
    python run.py toyland deepseek/deepseek-flash runs/081-toyland-deepseek
    python run.py opener qwen-token-plan-cn/qwen3.8-flash runs/09-opener-qwen

Copies a snapshot of the skill next to the task, writes REQUEST.md and ENV.md, runs pi unattended and records
the command, the snapshot hashes, the events and the exit status under <out>/log.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
SKILL = HERE.parents[3] / "video-craft"
PY_ENV = Path(os.environ["USERPROFILE"]) / ".conda/envs/videovoice"

BRIEFS = {
    "mv": ("请使用本次提供的 video-craft，为 Mr_Yesterday 的《A Thousand Songs Away》制作完整 MV。"
           "原声是当前目录的 original.mp3，作者在 ccMixter 以 CC BY 3.0 发布；歌词在 lyrics.txt，是作者发布的版本。"
           "保持整首原录音的速度、起止与内容，片尾注明歌名、作者、作词和许可。创意、画面、设计和剪辑由你决定。"
           "交付可播放的 output/final.mp4 和可继续编辑的工程，并简要说明你实际验证过的内容。"),
    "promo": ("请使用本次提供的 video-craft，为一款产品做一支 45–60 秒的宣传片，在社交平台投放。"
              "产品叫「透气」，是一盏放在书桌上的二氧化碳小夜灯：室内二氧化碳浓度升高时，灯从暖白慢慢变成琥珀色，"
              "提醒开窗；开窗后浓度回落，灯再变回暖白。没有 App，不用联网，USB-C 供电，售价 129 元。"
              "主要卖给在家办公、在宿舍学习的人。要有中文旁白和背景音乐。创意、画面、设计和剪辑由你决定。"
              "交付可播放的 output/final.mp4 和可继续编辑的工程，并简要说明你实际验证过的内容。"),
    "toyland": ("请使用本次提供的 video-craft，为《Toyland》这段录音做一段 30–45 秒的 MV 片段：从录音里选一段完整的乐句"
                "（可以是一段主歌接副歌，或整段副歌），起止落在乐句上，不变速。录音是当前目录的 song.mp3，"
                "来源页面的原文（含歌词和作者说明）在 source.txt。片尾署名。创意、画面、设计和剪辑由你决定。"
                "交付可播放的 output/final.mp4 和可继续编辑的工程，并简要说明你实际验证过的内容。"),
    "umbrella": ("请使用本次提供的 video-craft，为一款产品做一支 20–30 秒的短宣传片，在社交平台投放。"
                 "产品叫「带伞」，是挂在门把手上的一块小圆牌：每天早上自己取当地天气预报，当天要下雨就亮蓝色，"
                 "提醒出门带伞；不下雨就不亮。不用 App，不连家里的网络，一节纽扣电池用一年，售价 69 元。"
                 "主要卖给早上赶时间出门的上班族和学生。要有中文旁白和背景音乐。创意、画面、设计和剪辑由你决定。"
                 "交付可播放的 output/final.mp4 和可继续编辑的工程，并简要说明你实际验证过的内容。"),
    "compound": ("请使用本次提供的 video-craft，做一支 20–30 秒的横屏科普短片，在社交平台投放：每天进步 1%，一年后是原来的多少倍；"
                 "每天退步 1%，一年后还剩多少。不需要旁白，要背景音乐和音效，画面上的字要读得完。创意、画面、设计和剪辑由你决定。"
                 "交付可播放的 output/final.mp4 和可继续编辑的工程，并简要说明你实际验证过的内容。"),
    "opener": ("请使用本次提供的 video-craft，为一档播客做一段 10–15 秒的横屏片头。播客叫「慢车」，每期请一位嘉宾讲一段坐慢火车的旅程，"
               "主持人只有一位。要有片头音乐。创意、画面、设计和剪辑由你决定。"
               "交付可播放的 output/final.mp4 和可继续编辑的工程，并简要说明你实际验证过的内容。"),
}
# The request is REQUEST.md, not BRIEF.md: on Windows the task sheet brief.md the skill asks for would overwrite it.
INPUTS = {"mv": {"original.mp3": "inputs/song.mp3", "lyrics.txt": "inputs/lyrics.txt"}, "promo": {},
          "toyland": {"song.mp3": "inputs/toyland/song.mp3", "source.txt": "inputs/toyland/source.txt"}, "umbrella": {}, "compound": {}, "opener": {}}
ENV_TEXT = ("当前目录是独立的工作区，上一层的 video-craft 是本次提供的技能。可在当前目录内制作、渲染与取帧，"
            "任务文件、检查结果与中间产物都放在当前目录。已有 Node、Python、FFmpeg 和 FFprobe；渲染用的浏览器和 "
            "Playwright 已由 VC_CHROME、VC_NODE_MODULES 指好。命令行里的 python 已装 NumPy、Pillow、faster-whisper "
            "和 VoxCPM，转写和配音模型已在本机缓存，不需要联网下载。这次没有人在线回答问题："
            "需要确认的地方自己判断，写进任务单后接着做完。\n")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


# pi lists deepseek-flash with a 1M-token window, so it never compacts, while the API fails ("550, no body")
# at about 256K. A per-run project setting makes pi compact at about 180K instead; --approve lets pi read it.
COMPACT_AT = {"deepseek/deepseek-flash": 180_000}
LISTED_WINDOW = {"deepseek/deepseek-flash": 1_000_000}


def pi_project_settings(task, model):
    """Write task/.pi/settings.json when the model needs an earlier compaction; return the extra pi flags."""
    if model not in COMPACT_AT:
        return []
    settings = {"compaction": {"modelOverrides": {model: {"reserveTokens": LISTED_WINDOW[model] - COMPACT_AT[model]}}}}
    (task / ".pi").mkdir(exist_ok=True)
    save(task / ".pi/settings.json", settings)
    return ["--approve"]


def pi_env():
    env = dict(os.environ)
    env.update(VC_CHROME="C:/Program Files/Google/Chrome/Application/chrome.exe",
               VC_NODE_MODULES=str(Path(os.environ["LOCALAPPDATA"]) / "video-craft-kit"),
               PYTHONNOUSERSITE="1", HF_HUB_OFFLINE="1", PYTHONIOENCODING="utf-8",
               PATH=os.pathsep.join([str(PY_ENV), str(PY_ENV / "Scripts"), str(PY_ENV / "Library/bin"), env["PATH"]]))
    return env


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task", choices=sorted(BRIEFS))
    ap.add_argument("model", help="pi provider/model")
    ap.add_argument("out", type=Path)
    args = ap.parse_args()
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        ap.error("use a fresh, empty output directory")
    task, logs, snapshot = out / "task", out / "log", out / "video-craft"
    task.mkdir(parents=True)
    logs.mkdir()
    shutil.copytree(SKILL, snapshot, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules", ".git"))
    save(logs / "snapshot.json", {p.relative_to(snapshot).as_posix(): digest(p)
                                  for p in sorted(snapshot.rglob("*")) if p.is_file()})
    for name, src in INPUTS[args.task].items():
        shutil.copyfile(HERE / src, task / name)
    (task / "REQUEST.md").write_text(BRIEFS[args.task] + "\n", encoding="utf-8")
    (task / "ENV.md").write_text(ENV_TEXT, encoding="utf-8")

    cli = Path(shutil.which("pi.cmd") or shutil.which("pi")).parent
    entry = cli / "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
    launcher = ["node", str(entry)]
    command = launcher + ["--print", "--offline", "--mode", "json", "--session", str(logs / "session.jsonl"),
                          "--no-context-files", "--no-skills", "--no-extensions", "--no-mcp",
                          "--no-prompt-templates", "--tools", "read,bash,powershell,edit,write",
                          *pi_project_settings(task, args.model),
                          "--skill", str(snapshot), "--model", args.model, "--",
                          "请阅读当前目录的 REQUEST.md 和 ENV.md，完成这次委托。"]
    env = pi_env()
    run = {"task": args.task, "model": args.model, "command": command, "status": "running",
           "start": datetime.now(timezone.utc).isoformat()}
    save(logs / "run.json", run)
    with (logs / "events.jsonl").open("wb") as events, (logs / "stderr.log").open("wb") as errors:
        result = subprocess.run(command, cwd=task, env=env, stdin=subprocess.DEVNULL, stdout=events, stderr=errors)
    final = task / "output/final.mp4"
    run.update(status="finished", exit_code=result.returncode, end=datetime.now(timezone.utc).isoformat(),
               final_bytes=final.stat().st_size if final.is_file() else 0)
    save(logs / "run.json", run)
    print(f"{args.task} {args.model}: exit={result.returncode}, final.mp4={run['final_bytes']} bytes")


if __name__ == "__main__":
    main()
