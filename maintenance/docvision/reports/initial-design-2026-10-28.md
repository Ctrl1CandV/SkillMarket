# docvision 初版设计与调研报告

- 日期：2026-10-28
- 分支：dev
- 目标：用新技能替代旧的 `mineru` 副本，形成“本地 OCR + 远程 API”两层能力，覆盖文本、公式、表格、图表，并解决旧副本在中文文件名、页码、隐私边界和输出碰撞上的问题。
- 结论：完成 `docvision` 0.1.0-rc.1 的本地/远程统一 CLI、输出契约、环境引导、参考文档和首轮实测；远程 Standard/GLM/Mistral/Gemini 尚未用真实 key 做端到端，不能写成“全部验证通过”。

## 1. 需求拆解

用户要的不是“再包一层 MinerU 命令”，而是：

1. **AI 能用**：给文件路径就能产出可读、可引用、可检查的 Markdown/JSON，而不是一大段不可定位的文本。
2. **本地优先**：8 GB / 16 GB 显存两台机器都能跑；默认不上传。
3. **远程兜底**：本地没环境、复杂版面、批量吞吐时，可切到免费额度/低价 API。
4. **公式、表格、图表**：保留 LaTeX/HTML、区域图、页码和 bbox，能回看页面图。
5. **长期环境**：首次使用能构建隔离、可复现、可回滚的环境，不把依赖塞进技能目录。
6. **隐私边界**：本地失败不能静默转云端；远程必须显式授权。
7. **可维护**：模型/接口会变，技能要能定位版本、降级和排障。

## 2. 调研结论

### 2.1 本地模型

| 候选 | 结论 |
|---|---|
| MinerU 4.0.12 | **默认本地引擎**。`mineru-kit parse --format zip` 一次给 Markdown、middle JSON、structured content、图片；标准档约 2 GB 模型，8 GB+ VRAM / 16 GB RAM；Windows 基础包用 ONNX + llama.cpp Vulkan，不强制 CUDA。 |
| PaddleOCR-VL-1.6 (0.9B) | **可选第二本地引擎**。完整“布局检测 + VLM 逐元素识别”，96.33 OmniDocBench v1.6，109 语言，Apache 2.0；GPU 单页约 1.4 秒（本机），但 PaddlePaddle GPU 安装比 MinerU 重、cuDNN 版本更敏感。 |
| GLM-OCR (0.9B) | 本地可作为 OpenAI 兼容 VLM/官方 SDK 使用；本技能主要接它的远程 API（0.2 元/百万 tokens），没有把 vLLM/SGLang 本地部署写成默认，因为 Windows 上更麻烦。 |
| DeepSeek-OCR 2 / dots.ocr / Chandra / olmOCR | 调研过，但要么显存/依赖更重，要么整本结构/许可证/生态不如 MinerU/Paddle 稳；不纳入首版默认。 |
| Docling / Tesseract | 适合数字版文档/纯文字兜底，不解决公式/表格/图表的主要痛点；不纳入首版主路线。 |

官方依据：

- MinerU：<https://github.com/opendatalab/MinerU>、<https://opendatalab.github.io/MinerU/>、release 4.0.12（2026-10-11）。
- PaddleOCR：<https://github.com/PaddlePaddle/PaddleOCR>、PaddleOCR-VL-1.6 模型卡（2026-05-28）。
- OmniDocBench v1.6 榜单：<https://github.com/opendatalab/OmniDocBench>（2026-09 更新）。
- GLM-OCR：<https://github.com/zai-org/GLM-OCR>、<https://docs.bigmodel.cn/cn/guide/models/vlm/glm-ocr>。
- Mistral OCR 价格：<https://docs.mistral.ai/inference/pricing>。

### 2.2 远程接口

| 接口 | 结论 |
|---|---|
| MinerU Standard | 首选远程完整结果；每日 1000 页最高优先级额度，200 MB/200 页，zip 含 Markdown/JSON/图片；需要 token。 |
| MinerU Agent | 免 token、10 MB/20 页、仅 Markdown；作为小文件预览，不承诺结构/公式/表格。 |
| GLM-OCR | 0.9B，同步 `layout_parsing`，0.2 元/百万 tokens，100 页/50 MB；返回 `md_results` + `layout_details`；中文/表格/手写好。 |
| Mistral OCR | OCR 4.1 $4/1000 页，OCR 3 $2/1000 页；返回页、块、bbox、图片/表格；适合结构化/图表密集。 |
| Gemini | 原生 PDF/图片理解，复杂版面和图表推理强；输出结构不保证，免费层/保留策略随账号变化；需显式授权。 |
| 百度 PaddleOCR 云 | 个人 200 页/企业 1000 页免费测试，之后约 0.05-0.09 元/页；本技能默认走本地 PaddleOCR，未接百度云适配器，避免把额度混为一谈。 |

