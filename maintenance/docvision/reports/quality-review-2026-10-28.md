# Docvision 0.3.0 质量审查

审查日期：2026-10-28（Asia/Shanghai）。审查基线：`0bf5ad5`。范围包括 SKILL/references、CLI、安装、凭据、本地/云端适配、统一输出、精读与评测。此次仅审查，未修复运行代码。

后续状态（2026-10-29）：本文保留审查时的证据和位置；8 个确认问题已在当前工作树的 0.4.0 修复，并补充批量阅读与缓存优化。修复验证及仍未完成的 OCR 精度实测见 [0.4.0 更新报告](personal-reading-upgrade-0.4.0-2026-10-29.md)。

## 结论

设计基础较好，已具备实用 OCR 工作流的结构；当前适合受控试用，尚不宜作为“安装后普遍可靠”的通用稳定版背书。确认 1 个 P1 和 7 个 P2。应先修复本地请求的代理外发问题，再补齐首次使用、证据版本、重试缓存和配置边界。

优点明确：本地优先；云端有持久同意与逐次调用授权；识别、结构检查、实际准确率区分清楚；OCR 与图形语义解释分工合理；页码、块、bbox、裁图和独立精读结果能够支持核对；异常不自动切换其他云服务；现有回归覆盖较丰富。

## 确认问题

### 1. [P1] 本地视觉请求仍可经过外部 HTTP 代理

- 位置：[openai_compat.py:127](<D:/Program Project/SkillMarket/docvision/scripts/dv/providers/openai_compat.py:127>)、[util.py:332](<D:/Program Project/SkillMarket/docvision/scripts/dv/util.py:332>)。
- 条件：配置本地 VLM 地址，例如 `http://127.0.0.1:11434/v1`；环境设置外部 `http_proxy`，没有相应 `no_proxy`。
- 原因：适配器仅验证 URL 的 host 是 loopback，随后使用 `urllib.request.urlopen()` 的默认代理处理。目标地址为本地不代表实际连接不经过代理。
- 证据：保留 urllib 代理选择逻辑，只将底层 HTTPConnection 替换为不联网记录器。`Options(allow_remote=False)` 下记录到 `connect_host=external-proxy.example`、`has_image=True`，返回元数据仍为 `local=True`。没有实际外发图片。
- 影响：图像与文本上下文可能发送给外部代理，违反本地处理与上传授权边界。
- 建议：本地 VLM 使用显式禁用代理的专用 opener，并限制重定向；增加有代理环境下实际连接目标的回归。

### 2. [P2] 只装 core 的首次使用路线走不通

- 位置：[SKILL.md:36](<D:/Program Project/SkillMarket/docvision/SKILL.md:36>)、[detect.py:67](<D:/Program Project/SkillMarket/docvision/scripts/dv/detect.py:67>)、[read.py:13](<D:/Program Project/SkillMarket/docvision/scripts/dv/read.py:13>)。
- 文档推荐不下载模型时只装 core 制作精读包，也介绍无 GPU 的文字层路线。
- 实际 convert 必须发现 MinerU/Paddle/VLM 或选择已授权远程服务；fast 也没有独立的 core 文字层 provider。refine 又要求输入已有 meta.json/content.json 的转换目录。
- 离线复现：所有引擎 unavailable、同意为 local-only 时，fast 返回 `No local OCR engine is installed`；将原始 PDF 传入 packet 返回 `Not a docvision output directory`。
- 影响：新用户按低配置、无模型的推荐路线不能从原文获得精读包。现有 pages 可以渲染图片，但不是文档所承诺的 refine 精读包入口。
- 建议：增加原始 PDF/图片的 packet 与文字层入口，或收窄文档承诺并给出可执行的 pages 看图流程。

### 3. [P2] 源文件替换后，crop 使用旧坐标裁剪新文件

- 位置：[read.py:179](<D:/Program Project/SkillMarket/docvision/scripts/dv/read.py:179>)、[read.py:193](<D:/Program Project/SkillMarket/docvision/scripts/dv/read.py:193>)。
- crop 从旧 content.json 读取块坐标，render_page 按当前源文件哈希重新渲染，但没有核对它是否等于 meta.source.sha256。
- 离线复现：将已转换的红色源图片同路径替换为蓝色，crop --block 成功裁出蓝图，旧 OCR 内容和块归属没有改变。同样操作走 refine 会正确拒绝源文件变化。
- 影响：论文修订、扫描件同名替换后，新图可能被误当成旧 OCR 文本的视觉证据。
- 建议：crop 复用 refine 的源指纹一致性检查；read 的页面图输出也应拒绝或明确标记版本不匹配。

### 4. [P2] 强制重转后，旧精读记录仍被关联到新文档

- 位置：[refine.py:251](<D:/Program Project/SkillMarket/docvision/scripts/dv/refine.py:251>)。
- --force 会按相同来源路径复用输出目录，保留 refinements；list_results 只按 page/block 过滤，不验证记录的 source.sha256 或上下文版本。
- 离线复现：转换白色源图并生成真实 packet；同路径替换黑图后强制重转；当前文档和旧记录的 SHA256 不同，但 list_results(page=1, block=p1-b0) 仍返回旧记录。
- 影响：read 会把旧文件的精读结果列为当前页/块的关联结果，未标明过期；块 ID 本身不能证明是同一版本的内容。
- 建议：保留历史，但只把匹配当前源指纹及上下文的记录列为有效结果，其他结果明确标记 stale 或单独归档。

