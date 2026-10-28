# docvision evals

## Adapter/output checks

```text
python maintenance/docvision/evals/check.py
```

起一个本地 mock HTTP 服务器，覆盖：

- GLM-OCR：`layout_details` -> 页/块/formula，`md_results`。
- Mistral OCR：页、blocks、base64 图片、table 占位符替换。
- Gemini：`candidates[].content.parts[].text` 与页标记。
- OpenAI 兼容 / local-vlm：`chat/completions` 内容。
- MinerU Standard：`file-urls/batch` -> PUT -> 轮询 -> zip -> middle_json。

不调用真实 OCR 服务，不消耗额度，不验证真实响应/限流/计费。2026-10-28 运行结果：5 项通过。

## Real smoke (manual)

```text
python docvision/scripts/docvision.py doctor --json
python docvision/scripts/docvision.py convert D:/temp/docvision-test/sample.pdf --provider mineru-local --json
python docvision/scripts/docvision.py read <out> --page 1
python docvision/scripts/docvision.py verify <out> --json
```

本机结果见 [初版报告](../reports/initial-design-2026-10-28.md) 第 5 节。不要把真实文档、token 或转换输出提交到仓库。
