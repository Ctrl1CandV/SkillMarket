# 工具包

`kit/` 里有两类文件。

- **浏览器里用的模块**：
  - `kit.js`：缓动、弹簧、随机数、颜色、字体、注册函数，以及跟随录音的 `songAt`、`envAt`、`pulse`。
  - `lesson.js`：课程、讲题与硬核科普 SVG 引擎：支持五套开放起手色板（`ivory`/`paper`/`blueprint`/`chalk`/`slate`）与任意自定义语义主题 `resolveTheme`、离线同步 MathJax v3 公式编译（`\id{key}{expr}` 子项寻址、`role: 'label'` 图内短标豁免）、跨步弧线平滑变形 `morphFormula`、子项信号框 `highlightPart`、词级旁白时间线 `buildTimeline`、无重影分幕序列器 `actAt`、2D/3D 焦点相机、坐标系与函数曲线、工程标尺 `svgRuler`、力矢量剥离闭合 `svgMorphArrow`、极坐标轨迹扇 `svgLocusFan` 及可选具象参考模具（`svgMediaTank`/`svgStepColumns`/`svgCard`/`svgNodeBox`/`svgArray`）。详见[课程与讲题制作指南](course-and-stem.md)。
  - `stage.js`：第一档产品演示、软件界面与空间转场的纯函数调度原语（无绑定配色）：零过冲微弧线指针与定点点击波纹（`cursorAt`、`drawCursor`）、计入圆角安全内接框的无漏边穿屏相机（`throughScreen`、`cssStageTransform`、`applyStageCamera`）、两阶段原地形变与轨迹移位（`morphMoveRect`、`lerpRect`、`arcPoint`）及防跳位跳字格式化（`rollNumber`）。详见[产品宣传与软件演示](explain-and-demo.md)。
  - `stage3d.js`（+ `kit/vendor/three/` 离线 Three.js r160）：**第二档重装绚丽视效引擎**——线性浮点帧缓冲、5 级 Karis 防闪烁 HDR 泛光 + `ACESFilmic` 色调映射 + 边缘微色散后期合成器 `createStage3D`、程序化摄影棚柔光箱 `studioEnv`、动态掠光灯组 `addStudioRig`、物理材质 `pbrMaterial`（金属/钛合金/折射水晶玻璃/薄膜虹彩/清漆陶瓷/自发光灯丝）、多段平滑倒角实体 `roundedSlab`、千枚三维实例场 `instancedField` 与窄焦环绕推拉相机 `orbitCamera`。详见[第二档：重装绚丽视效指南](spectacle-3d.md)。
  - `draw.js`：分层、噪声、光晕与 bloom、侧边羽化体积光束 `lightBeam`、预缓存幂律散景 `bokeh`、山脊剪影、视差相机、纯函数手持呼吸 `handheld`/`withHandheld`、逐渐画出的线、暗角和颗粒。
  - `graphic.js`：版面式动态设计的零件：纸面、网格、色条、角标、逐字解出的标签、大字进场、卡片、刻度圆环、波形、平面着色的 3D 形体，以及三种遮罩转场。
  - `shader.js`：把一段 GLSL 片元着色器变成一张可叠加的画布，画星云、极光、烟和液态光；传 `{ sdf: true }` 额外注入 3D 光线步进（Raymarching SDF）与薄膜虹彩/ACES 调色函数库。
  - `sound.js`：自然高频阻尼房间/大厅混响与可选磁带柔饱和混音台、合成乐器（含 FM 电钢 `epiano`、单声道泛音超低音 `subBass`、通透钟琴 `glass`）、触感界面拟音（确定性微点击 `uiClick`、空气滑擦 `swipe`）、独立侧链呼吸 `sidechain` 与人声避让 `duck`，测响度并编 Opus/WebM。
- **Python 工具**：`gpu.py` 采样显卡利用率、空闲显存并解析本地离线模型缓存；`songmap.py` 给歌曲做地图；`shotlist.py` 给成片列镜头表并标出可疑剪辑（支持 `--mode lesson` 讲题模式与 `--song` 唱词起音/重复乐段比对）；`narrate.py` 生成旁白并导出逐词时间戳 `words.js`；`blender_bridge.py` 为本机已装 Blender 时的第二档无头渲染提供跨版本（3.6/4.2+/5.0）摄影棚、材质、AgX 泛光与 `songmap` 拍点采样桥接。需要 Python 3.9+、NumPy 和 FFmpeg。
- **Node 命令行工具**：渲染、版面碰撞检查（`boardcheck.mjs`）、出音轨。它们通过 Playwright 驱动无头 Chromium 打开场景页，逐帧调用 `__seek(t)` 截图，再交给 ffmpeg 编码。
- 图片、录屏或其他引擎的镜头已有文件时，可单独用 `cut.mjs` 做有声动态分镜或最终组装，只依赖 Node 与带 libx264 的 FFmpeg。格式和可复制的命令见[剪辑单](editing.md)。

