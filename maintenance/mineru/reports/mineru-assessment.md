# MinerU 已安装技能核验报告

- 核验日期：2026-10-03。
- 来源：`C:\Users\11487\.zcode\skills\mineru`；脚本自报版本 `3.3.1`。
- 结论：**不收录**。基础英文文件的云端流程可通过模拟测试，但不能据此认定当前副本“拿到直接能用”：中文文件名生成的 Standard API `data_id` 不符合官方契约；复杂页码选择会静默丢页；显式离线模式在缺失模块时会转入云端。仅记录问题，未修复或优化。
- 仓库交付仅本报告；未创建 `mineru` 目录，未修改已安装副本，未 git 提交。仓库其他已有修改不属于本次核验。

## 1. 来源完整性

已完整读取全部两个文件：`SKILL.md`（34 行）和 `scripts/mineru.py`（1997 行）。没有附带测试、依赖锁文件、其他 Python 模块或原始上游来源信息；不能把本地副本当成已经核实的官方发布包。

| 相对来源路径 | SHA256（原始字节） |
| --- | --- |
| `SKILL.md` | `372a8c0545ea6bb19bbfd6efd1d26776706250126c059dfca782535144f94c89` |
| `scripts/mineru.py` | `ea11aea799754cb0ce02b2452b7b2bb9053975f08e1ecc91d47bd40e50c279a7` |

## 2. 环境、依赖与 token

- `uv 0.12.1` 可用；系统 Python 为 `3.12.9`，模拟测试在 Python 3.12.9 运行。
- 原样执行 `uv run --no-project "C:/Users/11487/.zcode/skills/mineru/scripts/mineru.py" --help` 和 `--version` 成功，版本输出 `mineru 3.3.1`。按技能说明启用 `PYTHONUTF8=1`。
- 脚本 PEP 723 声明 Python `>=3.8`、`dependencies = []`。默认云端路径仅使用标准库；“零依赖”不等于不需要 Python/uv、联网、MinerU 服务和对象存储/CDN。没有验证 Python 3.8 等其他解释器。
- 在当前进程环境中仅布尔检测 `MINERU_TOKEN`：**存在**。没有打印或检查值、长度、内容，没有搜索 `.env`、注册表、配置文件等秘密来源，没有用真实 token 发请求。存在不表示有效、未过期、额度足够或可迁移到别的机器。
- 系统 Python 可找到 `pypdf`，找不到 `pymupdf4llm`。未安装依赖；这不保证其他 uv 解释器也拥有可选包。
- 源目录缺少代码引用的 `splitter.py`、`local_engine.py`、`chunking.py` 和 `sinks` 包。仅安装 pypdf 也不能补全缺失的拆分模块。
- `SKILL.md` 直接宣称 token 已配置属于当前机器假设，不是技能包可携带的配置。

## 3. 当前官方 API 契约核对

来源：<https://mineru.net/apiManage/docs>，核验日通过 Python 标准库 HTTPS GET 读取公开页面并提取正文。首次 WebFetch 超时，后续直接 GET 成功。一次读取的页面原始字节 SHA256 为 `6b72fd975b37f5d64996bdd97d97f755b7de82602f7e6c1f37cc27b9f51e24fa`；动态页面未来可能变化。没有登录或携带 token/cookie。

| 项目 | 官方文档及代码对照 |
| --- | --- |
| Standard 鉴权 | `Authorization: Bearer <token>`；脚本实现一致 |
| Standard 本地文件 | POST `/api/v4/file-urls/batch` → `batch_id` / `file_urls` → PUT → GET `/api/v4/extract-results/batch/{batch_id}` → `full_zip_url`；核心字段匹配 |
| Standard URL | POST `/api/v4/extract/task` → `task_id` → GET `/api/v4/extract/task/{task_id}`；批量 URL 另有 `/extract/task/batch`；脚本使用相应路径 |
| Standard 文件上限 | 200 MB、200 页；脚本常量一致。文档模式对比现为批量最多 200 个，脚本保守限制 50 个，不单独构成阻塞 |
| Standard 数据标识 | `data_id` 仅大小写英文字母、数字、`_-.`，最多 128 字符；脚本存在违反该约束的情况 |
| Agent | 无需 token、按 IP 限频；10 MB、20 页；POST `/api/v1/agent/parse/file` 或 `/parse/url`，GET `/parse/{task_id}`；签名上传字段 `file_url`，结果 `markdown_url`，脚本基本匹配 |
| 页码 | Standard `page_ranges` 支持 `2,4-6` 等；Agent `page_range` 仅单页或连续范围，不支持逗号；脚本会静默截掉逗号后部分 |
| 输出 | Standard ZIP 含 Markdown/JSON，可附加 docx/html/latex；Agent 仅 Markdown CDN 链接。Agent 路径不会下载图片到本地 `images/`，不能普遍承诺技能说明中的本地图片目录 |

官方 Agent 文档内部存在歧义：概述说轻量模型禁用表格/公式，但请求参数表又列出 `enable_table`、`enable_formula` 默认 true；格式支持总表与 URL 参数表对旧 Office 扩展名也不完全一致。本次不能断言实际服务一定支持/不支持这些能力。脚本有 token 的小文件也优先走 Agent，因此不能仅凭默认 `model=vlm` 和技能说明保证高精度公式/表格输出。

**费用与额度**：官方文档明确每账号每天有 **1000 页最高优先级解析额度，超过后降低优先级**，不是“每天只能免费解析 1000 页”的同义表达。Agent 免 token 不等于无限制，也不证明永久免费。当前抓取正文未见可作为永久免费承诺的条款；本次未核验账号实际额度、计费状态或商业条款。脚本 `FREE_DAILY_PAGES` 及某些报错中的 “free pages/day” 不能当成收费政策证据。

