# 方法参考与取舍

## 高校阅读方法与开放学术元数据（2026-10-12）

本节依据公开的一手方法指导与数据文档。迁移的是可复用的读法、核查口径和资料组织，课程配额、学校声誉与数据库分数不能代替论文内容验收。

| 来源 | 本插件采用什么 | 使用限制 |
|---|---|---|
| Waterloo S. Keshav，[How to Read a Paper，UCSD 课程托管版](https://cseweb.ucsd.edu/~dstefan/cse227-spring22/papers/keshav%3Ahow.pdf) | 分阶段定位问题、阅读机制与证据、重建论证；从近期相关研究、参考与正式 proceedings 扩展候选 | 三遍是按需要加深的读法，不要求每篇全精读，也不把推演当复现实验 |
| [Stanford CS224U 项目指导](https://web.stanford.edu/class/cs224u/projects.html) | 围绕共同问题做比较/对照，解释冲突、局限和未来问题，准确保留文献信息 | 不搬用课程的固定篇数、页数、作业格式；多篇综合不等于读一篇综述 |
| [CCF 第七版推荐目录及说明](https://www.ccf.org.cn/Academic_Evaluation/By_category/) | 查询实际学科、期刊/会议与发表轨道；2026-03-31 发布，4 月修正勘误，未来按查询时版本 | 目录中会议指正式 Full/Regular 长文，其他轨道不能套等级；刊会级别不是单篇内容质量认证 |
| [OpenAlex Works 属性](https://help.openalex.org/data/works/attributes/) | 保存 cited_by_count 的来源/日期；按类型、年份和领域理解 fwci/归一化百分位；核 DOI、年份、公开版本及已知撤稿标记 | 只用实际返回字段，缺值记未知；归一化影响不是正确性。API/访问要求按当前文档，未取得数据不填估计数 |
| [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | 核 DOI 与出版元数据，交叉对照发表信息及更新 | 元数据依出版方提交，不能单凭条目认定正文已核或同行评审完成 |
| [dblp 官方开放元数据说明](https://blog.dblp.org/2026/04/29/results-and-findings-from-the-2025-2026-dblp-user-survey/) | 计算机论文题名、作者、出处与版本关系的辅助书目核查 | 不把 dblp 当引用排名；具体记录仍核出版/接收来源。FAQ 本轮受访问限制，未作全文核验 |
| [DORA 原声明](https://sfdora.org/read/) | 元数据筛选后继续做内容判断，避免用刊物指标代替单篇成果的质量 | 不抹掉用户明确要求的刊会/引用硬条件；将筛选目的与内容质量判断分开 |

以上常见筛选窗口、按场景调整的属性优先顺序、来源/成熟度标签和压缩对账清单是本插件综合这些方法并结合用户要求形成的设计，不宣称高校给出了统一推荐算法。顶刊顶会与近三年作为常见起点，经典学习重基础与长期影响，时效应用重近期和设置匹配；具体任务的硬条件不自行放宽。动态引用量、目录及发表状态每次选文都重新核验，不能把这次方法文档核验当成具体候选的核验。

## 既有开源方法参考（2026-10-09 记录）

核验日期：2026-10-09。通过 GitHub 读取原始技能/代码，未安装参考项目。以下是方法参考，不把其介绍、示例或性能声明当本插件实测结果。

| 原始来源 | 核验文件/文件 SHA | 在本插件中的应用 |
| --- | --- | --- |
| [K-Dense literature-review](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/literature-review/SKILL.md) | SKILL.md `5178dce6419cee412155e7b9dd523d5b2ef703f5`；[core_workflow](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/literature-review/references/core_workflow.md) `6a0bab11cd67d05dd683576f512b2045d85c826b`；[example_workflow](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/literature-review/references/example_workflow.md) `521308758c8847254edb1d62ad242e982f00dbe5` | 明确问题/范围，扩同义词，摘要后核正文，留下取舍，身份核验与论点支持分开。示例自称 illustrative；本轮不采用系统综述/PRISMA整套流程或其外部服务依赖。 |
| [PaperQA](https://github.com/Future-House/paper-qa/blob/main/src/paperqa/prompts.py) | prompts.py `f830d0c4096360c51e68b55f39d8d20486f1002c`；[README](https://github.com/Future-House/paper-qa/blob/main/README.md) `0b5639921586f03bd1f9d93445af9e0d17f37c48` | 先找问题相关证据再组织答案，带来源和具体设置，证据不足就保留缺口；图表文本不可靠时回实际图像。检索相关片段适合问答，完整综述另做全篇覆盖；未引入向量库、评分或额外模型调用。 |
| [GPT Researcher](https://github.com/assafelovic/gpt-researcher/blob/main/gpt_researcher/prompts.py) | prompts.py `958628026c2fe315ec1714719626875d97ef322c` | 把学习问题拆为可执行的少量查询，利用候选反馈收窄；通用搜索不盲套数据库语法。未采用固定最低字数、固定来源数量或自动报告系统。 |

实现采用原创中文流程与轻量检查，没有复制这些项目的代码。更多接口、云解析和依赖是否必要，在实际任务中再核查。例子只用于解释方法，须标示示意/来源范围；不能用“已核参考项目”代替本插件产物的原文核对。
