# 部署、复用与迁移

## 目录与依赖

技能代码、模型、运行状态、生成产物分开放置。技能可以复制到支持 `SKILL.md` 的宿主目录；宿主不支持自动发现时，显式读取入口并执行同一个 CLI，不必安装 MCP 插件。不要把某宿主的工作目录或用户盘符写进运行文件。

- **客户端**：Python 3.10+；发现、配置、下载和文生图规划使用标准库。参考图和输出校验需要 Pillow，现有 ComfyUI 环境通常已有。优先选择它的解释器；没有时先说明缺什么，再由用户决定建立独立客户端环境，不能污染系统 Python。
- **后端**：支持所选 FLUX.2 klein 或 Z-Image Turbo 及所列原生节点的现有 ComfyUI。已知版本号不代替 `/object_info` 和实测；不自动升级 core、PyTorch、CUDA wheel、自定义节点或前端包。
- **模型**：默认 `models/flux-klein-4b.json`；文字用途可显式选 `z-image-turbo.json`，FP8 mixed 文本备选为 `z-image-turbo-fp8.json`。各自固定来源、revision、精确大小、SHA-256 和布局；不预装全部配置，不自动换精度，不包含 LoRA、ControlNet 或放大器。
- **状态**：默认 Windows `%LOCALAPPDATA%/imagecraft`；其他系统 `$XDG_STATE_HOME/imagecraft` 或 `~/.local/state/imagecraft`。可用 `IMAGECRAFT_HOME` 指定状态根目录，也可在子命令前传 `--config <absolute-config.json>`。
- **产物**：每次生成使用外部独立目录。交付 `image.png`；其余 JSON 为私有记录，含提示词、参考文件路径或服务配置，不默认分享。

客户端不创建 Python 环境、不执行 pip/conda、不注册开机服务、不申请管理员权限，也不修改原 ComfyUI 启动器或包版本。仅 `configure`、显式下载、`serve` 和生成/续接等操作写入各自经过选择的外部目录。

## 现有环境怎么复用

1. `discover` 只做有限范围的只读查找，默认检查常见目录和部分盘符根目录，不全盘扫描。多个候选需人工确认；没找到就请求路径，不启动安装器。
2. 检查 ComfyUI 的 Python、服务地址、模型目录和正在执行的任务。Portable/manual 的外部权重配置一般是 `ComfyUI/extra_model_paths.yaml`；Desktop 通常是用户配置目录中的 `ComfyUI/extra_models_config.yaml`。这些是私人机器配置，不提交仓库。CLI 不擅自猜测或改写其中的映射。
3. 如果三个组件已位于同一共享根目录下的 `diffusion_models/`、`text_encoders/`、`vae/`，`configure --models-root <shared-root>` 即可复用。文件同名但哈希不同是冲突，不覆盖；散落在不同布局里的权重先确认映射或采用用户认可的整理方式，不能一律重新下载。
4. 已运行的服务直接接入。原生节点兼容性及文件枚举会预检，但 HTTP API 不能完全证明另一进程实际从哪个重名路径载入权重；有重复名称/外部搜索路径时必须核对，不把客户端文件哈希误说成服务端远程证明。
5. 服务未运行时，`serve` 复用选中的核心和 Python，使用独立 runtime 目录及启动参数。额外模型映射设为优先，但不改原映射文件；停掉该进程后，原启动器仍按原参数工作。

`serve` 默认只监听配置的回环地址，关闭自动打开浏览器、第三方节点、云 API 节点和 PNG 提示词元数据，并在本次子进程设置 Hugging Face/Transformers 离线与禁遥测选项。采用保守的 low-VRAM、默认 2.5 GiB 预留（`serve --reserve-vram <GiB>` 可调；在大显存卡上调高仅模拟卸载预算，不是显存硬上限或真小卡验证）及关闭 pinned memory/async offload；这些是单次进程参数，不是全局配置。它拒绝占用已有端口，并检查 8188/8189 的其他 ComfyUI 服务；这不能探测所有端口上的 GPU 任务，操作者仍须查 GPU 和相关服务队列。

该模式不是操作系统级网络沙箱，也不是独立 Python 环境；冻结共享依赖、禁用自定义节点不能证明整个后端没有外部行为。若现有环境不兼容，先给出隔离部署计划、磁盘和回退成本，得到批准后另建环境并共享可复用权重，不边测边升级原环境。

## 权重预算与下载

| 组件 | 精度 | 精确字节 | 约 GB |
|---|---|---:|---:|
| FLUX.2 klein 4B distilled | FP8 | 4,070,624,520 | 4.07 |
| Qwen3 4B 文本编码器 | BF16 | 8,044,982,048 | 8.04 |
| FLUX.2 VAE，取自 Klein 包 | BF16 | 336,211,292 | 0.34 |
| 合计 | | 12,451,817,860 | 12.45 |

GB 为十进制磁盘大小，不是运行显存。显存、系统内存、模型卸载行为与分辨率和后端版本有关，不承诺“三个文件能同时驻留 16GB VRAM”。

