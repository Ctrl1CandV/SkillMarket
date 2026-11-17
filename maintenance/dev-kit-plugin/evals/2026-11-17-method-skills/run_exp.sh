#!/usr/bin/env bash
# dev-kit 方法技能实验：pi + deepseek-flash，一次一个实验，提示词里不点技能名。
# 用法：bash run_exp.sh <e1|e2|e3|e4> <新的输出目录>
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../../../.." && pwd)"
X="$1"; OUT="$2"
[ -e "$OUT/task" ] && { echo "已有 task/" >&2; exit 2; }
mkdir -p "$OUT/task" "$OUT/log" "$OUT/skills" || exit 1
cp -r "$ROOT"/plugins/dev-kit-plugin/skills/* "$OUT/skills/" || exit 1
(cd "$ROOT" && git rev-parse --short HEAD) > "$OUT/log/skills-commit.txt"
F="$HERE/fixtures"; T="$OUT/task"
g() { git -C "$T" "$@" >/dev/null; }
case "$X" in
  e1) cp "$F/e1-tdd/需求.md" "$T/"; git -C "$T" init -q; g add -A; g commit -m "需求"
      MSG="按 需求.md 实现地铁票价模块。核心计费逻辑要先写测试再写实现。" ;;
  e2) cp "$F/e2-diagnose/v1/"* "$T/"; git -C "$T" init -q; g add -A; g commit -m "AA 分账：均分到分"
      cp "$F/e2-diagnose/v2/cli.py" "$T/"; g add -A; g commit -m "输出改为两位小数并带单位"
      cp "$F/e2-diagnose/反馈.md" "$T/"
      MSG="看一下 反馈.md 里用户反馈的问题，查清原因并修好。" ;;
  e3) cp "$F/e3-design/"* "$T/"; git -C "$T" init -q; g add -A; g commit -m "图书角现状"
      MSG="看 说明.md。借书流程散在两个调用方里，经常漏步骤。帮我重新设计 library 的借还书接口，给几种方案比较一下，推荐一种。先别改代码，我看完再决定。" ;;
  e4) cp "$F/e4-review/base/"* "$T/"; git -C "$T" init -q -b main; g add -A; g commit -m "订单查询"
      git -C "$T" checkout -q -b feature; cp -r "$F/e4-review/feature/"* "$T/"; g add -A; g commit -m "按客户分页查询订单，导出 CSV"
      MSG="帮我审查 feature 分支相对 main 的改动，只报告，不要改代码。" ;;
  *) echo "未知实验 $X" >&2; exit 2 ;;
esac
MSG="$MSG 我不在，有需要我决定的地方按你的推荐决定，并写明你的决定。"
SK=(); for d in "$OUT"/skills/*/; do SK+=(--skill "${d%/}"); done
export PATH="/c/Users/11487/.conda/envs/skillmarket:/c/Users/11487/.conda/envs/skillmarket/Scripts:$PATH" PYTHONNOUSERSITE=1
cd "$T" || exit 1
date -u +%FT%TZ > "$OUT/log/start.txt"
timeout 3600 pi --mode json --session "$OUT/log/session.jsonl" \
  --no-context-files --no-skills --no-extensions -e "C:/Users/11487/.pi/agent/npm/node_modules/pi-subagents/bundle/index.js" --no-mcp \
  "${SK[@]}" --model deepseek/deepseek-flash -- "$MSG" < /dev/null > "$OUT/log/run.jsonl" 2> "$OUT/log/run.err"
echo "exit=$?" > "$OUT/log/exit.txt"; date -u +%FT%TZ > "$OUT/log/end.txt"
