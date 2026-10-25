# frontend-craft 0.4.1：固定内容与布局下的样式组合

2026-10-25。本轮以用户提供的 `frontend-craft-style-optimization-guide.md` 为思考依据，完整阅读后核对固定版本源码，改写运行规则。目标是让颜色、字形、表面、边缘与光影能够一起选择和局部修订。后续四个独立演示已获用户认可，并按配色相似的反馈做轻量补充；本记录区分规则检查、页面观察、用户评价与尚未验证的泛化收益。

## 基线与范围

- 开始时 dev 为 `3a829383a96b3f859f32a9d1033a3dc3e25332a4`，main 为 `e23291a9f1e9e23374cd405ed209fa391f1ef160`；两边 `frontend-craft/` 相同，版本均为 0.4.0，与指南基线一致。
- 仓库及其父目录、相关子目录未发现适用的 `AGENTS.md`。沿用根 README 和 maintenance README：运行文件进入 main/dev，维护材料只在 dev。原工作区唯一未提交文件是用户指南，保留原样，不加入运行路由。
- 本轮运行修改限于 `SKILL.md`、`references/visual-style.md`、`references/review.md`、`references/exemplars.md`。在现有能力内补足方法并修正约束边界，版本为 0.4.1；没有新增技能、依赖或发布流程。
- 已继承 [0.4 修订](frontend-craft-0.4-diagnosis-2026-10-25.md)：品牌与视觉丰富度、中文实际字体、内容按使用者任务编排、辅助说明按需出现、保存/刷新/连接的真实语义，以及验证按问题收敛。这些不是本轮新建能力。

## 参考核对：源码事实、机制解释、本项目决定

GitHub 来源均读取指南指定的提交，不混用更新版本；网页规范于 2026-10-25 核对。下表中“机制解释”是面向本项目的推断，不是对原项目设计效果的实证结论。仅借鉴方法，未导入外部代码、色板数据库或资产。

| 参考与实际做法 | 机制解释 | 采纳、改写与舍弃 |
| --- | --- | --- |
| [Anthropic frontend-design][anthropic] 的 Design principles / Process / Restraint：从题材、受众与材料选择字体、颜色和重点；紧凑计划包含颜色与字体。默认风格警示同时承认特定 brief 的例外，用户明确方向优先。 | 共同题材减少单项选择互不相干；突出集中有助于主次。 | 0.4 已覆盖，继续继承，不再扩写“独特、高级”要求；不移植固定颜色数量或每次重做计划，也不将其警示描述为无条件禁令。 |
| [Impeccable colorize][colorize] 的 Choose a strategy / Apply at system scale / Contrast and perception：指定冷暖、主导关系、对比与用量；允许中性灰，反对固定比例；彩底次级字从前景或底色推导；色阶两端调色度，透明与暗色另查。 | 颜色先有承载对象和用途，才能避免局部好看、合起来失衡。 | 将角色列表变成实际前景背景配对，加入中性色、面积、透明和深色的局部修法。彩底染色改成有问题时的一种选择；不搬全状态检查、双主题要求、live 变体或后续 polish 工具链。 |
| [UI UX Pro Max 入口][promax-skill] 区分整套系统与单领域检索；[colors.csv][promax-colors] 同列 Primary/On Primary、Card/Card Foreground、Muted/Muted Foreground 等组合，也有 luxury 深色金色、AI 紫青等行业映射。 | 配对数据能避免只换填充而忘记前景；单领域入口有助于控制范围。 | 让主按钮、选中、正文表面和彩色区域按真实用途成对确定，复用已有 token。行业命中只提供候选，不证明品牌适配或对比合格；不引入数据库和搜索程序。 |
| [Taste 入口][taste-skill] 的 restyle 保留布局，redesign 才重组；品牌可保留 palette/type。[palettes.json][taste-palettes] 同时有 bg、surface、ink、muted、accent、accentInk、局部 fields、note 和 seenIn。 | “一组颜色怎样用”比裸色号更能决定面积与注意力；restyle 允许固定骨架下的有效变化。 | 明确纯样式任务入口、限定“仅换颜色不足以比较构图”，用关系说明替代裸色卡。seenIn 只是数据关联，不能冒充我们已观察的页面。 |
| [Taste colour.md][taste-colour] 的 Roles / Proportion / Colour fields / Banned families 有配对方法，也规定背景 70–90%、强调少于 5%，限制色系、渐变与静态阴影。入口另区分 page/app，并允许品牌豁免。 | 面积值得判断，但这些具体比例与排除项属于作者风格；其自述样本站点统计不建立因果效果。 | 保留角色、邻接与面积判断，不采用比例、色系黑名单或材质禁令；不把页面规则概括为它对所有应用的要求，也不移植 inspector 与方向抽选流程。 |
| Oil UI 0.25.0 的 [设计方向][oil-direction] 从产品资产定色，说明底色、强调和派生态；[视觉语言][oil-visual] 让字体、图标、控件、表面与状态共用表达，并要求指出哪个元素与谁有问题。原文也有具体图标尺寸/线宽建议及多方向探索。 | 控件和字体共同决定分量；以可见关系描述缺陷，比泛称“不精致”更能指导修订。 | 采纳光学重量、表面层级、嵌套边缘、光影及相关状态的协同。将“同层一样重”收窄为同层且同等重要时相称；不采用相同数值、固定图标比例或每次跳出品类默认。 |
| Radix [色阶用途][radix-scale] 将背景、状态、边界、实色与文字分配到不同用途，部分明亮实色配深前景；[色板组合][radix-palette] 同时允许纯灰和带色灰，并提醒彩色组件与过强底调可能冲突。文档的特定对比承诺依赖指定色阶、底色及度量。 | 用途决定哪些颜色必须一起判断；色阶保证有条件。 | 采纳实际配对和中性色条件判断，不要求建十二级色阶，不把 APCA 的特定承诺转换成任意配对的 WCAG 保证；改变原色阶后重新核算。 |

