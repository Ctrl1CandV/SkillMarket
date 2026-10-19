---
name: grad-radar
description: 根据读者基础和学习问题找、选、读论文与综述；按场景权衡刊会、年份和引用影响，进行有证据的信息压缩、完整综述导读、单篇精读及按本次方向的 arXiv 每日追新。默认照顾阅读经验较少的读者，支持链接/arXiv ID/PDF、快速判断与继续阅读，不代替系统性文献检索。
license: MIT
metadata:
  version: "0.4.0"
---

# grad-radar：需求选文、充分讲解与每日发现

按意图进入对应流程，单篇内容继续复用现有主记录：

默认服务阅读经验较少的学生或研究者，先建立文章整体，再连贯解释作者的问题、做法与发现，不将新生等同于零基础。先确定本次任务范围；范围内的深度首先依据论文本身的内容、论证复杂性与理解依赖决定，必要公式、架构和实验设计主动讲清，不等待用户要求加深。用户明确要求可以进一步调整；论文年代、引用量和已读篇数不代替内容判断。准确来源、重要条件和未读范围始终保留。

- **主题选文**：用户描述领域、技术或研究问题 → 读 `references/selection-protocol.md` → 明确属性优先顺序与硬条件，核验来源、年份、引用及关键正文，给有理由的主读与互补推荐。一般优先顶刊顶会与近三年，经典基础和时效应用按场景调整，不套每日三天窗口。
- **完整综述导读**：用户要求完整总结一篇综述 → 读 `references/survey-protocol.md` → 全篇覆盖、按需求展开、核对后交付可直接阅读的中文导读。选节工具按目录逐节调用；短预览不替代正文。
- **单篇阅读（核心）**：用户指定论文（链接/arXiv ID/本地 PDF）或从每日简报选中 → 按 `references/reading-protocol.md` 判断与阅读 → 按 `references/note-templates.md` 产出笔记 → `scripts/reading_record.py` 落盘。每篇一个主记录、一个当前主笔记，AI 整理程度与人的阅读状态分开记录。
- **每日发现（漏斗）**：本次输入确定方向/问题/偏好 → 元数据初筛、分级与少量信息提取 → 用户选中的论文**回到单篇阅读**。本次偏好不持久化；大部分论文不必读，读的那部分也只有一部分内容值得精读。

## 边界（不做什么）

- 主题选文服务当前学习问题，保留实际渠道、查询与取舍，不声称穷尽或形成可发表的系统综述。需要系统检索时使用实际可用的专项方法。
- **阅读方法论在插件内**（reading-protocol/note-templates 就是它）；`paper-reader` 等外部精读工具若可用是可选增强，缺失不影响基本阅读——「无外部工具无法继续」不成立。
- 不做语义向量检索；不发邮件/推送；不自动创建定时任务；「每日」= 用户调用时处理当天窗口。
- 重要性/难度/阅读路线是**可纠正的建议**；「结论成立」「用户已读完」不由脚本或模型代判。

## 路径占位符

`{SKILL_DIR}` 指本 SKILL.md 所在目录的绝对路径，由调用方展开。脚本一律用引号包裹（路径可能含空格）。Windows 中文乱码时前置 `PYTHONUTF8=1`。

## 配置：`.grad/config.json`

单篇讲解、主题选文和每日发现可直接使用本次会话，不要求先初始化。用户要求建立项目配置时才初始化；已有配置不覆盖（`CONFLICT` 转 `validate`）。日常可读取已有的数量/时间设置，研究方向以本次输入为准，不自动沿用旧查询：

```bash
uv run --no-project "{SKILL_DIR}/scripts/radar_config.py" init --config ".grad/config.json" --json
uv run --no-project "{SKILL_DIR}/scripts/radar_config.py" validate --config ".grad/config.json" --json
```

- 脚本兼容 `keywords`/`categories`/`daily_caps`/`days`/`reading_profile`；`venues_watch`、`thesis_rules` 等其他 skill 字段原样保留。新模板的 `keywords`/`categories` 为空，不预填或保存研究方向。旧查询字段保留兼容，但不自动用于新的每日检索；用户本次明确指定使用旧配置范围时才读取它们。
- 模板起点为低负担：`daily_caps: {must_read: 1, skim: 2}`、`days: 3`。本次数量/窗口要求优先；其余沿用已有设置，不静默覆盖。`daily_caps` 允许 0（该类不安排，允许零输出），拒绝负数/bool/非整数。
- `reading_profile`（首次背景，四类）：direction/learning_goal/known_background/available_minutes。用户没填也能读论文（入门友好 + 难度标暂定）；会话内明确「我学过 X」本次生效；**用户明确要求记住才**按字段更新：

```bash
uv run --no-project "{SKILL_DIR}/scripts/radar_config.py" profile --config ".grad/config.json" \
  --direction "<方向>" --known-background "python,注意力机制" --available-minutes 20 --json
```

