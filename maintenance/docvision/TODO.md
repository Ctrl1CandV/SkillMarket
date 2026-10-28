# docvision 待办

## 本轮 0.2.0-rc.1 已落地

- [x] 本地批量 economy/basic 与关键区域 triage/refine；精读保留原稿、原页/bbox、裁图与独立结果。
- [x] PaddleOCR 官方托管 API，免费额度与账号限制文档；官方协议形状的本地HTTP测试。
- [x] 公式/表格与图形语义任务分开；无密钥时由当前宿主实际看图的精读包。
- [x] 缺页/错页/空正文、resume配置、DPI缓存、Paddle图资源与脚注、core环境执行、引擎发现开销修复。
- [x] 本机Paddle依赖修复与实际PDF/PNG推理；完整隔离core入口试跑。

## 仍需真实账号/硬件的验收

- [x] 用有效 PADDLEOCR_ACCESS_TOKEN 在真实服务验证一次公开公式/合并表格裁图，与本地同图对比；云端/本地 Paddle 表格 HTML 逐字节一致、公式一致、refine 缓存不重复上传，见[云端验证报告](reports/paddle-cloud-verification-2026-10-28.md)。额度耗尽时的真实错误码未捕获，mock 已覆盖错误映射。
- [ ] 用有效 Gemini 免费层项目验证一次架构图任务；确认账号资格、实际模型、额度和数据使用条款。
- [ ] 额度耗尽时 Paddle 云端真实错误码与恢复策略实测（mock 已覆盖错误映射，真实额度波动按账号政策）。
- [ ] 8 GB 真机：economy/standard、单页/10页/50页峰值显存与端到端耗时。
- [ ] 约20–30页公开真实样本：英文双栏、中文扫描、密集公式、跨列表格、曲线图和架构图，记录错误页及冷/热/连续批处理开销。
- [ ] 16 GB 的长文档与双并发收益：测量后再决定默认；当前单并发。
- [ ] 有真实需求再考虑常驻引擎，避免为低频使用新增服务维护面。

其他远程provider保持可选；首版未做真实key验证的历史边界仍适用。详细记录见 [本轮优化](reports/hybrid-optimization-2026-10-28.md)与[首版报告](reports/initial-design-2026-10-28.md)。向main整合只带运行资源与README，不带maintenance。
