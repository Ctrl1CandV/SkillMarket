#!/usr/bin/env bash
# imagecraft 行为实测：让 pi 带着技能做一个出图任务，看它怎样判断硬件、选路线和交付。
# 用法：bash run_pi.sh <cover|architecture> <仓库外的新目录> [模型，默认 deepseek/deepseek-flash]
# 会调用模型并产生费用；成品与日志写在输出目录，不进仓库。
# 技能用开跑时的快照（输出目录下的 skill/），免得运行中途被改。
# 可选 PY_ENV_DIR：放到 PATH 最前面的 Python 环境目录（Windows 上 `python` 默认是应用商店的占位程序）。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
TASK="${1:?cover 或 architecture}"; OUT="${2:?需要一个新的输出目录}"; MODEL="${3:-deepseek/deepseek-flash}"
[ -f "$HERE/$TASK/prompt.txt" ] || { echo "没有这个任务：$TASK" >&2; exit 2; }
[ -e "$OUT/task" ] && { echo "输出目录已有 task/，换一个新目录" >&2; exit 2; }
mkdir -p "$OUT/task" "$OUT/log" || exit 1
cp -r "$ROOT/imagecraft" "$OUT/skill" || exit 1
find "$HERE/$TASK" -maxdepth 1 -type f ! -name prompt.txt -exec cp {} "$OUT/task/" \;
OUT="$(cd "$OUT" && pwd)"
# 项目虚拟环境：Linux/macOS 在 .venv/bin，Windows（Git Bash）在 .venv/Scripts
for V in "$ROOT/.venv/bin" "$ROOT/.venv/Scripts"; do [ -d "$V" ] && export PATH="$V:$PATH"; done
[ -n "${PY_ENV_DIR:-}" ] && export PATH="$PY_ENV_DIR:$PY_ENV_DIR/Scripts:$PY_ENV_DIR/bin:$PATH"
cd "$OUT/task" || exit 1
date -u +%FT%TZ > "$OUT/log/start.txt"
timeout 1200 pi --mode json --no-session --tools read,bash,edit,write \
  --no-context-files --no-skills --no-extensions --no-mcp \
  --skill "$OUT/skill" --model "$MODEL" \
  -- "$(cat "$HERE/$TASK/prompt.txt")" < /dev/null > "$OUT/log/run.jsonl" 2> "$OUT/log/run.err"
echo "exit=$?" > "$OUT/log/exit.txt"; date -u +%FT%TZ > "$OUT/log/end.txt"
