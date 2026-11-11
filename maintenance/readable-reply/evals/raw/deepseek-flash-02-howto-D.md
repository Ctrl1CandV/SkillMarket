`git push` 被拒是因为远程分支上有你本地没有的提交，历史已经分叉了。先拉取并合并，再推送：

```bash
git pull --rebase origin <分支名>
git push origin <分支名>
```

如果不确定具体分支名，直接 `git pull --rebase`（已设 upstream 时能自动识别）。rebase 会把你的本地提交挪到远程最新提交之后，历史保持线性，通常不会产生 merge commit。

如果 rebase 过程中出现冲突，改完文件后 `git add <文件>`，再 `git rebase --continue`；想放弃就 `git rebase --abort` 回到 push 前的状态。

两个前提值得确认：一是确实是你自己独占的分支，共享分支上 rebase 会改写别人的历史，这种情况改用 `git pull`（普通合并）；二是如果只是想覆盖远程、本地提交是对的，得用 `git push --force-with-lease`，它会先检查远程有没有你不知道的新提交，比 `--force` 安全。