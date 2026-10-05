# grad-companion-plugin 优化策略：论文与综述的分析总结

日期：2026-10-04。状态：**方案稿，待用户确认后实施**；本轮未修改 `plugins/grad-companion-plugin/` 任何内容，未提交。

## 结论

插件在"读单篇论文"上闭环完整（协议、三档深度、笔记模板、主记录、降级链、诚实纪律都在），但按最终目标衡量缺两块：**综述没有专用读法**（reading-protocol 里只有表格中的一行），**跨论文综合不存在**（七个技能没有一个做"多篇放在一起"）。这两块正好对应 ResearchWorkbench 自认的缺口：三个综述阅读包全部 `state: partial`，知识脉络图的边几乎全是"整理排定"而非真实引用。方案按四个方向推进，P0 是综述协议和跨论文综合，单篇阅读只做小改，检索边界不动。

## 1. 最终目标与依据

- 用户目标（2026-10-04 原话归纳）：平台不仅是筛选论文、根据关键词给出论文和综述，还要进行论文和综述的分析和总结；优化可参考顶尖高校开源的科研项目。
- 载体是 ResearchWorkbench（只读调研结论见 §3 与 §7）。该平台的 AGENTS.md 写明"grad-companion 的阅读、每日发现等既有技能应优先复用"，README 写明"精选允许在 harness 中更新项目内容，网页展示整理结果"——**平台把本插件当作内容生产者**。插件产出什么形状，平台就得消化什么形状；反过来平台契约要求什么，插件就该供给什么。
- 平台输入契约三类：`docs/READING-TEMPLATES-005.md` 阅读卡（lead/learner/questions/guidedReading/coverage/auditRef，`references[].relation` 强制区分 citation 与 editorial）、`public/content/surveys.js` 综述阅读包（units + topicMap + coverage + readingPaths + edition sha256）、`docs/DAILY-BRIEF-006.md` 简报（检索/收获/边界三段）。

## 2. 现状对照

| 能力 | 插件现状（main 分支实测文件） | 与最终目标的差距 |
|---|---|---|
| 单篇阅读 | grad-radar 完整：§0 路由、三档深度、六类型重点、保存冲突保护、AI/人状态分离 | 基底可复用；standard/deep 缺"读前提问"环节；deep 的逐条主张锚点只是模板里的建议句 |
| 综述处理 | reading-protocol §4 一行（"范围、分类图、核心分支、代表工作"）；tiering 默认把 survey 列为速览信号 | 没有协议：章节取舍、问题地图构建、原文与图表核验、开放问题提取、当作入口的读完动作都没有 |
| 跨论文综合 | 无 | 平台知识脉络图 20 节点多数只核对过摘要与元数据、19 条边只有 2 对真实引用；directions 的 openQuestions 无机制供给 |
| 积累层 | idea-ledger 只管选题；run-provenance 只管实验与 claim | 概念、术语、方法没有台账；平台个人笔记每篇只有一个自由文本字段 |
| 发现 | 每日漏斗元数据级；明确"不做系统性文献检索" | 边界维持。用户本轮强调的增量在分析与总结，不在检索 |

## 3. 平台侧证据（缺口是平台自己承认的）

以下均出自平台文件（路径见 §7）：

1. 深度金字塔倒挂：约 50 张论文卡里 deep 只有约 1 张，多数只做了 HTML/文字层部分核验（papers-collab.js 头注、SPEC.md）。
2. 三个综述阅读包全部 `state: partial`，表格普遍带"列值依文字层转录，表格视觉排布及脚注仍待 PDF 核查"类警告（surveys.js）。
3. 知识脉络图自述："除 TOSEM 与 CAMERA 两处外，论文之间的相邻关系都是整理时排定的阅读顺序，不是论文之间真实的引用关系"（library-content.js:38）。
4. 论文搜索只是标题/导语的子串过滤，`/api/discover` 按设计不支持自由检索（SURVEY-013 §2 把它列为缺陷）。
5. 个人笔记无结构：每篇一个 question 一个 note，无引文、无证据链接、无按节积累（notes.js）。
6. 每日精选停更，条目只依据摘要（READING-014 README、briefs.js）。

