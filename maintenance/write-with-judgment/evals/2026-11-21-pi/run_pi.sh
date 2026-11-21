#!/usr/bin/env bash
# write-with-judgment 1.0.0 对照试跑：用 pi 的 JSON 模式跑 4 题 × 3 组（A 无技能；B 旧版 0.2.1；C 新版 1.0.0）。
# 所有组只开放 read 工具，技能按名称与描述自然触发（不加 /skill: 强制前缀）。
# 用法：bash run_pi.sh [模型名，默认 deepseek/deepseek-flash] [标签，默认 deepseek-flash]
set -u
export PATH="/c/Users/11487/AppData/Roaming/npm:$PATH"
MODEL="${1:-deepseek/deepseek-flash}"
TAG="${2:-deepseek-flash}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"
OLD_SKILL="$ROOT/maintenance/write-with-judgment/archive/0.2.1"
NEW_SKILL="$ROOT/write-with-judgment"
EXTRACT="$ROOT/maintenance/readable-reply/evals/extract.py"
PY="/c/Users/11487/.conda/envs/skillmarket/python.exe"
[ -x "$PY" ] || PY="python3"
RAW="$HERE/raw"
mkdir -p "$RAW"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

to_native() {
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -m "$1"
  else
    printf '%s' "$1"
  fi
}

# 为旧版技能准备临时同名目录 write-with-judgment，确保技能名与触发条件一致
OLD_WRAP="$WORK/old_skill_wrap/write-with-judgment"
mkdir -p "$OLD_WRAP"
cp -r "$OLD_SKILL"/* "$OLD_WRAP"/

OLD_WRAP_NATIVE="$(to_native "$OLD_WRAP")"
NEW_SKILL_NATIVE="$(to_native "$NEW_SKILL")"
EXTRACT_NATIVE="$(to_native "$EXTRACT")"

COMMON=(--mode json --no-session --tools read --no-context-files --no-skills --no-extensions --no-mcp --model "$MODEL")

{
  echo "date: $(date -Iseconds)"
  echo "model: $MODEL"
  echo "pi: $(pi --version 2>&1 | head -1)"
  echo "old_skill: $OLD_WRAP_NATIVE (0.2.1)"
  echo "new_skill: $NEW_SKILL_NATIVE (1.0.0)"
} > "$RAW/_meta-$TAG.txt"

RUN_DIR="$WORK/run"
mkdir -p "$RUN_DIR"
cd "$RUN_DIR" || exit 1

for P in "$HERE"/prompts/${FILTER:-*}.txt; do
  N="$(basename "$P" .txt)"
  PROMPT="$(cat "$P")"
  for G in ${GROUPS:-A B C}; do
    OUT="$RAW/$TAG-$N-$G.md"
    OUT_NATIVE="$(to_native "$OUT")"
    JSONL_NATIVE="$(to_native "${OUT%.md}.jsonl")"
    TOOLS_NATIVE="$(to_native "${OUT%.md}.tools.txt")"
    case "$G" in
      A) EXTRA=() ;;
      B) EXTRA=(--skill "$OLD_WRAP_NATIVE") ;;
      C) EXTRA=(--skill "$NEW_SKILL_NATIVE") ;;
    esac
    echo ">> [write-with-judgment] $TAG $N $G"
    timeout 300 pi "${COMMON[@]}" "${EXTRA[@]}" -- "$PROMPT" < /dev/null > "${OUT%.md}.jsonl" 2> "$OUT.err"
    rc=$?
    PYTHONNOUSERSITE=1 "$PY" -I "$EXTRACT_NATIVE" "$JSONL_NATIVE" "$OUT_NATIVE" "$TOOLS_NATIVE"
    echo "   exit=$rc bytes=$(wc -c < "$OUT") tools=$(grep -c . "${OUT%.md}.tools.txt" || true)"
  done
done
echo "完成。原文在 $RAW"
