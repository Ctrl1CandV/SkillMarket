先别用 `--force`，`non-fast-forward` 表示远程有你本地没有的提交，最稳妥是 `git pull --rebase` 再推。

```bash
git pull --rebase origin <分支名>
git push origin <分支名>
```

`--rebase` 会把你的本地提交“挪到”远程最新提交之后，保持历史线性、避免多出一个 merge commit。如果 rebase 中出现冲突，解决后 `git add <文件>`，然后 `git rebase --continue`；想放弃就 `git rebase --abort` 回到原状。

确认推送安全（远程那些提交确实该保留、你自己没强推需求）之前，不要用 `git push --force`；如果确实要改写远程历史，用 `--force-with-lease`，它会在远程被别人更新时拒绝，比 `--force` 安全。
