# 中文排版

## 字体：先弄清访客电脑上实际有什么

| 平台 | 黑体（无衬线） | 宋体（衬线） | 楷体等 |
| --- | --- | --- | --- |
| Windows | 微软雅黑 Microsoft YaHei（有粗体）、等线 DengXian | 宋体 SimSun（只有常规体） | KaiTi、FangSong（单字重） |
| macOS / iOS | 苹方 PingFang SC（多字重） | 宋体-简 Songti SC（多字重） | 楷体-简 Kaiti SC |
| Android / Linux | 思源黑体 Noto Sans CJK SC | 思源宋体 Noto Serif CJK SC（视安装情况） | — |

- **字体栈按平台写全。** 例如：
  ```css
  --sans: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", "Noto Sans SC", sans-serif;
  --serif: "Songti SC", "Noto Serif CJK SC", "Noto Serif SC", SimSun, serif;
  ```
  想让英文和数字用某款拉丁字体，就把它放在中文字体之前，汉字会自动回落到后面的中文字体。
- **宋体加粗要用真粗体。** 常规粗细的宋体正文在各平台都没有问题，适合阅读页。问题只出在加粗时：SimSun 没有粗体，Windows 上加粗会变成笔画发糊的合成粗体。所以宋体只用在常规粗细的正文和不加粗的大标题上；需要加粗的宋体标题，就加载带真粗体的字体（如思源宋体），或者把这一级标题改用黑体。
- **网页中文字体很大。** 一款字体的一个字重往往就有数 MB。需要特定气质时，用按 `unicode-range` 分片的字体服务，或只加载标题用到的那些字的子集。访客在中国大陆时，海外字体服务可能加载不了，自托管或系统字体更稳妥。
- **楷体、仿宋适合少量文字**，比如引文、批注、题签。

## 正文

- **尺寸起点**：字号 16–18px（手机 16–17px），行高 1.7–1.9，每行约 30–40 个汉字（正文容器 30–40em）。
- **分段**：网页上用段间距分段（约 0.8–1em）。首行缩进也可以，两种方式选一种。
- **对齐**：默认用 `text-align: start`。两端对齐适合宽栏、段落里少有长英文词和链接的场合；用之前在手机宽度下看一遍，确认没有哪一行的字距被拉开。
- **强调**：用加粗（黑体效果最好）、颜色，或着重号：
  ```css
  em.dot { font-style: normal; text-emphasis: filled dot; text-emphasis-position: under right; }
  ```
  中文没有真正的斜体，浏览器只能把字形硬拉斜。中文强调用以上方式；英文书名、论文名可以保持正体，也可以用斜体。

## 中英混排

- **中文和英文、数字之间留出空隙。** 需要自动间距时显式写 `text-autospace: normal`。MDN 兼容数据记录的浏览器初始值为 `no-autospace`，不能把支持该属性等同于默认启用。将它作为渐进增强，旧浏览器可能忽略；保留材料已有空格，在实际字体与混排内容中检查，不批量重写代码、URL 和标识符。
- **标点**：中文句子用全角标点（，。：；“”），完整的英文句子内部用半角。
- **专有名词按官方写法**，比如 GitHub、arXiv、JavaScript。
- **长英文词、URL 和代码**在窄栏里会撑破布局或拉开字距。给它们加 `overflow-wrap: anywhere`；代码块放在自己的容器里横向滚动。

## 断行

- **避头尾**：`line-break: strict` 让句号、逗号、右引号等不出现在行首。
- **标题**：可用 `text-wrap: balance` 改善短标题的断行；不保证消除孤字，仍看实际宽度。正文可用 `text-wrap: pretty` 渐进增强，支持范围和行为按目标浏览器核对。
- **不该拆开的短语**：日期、金额、“第 3 章”这类短语，用 `white-space: nowrap` 包起来。
- **整段文字保持默认断行**。`word-break: break-all` 会把英文单词从中间切开，只用在 URL、哈希值这类元素上。

## 标点挤压

连续标点的间距受字体与浏览器影响。`text-spacing-trim` 尚未达到 Baseline，按目标浏览器核对兼容性；需要微调时用实际字体与连续标点样本检查，不假定各端默认表现相同。

## 标题与数字

- **标题字重**：黑体标题用 600–700；宋体标题用字体本身就有的粗字重。
- **大标题字距**：大字号中文标题显得松散时，可以把字距收紧一点（约 −0.01 到 −0.02em），以实际看到的效果为准。小号的英文大写标签则相反，可以稍微加一点字距。
- **数字对齐**：数字成列对齐时用 `font-variant-numeric: tabular-nums`。

## 依据

- W3C [Requirements for Chinese Text Layout（clreq）](https://www.w3.org/TR/clreq/)：§3.1 字体、§5.3.1 着重号、§6.1 断行与避头尾、§6.3 标点调整与中西文混排。
- [中文文案排版指北](https://github.com/sparanoid/chinese-copywriting-guidelines)（MIT）。
- MDN：[text-autospace](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/text-autospace)、[兼容数据中的初始值](https://github.com/mdn/browser-compat-data/blob/main/css/properties/text-autospace.json)、[text-spacing-trim](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/text-spacing-trim)、[text-wrap](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/text-wrap)（2026-10-24 核对）。