关键对齐点：平台 `#/surveys` 页的"为其他主题生成综述阅读任务"表单输出的提示词，实际上就是综述协议的**验收标准**——固定版本身份、核全文/图表/附录、章节取舍、连贯中文讲解带章节页码定位、区分作者原意/编辑联系/自编例子、如实标注未核验、不假装读过被引文献。插件侧协议照这八条设计即可两端一致。

## 4. 开源参考与可借机制（2026-10-04 核验）

先说核查结论：**没有找到任何高校官方发布 SKILL.md 格式的科研技能**（GitHub 与 web 检索）；高校贡献集中在框架与课程方法论层面。最接近"科研技能合集"的是公司维护的 K-Dense scientific-agent-skills（MIT，47.5k stars，约 177 个技能，含 literature-review、peer-review、paperclip 等），属次要参考。另有两处常见说法需要修正：OpenScholar 出自 Allen AI + 华盛顿大学（常被误传为 Harvard）；CS197 是哈佛 Pranav Rajpurkar 的课程（不是斯坦福 Percy Liang）。

| # | 项目 | 出处 / 许可 | 可借机制 | 落到插件哪里 |
|---|---|---|---|---|
| 1 | PaperQA2 | FutureHouse / Apache-2.0，最活跃 | 每块文本先"相对当前问题打分+语境化摘要"再综合；主张必须带页码引文（`Author2024 pages 3-4` 式）；专门的跨论文矛盾检测 pass | 综述协议与综合技能的证据规则；单篇 deep 的证据小节 |
| 2 | STORM / Co-STORM | Stanford OVAL / MIT | 多视角提问先行（不同 persona 的问题清单驱动检索与写作）；大纲驱动成文；思维导图→报告 | 单篇读前提问；综合技能"先大纲后成文" |
| 3 | OpenScholar | Allen AI + UW / Apache-2.0 | 自反馈循环显式"补证据"；逐主张回查引用真实性（其指标 Citation F1：GPT-4o 裸写 80–95% 引用有问题，加循环后 0.1→39.5）；综合时单篇来源配额防一家独大 | 综合技能的核验 pass 与配额规则 |
| 4 | CS197 课程书 | Harvard（Rajpurkar）/ 免费课程材料 | 笔记骨架 contributions/question/setup/findings/limitations；跨笔记找 gap（问题缺口/设置缺口/发现缺口） | 综合技能的缺口发现节；与现有 note-templates §4/§5 互补 |
| 5 | LLMxMapReduce-V2 | 清华 thunlp / Apache-2.0 | 多文档 map-reduce 分块综合（超出上下文时）、大纲驱动、critique-revise；附 SurveyEval 评测维度 | 综述/多篇综合的作业顺序 |
| 6 | ResearchAgent | KAIST，NAACL 2025，无官方仓库（paper-only） | 从种子论文抽取 problem/method/finding 实体建关系图 | 综合输出的脉络字段设计 |
| 7 | AutoSurvey | Westlake 等 / 无 LICENSE 文件 | LLM 自评四维：单篇覆盖/结构/相关性 + 跨节一致性 | 综合产出的自查清单（只借思想） |

许可红线：gpt_academic（GPL-3.0）、ChatPaper（CC BY-NC-ND）、CycleResearcher（自定义注册许可）、AI-Researcher（无 LICENSE）——一律只借思想，不复制文字与提示词原文。

## 5. 优化方案

### 方向 A（P0）：综述阅读协议 —— grad-radar 新增 `references/survey-protocol.md`

- 内容：综述作为"入口"而非"目的地"的读法；章节取舍规则；问题地图/分类树构建；每节三分标注（作者原意 / 编辑联系 / 自编例子）带章节页码；图表核验与 limitations 如实记录；开放问题与代表作提取；"读完一篇综述的交付物是下一步阅读计划"。
- 产出物：`.grad/radar/surveys/<survey_id>.md` 阅读包，frontmatter 记 edition（版本/sha256/页数）与 coverage（已核读/已讲解/未覆盖），单元块类型对齐平台 surveys.js（source-explanation / editorial-connection / teaching-example）。
- 验收标准直接采用平台任务表单八条（§3 末）。
- 联动小改：reading-protocol §4 survey 行与 tiering 速览信号改为指向该协议；SKILL.md description 增加"综述精读、综述阅读包、问题地图"类触发词。
- **不加新脚本**：阅读包是 markdown 契约，主记录复用现有 register/save-note；脚本化等出现机械需求再说。

