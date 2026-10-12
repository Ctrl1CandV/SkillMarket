# 文件入库、本地保留与外部存储

## 按用途分类

先看项目如何构建、测试和交付，再对具体路径分类；以下是建议，不是凭文件后缀机械判断。

| 类别 | 通常做法 | 决策条件 |
|---|---|---|
| 源码、测试、构建/依赖声明、CI、数据库迁移、安装文档 | 入库 | 新克隆应能理解并重建该版本；测试小夹具需可分发且已脱敏 |
| 团队配置、格式规则、`.gitignore`、必要 `.gitattributes` | 入库 | 含可共享默认值，避免个人绝对路径和真实凭据 |
| 依赖 lockfile | 按工具规则入库，通常保留 | 与 manifest 同步；不要以“自动生成”或“这是库”为由一律忽略 |
| 包依赖安装目录、虚拟环境、编译缓存、可重建日志 | 忽略、需要时定向清理 | 必须确实能重建；不能只凭名字判断 `build/` 或 `dist/` |
| 编译产物、生成代码、网页站点、导出的 PDF | 通常走制品存储；必要时入库 | 若它是下游直接使用的交付源、规范要求的 generated code，或无法可靠重建，应记录生成方式与更新约束 |
| 密钥、token、私钥、带口令的连接串、真实 `.env` | 密钥系统或本地安全存储 | 不入任何普通分支或 LFS；示例文件只放占位值 |
| 私人笔记、个人 IDE 配置、临时草稿 | 本地或用户选定的私人位置 | 团队共享的 IDE 设置可入库，个人状态不随之入库 |
| 原始数据、模型权重、大型视频、二进制设计源文件 | 按权限/体积选 LFS 或外部存储 | 有许可证、可获取性、版本标识与完整性记录；LFS 适合需随源版本协作的资产 |
| 研究配置、种子、环境声明、小型结果索引 | 通常入库 | 原始运行结果外存；保存版本、数据标识和复现入口，不把每次输出都塞进 Git |
| 项目要求保留的审查记录和历史说明 | 入库或按已约定分支存放 | 有持续使用价值；工作临时记录没有自动入库的理由 |

