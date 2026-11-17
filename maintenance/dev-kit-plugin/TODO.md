# dev-kit-plugin 待办

- [x] 用户在 Codex（gpt-6.1-sol）里正式开发图论课程设计（2026-11-17）：开工、实现、独立审查都走通，用户认为效果可以。dev-kickoff 和 dev-acceptance 通过这一轮验收，见 [REPORT](evals/2026-11-17-shortest-path/REPORT.md)。
- [ ] tdd、codebase-design、diagnose 还没在真实任务里用上，等遇到需要先写测试的核心逻辑或难查的 bug 时再看。
- [ ] Codex 里装着 superpowers 插件，它的测试先行、完成前核验、规划和 dev-kit 有重叠，要不要在 Codex 里停用，由用户决定。
- [ ] 用户 Python 的 site-packages 在 Codex 会话期间（22:38）新装了 edge-tts 及其依赖，Codex 的记录里没有对应的安装命令，来源待用户确认。
- [x] pi + deepseek-flash 试用（2026-11-17，开工由优化者代答）：开工、实现、子代理审查都走通了；看到的 4 个问题已在 0.1.1 补上，见 [REPORT](evals/2026-11-17-shortest-path/REPORT.md)。0.1.1 还没重跑。
- [ ] code-reviewer 的三个打分脚本：在课程设计的代码上运行一次（需要用户同意运行第三方脚本），能查出实际问题才保留。
- [x] Codex 的提问工具：VS Code 里的 Codex 在默认模式下用的是 request_user_input_async，可以带选项，用户也能自己写回答（2026-11-17 实测）。
- [ ] 待核实：Antigravity 和 ZCode 有没有提问工具和子代理，它们的用户技能目录在哪。
- [ ] 留给负责安装的 Agent：
  - 把技能装进其余宿主（2026-11-17 已按用户要求装进 Codex 的 `~/.codex/skills`）；
  - 用新版替换 `~/.agents/skills` 里的三份旧技能，design-an-interface 删除；
  - 在各宿主的全局说明里加一行提醒：开发新功能前用 dev-kickoff，提交前用 dev-acceptance。
