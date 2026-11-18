# modern-web-guidance 维护记录

这是 Google Chrome 团队的前端实现指南（Apache-2.0 许可）。它负责“写得对不对”，包括平台能力、无障碍、表单、浮层、深色模式、动效和性能；frontend-craft 负责“排得好不好”。两者的对照见 [frontend-craft 对照报告](../frontend-craft/reports/mwg-gap-2026-11-18.md)。

## 采用方式（2026-11-18 用户选 B：本地固定版本）

- **包**：npm 上的 `modern-web-guidance` 1.0.1，2026-11-16 发布，约 17 MB，没有依赖，指南全在包里。原样解压到 `%LOCALAPPDATA%\modern-web-guidance\1.0.1\package`，不进仓库。
- **仓库里只放三样**：
  - 改过命令的 `SKILL.md`；
  - 启动脚本 `scripts/mwg.mjs`；
  - Google 的 `LICENSE`。
- **对 SKILL.md 的改动**，在正文开头也有说明：
  1. frontmatter 加上 `license` 和 `metadata`；
  2. 第 1 步、第 2 步和“现代化旧代码”一节里的 `npx -y modern-web-guidance@latest …`，都改成 `node "<本技能目录>/scripts/mwg.mjs" …`；
  3. “Using npx / pnpx”一节换成 “Running the local copy”。

  指南正文和其他步骤一字未改。
- **启动脚本**做三件事：
  - 设 `DISABLE_TELEMETRY=1`，关掉遥测。核对过源码：关掉遥测后，不会再启动上报进程。
  - 把超过 9.5 KB 的输出存进 `%LOCALAPPDATA%\modern-web-guidance\tmp`，不散落在系统临时目录。
  - 找不到包时，打印安装命令并退出（退出码 2），交给用户决定装不装。
- **为什么不用 npx**：本机 npm 的缓存目录配在 `D:\Program Files\nodejs\node_cache`，没有管理员权限建不了这个目录，`npx` 会报 EPERM；另外 `@latest` 不固定版本，前后对比实验会不可比。

## 已安装

2026-11-18 复制到 `~/.claude/skills/modern-web-guidance` 和 `~/.codex/skills/modern-web-guidance`，两处都实际查询过一次。其余宿主交给负责安装的 Agent。

## 更新版本

1. 在 npm registry 查最新版本：`https://registry.npmjs.org/modern-web-guidance` 的 `dist-tags.latest`。
2. 下载并解压到 `%LOCALAPPDATA%\modern-web-guidance\<新版本>\package`。
3. 拿新包里的 `skills/modern-web-guidance/SKILL.md` 和旧版做 diff，把上面三处改动重新套上。注意 `--skill-version` 的值要换成新包 `skill-version.txt` 里的值。
4. 把 `scripts/mwg.mjs` 里的 `VERSION` 改成新版本，再查询一次确认能用。
