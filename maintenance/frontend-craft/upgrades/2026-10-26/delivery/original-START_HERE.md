# SkillMarket 两技能升级交付包

本包将前面的“补足缺失能力”和“修订现有规则”合为一轮升级。可直接使用的候选文件位于 `runtime/`；需要在项目环境中完成的参考画面、渲染和新旧版本使用验证，已有两个独立 Codex 提示词接手。

**当前状态：候选实现已生成，尚未完成效果验收。** `frontend-craft` 为 `0.5.0-rc.1`，`product-design` 为 `0.2.0-rc.1`。RC 用来区分文件交付与经过实际运行验证的稳定版本。

## 包内位置与去向

| 包内位置 | 内容 | 放置位置 |
| --- | --- | --- |
| `runtime/frontend-craft/` | 完整候选技能、参考、索引与离线样式样张 | 仓库的 `frontend-craft/` |
| `runtime/product-design/` | 完整候选技能与三个参考文件 | 仓库的 `product-design/` |
| `dev-only/maintenance/frontend-craft/upgrades/2026-10-26/` | 本轮计划、要求、执行与终审提示词、对比任务、检查工具和交付状态 | **dev 分支**的 `maintenance/frontend-craft/upgrades/2026-10-26/` |
| `baseline/` | 本轮读取的旧版两个技能，共 12 个文件 | 对比用的独立目录；不覆盖新技能，不放入 main |
| `manifest.json`、`SHA256SUMS` | 包内文件用途、基线与校验值 | 交付记录；不属于运行技能 |

仓库 README 约定：main 只放技能、插件和说明等运行资源；维护、测试与升级材料留在 dev 的 maintenance。本包依此分开。不要把压缩包整体复制进 main，也不要把 `runtime` 作为技能的父级目录一并安装。

## 推荐执行顺序

1. 阅读[本轮计划](dev-only/maintenance/frontend-craft/upgrades/2026-10-26/PLAN.md)与[当前交付状态](dev-only/maintenance/frontend-craft/upgrades/2026-10-26/DELIVERY_STATUS.md)，了解哪些已完成、哪些还待实测。
2. 保留自己的现有改动。在 dev 或由 dev 建立的独立工作树中，将两个 `runtime/` 子目录对应合并到仓库根目录；当前文件若与基线不同，先比较并合并，不直接覆盖。
3. 将本包 `dev-only/maintenance/` 合入 dev 的 `maintenance/`。将 `baseline/` 放在独立评测工作目录；告诉执行者其实际路径。
4. 在仓库中启动 Codex，把[补全与实测提示词](dev-only/maintenance/frontend-craft/upgrades/2026-10-26/prompts/01-complete-and-evaluate.md)全文发送给它，并提供本包解压目录。它会补充外部参考画面、渲染样张、运行隔离的新旧版本比较，并修复发现的问题。
5. 上一步完成后，在**新的 Codex 会话**中发送[独立终审提示词](dev-only/maintenance/frontend-craft/upgrades/2026-10-26/prompts/02-final-review.md)，同时提供仓库、解压目录和执行报告位置。终审按原始证据判断这一轮能否结束。
6. 只有终审为 PASS，才考虑由你按仓库流程将运行文件纳入 main 或改成稳定版本。提示词没有授权自动推送、合并或发布。

## 先预览样张

解压后直接打开 `runtime/frontend-craft/assets/style-lab/index.html`。它是离线原创样张，不需要下载字体或依赖。三套主题共享演示内容，可查看阅读、列表和组件状态。所有业务内容均为演示；不表示真实研究或远程业务能力。

样张源码交付不等于画面已经验证。本轮交付环境未能取得可运行浏览器，实际渲染、字体回退、窄屏与操作检查由第 4 步完成。外部范例索引也没有把候选或方法资料写成已经视觉核验的截图。

## 静态检查入口

在解压目录运行：

```sh
python3 dev-only/maintenance/frontend-craft/upgrades/2026-10-26/tools/check_package.py --package-root .
```

迁入仓库后，可运行同一工具并指定 `--repo-root /实际仓库路径`。补全画面索引后再加 `--release` 检查资源证据的结构门槛。该命令不判断美观或任务完成；最终结论仍由独立终审结合实际画面与操作给出。

## 其他材料

- [逐项要求](dev-only/maintenance/frontend-craft/upgrades/2026-10-26/REQUIREMENTS.md)：遗漏检查和追踪位置。
- [验收要求](dev-only/maintenance/frontend-craft/upgrades/2026-10-26/ACCEPTANCE.md)：证据、比较方法及终审结论。
- [参考来源](dev-only/maintenance/frontend-craft/upgrades/2026-10-26/SOURCES.md)：借鉴了什么，以及没有据此推断什么。
- [对比任务说明](dev-only/maintenance/frontend-craft/upgrades/2026-10-26/evals/README.md)：同条件旧版与候选版的运行方法。

