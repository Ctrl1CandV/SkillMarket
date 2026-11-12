# 2026-11-12 实测：真实论文的筛读路线 + 一页扫描件的本地 OCR

目的：迁到 Windows 本机后补上 0.5.x 没做的完整一轮。确认显卡，用一篇真实论文走数字 PDF 的筛读路线，再用一页真实扫描件验收本地 OCR。任务单见 [BRIEF-paper.md](BRIEF-paper.md)、[BRIEF-scan.md](BRIEF-scan.md)，环境说明见 [ENV.md](ENV.md)，运行脚本见 [run_pi.sh](run_pi.sh)。样本和完整日志在仓库外，没有入库。

## 样本

用户让我自己找论文，所以两份样本都是公开材料：

- **论文**：arXiv 2611.14286v1《ForeseeDrive: Future-Token Conditioning for Anticipatory Generative Driving》。15 页数字 PDF，0.8 MB，有公式、7 张表、3 张图。选这篇是因为它够新，模型不能靠记忆答题。
- **扫描页**：Shannon 1948《A Mathematical Theory of Communication》BSTJ 期刊扫描件第 393 页。来自 archive.org 条目 `bstj27-3-379` 的单页图 `page/n14.jpg`，1020×1746 灰度 JPEG。页内有行内分数、两条行间公式（含求和上下限）、一张树状图、定理和脚注。

标准答案：

- 我对照原页渲染图定了论文题目的标准答案：表 1 在第 7 页，ForeseeDrive 的 PDMS 为 89.2，最高对比方法 SeerDrive 为 88.9。图 2 在第 3 页，400 dpi 裁图核对，蒸馏虚线从教师 token 落到预测 token，基础候选另有蓝线接到 TTC 守卫。式 (5) 是在固定候选集上取 argmax，式 (6) 是条件生成。
- 扫描页由我逐行对照原图。

## 环境（doctor）

- RTX 4070 Ti SUPER 16 GB、内存 32 GB，`doctor` 正确识别显卡。
- PaddleOCR 3.7.0（GPU），MinerU 4.0.12（`docvision-mineru` 环境）。
- 远程同意记录为 `remote`，但没有 Paddle 密钥，所以云端不可用，几次运行都没有上传。
- 我先手动跑了一页扫描件（不是验收页）：MinerU standard 档，单页 13 秒，正文、公式和脚注基本都对，只把一行字母序列标成了标题。

## 运行

条件：pi 1.4.0，工具 read/bash/edit/write，技能按描述自然触发。技能用开跑时的快照，排除凭据文件。提示只有一句：“请阅读当前目录下的 BRIEF.md 和 ENV.md，按要求完成任务。”论文用 `deepseek/deepseek-flash`，扫描页用 `openai/gpt-6.1-sol`（用户指定）。每个条件只跑 1 次。

| 运行 | 技能 | 用时 / 工具调用 / 费用 | 结果 |
|---|---|---|---|
| 论文 1 | 0.5.1 | 1 分 50 秒 / 27 / 0.025 | 四题全对，页码全对 |
| 扫描 1 | 0.5.1 | 27 秒 / 0 / 0 | 失败：pi 刷新 OpenAI 登录凭据时网络请求失败，没开始做；与技能无关 |
| 扫描 2 | 0.5.1 | 2 分 43 秒 / 14 / 0.088 | page.md 与原图逐字一致 |
| 论文 2 | 0.5.2 | 3 分 22 秒 / 42 / 0.035 | 四题全对；看到新警告后改用页面图和 OCR 核对 |

**论文 1。**

- 流程：doctor → fast 转换 → 读全文 → 对第 7 页（表）和第 3 页（图）做精读包并实际看图。图 2 字太小，模型自己用 bbox 加 500 dpi 裁图。
- 用 `correct add` 把核对结果存成本页校正，最后 verify 通过。
- 回答里有一处错误说法：“PDF 前 7 页是匿名审稿版和 arXiv 版并存的双版式，文字层每页出现两遍”。实际上页面上只显示 arXiv 版，见下面问题 1。
- 中途 `correct add` 打印结果时崩溃，见问题 2；模型之后自己加了 `PYTHONIOENCODING=utf-8`。

