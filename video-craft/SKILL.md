---
name: video-craft
description: 用代码做出能直接发布的视频：教学讲解、科普与数据故事、软件演示与产品宣传、歌曲 MV、电影感短片与视觉奇观、片头、竖屏短视频及混合形式。题材和创意可以由 AI 自己定。技能负责从构思到成片：找核心画面，定美术和光，按旁白或歌曲的实际时间排镜头，用可逐帧定位的 HTML/Canvas/WebGL 页面实现，配上自然的人声、音乐和音效，渲染后看帧、查镜头表、听声音，修到达标再交付。自带工具：逐帧渲染，歌曲分析（拍点、段落、歌词时间），成片镜头检查，本地神经旁白，声音合成与混音检查，以及多个可改的完整示例。用户说“做个视频/动画/MV/宣传片/讲解视频/短视频”，或“AI 做的视频像 PPT、不好看”时使用。不用于给 Sora、可灵等视频生成模型写提示词，也不用于实拍素材的精剪调色或纯音频制作。
metadata:
  version: "0.7.0"
---

# Video craft

用户把题目交给你时，内容、风格和形式由你决定；用户已有脚本、歌曲、产品或开工确认单（`docs/briefs/`）时，沿用其中的设定；只要分镜、一段效果或一处修改时，只交付那一部分。

## 好的成片是什么样

交付前，成片要做到下面六条。做不到的，交付时写明原因。

- **画面自己讲。** 关掉声音，观众仍能看出发生了什么：
  - 科普的数字和现象由代码算出、模拟出来；
  - 软件演示用真实界面和真实结果；
  - MV 唱到什么，画面就给出它的形象，高潮和结尾说的是歌手的态度：遗憾的歌不拍成团圆。
  
  不要在幻灯片上贴一句结论。
- **每一帧都像一幅完成的画。** 有主光，有远近层次，有质感（光晕、雾、颗粒、暗角），颜色从题材里来。纯色底加居中图标加标题，就是幻灯片。
- **镜头在发展。** 每个镜头里都有变化：相机、主体或光。镜头长度由内容、乐句或台词决定，不按固定秒数切。切到近景要有新细节；转场本身也在讲故事，比如穿过窗户，或者形状相接。
- **声画一张时间表。**
  - 有旁白的片子，按配音实测长度排镜头；
  - MV 按歌曲实际的拍点、段落和歌词排镜头；
  - 画面里的事件都有对应的声音；
  - 音乐的起伏跟着叙事走。
- **人声自然。** 全片一个声音，像人在对人说话，没有爆音、断字和底噪。
- **看过、听过。** 每一轮都看渲染出来的帧和镜头表，听成片，不靠读代码判断效果。

## 按类型找起点

| 要做的 | 先读 | 可改的示例 |
|---|---|---|
| 教学、科普、数据故事：讲清一个机制，让人能照做或做出判断 | [讲解与演示](references/explain-and-demo.md)、[核心画面](references/pictures.md) | [九枚硬币](examples/worked-lesson/brief.md)（带旁白的例题与练习）、[sky](examples/sky/brief.md)（跨尺度的连续镜头） |
| 软件演示、产品宣传：让人看清操作，相信产品能做到 | [讲解与演示](references/explain-and-demo.md)，先拿到真实输入、操作和结果 | [开场提前十五分](examples/product-spot/brief.md)（真实可试的产品）、[promo](examples/promo/brief.md)（推进穿过手机屏幕） |
| 歌曲 MV：画面随一首歌发展 | [MV](references/music-video.md)，先跑 `songmap.py` | [最后一盏灯](examples/last-light/brief.md)（只靠录音的歌曲地图，先看这个）、[纸鸟](examples/sung-mv/brief.md)（原创演唱）、[回潮](examples/music-film/brief.md)（器乐） |
| 电影感短片、视觉奇观：用空间、光、动作和声音讲一个场面 | [电影镜头与场面调度](references/cinematography.md)、[用代码画出完成的画面](references/drawing.md) | [雾夜灯塔](examples/short-film/brief.md)、[layers](examples/layers/brief.md)（光与层次）、[虹彩鳞翅](examples/iridescence/brief.md)（WebGL 材质） |
| 片头、竖屏短视频、混合形式 | 按每一段的主要任务分别借用上面各行 | [starter](examples/starter/)（旁白驱动的起步模板） |

