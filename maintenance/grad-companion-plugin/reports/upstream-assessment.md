# grad-companion-plugin 上游远端版本核验

核验日期：2026-10-03。本文拆分自当日的两插件联合评估报告，仅按插件重组归属，正文保留；agent-parliament-plugin 部分见 `../../agent-parliament-plugin/reports/upstream-assessment.md`。

> 结构更新（2026-10-04）：用户决定移除 `plugin/` 包裹层、`manifest.json` 与 `LICENSE`，仓库仅保留技能与命令本身；本报告描述的是 2026-10-03 核验时的上游结构。

## 结论

| 仓库 | 固定版本 | 处理 | 判断 |
|---|---|---|---|
| Ctrl1CandV/grad-companion-plugin | `55657c61e96908e7fff85bfe3991fa0f4d74c26e`；manifest 0.4.0 | **原样收录**到 `plugins/grad-companion-plugin/` | 内置论文阅读协议、笔记模板、来源与版本记录及人工阅读状态，适合读研阅读与科研积累；双宿主构建和有限离线行为测试通过。不是自动完成研究或完整软件项目的执行器。 |

静态结构检查、构建成功及合成数据行为测试，**不等于真实论文阅读效果或完整项目构建的端到端验证**。

## 来源与获取证据（两插件共用，保留原文）

