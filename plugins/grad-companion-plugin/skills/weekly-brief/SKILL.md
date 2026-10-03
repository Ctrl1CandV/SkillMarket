---
name: weekly-brief
description: 研究生周报与组会汇报材料生成：汇总本周 git 提交、实验 run、论文阅读与 claim 变化，产出四段式周报（本周做了什么/结论/下周计划/需要导师拍板的问题）。触发词：周报、组会、组会汇报、导师汇报、本周进展、weekly。只汇总真实记录，不编造进展。
license: MIT
---

# weekly-brief：周报与组会材料

每周雷打不动的机械汇总。输入已经结构化（git log、`.grad/` 台账），本 skill 只做**收集、翻译、组织**，不做任何发挥。

## 铁律

- **每条进展必须可追溯**：标注来源 commit hash、run id 或 `.grad/radar/` 文件名。没有来源的条目不写
- 失败 run 不是“无进展”：单列 OOM/发散/超时及 failure_reason，作为下周止损和导师决策材料；不得把它包装成成功结果
- **不编造进展**。某数据源为空就如实说「本周无」（例如没有 run 时写「本周无新实验记录」），不凑字数
- **AI 整理的笔记不是用户读完**：radar/digest 里的笔记是 AI 辅助阅读产物。周报里它们计入「AI 整理」，只有用户的明确表态（或阅读记录里来源为 user 的已读状态）才能写成读过。存在 `.grad/radar/papers/` 主记录时，「AI 整理过」取 note.generated_at、「用户读完」取 reading.status/last_read_at，两者分开统计
- 数据源缺失（如目录不存在）→ 在周报开头注明哪些数据源不可用，继续处理其余的

## 数据源（按序收集）

时间窗默认最近 7 天（**本期**窗口：宿主当地今天及之前 6 天），用户指定周数/日期则按用户来。

**第 0 步·承诺对账**：`.grad/briefs/` 里存在上一份 brief 时，先跑机械提取。**本期窗口由你明确计算并传入**——prev 只提供待核对计划与问题，脚本不再从上期标题推导本期：

```bash
uv run --no-project "{SKILL_DIR}/scripts/brief_reconcile.py" --prev <上一份brief路径> --repo . \
  --since <本期首日 YYYY-MM-DD> --until <本期末日 YYYY-MM-DD> --json
```

返回 {plan_items, pending_decisions, evidence{commits, new_runs, updated_runs, new_claims}, evidence_status{per_source, overall}, period{since, until, timezone}}。**evidence_status 是每个证据源的诚实度**：`ok`（读取成功，列表内容可信）、`not_present`（该记录源不存在）、`unavailable`（读不了）、`partial`（部分条目损坏被跳过）。据此用词：`unavailable` 的相关条目判「无法核对」（不是没做）；`overall=partial` 时周报必须写明「证据池不完整（哪些条目没读到）」；只有 `ok/complete` 才能把「指不回证据」写成「未找到完成证据」。不带 --since/--until 时默认本期为「今天及之前 6 天」（上期周报是旧周期，不能用它的日期当本期）。返回的 period 与实际时区要如实呈现给用户——让用户能看见查询范围。

然后按条目逐一对账，四种结果各有条件：

- **完成**：证据**直接覆盖承诺内容**才打勾附指针。承诺「完成三组对比实验」而只有搭环境的 commit = 不算完成
- **部分完成**：证据只覆盖承诺的一部分（如三组做完一组）——写明覆盖了哪部分、未覆盖哪部分
- **未找到完成证据**：窗口内指不回覆盖性证据。这只说明证据缺失，不评判用户没做（如实写）
- **无法核对**：数据源本身读不了（非 git 目录、台账缺失等）——标无法核对，**不等于证明用户没有做**

上期拍板问题：**只有存在实际决定记录（用户转述的导师决定、会议记录）才能标「已拍板/解决」**；相关代码提交不能推断导师做了决定。无新决定记录标「仍待拍板」。

```bash
# 1. 代码进展：git log --since="<窗口起点>" --pretty=format:"%h %ad %s" --date=short
#    附 git diff --stat 概览改动面
# 2. 实验记录：列出 .grad/runs/ 下窗口内新增的 run 与本期补录结果的 run（对账脚本的 new_runs/updated_runs），
#    读 meta.json 摘要（方法/benchmark/seed/status/结果或失败原因）；updated_runs 表述为「本期补齐结果」，
#    created_at 与 commit 仍是实验当时的，不能当新实验邀功
# 3. 文献动态：读窗口内 .grad/radar/*.md；优先从 frontmatter 的 papers[] 读取 tier（must_read/skim/archive）/arxiv_id/path，旧文件无头部才回退正文并标记 legacy。
#    存在 .grad/radar/papers/ 主记录时按 paper_id 连接：「本周发现」= 本期简报条目；「AI 整理」= note.generated_at
#    落在窗口内的笔记；「用户读完」= reading.status/last_read_at（用户明确表态）；三者分开计数，同篇一週多次更新笔记按一篇汇总。
#    digest/history/ 旧稿与 *.user.md 批注不是新论文，不计入任何一档
# 4. claim 变化：.grad/claims.jsonl 窗口内新增行（论文主张与 run 的绑定）；读 support/support_by，legacy 行只有旧 status——执行者写的 supported 不当作人的确认
# 5. idea 台账停滞计数：uv run --no-project "{SKILL_DIR}/../idea-ledger/scripts/idea_ledger.py" stagnation --repo . --json
#    （detect-only 纯计数；any_signal=false 时本条跳过，不产出任何段落）
```

