# 长期学习与研究准备：最小增量更新

日期：2026-10-23。工作分支：dev。基线：304a1443d2740592b8696d55e40659da2b6e1c43。

## 结论与范围

原有 grad-radar 已覆盖需求选文、经典材料、完整综述导读和单篇阅读；idea-ledger 已处理候选登记及归属。本次只补跨篇知识依赖、渐进学习和按明确目标判断研究准备度，不重写这些流程。

最终涉及 5 个文件：3 个运行文件、2 个 dev 维护文件。相比独立 research-path 技能方案，省去新技能入口、新命令、拆分参考文件及 README 改动，避免重复发现入口和记录机制。

| 文件（仓库相对路径） | 变更 |
| --- | --- |
| plugins/grad-companion-plugin/skills/grad-radar/references/learning-research-path.md | 新增一份按需加载的协议 |
| plugins/grad-companion-plugin/skills/grad-radar/SKILL.md | 描述补充、一个路由条目；技能 metadata 版本 0.4.0 → 0.5.0 |
| plugins/grad-companion-plugin/commands/radar.md | 描述补充、一个路由条目 |
| maintenance/grad-companion-plugin/reports/learning-research-update-2026-10-23.md | 本报告，仅 dev |
| maintenance/grad-companion-plugin/evals/learning-research-cases-2026-10-23.md | 合成响应记录，仅 dev |

运行协议约 2,200 汉字、六节；两个入口的 Git diff 共 5 行新增、3 行删除（含描述与版本的替换行）；实际新增路由各一行，不改变其他正文。脚本、schema、配置字段、阅读协议、其他技能与 README 均未改。

## 检索与取舍

先核对本地能力，再按 skill-search 方法执行 skills CLI 帮助及两项查询。实际调用形态为：

```text
npx --yes --cache <临时缓存> skills --help
npx --yes --cache <临时缓存> skills find "research ideation"
npx --yes --cache <临时缓存> skills find "learning path"
```

临时缓存占位符仅用于报告去除本机路径；实际命令使用临时目录。未执行 skills add 或安装任何候选。目录用于发现，安装量未用于质量判断；learning path 的部分结果只是词面相近，未收录无关条目。通过 GitHub connector 定位、读取原始文件；仓库检索未命中时使用已核仓库目录定位，不把搜索空结果当成文件不存在。

以下是方法比较，不能理解为这些项目在当前宿主已安装或经集成验证。

