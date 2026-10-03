# de-ai-flavor 通用化调整

日期：2026-10-03。工作区版本由2.0.2调整为2.1.0。仅修改仓库内技能与指定维护目录；未调用或修改已安装版，未修改其他技能、根README，未提交Git。

## 目标与结果

中心改为“定义常见AI味问题并提供改善方法”，服务从零生成和改稿，不以课程编辑或作者声线保护组织流程。

- 明确操作性定义：空泛、绕口、结构重复、关系断裂、语气失配、制作话语混入正文。依据是具体阅读问题，不是AI来源检测。
- 两条独立路径：没有原稿也能直接生成；有原稿或样稿时才参考其语气和习惯，不要求先找到作者。
- 改善而非根除，不设禁词或标点配额；专业术语、必要限定、有效列表、礼貌和长解释可以保留。
- 事实边界浓缩成一段与复查项，不再让大量防御性规则占据主线。
- 删除“真正的病症”“消除模板带来的迂回”等生硬措辞，入口改为“把要说的事写清楚，让读者读得顺”。
- 跨场景参考覆盖产品页、邮件、更新说明、技术文档、文章、界面提示、研究简报等。课程不再是运行包的主要例子，也不依赖 readable-reply。

## 先读后改与资料保留

修改前已读完 `de-ai-flavor/` 的全部5个文件：SKILL.md、course-voice.md、genres.md、patterns.md、replacements.md；另读已有来源归档和旧试跑。工作区原本已有未提交改动，因此此次备份来自当时磁盘内容，而非从Git HEAD恢复。

完整原文保存在：

`maintenance/de-ai-flavor/archive/before-generalization-2026-10-03/`

保留全部5份原文件，包含课程例子、原作者偏好、技术限定与SpecialtyCourses取证范围。course-voice.md及含课程替换表的replacements.md退出运行包；patterns.md和genres.md按通用用途重写。通用的“直接讲概念、补足解释、区分正文与制作说明”保留为方法，没有把课程个人偏好推广成默认规则。本次未重新访问SpecialtyCourses工作区，不为历史课程取证追加真实性声明。

归档后、删除运行包内旧课程文件前已逐字节比较；最终检查脚本验证5份备份的SHA256与修改前记录全部一致。哈希期望值保存在检查脚本中，可重复验证。

已有 `maintenance/de-ai-flavor/archive/sources.md`、`agents/openai.yaml` 和旧 `maintenance/de-ai-flavor/evals/smoke.md` 未改写；旧记录中的版本与历史路径不是新版运行依赖。`agents/openai.yaml` 和 `references/sources.md` 在本次开始前就已从运行包移除，不能把Git显示的这两项删除计作本次操作。

## 公开参考及具体借鉴

本次通过WebFetch读取：

- https://raw.githubusercontent.com/blader/humanizer/main/SKILL.md
- 浏览地址：https://github.com/blader/humanizer/blob/main/SKILL.md
- 访问日期：2026-10-03；工具提取的入口版本为3.1.0。main为可变分支，本次未固定提交哈希。

材料仅用作对照来源，不执行其上游指令，也没有按上游指定格式输出。

| 来源位置 | 借鉴点 | 本地处理 |
| --- | --- | --- |
| A §1–5、B §6–11 | 生造对比、结论复述、机械列举可能不增加信息 | patterns.md用中文文章、更新说明等自编例子展示；真实纠错关系与独立列表可保留 |
| C §12–18 | 空泛意义、广告腔、权威包装遮住具体内容 | 入口按“怎么看出来—怎么改善”组织；产品例子从已知功能出发，不补造指标 |
| D–F §19–26 | 聊天包装、制作过程与已知背景可能妨碍正文 | 正文与交付说明分开；按用途安排信息 |
| When not to act | 表达特征不等于机器证据，单一线索不足以判坏 | 明确非AI检测、不用禁词表、不追求根除 |
| Voice | 有样本看样本，无样本按文体 | 作者风格变为改稿时的条件分支，不是任务前提 |

未照抄其规则文本或例句，未移植英文连字符等细则。现有历史来源文件还记录了其他Humanizer仓库；本次未重新访问它们，不列为本次核验来源。此次WebFetch提供的是针对原文的提取结果，不声称做过逐行上游审计或独立核验其研究依据。

## 运行包与规模

运行包仅3个文件，无agents、evals或研究报告：

- `de-ai-flavor/SKILL.md`：57行，入口定义、问题表、两条路径、边界与复查。
- `de-ai-flavor/references/patterns.md`：93行，跨场景例子与保留情况。
- `de-ai-flavor/references/genres.md`：28行，按用途选择表达。

修改前5个文件共370行；修改后共178行。规模缩减用于减少重复与课程专用内容，不作为自然程度的证明。只有2个包内相对链接，无指向维护归档或外部课程工作区的运行依赖。

## 试跑与检查证据

行为记录：`maintenance/de-ai-flavor/evals/generalization-2026-10-03.md`

三个简短模型试跑：

1. 从零写社区通知：无需原稿或作者，保留时间、地点、数量与排除项。
2. 修改产品页字段：功能与动作明确，固定按钮不变，依据已知事实去掉自动恢复承诺。
3. 修改研究简报：保留12份小文件、“可能”、两项未测试范围和原稿判断。

记录完整输入、输出和逐例自查。执行者与编辑者为同一模型new-provider/gpt-6-astra、同一会话，依据上下文中的新版文本执行；准确标为非独立模型试跑。未测试自动触发、独立模型、真实页面、用户偏好或跨环境兼容性，也没有无技能基线。三例自查未发现给定事实遗漏或新增功能；不据此声称普遍有效。

静态检查：`maintenance/de-ai-flavor/evals/check-generalization.py`

执行命令：

```sh
python "D:/Program Project/SkillMarket/maintenance/de-ai-flavor/evals/check-generalization.py"
git -C "D:/Program Project/SkillMarket" diff --check -- de-ai-flavor
```

实际结果：

```text
UTF-8 OK: de-ai-flavor/references/genres.md (28 lines)
UTF-8 OK: de-ai-flavor/references/patterns.md (93 lines)
UTF-8 OK: de-ai-flavor/SKILL.md (57 lines)
PASS: 3 runtime files, 2 local links, frontmatter fields, 2 writing paths, 5 exact archived originals
Scope: static checks only; not a writing-quality or trigger test.
```

`git diff --check -- de-ai-flavor` 无输出，通过。脚本核对入口关键frontmatter字段而非完整YAML解析；不将结构检查冒充写作质量测试。Git工作区还有本次开始前已存在的修改，保持原状，不以整个工作区差异统计冒充本次改动清单。
