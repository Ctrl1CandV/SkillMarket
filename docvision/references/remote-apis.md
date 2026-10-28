# 远程接口

远程是“复杂情况”的出口，不是默认。使用前确认：文件是否可以上传、账号额度是否足够、服务条款是否允许。价格/额度为 2026-10-28 调研值，随时可能变；`docvision usage` 只是提示，不是账单依据。

## 选择顺序

1. **MinerU Standard**：有 token、需要完整 zip（Markdown/JSON/图片）、整本报告；最接近本地 MinerU 的结果。
2. **GLM-OCR**：中文、表格、手写、印章、票据；同步接口，单文件 100 页，便宜。
3. **Mistral OCR**：需要结构化块/bbox、图表密集文档；按页计费。
4. **Gemini**：版面复杂、需要跨页推理/图表解释；输出结构不保证，需自己校验。
5. **MinerU Agent**：没有 token 的小文件预览；只给 Markdown，不保证公式/表格。
6. **OpenAI 兼容**：已有 Ollama/vLLM/SiliconFlow/OpenRouter 等端点时复用；适合单页/截图，不适合整本结构。

## MinerU Standard API

- 入口：`https://mineru.net/api/v4`
- 鉴权：`Authorization: Bearer <MINERU_TOKEN>`；token 在 <https://mineru.net/apiManage/token> 创建。
- 本地文件：`POST /file-urls/batch` 申请上传链接 → `PUT` 上传 → 轮询 `GET /extract-results/batch/{batch_id}` → 下载 `full_zip_url`。
- URL：`POST /extract/task` → 轮询 `GET /extract/task/{task_id}`。
- 参数：`model_version=pipeline|vlm|MinerU-HTML`（推荐 `vlm`）、`is_ocr`、`enable_formula`、`enable_table`、`language`、`page_ranges`（如 `2,4-6`）、`extra_formats`（docx/html/latex）。
- 限制：单文件 ≤200 MB、≤200 页；批量单次 ≤50 个上传链接（文档另有 200 个的说法，按 50 保守使用）。
- 额度：每账号每天 1000 页最高优先级解析额度，超出后降低优先级；这不是“每天只能免费 1000 页”的等价表述，也不是永久免费承诺。
- 输出 zip：`full.md`、`layout.json`（中间结果）、`*_content_list.json`、`*_model.json`、图片；MinerU 4 自建 zip 则是 `markdown.md`、`middle_json.json`、`structured_content.json`。本技能两种都解析。
- 注意：`data_id` 只允许 ASCII 字母/数字/`_-.`，≤128 字符；本技能用哈希生成。`PUT` 上传不要带 `Content-Type`，否则 OSS 签名可能不匹配。
- 隐私：文件会上传到 MinerU 的对象存储/CDN；不要上传敏感材料，除非用户明确同意并确认条款。

## MinerU Agent API

- 入口：`https://mineru.net/api/v1/agent`
- 无 token，按 IP 限频；`POST /parse/file`（签名上传）或 `/parse/url`，轮询 `GET /parse/{task_id}`。
- 限制：≤10 MB、≤20 页；`page_range` 只支持单页或连续范围，不支持逗号；输出只有 `markdown_url`，没有图片、bbox、页结构。
- 适合快速预览/小截图；不要用它承诺公式、表格、图表质量。复杂页码会直接报错，不会静默截断。

## 智谱 GLM-OCR

- 入口：`POST https://open.bigmodel.cn/api/paas/v4/layout_parsing`
- 鉴权：`Authorization: <ZHIPU_API_KEY>`（不是 Bearer；按官方示例）。
- 请求：`{"model":"glm-ocr","file":"<URL 或 data:...base64>"}`；可选 `start_page_id`、`end_page_id`、`return_crop_images`、`need_layout_visualization`。
- 限制：图片 ≤10 MB、PDF ≤50 MB、≤100 页；中文、英文、日韩、法德俄西等；同步请求。
- 返回：`md_results`（整篇 Markdown）、`layout_details`（逐页数组，元素含 `label`、`bbox_2d` 归一化坐标、`content`、`width/height`）、`usage`。
- 价格：输入输出同价 0.2 元/百万 tokens；官方称 1 元约 2000 张 A4 扫描图或 200 份 10 页简单 PDF；以账单为准。
- 适合：中文表格、手写、印章、票据、代码文档；不适合超过 100 页或超大 PDF。
- 密钥：`ZHIPU_API_KEY`（也接受 `GLM_API_KEY`）；本技能不写配置文件。

## Mistral OCR

