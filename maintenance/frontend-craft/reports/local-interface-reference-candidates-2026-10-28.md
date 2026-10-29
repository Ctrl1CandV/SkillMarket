# 多信息、多功能局部界面参考：首批候选与覆盖缺口

来源核对日期：2026-10-28；收集策略修订：2026-10-29。配套 [优化策略与实施摘要](local-interface-upgrade-plan-2026-10-28.md)。

本轮收集 12 组官方产品案例与设计方法，供后续实施选用。以下来源均已核对官方文档或示例说明；未登录操作产品，未完成图片视觉核验，也未验证中文、窄屏与长内容表现。当前属于 documented 候选材料，没有修改运行索引或把它们登记为 verified_visual。

用户进一步明确：原三个 PaperDesk 场景是问题证据，不是实施和验收清单。首批资料因从这些问题出发而偏向 API 与学术阅读；保留其中有价值的方法，后续按信息形态、功能关系和交互复杂度补齐跨业务参考。此清单不是固定模板库，也不直接充当验收题库。

本轮曾尝试查看官方页面画面，但未成功取得可观察截图；访问页面及读取其文字不能代替看图。图片链接是后续采集入口，不是本地已核验资产。下文的借鉴建议是根据来源作出的设计推论。

## 配置对象、依赖与状态：已有 API 类来源

### 01 Open WebUI：连接对象与编辑表单

