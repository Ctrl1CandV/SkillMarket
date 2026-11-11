你的 push 被拒绝的原因是：远端仓库有本地没有的提交（non-fast-forward），Git 不会自动覆盖远端历史。

**先确认情况：**
```bash
git pull --rebase   # 把远端新提交拉下来，再把你的提交放到最上面
git push
```

**如果 pull 时出现冲突：**
1. 手动解决冲突文件（搜索 `<<<<<<<` 标记）
2. `git add <冲突文件>`
3. `git rebase --continue`
4. 最后 `git push`

**其他常见处理方式：**

| 场景 | 做法 |
|---|---|
| 你就想 rebase（推荐） | `git pull --rebase` 后 `git push` |
| 想用 merge 提交合并 | `git pull`（默认 merge）后解决冲突再 push |
| 你的提交没用了，要丢弃 | `git reset --hard origin/你的分支` |
| 确认远端历史是错的，要强推 | `git push --force-with-lease`（**危险**，会覆盖他人提交，团队分支禁用） |

**注意：**
- 强推用 `--force-with-lease` 而不是 `--force`，前者会在远端被别人更新时拒绝，更安全。
- 如果只是想强推自己刚 amend 的提交，且分支只有你在用，`--force-with-lease` 是可以接受的。

一般先用 `git pull --rebase`，绝大多数情况都能解决。如果 rebase 后还有其他报错，把完整输出发给我。