| 原始来源及实际阅读范围 | 少量可取之处 | 未采用部分 |
| --- | --- | --- |
| [Cursor create-learning-path](https://github.com/cursor/plugins/blob/8b3326d99fd4b993cb33a24dad8af03175c642c5/teaching/skills/create-learning-path/SKILL.md) 与 [run-learning-retrospective](https://github.com/cursor/plugins/blob/8b3326d99fd4b993cb33a24dad8af03175c642c5/teaching/skills/run-learning-retrospective/SKILL.md)，全文；同版本 teaching/README 也已读 | 目标与基础决定下一步，按明确反馈调整节奏，控制材料数量 | 固定周计划、每阶段必须练习、绑定某个宿主提问工具 |
| [Anthropic scientific-problem-selection](https://github.com/anthropics/life-sciences/blob/main/scientific-problem-selection/SKILL.md)，全文；[风险参考](https://github.com/anthropics/life-sciences/blob/main/scientific-problem-selection/references/02-risk-assessment.md) 第 1–180 行；[决策树参考](https://github.com/anthropics/life-sciences/blob/main/scientific-problem-selection/references/05-decision-tree.md) 全文（请求范围 1–170 行） | 把关键假设提前验证；新证据出现后重新判断下一步 | 九模块框架、固定产物和周期、概率评分，以及以高影响突破贬低增量研究的倾向 |
| [K-Dense scientific-brainstorming](https://github.com/K-Dense-AI/scientific-agent-skills/blob/593377bb048752abb0152deab9fbb1083a6087df/skills/scientific-brainstorming/SKILL.md)，全文；同版本 references/idea_evaluation.md 第 1–130 行；已核引用目录存在 | 用于反查边界：提案、假设与证据分开，未知不是零，搜索未命中不证明新颖性 | 群体研讨十步流程、打分矩阵、附带 CLI 和新的登记格式；不据目录存在宣称这些脚本已验证可用 |
| [SakanaAI/AI-Scientist README](https://github.com/SakanaAI/AI-Scientist/blob/main/README.md) 与 [generate_ideas.py](https://github.com/SakanaAI/AI-Scientist/blob/1de1dbc1f4ee2c5f61e9c94348d55eb51d7fa2eb/ai_scientist/generate_ideas.py)，全文，由只读协作审查核验 | 想法应受现有资源约束，并说明可做的实验；核最近邻工作后再决定是否推进 | 数值自评、批量生成、自动实验/写作和二元 novel 判断；源码在异常或未形成结论时可能保留默认 False，不能把这种结果等同于不新颖 |

可复核快照：Anthropic SKILL 文件 blob 为 a139a4dbe32900d6d8860b6268c5c2effab6aef4，风险参考 blob 为 3c3c46ac6cf1979c8455e94e0db01fd61c9a7bc8，决策树 blob 为 84cf808a9ae674a54ba02fa252b7181c11fbe290；AI-Scientist README blob 为 6d9b58e462117e7b653ae2a34407e96c3d0ce16a。以上 blob 均为文件对象，不是提交号。Cursor、K-Dense 及生成想法源码的链接已固定提交。

许可核查限于本次方法比较：Cursor teaching README 声明 MIT；Anthropic 技能的 LICENSE.txt 全文为 Apache-2.0；K-Dense 技能元数据声明 MIT；AI-Scientist README 自述特定源码许可，未单独读其许可全文。本次没有复制第三方代码、模板或成段规则，也没有安装或运行外部项目；以原创短规则表达所需机制，并保留来源。没有把第三方框架整套引入。

## 关键设计决定

- 长期学习请求按需加载协议；普通读文和概念问答优先完成本题。已采用双轨流程时，只在实质线索出现后补阶段判断。
- 学习材料可用、读过原文、理解程度和本人实验分别处理。允许边学边试，不要求学完整张地图才探索。
- 发表目标由明确偏好给出；评价体系与版本不混同。通用规则不预置某个人的门槛、领域或平台路径，阅读材料质量也不随发表门槛降低。
- 接受问题明确、差异合理、证据相称的增量贡献。建议最小验证、收敛课题、开始写作或投稿核对，避免把可发表判断做成综合评分。
- 时间估计包含条件、依赖、重叠和缓冲；当前机会与预计投稿时风险分开判断。保留未核实状态，不承诺录用概率或未设置的后台监测。
- 沿用 idea-ledger、run-provenance、submission-gate；不引入新数据库、配置或私人记录格式。

## 验证与限制

- 主流程在授权环境确认初始工作区干净且为 dev；main 与 dev 的提交分别为 a673fd8340c274f04d22e8bb5cf77e99b62e1ccf、304a1443d2740592b8696d55e40659da2b6e1c43。未切换分支、提交、推送或修改 main。
- 已运行 `python -B maintenance/grad-companion-plugin/evals/test_reading_upgrade.py`：35 项通过，0 失败。仅使用临时目录的合成记录；它验证已有脚本契约，不证明新提示词的教学效果。
- 检查两个入口的完整 Git diff，只有描述、路由及技能 metadata 版本变化。新增协议人工全文审阅；运行文件的 8 个本地 Markdown 链接均存在，无指向 dev-only maintenance 的依赖。
- 一次性路径扫描最初把 URL 末尾字母加冒号误识别为盘符，修正边界条件后通过；这是检查表达式的误报，没有因此改动 URL 或产品逻辑。
- 只读协作审查实际生成 8 组合成响应，均满足本次观察点，详见[评估记录](../evals/learning-research-cases-2026-10-23.md)。据审查将“记录建议的依据”收敛为“说明建议的依据”，减少非必要落盘歧义。
- 普通沙箱及子代理中的 Git 目录访问曾被拒；主流程使用获准访问完成分支与差异核查，未修改 Git 配置。协作审查只声称完成内容审阅，不声称独立核实 Git 状态。
- 未验证真实长期学习效果、实际刊会录用或数月后竞争变化；没有更新安装缓存、全局指令、个人偏好记录或任何网站内容。源文件更新不等于已安装副本生效。

## 分支交付

此轮只在 dev 工作区写入以上 5 文件。后续若获准整合 main，只选择 3 个运行文件；两份 maintenance 文档留 dev，不能整分支合入。没有提交或发布，本报告的技能版本不代表安装包版本。
