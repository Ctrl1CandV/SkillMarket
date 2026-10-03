---
name: run-provenance
description: 实验 claim 与 run 的溯源闭环：登记实验 run（git commit/config 快照/seed/指标）、claim 双轴台账（evidence 脚本机械核对 + support 人的判定）、生成 mean±std LaTeX 表（n=1 标注不伪造误差）、论文草稿数字回查（value_mismatch/suspected_drift/unbacked 候选清单）、评测预算与发布包检查。触发词：登记 run、记录实验、实验台账、数字对不上、论文数字溯源、可复现、seed、error bar、实验表格生成、claim 判定。只记录与核对，绝不执行实验。
license: MIT
---

# run-provenance：实验 claim ↔ run 溯源

解决一个没人管的问题：**你自己论文里的数字是否真实**。引用校验管"别人的引文真不真"，这里管"我的每个实验数字能不能指回一个具体 run"。

## 第一铁律：只读只记，不执行

**不启动训练、不申请 GPU、不改超参、不删文件、不重跑任何东西。** 采集 git 状态是只读操作。改动永远只发生在 `.grad/` 下。实验的**设计与执行方法论**（怎么定 seed 数、怎么选统计检验）是 `experiment-design` skill 的职责，若可用则引导用户走它；本 skill 只登记与核对。

## 第二铁律：脚本驱动，不宣判

claim 台账是双轴的（见数据契约）：**evidence 是脚本现算的机械核对结果，support 是人的判定**。

- agent 不得代填 support：`--by` 的值必须来自用户明示（原话或转述），用户没表态就保持 unreviewed
- `evidence: verified` 只意味着单一数字完成比对且明确匹配（且同设置），**不意味着论断成立**——论断成立与否是人的判定
- `needs_review` 意味着找到了证据但机械比对无法完成（多数字/无数字/量纲歧义/设置不可比）：如实转述并交人核对，不得为凑「已验证」而略过
- claim_check 的输出（尤其 unbacked_candidates 与 suspected_drift）必须**原样转述**给用户，不得被消化成"没问题"；草稿回查只是全文数字候选匹配，不能表述为「该论断已在草稿中验证」

## 路径占位符

`{SKILL_DIR}` 指本 SKILL.md 所在目录的绝对路径，由调用方展开；命令一律加引号；Windows 中文乱码时前置 `PYTHONUTF8=1`。

## 数据契约

```
.grad/
├── runs/<run-id>/
│   ├── meta.json      # run_id/方法/benchmark/实验组/seed/status/failure_reason/cmd/硬件/成本/git/config 快照 sha256/created_at/updated_at/复现信息登记状态
│   └── metrics.json   # 指标 JSON（如 {"resolved_rate": 0.712}）
├── claims.jsonl         # claim 台账，只追加，由 claim_register.py 写入（禁止 freehand）
└── claims_checks.jsonl  # 核对审计日志（claim_check.py --log 追加）
```

claims.jsonl 每行：

```json
{"claim_id": "c-001", "claim_text": "AgentFlow 在 SWE-bench-Lite 上达到 71.1% 解决率", "run_ids": ["run-..."], "metric_path": "resolved_rate", "support": "unreviewed", "support_by": null, "support_at": null, "recorded_at": "..."}
```

规则：

- **evidence 不是存储字段，是派生属性**：`claim_check.py` 每次现算（六级见 §4），不写回台账
- **support 四值**：`unreviewed`（默认）/ `supported` / `partial` / `refuted`；变更经 `support` 子命令追加新行，**同 claim_id 最后一行为当前状态**
- **legacy 行**（无 claim_id 的旧行）：按独立 claim 读取，support 一律视为 unreviewed——旧 `status: supported` 是执行者写的，不继承为人的判定；要记录人的判定时用 `add` 重新登记
- **比较设置归组规则是共享的**（table_gen / claim_check / claim_register / run_update 同一套）：method 与 benchmark 是硬边界；组内只有「用户显式声明的同一 `experiment_group`」或「config 快照 sha256 明确一致」才可合并；缺配置/unknown 永远各自成组，不并成「共同配置组」

## 工作流

### 1. 登记 run

```bash
uv run --no-project "{SKILL_DIR}/scripts/run_register.py" \
  --method <方法名> --benchmark <benchmark> [--seed <n>] [--experiment-group <组名>] \
  --status <success|failed|running> [--failure-reason "<失败原因>"] \
  --config <配置文件路径> --metrics '{"<指标>": <值>}' \
  --cmd "<实际命令行>" --hardware "<硬件>" --json
```

