# 回潮 · Tide Returns

一支 20 秒竖屏器乐 MV。1080×1920、30 fps。远岸和一叶小船留在同一片水上。观众凭同一个圆形认出远处的月轮、水面里的倒影，以及最后回到天际的月轮。两次切换都让圆在画幅中的位置与大小接得上。

| 秒数 | 声音 | 画面 |
|---|---|---|
| 0–5 | 拨弦和钢琴奏出 A–C–E–D，句尾留空 | 紫红夜色，船从月轮与观众之间划过去 |
| 5–10 | 四音动机重来，回应抬高，低鼓与细碎打击进入 | 切到贴近水面的桨叶特写。桨触水，划开铜色倒影，镜头抬高时倒影重新连成圆 |
| 10–15 | 鼓退，低音区的钢琴音隔得更开，伴奏滤暗 | 同一个圆变为俯拍水面的倒影，水纹把圆推向取景框下方 |
| 15–20 | 四音动机返回，出现左右拨弦回声，最后落到 C | 橙金色天光打开，月轮从山脊附近升起。尾音响起，船在光带留下一圈同方向的余波 |

画面、音乐和颗粒纹理都由代码生成。音乐与画面共享 `phrases.js`，单帧由秒数和固定种子推导。

## 运行

在示例目录运行，环境见 [工具包](../../references/kit.md)。

```text
node ../../kit/render.mjs index.html sheet out/sheet.jpg --every 1 --cols 6 --w 192
node ../../kit/audio.mjs index.html score.html out/music.webm --wav out/music.wav
node ../../kit/render.mjs index.html video out/tide-returns.mp4 --audio out/music.wav
```

最后一条命令会生成带声成片 `out/tide-returns-av.mp4`。

换成已有歌曲时，按实际录音改 `PHRASES` 的四段时点，将 `MELODY` 里的 `dip`、`pull`、`lift`、`wake` 标到新歌里听得清楚的音上，让桨叶有足够时间入水、划动和抬起。缩短或拉长选段时，把 `DURATION` 改成剪好的音轨长度。用这条音轨作 `--audio` 输入。如果要叠歌词，按录音记每句起止秒数，避开反光和船的位置。详细步骤见 [MV 指南](../../references/music-video.md)。
