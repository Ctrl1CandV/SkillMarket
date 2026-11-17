# dev-kit-plugin 维护记录

开发技能组，替代已停用的 agent-parliament。核心是开发前后两头：开工时问清需求、写成确认单；收尾时由独立审查者按确认单逐条验收。中间的实现主要交给模型本身，只配了测试、接口设计、排错和代码审查四个方法技能。

运行文件在 [plugins/dev-kit-plugin/skills/](../../plugins/dev-kit-plugin/skills/)。来源与本地改动见 [UPSTREAM.md](UPSTREAM.md)，待办见 [TODO.md](TODO.md)。

## 组成（0.1.0，2026-11-17）

| 技能 | 作用 | 来源 |
|---|---|---|
| dev-kickoff | 开工追问，产出 `docs/briefs/` 确认单 | 新写；问法改编自 mattpocock/skills 的 grilling |
| dev-acceptance | 开发者自测 → 独立审查者按确认单逐条验收 → 提交 | 新写 |
| tdd | 先写测试，按约定的接缝逐个切片 | mattpocock/skills 原文，只改了引用 |
| codebase-design | 深模块词汇、接口设计两遍 | mattpocock/skills 原文，并入 design-an-interface |
| diagnose | 先有会变红的复现命令，再找原因 | 重写，骨架取自 Matt 的 diagnosing-bugs |
| code-reviewer | 代码质量审查 | 正文重写；规则、语言指南、脚本取自 alirezarezvani/claude-skills |

product-design、frontend-craft、imagecraft、presentation-craft、video-craft 各加了一句“有确认单先读它”。

## 用户确认的决定（三轮追问，2026-11-17）

需求：
- 项目以小型为主：网页前后端、个人小工具、课程设计、研究与实验代码。跨很多次会话的大流程不装，包括 to-spec、to-tickets、implement、wayfinder、triage。
- 要能用在 Claude Code、Codex、pi，以及 Antigravity、ZCode。因此技能写成通用文字；宿主有子代理或提问工具就用，没有也能走完。
- 两头最重要：开头弄清需求和倾向，决定架构、功能和展示；结尾审查验证，并和开头呼应。
- 测试深度按项目的类别、对象和大小定。自用的小网页服务能用、显示效果好就算完成。
- 一个完整的功能点或一次局部重做提交一次，不零碎提交。推送等用户开口。

开工与收尾：
- 提问方式：有提问工具的宿主（Claude Code、Codex）用工具问，给推荐选项，并保留用户自己填写的入口；没有的（如 pi）就在对话里编号列出。
- 开工必问六个方面，其中“审美与展示”是用户特意加的，理由是大部分项目都有被看到的部分。
- 文档按寿命定：短期项目只写确认单；长期项目要有完整的管理文档，并及时更新。
- 收尾：要了解实现才能测的功能测试，由开发者自己做；其余审查必须交给没参与开发的审查者（子代理、子进程或新会话）。可以用同一个模型。

范围与入库：
- 技能组成如上表。
- 新技能、Matt 的原技能、本机三份旧技能（优化后），全部入库统一维护。Matt 的技能保留英文原文，只改指向没装的技能的引用。
- 这一轮不安装，不写安装脚本，也不在各宿主的全局说明里加提醒，这些留给用户以后安排的负责更新的 Agent。
- 用用户的图论课程设计做真实试用，计划见 [evals/2026-11-17-shortest-path/PLAN.md](evals/2026-11-17-shortest-path/PLAN.md)。

## 自检

```bash
PYTHONNOUSERSITE=1 /c/Users/11487/.conda/envs/skillmarket/python.exe -I maintenance/dev-kit-plugin/tests/check.py
```

检查各技能的 frontmatter、名字与目录是否一致，文内相对链接，提到的技能名是否在仓库里，以及外来技能是否附有许可证。只查结构，不能证明技能好用。
