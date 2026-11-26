# 斜拉极值与摩擦角（`lesson.js` 空间矢量涌现示例之一）

> **借它的工程骨架，不要抄它的配色与版式**：本片之所以选深空底 `#060A12`、光学辉光与左右推进，是因为本题核心动作是**摩擦热光晕的明暗消长**与**力矢量从物块剥离升空闭合成发光三角形**。做其他题目时，只复用 `data.js` 单一数据源、`compileFormula`/`morphFormula` 公式变形与 `buildTimeline` 词级同步骨架——请按新题本身的学科气质重新确立底色（如清透讲义白、暖纸、工程蓝图、石版黑板等）、空间构图与专属视觉隐喻。

## 本片三项导演决定（因为本题……所以……）
1. **核心视觉主角**：打破“水平拉最省力”的第一直觉——滑块在滚动剖面地面上匀速滑行，底面摩擦热光晕随上托减重实时降温收缩；拉力仰角 $\alpha$ 扫描时，`svgLocusFan` 在物块前方扫出轨迹扇并与 $0.60\,mg$ 最小半径圆相切。
2. **空间编排**：前半段物块在左、辅助角公式与极值曲线在右同步联动；进入几何证法时，代数区清场退净，重力 $\vec{G}$、拉力 $\vec{F}$ 与全反力 $\vec{R}$ 通过 `svgMorphArrow` 从物块剥离升空，在画幅中右闭合成直角三角形。
3. **色调与语义色**：深蓝黑底承托热摩擦珊瑚红（阻力）与极值翠绿（全反力恒定方向及最短垂线段），琥珀金固定分配给主控拉力 $\vec{F}$。

## 快速运行

```bash
# 1. 生成旁白与逐词时间戳（无显卡或显卡忙时加 --engine edge）
python ../../kit/narrate.py cues.json vo/ --voice teacher --takes 2

# 2. 导出 -16 LUFS 纯净人声轨与 .srt 软字幕
node ../../kit/audio.mjs index.html - out/audio.webm --vo vo/ --srt out/captions.srt

# 3. 版面碰撞自检 + 1080p@30fps 高清成片渲染
node ../../kit/boardcheck.mjs index.html --every 3
node ../../kit/render.mjs index.html video out/pic.mp4 --audio out/audio.webm --srt out/captions.srt --mux out/final.mp4
```
