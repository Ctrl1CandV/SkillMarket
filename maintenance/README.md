# maintenance

维护资料目录：每个技能/插件一个子目录，内含评估与优化报告（`reports/`）、测试记录（`evals/`）、历史版本存档（`archive/`）及各自待办（`TODO.md`）。本目录在 **dev 分支**维护；main 分支只保留技能、插件与 README。

## 目录

| 目录 | 内容 |
|---|---|
| [de-ai-flavor](de-ai-flavor/) | 通用化调整报告、模型试跑与结构检查脚本、改版前完整存档（含 `agents/openai.yaml` 与历史来源记录） |
| [readable-reply](readable-reply/) | 收录时的行为试跑记录、安装前旧版存档 |
| [frontend-craft](frontend-craft/) | 布局优先方案与两轮审查报告、v0.1/v0.2 检查脚本与小样、0.1.1 完整存档、浏览器检查记录 |
| [grad-companion-plugin](grad-companion-plugin/) | 上游远端核验报告、分析总结方向优化策略（待确认）、hosts 宿主适配层与原 README 存档 |
| [agent-parliament-plugin](agent-parliament-plugin/) | 上游核验报告、去 MCP 化交付报告、结构与流程模拟检查 |
| [mineru](mineru/) | 已安装副本核验报告（暂不收录） |
| [skill-search](skill-search/) | 技能搜索方法的设计审查、触发条件与范围优化记录、待办 |

页面样例 `evening-radio.html`、`field-notes.html` 位于 dev 分支仓库根目录，由 frontend-craft v0.2.0 生成。

## 当前待办

- **frontend-craft**：布局优先对照实验待执行，方案见 [reports/frontend-layout-strategy.md](frontend-craft/reports/frontend-layout-strategy.md)；样例视觉验收待补。
- **grad-companion-plugin**：论文与综述分析总结方向的优化方案待确认后实施，见 [TODO](grad-companion-plugin/TODO.md)。
- **agent-parliament-plugin**：真实宿主安装试用与上游许可正文确认，见 [TODO](agent-parliament-plugin/TODO.md)。
- **mineru**：修复中文 data_id、复杂页码与离线模式回落云端等问题并重验后，再评估收录，见 [TODO](mineru/TODO.md)。
- **skill-search**：触发条件与范围已按用户审查优化，待真实使用观察，见 [TODO](skill-search/TODO.md)。

## 约定

- 技能与插件目录只放运行所需内容；报告、评测、旧版与本目录对应文件夹存放。
- 2026-10-04 按用户决定移除插件中的宿主适配文件（grad-companion 的 `plugin/` 包裹层、`manifest.json` 与 `LICENSE`；agent-parliament 的 `.zcode-plugin/plugin.json`），仓库只保留技能与命令本身；各报告中记录的清单结构为当时验证状态。
- SpecialtyCourses 是 de-ai-flavor 的经验来源，不是其适用范围限制；可复用方法推广到其他文本，个人声线与项目约定不强加给别的作者。
- 第三方素材保留来源与许可记录；不收入凭据、私人笔记、运行缓存。
- 历史报告中提到的文件路径可能指向重组前位置，以本目录现状为准。
