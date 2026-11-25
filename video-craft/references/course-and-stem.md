# 轨道 A：课程、讲题与硬核科普制作指南

面向数学推导、工程物理与力学分析、计算机算法与系统机制、概率统计及硬核定量科普。本轨道使用 [`kit/lesson.js`](../kit/lesson.js)（内置离线 MathJax v3 SVG 矢量公式、子表达式平滑变形、世界坐标焦点相机、力学/坐标系/框图原语及逐词时间锚点），**不要去读 MV 或写景短片的参考文档**。

---

## 一、内容与认知设计：三段式结构 + 严禁三遍复读

好讲题片和“有声 PPT”的分水岭不在特效，而在**认知结构**与**声画分工**。动笔写代码前，先在 `brief.md` 写清三件事：

1. **三段式篇幅配额（拒绝平均用力切成八九张同版式卡片）**
   - **破题与直觉反差（约 15%–20%）**：不背教科书定义，直接抛出学生最容易答错的第一反应或卡壳点（例如：“觉得水平拉最省力？抬高一点试试，正压力和摩擦力其实变小了”），用动态画面亮出核心矛盾。
   - **单画布连续推演（强制占全片 50%–65% 主场）**：所有受力分解、状态迁移和公式恒等变形，在**同一张原图 / 同一个主方程**上连续生长。下一步从上一步的图形和项变形而来（`morphFormula`），用完的辅助式压暗退居上方，不靠翻页硬切推进。若一题有代数与几何两重本质（如辅助角配凑 ↔ 摩擦角矢量三角形），让两者在同屏左右印证。
   - **边界陷阱与通法收束（约 15%–20%）**：改动一个关键条件看边界（如斜向上拉改为斜向下推出现 $53^\circ$ 自锁渐近线；或换一组极端先验概率），点破考场易错坑与可迁移通法。

2. **严格声画分工（消除多媒体冗余效应）**
   - **口播（耳朵）**：讲“为什么这么想、下一步往哪转、哪一项消掉了”，写成自然的口语短句（数字写汉字读法：“四分之三”“三十七度”）。
   - **画布（眼睛）**：只放**题干关键条件、正在演化的公式/几何图/状态框、以及 ≤10 字的极短信号批注**（如 `分母最大 ⟹ F 最小`）。
   - **字幕（独立软轨）**：口播字幕默认由 `audio.mjs --srt output/captions.srt` 生成并由 `render.mjs --srt` 封装成 MP4 可开关软字幕轨。**严禁在画布上既放口播原话大标题、又烧录底部双行硬字幕**，把宝贵的纵向空间全部留给推导与图形。

3. **色彩语义绑定与聚光引导（Signaling）**
   - 同一物理量或算法指针在全片锁死同一种强调色：受力图上支持力箭头 $\vec{F}_N$ 用青色，右侧方程里的 `\id{fn}{F_N}` 就用同一个青色；非当前讨论的辅助项压低透明度（`alpha: 0.4–0.5`）。
   - 单一数据源：片中所有长度、角度、曲线与数值读数必须由同一个 `data.js` 函数算出，绝不手填两套常数。

---

## 二、空间舞台美学：去看板化、物理动态反馈与空间几何涌现

讲题视频最忌做成“顶栏导航条 + 左右两个圆角大卡片框 + 底部仪表条”的网页后台看板——框套框会把画面锁死成呆板课件。想做出既讲透本质又让人眼前一亮的画面，遵循四条空间原则：

1. **无框深空舞台（Zero-Box Stage）**
   - 用整张 `1920×1080` 画布作统一物理与数学空间（`drawStageBackground(svg, T, { gridStep: 0, glow: true, spotlight: [x, y], vignette: 0.48 })` + 稀疏十字准星），公式与函数曲线直接悬浮在深空聚光区（可用柔和径向渐变背光衬底，不要套实心圆角框），顶部只放极轻的无框章节圆点与单行参数读数，底部贴边放 `3px` 进度细线。
2. **让物理与系统对象“活”起来（Living Feedback）**
   - 题干说“匀速滑行”，地面剖面线就用 `svgSurface(..., { scroll: -t * 95 })` 向后连续滚动，配上微弱尾迹线；说“上托减小正压力与摩擦”，物块底面就加一层随 $\mu F_N$ 实时收缩变淡的接触热光晕（`filter="url(#vc-glow)"`）；讲电路谐振或算法指针，能量包络或窗口高亮就随当前参数实时呼吸。