## 安装与环境

在项目里装上 playwright-core 和浏览器：

```text
npm i -D playwright-core
npx playwright install chromium        # 或 chromium-headless-shell
```

找不到工具时，用环境变量指定：

| 变量 | 作用 |
|---|---|
| `VC_NODE_MODULES` | 含 `node_modules/playwright-core` 的目录（默认依次找当前目录、kit 目录） |
| `VC_CHROME` | Chromium 或 chrome-headless-shell 的可执行文件 |
| `VC_FFMPEG` | ffmpeg 路径（默认用 PATH 里的） |
| `VC_FFPROBE` | ffprobe 路径（默认取 ffmpeg 旁边的同名文件），供 `shotlist.py` 与 `mux_original.py` |
| `VC_PYTHON` | doctor 检查的 Python（默认 `python`）；装了 VoxCPM 的环境另建时指向它 |
| `VC_VOXCPM` | VoxCPM 模型目录或 Hugging Face id（默认优先离线发现本机 ModelScope/HF 缓存中的 `VoxCPM1.5`） |
| `VC_WHISPER` | faster-whisper 模型目录或名字（默认优先离线发现本机缓存中的 `large-v3-turbo`），供 `songmap.py --lyrics` 与 `narrate.py` 词级对齐 |
| `VC_BLENDER` | 可选 Blender 可执行文件路径（供第二档离线光追桥接 `blender_bridge.py` 与 `doctor.mjs` 探测） |
| `VC_SOFTWARE_GL` | 设为 `1` 时强制无头浏览器走 SwiftShader 软件渲染，避开高占用物理显卡 |

有些沙箱需要额外设置 `LD_LIBRARY_PATH`（缺系统库时）和 `FONTCONFIG_FILE`（没有中文字体时）。`node kit/doctor.mjs` 会报告浏览器版本、WebGL 渲染器、WebCodecs 支持哪些编码、语音数量，以及 ffmpeg 有没有 VP9/H.264/AAC 编码器，并给出建议。

Ubuntu/WSL 上 `sudo apt install ffmpeg` 就够了（22.04 的 4.4.2 自带 libx264 和 aac）。目标文件名写成 `.mp4` 时，`render.mjs` 输出 H.264（yuv420p、faststart），合入音轨时转成 AAC 192k。实测 28 秒的 DOM 宣传片在 crf 18 下约 19 MB；带颗粒的片子码率更高，59 秒约 41 MB，用于网络分享时可以用 `--crf 20`–`23`。

只有最简 ffmpeg 时（只有 libvpx），交付 WebM：VP9 视频加 Opus 音频，Chrome、Edge、Firefox、VLC 都能播。需要 MP4 时，在有完整 ffmpeg 的机器上转一下：

```text
ffmpeg -i film-av.webm -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart film.mp4
```

## 场景页的约定

```html
<div id="stage"><canvas id="cv" width="1920" height="1080"></canvas><div id="caps"></div></div>
<script type="module" src="scene.js"></script>
```

```js
import { register, loadFonts } from '<kit>/kit.js';
function seek(t) { /* 根据 t 画出这一帧 */ }
await loadFonts([['Noto Sans SC', 'fonts/NotoSansSC-Bold.otf', { weight: '700' }]]);
register({ duration: 28, fps: 30, width: 1920, height: 1080, seek, meta: { events } });
seek(0);
```

- `seek(t)` 必须是纯函数：同一个 t 永远得到同一帧，可以任意顺序调用。**严禁在 DOM/SVG 场景中使用 CSS `transition`、`animation` 或 `@keyframes`**（无头渲染器禁用浏览器动画，一切动效均由 `seek(t)` 直接计算赋值）。
- 有异步素材时让 `seek(t)` 返回 Promise，完成取帧和绘制后再 resolve，截图会等待。长录屏、实拍和其他已经渲染的片段直接放进剪辑单更省资源。
- 画布、DOM、SVG、WebGL 可以混用。WebGL 在软件 GL（SwiftShader）上很慢，按 1/3 分辨率渲染再放大到 2D 画布上，天空就是这样做的。
- 页面用 `file://` 打开，取媒体文件时 `fetch` 会失败。字体用 `FontFace` 加载；音频交给 Node 读成 base64 再传给页面（`--vo` 已经处理好）。

