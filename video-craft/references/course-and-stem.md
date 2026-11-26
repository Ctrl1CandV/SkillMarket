# 轨道 A：课程、讲题与硬核科普制作指南

面向数学推导、工程物理与力学分析、计算机算法与系统机制、概率统计及硬核定量科普。本轨道主引擎为 [`kit/lesson.js`](../kit/lesson.js)（离线 MathJax v3 SVG 矢量公式、子项平滑变形、具象物理介质与积木阶梯图、角标参数牌、词级时间线），并可按需结合 [`kit/graphic.js`](../kit/graphic.js) 的纸面肌理与 `iris`/`wipe` 遮罩转场。

---

## 一、内容与讲稿设计：老师口语推理 + 严禁电报口号腔

好讲题片的灵魂是**把观众没想通的那一层窗户纸捅破**，而不是背定义或刷海报口号。写代码前先在 `brief.md` 定下三件事：

1. **三段式认知结构**
   - **破题与直觉反差（约 15%–20%）**：直接亮出学生最容易错的第一反应（如“两点之间直线最短，为什么光偏偏走折线？”“同样怀疑丢包，为什么 3 个重复 ACK 只减半，超时却一棒子打回 1？”），用双路径竞速或对比画面建立悬念。
   - **分幕因果推演（占 55%–65%）**：一步一幕把代数/系统规则和几何/物理机制对应起来（如求导令 $T'(x)=0$ 的分式如何直接对应法线夹角正弦 $\sin\theta$；`cwnd` 每轮如何按翻倍与加一垒高）。
   - **考场易错坑与通法收束（约 15%–20%）**：专门点破考场高频失分点（如 `9 / 2 = 4.5` 向下取整取 `4` 而不是 `5`；斜向上拉变斜向下推时的 $53^\circ$ 自锁边界；二阶导数恒正保证唯一全局极小）。
2. **自然连贯的老师讲稿（严防“海报电报腔”与概念失真）**
   - **反面教材（机械电报腔 + 概念错）**：“阈值八，窗口从一出发。超时：阈值减半，四；窗口归一。”甚至把 `cwnd = 1` 写成“一次归零”。
   - **正面写法（有因果、有连词的自然口语）**：“过了阈值八就转入拥塞避免，每个往返只加一，涨到十二。这时收到三个重复确认——说明后面的包还在陆续到达，链路没断，只是轻度拥塞，所以把阈值和窗口一起砍半到六就够了。”
   - 配音文本里的数字和符号一律写成准确的中文读法（“四分之三”“七点三七零米”）。
3. **严格声画分工（消除三遍复读）**
   - 口播字幕统一由 `audio.mjs ... --srt output/captions.srt` 导出并由 `render.mjs --srt` 封装成可开关 MP4 软字幕轨，**严禁在画面底部再烧录一条黑底硬字幕**，把宝贵的画面空间全部留给图形与公式。
   - 单一数据源：所有坐标、曲线、角度、窗口值与比较表数值必须由同一个 `data.js` 函数算出，绝不手填两套数字。

---

## 二、版面质感、分幕清场与具象物理画法（三大铁律）

实测表明，讲题画面最容易掉进两个极端坑：要么做成“五六个弹窗框套小字”的网页后台，要么做成“纯黑底上画两根裸线 + 把七八行公式全堆在一屏”的简陋草图。必须同时守住以下三条铁律：

### 铁律 1：主图常驻联动 + 推导区按幕清场（同屏主公式严控 ≤ 2 个！）
- **严禁公式堆积**：绝对不要把第 1 步到第 7 步的公式全部留在右半屏！使用 `actAt(t, ACTS)` 把右半屏划分为清晰的推导幕（如：`01 建模写出 T(x)` → `02 求导极值条件` → `03 几何正弦识别导出折射定律` → `04 本题数值解与直线对比表`）。
- **每幕只放大展示 1–2 个核心公式（字号 38–52px）**：同一幕内的恒等变形用 `morphFormula` 原地平滑变形；进入下一幕时，上一幕已完成的过渡式**干脆淡出清场**，留出充足留白与大字号可读性。`boardcheck.mjs` 会自动检测同屏公式数量，超过上限直接报 `formula_crowding` 错误！

