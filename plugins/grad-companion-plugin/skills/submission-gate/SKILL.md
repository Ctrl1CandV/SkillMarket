---
name: submission-gate
description: 投稿前机械核对与倒排期：页数/checklist/Limitations/匿名性/related work 位置/LLM 使用披露逐项检查，ICLR/NeurIPS/ICML/ACL 截稿日倒计时与冲突检测，rebuttal 意见分类（ARR 无效批评 H1-H17 与有效弱点 M/T/R/G）。触发词：投稿检查、截稿、deadline、desk reject、页数超了、rebuttal、审稿意见怎么回、投稿前核对。不生成审稿意见，不替你决定投哪里。
license: MIT
---

# submission-gate：投稿前机械核对

违规代价是全损（desk reject / rejected without review），而规则是明文可核对的。本 skill 做核对器：**把判定材料摆出来，判定权在人**。

## 边界（不做什么）

- **不生成审稿意见**——AI 审稿有 hivemind effect 且可被操纵，ARR 规定 LLM 生成审稿可致审稿人自己的投稿被 desk reject。本 skill 只服务作者侧
- **不替用户决定投哪里**——给证据与接收率参照，选择是用户的
- **不编译 PDF**、不修改稿件（指出问题，改不改用户定）
- rebuttal 的**写作方法论**是 `academic-writing` skill 的职责（它有 rebuttal 模式）；若可用则引导走它，本 skill 负责其前的**分类与排序**

## 路径占位符

`{SKILL_DIR}` 指本 SKILL.md 所在目录的绝对路径，由调用方展开。命令一律加引号。Windows 中文乱码时前置 `PYTHONUTF8=1`。

## 流程

### 1. 确定 venue 与规则

从用户参数确定 venue。**先读 `{SKILL_DIR}/references/venues.md`**（规则表 + 逐项核对清单）。venue 不在表里 → 明确说不覆盖、请用户给官方 CFP 链接，不猜规则。

### 2. 截稿日与倒排期

```bash
uv run --no-project "{SKILL_DIR}/scripts/ddl_fetch.py" --venues "ICLR,ACL,NeurIPS" --json
```

- 缓存于 `.grad/cache/ccfddl/`，TTL 7 天，不要更频繁地拉
- 产出：每个会议各年份的 abstract/full 截稿、倒计时（天）、时区
- JSON 的 `timelines` 保留每个 track/round；`name` 来自原始 `comment`，缺失时是稳定的 `timeline-N`。顶层 abstract/full 只是兼容首项摘要，不代表完整生命周期，也不得把 comment 猜成 rebuttal 或 camera-ready
- **倒排期**：对目标 timeline 的 deadline 反推——检查点（T-14d 实验冻结、T-7d 全文成稿、T-3d 逐项核对、T-1d 提交系统试传）。只在数据源实际给出对应窗口时标冲突，缺失信息记 unknown
- 规则会变：**距截稿 2 周内必须提醒用户回官网复核**当前 CFP

### 3. 逐项机械核对（有稿件时）

用户提供 PDF / LaTeX 源码 / 目录，按 venues.md 的八项清单逐项核对。每项输出三态：

- ✅ **已自动核对**（附证据：页数、命中的文本片段）
- ⚠️ **需人工确认**（说明缺什么、怎么查——如边距需与官方模板 diff）
- ❌ **违规**（附依据的规则原文）

数不了的页数不猜；搜不到的 checklist 说没搜到，不默认存在。文件元数据（PDF author 字段）也是匿名性检查的一部分。

### 3.5 judge 使用披露与一致性验证（论文用了 LLM-as-judge 时）

Agent 论文几乎必用 judge。逐项核对：
- ⚠️ **需人工确认**：是否报告了 judge 一致性验证（κ / 一致率 / 与人工的对比协议）。ARR 把「未经验证的 LLM-as-judge」列为方法缺陷首条，没有验证的一致性声明会在 rebuttal 被盯上
- 验证材料在 run-provenance 侧准备（`judge_agreement.py` + `references/judge-protocol.md`）；本 skill 只核对「有没有报」，算数与判定不在这里


### 4. rebuttal 分类（用户拿到审稿意见时）

**先读 `{SKILL_DIR}/references/arr-h-list.md`**。逐条审稿意见归为：

- **可反驳的无效批评**（命中 H1-H17）——引用指南原文要义回应
- **须实证回应的有效弱点**（命中 M/T/R/G）——给数据/补实验/修改承诺
- 中性建议——礼貌采纳

排序服从「AC 只读每个 thread 前两条」：最强的回应放最前。R5（error bar）与 R1（best-of-N）命中时，若本项目有 run-provenance 登记的 run（`.grad/runs/`），直接引用其 mean±std 表作答。

### 5. 投稿策略参照（用户问投哪里时）

给 venues.md 末尾的接收率数据 + Findings 兜底机制 + reciprocal reviewing 新人豁免，注明「这是参照不是建议」。方向与 venue 的匹配（如 ACL 2026 topic 列表含 AI/LLM Agents）只作为事实陈述。

## 错误契约

脚本输出 `{"ok": false, ...}` 时如实转述 error 与 detail。`NETWORK` 失败时说明：缓存里可能还有上次的数据（`.grad/cache/ccfddl/`），可降级读取并标注数据日期。
