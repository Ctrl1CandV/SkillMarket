# 主会话浏览器补充检查

2026-10-03；frontend-craft 0.1.0。此记录补充 frontend-craft-assessment.md 中子代理不可用的浏览器部分，不代表完整视觉验收。

通过官方 browser-use 的 ZCode IAB 启动本机 evals HTTP 服务，未启动或修改 ResearchWorkbench。

## 实际结果

- workbench.html 在 1280×900 成功加载，DOM 包含三个论文来源、搜索、范围选择及阅读入口。
- 搜索框填入“不存在测试”，真实 DOM 更新为“显示 0 / 3 篇”和“没有匹配的论文”。
- 点击“清空筛选”超时；重新快照仍在空结果状态。未把 mock 测试成功替代本次真实点击，不确定是宿主自动操作限制或页面可交互性问题，恢复链路仍未验收。
- 工作台切至 390×844，innerWidth=390、documentElement.scrollWidth=375；当前空状态没有文档级横向溢出。
- reading.html 成功加载，目录、正文、表格、思考提示及来源出现在 DOM。
- 阅读页 390×844 下测得 scrollWidth=375；1280×900 下为1265，无文档级横向溢出。这不是逐元素裁切检查。
- 采集了四份真实截图。宿主返回工件路径，Read 的图像响应呈现为编码内容，未能据此可靠作视觉判断；不将“截图生成”写成“画面通过”。未完成截图驱动修订、键盘遍历、200%缩放、阅读页下半部及失败重试真实检查。

## 本次截图工件（会话本地，不属于持久仓库）

- 工作台桌面：C:/Users/11487/.zcode/cli/artifacts/sess_6c166644-b83c-4732-889a-463f067b9833/call_3t3IozebLDn3CO5JLnHgvCa6-tool-result-488020f4-3d31-4de0-9905-2eb028e05a03.png
- 工作台手机空状态：C:/Users/11487/.zcode/cli/artifacts/sess_6c166644-b83c-4732-889a-463f067b9833/call_AKstJjcGlCTL1GJGu3HOk7vJ-tool-result-02b30810-7ba6-4cc5-b85b-a094d89ab0e5.png
- 阅读手机：C:/Users/11487/.zcode/cli/artifacts/sess_6c166644-b83c-4732-889a-463f067b9833/call_NM1iKmfEgZRH87l4T80GsIu7-tool-result-977183c9-d27e-44c1-944e-8b0d183646c8.png
- 阅读桌面：C:/Users/11487/.zcode/cli/artifacts/sess_6c166644-b83c-4732-889a-463f067b9833/call_NM1iKmfEgZRH87l4T80GsIu7-tool-result-ff40a0fc-d944-4ebf-9203-1df5a82ec115.png

结论：真实浏览器冒烟部分完成，视觉效果优于旧技能、全交互通过、移动设备通过等结论均不成立。首版按实验性入库，剩余矩阵留在 cases.json。