### 铁律 2：复杂子机制敢于切入“全屏专场”，不要缩在角落画火柴盒
- 当主画面是宏观全局图表（如 16 个 RTT 的 `cwnd` 阶梯全景），而中间需要讲透一个微观动态机制（如“发送方 → 信道 → 接收方：为什么 3 个重复 ACK 有连续回声，而超时是一片死寂”）时，**不要在主图角落塞一个 200px 宽的迷你示意图**！
- 正确做法：借用 `FocusCamera` 大幅推近，或在 Canvas/混合层用 `kit/graphic.js` 的 `iris` / `wipe` 遮罩（0.6–0.8s）**切入全屏深色/撞色机制专场**，用大尺寸节点、滑动窗口槽位、飞行数据包与回声波形把机理演透，再遮罩切回全局主图继续推演。

### 铁律 3：拒绝裸线草图！用学术版面与具象物理层次做画面
- **选一套成体系的视觉底板**：
  - **深青光学课堂风（`THEMES.slate`）**：搭配 `drawChapterTitle` 顶部章节大标题与细分割线、`svgCard(..., { corners: true })` 带角标的参数/对比牌、光学辉光 `#vc-glow`；
  - **暖纸纹学术期刊风（`THEMES.paper` 或 `graphic.js` `paper` + `grid`）**：米白纸纹 `#ECE7DC` + 建筑细网格 + 墨黑大字 + 青绿 `#0C7468` / 朱砂红 `#D2402B` 强调色，信息密度高时极清爽耐看。
- **物理介质与离散结构必须画得具象饱满**：
  - **连续物理/几何题**（光学、力学、电磁、微积分）：严禁只画一个 `opacity: 0.06` 方块充当水或斜面！使用 `svgMediaTank` 画出**深浅渐变水体、动态正弦水波纹、发光分界面、网格衬底与 `svgRuler` 坐标标尺**；几何推导时画出**半透明着色辅助直角三角形**（标清边长 $x, 4, 10-x, 3$）；讲“最快路径”时，**同时发出两颗光子（灰色虚线直连光子 vs 金青折线折射光子）同台竞速**，让观众亲眼看到折线光子先到终点！
  - **离散算法/系统题**（计网、OS、数据结构、概率统计）：严禁只画一根孤零零的细折线！使用 `svgStepColumns(..., { unitBlocks: true })` 把每个轮次的窗口/计数画成**一格格向上垒起的实体积木块**，配阶梯虚线阈值、红色下坠箭头与差值角标，右上角配 `svgCard` 大字号实时状态牌。

---

## 三、固定音色人声 + 事件微音效工作流

讲题轨采用**固定音色老师干声 + 贴合画面动作的轻量事件微音效**（不铺持续嗡嗡响的背景合成器垫音，但保留物理与交互动作的声音质感）：

```bash
# 1. 先跑 doctor 检查显卡是否空闲：
node <kit>/doctor.mjs
#    - 若 gpu.voxcpm15_safe === true：用本地离线 VoxCPM1.5 克隆固定 teacher 音色卡
python <kit>/narrate.py cues.json vo/ --voice teacher --takes 2
#    - 若 gpu.busy === true（如利用率 ≥75%，无人值守批处理时）：自动避让显卡，走零显存 Edge 讲师男声（同样导出逐词时间戳）
python <kit>/narrate.py cues.json vo/ --voice teacher --engine edge

# 2. 无需手写 score.html，传 '-' 即可将 vo/ 干声与场景 meta.sfx 微音效合成为 -16 LUFS 音轨，并导出 .srt 软字幕：
node <kit>/audio.mjs index.html - out/audio.webm --vo vo/ --srt output/captions.srt
```

在 `scene.js` 中用 `TL.word` 做词级声画同步，并在 `meta.sfx` 声明关键动作微音效：

```js
const sfx = [
  ...ROUNDS.map((r, i) => ({ t: r.t0, kind: 'tick', freq: 2200 - i * 45, gain: 0.02 })), // 每轮积木垒起轻叩
  { t: T_REFRACT, kind: 'pluck', note: 'E5', gain: 0.045 },                              // 光子入水偏折 / 快重传
  { t: T_IRIS_IN, kind: 'whoosh', gain: 0.04 },                                          // 切入全屏机制专场
  { t: T_TIMEOUT, kind: 'thud', freq: 88, gain: 0.14 },                                  // 超时断崖重击
  { t: T_OPTIMUM, kind: 'chime', note: 'G5', gain: 0.04 },                               // 极值/定理锁定清音
];
register({ duration: TL.duration, fps: 30, width: 1920, height: 1080, seek, meta: { cues: TL.cues, sfx } });
```

