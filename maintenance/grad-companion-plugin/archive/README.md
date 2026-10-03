# grad-companion

> 归档说明（2026-10-03）：本文保留原项目介绍和历史验证记录，不是当前运行包的安装入口。运行主干在 `../../../plugins/grad-companion-plugin/plugin/`，许可证在 `../../../plugins/grad-companion-plugin/LICENSE`。宿主适配仅供维护，已移出运行包；从本归档目录运行下文 `python hosts/<宿主>/build.py`，脚本读取上述主干，产物只写入本归档目录的 `dist/`。下文历史项目结构、旧版本状态与测试记录按原样保留。

面向计算机专业研究生的科研执行插件。一句话定位：**阅读是核心，执行层让一切可追溯**——读论文有一套内置协议（三档深度、按类型抓重点、笔记可回查），「筛论文、记实验、对规则、写周报」这些每周重复、可机械化的环节被接起来，每条产出指回真实来源。

为谁做：目标是「扎实读论文 + 早发论文 + 拿到大厂实习」的 CS 硕士。默认语境是 LLM/Agent 方向，机制不绑定方向。

## 它做什么

| 命令 | 能力 | 使用频率 |
|---|---|---|
| `/grad:radar` | **单篇阅读核心**：给链接/arXiv ID/PDF 就能读——快速判断卡片 / 标准笔记 / 重点精读，按论文类型（方法/综述/理论/系统/评测）抓不同重点，笔记与阅读进度落盘可续读；**每日发现**：arXiv 定向拉取，分级简报（优先关注/速览/候选，数量随配置，新起点低负担 1+2） | 每天 |
| `/grad:run` | 登记实验 run（git commit、config 快照、seed、指标、running→补录）；claim 双轴台账与论文数字一致性核对（不同配置不静默合并）；mean±std LaTeX 表（n=1 标注而非伪造误差） | 有实验时 |
| `/grad:gate` | 投稿前机械核对（页数、checklist、匿名性、LLM 使用披露等）；ccfddl 截稿倒排与冲突检测；ARR 无效批评清单辅助 rebuttal 分类 | 投稿季 |
| `/grad:idea` | 选题台账与弯路记录：候选登记、选入/否决流转（否决必须给方法级否定理由）、排序理由显式化、选题停滞计数提醒 | 有想法时 |
| `/grad:brief` | 周报：上期承诺逐条对账（证据覆盖才算完成/部分覆盖标部分/无源标无法核对）；收集、AI 整理笔记、用户实际读完分开呈现 | 每周 |
| `/grad:career` | 从实验记录生成简历项目卡 + 面试深挖追问（素材来自真实 ablation 记录）+ Agent 岗考点缺口清单 | 求职季 |
| `/grad:thesis` | 中文学位论文合规：GB/T 7714 文献格式（版本状态如实标注）、中英摘要一致性、章节与图表清单 | 毕业季 |

