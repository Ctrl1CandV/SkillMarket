# 排障

按“先定位层，再改一处”的顺序处理。不要同时升级 Python、CUDA、Paddle 和模型。

## 先跑这三条

```text
python "{SKILL_DIR}/scripts/docvision.py" doctor --json
python "{SKILL_DIR}/scripts/docvision.py" env --json
python "{SKILL_DIR}/scripts/docvision.py" verify <输出目录> --json
```

`doctor` 看引擎/模型/密钥；`env` 看路径；`verify` 看输出。不要把“能 import”当成“能推理”。

## 本地引擎找不到

- `mineru-kit not found`：`setup --profile mineru --yes`，或把已有 MinerU 4 的 `mineru-kit` 路径写进 `config.json` 的 `engines.mineru.exe`。
- 已有 MinerU 3.x：本技能要求 4.x；3.x 的命令/输出不同，不要混用。新建 `docvision-mineru` 环境。
- `paddleocr not found`：`setup --profile paddle --device cuda --yes`；或写 `engines.paddleocr.exe`。
- conda 找不到：`conda` 可能不在 PATH；用 `--manager uv`，或把 conda 加入 PATH 后重试。
- 环境创建失败（channel 404）：`setup` 已用 `-c conda-forge --override-channels`；仍失败时检查网络/代理，或指定 `--conda-channel`。

## MinerU

### 模型未下载

```bash
mineru-kit models show
mineru-kit models download --tier standard
mineru-kit models verify --tier standard
```

standard 档约 2 GB。下载中断后重跑即可；不要手动改模型目录名。

### 解析很慢

- 首次运行含模型加载，2 页 10 秒左右正常；整本按页数线性增长。
- 不要同时跑两个 MinerU 进程抢 GPU；批量用 `--workers 1` 或 2。
- `--tier fast` 只取文字层，最快；`quality` 更慢。
- 纯文字数字版 PDF 用 `--mode text`；扫描件才用 `--mode ocr`。

### OOM / CUDA

- 减少 `--pages`，关闭其他 GPU 程序；8 GB 显存不要跑 `advanced` + 大页数。
- Windows 基础包走 Vulkan/ONNX；不要为了“用 GPU”强行装不匹配的 torch/vLLM。
- 需要 `[full]` 时优先 Linux/WSL2；Windows 的 GPU torch 和 vLLM 支持有限。

### 输出为空

- 确认 PDF 不是加密/损坏；`pdf_page_count` 能读到页数吗？
- 扫描页可能整页是图；试 `--mode ocr --tier standard`。
- 页码范围是否超出实际页数？`--pages` 是 1-based。
- 看 `meta.json` 的 `warnings` 和 `raw_meta.command`，再跑 `--keep-raw` 保留原始 zip。

## PaddleOCR-VL

### 导入/初始化失败

```bash
conda activate docvision-paddle
python -c "import paddle; print(paddle.__version__, paddle.device.get_device(), paddle.device.is_compiled_with_cuda())"
paddleocr doc_parser --help
```

- `paddle` 没装：`paddlepaddle-gpu==3.2.1` 要用 Baidu cu126 源；CPU 用 `paddlepaddle==3.2.1`。
- 多个 Paddle 版本冲突：新建干净环境，不要在原环境反复 `pip install -U`。
- Python 3.12 不兼容某些旧轮子：用 3.12 + 官方当前版本。

### cuDNN 版本警告

类似：

```text
The installed Paddle is compiled with CUDNN 9.9, but CUDNN version in your machine is 9.5
```

先单页真实样本试跑。能稳定输出再批量；若报错，按 Paddle 官方安装页匹配 CUDA/cuDNN，或先用 `--device cpu` 验证流程。不要用“警告没消失”判断失败，也不要用“能导入”判断成功。

### DOCX 导出报错

