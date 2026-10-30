# 提交、同步、协作与发布

## 提交是一项完整的逻辑变更

功能、相关回归测试和必要文档通常一起提交；独立的格式化、依赖升级、文件搬迁和业务修改按可审查/可回滚的逻辑拆分。不是每个文件一个提交，也不是把一天全部修改塞进一个提交。manifest 与必要 lockfile 一起更新。

先读贡献指南、commitlint/发布配置和近期标题。有既定格式就沿用。没有格式且需要机器生成变更日志时可建议 Conventional Commits；普通小项目也可用一致、具体的描述式标题。中文/英文、标题长度和 issue 格式属于团队选择，不声称 Git 强制 50/72 字符或英文命令式。

采用 Conventional Commits 时：

```text
type(scope)!: 简短的具体变化

解释触发条件、修改原因和影响，必要时给出验证或迁移信息。

BREAKING CHANGE: 不兼容变化及迁移方法
Refs: #123
```

scope、`!`、正文和 footer 都按实际需要；`!` 与 `BREAKING CHANGE:` 可择一表示破坏性变更。本技能建议兼容性变化较复杂时写明迁移。`feat` 表示功能，`fix` 表示修复；`docs`、`test`、`refactor`、`perf`、`build`、`ci`、`chore` 等是可选团队类型。规范没有要求所有这些类型，也不保证所有工具都支持团队自定义类型。[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)

具体标题如 `fix(cache): prevent stale results after invalidation` 或 `docs(install): 补充 Windows 安装步骤`；避免 `update`、`修改文件`、`各种优化`。只有行为未变才叫 refactor，不用它掩盖功能或兼容性变化。标题描述变化，正文解释原因，不复制整份 diff 或 AI 聊天记录。

不编造测试通过、issue 编号、签名、DCO 同意或 Co-authored-by。宿主或用户规定的署名行（如 AI 协作者 trailer）按规定照写，它记录真实参与者，不属于编造。仓库要求签名或 DCO 时使用已配置的合法身份；不能自行以用户身份宣告未确认的版权授权。

### Agent 提交消息的验收

先确定最终 staged 变更，再写标题；不要从用户的整段请求、计划或工作区全部改动生成消息。验收时核对：

1. 标题有可识别的对象和具体动作/行为，读者无需打开聊天记录就知道改了什么。
2. 标题与正文覆盖实际变化，没有把尚未暂存、未实施或失败的工作写成完成。
3. 一个标题需要用“以及其他修改”概括独立事项时，检查是否应拆提交；相关源码、测试与文档仍可是一项逻辑变更。
4. 正文只补充必要的原因、影响、迁移及真实验证；小改动用准确标题就够，不为格式填空话。
5. 日期、type 或 issue 号不能代替变化说明；沿用仓库风格时仍应具体。中途 WIP 可以按团队约定保留在私有工作分支，最终交付不留模糊 WIP 标题。

| 不清楚的消息 | 按实际快照修正后的示例 |
|---|---|
| `update` / `10.12 修改 skill` | `10.12 git-governance：增加分支文件清单与提交消息验收` |
| `fix: 修复问题并清理文件` | `fix(config): stop tracking local credentials and add example defaults` |
| `完善文档和测试`（实际只归档评测） | `10.12 git-governance 维护：记录入库范围审查与验证结果` |

这些是自拟示例，分别展示描述式和 Conventional Commits 风格；必须替换成当前快照事实，不能照抄未完成的安全处理或验证。

## 从暂存到 commit

已有 staged 内容属于谁、是否在本次范围必须先核对。同文件混合本次与用户修改时使用精确 hunk；不能非交互补丁时保留原状并说明需要解决的范围，不强行全文件 add。以下路径为占位示例：

```sh
git add -- path/to/source path/to/test
git diff --cached --name-status
git diff --cached --check
git diff --cached
git commit -F path/to/commit-message.txt
git show --stat --oneline HEAD
git status --short --branch
```

commit 默认提交整个 index，不是“刚才 add 的几个文件”。即使使用路径提交也要理解它可能绕开原暂存内容的语义；有不相关暂存时优先隔离或精确保全，不无意重写用户 index。

多行提交正文或 PR body 放在安全的临时文件中，通过 `-F` 或平台工具的 body-file/结构化参数传递；按实际 shell 引用路径，不把用户文本拼进可执行命令。消息文件别留作仓库新文件，也不要添加 `--no-verify` 来处理 hook 拒绝。

## 同步前先决定目标

`origin` 是常见名称，不保证是应推送的上游。fork 场景常从 upstream 获取，向个人 origin 推送；检查各远端实际作用及 push URL，在输出中隐藏凭据。

