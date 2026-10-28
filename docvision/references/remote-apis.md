# 远程接口：只有 PaddleOCR 官方 API

远程是“关键页复核”的出口，不是默认。本技能只保留一条云端路线：**PaddleOCR 官网 / AI Studio 官方 API**。原因很直接：它是本项目唯一用真实账号验证过公式与合并表格的远程服务，其余云端 OCR（GLM、Mistral、Gemini、MinerU 云端）没有验证过的 key，代码与文档都成了无法证实的承诺，已移除。删掉代码比留着“看起来支持”更诚实。

价格/额度为 2026-10-28 调研值，随时可能变；`docvision usage` 只是提示，不是账单依据。

## 两道开关

1. **安装级同意**（`config.json` 的 `remote.consent`）：`remote` 或 `local-only`。首次使用时技能必须询问用户；用户不配置就写 `local-only`，此后**任何**云端调用直接拒绝，即使命令行加了 `--allow-remote`。
2. **每次调用同意**（`--allow-remote`）：即使安装级已允许，单次上传仍要显式加这个参数。

没有任何路径会在本地失败后自动上传，也不会在失败后切换 provider。额度耗尽或 401 时明确报错、不重试。

## 凭据位置

固定一个文件：`{SKILL_DIR}/.credentials.env`（技能目录内，随附 `.gitignore` 已屏蔽）。写入方式：

```text
printf '%s' "$TOKEN" | python "{SKILL_DIR}/scripts/docvision.py" credentials set --stdin
python "{SKILL_DIR}/scripts/docvision.py" credentials show      # 只显示名字与 set/not set
python "{SKILL_DIR}/scripts/docvision.py" credentials remove    # 删除密钥并回到 local-only
```

- 解析顺序：`--env-file` → `DOCVISION_ENV_FILE` → `{SKILL_DIR}/.credentials.env` → 当前目录 `.env`。进程环境变量优先于文件。
- POSIX 上写入即 `chmod 600`；Windows 的 `chmod` 只切换只读位，实际保护来自用户目录 ACL 与 `.gitignore`，不要宣称它在 Windows 上等价于 0600。
- 写入前检查 `git check-ignore`：若技能目录位于某个 git 仓库且该文件未被忽略，直接拒绝写入，并提示应添加的忽略行。
- 拷贝/分享技能目录会一并带走密钥；分发前先 `credentials remove`。

## PaddleOCR 官方免费额度 API

2026-10-28 核验：[官方首页](https://www.paddleocr.ai/main/index.html)公布免费 API 每日文档解析上限 20,000 页；资格与实际额度以 AI Studio 账号为准，不承诺永久免费。

- provider：`paddleocr-cloud`；密钥名 `PADDLEOCR_ACCESS_TOKEN`，兼容 `DOCVISION_PADDLE_TOKEN`、`PADDLEOCR_API_TOKEN`、`AI_STUDIO_TOKEN`、`PADDLEAPIKEY`。
- HTTP：POST `https://paddleocr.aistudio-app.com/api/v2/ocr/jobs`，Bearer 鉴权；本地 multipart 文件，URL 用 JSON fileUrl；默认模型 PaddleOCR-VL-1.6，可显式覆盖。
- GET `/jobs/{jobId}` 轮询，下载 resultUrl.jsonUrl 的 JSONL，保留逐页 Markdown、图片和可用 bbox。资源下载不携带 API token。
- 本地上传 50 MB、每文件 1000 页；本客户端拒绝可能被服务静默截断的请求。未知页数 PDF URL 必须限定页范围，超过限制先本地拆分。
- 单次提交，不自动重传；选页映射回原页。`refine` 只提交裁图，随精读记录保存原页与 bbox。
- 已用真实 token 验证公式/合并表格与原页定位，覆盖本地初稿→裁块→云端精读→缓存复用；云端与本地 Paddle 的合并表格 HTML 逐字节一致。
- 公式/表格裁块直接指定 `promptLabel` 并关闭重复版面检测；整页保留版面分析。Markdown 格式和公式编号输出显式开启，但仍须回看原图核对。
- 云端排队时间会变化；区域请求实测约 4–64 秒，不能承诺云端总比本地快或更准确。真实额度耗尽响应未捕获，错误映射由 mock 覆盖，不靠耗尽额度做测试。
- 依据：[官方 API](https://ai.baidu.com/ai-doc/AISTUDIO/fml7mozw5)、[官方 SDK](https://github.com/PaddlePaddle/PaddleOCR/tree/main/paddleocr/_api_client)、[官方 CLI](https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/serving/paddleocr_official_api/cli.html)。

## 本地视觉服务（不是云端）

图表与架构图的语义解释没有云端路线了。可选：

1. `refine --provider packet`：生成裁图 + 上下文包，由**当前对话的视觉能力**实际看图（推荐，零上传）。
2. `refine --provider local-vlm`：本机 Ollama/vLLM 的 OpenAI 兼容端点，必须是 loopback（`127.0.0.1`/`localhost`），否则拒绝。

配置：`config.json` 的 `engines.vlm`（`base_url`、`model`）或 `DOCVISION_OPENAI_BASE_URL` / `DOCVISION_OPENAI_MODEL`；key 用 `DOCVISION_VLM_API_KEY`（本地 Ollama 可留空）。没有布局管线，阅读顺序与跨页表格需自己检查。

## 上传前检查清单

- 文件是否含个人信息、未发表数据、客户资料、医疗/法务/财务内容？
- 用户是否明确说“可以上传”（而不只是“配个 key”）？
- 是否可以先本地跑 3 页、只在关键区域上传裁图？
- 该次调用是否同时满足 `consent != local-only` 与 `--allow-remote`？
- 输出是否需要图片/bbox/页结构？只需要纯文本就先试本地。
- 失败重试是否会重复计费？结果未知时不要自动重传。

## 依据

- PaddleOCR 官方 API 与额度：<https://www.paddleocr.ai/main/index.html>、<https://ai.baidu.com/ai-doc/AISTUDIO/fml7mozw5>
- PaddleOCR SDK/CLI：<https://github.com/PaddlePaddle/PaddleOCR/tree/main/paddleocr/_api_client>
- 百度 PaddleOCR-VL 云价格（了解，不默认）：<https://ai.baidu.com/ai-doc/OCR/tlrzzplc1>