**扫描 2。**

- MinerU standard 档出初稿。初稿只丢了页眉页码，分数、求和上下限和脚注都对。
- 模型自己用 PIL 放大三块区域看图（没用技能的 `refine` 精读包），补回页眉，图注后加了标明“非原文”的图示说明，存成本页校正。
- 我逐行对照原图，没发现错误。

**论文 2。**

- fast 转换的输出里出现新警告，模型随即对第 3、7 页跑本地 OCR（MinerU，2 页 21 秒），再用 400–900 dpi 裁图核对图 2。
- 回答说明了那几页“文字层含页面上看不见的文字”，没有再说 PDF 有两版。没有遇到编码崩溃。

## 发现的问题和修改（0.5.2）

1. **fast 档会抽出页面上看不见的文字。**
   - 现象：这篇论文的图 1、2、3 是从匿名投稿版 PDF 整页裁出来的。裁掉的部分看不见，文字却还在文件里，pypdf 和 pdfium 都会抽出来，PyMuPDF 不会。
   - 影响：第 1、3、7 页的文字层混进了别处的内容，第 7 页甚至混进了另一页的整张表 3。读的人看不出来，可能把看不见的草稿文字当成论文内容引用。
   - 修改：`text_local` 对含插图文字的页面用 pdfium 按 72 dpi 渲染，统计“框内没有任何墨迹”的字符；超过 40 个且占 3% 以上时给出警告。这一页的 `read --page` 开头和 `read --list` 都会重复这条警告。
   - 校准：本文报出第 1、3、7 页，分别是 664、1123、3017 个字符。presentation-craft 的几份彩色背景 PDF 导出件一处都不报。15 页多花约 0.7 秒。
   - 没做的：看不见的字和可见的字交错排列，硬删会留残渣，所以只警告不删除。
2. **中文 Windows 上输出被管道接走时会崩溃。**
   - 现象：输出被管道或文件接走时默认用 GBK 编码，遇到论文里的 ϕ、ﬁ 连字等字符，`read`、`correct add` 会抛 `UnicodeEncodeError`。
   - 修改：入口把 stdout/stderr 改成 UTF-8；子进程那一侧原本就是 UTF-8。
3. **自检的显示问题。**
   - MinerU 启动失败时只显示 “Traceback (most recent call last):”。现在显示最后一行的真正原因。如果原因是缺模块，而当前设置了 `PYTHONNOUSERSITE`，会附带提示。
   - 剩余磁盘空间原来显示成 `505.71999740600586 GB`，现在保留一位小数；`setup` 的输出同样改了。
   - “remote consent … (file: 凭据文件路径)”容易误解，因为同意记录其实在 config.json 里。现在同意那一行写 config.json 的路径，凭据文件路径挪到密钥那一行。

回归测试从 270 项增至 276 项（新增 [test_text_layer_visibility.py](../test_text_layer_visibility.py)），全部通过，跳过 1 项。5 项契约检查通过。

## 本机环境里没修的问题（需要用户决定）

`docvision-mineru` 环境缺 pydantic、click、lxml、pillow 等十几个依赖，平时靠用户目录的 site-packages（`%APPDATA%\Python\Python312`）补上。普通终端里能用。一旦设置 `PYTHONNOUSERSITE=1`，或用户目录的包升级、删除，MinerU 就会启动失败。代码里原本就有注释承认这一点，所以 MinerU 子进程不隔离用户目录。

修好的办法是把缺的包装进这个环境，这属于安装软件，要先问用户。

## 任务目录之外

用户级 site-packages、字体、全局 npm、conda 环境列表、两个识别环境的包、docvision 配置和模型目录，运行前后都一致。

## 没验证的

- 每个条件只跑 1 次。
- 中文扫描件没测。
- 扫描页那次模型自己裁图，没走技能的 `refine` 精读包。
- PaddleOCR 本地路线这次没被选用。
- 云端 API 没有密钥，没测。
