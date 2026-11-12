---
name: imagecraft
description: 辅助型生图：为文章与汇报配图、前端页面方案比较、图标底图与无字素材、需要一张图才能继续讨论的任务出图；也为本身不能生图的模型补上出图、取回、核对与记录的链路。用户说“画一张”“生成图片”“配图”“出几版视觉稿”“做个封面/插画/背景”时使用。本机有合适显卡时复用现有 ComfyUI，默认 FLUX.2 klein，短中文标题可显式选 Z-Image Turbo；本机不适合时用用户已有的 GPT 订阅登录出图。内容与数字必须精确、或以后还要反复修改的图改用 HTML/SVG/TikZ 原生绘制。首次使用先判断本机条件，产物与中间文件放项目 .imagecraft/ 便于清理。不用于数据图表绘制、可交互网页实现或照片修图。
metadata:
  version: "0.3.1"
---

# Imagecraft：辅助生图

这个技能多数时候是配角：价值在于让用户的任务往前走一步——文章有配图、页面有可比较的方案、讲解有能用的示意图。判断标准是"这张图帮上忙了吗"，不是"这张图惊艳吗"。

它同时是**能力补位**：不少宿主模型只能读写文字，能写出完整的构图描述，却拿不出一张图。这个技能把描述接到真实出图链路上（本机 ComfyUI 或用户已有的 GPT 订阅），把结果变成宿主可以继续使用的文件与记录。

## 负责什么

- **任务辅助**：文章、汇报、概念讲解需要的配图与示意图。图是辅助材料，读者注意力在正文上。
- **补足宿主缺失的生图能力**：宿主只会写字时，由本技能出图、取回文件、核对与记录。宿主没有看图能力时，如实说明只做了技术校验，把画质判断交给用户。
- **方案比较**：做前端页面前先出几种视觉方向，用来选型，不是最终实现。
- **需要图才能继续的任务**：图标底图、无字素材、背景图、风格探索、给用户看的草图。
- **交给原生绘制的**：可交互网页、需要精确数字的图表、要进 LaTeX 的架构图、以后还要改很多遍的视觉稿，用 HTML/CSS/SVG/TikZ/PPT 原生形状直接写，内容和修改都可控。

## 先选路径

先问这张图以后还要不要改、内容是否必须精确；要改或必须精确就走原生绘制，能接受栅格成品再选出图通道。

| 路径 | 用在 | 代价 |
|---|---|---|
| 本机 FLUX.2 klein（默认） | 素材、无字底图、风格探索、参考图编辑 | 约 4 秒一张；文字和连线不可靠 |
| 本机 Z-Image Turbo（`--model z-image-turbo`） | 短中文标题、书封、海报主标题等少量文字 | 约 24 秒一张；只能文生图，全身人物易裁头 |
| GPT 订阅（`scripts/cloud_codex.py`） | 论文配图、PPT 结构图、页面视觉稿、文字较多的成品 | 需用户授权上传；每张约 2–3 个百分点额度，可能拥堵 |
| HTML / SVG / TikZ / PPT 原生 | 数字可靠、逐字精确、后续要改、要进 LaTeX 或要交互 | 要写代码和看渲染结果 |

两种本机模型都画不对完整的节点与连线；复杂结构图走 GPT 或原生绘制。实测数据与取舍依据见 [三层分工](references/routing.md)。

## 首次使用：先判断这台机器

下载权重之前先判断这台机器值不值得。按顺序看三件事，任何一步不成立就先用 GPT 订阅，本机部署留给用户决定。

1. **显卡与内存**：跑 `discover`，输出的 `gpu` 字段给出型号与显存（绑定后 `doctor` 也会报告）。不要只凭 `nvidia-smi` 命令找不到就说没有显卡：WSL 里它常不在 PATH 上。`state` 为 `present_but_inaccessible` 表示驱动在、当前环境却访问不到显卡，多见于沙箱或容器；这时请用户在普通终端跑一次 `nvidia-smi` 确认，不把它当成“没有 N 卡”。

   | 显存 | 建议 |
   |---|---|
   | 16 GB（配 32 GB 内存） | 已完整验证，两种模型都可用 |
   | 12 GB | 可以试 FLUX，先用 1024×1024，告诉用户这一档只有模拟数据 |
   | 8 GB | 默认用 GPT；用户愿意排障时才实验性试 FLUX 1024×1024 |
   | 更低、核显或没有 N 卡 | 用 GPT 或原生绘制 |

