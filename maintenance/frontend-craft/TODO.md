# frontend-craft 待办

当前版本 0.3.3（运行文件见 main 的 `frontend-craft/`）。0.3 的评测过程与结果见 [reports/frontend-craft-0.3-eval.md](reports/frontend-craft-0.3-eval.md)，0.2.0 的完整副本在 [archive/v0.2.0-2026-10-03/](archive/v0.2.0-2026-10-03/)。

- [ ] Opus 上的开销仍高于无技能组约 50%，目标是 +20% 以内。可以考虑把最常用的规则直接放进 SKILL.md，减少按需读取的参考数量。
- [ ] 盲评样本只有作者一人。找几位不同背景的人做同样的盲评（盲评页在 `evals/v0.3/gallery/` 的脚本可以重新生成），把结果并入报告。
- [ ] `text-autospace` 在 Chrome 上的支持状态，资料之间有冲突，需要查看当前的 MDN 兼容表后确认。
- [ ] 留出案例只用过一次（订单后台）。之后真实使用中遇到的新页面，可以作为新的留出案例。
- [ ] 外部模型（GPT、GLM 等）的效果：`evals/v0.3/inputs/external-prompt-case1.md` 可以直接在对方的工具中使用，结果只作参考。
