# SkillMarket 开发计划

更新：2026-10-28。依据本次会话及[此前确认的计划](https://chatgpt.com/space/page_fd8423620ef08191a6b6ef71798b3fd0)。本文在 dev 维护，记录优先级与进入下一阶段的条件；安装状态与 Git 提交状态分别记录。

| 优先级 | 能力 | 本轮状态与交付 | 下一步条件 |
|---|---|---|---|
| 当前主线 | docvision | 0.1.0-rc.1：本地 MinerU/PaddleOCR + 远程适配器、统一输出契约、conda/uv 环境引导；[设计与实测](docvision/reports/initial-design-2026-10-28.md) | 有有效 MinerU token 与 GLM/Mistral/Gemini key 时补真实端到端；8 GB 长文档与 5 类真实样本验收后再考虑进 main |
| 当前主线 | product-design + frontend-craft | product-design 0.1.0 与 frontend-craft 0.4.2 的运行资源已提交到本地 main/dev；声音艺术页获认可，两次管理页均未获认可，见[拆解](frontend-craft/evals/management-v042-review-2026-10-25/analysis.md)和[记录](product-design/reports/initial-design-2026-10-25.md) | 等用户阅读报告并给出思路，再开展优化；本轮不继续改样式，检查通过不证明视觉收益 |
| 近期 | experiment-design | 增加 grad-companion 内的[0.1.0 初版](../plugins/grad-companion-plugin/skills/experiment-design/SKILL.md)，覆盖最小判别实验、预算与衔接；[取舍与验证](experiment-design/reports/initial-design-2026-10-24.md) | 用用户一个真实研究想法检查可执行性、公平性、判别力和预算，依据实际缺口修订；本轮未获真实研究输入 |
| 条件具备后 | skill-eval | 仅[立案](skill-eval/PROPOSAL.md)，本轮不实现 Skill、评测脚本或平台 | 先明确真实任务、可比较基线、质量与成本口径，以及用户愿意投入的评测预算 |
| 后续 | academic-writing | 计划事项，未实现 | 有实际论文目标、材料和实验积累时，组织贡献—证据—逐节论证；复用 write-with-judgment 与 run-provenance，不重复写通用润色器 |
| 后续 | backend-reliability | 计划事项，未实现 | 从真实后端项目的并发、性能、数据一致性或故障问题起步，接入 agent-parliament；不预造通用平台 |

experiment-design 位于科研插件内，承接 idea-ledger 的想法与 run-provenance 的实际记录；它不要求这两个技能安装后才可使用。后续可单独复制该技能目录使用，不维护两份运行源。

本轮不纳入环境排障、订阅管理或额外科研技能。既有插件待办仍在各自 maintenance 目录；本表不默默取消或提前承诺它们。