另外核对 [WCAG 2.2 文字对比][wcag-text]与[非文字对比][wcag-nontext]：沿用正文和控件识别的底线，明确它们有适用对象和例外，装饰分隔线无需因此普遍加重。非文字对比针对必需的识别信息与相邻颜色，不是要求默认态与悬停态彼此达到 3:1。[MDN oklch()][oklch] 支持分开调整感知明度、色度与色相；工具本身不决定配色是否适合产品。指南中的历史颜色偏好研究本轮没有重新复核，也没有据此增加运行规则或效果断言。

## 规则如何改变具体选择

### 1. 给纯样式精修合法入口

旧版的“仅换颜色不算”对构图比较有用，但未限定范围时可能让模型为了证明设计变化而重排已有页面。现在入口允许内容和布局已定的任务直接进入样式与复看；参考保留新建时的构图判断，纯样式修改保护分区、主要间距、内容与操作语义。字体可调整，但断行、体量和控件高度的必要适配要识别，不能隐含重做整页或把几何收益归为颜色收益。

### 2. 将颜色角色连接成搭配过程

旧版已有角色、面积、品牌和对比原则，本轮没有再增一套色板。改写为整页先看大表面与素材，局部问题直接看相邻关系；随后对真实存在的正文、操作、选中、链接/焦点和彩色区域确定前景与背景。

这样模型不止决定“用绿色”，还要判断亮底是否适合白字、选中底是否把主要动作淹没、弱字是否在彩底和透明叠加后失衡。冷暖混合、大色面、高色度和中性灰都保留选择空间；发生冲突时调整相关角色，不全局去色。状态语义由项目惯例与额外线索保持，原来“语义色不和主色混用”的绝对表述也改为可辨识要求，避免绿色品牌不能表达成功之类的误读。

### 3. 将字体、边缘和光影放回同一画面

“同样线宽”改为在实际尺寸下协调图标与文字的光学重量；不要求所有字重、圆角或阴影值相同。普通表面、嵌入区和浮层按已有层级判断，边线、阴影、高光可以组合，但要定位是否重复加重同一个边界。材质可精细也可鲜明，差异应与角色、层级或表现意图有关。

