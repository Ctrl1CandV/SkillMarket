# 本地初稿与局部精读

## 路线

1. 数字 PDF 先用 fast 的 text-local 路线筛读；要 OCR 版面与块坐标时用 MinerU standard。economy 只有同页实测更合算时才作为批量档。
2. 围绕用户的问题选页；triage 提示公式、合并表格、图块等需要复核的区域。未被标出的内容也可能有错。
3. 先实际看图核对关键内容。有缺字、符号歧义、错列等具体疑点时，显式用另一 OCR（包括 API）获取纠错候选；趋势/架构关系由视觉能力解释。当前对话已有视觉能力时，packet 路线能复用它。
4. 以同一原图判断候选，核对后通过 `correct add` 保存有依据的修订，保留不确定项和原页码。两份 OCR 一致也不等于已证明正确。

## 任务对应

| 任务 | 输入重点 | 核对内容 | 默认自动精读路线 |
|---|---|---|---|
| formula | 包含完整表达式和编号的裁图 | 下标、幂、求和边界、括号、希腊字母 | packet（宿主看图）；疑点再显式选 API |
| table | 完整表头、脚注与所有列 | rowspan/colspan、单位、负号、空值、数字 | packet（宿主看图）；疑点再显式选 API |
| chart | 轴、图例、单位与曲线 | 趋势、可读数值、尺度、误差棒 | 本地视觉服务 → packet |
| figure | 完整图块与相关图注/邻近正文 | 模块名、箭头方向、分支、循环、数据流 | 本地视觉服务 → packet |
| transcribe | 局部正文或整页 | 忠实转写、阅读顺序 | packet；疑点再显式选 API |

auto 的 OCR 任务始终输出 packet，不因已有密钥/上传许可自动调用 API。显式云端仍需安装级同意与 `--allow-remote`，且只有 PaddleOCR 一条路线。2026-10-29 小样本没有显示 API 精度优势，仅首次公式裁图更快；定位为疑难区域辅助纠错，而非默认高精度阶段，亦不能据此宣布所有文档本地都更准。

## 精读包与证据

`refine` 默认 300 DPI，选块时使用其归一化 bbox，手动 bbox 必须有效且非空。原图过期则拒绝沿用旧坐标。截图仍保持原始信息量，提高 DPI 无法补回缺失像素。

输出独立保存在 `refinements/`，局部选择仅附选中/重叠块和相邻块文字，整页选择才附整页正文；dry-run 与 record 的 context_scope/context_chars 显示实际范围。包含裁图、上下文、任务指令、源文件指纹、原页/bbox、请求签名、状态、模型、原始服务输出和结果路径。

- packet 的 `review_required` 意味着尚未视觉复核；必须实际打开 PNG。可用宿主 view_image 等图像工具，不能只读取 PNG 文件路径或 OCR 文本。
- `recognized` 是识别完成，不表示已校对正确。每份结果都保留 `accuracy_verified=false`。
- 无结果、截断、缺页、缺图等不能当完成；中断的 submitted 结果不自动重新上传。
- 只对同请求复用缓存，`--force` 明确新建一次尝试，旧记录保留；下一次普通请求读取最新 attempt，最新失败或提交中不退回旧成功。

查看 `read --page` / `read --block` 时只列出与当前源指纹、块位置及上下文一致的关联记录，结果冲突回到原图。校正、续接、搬家与回退命令见[长期阅读维护](maintenance.md)。远程处理的裁图与邻近上下文都属于授权范围；Paddle 专业 OCR 当前发送裁图与任务参数，宿主/本机视觉模型另使用上下文。

## 采用的参考与取舍

2026-10-28 阅读并吸收 [MinerU 官方 skill](https://github.com/opendatalab/MinerU/blob/master/skills/mineru/SKILL.md) 的局部阅读、稳定定位、邻近上下文与按档缓存；参考 [PaddleOCR 官方 skill](https://github.com/PaddlePaddle/PaddleOCR/blob/main/skills/paddleocr-doc-parsing/SKILL.md) 和官方 API 客户端的提交、轮询、资源保留方式。本技能继续维护统一契约，未安装这些上游 skill，也不复制其全局偏好。

本轮保留 MinerU/Paddle 两条本地主线，没有为了模型数量增加更多依赖。下一次模型替换应以同页正文、公式、表格和图形任务的结果及端到端耗时为依据。
