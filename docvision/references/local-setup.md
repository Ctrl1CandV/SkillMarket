# 首次使用与长期环境

先运行 `doctor --json`，根据硬件建议和已有引擎选择路线，再安装。这里的容量门槛是规划建议；没有测过的设备不能仅凭显存数字宣称可用。

## 路线选择

| 条件 | 首次建议 |
|---|---|
| 8/16 GB 显存，内存充足 | MinerU standard，先单页单并发；已有一台 8 GB 设备的小样本验收，长文档仍需按实际情况验证 |
| 无 GPU、内存较少 | 数字 PDF 用 fast；扫描件先试 economy/basic，CPU 可能很慢 |
| Apple/AMD/检测不到 GPU | 不把 NVIDIA 检测失败当作没有任何加速；先确认上游平台支持并单页试跑，不自动装 CUDA |
| 不想装模型/磁盘不足 | 只装 core：数字 PDF 用 fast 转换后制作精读包；扫描件用 pages 看图或已授权的 Paddle API |
| 无 Python/conda/uv | 先安装 Python 3.10+ 及 conda 或 uv；skill 不修改全局 Python |

core 提供数字 PDF 文字层读取、渲染、拆页和图片裁剪，不是 OCR 引擎。fast 不启动 MinerU/Paddle，输出没有 bbox；整页或手动 bbox 可继续 refine packet。没有 API 账号也能读文字层、使用本地 OCR 或由当前对话看精读包。Paddle 账号注册由用户完成，不要求在聊天里交密钥。

## 固定布局

```text
技能目录：SKILL.md、references/、scripts/、.gitignore
          .credentials.env（可选，仅本机用户，不能打包分享）
用户数据目录：
  Windows %LOCALAPPDATA%/docvision/
  Linux/macOS ${XDG_DATA_HOME:-~/.local/share}/docvision/
    envs/docvision-core-<安装ID>/   # 每次安装新建独立 conda/uv 环境
    envs/docvision-mineru-<安装ID>/
    envs/docvision-paddle-<安装ID>/ # 可选
    models/installations/<安装ID>/mineru/
    models/installations/<安装ID>/paddlex/
用户配置：Windows %APPDATA%/docvision/config.json
          Linux/macOS ${XDG_CONFIG_HOME:-~/.config}/docvision/config.json
项目目录：docvision-out/ 或 --output 指定目录
          .staging/、页图、初稿、refinements/ 都在输出内
```

每个系统账号使用自己的环境、配置和凭据。不修改未知的同名共享 conda 环境；已有独立环境可在配置中显式指定 Python/exe 复用。Windows conda 的 Python 在 `<env>/python.exe`，uv venv 在 `<env>/Scripts/python.exe`，入口会识别两种布局。

安装分配根由配置 `models_dir`、`DOCVISION_MODELS` 或默认用户数据目录决定。新安装会在其 `installations/<ID>/` 建独立模型目录，激活后用引擎的 `model_home` 固定运行路径，避免更新模型破坏旧环境。显式 `DOCVISION_MODELS` 可临时覆盖活动模型路径，安装验收会禁用该覆盖，并提示验收后清除它。没有活动 pin 或显式全局根时，沿用旧引擎路径、模型环境变量及 `~/.mineru`/`~/.paddlex` 的兼容规则。`doctor` 显示实际目录；路径应为绝对路径，`setup --models-dir` 会解析后保存。

## 安装与验收

把 `{SKILL_DIR}` 换成安装目录。从项目目录运行：

```text
python "{SKILL_DIR}/scripts/docvision.py" doctor --json
python "{SKILL_DIR}/scripts/docvision.py" setup --profile core --dry-run
python "{SKILL_DIR}/scripts/docvision.py" setup --profile core --yes
python "{SKILL_DIR}/scripts/docvision.py" setup --profile mineru --sample "一页真实样本.pdf" --yes
```

`--manager auto` 优先 conda，否则 uv；新环境都放用户数据目录 `envs/`。没有管理器时清楚报错，不安装到全局。`--dry-run` 仅打印计划，不保存配置或下载。可指定固定模型根：

