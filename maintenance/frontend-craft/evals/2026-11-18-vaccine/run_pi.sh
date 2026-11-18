#!/usr/bin/env bash
# frontend-craft 0.7.0 对照：A 只带 frontend-craft；B 再加 modern-web-guidance；C 是基线，带上一版 0.6.2（仓库提交 6f0f756）。
# pi + deepseek-flash，技能按名称和描述自然触发。
# 用法：bash run_pi.sh <A|B|C> <新的输出目录>
# 需要：FC_NODE_MODULES、FC_CHROME；B 还需要 %LOCALAPPDATA%/modern-web-guidance/1.0.1（见 maintenance/modern-web-guidance）。
# B 组的技能文件后来移到了 maintenance/modern-web-guidance/skill，下面按新位置复制。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../../../.." && pwd)"
ARM="$1"; OUT="$2"
[ -e "$OUT/task" ] && { echo "已有 task/" >&2; exit 2; }
: "${FC_NODE_MODULES:?}" "${FC_CHROME:?}"
mkdir -p "$OUT/task" "$OUT/log" "$OUT/skills" || exit 1
cp "$HERE/BRIEF.md" "$HERE/ENV.md" "$OUT/task/" || exit 1
if [ "$ARM" = C ]; then git -C "$ROOT" archive 6f0f756 frontend-craft | tar -x -C "$OUT/skills" || exit 1
else cp -r "$ROOT/frontend-craft" "$OUT/skills/frontend-craft" || exit 1; fi
SK=(--skill "$OUT/skills/frontend-craft")
if [ "$ARM" = B ]; then cp -r "$ROOT/maintenance/modern-web-guidance/skill" "$OUT/skills/modern-web-guidance" || exit 1; SK+=(--skill "$OUT/skills/modern-web-guidance"); fi
if [ "$ARM" = C ]; then echo 6f0f756 > "$OUT/log/skills-commit.txt"; else (cd "$ROOT" && git rev-parse --short HEAD) > "$OUT/log/skills-commit.txt"; fi
OUT="$(cd "$OUT" && pwd)"
export FC_NODE_MODULES FC_CHROME PYTHONNOUSERSITE=1
cd "$OUT/task" || exit 1
date -u +%FT%TZ > "$OUT/log/start.txt"
timeout 7200 pi --mode json --no-session --tools read,bash,edit,write \
  --no-context-files --no-skills --no-extensions --no-mcp \
  "${SK[@]}" --model deepseek/deepseek-flash \
  -- "请阅读当前目录下的 BRIEF.md 和 ENV.md，按要求完成任务。" < /dev/null > "$OUT/log/run.jsonl" 2> "$OUT/log/run.err"
echo "exit=$?" > "$OUT/log/exit.txt"; date -u +%FT%TZ > "$OUT/log/end.txt"
