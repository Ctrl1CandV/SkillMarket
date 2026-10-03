# mineru 待办

已安装副本（3.3.1）核验发现以下问题（详见 [reports/mineru-assessment.md](reports/mineru-assessment.md)），修复并重验前不作为可直接使用的包收录：

- [ ] 中文文件名生成的 Standard API `data_id` 不符合官方 ASCII 约束；批量路径超长后缀也会越界。
- [ ] 复杂页码（如 `2,4-6`）在 Agent 路径被静默截断为第一段，返回"成功但不完整"。
- [ ] 显式 `--engine local` 在缺失 `local_engine` 模块时仍进入云端路径，涉及文档上传边界，优先处理。
- [ ] `--split`、`--chunk`、`--to`/`--obsidian` 依赖的模块未随包提供，仅警告不执行。
- [ ] 输出目录命名碰撞（同名 stem 覆盖风险）。
- [ ] `--doctor` 把网络错误误判为 token 有效。

说明：官方每日 1000 页是最高优先级额度，不等于永久免费承诺；脚本 `FREE_DAILY_PAGES` 等常量不能当收费政策证据。
