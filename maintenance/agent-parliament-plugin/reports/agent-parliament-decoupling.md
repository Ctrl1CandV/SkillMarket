# agent-parliament-plugin 去耦交付报告

> 结构更新（2026-10-04）：用户决定移除 `.zcode-plugin/plugin.json` 宿主适配清单，仓库仅保留技能与共享流程文件；本报告描述的是交付时的结构。

## 来源与固定版本

- 核对日期：2026-10-03。
- 上游：https://github.com/Ctrl1CandV/agent-parliament-plugin
- 本次实际执行 `git ls-remote https://github.com/Ctrl1CandV/agent-parliament-plugin.git HEAD`，远端 HEAD 为 `3c893b9b8aa11be09df65f0208e1a96d1ab9b81e`，与前次记录一致。此为核对时的最新 HEAD，不保证未来仍最新。
- 复用只读缓存：`C:\Users\11487\AppData\Local\Temp\plugin-assessment-20261003\agent-parliament-plugin`。`git rev-parse HEAD` 返回同一 SHA；`git status --short` 当时为空；origin 为上述仓库。已读全部七个 SKILL.md、manifest、配置和中文 README，并检查固定提交的完整文件清单。
- 上游 manifest 名称 `agent-parliament`、版本 `1.7.0`。派生包使用目录一致的身份 `agent-parliament-plugin`、独立版本 `0.1.0`；不是对已安装上游包的原位升级。

## 许可边界

固定提交的 README 只有 `MIT` 声明，manifest 有 `license: MIT`；整个跟踪文件清单中没有 LICENSE 正文或完整版权通知。本次保留这里的来源事实，不伪造许可证正文、作者、版权年份或授权，不将上游声明擅自当作本派生版本已完成许可核实。运行 manifest 未填写 license/author。公开发布或再分发前需要向上游确认适用的完整许可及通知要求；此报告不作法律授权结论。

## 落盘范围与最小发现格式

运行根目录：`D:\Program Project\SkillMarket\plugins\agent-parliament-plugin`。

已加载 plugin-creator，并阅读其 `plugin-json-spec.md` 和 `installing-and-updating.md`。按当前 ZCode 文档采用 `.zcode-plugin/plugin.json`，明确 `skills: ./skills`，每个 `skills/<name>/SKILL.md` 有 name/description frontmatter。这是明确可发现的源码格式，不是已安装或运行成功的证据。流程内容不依赖特定宿主工具；manifest 是 ZCode 的最小包装，未声称所有宿主都支持该包装。

运行包共 9 文件：1 manifest、7 skills、1 共享 reference（位于 orchestrator/references/process.md，各 skill 用相对链接显式读取）。只有运行需要的资源，没有配置服务、绝对本机路径、hosts、evals、测试、来源文档或 .git。单独复制某个 skill 会丢失共享依赖，应保留整个插件内相对结构；其他宿主需通过其技能机制加载内容，未验证其插件安装兼容性。

本轮交付源码包，主会话已更新市场 README 与维护事项；未新增 marketplace catalog，也未注册、安装或启用插件。当前 SkillMarket 是源码集合，不代表已配置为宿主可安装市场；未声称存在市场 ID 或完整市场插件 ID。

## 迁移表

| 上游资源/职责 | 派生处理 | 实质差异 |
|---|---|---|
| `.claude-plugin/plugin.json`，隐式技能发现 | `.zcode-plugin/plugin.json` 显式 skills 路径 | 保持七技能可发现；新身份/版本；不照搬未核实许可元数据 |
| `.mcp.json` 与本机服务路径 | 不进入运行包 | 不再要求服务、模型端点或安装目录，不换一个专用服务续绑 |
| orchestrator | 有序阶段协调与实际顺序执行入口 | 不再“只路由不干活”导致无代理时停摆；可切入角色执行，明确每阶段交接与回退 |
| project-planner | 需求、验收、最小计划与有证据的修订 | 不强制 SPEC/PLAN/ADR、固定标题或 REV 补丁合成；沿用已有载体；用户保留范围/风险/权限决定 |
| adversary | 实现前反例、假设和边界质疑 | 不再依赖外部交叉验证才可工作，也不直接改草案使之生效；问题回 planner，三轮上限不等于通过 |
| code-developer | 最小实现、回归、自审、实际命令证据 | 不调用 peer_review/test_audit 等工具；修复后必须回审查；证据缺失如实待验证 |
| reviewer | 契约与 diff 的四维审查 | 局部缺陷回实现，结构问题回规划；不按严重性机械创建后继 PLAN；角色切换不是独立评审 |
| untangler | 阻塞证据、根因假设、最小判别实验、方向交接 | 保留只诊断不落地，去除工具链；明确无环境/权限时返回用户，不能越过质量闸门 |
| memory-keeper | 必要记录的一致性核对与事实交付 | 不创建空骨架、不改全套文档架构；不以归档把失败或未验证标完成 |
| 自动上下文注入与 context_files/project_dir 约定 | 明确手动最小交接 | 接收方读取实际材料；不假设宿主注入；指定范围和只读边界 |
| 外部多模型“独立防线” | 自审 / 实际独立评审 / 待外部评审三态 | 默认单代理顺序执行；有宿主代理可选且需授权；项目必需独立评审时不可用就阻塞 |