自动生成不等于不该跟踪：npm 明确建议提交 `package-lock.json`，Cargo 则解释了 `Cargo.lock` 的确定性和对库消费者的限制。具体工具策略以当前官方文档和项目约定为准。[npm lockfile](https://docs.npmjs.com/cli/v11/configuring-npm/package-lock-json/)、[Cargo FAQ](https://doc.rust-lang.org/cargo/faq.html)

不把 `*.json`、`*.yaml`、`*.csv`、`*.pdf`、`*.lock`、整个 `data/` 或所有隐藏目录设成默认忽略；它们可能是配置、数据夹具、论文原稿或交付资产。框架模版忽略规则也要逐项匹配实际项目。

## 把分类落实为本次提交清单

暂存之前先列出具体文件或经逐文件审查的目录：目标分支、本次用途、是否跟踪、提交/本地保留/外存/待确认，以及理由。小改动可在工作记录中简短列明，不要求每次生成治理文档。检查新增、修改、删除和改名两端路径，不能只筛选 untracked 文件。

| 容易误入提交的内容 | 默认处理 | 必须核对的例外 |
|---|---|---|
| `testt/`、临时调试目录、一次性 smoke 文件 | 未明确用途前不暂存；保留本地，核实可重建再清理 | 若实际是团队维护的测试源，按项目规则入库；不能把拼写猜测当结论 |
| 正式 `tests/`、回归夹具 | 通常与对应源码入库 | 发布包可排除；仓库明确区分运行分支与维护分支时放到规定位置，别全局忽略测试 |
| `private/`、个人笔记、内部草稿、真实配置 | 默认本地或有独立权限的存储，所有普通分支均不纳入 | 名为 private 的代码模块可能是合法源码，先查内容与项目规则；明确允许共享且脱敏的资料才能例外 |
| Agent 的计划、对话导出、临时审查/验证报告、截图 | 当前任务没有维护需求时留本地；项目要求留档则归维护位置 | 可复用规范、用户手册或正式设计决策有明确用途时可入库，不用“AI 生成”作为排除理由 |
| 项目文档 | 安装、接口、构建和使用必需的文档随源版本保留 | 内部会议记录、工作日记、评估和归档按项目分支/权限规则处理；引用链需要的 references 不能漏发 |

新增整个 skill/plugin 时，从 `SKILL.md` 的相对引用继续核对脚本、参考和模板，确保使用者拿到后能运行；评测代码与运行依赖是两类内容。执行 `git add -- DIRECTORY` 前确认该目录的每个新增文件都在清单内，否则逐路径暂存。

只留本地的**共享项目规则**写入适当的 `.gitignore`，个人规则写入本地 exclude；对已有 tracked 文件先按后文处理，不能以为加 ignore 已经排除。仅在 dev 入库而 main 排除的维护资料，靠分支整合范围管理，不能在 dev 全局忽略它来代替规则。

commit 前将 `git diff --cached --name-status` 与清单对账，push 前还要核对所有待推送提交的路径。所有文件都在允许目录下也不代表本次任务授权修改它们；分支允许范围与任务清单必须同时满足。未知分类先保留文件，阻止其进入提交即可，不自动删除。

## 三个忽略层级

- `.gitignore`：共享的项目忽略规则，随仓库版本管理。
- 仓库的本地 exclude 文件：个人在此仓库的辅助文件；通常是 `.git/info/exclude`，worktree 场景用 `git rev-parse --git-path info/exclude` 找真实位置。
- `core.excludesFile`：用户跨仓库的个人忽略规则；不为一个项目擅自修改全局配置。

忽略只控制未跟踪文件。已跟踪文件仍会被检查和提交；`assume-unchanged`、`skip-worktree` 是 index 功能，不能当作可靠的“本地配置不上传”方案。[gitignore 文档](https://git-scm.com/docs/gitignore)、[Git FAQ](https://git-scm.com/docs/gitfaq)

需要跟踪默认配置而保留本地差异时，拆成受版本管理的 defaults/example 和被忽略的 local override，并在程序中明确加载方式。不要让同一个被跟踪配置靠 Git 标志“藏住”本地口令。

下面是按需选取的规则片段，不是完整的通用模板；复制前确认路径和用途：

```gitignore
# 仅在这些目录确为可再安装/可重建内容时使用
node_modules/
.venv/
__pycache__/
*.py[cod]
/coverage/

# 本地环境；示例必须先检查为占位值
.env
.env.*
!.env.example
!.env.sample

# 允许小夹具，不要直接忽略整个父目录
/data/*
!/data/fixtures/
```

`/name/` 锚定当前 `.gitignore` 所在层级，`name/` 可匹配下层同名目录；否定规则不能重新包含已被忽略父目录里的文件。验证候选规则：

```sh
git check-ignore -v -- path/to/local-file
git ls-files -- path/to/file
git ls-files --others --exclude-standard
git ls-files --others --ignored --exclude-standard
```

`check-ignore` 默认不报告已跟踪文件；要诊断它们匹配哪些规则可用 `git check-ignore -v --no-index -- path/to/file`。不匹配时退出码 1 不表示故障。[git check-ignore](https://git-scm.com/docs/git-check-ignore)

## 已跟踪文件改为本地保留

适用于本地配置或缓存等确实不该再跟踪的路径。先检查 staged/unstaged 状态，必要时安全备份；不要用 `-f` 绕过状态检查。添加准确 ignore 规则后：

```sh
git rm --cached -- path/to/local-file
git diff --cached --name-status
```

`--cached` 只移除 index 中的路径，在当前工作区保留文件；下一次提交会记录该路径从版本树删除。这不清除历史，其他成员更新到删除提交时可能失去此前受跟踪的副本，需提前安排本地配置迁移。首次仓库也可用它移除误暂存的新增文件。不用 `git rm -r --cached .` 全库重建 index 来解决一个路径。[git rm](https://git-scm.com/docs/git-rm)

跟踪停止、物理删除、历史清除是三种不同操作。若文件是敏感信息，转到 [泄露处理](recovery-and-cleanup.md)，仅改 ignore 和删除最新版本不足以解决问题。

## 大文件与复现信息

确认大文件是否需要随源版本追踪、是否频繁变更、下游是否能使用 LFS。LFS 把 pointer 放入 Git，内容放到 LFS 存储；先确认托管支持、权限、配额和完整下载，再选择，不硬编码某平台的限额。[Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage)

采用 LFS 时提交相应 `.gitattributes` 和 pointer，并验证内容可获取；新设 tracking 规则不会自动把旧提交转换为 LFS。历史迁移另作有授权的操作。外部存储则记录数据/制品 ID、版本、校验值、许可、获取方式与必要权限，避免在清单中保存短期含签名凭据的 URL。

对于普通 Git 中的大文件，检查待推送历史，而非只看工作区大小；增加一个“删除大文件”的提交仍可能推送它的旧对象。不要未经调查重写全仓库历史。

## 跨平台与嵌套仓库

共享换行、二进制识别和归档属性放进 `.gitattributes`。如要采用 `* text=auto` 和具体脚本的 EOL 规则，先检查现状；`git add --renormalize` 会造成大范围变更，应单独审查，不混在功能修复里。[gitattributes](https://git-scm.com/docs/gitattributes)

留意大小写改名、可执行位、符号链接和平台专用路径；Linux CI 与大小写不敏感的本地文件系统可能表现不同。遇到嵌套 `.git`，先查它是 submodule、独立项目还是误嵌套，不删除 `.git` 来“整理”；需要 submodule 时记录可访问的 URL 与具体提交，不把本地独立仓库误当成普通目录提交。