### 方向 B（P0）：跨论文综合 —— 新技能 `synthesis`（暂名）+ `commands/synth.md`

- 输入：`.grad/radar/papers/` 主记录与已有笔记 + 用户指定的主题或论文集。
- 流程：收集材料并逐篇标注 basis（**只据摘要的不得冒充读过正文**）→ 视角提问（STORM）→ 先大纲后成文（对比维度/发展脉络/方法分类）→ 逐主张写作带出处，回查引用真实性并设单篇来源配额（OpenScholar）→ 矛盾检测 pass（PaperQA2）→ 缺口发现（CS197 三类 gap）→ 四维自查（AutoSurvey）。
- 产出：`.grad/synthesis/<topic>.md`：对比表、脉络（真实引用关系标 citation，整理排定的阅读顺序标 editorial——直接对应平台 PF-07）、矛盾与未决、开放问题、下一步阅读计划。
- 铁律沿用：每条结论可反驳、basis 如实、AI 综合不等于用户结论；不自动进入平台内容库（平台侧有自己的审核引入流程）。

### 方向 C（P1）：单篇阅读小改 —— note-templates + reading-protocol

- standard/deep 动笔前先生成 2—3 个"读者视角问题"（入门者/复现者/审稿人按任务取用），笔记必须回答并落在"问题"位置——平台卡片本来就有 `questions[]` 字段，插件此前不生产它。
- deep 的"结论靠什么支撑"节：每条主张带章节/页锚点（模板现仅要求"关键结论附近放来源指针"，升格为逐条要求）。
- quick 与每日漏斗不动。

### 方向 D（P2，可选）：概念/方法台账

- `.grad/ledger/concepts.jsonl`：术语、定义、出处、关联论文，为平台 foundations/知识地图供给原料。需要新脚本（追加/去重），等 A/B 落地后按真实需要决定是否值得。

### 不做什么

- 不做系统性文献检索（grad-radar 边界维持；literature-search 若可用照旧引导）。
- 不把平台专属字段名写进插件——插件保持通用，平台侧映射由平台文档（READING-TEMPLATES-005 §6）承担。
- 不引外部服务、不加向量检索；run-provenance / weekly-brief / submission-gate / thesis-cn / career-bridge 本轮不动。

## 6. 实施与验证顺序（确认后执行）

1. 方向 A：写 `survey-protocol.md` + grad-radar 三处引用改动 → 静态检查（链接、结构、`{SKILL_DIR}` 用法）→ 合成综述试运行，验证三分标注、basis 降级、未核验标注的实际行为。
2. 方向 B：写 synthesis 技能与命令 → 合成数据试运行（3 篇合成笔记 → 综合产出），检查每条主张的出处可指回、矛盾检测产生真实锚点、basis 标注诚实。
3. 真实试用：用户挑一篇综述 + 一组论文走完整流程，人工判断质量后再提交入库（提交沿用 `10.04` 式日期前缀）。
4. 每步同步更新本目录 TODO 与检查脚本（参照 agent-parliament 的 check.mjs 模式）。

## 7. 证据层级与未核验声明

- 插件现状：本轮直接读取 main 分支工作区文件（grad-radar 全部三份 references 与 SKILL.md、idea-ledger、weekly-brief）；run-provenance / submission-gate / thesis-cn / career-bridge 沿用 2026-10-03 核验报告，本轮未重读。
- ResearchWorkbench 需求：只读代理调研（约 30 次工具调用），证据落在具体文件路径（AGENTS.md、docs/READING-TEMPLATES-005.md、docs/DAILY-BRIEF-006.md、docs/plans/SURVEY-013/、docs/plans/READING-014/、public/content/*.js、public/library.js、public/surveys.js、public/notes.js、server.mjs、discovery.mjs）。本轮未运行平台代码，未修改平台任何文件。
- 开源参考：调研代理经 GitHub API 核验了 license、stars 与最近活跃时间并读取 README（2026-10-04）；机制描述为二手转述，实施引用前应抽查原始仓库文档。未复制任何外部代码或文本。
- 本文件是方案，所有脚本与技能改动尚未发生。
