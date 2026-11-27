# RTX 4060 Laptop（8G 显存 + 24G 内存）迁移与长期研发交接手册

> 更新日期：2026-11-27
> 适用目标机：**NVIDIA GeForce RTX 4060 Laptop GPU（8 GB GDDR6，Ada Lovelace 架构） + 24 GB 内存 + 充足 SSD 存储（Windows）**
> 仓库地址：`https://github.com/Ctrl1CandV/SkillMarket.git`（**长期开发请检出 `dev` 分支**；`main` 仅放已验收发布的纯净技能包）

---

## 一、4060 Laptop（8G 显存 + 24G 内存）配置够用吗？

**结论：完全够用，而且因为是独占空闲的 Ada 架构独显，交互调优体验远好于长期 97% 被占用的台式卡。**

各模块在 `8 GB VRAM + 24 GB RAM` 下的真实资源账本与使用纪律如下：

| 研发环节 | 峰值显存 | 系统内存 | 在 4060 Laptop 上的表现与注意事项 |
|---|---|---|---|
| **WebGL2 / `stage3d.js`（Three.js PBR + 5 级 HDR 泛光）+ `shader.js` 光线步进（1080p@60fps）** | `0.5–1.4 GB` | `1.5–3 GB` | **满血流畅**。3072 个 CUDA 核心 + 第 8 代硬件编码器，跑第二档三维金属/水晶掠光、千枚实例与粒子地形海比 CPU 软渲染快 `10–20` 倍 |
| **本地神经配音 `VoxCPM1.5`（克隆声音卡，`narrate.py`）** | `~2.2 GB` | `~4 GB` | **绰绰有余**（约 1.2–1.5 倍实时生成，`--takes 2` 毫无压力） |
| **新声音卡设计 `VoxCPM2`（仅换新声线时偶用）** | `~5.2 GB` | `~6 GB` | **单独运行时够用**（跑之前关闭浏览器重度 3D 页与 ComfyUI） |
| **词级时间戳与歌词转写 `faster-whisper`（`large-v3-turbo`）** | `~1.8 GB` | `~3 GB` | **完全够用**（`narrate.py` 已做成独立子进程，在 `VoxCPM` 退出释放显存后才启动，显存绝不叠加） |
| **本机辅助生图 `imagecraft`（ComfyUI + FLUX 量化版 / Z-Image Turbo）** | `6.5–7.6 GB` | `14–18 GB` | **可用，守住两条纪律**：① 选 `FP8` / `GGUF Q8` 权重并让 ComfyUI 自动 `--normalvram` 卸载；② 生完底图后调 `/free` 或关掉 ComfyUI 再跑视频渲染与配音 |
| **可选原生 Blender 4.2+ LTS（`EEVEE Next` / `Cycles OptiX`）** | `2.0–6.0 GB` | `4–10 GB` | **够用**。4060 Laptop 带第 3 代 RT 光追核，开启 `OptiX` 跑产品微距、玻璃折射焦散与中等规模刚体动画很稳 |

### 新机必做的两条系统小设置（防爆显存与内存峰值）

1. **串行用卡，不同时常驻两个大模型**：不要一边后台挂着未释放权重的 ComfyUI，一边同时跑 `VoxCPM2` 或 Blender Cycles；`video-craft/kit/gpu.py` 已自带显存与占用率闸门（空闲 `< 4096 MiB` 时会自动提醒保护）。
2. **给 SSD 配 `32 GB` 固定虚拟内存（Pagefile）**：24 GB 物理内存在单独跑视频、配音、Blender 时非常宽裕，但在 ComfyUI 加载 `FLUX` 大权重瞬间会有几秒钟的 CPU 内存峰值。在 Windows「高级系统设置 → 性能设置 → 高级 → 虚拟内存」中，在剩余空间充足的 NVMe SSD 上设 `初始大小 24576 MB / 最大值 32768 MB`，即可彻底杜绝偶发 OOM。

---

## 二、随 Git `dev` 分支已打包带走的全部资产清单

