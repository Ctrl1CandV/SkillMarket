---
name: video-craft
description: 用代码制作视频时使用：解说与科普、产品演示与宣传、数据故事、教程与代码讲解、竖屏短视频、片头与动态标题，用 Remotion、HyperFrames、HTML/GSAP、Manim、Motion Canvas 或 Python/ffmpeg 生成。把需求落成口播稿、带时长的分镜、风格令牌与样帧，再编排运动、配音、字幕与音乐，最后渲染联系表、切点帧条和检测报告，实际看过再修订。用户说“做个视频/动画/宣传片/讲解视频/短视频”“用 Remotion 或 Manim 做”“AI 做的视频像 PPT、不好看”时使用。不用于 Sora、可灵等生成式视频模型的提示词，实拍素材的精剪调色，或纯音频制作。
metadata:
  version: "0.1.1"
---

# Video craft：用代码做视频

好的视频让观众每一刻都知道该看哪里：画面负责讲解，旁白负责串联，屏幕文字只点出关键词和数字；每个运动都有原因，方向一致，节奏有快有慢；有配音时声音就是时钟，画面落在说到的那个词上。代码能精确控制每一帧，难处在于先想清楚每一帧该是什么，做完再实际看渲染结果。

AI 直接写出的视频，常见的样子是“会动的幻灯片”：每屏一个标题加几条要点，逐条淡入，居中排列，镜头之间互不相关，写完代码就交付。本技能把制作拆成几步，每一步都有能看、能量的产物，后一步以前一步为依据。

## 接收任务

先把需求写成数字和清单，存为 `video/brief.md`：

- 用途与平台、观众、看完要记住或能做到的一件事；
- 画幅、分辨率、帧率、总时长；
- 语言，是否要配音、字幕、音乐；
- 必须出现的内容、数据与素材，品牌色和字体；
- 交付格式。

缺失的信息只在会实质改变成片时询问，其余用默认值并在交付时说明：横屏 1920×1080，竖屏平台 1080×1920，30 fps，中文；有配音就同时出字幕；未指定时长时按内容定，教学类单段不超过 6 分钟，宣传类 15–60 秒。用户给了参考视频，先抽帧看清它的构图、配色和节奏（`video_qa.py sheet`），写下要借鉴的具体做法。

## 工作顺序

用户只要脚本、分镜或局部修改时，只做那一部分。

1. **内容：一句话要点与口播稿。** 读 [内容与脚本](references/content.md)。按视频类型选结构，口播写成适合听的短句，分清画面、旁白、屏幕文字各自负责什么，写入 `video/script.md`。
2. **分镜：带时长的镜头表。** 读 [分镜与构图](references/storyboard.md)，写 `video/storyboard.json`：每个镜头的作用、视觉主体、构图、景别、运动、与下一镜头的衔接、旁白和屏幕文字。用脚本检查时长、语速、文字量和画面变化：

   ```text
   python <skill>/scripts/storyboard.py check video/storyboard.json
   ```

3. **风格与样帧。** 读 [画面与风格](references/visual.md)，选定一个风格方向，写成 `video/style.json` 令牌（颜色、字体、字号、圆角、线宽、质感），全片共用。做动画之前，先按最终分辨率渲染 2–3 张最关键的静帧：开场、信息最密的一镜、数据或结构镜头，缩小拼成一张图来看，细节处再裁局部。改到满意再继续，这一步改起来最便宜。
4. **声音先行。** 有配音时读 [声音与字幕](references/audio.md)：按镜头分段生成配音，量出真实时长，生成时间线和字幕；配音还没有时先按语速估算出草稿时间线，配音到位后重新生成。没有配音的片子也用同一命令生成时间线。代码从时间线读取每个镜头的起止，不手写秒数：

   ```text
   python <skill>/scripts/storyboard.py timeline video/storyboard.json --audio-dir video/audio/vo --out video/timeline.json
   python <skill>/scripts/storyboard.py srt video/storyboard.json --timeline video/timeline.json --out video/subtitles.srt
   ```

5. **运动编排。** 读 [运动与转场](references/motion.md)。先排主体，再排跟随；同类元素共用一套缓动与时长；全片只用 2–3 种转场，方向保持一致。
6. **渲染与审查。** 读 [审查](references/review.md)。对草稿生成联系表、切点帧条和检测报告，逐张看图后修订：

   ```text
   python <skill>/scripts/video_qa.py all video/renders/draft.mp4 --timeline video/timeline.json --out video/qa/draft-01
   ```

