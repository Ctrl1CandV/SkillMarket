# 引擎与输出

## 1. 选择

先运行 `doctor.py --project <目录>`，看清已安装的工具、项目已用的引擎和中文字体。项目已有引擎就沿用；新项目按内容选：

| 内容 | 引擎 | 理由与代价 |
|---|---|---|
| 动态图形、宣传片、数据故事、口播加字幕、批量模板视频 | **Remotion**（React） | 生态成熟，组件化，能按数据批量渲染；需要 Node 和它自动下载的 Chrome。个人、非营利组织和不超过 3 名员工的公司可免费使用，更大的公司需要购买公司许可 |
| 同上，团队更熟悉 HTML/CSS，或要用 GSAP、Lottie、Three.js | **HyperFrames**（HTML + GSAP） | Apache-2.0；为 agent 设计，按时间定位每一帧渲染；需要 Node 22+ 和 FFmpeg |
| 数学、几何、算法、公式推导 | **Manim Community** | 公式与变形动画最好；需要 FFmpeg、Cairo/Pango，公式需要 LaTeX |
| 想在编辑器里调时间点的讲解动画 | **Motion Canvas** | 生成器写法，时间事件可在编辑器里拖动；渲染通常在编辑器里进行 |
| 已有图片、录屏、视频片段的拼接、配音、字幕 | **ffmpeg** 或 **MoviePy** | 最轻；复杂动画不适合 |

引擎的 API 会随版本变化，具体写法以已安装版本的官方文档为准。Remotion 有官方 agent 技能（`remotion-dev/skills`），HyperFrames 自带技能；宿主装了它们就一并使用，它们管 API 正确性，本技能管内容、画面、节奏和审查。安装新工具和技能前先征得用户同意。

## 2. 确定性：每一帧只由时间决定

代码渲染视频是逐帧截图，不是实时播放。以下要求适用于所有引擎：

- 所有动画属性都从当前帧号或时间计算。不使用 `setTimeout`、`setInterval`、实时的 `requestAnimationFrame`、`Date.now()`；Remotion 中 CSS `transition`/`animation` 和 Tailwind 动画类不会正确渲染。
- 随机数固定种子（Remotion `random('seed')`，Python `random.Random(42)`）。
- 字体、图片、视频、数据在第一帧前加载完成；资源下载到工程里，不在渲染时请求网络。
- 画布尺寸等于输出尺寸，在 1920×1080 上设计，不在小画布上设计再放大。
- 嵌入的视频要能逐帧定位（Remotion 用官方视频组件；HTML 方案用关键帧间隔小的 MP4）。
- 抽查：同一帧渲染两次，结果应完全一致。

## 3. 从 timeline.json 读时间

`storyboard.py timeline` 生成的 `timeline.json` 包含每个镜头的 `start`、`end`（秒）和 `from`、`durationInFrames`（帧），以及配音起点 `vo.start` 和绝对时间的 `beats`、`sfx`。

- **Remotion**：`import timeline from '../timeline.json'`；合成时长用 `timeline.duration_frames`；每个镜头放进一个 `<Sequence from={s.from} durationInFrames={s.durationInFrames}>`（或已安装版本推荐的时间轨组件）；镜头内部用 `useCurrentFrame()` 相对时间。使用会让镜头重叠的转场组件时，重叠会缩短总时长，要按官方文档补偿，保证切点仍与配音一致。
- **HyperFrames**：把 `start`、`end - start` 写进对应片段的 `data-start`、`data-duration`；GSAP 时间线在 `start` 处安排入场。
- **Manim**：在 `construct` 里读取 JSON；每个镜头结束时 `self.wait(max(0, shot["end"] - self.renderer.time))` 补齐到计划时间，避免累计误差；配音用 `self.add_sound()` 或在 `mix_audio.py` 里统一混入。
- **ffmpeg / MoviePy**：用 `start` 和时长生成片段列表与转场偏移。

## 4. 各引擎的要点

### Remotion

```text
npx create-video@latest                      新建工程
npx remotion studio                          预览
npx remotion still <合成ID> renders/s03.png --frame=240
npx remotion render <合成ID> renders/draft.mp4 --codec=h264 --crf=18
```

- 动画只用 `useCurrentFrame()`、`interpolate()`（设 `extrapolateLeft/Right: "clamp"`）和 `spring()`。
- 素材放 `public/`，用 `staticFile()` 引用。
- 中文字体：`@remotion/google-fonts/NotoSansSC` 的 `loadFont()`，或把字体文件放进 `public/` 用官方本地字体加载方式。
- 用 `calculateMetadata` 或直接读 `timeline.json` 决定时长，不把总帧数写死。

### HyperFrames

