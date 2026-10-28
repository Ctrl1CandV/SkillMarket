# docvision evals

## Adapter/output checks

```text
python maintenance/docvision/evals/check.py
```

起一个本地 mock HTTP 服务器，覆盖：

- PaddleOCR 官方 API：提交任务、轮询、下载 JSONL，解析页/块/formula/table 并验证输出。
- 本地 loopback VLM：`chat/completions` 图片请求、成功响应、Markdown 落盘与结构检查。
- 远程请求必须带每次上传授权；安装级 `local-only` 设置即使有上传标志也拒绝远程。
- 固定凭据文件中的虚假 token 不写入 `config.json`。

不调用真实 OCR 服务，不消耗额度，不验证真实响应/限流/计费。当前共 5 项；临时夹具在测试结束后自动清理。

## Real smoke (manual)

```text
python docvision/scripts/docvision.py doctor --json
python docvision/scripts/docvision.py convert D:/temp/docvision-test/sample.pdf --provider mineru-local --json
python docvision/scripts/docvision.py read <out> --page 1
python docvision/scripts/docvision.py verify <out> --json
```

本机结果见 [初版报告](../reports/initial-design-2026-10-28.md) 第 5 节。不要把真实文档、token 或转换输出提交到仓库。

## Real cloud verification (manual, 2026-10-28)

真实 PADDLEOCR_ACCESS_TOKEN 通过 `--env-file` 加载（文件在 gitignore 内），对公开 Attention 论文公式页与合并表格页完成云端转换、裁图 refine 与本地同图对比：云端/本地 Paddle 表格 HTML 逐字节一致，公式一致，refine 重复请求命中缓存不再上传。详见 [云端验证报告](../reports/paddle-cloud-verification-2026-10-28.md)。共 3 次真实提交；额度状态随账号政策变化，未验证真实额度耗尽错误码。

## Hybrid / 0.2 regression

```text
python -m unittest discover -s maintenance/docvision/evals -p "test_*.py"
```

`test_integrity.py` 覆盖完整页集合、空正文、DPI和请求缓存；`test_local.py` 覆盖发现/隔离/资源和本地档位；`test_paddle_cloud.py` 用本地HTTP服务验证官方异步契约；`test_hybrid.py` 验证单区域精读、原稿保留、任务、缓存/并发、上传授权和截断。

外部服务测试均用虚假token和本地响应，不消费外部额度。真实论文/原始OCR输出保存在本机临时目录，仓库只保存脱敏结论。
