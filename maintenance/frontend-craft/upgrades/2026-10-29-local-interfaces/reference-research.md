# 局部界面参考核查与入库选择

核查日期：2026-10-29（Asia/Shanghai）。依据：[已批准计划](../../reports/local-interface-upgrade-plan-2026-10-28.md)及[首批 12 组候选](../../reports/local-interface-reference-candidates-2026-10-28.md)。

本轮成功读取 12 组候选的一手文档，并补查 VS Code 设置编辑器和 GitHub PR 审查。按关系增量采纳原候选中的 8 组，加上 2 组非 API、非学术阅读来源，共新增 10 个 `documented` 条目。其余 4 组保留在维护候选中，不因已找到链接就进入运行索引。

## 核查方式与证据范围

- 使用 web 工具读取官方页面文字、相关章节与图注；访问成功不等于页面视觉已经核验。
- 未登录或操作产品，未查看图像像素，未获取本地截图；没有新增 `verified_visual`，没有把来源声明当作本技能效果证据。
- 下列“可借鉴”是依据来源作出的迁移判断；产品能力和图像入口是文档所述事实。未验证中文、窄窗口、真实长内容及组合状态的表现。
- 仅保留链接；未核查图片再分发授权，不下载或分发图片。既有画面、许可和证据记录保持原样。
- 机器索引保持 `schema_version: 1`，使用既有字段；核查日期、关系和限制放在 `notes`。新增条目的 `screenshots` 为空，`capture`、`license`、`review` 为 null。

## 采纳的产品关系

### 1. Open WebUI：连接对象与条件字段

- 成功访问：[OpenAI-Compatible](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/)。核对添加连接、手动模型列表、启停说明。
- 文档证据：连接包含地址、凭据和可选模型；验证后可获得模型建议，启停不删除配置。
- 可借鉴：连接列表与编辑窗口各有职责；参数、结果与动作依附同一个连接对象，避免设置散落。
- 限制：验证、模型发现和供应商特例不能照搬。图线索为 MiniMax 配置步骤后的两幅配置图，官方已提示其中模型名称较旧；未看图。
- 入库：`openwebui-connections`。

### 2. Dify：配置所属的对象层次

