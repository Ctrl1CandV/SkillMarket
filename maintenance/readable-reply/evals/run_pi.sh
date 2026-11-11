#!/usr/bin/env bash
# readable-reply 2.0.0 简洁度对照试跑：用 pi 的 JSON 模式跑 6 题 × 4 组。
# 组别：A 无指令；B 全局短版；C 加载技能（模型自己决定是否读 SKILL.md）；D 强制加载技能（/skill:readable-reply）。
# 所有组只开放 read 工具：技能靠模型用 read 读取才算加载；不开放 bash 等其他工具。
# 用法：bash run_pi.sh <模型匹配串> [标签]
#   例：bash run_pi.sh deepseek       （先用 pi --list-models deepseek 确认名称）
#       bash run_pi.sh gpt
# 在会话里用 `! bash <本文件完整路径> deepseek` 运行。结果写入 raw/，不修改任何技能文件。
set -u
MODEL="${1:?用法: bash run_pi.sh <模型匹配串> [标签]}"
TAG="${2:-$(echo "$MODEL" | tr -c 'A-Za-z0-9' '_')}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$HERE/../../../readable-reply" && pwd)"
RAW="$HERE/raw"
mkdir -p "$RAW"
WORK="$(mktemp -d)"            # 空目录运行，避免读到项目上下文
trap 'rm -rf "$WORK"' EXIT

# 全局指令短版：取 global-instruction.md 里第一个代码块
GI="$(awk '/^```/{n++; next} n==1' "$SKILL_DIR/references/global-instruction.md")"
[ -n "$GI" ] || { echo "取不到全局指令短版" >&2; exit 1; }

COMMON=(--mode json --no-session --tools read --no-context-files --no-skills --no-extensions --no-mcp --model "$MODEL")

{
  echo "date: $(date -Iseconds)"
  echo "model_pattern: $MODEL"
  echo "pi: $(pi --version 2>&1 | head -1)"
  echo "skill_dir: $SKILL_DIR"
} > "$RAW/_meta-$TAG.txt"

cd "$WORK" || exit 1
for P in "$HERE"/prompts/*.txt; do
  N="$(basename "$P" .txt)"
  PROMPT="$(cat "$P")"
  for G in A B C D; do
    OUT="$RAW/$TAG-$N-$G.md"
    case "$G" in
      A) EXTRA=() ;;
      B) EXTRA=(--append-system-prompt "$GI") ;;
      C) EXTRA=(--skill "$SKILL_DIR") ;;
      D) EXTRA=(--skill "$SKILL_DIR"); PROMPT_G="/skill:readable-reply $PROMPT" ;;
    esac
    echo ">> $TAG $N $G"
    timeout 300 pi "${COMMON[@]}" "${EXTRA[@]}" -- "${PROMPT_G:-$PROMPT}" < /dev/null > "${OUT%.md}.jsonl" 2> "$OUT.err"
    rc=$?
    python3 -I "$HERE/extract.py" "${OUT%.md}.jsonl" "$OUT" "${OUT%.md}.tools.txt"
    echo "   exit=$rc bytes=$(wc -c < "$OUT") tools=$(grep -c . "${OUT%.md}.tools.txt")"
    unset PROMPT_G
  done
done
echo "完成。原文在 $RAW ；*.err 是 stderr，空文件可忽略。"
