# 免费工具与运行

## 依赖选择

宿主提供文档/幻灯片运行时或依赖加载入口时，优先使用它返回的 Node、Python 与包目录；没有时使用已有环境或任务内依赖。不要将某台机器的绝对路径写进源稿或技能。

`scripts/doctor.py` 报告当前 Node、PptxGenJS、Python-PPTX、LibreOffice、Windows PowerPoint COM 和 PDF 栅格工具的可用性，分别列出原生制作引擎与渲染路线。PowerPoint 只探测 Python 支持和 COM 注册，不启动软件；注册存在不保证授权、导出或字体正常。缺失的可选引擎不意味着所有路线失败。探测不安装软件、不访问模型服务、不证明生成效果。

宿主返回的 Node 与包目录没有进入默认搜索路径时，在当前任务进程临时设置 `NODE_PATH` 为该包目录，再运行 `doctor.py --node <宿主Node可执行文件>`；不用因此重复安装包或修改系统环境。运行时路径从宿主获取，不硬编码到技能和源稿。

## 原生 PPTX 路线

PptxGenJS（MIT）用 JavaScript 创建文本、形状、表格、图表、图片和备注。适合需要可编辑 PPTX 的任务。复用安装的包；确有缺失时可在任务工程执行 `npm install pptxgenjs`，不要默认全局安装。

- 在添加页面前设置画布，例如 `LAYOUT_WIDE` 为约 13.33 × 7.5 英寸。使用真实画布尺寸，不能混用其他尺寸下的坐标。
- 定义少量主题字体、颜色、间距常量，具体元素仍按内容调整。原生文本/图表优先，复杂结构图可插入高分辨率或矢量资产。
- 原生图表使用真实数据；备注使用 `slide.addNotes(...)`。不要将备注放进页面正文。
- 颜色写为六位十六进制，不带 `#`；不要在颜色字符串里编码透明度。
- 新建每个对象的 options，避免共享被库修改的嵌套对象。公式与复杂结构图的实际编辑边界需说明。
- 用异步入口等待 `writeFile` 完成，再检查和渲染文件；交付 JS 与实际使用的资源，保持相对路径可重建。
- PptxGenJS 生成原生对象不等于自动生成入场动画。基本点击出现/淡入用 [基本动画](basic-motion.md) 的后处理脚本，之后检查最终动画文件；不以静态导出替代动态交付。

对于用户提供的 PPTX 模板，`python-pptx` 可做适当的局部修改；保留富文本 run、原媒体和布局，不通过清空整段文本破坏格式。复杂图表、SmartArt、母版和嵌入对象先检查支持情况；不盲目往返重建原稿。

## 数据图表的制作边界

先按 [图表与表格选型](charts-and-tables.md) 决定表达关系，再选实现路线。普通新稿不需要新增绘图库才能开始；已有环境能可靠完成即可，不编写通用图表引擎或复制完整 API 教程。

| 需要 | 合适的实现 | 交付时说明 |
| --- | --- | --- |
| 常规折线、柱/条、饼/环、散点 | PptxGenJS 或已有 python-pptx 支持的原生图表 | 实际类别、系列与嵌入数据可继续编辑；核对导出和数据缓存。 |
| 精确值、配置、消融或决策表 | 原生 PPT 表格；需要时辅以原生标记 | 保持文本、数值和单元可编辑，不把整张表截图。 |
| 热力矩阵、特殊点区间等 | 简单且规模合适时用原生形状/表格，或数据绘图 | 原生形状不等于带“编辑数据”的图表；不要用数百对象勉强模拟复杂图。 |
| 箱线/小提琴、密度、等高线、三维、复杂科学图 | 用已有 Matplotlib 等科学绘图工具由数据确定性生成 | 保留数据/函数与绘图源稿。可用 SVG 等矢量时优先并验证兼容；否则按最终尺寸用清晰 PNG，避免 JPEG 模糊文字。 |

原生图型名称不保证坐标语义正确：普通折线的类别轴可能将不等间隔迭代等距绘制；此时用带连线的 XY 散点等数值横轴实现，检查实际间隔。不能为了坚持某种原生图型而扭曲数据关系。

向 PPT 插入程序生成的图是有效的数据图路线，不是把现成图片充当实验数据；其可编辑边界是“可通过源稿重绘”，不能写成“在 PPT 中原生编辑数据”。不把整页栅格化，标题、解释和来源仍保留原生文本。矢量支持、公式及复杂图形的编辑能力以实际工具和文件为准。

常见图型的演示资源见 [样张](../assets/chart-gallery.pptx)；`scripts/build_chart_gallery.py` 仅负责重建这组示例，使用演示数据，不接管用户任务的数据分析或选型判断。

## 网页路线

