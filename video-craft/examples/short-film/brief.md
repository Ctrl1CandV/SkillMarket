# 回光

22 秒、1920 × 864、24 帧/秒。暴雨里一艘船靠近礁岸，灯塔值守员合上开关。透镜亮起，灯光扫过海面，船掉头驶离。短片用画内动作、光线和声音交代经过。

| 时间 | 镜头与声音 |
| --- | --- |
| 0–4.50 秒 | 海岸全景。暗着的灯塔在左，船朝礁岸靠近。远处汽笛和左侧碎浪分开声像。 |
| 4.50–8.25 秒 | 切到窗边开关。窗里仍能看见船灯。海声变闷，手套入画，触点闭合有一次机械撞击和小火花。 |
| 8.25–11.70 秒 | 菲涅尔透镜近景。光从灯泡向外溢出，透镜棱和金属边框依次被照亮。电机低频先入，之后引出和声。 |
| 11.70–17.00 秒 | 回到海面。灯扫过船及近处海雾，船先露出正面，再把船头转向右侧。浪声回到近处。 |
| 17.00–22.00 秒 | 回到海岸全景。灯已经亮起，船驶往右远方，风声和音乐逐渐落下。 |

`timeline.js` 的事件由场景交给乐谱。`coast.js` 画灯塔、船和海面，`interior.js` 画开关与透镜，`paint.js` 提供重复使用的纹理和画笔。全片用本地 Canvas 2D 绘制，运行动画和声音时无需字体、素材下载或额外的渲染引擎。故事与船的操作均为虚构，片中开关与灯光运动按视觉表达设计。

从 `video-craft` 目录运行，先准备 [工具包](../../references/kit.md) 的 Chromium 和 FFmpeg。

```sh
node kit/render.mjs examples/short-film/index.html sheet out/return-signal-sheet.jpg --every 1.5
node kit/render.mjs examples/short-film/index.html strip out/return-signal-strips.jpg --at 4.5,7.65,8.25,8.62,11.7,13.15,17
node kit/mixcheck.mjs examples/short-film/index.html examples/short-film/score.html out/return-signal-mix.png
node kit/audio.mjs examples/short-film/index.html examples/short-film/score.html out/return-signal-audio.webm --stems
node kit/render.mjs examples/short-film/index.html video out/return-signal.mp4 --audio out/return-signal-audio.webm
```
