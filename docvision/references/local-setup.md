# 本地环境：一次装好，长期可用

目标不是“装一个能跑的包”，而是让 OCR 在半年后、换项目后、系统更新后仍然能定位、能复现、能回滚。做法是：**技能目录只放代码；运行时放独立环境；模型放用户缓存；版本写进约束；每次升级先小样本验收。**

## 推荐布局

```text
技能目录（只读运行资源 + 一个被忽略的凭据文件）
  docvision/
    SKILL.md
    references/
    scripts/            # 本技能代码，无第三方依赖
    scripts/constraints/ # 版本约束
    .gitignore          # 屏蔽 .credentials.env / .staging
    .credentials.env    # 可选；本地凭据，永不提交

用户环境（不随仓库提交）
  conda env docvision-mineru    # MinerU 4，默认本地引擎
  conda env docvision-paddle    # PaddleOCR-VL，可选 GPU
  conda env docvision-core      # pypdfium2/Pillow/pypdf，页码渲染/裁剪
  <models_dir>/mineru/          # 固定模型根，默认 %LOCALAPPDATA%/docvision/models
  <models_dir>/paddlex/         # 同上；已存在 ~/.paddlex 时自动复用旧安装
  %APPDATA%/docvision/config.json  # 只存路径与 remote.consent，不存密钥
```

模型根固定、可覆盖：`DOCVISION_MODELS` 环境变量或 `setup --models-dir <path>`，也可写 `config.json` 的 `models_dir`。解析优先级：`models_dir` → `DOCVISION_MODELS` → 默认应用数据目录。显式指定时会关闭对 `~/.mineru`、`~/.paddlex` 旧路径的自动复用。

Windows 的 conda 环境 Python 在 `<env>\python.exe`；venv 在 `<env>\Scripts\python.exe`。技能会两种都识别。

## 一键安装

在用户同意下载后运行（不加 `--yes` 只打印计划）：

```text
python "{SKILL_DIR}/scripts/docvision.py" setup --profile mineru --yes
python "{SKILL_DIR}/scripts/docvision.py" setup --profile paddle --device cuda --yes
python "{SKILL_DIR}/scripts/docvision.py" setup --profile core --yes
```

行为：

- `--manager auto`：有 conda 用 conda，否则用 uv。
- `--manager conda`：创建 `docvision-*` 环境，Python 3.12；不碰现有 `mineru`、`comfyui-h3` 等环境。
- MinerU：安装 `mineru>=4.0,<5`，然后下载 standard 档模型（约 2 GB）。基础包已含 ONNX 小模型和 llama.cpp Vulkan，不强制 CUDA。
- Paddle：GPU 时安装 `paddlepaddle-gpu==3.2.1`（Baidu cu126 源）和 `paddleocr[doc-parser]>=3.7,<3.8`；CPU 时安装 `paddlepaddle==3.2.1`。同时装 `python-docx`（Paddle OCR 的 DOCX 导出依赖）和 `pypdf`。
- Core：只装页面渲染/裁剪需要的 `pypdfium2`、`pillow`、`pypdf`，不装 OCR 模型。
- 配置会写入 `%APPDATA%/docvision/config.json` 或 `~/.config/docvision/config.json`，记录可执行文件路径、`models_dir` 与 `remote.consent`；不写任何 key。

如果 conda 的默认 channel 配置损坏（例如镜像 404），`setup` 用 `-c conda-forge --override-channels` 建环境；也可以用 `--conda-channel` 指定可用 channel。

## 手动安装（审计/离线时）

### MinerU（推荐默认）

```bash
conda create -y -n docvision-mineru python=3.12 -c conda-forge --override-channels
conda activate docvision-mineru
python -m pip install -U "mineru>=4.0,<5"
mineru --version
mineru-kit parse --help
mineru-kit models download --tier standard
mineru-kit models verify --tier standard
```

