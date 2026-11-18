#!/usr/bin/env bash
# windows-ops 0.1.0 试用：pi + deepseek-flash，技能按名称和描述自然触发。
# 用法：bash run_pi.sh <新的输出目录>
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../../../.." && pwd)"; OUT="$1"
[ -e "$OUT/task" ] && { echo "已有 task/" >&2; exit 2; }
mkdir -p "$OUT/task/旧版本" "$OUT/log" "$OUT/skills" || exit 1
cp "$HERE/BRIEF.md" "$OUT/task/" && cp "$HERE"/data/*.csv "$OUT/task/" && cp "$HERE"/data/old/* "$OUT/task/旧版本/" || exit 1
cp -r "$ROOT/windows-ops" "$OUT/skills/windows-ops" || exit 1
(cd "$ROOT" && git rev-parse --short HEAD) > "$OUT/log/skills-commit.txt"
OUT="$(cd "$OUT" && pwd)"; export PYTHONNOUSERSITE=1
cd "$OUT/task" || exit 1
date -u +%FT%TZ > "$OUT/log/start.txt"
timeout 3600 pi --mode json --no-session --tools read,bash,edit,write \
  --no-context-files --no-skills --no-extensions --no-mcp \
  --skill "$OUT/skills/windows-ops" --model deepseek/deepseek-flash \
  -- "请阅读当前目录下的 BRIEF.md，按要求完成。" < /dev/null > "$OUT/log/run.jsonl" 2> "$OUT/log/run.err"
echo "exit=$?" > "$OUT/log/exit.txt"; date -u +%FT%TZ > "$OUT/log/end.txt"
