# B · 任务三：书店周末外摆选书

产物：`preview/evaluation/b/task-3.html`。单个自包含 HTML，内联 CSS 与 JavaScript；未使用网络、第三方依赖、持久存储或真实业务接口。

## 设计取舍

- 主要判断是“哪些书适合带、还能带几册、从哪家店取”。书目使用连续多行列表，完整保留长书名、作者/出版社、主题/取书点以及在库减预留的余量依据。编号退后，书名承担识别，数量和加入动作邻近。
- 宽屏书目与携带清单并置，清单始终独立于检索结果；对筛选外的已选条目显示文字标签与汇总。窄屏使用“浏览书目 / 携带清单”切换，同时保留固定底部总量与保存入口，避免把已选内容放到整份书目末尾。
- 备注、荐语、单书数量、暂缓和恢复集中在单书详情；已选条目也提供直接数量操作。B01 的荐语独立于可编辑备注，不把固定荐语覆盖成输入内容。B06 的初始备注按题目保留。
- 采用偏暖底色、近白内容面与深绿动作强调。选中书目只使用细色条，携带清单以整体边界明确范围；数量及状态通过文字与颜色共同表达。没有新增封面图片或虚构内容摘要。
- 西店由同事带书的说明保留完整；清单显示两店册数，发生变化后可展开“数量变化”，对照各书初选数量与当前数量。
- 全局保存仅形成当前页面内存中的快照。书目筛选和排序不影响保存状态；数量、选择、备注与暂缓状态改动会标记“尚未保存”。界面明确刷新后重置、不调拨库存。

## 交互与状态

- 初始 B01×2、B04×1、B06×2，共 3 种 5 册。
- 搜索书名/作者/出版社，主题、取书点、余量条件取交集；支持书名和余量双向排序，并提供编号顺序。
- 可取消当前筛选结果中的选择、取消全部选择；两者均保留备注，暂缓对象单独管理。
- 所有数量变更、首次加入及恢复操作共用数量校验：正整数、不超过单书余量、总数不超过 18。校验失败时展示具体原因并保留之前有效状态；无余量书可查看、编辑备注，但不能加入。
- 单书暂缓保留数量、备注和暂缓前是否已选。原已选对象恢复时尝试恢复原数量，容量不足则仍保持暂缓；原未选对象恢复后回到待选，不擅自选中。
- 数量输入以失焦或 Enter 确认，直接加减即时修改。静态审查时调整了更新方式：数量校验只更新数值与反馈，不替换正在使用的输入或按钮节点，避免失焦校验吞掉下一次按钮点击。
- 原生 dialog 提供单书详情与 Escape 关闭；关闭后尝试回到原入口。具有标签、键盘焦点样式与文字状态；本地提示通过 live region 提供。

## 实际读取的材料

仅使用此次分配范围，以下路径均相对 `maintenance/frontend-craft/upgrades/2026-10-29-local-interfaces/`：

- `candidate/frontend-craft/SKILL.md`
- `candidate/product-design/SKILL.md`
- `evaluation/briefs.md`
- `evaluation/tasks/task-3.md`
- `candidate/frontend-craft/references/local-interfaces.md`
- `candidate/frontend-craft/references/reference-selection.md`
- `candidate/frontend-craft/references/exemplars.md`（按相关条目阅读，批量输出中部分文本截断）
- `candidate/frontend-craft/references/style-samples.md`
- `candidate/frontend-craft/references/cjk-typography.md`
- `candidate/frontend-craft/references/layout.md`
- `candidate/frontend-craft/references/visual-style.md`
- `candidate/frontend-craft/assets/references/tabler/desktop.jpg`（使用本地图像查看工具实际查看）

参考迁移：Tabler 本地图像的连续行、稳定属性位置与轻分隔适合书目扫描；本题长中文名称和手机窗口不适合直接照搬多列表格，因此改为多行书目并保留完整标题。该截图提供整体秩序依据；没有将其颜色、字体或列宽原样迁移。样式样张只读说明，没有打开运行或声称查看其画面。

没有读取根 skill、baseline、scoring.md、其他组产物或其他代理报告。没有修改技能，也没有生成额外测试题或提交版本。

## 静态检查结果

- Node.js 内置 `vm.Script` 只解析内联脚本，语法通过；没有执行页面业务逻辑或模拟浏览器。
- HTML 源码中静态 ID 无重复，字面量 DOM ID 引用均可找到；具名函数无重复。
- 8 本书及初始数量序列与题目一致，初选正数为 2、1、2。
- 一个内联 style、一个内联 script；未发现 HTTP(S) 资源、fetch、XHR、localStorage、sessionStorage、IndexedDB、cookie 或 CSS import。
- 源码核对了错误保留旧值、恢复校验、筛选不清空选择，以及保存状态只受草稿改动影响的分支。
- 源码包含 720px 响应式断点：960×720 使用两列，400×820 使用工作区切换和自然页面滚动；书名没有省略，备注预览可展开单书查看全文。

## 限制

遵守本轮“仅静态检查，由父任务统一实测”的要求，没有用浏览器打开产物、截图验收、运行交互测试或依据实测精修。960×720 与 400×820 的实际排版、系统字体、原生 dialog、键盘与触屏操作仍待父任务统一验证。静态语法与源码检查不代表这些运行效果已经通过。

仅有内存草稿；刷新会恢复题目初值。没有真实保存、跨设备同步、库存扣减或调拨动作。