有声参考片：[examples/screening.html](examples/screening.html)。另有[三位创作者的拆法](references/watch-notes.md)。

## 画面从哪里来

1. **代码画（默认）。** Canvas、WebGL、SVG、DOM。先读[用代码画出完成的画面](references/drawing.md)。代码擅长：
   - 光、大量粒子、线、剪影和纵深；
   - 天空和水、几何、模拟、界面和图表。

   代码不擅长写实的人脸、人体、动物和真实地点。遇到这些，改用星座、剪影、背影、手的轮廓或物件来表现，不要硬画一个僵硬的小人。
2. **真实软件或产品**：操作并录下真实界面，见[讲解与演示](references/explain-and-demo.md)。
3. **生成图（可选加强）**：本机有 imagecraft 技能（本地 FLUX）时，可以生成代码画不好的底版，比如一个真实的地方或一位人物。生成图只当底版，运动、光和节奏仍由代码完成，不做成逐张放大的幻灯片。做法见 drawing.md 末节。
4. **用户给的素材**：录屏、照片、实拍、音乐，用[剪辑单](references/editing.md)剪入。

## 工作顺序

每一步都产出一件能看或能听的东西。

0. **查环境**：`node <kit>/doctor.mjs`。它报告浏览器、WebGL、编码器、FFmpeg 和语音是否可用。缺什么，见[工具包](references/kit.md)。
1. **任务单 `brief.md`。** 写下：
   - 观众、用途、平台、画幅、时长；
   - 看完要记住的一句话，或要感受到的变化；
   - 片中出现的事实和数字及其来源（数字由代码从同一份数据算出）；
   - 用什么人声、什么音乐；
   - 画面来源。

   缺的信息用默认值补，交付时说明。默认值：横屏 1920×1080，30 fps，中文；科普 45–90 秒，宣传 20–40 秒，MV 按歌曲长度。
   - **MV 先跑** `python <kit>/songmap.py song.m4a out/song --lyrics`，读 `songmap.md` 和歌词，再写概念。
2. **概念与核心画面。** 写 3–5 个“不看字也能懂”的画面，一样贯穿全片、每次出现都有变化的东西，以及每一段观众新看到什么。MV 先写一句唱的人怎么看这件事，再逐段写出歌词对应的画面，[MV](references/music-video.md)第 2 步给了四个问题和段落表的格式。
3. **美术与样帧。** 定 4–6 个颜色、主光和字体。按最终分辨率画出 2–4 张最关键的静帧（`render.mjs page.html stills out/ t1 t2 …`），用上面六条衡量，改到满意再往下走。见[画面质感](references/look.md)、[用代码画出完成的画面](references/drawing.md)。
4. **声音和时间表。**
   - 旁白：用 `narrate.py` 生成（见[人声](references/voice.md)），再用 `vo.mjs` 量出每句长度，镜头时间由这些长度算出。
   - 歌曲：所有时间取自 `songmap` 的拍点和小节线。
   - 配乐和音效：用 `sound.js` 写在 `score.js` 里，见[声音](references/sound.md)。
5. **分镜表。** 每行一个镜头，写明：
   - 起止时间；
   - 镜头里的变化；
   - 相机运动；
   - 怎样接到下一镜；
   - 声音。

   时间写成常量，从配音长度或拍点算出。镜头长度要有长有短。见[运动与剪辑](references/motion.md)、[电影镜头](references/cinematography.md)。
6. **实现。** 从最接近的示例复制改起，不从空白页开始。`seek(t)` 必须是纯函数：
   - 同一个 t 永远画出同一帧；
   - 不用 CSS 动画、`Date` 或无种子的 `Math.random`。

   先做最难的 8–12 秒，带声音渲染出来看。成立以后再铺满全片。
7. **看帧、查表、听声，修订。** 按[审查](references/review.md)的顺序：
   1. `shotlist.py` 镜头表；
   2. 联系表；
   3. 关键帧原尺寸；
   4. 切点帧条；
   5. 字幕；
   6. 从成片解码抽帧；
   7. 带声完整播放。

   改完再看受影响的镜头。一条片子通常要修 4–6 轮。