同一控件的相关状态一起处理，避免默认态协调、交互后出现另一套组件库效果。规则限于本次涉及的状态，没有新增完整状态矩阵、动画或暗色主题要求。

### 4. 将审美反馈变成待核实的关系问题

review 保留整体判断，增加少量高频线索：灰蒙检查关键角色是否过近，刺眼检查强刺激叠加，拼装感检查冷暖/字形/边缘/光影，厚重或操作后混乱检查层级与状态来源。它们是候选解释，不能直接当病因。修订描述落到元素、相邻对象、改动变量与预期结果；改后回到整页看主次。

### 5. 正例只解释已有观察

`exemplars.md` 沿用 0.4.0 已有的 reader/mail 观察记录，仅补关系解读与迁移边界：书页正文和页边批注分工；邮件浅底选中、橙色动作/星标和未读圆点各有用途。没有新增色值、材质、阴影或当前视觉质量断言，没有新增假设页面。将“强调色用得很少”这种容易被泛化的结论改为角色分工，保留原有布局与功能分析。

本轮尝试重新打开 reader 原站，但浏览器调用超时，未获得可用画面；没有把尝试写成观察成功，也没有用文字介绍推断新的视觉细节。现有范例解释不是对外站当前版本的重新验收。

## 未采用与保留的边界

- 不移入指南全文、整张诊断表、指南中的四个完整假设场景或完整来源分析。运行主入口只增加范围与路由，搭配细节仍按需读取；完整取舍留在本文件。
- 不采用统一低饱和、固定颜色比例、行业色相映射、通用风格黑名单、全部灰染色、固定色阶级数或 CSS 同值。它们会在解决组合问题时再次削弱已有身份与表达。
- 不为每个局部任务重定品牌、重做构图、重造控件或新增材质。已有方向可成立，重点是补足它内部的配对与分量。
- 不移植外部检索/变体/检查器工程，不默认新建 demo、全状态矩阵、双主题或跨模型评测。本轮没有需要靠真实改版区分的具体竞争解释。
- 不修改中文排版、内容编排和场景参考；设计理由仍放在开发记录，不能进入普通使用者页面。

## 检查与交付状态

- **来源核对**：上述固定提交的关键原文、色板字段及适用条件已核对；区分原文事实、机制推断和本项目规则，未采用第三方效果自述作为证明。
- **规则一致性**：完成一次独立只读审查，修正主流程中无条件“窄屏重排”的范围歧义，并把字体变化的效果归因说明集中在 review，减少重复。以“保留饱和蓝侧栏的局部精修”和“中文换字形使控件变高”两个假设任务做纸面推演，未发现必须改品牌、扩张状态矩阵或拒绝必要适配的冲突；这不是实际生成试验。
- **首轮结构与链接**：当时 `quick_validate.py`（UTF-8 模式）通过；8 份运行文档与3份本轮维护文档共47个相对链接目标存在，来源引用标签完整。`git diff --check` 通过，无范围外修改。这是首轮检查口径，后续新增演示另检。
- **按需加载**：主入口只增加范围和路由；样式增量集中在按需加载的 visual-style，review 和 exemplars 仅补对应诊断与解释。最后的搭配起点也放在 visual-style，没有将用户指南或评审记录加入运行入口。
- **早期样式示意**：[并排样式示意](../evals/style-pair-2026-10-25/index.html)由主 agent 手工编排，共用内容和布局，不是两版 Skill 独立生成。该页的 `file:` 浏览器检查被安全策略拒绝，未绕过；用户直接查看后认为收益不明显、颜色不自然并质疑刻意制造对比。保留此文件作为反馈对象，不把它作为新版有效的证据。
- **后续独立页面**：按用户新请求制作[四种页面](../evals/current-skill-showcase-2026-10-25/index.html)，任务、音乐、城市杂志与灯具商品各有独立内容和风格方向；制作方式与检查详见[记录](../evals/current-skill-showcase-2026-10-25/README.md)。这批新文件通过仅本机访问的预览服务完成真实浏览器检查：桌面首屏、390px 窄屏及四类主要交互。没有重新检查早期被拒绝的页面，也没有完成全部状态或完整业务流程测试。

