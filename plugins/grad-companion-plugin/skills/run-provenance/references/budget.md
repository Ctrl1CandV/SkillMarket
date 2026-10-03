# 评测预算参照（run-provenance）

> 数字只有两类：**带 arXiv id 的一手数字**（可直接引用）与**用户自己填的**（单价、卡时）。没有第三类。

## 量级锚点：HAL

Holistic Agent Leaderboard（`arXiv:2510.11977`）公开账单：

- 21,730 次 rollout = 9 模型 × 9 benchmark
- 约 **$40,000**、2.5B tokens
- 推算量级（由上两行算术得出，仅作感知）：**单次 rollout 约 $1.8 / 约 11.5 万 token**

含义：学生项目「全量跑」不现实。9 模型 × 9 benchmark 是机构行为；个人的合理规模是 1-3 模型 × 1-2 benchmark × 20-100 task。

## 为什么不能随意砍样本

`arXiv:2607.12338` 研究部分 run 与完整 benchmark 的成对结论一致性，原文要点：
「costly evaluations make partial runs tempting. A task fraction alone does not show whether a partial run supports the same pairwise conclusion as the completed benchmark」——
只按比例砍 task 数**不能保证**保留与全量相同的「A 优于 B」结论。砍样本前先想清楚要支撑的是绝对数字还是成对比较，后者对样本量更敏感。

## 预算工作表（登记前填）

```
task 数 × seed 数 × 单次成本 = 总预算
```

1. 先跑 pilot（3-5 task × 1 seed）确认管线通，再放全量——pilot 的 run 也登记（label 标 pilot）
2. 单次成本：用户填（API 按价目表算 token，本地卡按卡时），脚本不猜
3. seed 数 ≥3 才能报 ±（n=2 的 std 勉强，n=1 只能标 `(n=1)`，见 table_gen）
4. 超预算的信号：预估 token > 数十亿 或 费用 > 四位数美元 → 建议先砍模型数再砍 task 数，最后才砍 seed（seed 决定能不能报 error bar）

## 发布包检查清单（对冲 83% vs 38% 差距）

`arXiv:2608.05179` 审计 24 个 AI Scientist 系统：83% 发布代码，但只有 **38% 发布 seed 或执行 trace**。发布前自查：

- [ ] 代码发布：repo 指向论文里的 commit（不是"最新 main"）
- [ ] 每个 seed 都在 README/脚本里显式列出
- [ ] 关键实验的完整命令行可复制粘贴重跑（从 meta.json 的 cmd 字段来）
- [ ] 随机性来源盘点：Python/numpy/torch seed、CUDA 非确定性、数据 shuffle、温度采样——逐一固定或声明
- [ ] 执行 trace（可选但差异化）：输入输出日志、中间 checkpoint 索引
