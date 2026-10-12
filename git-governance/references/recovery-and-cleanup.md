# 清理、回滚与恢复

## 先识别对象，再选择操作

“不上传”与“可删除”没有等价关系。缓存可能可重建，本地数据库、实验结果、ignored 的配置和私人草稿可能没有任何其他副本。Git 也不能恢复从未记录过的普通文件。

| 用户目标 | 优先动作 | 风险与前置事实 |
|---|---|---|
| 从提交里撤下文件，保留当前修改 | 已有 HEAD 时 `git restore --staged -- PATH` | 只改变 index；不同时带 `--worktree`；无首次提交时用适合初始 index 的操作 |
| 已跟踪文件以后只放本地 | ignore + `git rm --cached -- PATH` | 保留当前工作区，提交删除版本树路径；历史仍在 |
| 撤销已经共享的普通提交 | `git revert COMMIT` | 生成反向提交，可能冲突；不会清除敏感历史 |
| 整理仅自己使用的未共享提交 | amend/rebase，先保留恢复引用 | 改变 commit ID；确认范围、工作区和他人依赖 |
| 丢弃指定未提交修改 | 核对 diff、必要备份后定向 restore | 工作区 restore 会覆盖相应修改；这是删除工作，不是取消暂存 |
| 删除可重建的未跟踪文件 | 指定路径的 clean dry-run，再清理 | Git 没有普通文件的回收站；先确认预览名单 |
| 清理已合并本地分支 | 核对已整合及未使用的分支后 `branch -d` | squash/rebase merge 可能让安全删除检查拒绝，不能直接升级 `-D` |

命令语义依据：[git restore](https://git-scm.com/docs/git-restore)、[git rm](https://git-scm.com/docs/git-rm)、[git revert](https://git-scm.com/docs/git-revert)。`revert` merge commit 需要先确定主线 parent，并影响后续再次合并的语义，不机械使用 `-m 1`。

已有明确授权就按其范围执行；别因操作出现在风险表里又重复问一次。若“清理”范围不明，先完成清单、预览、影响说明和可逆修改，再对确实缺少授权的删除、覆盖、远端删除或共享历史重写确认具体对象。不能把一次批准扩展成以后所有破坏性操作。

## 未跟踪文件清理

以确认可重建的路径为边界，先预览：

```sh
git clean -nd -- path/to/disposable-output/
```

检查输出确实都是目标，必要的副本已保存且范围已获授权，才把同样的命令改成 `git clean -fd -- path/to/disposable-output/`。执行前若文件或路径状态发生变化，重新预览。

`-X` 只选 ignored 文件，`-x` 连 ignored 文件一起选；都可能删除真实 `.env`、本地数据和虚拟环境。ignored 不表示可再生成。禁止把 `git clean -fdx` 当通用的“修复构建/同步/提交失败”手段，不用 `-ff` 越过嵌套仓库保护。[git clean](https://git-scm.com/docs/git-clean)

如使用文件系统删除，解析并检查真实绝对目标属于获准目录；防止路径拼接、符号链接或 junction 越界。Windows 使用同一 shell 的原生路径操作，如 PowerShell `-LiteralPath`，不要把枚举路径拼接进另一个 shell 执行。不要通过删除 `.git`、手动修改其内部对象或 `gc --prune=now` 来“清理项目”。

## 保全与恢复的实际边界

变更前根据目标保全：已提交历史可建恢复分支/tag；未提交文本可以保存 diff（包括 staged 与 unstaged 两部分）；未跟踪、二进制、ignored 内容要另用合适备份。单独一份普通 diff 不能覆盖所有这些内容，Git bundle 也不保存工作区文件。

stash 默认不包含 untracked；`-u` 增加 untracked，`-a` 还包含 ignored 并会从工作区移除它们。不要盲目 stash 所有人的改动或把真实密钥纳入 stash。必要时按路径选择并记录 stash 标识，恢复优先 apply、检查，再 drop；不要自动清空全部 stash。[git stash](https://git-scm.com/docs/git-stash)

误删分支或移动 HEAD 时，先查看 `git reflog`、`git log --all`，确认目标提交后建恢复引用，再决定工作区如何恢复。reflog 是本地记录且会过期，不能保证恢复所有历史或未提交文件；不要把 `reset --hard` 当找回工作的第一步。[git reflog](https://git-scm.com/docs/git-reflog)

丢失文件若从未 add/commit/stash，优先查看编辑器历史或实际备份，不承诺 Git 可恢复。被删除分支中未整合的提交要先保留引用；远端删分支只删引用，不保证清除所有对象或第三方副本。

## 普通拒绝与强推分开处理

non-fast-forward、保护规则和 hook 拒绝分别查原因。普通修复先 fetch/整合/补检查；不改 force、不禁用 hooks、不关闭保护来绕过拒绝。

任务明确需要替换共享历史时，先准备可审查的结果，记录受影响 remote/ref、当前远端完整 OID、预期新历史和协作恢复方案。有范围明确的授权后再执行。普通历史整理保留旧引用；泄露事件的备份只能保存在受控位置，别又公开备份分支。

用指定预期 OID 的 lease 限制覆盖范围；下列大写项是需要替换的占位符：

```sh
git push --force-with-lease=refs/heads/TOPIC:EXPECTED_OID REMOTE HEAD:refs/heads/TOPIC
```

`EXPECTED_OID` 必须是实际查得并审查过的远端值。不能只复制一个看似正确的旧值；远端在准备期间有新增提交时重新审查。裸 `--force-with-lease` 依赖远端跟踪引用，后台 fetch 可削弱它的保护。lease 只检查引用的预期值，不证明替换内容正确，也不是授权。[git push 的 lease 说明](https://git-scm.com/docs/git-push)

## 凭据或私密数据进入历史

1. 停止继续传播，说明受影响路径、提交/分支和可见范围；不在聊天、日志或 issue 中重复内容。未经确认不要向平台上传样本“验证”。
2. 凭据已经暴露时首先撤销或轮换。没有账户权限就清楚说明需由持有人处理；不能把“删除文件”说成“凭据已失效”。
3. 查清内容是否仅误暂存、进入未共享本地提交，还是已推送/存在于 PR、tag、缓存、LFS 或副本；前两者可在正确范围整理，已共享历史需要平台与协作者配合。
4. 建立未来忽略/本地配置方案，并根据暴露程度决定是否需要历史移除。只修改 `.gitignore`、再提交删除或 revert 都不会清掉旧内容。
5. 必须历史清除时使用当前平台官方流程和合适工具，在受控副本先检查结果，明确所有受影响 refs 与副本处理，再按授权更新远端；避免随意拼接全库重写命令。无法控制 fork、他人 clone 或缓存时如实记录限制。

处理顺序及历史重写限制见 [GitHub 移除敏感数据指南](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)。GitHub 的具体缓存/支持流程不外推到其他托管平台；相关账户和服务操作需按用户授权完成。

## 分支和工作区退役

删除前核对是否有未整合提交、活动 PR、下游依赖或其他 worktree 占用。对于 squash/rebase 合并，确认等价变更已进目标分支，并保留必要引用，不为让 `-d` 成功而造假 merge。远端删除需确认具体 remote/ref 和任务授权；本地删分支不等于远端删除。worktree 删除先检查 ignored 的必要文件，不用 force 擦除未交付工作。