3. **在原空间里涌现轨迹，而非只画外部折线图（`svgLocusFan`）**
   - 参数扫描时（如拉力仰角 $\alpha$ 从 $0^\circ$ 扫到 $70^\circ$、抛体仰角包络、相量旋转），直接从物理作用点用 `svgLocusFan` 扫出半透明残影扇与发光极坐标轨迹线，配合同心最小半径相切圆弧，让观众肉眼看见极值在物理空间里是怎么“切”出来的，再与旁边的函数谷底曲线互相印证。
4. **图形元素的空间剥离与重组（`svgMorphArrow`）**
   - 当需要从受力图过渡到闭合矢量三角形、从链表节点过渡到树结构、或从时域脉冲过渡到频域相量时，**不要硬切重画一张新图**：用 `svgMorphArrow(world, a0, a1, b0, b1, m, { arc, glow })` 让原本长在物块上的矢量箭头直接脱离物块（物块保留淡影交代来处），在空中划出弧线飞向中心舞台首尾相接闭合成发光几何图形。闭合多边形的矢量公式标签统一标在**边中点外法线处**，避开顶点箭头汇聚区。

---

## 三、声音与词级同步工作流

讲题轨默认采用**纯净人声主导**：不铺持续合成器垫音（避免干扰思考与电子塑料感），只保留自然说话气口，必要时仅在章节切换处加极轻单音提示（`gain: 0.03`）。

```bash
# 1. 生成配音并自动导出词级时间戳 vo/words.js 与句长 vo/vo.js
#    GPU 空闲且显存充裕（doctor 报 voxcpm15_safe: true）时用本地 VoxCPM1.5：
python <kit>/narrate.py cues.json vo/ --voice teacher --takes 2
#    无显卡、或 GPU 正忙且用户选择轻量通道时，用零显存 Edge 语音（同样原生导出词边界）：
python <kit>/narrate.py cues.json vo/ --engine edge

# 2. 无需手写 score.html，直接传入 '-' 组装 -16 LUFS 纯净人声轨并导出 .srt 软字幕：
node <kit>/audio.mjs index.html - out/audio.webm --vo vo/ --srt output/captions.srt
```

在 `scene.js` 中用 `buildTimeline` 读取词级时间戳，让箭头、高亮框和公式变形**精准卡在老师念出该术语的那一拍**：

```js
import WORDS from './vo/words.js';
import { buildTimeline } from '<kit>/lesson.js';

const TL = buildTimeline([
  { id: 'c01', gap: 0.45, text: '竖直方向有向下的重力，向上的支持力，还有拉力向上的分力。' },
  // ...
], WORDS);

const T_GRAV = TL.word('c01', '重力', 0.45);       // 精确命中“重力”起音秒数（未配音前按第 3 参数比例兜底）
const T_NORM = TL.word('c01', '支持力', 0.68);     // 精确命中“支持力”起音秒数
```

---

## 四、`kit/lesson.js` 核心原语速查

起步可直接复制 [`examples/stem-lesson/`](../examples/stem-lesson/)。页面只需一个 `<svg id="svg" viewBox="0 0 1920 1080"></svg>`：

```js
import { register, seg } from '<kit>/kit.js';
import {
  THEMES, svgEl, clearEl, loadMath, compileFormula, drawFormula, morphFormula, highlightPart,
  buildTimeline, cameraAt, applyCamera, makeCamera3D, drawStageBackground,
  svgSurface, svgBlock, svgSpring, svgArrow, svgMorphArrow, svgLocusFan, svgAngleArc, svgAxes, svgPlot,
  svgNodeBox, svgArray, svgConnect,
} from '<kit>/lesson.js';

const T = THEMES.slate; // 或 THEMES.ivory（浅色学术纸面）
const svg = document.getElementById('svg');
const measureHost = svgEl('g', { visibility: 'hidden' }, svg);
await loadMath(); // 同步加载内置离线 MathJax v3 SVG，无需联网或外部字体
```

