---
name: grad-radar
description: 论文阅读核心与 arXiv 每日追新：帮我读这篇（链接/arXiv ID/PDF）、快速判断值不值得读、标准阅读笔记、重点精读讲解、继续阅读、今天有什么新论文、arXiv 简报、分级筛选（优先关注/速览/归档）、按章节切片。内置三档阅读流程与可回查笔记，外部阅读工具只是可选增强。触发词：读这篇、帮我读、值不值得读、精读、讲解、继续看、新论文、追新、文献雷达。不做系统性文献检索。
license: MIT
---

# grad-radar：论文阅读核心 + arXiv 每日漏斗

两条主线共用同一套阅读流程与主记录：

- **单篇阅读（核心）**：用户指定论文（链接/arXiv ID/本地 PDF）或从每日简报选中 → 按 `references/reading-protocol.md` 判断与阅读 → 按 `references/note-templates.md` 产出笔记 → `scripts/reading_record.py` 落盘。每篇一个主记录、一个当前主笔记，AI 整理程度与人的阅读状态分开记录。
- **每日发现（漏斗）**：只用元数据筛选 → 分级简报 → 用户选中的论文**回到单篇阅读**。大部分论文不必读；读的那部分也只有一部分内容值得精读。

## 边界（不做什么）

- **不做系统性文献检索**——检索式设计与判据是 `literature-search` skill 的方法论（若可用则引导）。本 skill 的检索只服务每日定向与单篇定位。
- **阅读方法论在插件内**（reading-protocol/note-templates 就是它）；`paper-reader` 等外部精读工具若可用是可选增强，缺失不影响基本阅读——「无外部工具无法继续」不成立。
- 不做语义向量检索；不发邮件/推送；不自动创建定时任务；「每日」= 用户调用时处理当天窗口。
- 重要性/难度/阅读路线是**可纠正的建议**；「结论成立」「用户已读完」不由脚本或模型代判。

## 路径占位符

`{SKILL_DIR}` 指本 SKILL.md 所在目录的绝对路径，由调用方展开。脚本一律用引号包裹（路径可能含空格）。Windows 中文乱码时前置 `PYTHONUTF8=1`。

## 配置：`.grad/config.json`

首次运行先初始化，已有文件绝不覆盖（`CONFLICT` 不是错误信号，转 `validate`）：

```bash
uv run --no-project "{SKILL_DIR}/scripts/radar_config.py" init --config ".grad/config.json" --json
uv run --no-project "{SKILL_DIR}/scripts/radar_config.py" validate --config ".grad/config.json" --json
```

- 脚本只管 `keywords`/`categories`/`daily_caps`/`days`/`reading_profile`；`venues_watch`、`thesis_rules` 等其他 skill 字段原样保留。
- 模板起点为低负担：`daily_caps: {must_read: 1, skim: 2}`、`days: 3`。`daily_caps` 允许 0（该类不安排，允许零输出），拒绝负数/bool/非整数。**已有自定义值（如 5/15）继续生效，不静默覆盖**，可建议用户切换低负担起点。
- `reading_profile`（首次背景，四类）：direction/learning_goal/known_background/available_minutes。用户没填也能读论文（入门友好 + 难度标暂定）；会话内明确「我学过 X」本次生效；**用户明确要求记住才**按字段更新：

```bash
uv run --no-project "{SKILL_DIR}/scripts/radar_config.py" profile --config ".grad/config.json" \
  --direction "<方向>" --known-background "python,注意力机制" --available-minutes 20 --json
```

- 拉取不再手转参数：`arxiv_fetch.py --config` 直接读配置（优先级 显式 CLI > 配置 > 默认；输出 `effective_params` 注明来源）。**分类与关键词必须真实反映在查询上**。

## 单篇阅读（主流程）

对「帮我读这篇 / 值不值得读 / 讲详细一点 / 继续上次那篇」类请求：

1. **读协议**：`references/reading-protocol.md` §0 路由 → §1 处理顺序。先 `show` 查已有记录，已有进度与背景不重复询问。
2. **取内容**：arXiv 走 `arxiv_html.py`（先看目录再取章节，不整篇读）；用户提供 vN 必须读 vN（版本语义见脚本输出 version/version_status）；本地 PDF 用宿主实际可用的阅读能力；复杂版式/扫描件/乱码按协议 §6 如实降级。**只有摘要时最高交付 quick**——deep 请求未完成就说未完成。
3. **写笔记**：按 `references/note-templates.md` 对应模板写作（三维判断各附一句理由、关键数字带设置、未覆盖如实列）。
4. **落盘**（每篇首次先 `register` 建主记录，同身份幂等复用）：

