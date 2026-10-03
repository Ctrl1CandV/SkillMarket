---
description: 登记实验 run、绑定 claim、生成 mean±std 表或做论文数字一致性核对。
argument-hint: "<登记|表格|核对> [参数]"
skill: run-provenance
---

按意图分流：judge 一致性验证则跑 judge_agreement.py（κ 只算数不下结论，协议先读 references/judge-protocol.md）；camera-ready 前发布包则跑 repro_pack.py（MISSING 如实标注不猜）；登记则跑 run_register.py（路径只从用户原话取，缺 seed 记 null；失败 run 用 `--status failed --failure-reason` 如实登记）；绑定 claim 则跑 claim_register.py add（多 seed 绑全部 run 不挑最好的；人的判定走其 support 子命令，--by 必须来自用户原话，agent 不得代填）；表格则跑 table_gen.py（默认排除失败 run，n=1 标注不伪造误差，指标键漂移只告警）；核对则跑 claim_check.py（台账自检报 evidence 五级，--draft 另做草稿数字回查报 found/suspected_drift/unbacked 候选），输出是机械核对证据不是审稿意见，只报告不改稿。
