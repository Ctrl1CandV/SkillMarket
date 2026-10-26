# 本轮升级归档入口

本轮完成 frontend-craft 0.5.0-rc.1 与 product-design 0.2.0-rc.1 的替换、参考补充、样张验证、独立配对及用户评价。阅读布局获用户认可，整体差距不明显，旧版标题层级略受偏好。实施与核查已收尾，不宣称新版整体视觉效果得到证明；候选版本继续保留 RC。

- [当前交付与收尾](DELIVERY_STATUS.md)、[提交与清理记录](reports/closeout.md)。
- [用户反馈](reports/user-feedback-2026-10-26.md)、[原因分析](reports/reading-cause-analysis.md)、[比较结论](reports/comparison-report.md)。
- [原终审](reports/final-review.md)与[用户调整后的结束条件](ACCEPTANCE-ADDENDUM-2026-10-26.md)，两者保留各自时点和范围。
- [原始交付包](delivery/original-package.zip)及[归档校验](delivery/original-package-archive.json)：56 文件逐字节保存，根目录的重复解压副本已删除。

## 复看页面

收尾已停止本轮本地服务并关闭对比标签。在仓库根启动 `python -m http.server 8766 --bind 127.0.0.1` 后，打开 `http://127.0.0.1:8766/maintenance/frontend-craft/upgrades/2026-10-26/user-review/index.html`。原图和实现均保留；静态 HTML 对比也可从 [user-review/index.html](user-review/index.html) 进入。

## 复查与证据

原始 checker 保持不变，可从仓库根执行：

```text
python maintenance/frontend-craft/upgrades/2026-10-26/tools/check_package.py --repo-root . --release
```

需要同时核对归档原要求、配对输入和运行哈希时，执行 `tools/final_checks.py --output-dir <一个尚不存在的输出目录>`。该工具从 ZIP 读取原包，并拒绝覆盖已有输出目录；旧审查结果和旧哈希不被重写。CLI 路径相对于当前目录，本轮实际收尾复查位于 [reports/closeout-checks](reports/closeout-checks/)。这些静态检查不产生新的视觉评价。

维护材料只在 dev 保留；main 仅收录运行技能、引用的参考资源与样式样张。