`save_all` 可能在写 DOCX 时缺 `python-docx`；本技能安装时已带上。若仍报错，JSON/Markdown 往往已经写出，本技能会保留并警告；也可以手动 `pip install python-docx`。

### PDF 逐页输出

Paddle CLI 对 PDF 输出 `*_0.md`、`*_0_res.json` 等逐页文件；本技能按 `page_index` 合并并映射回原页。若页码不对，检查是否用了 `--pages` 拆分（拆分后 page_index 是局部的，本技能会映射回原页）。

## 远程（只有 PaddleOCR 官方 API）

### 401/403 或“额度耗尽”

- token 过期/错误/额度用尽：重新生成或更换账号，然后
  `printf '%s' "$TOKEN" | docvision credentials set --stdin` 重写固定凭据文件。
- 没有不扣费的鉴权探测入口，`doctor --probe` 只能报告“key present”；真实转换才是验证。
- 额度耗尽不要立即重试同一批；错误会明确报出，不会自动重传或换付费 provider。

### 被拒绝上传

- “remote upload was declined for this installation”：安装级同意是 `local-only`。只有用户改变主意时才 `docvision setup --remote`。
- “which was not authorized”：缺 `--allow-remote`。两者同时满足才会真正上传。
- 删掉密钥后会回到 `local-only`；再想用云端需重新 `credentials set`。

### 文件太大

- 本机上传递交 50 MB / 1000 页；超过先本地拆分或只提交关键裁图。
- 只上传 `refine` 的裁图通常已经够用，不要为几个区域上传整篇。

### 网络/代理

- 公司代理需要 `HTTPS_PROXY`；不要把代理凭据写进仓库。
- 超时先看 `meta.usage`/`raw_meta`，不要盲目加 `--timeout` 到很大；结果未知时不要重复提交。

### 复杂页码

- Agent 只支持单页或连续范围；`2,4-6` 会报错。
- Standard/MinerU 本地/Paddle 本地支持逗号范围；Paddle 会用 pypdf 拆页。
- 页码是 PDF 物理页，不是印刷页码；带封面/前言的教材要确认偏移。

## 输出/引用

### 图片引用失效

- `verify` 会列 missing refs；检查 `assets/` 是否存在。
- 本地视觉模型没有布局资产时，这是预期；不要伪造 `assets/`。
- 重新转换时用 `--force` 或新输出目录，避免新旧文件混在一起。

### 页号缺失/重复

- 某些 provider 不给完整页结构（本地视觉模型无布局管线）；`content.json` 会退化并警告。
- 重复页文本可能是缓存/页循环错误；用 `--force` 重跑，或换 provider。
- Paddle 拆页后页码错：确认 `--pages` 映射；本技能会把局部 page_index 映射回原页。

### 临时文件

- 中间文件写在输出目录的 `.staging/`（不是系统临时目录），成功后自动删除。
- 需要保留现场时设 `DOCVISION_KEEP_TEMP=1`；删掉整个 `docvision-out/` 即可清干净。

### 中文文件名/路径

- 本技能保留中文输出名，替换 Windows 非法字符；`data_id` 用 ASCII 哈希，不违反 MinerU 约束。
- 路径过长：输出目录尽量短；Windows 260 字符限制仍可能触发，换短目录。
- 控制台乱码：设置 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`；本技能子进程已设置。

## 性能与并发

- 本地：先单页测速，再 `--workers 2`；GPU 显存不足会互相拖慢。
- 远程：默认 `--workers 1`；并发受账号 QPS/额度限制。
- 大批量：先 `--dry-run` 看路线，再分批；保留 `--resume` 避免重复计费。
- 不要在一个命令里混用本地和远程不同 provider；按文件分批更可控。

## 还修不好

保留以下信息再求助/换路线：

```text
doctor --json
env --json
meta.json
qa.json
raw_meta.command（如有）
失败页的页面图
```

不要上传含密钥、个人信息或未发表数据的原始文件到公共 issue。
