# B · task-2 首轮实现记录

题目：巡演无线设备维修处置。交付文件：`preview/evaluation/b/task-2.html`（以本次 upgrade 目录为根）。

## 设计取舍

- 核心对象是工单 R-204。顶部保留剧社、设备、联系人与两项时间；完整客户原话和 H1 追加说明直接可读，避免把同时双通道及两路 XLR 的限制藏在展开项中。
- 宽屏采用“检验登记 / 今晚方案”的关联双栏，左栏按 C1–C4 连续排列，右栏只展开当前方案。错误摘要及原机交付条件可定位到相关控件。730px 以下顺序堆叠，沿页面自然滚动；固定底栏收束保存、确认和全局状态，并预留底部空间。
- H2 维修记录置于 C2 编辑区，保留故障背景。C2 的编辑值与已登记记录分开显示；修改即清空 C3 的有效结论，C2 未重新登记前禁用 C3 登记。C3 记录绑定 C2 版本。
- 三种方案保留各自输入，校验只针对当前方案。W-091 展示占用期限与禁用操作；W-088 提供明确的占用、释放及状态。切换方案保留占用并显示提示。
- “未保存 / 已保存”表达草稿状态，“已确认 / 确认已过期 / 已撤销”表达结果状态。确认生成静态快照，包含方案、依据及交接说明；相关编辑令结果过期。撤销备用机确认时释放 W-088，并保留登记、兼容勾选和说明。
- 中性浅底和连续白色工作面承托内容，深绿用于主动作与通过状态，红色提示失败，暖色标识待补齐与过期。状态同时提供文字；采用本地中文字体回退、标准表单控件和可见键盘焦点。

## 已阅读的材料

仅使用本次分配范围内的材料：

- `candidate/frontend-craft/SKILL.md`
- `candidate/product-design/SKILL.md`
- `evaluation/briefs.md`
- `evaluation/tasks/task-2.md`
- `candidate/frontend-craft/references/local-interfaces.md`
- `candidate/frontend-craft/references/reference-selection.md`
- `candidate/frontend-craft/references/exemplars.md`（索引与本任务相关条目）
- `candidate/frontend-craft/references/style-samples.md`
- `candidate/frontend-craft/references/cjk-typography.md`
- `candidate/frontend-craft/references/layout.md`

实际通过本地图像工具查看了 `candidate/frontend-craft/assets/references/tabler/desktop.jpg`。借鉴连续内容面、稳定对齐、低权重分隔与状态强调关系；没有复制表格或英文尺度。该图为参考资料，非本原型的运行截图。未打开样式样张页面，未声称核验其渲染表现。

## 静态检查

对最终 HTML 的内联 JavaScript 执行 `node --check`，退出码 0。

使用 Python 标准库 `HTMLParser` 检查 HTML 结构与引用，结果：

- 0 个重复 ID，0 个结构闭合错误。
- 表单标签、描述引用完整；结果标题由确认结果渲染时生成。
- 1 个内联 style，1 个内联 script；无外部资源引用。
- 未出现 fetch、XMLHttpRequest、WebSocket、localStorage、sessionStorage、indexedDB 或 eval。
- 含 730px 响应式断点；没有引入依赖。

代码层面对照了任务条件：C2 通过说明至少 10 字（不计空白）；任意 C2 编辑清空 C3；C3 对应最新 C2 版本；原机条件与备用机、继续检修条件分别校验；保存、切换和撤销均保留相关输入；动态结果文本转义后呈现。

## 限制与未验证部分

这是首轮静态实现。遵循本次统一评测安排，未使用浏览器，也未执行运行时行为测试；960×720、400×820 的实际排版、触控、键盘与验收路径由父任务统一验证。未根据浏览器结果进行额外精修。

所有数据均为题目提供的虚构业务信息，状态仅在页面内存；保存不跨刷新，不执行真实维修、通知、调度或设备占用。时间戳使用当前浏览器本地时间。没有联网、持久存储、提交、技能修改或读取另一组产物。