## 4. 已确认问题

### A. 中文文件名使 Standard 核心请求不符合契约（收录阻塞）

`scripts/mineru.py:246-249` 的 `safe_data_id` 使用 Unicode `str.isalnum()`，因而 `safe_data_id("机器学习")` 返回原中文。`722` 行的本地单文件上传与 `1075` 行的批量规划均使用该标识。官方仅允许英文字母等 ASCII 字符，因此技能示例的中文书名一旦走 Standard 就会发送不合规参数。

模拟已确认返回中文标识；是否被当前服务严格拒绝未在线验证，不声称收到过真实拒绝响应。此外，128 字符的 ASCII 文件名在批量路径追加 `-0` 后产生 130 字符 `data_id`，也已复现。

### B. 页码范围静默丢失（收录阻塞）

`276-281` 行只保留第一个逗号前片段；`643-652` 行构造 Agent 请求。实测 `--pages '2,4-6'` 对应请求值变成 `'2'`。`choose_api` 不以复杂页码为依据切 Standard，单个小文件即使有 token 仍走 Agent。这不是“不支持但清晰报错”，而是可能成功返回不完整内容。

`SKILL.md:28` 还把页码称为“书本实际页码”，但脚本未实现印刷页码到 PDF 页面序号的映射；带封面、前言的教材可能选错章节。是否有特定 PDF 页码标签支持未验证。

### C. 显式离线模式仍调用云端（隐私边界问题，收录阻塞）

`919-940` 行：当 `engine='local'` 且 `_load_local_engine()` 因缺失模块返回 `None` 时，不报错而继续执行云端分支。源包确实没有该模块。模拟中调用 `process_one(..., engine='local')`，mock 的 `agent_parse` 被执行，结果 `api='agent'`。真实运行可能上传本地文档，与帮助中的 “local (offline ...)” 承诺相反。本测试没有上传文件。

### D. CLI 展示的扩展能力未随包提供

- `--split`：`1508-1513`、`1577-1583` 行导入不存在的 `splitter`，模拟实际返回 `failed / No module named 'splitter'`。
- `--chunk`：缺 `chunking`，仅警告后返回，不生成分块结果；`--quiet` 会隐藏警告。
- `--to` / `--obsidian`：缺 `sinks`，无法执行交付；相关 CLI 路径仅警告，不因此改变退出码。这里是源码结论，没有调用真实外部交付服务。

### E. 输出名称碰撞

`228-243` 行只按原始 stem 计数，不确保最终命名唯一。模拟输入 `a/report.pdf`、`b/report.pdf`、`c/report-2.pdf` 得到 `['report', 'report-2', 'report-2']`；批处理会共用输出目录，可能覆盖、争用或让 resume 错误跳过。已复现命名冲突，未执行实际并发覆盖。

### F. 自检错误地把网络错误当 token 有效

`1748-1757` 行 `_check_token` 对非 A0202/A0211 的所有 `MinerUError` 都返回 accepted。模拟网络错误后 `ok=True`，所以 `--doctor` 不能作为真实 token 有效性的可靠证据。本次没有执行真实 token 自检。

## 5. 实际执行的测试与边界

测试通过标准输入执行，不保存测试脚本、不修改源代码；设置禁止写入 Python bytecode。自造字节 fixture 位于系统临时目录，退出自动清理。模拟期间把 socket connect 替换为立即失败，所有服务响应、上传和下载均打桩；传入的 `MOCK` 字符串不是环境秘密。

| 测试 | 实际结果 |
| --- | --- |
| 原始 uv 命令 `--help`、`--version` | 成功 |
| Agent 提交→上传→轮询→下载→Markdown 落盘 | mock 成功 |
| CLI `--json --quiet` | mock 成功，JSON `done=1`、退出码 0 |
| Standard 本地签名上传→轮询→ZIP 解包 | mock 成功，生成 Markdown |
| Standard pipeline 批处理代码路径 | mock 成功（单任务批次），未压测多文件并发 |
| 单文件 Agent 页数错误升级 Standard | mock `-30003` 后升级成功 |
| resume | 已有 Markdown 被标为 skipped |
| 缺 token 的 Standard 请求 | 清晰失败，无网络 |
| ZIP `../escape.txt` | 被拒绝 |
| 复杂页码、中文/超长 data_id、同名冲突 | 均复现上文问题 |
| 缺 splitter、local 转云端、自检假阳性 | 均复现上文问题 |

**在线操作仅公开官方文档 GET**。未创建解析任务、未上传任何用户文件、未上传自造样本、未消耗已知账号解析额度、未使用真实 token。无需用在线上传再次证明已存在的本地问题，故停止在核验和报告阶段。

未验证：真实 Agent/Standard 端到端成功率、token 有效性、账号额度、实际收费、真实公式/表格/OCR精度、全部文件格式、代理/防火墙适配、超大文件、全部失败/重试状态、多文件并发压力、所有 ZIP 安全边界和所有操作系统/解释器组合。mock 成功仅证明客户端在设定响应下可串通，不是生产可用性背书。

## 6. 决策

当前副本不满足原样收录条件。最直接影响用户场景的是中文教材文件名的 Standard 参数、页码选择和离线模式的上传边界。遵守“找到问题但不要优化”：不拷贝技能、不补模块、不修源代码、不替换文案；仅交付本报告。
