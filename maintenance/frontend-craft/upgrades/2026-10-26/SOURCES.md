# 来源、借鉴与边界

本轮以用户的两套技能、前面讨论和以下一手资料为依据，重新组织成当前任务的规则。采用的是有适用条件的经验与方法，没有整体复制第三方技能、网页、字体或素材。本表不是质量排名，也没有用星数或安装量证明视觉效果。

## 用户仓库与基线

- [仓库](https://github.com/Ctrl1CandV/SkillMarket)。
- [固定基线 README](https://github.com/Ctrl1CandV/SkillMarket/blob/d4c9eadcaa8f7ba287c3cd7f61a26775552eaf11/README.md)：main/dev 与 maintenance 的分工。
- [旧 frontend-craft](https://github.com/Ctrl1CandV/SkillMarket/blob/d4c9eadcaa8f7ba287c3cd7f61a26775552eaf11/frontend-craft/SKILL.md)。
- [旧 product-design](https://github.com/Ctrl1CandV/SkillMarket/blob/d4c9eadcaa8f7ba287c3cd7f61a26775552eaf11/product-design/SKILL.md)。

包内 baseline 是上述提交的 12 个技能文件快照。后续用户仓库可能继续变化；合并时以实际文件差异为准。

## 开源技能与可复用工作方法

| 来源 | 本轮吸收什么 | 明确限制 |
| --- | --- | --- |
| [Anthropic frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) | 先形成完整表现方向，再联动字体、空间、颜色与细节；避免只修局部 | 不把大胆、新奇、强品牌表达规定为每个工具或阅读界面的目标；通用字体和成熟控件可合理使用 |
| [Impeccable：Designing](https://impeccable.style/designing/) 与 [Context](https://impeccable.style/docs/context/) | 从上下文选择方向，分开理解问题、设计与精修，按实际视觉问题迭代 | 不把完整命令体系或每项检查复制成日常必走流程；不凭工具名称声称效果已验证 |
| [Impeccable 技能源文件](https://github.com/pbakaus/impeccable/blob/main/skill/SKILL.src.md) | 对视觉判断提供具体正向指导与情境说明 | 当前实现仍需用自己的目标任务验收 |
| [Taste skill](https://github.com/Leonxlnx/taste-skill/blob/main/skills/taste-skill/SKILL.md) 与 [研究记录](https://github.com/Leonxlnx/taste-skill/blob/main/skills/taste-skill/references/research.md) | 关注默认输出惯性；用具体设计决定而非模糊形容词引导 | 作者的小规模模型评审不等于大众用户研究；不移植风格强制项或把通过规则当成美感 |
| [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/README.md) | 结构化组织样式、色彩、字体、场景资源，方便按需检索 | 不按行业名称机械确定调色板；数量多不等于每条都经过适用性核验 |

## 构图、内容与任务关系

| 来源 | 本轮吸收什么 | 明确限制 |
| --- | --- | --- |
| [Priority guides](https://alistapart.com/article/priority-guides-a-content-first-alternative-to-wireframes/)（Heleen van Nues、Lennart Overkamp） | 用用户需要和真实内容确定优先关系，布局不先绑在组件骨架上 | 优先级不等于所有重要内容一律置顶；本轮继续补视觉尺度与行为关系 |
| [Object-Oriented UX](https://alistapart.com/article/object-oriented-ux/) | 对象、内容和动作一起理解，入口以用户认识的对象为基础 | 不把后台实体逐个变成导航，也不以对象方法替代实际任务 |
| [Every Layout](https://every-layout.dev/layouts/) 与 [Axioms](https://every-layout.dev/rudiments/axioms/) | 可组合布局原语、内容约束与自然重排 | 原语解决实现关系，不自动产生完整构图与视觉质量 |
| [Carbon 2x Grid](https://www.carbondesignsystem.com/building-blocks/foundations/2x-grid/overview) | 关键对齐线、节奏，以及宽度增加时“更多条目/每条更多内容”的选择 | 不把 IBM 的尺寸体系规定为所有产品通用值 |
| [Android canonical layouts](https://developer.android.com/develop/adaptive-apps/guides/canonical-layouts?hl=en) | 区分列表—详情和主体—支持区；窗口变化保持任务关系 | 迁移关系，不移植 Android 组件或平台限定 |
| [Refactoring UI：Labels](https://refactoringui.com/previews/labels-are-a-last-resort) | 标签和值按任务分配权重，注意需要强调标签的例外 | 不归纳成所有标签都该弱化；输入与可访问名称要保留 |
| [Linear 改版说明](https://linear.app/now/behind-the-latest-design-refresh) | 保留有效密度，通过导航权重、表面、边界与图标改善整体关系 | 这是作者方法说明；当前本包未附已核验的完整本地画面，不能据此声称看过所有工作状态 |
| [Letterform Archive 在线档案设计](https://letterformarchive.org/news/designing-the-online-archive/) | 内容图像作为主体，考虑浏览与观看的关系 | 不把图像丰富的档案布局直接当成长文工具模板 |

## 文字、颜色与行为

| 来源 | 本轮吸收什么 | 明确限制 |
| --- | --- | --- |
| [Carbon typography](https://www.carbondesignsystem.com/building-blocks/foundations/typography/style-strategies) | 文字角色、信息密度与表现强度共同决定 | 不规定全站只能使用一种尺度，也不固定其字族 |
| [W3C 中文排版需求](https://www.w3.org/TR/clreq/) | 字形、行长、混排、断行与标点关系 | 书刊经验需按网页和目标环境调整 |
| [W3C 字体映射](https://w3c.github.io/clreq/others/system-font-mappings.html) | 区分系统内置、可选与依赖字体包的资源 | 表中候选不等于用户设备保证安装 |
| [CSS Fonts](https://www.w3.org/TR/css-fonts-4/#font-style-prop) | 区分真实字面和合成效果 | 实际字体与浏览器仍须核对 |
| [MDN text-autospace](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/text-autospace)、[text-spacing-trim](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/text-spacing-trim) | 作为混排与标点的渐进增强参考 | 不将暂时的支持状态永久写成技能结论 |
| [Radix 色阶](https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale) 与 [调色板组合](https://www.radix-ui.com/colors/docs/palette-composition/composing-a-palette) | 按背景、边界、交互与文字角色组织色彩，并考虑邻接与状态 | 本包原创样张不是 Radix 官方色板复制；颜色角色有效不代表整屏已经协调 |
| [Carbon motion](https://www.carbondesignsystem.com/building-blocks/foundations/motion/overview) | 动效服务于操作、关系和状态理解 | 不为安静的阅读过程强加表现动画 |
| [Vercel Web Interface Guidelines](https://vercel.com/design/guidelines) | 焦点、布局稳定、加载和操作过程也进入完成度检查 | 按当前任务采用，避免不加判断地复制全部建议 |
| [v0 Screenshots](https://v0.app/docs/screenshots) | 图像可给实现提供比抽象词更具体的视觉信息 | 输入截图不保证复现质量，更不保证适用于不同内容与任务 |

## 沿用但仍待重新核验的候选

旧版已有 [Oil UI](https://github.com/oil-oil/oil-ui) 的 [Reader](https://ui.oiloil.org/works/reader/live/index.html)、[Minutes](https://ui.oiloil.org/works/minutes/live/index.html)、[Mail](https://ui.oiloil.org/works/mail/live/index.html)、[Folio](https://ui.oiloil.org/works/folio/live/index.html) 描述。本轮保留发现入口与待观察关系，索引为 candidate；没有把这些继承描述写成已经重新查看的画面，也没有打包未经核对的截图。

## 2026-10-26 项目环境补全

实际仓库已补入 Tufte CSS 连续正文与旁注、Tabler DataTables 排序状态、PhotoSwipe 首页画廊与首图灯箱，以及 Wikipedia 正文引用和来源定位六个原始视口，来自四个独立发布主体。完整来源、许可、观察和迁移限制见 [采集记录](evidence/references/README.md) 与运行技能的 [范例索引](../../../../frontend-craft/references/exemplar-index.json)。上述 Linear 等方法资料仍没有对应本地截图，保留原状态；Oil 旧条目未被冒充为已重新核验。

Tufte 和 Tabler 随图保留原仓库 MIT；PhotoSwipe 的界面代码 MIT 与 Luca Bravo 摄影的 Unsplash 许可分别记录。Wikipedia 的 CC BY-SA 4.0 文字、作者历史和页脚标识的说明性使用分别记载。代码或文字许可没有扩展到其他未核验品牌、图像或被引论文。原创 style-lab 仍与外部参考分开。Wikipedia 为六次配对构建冻结后的资源补证；Distill 未取得合格画面，仅留维护研究，不计入运行图库。

## 本包原创内容（原始交付说明）

两套候选技能的本轮改写、style-lab 实现和评测 fixture 为本轮产生的内容。样张与 fixture 中的研究、数字、项目和展品为明确标注的演示，不属于外部参考来源或真实科学证据。样张不加载第三方字体、不含外部截图资产。

对外发布时沿用仓库所有者实际选择的许可政策；本包不替用户为第三方资料创设授权。后续采集素材须保留其真实来源与使用条件。main 分支链接随时间变化，未来维护以当时原文为准；本文件只说明本轮的借鉴关系。