---

## 四、`kit/lesson.js` 核心原语速查

起步可参考 [`examples/stem-lesson/`](../examples/stem-lesson/)（SVG 空间涌现）与 [`examples/transit-map/`](../examples/transit-map/)（Canvas 暖纸纹版面与遮罩转场；SVG 与 Canvas 可在同一 `#stage` 叠放混用）：

| 类别 | 函数 | 用法与要点 |
|---|---|---|
| **主题与章节顶栏** | `THEMES.slate` / `THEMES.paper` / `THEMES.ivory`、`drawChapterTitle(svg, { kicker, title, step })` | 深青光学主题与暖米白学术纸面主题；`drawChapterTitle` 绘出大尺度章节标题、右对齐步骤号与建筑细横线 |
| **分幕清场序列器** | `actAt(t, [{ id, t0 }, ...], { fade })` | 返回 `{ id, index, localT, alpha }`，自动保证“前幕先退净、后幕再进入”，零重影切换右半屏推导步骤 |
| **角标参数/对比卡** | `svgCard(parent, x, y, w, h, k, { title, badge, accent, corners, shadow, theme })` | 带偏移阴影、左侧强调色条与四角裁剪角标（`corners: true`）的设计感信息牌，装实时读数或路径对比表 |
| **双介质波纹实验槽** | `svgMediaTank(parent, box, { splitRatio, topLabel, bottomLabel, waves, t, rulerDomain })` | 渐变双介质（如空气/水）、动态水波纹、发光分界面、内置细网格与底部 `svgRuler` 坐标尺，返回 `{ surfY, xOf }` |
| **实体积木阶梯图** | `svgStepColumns(parent, box, columns, t, { maxVal, thresholds, unitBlocks })` | 按时间逐列垒起离散单元积木块（如每轮 `cwnd` MSS 格）、阶梯虚线阈值（`ssthresh`）与下坠箭头角标 |
| **刻度尺与坐标系** | `svgRuler(parent, p0, p1, k, { domain, step, majorStep, unit })`、`svgAxes` + `svgPlot` | 工程长度/坐标刻度尺；二维函数坐标系与发光曲线、动态追踪光标 |
| **出版级公式与变形** | `loadMath`、`compileFormula`（`\id{key}{子式}`）、`drawFormula`、`morphFormula`、`highlightPart` | 离线 MathJax v3 SVG 编译、子项语义上色、跨步弧线平滑变形、下划线/方框聚光标注 |
| **力学、空间与框图** | `svgSurface`、`svgBlock`、`svgArrow`、`svgMorphArrow`、`svgLocusFan`、`svgAngleArc`、`svgNodeBox`、`svgArray`、`svgConnect` | 滚动剖面地面、倒角刚体、发光力矢量与升空闭合、极坐标扫描轨迹扇、角度弧、算法数组指针与状态节点 |

---

## 五、快渲调优与交付前硬体检

1. **改稿用 `--draft`，交付必跑 `1080p@30fps`**：
   ```bash
   # 快渲预览（960×540@15fps，严禁用于最终交付）：
   node <kit>/render.mjs index.html video out/draft.mp4 --draft --audio out/audio.webm --mux out/preview.mp4
   # 正式母带交付（1920×1080@30fps + 内封可开关软字幕）：
   node <kit>/render.mjs index.html video out/picture.mp4 --audio out/audio.webm --srt output/captions.srt --mux output/final.mp4
   ```
2. **三项必过体检**：
   - `node <kit>/boardcheck.mjs index.html --every 3`：**0 公式堆积（`formula_crowding`）**、**0 文字重叠（`overlap`）**、**0 实线穿字（`line_crosses_label`）**、**0 越界与过小字**；
   - `node <kit>/render.mjs index.html stills out/stills <每幕代表秒数>`：用读文件工具打开 `1920×1080` 原尺寸静帧，用人眼审视**物理图解是否饱满有层次（非裸线草图）、每幕排版是否清爽大字号**；
   - `python <kit>/shotlist.py output/final.mp4 --mode lesson` + `ffmpeg` 解码抽帧核验清晰度。
