# 基本原生 PPTX 动画

目标是正常报告中的分步解释：点击显示下一条观点、下一张图、下一步流程。默认用出现；需要柔和进入时用短淡入。标题、背景、页码和必要的上下文在进入页面时就能看到。按内容决定点击数，不给所有装饰逐个加动画，也不默认自动换页。

## 制作方式

正文逐条出现时，将各条拆成独立原生文本框。辅助脚本按对象动画，单个文本框中的多段文字会一起出现；它不实现段落级构建。图表仍为原生图表，作为完整对象进入；它不实现按系列增长。一个步骤里的相关文本、图形、箭头和图注可同时出现。

PptxGenJS 完成布局后，运行 `scripts/animate_pptx.py`。该脚本只用 Python 标准库，在 PPTX 里写入标准动画时间线，不调用 PowerPoint、云模型或付费 API，不把页面变成图片。输入不被覆盖，不涉及的页面、图片、图表和备注保持原样。

先列出当前文件的顶层对象 ID 与文本；不要猜 ID：

```text
python scripts/animate_pptx.py task/deck.pptx --list
```

为需要分步的页面写 `task/motion.json`，示例如下，页码与 ID 替换为真实对象。`steps` 每个内层列表代表一次点击，同一步里的对象同时显示：

```json
{
  "slides": [
    {"page": 2, "effect": "appear", "steps": [[8, 9], [10], [11, 12]]},
    {"page": 3, "effect": "fade", "duration_ms": 300, "steps": [[7], [8, 9]]}
  ]
}
```

```text
python scripts/animate_pptx.py task/deck.pptx --plan task/motion.json --output task/deck-animated.pptx
```

从最终动画文件重新审查与渲染。交付动画文件、源稿、素材及点击计划。支持顶层文本、形状、图片、图表/表格和组合；要分别控制组合内部对象时在制作阶段调整分组。对象 ID 必须唯一，每个对象只在一个出现步骤中使用。已有动画的目标页会被拒绝，避免覆盖用户原有动画；用原制作工具保留或修改其时间线。工具只支持 UTF-8 XML、出现和淡入，不声称提供退场、路径、Morph 或复杂触发功能。

## 检查与边界

结构审查会清点动画与检查对象引用；还需在最终播放软件中进入放映，验证未揭示对象初始隐藏、一次点击只启动下一步、同组对象一起出现、展示完成后可以正常换页、返回和重播行为可用。

在 `qa/review.json` 加入实际放映记录，`pages` 覆盖所有带动画/转场的页面：

```json
{
  "animation_review": {
    "status": "pass",
    "method": "slideshow",
    "player": "实际使用的软件与版本",
    "pages": [2, 3],
    "summary": "实际检查了初始隐藏、点击顺序、同组出现、返回及重播；按真实结果填写。"
  }
}
```

只有导入识别或 XML 检查时不能写 `method: slideshow` 或通过。`finalize.py` 对含动画文件要求放映记录；静态画面通过不能冒充动画已验证。动画支持因 PowerPoint、WPS、Impress 版本而异；准确说明实际测试软件和剩余范围。PDF 是阅读/版面预览，不能代替动态 PPTX；不要用多张静态页代替用户要求的对象动画。

标准依据：[Microsoft PresentationML ShapeTarget](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.shapetarget)、[PowerPoint Effect](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.effect)。另参考了 [pptx-motion-lite](https://github.com/yinzige/pptx-motion-lite) 对原生动画与生成器的分工；本脚本为限定出现/淡入、显式点击计划的独立实现，不依赖或捆绑该技能。
