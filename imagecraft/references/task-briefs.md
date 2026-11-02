# 任务组织与看图验收

本地默认 FLUX.2 klein 4B，保留极速素材与参考编辑；短中文标题等低密度文字可显式选 Z-Image Turbo，仍逐字验收。要求高且可接受栅格成品时走 [云端路径](cloud-fallback.md)。先改善任务表达、参考图和验收，再讨论是否增加模型；模型不应因读到“动漫”“网页”等词就自动下载专用权重。以下是起点，不是强制审美模板。

共同前提：把“必须出现的文字”和“必须避免的元素”写成清单，方便实际看图时逐项核对。

## 本机提示词怎么写

FLUX 默认 4 步、Z 默认 8 步，CFG 均为 1，当前工作流没有独立负向提示输入；这不等于模型完全不理解语义否定。先写清 brief，短写法已经表达完整就直接提交，**不强制 120–300 词**。宿主可在缺少细节时补写英文画面描述，原 brief 留在 `briefs/` 作为验收依据，不让扩写擅自增加对象或冲突条件。

本机 FLUX 的三 brief × 长短 × 正负 × 两 seed 共 24 张对照，没有证明长段落或正面写法普遍更好：长产品描述把侧窗画进了要求留白的墙，长页面仍把四指标画成三块，肖像长短都可用。另一个颜色 pair 也没有显示 HEX 更准。这些只针对当前具体写法，扩写还增加了细节，不是纯词数的因果试验。

需要扩写时，可按下面的顺序检查，不必每项都写满：

1. **开头一句定性**：媒介、风格、主体、背景与色调，例如 "A wide editorial photograph of a ceramic teapot on a weathered oak desk, warm ivory background."
2. **按画面位置走一遍**：先背景，再从上到下、从左到右写每个区域，多用 "in the upper-left corner""across the lower third" 这样的位置短语；人物或单个物体则从姿态到面部、衣物、手中物依次写。
3. **要出现的字**：每段文字写清位置、字重、颜色和内容，用英文直引号原样给出，中文就写中文；越短越好。不需要可读的字写成 "blurred, too small to read"，别让模型编字。
4. **单独一句写光线**：光源、方向、软硬和阴影。
5. **一句收尾**：整体构图、配色和情绪。

另外几条：

- **把期望效果写具体**，如 "flat matte colors, soft daylight, plain off-white background"；少量明确禁止项可以保留，但正负表达都不是硬约束。对照里否定版没有招来霓虹，页面投影在两种写法中都出现，不能把禁止词本身当作失败原因。GPT 的禁止项也要看图核对。
- **不加质量咒语**："masterpiece, 8K, highly detailed" 对这类模型没有约束力，换成具体的材质（brushed metal, coarse linen, frosted glass）。
- **颜色名称或色值只表达方向**，如 "muted terracotta"；不声称 HEX 更稳定。品牌色必须准确时，在 SVG/CSS 或真实排版层设置，不靠扩散提示锁色。
- **中文长句、多处小字不要指望本机写对**，留白后用真实字体叠加（[局部修补](raster-repair.md)）。
- **比较方向时固定其他条件**：同一段提示词换 2–4 个 seed 挑构图；比较风格时固定 seed，只改风格那一句。

## 通用任务

把主体及动作写在前面，然后写空间关系、视角/构图、材料/光线、风格和少数不可违反的约束。需要产品结构准确、人物一致或品牌约束时使用有权使用的参考图，区分“必须保留”和“允许变化”；不借参考图暗示结果具有来源认证或真实拍摄身份。

没有指定风格时，选一个符合用途的具体方向，不把互相冲突的风格并列。需要比较时固定 seed、尺寸和其他条件，只改变一个主要因素。不同 GPU/后端版本不保证逐像素复现，保存工作流与实际版本信息。

通用验收检查：主体数量、关系与位置是否正确，裁切是否符合用途，是否出现多余物体、融化形状、假纹理或难看的文字。扩散输出是栅格图，不声称拥有矢量、图层、透明通道或可编辑的原生设计文件。

## 人像 / 写实

先明确年龄段为成年人、场景与服装、半身或全身、相机视角和光线。自然皮肤、可信面部比例和符合环境的光照比“完美面孔”更可验收；不要默认磨皮、白化肤色或固定性别审美。有真实人物参考时，遵守本人许可、隐私和宿主安全规则，不协助侵犯隐私、非自愿性图像或误导性冒充。

示例方向：

> Editorial half-body portrait of an adult ceramic artist in a sunlit studio, plain indigo work apron, natural skin texture, relaxed expression, hands resting on the wooden workbench, soft side-window light, understated warm colors, realistic photography.

看图重点：脸部与手指结构、眼神方向、肢体数量、衣服与工具边界、皮肤及光照。若手被藏起来或裁掉，不能把它算作“手部生成已通过”。身份保真和细节保留不是首版的保证。

## 动漫 / 插画

先给角色轮廓、发型服装、姿态、线条和上色方法，再给环境与镜头。用可描述的视觉特征，不要求必须模仿某位作者才能出效果。可以选干净赛璐璐、柔和水彩、厚涂或复古版画，但一次别全选。