8. **交付。** 交付带最终混音的 MP4（没有 libx264 时交付 WebM），并告诉用户：
   - 文件路径；
   - 规格：分辨率、时长、编码、响度；
   - 做过哪些检查；
   - 没能做或没能验证的地方，例如“我听不到声音，只看了响度曲线”。

## 命令速查

`<kit>` 指本技能的 `kit/` 目录。网页工具需要 Node 18+、playwright-core、Chromium 和 FFmpeg；Python 工具需要 Python 3.9+、NumPy、FFmpeg。完整参数见[工具包](references/kit.md)。

| 目的 | 命令 |
|---|---|
| 环境探测 | `node <kit>/doctor.mjs` |
| 歌曲地图（拍点、段落、歌词） | `python <kit>/songmap.py song.m4a out/song --lyrics` |
| 生成旁白（本地 VoxCPM，同一声音） | `python <kit>/narrate.py cues.json vo/ --voice teacher --takes 3` |
| 配音计时 | `node <kit>/vo.mjs vo/ vo/vo.js` |
| 原尺寸静帧 | `node <kit>/render.mjs page.html stills out/ 2.5 10 31` |
| 联系表 | `node <kit>/render.mjs page.html sheet out/sheet.jpg --every 1`（或 `--times a,b,c`） |
| 切点帧条 | `node <kit>/render.mjs page.html strip out/strip.jpg --at 9.85,18.2` |
| 成片 | `node <kit>/render.mjs page.html video out/picture.mp4 --audio track.wav --mux out/final.mp4` |
| 成片镜头表与剪辑检查 | `python <kit>/shotlist.py out/final.mp4 [--song out/song/songmap.json]` |
| 合入整首原声 | `python <kit>/mux_original.py out/picture.mp4 song.m4a out/film.mp4` |
| 合成配乐、看响度 | `node <kit>/audio.mjs page.html score.html out/audio.webm --vo vo/`、`node <kit>/mixcheck.mjs page.html score.html out/mix.png` |
| 素材剪辑单 | `node <kit>/cut.mjs edit.json out/cut.mp4` · [格式](references/editing.md) |
| 字幕与已有 SRT | `node <kit>/textcheck.mjs page.html`、`node <kit>/captions.mjs song.srt cues.js` |
| 成片声音频谱 | `node <kit>/audiocheck.mjs out/final.mp4 page.html out/check.png` |

## 交付前核对

- [ ] 第一帧就是完整的构图，不是黑屏或纯色。
- [ ] 每个镜头都有主光和远近层次，没有“纯色底加图标加标题”的画面。
- [ ] `shotlist.py` 的每条标记都已改掉，或在任务单里写了理由：
  - 连续同长的镜头；
  - 只放大上一镜的切；
  - 黑场；
  - 超过 2 秒不动的段落；
  - 偏离拍点的切点。
- [ ] MV：
  - 高潮和结尾的画面和唱的人对这件事的态度一致（遗憾的歌没有被拍成团圆）；
  - 关键歌词句都有对应的画面；
  - 相同的段落（副歌）每次都有新变化；
  - 切点取自实际拍点。
- [ ] 每个数字都能在任务单里找到出处；示意图注明“未按比例”。
- [ ] 字幕：
  - 上一句完全退出后下一句再进；
  - 最小字号不小于画面高的 1/30；
  - 都在安全边距内（`textcheck`）。
- [ ] 换场没有残留：上一镜的图和字退完，下一镜再进。
- [ ] 结尾停在有意义的状态上；结尾卡读得完。
- [ ] 声音：
  - 自己混的音轨响度约 −16 LUFS，采样峰值不高于 −1.5 dBFS（`audio.mjs` 的默认值）；整首原声合片保留母带原样，不再归一；
  - 关键音效在事件处听得见；
  - 音乐不压人声；
  - 旁白全片一个声音，没有断字和爆音。
- [ ] 从编码后的成片解码抽帧看过：文字边缘、渐变色带、暗部。

## 时间参考

实测：

- 59 秒的 WebGL 科普，软件 GL 渲染约 5 分钟；
- 28 秒的 DOM 宣传片约 1.5 分钟；
- VoxCPM1.5 在 RTX 4070 Ti SUPER 上生成 6 秒的句子约 4.5 秒；70 秒的教学旁白每句生成三遍再挑，连同加载模型和转写核对共约 6.5 分钟。
