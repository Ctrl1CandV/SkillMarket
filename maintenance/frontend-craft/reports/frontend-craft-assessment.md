# frontend-craft 首版评估

> 归档说明（2026-10-03）：本文保留历史测试正文与当时路径。小样和测试现位于 `maintenance/frontend-craft/evals/`；当前可执行命令为 `node "D:/Program Project/SkillMarket/maintenance/frontend-craft/evals/check.mjs"`。本迁移不追加或改变原报告的验证结论。

日期：2026-10-03；版本：0.1.0；结论：**技能草案、分场景参考与两个 Web 小样已完成；主会话已补充真实浏览器加载、搜索空状态与视口尺寸证据，但完整视觉和交互验收未通过，不能宣称首版视觉质量已验证。**

## 范围与交付

仅写 `D:/Program Project/SkillMarket/frontend-craft/` 及本报告。没有修改 ResearchWorkbench、已安装技能或其它业务目录，没有 Git 提交。工作区原有 de-ai-flavor、readable-reply、.zcodeignore 等变更均保持原样。

- `frontend-craft/SKILL.md`：70 行原创入口，任务判断→代表小样→证据→修订，不是 taste/frontend-design 摘抄集合。
- `references/`：workspaces、landing、reading、verification、boundaries、sources 六个按需文件。
- `evals/workbench.html`：搜索/范围筛选/空结果/模拟加载失败及重试。
- `evals/reading.html`：连续中文阅读、目录、混排、对照表、提示展开、来源。
- `evals/cases.json`：本轮两个提示及下一阶段五类测试。
- `evals/check.mjs`：无依赖静态与 mock-DOM 检查，不是浏览器测试。

这两份 HTML 是独立小样，**不是已经改好的 ResearchWorkbench**。没有安装技能到自动发现目录；这是用户指定路径的可审阅源包。没有新会话触发验证或独立模型 A/B 实验。

## 第一轮：来源核验与范围纠偏

加载 skill-creator、frontend-design、官方 browser-use；读取本机 taste 适用范围及相关设计/状态规则。taste 文件过长，工具仅显示前 729 行，不声称读完整 1207 行；第 8 行明确排除 dashboard、data table、multi-step UI。其本机 SHA256：`60386ac793dfa95649c04250e86a0d63f0edc3ca3d4be60bd77782de98b2b382`。

通过 GitHub tree API 核验并通过 raw 读取：

| 来源 | 核验 SHA | 许可与处理 |
|---|---|---|
| oil-oil/oil-ui | af3f16e1f7adca8e968f3c52a2d3232b8e610326 | MIT / oil-oil 2026；方法参考，无源码复制 |
| pbakaus/impeccable | e103efe779e2dd01274dabae83531fef00bf2563 | Apache-2.0 / Paul Bakaus 2025；方法参考，无原文再分发 |
| shadcn-ui/ui | 295a1f114a138f23b5dfee0e0c6812394dfeb90c | MIT / shadcn 2023；只借组件组合思路 |
| radix-ui/primitives | f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae | MIT / WorkOS 2022；只借交互契约 |

更正名称是 oil-ui，不是 oli-ui。oil-ui 当前核验版本为 0.11.0，方案数量按任务决定，并非固定三套；其真实流程包含用户选择/无法交互时默认选择、代表小样、看图与修订。本包不继承自动更新、促销、强制动效，也不继承将“示例”说明从界面隐藏的规则。研究工具必须避免把演示覆盖/进度误当事实。

Impeccable 核验文件为 `.claude/skills/impeccable/SKILL.md` v4.5.0；借 brief 优先、精修保留行为、渐进加载与有界检查，不执行其下载/上下文命令。frontend-design 的内容驱动用于选择，不把“独特、大胆”设为所有工具的主目标。保留颜色/字体/卡片的合理使用，不扩散 taste 的绝对禁令。

WebFetch 实际读取 shadcn data-table 和 Radix Dialog 官方文档：前者说明筛选/排序/分页/选择按具体表格组合；后者说明标题、焦点约束、Escape 与触发器焦点返回。在线文档按访问日核验，不声称和代码 SHA 一一同版。完整 URL、许可边界见 sources.md。无外部图片、字体、品牌 logo、第三方组件源码进入小样。

## 第二轮：只读 ResearchWorkbench

读取 `AGENTS.md`、`docs/SPEC.md`、`docs/BACKLOG.md`、真实 `public/index.html`、相关 styles.css 与 library.js；没有访问 private 数据、没有启动可能写入记录的产品流程。`git status --short` 返回干净。

具体发现（源码证据，不冒充实际看图）：

1. **明确对比度问题**：`D:/Program Project/ResearchWorkbench/public/styles.css:14` 侧栏背景 `#e7eef3`，`:93–102` 快捷链接 hover 改为 `#ffffff`，该规则未同步给深色背景。两色计算对比度 **1.17:1**。这是基于声明颜色的可复现风险；浏览器未验证最终级联和实际 hover 画面，报告不夸成已看图结论。
2. **回访与初次使用的阅读优先级值得验证**：`public/library.js:2443–2444` 指向真正的 `renderHomeReader`，而非下面的 legacy 函数。`:2467–2484` 起步介绍与三步入口先出现，`:2526–2539` 本人在读项随后进入 startBox；`:2572–2595` 又出现多组栏目说明。对回访用户可能需要更快到达在读项；这是任务假设而不是单凭源码断言“首页糟糕”。需同视口截图和找入口任务验证。
3. **已有正确底线应保留**：`public/index.html:16–24` 有命名导航；`styles.css:69–74` 有当前页与焦点；`styles.css:354` 表格局部滚动，`:484` 起有窄屏布局；不能将旧项目概括成“没有响应式/无障碍”。
4. **历史验收不能抵当次实测**：`docs/BACKLOG.md:38–40` 留有全矩阵视觉/真实交互缺口；这是项目自己的历史记录，不是本轮测试结果。`docs/SPEC.md:38` 也明确要求将各类验收分开。

