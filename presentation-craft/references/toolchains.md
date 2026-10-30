# 免费工具与运行

## 依赖选择

宿主提供文档/幻灯片运行时或依赖加载入口时，优先使用它返回的 Node、Python 与包目录；没有时使用已有环境或任务内依赖。不要将某台机器的绝对路径写进源稿或技能。

`scripts/doctor.py` 报告当前 Node、PptxGenJS、Python-PPTX、LibreOffice 和 PDF 栅格工具的可用性。缺失的可选引擎不意味着所有路线失败。它不安装软件、不访问模型服务、不证明生成效果。

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

`scripts/render_pptx.py` 用 LibreOffice 转 PDF，再用 `pdftoppm` 生成实际页面 PNG；有 PyMuPDF 时也能栅格化。Pillow 可选，用来做总览图。它使用隔离的临时配置和新输出目录，不覆盖用户已有 QA 文件。

Windows 安装已有 LibreOffice 时可自动找到，或传 `--soffice`；Poppler 不在 PATH 时传 `--pdftoppm`。首次运行产生新的输入 hash 与页面清单。修改后用新目录渲染，避免旧预览冒充新结果。

LibreOffice 与 PowerPoint 的字体和部分图表渲染可能不同。留文字余量、选择实际存在的字体；有用户最终展示环境时核对关键页面。渲染转换或字体失败需修复/说明，不能单靠 PPTX 能打开就过关。

## 不作为核心依赖的服务

PPTAgent 的审查与导出工作流可参考，但本技能无需另装其完整运行时。Nature-paper2ppt 提供学术叙事与原图追溯参考，不作为必须安装的共享技能。Presenton 本地版可按用户既有环境使用；其云服务或额外云模型并非自动免费。NotebookLM、Gamma、Canva 等生成额度、导出和水印条件会变化，不将它们设为唯一出口。

## 依据与边界

核验日期：2026-10-09。本技能的流程和辅助脚本为独立实现，没有复制 Anthropic 的受限 PPTX 技能代码或第三方技能包。外部项目无需打包进本技能。

- [PptxGenJS](https://github.com/gitbrent/PptxGenJS)：原生 PPTX 制作，MIT。
- [Slidev 导出](https://sli.dev/guide/exporting)：网页与导出格式、图片/原生对象边界。
- [Slidev AI 支持](https://sli.dev/guide/work-with-ai)：官方 skill/MCP 可选，非本技能的强制依赖。
- [PPTAgent skill](https://github.com/icip-cas/PPTAgent/tree/main/skills/pptagent)：源稿审查与最终 PPTX 审查的参考。
- [nature-paper2ppt](https://github.com/yuan1z0825/nature-skills/tree/main/skills/nature-paper2ppt)：中文学术论证、原图和备注的参考。
