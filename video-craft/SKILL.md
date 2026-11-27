---
name: video-craft
description: 用代码做出能直接发布的视频：硬核课程与考研讲题（专业公式变形、工程物理与力学分析、计算机算法与系统机制）、科普与数据故事、软件演示与产品宣传、歌曲 MV、电影感短片与片头。入口先做环境与显卡承载力预判，再按「课程与讲题轨」和「宣传与视听轨（支持第一档轻快叙事与第二档重装 3D/HDR 绚丽视效分档）」分流。自带工具：离线 MathJax SVG 公式变形引擎、内建 Three.js PBR 摄影棚与多级 HDR 泛光/光线步进视效引擎（兼可选 Blender 无头桥接）、产品界面调度原语、纸面网格版面动效、自然阻尼混响与触感微音效合成、本地神经旁白与逐词同步、歌曲拍点地图、快渲预览与版面/镜头检查。用户说“做个视频/讲题视频/动画/MV/宣传片/讲解视频/短视频”，或要求“视觉震撼、画面绚丽、大片感、Blender 级效果”时使用。不用于给 Sora、可灵等视频生成模型写提示词，也不用于实拍素材的精剪调色或纯音频制作。
metadata:
  version: "1.2.0"
---

# Video craft

用户把题目交给你时，内容、风格和形式由你决定；用户已有脚本、题目、歌曲、产品或开工确认单（`docs/briefs/`）时，沿用其中的设定；只要分镜、一段效果或一处修改时，只交付那一部分。

## 第 0 步：环境探测与承载力双重闸门（开工必做）

动手前先跑 `node <kit>/doctor.mjs`（`<kit>` 指本技能的 `kit/` 目录，完整参数见[工具包](references/kit.md)），同时完成下面两项判断。**做不到或拿不准的地方，在线对话先如实告诉用户并给出替代方案，绝不硬凑充数。**

1. **硬件与显卡避让闸门**（看 `doctor.mjs` 输出的 `gpu`、`ffmpeg`、`browser` 字段）：
   - `gpu.state === "present_but_inaccessible"`：驱动在，但当前沙箱挡住了显卡设备。请用户在普通终端跑一次 `nvidia-smi` 确认，**不要谎报“这台机器没有显卡”**。
   - `gpu.busy === true`（核心利用率 ≥75%）或 `!gpu.voxcpm15_safe`（空闲显存 `< 4096 MiB`）：本机显卡正被其他重任务占用。**在线对话必须先停下汇报当前显存/占用率**，请用户选择：① 用 `--device cpu --takes 1` 在 CPU 上跑本地 `VoxCPM1.5` 克隆声音卡（零显存占用、音色自然，6–8 句约需 2 分钟）；② 改走 `--engine edge` 零显存快速配音；③ 等显卡空闲，或用户明确允许共用时加 `--force-gpu`。无人值守批处理时，若本机已缓存 `VoxCPM1.5` 优先用 `--device cpu --takes 1` 保住自然老师音色（或用 `--engine edge`），并在交付首行说明。显卡繁忙期间，第一档无头渲染设 `VC_SOFTWARE_GL=1`（`shader.js` 配 `{ scale: 0.5 }`），`songmap.py --lyrics` 自动退回 CPU `int8`；**若任务需走轨道 B「第二档 · 重装绚丽视效档」（重度 3D PBR / 光线步进 / Blender），可先用 `VC_SOFTWARE_GL=1 --draft` 出预览，正式 1080p 母带及本机 `imagecraft`/Blender GPU 渲染须等显卡释放或获用户明确许可后再跑**。
   - 渲染帧速与分档：改稿与对同步阶段统一用 `render.mjs ... --draft`（`960×540 @ 15fps` 快渲预览）；**最终交付无论有无显卡，一律渲染 `1920×1080 @ 30fps` 高清母带**（无 `libx264` 时交付 WebM 并说明），绝不把 `--draft` 预览当作成片交付。