Windows 上不需要先装 CUDA 就能用基础包；它会用 ONNX 做小模型、llama.cpp Vulkan 做 VLM。想要更高吞吐，官方提供 `mineru[full]`（vLLM/LMDeploy），但 Windows 的 GPU torch 要单独装，且 vLLM 原生 Windows 支持有限；优先在 Linux/WSL2 上尝试。不要为了“更快”在生产任务当天换引擎。

### PaddleOCR-VL（可选，GPU）

```bash
conda create -y -n docvision-paddle python=3.12 -c conda-forge --override-channels
conda activate docvision-paddle

# Windows/Linux，CUDA 12.6；如用其他 CUDA 版本，换官方 index
python -m pip install "paddlepaddle-gpu==3.2.1" \
  -i https://www.paddlepaddle.org.cn/packages/stable/cu126/ \
  --extra-index-url https://pypi.org/simple
python -m pip install "paddleocr[doc-parser]>=3.7,<3.8" python-docx pypdf

python -c "import paddle; print(paddle.__version__, paddle.device.get_device(), paddle.device.is_compiled_with_cuda())"
paddleocr doc_parser --help
```

CPU 机器把 `paddlepaddle-gpu` 换成 `paddlepaddle==3.2.1`，不要加 CUDA index。

Paddle 的 cuDNN 编译版本和安装的 NVIDIA 运行库可能不一致，出现类似 “compiled with CUDNN 9.9, but CUDNN version ... 9.5” 的警告时，先跑一页真实样本；能稳定跑再批量。若报错，优先改用 CPU 单页验证，再按 Paddle 官方安装页匹配 CUDA/cuDNN，不要混装多个 Paddle 版本。

### Core（页面图/裁剪）

```bash
conda create -y -n docvision-core python=3.12 -c conda-forge --override-channels
conda activate docvision-core
python -m pip install "pypdfium2>=4,<6" "pillow>=10,<13" "pypdf>=5,<7"
```

`pypdfium2` 用于把 PDF 页渲染成 PNG；`Pillow` 用于裁剪/总览图；`pypdf` 用于按页拆分给 PaddleOCR。没有它们时，文本转换仍可工作，但 `read --format image`、`crop`、`pages` 会提示安装。

## 版本基线（2026-10-28 实测）

| 组件 | 实测/约束 | 说明 |
|---|---|---|
| Python | 3.12 | 技能要求 >=3.10；3.12 兼容性最好 |
| MinerU | 4.0.12 | `mineru>=4.0,<5`；模型 standard 档约 2 GB |
| PaddleOCR | 3.7.0 | `paddleocr[doc-parser]>=3.7,<3.8` |
| PaddlePaddle GPU | 3.2.1 | cu126；Windows 可用 |
| PaddleOCR-VL | 1.6 | 0.9B，首次运行自动下载 |
| python-docx | 1.2.0 | Paddle `save_all` 的 DOCX 导出 |
| pypdfium2 | 5.13.0 | 页面渲染 |
| Pillow | 12.3.0 | 裁剪/总览 |
| pypdf | 6.1.1 | 拆页 |

约束文件在 `scripts/constraints/`，给离线/审计用；`setup` 使用范围约束而不是死锁，方便安全更新。若需要完全可复现，安装后执行 `pip freeze > lock.txt`，下次用同一 lock 重建。

## 验收

装完不要只看“导入成功”：

```text
python "{SKILL_DIR}/scripts/docvision.py" doctor --probe --json
python "{SKILL_DIR}/scripts/docvision.py" convert "一页真实样本.pdf" --provider mineru-local --json
python "{SKILL_DIR}/scripts/docvision.py" verify <输出目录> --json
python "{SKILL_DIR}/scripts/docvision.py" read <输出目录> --page 1
```

至少检查：正文是否完整、公式是否可读、表格列是否对齐、图片是否落盘、页码是否正确、耗时是否可接受。Paddle 还要单页跑一次 `--provider paddleocr-local`，确认 GPU 真的在用（`doctor` 会显示 `gpu:0`，但真正证据是速度和显存）。

## 更新

升级是显式动作，不在任务中途自动发生：