- 先查看 Windows 临时目录（Git Bash `/tmp` 指向相同位置），并在临时目录及存在的 `C:/tmp`、`D:/tmp` 中做有限深度的目标名称搜索，未找到可确认复用的这两个仓库下载。未用旧安装版代替远端。
- `gh` 2.97.0 可执行，但 `gh api` 因未登录、无 GH_TOKEN 失败；没有要求登录或读取凭据。改用公开 HTTPS Git 只读获取。
- 分别执行 `git ls-remote <URL> HEAD refs/heads/main`，随后浅克隆，并以 `git log -1` 确认本地 HEAD。评估结束再次查询远端 HEAD，两个 SHA 均未变化。
- grad-companion：<https://github.com/Ctrl1CandV/grad-companion-plugin/tree/55657c61e96908e7fff85bfe3991fa0f4d74c26e>；提交时间 `2026-09-11T22:56:52+08:00`。
- agent-parliament：<https://github.com/Ctrl1CandV/agent-parliament-plugin/tree/3c893b9b8aa11be09df65f0208e1a96d1ab9b81e>；提交时间 `2026-07-18T12:53:41+08:00`。
- 本次下载及测试区：`C:\Users\11487\AppData\Local\Temp\plugin-assessment-20261003\`。此处副本仅为评估用途，不代表已安装或已批准收录。
- 收录文件通过 `git ls-files` 枚举、逐个 `git show HEAD:<path>` 写出并逐字节比较，共 **49 个受跟踪文件**。没有换行转换或源码修改；未包含 `.git`、`dist`、`__pycache__`、`.pyc`、测试生成数据或其他缓存。

## grad-companion-plugin

### 结构、技能与实际工作流程

权威清单 `plugin/manifest.json` 列出 7 个 skill 和 7 个命令，runtime 为 Python >=3.12 与 uv；两套 `hosts/*/build.py` 从同一主干生成宿主格式，不应把仓库根直接当已构建插件安装。

- **grad-radar**：指定论文/每日 arXiv 发现 → 阅读协议 → HTML 目录与章节或宿主 PDF/用户文本降级 → quick/standard/deep 笔记 → 主记录和用户批注。重要性、难度、论文类型分开判断，来源、版本、覆盖章节和未核对图表明确记录。AI 生成笔记不等于用户读完。
- **run-provenance**：登记 run、结果补录、claim 与 run/指标绑定、表格聚合、judge 一致性计算及复现材料索引。按设计只读只记，不启动训练；命令和硬件登记不证明实验已复现。
- **idea-ledger**：候选、选择、否决与理由的台账；停滞是计数提醒而非自动选题。
- **weekly-brief**：上一期承诺对账，区分本期发现、AI 整理、人的阅读完成以及实验结果补录。
- **submission-gate**：投稿规则与截稿日期辅助核对，不替代官方 CFP 和人工判断。
- **career-bridge**：从真实实验材料形成项目卡和面试追问；**thesis-cn**：中文学位论文的有限合规检查，不替代校级模板及写作。

已检查七个 skill 的结构、脚本入口、引用与跨技能关系，以及全部 10 个 references 文件的目录/证据边界。阅读核心的 `reading-protocol.md`、`note-templates.md`、`tiering.md` 均存在；各脚本引用有对应源码；weekly-brief 对 idea-ledger 的相对路径存在。submission-gate 提及 `references/judge-protocol.md` 时明确说材料位于 run-provenance，实际文件也在那里，不误判为本地文件丢失。Markdown 本地链接检查未发现此仓库真实断链。

### 许可与依赖

- 根目录 `LICENSE` 包含完整 MIT 授权、免责及 `Copyright (c) 2026 LiuYijie (Ctrl1CandV)`；manifest 与技能许可声明一致。收录保留原始许可证。
- 17 个 Python 文件：2 个构建器、14 个可执行脚本、1 个共享模块 `run_grouping.py`。主要使用标准库；arxiv_fetch、arxiv_html、ddl_fetch 用 PEP 723 声明 `httpx`。
- `httpx` 未锁版本，仓库也没有依赖锁文件，uv 初次运行这些联网脚本可能下载依赖。此次没有安装依赖或修改全局 Python 环境。
- arXiv、ccfddl 是运行期外部公开数据服务；网络故障、索引滞后、网页结构变化需要降级。PDF 读取依赖宿主实际能力，paper-reader/mineru 等只是可选增强。
- 默认状态写到项目 `.grad/`；arXiv seen 台账默认写 `~/.grad-radar/seen.jsonl`。本次没有执行默认联网拉取，测试数据全部指定到临时区。
- 静态执行入口检查没有发现 eval/exec、pickle 反序列化或 shell=True 命令拼接。run_register 使用参数数组执行只读 Git 查询；构建器的删除操作限于其 dist staging/backup 生命周期。此结论不是完整安全审计。

### 本次可复现的安全测试

环境：Windows、Python 3.12.9、uv 0.12.1；测试使用 Python 直接调用、UTF-8 模式及禁写字节码，没有执行真实训练、模型调用或用户项目开发。

1. 所有 17 个 Python 源文件 AST 语法解析通过。
2. ZCode 与 Claude Code 构建器均退出 0，各生成 7/7 skills、7/7 commands；包括构建器自身的主干中立性和结构 lint。产物只留在临时副本，未收录生成目录。
3. 14 个可执行脚本 `--help` 全部退出 0。这仅证明 CLI 可启动，不代表它们的全部业务功能通过。
4. radar_config 的 init/validate 在隔离配置上通过。
5. 合成身份注册后再次注册返回 `created=false`，基础 arXiv 身份去重通过。
6. `save-note --mode deep --basis metadata` 实际降级为 quick 并产生警告，而不是把摘要冒充精读；人的状态仍是 unread。
7. 人工编辑主笔记后普通保存返回 CONFLICT；`--merge` 成功并保留人工文本。
8. 显式 set-status 的合成用户确认以 v3 记录 last_read_version；没有把笔记生成当用户读完。
9. `basis=unavailable` 且未指定 record-failure 时返回 BAD_ARGS，拒绝无材料笔记。
10. 源码 JSON 清单解析通过；仓库本地 Markdown 链接检查通过。

测试过程曾出现两次**测试端断言错误**：首次误把响应字段 `data.created` 当顶层 `created`；其次误以为摘要请求 deep 应非零退出。读取源码和协议后修正断言，复跑上述行为测试通过。没有据此修改插件，也没有将这两次错误归咎于上游。

### 保留的局限与非核心问题

- README 声称的 30+14+15 回归/契约/阅读测试不随仓库分发，本次不能独立复跑那些套件；提交说明或 README 的“通过”不是本次测试证据。
- 未验证真实宿主安装、技能自动触发、命令发现、网络抓取、真实论文全文/图表解析、笔记学术正确性、跨会话恢复、实验统计全路径、周报全链路、投稿规则时效或端到端科研收益。
- 参考材料里的会议规则、面经、benchmark 警示、统计阈值等不视为本次独立核实的事实。尤其 judge-protocol 表中“≤0.40 审稿人默认视同未验证”的概括不能替代领域判断；投稿/学位合规必须回查一手规则。
- thesis-cn 明确承认 GB/T 7714-2025 细则尚未适配，实际速查条款标记 legacy_2015；不能把它宣传为完成 2025 版合规。
- 构建后的 dist 未复制根 LICENSE；本次完整源码收录保留了授权，但如果日后单独再分发 dist，需另行核对许可通知随附问题。本次不补文件、不修构建器。

综合：阅读核心无需未提供的私有执行服务即可形成基本闭环，有限离线测试与文件检查未发现阻断该目标的核心问题，故以明确能力边界原样收录。

## 交付范围

- 新增：`D:\Program Project\SkillMarket\plugins\grad-companion-plugin\`（固定 SHA 的完整原始受跟踪文件，49 个）。
- 未修改上游仓库；未进行 Git 提交、暂存或推送。
