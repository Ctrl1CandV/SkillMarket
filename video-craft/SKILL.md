---
name: video-craft
description: 用代码做出能直接发布的视频：硬核课程与考研讲题（专业公式变形、工程物理与力学分析、计算机算法与系统机制）、科普与数据故事、软件演示与产品宣传、歌曲 MV、电影感短片与片头。入口先做环境与显卡承载力预判，再按「课程与讲题轨」和「宣传与视听轨」分流。自带工具：离线 MathJax SVG 子项公式变形与具象理工图解引擎、纸面与建筑网格版面动效、场景分层绘制、本地神经旁白与逐词时间戳同步、事件微音效、歌曲拍点歌词地图、快渲预览、版面碰撞与公式堆积检查，以及十三个可改的完整示例。用户说“做个视频/讲题视频/动画/MV/宣传片/讲解视频/短视频”，或“AI 做的视频像 PPT、不好看”时使用。不用于给 Sora、可灵等视频生成模型写提示词，也不用于实拍素材的精剪调色或纯音频制作。
metadata:
  version: "1.1.2"
---

# Video craft

用户把题目交给你时，内容、风格和形式由你决定；用户已有脚本、题目、歌曲、产品或开工确认单（`docs/briefs/`）时，沿用其中的设定；只要分镜、一段效果或一处修改时，只交付那一部分。

## 第 0 步：环境探测与承载力双重闸门（开工必做）

动手前先跑 `node <kit>/doctor.mjs`（`<kit>` 指本技能的 `kit/` 目录，完整参数见[工具包](references/kit.md)），同时完成下面两项判断。**做不到或拿不准的地方，在线对话先如实告诉用户并给出替代方案，绝不硬凑充数。**

1. **硬件与显卡避让闸门**（看 `doctor.mjs` 输出的 `gpu`、`ffmpeg`、`browser` 字段）：
   - `gpu.state === "present_but_inaccessible"`：驱动在，但当前沙箱挡住了显卡设备。请用户在普通终端跑一次 `nvidia-smi` 确认，**不要谎报“这台机器没有显卡”**。
   - `gpu.busy === true`（核心利用率 ≥75%）或 `!gpu.voxcpm15_safe`（空闲显存 `< 4096 MiB`）：本机显卡正被其他重任务占用。**在线对话必须先停下汇报当前显存/占用率**，请用户选择：① 用 `--device cpu --takes 1` 在 CPU 上跑本地 `VoxCPM1.5` 克隆声音卡（零显存占用、音色自然，6–8 句约需 2 分钟）；② 改走 `--engine edge` 零显存快速配音；③ 等显卡空闲，或用户明确允许共用时加 `--force-gpu`。无人值守批处理时，若本机已缓存 `VoxCPM1.5` 优先用 `--device cpu --takes 1` 保住自然老师音色（或用 `--engine edge`），并在交付首行说明。
   - 渲染帧速与分档：改稿与对同步阶段统一用 `render.mjs ... --draft`（`960×540 @ 15fps` 快渲预览）；**最终交付无论有无显卡，一律渲染 `1920×1080 @ 30fps` 高清母带**（无 `libx264` 时交付 WebM 并说明），绝不把 `--draft` 预览当作成片交付。
2. **表达边界闸门**（评估任务里有没有代码画不好的东西）：
   - 代码擅长：出版级数学/物理公式变形、几何与力学矢量、函数曲线、算法与系统状态流转、光影山谷/星空粒子、版面式大字与网格动效。
   - 代码不擅长：写实人脸与手部表情、复杂人体动作、动物、三维连续介质复杂形变、没有真实界面的软件操作。
   - 遇到不擅长的内容：**绝不拿 Canvas 硬画火柴人或简笔画积木**。讲题与工程分析改用标准二维剖面、刚体物块与矢量图；叙事与宣传改用剪影、物件隐喻、请用户补充真实录屏/素材，或在本机 `imagecraft` 可用时按需生成静态底图。拿不准用户能否接受抽象替代时，先问一句再画。

