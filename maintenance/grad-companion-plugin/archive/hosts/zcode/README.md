# ZCode 适配

本目录是已归档的 ZCode 宿主适配层，仅供维护，不随运行包分发。它只读工作区 `plugins/grad-companion-plugin/plugin/`，产物写到本归档目录 `maintenance/grad-companion-plugin/archive/dist/zcode/`，从不写回主干。下文 `plugin/`、`dist/` 分别指这两个位置。

注：2026-10-04 起工作区主干已去除 `plugin/` 包裹层与清单（用户决定），运行构建前需先调整脚本的读取路径。

## 构建

```bash
cd "/d/Program Project/SkillMarket/maintenance/grad-companion-plugin/archive"
python hosts/zcode/build.py        # 或 uv run --no-project hosts/zcode/build.py
```

构建前会自动扫描 `plugin/`，出现任何宿主专有词即中止。

## 安装（本机）

1. 先跑一次上面的构建，确保 `dist/zcode/` 存在。
2. ZCode 的 **Discover** 标签页 → 右上角 `+` → 添加本地目录：
   `D:\Program Project\SkillMarket\maintenance\grad-companion-plugin\archive\dist\zcode`
3. 在 Discover 列表里找到 grad-companion，点 **Get** 安装。

注意：**添加的是 `dist/zcode/`，不是项目根**——项目根没有宿主清单，加了会失败。

## 开发循环

改 `plugin/` 下的任何内容 → 重新跑 `build.py` → 在 ZCode 里重新安装（或先卸载再装）。
`dist/` 是产物目录，已进 `.gitignore`，随时可删重建。

## 产物布局

```
dist/zcode/
├── .zcode-plugin/plugin.json   # 由 plugin/manifest.json 生成
├── marketplace.json            # 由本目录模板 + 版本号生成
├── skills/<name>/              # 由 plugin/skills/<name>/ 原样复制
└── commands/grad/<name>.md     # 由 plugin/commands/<name>.md 转换（嵌套目录 → /grad:<name>）
```

命令的三处转换：frontmatter 的 `skill:` 改为 `skills:`、正文注入 `$ARGUMENTS` 与技能引导语、文件落到 `grad/` 子目录产生冒号命名空间。
