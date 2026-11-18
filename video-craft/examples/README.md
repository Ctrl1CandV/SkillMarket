# 从哪里借镜头

[先播放三条带讲解的参考片](screening.html)。每条可以从关键时刻起播。读文件时，直接打开下面相应的拆镜页，成片帧上标了秒数。九个工程可以分别渲染，也可以只借某一个动作。

| 工程 | 看什么 | 从哪里改 |
|---|---|---|
| [九枚硬币，只称两次](worked-lesson/brief.md) · 77 秒教学 | 观察天平，排除六枚，用另一组称量结果自行解题 | 改 [四字段变体卡](worked-lesson/variant.json) 的称量结果、问句或思考时间，即可重算旁白与画面 |
| [纸鸟](sung-mv/brief.md) · 23 秒歌曲 MV | 听两句“飞呀”的音高和时值，观察同一只鸟在两次呼唤时占多大画面 | 从[命名镜头剪辑](sung-mv/excerpt.mjs)选“第二次飞呀”到“落在掌心”，或用自己的母带替换[逐字旋律](sung-mv/song.mjs) |
| [开场，提前十五分](product-spot/brief.md) · 26 秒软件广告 | 一个临时变更如何影响后台全组；真实下载的台本兑现片尾承诺 | 只把原时刻和提前量交给[改期工具](product-spot/retime.mjs)，再打开[实际软件](product-spot/product.html)核对重排结果 |
| [starter](starter/) · 一杯水里有多少个分子 | 旁白长度如何决定字幕、数字和声音事件 | `scene.js` 里的台词、数据和时间线。有逐句录音时，放到 `vo/01.wav` 等文件，先运行 `vo.mjs vo vo/vo.js`，导出音轨时加 `--vo vo` |
| [sky](sky/brief.md) · 59 秒横屏科普 | 从山谷进入空气，再到地球尺度。蓝光与红光的强度差在动作与声音中都能辨认 | `atmo.js`、`micro.js`、`space.js` 各管一种尺度的画面，`scene.js` 排镜头 |
| [promo](promo/brief.md) · 28 秒横屏产品宣传 | 群聊里的票据进入手机，20 笔转账变成 4 笔，数字来自同一组示例支出 | `scene.js` 的支出、界面和时间常量；真实产品另走[录屏与演示](../references/explain-and-demo.md) |
| [music-film](music-film/brief.md) · 20 秒竖屏器乐 MV | 旋律重现时，构图和镜头怎样回应；一轮月亮在岸边与水中有两种拍法 | 先听曲，再改 `phrases.js` 的乐句；有现成歌曲可直接用其录音合片 |
| [short-film](short-film/brief.md) · 22 秒叙事短片 | 雾夜海岸的全景、手部动作、灯具特写如何共同说明一次转向 | `timeline.js` 给动作、景别切换与声音标时，`scene.js` 调度镜头 |
| [iridescence](iridescence/brief.md) · 特效片头《显色》 | 从鳞片的微距高光拉到完整蝶形，同时看材质、遮挡和投影 | WebGL2 镜头及材质可拆作独立镜头 |

从本目录运行下面的命令可生成示例。先输出联系表也会建立输出目录。前面三个工程会尝试从各自的 `fonts/` 载入思源黑体/宋体和 Ubuntu，缺少时使用系统字体。

```text
node ../kit/render.mjs sky/index.html sheet out/sky.jpg --every 2
node ../kit/audio.mjs sky/index.html sky/score.html out/sky-audio.webm
node ../kit/render.mjs sky/index.html video out/sky.mp4 --audio out/sky-audio.webm --mux out/sky-final.mp4
```

[工具环境与接口](../references/kit.md) · [将已有片段、图片与音轨剪在一起](../references/editing.md)