所有核心代码、离线引擎库、标杆拆解与历史维护文档均已提交进 `origin/dev`，**无需从旧电脑手拷零散源码**：

1. **`video-craft` `1.2.0` 完整双轨 + 双档引擎（`video-craft/`）**：
   - **离线第三方库已随包入库**：`kit/vendor/mathjax/tex-svg-full.js`（离线公式 SVG 编译，2.2 MB）、`kit/vendor/three/`（离线 Three.js r160 + `GLTFLoader` + `BufferGeometryUtils`，0.8 MB）、`kit/voices/`（`teacher`、`promo`、`story` 三张基准声音卡 WAV + TXT）。
   - **第一阶段已验收底座（`1.0.0–1.1.3`）**：`lesson.js`（五套开放起手色板 + 自定义语义主题 + MathJax 子项弧线变形 + 具象物理/算法可选模具）、`boardcheck.mjs`（无左右偏置碰撞/穿字/卡片汤检查）、`narrate.py`（自然长句口语门禁 + 词级时间戳 `words.js` + 显卡护栏）、`gpu.py`。
   - **第二阶段刚完成的宣传/MV 双档引擎（`1.2.0`，待在新机 GPU 实测成片）**：
     - 第一档交互与光影：`kit/stage.js`（零过冲微弧线指针 `cursorAt`、定点波纹、计入圆角安全内接框的无漏边穿屏 `throughScreen`、`rollNumber`）、`kit/draw.js`（侧边羽化体积光束 `lightBeam`、预缓存幂律散景 `bokeh`、手持呼吸 `withHandheld`）；
     - 第二档重装绚丽视效：`kit/stage3d.js`（线性浮点帧缓冲、5 级 Karis 防闪烁 HDR 泛光 + `ACESFilmic` 色调映射 + 边缘微色散、程序化摄影棚柔光箱 `studioEnv`、圆角倒角实体 `roundedSlab`、千枚实例声画共振 `instancedField`）、`kit/shader.js`（`{ sdf: true }` 3D 光线步进与薄膜干涉库）、`kit/blender_bridge.py`（兼容 Blender 3.6/4.2+/5.0）及指南 [`spectacle-3d.md`](../../video-craft/references/spectacle-3d.md)；
     - 升级版声音底座：`kit/sound.js` + `audio.mjs`（带前置延迟与空气高频吸收阻尼的自然房间混响、独立于 `duck` 的节拍侧链 `sidechain`、FM 电钢 `epiano`、泛音超低音 `subBass`、玻璃钟琴 `glass`、物理微点击 `uiClick` 与滑擦 `swipe`）；
     - 质检增强：`captions.mjs`（禁 `*.draft.srt`、禁未校改占位符、`--no-overlap`）、`textcheck.mjs`（自动覆盖 `#lyric` 与 `9:16` 竖屏）、`shotlist.py`（识别唱词乐句起音切镜并预警副歌同构重复）。
2. **全新搭建的长期研发工作区（`maintenance/video-craft/studio/`）**：
   - [`studio/README.md`](studio/README.md)：第 4 层高阶镜头招式试炼场的目录约定与 A/B 迭代规矩；
   - [`studio/benchmarks/2026-11-27-openai-showreel/`](studio/benchmarks/2026-11-27-openai-showreel/DECONSTRUCTION.md)：用户指定的“最高视觉标准”标杆片完整 35 镜技术拆解、24 格联系表 `sheet.jpg` 与 4 张代表性关键帧；
   - [`studio/JOURNAL.md`](studio/JOURNAL.md)：首批 7 支 60fps 镜头招式练习曲（Etudes 01–07）研发蓝图。
3. **待跑盲评预案与自动化回归脚本**：
   - `maintenance/video-craft/evals/check-captions.mjs`、`check-phase2-kit.mjs`（6 项全链路单测）；
   - [`maintenance/video-craft/evals/2026-11-26-promo-mv-plan/README.md`](evals/2026-11-26-promo-mv-plan/README.md)（待 GPU 空闲开跑的第二档验收题单）。
