#!/usr/bin/env bash
# presentation-craft 实测：让 pi 带着技能做一份“实验进展”组会 PPT。
# 技能按名称和描述自然触发，不强制加载；材料与数据是演示用的，不是真实研究结果。
#
# 用法：bash run_pi.sh <新的输出目录> [模型，默认 deepseek/deepseek-flash]
# 输出目录放在仓库之外；里面会生成 task/（成品与中间文件）和 log/（完整记录）。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"
OUT="${1:?需要一个新的输出目录}"
MODEL="${2:-deepseek/deepseek-flash}"
[ -e "$OUT/task" ] && { echo "输出目录已有 task/，换一个新目录" >&2; exit 2; }
mkdir -p "$OUT/task" "$OUT/log" || exit 1
cp -r "$HERE/material.md" "$HERE/data" "$OUT/task/" || exit 1
OUT="$(cd "$OUT" && pwd)"
# 有项目虚拟环境时让 python 指向它（需要 python-pptx、Pillow）
# 项目虚拟环境：Linux/macOS 在 .venv/bin，Windows（Git Bash）在 .venv/Scripts
for V in "$ROOT/.venv/bin" "$ROOT/.venv/Scripts"; do [ -d "$V" ] && export PATH="$V:$PATH"; done
cd "$OUT/task" || exit 1
date -u +%FT%TZ > "$OUT/log/start.txt"
timeout 2700 pi --mode json --no-session --tools read,bash,edit,write \
  --no-context-files --no-skills --no-extensions --no-mcp \
  --skill "$ROOT/presentation-craft" --model "$MODEL" \
  -- "$(cat "$HERE/prompt.txt")" < /dev/null > "$OUT/log/run.jsonl" 2> "$OUT/log/run.err"
echo "exit=$?" > "$OUT/log/exit.txt"
date -u +%FT%TZ > "$OUT/log/end.txt"