Slidev（MIT）适合公式、代码、结构图和网页演示。宿主 AI 写 Markdown、Vue/HTML 与样式，Slidev 不需要自己的模型 API。使用用户的已有 Slidev 项目或在任务目录初始化；先查看当前安装版本的帮助和导出能力。

示例：

```text
npm init slidev@latest
npm install -D playwright-chromium
npm run dev
```

对应项目里通过本地 CLI 导出：

```text
npx slidev export slides.md --format pdf
npx slidev export slides.md --format pptx --with-clicks false
```

普通 PPTX 是整页图片；备注可保留。2026-10-09 的官方文档也列出 `--format pptx-editable`，但先确认本机版本实际支持。它把部分对象还原为原生形状，公式、SVG、canvas 和复杂效果仍可能是图片，某些页面会整页降级。不能仅因扩展名为 `.pptx` 声称全稿可编辑。

检查网页渲染与最终导出的 PPTX 两种结果。动画分步可能增加导出页数；除非用户需要分步副本，显式关闭按点击步骤导出。保持公式、代码和图例在最终静态文件中完整。

如果只有离线网页或 PDF 达到效果，而用户要求 PPTX，继续解决导出；不擅自以链接代替交付。用户接受固定图片式 PPTX 时可以使用该路线，保持精确数据原图及源稿。

## 真实 PPTX 渲染

`scripts/render_pptx.py` 先从实际 PPTX 导出 PDF，再用 `pdftoppm` 生成实际页面 PNG；有 PyMuPDF 时也能栅格化。Pillow 可选，用来做总览图。输出目录须新建或为空，不覆盖用户已有 QA 文件。

`--renderer auto` 为默认：优先使用 LibreOffice；其缺失时，Windows 可使用已安装且能通过 pywin32 调用的 PowerPoint。也可显式选择 `--renderer libreoffice` 或 `--renderer powerpoint`；指定路线失败会准确报错，不自动改用另一条路线。PowerPoint 是已有本地软件的可选路线，不要求用户为此购买或安装 Office；免费环境仍可使用 LibreOffice。

LibreOffice 使用隔离临时配置。PowerPoint 通过 `DispatchEx` 获取 COM 引用，只读且隐藏打开本次文稿，导出包含隐藏页的完整 PDF；只关闭本次打开的文稿。PowerPoint 可能复用已有进程，所以脚本仅在调用前不存在 PowerPoint 进程、且结束时该实例没有其他文稿时退出应用，不修改应用级设置或关闭用户原有进程。COM 调用受桌面 Office 环境影响，`--timeout` 控制外部命令，不是 COM 方法的超时保证。实际放映仍须另行检查。

Windows 安装已有 LibreOffice 时可自动找到，或传 `--soffice`；Poppler 不在 PATH 时传 `--pdftoppm`。首次运行产生新的输入 hash 与页面清单。修改后用新目录渲染，避免旧预览冒充新结果。

清单 `manifest.json` 如实记录实际使用的渲染器、输入文件及导出 PDF/逐页 PNG 的 hash，可继续交给 `finalize.py` 核对。LibreOffice 与 PowerPoint 的字体和部分图表渲染可能不同。留文字余量、选择实际存在的字体；有用户最终展示环境时核对关键页面。渲染转换或字体失败需修复/说明，不能单靠 PPTX 能打开就过关。PowerPoint 导出接口见 [Microsoft 官方说明](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.presentation.exportasfixedformat)。

## 不作为核心依赖的服务

PPTAgent 的审查与导出工作流可参考，但本技能无需另装其完整运行时。Nature-paper2ppt 提供学术叙事与原图追溯参考，不作为必须安装的共享技能。Presenton 本地版可按用户既有环境使用；其云服务或额外云模型并非自动免费。NotebookLM、Gamma、Canva 等生成额度、导出和水印条件会变化，不将它们设为唯一出口。

## 依据与边界

核验日期：2026-10-09。本技能的流程和辅助脚本为独立实现，没有复制 Anthropic 的受限 PPTX 技能代码或第三方技能包。外部项目无需打包进本技能。

- [PptxGenJS](https://github.com/gitbrent/PptxGenJS)：原生 PPTX 制作，MIT。
- [Slidev 导出](https://sli.dev/guide/exporting)：网页与导出格式、图片/原生对象边界。
- [Slidev AI 支持](https://sli.dev/guide/work-with-ai)：官方 skill/MCP 可选，非本技能的强制依赖。
- [PPTAgent skill](https://github.com/icip-cas/PPTAgent/tree/main/skills/pptagent)：源稿审查与最终 PPTX 审查的参考。
- [nature-paper2ppt](https://github.com/yuan1z0825/nature-skills/tree/main/skills/nature-paper2ppt)：中文学术论证、原图和备注的参考。