```bash
conda activate docvision-mineru
python -m pip install -U "mineru>=4.0,<4.1"   # 先小版本
mineru-kit models verify --tier standard
# 用 3-5 页真实样本重跑，比较输出和速度
```

Paddle 同理，先固定 `paddleocr==3.7.x` 和 `paddlepaddle-gpu==3.2.1`，确认新版本再改约束。更新后跑 `doctor`、`verify` 和至少一个含公式/表格的样本。不要在同一环境里同时升级 Paddle、CUDA 和 OCR 模型，否则出问题无法定位。

## 回滚

- conda：`conda env export --from-history > environment.yml`；出问题用 `conda env create -f environment.yml` 重建，不要在原环境里反复卸载。
- 记录 `python -m pip freeze > lock.txt`；回滚时按 lock 重装。
- 模型与代码分离：删/换 `<models_dir>/mineru` 或 `<models_dir>/paddlex` 不会破坏代码；换模型前保留旧目录名。
- 技能配置在 `config.json`，只存路径；路径失效时改配置或重跑 `setup`，不要删模型缓存。

## 磁盘与缓存

- MinerU 标准档模型约 2 GB；PaddleOCR-VL-1.6 加布局模型约 1-2 GB；CUDA/cuDNN 轮子约 1.5 GB。预留 10 GB 以上。
- 转换中间文件写在输出目录的 `.staging/`，成功即删；保留现场用 `DOCVISION_KEEP_TEMP=1`。模型缓存不要放进技能目录或 Git。
- 换机器时只需重装环境；不要把模型目录或 conda 环境打包进仓库。

## 安全

- 密钥只放 `{SKILL_DIR}/.credentials.env`（`credentials set --stdin` 写入）或环境变量：`PADDLEOCR_ACCESS_TOKEN`、`DOCVISION_VLM_API_KEY`。`doctor`/`credentials show` 只显示 set/not set，不打印值。
- 凭据文件被随附的 `docvision/.gitignore` 屏蔽；写入前会用 `git check-ignore` 复查，未忽略则拒绝写入。
- POSIX 上写入后 `chmod 600`；Windows 上 `chmod` 不等价于 POSIX 权限，实际保护来自用户目录 ACL 与 `.gitignore`。
- 不把 `.credentials.env`、token、真实文档、转换输出提交到任何分支；分发技能前先 `credentials remove`。
- 远程转换需要安装级 `remote.consent != local-only` **和** 每次 `--allow-remote`；本地引擎失败不会自动上传。

## 0.2 环境补充

uv 安装 Paddle GPU 使用官方 CUDA wheel 源与 PyPI 两个索引；多索引时显式采用与pip一致的候选选择策略，避免PyPI旧版本遮蔽官方指定版本。core/MinerU 单索引安装行为保持原样。此安装路径验证了命令与本地索引解析；本轮实际GPU推理使用已有隔离conda环境。

`setup --profile core` 现在保存 core.python；CLI 当前解释器缺渲染/裁剪依赖时，入口切到该 Python 执行。可用 `python -S scripts/docvision.py pages <pdf> --pages 1` 检验干净入口。core 与 Paddle 子进程禁用用户 site，避免把全局依赖误当隔离环境已有包；既有 MinerU 的用户包策略保持兼容。

Paddle 的 doctor 可检查 OCR extras、导入和 CUDA，但管线/模型推理未运行时显示未验证。安装完成后必须真实试一页；仅有 exe 或 import 成功不足以证明可推理。本轮曾修复本机 docvision-paddle 缺失依赖，环境本体 pip check 和实际 PDF/PNG 已补验，换机仍需运行相同检查。

MinerU `economy` 映射 basic；`fast` 的单独图片也走 basic OCR，不把图片当文字层。若缺 basic 模型，先对已配置 MINERU_HOME 运行 `mineru-kit models download --tier basic`。`--device` 目前不能直接透传至 MinerU4 CLI，显式指定会提示使用其运行时配置；Paddle 支持设备参数。
