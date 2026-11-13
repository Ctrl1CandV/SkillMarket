#!/usr/bin/env bash
# frontend-craft + product-design 实测：让 pi 带着两个技能做快递驿站的柜台工作台和站长周看板（Windows 本机，Git Bash）。
# 两个技能用开跑时的快照，免得运行中途被改；技能按名称和描述自然触发。
#
# 用法：bash run_pi.sh <新的输出目录> [模型，默认 deepseek/deepseek-flash]
# 输出目录放在仓库之外；里面会生成 task/（工作目录）、skills/（技能快照）和 log/（完整记录）。
# 需要的环境变量：FC_NODE_MODULES（playwright-core 所在的 node_modules）、FC_CHROME（本机 Chrome）。
# 可选：PY_ENV_DIR（带 numpy、Pillow 的 Python 环境目录）；FC_SRC、PD_SRC（要测的技能目录，默认仓库里的版本）。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"
OUT="${1:?需要一个新的输出目录}"
MODEL="${2:-deepseek/deepseek-flash}"
[ -e "$OUT/task" ] && { echo "输出目录已有 task/，换一个新目录" >&2; exit 2; }
: "${FC_NODE_MODULES:?先设置 FC_NODE_MODULES}" "${FC_CHROME:?先设置 FC_CHROME}"
mkdir -p "$OUT/task" "$OUT/log" "$OUT/skills" || exit 1
cp "$HERE/BRIEF.md" "$HERE/ENV.md" "$OUT/task/" && cp -r "$HERE/data" "$OUT/task/" || exit 1
cp -r "${FC_SRC:-$ROOT/frontend-craft}" "$OUT/skills/frontend-craft" || exit 1
cp -r "${PD_SRC:-$ROOT/product-design}" "$OUT/skills/product-design" || exit 1
OUT="$(cd "$OUT" && pwd)"
if [ -n "${PY_ENV_DIR:-}" ]; then
  export PATH="$PY_ENV_DIR:$PY_ENV_DIR/Scripts:$PY_ENV_DIR/bin:$PATH" PYTHONNOUSERSITE=1
fi
export FC_NODE_MODULES FC_CHROME
cd "$OUT/task" || exit 1
date -u +%FT%TZ > "$OUT/log/start.txt"
timeout 7200 pi --mode json --no-session --tools read,bash,edit,write \
  --no-context-files --no-skills --no-extensions --no-mcp \
  --skill "$OUT/skills/frontend-craft" --skill "$OUT/skills/product-design" --model "$MODEL" \
  -- "请阅读当前目录下的 BRIEF.md 和 ENV.md，按要求完成任务。" < /dev/null > "$OUT/log/run.jsonl" 2> "$OUT/log/run.err"
echo "exit=$?" > "$OUT/log/exit.txt"
date -u +%FT%TZ > "$OUT/log/end.txt"