---

## 按轨道分流（只读所属轨道的参考文档，禁止跨轨混读）

本技能内部隔离为两条创作范式截然不同的轨道，**进入其中一条后不要加载另一条的参考文档**，以免规则串味和稀释注意力：

| 轨道 | 适用任务 | 必读指南（只读这一组） | 起步示例 |
|---|---|---|---|
| **轨道 A · 课程、讲题与硬核科普** | 考研/大学课程例题精讲、专业数学公式推演、工程物理与力学分析、计算机算法/系统机制、定量科普 | **[课程与讲题制作指南](references/course-and-stem.md)**、[工具包](references/kit.md)（需要纸面网格与遮罩转场时可参看[版面式动态设计](references/graphic.md)的零件表，但讲稿严禁用海报口号腔） | [斜拉极值与摩擦角](examples/stem-lesson/brief.md)（`lesson.js` 理工标准模板）、[地铁图](examples/transit-map/brief.md)（暖纸纹版面与 `wipe`/`iris` 遮罩转场）、[sky](examples/sky/brief.md)（连续跨尺度物理模拟） |
| **轨道 B1 · 软件演示与产品宣传** | 真实软件操作教程、产品痛点广告、发布会风格短片 | [讲解与演示](references/explain-and-demo.md)、[版面式动态设计](references/graphic.md)、[声音](references/sound.md)、[审查](references/review.md) | [开场提前十五分](examples/product-spot/brief.md)（真实可交互界面）、[promo](examples/promo/brief.md)（穿屏转场）、[地铁图](examples/transit-map/brief.md)（`graphic.js` 版面） |
| **轨道 B2 · 歌曲 MV** | 现成录音或原创演唱的音乐视频 | 先跑 `songmap.py`，再读 **[MV](references/music-video.md)**、[用代码画出完成的画面](references/drawing.md)、[审查](references/review.md) | [最后一盏灯](examples/last-light/brief.md)（拍点与小节切镜）、[纸鸟](examples/sung-mv/brief.md)、[回潮](examples/music-film/brief.md) |
| **轨道 B3 · 电影感短片与片头** | 氛围叙事、视觉奇观、播客/栏目片头 | [电影镜头与场面调度](references/cinematography.md)、[用代码画出完成的画面](references/drawing.md)、[版面式动态设计](references/graphic.md)、[声音](references/sound.md)、[审查](references/review.md) | [雾夜灯塔](examples/short-film/brief.md)、[layers](examples/layers/brief.md)、[虹彩鳞翅](examples/iridescence/brief.md) |

另有：[人声生成与声音卡](references/voice.md)、[外部素材剪辑单](references/editing.md)、[已有 SRT 字幕导入](references/timed-text.md)、[画面质感参数](references/look.md)、[运动与缓动曲线](references/motion.md)、[核心画面构思](references/pictures.md)、[离线有声参考片](examples/screening.html)。

---

## 两条轨道各自的执行闭环

### 走「轨道 A · 课程与讲题轨」时（详见 [course-and-stem.md](references/course-and-stem.md)）

