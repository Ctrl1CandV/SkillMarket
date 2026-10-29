# B / task-1 实现记录

题目：播客试听片段批量制作与交付。

产物：`preview/evaluation/b/task-1.html`。单文件内联 HTML、CSS、JavaScript，无外部依赖、联网、持久存储及真实业务操作。刷新恢复初始状态；导出在本地生成 JSON。

## 设计决定

- 围绕六个节目组织连续列表，保留完整标题。截取范围、目标格式、源时长与当前产物状态在同一条目中可扫读；异常原因在收起时也直接出现。
- 参数与产物详情在原条目展开，编辑起终点、独立格式、确认推广和补关联源均归属对应节目。全局格式和批量选择位于列表顶部；制作与导出在固定页脚收束。
- 已有产物记录实际范围与格式，当前参数、有效性、制作失败分别计算。批量处理保留已匹配项并记录原因，跳过校验阻塞项，逐项模拟 500 毫秒；P04 首次固定失败。
- 960×720 采用连续宽列表、同列状态与三列参数；400×820 改为条目内状态行、两列范围和独立格式行，页脚保留两个核心操作。只有页面自然滚动，不引入多处独立滚动。
- 中性浅底、深绿操作强调，浅暖色用于需要确认和过期，红色用于源缺失、范围错误与制作失败。系统中文黑体；标题、元信息、说明和控件使用不同尺度。

## 已读材料

仅读取本次分配范围：

- `candidate/frontend-craft/SKILL.md`
- `candidate/product-design/SKILL.md`
- `candidate/frontend-craft/references/local-interfaces.md`
- `candidate/frontend-craft/references/reference-selection.md`
- `candidate/frontend-craft/references/exemplars.md`
- `candidate/frontend-craft/references/style-samples.md`
- `candidate/frontend-craft/references/layout.md`
- `candidate/frontend-craft/references/cjk-typography.md`
- `candidate/frontend-craft/references/visual-style.md`
- `candidate/frontend-craft/references/review.md`
- `evaluation/briefs.md`
- `evaluation/tasks/task-1.md`

实际通过图像工具查看了 `candidate/frontend-craft/assets/references/tabler/desktop.jpg`：参考连续内容面、对齐的状态列及低权重分隔；本题中文标题较长并需要原位编辑，因此不照搬英文单行表格。不曾打开目标产物的浏览器画面。

## 静态检查

- Node 解析内联 JavaScript：通过（`new Function` 仅编译，不执行页面或业务逻辑）。
- 一个内联 script；六项原始数据；静态 id/动态 id 模板无重复。
- 未发现外部 script/stylesheet 依赖，未发现 fetch、XHR、WebSocket、sendBeacon 或持久存储 API。
- 检查到 650px 响应式断点、原生输入标签、展开的 aria-expanded/aria-controls、焦点轮廓、状态播报，以及本地 Blob JSON 下载。
- 代码逐项对照验收路径：初始四选/P01 有效/P05 过期/P02 待确认；批量分流；范围修复与备用源；P04 重试；格式继承；当前选择对应的有效产物与排除原因导出。此项为静态阅读，未执行交互验收。

## 限制

按分配要求，仅做静态检查，未用浏览器查看或操作目标 HTML；960×720 与 400×820 的实际排版、键盘焦点、下载及完整验收路径均留给父任务统一实测。未声称实际画面或交互已验证。音频制作是内存模拟，无播放或音频文件。
