# dev-kit-plugin 待办

- [x] 用户在 Codex（gpt-6.1-sol）里正式开发图论课程设计（2026-11-17）：开工、实现、独立审查都走通，用户认为效果可以。dev-kickoff 和 dev-acceptance 通过这一轮验收，见 [REPORT](evals/2026-11-17-shortest-path/REPORT.md)。
- [x] tdd、codebase-design、diagnose、code-reviewer 各做一个预先定好标准的小实验（2026-11-17，deepseek-flash，各一次），全部通过，见 [实验结果](evals/2026-11-17-method-skills/REPORT.md)。观察项：tdd 没给每个接缝写“能发现什么”；diagnose 的时好时坏和性能两条路线没测。
- [x] 2026-11-17 按用户决定在 Codex 里停用 superpowers 插件（`~/.codex/config.toml` 中该项 `enabled = false`）。
- [x] 用户 Python 的 site-packages 在 Codex 会话期间（22:38）新装的 edge-tts 及其依赖：用户确认是其他项目装的，与 dev-kit 无关。
- [x] pi + deepseek-flash 试用（2026-11-17，开工由优化者代答）：开工、实现、子代理审查都走通了；看到的 4 个问题已在 0.1.1 补上，见 [REPORT](evals/2026-11-17-shortest-path/REPORT.md)。0.1.1 还没重跑。
- [x] code-reviewer 的三个打分脚本：实验中运行过的那个没有任何真实发现，0.2.0 删除。
- [x] Codex 的提问工具：VS Code 里的 Codex 在默认模式下用的是 request_user_input_async，可以带选项，用户也能自己写回答（2026-11-17 实测）。
- [ ] 待核实：Antigravity 和 ZCode 有没有提问工具和子代理，它们的用户技能目录在哪。
- [ ] 留给负责安装的 Agent：
  - 把技能装进其余宿主（2026-11-17 已按用户要求装进 Codex 的 `~/.codex/skills`）；
  - 用新版替换 `~/.agents/skills` 里的三份旧技能，design-an-interface 删除；
  - 在各宿主的全局说明里加一行提醒：开发新功能前用 dev-kickoff，提交前用 dev-acceptance。
