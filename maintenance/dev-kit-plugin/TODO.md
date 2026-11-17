# dev-kit-plugin 待办

- [ ] 用户在 Codex（gpt-6.1-sol）里正式开发图论课程设计：开工、实现、收尾，见 [PLAN](evals/2026-11-17-shortest-path/PLAN.md)。技能已装进 `~/.codex/skills`。
- [x] pi + deepseek-flash 试用（2026-11-17，开工由优化者代答）：开工、实现、子代理审查都走通了；看到的 4 个问题已在 0.1.1 补上，见 [REPORT](evals/2026-11-17-shortest-path/REPORT.md)。0.1.1 还没重跑。
- [ ] code-reviewer 的三个打分脚本：在课程设计的代码上运行一次（需要用户同意运行第三方脚本），能查出实际问题才保留。
- [ ] 待核实：Codex 的 request_user_input 在默认模式下能不能用（本机 0.154 的程序里有这个名字，但还没实际调用过）。
- [ ] 待核实：Antigravity 和 ZCode 有没有提问工具和子代理，它们的用户技能目录在哪。
- [ ] 留给负责安装的 Agent：
  - 把技能装进其余宿主（2026-11-17 已按用户要求装进 Codex 的 `~/.codex/skills`）；
  - 用新版替换 `~/.agents/skills` 里的三份旧技能，design-an-interface 删除；
  - 在各宿主的全局说明里加一行提醒：开发新功能前用 dev-kickoff，提交前用 dev-acceptance。