### 原工具能力的中立替代

- delegate_research：先读本地代码与文档，具体未知再按权限调研；不自动外发上下文。
- validate_approach / independent_analysis / advisor_analysis / consensus：显式列假设、反例、证据及用户取舍；实际有另一执行者才报告外部意见，不伪造共识。
- peer_review / test_audit：读实际 diff、逐条比对验收、检查测试是否可抓错，按事实标自审或独立评审。
- verify_implementation：使用项目已有真实验证命令，先检查副作用；不宣称文件树隔离就是环境隔离。
- delegate_chain / delegate_dialogue：由阶段顺序和真正需要用户决定的阻塞点承接，而非替换成另一个服务接口。

## 流程与权限边界

保留澄清 → 规划 → 质疑 → 实现 → 审查 → 修复/复核 → 最终验证 → 交付。小 bug 可在会话里压缩，但不省真实质量动作；中型显式规划和审查并复用现有记录；安全/并发/数据完整性等不因修改少就降级。

每次交接包含目标/验收、有效计划与阶段、产物与证据、未决问题与授权、责任角色及前进/返回条件。执行中修订保留旧结论，待接受方案不生效。AGENTS.md、CLAUDE.md 和适用项目约定优先于插件模板，不能用插件改写项目制度。

明确禁止自动提交/推送/发布、未授权外发代码、修改宿主配置和突破写入范围。测试前检查真实副作用；生产、数据库、迁移、删除与依赖安装按权限停问。角色审查不授予任何新权限。宿主代理仅可选，未授权外部服务和“角色换名等于独立评审”均不成立。

## 可复跑检查与行为用例

维护文件：

- `D:\Program Project\SkillMarket\maintenance\tests\agent-parliament-decoupling\check.mjs`
- `D:\Program Project\SkillMarket\maintenance\tests\agent-parliament-decoupling\cases.json`

已有 Node 环境可运行（本次 Node v24.19.0）：

```sh
node "D:/Program Project/SkillMarket/maintenance/agent-parliament-plugin/evals/check.mjs"
```

脚本无第三方依赖、不联网、不运行子进程、不写项目文件，按自身位置定位插件。结构检查包含精确运行文件白名单、manifest 字段/目录身份/版本/skills 路径、七技能 frontmatter、相对引用存在与边界、拒绝符号链接、旧工具绑定/本机路径/占位符扫描、核心政策锚点。

三个行为用例含原始输入、期望轨迹、禁止宣称与人工评估 rubric：

| 用例 | 模拟观察 | 结果 |
|---|---|---|
| 小 bug | 会话契约和计划 → 边界质疑 → 实现 → 自审 → 验证 → 交付，无文档骨架 | delivered |
| 中型功能 | 未决兼容问题先等用户 → 质疑失败回规划 → 顺序实现/自审/验证，复用记录 | delivered |
| 审查失败回退 | 数据完整性升级 → 结构问题回规划/质疑 → 局部问题修复/复审 → 数据库环境缺失 | awaiting-verification，不能宣称完成 |

另有 7 条拒绝轨迹：用户未决定却规划、未接受方案直接实施、修复跳过复审、缺验证仍交付、验证失败仍交付、三轮耗尽视作通过、把自审充当必需独立评审。

本次执行输出：结构检查通过（9 文件、7 skills），3 个合成用例通过，7 条不安全轨迹被拒绝；命令返回码 0。`git diff --check` 返回码 0，但它不覆盖未跟踪的新文件，因此不能用它替代结构脚本。

### 检查能力限制

行为部分是维护脚本手写的协议状态模型，用固定输入检查门禁一致性；它不是运行时技能执行器，不会调用语言模型或宿主，不证明模型真的遵循文本。静态锚点只能发现部分回归，不能证明语义正确。fixtures 中 verify-pass 是假设事件，不代表真实代码测试通过。人工对照三个 rubric 已检查文本具备对应行为，但未执行真实项目构建、真实独立评审或宿主 UI 安装试用，也未调用 ZCode CLI schema validator。

建议获准安装后，新任务从技能选择器选本插件 orchestrator，发送小 bug 用例；观察它是否先读约定、仅会话规划、实际验证、明确自审且不提交。中型与审查回退用例分别验证用户决策暂停与缺环境阻塞，不能只看最后一句“通过”。这些真实行为验证本次待做。

## 范围核对

只在上述新插件和同名维护报告/测试目录创建文件，没有改外部源仓库或已安装副本，没有提交、推送、注册或安装。工作区原有未提交改动保持不动；检查期间 de-ai-flavor 的工作树状态还出现其他变化，本任务未读写或回滚这些文件。共享市场接入、许可正文确认和宿主真实试用是明确未完成边界，不在此轮授权内扩散。
