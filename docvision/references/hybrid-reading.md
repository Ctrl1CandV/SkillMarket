# 本地初稿与局部精读

## 路线

1. 用本地 MinerU 建立带页/块定位的初稿，低开销批量用 economy，日常论文用 standard。数字版仅正文用 fast。
2. 围绕用户的问题选页；triage 提示公式、合并表格、图块等需要复核的区域。未被标出的内容也可能有错。
3. 精确符号/表格用专业 OCR 独立复核；趋势/架构关系用视觉模型实际看图。当前对话已有视觉能力时，packet 路线能复用它。
4. 用同一原图对照两份结果，保留不确定项和原页码，不自动把云端结果覆盖到本地初稿。

## 任务对应

| 任务 | 输入重点 | 核对内容 | 默认自动精读路线（已授权远程） |
|---|---|---|---|
| formula | 包含完整表达式和编号的裁图 | 下标、幂、求和边界、括号、希腊字母 | Paddle 官方 → MinerU Standard → Gemini |
| table | 完整表头、脚注与所有列 | rowspan/colspan、单位、负号、空值、数字 | Paddle 官方 → MinerU Standard → Gemini |
| chart | 轴、图例、单位与曲线 | 趋势、可读数值、尺度、误差棒 | Gemini → 本地视觉服务 → packet |
| figure | 完整图块与相关图注/邻近正文 | 模块名、箭头方向、分支、循环、数据流 | Gemini → 本地视觉服务 → packet |
| transcribe | 局部正文或整页 | 忠实转写、阅读顺序 | Paddle 官方 → MinerU Standard → Gemini |

无密钥/未授权时 auto 输出 packet；不自动选择 GLM/Mistral/OpenAI 兼容付费服务。显式 provider 的费用由账号决定，免费额度不是识别正确性保证。

## 精读包与证据

`refine` 默认 300 DPI，选块时使用其归一化 bbox，手动 bbox 必须有效且非空。原图过期则拒绝沿用旧坐标。截图仍保持原始信息量，提高 DPI 无法补回缺失像素。

输出独立保存在 `refinements/`，局部选择仅附选中/重叠块和相邻块文字，整页选择才附整页正文；dry-run 与 record 的 context_scope/context_chars 显示实际范围。包含裁图、上下文、任务指令、源文件指纹、原页/bbox、请求签名、状态、模型、原始服务输出和结果路径。

- packet 的 `review_required` 意味着尚未视觉复核；必须实际打开 PNG。可用宿主 view_image 等图像工具，不能只读取 PNG 文件路径或 OCR 文本。
- `recognized` 是识别完成，不表示已校对正确。每份结果都保留 `accuracy_verified=false`。
- 无结果、截断、缺页、缺图等不能当完成；中断的 submitted 结果不自动重新上传。
- 只对同请求复用缓存，`--force` 明确新建一次尝试，旧记录保留。

查看 `read --page` / `read --block` 时会列出关联记录，结果冲突回到原图。远程处理的裁图与邻近上下文都属于上传范围，应符合用户本轮的授权。

## 采用的参考与取舍

2026-10-28 阅读并吸收 [MinerU 官方 skill](https://github.com/opendatalab/MinerU/blob/master/skills/mineru/SKILL.md) 的局部阅读、稳定定位、邻近上下文与按档缓存；参考 [PaddleOCR 官方 skill](https://github.com/PaddlePaddle/PaddleOCR/blob/main/skills/paddleocr-doc-parsing/SKILL.md) 和官方 API 客户端的提交、轮询、资源保留方式。本技能继续维护统一契约，未安装这些上游 skill，也不复制其全局偏好。

本轮保留 MinerU/Paddle 两条本地主线，没有为了模型数量增加更多依赖。下一次模型替换应以同页正文、公式、表格和图形任务的结果及端到端耗时为依据。
