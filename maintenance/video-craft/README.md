# video-craft 维护记录

## 0.2.0（2026-11-10 dev，2026-11-11 发布到 main）：先做出好视频，再提炼

0.1.x 的评测和用户反馈说明：只有规则、没有零件，模型每次都要从零手写一千多行渲染代码；检查只验证文档、不看像素，效果并不好（见 `evals/2026-11-09-pi-deepseek-summary.md` 末尾的复盘）。于是改了开发顺序：先在 `lab/` 里自己做视频，直到用户认可（实验 2“天空为什么是蓝的”，用户结论为“可以直接用”，仍有优化空间）；再做一条不同类型的（实验 3「两清」宣传片），最后把做法和工具提炼成 0.2.0。过程见 `lab/log.md`。

- 结构：
  - `SKILL.md`：流程与交付核对。
  - `references/`：
    - pictures：核心画面与结构；
    - look：画面质感；
    - motion：运动、镜头与节拍；
    - sound：声音；
    - review：审查与问题清单；
    - kit：工具包与环境。
  - `kit/`：实验中写的工具，去掉了本机路径，用 `env.mjs` 统一查找 playwright-core、Chromium 和 ffmpeg。
  - `examples/`：starter、sky、promo 三个完整工程。
- 新增：
  - `doctor.mjs`：环境探测。
  - `vo.mjs`：配音计时。
  - `sound.js` 的配音总线，以及 `voice()`、`duck()`。
  - `audio.mjs` / `mixcheck.mjs` 的 `--vo` 参数。
  - `render.mjs` 支持输出 `.mp4`：H.264，合入音轨时转 AAC。
  - `kit.js` 的 `kf` 关键帧轨道和 `FONT_STACK`；`loadFonts` 找不到字体时只警告。
- 移除：0.1.1 的 `scripts/`（storyboard.py、video_qa.py、mix_audio.py、doctor.py）、`assets/` 和旧版 references，连同测试一起存档到 `archive-0.1.1/`。Python 脚本校验的是分镜文档而不是画面，端到端测试也一直没在本机跑通。

### 验证（2026-11-10）

- 从干净副本运行：
  - `doctor.mjs`：报告 Chromium 140、SwiftShader WebGL2，WebCodecs 支持 VP9/AV1/Opus，ffmpeg 只有 VP9；
  - 三个示例的 `audio.mjs` 都能出音轨（starter −16.0、sky −16.1、promo −17.0 LUFS，峰值都是 −1.5 dB）；
  - sky 能出联系表，promo 能出一段带声音的视频；
  - sky 和 promo 的 `textcheck` 都通过；
  - 所有 `.mjs` 通过 `node --check`。
- 配音链路用合成的测试音验证（本机没有 TTS）。4 段测试音由 `vo.mjs` 量出时长并生成时间线；`--vo` 渲染出的人声分轨约 −15 LUFS；`duck` 在说话区间把音乐压低 9 dB，`mixcheck` 的曲线可以看到。
- MP4（2026-11-10，用户安装了系统 ffmpeg 4.4.2）：
  - `doctor.mjs` 报告 h264/aac 可用；
  - promo 直接输出 `.mp4`：H.264 High 1080p30 + AAC 48 kHz，28.000 s，完整解码无报错，−17.0 LUFS；
  - 发现合音轨后索引放到了文件末尾，于是在合入 MP4 音轨的命令里加上 `-movflags +faststart`，修正后 moov 紧跟在 ftyp 之后；
  - 按精确帧号对比解码帧与原始渲染帧，PSNR 39–41 dB，平均颜色差不超过 1/255；
  - kit.md 里的 WebM → MP4 转换命令也验证通过。
- 未验证：
  - 真实人声配音；
  - 在 Remotion/HyperFrames 项目中配合使用。
- 运行示例需要字体：开源的思源黑体/宋体、Ubuntu，放在示例目录的 `fonts/` 下，仓库不附带。

### 评测（2026-11-11）

