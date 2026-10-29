# A / 任务一实现记录

题目：播客试听片段批量制作与交付。

产物：`preview/evaluation/a/task-1.html`（相对本次 upgrade 目录）。单个自包含 HTML，内联 CSS / JavaScript，无新增依赖。

## 设计取舍

- 以六个片段为持续对象，完整标题、源时长、截取参数、当前输出格式、产物实际参数及状态就近显示。使用连续列表和轻分隔，避免长标题被裁切。
- 桌面将对象、参数与制作结果并置；窄屏按对象 → 范围/格式 → 状态/动作排列。保留自然页面滚动，底部汇总当前所选可交付数与待处理数。
- P02 的推广确认直接跟随该片段，并明确说明范围修改会清除确认。P03 的唯一备用源提供就地关联；P06 显示边界规则。
- 有效产物由实际范围、格式、源与当前校验共同判定。格式不匹配显示过期，已有产物的实际参数仍保留可见。制作时冻结参数和选择，防止重复提交或任务处理中改变参数。
- 提供批次结果记录、单项重试、交付清单核对及本地 JSON 下载。清单包含所选有效产物和其余所选项的排除原因，未选择项不加入清单。
- 使用绿灰底调、深绿操作色、浅底连续内容面；以文字标签区分成功、待确认、过期和失败，颜色不是唯一状态依据。

## 本次读取材料

仅读取已分配的以下资料，没有读取另一组产物、candidate、评分或其他报告。

- `baseline/frontend-craft/SKILL.md`
- `baseline/product-design/SKILL.md`
- `baseline/frontend-craft/references/reference-selection.md`
- `baseline/frontend-craft/references/exemplars.md`
- `baseline/frontend-craft/references/cjk-typography.md`
- `baseline/frontend-craft/references/layout.md`
- `baseline/frontend-craft/references/visual-style.md`
- `evaluation/briefs.md`
- `evaluation/tasks/task-1.md`

实际查看本地参考图：`baseline/frontend-craft/assets/references/tabler/desktop.jpg`。借鉴连续数据面、字段对齐与弱分隔的关系。此题具有长中文标题和逐项编辑，因此扩大行高并允许窄屏按对象重排；未复制参考的表格结构或颜色。没有访问外部网页。

## 静态检查

使用 Node.js `vm.Script` 仅解析内联脚本，未执行界面程序：语法通过。

静态扫描结果：固定 ID 无重复；无远程资源引用；无 fetch / XMLHttpRequest / localStorage / sessionStorage / indexedDB；本地下载由 Blob 与临时对象 URL 生成；含窄屏重排规则。检查时文件 27,074 字节。

逐项静态核对：初选 P01/P02/P04/P05；P01 为 MP3 有效产物；P05 已有 WAV 而当前跟随 MP3；P02 终点 120 且尚未确认推广；P03 缺源；P06 终点 370 超过 360。批量制作逐项等待 500 ms；P04 首次固定失败、下一次成功。每项保留独立格式选择，范围修改清除 P02 确认。导出按钮依据所选有效产物数量禁用。

## 未验证及限制

- 遵照统一评测要求，只做静态检查，没有打开原型浏览器、截图或执行交互验收。960×720 与 400×820 的实际布局、滚动、焦点和下载由父任务统一验收。
- 只模拟制作；不播放、读取或生成音频，不产生真实业务动作。
- 状态仅在页面内存保存，刷新恢复初始数据。唯一落盘动作是用户触发 JSON 清单下载。
- 字体使用系统回退，未联网加载字体，实际字形依运行环境而定。
