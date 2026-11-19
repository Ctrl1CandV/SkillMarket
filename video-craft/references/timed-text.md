# 用录音时间轴排字幕和歌词

先用实际录音确认文字、断句和时间。已核对的 UTF-8 SRT 可以用 `captions.mjs` 转成网页场景可导入的时间表。本地运行只需 Node 18 或更高版本，文本及时码均来自原 SRT。原文件留作字幕校对与独立交付，生成文件供画面取用。

## 整段或选段

```text
node <kit>/captions.mjs dialogue.srt dialogue.mjs
node <kit>/captions.mjs song.srt lyrics.mjs --from 8.5 --to 12
```

`--from` 和 `--to` 是原录音的起止秒数，可省略任一端。默认从原录音的 0 秒开始，保留后续全部字幕。字幕和截取范围有交集时，起止时间裁到范围内，再减去 `--from`。参数最多精确到毫秒。只碰到端点的字幕跳过，同时出现的字幕以及单条字幕中的换行保留。对有跳段的剪辑，先按每段的来源分别截取，再加上它在成片中的起点。

例如 `song.srt` 的两条字幕覆盖 `7–9` 秒与 `8.75–12.5` 秒。

```srt
1
00:00:07,000 --> 00:00:09,000
雾沿着屋檐落下来
Mist falls along the eaves

2
00:00:08,750 --> 00:00:12,500
街灯回到了屋里
The streetlights return indoors
```

`8.5–12` 秒的选段会导出以下时间表。单位是成片片段内的秒数，交叠的 `0.25–0.5` 秒仍显示两条字幕。

```js
export default [
  { start: 0, end: 0.5, text: '雾沿着屋檐落下来\nMist falls along the eaves' },
  { start: 0.25, end: 3.5, text: '街灯回到了屋里\nThe streetlights return indoors' },
];
```

第一条只剩半秒，原文保留供你判断。交付前用成片核对这种被截断的句子，按实际听到的部分修订，或调整音频和画面的截取点。

## 网页逐帧显示

把 `<div id="captions" hidden></div>` 放在字幕层。用 `textContent` 写入原始文字，CSS 用 `white-space: pre-line` 保留换行。SRT 里的样式标签会按字符保留，带 `<i>` 等样式标记的文件可先在字幕编辑器中另存成纯文本字幕，再用 CSS 处理字形。

```js
import cues from './lyrics.mjs';

const captions = document.querySelector('#captions');

// Call this inside your scene's seek(t).
function drawCaptions(t) {
  const visible = cues.filter(({ start, end }) => start <= t && t < end);
  captions.textContent = visible.map(({ text }) => text).join('\n');
  captions.hidden = visible.length === 0;
}
```

```css
#captions {
  max-inline-size: 80%;
  white-space: pre-line;
  line-height: 1.35;
}
```

MV 的歌词字幕按 [MV](music-video.md#歌词字幕) 的做法：全片一个位置，原文和译文分两行各设字号，按实际呼吸划句；主体经过字幕区时调构图，不挪字幕。长音在字幕仍需阅读时可以保留原句。教程里字幕可以保持稳定字号和位置；先给界面结果和选项留空间，长指令单独停留，便于抄录。实际有和声、叠唱或对话交错时，检查本例的逐条堆叠是否读得过来，必要时给不同说话者分配位置，或者另交完整的字幕文件。

把文字检查指向实际字幕元素，例如 `node <kit>/textcheck.mjs page.html --sel '#captions'`。在交付分辨率复看片首、片尾、双语最长行和重叠处，确认文字未遮住关键画面，截取之后字幕与最终音轨仍同步。 [声音](sound.md) · [音乐驱动与 MV](music-video.md)
