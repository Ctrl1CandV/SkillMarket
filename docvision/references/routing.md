# 路线与取舍

本文记录 2026-10-28 的调研与实测。模型、价格、额度会变；把这里当“怎么选”的依据，不要当永久承诺。实测机器：RTX 4070 Ti SUPER 16 GB、32 GB RAM、Windows 10、Python 3.12。其他机器速度会不同。

## 本轮优先路线

数字 PDF 批量筛读用 core 的 text-local（auto + fast）；需要 OCR 布局时用 MinerU standard，economy/basic 待同页对照再选；关键区域用 `triage` + `refine` 实际看图。小样本没有显示 API 的精度优势，现将它定位为疑难区域的纠错候选来源，需显式选择 PaddleOCR API、安装级同意与本次 `--allow-remote`。auto 不自动送云端；图形解释由当前对话视觉能力实际看图，或使用本机 loopback 视觉服务。见 [混合精读](hybrid-reading.md)。

## 一句话路线

- **默认本地 MinerU**：完整文档、公式、表格、图片、长期使用，8 GB 只是规划起点，需用真实文档验证标准档。
- **本地 PaddleOCR-VL**：更轻（0.9B）、元素级准确率高、适合单页/截图/图表；需要 PaddlePaddle GPU 环境，安装比 MinerU 重。
- **远程 PaddleOCR 官方 API**：唯一云端 OCR。疑难公式/表格裁图的第二份转写，用于辅助纠错，不能默认比本地正确；额度以账号为准。
- **本地 OpenAI 兼容 VLM**：Ollama/vLLM 上的视觉模型，适合截图和单页图形解释；没有布局管线时不要期待整本论文的稳定结构。

## 为什么默认 MinerU

MinerU 4.0 把“解析、文档库、服务”合成一套 CLI，`mineru-kit parse --format zip` 一次给出：

- `markdown.md`
- `middle_json.json`（按页、块、bbox、阅读顺序）
- `structured_content.json`
- `images/`（表格/图表区域图）

