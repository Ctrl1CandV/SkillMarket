# frontend-craft：布局优先的调研与优化方案

日期：2026-10-03。本轮只研究，不修改运行技能、不制作新页面。用户的核心判断是：给定内容后，分组、位置、比例、留白和阅读顺序先于样式配色。

## 结论

把当前并列的“构图、字体、颜色、素材”要求改成有先后的设计判断：理解内容关系，选择空间结构，用真实内容检验，再完善视觉样式。不是新增一套强制网格、固定比例或禁止卡片规则。布局正确也不自动等于美观，还需比例、节奏、字体及整体完成度的观图判断。

## 来源与证据层次

### 官方设计指导（本轮查阅正文）

- NN/g 邻近：https://www.nngroup.com/articles/gestalt-proximity/ 。相近表示关联；错误分组会误导操作；响应式堆叠可能拆散关联。
- NN/g 视觉层级：https://www.nngroup.com/articles/visual-hierarchy-ux-definition/ 。尺寸、对比与分组共同表达重要性。其经验数值不作为通用强制上限。
- NN/g F形扫描：https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/ 。特定阅读条件下观察到的模式，不是所有页面应照画的布局模板。
- Carbon 间距：https://carbondesignsystem.com/guidelines/spacing/overview 。用一致间距体系表达关系、层级与密度；借机制，不强制其全部数值或CSS写法。
- Carbon 网格：https://carbondesignsystem.com/guidelines/2x-grid/overview 。流式、固定、混合网格解决不同内容问题；不要把列数当作设计起点。
- Apple HIG：https://developer.apple.com/design/human-interface-guidelines/layout 。按内容重要性组织；对齐、留白、容器、缩进表达关系；适应文字与可用空间。页面正文经官方JSON接口查阅。
- Android 自适应布局：https://developer.android.com/develop/ui/compose/layouts/adaptive/canonical-layouts ，https://developer.android.com/develop/ui/compose/layouts/adaptive/use-window-size-classes 。列表详情、主辅、信息流是内容关系的实现；窗口变化需要保持任务状态。原生dp数值不直接当Web断点。
- Microsoft：https://learn.microsoft.com/en-us/windows/apps/design/layout/page-layout （访问重定向至应用轮廓内容）。导航轮廓与边距服务内容类型，不是所有应用同一侧栏。

### 开源实现（源码证据，不是视觉评级）

1. oil-ui 本轮核验 7040c40d331ca7c0b8500f5b51ee2e525f088f12，0.14.0，区别于前次0.11.0。
   https://github.com/oil-oil/oil-ui/tree/7040c40d331ca7c0b8500f5b51ee2e525f088f12
   重点读取 references/design-direction.md、layout-and-viewport.md：比较结构而非只换皮，核对视口、主区域比例与对齐线。保留这些机制，不继承固定候选数、分栏次数或强调色面积配额；未读取付费内容。公开展示的版本/模型标签不能证明由此固定源码单独产生效果。
2. Outline：478e8121cbe517b9d7773e9d68d20bfe26056c59。
   https://github.com/outline/outline/blob/478e8121cbe517b9d7773e9d68d20bfe26056c59/app/components/Layout.tsx
   https://github.com/outline/outline/blob/478e8121cbe517b9d7773e9d68d20bfe26056c59/app/scenes/Document/components/Document.tsx
   侧栏宽度与内容区协同；目录和正文分工；小窗口改变侧栏呈现方式。可借正文宽度预算与辅助栏退出机制，不照抄负偏移、52em或状态管理。
3. Actual Budget：821caa264304b391f62216e4affa1ee5e6dc5410。
   https://github.com/actualbudget/actual/blob/821caa264304b391f62216e4affa1ee5e6dc5410/packages/desktop-client/src/components/Page.tsx
   存在专门的移动页面结构，不是只缩小桌面密集表格。可借任务在窄屏重组的思路，不要求复制双组件树。对比任务仍可能需要表格，不能一律转卡片。
4. calcom/cal.diy：54343aa685ae8f33159d2f485ec4a57bad5c574a。
   https://github.com/calcom/cal.diy/blob/54343aa685ae8f33159d2f485ec4a57bad5c574a/packages/features/bookings/components/Section.tsx
   预约页面以命名区域和布局变体重新映射内容。可借“内容区域身份不变，位置随空间改变”，不是绑定Tailwind或某个断点。

### 实际浏览器案例

通过官方ZCode浏览器打开 https://ui.oiloil.org ，由可见案例链接进入：
- Post：https://ui.oiloil.org/works/mail/ ，实际页面 https://ui.oiloil.org/works/mail/live/index.html 。展示说明写明“打磨5轮”，不能当一次生成成绩。DOM确认导航、邮件列表、阅读回复三组。1440×900时测得列表 x=208/宽386，阅读回复 x=594/宽846；其余左侧空间208。说明空间分配不平均，阅读与回复获得更多空间；这些数值是一次实际测量，不是推荐模板。没有发送、归档或编辑任何邮件。
- 页边：https://ui.oiloil.org/works/reader/ ，实际页面 https://ui.oiloil.org/works/reader/live/index.html 。DOM确认正文article、批注、进度与阅读工具分离；测得article屏幕包围框宽约391.68，CSS行高38px，字体栈含Page Serif/Songti/Noto Serif。页面可能有整体缩放，包围框不能直接当原始CSS栏宽，声明字体不等于最终加载字体。