```bash
uv run --no-project "{SKILL_DIR}/scripts/reading_record.py" register --repo . --input-file <身份+来源+分类 JSON 文件> --json
uv run --no-project "{SKILL_DIR}/scripts/reading_record.py" save-note --repo . --paper <id> \
  --note-file <笔记正文> --mode quick|standard|deep --basis sections \
  --sections S1,S3 --limitations "图3仅提取到图注" --json
```

5. **回复**：简短导读 + 笔记路径 + 一个具体后续动作。
6. **用户表达阅读状态**只有这一条路（AI 生成笔记≠读完，脚本层面禁止）：

```bash
uv run --no-project "{SKILL_DIR}/scripts/reading_record.py" set-status --repo . --paper <id或带版本的id> \
  --status read --user-quote "<用户原话>" [--read-version v1] --json
```

已读 v1 后又获取 v2：呈现「读过 v1，当前资料 v2」，不宣称 v2 已读，不抹阅读历史。**读完的版本以用户表达为准**（`--read-version` 或带版本定位查询 `--paper 2410.06992v1`），没有任何版本依据时 last_read_version 留 null——不拿当前资料版本冒充。笔记冲突（被人工编辑/merge 过）脚本默认拒绝整体替换；`--merge` 可连续多次追加补充段、人工内容永不丢，merge 过的笔记后续普通保存也继续走追加保护；确需整体重写才用 `--force`（旧稿自动快照进 history）。`.user.md` 用户批注 AI 永不覆盖。没有可读来源时不保存任何档笔记（`--basis unavailable` 会被拒），用 `--record-failure` 只登记获取失败与待补材料。

## 每日发现

```bash
uv run --no-project "{SKILL_DIR}/scripts/arxiv_fetch.py" --config ".grad/config.json" --json
```

- 脚本内部串行 + 1 req/3s + 429 指数退避，不要并行调用；窗口默认 3 天（arXiv 索引滞后 1—3 天），旧条目在 seen 台账标 `new: false` 不会重复。
- 空结果且非网络错误：先怀疑索引滞后，可扩大窗口跑一次（`--days 5`），仍空就如实说。网络错误（NETWORK/RATE_LIMITED）与「没有匹配论文」分开呈现，**不把离线当零新文**。
- 结果截断（`truncated: true`）必须展示，不能称已覆盖全部新论文。

拿到列表后**读 `references/tiering.md`** 分级：machine 枚举 `must_read`/`skim`/`archive` 继续用，但用户侧呈现为「优先关注/可以速览/其他候选」——must_read 是当次推荐等级，≠ importance=core，更不是阅读任务；正文数量以**配置生效后的 daily_caps** 为上限（新起点 1+2），不足不凑数，其余进一句理由的简短索引。默认不为几十篇候选获取全文；用户选中的才进单篇阅读。每篇写明可反驳的理由，输出声明「启发式排序，不是质量判断」。

当日简报 `.grad/radar/YYYY-MM-DD.md`（**已存在默认复用，不静默覆盖**；用户要求刷新时保留旧版再更新）：

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

去重台账 `~/.grad-radar/seen.jsonl`（跨项目共享）**只表示曾获取/见过基础 ID**——seen ≠ 用户读过；兴趣、处理、笔记、阅读状态全在项目 `.grad/` 的主记录里。

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
4. 只有元数据 → 只登记身份 + quick 摘要卡（`source: metadata_only`），**不生成虚构内容笔记**

## 铁律

- 每篇、每级都写可反驳的理由；不编造 arXiv id、章节号、数字；脚本报什么就是什么
- AI 没读的章节就写进「未覆盖」，不假装读完全文；图的图注≠看过图
- 简报与笔记都是新建/授权更新，不静默覆盖；重复展示与重读不产生重复笔记
- 记录维护时间（created_at/updated_at/note.generated_at）永远不等于用户完成阅读的时间

## 错误契约

脚本输出 `{"ok": false, "error": ..., "detail": ...}` 时如实转述，不盲目重试：`RATE_LIMITED`/`NETWORK` 说明离线或稍后再试（降级=读已有 `.grad/radar/` 历史）；`NO_CONFIG`/`BAD_CONFIG` 引导 init/修正配置；`AMBIGUOUS_IDENTITY` 列候选让用户确认；`CONFLICT` 说明保护了哪份旧内容、给哪几个出口；`NOT_FOUND` 说明没有这条记录。`ok: true` 只说明脚本完成，不说明笔记质量。
