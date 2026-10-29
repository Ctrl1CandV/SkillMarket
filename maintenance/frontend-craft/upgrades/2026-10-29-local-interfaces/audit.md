# 本轮运行资源静态审核

检查时间：2026-10-29 10:55:16（Asia/Shanghai）。

结论：本次要求的静态检查全部通过，未发现需要修改候选包的缺陷。此结论限于格式、资源连接、索引保留、JavaScript 语法及快照完整性，不证明实际视觉质量、交互正确性或技能升级收益。

## 范围与方法

检查冻结的 `candidate/frontend-craft`、`candidate/product-design`，并逐文件确认它们与工作区当前对应运行目录完全一致；基线仅用于清单完整性和索引条目比较。未访问浏览器、网络、evaluation 任务或产物。未修改运行资源、baseline、candidate 或两个 SHA256 清单；README 与 docvision 的并行变更不在本次范围。

可重复脚本为 [static_audit.py](static_audit.py)，完整机器结果为 [audit-results.json](audit-results.json)。从仓库根目录运行：

```powershell
python -X utf8 maintenance/frontend-craft/upgrades/2026-10-29-local-interfaces/static_audit.py
```

脚本使用当前安装的 skill-creator `quick_validate.py`（可通过 `--validator` 指定路径），以及 PATH 中的 Node.js；结果记录实际命令与退出状态。脚本只读取两个技能目录及本轮两个快照，把检查结果写回本维护目录，不读取验收材料。

## 检查结果

| 检查 | 实际结果 |
| --- | --- |
| 两个技能的 quick_validate | 冻结候选与当前运行目录共 4 次调用均返回 `Skill is valid!`，退出码为 0；使用 Python UTF-8 模式读取中文 |
| 当前运行资源与冻结候选 | 36 个文件的集合、相对路径和 SHA256 完全一致，无新增、缺失或内容差异 |
| 本地相对链接与资源 | 检查 128 处引用，无缺失文件或片段目标；包括 Markdown 链接、HTML 的 href/src/poster、CSS url() 和索引截图路径。Markdown 标题片段与 HTML id/name 按静态内容核对 |
| 原有范例条目 | baseline 的原 14 条记录在候选中字段、值、嵌套数据及条目顺序完全相同，采用解析后的 JSON 深比较；不要求整个索引文件字节相同 |
| 新增范例条目 | 候选共 24 条，新增 10 条均为 `documented`，无重复 ID；新增条目的 screenshots 均为空，capture 均为 null，未冒充新的视觉采集 |
| JavaScript 语法 | 对候选与当前运行目录的 `lab.js`、`local-interface.js` 分别执行 `node --check`，共 4 次通过；HTML 未发现需要另查的内联 JavaScript 块 |
| 额外资源引用形式 | 定向搜索样张目录中的 srcset、CSS @import、JS import/require/fetch/new URL 及直接 href/src/location 赋值，未发现额外待核对的资源引用形式 |
| 差异空白检查 | `git diff --check -- frontend-craft product-design` 退出码为 0；仅提示 Git 后续可能进行 LF/CRLF 转换，无空白错误 |

## 快照完整性

审计开始和结束时均重新枚举快照文件并计算 SHA256，与已保存清单逐项比较；结果一致。没有仅检查“清单文件存在”。

| 快照 | 清单项数／实际文件数 | 内容变化 | 缺失／额外文件 |
| --- | --- | --- | --- |
| baseline | 32／32 | 0 | 0／0 |
| candidate | 36／36 | 0 | 0／0 |

清单文件自身在本次审核前后亦未改变，审核时哈希为：

```text
baseline-sha256.json
aca4478ade45cef04c6a432400f336feb8df3fd7c3d9a559e816b806fe2700ad

candidate-sha256.json
7c67ca720885869b40ebf23a87e0b7daa92acef390653d5855815e1cb044cf6c
```

上述结果说明快照内容与当前保存的清单一致，并记录清单本次审计期间的稳定性；不额外声称有独立签名或审计前的清单防篡改证明。

## 语义抽查与边界

抽查新增局部组织指导、product-design 的职责与上下文补充、样张说明及实现、范例文字与索引：局部重排沿用已有产品依据，未要求所有窗口重新做全产品分析；指导推演与样张标明假设或虚构用途，保存演示没有宣称真实审核或发运；新增外部来源保持文档级证据定位。未发现与本轮通用能力范围直接冲突的表述。

本次未复核外部链接当前可访问性、来源文字真实性或许可判断，也未运行页面、检查实际渲染、键盘焦点、错误恢复或审美效果。JavaScript 语法通过不代表这些行为通过。本报告不得作为跨业务迁移、用户认可或视觉提升的验收结论。