## kit.js

| 名称 | 用途 |
|---|---|
| `clamp, lerp, inv` | 基础插值；`inv(a,b,x)` 把 x 映射到 0–1 |
| `ease.{linear,out,outSoft,in,inOut,inOutSoft,back}`、`bezier()` | 缓动曲线 |
| `seg(t, t0, dur, ease)` | 从 t0 开始、持续 dur 的进度（0–1） |
| `kf(t, keys, log)` | 关键帧轨道：`[[t, v, ease?], …]`，`log=true` 时在对数空间插值 |
| `spring(s, {stiffness, damping})` | 弹簧阶跃响应，s 是开始后经过的秒数 |
| `rng(seed)` | 带种子的随机数（mulberry32） |
| `hex, mixHex, rgba` | 颜色工具 |
| `loadFonts(list)`、`FONT_STACK` | 预加载字体，失败时只警告；CSS 后备字体栈 |
| `register({...})` | 注册 `window.__video` 和 `window.__seek` |
| `songAt(map, t)` | 歌曲 t 秒处的拍、小节及相位，所在段落和段内进度，响度、低频、高频，低频重音 `kick`、高频 `snap`（取自 `accents`，约每小节一次），正在唱的那句 `line`。`map` 来自 `songmap.js` |
| `envAt(curve, fps, t)`、`pulse(hits, t, decay, minStrength)` | 读逐帧曲线；最近一次击打后衰减的脉冲 |

## stage.js

用法与分镜示例见[产品宣传与软件演示](explain-and-demo.md)。所有函数只返回纯状态或按调用方传入色值绘制，不预设任何设备外观或固定配色。

| 名称 | 用途 |
|---|---|
| `arcPoint([x0,y0], [x1,y1], k, {bend})` | 两点间的微弧二次贝塞尔插值，起止严格落点、零过冲 |
| `lerpRect(a, b, k)`、`morphMoveRect(from, to, kMorph, kMove, {midW, midH, bend})` | 矩形插值；“先原地形变、再沿弧线飞入目标位”两阶段平滑过渡 |
| `cursorAt(t, waypoints, {pressDur, rippleDur, bend, moveEase})` | 根据路标 `[{t, x, y, click?, travel?, settle?, dwell?}]` 计算指针位置、按压缩放与钉在点击处的波纹 `{x, y, press, clicking, ripple}` |
| `drawCursor(ctx, state, {kind, size, fill, stroke, accent})` | 在 Canvas 上画指针（`'arrow' \| 'dot' \| 'ring'`）与定点波纹；DOM 场景可直接读 `cursorAt` 状态 |
| `throughScreen(k, screenRect, viewport, {borderRadius, pose0, origin, safety})` | 对数缩放 + 提前展平三维倾角 + 圆角安全内接框对齐，`k=1` 时四边与圆角完全越出画幅不漏黑边 |
| `cssStageTransform(state, {perspective})`、`applyStageCamera(ctx, state, fn)` | 将 `throughScreen` 状态分别应用到 DOM `transform` 或 Canvas 2D |
| `rollNumber(v0, v1, k, {decimals, prefix, suffix, locale, padStart})` | 滚动读数格式化（配合等宽数字字体防抖动） |

## draw.js

[用代码画出完成的画面](drawing.md)讲什么时候用哪一个；颜色参数同时支持 `[r, g, b]` 数组与 `'#rrggbb'` 字符串。

