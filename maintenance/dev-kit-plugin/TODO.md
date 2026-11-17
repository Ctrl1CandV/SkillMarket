# dev-kit-plugin 待办

- [ ] 第一遍试用：图论课程设计，由用户在 Codex（gpt-6.1-sol）里跑开工、实现、收尾，见 [PLAN](evals/2026-11-17-shortest-path/PLAN.md)。
- [ ] 第二遍试用：从第一遍确认过的确认单出发，用 pi + deepseek-flash 做实现和收尾，看弱模型能不能照着走，以及 pi 子代理审查有没有用。
- [ ] code-reviewer 的三个打分脚本：在课程设计的代码上运行一次（需要用户同意运行第三方脚本），能查出实际问题才保留。
- [ ] 待核实：Codex 的 request_user_input 在默认模式下能不能用（本机 0.154 的程序里有这个名字，但还没实际调用过）。
- [ ] 待核实：Antigravity 和 ZCode 有没有提问工具和子代理，它们的用户技能目录在哪。
- [ ] 留给负责安装的 Agent：
  - 把技能装进五个宿主；
  - 用新版替换 `~/.agents/skills` 里的三份旧技能，design-an-interface 删除；
  - 在各宿主的全局说明里加一行提醒：开发新功能前用 dev-kickoff，提交前用 dev-acceptance。
