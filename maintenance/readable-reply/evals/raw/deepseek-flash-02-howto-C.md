Git push 被拒，是因为远端有你本地没有的提交。先别慌，也别急着 `--force`；一旦强制推送，别人的提交就会丢。先看清楚情况再动手。

**第一步：先确认远端实际内容**

```bash
git fetch origin
git log --oneline --graph --all -20
```

看你的分支和 `origin/你的分支` 在哪里分叉，远端多了哪些提交。

**第二步：按情况选方案**

1. **远端新提交是你本该拉取的**（别人推的，或你在别的机器推过）：最常用
   ```bash
   git pull --rebase origin <分支名>
   git push
   ```
   用 rebase，避免多出一条毫无意义的 merge 提交。

2. **本地和远端改的是同一处、冲突了**：rebase 中途会停下来，手动改冲突文件后 `git add` → `git rebase --continue`，推完再 push。

3. **确实要让远端变成你本地的样子**（常见于自己分支、确认没别人的提交）：
   ```bash
   git push --force-with-lease
   ```
   用 `--force-with-lease`，不用 `--force`。前者在远端被别动过时会拒绝，是安全网。

4. **不确定远端提交有没有用**：先备份再动
   ```bash
   git branch backup-$(date +%s)
   ```
   有备份就可以随意 rebase / force，出事能回。

**几个坑**

- 共享分支（`main`/`develop`）优先想办法合并，别 force。
- 如果 push 被拒是因为**远端设了保护分支或需要 PR**，上面的推送命令都会失败，得走合并请求流程。
- `git pull` 默认可能是 merge，会产生噪音提交；建议长期设一次 `git config --global pull.rebase true`。

如果愿意的话，把分支名和 `git log --oneline --graph --all` 的输出贴出来，我可以帮你判断该用哪条路。