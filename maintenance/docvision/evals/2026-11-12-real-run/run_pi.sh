#!/usr/bin/env bash
# docvision 实测：让 pi 带着技能完成一个真实阅读任务（Windows 本机，Git Bash）。
# 技能用开跑时工作区 docvision/ 的快照（排除本机凭据文件和缓存），技能按名称和描述自然触发。
#
# 用法：bash run_pi.sh <paper|scan> <输入文件> <新的输出目录> [模型，默认 deepseek/deepseek-flash]
# 输出目录放在仓库之外；里面会生成 task/（工作目录）、skill/（技能快照）和 log/（完整记录）。
# 可选 PY_ENV_DIR：放到 PATH 最前面的 Python 环境目录（提供 `python`）。
# 不设 PYTHONNOUSERSITE：本机 MinerU 环境的部分依赖在用户 site-packages 里，设了会让 MinerU 无法启动。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"
KIND="${1:?paper 或 scan}"; INPUT="${2:?需要输入文件}"; OUT="${3:?需要一个新的输出目录}"
MODEL="${4:-deepseek/deepseek-flash}"
case "$KIND" in paper) NAME=paper.pdf ;; scan) NAME=scan.jpg ;; *) echo "第一个参数是 paper 或 scan" >&2; exit 2 ;; esac
[ -e "$OUT/task" ] && { echo "输出目录已有 task/，换一个新目录" >&2; exit 2; }
mkdir -p "$OUT/task" "$OUT/log" "$OUT/skill" || exit 1
cp "$HERE/BRIEF-$KIND.md" "$OUT/task/BRIEF.md" && cp "$HERE/ENV.md" "$OUT/task/" && cp "$INPUT" "$OUT/task/$NAME" || exit 1
tar -C "$ROOT" --exclude=.credentials.env --exclude=__pycache__ -cf - docvision | tar -x -C "$OUT/skill" --strip-components=1 || exit 1
OUT="$(cd "$OUT" && pwd)"
[ -n "${PY_ENV_DIR:-}" ] && export PATH="$PY_ENV_DIR:$PY_ENV_DIR/Scripts:$PY_ENV_DIR/bin:$PATH"
cd "$OUT/task" || exit 1
date -u +%FT%TZ > "$OUT/log/start.txt"
timeout 3600 pi --mode json --no-session --tools read,bash,edit,write \
  --no-context-files --no-skills --no-extensions --no-mcp \
  --skill "$OUT/skill" --model "$MODEL" \
  -- "请阅读当前目录下的 BRIEF.md 和 ENV.md，按要求完成任务。" < /dev/null > "$OUT/log/run.jsonl" 2> "$OUT/log/run.err"
echo "exit=$?" > "$OUT/log/exit.txt"
date -u +%FT%TZ > "$OUT/log/end.txt"