2. **表达边界闸门**（评估任务里有没有代码画不好的东西）：
   - 代码擅长：出版级数学/物理公式变形、几何与力学矢量、函数曲线、算法与系统状态流转、光影山谷/星空粒子、版面式大字与网格动效。
   - 代码不擅长：写实人脸与手部表情、复杂人体动作、动物、三维连续介质复杂形变、没有真实界面的软件操作。
   - 遇到不擅长的内容：**绝不拿 Canvas 硬画火柴人或简笔画积木**。讲题与工程分析改用标准二维剖面、刚体物块与矢量图；叙事与宣传改用剪影、物件隐喻、请用户补充真实录屏/素材，或在本机 `imagecraft` 可用时按需生成静态底图。拿不准用户能否接受抽象替代时，先问一句再画。

---

## 按轨道分流（隔离体裁话术，共享底层工艺）

不同体裁的叙事逻辑与评价标准差异极大：**进入一条轨道后不要混读另一轨道的体裁指南**（如禁止拿宣传片口号腔写讲题台词），但通用的底层画面、色彩与缓动工艺（[画面质感](references/look.md)、[运动曲线](references/motion.md)、[核心画面构思](references/pictures.md)及 `graphic.js` 版面/遮罩零件）各轨道均可按需借用：

| 轨道 | 适用任务 | 必读指南 | 多方向参考样例（借工程骨架与决策，禁照搬原题配色版式） |
|---|---|---|---|
| **轨道 A · 课程、讲题与硬核科普** | 考研/大学课程例题精讲、数学公式推演、工程物理与力学分析、计算机算法/系统机制、定量科普 | **[课程与讲题制作指南](references/course-and-stem.md)**、[工具包](references/kit.md) | [九枚硬币](examples/worked-lesson/brief.md)（石版黑板居中天平 + 提问留白）、[斜拉极值](examples/stem-lesson/brief.md)（深空矢量剥离 + MathJax 子项变形）、[地铁图](examples/transit-map/brief.md)（暖纸印刷网格 + 拓扑变形）、[sky](examples/sky/brief.md)（无旁白跨尺度连续物理场） |
| **轨道 B1 · 软件演示与产品宣传** | 第一档：真实软件操作教程、产品痛点广告；**第二档：旗舰硬件/概念震撼揭晓大片** | **[讲解与演示](references/explain-and-demo.md)**、[版面式动态设计](references/graphic.md)、[声音](references/sound.md)、[审查](references/review.md)；**第二档必读 [重装绚丽视效指南](references/spectacle-3d.md)** | [开场提前十五分](examples/product-spot/brief.md)（借真实界面证据闭环，勿仿其简笔小人与非标分辨率）、[promo](examples/promo/brief.md)（借数据同源与穿屏衔接，勿照搬倾斜手机与印章红）、[地铁图](examples/transit-map/brief.md)（`graphic.js` 印刷网格与拓扑变形）、[虹彩鳞翅](examples/iridescence/brief.md)（三维微距掠光与薄膜干涉） |
| **轨道 B2 · 歌曲 MV** | 第一档：克制生活叙事 MV；**第二档：流光溢彩、三维/光线步进声画共振奇观 MV** | 先跑 `songmap.py`，再读 **[MV](references/music-video.md)**、[用代码画出完成的画面](references/drawing.md)、[审查](references/review.md)；**第二档必读 [重装绚丽视效指南](references/spectacle-3d.md)** | [最后一盏灯](examples/last-light/brief.md)（借 `songmap` 拍点切镜，勿照搬夜湖星空）、[纸鸟](examples/sung-mv/brief.md)（暖色纸面剪影与逐字音高）、[回潮](examples/music-film/brief.md)（竖屏几何母题随乐句变奏） |
| **轨道 B3 · 电影感短片与片头** | 氛围叙事、**三维物理材质与着色器视觉奇观**、播客/发布会片头 | **[电影镜头与场面调度](references/cinematography.md)**、[重装绚丽视效指南](references/spectacle-3d.md)、[用代码画出完成的画面](references/drawing.md)、[版面式动态设计](references/graphic.md)、[声音](references/sound.md)、[审查](references/review.md) | [雾夜灯塔](examples/short-film/brief.md)（五镜因果动作链）、[layers](examples/layers/brief.md)（纯 2D 视差山谷）、[虹彩鳞翅](examples/iridescence/brief.md)（微距物理显色片头） |

