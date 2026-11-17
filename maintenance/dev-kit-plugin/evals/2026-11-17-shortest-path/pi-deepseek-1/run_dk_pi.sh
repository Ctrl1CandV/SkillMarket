#!/usr/bin/env bash
# dev-kit 试用：pi + deepseek-flash，多轮对话共用一个会话文件。
# 用法：bash run_dk_pi.sh <输出目录> <第几轮> <这一轮要说的话>
#   第 1 轮会建 task/（课程设计起点）和 skills/（技能快照）。
set -u
OUT="$1"; N="$2"; MSG="$3"
R="/d/Program Project/SkillMarket"
SUB="C:/Users/11487/.pi/agent/npm/node_modules/pi-subagents/bundle/index.js"
if [ "$N" = 1 ]; then
  [ -e "$OUT/task" ] && { echo "已有 task/" >&2; exit 2; }
  mkdir -p "$OUT/task" "$OUT/log" "$OUT/skills" || exit 1
  cp "/d/Program Project/ShortestPathTraffic/任务书.md" "$OUT/task/" || exit 1
  (cd "$OUT/task" && git init -q && git add 任务书.md && git commit -q -m "初始：课程设计任务书") || exit 1
  cp -r "$R"/plugins/dev-kit-plugin/skills/* "$OUT/skills/" && cp -r "$R/frontend-craft" "$R/product-design" "$R/git-governance" "$OUT/skills/" || exit 1
  (cd "$R" && git rev-parse --short HEAD) > "$OUT/log/skills-commit.txt"
fi
OUT="$(cd "$OUT" && pwd)"
SK=(); for d in "$OUT"/skills/*/; do SK+=(--skill "${d%/}"); done
export PATH="/c/Users/11487/.conda/envs/skillmarket:/c/Users/11487/.conda/envs/skillmarket/Scripts:$PATH" PYTHONNOUSERSITE=1
export FC_NODE_MODULES="$LOCALAPPDATA\video-craft-kit\node_modules" FC_CHROME="C:\Program Files\Google\Chrome\Application\chrome.exe"
cd "$OUT/task" || exit 1
date -u +%FT%TZ > "$OUT/log/turn$N.start"
timeout 7200 pi --mode json --session "$OUT/log/session.jsonl" \
  --no-context-files --no-skills --no-extensions -e "$SUB" --no-mcp \
  "${SK[@]}" --model deepseek/deepseek-flash \
  -- "$MSG" < /dev/null > "$OUT/log/turn$N.jsonl" 2> "$OUT/log/turn$N.err"
echo "exit=$?" > "$OUT/log/turn$N.exit"
date -u +%FT%TZ > "$OUT/log/turn$N.end"