确认实际 remote 与 base 后，用下面的形式获取并查看最新事实；大写名称是占位符，替换后执行，不含 shell 的重定向符号：

```sh
git fetch REMOTE
git rev-list --left-right --count HEAD...REMOTE/BASE
git log --oneline --left-right HEAD...REMOTE/BASE
```

`HEAD...REMOTE/BASE` 用于这里的分叉检查；PR 内容常用 `git diff REMOTE/BASE...HEAD` 查看 merge-base 之后的变更，比较两端树则用 `git diff REMOTE/BASE HEAD`。它们回答不同问题；确认比较基线和结果语义后使用。[git diff](https://git-scm.com/docs/git-diff)

| 事实 | 处理 |
|---|---|
| 本地落后且无本地独有提交 | 适合 `git merge --ff-only REMOTE/BASE`；先确保操作不会覆盖本地文件 |
| 只有本地独有提交 | 无需为“同步”额外造 merge；检查后可按任务推送 |
| 两边都有独有提交 | 私有 topic 可按约定 rebase；共享分支通常 merge 或另建整合分支，不自动重写同伴历史 |
| 无 upstream 或新分支 | 明确 remote 与同名/指定目标，再建立 tracking；不能假定任何现存引用就是发布目标 |

合并/rebase 前保全必要修改；普通 `pull` 会依配置执行不同整合方式，不在不清楚配置时盲用。共享与私有不仅取决于是否已经 push：有人依赖该分支时就需协调。

冲突处理先读两端变化与意图；不要全局选 ours/theirs。rebase 中 ours/theirs 的视角容易与直觉不同。解决后逐路径 add，检查冲突清单，运行受影响验证，再按当前操作 `--continue`。若中止，用当前操作对应的 `merge --abort`、`rebase --abort` 或 `cherry-pick --abort`；初始脏工作区的 merge 不保证能完美重建。[git rebase](https://git-scm.com/docs/git-rebase)、[git merge 的警告](https://git-scm.com/docs/git-merge)

## 推送的是引用与历史

任务包含 push 时，检查目标仓库、分支及可能触发的部署。查看本地相对目标已有的全部提交，而不只看 HEAD；新远端或新历史则审查将送出的完整历史。有大文件或敏感文件曾入库时转到清理参考。

普通推送用明确 refspec，例如：

```sh
git push --dry-run REMOTE HEAD:refs/heads/TOPIC
git push -u REMOTE HEAD:refs/heads/TOPIC
```

dry-run 只能预览部分推送行为，不证明服务端所有 hook、CI、权限或敏感检查都能通过。默认不推 `--all`、`--mirror`、`--tags`，不把“做了 commit”表述成“已上传”。被 non-fast-forward 拒绝时重新 fetch 并审查新增提交；不能升级为 force 来完成普通同步。[git push](https://git-scm.com/docs/git-push)

## 多人、多 AI 与 worktree

并行任务各用自己的工作目录和分支；先查已有 worktree 与分支占用，再按正确基线建新 worktree。分支树只含该基线的已提交内容，需要原工作区改动时精确迁移；依赖、ignored 配置与运行环境也不会自动具备。[git worktree](https://git-scm.com/docs/git-worktree)

worktree 共享对象库和部分仓库状态，并非完整沙箱。共同的 refs、remote 操作和配置要协调；不在另一任务使用的分支上 reset/rebase，也不替它清理目录。完成后先核对未提交和 ignored 的必要文件，再安全移除工作区。宿主有管理工具时遵守宿主管理方式。

## PR、合并与发布

PR/MR 明确源与目标分支；描述实际问题、最终行为、验证及兼容/迁移影响，遵平台模板。检查完整 diff 是否只含本次范围，草稿可提前供审查，但不能把未通过门槛的工作说成可发布。[GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow)

合并方式遵项目：merge 保留分支结构，squash 将逻辑任务压成一个提交，rebase merge 重放提交并保持线性。squash 或重放会改变提交 ID，后续核对是否已整合不能只依赖祖先关系或 `branch --merged`。采用基于标题的发布自动化时检查最终进入目标分支的标题，例如 squash PR 标题。

发布前确定 commit/tag、版本、变更日志、包内容、构建和平台要求的验证；审查归档或打包输出不含本地配置与多余内容。已发布 tag 不随意移动；修复一般创建新版本，并向仍受影响的开发/维护线回流。只推明确的 tag；发布网页、发布包、部署系统是独立动作，按任务授权执行。公共接口与版本兼容规则见 [SemVer](https://semver.org/)。