- 入口：`POST https://api.mistral.ai/v1/ocr`
- 鉴权：`Authorization: Bearer <MISTRAL_API_KEY>`。
- 请求：`{"model":"mistral-ocr-latest","document":{"type":"document_url","document_url":"<URL 或 data URI>"},"table_format":"html","include_image_base64":true,"include_blocks":true}`。
- 返回：`pages[]`，每页 `markdown`、`images`、`tables`、`hyperlinks`、`dimensions`、`blocks`（OCR 4+）、可选 `confidence_scores`；图片/表格用占位符，需要按字段映射。
- 限制/价格：OCR 4.1 $4/1000 页，OCR 3 $2/1000 页；具体大小/页数上限按官方文档和账号。
- 适合：图表/表格密集、需要 bbox 和块结构的文档；中文能力可用但不如中文专用模型稳。
- 密钥：`MISTRAL_API_KEY`。

## Google Gemini

- 入口：`POST https://generativelanguage.googleapis.com/v1beta/models/<model>:generateContent?key=<GEMINI_API_KEY>`
- 原生 PDF：inline_data `application/pdf`；也支持图片。PDF 可到 1000 页（模型/账号为准），inline 请求约 18 MB 上限；更大文件用 Files API（本技能未封装）。
- 本技能自动从 `/v1beta/models` 选择可用的 Flash 模型；也可用 `DOCVISION_GEMINI_MODEL` 固定。
- 输出：模型生成的 Markdown；本技能要求页标记 `<!-- page: N -->`，但模型可能不遵守，页映射可能退化为单页并给出警告。
- 价格/免费层：按输入/输出 token 计费；免费层和“是否用于改进产品”随账号/地区变化，不能默认免费。敏感文档优先本地。
- 密钥：`GEMINI_API_KEY` 或 `GOOGLE_API_KEY`。

## OpenAI 兼容 / 本地 VLM

- 端点：`POST <base_url>/chat/completions`，`Authorization: Bearer <key>`（本地 Ollama 可任意/空 key）。
- 示例 base URL：
  - Ollama：`http://127.0.0.1:11434/v1`，模型如 `glm-ocr`、`qwen3-vl`（以实际拉取为准）。
  - vLLM/SGLang：`http://127.0.0.1:8000/v1`。
  - SiliconFlow/OpenRouter 等：按服务商给的 base URL 和模型名。
- 本技能对 PDF 会逐页渲染成 PNG 再请求；没有布局管线，阅读顺序/跨页表格需自己检查。适合截图、单页图表、已有视觉模型的环境。
- 配置：`DOCVISION_OPENAI_BASE_URL`、`DOCVISION_OPENAI_MODEL`、`DOCVISION_OPENAI_API_KEY`；本地 VLM 也可写入 `config.json` 的 `engines.vlm`（不写 key）。
- 免费模型/额度会变；不要因为“免费”就上传敏感文档。

## 百度 PaddleOCR 云 API（了解，不默认）

百度智能云也提供文档解析（PaddleOCR-VL）异步 API：`aip.baidubce.com/rest/2.0/brain/online/v2/paddle-vl-parser/...`，需要 API Key/Secret 换 access_token；个人认证 200 页、企业认证 1000 页免费测试资源，之后约 0.05-0.09 元/页（2026-10 价格页）。本技能默认走**本地 PaddleOCR**；如果你确实需要百度云，按官方文档接，不要把它的额度和本地模型混为一谈。

## 上传前检查清单

- 文件是否含个人信息、未发表数据、客户资料、医疗/法务/财务内容？
- 用户是否明确说“可以上传”？
- 是否可以先本地跑 3 页看看？本地失败是否只是页码/显存/模型未下载？
- 选的服务是否在用户所在地区可用？token 是否过期？
- 输出是否需要图片/bbox/页结构？如果只需要纯文本，Agent 或本地 fast 档就够。
- 失败重试是否会重复计费？不要在未知结果时自动重传大文件。

## 依据

- MinerU API：<https://mineru.net/apiManage/docs>
- GLM-OCR：<https://docs.bigmodel.cn/cn/guide/models/vlm/glm-ocr>、<https://docs.bigmodel.cn/api-reference/模型-api/文档解析>
- Mistral OCR：<https://docs.mistral.ai/capabilities/document_ai/basic_ocr>、<https://docs.mistral.ai/inference/pricing>
- Gemini 文档理解：<https://ai.google.dev/gemini-api/docs/document-processing>
- 百度 PaddleOCR-VL 价格：<https://ai.baidu.com/ai-doc/OCR/tlrzzplc1>