另有：[人声生成与声音卡](references/voice.md)、[外部素材剪辑单](references/editing.md)、[已有 SRT 字幕导入](references/timed-text.md)、[画面质感参数](references/look.md)、[运动与缓动曲线](references/motion.md)、[核心画面构思](references/pictures.md)、[离线有声参考片](examples/screening.html)。

---

## 两条轨道各自的执行闭环

### 走「轨道 A · 课程与讲题轨」时（详见 [course-and-stem.md](references/course-and-stem.md)）

1. **任务单、单一数据源与原创导演构思（`brief.md` + `data.js` + `scene.js` 头部注释）**：
   - 有用户指定倾向或 `docs/briefs/` 确认单时优先沿用；未指定时，按题目性质选择最自然的叙事弧（直觉反差推演、观察→猜想→验证、具体算例→连续几何演化→通解等，不必硬套单一八股结构），把全部定量与状态关系收进唯一 `data.js`。
   - 写代码前在 `brief.md` 与 `scene.js` 顶部注释写下三条**“因为本题具体事实 → 所以专属视觉隐喻 / 空间编排 / 色调与语义色”**（换道无关题仍能原样成立的套话不算，禁止直接照搬示例色值与坐标）。在线交互且用户未要求直接交付时，先把切口与视觉方案给用户确认一次；无人值守时写进任务单继续完成。
2. **有呼吸节奏的自然讲稿 + 固定音色干声 + 声画分工**：
   - 主体推演写成 **35–75 字舒展连贯的讲台口语整句**，允许穿插 15–25 字利落设问或收束拉出快慢呼吸；严禁通篇三四字蹦词电报腔、冒号提纲报幕腔或顿号点名报数串，公式代码变量在口播中说中文含义、小数与比值写汉字读法（`narrate.py` 自动核查）。
   - 生成全片同音色干声与 `vo/words.js`，在 `meta.sfx` 为关键物理/逻辑节点配克制微音效（不铺持续嗡鸣垫音）。有全片口播并由 `audio.mjs ... --srt` 挂载软字幕轨时，**不在画面底部再烧录重复硬字幕**（无旁白纯画面科普或用户要求硬字幕除外）。
3. **守住三条构图不变量，彻底放开版式、画风与自绘创造力**：
   - **主体统治力（禁网页卡片汤）**：核心动态图形（几何演化、实验剖面、数据结构、场与曲线）必须占据主舞台主导空间，复杂微观机理敢于推近或切入全屏专场演透，严禁把屏幕切碎成 ≥5 个圆角框拼监控后台。
   - **同屏聚焦与有序清场（不限左右分栏）**：空间构图随题材自由生长（居中全幅、分栏对照、上下时序、宏微转场皆可）；同一时刻严控展示级公式数量，推完的中间式原地 `morphFormula` 变形或随 `actAt` 清场退净，绝不堆满一屏。
   - **视觉完成度与开放美学（反裸线草图、禁绑死模板）**：拒绝两根细线配淡透明框的草图感，主体须兼具材质/场域层次、动态演化载体与清晰标尺读数。没有光学辉光或暗场撞色需求时，长时间听题推演可优先考虑明快通透的亮色画面（如清透讲义白、暖纸、工程蓝图等），亦可按题材采用黑板或暗场聚光；`kit/lesson.js` 的 `THEMES` 与具象模具均为**可选起点**，鼓励传入自定义语义配色并手绘本题专属 SVG/Canvas 图形。
4. **快渲调优 → 版面与密度体检 → 1080p 母带交付**：
   - 改稿阶段用 `--draft` 快渲；跑 `node <kit>/boardcheck.mjs index.html` 清零公式堆积、文字碰撞、无底衬穿字与过空草图，打开 `1920×1080` 原尺寸静帧核验完成度；最后渲染 `1920×1080 @ 30fps` 母带并经 `shotlist.py --mode lesson` 与解码抽帧核验交付。