2. **有没有可用的 ComfyUI**：跑 `discover`。找到就复用，尤其是已经能跑 FLUX 或视频的那一套。没找到先问用户装在哪；确实没有、硬件也够，就说明两种选择：现在用 GPT，或由用户自己装官方 ComfyUI（Desktop 或 Portable）后再回来绑定。本技能自己不运行安装器。
3. **权重在不在**：FLUX 三个文件共 12.45 GB，首次建议预留至少 25 GB 磁盘。Z-Image 与 FLUX 共用文本编码器，已有 FLUX 时只需再下约 6.54 GB。已有同哈希文件就复用（`--models-root` 指向共享根），缺了征得同意再下载；用户需要哪个模型就只装哪个。

绑定只需一次，完整做法见 [部署与复用](references/deployment.md)：

```text
<python> <skill>/scripts/imagecraft.py discover
<python> <skill>/scripts/imagecraft.py configure --comfy-root <existing-ComfyUI> --python <existing-python> --url http://127.0.0.1:8188
<python> <skill>/scripts/imagecraft.py models plan            # 增配 Z 时加 --model z-image-turbo
<python> <skill>/scripts/imagecraft.py serve                  # 服务没在跑时，放在单独终端前台运行
<python> <skill>/scripts/imagecraft.py doctor --verify
```

`<python>` 用那套 ComfyUI 自己的解释器（Portable 版是 `python_embeded/python.exe`，手动安装通常是其 `.venv` 或 conda 环境）。服务已经在跑就直接接入，不再起第二个。模型放 `ComfyUI/models/` 下的 `diffusion_models/`、`text_encoders/`、`vae/`；已有 `extra_model_paths.yaml` 的机器按原映射走。本技能不升级 ComfyUI、不装自定义节点、不改原启动器。

GPT 这一路的安装与登录（`npm install -g @openai/codex`、`codex login`）见 [云端路径](references/cloud-fallback.md)，同样由用户批准后进行。

**两条出图通道都用不了时，先停下来说清楚。** 任务要的是栅格图（封面、插画、照片感素材），而本机和 GPT 订阅都不可用时，不要自己用代码画一张顶替。先告诉用户缺的是什么、补上哪一样就能出图（在普通终端确认显卡、绑定现有 ComfyUI，或授权登录 GPT 订阅），再提出马上能做的替代，例如扁平的矢量示意图，由用户决定。能问就先问。问不了（一次性任务、用户不在场）时可以做替代图，但交付的第一句写明它是代码绘制的替代品、不是生图结果，说清补上什么就能换成真正的生图，并且只做一两轮修改，不在替代品上反复打磨。

## 每次任务怎么做

先把要求写成能核对的东西，再出图。"专业、精美、高质量"这类词对结果没有约束力，逐字的文案清单和具体的风格描述才有。