- 题目“GPS 是怎么知道你在哪的”，pi + `openai-codex/gpt-6.1-sol`，有技能和无技能各跑一次。详见 `evals/2026-11-11-pi-gpt-summary.md`。
  - 用户盲看：有技能的那条“好很多”，无技能的那条“更像一个 PPT……杂乱无章”。
  - 我的审查：两条都是“小改后能发布”，有技能的讲得更清楚，声音跟着画面走；主要毛病是换场的交叉淡化重影。
- 原计划用 DeepSeek，但 `api.deepseek.com` 连不上（useProblem ISS-002）。gpt-6-luna 跑的一轮两组都只用了 3 分钟，没看过画面，用户判断模型不适合，那一轮删掉重跑。
- 发布前据此补了 review.md 和 motion.md：换场默认先退后进；切点帧条要找重影；文字和图从同一个时刻表换场。

### 回归（2026-11-12，Windows 本机）

- 环境：Node 24.19、playwright-core 1.65（装在 `%LOCALAPPDATA%\video-craft-kit`，`VC_NODE_MODULES` 指过去）、系统 Chrome 157（`VC_CHROME`）、ffmpeg 8.1.1。`doctor.mjs`：WebGL2 走 RTX 4070 Ti SUPER（ANGLE/D3D11），WebCodecs 与 ffmpeg 都有 VP9/H.264/AAC/Opus，浏览器里没有语音合成。
- 三个示例从仓库目录直接跑，各 1 次：
  - 联系表（每 2 秒一帧）都能出，sky 30 帧约 3 秒；看过 sky 和 promo 的联系表，画面与 0.2.0 发布时一致；
  - 音轨：starter −16.0、sky −16.1、promo −17.0 LUFS，峰值都是 −1.5 dB，与 11-10 的记录相同；starter 没有配音文件，按预期提示缺少 4 段并跳过；
  - sky、promo 的 `textcheck` 通过；
  - promo 直接出 MP4：H.264 1920×1080 30 fps，28.000 s，合入音轨的 `promo-av.mp4` 也生成了；840 帧渲染约 35 秒（11-10 在软件 GL 上约 1.5 分钟）。
- 示例的开源字体（Noto Sans/Serif SC、Ubuntu）仓库不附带，这次全部退回系统字体（微软雅黑等），页面只警告不报错。
- 真实小任务见下一节。

## 0.3.0（2026-11-12 dev）：联系表标出冻住的画面，修 Windows 路径

依据 [竖屏咖啡因短片实测](evals/2026-11-12-caffeine/README.md)（pi + gpt-6.1-sol，用户指定）：流程走得完整、数字全对，但每段动画做完就停住，32 秒里约 13 秒画面没有任何变化；模型看过联系表却没处理。

- `render.mjs sheet` 标出和上一格几乎没变的格子，连续静止 2 秒以上时在输出里列出时段（`--still`）。
- starter 示例加整片缓慢推近，不再示范“读字时画面冻住”。
- `review.md`、SKILL.md 交付核对、`kit.md` 各补一处。
- `audiocheck.mjs` 在 Windows 上找不到 score.html（`/` 截路径），改用 `dirname`；`montage.mjs` 图注用 `basename`。

### 下一步

- 真人配音（下一个版本）：edge-tts 用 `zh-CN-YunxiNeural`，但 `speech.platform.bing.com` 目前连不上（ISS-002）；离线备选 Kokoro v1.1-zh。拿到真实配音后验证 `vo.mjs` → `--vo` → `duck` 全链路。
- 用更多题目和模型复测，尤其是竖屏、数据故事；看补上的换场规则是否生效。


## 定位与取舍（2026-11-09，0.1.0 开发中）

