# 联合升级执行记录

Git 收尾更新：用户后续明确要求清理及 main/dev 提交推送，见[收尾记录](closeout.md)。原解压包已完整归档、临时服务已停止；以下“未提交/原包保留”仍按首次执行时点理解。

**后续状态说明：** 本报告正文记载首次执行及按当时要求形成的终审。此后用户明确允许局部场景未达预期，并给出实际阅读评价；当前以[验收追加说明](../ACCEPTANCE-ADDENDUM-2026-10-26.md)和[用户反馈记录](user-feedback-2026-10-26.md)为准。用户认可两版布局、整体差距不明显，略偏向旧版标题层级。阅读原因核查已收束，不再把主要阅读必须胜出作为单项硬门槛；实施与核查完成不等于已证明整体提升。以下原执行事实和原终审结论保留。

文件替换与补全、六个独立实现、22张统一截图、冻结盲评及独立终审均已完成。独立终审结论为 **INSUFFICIENT_EVIDENCE**：外部来源覆盖缺口已经补齐，但主要阅读结果尚不足以支持有意义的整体改善，整轮升级不能标为通过。候选保留 RC。

## 范围与合并

执行依据为用户给出的完整五轮会话、原始交付包及本目录 `prompts/01-complete-and-evaluate.md`。核心意图是让产品依据转成实际界面关系，把整屏构图、文字、密度、颜色、素材和行为作为共同设计对象；成熟参考提供默认方向，真实成品检查负责验证，不要求用户反复做偏好审批。

仓库位于 `D:/Program Project/SkillMarket`，分支 `dev`，起点 HEAD 为 `eddd2176090961bc5247f2050e7015aec538d53a`。与包内固定基线 `d4c9eadcaa8f7ba287c3cd7f61a26775552eaf11` 的十二个运行文件比较后，内容均一致：frontend 八个文件只有 CRLF 差异，product 四个文件字节一致。因此合并完整候选，没有覆盖这两个技能中的后续有效修改。

原包 55 个 SHA256 项全部匹配。原始解压包保留不动，原交付 manifest、哈希与入口说明另存于 `delivery/original-*`。旧运行资源存于 `evidence/baseline/`，维护材料留在 dev 的 maintenance。起点已有的 `write-with-judgment/agents/openai.yaml` 删除保持不动。没有提交、推送、合并远程分支、发布或安装个人技能。

受审版本保持 `frontend-craft 0.5.0-rc.1`、`product-design 0.2.0-rc.1`。见 [包校验](package-integrity.json)、[合并判断](merge-check.json)、[静态规则审阅](static-rule-review.md)。

## 实际补全

1. 将完整候选正文、十四个 Markdown 运行文件、索引及三主题 style-lab 合并到仓库根部两技能目录。没有另写第三技能，没有把本次维护追踪变成运行技能的必走流程。
2. 加入六张真实外部画面：Tufte CSS 连续正文与编号旁注，Tabler 七列十五行排序表格，PhotoSwipe 首屏画廊和首图灯箱，Wikipedia 正文引用和来源定位。来自四个独立发布主体。终审指出 Tufte 不能单独承担证据核对覆盖后，补充了 Wikipedia 两图和实际回链检查；该补充发生在六次构建冻结后，不计作构建输入。原图、许可、状态和迁移边界均保存；MIT 代码/文档、Unsplash 摄影和 Wikipedia CC BY-SA 4.0 文字及页脚商标分别记录。
3. 原 Oil 四项仍为 candidate，四项方法资料仍为 documented；没有用 inherited 描述、作者宣传或原创样张替代已看过的外部界面。最终索引为十四项，其中六项 verified_visual。见 [采集记录](../evidence/references/README.md)、[采集清单](../evidence/references/capture-manifest.json)、[冻结后补充](post-freeze-resource-supplement.md)。
4. 三主题均实际查看桌面与窄屏，并执行视图/主题切换、列表搜索/清空/筛选、引用往返、临时批注、表单验证和组合状态键盘焦点。字体供应、视口和原始截图尺寸分别记录；51 对声明颜色角色通过相应对比门槛。这些检查未发现需要修改样张源码的具体问题。见 [样张实际检查](style-lab-review.md)。
5. 在无父会话的新构建上下文中执行三场景、两个版本的独立实现。每一方只收到自己的技能、相同原始任务/数据和共同工程条件。六个运行保留全部首轮产物与自检记录。候选在构建前冻结，构建期间没有向任一方提供对方产物或升级诊断。见 [运行清单](../evidence/run-manifest.json)、[隔离和公平性边界](../evidence/builder-protocol.md)、[输入校验](input-integrity.json)。

## 环境与证据边界

Windows 本机 Codex IAB，浏览器 HTTP User-Agent 为 Chrome/156.0.0.0；该 reduced UA 不能当作不可变精确补丁版本。CSS 视口以 1440×1000 和 390×844 为准，截图保留工具返回像素，不拉伸冒充 CSS 尺寸。字体栈与已安装字体已核对，未进行逐字形字体追踪或跨浏览器验证。

页面以已有 Python 本地静态服务运行，端口 8766；服务根为仓库。运行产物只使用本地虚构数据。无障碍验证包括实际焦点、表单语义与相关状态，不是完整读屏审计。浏览器并发期间曾发生全局视口干扰，因此最终配对截图在构建结束后串行采集，旧捕获保留其真实限制。完成浏览器检查后，已核对命令行并停止本次三个临时服务、恢复视口设置，见 `evidence/environment-cleanup.json`；复看可从仓库根运行 `python -m http.server 8766 --bind 127.0.0.1`。

同模型指所有构建者继承相同父模型且不设置 override；宿主未暴露不可变模型 build ID。每方约定相同最多 25 分钟、一次实现及正常自检修复，工具没有硬预算锁和逐步 token 账本。这是六个有限样本的工程比较，不是统计实验或用户研究。

## 收尾状态

冻结盲评和揭盲汇总见 [comparison-report](comparison-report.md)：新版在文字/入口、密度、作品语境有局部优势，也有引用辨识、编号和移动筛选次序的局部得失；主要阅读构图与行为大体相当。R33 不能标为效果已验证。[独立终审](final-review.md)给出的唯一结论为 INSUFFICIENT_EVIDENCE；静态检查、资源结构门槛或执行者自检均不能替代它。原始 PLAN、REQUIREMENTS、ACCEPTANCE、fixtures 和检查器保持交付内容，未为通过降低标准。当前唯一未关闭项及最小继续方向见 [remaining-work](remaining-work.md)，不以重复抽样或单修演示页面替代技能效果证明。
