# venue 规则库（submission-gate）

> **规则会变。** 每条规则标注来源与核对日期；**临近截稿（2 周内）必须回官网复核**，本文件不是权威，是核对起点。发现规则过时就改这里并更新核对日期。

核对日期统一为 2026-08-22（调研定稿）与 2026-08-23（ARR 页面复核）。

## 硬规则表

| venue | 正文页数 | 硬规则（违规代价） | 来源 |
|---|---|---|---|
| ICLR 2026/2027 | 投稿 9 页；rebuttal/camera-ready 放宽到 10 页 | 超页 desk reject；参考文献不计页；**LLM 使用须披露，未披露重大使用可 desk reject**（2026 起新增） | iclr.cc/Conferences/2026/AuthorGuide、iclr.cc/Conferences/2027/CallForPapers |
| NeurIPS 2025 | 9 页含图表 | **缺 paper checklist 即 desk reject**；改边距/字号可 "rejection without further review" | neurips.cc/Conferences/2025/CallForPapers、neurips.cc/public/guides/PaperChecklist |
| ICML 2026 | **8 页** | 不合 policy 者 "rejected without review" | icml.cc/Conferences/2026/CallForPapers |
| ACL/ARR | 长文 8 页、短文 4 页（**不计** ethics considerations 与 Limitations，已复核原文） | **related work 只放附录 = 规避页数限制 = desk reject**；Limitations 强制存在；2024-12 起 egregious checklist 违规可 desk reject | aclrollingreview.org/authors、/reviewerguidelines |
| AAAI | **未取证**（页数规则用前必查官网 CFP） | 已知仅投稿量：AAAI 2026 约 23,000 篇（papercopilot） | ojs.aaai.org 临用自查 |

## 逐项核对清单（按此生成「已自动核对 / 需人工确认」两栏结果）

1. **页数**：有 PDF 且能读页数则自动核对；读不了标「需人工确认」，不猜
2. **checklist 存在性**（NeurIPS 强制；ARR 的 Responsible NLP checklist）
3. **Limitations 存在性**（ARR 强制，且不计页）
4. **related work 在正文**（ARR：只放附录即 desk reject）
5. **匿名性**：正文/PDF 里搜作者名、致谢、基金号、个人 repo 链接、文件元数据（PDF author 字段）
6. **LLM 使用披露**（ICLR 2026 起未披露重大使用可 desk reject；写作辅助一般需披露，以当年 CFP 原文为准）
7. **模板未被篡改**：边距/字号/行距与官方模板一致（需人工比对或 diff 模板文件）
8. **文件大小/格式**：以当年提交系统要求为准

## 审稿与 rebuttal 机制（影响应对策略）

- **ARR 的 AC 只被要求读每个 reviewer thread 里约前两条 author response** → 最强的论点必须放最前面，不要按审稿意见顺序逐条回应
- **reciprocal reviewing 对新人是豁免的**：ICLR 原文「If none of the authors are qualified under this definition, then they are exempt from this requirement」——没有顶会论文的师生组合不必担心
- 无效批评与有效弱点的分类标准见 `arr-h-list.md`（同目录）

## 接收率参照（选投稿线时的心态校准，非决策依据）

| 会议 | 最近一届 | 接受率 |
|---|---|---|
| ICLR 2026 | 19,814 投 | 26.95%（2022 为 3,422 投 / 32.00%，五年投稿量 5.8 倍） |
| ACL 2025 | 8,360 投 | 36.97%，且有 Findings 兜底 |

来源 papercopilot.com/statistics。对首篇论文，ACL/ARR 路线期望产出显著更高，且 ACL 2026 topic 列表第一项即「AI/LLM Agents」。

## 边界

本 skill 只核对明文规则与给出证据，**判定权在人**：输出的是「符合/不符合/需人工确认 + 依据原文」，不是「能中/不能中」。
