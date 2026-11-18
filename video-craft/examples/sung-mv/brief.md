# 《纸鸟》· 原创中文歌曲 MV

一张画着心的红纸被折成鸟，飞过街角，落在收信人手上。歌里出现两次“飞呀”。第一次拉远看它飞向哪里，第二次切近看见出发时印在翅膀上的邮戳。全片约 23 秒，1440 × 900，24 fps。

[从成片解码的三格画面](frames.jpg) · [有声预览](preview.mp4) · [完整歌曲母带](song.ogg)

本版采用 AI 合成演唱，声库为 **绮萱 v2.7.0**，歌唱引擎为 **DiffSinger**，使用 OpenVPI 的 PC-NSF-HiFiGAN 2025.02 声码器。全片使用四句原创歌词与原编配。公开发布本版时在作品说明、字幕或片中醒目处写明绮萱、DiffSinger 和 AI 合成演唱。声库作者允许发布合成音乐并指定了署名方式，模型权重另行下载。[绮萱使用条款](https://github.com/yqzhishen/qixuan-diffsinger/blob/main/terms_of_use/Terms_of_Use.zh-CN.md) · [声码器说明](https://openvpi.github.io/vocoders/)

## 对着四句歌拆镜头

| 母带时间 | 演唱 | 对照画面和工程 |
|---|---|---|
| 0–2.40 秒 | 拨弦前奏 | 俯看桌面。红纸上有心形笔迹和邮戳，折之前先让人认得它。 |
| 2.40–7.20 秒 | 把心折成鸟 | 唱到“折”（3.60 秒），纸上的三角面沿同一组折线收起。4.8 秒起的“鸟”拖长，把这段时间留给轮廓成形和离桌。见 [折纸的两组顶点](print.js) 与 [桌面镜头](scene.js)。 |
| 7.20–12.00 秒 | 飞过旧街角 | 从桌面切到跟拍。远屋慢移、近屋快移，晾衣绳从鸟的下方经过。同一只红鸟在青绿、赭黄的街道上容易找。 |
| 12.00–16.80 秒 | 飞呀，飞呀 | 12.0 秒的“飞”在日轮前用小全景，14.40 秒再次唱“飞”时切到近景。此时看清折纸的邮戳，前后两句有了不同的意思。 |
| 16.80–22.80 秒 | 飞进你掌心 | 手从画右伸入；19.20 秒唱到“心”时鸟落定。尾奏留纸翼缓缓收住，把投递动作做完。 |

## 用它改自己的歌

- **先剪一个有声预告。** 在示例目录运行 `node excerpt.mjs 第二次飞呀 落在掌心 1 out/teaser.mp4`。它从随附全长预览剪取第二声“飞”到纸鸟落掌，再多留 1 秒，即母带 14.40–20.20 秒，保留同期演唱。参数是起点事件、终点事件、终点后多留的秒数、输出路径；可省略余量。中英文事件名都能用，按原片顺序依次为 `纸开始折起/fold`、`飞过旧街角/launch`、`第一次飞呀/hook`、`第二次飞呀/secondCall`、`手伸入画面/land`、`落在掌心/palm`。脚本从实际预览读取时长，按原帧率出片，需要 Node、FFmpeg 和同包的 ffprobe。[剪选段脚本](excerpt.mjs)
- **先复现一段。** 从当前示例目录运行下列命令，输出已有副歌的 4.8 秒有声样片。查看两次“飞”各对哪一个景别，再决定换掉哪个镜头。完整输出时去掉 `--from 12 --to 16.8`。

  ```sh
  node ../../kit/render.mjs index.html video out/picture.mp4 --from 12 --to 16.8 --audio song.ogg --mux out/film.mp4
  ```

- **已有演唱录音。** 把命令里的 `song.ogg` 换成自己的母带。按录音量出重复乐句和收尾的实际秒数，先改 [song.mjs 的 cues、duration 和 lines](song.mjs)。本例字幕由 `scene.js` 的 `caption()` 按整句出现；自己的歌有 SRT 时可以用 [已有字幕对时](../../references/timed-text.md)。旧歌的 100 BPM 只是这份示例的刻度。
- **给自己的副歌做画面。** 找一件能从主歌带进副歌的东西。例如主歌有人系鞋带，第一声副歌可以看到跑道上的整个人，第二声切回跑鞋踩进雨水。对应本例，换 `print.js` 里的 `bird()` 和 `scene.js` 里的 `meadow()` 即可试这一段；既定歌的字、音高和音轨可直接沿用。
- **重新写词作曲。** [song.mjs](song.mjs) 中每音的四项是字、开始拍、持续拍和 MIDI 音高，每句的 `pinyin` 按相同顺序填写不带声调的标准拼音。编配整体移调 −3 半音。下载并解压[绮萱 v2.7.0 的 OpenUtau ZIP](https://github.com/yqzhishen/qixuan-diffsinger/releases/tag/v2.7.0) 和 [OpenVPI 2025.02 的 .oudep 声码器](https://github.com/openvpi/vocoders/releases/tag/pc-nsf-hifigan-44.1k-hop512-128bin-2025.02)（后者为 ZIP 格式）。下面的前两个位置参数指向分别含 `dsconfig.yaml` 与 `vocoder.yaml` 的已解压目录。需要 Python、NumPy、PyYAML、ONNX Runtime、Node 与 FFmpeg。

  ```sh
  python sing.py path/to/Qixuan_v2.7.0_DiffSinger_OpenUtau path/to/vocoder out/vocal.wav
  python make-song.py out/vocal.wav out/audio
  node ../../kit/render.mjs index.html video out/picture.mp4 --audio out/audio/song.ogg --mux out/film.mp4
  ```

  第一句和最后一句各留有闭口鼻音，拉长的是韵腹。初次重做可以在第一条命令末尾加 `--line 3` 只唱副歌，输出文件仍从影片第 0 秒对齐，便于直接与画面对照。检查歌声音头、连唱及尾音，再生成全曲。录好的其他演唱也可直接作为与影片对齐的 `vocal.wav` 送入混音。

## 怎样改过首版

首版翅膀与脖子连成一块，缩小后像一架纸飞机。重画折后顶点后，从 5.7、15.8 和 20.2 秒的画面都能认出同一只鸟。

上一版把普通话朗读单字拉成长音，字与字之间容易断开。这一版将一整句的歌词和音符一起送入歌声模型，在同一乐句内预测音高、气声与发声强度。制作时发现“角”和“心”的预测辅音长达约 0.8 秒，把拖长的时值留给后面的韵母。首句又单独唱了四遍比较咬字，“把心折成鸟”的辅音最后分别给了 110、120、75、90、75 毫秒，数值在歌谱该句的 `onsetMs`，仅用于这一次演唱。换词时从模型预测起，只有具体字听不清时才手调。混音同时给同一拍上的拨弦让出空间。随附母带已含演唱；需要真人口型时仍须取得相应的表演画面。
