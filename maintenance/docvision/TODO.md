# docvision 待办

## 0.2.0 正式版

- [x] 最终独立审查与真实复杂公式/稀疏合并表格实验；区域公式任务避免重新分类导致的下标错误。
- [x] 修复强制重转旧页图、同名输出并发覆盖、远程端点缓存与uv多索引安装行为。
- [x] 补全.env/别名/全局参数文档，统一正式版本号；发布核验见[报告](reports/release-0.2.0-2026-10-28.md)。

## 本轮 0.2.0-rc.1 已落地

- [x] 本地批量 economy/basic 与关键区域 triage/refine；精读保留原稿、原页/bbox、裁图与独立结果。
- [x] PaddleOCR 官方托管 API，免费额度与账号限制文档；官方协议形状的本地HTTP测试。
- [x] 公式/表格与图形语义任务分开；无密钥时由当前宿主实际看图的精读包。
- [x] 缺页/错页/空正文、resume配置、DPI缓存、Paddle图资源与脚注、core环境执行、引擎发现开销修复。
- [x] 本机Paddle依赖修复与实际PDF/PNG推理；完整隔离core入口试跑。

## 仍需真实账号/硬件的验收

- [x] 用有效 PADDLEOCR_ACCESS_TOKEN 在真实服务验证一次公开公式/合并表格裁图，与本地同图对比；云端/本地 Paddle 表格 HTML 逐字节一致、公式一致、refine 缓存不重复上传，见[云端验证报告](reports/paddle-cloud-verification-2026-10-28.md)。额度耗尽时的真实错误码未捕获，mock 已覆盖错误映射。
- [ ] 额度耗尽时 Paddle 云端真实错误码与恢复策略实测（mock 已覆盖错误映射，真实额度波动按账号政策）。
- [ ] 8 GB 真机：economy/standard、单页/10页/50页峰值显存与端到端耗时。
- [ ] 约20–30页公开真实样本：英文双栏、中文扫描、密集公式、跨列表格、曲线图和架构图，记录错误页及冷/热/连续批处理开销。
- [ ] 16 GB 的长文档与双并发收益：测量后再决定默认；当前单并发。
- [ ] 有真实需求再考虑常驻引擎，避免为低频使用新增服务维护面。

Gemin/GLM/Mistral/MinerU 云端适配器已在 0.3.0 删除（无法验证的 key、被误解的默认型号）；远端只剩 PaddleOCR 一条。详细记录见 [0.3.0 报告](reports/scope-consent-0.3.0-2026-10-28.md)、[本轮优化](reports/hybrid-optimization-2026-10-28.md)与[首版报告](reports/initial-design-2026-10-28.md)。向main整合只带运行资源与README，不带maintenance。

## 0.3.0 通用化与清理

- [x] 删除 Gemini/GLM/Mistral/MinerU 云端适配器与 `gemini-3.8-flash` 默认；远端只剩 `paddleocr-cloud`。
- [x] 首次使用必须询问远程 API；`remote.consent=local-only` 是持久拒绝，带 `--allow-remote` 也拒绝。
- [x] 凭据固定到 `{SKILL_DIR}/.credentials.env`，随附 `.gitignore` + 写入前 `git check-ignore`；`credentials set/show/remove/path`。
- [x] 模型固定到 `%LOCALAPPDATA%/docvision/models`（Linux `~/.local/share/docvision/models`），`models_dir` / `DOCVISION_MODELS` / `setup --models-dir` 可覆盖，旧 `~/.mineru`、`~/.paddlex` 自动复用。
- [x] 中间文件改到输出目录 `.staging/` 并在成功后删除；`DOCVISION_KEEP_TEMP=1` 保留现场。
- [ ] 全新机器上从头跑一次 `setup`（本机环境已存在，未实测冷启动）。
- [x] Windows 凭据创建时设置私有 DACL，并验证所有者与访问规则；真实假密钥/共享目录回归通过。
- [x] 最终审查补齐未记录同意时拒绝上传、`--local-only` 落盘、密钥身份绑定、绝对模型根与失败安装状态；恢复本地 VLM 正常响应回归。见 [最终发布报告](reports/release-0.3.0-2026-10-28.md)。
