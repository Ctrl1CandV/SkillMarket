# git-governance 1.0.0 验证记录

核验日期：2026-10-12。技能目录只放入口、按需参考和项目规范模板；本记录与验证代码按仓库约定保留在 dev 的 maintenance 中。

## 来源与适用范围

已查阅 Git 命令官方手册/FAQ、GitHub flow 与分支保护/敏感信息/LFS 文档、Conventional Commits 1.0.0、SemVer、Gitflow 原作者及其 2020 年反思、npm 与 Cargo 的 lockfile 文档。链接放在技能中各项规则附近。项目类型决策表明确是本技能的建议，不冒充 Git 的统一规定。

技能运行只需能读取 Markdown 和按任务调用 Git，不依赖 Codex、托管平台 MCP、其他技能或本验证脚本。Codex 的 skill-creator 仅用于本次制作和结构验证，没有写成使用者依赖。

## 实际命令验证

环境为 Windows，Git `2.47.0.windows.1`。`evals/check.py` 在自己的临时仓库中运行，无网络访问；每个用例使用独立仓库和虚构内容，清理前核对绝对路径属于自建 fixture。共 9 项通过：

| 用例 | 观察到的行为 |
|---|---|
| ignore 与 cached removal | `.gitignore` 不影响已跟踪文件；`rm --cached` 保留当前文件且不清除旧提交 |
| 取消暂存 | 定向 `restore --staged` 保留工作区修改和其他路径已暂存内容 |
| 初始 index | 尚无 HEAD 时 `rm --cached` 可撤下新增暂存文件并保留本地副本 |
| 定向 clean | dry-run 不删除；定向清理只删除指定可重建目录；`-X` 与 `-x` 能选中 ignored 的本地配置 |
| ignore 否定规则 | 忽略父目录后无法用子目录否定恢复；保持父目录可遍历才可保留 fixtures |
| 归档排除 | `export-ignore` 排除归档中的 maintenance，但版本树仍跟踪该目录 |
| 分支目录差异 | 完整 merge 会把 dev 独有的 maintenance 目录带到 main |
| worktree | 新工作区只带基线提交，不带原工作区未提交修改和未跟踪依赖 |
| 删除后的历史导出 | 最新树已删除的文件仍存在于 bundle 导出并导入后的旧提交中 |

系统默认临时目录的沙箱权限不支持创建测试子目录，改用本次获准的可视化工作目录作为临时根。初次本地 push 用例受 MSYS 子进程权限限制，最终改为 bundle 导出/导入验证可达历史，未执行或声称通过实际远端 push；push 的对象与引用行为另依据官方文档。随后修正测试夹具的 Windows 换行差异，最终完整 9 项运行通过。

运行方式：

```sh
python maintenance/git-governance/evals/check.py
```

默认临时目录不可写时，先在实际 shell 中将 `SKILL_EVAL_TEMP` 设为已存在的获准目录。脚本不是技能执行时必须运行的检查。

## 结构与场景复核

skill-creator 的 `quick_validate.py` 通过；6 个运行用 Markdown 文件的 7 个本地引用均可解析，UTF-8 内容正常；`git diff --check` 通过。

人工复核以下请求的决策路径：

- 个人网站：以一个长期主分支加按需短期分支为起点，不自动建立 develop。
- 多版本 SDK：基于仍支持的版本线建立维护分支，并指定修复回流，分支数量不固定。
- 清理本地数据库/实验输出：先按可重建性和授权分类，不因 ignored 就删除。
- 准备提交但 index 已有用户内容：识别归属并隔离，不能直接 commit 整个 index。
- dev 有维护资料、main 只交付运行资源：遵项目明确约定，检查整合路径与完整发布差异。
- 已删除泄露文件：区分最新树与历史，先安排撤销/轮换，不宣称 ignore 或 revert 已消除泄露。
- 新仓库无 remote/upstream/HEAD：按正常初始状态处理，不自动添加远端或推送。

这些复核不是不同模型的行为评测。未验证真实托管平台的保护规则、发布流程、LFS 传输或模型实际执行表现；后续应基于真实使用修正规则，不把当前测试当作所有 Git 操作的安全保证。
