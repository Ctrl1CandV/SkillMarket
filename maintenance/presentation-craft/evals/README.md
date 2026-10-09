# presentation-craft 评测

本目录只在 dev 分支维护。所有生成文件、渲染、审查记录写到另建的任务目录，不提交缓存或生成成品。示例 JS、热图与点击计划为本项目独立制作；其中数值与图像都是清楚标注的演示数据，不代表研究结果。

## 标准库回归检查

从仓库根目录运行：

```text
python maintenance/presentation-craft/evals/check.py
```

无需 Node、Office 或第三方 Python 包。13 项行为检查覆盖点击分组、实际幻灯片顺序、原始 XML/媒体/图表/备注的保留，错误计划与覆盖拒绝，ZIP 重名/CRC 损坏，以及最终记录的页码、类型、hash、文件完整性和动画放映门槛。

测试在当前可写目录建立临时目录并自动清理；仓库只读时，可在任务目录用绝对路径运行脚本。第二个位置参数可指定待测 `scripts` 目录。合成 PPTX 只包含这些函数需要的结构，图片/PDF 是测试字节，不用于打开或渲染。合成 `pass` 记录只检验核对逻辑，不能当作看图或实际放映的证据。

## 真实六页示例

需已有 PptxGenJS、可用中文字体；渲染另需 LibreOffice 和 pdftoppm 或 PyMuPDF。优先复用宿主运行时，未安装依赖时按运行技能的工具参考处理，不全局安装。

以下从仓库根目录运行，`task` 替换为新的任务输出目录：

```text
node maintenance/presentation-craft/evals/demo.cjs task
python presentation-craft/scripts/audit_pptx.py task/demo.pptx --expected-slides 6 --report task/qa/audit-static.json
python presentation-craft/scripts/animate_pptx.py task/demo.pptx --list
python presentation-craft/scripts/animate_pptx.py task/demo.pptx --plan maintenance/presentation-craft/evals/basic-motion.json --output task/demo-basic-motion.pptx
python presentation-craft/scripts/audit_pptx.py task/demo-basic-motion.pptx --expected-slides 6 --report task/qa/audit-motion.json
python presentation-craft/scripts/render_pptx.py task/demo-basic-motion.pptx --out-dir task/qa/render-01
```

生成器拒绝覆盖已有 `demo.pptx`；不传输出目录时会新建系统临时目录并打印输出路径。示例包含长中文标题、原生图表、图片、表格和每页备注；展示一个配色方向，不是六种主题成品。它使用 Microsoft YaHei；其他平台应换为实际可用的中文字体，再检查真实渲染。

点击计划对应这份源稿：第 2/3/4 页分别 4/2/3 次点击，共 32 个对象入场。修改源稿或更换生成器版本之后，必须先核对实际 ID，再调整计划。当前 PptxGenJS 表格页曾出现与前一对象相同的 ID，示例没有对第 5 页加动画；需要对该页加动画时先在制作工具中修复 ID，并重新审查。

看每页真实渲染图和缩略图，再按运行技能的质量参考写实际检查记录。含动画的文件还需在最终演示软件放映，验证初始隐藏、点击顺序、同组出现、返回与重播。导入识别、PDF/PNG 或本目录的回归测试均不能替代实际放映。
