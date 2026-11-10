# 调研笔记（2026-11-10）

只记对“做出好视频”有用、且能在实验里检验的内容。来源多为业内文章，证据强度一般，所以每条都当作待验证的假设。

## 1. 先有一个能被看见的核心画面

- 产品片要围绕前后对比的“高光画面”来设计，那个只有本产品能做到的时刻拿最多的屏幕时间，其余镜头都为它铺垫。问题状态要不用解释就能认出来（Every product-launch-video SKILL.md）。
- 讲解片把一个概念先写成一句大白话，再选一个具体的视觉替身；成败在于隐喻选得对不对，跟镜头数量关系不大（prompt-architects；animationexplainers.com 的 30 个例子）。
- Kurzgesagt 流程的前三步都发生在写稿之前：先把信息画出来、理清结构、搞清各部分怎么连起来；脚本是最慢的环节，要反复删短（UX Munich 2015 讲座的二手整理）。
- 24 支 SaaS 发布视频：几乎都直接展示真实界面；动效类中位时长约 50 秒；每个镜头只有一行字，静音也能看懂；结尾落在产品名或标志（asapmotion.co）。

**实验假设 H1**：0.1.x 的结果平淡，是因为没有先找到这个核心画面，后面的分镜只是在给文字配图。

## 2. 一个镜头讲一件事，并在整个时长里持续展开

- HyperFrames 的讲解技能把“场景密度：一个镜头一个想法”称为影响质量的最大因素；每个主体镜头只推进一个机制、步骤、例子或推论；第二个镜头之前要让观众明白主旨。揭示的节奏要跟着旁白铺满整个镜头，不能开头一下全出来然后定住（hyperframes.heygen.com guides/faceless-explainer、prompting/explainers）。
- 如果一个镜头需要两句旁白才能讲清，那就该拆成两个镜头（movingstonedigital）。
- 画面太久不变观众会察觉，哪怕说不出原因；强调要配得上内容，大的想法才用大的动作（thinkinpublic 实用指南）。

**实验假设 H2**：0.1.1 排队题“40 秒同一画面”，问题不在连贯本身，在于画面里没有持续发生的变化。

## 3. 界面与产品的拍法

- 好的发布视频：字填满画面；界面放进有纵深的空间，不是平贴；用焦点转移带动视线；一两个华丽时刻，例如光晕或扫光（Raylight 用例页）。
- Raycast 用连续的摇镜，从搜索框一路带到执行面板，从不切断画面；Notion 用硬切。点击反馈有两种做法：Linear 全屏反色，Raycast 从按钮中心扩散的小涟漪（advids.co）。
- 界面要在 720p 下可读（Every：最小相当于 18 px）。实际做法是镜头推近到界面局部，而不是把整页界面缩在画面里。
- 只用真实界面文案；编造的标签最容易让发布视频显得假（Every）。

**实验假设 H3**：0.1.1 拾光题的界面字小，是因为整页界面平铺在画面里；换成“镜头推进到局部 + 纵深”可以同时解决可读性和单调。

## 4. 动效原则（UX in Motion，Willenskomer 2017）

12 条：缓动、错峰与延迟、父子关系、变形、数值变化、遮罩、叠加、克隆、遮挡、视差、维度、推拉与缩放。其中变形、数值变化、遮罩、叠加、克隆都服务于“对象连续性”：同一个东西改变用途，观众不会跟丢。

**实验假设 H4**：转场最好是同一个对象的变形或镜头穿过它，比淡入淡出、滑动更容易做出“像视频”的感觉。

## 5. 声音

- 嗖声在镜头运动开始前 10–20 ms 起，加一个落点声音标记画面落定；只有物体停下、贴合或出现时才配点击或弹出声；同一个嗖声连续重复会显得廉价，要变音高和长度（sonilo、pixflow）。
- 音乐要压在旁白之下，用来填补空白、推动节奏（thinkinpublic）。

**实验假设 H5**：哪怕没有配音，同步的音效和音乐也会让同样的画面显得精致很多。本机可以用 WebAudio 离线合成。

## 6. 竖屏短视频

- 业内数据（来源不明，只作参考）：多数流失发生在前 3 秒；开头 1 秒内要有画面变化；钩子文字 5–8 个字、一眼读完（OpusClip、Videotto、CapCut 博客）。
- PaperTok（arXiv 2601.18218）：参与者普遍否定以静态截图为主的视频，觉得动态画面更吸引人；抽象概念做视觉转译有助理解。

## 7. 代码视频的现实情况

- Remotion 官方技能 2026 年 1 月走红后，大量人用 Claude Code 做发布视频。好的案例都是先手写故事或分镜、用真实产品素材、一个镜头一个镜头地做；直接一句提示得到的是“非常平淡、像素材库”的视频，再提 10 次也没变好（@rameerez）。还需要设计知识，并用对方能听懂的术语说出想要什么。
- Every 的技能：先分镜后代码；每个镜头先渲一张静帧检查；2–3 轮自查后渲约 20 帧，由设计、可读性、节奏、品牌四个角度的审查者各列修改单，合并后再改。

## 8. 代码独有的强项（我的判断，待实验）

- 能真的模拟：排队题可以让三条队按随机服务时间真实地跑，比贴标签有说服力得多。
- 能用真实数据和真实交互：搜索框真的逐字输入、结果真的过滤。
- 能精确同步：音效、字幕、数字变化都落在同一帧。
- 能生成：粒子、网格、纹理、光效都可以按种子生成，不需要素材。

## 来源

- Every, product-launch-video：https://github.com/EveryInc/product-launch-video
- HyperFrames 讲解指南：https://hyperframes.heygen.com/guides/faceless-explainer ；https://hyperframes.heygen.com/prompting/explainers
- asapmotion.co, 24 SaaS Launch Video Examples：https://asapmotion.co/guides/saas-launch-video-examples/
- advids.co, SaaS Feature Launch Video：https://advids.co/blog/saas-feature-launch
- Raylight, SaaS launch videos：https://www.raylight.app/use-cases/saas-launch-videos
- Willenskomer, UX in Motion Manifesto：https://medium.com/ux-in-motion/creating-usability-with-motion-the-ux-in-motion-manifesto-a87a4584ddc
- thinkinpublic, A Practical Guide to Making Animated Explainer Videos：https://www.thinkinpublic.app/post/a-practical-guide-to-making-animated-explainer-videos
- Designer Daily：https://www.designer-daily.com/motion-graphics-that-actually-communicate-lessons-from-explainer-videos-213110
- Kurzgesagt 流程整理：https://stuartelliotblog.wordpress.com/2016/03/15/kurzgesagt-behind-the-scenes/
- sonilo 嗖声指南：https://sonilo.com/ai-music/whoosh-sound-effect-guide
- PaperTok：https://arxiv.org/pdf/2601.18218
- @rameerez 的经验：https://x.com/rameerez/status/2015859121661059569