- 每日拉取默认把本次方向转换成显式 `--keywords`/`--categories`，不写回配置；检查 `effective_params`，确保分类与关键词真实反映在查询上。`--config` 仍兼容用户明确指定的配置查询，显式 CLI > 该次指定配置 > 默认，读取不修改文件。已保存阅读背景供单篇讲解使用，不自动变成每日筛选方向。

## 单篇阅读（主流程）

对「帮我读这篇 / 值不值得读 / 讲详细一点 / 继续上次那篇」类请求：

1. **读协议**：`references/reading-protocol.md` §0 路由 → §1 处理顺序。先 `show` 查已有记录，已有进度与背景不重复询问。
2. **取内容**：arXiv 走 `arxiv_html.py`（先目录，再按任务取节；完整综述须循环处理全篇）；用户提供 vN 必须读 vN；本地 PDF 用宿主实际可用的能力。只有摘要时最高交付 quick；仅身份交付原文入口，不生成内容笔记。
3. **提取与写作**：读 `references/extraction-guide.md`，先建立关键论点的证据与条件清单，再按 `references/note-templates.md` 写连贯讲解。首次导读先讲文章整体，主体串起研究目标怎样落实为方法与证据、实际发现是什么，再说明价值和边界；继续阅读或单点追问直接接续相关内容。按论文的理解需要决定深入程度，核对定义、机制、设置、结果和限制；内容不足交付部分结果。完整综述另走 survey-protocol，不套短标准卡。
4. **落盘**：用户请求笔记/继续更新或已有项目约定要求保存时使用脚本；只在聊天解释、推荐候选时可直接交付。公共内容生产用明确指定的隔离目录，不初始化或改写个人 `.grad`。每篇首次先 `register`（同身份幂等复用）：

```bash
uv run --no-project "{SKILL_DIR}/scripts/reading_record.py" register --repo . --input-file <身份+来源+分类 JSON 文件> --json
uv run --no-project "{SKILL_DIR}/scripts/reading_record.py" save-note --repo . --paper <id> \
  --note-file <笔记正文> --mode quick|standard|deep --basis sections \
  --sections S1,S3 --limitations "图3仅提取到图注" --json
```

5. **回复**：可直接阅读的结果；保存时附笔记路径。关键主张附近保留准确原文定位，并另判断是否需要亲读：有则说明读哪里、为什么、关注什么，无则明确当前无需额外原文阅读；引用不等于必读清单。跨论文联系有可靠依据且有助理解时再给，不设配额，本篇必需的背景仍要讲清。理解题和积累建议可选；快速判断、结论核查或用户已有读法时按任务收尾。没有目录不猜定位。
6. **用户表达阅读状态**只有这一条路（AI 生成笔记≠读完，脚本层面禁止）：

```bash
uv run --no-project "{SKILL_DIR}/scripts/reading_record.py" set-status --repo . --paper <id或带版本的id> \
  --status read --user-quote "<用户原话>" [--read-version v1] --json
```

已读 v1 后又获取 v2：呈现「读过 v1，当前资料 v2」，不宣称 v2 已读，不抹阅读历史。**读完的版本以用户表达为准**（`--read-version` 或带版本定位查询 `--paper 2410.06992v1`），没有任何版本依据时 last_read_version 留 null——不拿当前资料版本冒充。笔记冲突（被人工编辑/merge 过）脚本默认拒绝整体替换；`--merge` 可连续多次追加补充段、人工内容永不丢，merge 过的笔记后续普通保存也继续走追加保护；确需整体重写才用 `--force`（旧稿自动快照进 history）。`.user.md` 用户批注 AI 永不覆盖。没有可读来源时不保存任何档笔记（`--basis unavailable` 会被拒），用 `--record-failure` 只登记获取失败与待补材料。

## 每日发现

复用本次请求和同一任务会话中的方向、问题及偏好；只缺少会改变查询范围的信息时才询问。没有范围时不套默认 LLM/Agent 方向、不从阅读记录推断兴趣。按本次目标拆关键词、选择分类：分类仅在有助限定时给出，不猜分类编号；只查关键词时省略 --categories。

```bash
uv run --no-project "{SKILL_DIR}/scripts/arxiv_fetch.py" \
  --keywords "<本次一组关键词，逗号分隔>" --days 3 --json
```

- `days` 用本次要求或已有时间设置，未指定时 3；关键词重复传参表示组间 OR，组内 AND，可按本次范围增补分类。查询、元数据筛选、分级、少量提取和选中后阅读这套常规流程保留，不要求持久化研究偏好。
- 脚本内部串行 + 1 req/3s + 429 指数退避，不要并行调用；窗口默认 3 天（arXiv 索引滞后 1—3 天）。旧条目标 `new: false` 表示曾获取；同一范围避免重复提醒，另一主题仍可因当前相关性被推荐，不把 seen 当兴趣过滤器。
- 空结果且非网络错误：先怀疑索引滞后，可扩大窗口跑一次（`--days 5`），仍空就如实说。网络错误（NETWORK/RATE_LIMITED）与「没有匹配论文」分开呈现，**不把离线当零新文**。
- 结果截断（`truncated: true`）必须展示，不能称已覆盖全部新论文。