7. **混音与交付。** 合成配音、音乐和音效，压低音乐让位人声，统一响度：

   ```text
   python <skill>/scripts/mix_audio.py --video video/renders/draft.mp4 --timeline video/timeline.json --music video/audio/music.mp3 --out video/renders/final.mp4
   ```

## 选择引擎

读 [引擎与输出](references/engines.md)。先看机器上已有什么、项目已经用什么：

```text
python <skill>/scripts/doctor.py --project <项目目录>
```

| 内容 | 首选 |
|---|---|
| 动态图形、产品宣传、数据故事、口播加字幕 | Remotion（React）或 HyperFrames（HTML + GSAP） |
| 数学、几何、算法、公式推导 | Manim Community |
| 已有图片、录屏、视频片段的拼接与配音 | ffmpeg 或 MoviePy |
| 内容本身是网页或产品界面 | 能按时间逐帧渲染的 HTML 方案（HyperFrames、Remotion） |

项目已有引擎就沿用。引擎 API 以已安装版本的官方文档和官方 agent 技能为准（Remotion 有 `remotion-dev/skills`，HyperFrames 自带技能）；本技能负责它们不管的部分：内容、分镜、画面、节奏、声音与审查。无论用哪种引擎，每一帧都只由时间决定：所有动画从当前帧或时间计算，随机数固定种子，字体和素材在第一帧之前加载完成。

## 审查实际画面

读代码不等于看过成片。渲染后至少看三样：由各镜头中段和末帧组成的联系表、每个切点前后的帧条、检测报告（黑帧、白闪、长时间静止、静音、响度、编码参数）。宿主能看图就逐张看；不能看图时，说明只完成了自动检测，画面质量交给用户判断。

看图有成本：读进来的图会一直占着上下文。看联系表和帧条把握全局，只对有疑问的地方裁出局部原尺寸看，不逐张读整幅原图。

第一版完整草稿出来就先放到交付位置，之后有更好的版本再替换。每轮把问题列全、一次改完：先修阻断问题（缺字或豆腐块、文字越界被裁、元素重叠、白闪黑帧、音画不同步、数字错误），再修主要问题（焦点不明、字太小、节奏拖沓或过快、运动没有原因、风格不统一、转场杂乱），偏好留给用户。草稿通常改一到两轮。修改后重新渲染受影响的镜头再审查，最终报告必须对应最终文件。

## 工作区约定

```text
<project>/video/
  brief.md          需求与默认值
  script.md         一句话要点、结构与口播稿
  storyboard.json   分镜：时长、构图、运动、旁白、屏幕文字
  style.json        风格令牌
  timeline.json     由配音实测生成的时间线，代码只读它
  assets/           素材，附来源与许可
  audio/            配音分段 vo/、音乐、音效 sfx/，附来源与许可
  src/              引擎工程（也可以在已有项目里，路径写进 brief）
  renders/          样帧、草稿与成片
  qa/               联系表、帧条、检测报告与审查记录
```

`renders/`、`qa/` 和大体积音频在 Git 项目里默认不提交。

## 交付

交付成片（H.264、yuv420p、AAC，可直接上传）、字幕文件、封面帧和能重建成片的工程。简要说明：内容与风格的选择、实际看过哪些画面、检测结果（时长、响度、编码）、仍存在的问题和没验证的部分（例如宿主听不到声音时，配音读音只经过转写核对或没有核对）。音乐、字体、图片写明来源与许可。

## 按需阅读

| 现在要决定的事 | 读 |
|---|---|
| 讲什么、按什么结构、口播怎么写、画面和文字怎么分工 | [内容与脚本](references/content.md) |
| 镜头怎么切分、构图、景别，镜头之间怎么衔接 | [分镜与构图](references/storyboard.md) |
| 风格方向、配色、中文字号、安全区、素材与数据图 | [画面与风格](references/visual.md) |
| 缓动、时长、错峰、镜头运动、文字动画、转场 | [运动与转场](references/motion.md) |
| 配音、字幕、音乐、音效与响度 | [声音与字幕](references/audio.md) |
| 选哪种引擎、确定性规则、各引擎要点、编码与平台规格 | [引擎与输出](references/engines.md) |
| 怎么看成片、检查清单、问题分级 | [审查](references/review.md) |
| 完整分镜与风格令牌示例 | [示例分镜](assets/storyboard.example.json)、[示例令牌](assets/style.example.json) |

所有相对路径以本文件所在目录为基准。