### 5. [P2] setup 的 dry-run 实际修改上传同意

- 位置：[cli.py:454](<D:/Program Project/SkillMarket/docvision/scripts/dv/cli.py:454>)。
- remote/local-only 分支直接 config.set_consent，未检查 dry_run。
- 临时配置实测：`setup --remote --dry-run` 返回 0，并将 `local-only` 实际改为 `remote`。
- 影响：安装预演改变后续上传许可，违反 local-setup.md 的“不保存配置”承诺。逐次 --allow-remote 仍保留，因此这不是立即无条件上传。
- 建议：该分支遵守 dry-run，或明确拒绝参数组合。

### 6. [P2] 精读强制重试成功后仍命中旧失败缓存

- 位置：[refine.py:181](<D:/Program Project/SkillMarket/docvision/scripts/dv/refine.py:181>)、[refine.py:201](<D:/Program Project/SkillMarket/docvision/scripts/dv/refine.py:201>)。
- 普通请求只读基本 identifier 目录；--force 的新尝试写入 identifier-2 等目录，没有更新当前有效尝试的索引。
- 离线 provider 替身复现：首次 failed → --force recognized → 普通重复请求仍 failed、cached=True。
- 影响：恢复成功后仍显示旧失败；已有成功结果再次精读得到更好结果时，普通请求也仍复用旧版本。
- 建议：保留历史，同时记录每个签名当前有效的 attempt，明确失败/成功尝试的选择规则。

### 7. [P2] 文档推荐的本地 VLM 环境变量不生效

- 位置：[openai_compat.py:79](<D:/Program Project/SkillMarket/docvision/scripts/dv/providers/openai_compat.py:79>)、[config.py:347](<D:/Program Project/SkillMarket/docvision/scripts/dv/config.py:347>)。
- remote-apis.md:53 及运行错误提示都推荐 DOCVISION_OPENAI_BASE_URL / DOCVISION_OPENAI_MODEL，但发现与执行路径只读 config/extra。
- 离线复现：仅设置变量时 discover_vlm.available=False；auto 返回 packet；显式调用 local-vlm 报 `No vision model is configured`。
- 建议：发现、运行与缓存共用一个有效配置解析函数，统一 extra/env/config 优先级。

### 8. [P2] 使用另一种支持的别名更新 token 后仍选旧值

- 位置：[credentials.py:398](<D:/Program Project/SkillMarket/docvision/scripts/dv/credentials.py:398>)。
- save_credentials 仅 update 字典，未删除同一凭据组的旧别名。
- 假凭据复现：先保存 DOCVISION_PADDLE_TOKEN=old，再按默认 credentials set 保存 PADDLEOCR_ACCESS_TOKEN=new。重新加载后 remote_keys 仍选择 old，因为其别名优先级更高。
- 影响：旧 token 过期时，用户得到保存成功提示但调用继续使用旧 token。
- 建议：保存新凭据时替换该凭据组，并移除该组其他旧别名；其他组不受影响。

## 验证与实际能力边界

- 本次独立复跑 unittest discover：161 项，160 通过、1 跳过、0 失败/错误；跳过项为 Windows 符号链接创建权限。
- 本次独立复跑 check.py：5 项全部通过。
- 测试隔离配置、模型路径、凭据和临时目录；使用假 token，socket 审计阻止非 loopback 外网连接。沙箱下首次执行受临时目录、回环网络和 junction 权限影响；最终在隔离目录通过所需权限运行，不把环境失败计作产品缺陷。
- 上述新增问题用无网络替身或合成图片单独复现，说明现有全部通过的回归并未覆盖这些边界。
- 此次没有安装/下载 OCR 模型，没有读取真实密钥，也没有调用真实云端 API。因此不能给出新的 OCR 准确率、性能或真实额度结论。
- 仓库已有真实验证记录，集中于 Windows/NVIDIA 16 GB 环境及 Attention 论文公式/合并表格；不是只有 mock。但全新机器安装、8 GB、Linux/macOS、长文档和 20–30 页多样真实标注集仍未完成，见 maintenance/docvision/TODO.md 与 release-0.3.0-2026-10-28.md。
- 上游云端协议另作静态核对：提交/鉴权、轮询与 JSONL 解析未发现新的确定缺陷。参考 [PaddleOCR 官方 HTTP 客户端](https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/paddleocr/_api_client/_http.py)及[官方轮询/解析器](https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/paddleocr/_api_client/_poller.py)。静态相符不等于本次执行过真实服务。

## 非阻塞观察与后续顺序

安装代码的 MinerU 范围为 >=4.0,<5，随附 constraints/mineru.txt 却为 <4.1，setup 没有使用这些约束文件。当前没有证明某个新版本已不兼容，故不将其列为已发生的运行故障，但应消除两套依赖范围以便复现。

建议顺序：先修复代理外发；再解决两个证据版本问题和 dry-run；补齐 core-only、重试缓存、配置与 token 更新；最后以干净环境安装和多样真实材料补足通用质量证据。接口测试通过与 OCR 识别准确率应持续分开报告。
