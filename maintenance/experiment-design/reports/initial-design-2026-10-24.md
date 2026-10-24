# experiment-design 0.1.0 初版设计记录

日期：2026-10-24。本轮目标是补上“研究想法 → 可执行、有判别力、预算可承受的实验方案”，不是替用户运行研究实验。没有收到真实研究问题、代码或数据，当前为可试用初版，真实项目效果尚未验收。

## 放置与职责

运行源放在 `plugins/grad-companion-plugin/skills/experiment-design/`，而非新增另一份顶层技能。它属于 grad-companion 的科研链条，已有 run-provenance 明确将实验设计方法留给它。技能可独立复制使用，不强依赖插件内的 idea-ledger、run-provenance 或其他统计技能。

| 文件 | 用途 |
|---|---|
| `SKILL.md` | 核心设计判断、预算、交付和与现有台账的职责边界 |
| `references/measurement.md` | 有重复、分组、统计、泄漏或主观评审时按需使用 |
| `assets/experiment-plan.md` | 需要持久化/执行交接时可裁剪的计划模板；简单讨论不强制填表 |

不新增实验调度、GPU 管理、统计脚本或台账脚本。实际 run/claim 继续由 run-provenance 登记，idea 状态仍由人决定。方案中的估计、作者结果与计划都不得成为本人的运行证据。

## 调研与选择性吸收

先读取原会话和[确认的开发计划](https://chatgpt.com/space/page_fd8423620ef08191a6b6ef71798b3fd0)，再读本地 idea-ledger、run-provenance 与现有维护约定。以下外部材料于 2026-10-24 核验；未复制上游代码、模板或整段指令。

| 一手来源 | 吸收的机制 | 针对当前用途的改造/不采纳 |
|---|---|---|
| [K-Dense scientific-agent-skills / experimental-design](https://github.com/K-Dense-AI/scientific-agent-skills/blob/a92663a0214b3b9fa1ba6b958284ffd919c00a0c/skills/experimental-design/SKILL.md)（读到 1.5） | 先说明实验单位与响应，再处理混杂、独立重复、分块和运行次序；避免伪重复 | 改成任务/文档/仓库/seed 的计算研究情形，不引入湿实验与临床随机分配工具、DOE 环境或强制调用其他统计 Skill |
| [NIST 选择实验设计](https://www.itl.nist.gov/div898/handbook/pri/section3/pri3.htm)、[随机分块设计](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm) | 根据问题、变量和重要干扰因素选结构 | 将时间/机器/批次纳入必要时的控制，不要求每个小问题遍历完整 DOE 分类 |
| [NeurIPS Paper Checklist](https://nips.cc/public/guides/PaperChecklist) 第 6—8 项 | 明确实验设置、误差条对应的波动来源、单次及总计算资源 | 前移到计划与执行交接中，加入先导/调参/失败成本；不把投稿清单整体塞入技能，也不硬编码 seed 数 |
| [scikit-learn Common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) | 数据先划分，预处理/特征选择不使用测试信息；随机性与重复比较需明确 | 扩展为计算研究的数据/任务划分与提示词调参边界，分析不绑定 scikit-learn |

K-Dense 的[GitHub 仓库元数据](https://api.github.com/repos/K-Dense-AI/scientific-agent-skills)本次返回 54,395 stars、4,791 forks（动态快照），说明值得作为有传播基础的候选检查；它们既不是论文引用数，也不是该单一 Skill 有效性的证据。没有将项目宣传中的用户数量当成已独立核实事实。固定提交来自该文件最近提交查询，全文与该版本片段已读。

## 本地适配的关键决定

- 从“想证明有效”转成可区分的解释，明确何种对照能排除多花预算、额外输入或更多调参造成的差异。
- 给执行者可开展的最小轮次与条件式扩展，不默认建立大而全的论文实验矩阵。
- 缺少单次费用或方差时给先导与计算方式，不虚构机器、成本、效应量或统一重复次数。
- 统计细节单独按需加载，核心仍保留独立单位、泄漏、失败分母与证据不足这几个会影响设计的判断。
- 计划只写已有事实与建议，明确可执行/草案/探索状态；无真实命令时交代缺口，避免造一个看似能运行的入口。
- 输出路径适应项目。简单讨论不额外落盘；持久化用可裁剪模板，不新增必须维护的状态系统。

## 验证与限制

- 已运行 skill-creator 的 `quick_validate.py`：通过。检查 frontmatter、命名与未完成脚手架；这不证明方法效果。
- 2026-10-25 提交前复查以实际交付为准：运行目录包含上述 3 个文件，不含 `agents/openai.yaml`。已核对 UTF-8、文件尾换行、尾空格和本地链接；此前关于四文件及 UI 字段的表述已更正。Skill 的发现信息位于 `SKILL.md` frontmatter。
- 行为检查使用独立代理读取候选 Skill 完成一个未提供预期答案的合成请求；实际结果与评价记录于 [probe-2026-10-24.md](../evals/probe-2026-10-24.md)。这是一次方案生成检查，不是训练、API 评测或真实科研验证。
- 本轮没有改现有台账格式、启动训练、调用付费模型进行研究实验、安装全局技能或发布插件。

真实验收仍待用户提供一个研究想法及可用材料：检查第一轮能否按入口实际执行，对照是否公平、结论是否可区分、预算是否符合测得成本。后续只依据实际失效补规则；不以合成方案或格式检查宣称已提升科研成功率。

关联：[总计划](../../ROADMAP.md)、[skill-eval 仅立案](../../skill-eval/PROPOSAL.md)。