### 走「轨道 B · 宣传、MV 与视听短片轨」时（先定视效档位，再进四步闭环）

0. **按任务诉求明确选定「第一档」或「第二档」**：
   - **第一档 · 清晰叙事与实操档（`stage.js` + `graphic.js` + `draw.js`）**：适合软件实操教程、重在真实界面细节与逻辑证明的功能演示、克制温情的日常叙事 MV，或需在无独显/显卡繁忙时轻快出片的任务。
   - **第二档 · 重装绚丽视效档（必读 [spectacle-3d.md](references/spectacle-3d.md)：内建 `stage3d.js` Three.js PBR + HDR 多级泛光 + `shader.js` `{ sdf: true }` 光线步进，或本机可用时桥接 `blender_bridge.py`）**：当用户提出“视觉震撼、画面绚丽、流光溢彩、大片感、发布会级、Blender 级效果”，或制作旗舰硬件/概念大片、高燃电音/流行/后摇 MV 与奇观片头时直接启用——靠真实圆角倒角金属/折射水晶/薄膜虹彩材质、程序化摄影棚柔光箱掠光、5 级防闪烁 HDR 泛光 + `ACESFilmic` 色调映射、千枚三维实例声画共振与 2D 刀锋排版合成兑现大片质感（严禁拿裸直角方块拼廉价霓虹屏保）。
1. **偏好外置、任务单与原创导演三问（`brief.md` + `scene.js` 头部注释）**：
   - 有用户指定风格或 `docs/briefs/` 确认单时优先沿用；MV 动手前先跑 `songmap.py song.m4a out/song --lyrics`。写清具体观众与处境、看完要记住的一句话、温度与克制边界；引用他人歌曲或素材时，照来源原文逐人抄下角色与许可。
   - 写代码前在 `brief.md` 与 `scene.js` 顶部注释写下三条**“因为本产品/本曲具体处境与事实 → 所以专属视觉世界 / 核心调度动作 / 声音织体与色调”**（换一个无关产品或换一首歌仍能原样套用的空话不算；**严禁照搬示例的倾斜手机、印章红、夜湖银河或 120 BPM 四和弦循环**）。在线交互且用户未要求直接做完时，先把内容设计与视觉方向给用户看一眼；无人值守时写进任务单接着完成。
2. **时辰主光前置锁定 + 核心动态主体 + 纯函数 `seek(t)`**：
   - **先锁时辰与主光再动笔**：先按台词、歌词或产品使用场景里的具体时间与天气定下主光方向、环境色温与底色（说“下午三点”或“赶早班”就绝不能套夜景模板画月亮繁星；日光、暖纸、正视桌面、暗场聚光随题材自由生长）。
   - **守住表达边界与主体递进**：定下贯穿全片且每次回归都有状态/尺度变化的核心视觉主体（版面式设计仍须有占主舞台主导空间、盖住大字仍在讲清此事的核心动态图形；涉及人物时用干净剪影、建筑框景、光影或日常器物演出处境，绝不硬画僵硬火柴人或多关节简笔手）。DOM/SVG/Canvas 运动一律写成 `t` 的纯函数，**严禁用 CSS `transition` 或 `@keyframes`**。先出 2–4 张 `1080p` 原尺寸静帧核验满意后再铺开。
3. **声画时间表与触感编排**：
   - 旁白按 `narrate.py` 实测时长排镜；软件与产品交互可按需选用 `kit/stage.js`（零过冲弧线指针 `cursorAt` + 定点点击波纹、计入圆角安全内接框的穿屏变换 `throughScreen`、平滑跳字 `rollNumber` 等，亦可直接正视裁切或分屏对照）；配乐与音效在 `kit/sound.js` 中按题材自由选用触感拟音留白（`uiClick`/`swipe`/`glass`，不必每片硬铺鼓组循环）、温暖电钢律动（`epiano` + `subBass`）、侧链脉冲（`sidechain`）或阻尼房间/大厅混响。
   - MV 切点严格取 `songmap` 的 `downbeats`/`beats` 或唱词乐句起音；字幕必须将 `lyrics.draft.srt` 复制为 `lyrics.srt` 人工核对校改后，经 `node <kit>/captions.mjs out/song/lyrics.srt lyrics.mjs --no-overlap` 导出（严禁把未校对草稿或 `(repeated, check by ear)` 搬上屏幕）。先做最难的 8–12 秒有声试片，成立后铺满全片。