## 最终反馈与轻量补充

用户认可后续四页的整体设计，指出任务、城市杂志、灯具页的配色有些雷同，授权简单增加搭配风格后同步两分支。保持已认可页面和原有品牌、内容、交互规则；只在颜色小节补开放方向下的选择方法与四种假设搭配起点：冷白/钴蓝、墨色/冰青、浅粉/莓红、明黄/墨紫。

这些起点分别改变底调、明暗与色面使用，并连接正文、动作、选中、字形和边缘；没有固定色值、颜色比例、行业映射或抽签式选风格。独立项目可比较不同方向，同一产品保持一致；适合内容的相同组合仍可保留。另澄清保护已认可的视觉身份不等于冻结历史 token 的具体取值。

独立复核据此收窄了“不能只换强调色”的绝对措辞，避免把暖白、灰绿反过来列为禁用项。四种搭配明确标为假设，不冒充观察过的页面；没有再做 demo 或调整已获认可的四页。用户认可限于本次样例，新增搭配规则的实际生成效果尚未单独验证。

最终文本检查：系统 Python 的 `quick_validate.py`（UTF-8 模式）通过；本轮范围内 12 份 Markdown 的 59 个相对链接均可解析，6 个 HTML 的资源、锚点、重复 ID 与内联脚本语法检查通过，`git diff --check` 通过。内置 Python 缺少 PyYAML，改用已有的系统 Python 完成验证，未为此安装依赖。没有把这些结果记为新增搭配的视觉验证。

交付按既有分支约定：四个运行文件进入 main/dev；本记录、两组演示和维护索引只进入 dev。保留供用户评审的 HTML、入口缩略图与已交付总览截图，没有额外测试脚本或运行缓存入库；用户原始指南保持本地原样，不纳入提交。此次不执行安装、打包或打标签。

运行提交：dev `97a9ea0`，main `6e85277`，标题均为 `10.25 frontend-craft 0.4.1：补强样式组合与配色方向`；通过独立运行提交整合，已核对两分支的 `frontend-craft/` 树相同。维护记录另作 dev 提交。

[anthropic]: https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/frontend-design/SKILL.md
[colorize]: https://github.com/pbakaus/impeccable/blob/936867543ac2576920d663cc9803597f6044f3ac/skill/reference/colorize.md
[promax-skill]: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/d14efff8ed1faa4187f004f79926f428c8074ec7/.claude/skills/ui-ux-pro-max/SKILL.md
[promax-colors]: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/d14efff8ed1faa4187f004f79926f428c8074ec7/.claude/skills/ui-ux-pro-max/data/colors.csv
[taste-skill]: https://github.com/Leonxlnx/taste-skill/blob/12af471f627f866411b4bd785b19646d3672784c/skills/taste-skill/SKILL.md
[taste-palettes]: https://github.com/Leonxlnx/taste-skill/blob/12af471f627f866411b4bd785b19646d3672784c/skills/taste-skill/library/palettes.json
[taste-colour]: https://github.com/Leonxlnx/taste-skill/blob/12af471f627f866411b4bd785b19646d3672784c/skills/taste-skill/references/colour.md
[oil-direction]: https://github.com/oil-oil/oil-ui/blob/ff3ed0a88972747840ece9d4cd664807d6f5d501/references/design-direction.md
[oil-visual]: https://github.com/oil-oil/oil-ui/blob/ff3ed0a88972747840ece9d4cd664807d6f5d501/references/visual-language.md
[radix-scale]: https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale
[radix-palette]: https://www.radix-ui.com/colors/docs/palette-composition/composing-a-palette
[wcag-text]: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
[wcag-nontext]: https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html
[oklch]: https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/color_value/oklch