- 成功访问：[Model Providers](https://docs.dify.ai/en/cloud/use-dify/workspace/model-providers)。核对管理凭据、默认模型与负载均衡章节。
- 文档证据：供应商模型共用的凭据与自定义模型凭据分别管理；工作区默认模型按用途指定，负载均衡在模型配置内。
- 可借鉴：服务身份、具体模型与默认选择不是同一种设置；入口和操作范围随所属对象安排。
- 限制：插件、计费及密钥池仅在目标产品真实具备时适用。图线索为供应商凭据、自定义模型配置与负载均衡配图；未看图。
- 入库：`dify-provider-scope`。

### 3. Bruno：生效值、继承来源与编辑入口

- 成功访问：[Authentication](https://docs.usebruno.com/auth/overview)及[Environment Variables](https://docs.usebruno.com/variables/environment-variables)。入库选择前者，避免重复条目。
- 文档证据：继承身份验证时显示只读有效值、来源和编辑来源链接；查看有效值不会改变继承模式。环境文档也区分当前选择、父级及覆盖。
- 可借鉴：把“现在使用什么”“由哪里决定”“去哪里修改”放在同一关系中，区分查看与改变。
- 限制：无继承的产品不添加层级。图线索为继承身份验证的来源提示和只读字段；未看图。
- 入库：`bruno-inherited-auth`。

### 4. VS Code：混合控件、作用域与修改状态（新增）

- 成功访问：[User and workspace settings](https://code.visualstudio.com/docs/configure/settings)。核对 Settings editor、Settings groups、Modified settings、Reset settings。
- 文档证据：分类和搜索帮助定位设置；用户与工作区区分作用域；编辑即时生效，修改标记、已修改筛选和单项重置辅助检查。
- 可借鉴：较多设置中的导航、输入、状态和恢复共存；围绕当前作用域组织，不把每个控件都独立做卡片。
- 限制：不能把即时应用迁移成需要提交的草稿行为；不复制其全部层级。图线索为作用域标签、搜索结果、已修改标记及设置菜单；未看图。
- 入库：`vscode-settings-scope`。

### 5. GitHub：局部进度、待提交反馈与整体决定（新增）

- 成功访问：[Reviewing proposed changes](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/reviewing-proposed-changes-in-a-pull-request)。旧 `collaborating-with-pull-requests` 路径已重定向至此，索引使用当前地址。
- 文档证据：侧栏提供关联背景；逐文件检查关联行评论和已查看状态；待提交评论只对本人可见，最终提交审查才形成整体反馈。已查看文件再变化会取消其查看标记。
- 可借鉴：局部完成、草稿与整体动作分开；内容变化可使旧状态失效，而不抹去其他对象的进度。
- 限制：不复制 diff、折叠或审查机制。图线索为文件头查看状态、评论字段及提交审查入口；未看图。
- 入库：`github-review-progress`。

### 6. Readwise：内容旁的会话与相邻动作

- 成功访问：[Chat with your documents](https://docs.readwise.io/reader/guides/ghostreader/chat)。核对打开会话、选段提问、保存回复和切换模型。
- 文档证据：会话依附文档，可带选中文段；模型选择在输入附近，回答可单独存入文档笔记；文档明确区分单文档与全库模式。
- 可借鉴：消息阅读、当前提问材料和保存某条结果分别归属相应区域与对象。
- 限制：不混写两种会话范围；未确认长回答、焦点及位置保持。图线索为聊天侧栏、回答下方笔记动作和模型选择；未看图。
- 入库：`readwise-document-chat`。

### 7. Zotero：主体、注释与可编辑结果

- 成功访问：[PDF Reader and Note Editor](https://www.zotero.org/support/pdf_reader)。核对注释加入笔记及来源链接。
- 文档证据：笔记面板可接收正文或注释列表中的内容；加入笔记的注释保留 PDF 页面回链与引用。
- 可借鉴：主体阅读、辅助整理和编辑结果有明确联系；移动内容后仍能返回来源。
- 限制：注释编辑与长会话不同，不推广为三栏比例。图线索为文档开头阅读器整体图及由条目创建笔记示例；未看图。
- 入库：`zotero-annotation-notes`。

## 采纳的组合方法

### 8. Carbon：分组和动作区共同对齐

- 成功访问：[Forms](https://www.carbondesignsystem.com/building-blocks/core/patterns/forms)。核对相关任务分组、按钮、间距和容器差异。
- 文档证据：字段按相关任务分组，组间与组内空间有区别；页面表单与容器表单采用不同动作排列，后者可使用通栏动作组。
- 可借鉴：将标签、字段、组间距与完成动作作为整体安排，而非逐项加装饰。
- 限制：贴边、按钮次序与尺寸属于 Carbon 的系统选择。图线索为表单间距、页内与容器动作排列；未看图。
- 入库：`carbon-contained-forms`，类型为方法依据。

### 9. Primer：有完成边界的窗口结构

- 成功访问：[Dialog guidelines](https://primer.style/product/components/dialog/guidelines/)。核对可选副标题区域、主体、页脚及滚动。
- 文档证据：筛选或局部导航可放在副标题区域，主体按内容滚动；主动作与相关动作在页脚右侧成组，辅助动作可在左侧。
- 可借鉴：搜索、内容和完成动作有稳定职责；与 Carbon 通栏是不同的整体解法。
- 限制：不拼接两套系统的零散控件，也不把整页设置压入一个对话框。图线索为右对齐页脚、左侧辅助动作和滚动主体；未看图。
- 入库：`primer-dialog-regions`，类型为方法依据。

### 10. Fluent：共视关系与错误归属

- 成功访问：[Drawer](https://fluent2.microsoft.design/components/web/react/core/drawer/usage)及[Dialog](https://fluent2.microsoft.design/components/web/react/core/dialog/usage)。入库选择 Drawer，Dialog 的主体/页脚关系由 Primer 覆盖。
- 文档证据：并置抽屉允许同时操作主体，覆盖抽屉引导关注；单个分组失败的提示放在该组，整体失败采用对应整体状态。
- 可借鉴：依据是否需要共视选择容器；按影响范围组织错误与恢复，避免错误或辅助内容占满整个区域。
- 限制：原文短任务的步数和遮罩建议不推广为所有局部界面的限制。图线索为 Inline、Overlay 和 Section loading error；未看图。
- 入库：`fluent-drawer-states`，类型为方法依据。

## 本轮不加入运行索引的四组

| 来源及本轮成功访问地址 | 暂缓理由及重新考虑条件 |
| --- | --- |
| [n8n 凭据](https://docs.n8n.io/build/understand-workflows/create-and-edit-credentials.md) | 服务选择、凭据复用及保存测试与当前配置来源重合；材料以流程文字为主。若需要研究真实失败恢复或找到完整表单状态，再采纳 |
| [Ant Design Drawer](https://ant.design/components/drawer/) | 表单、预览和多层抽屉演示入口可用，但本轮没有操作演示，与 Primer/Fluent 覆盖重合。需要中文长标签或特定抽屉实现时再读，不据组件支持推导应叠加窗口 |
| [Semantic Scholar Product](https://webflow.semanticscholar.org/product) | 当前材料主要介绍扫描摘要、引用和论文功能，不能支持完整复杂详情的组织；与现有阅读依据相比增量不足。取得完整详情及相关状态后再考虑 |
| [Elicit Reports](https://elicit.com/blog/introducing-elicit-reports) | 官方文章发布于 2025-02-26，描述报告、步骤和引用，含营销比较；不作为当前完整操作证据。需进一步核验完整报告与证据查阅关系后再进入运行库 |

暂缓不等于来源质量差；这里只判断它们对本轮已选关系是否增加足够信息。保留原候选文件中的追踪线索，不新增重复的机器候选条目。

## 入库后的使用与剩余缺口

运行索引新增 10 个条目：配置对象与范围 3 个，跨业务状态与动作 2 个，阅读与内容生产 2 个，组合方法 3 个。它们提供不同决策关系，不构成预设界面模板，也不直接提供最终验收题答案。

完整局部画面及变化过程仍缺实际视觉证据。后续选用某个来源时，应按当前任务查看相关图像或可用公开界面，再核对真实内容与状态；不要因为这些条目已 `documented` 就宣称外部画面经过检查。中文内容、长短差异与多状态共同出现由本轮开发样例及独立评估检验，不从官方链接数量推断覆盖充分。
