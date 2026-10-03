---
name: idea-ledger
description: 选题台账与弯路记录：登记候选研究方向、选入/否决流转（killed 必须给方法级否定理由，环境性失败自动警告）、why-not-selected 排序理由显式化、选题停滞计数提醒。触发词：记个想法、idea 台账、这个方向做过了、选题记录、弯路记录、方向否决、停滞检测。只记录不裁决：杀不杀 idea 由人决定。
license: MIT
---

# idea-ledger：选题与弯路台账

半年后回看，「当时为什么没选它」「什么被否证过」比「做成了什么」更稀缺。本 skill 把这类信息变成**只追加的台账**，防重复踩坑。

## 铁律

- **只记录，不裁决**——某个方向该不该杀是人做的判断；脚本输出永远是记录与计数，不是「放弃吧」
- `status=killed` 必须给非空 `--reason`（方法级否定：为什么这个想法本身不成立）；换工具、修配置能解决的属于环境问题，不是 kill 理由
- **防记忆投毒**：「某工具做不到 X」类负面能力断言不写入 text（会被载入后续会话并自我引用）——改记 workaround 或需求

## 路径占位符

`{SKILL_DIR}` 指本 SKILL.md 所在目录的绝对路径，由调用方展开；命令一律加引号；Windows 中文乱码时前置 `PYTHONUTF8=1`。

## 数据契约

`.grad/ideas.jsonl` 只追加，每行：

```json
{"idea_id": "i-001", "text": "<一句话>", "status": "candidate",
 "source": null, "why_not_selected": null, "killed_reason": null, "recorded_at": "..."}
```

同 idea_id **最后一行为当前状态**（latest-wins）；killed → selected 回切合法（历史保留，翻案也是信息）。执行者不得 freehand 写此文件。

## 工作流

```bash
# 登记（text 必填；source 给 arXiv id 或一句话；排序理由显式化）
uv run --no-project "{SKILL_DIR}/scripts/idea_ledger.py" add \
  --text "<一句话方向>" [--source "<arXiv id 或一句话>"] \
  [--why-not-selected "<为什么当下没先选它>"] --json

# 状态流转（killed 必填 --reason；--note 可写流转备注如换向何处）
uv run --no-project "{SKILL_DIR}/scripts/idea_ledger.py" update \
  --id i-001 --status <candidate|selected|killed> [--reason "<…>"] --json

uv run --no-project "{SKILL_DIR}/scripts/idea_ledger.py" list [--json]
```

- add 对未收敛条目（candidate/selected）文本重复会警告；对「做不到 X」式断言也会警告
- update killed 时 reason 命中环境性失败模式 → **只警告不阻断**（原话保留在案），是否坚持由人定

### 停滞计数（detect-only，weekly-brief 消费）

```bash
uv run --no-project "{SKILL_DIR}/scripts/idea_ledger.py" stagnation --repo . --json
```

纯计数输出：未收敛条目数、最老 open 周龄、距上次 claim 事件天数、距上次 run 天数、按窗口（默认 3 周）的三档布尔信号。**只列数字不裁决**；weekly-brief 在有信号时把它作为「选题停滞提示」一行放进周报。

## 错误契约

脚本输出 `{"ok": false, ...}` 时如实转述 error 与 detail。`NOT_FOUND` 会列出已知 idea_id；`BAD_ARGS` 是输入问题（空 text / killed 缺 reason），修正后重跑；离线全程可用。