命令只是入口，七个 skill 也会被对话自然触发（「帮我读这篇」「值不值得读」「继续上次那篇」都会路由到阅读流程）。截稿数据实时来自 [ccfddl](https://ccfddl.com)，`/grad:gate` 永远给出当前倒计时，仓库里不维护会过期的日期。

## 核心设计：阅读优先

组织原则：**大部分论文不必读；要读的那部分，怎么读取决于论文是什么、你缺什么。**

```
两个入口 → 同一套单篇阅读流程
 每日简报选中的论文      用户直接给的 链接 / arXiv ID / 本地 PDF
        ↘              ↙
   一篇一个主记录（.grad/radar/papers/）：身份+版本、三维判断（重要性/难度/类型，各附理由）、
   AI 笔记（quick 卡片 / standard 骨架 / deep 展开）+ 用户批注文件 + 人的阅读状态（unread/reading/read/deferred）
        ↑
   内容来源：arXiv HTML 按章节取（主路径，版本固定获取）> 本地/下载 PDF 经宿主能力 > 用户粘贴文本 > 只有元数据
```

- **AI 整理 ≠ 你读完**：笔记生成、重新展示都不动阅读状态；「读完/暂缓」只有你明确表态才记录，且带原话引用
- **每篇的笔记知道自己是基于什么写的**：读了哪几节、哪些图只到图注、哪些表没核对，写在「证据与覆盖说明」里；只有摘要时系统层面就交付不了精读
- **旧内容不被吞**：更新笔记先存历史快照；被人工编辑过的笔记默认拒绝整体覆盖，追加或另存由用户决定
- **为什么 HTML 优先于 PDF 解析**：arXiv 的 LaTeXML 全文比 PDF 小一个数量级（实测同一篇 686KB vs 12.4MB），带稳定章节锚点（`S2.SS1`），公式是 LaTeX 源而非图片；PDF/外部解析器是真实可用的降级路径，不是唯一入口

## 安装（ZCode 宿主）

前置：[uv](https://docs.astral.sh/uv/) 与 Python ≥ 3.12。**不需要任何 API key**——数据源只有 arXiv 与 ccfddl 的公开接口。

```bash
python hosts/zcode/build.py     # 生成 dist/zcode/
```

**ZCode**：设置 → 插件 → 添加插件市场 → 本地目录，选 `dist/zcode`，安装并启用 grad-companion。输入 `/grad:` 应看到七条命令。

**Claude Code**（0.3.0 起）：`python hosts/claude-code/build.py` 生成 `dist/claude-code/`，按该宿主的本地插件方式装载。结构与清单经构建自检与回归测试校验；真实宿主内的加载行为未实测，以实际表现为准（见 `hosts/claude-code/README.md` 验证边界）。

改动主干后重新 build 对应宿主即可。两个适配层互不 import，全部由 manifest 驱动——加第七个能力时 zcode 构建自动拾取即是例证。

其他宿主（Qoder、Claude Code 等）：**插件本体是宿主中立的**，`plugin/` 里 grep 不到任何宿主名（有机械检查）。适配一个新宿主 = 在 `hosts/` 下加一个平级目录，主干零改动。

## 从今天开始用（入学初期三个周常）

其余能力随研究阶段自然启用，不再主动排期。当下只需三件事：

1. **每天 `/grad:radar`**——首次运行会生成 `.grad/config.json` 关键词配置并自动校验（分类/关键词/每日数量真实作用于查询与简报）；看到想读的直接把链接或 ID 丢进来
2. **遇到要读的论文直接说**——「帮我读这篇 <链接/ID/PDF>」出标准笔记；「先判断值不值得读」出快速卡片；读完了明确说一句「这篇读完了」才会进阅读台账
3. **有想法就 `/grad:idea`**——candidate 也记、否决更要记（否决必须给方法级理由，环境性失败会被脚本提醒）
4. **每周 `/grad:brief`**——第一次没有上一份可对账属正常；从第二周起「上期对账」按证据覆盖度逐条判定，本周文献按「收集 / AI 整理 / 实际读完」分开呈现

另外一个提前量：上手复现实验室 baseline 时就用 `/grad:run` 登记——这批 run 既是你熟悉实验流程的过程记录，也是将来项目卡与论文数字的第一批原料。

## 质量验证（2026-09-11 阅读核心发布前实跑）

发布流程固定四步验收：常驻回归（解析器、配置护栏、DDL 时区、统计口径、失败/占位 run 契约、分组与数字核对等）、SKILL.md 契约断言（含宿主中立 grep、阅读核心文档间一致性、跨文件契约）、阅读核心行为用例（身份去重、版本、笔记保护、配置连通）、双宿主构建（manifest 驱动、fail-loud lint）。**测试代码本身本地维护、不随仓库分发**——但两个 `build.py` 在仓库内，任何人重建产物时都会跑其中可复现的结构校验与 lint。

```
$ uv run --no-project tests/test_regression.py
30 tests passed
$ uv run --no-project tests/test_contracts.py
14 tests passed
$ uv run --no-project tests/test_reading.py
15 tests passed
$ uv run --no-project hosts/zcode/build.py
  skills 复制 7/7，commands 生成 7/7
$ uv run --no-project hosts/claude-code/build.py
  skills 复制 7/7，commands 生成 7/7
```

阅读效果本身不按测试计数验收：以三篇真实论文试读为准（一篇综述 standard、一篇方法论文 standard、一篇评测论文 deep、一篇经典 PDF 路径 quick），产物示例见开发文档（本地维护）。

## 设计哲学：不做什么

- **方法论只做够用的，外部增强是可选。** 阅读流程内置（协议+模板+记录），`paper-reader`、`mineru` 等外部能力可用则增强、缺失不影响基本阅读；系统综述式检索、实验设计原则、学术写作仍属方法论工具，若有此类 skill 本插件与之协作而非竞争。脚本层永远只做确定性执行：规范化身份、按明文规则核对、结构化落盘
- **判定权留给人。** 不自动判定 novelty，不生成审稿意见，不替你决定投哪里。输出永远是「证据 + 清单 + 需人工确认项」
- **只记录不执行。** run 登记不启动训练、不改超参、不删文件
- **单一数据源。** 检索与下载只用 arXiv，另加 ccfddl 取截稿日；不接需要 key 或按量计费的源
- **缺失信息标 unknown，不填猜测值。** 数字必须能指回一个 run id

## 与「全流程科研助手」的区别

通用全流程赛道已有成熟竞品。本插件避开那条赛道，做三处无人覆盖的空白：

| 空白 | 现状 | 本插件的动作 |
|---|---|---|
| 实验结论 ↔ 运行记录的溯源 | 头部竞品明确声明不执行实验；实验追踪工具不管论文里的数字 | `run-provenance`：数字绑 run + commit，改稿时检出漂移 |
| 科研产出 → 求职资产 | 求职仓库全是静态文档，无一是可执行工具 | `career-bridge`：真实实验记录生成面试深挖素材 |
| 中文学位论文合规 | 校级模板生态停更、无许可证 | `thesis-cn`：GB/T 7714 + 摘要一致性，校级规则走用户配置 |

## 项目结构

```
grad-companion/
├── plugin/         # 插件本体，宿主中立（95% 的工作量）
│   ├── manifest.json
│   ├── commands/   # 七个命令（中立 frontmatter）
│   └── skills/     # 七个 skill：SKILL.md + scripts/ + references/
├── hosts/zcode/    # ZCode 适配层：build.py 读 plugin/ 生成 dist/zcode/
└── dist/           # 构建产物（gitignore，随时可重建）
```

## 状态

0.1.2：六个 skill 全部落地，并补齐 HTML 算法/跨格表格解析、radar 配置护栏、完整 timeline、失败 run、指标键漂移告警与常驻回归测试。宿主适配可由 `hosts/zcode/build.py` 重建。MIT License，见 [LICENSE](../../../plugins/grad-companion-plugin/LICENSE)。

项目的设计与开发文档为本地维护，不随本仓库发布；如需了解某项能力的设计取舍，欢迎提 issue。

0.1.3：把纪律变成可执行的——claims 双轴拆分（claim_register / claim_check）、SKILL.md 契约测试与宿主中立断言、Type-A/Type-B 门类型学入档。
0.2.0：投稿季三件套 + 组会对账——judge 一致性验证（judge_agreement + 协议）、可复现发布包（repro_pack）、benchmark 可信度标注（benchmark-caveats 活文档）、周报承诺对账（brief_reconcile）。
0.3.0：第二宿主适配验证（hosts/claude-code，双构建共享 manifest、主干哈希零变化被测试锁定）+ 选题台账 idea-ledger（/grad:idea，killed 必须方法级理由、停滞纯计数 detect-only）。
0.4.0：阅读核心落地 + 正确性加固——单篇阅读双入口共用主记录（身份去重、版本固定、三档深度、类型化笔记、AI 整理与人的阅读状态分离、批注与历史保护）；配置真实作用于查询与每日数量；数字未比对不再冒充 verified、不同配置不再静默合并、周报按本期窗口对账并支持结果补录、承诺须证据覆盖才算完成、「可复现」降为登记状态；GB/T 7714 版本状态如实标注（2025 已实施、细则待核对）。
