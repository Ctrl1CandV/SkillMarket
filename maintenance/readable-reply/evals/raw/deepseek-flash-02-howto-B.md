non-fast-forward 意味着远程分支有你本地没有的新提交，远端拒绝覆盖，因此不能强推；正确做法是先把远程的改动拉下来，再推送。

```bash
git pull --rebase origin <分支名>   # 把你的本地提交挪到远程提交之上
# 若 rebase 有冲突：解决后 git add <文件>，然后 git rebase --continue
git push origin <分支名>
```

如果不确定远程更新了什么，先运行 `git fetch origin` 和 `git log --oneline HEAD..origin/<分支名>` 查看，确认没有别人的提交会被你覆盖后再 rebase。只有在明确知道自己要覆盖远程，例如刚执行过 amend 或 reset，并且该分支只有你一个人使用时，才用 `git push --force-with-lease`；不要使用 `--force`。