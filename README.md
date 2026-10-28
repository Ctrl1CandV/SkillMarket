# SkillMarket

存放自己常用的 skill 和 plugin，把项目里的经验整理成可复用的方法，再根据实际使用持续改进。

- [write-with-judgment](write-with-judgment/SKILL.md)：结合材料、组织、语言和阅读感受，指导新写、实质改稿与审校；现有 de-ai-flavor 继续保留。
- [de-ai-flavor](de-ai-flavor/SKILL.md)：识别空泛、绕口、重复等常见 AI 味问题，改善新写或已有的文稿、页面文案与回复。
- [readable-reply](readable-reply/SKILL.md)：让 AI 回复更容易读懂，避免碎句、过度排版和冗长堆砌。
- [product-design](product-design/SKILL.md)：为新建产品、整体重设计与核心流程调整建立设计依据，把用户任务、真实内容和对象关系转成页面职责、展示重点与表现方向，再衔接界面实现。
- [frontend-craft](frontend-craft/SKILL.md)：依据项目方向完成页面级内容编排、构图、排版、配色和交互细节，并通过实际画面修订；与 product-design 配合，局部精修也可直接使用。
- [grad-companion](plugins/grad-companion-plugin/)：辅助读研期间的论文阅读、研究记录、实验积累与阶段复盘；新增 [experiment-design](plugins/grad-companion-plugin/skills/experiment-design/SKILL.md)，把研究想法转成可执行、有判别力的实验计划。
- [agent-parliament](plugins/agent-parliament-plugin/skills/orchestrator/SKILL.md)：组织规划、质疑、实现、审查与验证，不依赖专用 MCP 服务；可由同一代理顺序执行。
- [skill-search](skill-search/SKILL.md)：针对明确的技能搜索请求或复杂项目中的能力缺口，寻找能改善任务的技能；检查已有能力、读候选正文、分清指标口径，找不到就停止。
- [docvision](docvision/SKILL.md)：0.2.0 正式版，本地批量解析 PDF/图片，按页或裁块精读公式、表格、图表与架构图；支持 PaddleOCR 官方免费额度 API 与私有 .env 凭据，保留原图、页码、bbox 和独立复核结果。
- [presentation-craft](presentation-craft/SKILL.md)：面向论文组会与实验进展，提供 12 种学术样式、科研页型、数据图表选型与表格展示规则及样张；用免费本地工具生成 PPTX 与基本点击动画，检查实际导出与放映。
- [git-governance](git-governance/SKILL.md)：按项目需要选择 Git 工作流，管理分支、文件入库与本地保留、提交、协作、发布和安全清理；区分 Git 机制、团队约定与发布清单。

main 分支保留技能、插件及 README；技能与插件目录只放运行所需的入口、参考、脚本和模板。dev 分支另保留测试记录、优化文档和历史版本，统一放在 `maintenance/` 目录（按技能/插件分文件夹）；两个页面样例（晚间电台、街角植物志）在 dev 分支 `maintenance/frontend-craft/evals/`。

私人资料、真实配置、凭据与一次性测试草稿不提交到任何分支。向 main 整合时只选运行资源与索引变更，先核对完整文件清单，避免把 dev 的 maintenance 一并带入；提交说明写清具体技能、实际变化与必要验证。
