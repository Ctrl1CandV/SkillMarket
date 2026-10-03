# agent-parliament-plugin 上游远端版本核验

核验日期：2026-10-03。本文拆分自当日的两插件联合评估报告，仅按插件重组归属，正文保留；grad-companion-plugin 部分见 `../../grad-companion-plugin/reports/upstream-assessment.md`。本次评估结论为"不收录、不修复"；后续的去 MCP 化派生另见本文末尾与本目录 [agent-parliament-decoupling.md](agent-parliament-decoupling.md)。

## 结论

| 仓库 | 固定版本 | 处理 | 判断 |
|---|---|---|---|
| Ctrl1CandV/agent-parliament-plugin | `3c893b9b8aa11be09df65f0208e1a96d1ab9b81e`；manifest 1.7.0 | **不收录，仅报告** | 项目开发角色设计有价值，但核心多模型执行依赖仓库外 AgentParliament MCP；随附配置绑定作者机器路径、与 README 必需超时配置不一致，依赖没有固定版本；另缺完整许可证文本。按"原样可收录、核心阻塞不修复"的门槛暂不通过。 |

静态结构检查、构建成功及合成数据行为测试，**不等于真实论文阅读效果或完整项目构建的端到端验证**。

## 来源与获取证据（两插件共用，保留原文）

- 先查看 Windows 临时目录（Git Bash `/tmp` 指向相同位置），并在临时目录及存在的 `C:/tmp`、`D:/tmp` 中做有限深度的目标名称搜索，未找到可确认复用的这两个仓库下载。未用旧安装版代替远端。
- `gh` 2.97.0 可执行，但 `gh api` 因未登录、无 GH_TOKEN 失败；没有要求登录或读取凭据。改用公开 HTTPS Git 只读获取。
- 分别执行 `git ls-remote <URL> HEAD refs/heads/main`，随后浅克隆，并以 `git log -1` 确认本地 HEAD。评估结束再次查询远端 HEAD，两个 SHA 均未变化。
- grad-companion：<https://github.com/Ctrl1CandV/grad-companion-plugin/tree/55657c61e96908e7fff85bfe3991fa0f4d74c26e>；提交时间 `2026-09-11T22:56:52+08:00`。
- agent-parliament：<https://github.com/Ctrl1CandV/agent-parliament-plugin/tree/3c893b9b8aa11be09df65f0208e1a96d1ab9b81e>；提交时间 `2026-07-18T12:53:41+08:00`。
- 本次下载及测试区：`C:\Users\11487\AppData\Local\Temp\plugin-assessment-20261003\`。此处副本仅为评估用途，不代表已安装或已批准收录。
- 收录文件通过 `git ls-files` 枚举、逐个 `git show HEAD:<path>` 写出并逐字节比较，共 **49 个受跟踪文件**。没有换行转换或源码修改；未包含 `.git`、`dist`、`__pycache__`、`.pyc`、测试生成数据或其他缓存。（此条描述 grad-companion 的收录核对方式；agent-parliament 未收录，仅做只读评估。）

## agent-parliament-plugin

### 已核验的结构与价值

远端包含 12 个受跟踪文件：7 个 `skills/*/SKILL.md`、中英文 README、`.claude-plugin/plugin.json`、`.mcp.json` 和 `.gitignore`。七个技能都具 name/description；两个 JSON 文件可解析。没有执行脚本、依赖锁文件、服务源码或测试套件。

角色是 orchestrator、project-planner、adversary、code-developer、reviewer、untangler、memory-keeper。调度总纲将需求/方案、对抗、实施、独立复盘、修复、归档串联，按任务规模缩放；CLAUDE/ADR/SPEC/PLAN 分别保存长期约束、架构理由、行为契约、实施及审查证据。代码生产与审查角色分离、计划修订裁决归属较清楚。这些是**提示词协议**，不是随仓库交付的可执行多模型编排器。

### 不收录的核心原因

1. **原样配置缺乏可移植的执行依赖。** `.mcp.json:4-9` 实际执行 `uv run --directory d:\AgentParliament agent-parliament`。核心十个 MCP 工具来自该仓库之外的服务，当前插件既不打包服务，也不固定该服务 commit/版本或可解析的发行依赖；README 的安装说明要求用户另行配置模型端点、密钥和 profiles.json。本机 `D:\AgentParliament` 路径确实存在，故不声称"本机目录不存在"，但存在不代表版本、服务入口和工具契约已确认。本次不读取其私有配置、不启动外部服务、不发送代码或材料给模型。
2. **必需超时说明与真实配置不一致。** README.md:73-90 声称根配置包含 `timeoutMs: 600000`，并明确说必须增加以避免默认 30 秒中断；实际 `.mcp.json` 完全没有 timeoutMs。服务耗时和宿主默认超时未实测，但文件不一致是确定事实，原样配置不能据此保证文档所述长调用链。
3. **服务文档不随插件闭合。** 两份 README 中各有三处 `../AgentParliament/README.md` 相对链接，孤立克隆均不可解析。这不是内部技能文件缺失，而是核心安装与依赖说明指向仓库外的兄弟目录。未按相邻目录猜测其来源来补齐。
4. **许可证交付不完整。** README License 章节和 plugin.json 都声明 MIT，但远端所有受跟踪文件中没有 LICENSE/COPYING，也没有完整 MIT 授权和版权通知。不能等同于"明确禁止使用"，但不足以把一个自己补写的 MIT 文本当作上游授权附件；保守分发门槛下暂不原样收录。

相对链接检查还命中 memory-keeper 中 `plans/PLAN-XXX-描述.md`，经上下文判断是用户项目 SPEC 的模板指针，不是应随插件分发的资源，未列为缺陷。

### 未执行及判断边界

没有启动 MCP、安装外部 AgentParliament、配置 API key、调用模型、生成真实项目、改用户 CLAUDE/SPEC/PLAN、验证角色自触发、验证宿主超时或测试外部工具 schema。本次不能证明该插件与作者的完整环境配套后无法工作；结论仅是**当前指定仓库原样快照不满足本次完整项目构建收录门槛**。依用户要求只报告，不修 `.mcp.json`、不补许可证、不拉入第三仓库。

## 交付范围

- 未收录 agent-parliament-plugin；上游仓库未修改。
- 后续动作：2026-10-03 同日按用户指示完成去 MCP 化派生版（`plugins/agent-parliament-plugin/`，0.1.0），详见 [agent-parliament-decoupling.md](agent-parliament-decoupling.md)。