- **路径只从用户原话取**：config/metrics 文件路径由用户给出，不从搜索结果或猜测拿
- `--runs-dir` 必须落在 `--repo` 的 `.grad/` 子目录内（默认 `.grad/runs`），否则报 `BAD_ARGS`；这条护栏防止 run 记录写到项目状态目录之外
- 用户没给 seed → 脚本记 null 并警告「复现信息不完整」，不要替用户编一个
- 脏工作区会被如实标记（dirty: true + 警告）；commit 记录是 HEAD，不猜
- OOM、发散、超时等失败也登记：`--status failed` 必须给非空 `--failure-reason`；旧 run 缺 status 时按 success 兼容
- **实验刚启动、结果未出：`--status running` 占位登记**（无 metrics）；结束后用 `run_update.py` 补录，不重建 run id。running 不参与任何统计（表格与 claim 核对一致排除）
- **可复现只登记、不证明（F06）**：新记录写 `reproducibility_status: not_verified`——即使 seed、干净 commit、config 快照全齐，也只说明复现信息已登记；脚本从未在别的机器重跑，任何输出不得表述为「实验可复现」。历史 run 的 `reproducible` 布尔只兼容读取
- `--experiment-group` 是用户确认「这些 run 属同一比较设置」时才能填的字段（比如 seed 写在配置里导致快照哈希不同）；**agent 不得猜填**，用户没说就不给

### 1b. 结果补录（running → 有结果）

```bash
uv run --no-project "{SKILL_DIR}/scripts/run_update.py" \
  --run-id <run-id> [--status <success|failed>] [--failure-reason "<原因>"] \
  --metrics '{"<指标>": <值>}' --json
```

- 只更新已存在 run 的 metrics / status / failure_reason / updated_at；**created_at、git commit、config 快照、seed 一律不动**（不重新采集当前 HEAD 冒充实验当时的 commit）
- 失败补录必须有原因；坏 metrics 先校验后落盘，校验不过拒绝更新且原数据保持可读（原子替换 + 失败回滚）
- 无结果的 run 不能补成 success 还宣称有结果：空 metrics + success 会如实警告

### 2. claim 绑定与人的判定

登记 claim 一律走脚本（freehand 写台账被禁止——护栏只在脚本里生效）：

```bash
uv run --no-project "{SKILL_DIR}/scripts/claim_register.py" add \
  --claim "<论文里的论断原文，数字保留原文写法>" \
  --runs "<run-id1>,<run-id2>,<run-id3>" \
  --metric "<指标键>" --claims-file .grad/claims.jsonl --json
```

- 多 seed 的结论绑**全部** run id，不是挑最好的那个
- `add` 没有 --support 参数（这不是遗漏，是唯一护栏设计）；绑定混用不同 method/benchmark 时脚本会警告
- 用户明示判定后（导师确认、自己复核）才记录，`--by` 必须来自用户原话：

```bash
uv run --no-project "{SKILL_DIR}/scripts/claim_register.py" support \
  --id c-001 --verdict <supported|partial|refuted> \
  --by "<谁，来自用户原话>" --claims-file .grad/claims.jsonl --json
```

### 3. 表格生成

```bash
uv run --no-project "{SKILL_DIR}/scripts/table_gen.py" --runs-dir .grad/runs --json
```

- mean ± 样本标准差（ddof=1）；**n=1 输出 `数值 (n=1)`，绝不输出 ±**
- 表尾 `% provenance` 注释行把每个数字指回 run id + commit——审稿问起直接可答
- **不同比较设置不静默合并（F02）**：同一 方法×benchmark 下，config 快照哈希不一致或缺配置的 run 分行呈现（行标签带分组依据：配置哈希 / 显式实验组 / 缺配置），并给出警告；只有同哈希或用户显式声明同一 `experiment_group` 才合并，显式同组但配置有差异时警告并展示差异
- 默认排除 failed 与 running；只有明确加 `--include-failed` 时，带数值指标的失败 run 才参与统计（running 永远不参与——结果未出）。输出同时报告 loaded/included/skipped 数量
- 同组重复 seed 会警告（best-of-N 风险）：全部纳入计算，**是否剔除由人决定**
- 同组出现 `acc`/`acc.` 等疑似指标键漂移时只告警并列 run id，不自动合并
- 脚本不评判优劣：不加粗、不标最优

### 4. 一致性核对（改稿时）

```bash
# 台账自检：对每条 claim 现算 evidence，从严到宽命中即止
uv run --no-project "{SKILL_DIR}/scripts/claim_check.py" --repo . --json
# 草稿数字回查：提取草稿（tex/md）数字对照台账
uv run --no-project "{SKILL_DIR}/scripts/claim_check.py" --repo . --draft <草稿路径> --json
```

