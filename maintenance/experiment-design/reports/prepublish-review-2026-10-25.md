# experiment-design 提交前独立复查

日期：2026-10-25。用户授权独立复查通过后，将运行资源提交并推送 main、dev，将计划与验证资料仅提交 dev。frontend-craft 候选不在本次发布范围。

## 审查范围与结果

未参与初版编写、未继承会话历史的代理，审查了三个运行文件、初版报告和合成响应、skill-eval 立案、开发计划及 README 索引，并核对 idea-ledger/run-provenance 的真实接口。审查者未修改文件或操作 Git；修正由主代理完成，再交还同一审查者复核。

两项发布前问题已修复：

1. 初版报告列出了实际不存在的 `agents/openai.yaml`，并据此宣称验证四个文件和 UI 字段。现按实际三个运行文件更正，不补造验证结果。
2. `measurement.md` 原先泛称复用 run-provenance 的 judge 协议。该旧协议含统一样本量与一致性判断，可能覆盖本技能按研究目标设计的原则。现仅复用逐条记录与适用计算工具，要求核对工具约束，样本量及结论边界仍由当前研究决定。

复核后无剩余阻断项。方法来源及上游许可已核对，未发现复制代码、模板或成段指令；Skill 能在未安装其他科研技能时独立完成计划，未把计划当 run、未让模型代替人工作台账判定。skill-eval 仍只有 dev 计划，academic-writing 与 backend-reliability 未提前实现。

## 验证边界

`quick_validate.py` 通过；范围内文档的 UTF-8、末尾换行、尾空格、相对链接及 diff 检查通过。已有合成行为记录是一次设计回复，不能证明真实成本、统计功效、执行入口或跨任务效果；真实研究验收仍待开展。

## 分支范围

- main、dev：`plugins/grad-companion-plugin/skills/experiment-design/` 的三个运行文件与根 README 索引。
- 仅 dev：experiment-design 的维护记录、`maintenance/ROADMAP.md`、`maintenance/skill-eval/PROPOSAL.md` 及 maintenance 索引中的对应条目。
- 不纳入：frontend-craft 运行文件、评测、历史存档和相关索引改动。

提交标题沿用仓库“月.日 对象：具体变化”的格式；运行资源与维护资料按分支职责拆分，不整合整个 dev 到 main。