1. **任务单与单一数据源（`brief.md` + `data.js`）**：写明目标受众容易踩的直觉误区、三段式结构（破题直觉反差 → 分幕因果推演 → 考场易错坑与通法），并把题中所有物理/数学/系统关系写进同一个 `data.js`（严核边界定义，如 TCP 超时是 `cwnd = 1` 而非归零）。用户未声明“直接做完”时，先把解题切口与分幕列在回复里请用户确认一次；无人值守或要求直接交付时写进 `brief.md` 继续执行。
2. **舒展自然的老师讲稿 + 固定音色干声 + 克制动作微音效**：台词必须写成**真老师站在讲台上娓娓道来的连贯整句**——每条 `cue` 控制在 **42–75 个汉字（2–3 句完整的话，全片 6–8 条）**，主谓宾齐全、因果过渡自然；**严禁写成三四字一逗的蹦词电报腔、冒号报幕腔（“两个坑：”）、分号对称排比腔或顿号点名报数腔（“一、二、四、八”）**，协议与公式符号在口播中一律说中文名（说“拥塞窗口”“慢启动阈值”而非生读 `cwnd`），数字写汉字读法（`narrate.py --style lesson` 会自动拦截破碎生硬的 AI 讲稿）。生成全片同音色干声并导出 `vo/words.js`；在 `meta.sfx` 为关键动作（步进 `tick`、入水/重传 `pluck`、丢包/超时 `thud`、极值锁定 `chime`、遮罩转场 `whoosh`）配克制微音效，**不铺吵人的持续电子垫音**，并用 `audio.mjs index.html - out/audio.webm --vo vo/ --srt output/captions.srt` 导出音轨与独立软字幕（**禁止画布再烧录底字幕**）。
3. **基于 `kit/lesson.js`（可配 `graphic.js`）实现有质感、不堆砌的画面**：
   - **主图常驻演化，推导区按幕清场（严禁堆满一屏公式）**：物理/几何/主图表常驻联动，但右半屏推导区必须用 `actAt(t, ACTS)` 按幕切换——**每幕同屏最多展示 1–2 个大号核心公式（38–52px）**，上一步中间式要么原地 `morphFormula` 变成下一式，要么随上一幕退出清场，绝不把推完的旧式子半透明堆在屏上！遇到复杂微观机制（如发送方↔接收方包回声 vs 超时沉默）时，**不要缩在角落画小框**，用 `iris`/`wipe` 遮罩或相机推近切入**全屏机制专场**演透再切回主图。
   - **拒绝裸线草图，优先亮色学术版面与具象物理层次**：禁止只画几根单薄细线加半透明色块。**题目讲解与板书推演默认首选亮色暖纸纹学术底板**（`THEMES.paper` / `THEMES.ivory` 配建筑细网格与角标参数牌 `svgCard(..., { corners: true })`），清爽耐看；深色 `THEMES.slate` 保留给光学发光轨迹、全屏机制专场的暗场撞色切换或用户指定暗底时使用。画物理介质用 `svgMediaTank`（渐变水体、动态水波纹、界面线、坐标标尺 `svgRuler`、阴影辅助直角三角形、直线 vs 折线双粒子同时出发竞速）；画离散轮次/窗口用 `svgStepColumns` 垒出实体积木块。
4. **快渲调优 → 版面与公式密度体检 → 1080p 母带交付**：
   - 先用 `--draft` 快渲检查动画衔接；
   - 跑 `node <kit>/boardcheck.mjs index.html` 清零**公式过多堆积（`formula_crowding`）**、文字重叠、实线穿字（`line_crosses_label`）与越界，并用 `stills` 打开 `1920×1080` 原尺寸关键帧肉眼核验画面丰富度与排版呼吸感；
   - 渲染 `1920×1080 @ 30fps` 母带（`--srt` 内封软字幕），跑 `shotlist.py output/final.mp4 --mode lesson` 与 `ffmpeg` 解码抽帧核验后交付。

### 走「轨道 B · 宣传、MV 与视听短片轨」时

