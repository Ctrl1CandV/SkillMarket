# 示例

三个示例都是完整的工程，可以直接渲染。新片子从最接近的一个复制出来改。

| 示例 | 内容 | 演示的做法 |
|---|---|---|
| `starter/` | 一杯水里有多少个分子（约 14 秒） | 最小结构：旁白或配音生成时间线、遮罩字幕、颗粒与暗角、事件表、配音铺入并压低音乐 |
| `sky/` | 天空为什么是蓝的，晚霞为什么是红的（59 秒，横屏） | WebGL 大气散射着色器；远山从天空取色；发光光波与景深分子；从山谷到微观再到太空的连续镜头；把物理规律变成声音的配乐 |
| `promo/` | 虚构 App「两清」的宣传片（28 秒，横屏，120 BPM） | DOM 实现的手机与界面；消息先原地变形再飞入；推进穿过屏幕；数字由数据算出（20 笔 → 4 笔）；印章收尾；节拍型配乐与侧链 |

每个示例目录里都有 `brief.md`（starter 除外），写着任务、事实核对、核心画面和分镜，可以照着这个格式写自己的任务单。

## 运行

字体：示例默认从各自目录下的 `fonts/` 加载 `NotoSansSC-Bold.otf`、`NotoSansSC-Regular.otf`、`NotoSerifSC-Bold.otf`、`Ubuntu-B.ttf`、`Ubuntu-M.ttf`（都是开源字体）。找不到时会退回系统里的中文字体，排版可能略有出入。

```text
node ../kit/render.mjs sky/index.html sheet out/sky.jpg --every 2
node ../kit/audio.mjs sky/index.html sky/score.html out/sky-audio.webm
node ../kit/render.mjs sky/index.html video out/sky.webm --audio out/sky-audio.webm
```

starter 的配音：把每句的录音放到 `starter/vo/01.wav`、`02.wav`……，运行 `node ../kit/vo.mjs starter/vo starter/vo/vo.js`。之后渲染音轨时加上 `--vo starter/vo`。