- **做成技能，不做插件。** 本仓库的技能约定不依赖具体宿主；插件的命令和钩子只在 Claude Code 中生效，换到 GPT、DeepSeek 等宿主就失效。用户的出发点正是“GPT 和 DeepSeek 做的视频效果不好”，所以方法写成通用文字，确定性的部分写成只依赖 Python 标准库与 ffmpeg 的脚本。
- **不重复引擎技能。** Remotion 官方有 `remotion-dev/skills`（约 12 个子技能，管 API 正确性）；HeyGen 的 HyperFrames 自带约 20 个技能（含 `motion-doctrine`、`cut-the-curve` 等运动规范）。它们都不管或很少管：一句话要点与结构、口播写法、分镜作为时间来源、样帧、配音驱动时间线、字幕规范、响度、看成片。video-craft 补这些，并在 engines.md 指向官方技能。
- **抓最大的杠杆。** AI 写视频代码的常见问题（据调研与常识）：幻灯片式镜头、居中堆字、线性/统一淡入、镜头之间无关联、转场杂乱、时长手写导致音画错位、中文豆腐块、从不看成片。对应做法：分镜里强制写作用/主体/构图/衔接；样帧先行；timeline.json 作为唯一时间来源；联系表 + 切点帧条 + 自动检测。
- **正面示范优先。** 遵守仓库的技能写法：每节先写“好的样子”，用具体数值和示例（content.md 的 HTTPS 两种写法、motion.md 的 8 秒镜头编排、assets 里的完整分镜与令牌），少用禁止清单。

## 调研来源

