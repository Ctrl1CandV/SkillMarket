# windows-ops 维护记录

让 Agent 在 Windows 上操作软件和系统。用户的痛点：Codex、ZCode 的截图式电脑操作慢，而且操作期间占着屏幕。要求是装起来和用起来都简单，效果不必最好。

## 决定（2026-11-18，用户选定）

- **采用 [agent-desktop](https://github.com/vercel-labs/agent-desktop)**（Vercel Labs，Apache-2.0），不用 Windows-MCP。理由：
  - 它是命令行程序，CC、Codex、pi、ZCode、Antigravity 只要能跑命令就能用，不用逐个配 MCP；pi 本身不支持 MCP。
  - 它读系统的界面结构（UI Automation），点击、填值默认走系统接口，不移动鼠标、不抢窗口。Windows-MCP 点击时会移动真实鼠标。
- **安装方式：下载固定版本的发布包**，不用 `npm install -g`。本机 npm 缓存在 Program Files 下，写不进去。
- **确认规则**：用户明确同意的范围内直接做；其中重大、无法挽回、可能造成损失的一步再确认一次；范围不清楚就先问。写进了 SKILL.md 第 3 节。
- **不重写它的操作说明**。它的说明编译在程序里，随版本走（`skills get desktop`、`skills get platform`）。本技能只补三样它没有的：
  - 先走命令行和 COM 的路线顺序；
  - 本机实测得出的几条注意事项；
  - 用户的确认规则。

## 安装（本机已装）

- 程序：`%LOCALAPPDATA%\agent-desktop\1.3.1\bin\agent-desktop.exe`，来自 GitHub 发布页的 `agent-desktop-v1.3.1-x86_64-pc-windows-msvc.tar.gz`（1.8 MB）。SHA-256 `6ee4b1e0…a08c13`，与发布页的 digest 和 `checksums.txt` 都核对过。程序没有数字签名。
- 状态目录：`%LOCALAPPDATA%\agent-desktop\state`，由 `scripts/ad.mjs` 设置 `AGENT_DESKTOP_HOME`。默认的 `~\.agent-desktop` 在本机会被 Codex 沙箱加上 `CodexSandboxUsers` 的读权限，agent-desktop 因此拒绝使用（报“private file DACL grants an untrusted principal”）。第一次试用时生成的 `~\.agent-desktop` 已删除。
- 升级：改 `scripts/ad.mjs` 里的 `VERSION` 和 `SHA256`，按脚本打印的命令下载到新的版本目录，再把下面的实测重跑一遍。

## 亲手试用（2026-11-18，只用草稿文件）

| 软件 | 结果 | 结论 |
|---|---|---|
| 资源管理器 | 读一个窗口 1.6 秒，117 个元素；点击文件、点“关闭”都行。改名被拒：每一行的“名称”框都一样，它不肯猜是哪一行 | 文件操作走 PowerShell |
| 系统设置（显示页） | 0.4 秒读完，连屏幕外的缩放 150%、分辨率 3840×2160 都读到；没改任何设置 | 读设置可以用它 |
| Excel | Office 没激活，激活向导挡住窗口 | 本机交给 WPS |
| WPS 表格 | 界面结构里只有窗口外框，编辑区和功能区读不到；窗口截图正常，不需要切到前台。COM（`KET.Application`）后台读、写、存 xlsx 都在 1.1 秒左右 | WPS 内容走 COM，看画面用截图 |
| VS Code | 1.4 秒读到文件树、标签和菜单；点文件树里的文件被拒（无头模式下这个元素不支持点击） | 用 `code` 命令 |

其他发现：
- 同一程序有多个实例时（本机开着两个资源管理器），按程序名操作的命令会拒绝，要改用窗口编号。
- 它的输出是 UTF-8。管道里按系统默认编码读会乱码。
- 在 PowerShell 里查系统 DPI，因为进程没声明 DPI 感知，150% 会读成 100%。缩放比例要从设置页读。
- WPS 的 COM 用完要 `Quit()` 并释放对象，否则会留下后台进程。

## 评测

- [2026-11-18 pi 试用](evals/2026-11-18-pi/)：同一个任务里有文件、WPS 表格、系统设置、VS Code 四件事。
