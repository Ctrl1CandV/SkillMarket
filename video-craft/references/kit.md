# 工具包

`kit/` 里有两类文件。

- **浏览器里用的模块**：`kit.js` 提供缓动、弹簧、随机数、颜色、字体和注册函数；`sound.js` 负责合成音乐、音效和配音，测响度，编 Opus/WebM。
- **Node 命令行工具**：渲染、检查、出音轨。它们通过 Playwright 驱动无头 Chromium 打开场景页，逐帧调用 `__seek(t)` 截图，再交给 ffmpeg 编码。

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

- `seek(t)` 必须是纯函数：同一个 t 永远得到同一帧，可以任意顺序调用。
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

## sound.js

| 名称 | 用途 |
|---|---|
| `NOTE('F#5')` | 音名 → 频率 |
| `piano, pluck, bass, warmPad, pad, tone, chime, glide` | 乐音 |
| `kick, clap, snare, hat, crash, impact` | 鼓与冲击 |
| `pop, tick, whoosh, riser, rewind, thud, wind` | 音效与环境 |
| `voice(m, t, id)`、`duck(bus, regions, {depth})` | 配音与压低音乐 |
| `install(score, {reverb, irSec, irPow})` | 在乐谱页注册渲染入口；`m.music / m.sfx / m.voice` 是三条总线 |
| `lufs, momentary, peakDb, normalize, encodeWebmOpus, toWav` | 测量与输出（工具内部使用） |

乐谱页只需要一行：`<script type="module" src="score.js"></script>`。

## 命令

| 工具 | 用法 | 说明 |
|---|---|---|
| `render.mjs` | `page stills <dir> t…` / `sheet <jpg> [--every s] [--times a,b] [--cols n] [--w px]` / `strip <jpg> --at t… [--offsets f…]` / `video <out.webm\|.mp4> [--crf n] [--audio a.webm] [--mux out]` | 视频用 JPEG 帧通过管道交给 ffmpeg |
| `audio.mjs` | `page score out.webm [--vo dir] [--stems] [--target -16] [--wav out.wav]` | 合成、归一、限幅、编码 |
| `mixcheck.mjs` | `page score out.png [--vo dir] [--from a --to b]` | 各轨瞬时响度曲线 + 事件线 |
| `audiocheck.mjs` | `media page out.png [--from a --to b]` | 从成片解码，画频谱、包络和事件线 |
| `vo.mjs` | `dir out.js` | 量配音片段长度，写成可 import 的模块 |
| `textcheck.mjs` | `page [--margin 80] [--sel '#caps .cap']` | 字幕边距与最小字号 |
| `montage.mjs` | `out.jpg width img…` | 几张图横排缩小 |
| `doctor.mjs` | — | 环境探测 |

速度参考（软件渲染）：DOM 场景约每秒 10 帧；带 WebGL 天空的画布场景约每秒 6 帧。

## 配合其他引擎

- **Remotion**：时间来自 `useCurrentFrame()`，原则相同。用 `npx remotion still` 渲染关键帧，用 `npx remotion render` 出成片。事件表可以写成一个 TS 常量，供 `<Audio>` 和 `<Sequence>` 共用。kit 的 `sound.js` 能在单独的页面里合成音轨，再作为 `<Audio>` 素材放进去。
- **HyperFrames、Motion Canvas、Manim**：用各自的命令出成片后，从成片截取联系表和切点帧：`ffmpeg -ss t -i film.mp4 -frames:v 1 …`，再用 `montage.mjs` 拼起来。审查顺序和问题清单照用。
- 这些引擎的 API 细节以官方文档和它们自带的技能为准（Remotion 有 `remotion-dev/skills`，HyperFrames 自带技能）；本技能只负责内容、画面、节奏、声音和审查。
