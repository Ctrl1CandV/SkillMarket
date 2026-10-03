---
description: 论文阅读入口：读这篇（链接/arXiv ID/PDF）、快速判断、重点讲解、继续阅读，或拉当日 arXiv 新论文分级简报。
argument-hint: "[论文链接/ID/PDF 路径或自然语言意图，可省略=每日发现]"
skill: grad-radar
---

按用户意图路由（协议见 grad-radar 技能）：

- **带论文指向**（链接/arXiv ID/PDF/标题）或「帮我读/值不值得读/讲详细一点/继续上次那篇」→ 单篇阅读流程：`reading_record.py show` 查已有记录（有则复用进度与背景）→ 按阅读协议取内容、定三档深度（quick 快速判断 / standard 标准阅读 / deep 重点精读）→ 按笔记模板产出 → `register`+`save-note` 落盘（人工批注与旧稿受保护）。用户明确表达读完/暂缓才 `set-status`；生成笔记不等于读完。
- **省略参数或问「今天有什么新论文」**→ 每日发现：radar_config 初始化/校验后跑 `arxiv_fetch.py --config`（配置真实生效），按 tiering 规则分级写当日简报（已存在不静默覆盖），正文数量以配置 daily_caps 为准（默认低负担起点，不足不凑数）；用户选中的论文回到单篇流程。

无法唯一定位「上次那篇」时列候选请用户确认，不猜 ID/DOI/路径。
