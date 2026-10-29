# 远程接口：只有 PaddleOCR 官方 API

远程用于疑难区域的第二份转写，辅助查错与纠错。本技能只保留一条云端路线：**PaddleOCR 官网 / AI Studio 官方 API**。2026-10-29 同图小样本未显示 API 的精度优势；仅首次公式裁图更快，整页和表格本地更快。它可以补充不同模型的结果，但仍可能漏编号、误识符号，采纳必须回看原图。其他未经实际账号验证的云端适配器已移除。

价格/额度为 2026-10-28 调研值，随时可能变；`docvision usage` 只是提示，不是账单依据。

## 两道开关

1. **当前用户的持久同意**（`config.json` 的 `remote.consent`）：初始为 `unset`，询问后记为 `remote` 或 `local-only`。只有 `remote` 可以上传；未回答或拒绝时，即使加 `--allow-remote` 也不能上传。已有选择沿用，不重复询问。
2. **每次调用同意**（`--allow-remote`）：即使安装级已允许，单次上传仍要显式加这个参数。

没有任何路径会在本地失败后自动上传，也不会在失败后切换 provider。额度耗尽或 401 时明确报错、不重试。

`refine --provider auto` 即使具备两道开关也先生成 OCR 精读包；需要第二份转写时显式选 `--provider paddleocr-cloud`。有 jobId 的中断任务用 `jobs resume` 只继续 GET；未知提交不自动重传。完整恢复、迁移和保存校正方法见[长期阅读维护](maintenance.md)。

## 凭据位置

固定一个文件：`{SKILL_DIR}/.credentials.env`（技能目录内，随附 `.gitignore` 已屏蔽）。写入方式：

```text
python "{SKILL_DIR}/scripts/docvision.py" credentials set --prompt  # 用户在自己的终端隐藏输入
python "{SKILL_DIR}/scripts/docvision.py" credentials show      # 只显示名字与 set/not set
python "{SKILL_DIR}/scripts/docvision.py" credentials remove    # 删除密钥并回到 local-only
```

- 解析顺序：`--env-file` → `DOCVISION_ENV_FILE` → `{SKILL_DIR}/.credentials.env` → 当前目录 `.env`。进程环境变量优先于文件。`credentials set` 会替换同一凭据组的旧别名；如果进程仍带旧 token，需更新或清除该环境变量。
- 凭据绑定当前机器与系统用户；自动加载只接受匹配绑定。旧未绑定文件请重新 `credentials set --prompt`，开发测试可显式 `--env-file` 选择。进程环境变量可独立使用。
- POSIX 从创建时使用 0600；Windows 写入并核对当前用户的私有 DACL。权限设置失败就拒绝保存；不写符号链接/重解析点。文件权限与 Git 忽略各自处理不同问题。
- 写入前检查 `git check-ignore`：若技能目录位于某个 git 仓库且该文件未被忽略，直接拒绝写入，并提示应添加的忽略行。
- 拷贝/分享技能目录会一并带走密钥；分发前先 `credentials remove`。
- 推荐每个系统账号安装自己的技能目录。共享/只读安装用 `DOCVISION_CREDENTIALS` 指定私有文件路径，仍需该用户单独授权。多人共用同一个系统账号没有可靠的相互隔离。
- `--prompt` 与 `--stdin` 二选一；只想存 key 可加 `--local-only`。开发仓库的测试 key 只留在被忽略的 `maintenance/docvision/.env`，不上传 main 或 dev。

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

1. `refine --provider packet`：生成裁图 + 上下文包，由**当前对话的视觉能力**实际看图（推荐；制作包本身不调用 OCR API，宿主看图遵循宿主的数据处理策略）。
2. `refine --provider local-vlm`：本机 Ollama/vLLM 的 OpenAI 兼容端点，必须是 loopback（`127.0.0.1`/`localhost`），否则拒绝。本地视觉请求显式绕过环境代理并拒绝 HTTP 重定向。

配置：`config.json` 的 `engines.vlm`（`base_url`、`model`）或 `DOCVISION_OPENAI_BASE_URL` / `DOCVISION_OPENAI_MODEL`；key 用 `DOCVISION_VLM_API_KEY`（本地 Ollama 可留空）。有效设置顺序为本次 `--extra` → DOCVISION 环境变量 → OPENAI 别名 → config，发现、执行与缓存使用相同解析。没有布局管线，阅读顺序与跨页表格需自己检查。

## 上传前检查清单

- 文件是否含个人信息、未发表数据、客户资料、医疗/法务/财务内容？
- 用户是否明确说“可以上传”（而不只是“配个 key”）？
- 是否可以先本地跑 3 页、只在关键区域上传裁图？
- 该次调用是否同时满足 `consent=remote` 与 `--allow-remote`？
- 输出是否需要图片/bbox/页结构？只需要纯文本就先试本地。
- 失败重试是否会重复计费？结果未知时不要自动重传。

## 依据

- PaddleOCR 官方 API 与额度：<https://www.paddleocr.ai/main/index.html>、<https://ai.baidu.com/ai-doc/AISTUDIO/fml7mozw5>
- PaddleOCR SDK/CLI：<https://github.com/PaddlePaddle/PaddleOCR/tree/main/paddleocr/_api_client>
- 百度 PaddleOCR-VL 云价格（了解，不默认）：<https://ai.baidu.com/ai-doc/OCR/tlrzzplc1>