拿到列表后**读 `references/tiering.md`** 分级：machine 枚举 `must_read`/`skim`/`archive` 继续用，但用户侧呈现为「优先关注/可以速览/其他候选」——must_read 是当次推荐等级，≠ importance=core，更不是阅读任务。数量先按本次要求，其次已有 daily_caps，均无时用低负担起点 1+2；不足不凑数，其余进简短索引。按本次问题排列信号，不按论文类型或领域固定降级。默认不为几十篇候选获取全文；用户选中的才进单篇阅读。每篇写明可反驳的理由，输出声明「启发式排序，不是质量判断」。

arXiv 新稿只表示近期候选，不自动满足“顶会/高被引”。用户要求高质量推荐时，最终主读还须走 selection-protocol 的来源与内容核验；用户直接指定某篇时照常阅读，不因未满足推荐门槛拒绝解释。

用户请求留存或项目约定需要时保存当日简报 `.grad/radar/YYYY-MM-DD.md`。先核日期、查询范围与参数：同日同范围已有文件默认复用；范围变化时使用有区分的文件名，或按用户刷新请求保留旧版再更新，不把另一主题的旧简报当本次结果。简报记录本期查询与取舍供复核，不作为以后自动采用的偏好：

```markdown
---
date: YYYY-MM-DD
papers:
  - tier: must_read
    arxiv_id: "<基础 id>"
    paper_id: "arxiv-<基础 id>"
    path: "radar/digest/arxiv-<基础 id>.md"
  - tier: skim
    arxiv_id: "<id>"
    paper_id: null
    path: null
---
```

头部是机器可读契约：`papers` 覆盖本期全部论文；`tier` 枚举 `must_read`/`skim`/`archive`；`arxiv_id` 字符串；`paper_id` 连接主记录（未登记写 null）；`path` 相对 `.grad/` 的笔记路径，无笔记 null。正文供人阅读，头部供 weekly-brief 等下游读取。简报末尾最多给一个当前学习建议（可以是「继续读完手里的 X」）。

去重台账 `~/.grad-radar/seen.jsonl`（跨项目共享）**只表示曾获取/见过基础 ID**——seen ≠ 用户读过，也不表示兴趣；不从见过的论文推断未来偏好。单篇处理、笔记、阅读状态仍在项目 `.grad/` 的主记录里，日常分级反馈仅影响本次结果，不改 config 或插件规则。

## 章节切片（HTML 主路径）

```bash
uv run --no-project "{SKILL_DIR}/scripts/arxiv_html.py" <id|idvN> --outline --json
uv run --no-project "{SKILL_DIR}/scripts/arxiv_html.py" <id|idvN> --sections 3,3.2 --json
```

先目录后取节。输出带 `version/version_status/fetched_at`：缓存按版本隔离，命中保留原始获取时间；显式版本 404 如实报，不静默换版。

## 降级链（按顺序，失败要说清卡在哪一级）

1. `arxiv.org/html/<id>` 有 LaTeXML 结构 → 章节切片（主路径，`source: arxiv_html`）
2. `NO_HTML`（无 LaTeXML，极老论文/纯图投稿）→ 询问用户是否有 PDF，或经宿主/外部解析器（mineru 等，若可用）读取（`source: host_pdf`/`external_parser` + `parser_name`）
3. 用户直接粘正文/摘要 → `source: user_text`
4. 有可靠摘要、无正文 → quick，`basis: abstract`；仅身份/标题 → 原文入口，按授权只登记身份。`basis: metadata` 不能保存内容笔记。

## 铁律

- 每篇、每级都写可反驳的理由；不编造 arXiv id、章节号、数字；脚本报什么就是什么
- AI 没读的章节就写进「未覆盖」，不假装读完全文；图的图注≠看过图
- 简报与笔记都是新建/授权更新，不静默覆盖；重复展示与重读不产生重复笔记
- 记录维护时间（created_at/updated_at/note.generated_at）永远不等于用户完成阅读的时间

## 错误契约

脚本输出 `{"ok": false, "error": ..., "detail": ...}` 时如实转述，不盲目重试：`RATE_LIMITED`/`NETWORK` 说明离线或稍后再试，已有历史仅作为明确标记的旧资料；`NO_CONFIG`/`BAD_CONFIG` 核对本次指定的配置，日常检索可改用显式查询参数；`BAD_ARGS` 缺范围时补本次范围，不以空配置发起全领域查询；`AMBIGUOUS_IDENTITY` 列候选让用户确认；`CONFLICT` 说明保护了哪份旧内容、给哪几个出口；`NOT_FOUND` 说明没有这条记录。`ok: true` 只说明脚本完成，不说明笔记质量。
