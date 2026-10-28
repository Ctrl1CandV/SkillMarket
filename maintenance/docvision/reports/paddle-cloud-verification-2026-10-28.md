# PaddleOCR 官方云端真实验证与收尾

- 日期：2026-10-28（Asia/Shanghai）。
- 目标：补上 0.2.0-rc.1 遗留的唯一阻塞项——用真实 PADDLEOCR_ACCESS_TOKEN 在官方服务验证公式/合并表格裁图，并与本地同图对比。
- 密钥来源：用户自行放入 `maintenance/docvision/.env`（gitignore 覆盖，未提交、未打印）；通过 `--env-file` 显式加载，环境变量别名优先级按 credentials.py 约定。
- 费用与额度：本轮共 3 次真实提交（1 张 PNG + 1 份 2 页 PDF + 1 次公式裁图 refine），其余重复请求命中缓存未再上传。本轮 14:43–14:50 时段调用成功。此前会话模型的额度中断不能作为 Paddle API 额度耗尽的证据；没有观察到真实 Paddle 额度耗尽响应。本记录不构成永久免费承诺。

## 1. 真实云端验证结果

样本：公开 [Attention Is All You Need v7](https://arxiv.org/abs/1706.03762)（SHA256 `bdfaa68d…697`，15 页），取物理页 4、8 组成两页 PDF，覆盖核心公式与合并单元格表格；与前次审查同一来源。

| 路线 | 输入 | 结果 | 耗时 | QA |
|---|---|---|---:|---|
| paddleocr-cloud（真实 token） | attention-p4-p8.pdf（2 页） | 成功，2 页，图资源/页映射正确 | 55.89 秒 | pass |
| paddleocr-local | 同一文件 | 成功 | 38.41 秒 | pass |
| mineru-local standard+ocr | 同一文件 | 成功 | 18.23 秒 | pass |
| paddleocr-cloud refine | p1-b6 公式裁图（300 DPI） | 成功，公式完整 | 4.23 秒 | pass |
| mineru-local refine | 同一裁图 | 成功，公式完整 | 8.86 秒 | pass |

缓存边界已实测：相同 refine 请求第二次返回 `cached: true`，没有重复上传；不同 provider/任务的缓存相互独立（首轮记录 signature 指纹不同）。

## 2. 同图对比（云端 vs 本地）

用 `content.json` 块级文本和 300 DPI 裁图逐项核对，不是只比结构 QA。

### 核心公式（p4，`p1-b6`）

- 云端与本地 Paddle 完全一致：`Attention(Q,K,V)=softmax(\frac{QK^{T}}{\sqrt{d_{k}}})V`。
- MinerU 语义一致，`d_k`、`\frac`、`\sqrt`、转置齐全，另保留 `\tag{1}` 编号。
- refine 裁图重识别（云端）同样完整；初稿未被覆盖，两份结果并存。

### 合并单元格表格（p8，`p2-b1`）

- 表头结构：云端与本地 Paddle 的 HTML 逐字节一致（len=1282），`rowspan="2"`（Model 列）与 4 处 `colspan="2"`（BLEU / Training Cost 分组）全部保留。
- MinerU 同样保留 rowspan/colspan 结构（len=1352），单元格数值一致。
- 三方数值与原图一致：ByteNet 23.75；GNMT+RL 24.6/39.92、2.3×10¹⁹/1.4×10²⁰；Transformer base 27.3/38.1、3.3×10¹⁸；Transformer big 28.4/41.8、2.3×10¹⁹。表格内联 LaTeX（`1.0 \cdot 10^{20}` 等）在云端/本地 Paddle 中保留为公式文本，MinerU 中去掉 `$` 包裹但数值与指数一致。
- 云端裁图与本地裁图（同 bbox、同 300 DPI）目视一致，与源页表格一致；此前一次裁图误用 `p2-b2`（Residual Dropout 段落）是调用方参数选择问题，工具行为正确，按 `p2-b1` 重裁后即为表格。

### 脚注求和公式（p4）

- 云端与本地 Paddle 一致恢复 `q·k = \sum_{i=1}^{d_k} q_i k_i`。
- MinerU（standard+ocr）同样恢复完整求和式，写法为 `\sum_{i=1}^{d_{k}} q_{i} k_{i}`。
- 与前次审查（MinerU auto 档脚注损坏）对比，强制 OCR 仍是修复该类问题的有效手段；三方在这份样本上均正确，不能推断所有论文如此。

结论：在公式与合并表格两类目标上，**云端与本地同图结果一致且与原图相符**；云端 Paddle 与本地 Paddle 输出几乎逐字节相同（同为 PaddleOCR-VL-1.6），符合预期。差异集中在 MinerU 的 LaTeX 风格与表格内联公式写法，语义无损。没有发现云端引入的新错误，也不能据此宣称云端全面更优。

## 3. 全量回归

- `python -m unittest discover -s maintenance/docvision/evals -p 'test_*.py'`：95 项通过（含 credential 解析、hybrid 精读、完整性、本地运行时、Paddle 云端协议 mock）。
- `python maintenance/docvision/evals/check.py`：5 项适配器 mock 通过。
- CLI 实测路径：`convert`（paddleocr-cloud / paddleocr-local / mineru-local）、`refine`（paddleocr-cloud / mineru-local）、`crop`、`read --page/--block`、`verify`；`--env-file` 加载 `maintenance/docvision/.env` 正常，输出与配置未泄露密钥。
- `git status` 中 `maintenance/docvision/.env` 被 `.gitignore` 排除（`!!` 状态），未纳入提交。

## 4. 边界与未验证

- 额度状态是账户政策：本轮时段可用。额度耗尽时的错误映射由 mock 测试覆盖（明确报错、不重试、不静默换付费 provider），**真实服务的额度耗尽错误码未捕获**。会话模型额度与Paddle API额度分开记录。
- 云端调用次数有限（3 次），没有做批量、并发、大文件、长文档或页数上限测试。
- 仍无 8 GB 真机、峰值显存、20–30 页标注集与双并发基准；这些不因本轮云端验证而改变。
- Gemini 图形语义任务仍未用真实 key 验证；本轮 refine 的 formula/table 走 OCR 路线，figure/chart 视觉解释仍需宿主看图或 Gemini。
- 表格对比以块文本与裁图人工核对为主，未做 TEDS/CDM 自动评分。

## 5. 收尾结论

0.2.0-rc.1 的唯一阻塞项（真实 PaddleOCR 云端验证与同图对比）已完成，结果与本地一致。技能可以进入真实使用观察；后续按 [TODO](../TODO.md) 的剩余项推进（8 GB 实测、标注集、Gemini 图形任务），不再以“云端未验证”为由阻塞使用。