这正好是 AI 需要的“可读正文 + 可定位结构 + 可看图”的组合。[官方硬件表](https://github.com/opendatalab/MinerU#model-engines-with-extras)按后端区分要求：基础安装的 ONNX + llama.cpp 标准/高级档以 8 GB 内存为最低参考，CPU 可运行、推荐 Vulkan；PyTorch 等后端的内存和 GPU 要求更高，不能把这些门槛混成所有标准档的统一要求。Windows 基础安装不强制 CUDA。2026-10-29 在 8 GB RTX 4060 Laptop 上，本地标准档 3 页约 30.9 秒，后端为 llama-cpp，详见[评测](evaluation.md)；批量仍先用 `--workers 1`。

注意 MinerU 仓库是“Apache 2.0 + 附加条件”的自定义许可证，模型卡为 Apache 2.0；商用/再分发前读 [LICENSE.md](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md)。

## 为什么保留 PaddleOCR-VL

PaddleOCR-VL-1.6 是 0.9B 的“布局检测 + VLM 逐元素识别”完整管线，官方在 OmniDocBench v1.6 上报 96.33，支持 109 种语言，文本、公式、表格、图表、印章都在同一管线里。它比 MinerU 更轻，单页识别很快；缺点是安装 PaddlePaddle GPU 比装 MinerU 更容易遇到 CUDA/cuDNN 版本问题，PDF 按页输出后需要自己合并。

实测（本机 GPU，conda 环境，PaddleOCR 3.7.0 + PaddlePaddle GPU 3.2.1）：

- 单页 PNG，模型已缓存：约 1.4 秒推理，10 秒进程总耗时。
- 2 页 PDF：约 8.7 秒进程总耗时。
- 首次运行会下载模型；CPU 路径明显慢，不建议作为日常整本方案。

PaddleOCR 的 CLI 在缺少 `python-docx` 时可能在 `save_all` 导出 DOCX 阶段报错，但 JSON/Markdown 已经写出；本技能会保留可用结果并给出警告。安装时已带上 `python-docx`。

## 对比表

| 路线 | 参数量/形态 | 适合 | 主要限制 | 成本/额度（调研日） |
|---|---|---|---|---|
| text-local | core 的 pypdf 文字层 | 数字 PDF 筛读、页定位、为整页精读准备上下文 | 无 OCR、bbox、图表语义；扫描页需另行处理 | 本机 CPU |
| MinerU 4 本地 | 1.2B VLM + 小模型 | 论文、报告、扫描件、公式/表格/图片、整本 | 标准档约 2 GB 模型；硬件要求按后端判断；复杂版式仍需看图 | 免费，占本机算力 |
| PaddleOCR-VL 1.6 本地 | 0.9B | 单页/截图、图表、印章、多语言、元素级 | Paddle GPU 环境较重；跨页结构需合并 | 免费，占本机算力 |
| PaddleOCR 官方 API | 云端 PaddleOCR-VL | 关键公式/表格裁图复核、无本地环境时 | 需上传 + 安装级同意 + `--allow-remote` | 官网公布每日 20,000 页，账号为准 |
| 本地 OpenAI 兼容 VLM | 任意 | 截图、单页图形解释、已有 Ollama/vLLM | 仅 loopback；无布局/阅读顺序；整本弱 | 免费，占本机算力 |

## 按硬件选

| 机器 | 推荐 |
|---|---|
| 8 GB VRAM / 16 GB RAM | MinerU 标准档（llama.cpp Vulkan）或 PaddleOCR-VL GPU；不要同时开两个引擎；复杂文档优先单页/分段 |
| 16 GB VRAM / 32 GB RAM | MinerU 标准/高级档；PaddleOCR-VL GPU；先单并发，测量后再决定双并发 |
| 无 NVIDIA GPU | MinerU 基础/标准档 CPU（慢），或用户同意后走 PaddleOCR 官方 API 的裁图复核 |
| 只有 8 GB 内存 | 优先 core 或 basic；基础安装的 standard 虽以 8 GB 为最低参考，仍需为系统留出余量并先试单页 |

“能加载模型”不等于“能稳定跑完整本”。先用 3-5 页真实样本测速度、显存和输出质量，再决定批量。

## 质量判断

OmniDocBench v1.6（2026-09 榜单）上，TeleOCR 1.2B 96.91、OvisOCR2 0.8B 96.47、PaddleOCR-VL-1.6 96.34、MinerU2.5-Pro 95.75、GLM-OCR 95.22、MinerU-2.5 93.04、dots.ocr 90.77、DeepSeek-OCR 2 90.25。榜单是平均分，不代表你的扫描件、手写、古籍或复杂表格一定如此；也不能据此断定某个模型“全面更好”。真实任务是：用你自己的 3-5 页样本，比较正文缺失、公式、表格、阅读顺序和图表描述，再选默认。

## 不选谁

- Tesseract：快、便宜，但公式/表格/阅读顺序不适合本技能的主要场景；可作为纯文字兜底，不作为默认。
- 只用 `pdftotext`/`PyMuPDF`：有文字层的 PDF 可以，但扫描件、公式、图表不行；本技能 auto + `--tier fast` 用 core 文字层处理这一情况，无需启动 OCR。显式指定 MinerU 时保留它的 flash 路线。
- 通用聊天模型直接“看图说话”：没有 bbox、页码、可复核资产，容易编造；本技能要求输出落盘并检查。

## 依据

- MinerU 4.0.12 README/文档：<https://github.com/opendatalab/MinerU>、<https://opendatalab.github.io/MinerU/>
- PaddleOCR 3.7.0 / PaddleOCR-VL-1.6：<https://github.com/PaddlePaddle/PaddleOCR>、<https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6>
- OmniDocBench v1.6 榜单：<https://github.com/opendatalab/OmniDocBench>
- PaddleOCR 官方 API 与额度：<https://www.paddleocr.ai/main/index.html>
