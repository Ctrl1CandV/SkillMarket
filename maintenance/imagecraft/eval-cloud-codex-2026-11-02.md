# 官方订阅入口验收（2026-11-02）

## 实际结果与未完成项

本轮最多两张的授权下，进行两次独立 exec 调用，没有自动重提或切换模型/账户：**无字素材探针成功取回一张图；正式脚本的中文高密度界面调用因官方控制模型拥堵失败，无图。** 任务 3 的代码与本地回归完成，但“新版 generate 成功生成并取回”和“本轮高密度界面视觉验收”仍未完成，不能用历史界面图或假服务器测试补成通过。再次提交需要新增用户授权。

脱敏数据见 [cloud-codex-v1.json](results/cloud-codex-v1.json)；提示词、原图、原线程回执和原始日志都在仓库外。登录由官方客户端保存和刷新，没有读取 `auth.json`、cookie 或 token，没有使用 API key、购买 credits、修改网络或安装依赖。

## 任务 3.1：exec 能否出图

客户端为 `codex-cli 0.154.0`、ChatGPT Plus；官方 app-server 能力报告 `imageGeneration=true`。无字陶艺 Hero 通过一次官方 `codex exec` 生成，墙钟 **62.911 秒**、returncode 0，取回的原生源文件为 **1536×1024 PNG、2,047,127 字节**，SHA-256：

```text
a52cd926e440ea0a338eefd34fce47ca616cb5f130f1ee85cdd622afe9485bd7
```

关键兼容性事实：exec 的 JSONL 没有原生 image item，最终文本文件也是空的。没有据此重交，而是用 app-server `thread/read` 查询原线程，得到一个 completed `imageGeneration`，其 `savedPath` 和内联结果均存在；从官方 `$CODEX_HOME/generated_images/<thread>/` 的原生路径取回，标准库实际解码、核对尺寸与哈希后发布。

后续审查把元数据清理改为像素/透明度块白名单，先用未知附加块夹具复现泄漏、再修复通过。该原生文件另含 `caBX` 元数据；在新目录另存过滤版 **2,025,234 字节**、SHA-256 `f01edf0882d7ce45b018d582d6f1e77066bf4da67c46473cd9985044c962c0d2`，逐像素字节比较未变，原始文件保留。此为同一张 AI 生成图片的元数据处理，不是重生成或图像修补，也不隐瞒其生成来源。

原图已查看：陶壶、一个奶油杯、亚麻布、右侧主体和左墙留白可用，没有假字或 logo。右边额外花瓶/枝叶作为偏离记录，结论为素材用途可用，不是完美复现。它是探针通路成功，非之后重写的正式 `generate` 成功验收。

准备探针时曾因外部源码副本不完整出现 `ModuleNotFoundError`；发生在任何云端提交前，补齐副本后才做上述唯一调用，不把导入失败算成另一张图。

## 任务 3.2：正式脚本

新增标准库 `cloud_codex.py`、有界 stdio transport 与受限 PNG8 解码器。流程为官方预检 → 保存 attempt=1 → 一次 exec → 原线程读取 native item → savedPath / 原生内联 / 唯一线程目录三路径取图 → PNG 解码与发布 → 额度快照。禁止从 agent 文本或预览臆造产物。

`job.json` 分开记录 submission、generation、retrieval、quota；额度后读失败不抹掉有效图片。新输出目录防覆盖，提示词与显式 PNG 参考以外的项目文件不作为输入。未知结果只能 status/resume 查原线程，连 thread ID 都丢失时也不自动重新提交。模型/seed 未提供就不补造，不把控制模型名当图像模型名。

正式 `generate` 对中文高密度财务视觉稿实际发起一次，拿到了 thread/turn 回执，随后客户端报错。原线程只包含 user message，终态 failed，官方错误为：

```text
Selected model is at capacity. Please try a different model.
codexErrorInfo: serverOverloaded
```

这里没有原生 image item、savedPath 或已取回图片。只使用 `status/resume --wait 0` 查询原线程，attempt 始终为 1，没有照错误提示静默换模型。脚本补充了安全的拥堵分类与回归：generation=failed、failure_code=server_overloaded、state=no_verified_image；不持久化可能含隐私的任意上游错误正文。

早期错误分支当时未保存完整 exec 耗时，不能补写推理秒数；已修正后续代码的 finally 耗时记录。第一张兼容回执的离线 status/resume 与第二张失败线程的在线 status/resume 都已实际执行。正式入口成功闭环仍待下一次明确授权。

## 任务 3.3：本地回归

假官方 CLI 与 stdio JSON-RPC 服务不联网、不消耗订阅。覆盖订阅/API-key 模式拒绝、能力/余量预检、真实 exec 省略 image item 的形态、三种取图、预览和越界路径拒绝、额度后读失败仍保留图片、早/晚丢回执不重提、已存在输出目录、显式参考去元数据、非图工具/多图策略违规、产物篡改及 PNG 完整性。另把本次 `serverOverloaded` 的原线程恢复形态加入回归；不调用 `turn/start` 做重提。

这些测试证明客户端的本地控制流与失败行为，不代替真实服务成功验收；最终全套数量与静态诊断以交接文件末尾执行结果为准。

## 任务 3.4：额度观察

| 调用 | 可见池 | 提交前已用 | 提交后已用 | 说明 |
|---|---|---|---|---|
| 无字素材 | codex；300min / 10080min | 0% / 31% | 2% / 31% | 前后观测，ordinary usage 允许、未触发 spend control |
| 中文界面（拥堵无图） | 同上 | 2% / 31% | 2% / 31% | 立即后读 RPC -32603；表中是稍后原线程查询时的观测，不是即时费用 |

只观察到 codex 桶，不能判断是否有独立图像额度池，也不能证明每张固定消耗或失败零消耗。整数取整、时间差与其他使用都会影响比例。已用和剩余不混说，不把当前能读到额度当成绝不会产生额外消费的保证。

## 文档落地

运行入口、安装与订阅登录、显式上传授权、原线程恢复、取图与额度边界已写入 [云端路径](../../imagecraft/references/cloud-fallback.md)，SKILL 三层表和首用说明同步。保持 dev 交付；未完成的真实成功闭环明确留给审查方与用户决定是否追加授权，不发布 main。