```text
npx hyperframes init my-video
npx hyperframes preview
npx hyperframes render
```

- 片段用 `data-start`、`data-duration`、`data-track-index`；GSAP 时间线保持暂停并按官方方式注册，由渲染器定位。
- 舞台根元素设不透明背景，避免透明度转场时透出白色。
- 其余命令（检查、截帧）以 `npx hyperframes --help` 和其自带技能为准。

### Manim Community

```text
manim -qh scene.py MyScene                   1080p 60 fps
manim -r 1920,1080 --fps 30 scene.py MyScene
manim -s -qh scene.py MyScene                只存最后一帧
```

- 用 `next_to`、`arrange(buff=…)`、`to_edge`、`scale_to_fit_width` 做相对布局；绝对坐标堆叠是文字重叠的主要来源。画面宽约 14.2、高 8 个单位。
- 竖屏：`config.pixel_width = 1080`，`config.pixel_height = 1920`，同时把 `frame_width`、`frame_height` 改成 8 和 14.2 左右。
- 中文：`Text("中文", font="Noto Sans SC")`；LaTeX 里写中文用 `TexTemplateLibrary.ctex`。
- 每个 `play` 默认 1 秒、`wait` 默认 1 秒，全片会变成匀速的节奏：按内容的重要性设置 `run_time`。
- 不再需要的对象及时 `FadeOut`，避免画面越积越满；公式推导用 `TransformMatchingTex` 让相同的部分留在原位。
- 用 `self.next_section("s03")` 配合 `--save_sections` 可以按镜头输出片段，方便单独检查和重渲染。

### ffmpeg / MoviePy

- 图片推拉（Ken Burns）：`zoompan` 直接用在原图上会抖动；先把图放大到输出尺寸的 4 倍左右再 `zoompan`，或者在代码里用高精度缩放裁切。
- 镜头之间的转场：`xfade=transition=fade:duration=0.5:offset=<秒>`。
- 烧录 SRT 字幕：`subtitles=subs.srt:fontsdir=fonts:force_style='FontName=Noto Sans SC,FontSize=14,Outline=2,MarginV=60'`。SRT 经 libass 渲染时字号按 288 的参考高度换算，`FontSize=14` 在 1080 高的画面上约 52 px。
- `drawtext` 写中文必须用 `fontfile=` 指定中文字体文件。
- MoviePy 2.x 与 1.x 的 API 不同，按已安装版本写。

### 没有框架时

只有浏览器和 ffmpeg 时，可以写一个按时间定位的 HTML 页面：所有动画用暂停的 GSAP 时间线或 Web Animations API，页面暴露 `seek(t)`；用无头浏览器逐帧调用 `seek` 并截图，再交给 ffmpeg 编码。这样慢但确定。能装 HyperFrames 或 Remotion 时优先用它们。

## 5. 中文字体

- 渲染机器上没有中文字体会出现豆腐块。`doctor.py` 会检查系统中文字体；工程里最好自带字体文件并显式加载，不依赖系统。
- 浏览器类引擎：用 `@font-face` 加载工程内的字体文件，并在渲染前确认字体已加载（`document.fonts.ready`，Remotion 的字体加载会自动等待）。
- Manim / Pango：字体要能被系统字体配置找到；用 `fc-list :lang=zh` 检查。

## 6. 输出与平台

上传平台用的成片：

```text
ffmpeg -i <渲染输出> -c:v libx264 -profile:v high -pix_fmt yuv420p -crf 18 -preset slow \
  -r 30 -g 60 -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart final.mp4
```

- H.264 High、yuv420p、恒定帧率、宽高为偶数、AAC 48 kHz、`+faststart`（边下边播）。文字多、纯色多的画面 CRF 用 16–18。
- 交给剪辑软件的中间文件用 ProRes 422 HQ 或高码率 H.264；透明背景用 ProRes 4444 或带透明通道的 WebM。
- 帧率：默认 30；录屏、滚动界面和快速运动用 60；要电影感用 24 或 25。
- 封面：导出标题清楚的一帧 PNG；竖屏封面同样避开界面遮挡区。

| 平台 | 画幅 | 分辨率 |
|---|---|---|
| B 站、YouTube、西瓜视频 | 16:9 | 1920×1080，可 3840×2160 |
| 抖音、快手、视频号、TikTok、Shorts、Reels | 9:16 | 1080×1920 |
| 小红书、信息流 | 3:4 或 4:5 | 1080×1440 或 1080×1350 |
| 方形 | 1:1 | 1080×1080 |

平台的上传规格会变，正式发布前核对最新要求。`mix_audio.py` 输出的文件已经符合上面的编码参数；`video_qa.py probe` 会检查编码、像素格式、帧率、faststart 和音视频时长。