`brief_reconcile.py` 与 idea_ledger 是机械提取；汇总与措辞由你（agent）按上面的规则做。

## 四段结构（产出文件）

写到 `.grad/briefs/YYYY-MM-DD.md`（已存在则报冲突，不静默覆盖），同时在回复里给出全文。

```markdown
# 周报 · YYYY-MM-DD ~ YYYY-MM-DD

## 零、上期对账
<!-- 存在上一份 brief 时此段为第一段；全部兑现时可省略但需在开头说明「上期计划全部兑现」 -->
- ✅ <计划条目> —— 兑现（证据覆盖承诺）：<commit 短哈希 / run-id / claim-id>
- ◐ <计划条目> —— 部分完成：<覆盖了哪部分 + 证据>；未覆盖：<缺的部分>
- ❌ <计划条目> —— 未找到完成证据（原因如实写，不包装，也不推断用户没做）
- ⚠️ <计划条目> —— 无法核对：<数据源不可读的具体原因>；这不等于没做
- ⏳ <拍板问题> —— 仍待拍板（只有实际决定记录才能标已决定；代码提交不算导师决定）

## 选题停滞提示（可选）
<!-- 仅当 stagnation 的 any_signal=true 时写这一段：原样列出数字（open 数、最老 open 周龄、距上次 claim/run 天数），措辞只描述事实——是否换向由人裁决 -->
- 最老未收敛方向已 <N> 周；距上次新 claim 事件 <N> 天；距上次 run <N> 天

## 一、本周做了什么
- <条目>（来源：<commit 短哈希> / <run-id> / <radar 文件>）
…

## 二、结论是什么
- 从本周 run/阅读中能站得住的结论，逐条注明依据；没有明确结论就写「本周以调研/搭环境为主，无阶段性结论」
- 本周新增的人的 claim 判定（supported/partial/refuted，注明 support_by 与时间）单列：导师真正拍板过的东西，比代码 commit 更该进周报

## 三、下周计划
- 从本周未完成项与导师反馈推出；不凭空造新目标

## 四、需要导师拍板的问题
<!-- 本段是周报的价值所在，生成规则见下 -->
```

## 「需要导师拍板的问题」生成规则

导师可能不做 Agent 方向，**默认没有背景**。把技术选择翻译成决策语言：

1. 从本周工作中找出真正分叉的决策点（两种以上合理路线的技术选择、需要资源的请求、方向性取舍）
2. 每个问题写成：**背景一句话（给非本方向的人能懂）→ 2-3 个选项 → 每个选项的代价（时间/算力/风险）→ 你倾向哪个、为什么**
3. 控制在 2-3 个问题。没有真分叉就写「本周无需要拍板的事项」，不硬凑

✅ 「评测集选择：(a) 全量 SWE-bench——结论最硬但约需 X 卡时；(b) Lite 子集——快 6 倍但审稿人可能质疑覆盖度。我倾向 (b) 并在 Limitations 说明，请老师定」
❌ 「Transformer 层数怎么选」（没有选项与代价，不是决策问题）

## 可选：组会 PPT 骨架

用户要组会材料时，在周报基础上附 Markdown 大纲（每段一小节、关键数字列点）。渲染成 PPT 交给本机可用的文档处理 skill；没有可用的就只给大纲。

## 错误契约

`brief_reconcile.py` 输出 `{"ok": false, ...}` 时如实转述：`NO_PREV` 说明没有上一份周报（首份周报属正常情况，注明「首份周报，无上期可对账」即可，不算错误）；`BAD_ARGS` 说明日期不合法或窗口反向（until 早于 since），修正后重跑。本期窗口不再依赖 prev 的日期头部——prev 缺日期只影响 prev_date 展示，不影响对账窗口。

## 边界

- 不编造、不夸大（「跑通了」必须有对应 run 记录）
- 不替用户向导师做承诺（下周计划是「计划」，标注置信度）
- 不做 PPT 渲染本身；不发邮件
