# 斜拉极值与摩擦角（课程与讲题轨标准模板）

## 受众与直觉切口
面向大学物理 / 考研力学学习者。打破“水平用力最省力”的第一直觉，用同一套物理模型把**代数辅助角配凑**与**全反力矢量三角形垂线段最短**在同一个无框深空舞台里打通。

## 为什么不用左右分栏卡片框
- 全片零圆角面板框、零顶栏厚黑条：滑块在滚动剖面地面上真实匀速滑行，底面摩擦热光晕随上托减重实时降温收缩；
- 拉力仰角 $\alpha$ 扫描时，`svgLocusFan` 直接在物块前方扫出直线轨迹扇并与 $0.60\,mg$ 最小半径圆相切；
- 进入几何证法时，重力 $\vec{G}$、拉力 $\vec{F}$ 与全反力 $\vec{R}$ 通过 `svgMorphArrow` 直接从物块上剥离升空，首尾相接闭合成发光直角三角形。

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