4. **未入库、需在新机自动拉取或可选拷盘的大体积本地环境**：
   - HuggingFace / ModelScope 模型权重缓存（`OpenBMB/VoxCPM1.5` 约 2 GB、`faster-whisper-large-v3-turbo` 约 1.6 GB）：新机联网一行命令即可从 ModelScope 高速拉取，亦可直接把旧机 `%USERPROFILE%\.cache\modelscope` 和 `%USERPROFILE%\.cache\huggingface` 拷过去免下载。

---

## 三、4060 Laptop 新机 10 分钟开箱部署步骤（PowerShell）

### 1. 克隆仓库并切入 `dev` 研发分支

```powershell
git clone https://github.com/Ctrl1CandV/SkillMarket.git
cd SkillMarket
git checkout dev
```

### 2. 准备 Node 20+、FFmpeg 与 Playwright 无头渲染依赖

确认本机已有 `node`（建议 v20/v22/v24）、`ffmpeg`（含 `libx264` 与 `aac`，可通过 `winget install Gyan.FFmpeg` 安装）及 Chrome 浏览器后，把 `playwright-core` 装到 `%LOCALAPPDATA%\video-craft-kit`（`env.mjs` 会自动发现它，不污染仓库目录）：

```powershell
$kitDep = "$env:LOCALAPPDATA\video-craft-kit"
New-Item -ItemType Directory -Force -Path $kitDep | Out-Null
Push-Location $kitDep
npm init -y
npm i playwright-core
# 若本机未装 Chrome，可加跑：npx playwright install chromium
Pop-Location
```

### 3. 准备 Python 环境（Conda `skillmarket`）与本地配音/转写模型

```powershell
conda create -n skillmarket python=3.12 -y
conda activate skillmarket

# 安装与 RTX 4060 (CUDA 12.x) 匹配的 PyTorch，以及音频/视觉基础包
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install numpy pillow faster-whisper edge-tts voxcpm modelscope

# 预拉取 VoxCPM1.5 到本机缓存（国内走 ModelScope 极快，`gpu.py` 会离线自动发现）
python -c "from modelscope import snapshot_download; print(snapshot_download('OpenBMB/VoxCPM1.5'))"
```

> 可选设置用户级永久环境变量（省去每次手敲）：
> `[Environment]::SetEnvironmentVariable('VC_PYTHON', "$env:USERPROFILE\.conda\envs\skillmarket\python.exe", 'User')`
> 若后续装了 Blender 4.2+ LTS，`doctor.mjs` 会自动在 `C:\Program Files\Blender Foundation\` 下识别，无需额外配置。

### 4. 一键验收新机环境与全部底座测试

```powershell
$env:PYTHONNOUSERSITE = '1'
node video-craft/kit/doctor.mjs
node maintenance/video-craft/evals/check-captions.mjs
node maintenance/video-craft/evals/check-phase2-kit.mjs
```

看到 `doctor.mjs` 中 `"gpu": { "available": true, "busy": false, "voxcpm15_safe": true }`、`"three": true`、`"broken_scripts": []`，且两套测试全绿输出 `PASS [1/6]..[6/6]`，即代表新机满血就绪！

---

## 四、在新电脑开启下一个研发会话的推荐起手指令

在新机打开 AI 编程助手（Antigravity / Claude Code / Codex）时，直接发送下面这段话即可无缝续接：

> 请依次阅读 `maintenance/optimization/HANDOFF.md`、`maintenance/video-craft/MIGRATION_4060_LAPTOP.md`、`maintenance/video-craft/README.md` 以及 `maintenance/video-craft/studio/benchmarks/2026-11-27-openai-showreel/DECONSTRUCTION.md`（并查看其中的 `sheet.jpg` 和关键帧）。
> 当前我们在 `dev` 分支，本机是空闲的 RTX 4060 Laptop（8G 显存 + 24G 内存）。请先跑一次 `node video-craft/kit/doctor.mjs` 核对硬件加速状态，然后按 `maintenance/video-craft/studio/JOURNAL.md` 的规划，带我在 `studio/etudes/` 开始第一轮 60fps 高水准镜头招式试制与 `1.2.0` 实测验证。