| 名称 | 用途 |
|---|---|
| `layer(w, h)` | 离屏画布：光层、人物层、缓存的静态背景 |
| `noise(seed)` → `n(x, y)`、`n.fbm(x, y, oct)` | 0–1 的平滑噪声与分形和：雾、云、山脊、抖动 |
| `bloom(ctx, src, {base, amount, radii})` | 把光层叠加两层模糊副本，让光像光 |
| `glow(ctx, x, y, r, color, alpha)` | 柔和的径向光 |
| `lightBeam(ctx, x0, y0, x1, y1, w0, w1, color, alpha, {layers, blend})` | 侧边自然羽化的体积光束（窗光、路灯锥、舞台光柱；亮底传 `blend: 'source-over'`） |
| `bokeh(ctx, seed, count, cam, t, {w, h, color, depth, rMin, rMax, alpha, blend})` | 预缓存幂律散景光斑，支持相机视差与无缝循环漂移（无需逐帧 `ctx.filter`，软件渲染极快） |
| `ridge(seed, width, {base, amp, scale, steps})`、`fillRidge(ctx, ys, fill, {dx, bottom})` | 山脊、沙丘；`steps` 给出平顶，成为屋顶和城市 |
| `view(ctx, cam, depth, fn)` | 对一层套相机 `{x, y, z, rot}`；depth 越小越远，相机动时产生视差 |
| `handheld(t, {amp, rot, speed, seed})`、`withHandheld(cam, t, opts)` | 纯函数手持相机有机微呼吸，让停留长镜头保持生命力（背景层注意留出血边距） |
| `strokeTo(ctx, pts, k)` | 按长度画出折线的前 k（0–1），返回笔尖位置 |
| `finish(ctx, frame, {vignette, grain})` | 收尾的暗角与逐帧颗粒 |
| `mix(a, b, k)`、`css(c, a)` | `[r,g,b]` 颜色混合与转成 CSS |

## graphic.js

零件表、可试时长和用法见[版面式动态设计](graphic.md)，完整用法见[地铁图示例](../examples/transit-map/scene.js)。约定：

- 画出来的零件（`grid`、`rule`、`ring`、`ruler`……）收 `k`，0–1 的线性进度，零件自己缓动；有自己节奏的零件（`label`、`headline`、`card`）收 `s`，开始后经过的秒数，负数时不画，可选 `exit` 是开始退场后的秒数。
- 转场 `wipe`、`iris`、`halftone` 收线性的 `k` 和一个画下一镜的函数 `(ctx) => …`：先画上一镜，再调用转场。
- `MONO`、`SANS` 是等宽和中文黑体的字体栈。颜色写成 `#rrggbb`。收尾的 `finish` 在 draw.js 里。

## stage3d.js（第二档重装 3D PBR 与 HDR 泛光引擎）

用法、五种开放美学世界与反屏保铁律详见[第二档：重装绚丽视效指南](spectacle-3d.md)。在 `--draft` 下自动半分辨率快渲，`VC_SOFTWARE_GL=1` 下自动关闭多重采样避开软件光栅化退化。

| 名称 | 用途 |
|---|---|
| `THREE, GLTFLoader` | 直接重导出离线 `kit/vendor/three/` 模块，支持 `file://` 无映射直接加载 `.glb` |
| `createStage3D(w, h, {fov, bg, scale, exposure, bloom, bloomThreshold, bloomRadius, dispersion, vignette, grain})` | 创建带线性浮点帧缓冲、5 级 Karis 防闪烁泛光、`ACESFilmic` 色调映射与边缘微色散的三维舞台；`seek(t)` 内调 `stage.render(t)` 后把 `stage.canvas` 画入主画布或直接挂载 |
| `studioEnv(stage, panels, {domeTop, domeBottom, domeIntensity})` | 在注册前**一次性**用 `PMREMGenerator.fromScene` 烘焙 HDR 摄影棚柔光箱与环灯反射环境（严禁在 `seek(t)` 里每帧调用） |
| `addStudioRig(stage, {keyColor, keyIntensity, rimColor, rimIntensity, ...})` | 添加实时方向/轮廓光组，在 `seek(t)` 里调 `rig.sweep(angleRad, lift)` 让高光沿倒角流动 |
| `pbrMaterial(presetOrOpts, overrides)` | 构建物理材质（预设起点 `'metal'` / `'titanium'` / `'glass'` / `'crystal'` / `'iridescent'` / `'ceramic'` / `'matte'` / `'emissive'`，可覆盖全部颜色与物理参数） |
| `roundedSlab(w, h, d, {radius, bevel, segments})` | 生成多段平滑圆角与切面法线的三维实体（替代生硬直角 `BoxGeometry`） |
| `instancedField(geo, mat, count, (i, obj, col, t, extra) => ...)` | 驱动成百上千枚三维实例随 `t` 与音乐 `kick`/`energy` 矩阵及颜色更新 |
| `orbitCamera(camera, {target, radius, azimuth, elevation, roll, fov})` | 纯函数球面推拉、荷兰角倾斜与变焦相机控制 |

