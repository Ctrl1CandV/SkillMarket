# ARR 审稿指南：无效批评（H）与有效弱点（M/T/R/G）清单

来源：aclrollingreview.org/reviewerguidelines（2026-08-23 全文抓取复核，条目均为原文摘录或忠实转述）。
用途：rebuttal 时把审稿意见分类——命中的 H 条是「可反驳的无效批评」，命中的 M/T/R/G 是「须实证回应的有效弱点」。
**使用前注意**：指南会更新，重大 rebuttal 前回官网核对当届版本。

## H1-H17：这些批评不是当然的 weakness（可反驳）

| # | 批评 | 为什么无效（原文要义） |
|---|---|---|
| H1 | 结果不令人惊讶 | Many findings seem obvious in retrospect… 不代表社区已知晓并可用作 building blocks |
| H2 | 结果与我的预期矛盾 | You may be a victim of confirmation bias（确认偏误） |
| H3 | 结果不新颖 | 认为见过类似工作**必须给引用**；复现、分析类贡献在 CFP 范围内，应获公正评审 |
| H4 | 文献里没有先例 | papers that are more novel tend to be harder to publish——审稿人对更新颖的工作往往过度保守 |
| H5 | 没超过最新 SOTA | **SOTA results are neither necessary nor sufficient for a scientific contribution**；工程贡献可在效率/泛化/可解释/公平等维度 |
| H6 | 结果是负面的 | 只发正面结果是已知的领域病态；systematically does not work 是社区需要知道的 |
| H7 | 方法太简单 | The goal is to solve the problem, not to solve it in a complex way；简单方案更不易碎、更可部署 |
| H8 | 没用我偏好的方法论（如深度学习） | NLP 是交叉领域，模型/资源/综述/分析/立场/理论都是合法贡献 |
| H9 | 主题太小众 | A main track paper may well make a big contribution to a narrow subfield |
| H10 | 只在非英语语言上测 | 只测英语的论文同样有此问题；任何语言的单语工作都重要 |
| H11 | 有语言错误 | As long as the writing is clear enough，科学内容优先于文字功夫 |
| H12 | 缺某引用 | 只有该工作在**截稿前 3 个月以上正式发表**（published ≠ arXiv preprint）才算问题；否则属 suggestions。resubmission 只需对比原截稿日前 3 个月以上的工作 |
| H13 | 还能做额外实验 X | 论文只需为**它做出的 claim** 提供充分证据；额外实验属 nice-to-have，放 suggestions 不放 reasons to reject |
| H14 | 应与闭源模型 X 比较 | 只有直接影响 claim 时才合理；test contamination 与闭源模型信息缺失使比较可能无意义 |
| H15 | 应该用另一种做法 | 「我会换个写法」不是 weakness；只有作者的选择**阻碍回答研究问题**或 framing 误导时才成立 |
| H16 | Limitations ≠ weaknesses | 已写进 Limitations 的内容不应直接列为 weakness 或拒稿理由；要说它推翻全文须单独论证 |
| H17 | 引用数少 ≠ 不成立 | Citation count != validity |

## M/T/R/G：这些是有效弱点（须实证回应，不能只靠反驳）

**M 方法问题**：M1 LLM-as-judge 未验证可靠性（Agent 论文几乎必用 judge，高频命中）｜M2 可复现性问题（超参、代码/数据公开）｜M3 未披露的数据质量问题｜M4 模型/benchmark 选择无动机｜M5 假设或证明不完整

**T 数据与发布条款**：T1 数据收集的伦理问题｜T2 许可证/发布条款不清

**R 实验结果问题**：R1 分析问题（误导性统计、p-hacking、**多次试验挑最好（含 prompt tuning）**、基线未调好）｜R2 claim 范围不当（测的样本不代表 claim 的总体）｜R3 把假设当结论 ｜R4 误导性 framing / overclaiming｜R5 **缺统计显著性评估（error bars、置信区间、检验）**与变异因素讨论

**G 一般问题**：G1 研究问题/贡献不清｜G2 依赖坏先例｜G3 相关工作缺失或 misrepresented（与 H12 的区别：这里指表述错误）｜G4 关键术语含糊未定义｜G5 引用与被引内容不符

## rebuttal 使用法

1. 逐条给审稿意见分类：命中 H（可反驳，引用上表原文要义）、命中 M/T/R/G（须给实验/证据/修改承诺）、两者皆非（中性建议，礼貌采纳）
2. **排序服从「AC 只读前两条」现实**：每个 thread 最强的回应放第 1-2 条；无效批评的反驳虽然解气，若同时存在须实证的 R 类弱点，先回应 R
3. 反驳 H 时引用指南原文（AC 与审稿人都知道这份指南），语气是「按指南此条属建议而非弱点」，不是指责审稿人
4. 对 R5（error bar）与 R1（best-of-N）：有 run-provenance 登记的多 seed 数据就直接给表；没有就承诺补跑并给时间点

## 边界

本清单帮助**作者理解与回应**审稿意见。不生成审稿意见、不替用户判断稿件质量。
