# 范例索引

本索引用于按任务选择参考，不是行业模板菜单。实际查看方式和状态含义见[参考选用](reference-selection.md)；可检索条目在[exemplar-index.json](exemplar-index.json)。

Tufte CSS、Tabler、PhotoSwipe 与 Wikipedia 的六个原始页面状态已实际采集并逐张查看，标为 `verified_visual`。Oil UI 条目仍为 `candidate`；其旧版页面及画面再分发范围尚未确认。Linear、Carbon 与 Letterform 的方法资料保持 `documented`。可运行的原创候选另见[样式样张](style-samples.md)。

2026-10-29 增补的局部界面来源均为 `documented`：已核对官方文字与图像入口，没有实际看图、产品操作或本地截图包。按下表选择当前需要的关系，不默认加载全部来源。

## 已核验的本地画面

| 原始页面与本地图 | 实际观察的关系 | 迁移边界 |
| --- | --- | --- |
| [Tufte CSS 旁注章节](https://edwardtufte.github.io/tufte-css/#sidenotes) · [完整视口](../assets/references/tufte-css/desktop.jpg) | 连续正文、较小编号旁注、标题与代码保持同一阅读面 | 英文及一条短旁注，不能证明长 AI 解读或完整证据核验；中文和窄屏需另作判断 |
| [Wikipedia 正文引用](https://en.wikipedia.org/wiki/Attention_Is_All_You_Need#Attention_with_seq2seq) · [完整视口](../assets/references/wikipedia-attention/body-citation.jpg) | 连续正文中的轻量 [21] 编号连接具体来源 | 英文百科的来源定位，不代表已核验科学结论，也没有验证长 AI 解读 |
| [Wikipedia 来源定位](https://en.wikipedia.org/wiki/Attention_Is_All_You_Need#cite_note-:22-23) · [完整视口](../assets/references/wikipedia-attention/source-location.jpg) | 实际点击正文 [21] 后对应书目高亮；第一个回链实际回到第一次引用 | 返回目标贴近视口顶边，迁移时应保留上下文；不照搬三栏、书目双栏或英文尺度 |
| [Tabler DataTables](https://preview.tabler.io/datatables.html#content) · [完整视口](../assets/references/tabler/desktop.jpg) | 实际执行 Name 升序；连续表格、列对齐、低权重分隔与进度强调支撑密集比较 | 锚点已滚过站点导航；只验证排序，长中文、筛选、错误和窄屏尚未验证 |
| [PhotoSwipe 官方画廊](https://photoswipe.com/) · [完整视口](../assets/references/photoswipe/gallery.jpg) | 大竖图与四张横图分配观看次序，细缝、标题及署名衬托照片 | 组件展示页，非完整档案产品；预览裁切不能替代原图查看 |
| [PhotoSwipe 第一图灯箱](https://photoswipe.com/) · [完整视口](../assets/references/photoswipe/lightbox.jpg) | 实际打开第一图；保留照片比例，外围轻量控件与暗背景突出内容 | 与画廊属同一来源；只验证打开，不据此声称已全面测试灯箱行为 |

六图采集于 2026-10-26，CSS 视口均经 DOM 核对为 1440×1000；截图工具保存的原始 JPEG 均为 1425×990，未经改图。Tufte CSS、Tabler、PhotoSwipe、Wikipedia 是四个独立发布主体。前三者的完整 MIT 文本随图保留；Wikipedia 文字的 CC BY-SA 4.0、作者历史、标识使用及截图范围见 [Wikipedia 归属说明](../assets/references/wikipedia-attention/ATTRIBUTION.md)。摄影授权单独见 [PhotoSwipe 归属与素材范围](../assets/references/photoswipe/ATTRIBUTION.md)。机器索引含具体来源、状态、方法与观察限制。Tufte 只补充阅读与短旁注关系，证据来源定位由 Wikipedia 的两个状态支持。

## 优先按关系选

| 条目 | 适合研究的关系 | 使用边界 |
| --- | --- | --- |
| [Oil UI reader](https://ui.oiloil.org/works/reader/live/index.html) | 连续正文、页边批注与阅读工具的分工 | 不把深底、宋体、书签丝带当成阅读页必选样式 |
| [Oil UI minutes](https://ui.oiloil.org/works/minutes/live/index.html) | 整理结果与原始依据互相定位 | 真实依据更长或需跨段核对时重定空间与定位方式 |
| [Oil UI mail](https://ui.oiloil.org/works/mail/live/index.html) | 对象列表、选中关系、阅读与回复工作区 | 不把三栏和橙色强调当作工具页通用答案 |
| [Linear 界面改版说明](https://linear.app/now/behind-the-latest-design-refresh) | 丰富信息中的任务主次、导航与主要工作区权重 | 参考其判断及官方画面，不假装查看了登录后的全部产品 |
| [Carbon 排版策略](https://www.carbondesignsystem.com/building-blocks/foundations/typography/style-strategies) | 同一产品中不同区域的文字尺度和表达节奏 | 不直接移植 IBM 的字族、字号或身份 |
| [Carbon 网格](https://www.carbondesignsystem.com/building-blocks/foundations/2x-grid/overview) | 看更多条目与看每条更多内容的空间选择 | 网格数值属于原设计系统；这里只学习布局决策 |
| [Letterform Archive 档案设计](https://letterformarchive.org/news/designing-the-online-archive/) | 素材原貌、检索与档案内容的关系 | 不把作品图像丰富度当作所有工具都需要大图的证据 |
| [Oil UI folio](https://ui.oiloil.org/works/folio/live/index.html) | 作品比例、观看顺序和文字辅助关系 | 无真实作品素材时不能只复制空网格证明设计成立 |

## 局部信息、动作与状态

同样包含十多项内容的区域，可能需要配置作用域、共同查看或分步提交等不同关系。先匹配内容形态、动作后果与容器条件，再选来源；组件规范辅助组织，不替代完整产品画面。

| 关系与来源（2026-10-29 文档核验） | 适合研究的组合 | 迁移边界 |
| --- | --- | --- |
| [Open WebUI 连接](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/) | 连接列表到编辑窗口；地址、凭据、模型、启停与验证/保存归属同一连接 | 供应商特例及模型发现行为不可照搬；不是所有配置均应常驻 |
| [Dify 模型供应商](https://docs.dify.ai/en/cloud/use-dify/workspace/model-providers) | 供应商共享凭据、单模型凭据、默认模型分层组织 | 没有相应能力时不引入插件、计费或负载均衡层次 |
| [Bruno 继承身份验证](https://docs.usebruno.com/auth/overview) | 有效值、只读状态、来源说明与编辑来源入口同处一个局部区域 | 查看来源不改变继承模式；无继承关系时无需套层级 |
| [VS Code 设置编辑器](https://code.visualstudio.com/docs/configure/settings) | 分类与搜索、作用域、多类输入、改动标记和单项重置共同工作 | 即时生效与提交草稿不同；不复制全部作用域或默认窗口形态 |
| [GitHub PR 审查](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/reviewing-proposed-changes-in-a-pull-request) | 背景链接、逐文件内容、查看进度、待提交评论与最终决定分工 | 只学习局部状态与整体动作关系，不把 diff、折叠或审查机制套给其他业务 |
| [Readwise 文档会话](https://docs.readwise.io/reader/guides/ghostreader/chat) | 主体阅读与会话；选段材料、模型选择、保存回答依附各自操作 | 单文档与全库模式分开判断；未验证长回答、焦点或返回位置 |
| [Zotero 阅读与笔记](https://www.zotero.org/support/pdf_reader) | 正文、注释列表、可编辑笔记及返回来源的关联 | PDF 注释不等于长会话；不预设三栏比例 |
| [Carbon 表单](https://www.carbondesignsystem.com/building-blocks/core/patterns/forms) | 相关字段、组间距、标签与完整动作区；容器内通栏动作组是一种选择 | 贴边、顺序和尺寸属于其系统，不作为通用按钮规范 |
| [Primer 对话框](https://primer.style/product/components/dialog/guidelines/) | 筛选区、滚动主体与右对齐动作页脚；适合有明确结束点的任务 | 不能把整页强塞进弹窗；与 Carbon 是不同整体方案，不逐控件拼贴 |
| [Fluent 抽屉](https://fluent2.microsoft.design/components/web/react/core/drawer/usage) | 并置或覆盖的选择、局部与整体错误、受影响区域的恢复 | 短辅助任务的步数和遮罩建议不直接限制长内容 |

这些条目记录的是来源明确描述的关系；中文长标签、真实数量、组合错误与窗口变化仍需在当前工程验证。图像使用条件尚未核实，不随技能分发外部图片。

## 已有描述与方法依据

### 连续阅读与旁注

reader 的已有说明体现了正文与批注的分工：正文保持连续，旁注通过位置和颜色与正文关联。借鉴前先核对原页面当前画面；当前项目可能是 PDF、长回答或可编辑文档，版心、工具与注释密度都需重新判断。

### 结论与原始依据

minutes 的已有说明使用对应编号连接摘要与转写。可借鉴的是整理内容可追溯，而不是所有证据都要常驻一整栏。以实际的段落长度、引用密度与核查任务决定共同可见的范围。

### 密集工作界面的权重

Linear 官方改版说明讨论在保留信息密度的同时，让导航等支持元素退后、主要工作内容保持突出。该文章包含可核对的前后画面；只继承已经查看并解释清楚的关系，不从一张宣传裁图推断完整交互。

### 文字、网格与作品

Carbon 的资料可以帮助判断同一系统里哪些区域紧凑、哪些需要更舒展的阅读。档案与作品类案例则适合观察素材比例和观看顺序。它们与工具界面的任务不同，选择时核对可用素材、真实文本和交互范围。

## 增补方式

先补足当前任务需要的覆盖，不按数量囤图。一个有完整视口、必要细部、任务状态和迁移说明的案例，比多个只剩小缩略图的网页更有用。将截图与来源信息核实后再更新索引状态；只有文字核验的条目保持 `documented`。

参考库保持来源和表达的多样性，不让一种图库、同一浅色骨架或一个品牌占据全部默认起点。运行任务只加载选中的少量条目。采集与评测记录留在仓库维护目录，技能内保留使用这些参考所需的简短信息与资产。