### 2.3 旧 `mineru` 副本的问题

旧副本核验报告（`maintenance/mineru/`）列出的问题，新技能逐项处理：

- **中文文件名 data_id**：新技能用 `docvision-<sha1>` ASCII 标识；文件名保留中文只用于输出目录。
- **复杂页码**：Agent 明确报错，不静默截断；Standard/本地支持 `2,4-6`，Paddle 用 pypdf 拆页并映射回原页。
- **显式本地却回落云端**：新路由本地失败直接报错，绝不自动上传；远程要 `--allow-remote`。
- **缺失模块**：不再依赖未随包提供的 `splitter/local_engine/chunking/sinks`；所有运行模块在 `scripts/dv/` 内，核心只用标准库。
- **输出目录碰撞**：同名输入加短哈希；`--resume` 按 SHA-256 跳过；`--force` 才复用目录。
- **doctor 把网络错误当 token 有效**：`doctor --probe` 区分 401/A0202 与网络错误；不探测时只显示“已配置”，不声称有效。
- **“每天 1000 页免费”误读**：文档和 `usage` 明确写成“最高优先级额度，超出降优先级”，不作永久免费承诺。

## 3. 设计

### 3.1 名称

`docvision`：不绑定 MinerU，覆盖“文档视觉理解”；CLI 同名，便于 AI 和用户记忆。

### 3.2 两层、多后端

```text
本地层
  mineru-local        MinerU 4（默认）
  paddleocr-local     PaddleOCR-VL 1.6（可选）
  local-vlm           Ollama/vLLM 的 OpenAI 兼容视觉模型（截图/单页）

远程层
  mineru-cloud        Standard API
  mineru-agent        Agent 轻量 API（预览）
  glm-cloud           GLM-OCR
  mistral             Mistral OCR
  gemini              Gemini 原生 PDF/图片
  openai              OpenAI 兼容（可接 OpenRouter/SiliconFlow 等）
```

自动路线：本地 MinerU → 本地 Paddle → 本地 VLM → 远程（仅在 `--allow-remote` 且配置 key 时）。远程失败不自动换另一家，避免重复上传/计费。

### 3.3 统一输出

每次转换一个目录：

```text
<out>/<doc>/
  <doc>.md
  content.json   # 页/块/bbox/资产索引
  meta.json      # 来源、引擎、隐私、耗时、警告
  qa.json        # 确定性检查
  assets/
  pages/ crops/ raw/  # 按需
```

`content.json` 的 page 从 1 开始，bbox 归一化；块类型统一为 `heading/text/table/formula/image/chart/list/code/other`。这样 AI 可以按页读、按块裁剪、引用页码，而不是只能吞整篇 Markdown。

### 3.4 环境

- 技能目录只放代码/参考/约束；运行时在 conda 或 uv 隔离环境。
- `setup --profile mineru|paddle|core|all`，默认 conda；支持 `--manager uv`。
- MinerU 模型在 `~/.mineru`；Paddle 在 `~/.paddlex`；配置只存路径，不存 key。
- 版本基线：Python 3.12、MinerU 4.0.12、PaddleOCR 3.7.0、PaddlePaddle GPU 3.2.1、PaddleOCR-VL 1.6。
- 更新/回滚：小版本升级 + 3-5 页真实样本验收；`pip freeze`/`conda env export` 留档。

## 4. 实现清单

- `docvision/SKILL.md`：路由、命令、阅读纪律、隐私、失败降级。
- `docvision/references/`：routing、local-setup、remote-apis、output-contract、reading、troubleshooting、evaluation。
- `docvision/scripts/docvision.py` + `dv/`：
  - `cli.py`：convert/read/pages/crop/verify/doctor/providers/env/usage/setup。
  - `detect.py`：文件检查、路线选择、隐私标记。
  - `providers/`：MinerU 本地/云、PaddleOCR 本地、GLM、Mistral、Gemini、OpenAI 兼容。
  - `output.py`：统一契约、资产重写、页/块 id。
  - `verify.py`：空正文、页号、图片引用、表格/公式平衡、重复页。
  - `read.py`：按页/块读取、渲染、裁剪、总览图。
  - `setup_cmd.py`：conda/uv 环境引导、模型下载、配置写入。
  - `doctor.py`：引擎/模型/GPU/密钥/探针。
- `scripts/constraints/`：core/mineru/paddle 的版本记录。

## 5. 实测记录

