# 对照结果：frontend-craft 0.7.0，加不加 modern-web-guidance（2026-11-18，各跑一次）

依据开跑前写定的 [PLAN](PLAN.md)。两组都用 pi + deepseek-flash，技能快照为仓库提交 `7d1617f`。成品留在本地临时目录，没有入库；对照截图见 [shots/compare.jpg](shots/compare.jpg)。

## 一句话结论

**两组的差别比预想的小。** 只带 frontend-craft 0.7.0 的 A 组，也用了原生对话框、rem 字号、包含深色的 `color-scheme`、`aria-invalid` 和强制颜色轮廓，这些正是 0.7.0 正文里“没有该技能时至少做到”的几条。B 组多出来的是：
- 格式说明放在输入框上方；
- 家长姓名开了自动填充；
- 取消对话框的默认焦点用 `autofocus` 明确指定；
- 交付时写明用了哪几篇指南。

代价是费用多了 62%。每组只跑了一次，而且没有跑 0.6.2 当基线，所以分不清 A 组的这些写法，是 0.7.0 正文带来的，还是模型本来就会。

## 过程

| | A：只带 frontend-craft | B：再加 modern-web-guidance |
|---|---|---|
| 用时 / 工具调用 / 费用 | 29 分钟 / 157 次 / 0.335 | 30 分钟 / 167 次 / 0.542 |
| 查指南 | 没有这个技能 | 查了 7 篇：dialog、forms、validate-input-after-interaction、accessible-error-announcement、dark-mode、color、persistent-toast-notifications |
| 交付说明写没写用了哪些指南 | 没写，技能要求没查也要写“没查” | 写了，每篇一条，附原文引用 |
| 自己跑 pagecheck | 跑了，最后一次没有问题 | 跑了，最后一次没有问题 |

## 1. pagecheck 0.7.0（优化者在四种宽度下重跑）

两组都是“Nothing measurable found”，没有一类问题。

## 2. 结构写法（静态查代码）

| 项 | A | B |
|---|---|---|
| `<dialog>` 并用 `showModal()` 打开 | 2 个 | 3 个（多一个提交前的最后确认） |
| 自己写焦点陷阱或 Esc 处理、`role="dialog"` | 没有 | 没有 |
| popover | 没用 | 没用 |
| 出错状态 | `aria-invalid` 和 `aria-describedby`，没用 `:user-invalid` | 同 A |
| 自动填充 | 只有手机号 `tel`；家长姓名写了 `off` | 手机号 `tel`、家长姓名 `name` |
| 格式说明的位置 | 没有常驻说明，只有输入框里的占位文字，错误显示在下方 | 说明在输入框上方，错误在下方 |
| `color-scheme` | `light dark`，24 处 `light-dark()` | `light dark`，用 `prefers-color-scheme` 换整套颜色 |
| px 字号 | 0 处（62 处 rem） | 0 处（字号写在变量里，都用 rem） |
| `outline: none` 没有替代样式 | 没有 | 没有 |
| 强制颜色 / 减少动态效果 | 都写了 | 都写了 |

## 3. 实际操作（[behave.mjs](behave.mjs)）

| 步骤 | A | B |
|---|---|---|
| 打开取消确认对话框 | 模态；焦点在“先不取消” | 模态；焦点在“不取消了”（`autofocus`） |
| 按 Esc / 关掉后焦点 | 关闭；回到“取消预约”按钮 | 关闭；回到“取消预约”按钮 |
| 空提交 | 先选了时段再提交（A 要先选时段才能进到填表这一步）：5 个字段 `aria-invalid=true`，焦点到第一个出错的输入框 | 5 个字段 `aria-invalid=true`，焦点到第一个出错的地方，也就是还没选的时段 |
| 手机号填 `123` 后离开 | 报错，`aria-invalid=true`，错误文字在下方 | 报错，`aria-invalid=true`，说明在上方、错误在下方 |
| 系统设为深色 | 跟着变暗 | 跟着变暗 |
| 强制颜色下选中的时段 | 有 2px 轮廓 | 有 2px 轮廓 |

第一版脚本截强制颜色图时点到了已满的时段，没有选中任何东西，A 组的截图因此看不出选中状态。改成点第一个还有名额的时段后，两组都有轮廓。上面的结果以改过的脚本为准。

## 4. 任务目录之外

- 两组都在系统临时目录留下了东西：A 组留下一个截图文件夹 `vac-final`。另外有 35 个 Playwright 临时浏览器目录，共 95 MB，时间从前一天晚上到这次运行结束都有，包括优化者自己当天跑的检查脚本、练习页核对和 pagecheck。都是 Playwright 在 Windows 上关闭浏览器后没删干净的，已全部删除。
- B 组查指南时，超过 9.5 KB 的结果写进了 `%LOCALAPPDATA%\modern-web-guidance\tmp`，这是启动脚本指定的目录，符合预期。
- Python 包、字体、全局 npm、全局技能目录、Codex 配置都没有变化。

## 由此得到的待办

- **Playwright 临时目录残留**：frontend-craft 的 `env.mjs` 和 pagecheck 每次运行都可能在 Windows 的临时目录留下一个 Playwright 浏览器目录，越积越多。可以考虑在启动时指定一个固定的临时位置，结束后自己清掉。
- **要不要跑 0.6.2 基线**：如果想知道 0.7.0 正文本身起了多大作用，可以用同一题目再跑一次 0.6.2 当基线。这次没跑。
- **画面**：两组方向不同。A 是分步骤加整张日期×时段表；B 是一页分三块，桌面版有一张固定在右侧的核对卡。没有请用户盲看。
