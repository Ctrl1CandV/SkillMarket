# 逐项落实与证据

状态属于本轮有限样本，不能外推为每次技能调用的保证。`implemented` 仅表示文字/资源已实现；`verified` 表示相应范围有实际核对；`evaluated` 表示评价已完成但收益结论受证据限制。2026-10-26 用户允许局部场景未达预期并参与评价，R33 的当前判断由 [追加说明](../ACCEPTANCE-ADDENDUM-2026-10-26.md)限定；原要求和终审作为历史保留。

下表中的 `F` 指仓库根 frontend-craft，`P` 指 product-design。静态原始差异可从 Git 查看；[规则复核](static-rule-review.md)记录文本范围，[样张报告](style-lab-review.md)链接真实截图与操作结果，[运行清单](../evidence/run-manifest.json)链接六份实现记录。[盲评](blind-comparison.md)与[最终比较](comparison-report.md)在独立观察完成后形成。

| ID | 状态 | 实现位置 | 核对范围与原始证据 |
| --- | --- | --- | --- |
| R01 | verified | F/P SKILL 触发与职责 | 静态边界已核对；独立构建均直接推进，没有向用户要求额外审批。多 Agent 是本轮评测隔离，不是技能运行前置。 |
| R02 | implemented | P SKILL；product-context；examples | 六份 BUILD 记载产品取舍；是否转为更好关系由盲评/对比判断，不能仅凭表格验证。 |
| R03 | verified | F/P SKILL；new-and-redesign | 条件已核对；运行范围含所有六篇资料、十二项作业、八件作品，代表页面未冒充全部范围。 |
| R04 | verified | P SKILL；product-context | 原始 brief/data 与构建输出均保留演示身份；未补造访谈或真实研究，假设与工程限制分开记录。 |
| R05 | implemented | P SKILL；new-and-redesign | 原文规则已落实；入口与对象连续性的实际效果见完整运行产物及盲评。 |
| R06 | implemented | content；F/P SKILL | 必需数据和完整阅读/核验/展示路径进入实现；视觉与操作完整性仍由逐场景比较决定。 |
| R07 | implemented | content；layout | 重要性可通过面积/对比/时机表达，未设全部置顶；实际主次见同状态宽屏捕获。 |
| R08 | verified | content；review | 标签/重复改为有条件；样张搜索、引用往返、表单标签和反馈实际运行。未声称完整读屏审计。 |
| R09 | implemented | content；scenarios | 密集操作两份 BUILD 记录排序/筛选、跨筛选选择和混合批处理；独立比较核对结果。 |
| R10 | implemented | layout；F SKILL | 构图判断前置于布局原语；是否形成更佳主体和连续面以盲评为准。 |
| R11 | verified | layout；visual-style | 长中文、表格、列表、正文进入三主题实际画面；数值保留为可推翻的起点。 |
| R12 | implemented | layout；scenarios | 1440/390 CSS px 的样张往返已运行；六产物窄屏连续性由各 BUILD 与统一捕获/盲评核对。 |
| R13 | verified | layout；style-lab | 样张三主题窄屏实际根宽度不超出视口，引用目标不被固定头部遮挡；意图滚动区不当作页面溢出。范围限已运行状态。 |
| R14 | verified | visual-style；cjk-typography | 三主题真实尺寸看过标题、正文、工具、注释及混排；原始截图与字体栈在样张证据中。 |
| R15 | verified | cjk-typography | 已核对字体栈和 Windows 已安装候选。未声称逐字形落在哪一字体，未编造跨浏览器兼容结论。 |
| R16 | verified | visual-style；style-samples | 三主题同内容实看，包含浅冷、深色、纸色不同底调/表面/强调关系；不以按钮色或对比数值证明好看。 |
| R17 | verified | visual-style；review；style-lab | 实际空值验证、反馈状态、选择+警告+键盘焦点；51 对声明颜色角色计算见 contrast-check.json。 |
| R18 | implemented | visual-style；scenarios | 成熟控件可用，无强迫新奇条款；工具/阅读成品是否无操作退化由比较判断。 |
| R19 | verified | F SKILL；visual-style | 精修边界静态核对；本轮未以精修名义重写候选结构，没有自设禁止空间联动规则。 |
| R20 | verified | content；visual-style；scenarios | 演示身份明确；作品 SVG 原始数据保留；外部许可/图像分别有来源记录，未编造科学结果。 |
| R21 | implemented | scenarios；examples | 固定目录/多栏改为条件；阅读配对看实际关系而非按栏数评分。 |
| R22 | verified | review；scenarios；content | 样张定位/返回/临时预览与反馈真实运行；构建记录另包含刷新、保存和恢复。未声称无后端的演示已经云同步。 |
| R23 | verified | P references/examples.md | 静态逐例查看了竞争目标、取舍、界面结果和调整条件，覆盖工具与展示。 |
| R24 | verified | reference-selection；exemplars | 新资源记录任务/形态/密度/语言/设备差异；候选构建按任务选择 Tufte/Tabler 等实际参考，详见各 BUILD。 |
| R25 | verified | reference-selection；review；assets/references | 六张真实原始图由采集者与独立审查者查看；观察、状态与边界在 capture-manifest 和 SOURCE/ATTRIBUTION 文件。 |
| R26 | verified | exemplar-index；exemplars | 14 项=4 candidate+4 documented+6 verified_visual；继承 Oil 和方法文章未升级为已看图。资源检查仅作字段辅助。 |
| R27 | verified | assets/references；exemplar-index | Tufte 仅作为阅读补充；后补 Wikipedia 正文 [21] → Cho 2014 高亮来源两图及真实回链经独立审查，密集操作/展示另由 Tabler/PhotoSwipe 支撑。6图4主体；后补资源未参与六次生成，详见 post-freeze-resource-supplement。 |
| R28 | verified | assets/style-lab；style-samples | 三主题1440/390、各视图与声明行为已实际运行。file URL 被宿主策略限制，离线自包含性静态核对；真实运行经无外部依赖的 localhost。 |
| R29 | verified | style-samples；style-lab | 原创身份、演示内容与临时预览说明明确，未计入外部来源；运行资源不含整轮维护记录。 |
| R30 | verified | review；F/P SKILL | 样张及配对实现完成整屏、实际尺寸与操作观察，冻结盲评记录逐维得失；按实际观察修正来源覆盖，没有将看图流程完成等同效果通过。 |
| R31 | verified | F/P SKILL；refs | 按需加载、无第三技能/偏好审批/完整 PRD 强制项；本次评测材料留 maintenance。 |
| R32 | verified | evidence/run-manifest；builder-protocol | 六个无历史构建上下文、同字节输入、单次尝试、同宿主工具与约定预算，22张统一捕获及盲评完成；非物理隔离、模型精确build/硬预算/逐字启动导出限制明确，后补资源未参与生成。 |
| R33 | evaluated（证据有限） | evidence/runs；comparison-report；user-feedback-2026-10-26 | 三组配对与22图及关键行为评审完成，整体相当、局部有得失。用户认可阅读两版布局，认为差距不明显，略偏向旧版标题层级；阅读局部评价和原因核查收束。按新要求不强制阅读胜出，也不将局部认可扩大为整体采用或效果提升。 |
| R34 | verified | 各原始记录与报告 | 区分静态/实测、截图/CSS尺寸、reduced UA/精确版本、字体供应/实际字形；未运行项明确列出。 |
| R35 | verified | 两技能根目录；maintenance；closeout | 原包校验与基线比对通过；用户后续明确授权双分支提交推送，运行资源进入main/dev，维护只入dev，原有配置删除单独同步。原包完整归档、RC保留，无发布标签或安装，详见closeout。 |
| R36 | verified | prompts/02-final-review.md；final-review.md；acceptance-reassessment.md；user-feedback-2026-10-26 | 首次无历史独立终审已完成，按当时要求结论为 INSUFFICIENT_EVIDENCE。随后独立复核新标准及本次阅读反馈的解释范围，保留旧结论；实施与核查收尾不等于已证明新版整体更好或用户全面接受。 |

本表已根据冻结盲评、来源补正、首次独立终审、用户追加要求及实际阅读反馈更新。R27 已补齐；R33 已完成有限评价，保留相当与局部得失，不再机械要求主要阅读胜出。`verified` 中明确的局部范围不构成对每次技能调用效果的保证。
