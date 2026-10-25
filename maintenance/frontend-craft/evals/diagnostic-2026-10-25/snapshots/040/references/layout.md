# 排布手法

按内容之间的关系选手法，再细调比例。下面每种手法都写明适合什么内容，给出关键 CSS 和一个例子。

## 页面骨架

**工作区**：用于需要反复切换对象并查看详情的工具。导航、列表、详情可分栏，主要阅读区留足宽度，避免不必要的嵌套滚动。没有持续查看详情的任务时，用单列表或行内展开即可。下面是三栏起点，不是工具页固定模板。
```css
.app { display: grid; grid-template-columns: 220px minmax(320px, 420px) 1fr; height: 100dvh; }
.app > * { overflow: auto; }
```
例子：邮件客户端、样本库。窄屏时，列表和详情变成两步：点进去看详情，带返回按钮。

**阅读栏**：用于长文。正文单栏，宽约 30–40 个汉字。目录固定在一侧，注释和来源放在页边。
```css
.article { display: grid; grid-template-columns: 1fr minmax(0, 38em) 1fr; column-gap: 3rem; }
.article > * { grid-column: 2; }
.article .aside { grid-column: 3; position: sticky; top: 1rem; }
```

**主栏加侧栏**：主内容占大部分宽度，侧栏放摘要、属性或操作。侧栏宽度固定，主栏随窗口伸缩；空间不够时，侧栏自动换到下方。
```css
.with-sidebar { display: flex; flex-wrap: wrap; gap: 2rem; }
.with-sidebar > .side { flex-basis: 18rem; flex-grow: 1; }
.with-sidebar > .main { flex-basis: 0; flex-grow: 999; min-inline-size: 60%; }
```

**分段长页**：用于介绍、活动和产品页。一段讲一个主题，每段按自己的内容选构图，比如大数字、对照表、步骤、引言或作品图，各段不必都做成卡片网格。

## 区块内的排法

- **堆叠**：纵向排列，间距统一用 `gap` 控制：`display: flex; flex-direction: column; gap: var(--space-3);`
- **成簇**：标签、按钮组自然换行：`display: flex; flex-wrap: wrap; gap: .5rem;`
- **切换排**：少数几块并排，容器窄到阈值以下时整体改成竖排，不会挤成窄条：
  ```css
  .switcher { display: flex; flex-wrap: wrap; gap: 1rem; }
  .switcher > * { flex-grow: 1; flex-basis: calc((40rem - 100%) * 999); }
  ```
- **自动网格**：同类条目按可用宽度自动排列：`grid-template-columns: repeat(auto-fill, minmax(min(16rem, 100%), 1fr));`
- **横向卷轴**：窄屏上的一排标签或缩略图横向滑动：`display: flex; overflow-x: auto; scroll-snap-type: x mandatory;`
- **数据行**：列表的每一行用同一套列宽，左边放状态，中间放主信息，右边放次要信息和操作。扫读时视线可以顺着一列往下走：
  ```css
  .row { display: grid; grid-template-columns: 1.5rem minmax(0, 1fr) 8rem 6rem; align-items: baseline; gap: .75rem; }
  ```

## 分区

按独立任务、对象和阅读顺序分区。先判断相邻内容是否需要不同区域，再用对齐、间距和必要的标题表达关系；需求列表中的每一点不必对应一个卡片。

- **工作区**的详情放在列表旁边，选中关系清楚。仅当符合任务且不会触发业务动作时才默认预览第一项；需要用户主动选择时保留选择提示。聊天、编辑画布等用于后续内容的空间允许留白，不强塞统计或摘要；详情很少则用行内展开。
- **长页**用真正不同的内容划分区块，标题帮助定位，不复述相邻控件。重要段落可用版式变化或底色区分；连续正文保持连贯。
- **首屏**围绕视觉主角组织：展示页可以是作品、大标题或真实产品画面，无需额外拼一张摘要卡；工具页让当前对象与主要操作可见。
- **划分要一致**：同一层级的区块用同一种划分方式。一个页面里交替用色带、卡片、细线和留白，会让区域关系变得混乱。

## 比例与间距

- **间距档位**：定 4–6 档（如 4、8、12、20、32、56px）。组内用小档，组与组之间用大档，组间距明显大于组内间距，分组才能一眼看出。
- **主次比例**：写明具体数字，比如“列表 1 : 详情 2”，或“正文 38em、侧栏 16rem”。
- **密度**：按页面类型和数据量决定。
  - 成百上千条、需要反复处理的管理数据，可以排得紧凑，每行约 36–48px。
  - 十几到几十条的个人列表，条目之间要留出呼吸空间，每条约 64–96px。
  - 阅读页宽松。
  - 艺术和展示类页面大量留白。
- **分组方式**：分组先用对齐和留白。边框和底色留给真正独立的对象，比如弹层、选中项和可拖动的卡片。

## 窄屏

- **按任务重排**：
  - 工作区变成两步。
  - 侧栏移到主内容下方，或收进抽屉。
  - 筛选收成一行按钮，点开再展开面板。
  - 表格保留标识列和主状态，其余列放进展开行，或在表格自己的容器里横向滚动。
- **底部固定栏**：页面底部要留出和栏等高的空白，并加上 `env(safe-area-inset-bottom)`。

## 依据

Heydon Pickering 与 Andy Bell 的 [Every Layout](https://every-layout.dev/layouts/) 布局原语（Stack、Cluster、Sidebar、Switcher、Grid、Reel）；Carbon 设计系统的间距档位思路。