测试环境：Windows 10、RTX 4070 Ti SUPER 16 GB、32 GB RAM、Python 3.12.9、conda 25.1.1。

| 项 | 结果 |
|---|---|
| MinerU 4.0.12 安装 | 成功；`mineru-kit parse --format zip` 标准档 2 页合成 PDF 约 13 秒（含模型加载），输出 Markdown/middle JSON/图片 |
| MinerU 本地页范围/中文名 | 成功；中文输出目录正确；同名输入加哈希 |
| PaddleOCR 3.7 + PaddlePaddle GPU 3.2.1 | conda 环境成功；单页 PNG GPU 约 1.4 秒推理、10 秒总耗时；2 页 PDF 约 8.7 秒 |
| Paddle 逐页 JSON/Markdown 合并 | 成功；`--pages 2` 映射回原页 2 |
| MinerU Agent API | 2 页合成 PDF 上传/轮询/下载成功；确认仅 Markdown、无图片/bbox |
| MinerU Standard API | **未完成**：当前 `MINERU_TOKEN` 返回 401/A0202；用 mock 服务器验证了上传/轮询/zip 解析路径 |
| GLM/Mistral/Gemini/OpenAI | 无真实 key；用本地 mock HTTP 服务器验证响应解析、资产、页/块、输出契约，5 项测试通过 |
| `read/pages/crop/verify` | 本地输出通过；裁剪出表格区域 PNG；`verify` 结果为 pass |
| `resume`/碰撞/中文名 | 通过 |
| 8 GB 显存 | 未实测；按官方门槛推断标准档可跑，但长文档/并发需保守 |

## 6. 已知缺口

1. **MinerU Standard 真实端到端**：token 无效，未验证真实 zip 字段/限流；适配器已按官方文档 + mock 测试。
2. **远程真实 key**：GLM/Mistral/Gemini/OpenAI 只做 schema/mock；真实限流、计费、超大文件、页标记遵守率未验证。
3. **准确率**：没有做 OmniDocBench 或自建标注评测；合成样本只证明流程，不证明论文/扫描件质量。
4. **8 GB 显存/长文档**：未压测峰值显存、100+ 页、并发 2；文档给了保守建议。
5. **Paddle 图表/印章/手写**：未验证；只验证文本/公式/简单表。
6. **Gemini Files API/长 PDF**：未封装；inline 18 MB 以上会报错并提示换路线。
7. **`local-vlm`**：只验证 mock；没有在 Ollama/vLLM 上跑真实视觉模型。
8. **PaddleOCR 云 API**：只写参考，没有适配器；避免和本地 Paddle 混淆。

## 7. 决策与取舍

- 没有把所有开源 OCR 模型都封装：首版只保留两条本地主路线（MinerU、PaddleOCR），其余通过 OpenAI 兼容端点或远程 API 接入，降低维护面。
- 没有把 MinerU 官方 skill 直接复制：官方 skill 很强，但只覆盖 MinerU；本技能要跨引擎、统一输出、远程授权和环境引导。
- 没有把 Tesseract/Docling 作为默认：它们不能很好解决公式/表格/图表；作为未来轻量兜底更合适。
- 没有默认上传：本地失败就报错，让用户决定是否远程；这是旧副本最大的隐私问题。
- 没有承诺“每天 1000 页免费”：按官方“最高优先级额度”表述，避免把额度政策写死。

## 8. 文件与安装状态

- 新增 `docvision/`（运行资源）与 `maintenance/docvision/`（报告/评测/TODO）。
- 本机实际创建：
  - conda env `docvision-mineru`（MinerU 4.0.12）
  - conda env `docvision-paddle`（PaddleOCR 3.7.0 + PaddlePaddle GPU 3.2.1）
  - 配置 `C:\Users\11487\AppData\Roaming\docvision\config.json`
  - 模型 `C:\Users\11487\.mineru\models`、`C:\Users\11487\.paddlex\official_models`
- 未修改旧 `C:\Users\11487\.zcode\skills\mineru`；旧报告保留在 `maintenance/mineru/` 作为历史。

## 9. 下一步

见 [TODO](../TODO.md)。优先顺序：

1. 用有效 MinerU token 跑 Standard 真实样本，核对 zip 字段。
2. 用真实 GLM/Mistral/Gemini key 各跑 1 份中文/英文样本，记录限流/计费/页标记。
3. 在 8 GB 机器上测 MinerU 标准档 20 页、Paddle 单页峰值显存。
4. 建 5 类真实样本的最小评测集，记录失败页；不要用合成样本代替准确率。
5. 根据真实使用决定是否加 PaddleOCR 云、Gemini Files API、RAG 切片。
