#!/usr/bin/env bash
# video-craft 实测：让 pi 带着技能做一条竖屏数据短片（Windows 本机，Git Bash）。
# 技能用开跑时的快照，免得运行中途被改；技能按名称和描述自然触发。
#
# 用法：bash run_pi.sh <新的输出目录> [模型，默认 openai/gpt-6.1-sol]
# 输出目录放在仓库之外；里面会生成 task/（工作目录）、skill/（技能快照）和 log/（完整记录）。
# 需要的环境变量：VC_NODE_MODULES、VC_CHROME；可选 PY_ENV_DIR（带 numpy、Pillow 的 Python 环境目录）、
# SKILL_SRC（要测的技能目录，默认仓库里的 video-craft；测旧版时用 git archive 导出的目录）。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"
OUT="${1:?需要一个新的输出目录}"
MODEL="${2:-openai/gpt-6.1-sol}"
[ -e "$OUT/task" ] && { echo "输出目录已有 task/，换一个新目录" >&2; exit 2; }
: "${VC_NODE_MODULES:?先设置 VC_NODE_MODULES}" "${VC_CHROME:?先设置 VC_CHROME}"
mkdir -p "$OUT/task" "$OUT/log" || exit 1
cp "$HERE/BRIEF.md" "$HERE/ENV.md" "$OUT/task/" || exit 1
cp -r "${SKILL_SRC:-$ROOT/video-craft}" "$OUT/skill" || exit 1
OUT="$(cd "$OUT" && pwd)"
if [ -n "${PY_ENV_DIR:-}" ]; then
  export PATH="$PY_ENV_DIR:$PY_ENV_DIR/Scripts:$PY_ENV_DIR/bin:$PATH" PYTHONNOUSERSITE=1
fi
export VC_NODE_MODULES VC_CHROME
cd "$OUT/task" || exit 1
date -u +%FT%TZ > "$OUT/log/start.txt"
timeout 7200 pi --mode json --no-session --tools read,bash,edit,write \
  --no-context-files --no-skills --no-extensions --no-mcp \
  --skill "$OUT/skill" --model "$MODEL" \
  -- "请阅读当前目录下的 BRIEF.md 和 ENV.md，按要求完成任务。" < /dev/null > "$OUT/log/run.jsonl" 2> "$OUT/log/run.err"
echo "exit=$?" > "$OUT/log/exit.txt"
date -u +%FT%TZ > "$OUT/log/end.txt"