```text
python "{SKILL_DIR}/scripts/docvision.py" setup --profile mineru --models-dir "D:/OCR-models" --sample "一页真实样本.pdf" --yes
```

MinerU 默认下载 standard 档模型；下载或单页验收失败不切换配置。`--no-models` 只跳过预下载，仍需单页验收，上游可能在首次推理时下载模型。economy/basic 需要对应模型：在 doctor 显示的 MinerU 环境中，对同一个活动 `MINERU_HOME` 执行 `mineru-kit models download --tier basic`。`--mineru-home` 指定独立模型安装的基目录，新模型仍分配到其中的 `installations/<ID>/mineru`，不覆盖现有内容；不与 `--models-dir` 同用。

Paddle 是可选路线：

```text
python "{SKILL_DIR}/scripts/docvision.py" setup --profile paddle --device auto --dry-run
python "{SKILL_DIR}/scripts/docvision.py" setup --profile paddle --device cpu --sample "一页真实样本.png" --yes
```

自动 GPU 安装仅在检测到合适的 NVIDIA/平台条件时选择。GPU 轮子使用官方 CUDA 12.6 源；CUDA/cuDNN、驱动和平台仍须匹配，未知平台先用计划检查，不把 pip 成功当成 GPU 推理成功。Paddle GPU 多索引使用与 pip 一致的候选策略，避免 PyPI 旧版本遮蔽官方版本。

安装后：

```text
python "{SKILL_DIR}/scripts/docvision.py" doctor --probe --json
python "{SKILL_DIR}/scripts/docvision.py" convert "一页真实样本.pdf" --provider mineru-local --output ./_docvision --json
python "{SKILL_DIR}/scripts/docvision.py" verify ./_docvision/一页真实样本 --json
```

核对正文、公式、表格列、页码、图片和耗时。Paddle 还需真实跑一页 `--provider paddleocr-local`；导入检查不等于管线与模型已经验证。core/Paddle 子进程禁用用户 site，避免全局包混入；已有 MinerU 的用户包策略保持兼容。

## 版本、升级与恢复

2026-10-28 的历史验收基线：Python 3.12、MinerU 4.0.12、PaddleOCR 3.7.0、PaddlePaddle GPU 3.2.1、PaddleOCR-VL 1.6、pypdfium2 5.13.0、Pillow 12.3.0、pypdf 6.1.1，设备为 Windows/NVIDIA 16 GB。2026-10-29 又在 RTX 4060 Laptop 8 GB 上新建独立 MinerU 4.0.12 环境，下载/校验标准模型并完成 3 页及两类裁图对照；确认 llama-cpp 后端，未证明 GPU 加速占比。纯净系统和其他平台、长文档峰值显存仍未验收。

`setup` 使用兼容范围（MinerU 4.0.x、PaddleOCR 3.7.x）；`scripts/constraints/` 是参考版本快照，安装器不自动加载这些文件，并非完全锁定的跨平台安装包。每次安装先保存配置/包版本快照，创建全新环境和模型目录，候选单页必须 state=done、pages=1、qa=pass 才切换；core 则真实验证 PDF 写入、文字提取与渲染。失败保留原默认，不升级原环境。`setup --history --json` 查询，`setup --rollback ID --yes` 恢复安装字段并保留当前远程同意及其他设置，也保存回退前快照。旧环境/模型不删除，详见[长期阅读维护](maintenance.md)。结构验收无法替代识别质量判断，重要模型升级仍看同页差异。

## 清理与隐私

预留 10 GB 以上只是基础规划，轮子、多个档位和下载缓存会增加占用。模型与运行环境长期保留，不随项目清理；卸载或移动它们后需更新配置。

转换临时目录在输出 `.staging/`，精读临时文件在对应记录的 `work/`，完成或报错后清理；`DOCVISION_KEEP_TEMP=1` 保留诊断现场。页图、原始响应和精读记录是输出证据，保留在项目中。结束后可自行删除整个项目输出目录，用户级模型/环境不受影响。输出包含原文，放入共享仓库前也要忽略。

凭据录入、权限和远程同意见 [远程接口](remote-apis.md)。开发实验只使用忽略的 `maintenance/docvision/.env` 并显式 `--env-file` 读取，任何分支都不上传密钥、模型或真实文档。