1. **写 brief**：主体、用途、画幅、必须出现的文字、必须避免的元素，存到 `<project>/.imagecraft/briefs/`。按任务类型套 [需求与验收](references/task-briefs.md) 的模板；密集页面与架构图用清单式写法。
2. **写提示词**：本机模型用英文写清主体、位置、材质、光线和构图，缺什么补什么，不必凑长度；要出现的文字用引号原样给出。写法见 [本机提示词](references/task-briefs.md#本机提示词怎么写)。GPT 直接用内容契约。
3. **生成**：本机先 `plan` 看清要提交什么，再用新的输出目录 `generate`。素材、插画这类凭感觉挑的图，经用户同意可换 2–4 个 seed 各出一张再挑；文字、计数或结构错了，改 brief 或换路径，而不是继续换 seed。GPT 每张都要用户授权，一次只提交一张。
4. **打开看**：脚本成功只代表像素生成了。文字、节点、箭头、数值逐项核对，记下多出来的东西。
5. **交付**：给出绝对路径、尺寸、seed（云端写"未提供"）和实际观察到的问题。栅格图要说明改字需重出。

```text
# 本机
<python> <skill>/scripts/imagecraft.py plan --prompt-file <brief.txt> --seed 42
<python> <skill>/scripts/imagecraft.py generate --prompt-file <brief.txt> --output <project>/.imagecraft/jobs/<slug> --wait 600
<python> <skill>/scripts/imagecraft.py generate --model z-image-turbo --prompt-file <brief.txt> --output <project>/.imagecraft/jobs/<slug>-z --wait 600
<python> <skill>/scripts/imagecraft.py review --job <dir> --verdict accepted --notes "看到什么就写什么"

# GPT 订阅（已获上传授权）
<python> <skill>/scripts/cloud_codex.py generate --prompt-file <brief.txt> --output <project>/.imagecraft/jobs/<slug>-cloud --approve-cloud --wait 600
<python> <skill>/scripts/cloud_codex.py status --job <project>/.imagecraft/jobs/<slug>-cloud
```

带 `--reference` 的编辑任务自动使用 FLUX。任何结果不明（超时、中断、状态 `unknown`）都先用 `status`/`resume` 查原任务，不新开目录重交。

## 工作区约定

临时内容和结果都放在**用户当前项目**里，方便一次性清理：

```text
<project>/.imagecraft/
  briefs/     本次任务的提示词与内容清单
  jobs/       每次生成一个目录，含 image.png 与 job.json
  scratch/    参考图、裁切、对照图
  evidence/   需要保留的验收记录与评语
```

- 把 `.imagecraft/` 加进项目的 `.gitignore`；用户明确要归档时才提交。
- 一个任务一个目录，名字用用途（`hero-ceramics/`、`fig2-pipeline/`），后期好认。
- 产物还要用时，把最终图拷到用户指定位置；之后 `.imagecraft/` 可整体删除。清理前先确认没有未交付的内容。
- 需要换位置时用显式 `--output`，不改全局默认。
- 为了预览临时要装的依赖，放进项目自己的环境（`.venv`、`node_modules`）。不往用户目录装字体或全局包；确实需要时先说明要改什么。

## 验收纪律

- 文字和结构分开算：标签读得出不代表节点没有合并，箭头只按准确的起点、终点和方向认。
- GPT 也要逐项核对：实测中它把 130 处指定文字全写对，同时自作主张加了坐标轴刻度、改了卡片尺寸。偏离如实报给用户。
- 区分四种产物：模型原图、局部修补、分层合成、整图重建。修补过的图注明改了哪一块。
- 一张成功不等于这类任务都能成；没有跨图证据就不下质量结论。

## 边界

- 私人照片、未公开设计或论文只在用户明确同意、并知道会离开本机时才上传云端。
- 用户有游戏或其他 GPU 任务在跑时不启动推理，也不关闭用户进程。
- 订阅路径只用官方客户端自己的登录：不读 cookie 或 token，不切 API key，不买 credits，不轮换账户绕额度。
- 模型按用途增配，不为"覆盖更多类型"预装。

## 按需阅读

| 现在要决定的事 | 读 |
|---|---|
| 这张图该走本机、GPT 还是写代码；硬件门槛的依据 | [三层分工](references/routing.md) |
| 怎么组织提示词、不同题材看什么 | [需求与验收](references/task-briefs.md) |
| 内容要精确、文字要可控 | [内容前置](references/content-first.md) |
| 只错几个字或一条线 | [局部修补](references/raster-repair.md) |
| 首次部署、复用现有 ComfyUI、迁移 | [部署与复用](references/deployment.md) |
| GPT 订阅：安装、登录、提交、额度与失败处理 | [云端路径](references/cloud-fallback.md) |
| 模型与工作流的出处 | [来源](references/sources.md) |

所有相对路径以本文件所在目录为基准，不要按当前工作目录猜。
