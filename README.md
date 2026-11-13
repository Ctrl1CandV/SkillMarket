# SkillMarket

存放自己常用的 skill 和 plugin，把项目里的经验整理成可复用的方法，再根据实际使用持续改进。

- [write-with-judgment](write-with-judgment/SKILL.md)：结合材料、组织、语言和阅读感受，指导新写、实质改稿与审校；现有 de-ai-flavor 继续保留。
- [de-ai-flavor](de-ai-flavor/SKILL.md)：识别空泛、绕口、重复等常见 AI 味问题，改善新写或已有的文稿、页面文案与回复。
- [readable-reply](readable-reply/SKILL.md)：2.0.0，让任何 Agent 的回复先给答案、删掉铺垫与重复、少用标题加粗，更容易抓住重点；附可粘进全局指令的短版。
- [product-design](product-design/SKILL.md)：为新建产品、整体重设计与核心流程调整建立设计依据，把用户任务、真实内容和对象关系转成页面职责、展示重点与表现方向，再衔接界面实现。
- [frontend-craft](frontend-craft/SKILL.md)：0.6.0，依据项目方向完成页面级内容编排、构图、排版、配色和交互细节，并通过实际画面修订；先按页面类别选尺度和做法，附工作台、数据看板、设置、图鉴检索四个可直接改的起步样例，以及三种宽度截图并量出问题的检查脚本；与 product-design 配合，局部精修也可直接使用。
- [grad-companion](plugins/grad-companion-plugin/)：辅助读研期间的论文阅读、研究记录、实验积累与阶段复盘；新增 [experiment-design](plugins/grad-companion-plugin/skills/experiment-design/SKILL.md)，把研究想法转成可执行、有判别力的实验计划。
- [agent-parliament](plugins/agent-parliament-plugin/skills/orchestrator/SKILL.md)：组织规划、质疑、实现、审查与验证，不依赖专用 MCP 服务；可由同一代理顺序执行。
- [skill-search](skill-search/SKILL.md)：0.3.0，针对明确的技能搜索请求或复杂项目中的能力缺口，寻找能直接使用、或开发时值得借鉴的技能；检查已有能力、读候选正文、分清指标口径与许可，找不到就停止。
- [docvision](docvision/SKILL.md)：0.5.2，数字 PDF 批量筛读与本地 OCR，筛读时会提示页面上看不见的文字；疑难区域按需用 PaddleOCR API 对照纠错，图表与架构图实际看图。保留原稿和有依据的校正，支持云任务续接、文献搬家、环境验收与回退。
- [imagecraft](imagecraft/SKILL.md)：0.3.3，辅助型生图：文章配图、页面方案比较、无字素材，也为没有生图能力的宿主补上出图链路。首次使用先判断本机硬件（能分清“没有显卡”和“显卡被沙箱挡住”）并复用现有 ComfyUI，显卡正被别的任务占用时不提交：FLUX.2 klein 默认用于极速素材与参考编辑，Z-Image Turbo 可选用于短中文标题；本机不合适时用官方 Codex 订阅脚本出图（需授权，一次一张）。内容要精确或还要反复修改时改用 HTML/SVG/TikZ。固定权重来源与哈希，实际看图验收，产物放项目 `.imagecraft/` 便于清理。
- [presentation-craft](presentation-craft/SKILL.md)：0.4.0，面向论文组会与实验进展，提供 12 种学术样式、科研页型、数据图表选型与表格展示规则及样张；用免费本地工具生成 PPTX 与基本点击动画，检查实际导出与放映。结构审查会标出字号过小、标题不到正文两倍和中文未标语言的页面，渲染脚本从实际导出里找出行首标点、拆开的词等断行问题；缺渲染器时只做一次常规安装尝试，装不了就如实说明未验证。
- [video-craft](video-craft/SKILL.md)：0.3.0，用代码做能直接用的视频（科普、产品宣传、数据故事、教程）：先找让观众自己看懂的核心画面，再定质感、镜头与节拍，用可逐帧定位的网页实现，音乐、音效和配音与画面共用一张时间表；自带渲染、声音合成、混音检查与配音计时工具，以及三个完整示例，按联系表、切点帧条和响度曲线实际看过再交付；联系表会标出画面冻住的段落。
- [git-governance](git-governance/SKILL.md)：1.1.0，按项目需要选择 Git 工作流，管理分支、文件入库与本地保留、提交、协作、发布和安全清理；提交前按固定清单列出每个路径的去向，无仓库约定时用个人默认提交写法；区分 Git 机制、团队约定与发布清单。

main 分支保留技能、插件及 README；技能与插件目录只放运行所需的入口、参考、脚本和模板。dev 分支另保留测试记录、优化文档和历史版本，统一放在 `maintenance/` 目录（按技能/插件分文件夹）；两个页面样例（晚间电台、街角植物志）在 dev 分支 `maintenance/frontend-craft/evals/`。对已有技能逐个优化的计划、现状和交接说明在 dev 分支 `maintenance/optimization/HANDOFF.md`。

私人资料、真实配置、凭据与一次性测试草稿不提交到任何分支。向 main 整合时只选运行资源与索引变更，先核对完整文件清单，避免把 dev 的 maintenance 一并带入；提交说明写清具体技能、实际变化与必要验证。
