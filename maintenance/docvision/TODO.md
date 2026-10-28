# docvision 待办

初版 0.1.0-rc.1 已完成本地 MinerU/PaddleOCR、远程适配器、统一输出和环境引导。以下按优先级排列，完成前不要声称对应能力已验证。

## 必须补的真实性验证

- [ ] 用有效的 MinerU token 跑 Standard API 真实样本（本地 PDF + URL），核对 `full_zip_url` 的 `full.md`、`layout.json`、`content_list.json`、图片命名；当前 token 返回 401/A0202。
- [ ] 用真实 GLM-OCR key 跑 1 份中文表格/手写样本，确认 `layout_details` 的页序、`bbox_2d`、`md_results` 与文档一致。
- [ ] 用真实 Mistral key 跑 1 份含图表/合并单元格的 PDF，确认 `blocks` 的 bbox 坐标系、`dimensions` 字段、图片/表格占位符替换。
- [ ] 用真实 Gemini key 跑 1 份双栏论文 + 1 份图表页，记录页标记遵守率、inline 18 MB 限制、免费层/计费行为。
- [ ] 用真实 OpenAI 兼容端点（Ollama 或 vLLM）跑 1 张截图 + 1 页 PDF，确认页渲染、图片编码、`max_tokens` 兼容性。

## 8 GB / 长文档

- [ ] 在 8 GB 显存机器上测 MinerU standard：10 页论文、50 页扫描件的峰值显存、耗时、是否 OOM。
- [ ] 同机测 PaddleOCR-VL 单页/10 页；记录 cuDNN 警告是否影响稳定性。
- [ ] 测 `--workers 2` 在 8 GB / 16 GB 上的实际收益与 OOM 风险；必要时把默认并发改为按显存自动限制。
- [ ] 测 200+ 页 PDF 的本地 MinerU 与远程 Standard 的分段策略。

## 质量与评测

- [ ] 建立 5 类最小真实样本集（数字版论文、扫描书页、复杂表格、截图/幻灯片、手写/印章），只存脱敏/公开样本。
- [ ] 为每类记录正文、公式、表格、阅读顺序、图表描述的失败页；不要只报平均分。
- [ ] 对 MinerU、PaddleOCR、GLM、Mistral、Gemini 做同页对比；记录版本、设备、耗时、实际计费页数。
- [ ] 把 `qa.json` 的 `warn` 与人工复核结论关联，避免“结构 pass”被误当准确率。

## 功能

- [ ] 决定是否加 PaddleOCR 云 API（百度智能云）适配器；当前只有本地 PaddleOCR，参考文档已写但未实现。
- [ ] 决定是否加 Gemini Files API（>18 MB PDF）；当前明确报错并提示换路线。
- [ ] 决定是否加 RAG 切片导出（按页/块，保留 bbox/页码）；当前 `content.json` 已具备基础，不急着做。
- [ ] 评估 `local-vlm` 对 Ollama GLM-OCR / Qwen3-VL 的实际质量；没有布局管线时不要用于整本论文。
- [ ] 考虑 PDF 加密/损坏的友好检测；当前依赖 PyMuPDF/pypdfium2 报错。

## 工程

- [ ] 把 `setup_cmd` 的 conda/pip 长输出做成可选日志文件，避免终端刷屏；当前失败时只显示 tail。
- [ ] 为 `setup` 加 `--lock`/`--freeze`，生成可复现的 `pip freeze` 并把路径写入 `meta`；当前只写约束文件。
- [ ] 为 `convert --dry-run` 的远程 provider 去掉“必须先有 key”的限制，方便离线规划。
- [ ] 为 `read --format image --json` 返回结构化路径；当前返回字符串。
- [ ] 增加 `docvision doctor --json` 的 schema 测试，防止字段回归。
- [ ] 评估把 `scripts/dv` 打成单文件 zipapp，减少复制目录时的路径问题；当前包结构可读性更好，暂不打包。

## 文档/仓库

- [ ] 在真实使用 2-3 次后修订 SKILL.md 的触发描述，避免和普通“读 PDF”技能冲突。
- [ ] 把真实失败页/引擎版本记录到 `maintenance/docvision/evals/`，不要放敏感原文。
- [ ] 向 main 整合时只带 `docvision/` 运行资源与 README 索引，不带 `maintenance/`；提交前核对文件清单。
- [ ] 旧 `maintenance/mineru/` 保留为历史；不要把它和新 `docvision` 混为同一技能。