> An original adult courier with short dark hair and an orange utility jacket, standing beside a compact bicycle at a rainy train station, clean anime line art, restrained cel shading, teal and amber palette, clear silhouette, calm cinematic framing.

看图重点：角色特征是否贯彻、线条与阴影是否一致、肢体及配饰是否粘连、背景透视与主体比例。构图可用但五官、手或标志性服饰失真时明确指出，不因“像动漫”就判定通过。

## 网页视觉参考

先确定页面任务、目标读者和真实内容，把它当设计参考而非成品页面。需要跨页体验或核心流程时先做产品设计；单页构图可衔接页面设计技能。明确画幅、信息密度、文字区与图片区、视觉重心和要保留的空间。不要一律生成玻璃渐变、悬浮卡片和泛化 SaaS 标语。

> Desktop landing-page visual concept for a neighborhood ceramics studio. Warm ivory background, charcoal editorial typography, muted terracotta accents. A quiet left-aligned headline area with generous whitespace, one large pottery photograph on the right, a compact navigation bar and a clear workshop booking action. Below, a restrained three-column class schedule. Show a coherent full page, not a browser/device mockup. Short English labels only.

看图重点：真实内容能否放进去、标题和操作的层级、对齐与留白、图文关系，以及参考图转实现的价值。用户允许范围内的小字瑕疵可以保留并说明；主要标题、重要数值或控件缺失仍要指出，不能把大块乱码称为可用。生成结果的指定文案逐字通过后，视觉图可以直接交付，不必为了准确而整图重画。

只需要 hero 背景或插画时生成对应无字资产。静态视觉图可直接叠真实字体；真实页面再用 HTML/CSS 组织文字、按钮并检查窄屏和交互，不能把整张 PNG 铺成网页。少量错字可考虑 [局部修补](raster-repair.md)，密集准确数据则优先独立内容层。

## 高密度产品界面（视觉稿）

要做“像真在用”的后台或工作台截图，难点不在笔刷而在信息量和一致性。分两段写：先列区块与字段，再写风格约束。

内容清单示例（直接当提示词主体，不要压缩成形容词）：

```text
顶部：产品名、工作区切换、搜索框占位文案、期间筛选、主按钮
侧栏：分组标题 + 八项导航，其中“审批流”带角标 7
指标条：四张，标签与环比同行、数值紧贴其下
图表：标题、图例、12M/6M/30D 区间，两个序列、淡网格线
右列：待审批两条（金额+等待时长）、预算执行三条进度、账户余额三条
主表：标题、三个切片、导出、七列表头、七行数据、页脚“第 1 / 12 页 · 共 236 条”
次表：待核销发票，四列表头、两行
```

风格约束一行写完，用禁令而不是赞美：

> 高密度企业控制台，8px 间距节奏，20px 卡片内边距，1px 发丝线代替阴影堆叠，金额右对齐等宽数字，状态用小号低饱和圆点加文字，单一强调色，三级字阶。无霓虹、无玻璃、无渐变、无 3D、无插画、无照片、无超大圆角、无 emoji、无假 logo。

看图重点：每条字符串是否一字不差（金额符号、千分位、`¥` 与 `-` 尤其容易错）、表头与列是否对齐、状态是否与数值自洽、有没有凭空多出的卡片或坐标轴。多出的东西也是偏离，要报。

历史几张样例在压矮指标卡、加分组小标题和次级表后容纳了更多字段；这不能证明总体更稳，也不能把单张字段增长当成稳定性统计。这类图只适合当视觉稿或演示素材；用户要真页面时转前端实现。

## 架构图 / 流程图

严谨图先有独立的内容清单，不要求最终必须是纯代码框图。例如：

```text
nodes: client, api, queue, worker, model, storage
edges:
  client -> api: request
  api -> queue: enqueue
  queue -> worker: consume
  worker -> model: inference
  worker -> storage: save output
  storage -> client: retrieve result
```

先核对清单是否符合真实需求，再决定视觉路径。用户希望丰富插画时可生成整图，给标签和连线留干净通道；对照清单逐字逐边验收，全部正确可以交付生成图。需要可编辑性或密集复杂拓扑时，选 SVG/Mermaid/Graphviz 或素材与确定连线的分层合成，不强制所有架构都用同一种朴素布局。

标签正确不代表关系正确，OCR 也不能证明箭头的起终点和方向。少量孤立错线/错字可修补，再复核全部边；缺组件、合并节点、交错关系未解决时不得标为完成。提示词或正确参考图不是硬锁定。交付时分别说明模型画的部分、程序改的部分及内容依据；不要把未经查看的源文件当作已验证图片。

## 修改轮次与增配门槛

每轮记录用户要求、实际看到的差异、改动和结果。单张图失败先修正歧义、提示词和输入；改善仍有限时，向用户展示当前结果与局限，再讨论专用模型。增加一个模型意味着额外下载、许可证、显存/内存和维护成本，不是免费的质量开关。其他方向无需为了“全覆盖”预装模型。