两案例均生成真实截图，但本轮工具返回工件路径而非可可靠判读的图像展示，因此不声称完成视觉评审、判断其漂亮的具体原因或验证移动端。截图位于会话artifacts：Post为call_6c171a4504de4f7e8eac709267d4aada，页边为call_kyhxSQYqY3NXedAqUaKcWlq7。上述可证结论限DOM与几何测量。用户对oil-ui的认可作为研究动机，不冒充本轮盲评结果。

## 建议采用的设计步骤

### 1. 内容关系先于组件

以真实内容标明主对象、主任务、辅助信息、局部动作与全局动作；写清哪些必须一起看到，哪些按需出现。内容清单不等于每项都建模块，优先级不只取决于标题级别，还取决于当前任务阶段。不得为布局舒服擅自删除给定事实或功能。

### 2. 按关系选择空间结构

选择并解释适合的组织方式：连续阅读、列表详情、比较表、主内容加辅助面板、步骤流程、探索型信息流。它们是选择依据而非模板目录；允许组合，但一个区块应有清楚职责。不先决定使用某个仪表盘壳，再把内容塞进去。

### 3. 分配宽度和主次

先确定正文/表格/媒体/操作的可用尺寸和长内容要求，再分配导航和辅助区。说明哪部分固定、哪部分伸缩、空间不足时谁让位。不强制70/30、黄金比例或固定列数。必须比较的数据可保持同屏；连续阅读不因辅助栏挤窄。

### 4. 通过间距表达关系

复用少量间距档，区分元素内部、组内、组间和章节间。相关项应该视觉相连；不同任务不因同色同框而混组。可用对齐和留白分组时无需额外框线；容器确有边界/交互意义时保留。局部紧凑与整体呼吸可以共存，不把大留白当高级感公式。不要规定必须相差两档或两倍。

### 5. 真内容的低样式比较

方向不明的新建/整体重设计，先做两个低成本、同内容同功能的结构候选；局部修正无需强制多方案。固定基本字体、色彩与素材，保留真实文字长度、必要字重和字号层级，不能只画灰色方块。关键图片尺寸提前考虑，避免布局完成后硬塞资产。

候选须在分组、主对象位置、主辅比例或阅读顺序有实质差异，不靠换皮。灰度/减弱装饰是辅助检查，不是万能通关标准；图表与状态仍需非颜色线索，不粗暴消除必要语义。

### 6. 窄屏重新组织任务

不仅检查无溢出，还检查组是否拆散、操作是否离对象太远、已选条目/筛选/阅读位置能否保留。辅助面板可转抽屉、分步或下方内容，是否保留列表取决于任务，不固定“总隐藏列表”。桌面首选布局不能直接等比缩小。

### 7. 结构成立后做视觉完善

再确定字体个性、色彩、素材、图标、边框及动效；样式强化主次。文字排版的几何部分早期就参与，不把字体整体推到最后。结构有问题返回布局，微小边框问题才局部修，不为所谓流程完整强制来回重做。

## 对技能的最小修改方案（尚未实施）

- SKILL.md：将平铺的方向卡改成上述决策顺序的短入口，保留事实、行为与授权边界。
- 新增 references/layout.md：放内容分组、空间预算、间距、重排的少量正反例；所有界面任务按需读取，不再只靠按页面类别分流。
- workspaces/reading/landing：保留各任务例外，删除与通用布局重复的说法；不扩展成平台大全。
- verification：增加布局检查，并区分结构失败和样式失败。验证看实际读者是否看出正确主次，不强迫证明某个美学分数。
- sources：只保留运行必要归属；本报告与将来的比较样例留maintenance。

## 可执行的首轮实验

三个brief：处理邮件（列表/详情/回复）、阅读中文报告（正文/目录/批注）、介绍产品（价值/证据/行动）。固定内容、控件、资产、视口、模型与预算。不要只用研究工作台一个题目证明普适性。

先在同任务中比较A当前0.1.1与B布局优先附加指令；两组给予相同总生成/修订预算。B允许两个结构候选，但其成本计入预算。记录实际执行而非手填成功轨迹。

布局阶段固定色彩与字体条件，评审主次、分组、对齐、区域比例、内容节奏、窄屏连续性；定一个方向后再分别检查完整视觉效果与任务操作。至少看首屏、下半部、长内容与一个非默认状态。用户未反馈只能称自检或独立评审，不能代替其审美认可。

放弃条件：两候选仅换皮；省略内容换来清爽；主要任务仍不突出；窄屏拆散关键关系；修订持续只换色而保留结构问题。发生时重做相应结构或记录未通过，不硬选胜者。不是规定读者必须先看到一个特定左上角或每页只能两种字号。

本报告是有证据来源的优化提案，不是已改造或效果已验证的技能。最重要的未知仍是：这些步骤是否在同成本真实生成中改善用户看到的页面，而不仅是让模型多写设计理由。
