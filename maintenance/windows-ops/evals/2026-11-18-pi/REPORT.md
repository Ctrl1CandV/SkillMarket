# windows-ops 0.1.0 试用：pi + deepseek-flash，跑一次

任务见 [BRIEF](BRIEF.md)，材料在 [data/](data/)，运行脚本 [run_pi.sh](run_pi.sh)。提示词只说“读 BRIEF.md 完成”，不点技能名。技能是当时工作区里还没提交的 0.1.0（提交前的版本，和随后提交的只差下面“改进”一节的三条）。

## 结果

用时约 2 分钟，30 次工具调用，费用 0.025。四件事都做成了，优化者逐项复核：

| 事项 | 它走的路 | 复核 |
|---|---|---|
| 合并账单成 xlsx | PowerShell 读 CSV、排序、算合计；WPS COM（`KET.Application`）后台写入并存为 xlsx；再用 Excel COM 读一遍作验证 | 优化者用 WPS COM 读回：一张表“明细”，7 条按日期排好，末行合计 754.4，正确。合计写的是数值，不是公式 |
| 清掉 `旧版本` | `DeleteDirectory(..., SendToRecycleBin)` | 回收站里有这个文件夹，15:49 删除，可以还原。交付时还主动问要不要永久删除 |
| 屏幕缩放和分辨率 | `EnumDisplaySettings` + `GetDpiForMonitor`，再用注册表 `AppliedDPI` 交叉核对；只读 | 主屏 3840×2160、150%，和优化者在设置页读到的一致。另外报出了副屏 |
| VS Code 打开再关掉 | 发现 PATH 里的 `code` 是 QoderCN 的，改用 VS Code 全路径启动；agent-desktop `list-windows` 读标题，`screenshot` 看窗口；按进程号正常关闭 | 标题“欢迎 - task - Visual Studio Code”；关闭后没有 Code.exe 进程，其他窗口没动 |

- 全程没用 `--headed`，没有动用户的鼠标键盘。
- 路线和技能第 1 节一致：能用命令的都用命令，界面只用来读标题、截图。

## 任务目录之外

- 系统临时目录里留下一个 `shot.json`。它调用 `screenshot` 时没给路径，整张截图以 base64 输出，它把输出存成了这个文件。已删除。
- 回收站多了 `旧版本`，这是任务要求的。
- Python 包、全局 npm、全局技能目录、字体都没有变化；没有残留的 Excel 或 WPS 进程。

## 改进（已写进技能）

1. 截图一定给文件路径，用完删掉。
2. Windows PowerShell 5.1 会把没有 BOM 的 UTF-8 `.ps1` 当系统编码读，中文路径会坏。它在这里卡了一次，自己加 BOM 解决了。
3. 同名命令可能指向别的程序（本机的 `code`），启动前先 `Get-Command`。

另外，routes.md 原来写“PowerShell 里查 DPI 不可靠”。这次它用 `GetDpiForMonitor` 和注册表读对了，已改成更准确的说法。

## 没测到的

- 需要真正点界面才能完成的事，这个任务里没有。它在 VS Code 上只用了读取和截图，界面点击的可靠性只有优化者亲手试过（见 [README](../../README.md)）。
- 这里只有一个模型、一次运行。Codex、ZCode、Claude Code 上没有试。
- 没有考察“范围不清楚时先问”：pi 是非交互运行，问不了人。