公开目录中未找到可供本轮查看的 PDF/PNG/JPG 样本（没有扫描私人资料作为视觉资产）。因此没有对用户所说 PDF 质量作具体诊断；只建立分页、字体、图表及专门技能交接边界。

## 第三轮：原创实现与设计取舍

不是用两套皮肤证明技能广泛有效，而是两个不同任务切片：

- 工作台：目标是选论文。稳定列表、局部范围展开，冷色工具背景和克制动作色；不放大 KPI 或伪造阅读百分比。公开论文题名加来源，覆盖标签显式“演示”。
- 阅读页：目标是连续理解。单一主文栏、桌面侧目录/手机上方目录、绿色阅读提示、不同信息角色；没有把每段拆成卡片。作者编写的情境明确不是论文原句或实验。

没有用户具体审美画像；这些均是可逆默认。选中文系统字体是覆盖与无依赖考虑，并非宣称用户偏爱某字体。落地页已形成规则但本轮未做第三个小样；原生 App/PDF 不声称由 Web 自动覆盖。

## 第四轮：验证、阻塞与静态修订

### 官方浏览器实际尝试

调用 `mcp__node_repl__js`，按官方技能从宿主环境变量导入 browser-client，准备初始化、列浏览器和读取文档。工具直接返回：

> Browser is not available in subagent

没有获得浏览器描述符、页面快照、截图、视口切换或真实点击结果。没有偷偷用外部 Playwright/截图程序代替官方入口。已将阻塞和小样路径发送协调主会话以便接手；本报告截止时没有主会话验证结果。

因此 **ResearchWorkbench 实际画面、两小样桌面/移动、键盘及可访问性均未通过视觉验收**。不能满足“根据真实截图修一轮”的部分；本轮只做源码/静态自检修订。没有调用文档视觉 judge 检查网页。

### 可复验的已执行检查

运行：

```sh
node "D:/Program Project/SkillMarket/frontend-craft/evals/check.mjs"
```

结果：**39 项静态和 mock-DOM 断言通过**。覆盖 HTML ID/锚点/相对链接、viewport/lang、无外部脚本样式、JS 语法；模拟 DOM 上搜索/范围过滤/清空/空结果、失败和异步重试的输入保留、aria-busy/禁用状态、阅读提示展开/收起；参考链接存在、cases.json 可解析。mock 不模拟布局、浏览器事件默认行为或屏幕阅读器，不能把这些结果算成端到端。

静态复查发现阅读页的可聚焦表格滚动区未纳入自定义 focus-visible 规则，补入 `.table-wrap:focus-visible` 后重跑，同为 39 通过。此为源码修订，不是截图驱动修订。

WCAG 相对亮度公式计算的颜色对比：工具正文白底 13.90:1、工具次级字/页面底 5.96:1、工具链接白底 6.48:1、阅读次级字白底 6.67:1、阅读主按钮 7.38:1。仅涵盖选定声明色，不是整页无障碍认证。

末轮文件 SHA256：
- workbench.html：`0c756700a79084b93f695bfc36fd19a941adf8697a65e0acb668c7fae69465f9`
- reading.html：`2231416146b4885ea14ab2b4a68e5cc1debfd9a34f1bc2cbfefbf6c711b4a8b1`

`git diff --check` 无错误；新文件的静态检查如上。报告与源码无截图文件，避免虚构工件。

## 主会话补充

子代理完成后，主会话已通过官方浏览器加载两个页面、验证搜索空结果、检查390px/1280px文档宽度并生成截图；清空筛选点击超时，图像响应未能支持可靠视觉判断。详见 [browser-smoke.md](../evals/browser-smoke.md)。上文“没有快照或截图”仅描述子代理当时状态，不代表最终主会话未尝试。完整视觉验收及截图驱动修订仍未完成。

## 下一阶段：按优先级补齐，而非继续堆规则

1. 主会话可运行 `python -m http.server 8765 --bind 127.0.0.1 --directory "D:/Program Project/SkillMarket/frontend-craft/evals"`，仅公开两个小样及测试文件，不暴露参考项目。通过官方浏览器进入 `/workbench.html` 和 `/reading.html`。
2. 1280×800、390×844 截图查看（含阅读页下半部）；工作台搜索 ReAct/无匹配、范围筛选、清空、失败→重试；阅读目录与提示展开；Tab/Shift+Tab、200% 缩放；记录实际视口、状态和版本。按观察修一轮并复拍。
3. 浏览参考项目需只读运行/已运行实例，先检查启动副作用；不更改项目配置和本人存储，取当前路由证据。验证 hover 对比及初次/回访找入口任务。
4. 在隔离新会话验证 skill 触发，做有/无技能同提示对照；另测真实资产落地页、局部保行为、320px/400%/长内容/慢请求、PDF/原生交接。没有这些证据，不宣称“普遍优于现有技能”。
5. 邀请用户基于真实画面指出具体喜欢/不喜欢，再形成个人偏好记录；当前只有任务假设，没有用户审美画像。正式分发前由作者选择本包许可，若加入复制材料则补完整上游许可与 NOTICE。

本轮适合交付为“可试用的技能首版草案 + 可运行小样 + 已知验证缺口”，不适合称为“视觉闭环全部完成”。
