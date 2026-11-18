#!/usr/bin/env bash
# 系统题的画面对照：同一道题，N 不带技能，S7 带 frontend-craft 0.7.0，S8 带 0.8.0（都连同 product-design）。
# 技能取自固定的仓库提交，免得运行中途被改；技能按名称和描述自然触发，提示词不点名。
# 用法：bash run_pi.sh <clubs|lab|papers> <N|S7|S8|S9...> <新的输出目录> [模型，默认 openai/gpt-6.1-sol]
# 新版本的技能要对照时，在下面的 commit_of 里加一行。输出目录放在仓库之外。运行期间不要改这个脚本。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../../../.." && pwd)"
TASK="$1"; ARM="$2"; OUT="$3"; MODEL="${4:-openai/gpt-6.1-sol}"
commit_of() { case "$1" in S7) echo 04ea1c4 ;; S8) echo d1a61b6 ;; S9) echo 27ccaee ;; *) echo "" ;; esac; }
[ -d "$HERE/$TASK" ] || { echo "没有这道题：$TASK" >&2; exit 2; }
[ -e "$OUT/task" ] && { echo "已有 task/" >&2; exit 2; }
: "${FC_NODE_MODULES:?}" "${FC_CHROME:?}"
mkdir -p "$OUT/task" "$OUT/log" "$OUT/skills" || exit 1
cp "$HERE/$TASK/BRIEF.md" "$HERE/ENV.md" "$OUT/task/" && cp -r "$HERE/$TASK/data" "$OUT/task/" || exit 1
SK=()
if [ "$ARM" != N ]; then
  C="$(commit_of "$ARM")"; [ -n "$C" ] || { echo "不认识的组：$ARM" >&2; exit 2; }
  git -C "$ROOT" archive "$C" frontend-craft product-design | tar -x -C "$OUT/skills" || exit 1
  echo "$C" > "$OUT/log/skills-commit.txt"
  SK=(--skill "$OUT/skills/frontend-craft" --skill "$OUT/skills/product-design")
fi
OUT="$(cd "$OUT" && pwd)"
export FC_NODE_MODULES FC_CHROME PYTHONNOUSERSITE=1
cd "$OUT/task" || exit 1
date -u +%FT%TZ > "$OUT/log/start.txt"
timeout 7200 pi --mode json --no-session --tools read,bash,edit,write \
  --no-context-files --no-skills --no-extensions --no-mcp \
  "${SK[@]}" --model "$MODEL" \
  -- "请阅读当前目录下的 BRIEF.md 和 ENV.md，按要求完成任务。" < /dev/null > "$OUT/log/run.jsonl" 2> "$OUT/log/run.err"
echo "exit=$?" > "$OUT/log/exit.txt"; date -u +%FT%TZ > "$OUT/log/end.txt"