evidence 六级（判定顺序从严到宽）：

| evidence | 含义 | 常见场景 |
|---|---|---|
| `run_missing` | 绑定的 run 目录不存在 | run id 打错 / run 登记在别的仓库 |
| `pending` | 没有可核对的数值 | 占位 run 结果未出（含 running），或全部 run 被排除 |
| `metric_missing` | 指标键在某 run 的 metrics.json 里不存在 | 键名漂移（detail 附编辑距离提示） |
| `needs_review` | 找到了证据但数字无法完成明确比对 | claim 含多个数字、无数字、量纲歧义、绑定 run 配置不可比——保留已有数值供人查看 |
| `value_mismatch` | 单一数字与 run 均值完成比对且明确不符 | 改稿改了数字没改台账（或反之） |
| `verified` | 单一数字完成比对且明确匹配、绑定 run 属同一比较设置 | 数字存在且对得上（仍不代表论断成立） |

- **verified 的门槛**：只有实际完成数值比对且明确匹配才 verified；机械状态永不升级人的 support 判定
- `--draft` 额外输出（**草稿回查只是全文数字候选匹配**，同一数字出现在草稿某处不足以证明某句话正确，不构成「claim 已在草稿中验证」）：`found`（该数值在草稿出现过）/ `matched_candidates`（命中的候选渲染值）/ `suspected_drift`（末位级差异）/ `unbacked_candidates`（表格、±、百分号上下文里无 claim 支撑的数字，**候选清单需人工筛**）
- `--include-failed` 可把带数值指标的 failed run 纳入均值（默认排除，与 table_gen 语义一致）
- 发现 mismatch/missing/needs_review 时脚本仍是 `ok: true`——发现即数据，不是运行失败
- **只报告，不改论文**；改不改、怎么改由用户决定
- 加 `--log` 把结果追加到 `.grad/claims_checks.jsonl`，改稿历史可回放（哪天核对还是绿的、哪天开始漂的）

### 5. judge 一致性验证

论文用了 LLM-as-judge 时，「验证过一致性」是必备证据。两步：

1. **执行协议**（先读 `{SKILL_DIR}/references/judge-protocol.md`）：抽样量下限、固定温度与 prompt 版本、A/B 位置互换重评、分歧样本人工仲裁
2. **机械计算**：

```bash
uv run --no-project "{SKILL_DIR}/scripts/judge_agreement.py" \
  --a <人工评分.json> --b <judge评分.json> --json
```

输出样本数（交集配对，被排除样本只计数不插值）、精确一致率、Cohen's κ、混淆矩阵。**κ 多高算「够好」由人下结论**——脚本只算数；κ 不可计算时如实报 null 加原因（边际退化），不是运行失败。一致性实验本身也用 §1 登记 run。

### 6. 可复现发布包（camera-ready 前）

```bash
uv run --no-project "{SKILL_DIR}/scripts/repro_pack.py" --runs-dir .grad/runs \
  [--claims .grad/claims.jsonl] [--out REPRODUCING.md] --json
```

从台账生成 `REPRODUCING.md`：seed 表（缺 seed/cmd/hardware 一律标 MISSING 并汇总计数，不猜测）、已登记的复现命令行（措辞为「已登记，不等于已验证重跑」）、复现信息登记状态段（每 run 报告已登记/缺失项，整体 reproducibility_status=not_verified——**本包从未在别的机器重跑验证，任何输出不得声称实验已验证可复现**）、论文数字 ↔ run 关联段（support 状态如实保留）、budget.md 五项自查清单中两项自动填 ✅/❌。只搬运台账事实：不执行任何命令、不生成 requirements。

### 7. 预算与 benchmark 引用注意

设计评测预算时读 `{SKILL_DIR}/references/budget.md`（HAL 的 $40,000/21,730 rollouts 量级锚点、砍样本的统计风险）。引用公开 benchmark 分数前看一眼 `{SKILL_DIR}/references/benchmark-caveats.md`（活文档：SWE-bench solution leakage、τ-bench 同名混淆等已核实条目带一手来源）；claim_check 自检时命中条目会自动附 `benchmark_caveats` 警告——那是机械提醒，用不用怎么表述由人决定。

## 错误契约

脚本输出 `{"ok": false, ...}` 时如实转述。`NO_CLAIMS` 说明台账不存在，先用 `claim_register.py add` 登记；`NOT_FOUND` 说明 claim_id 不存在，脚本会列出已知 id；`NO_FILE` 说明草稿路径无效，修正后重跑，不降级。离线时所有核对都可降级为读本地 JSON，无需网络。