| 来源 | 取用的内容 |
|---|---|
| [remotion-dev/skills](https://github.com/remotion-dev/skills)（remotion-markup、video-layout、timing、multi-scene-video） | 动画只由 `useCurrentFrame` 驱动、CSS 动画不可用、`Easing.bezier(0.16,1,0.3,1)`、`spring({damping:200})`、1080 宽时标题 84 px / 辅助文字 44 px、安全边距 80/100 px |
| [HyperFrames](https://github.com/heygen-com/hyperframes)：`motion-doctrine`、`cut-the-curve`、`seam-craft` | 切点在运动中、方向一致、载体跨切点、Z 轴缩放符号一致、单个入场 ≤0.8 s、出场约为入场 75%、总错峰 ≤0.5 s、转场 2–3 种、高潮前 0.3–0.75 s 静止、不透明舞台防白闪、文字模糊上限 10 px |
| [HeyGen 研究文章 html-to-video](https://www.heygen.com/research/html-to-video)、HyperFrames README | “seek, don't play”：每帧只由时间决定；Node 22+、FFmpeg、Apache-2.0 |
| [Remotion 许可](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md) | 个人、非营利、≤3 名员工的公司免费，其余需公司许可 |
| [Code2Video（showlab，ICML 2026）](https://github.com/showlab/Code2Video) | Manim 生成教育视频：6×6 网格锚点放置 + 视觉语言模型看渲染结果修布局，相对直接生成代码提升约 40%——支持“网格锚点 + 看帧修订” |
| [ItsssssJack/claude-video-2](https://github.com/ItsssssJack/claude-video-2) | 先选一种风格贯穿；brief 写成数字；先出 3 张静帧再渲染；“Check frames, not code” |
| Guo、Kim、Rubin 2014（L@S，edX 视频参与度） | 参与度 6 分钟后明显下降；先规划再拍；非正式的讲述更有效 |
| Mayer 2017（JCAL）与独立元分析（Richter 2016、Schroeder & Cenkci、2025 年 ERR 元分析） | 时间邻近、信号、去冗余、空间邻近、分段的默认做法；独立研究效应偏小，写成默认而非铁律 |
| [Netflix 简体中文字幕规范](https://studiopartner.netflix.net/studio/chinese-simplified-timed-text-style-guide) | 每行 16 字（可到 18）、成人 9 字/秒、0.83–7 秒 |
| 中文配音语速（配音行业与播音资料汇总） | 专题/解说约 200–240 字/分钟，新闻约 250–300 |
| 竖屏安全区第三方汇总（RightBlogger、KreateFlo、Uplads 等，平台无官方值） | 上 130–220、下 420–480、右 140–180、左约 60 px（1080×1920） |
| 响度第三方汇总 | 网络平台约 −14 LUFS、真峰值 −1 dBTP；EBU R128 −23 LUFS |
| Palmer & Schloss 2010；仓库 frontend-craft 的配色结论 | 先统一色调再谈色相；棕与暗黄不做大面积主色 |

## 0.1.0 内容

- `SKILL.md`：接收任务 → 内容 → 分镜 → 风格与样帧 → 声音先行 → 运动 → 渲染审查 → 混音交付。
- `references/`：content、storyboard、visual（7 个风格方向与令牌）、motion（跨引擎缓动对照表）、audio、engines、review。
- `assets/`：竖屏复利解说的完整分镜示例、对应风格令牌。示例主题与将来的评测题目不能重合。
- `scripts/`：
  - `doctor.py` 只读探测；
  - `storyboard.py` check / timeline / srt；
  - `video_qa.py` probe / detect（黑场、闪帧、静止、静音、响度、切点比对）/ sheet / strips / frames / all；
  - `mix_audio.py` 配音分段统一响度、音乐循环与侧链让位、音效按峰值、两遍 loudnorm、按需重编码。

## 验证状态

- `python -B -m unittest discover -s maintenance/video-craft/tests`：27 个纯函数测试通过；6 个端到端测试需要 ffmpeg/ffprobe，本机暂缺（2026-11-09 开发代理 127.0.0.1:17892 拒绝连接，无法安装）。
- 端到端测试会合成一段 7 秒视频（含 1 帧白闪、2.5 秒静止、静音段），检查 video_qa 能否报出，并用合成的配音、音乐、音效跑 mix_audio，核对 −14 LUFS、48 kHz、faststart。
- 自测样片（2026-11-09）：`~/.local/share/vc-eval/demo-compound/`，按技能流程做“每天进步 1%”竖屏解说。没有网络，引擎用无框架的可定位 HTML（`src/scene.js` + `render.mjs`，现有 playwright-core 与 Chromium、思源黑体）。配音缺失，时间线按语速估算。
  - 分镜检查无问题；时间线 38.05 s / 1142 帧；字幕 13 条（竖屏默认每行 14 字）。
  - 样帧第一轮实际看图发现：第 4 镜之后图表残留（父层 `visibility:hidden` 被子元素 `visible` 覆盖，读代码看不出）；开场指数越出右侧安全区；大数字被网格线穿过；空格丢失；说明文字位置不统一。均已修正。由此在 review.md 加了“上一镜元素残留”一条。
  - 整片第一轮（1142 帧）后用浏览器拼的切点帧条、入场帧条复查：6 个切点中 4 个在运动中衔接、方向一致；发现第一帧全空、第 2 镜开头 0.5 s 近乎空白、第 5 镜未点亮方格过暗导致切点前后近乎空画面、第 6 镜首句偏左。均已修正，并把“第一帧要有主体”“镜头开头不留空白”写进 content.md 与 review.md。
  - 待 ffmpeg：编码 MP4、跑 video_qa、配音（网络恢复后可用 TTS）与混音。

## 已做的评测

- 2026-11-09 pi + deepseek-flash，无技能 vs 0.1.0 vs 0.1.1，两题：见 `evals/2026-11-09-pi-deepseek-summary.md`。据此发布 0.1.1（看图省上下文、先交付、限制修订轮数）。
- 2026-11-11 pi + gpt-6.1-sol，无技能 vs 0.2.0，一题（GPS）：见 `evals/2026-11-11-pi-gpt-summary.md`。用户盲看认为有技能的好很多，据此发布 0.2.0 到 main。

## 评测计划（原始设想）

1. 题目 3 个，均不与示例重合：竖屏科普解说（约 45 秒，配音字幕）、横屏产品功能演示（约 30 秒）、数学/算法讲解（Manim，约 60 秒）。
2. 条件：同一模型无技能 vs 有技能；可加用户自己在 GPT/DeepSeek 宿主上用技能文本跑一题。
3. 产物：成片 + video_qa 联系表；用户盲评（构图与主次、运动与衔接、内容清晰、整体观感），同时记录 token 与修订轮数。
4. 评测工作区放 `~/.local/share/vc-eval`（不放 /tmp）。

## 待办

- [ ] ffmpeg 可用后跑通端到端测试并修复。
- [ ] 用技能实际制作示例视频（自测），检查文档里的命令与 Remotion/HyperFrames 当前版本是否一致。
- [x] 盲评后按结果修订，再整合到 main（只带 `video-craft/` 与 README 索引行）。2026-11-11 完成。
