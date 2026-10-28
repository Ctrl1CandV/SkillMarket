# 0.3.0：只留 Paddle 云端、首次询问与固定存储、项目内中间文件

日期：2026-10-28（Asia/Shanghai）。开发分支 dev，提交前状态。两份用户要求：

1. 通用 skill 不绑定某台电脑：满足条件的机器首次使用就能搭好稳定环境（模型在固定路径）。
2. 后续使用只在项目本地产生过程文件，便于清理。

复查后发现两条都未完全满足，本版按下面的方案修正。

## 1. 删除无验证的云端路线

原因：Gemini 只是在“PaddleOCR 还是 Gemini”二选一时被顺带留下的；`gemini-3.8-flash` 是第二版自行填入的默认型号，v1 里是空值，无法用任何 key 验证，Google 已知命名也不存在这个型号。GLM、Mistral、MinerU Standard/Agent 同样没有可用 key，代码与文档构成“看起来支持”的承诺。

删除：

- `providers/gemini_cloud.py`、`glm_cloud.py`、`mistral_cloud.py`、`mineru_cloud.py`
- `config.py` 中 `gemini_base` / `gemini_model` / `glm_base` / `mistral_base`，`remote_keys()` 只剩 `paddle`
- `openai_compat` 的远程分支（保留 loopback 本地视觉 `local-vlm`）
- `cmd_usage`、`doctor._remote_probe`、`refine` 的 VISION/OCR 集合、`detect.choose_provider` 的远程候选
- 文档里所有 Gemini/GLM/Mistral/MinerU 云端章节与对照表行

现在远端只有 `paddleocr-cloud` 一条，且必须是“账号验证过 + 安装级同意 + 单次 `--allow-remote`”。

## 2. 首次使用必须询问，拒绝是持久状态

- `config.json` 新增 `remote.consent`：`unset | remote | local-only`。
- 新增 `docvision setup --local-only` / `--remote`（只写同意状态，不装环境）。
- 新增 `docvision credentials set|show|remove|path`：
  - `set` 只从 stdin 读密钥（拒绝 argv，避免进入 shell 历史），写入后默认把 consent 记为 `remote`；`--local-only` 则只存密钥不开上传。
  - `remove` 删除文件并把 consent 改为 `local-only`。
- 强制点：`detect.choose_provider`、`cli._guard_remote`、`refine.choose_provider` 三处检查 `local-only`，命中直接报错，即使传了 `--allow-remote`。
- SKILL.md 写明“第一次 convert/refine 前必须显式问一次”，并给出用户拒绝后的固定动作。

## 3. 凭据固定位置

- 唯一位置：`{SKILL_DIR}/.credentials.env`；解析顺序 `--env-file` → `DOCVISION_ENV_FILE` → skill 文件 → `cwd/.env`。
- 随附 `docvision/.gitignore` 屏蔽该文件与 `.staging/`；写入前用 `git check-ignore` 复查，未忽略则拒绝写入。
- POSIX 写入后 `chmod 600`。**Windows 上 `chmod` 只切换只读位，不等于 POSIX 0600**，实际保护来自用户目录 ACL 与 `.gitignore`——文档按这个事实写，不宣称等价。
- `doctor` / `env` / `credentials show` 只显示 set/not set，不打印值。

## 4. 模型固定在用户数据目录

- 固定根：Windows `%LOCALAPPDATA%\docvision\models`，Linux/macOS `~/.local/share/docvision/models`；`mineru/` 与 `paddlex/` 两个子目录。
- 覆盖：`config.json` 的 `models_dir` → `DOCVISION_MODELS` → 默认；`setup --models-dir` 写入配置。
- 已存在 `~/.mineru` / `~/.paddlex` 的机器自动复用旧安装（不在显式覆盖时回退），避免为了统一路径重新下载数 GB；`doctor` 同时显示“配置根”与“实际生效目录”。
- Paddle 子进程显式传 `PADDLE_PDX_CACHE_HOME`，MinerU 传 `MINERU_HOME`，不再依赖各工具的默认值。

## 5. 中间文件回到项目内

问题：两个本地 provider 用 `tempfile.mkdtemp()` 建暂存目录且**从不删除**。实测本机残留 34 个 `docvision-mineru-*` / `docvision-paddle-*`，13 MB，每次转换 +1，`%TEMP%` 里用户找不到也清不掉。

修正：

- `Options.staging` + `util.staging_dir()/release_staging()`：转换写到 `<output>/.staging/`，精读写到 `<refinement>/work/`，成功即删、空目录一并移除。
- 需要保留现场时设 `DOCVISION_KEEP_TEMP=1`。
- 清理失败也不影响结果（`ignore_errors`），但不再默认留垃圾。

实测同一张图：修复前 `%TEMP%` provider 目录 34→35；修复后 35→35，`./docvision-out/.staging/` 为空且被移除。输出内容不受影响（`qa pass`）。

## 6. 验证

- `unittest discover maintenance/docvision/evals`：**123 项通过**（新增 consent 拒绝、skill 文件优先于 cwd `.env`、写入只保留白名单名字、git 未忽略时拒绝写入、删除凭据、`local-only` 时 auto 不选云端、本地视觉只能 loopback 等）。
- `check.py`：4 项通过（Paddle 云端 mock 契约、上传闸门、`local-only` 拒绝、密钥不落 config）。
- 真实调用（非 mock）：
  - `mineru-local` 单页 7.7 秒，`qa pass`，模型沿用既有 `MINERU_HOME`。
  - `paddleocr-local` 单页 10.4 秒，`qa pass`，未新建模型目录（复用 `~/.paddlex`），说明回退逻辑生效。
  - `paddleocr-cloud` refine 公式裁图 4.2 秒，`recognized`，凭据来自新的固定文件，consent=remote。
- `doctor` 显示：本地两引擎 ready、paddle key set、consent remote、模型配置根与实际目录分别列出。

## 7. 未验证 / 边界

- 没有在“全新机器”上跑完整 `setup` 流程（本机环境已存在），首次安装路径仍只有命令与索引解析验证。
- 没有 8 GB 真机、峰值显存、20–30 页标注集与双并发基准；这些不因本版改变。
- Windows 上 `chmod 600` 不生效的说明已写进文档；未做 NTFS ACL 收紧。
- 本地视觉 `local-vlm` 只做了协议与 loopback 约束的单元验证，没有可用本机视觉模型做真实图形解释。
- 删除代码后，`git log` 仍可找回旧适配器；如需恢复某个云端，应同时补真实 key 验证，而不是直接 revert。
