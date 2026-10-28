# maintenance

维护资料目录：每个技能/插件一个子目录，内含评估与优化报告（`reports/`）、测试记录（`evals/`）、历史版本存档（`archive/`）及各自待办（`TODO.md`）。本目录在 **dev 分支**维护；main 分支只保留技能、插件与 README。

新增能力的优先级与推进条件见 [开发计划](ROADMAP.md)。

## 目录

| 目录 | 内容 |
|---|---|
| [write-with-judgment](write-with-judgment/reports/revision-0.2.1.md) | 0.2.1 整合取舍与静态审阅记录、0.1.0 完整存档；实际效果待试用 |
| [de-ai-flavor](de-ai-flavor/) | 通用化调整报告、模型试跑与结构检查脚本、改版前完整存档（含 `agents/openai.yaml` 与历史来源记录） |
| [readable-reply](readable-reply/) | 收录时的行为试跑记录、安装前旧版存档 |
| [product-design](product-design/) | [0.1.0 制作与衔接记录](product-design/reports/initial-design-2026-10-25.md)、[用户指导文档原件](product-design/reports/implementation-guide-2026-10-25.md)；已与 frontend-craft 0.4.2 提交至本地 main/dev，效果评价见页面反馈 |
| [frontend-craft](frontend-craft/) | [0.4.2 产品依据衔接](product-design/reports/initial-design-2026-10-25.md)、[0.4.1 四种页面](frontend-craft/evals/current-skill-showcase-2026-10-25/index.html)、[0.4.1 样式组合](frontend-craft/reports/frontend-craft-0.4.1-style-2026-10-25.md)、[0.4.1 样式示意](frontend-craft/evals/style-pair-2026-10-25/index.html)、[0.4 规则重审](frontend-craft/reports/frontend-craft-0.4-diagnosis-2026-10-25.md)、[交互页面对照](frontend-craft/evals/direct-comparison-2026-10-25/index.html)、[反馈记录](frontend-craft/evals/direct-comparison-2026-10-25/README.md)、历次评测存档 |
| [grad-companion-plugin](grad-companion-plugin/) | 上游核验、阅读/选文/综述与场景适配审查、35 项回归与真实清单复核、其余待办及历史存档 |
| [experiment-design](experiment-design/) | 0.1.0 初版方法取舍、合成方案与[提交前独立复查](experiment-design/reports/prepublish-review-2026-10-25.md)；真实研究验收待补 |
| [skill-eval](skill-eval/PROPOSAL.md) | 仅在 dev 立案：启动条件与候选范围，尚未实现 |
| [agent-parliament-plugin](agent-parliament-plugin/) | 上游核验报告、去 MCP 化交付报告、结构与流程模拟检查 |
| [docvision](docvision/) | [0.2.0 正式发布核验](docvision/reports/release-0.2.0-2026-10-28.md)：真实公式/复杂表格 API 对照、专用区域任务、缓存与并发修复、完整回归；8 GB 与规模准确率待补 |
| [mineru](mineru/) | 已安装副本核验报告（暂不收录） |
| [skill-search](skill-search/) | 技能搜索方法的设计审查、触发条件与范围优化记录、待办 |
| [presentation-craft](presentation-craft/) | 免费原生 PPTX 与基本动画方案审查、六种风格方向、脚本回归及示例源稿、待办 |
| [git-governance](git-governance/) | Git 官方来源核验、隔离仓库中的 9 项操作语义检查与场景复核记录 |

页面样例 `evening-radio.html`、`field-notes.html` 位于 [frontend-craft/evals/](frontend-craft/evals/)，由 frontend-craft v0.2.0 生成。

## 当前待办

- **product-design / frontend-craft**：0.2.0-rc.1 / 0.5.0-rc.1 的实施、比较、用户反馈和核查已收尾，按用户随后授权将运行变更提交到 main/dev、维护归档仅留 dev，见[收尾记录](frontend-craft/upgrades/2026-10-26/reports/closeout.md)。[阅读反馈](frontend-craft/upgrades/2026-10-26/reports/user-feedback-2026-10-26.md)认可两版布局、认为差距不明显，略偏向旧版标题层级；原终审 INSUFFICIENT_EVIDENCE 与整体视觉提升未证实的事实保留。原包已归档、临时服务与日志已清理，完整入口见[本轮归档](frontend-craft/upgrades/2026-10-26/README.md)和 [TODO](frontend-craft/TODO.md)。
- **grad-companion-plugin**：三项阅读优化已实施，真实使用与其余旧方案待办见 [TODO](grad-companion-plugin/TODO.md)。
- **agent-parliament-plugin**：真实宿主安装试用与上游许可正文确认，见 [TODO](agent-parliament-plugin/TODO.md)。
- **docvision**：0.3.0 只保留本地两引擎与 PaddleOCR 官方 API：首次使用询问远程密钥、拒绝后持久本地、模型固定路径、中间文件回收项目内；Gemini/GLM/Mistral/MinerU 云端因无真实 key 已删除，见 [0.3.0 报告](docvision/reports/scope-consent-0.3.0-2026-10-28.md) 与 [TODO](docvision/TODO.md)。旧 `mineru` 副本由 docvision 取代，历史报告保留。
- **mineru**：修复中文 data_id、复杂页码与离线模式回落云端等问题并重验后，再评估收录，见 [TODO](mineru/TODO.md)。
- **skill-search**：触发条件与范围已按用户审查优化，待真实使用观察，见 [TODO](skill-search/TODO.md)。
- **presentation-craft**：原生动画的实际放映验证、真实任务风格观察及按需 Slidev 导出验证，见 [TODO](presentation-craft/TODO.md)。

## 约定

- 技能与插件目录只放运行所需内容；报告、评测、旧版与本目录对应文件夹存放。
- 2026-10-04 按用户决定移除插件中的宿主适配文件（grad-companion 的 `plugin/` 包裹层、`manifest.json` 与 `LICENSE`；agent-parliament 的 `.zcode-plugin/plugin.json`），仓库只保留技能与命令本身；各报告中记录的清单结构为当时验证状态。
- SpecialtyCourses 是 de-ai-flavor 的经验来源，不是其适用范围限制；可复用方法推广到其他文本，个人声线与项目约定不强加给别的作者。
- 第三方素材保留来源与许可记录；不收入凭据、私人笔记、运行缓存。
- 历史报告中提到的文件路径可能指向重组前位置，以本目录现状为准。
