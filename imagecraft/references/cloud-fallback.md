# 云端路径：官方 Codex 订阅脚本

核对日期：2026-11-02；实测客户端 `codex-cli 0.154.0`、ChatGPT Plus。入口为 `scripts/cloud_codex.py`，只用 Python 标准库。它通过官方 CLI 生成一次，再用官方 app-server 查询**同一线程**取回原生 PNG；不读取 cookie、令牌或 `auth.json`，不改用 API key。

## 何时使用与首次准备

本机不适合，或需要较高完成度且可接受栅格成果时使用。精确数值、可编辑或要反复修改的成果仍优先原生绘制。提示词和显式参考图会上传 OpenAI，须先得到本次预算与上传授权；私人照片、未公开设计和论文原稿另行确认。

由用户安装官方 Codex CLI：`npm install -g @openai/codex`（需 Node.js），安装动作本身也须批准。用 `codex --version` 检查，再执行 `codex login` 登录 ChatGPT；无图形界面可按官方流程用 `codex login --device-auth`，需要的账户安全设置由用户自行决定，不代为更改。`codex login status` 应显示 ChatGPT 模式，API key 模式直接停止。

当前脚本要求支持的付费 ChatGPT 账户、官方 OpenAI provider、`imageGeneration` 能力以及可观测的 included-usage 余量；不能只按 Plus/Pro 等计划名保证当前账户一定可用。网络、额度与模型拥堵都可能阻止生成。网络故障只报告，不擅自更改代理、DNS 或 hosts。

## 每张图怎么做

先保存合成或已授权的内容契约，再用**全新目录**执行一次：

```text
<python> <skill>/scripts/cloud_codex.py generate --prompt-file <project>/.imagecraft/briefs/hero.txt --output <project>/.imagecraft/jobs/hero-cloud --approve-cloud --wait 600
<python> <skill>/scripts/cloud_codex.py status --job <project>/.imagecraft/jobs/hero-cloud
<python> <skill>/scripts/cloud_codex.py resume --job <project>/.imagecraft/jobs/hero-cloud --wait 600
```

`status/resume` 只查询原线程，不提交新回合；已有图片时先离线核对哈希。`--wait` 是有界等待，不代表服务端必定完成。提示词限 1–12000 字符；最多两个显式 `--reference <authorized.png>`，仅支持可解码的非交错 PNG8，先去元数据再上传。不是 JPEG/WebP 通用入口，也不扫描项目里的参考素材。

流程依次为：官方登录、provider 与能力预检 → 读取提交前额度 → 在 `job.json` 持久化 attempt=1 → 一次 `codex exec` → 原线程取回原生 image item → PNG 解码与哈希 → 提交后额度观测。exec 仅拿本次提示词及显式参考，忽略用户规则，禁 shell、代码执行、搜索、应用和多 agent；控制模型取官方列表的默认项，不把它冒称为底层图像模型。

**拿到文件后仍必须打开看。** 对照字符串、数字、节点和边检查，记录多出的内容；没有视觉能力的宿主只能报告技术校验。脚本输出 `downloaded` 不等于内容通过；人工验收另存工作区记录。本机 CLI 的 `review` 不用于云端任务。

## 为什么不能只看 exec 输出

0.154.0 实测中，成功的 `codex exec --json` 只给 thread/turn 与 agent 消息，省略原生 image item；最终文本也可能为空。这不是“没有图片”，更不能据此重交。脚本用 `thread/read`（必要时列原线程 turns）取得 native `imageGeneration`：优先原生 `savedPath`，其次原生内联结果，最后该线程 `generated_images` 目录中的唯一可验证 PNG。

只有预览、agent 自述或随意找到一个 PNG 都不算产物。取图限制在任务目录或对应线程生成目录，检查大小、时效和路径；标准库实际验证 CRC、zlib 数据和扫描行，而非只看 PNG 文件头。发布的 `image.png` 去除元数据，记录源文件与发布文件各自 SHA-256、尺寸和字节数，不覆盖不同图片。当前限制为 32 MiB 文件、2400 万像素的 PNG8。

## 回执不明与失败

- 已有输出目录一律拒绝新 `generate`。`submission`、`generation`、`retrieval`、`quota` 分开记录；退出码 0 为取图成功，2 为拒绝/失败/无可验证图片，3 为结果不明。策略违规即使有图片也不算成功。
- exec 开始前就写 attempt=1；早期退出连 thread ID 都没拿到时，仍保持 unknown，不自动换目录重提。交官方客户端排查原历史；脚本没有跨目录的服务端幂等保证。
- 已有 thread ID 时用上面的 `status/resume`；它们不会新建 turn。只有预览或尚未落盘时保留原回执，不把超时当失败证明。
- 服务过载也不静默换模型、账户或 API key。本轮第二次授权调用的原线程明确返回 `serverOverloaded`，没有原生 image item；只查询原线程，没有重提。若要再次尝试，须用户重新授权。
- 额度读取失败不抹掉已校验图片；没有图片也不能凭退出码或 agent 消息宣称成功。异常信息尽量用受控类型/错误码，原始 stderr 不保存，避免带出私有内容。

## 额度记录与预算

接口数字是**已用**比例 `usedPercent`。脚本按池保存 `limitId`、各窗口的 `windowDurationMins`、`resetsAt` 与已用比例，不假设 `primary` 必然为五小时。提交前要求 `ordinaryUsageAllowed=true`、可观测窗口均低于 90% 且未触发 spend control；这是保守前置检查，不是消费价格或绝不扣费的服务端保证。不同目录不会共享或强制执行用户给宿主的总张数预算，宿主仍须逐次计数。

本轮可见的是 codex 桶：第一张五小时已用 **0→2%**、周 **31→31%**；第二次调用因拥堵无图，立即后读额度失败，后续原线程查询时仍为 **2%、31%**。这些是该账户、该窗口的整数观测，不能推出独立图像额度池、图像与普通对话必定共用同一池、固定每张 2–3 点或零消耗。重置、并发使用和取整都会影响差值。不购买 credits，不更改账户支付设置，也不轮换账户绕额度。

## 已验证与未验证

本轮第一张无字陶艺 Hero 经官方 exec 单次生成，62.911 秒，1536×1024，原线程取回并解码、哈希通过；逐图验收可用，右边额外花瓶/枝叶另记。它是**探针通路成功**，之后据此实现正式入口，不冒称新版 `generate` 已端到端成功。

第二张中文高密度界面用正式 `generate` 实际调用一次，但官方控制模型拥堵，原线程失败、无图；新脚本的成功生成闭环与这张界面的内容验收仍待新增授权。`status/resume` 原线程恢复和拥堵分类已实测；取图三路径、预览拒绝、额度后读失败、丢回执不重提等由本地假 CLI / app-server 回归覆盖。历史网页、论文/PPT 和财务界面样例只说明当时成果，不代替本版入口的真实验收。

产物是栅格图，服务端尺寸、seed 和图像模型 ID 未必提供，未提供就写未提供。PNG 不冒充可编辑文件或可交互网页；改字重出、[局部修补](raster-repair.md) 与原图能力要分清。

## 官方资料

- [Codex 原生生图](https://developers.openai.com/codex/image-generation)
- [登录与认证](https://developers.openai.com/codex/auth)
- [app-server 协议](https://developers.openai.com/codex/app-server)
- [计划与用量](https://developers.openai.com/codex/pricing#image-generation-usage-limits)
- [ChatGPT 与 API 分开计费](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform)

产品能力与客户端行为会变。以当前官方客户端的能力、账户与实际回执为准，不据旧记录自动升级、换源或重交。