1. **任务单与内容设计（`brief.md`）**：MV 先跑 `songmap.py song.m4a out/song --lyrics`。写清具体观众与处境、看完要记住的一句话、温度与克制边界，每条取舍写成“因为观众……，所以拍……，不拍……”。用了他人歌曲或素材时，照来源原文逐人抄下角色与许可。
2. **核心画面与美术样帧**：定下贯穿全片且每次出现都有变化的视觉主体，选场景分层绘制（`kit/draw.js` + `shader.js`）或版面式设计（`kit/graphic.js`，版面里仍须有占 40%–60% 且持续讲清此事的核心动态图形），先出 2–4 张 `1080p` 静帧满意后再铺开。
3. **声画时间表与纯函数 `seek(t)`**：旁白按 `narrate.py` 实测时长排镜；MV 严格取 `songmap` 的 `downbeats`/`beats` 切镜并配校对后的双语/原文歌词字幕（`captions.mjs`）；配乐与音效在 `score.js` 中按场景 `meta.events` 同步驱动。先做最难的 8–12 秒试片，成立后铺满全片。
4. **审片修订与交付**：按 [review.md](references/review.md) 跑 `shotlist.py`（检查网格等长切、放大式切、黑场、超过 2 秒死水段及偏拍）、联系表、切点帧条、`textcheck.mjs`、`mixcheck.mjs` 与成片解码抽帧，修到全部达标后交付 `1080p` 成片。

---

## 命令速查

| 目的 | 命令 |
|---|---|
| 环境与显卡负载探测 | `node <kit>/doctor.mjs` |
| 生成旁白 + 逐词时间戳 | `python <kit>/narrate.py cues.json vo/ --voice teacher --style lesson --takes 2`（显卡忙时 `--device cpu --takes 1` 或 `--engine edge`） |
| 讲题纯净音轨 + 软字幕 | `node <kit>/audio.mjs index.html - out/audio.webm --vo vo/ --srt output/captions.srt` |
| 配乐合成与响度检查 | `node <kit>/audio.mjs index.html score.html out/audio.webm --vo vo/`、`node <kit>/mixcheck.mjs index.html score.html out/mix.png` |
| 草稿快渲预览（540p@15fps） | `node <kit>/render.mjs index.html video out/pic.mp4 --draft --audio out/audio.webm --mux out/preview.mp4` |
| 1080p 正式母带（可封软字幕） | `node <kit>/render.mjs index.html video out/pic.mp4 --audio out/audio.webm [--srt output/captions.srt] --mux output/final.mp4` |
| 原尺寸静帧 / 联系表 / 切点条 | `node <kit>/render.mjs index.html stills out/ 5 18 42` · `sheet out/sheet.jpg --every 2` · `strip out/strip.jpg --at 9.8,18.2` |
| 版面碰撞与越界体检 | `node <kit>/boardcheck.mjs index.html [--every 3]` |
| 成片镜头表检查 | `python <kit>/shotlist.py output/final.mp4 [--mode lesson]` · MV 加 `--song out/song/songmap.json` |
| 歌曲地图 / 原声无损合片 | `python <kit>/songmap.py song.m4a out/song --lyrics` · `python <kit>/mux_original.py out/pic.mp4 song.m4a output/final.mp4` |
| 字幕检查 / 素材粗剪 | `node <kit>/textcheck.mjs index.html` · `node <kit>/cut.mjs edit.json out/cut.mp4` |

---

## 交付前硬核对清单

- [ ] **承载力诚实披露**：显卡受限降档、未亲耳试听（仅凭响度 `-16 LUFS` 与频谱核对）、或抽象化替代之处，已在回复中如实写明。
- [ ] **无制作读数与首帧完整**：第一帧就是完整构图（非黑屏）；画面内无帧号、`00.0 / 89.7 s` 播放计时或调试辅助线。
- [ ] **话画一致且无冗余复读**：说到的时间、天气、物理量或动作在画面中真实可见；讲题轨做到了口播、板书与软字幕分工，没有“配音+大标题+硬字幕”同句复读三遍。
- [ ] **数据同源与署名准确**：所有计算数字同出一份数据代码；引用他人录音/素材时严格按原文逐人署名角色与许可，原创内容不编造署名。
- [ ] **自动化检查与解码抽帧全过**：`boardcheck.mjs` 无文字/公式碰撞与边缘裁切；`shotlist.py`（讲题用 `--mode lesson`）标记项已修正或有明确设计依据；最终交付文件确为 `1920×1080 @ 30fps` 并经 `ffmpeg` 解码抽帧核验清晰度。