4. **审片修订与母带交付**：按 [review.md](references/review.md) 跑 `shotlist.py`（MV 加 `--song`，核查网格等长切、放大式切、黑场、超过 2 秒死水段、偏拍及重复段落是否视觉雷同）、联系表、切点帧条、`textcheck.mjs`（自动覆盖 `#caps .cap` 与 `#lyric`）、`mixcheck.mjs` 与 `1920×1080 @ 30fps` 成片解码抽帧，修到全部达标后交付。

---

## 命令速查

| 目的 | 命令 |
|---|---|
| 环境与显卡负载探测 | `node <kit>/doctor.mjs` |
| 生成旁白 + 逐词时间戳 | `python <kit>/narrate.py cues.json vo/ --voice teacher --style lesson --takes 2`（显卡忙时 `--device cpu --takes 1` 或 `--engine edge`） |
| 讲题纯净音轨 + 软字幕 | `node <kit>/audio.mjs index.html - out/audio.webm --vo vo/ --srt output/captions.srt` |
| 配乐合成与响度检查 | `node <kit>/audio.mjs index.html score.html out/audio.webm --vo vo/`、`node <kit>/mixcheck.mjs index.html score.html out/mix.png` |
| 草稿快渲预览（540p@15fps） | `node <kit>/render.mjs index.html video out/pic.mp4 --draft --audio out/audio.webm --mux out/preview.mp4`（显卡忙时设 `VC_SOFTWARE_GL=1`） |
| 1080p 正式母带（可封软字幕） | `node <kit>/render.mjs index.html video out/pic.mp4 --audio out/audio.webm [--srt output/captions.srt] --mux output/final.mp4` |
| 原尺寸静帧 / 联系表 / 切点条 | `node <kit>/render.mjs index.html stills out/ 5 18 42` · `sheet out/sheet.jpg --every 2` · `strip out/strip.jpg --at 9.8,18.2` |
| 版面碰撞与越界体检 | `node <kit>/boardcheck.mjs index.html [--every 3]` |
| 成片镜头表检查 | `python <kit>/shotlist.py output/final.mp4 [--mode lesson]` · MV 加 `--song out/song/songmap.json` |
| 歌曲地图 / 歌词导出 / 原声合片 | `python <kit>/songmap.py song.m4a out/song --lyrics` · `node <kit>/captions.mjs out/song/lyrics.srt lyrics.mjs --no-overlap` · `python <kit>/mux_original.py out/pic.mp4 song.m4a output/final.mp4` |
| 字幕检查 / 素材粗剪 | `node <kit>/textcheck.mjs index.html` · `node <kit>/cut.mjs edit.json out/cut.mp4` |

---

## 交付前硬核对清单

- [ ] **承载力诚实披露**：显卡受限降档、未亲耳试听（仅凭响度 `-16 LUFS` 与频谱核对）、或抽象化替代之处，已在回复中如实写明。
- [ ] **无制作读数与首帧完整**：第一帧就是完整构图（非黑屏）；画面内无帧号、`00.0 / 89.7 s` 播放计时或调试辅助线。
- [ ] **话画一致且无冗余复读**：说到的时间、天气、物理量或动作在画面中真实可见；讲题轨做到了口播、板书与软字幕分工，没有“配音+大标题+硬字幕”同句复读三遍。
- [ ] **数据同源与署名准确**：所有计算数字同出一份数据代码；引用他人录音/素材时严格按原文逐人署名角色与许可，原创内容不编造署名。
- [ ] **自动化检查与解码抽帧全过**：`boardcheck.mjs` 无文字/公式碰撞与边缘裁切；`shotlist.py`（讲题用 `--mode lesson`）标记项已修正或有明确设计依据；最终交付文件确为 `1920×1080 @ 30fps` 并经 `ffmpeg` 解码抽帧核验清晰度。