| 类别 | 函数 | 用法与要点 |
|---|---|---|
| **专业公式编译** | `compileFormula(measureHost, tex, { size, color })` | 在 `seek(t)` 外预编译一次。用 `\id{key}{子式}` 标记要变色、框选或跨步变形的子项（支持嵌套在 `\frac`、`\sqrt`、矩阵内） |
| **公式绘制** | `drawFormula(parent, fm, x, y, { anchor, alpha, scale, partColors })` | `partColors: { fn: T.cyan }` 按键给子项上色；返回整体及各 `\id` 子项的世界坐标包围盒 `{ x, y, w, h, parts }` |
| **跨步平滑变形** | `morphFormula(parent, fmA, posA, fmB, posB, k, { partColorsA, partColorsB })` | 类似 Manim `TransformMatchingTex`：同名 `\id{key}{...}` 在两式间自动带弧线（`path_arc`）平滑移位与等比缩放，消去项淡出、新增项淡入 |
| **子项信号框** | `highlightPart(parent, laid.parts.den, k, { color, mode, label })` | 围绕任意分母/根式/矩阵项画动态描边方框或下划线（`mode: 'underline'`），并贴近给出简短结论批注 |
| **深空光效舞台** | `drawStageBackground(svg, theme, { glow, spotlight, vignette })` | 自动注入 `#vc-glow` / `#vc-glow-soft` 光学辉光滤镜、可移动径向聚光与暗角 |
| **世界与三维相机** | `cameraAt` + `applyCamera`、`makeCamera3D({ yaw, pitch, dist })` | 2D 世界坐标平滑推拉特写；轻量 3D 透视投影 `(x,y,z) -> [px,py,depth]` 用于空间场线与三维矢量 |
| **力学与动态表面** | `svgSurface(..., { scroll })`、`svgBlock`、`svgSpring`、`svgArrow(..., { glow })`、`svgAngleArc` | 支持连续滚动剖面线的地面/斜面、带高光倒角的刚体物块、弹簧、光学发光矢量箭头、角度弧 |
| **空间涌现与剥离** | `svgLocusFan(parent, origin, tipFn, k)`、`svgMorphArrow(parent, a0, a1, b0, b1, m, { arc })` | 参数扫描极坐标残影扇与发光轨迹线；矢量从物理对象平滑剥离飞向空中拼合闭合多边形 |
| **坐标系与曲线** | `svgAxes(parent, box, { xDomain, yDomain, xTicks, yTicks, k })` + `svgPlot(..., { glow })` | 返回 `{ x(v), y(v), pt(vx, vy) }` 映射器；`svgPlot` 渐进绘出发光函数曲线与阴影，支持极值切线标注 |
| **算法与系统图** | `svgNodeBox`、`svgArray`、`svgConnect` | 圆角状态框、自动带下标与上下命名指针（`i`, `j`, `top`）的一维数组/内存条（返回各格中心坐标）、带弧度 `bend` 的有向连接线 |

---

## 五、快渲调优与高清母带审查

1. **改稿阶段用 `--draft` 快渲，交付阶段必跑 `1080p@30fps`**
   - 调试动效与词级同步时：`node <kit>/render.mjs index.html video out/draft.mp4 --draft --audio out/audio.webm --mux out/preview.mp4`（自动以 `960×540 @ 15fps` 渲染，不改任何场景坐标，速度提升 6–8 倍）。
   - **禁止把 `--draft` 低清文件作为成片交付！** 无论配音走本地 `VoxCPM` 还是轻量 `Edge`，最终交付一律跑全分辨率母带：
     ```bash
     node <kit>/render.mjs index.html video out/picture.mp4 --audio out/audio.webm --srt output/captions.srt --mux output/final.mp4
     ```
2. **三项必做自检**
   - **几何与碰撞体检**：`node <kit>/boardcheck.mjs index.html --every 4` —— 自动检查全片公式与文字是否重叠、是否越出安全边距、字号是否过小（静止镜头要求 0 碰撞、0 越界；相机推拉过渡帧中移出镜头的背景元素除外）。
   - **关键帧原尺寸精查**：`node <kit>/render.mjs index.html stills out/stills <每段关键秒数>`，打开 `1920×1080` 原图肉眼检查箭头标签有没有压住方框边线、曲线有没有穿过批注文字。
   - **讲题模式镜头表与解码抽帧**：`python <kit>/shotlist.py output/final.mp4 --mode lesson`（检查黑场与超过 4.5 秒完全死水的静止段），并用 `ffmpeg -ss <t> -i output/final.mp4 -frames:v 1 out/dec.png` 核验编码后公式边缘清晰度。
