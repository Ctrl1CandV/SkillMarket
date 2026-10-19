# grad-companion：连贯导读与阅读成果衔接

2026-10-19。grad-radar 更新为 0.4.0，并同步五个关联技能及命令入口。0.4.0 是 grad-radar 的技能版本，不是整个插件的发行版本。本次更新源码，不修改安装缓存、宿主包装或个人研究记录。

## 问题与行为变化

首次阅读时，读者可能尚不清楚文章对象，就被要求理解局部结论或进行批判。旧规则也容易把 core 对应 deep、把复杂内容留到用户要求后再讲。本次先建立文章整体，连贯解释作者目标怎样成为方法和证据、结果实际说明什么，再谈价值与局限。

先确定本次是快速判断、主线导读、局部解释还是完整综述。在该范围内，深度首先由论文内容、论证复杂性与理解依赖决定，必要公式、架构和实验设计主动解释；用户明确要求进一步调整。年代、引用、重要性标签与阅读篇数都不代替内容判断。简单论文讲清即可，不为深度增加无关术语和篇幅。

原文引用在主张附近保留，以实际版本、节/图/页定位；另判断亲读必要性，给具体位置、目的和关注点，允许当前无需额外亲读。跨论文联系有据且有用时再加，不设配额；本篇必需背景仍须讲清。完整综述继续覆盖主体和必要资产，来源缺口继续如实降级。

## 关联技能的交接

| 技能 | 本次同步 |
|---|---|
| idea-ledger | 阅读疑问、作者开放问题、AI 建议不自动成为个人选题；明确登记时保留归属与来源，不把候选当作创新性或可行性认定 |
| run-provenance | 只登记本项目实际开展的实验；复现计划和作者结果不成为个人 run，running 必须已实际启动 |
| weekly-brief | 导读学习、原文阅读与掌握分开；学习时间不取笔记生成时间，文献发现与本人实验结论分开归属 |
| thesis-cn | 引文格式正确不代表事实已核实；导读中的关键事实回查原文及条件，保留二手来源与辅助解释的归属 |
| career-bridge | 导读可作讨论素材，但不能证明实施、复现或项目经验；作者数字不写成个人成果 |

对应五个命令入口同步这些边界；run 命令中的旧 evidence“五级”改为引用 SKILL 中的实际分级，避免重复定义漂移。submission-gate 的投稿检查不受本次阅读衔接影响，保持原样。运行脚本、记录格式与个人状态迁移均不改动。

## 分支与交付范围

沿用 README 的 main/dev 约定：dev 接收运行文件与维护资料，main 仅接收以下运行文件，不将 dev 整体合入 main。本次从已核验的远端 dev `468247f`、main `0f0ca4d` 接续，保留其中已有的 frontend-craft 更新。临时插件分支与工作区已经撤销，原目录的未提交翻译已按授权清除。

| 分类 | 路径（仓库根相对） |
|---|---|
| 运行 | `plugins/grad-companion-plugin/commands/brief.md` |
| 运行 | `plugins/grad-companion-plugin/commands/career.md` |
| 运行 | `plugins/grad-companion-plugin/commands/idea.md` |
| 运行 | `plugins/grad-companion-plugin/commands/radar.md` |
| 运行 | `plugins/grad-companion-plugin/commands/run.md` |
| 运行 | `plugins/grad-companion-plugin/commands/thesis.md` |
| 运行 | `plugins/grad-companion-plugin/skills/career-bridge/SKILL.md` |
| 运行 | `plugins/grad-companion-plugin/skills/grad-radar/SKILL.md` |
| 运行 | `plugins/grad-companion-plugin/skills/grad-radar/references/extraction-guide.md` |
| 运行 | `plugins/grad-companion-plugin/skills/grad-radar/references/note-templates.md` |
| 运行 | `plugins/grad-companion-plugin/skills/grad-radar/references/reading-protocol.md` |
| 运行 | `plugins/grad-companion-plugin/skills/grad-radar/references/selection-protocol.md` |
| 运行 | `plugins/grad-companion-plugin/skills/grad-radar/references/survey-protocol.md` |
| 运行 | `plugins/grad-companion-plugin/skills/grad-radar/references/tiering.md` |
| 运行 | `plugins/grad-companion-plugin/skills/idea-ledger/SKILL.md` |
| 运行 | `plugins/grad-companion-plugin/skills/run-provenance/SKILL.md` |
| 运行 | `plugins/grad-companion-plugin/skills/thesis-cn/SKILL.md` |
| 运行 | `plugins/grad-companion-plugin/skills/weekly-brief/SKILL.md` |
| dev 维护 | `maintenance/grad-companion-plugin/TODO.md` |
| dev 维护 | `maintenance/grad-companion-plugin/evals/guidance-cases-2026-10-19.md` |
| dev 维护 | `maintenance/grad-companion-plugin/reports/guidance-update-2026-10-19.md` |

共18个运行文件、3个维护文件。没有复制个人身份、偏好、私有笔记、完整试读范文或平台工程文档进插件；临时操作脚本及恢复副本不在交付清单内。

## 验证与审查

1. 关联技能同步后，在原仓库 dev 执行 `python -B maintenance/grad-companion-plugin/evals/test_reading_upgrade.py`，`GRAD_PLUGIN_ROOT` 指向本次插件，`GRAD_EVAL_TEMP` 指向专用临时目录，`PYTHONDONTWRITEBYTECODE=1`。**35项全部通过**。合成记录和模拟网络仅用于测试，没有读取或改写个人研究记录。
2. 导读规则四个有限合成响应检查普通导读、快筛、摘要不足和局部公式追问；最终关联技能另做四组合成衔接桌面推演。输入、输出与边界见[探针记录](../evals/guidance-cases-2026-10-19.md)。年份不决定深度、简单 core 不加长等另作规则一致性检查，没有冒充额外动态评测。
3. 独立内容审查核对最终关联技能与命令的增量、上下文及 grad-radar 契约，无阻断项。主会话核对范围、引用和分支文件清单；脚本测试不验证中文教学效果，提示词层桌面推演也不保证所有模型的运行时行为。

保留此前获认可的导读主线，没有新增给用户试读的论文范文。后续根据真实使用中的具体问题调整，不把源码提交或规则审查当作安装生效和教学效果全面验收。