## shader.js

| 名称 | 用途 |
|---|---|
| `shader(w, h, frag, {scale, uniforms, sdf})` → `{canvas, draw(t, extra)}` | 全屏片元着色器。默认注入 `t`、`res`、输出 `o` 及 `hash`、`noise`、`fbm`；传 **`sdf: true`** 时额外注入 3D 光线步进与光学函数（`rot2`、`smin`、`sdSphere`、`sdRoundBox`、`sdTorus`、`sdCapsule`、`opRep`、`thinFilm`、`aces`、`toSrgb`）。`extra` 的每个键成为一个 `float` 或 `vecN` uniform（勿与预定义名冲突），缺席帧自动置 0。示例见[着色器层](drawing.md#着色器层)与[重装绚丽视效指南](spectacle-3d.md) |

## sound.js

| 名称 | 用途 |
|---|---|
| `NOTE('F#5')` | 音名 → 频率 |
| `epiano, piano, subBass, bass, glass, pluck, warmPad, pad, tone, chime, glide` | 乐音（含 FM 电钢、笔记本外放清晰的单声道泛音超低音、通透玻璃钟琴） |
| `kick, clap, snare, hat, crash, impact` | 鼓与冲击 |
| `uiClick, swipe, pop, tick, whoosh, riser, rewind, thud, wind` | 触感界面拟音（确定性微点击、卡片空气滑擦）与环境音效 |
| `voice(m, t, id)`、`duck(bus, regions, {depth})`、`sidechain(bus, beatTimes, {depth, attack, release})` | 配音、台词闪避与独立于 `duck` 的节拍侧链呼吸（作用于 `bus.sc`） |
| `install(score, {reverb, irSec, irPow, irDamp, preDelay, warmth})` | 在乐谱页注册渲染入口；内置早期反射与高频阻尼混响，`warmth` 开启柔和磁带饱和（默认 `0` 透明直通）；`m.music / m.sfx / m.voice` 是三条总线 |
| `lufs, momentary, peakDb, normalize, encodeWebmOpus, toWav` | 测量与输出（工具内部使用） |

乐谱页只需要一行：`<script type="module" src="score.js"></script>`。

已有歌曲、对白或最终混音可直接传给 `render.mjs … video picture.mp4 --audio song.wav --mux final.mp4`。播放带声音的 `final.mp4`。制作局部试片时加 `--from 8 --to 12`，画面和这条全长母带都从第 8 秒取。歌曲选段如果另有源入点，先裁成从项目零点开始的音频，或用[剪辑单的音轨入点](editing.md)。检查最终母带可运行 `audiocheck.mjs final.mp4 page.html check.png`，无需配乐页。片段从场景第 8 秒开始时给检查命令加 `--scene-offset 8`，事件线会对齐到片段本地时间。

## 命令

| 工具 | 用法 | 说明 |
|---|---|---|
| `cut.mjs` | `edit.json final.mp4` | 静帧、已有镜头和可选成品音轨，按剪辑单出 MP4 |
| `captions.mjs` | `source.srt cues.mjs [--from a --to b] [--no-overlap] [--allow-draft]` | 把已核对的定时字幕转为场景模块；自动拦截未校对的 `*.draft.srt` 与 `(repeated, check by ear)` 占位词，MV 单槽字幕加 `--no-overlap` 拦截叠句，见[字幕示例](timed-text.md) |
| `render.mjs` | `page stills <dir> t…` / `sheet <jpg> [--every s] [--times a,b] [--cols n] [--w px] [--still s]` / `strip <jpg> --at t… [--offsets f…]` / `video <out.webm\|.mp4> [--draft] [--scale 0.5] [--fps n] [--crf n] [--from a --to b] [--audio track] [--srt subs.srt] [--mux out]` | `--draft` 以 `960×540@15fps` 快渲预览（保持 `1920×1080` 场景坐标不变，严禁用于最终交付）；`--srt` 在合入 MP4 时封装 `mov_text` 可开关软字幕轨 |
| `audio.mjs` | `page score\|- out.webm [--vo dir] [--srt out.srt] [--stems] [--target -16] [--wav out.wav]` | `score` 传 `'-'` 时无需乐谱页，直接按场景 `meta.cues` 干声与 `meta.sfx`（支持 `uiClick`/`click`/`swipe`/`glass`/`epiano`/`tick`/`pop`/`pluck`/`chime`/`thud`/`whoosh`/`glide`）合成 `-16 LUFS` 音轨；`--srt` 导出对齐字幕文件 |
| `mixcheck.mjs` | `page score out.png [--vo dir] [--from a --to b]` | 各轨瞬时响度曲线 + 事件线 |
| `audiocheck.mjs` | `media page out.png [--from a --to b] [--scene-offset s]` | 从成片解码，画频谱、包络和事件线 |
| `vo.mjs` | `dir out.js` | 量配音片段长度，写成可 import 的模块 |
| `songmap.py` | `song.m4a out/song [--lyrics] [--language en] [--bpm n] [--device auto\|cuda\|cpu]` | 歌曲地图：拍点、小节、段落、重击、能量曲线、带时间的歌词；显卡繁忙时自动切 CPU `int8` 转写 |
| `shotlist.py` | `film.mp4 [--mode general\|lesson\|mv\|promo] [--song songmap.json [--offset T0]] [--json out.json]` | 成片镜头表：`--mode lesson` 采用局部 `8×4` 网格动态感知与 4.5 秒阅读静止阈值；`--song` 识别唱词乐句起音切镜（`vocal_onset`）并预警重复乐段的画面雷同 |
| `narrate.py` | `cues.json voice-dir [--voice teacher] [--style auto\|lesson\|free] [--takes 2] [--engine voxcpm\|edge] [--device auto\|cuda\|cpu] [--force-gpu]` | 逐句旁白 WAV + `vo.js` + 逐词时间戳 `words.json`/`words.js`；内置讲稿口语流畅度门禁（拦截三四字蹦词腔、分号排比、顿号报数与 AI 报幕套话，退出码 `2`）与显卡负载护栏（占用 ≥75% 或空闲显存 <4GB 时退出码 `3`，可改传 `--device cpu` 或 `--engine edge`），见[人声](voice.md) |
| `boardcheck.mjs` | `page [--every 3] [--times a,b] [--margin 48] [--min-px 18] [--max-formulas 3] [--min-active 0.008]` | 版式无偏置的几何与视觉密度体检：检测同屏展示公式堆积（`formula_crowding`）、文字公式重叠、无底衬实线穿字（`line_crosses_label`，自动豁免带底色遮罩的标尺标签）、边距越界、过小字及过空帧，并对多框碎片化（`card_soup`）与稀疏草图（`low_visual_substance`）给出预警 |
| `gpu.py` | `[--json]` | 多次采样 `nvidia-smi` 探测显卡状态、利用率、空闲显存与 VoxCPM 安全阈值 |
| `listen_pair.py` | `old.mp4 a0 a1 new.mp4 b0 b1 pair.wav` | 从两个版本分别取完整句子，匹配响度，输出先旧后新的 PCM 听样 |
| `mux_original.py` | `picture.mp4 song.m4a final.mp4` | 从完整母带生成 MV，检查时长；兼容的音频格式直接复制，需 FFmpeg 与 FFprobe |
| `textcheck.mjs` | `page [--margin 80] [--sel '#caps .cap, #lyric, #captions']` | 自动抽检常见字幕与歌词选择器边距与最小字号（`min(W,H)/30`） |
| `montage.mjs` | `out.jpg width img…` | 几张图横排缩小 |
| `doctor.mjs` | — | 环境、显卡占用率与 kit Python/JS 脚本编译检查 |

速度参考（软件渲染）：DOM 场景约每秒 10 帧；带 WebGL 天空的画布场景约每秒 6 帧。

## 配合其他引擎

- **Remotion**：时间来自 `useCurrentFrame()`，原则相同。用 `npx remotion still` 渲染关键帧，用 `npx remotion render` 出成片。事件表可以写成一个 TS 常量，供 `<Audio>` 和 `<Sequence>` 共用。kit 的 `sound.js` 能在单独的页面里合成音轨，再作为 `<Audio>` 素材放进去。
- **HyperFrames、Motion Canvas、Manim**：用各自的命令出成片后，从成片截取联系表和切点帧：`ffmpeg -ss t -i film.mp4 -frames:v 1 …`，再用 `montage.mjs` 拼起来。审查顺序和问题清单照用。
- 这些引擎的 API 细节以官方文档和它们自带的技能为准（Remotion 有 `remotion-dev/skills`，HyperFrames 自带技能）；本技能只负责内容、画面、节奏、声音和审查。