- 来源：[OpenAI-compatible Connections](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/)、[OpenAI Connections](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai/)。
- 已核对：连接入口、地址和凭据等配置，以及配置后的模型使用关系；文档包含配置图。
- 借鉴：按连接对象组织字段与验证／保存，把管理连接和日常选择模型区分开。
- 后续看图：连接列表、编辑表单、相关状态和主要动作之间的关系；可从 [官方连接配置图](https://docs.openwebui.com/assets/images/manage-openai-e56ceeb637bb0fe62a1ab42c8541a135.png) 入手。
- 限制：单连接示例不覆盖额度、备用服务、联网和恢复同时出现的情况；供应商特例及历史模型名称不可照搬。
- 检索词：connection、provider、API、credentials、settings、actions。

### 02 Dify：供应商、模型与凭据的层次

- 来源：[Model Providers](https://docs.dify.ai/en/cloud/use-dify/workspace/model-providers)。
- 已核对：供应商凭据、模型配置、默认模型与负载均衡的相关说明及图片入口。
- 借鉴：分清服务身份、模型选择和凭据范围，辅助判断多个配置项应属于哪个对象。
- 后续看图：Manage Credentials for a Provider's Models、Custom Model Configuration、Add Credentials for Load Balancing。
- 限制：插件市场、计费与负载均衡属于它的产品能力；没有这些能力时不引入对应层次。
- 检索词：provider、model、credentials、scope、fallback。

### 03 n8n：凭据创建、复用与测试

- 来源：[Create and edit credentials](https://docs.n8n.io/build/understand-workflows/create-and-edit-credentials.md)。
- 已核对：按服务创建凭据、填写对应字段、保存和测试的流程；当前材料以流程说明为主。
- 借鉴：配置凭据与任务中选用凭据分别处理，结果贴近正在处理的连接对象。
- 后续补充：能显示完整凭据表单与失败恢复的官方画面；目前不把此条用于证明整体视觉质量。
- 限制：只有实际执行测试时才能使用“保存并测试”一类动作名称；不改变目标产品既有保存语义。
- 检索词：credentials、reuse、test、validation、workflow。

### 04 Bruno：当前生效配置与继承来源

- 来源：[Environments](https://docs.usebruno.com/variables/environment-variables)、[Authentication](https://docs.usebruno.com/auth/overview)。
- 已核对：环境选择、环境编辑，以及继承身份验证配置的说明与图注。
- 借鉴：把当前生效选择与修改配置区分开；继承值、来源与编辑入口保持清楚。
- 后续看图：Environment Variables location、缺失父环境的警告、Request Auth set to Inherit。
- 限制：只有确有继承和局部覆盖时才采用来源层次，不能为了让面板看起来丰富而新增机制。
- 检索词：environment、inheritance、active-value、override、auth。

## 控件组合与局部容器：辅助判断

### 05 Carbon：表单分组与完整动作区

- 来源：[Forms](https://www.carbondesignsystem.com/building-blocks/core/patterns/forms)、[Button guidelines](https://www.carbondesignsystem.com/building-blocks/core/components/button/guidelines)。
- 已核对：按相关任务组织字段，标签、帮助和输入分工，字段与分组的空间关系，容器表单和页面表单的动作组织。
- 借鉴：先形成字段组和操作范围，再用一致对齐、间距与主次按钮完成整块表单。通栏动作区是可比较的一种方案。
- 后续看图：表单间距、容器动作区、相关按钮成组的例子。
- 限制：Carbon 的贴边、通栏、按钮顺序、字族和尺寸是其系统选择，不作为所有产品的固定规范。
- 检索词：form、grouping、button-group、alignment、density。

### 06 Primer：对话框中的主体与动作页脚

- 来源：[Dialog guidelines](https://primer.style/product/components/dialog/guidelines/)。
- 已核对：页头、主体、可选筛选与页脚的分工，页脚动作对齐及辅助动作处理。
- 借鉴：主体可容纳变化的内容，主要动作保持稳定归属；可与 Carbon 的通栏方案比较。
- 后续看图：右对齐按钮页脚、左侧辅助动作、可滚动主体。
- 限制：对话框适用于有明确完成边界的任务；复杂设置若需要更多空间，不强塞进短弹窗。
- 检索词：dialog、footer、scroll-body、primary-action。

### 07 Ant Design：抽屉内表单与详情预览

- 来源：[Drawer](https://ant.design/components/drawer/)、[Form](https://ant.design/components/form/)。
- 已核对：公开页面提供抽屉表单、提交动作、对象详情预览等演示说明。
- 借鉴：在不丢失宿主上下文的情况下完成一个局部编辑任务；观察标签、字段、提交区的组合。
- 后续看图与操作：Submit form in drawer 和 Preview drawer；中文版本与长标签样本另查。
- 限制：多层抽屉是可用组件能力，不是本轮资料面板应叠加窗口的依据；组件演示不是完整 API 配置方案。
- 检索词：drawer、form、preview、context、Chinese-UI。

## 阅读与 AI 支持面板

### 08 Readwise Reader：文档旁的会话与来源

- 来源：[Chat with your documents](https://docs.readwise.io/reader/guides/ghostreader/chat)、[Global Ghostreader](https://docs.readwise.io/reader/guides/ghostreader/global)。
- 已核对：文档侧栏会话、选中文段作为提问材料、输入附近的模型选择及全库会话中的引用路径。
- 借鉴：让消息流承担主要阅读，材料与模型服务当前提问；区分当前文档和全库检索范围。
- 后续看图：[聊天侧栏](https://docs.readwise.io/images/chat-side-panel.png)、[来源预览](https://docs.readwise.io/images/global-ghostreader_ref-hover.gif)，随后核对长回答与返回阅读。
- 限制：单文档和全库会话的能力不同，不能混写成同一种状态；本轮没有验证实际焦点、位置保持或长回答效果。
- 检索词：reading-chat、source-preview、context、composer、long-answer。

### 09 Zotero：主体阅读与依附材料的辅助工作

- 来源：[PDF Reader](https://www.zotero.org/support/pdf_reader)。
- 已核对：阅读器笔记面板、注释进入笔记时的关联，以及回到 PDF 上下文的定位方式。
- 借鉴：主体阅读、辅助工作与原文定位形成可往返的关系，不把辅助内容处理成脱离材料的独立区域。
- 后续看图：[官方完整阅读器截图](https://www.zotero.org/static/images/blog/6.0/pdf-reader.jpg)，结合文档定位相关状态。
- 限制：PDF 注释与长 AI 对话不同；不据此规定三栏比例、聊天高度或文本密度。
- 检索词：reader、annotation、note-pane、source-return。

### 10 Fluent：并置与覆盖、局部错误与窗口结构

- 来源：[Drawer](https://fluent2.microsoft.design/components/web/react/core/drawer/usage)、[Dialog](https://fluent2.microsoft.design/components/web/react/core/dialog/usage)。
- 已核对：并置／覆盖侧栏、页头／主体／页脚、局部和整体错误，以及长内容下的容器处理。
- 借鉴：依据是否需要对照原内容选择资料展示方式；错误贴近受影响分组，主要动作对应窗口任务。
- 后续看图：Inline / Overlay、Section loading error、Anatomy、长内容状态。
- 限制：组件对短辅助信息的建议不能直接限制长会话；其按钮顺序与 Carbon 不同，应选择适合项目的一致体系。
- 检索词：inline-panel、overlay、error-scope、body-footer、scroll。

## 文献身份、说明与证据

### 11 Semantic Scholar：扫描依据与文献身份

- 来源：[Product](https://webflow.semanticscholar.org/product)。
- 已核对：TLDR、引用操作、Ask This Paper 与支持语句的官方介绍。
- 借鉴：文献身份、判断依据和相邻操作可以有不同分量；列表扫描和深度理解需要不同内容长度。
- 后续看图：搜索结果与论文详情分别观察，避免只看短摘要裁片。
- 限制：TLDR 适合快速扫描，不能据此把导读详情压成一句话；它不能证明完整中文导读或全章节导航的效果。
- 检索词：paper-identity、summary、detail、research-card、citation。

### 12 Elicit：连续解释与证据查阅

- 来源：[Introducing Elicit Reports](https://elicit.com/blog/introducing-elicit-reports)。
- 已核对：官方发布文章中的报告、研究步骤、来源摘录与报告追问说明及图像入口。
- 借鉴：解释保持连贯，出处与支持内容通过可理解的路径核对；辅助查阅不抢占主要论述。
- 后续看图：报告整体、引用摘录与追问之间的关系。
- 限制：2025 年发布示例仅代表当时官方展示；不采纳营销比较作为质量证据，不虚构目标产品尚未具备的段落级核查能力。
- 检索词：explanation、evidence、report、source-detail、follow-up。

## 下一轮采集与入库规则

1. 按“对象与属性、解释与判断、配置依赖、查询比较、多对象操作、动态状态”等关系选例，不按原三个场景配齐数量。已有 API 案例可解释对象与配置范围，阅读案例可解释连续内容与辅助操作；它们都只是局部证据。
2. 补充业务不同、信息较多且功能相互关联的完整界面，重点看内容筛选、分组、操作归属、密度和变化后的整体画面。当前覆盖缺口见下表。
3. 组件规范用于判断语义、对齐和容器关系，产品画面用于观察组合；不从不同来源各摘一个控件拼成缺少共同秩序的窗口。保留多种合理解法及其条件。
4. 每个采用案例记录实际查看的画面、尺寸、状态、日期、可迁移关系与限制。包含长内容、相关错误或选择变化等足以暴露问题的状态；具体采集由任务决定。
5. 确认图像使用条件后再决定是否随技能分发；暂未确认时保留官方链接。外部图、原创样张和维护评测截图分别标明来源。
6. 仅把本次设计确实需要且已说明用途的条目加入运行索引。保留候选来源方便后续实践，但不要求每次任务加载整份目录。

## 后续覆盖缺口

下表是采集方向，尚未宣称已找到或查看对应产品案例。指导案例与最终验收任务保持分离，验收不复刻已收集画面。

| 关系 | 首批资料的局限 | 待补方向 |
| --- | --- | --- |
| 多项配置与条件依赖 | 偏向连接与凭据 | 导出、发布、打印或其他配置随条件变化的局部界面 |
| 丰富对象详情与多动作 | 偏向文献身份和阅读 | 含说明、属性、状态、记录及多项处理动作的业务详情 |
| 查询、比较与结果处理 | 缺少完整组合案例 | 筛选、预览、对比、多选及批量处理相互关联的界面 |
| 混合状态与恢复 | 文档说明多，完整画面少 | 多个状态同时存在、局部失败与恢复后仍保持秩序的区域 |
| 中文及不同内容尺度 | 已核对的来源以英文为主 | 真实中文长短差异、混排、较多信息与有限窗口中的完整组织 |

这些材料提供设计依据，不证明采用后已经改善 PaperDesk，也不代表对第三方产品的当前完整体验进行了评测。
