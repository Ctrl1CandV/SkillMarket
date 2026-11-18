#!/usr/bin/env bash
# 画面质量的基线对照：同一道“报修处理台”题，S 带 frontend-craft 和 product-design（仓库当前文件），N 不带任何技能。
# 技能按名称和描述自然触发，提示词不点名。
# 用法：bash run_pi.sh <S|N> <新的输出目录> [模型，默认 openai/gpt-6.1-sol]
# 输出目录放在仓库之外。需要：FC_NODE_MODULES、FC_CHROME（两组都给，N 组也可以自己截图）。
# 运行期间不要改这个脚本。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../../../.." && pwd)"
ARM="$1"; OUT="$2"; MODEL="${3:-openai/gpt-6.1-sol}"
[ -e "$OUT/task" ] && { echo "已有 task/" >&2; exit 2; }
: "${FC_NODE_MODULES:?}" "${FC_CHROME:?}"
mkdir -p "$OUT/task" "$OUT/log" "$OUT/skills" || exit 1
cp "$HERE/BRIEF.md" "$HERE/ENV.md" "$OUT/task/" && cp -r "$HERE/data" "$OUT/task/" || exit 1
SK=()
if [ "$ARM" = S ]; then
  cp -r "$ROOT/frontend-craft" "$OUT/skills/frontend-craft" && cp -r "$ROOT/product-design" "$OUT/skills/product-design" || exit 1
  SK=(--skill "$OUT/skills/frontend-craft" --skill "$OUT/skills/product-design")
fi
(cd "$ROOT" && git rev-parse --short HEAD) > "$OUT/log/repo-commit.txt"
OUT="$(cd "$OUT" && pwd)"
export FC_NODE_MODULES FC_CHROME PYTHONNOUSERSITE=1
cd "$OUT/task" || exit 1
date -u +%FT%TZ > "$OUT/log/start.txt"
timeout 7200 pi --mode json --no-session --tools read,bash,edit,write \
  --no-context-files --no-skills --no-extensions --no-mcp \
  "${SK[@]}" --model "$MODEL" \
  -- "请阅读当前目录下的 BRIEF.md 和 ENV.md，按要求完成任务。" < /dev/null > "$OUT/log/run.jsonl" 2> "$OUT/log/run.err"
echo "exit=$?" > "$OUT/log/exit.txt"; date -u +%FT%TZ > "$OUT/log/end.txt"