显式增配 Z 时，INT8 扩散为 6,201,001,296 字节、专用 VAE 为 335,304,388 字节，与 FLUX 共用同哈希的 BF16 Qwen3 文本编码器，总计 14,581,287,732 字节；已有 FLUX 时只需新增 **6,536,305,684 字节**。两个 VAE 哈希不同，不能按通用名称相互替代。`models plan --model z-image-turbo` 会列出与 FLUX 共享的编码器和当前根目录已有文件；散落在别处的同哈希文件仍须先选对共享根，不宣称全盘自动去重。

`z-image-turbo-fp8` 只把文本编码器改为 5,631,994,051 字节的 FP8 mixed 文件，完整组 12,168,299,735 字节；不是 FLUX 的自动低显存档，也未证明与 BF16 质量等价。显式 `--model` 同时适用于 `models plan/download`、`models check --verify`、`doctor` 和 `plan/generate`。Z 只文生图，有参考图时选 FLUX。

16GB＋32GB RAM 为实机完整验证；本卡 reserve 6.5/10.5 下的成功只是小预算探针，真 12GB/8GB 及 16GB 系统 RAM 未验证。先按 [硬件闸](routing.md#第一层硬件与复用) 选择，不把权重总大小或整卡缓存读数当最低显存。

默认单连接下载可续传自己标记过的 `.imagecraft.part`；只有完整大小和 SHA-256 都通过才发布到正式路径。部分文件或哈希失败不会被当成可用模型，也不会覆盖已有正式文件。官方 HTTPS 源固定到 revision；不禁用 TLS 校验、不读账户 token，不自动改用第三方镜像。

网络慢可显式选择：

```text
<python> <skill>/scripts/imagecraft.py models download --yes --workers 8
<python> <skill>/scripts/imagecraft.py models download --yes --transport hf
```

- `--workers 2..16`：标准库分段下载，每段检查 HTTP 范围与大小，组装后再核验整文件哈希；不是只检查各段长度。中断后复用已完整接收的段。峰值磁盘比最终权重多一个最大组件，首次建议预留 **至少 25GB**，加上运行输出另计。使用支持硬链接的本地文件系统（如 NTFS、APFS、ext4）做原子不覆盖发布；不支持时换单连接方式或合适磁盘，不静默降低校验。
- `--transport hf`：仅使用环境中**已安装**的官方 `huggingface_hub`/Xet；不自动安装依赖，仍固定 HTTPS 官方源、禁用账户 token 并核验精确哈希。它有独立暂存目录；与标准库中断缓存不能混用。不能预设它一定更快。

下载会遵循已有网络代理配置，推理 API 则明确绕过代理。若连接失败，报告来源、状态和保留的部分文件，不打印带签名的 CDN 地址或凭据。不同下载方式会留下各自的中断缓存；确认正式文件通过校验后，可列清自己创建的缓存再由操作者清理，不能递归清空用户的模型缓存。

下载器不会自动安装 ComfyUI。模型缺失与后端不兼容是两种问题，不能用“一键安装”混在一起处理。

## 本地示例（PowerShell）

以下路径都是示例，替换后使用；不要把它们原样作为另一台机器的配置。

```powershell
$py = 'D:\ExistingComfy\.venv\Scripts\python.exe'
$cli = 'D:\Skills\imagecraft\scripts\imagecraft.py'
& $py $cli discover --root 'D:\ExistingComfy'
& $py $cli configure --comfy-root 'D:\ExistingComfy\ComfyUI' --python $py --url 'http://127.0.0.1:8189' --runtime-root 'D:\ImageWork\runtime'
& $py $cli models plan
# 在用户批准下载之后：
& $py $cli models download --yes
# 独立终端以前台运行；已有服务就不要再启动：
& $py $cli serve
# 另一个终端：
& $py $cli doctor --verify
& $py $cli generate --prompt 'A ceramic teapot on a wooden desk, soft morning light' --output 'D:\ImageWork\jobs\teapot-001'
```

Bash 使用同样参数，把 PowerShell 的 `& $py $cli` 改为 `"$py" "$cli"` 即可。不要把后台启动写成不受管理的 `&` 或脱离终端的 daemon；使用宿主的受管理后台任务或保留前台终端。服务就绪须通过 API 检查，进程存在或等了几秒不能证明已就绪。

## 迁移与回退

迁移技能代码和必要的权重；通过清单哈希确认，重新选择目标机器的 Python、GPU 配置和目录。**不直接复制 venv/conda 环境或原机器配置**。复制自己的生成记录时保留隐私判断；已完成的本地输出可离线 `verify`，旧机器未完成任务不能在新机器冒认续接。

只卸载技能时，删除宿主的技能入口即可，权重、配置和产物保留；如要清理它们，先列清对应路径、已完成任务与共享使用者，再获得删除授权。不要用全局 kill、清队列、重置 ComfyUI 或卸载共享 Python 包做回退。

环境验收至少覆盖：发现/复用、离线规划、真实文生图、编辑、冷启动、不同请求连续执行、客户端超时后续接、输出损坏检测及原有环境未被改动。没有真实测试的条目标记未验证，不用单元测试替代 GPU 推理或人工看图。
