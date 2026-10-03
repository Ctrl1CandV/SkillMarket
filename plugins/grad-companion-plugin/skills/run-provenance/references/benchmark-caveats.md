# benchmark 数字可信度标注（run-provenance，活文档）

> 引用 benchmark 分数时自动附带的已知缺陷提示。**机械提醒，不是质量判定**：命中只说明
> 「这个 benchmark 有已核实的缺陷/混淆案例」，用不用、怎么表述由人决定。
>
> 活文档纪律：新条目必须带一手来源（arXiv id 或官方 issue），禁止凭记忆添加；
> 过时条目标 `superseded: true` 保留不删（上游修复了也要留痕）。

## 条目表（claim_check.py 按此做名称匹配）

| benchmark 关键词 | 一手来源 | 缺陷摘要 | 引用时建议 |
|---|---|---|---|
| SWE-bench | arXiv:2410.06992 | solution leakage：32.67% 的成功 patch 存在问题泄露；过滤后 SWE-Agent+GPT-4 从 12.47% 掉到 3.97% | 报分数时注明用的是哪个子集/版本；主结论若依赖 SWE-bench 分数，至少在 Limitations 提泄露问题与已发布修复 |
| TAU-bench / τ-bench | arXiv:2608.05699（同名撞车） | arXiv 检索首条是同名视频异常理解论文，与 agent 的 τ^2-bench 无关；引用检索易错 | 引用走官方 repo 或确切 arXiv id，不要裸搜标题；参考文献里核对 id 指向 |

## 使用方式

1. **claim_check.py 自动提示**：台账自检时，claim 绑定 run 的 benchmark 名与本表关键词匹配（大小写不敏感的包含匹配）→ 输出附 `benchmark_caveats` 警告。这是唯一被脚本消费的方式
2. **写作/radar 引用时人工核对**：digest 或论文要引用某 benchmark 的公开数字时，查本表是否有该条目

## 不收录的内容（纪律）

- 未经核实的二手吐槽（推文、评论区说法）
- 泛化的「benchmark 都有污染问题」——没有具体数字与来源的一般性怀疑不进表
- 已 superseded 但有历史价值的条目（保留并标注，防止旧稿里的引用失据）
