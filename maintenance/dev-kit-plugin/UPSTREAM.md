# 来源与本地改动

## mattpocock/skills（MIT 许可）

固定在提交 `5863806dd4e15c63174bee4e7515a4256792ecfa`（2026-11-12）。同步新版时，拿这个提交和对方的新版做 diff，再把下面列出的本地改动重新套上。

两处都没有带上 `agents/openai.yaml`（Codex 界面的显示名），因为本仓库的技能统一不放宿主专用文件。

### tdd（skills/engineering/tdd）

`SKILL.md`、`tests.md`、`mocking.md`、`LICENSE` 原样复制，只在 `SKILL.md` 改了三处：

1. frontmatter 加上 `license` 和 `metadata`（版本号、来源）。
2. “call the Skill tool with "codebase-design"” 改为 “use the `codebase-design` skill”。原句是 Claude Code 的说法，其他宿主没有 Skill tool。
3. “see the `code-review` skill” 改为 `dev-acceptance`（没有装 Matt 的 code-review），并在后面补了一句：有确认单时，按其中的验收条目和测试档位决定测什么。

### codebase-design（skills/engineering/codebase-design）

`SKILL.md`、`DEEPENING.md`、`DESIGN-IT-TWICE.md`、`LICENSE` 原样复制，改了以下几处：

- `SKILL.md`：
  - frontmatter 加上 `license` 和 `metadata`；
  - description 加了 “compare alternative interfaces ("design it twice")”，接替 design-an-interface 的触发；
  - “Going deeper” 里的子代理改为 “in parallel sub-agents when the host has them”。
- `DESIGN-IT-TWICE.md`：并入本机旧技能 design-an-interface 的要点：
  - 新增 “Scale it to the decision” 一节：小决定自己画两版；宿主没有子代理时逐个自己写；方案之间要在形状上不同，而不只是改名字；不凑数。
  - 每个方案的产出补充两项：错误与资源由谁负责，以及对现有调用方的迁移成本。
  - 推荐部分补充两点：选满足实际需求的最简方案；用户要求后才开始实现。

## alirezarezvani/claude-skills（MIT 许可）

code-reviewer 的 `rules/`、`languages/`、`scripts/` 原样复制自 `engineering-team/skills/code-reviewer`，固定在提交 `7b1abd5e8aff00ecb66e38956274586cb22ad681`（2026-10-26），并附上对方的 `LICENSE`。对方的 `SKILL.md` 和 `README.md` 没有采用。`assets/` 和 `expected_outputs/` 只是脚本的回归样本，移到了 [code-reviewer-fixtures/](code-reviewer-fixtures/)。

用户本机 `~/.agents/skills/code-reviewer` 的情况：
- 和对方旧版比较（忽略换行差异）：除 `code_quality_checker.py` 有 134 行不同外，抽查的其余文件都相同。新版的这个脚本多了 C 语言支持。
- 那份 `SKILL.md` 是用户早先的改写，本仓库新的中文正文以它为底，加上了 Matt 的 code-review 里那组坏味道清单。

三个脚本这次没有运行过：运行刚下载的第三方脚本被权限拦下。只核对了内容：调用外部程序的只有 git 和同目录的另一个脚本，不联网，不删文件。

## 本机旧技能

`~/.agents/skills/` 里的三份没有动。pi 的配置按名字引用其中的 diagnose 和 code-reviewer，新版保留了同样的名字，以后替换时直接覆盖即可。

- **diagnose**：重写。骨架取自 Matt 的 diagnosing-bugs（同一个固定提交），保留旧版这几条：按问题大小取用、报告复现率、性能问题先测基线、分清原来就失败的和这次弄坏的、只跑了局部就说局部。
- **design-an-interface**：并入 codebase-design，不再单独保留。
- **code-reviewer**：见上一节。
