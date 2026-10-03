# Claude Code 宿主适配层

> 本适配层已移出运行包，仅供维护。以下命令在 `maintenance/grad-companion-plugin/archive/` 下执行；读取工作区 `plugins/grad-companion-plugin/plugin/`，输出本归档目录下的 `dist/claude-code/`。
>
> 注：2026-10-04 起工作区主干已去除 `plugin/` 包裹层与清单（用户决定），运行构建前需先调整脚本的读取路径。

把宿主中立的 `plugin/` 主干转换为 Claude Code 插件布局：

```bash
python hosts/claude-code/build.py    # 产物 → dist/claude-code/
```

## 产物结构

```
dist/claude-code/
├── .claude-plugin/
│   ├── plugin.json        # name/version/description/author/license + commands、skills 路径
│   └── marketplace.json   # 单插件本地市场包装（source 指向 ./）
├── skills/<name>/         # 与主干同构，整树复制
└── commands/<name>.md     # 扁平放置；命名空间由插件名提供（该宿主规则），frontmatter 已移除 skill: 键并注入 $ARGUMENTS
```

与 `hosts/zcode` 的差异都源于同一个原则：**namespace 是抽象概念，落地由各宿主 build 决定**。本适配层不 import 任何其他宿主的代码。

## 安装（未实测声明）

按公开的 Claude Code 插件规范生成。两种可能路径：

- 插件目录直装：在宿主会话里指向 `dist/claude-code/`（含 `.claude-plugin/plugin.json`）
- 市场方式：`.claude-plugin/marketplace.json` 提供 marketplace 元数据

**验证边界（重要）**：本仓库只能做结构与清单的静态校验（构建自检 + 回归测试的哈希不变量）；真实宿主里的加载、命令注册与 skill 发现**未在本机实测**——首次使用请以宿主实际行为为准，遇到格式出入欢迎回报 issue，修的是这一层的 build.py，主干不动。
