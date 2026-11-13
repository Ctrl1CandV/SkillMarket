# 技能优化计划与交接

更新：2026-11-13（第三阶段收尾）。写这份文档的原因：优化工作原先在一台 WSL 开发机的受限沙箱里进行，那里看不到显卡、装不了系统包；用户决定迁到本机 Windows 继续。之前会话里记住的分工、规矩和证据不随仓库走，这里一次写全。接手时先读本文，再读对应技能的 `TODO.md`。

## 一、任务是什么

用户让 AI 以“优化者”的身份工作：判断每个技能的重要程度，审查问题，给出优化方案和顺序。效果明确的直接改，拿不准的多轮讨论。

用户对各技能的定位：

| 类别 | 技能 | 用户的说明 |
|---|---|---|
| 不用管 | write-with-judgment、agent-parliament | 前者开发未通过验证，后者基本弃用 |
| 低频、临时写成、未验证 | readable-reply、git-governance、skill-search、de-ai-flavor | readable-reply 要让任何 Agent 的回复简洁可读（GPT 最啰嗦）；git-governance 要让 AI 在提交前整理文件、分清入库与保留、写好提交说明；skill-search 要能找到可直接用或可借鉴的技能 |
| 中频、已验证、补模型缺的能力 | docvision、presentation-craft、imagecraft、video-craft | OCR、PPT、生图、视频 |
| 高频、多轮打磨 | product-design + frontend-craft、grad-companion | 前端页面效果用户仍不满意；grad-companion 用户满意。2026-11-13 用户决定 grad-companion 这轮不做：论文改由 Claude 直接写，这个技能暂时用不到 |

用户最在意的是“展示”这一层：前端、PPT、视频、文字。算法和后端的产出差别不大，差距在展示。

## 二、顺序与规矩

**顺序（用户定的）**：先小而简单的技能，再四个补能力的技能，最难的 frontend-craft、product-design、grad-companion 放最后。

**暂缓**：展示类技能的审美共性（用户认为是终极问题，现在可能做不到）、write-with-judgment、de-ai-flavor 大版本。

**规矩**：

- 每个技能做完一轮优化就提交。dev 提交全部内容；main 只带运行文件和根 README，不带 `maintenance/`。按技能分开提交。
- 提交标题沿用仓库历史的写法：`MM.DD 对象 版本：具体变化`，标题和正文之间空一行。
- 推送要用户开口才做。
- 通过 pi 调用模型时：DeepSeek 只用 `deepseek-flash`，**不用 `deepseek-v4-pro`**；GPT 常用 `gpt-6.1-sol`，非常困难的任务才用 `gpt-6-astra`。任务难不是自行升级模型的理由。
- 用户不擅长描述审美或提供参考站点，擅长的是“看到两个东西后选哪个好”。需要调研和判断的事由 AI 自己做，机械性的工作可以写好交接文档交给 GPT 或 DeepSeek。
- 前端的实践样例不要用“拾声管理后台”，由 AI 另选一个可操作性强的页面。

## 三、用的方法

用户认同的出发点：技能是多轮实践之后固化下来的经验；展示类技能的问题多半不是规则不够，而是没有可以直接起步的具体零件。

每个技能走同一套流程：

1. 让 pi 带着技能做一个真实的小任务。技能按名称和描述自然触发，不强制加载。
2. 看它在哪一步走偏，并亲眼看产物。
3. 只针对观察到的问题改。优先改脚本和工具的输出（模型在需要的时刻一定会看到），其次才是往技能正文里加一句话。
4. 重跑走偏的部分，记录结果和没验证的部分，然后提交。

实测任务和运行脚本都在各技能的维护目录里，输出写到仓库之外：

| 技能 | 任务与脚本 | 记录 |
|---|---|---|
| readable-reply | `maintenance/readable-reply/evals/`（6 个问题 × 4 组） | `results-2026-11-11.md` |
| presentation-craft | `maintenance/presentation-craft/evals/progress-task/` | `evals/pi-run-2026-11-12/README.md` |
| imagecraft | `maintenance/imagecraft/pi-tasks/` | `eval-pi-routing-2026-11-12.md`、`eval-local-2026-11-12.md`、`eval-cloud-2026-11-12.md` |
| video-craft | `maintenance/video-craft/evals/2026-11-12-caffeine/` | 同目录 `README.md` |
| docvision | `maintenance/docvision/evals/2026-11-12-real-run/` | 同目录 `README.md` |

运行脚本是 bash 写的，Windows 上用 Git Bash。跑 pi 时不要加 `--no-tools`，否则模型读不到技能正文。

实测中反复出现、值得留意的三件事：

- **模型会为补环境花掉大量步骤。** 一次 PPT 任务里，177 次工具调用有 79 次用在拼装 LibreOffice 上。
- **模型会把指标正好调到警告线。** 字号警告设在 16 pt，复测时每页的中位字号都是 16.0 pt。
- **被测模型会改任务目录之外的东西**，例如往用户目录装字体和全局 Python 包。跑完要检查并如实告诉用户。

## 四、各技能现状

| 技能 | 版本 | 做了什么 | 没验证的 |
|---|---|---|---|
| readable-reply | 2.0.0 | 重写为“先给答案”的简洁规则，附可粘进全局指令的短版 | 只测了一个模型、每题一次；用户还没盲评原始回复；按需加载的技能在普通问答里 6 次都没被触发，实际起作用的是全局指令短版 |
| git-governance | 1.1.0 | 提交前的文件去向清单、提交标题怎么定 | 没做模型实测；用户是否有固定的“私人文件夹”约定未知 |
| skill-search | 0.3.0 | 区分“直接使用”和“借鉴参考” | 借鉴用途没在真实检索里试过 |
| presentation-craft | 0.4.0 | 真实渲染补验（PowerPoint）；审查报中文未标语言、标题不到正文 2 倍；渲染脚本报断行；样张标题 36 pt 并标中文 | 新字号建议没完整跑过；论文组会场景没测；动画放映没测；非文字问题（边框、箭头）仍只靠看图 |
| imagecraft | 0.3.3 | 本机 FLUX 和 GPT 订阅都真正出过图；`generate` 在显卡被占用时拒绝提交；订阅脚本报出账户套餐、说明客户端留存，任务目录可写相对路径 | 每个任务只跑 1 次；拦不住用户推理服务两次请求之间的空档；“连线两端分别看”在自出自验时是否有效没验证；Z-Image、交互式会话里的“先问”没测 |
| docvision | 0.5.2 | 真实论文筛读和真实扫描页 OCR 实测通过；fast 档报告页面上看不见的文字；中文 Windows 输出不再崩溃；doctor 显示引擎崩溃原因 | 每个条件只跑 1 次；中文扫描件、PaddleOCR 本地路线没测；MinerU 环境缺依赖靠用户目录补，待用户决定是否装进环境；用户说明用途是给 AI 做高精度、大批量识别，批量任务还没测 |
| frontend-craft | 0.6.1 | 先由优化者亲手做九类页面积累判断，再提炼：类别对照表放进主流程第 1 步；工作台、数据看板、设置、图鉴检索四个可直接改的起步样例；`scripts/pagecheck.mjs` 三种宽度截图并量出问题（含没算出来的 NaN） | 每种配置只跑 1 次；用户盲看分不出新旧好坏，能拿得出的证据都是量得出、查得到的；阅读、活动、艺术展示、3D、手机表单没有样例；样例可能让页面越来越像样例本身；把检查写成必须处理后出现过“为过检查而补”的写法 |
| product-design | 0.3.0 | 第 3 步加四个检验取舍的问题（信息在哪个时刻有用、数据多了少了排法还成不成立、先压缩再删、看板还是报告） | 没有单独实测，只随 frontend-craft 的任务一起跑过 |
| video-craft | 0.3.0 | Windows 回归通过；联系表标出冻住的画面；starter 加缓慢推近；修 audiocheck 的 Windows 路径 | 每个版本只跑 1 次；GPT 两条成片用户盲看认为差别不明显，揭晓后觉得新版前半段发灰、略差；DeepSeek 一对用户盲选新版（曲线图更好），旧版两次都被接口断连打断过；真人配音没测 |

## 五、迁到 Windows 后先做什么

原环境缺的东西在本机大多现成，所以先把欠下的验证补上，再继续往后做。建议顺序：

1. ~~presentation-craft 补看真实画面~~（2026-11-12 完成，0.4.0，见 `maintenance/presentation-craft/evals/pi-run-2026-11-12/README.md`）。
2. ~~video-craft~~（2026-11-12 完成一轮，0.3.0，见 `maintenance/video-craft/evals/2026-11-12-caffeine/README.md`）。
3. ~~docvision~~（2026-11-12 完成一轮，0.5.2，见 `maintenance/docvision/evals/2026-11-12-real-run/README.md`）。
4. ~~imagecraft 本机出图~~（2026-11-12 完成一轮，0.3.2，见 `maintenance/imagecraft/eval-local-2026-11-12.md`）。GPT 订阅出图 2026-11-12 补测（0.3.3，见 `maintenance/imagecraft/eval-cloud-2026-11-12.md`）。
5. ~~四个技能都补完后，进入第三阶段。~~ 2026-11-13 第三阶段收尾：frontend-craft 0.6.1、product-design 0.3.0 完成一轮；grad-companion 按用户决定不做；frontend-craft 第二批样例暂缓。

各技能的自测（都不调用模型）：

```text
python maintenance/presentation-craft/evals/check.py                      # 17 项
python -B -m unittest discover -s maintenance/imagecraft/tests            # 99 项
python -B -m unittest discover -s maintenance/docvision/evals -p "test_*.py"   # 276 项，Windows 上跳过 1 项
python maintenance/docvision/evals/check.py                                # 5 项
node maintenance/frontend-craft/evals/check.mjs                            # 126 项，只做静态和模拟 DOM
node maintenance/frontend-craft/evals/test_pagecheck.mjs                   # 85 项，要先设 FC_NODE_MODULES、FC_CHROME
```

需要的 Python 包：pillow、numpy、opencv-python-headless、pymupdf、python-pptx、pypdf、pypdfium2。原环境装在仓库根的 `.venv`（已被忽略）。

**Windows 本机（2026-11-12 摸底，用户同意后安装）：**

- `python` 命令指向微软商店占位程序，不能用。上面的包和 pywin32（PowerPoint COM 渲染要用）装在 conda 环境 `skillmarket`（`C:\Users\11487\.conda\envs\skillmarket\python.exe`）。用户级 site-packages 里有别的包（easyocr、opencv 等）会混进同版本的 Python，跑自测和实测时设 `PYTHONNOUSERSITE=1`。conda 的默认频道配置里有失效的镜像 `pkgs/pro`，建环境时用 `--override-channels -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main`。
- pi 实测：`PY_ENV_DIR=/c/Users/11487/.conda/envs/skillmarket bash maintenance/presentation-craft/evals/progress-task/run_pi.sh <输出目录>`，脚本会把该环境放到 PATH 最前并屏蔽用户级 site-packages。
- video-craft：playwright-core 装在 `%LOCALAPPDATA%\video-craft-kit`，运行前设 `VC_NODE_MODULES` 指向它、`VC_CHROME` 指向本机 Chrome。全局 npm 缓存配在 `D:\Program Files\nodejs\node_cache`，普通权限写不进去，安装时加 `--cache <可写目录>`。
- 已有：Node 24.19、pi 1.4.0、ffmpeg 8.1.1、Chrome 157、PowerPoint 16.0（无 LibreOffice）、WPS 12.1、RTX 4070 Ti SUPER 16 GB、微软雅黑等中文字体与 Noto Sans SC、ComfyUI 0.31（`D:\ComfyUI-H3`）、MinerU 和 PaddleOCR 各自的 conda 环境。
- 四组自测在 Windows 上都通过；docvision 跳过 1 项（这台机器的用户不能建符号链接）。

## 六、第三阶段（前端）已经知道的

- **历史评测的结论是“没有明显差距”。** frontend-craft 0.5.0 与 product-design 0.2.0 在 10 月 26 日的独立终审结论是证据不足：阅读、密集操作、公共展示三个场景新旧版整体相当。用户的反馈也是差距不明显，略偏向旧版的标题层级。所以再补一轮原则性文字，收益有限。材料在 `maintenance/frontend-craft/upgrades/2026-10-26/`。
- **外部参考多数没看过图。** frontend-craft 的 14 条外部参考里只有 6 条实际看过。
- **video-craft 的经验。** 0.1.x 失败是因为只有规则、没有零件，检查只验证文档不看像素。0.2.0 改成先做出好视频，再提炼出工具包和三个完整示例，才有效。见 `maintenance/video-craft/README.md`。
- **用户喜欢什么、不喜欢什么。**
  - 喜欢：拾声的声音艺术专题页（深青、暖纸色、赤陶色，原创的 SVG 主视觉，标题尺度大），以及“轨迹、频场、截面、隅物”四个展示页。
  - 不喜欢：拾声管理后台（“难看”，重做后“更差”）、不同页面配色雷同、标题层级弱。
- **用户确认过的假设。** 被喜欢的页面靠的是原创主视觉和大的尺度对比；工具类和后台类页面是弱项。
- **打算怎么做。** 做成零件（模板、设计参数），而不是继续写规则；评判信号由 AI 自己建立，方式是做出只差一个因素的成对页面，让用户二选一。
- **用户 2026-11-12 定的顺序。** 先由优化者亲手做一组不同类型的页面、积累自己的判断和经验，再提炼进技能，最后才用弱模型验证；页面本身不是目的。8 类页面的清单、进度和手记在 `maintenance/frontend-craft/practice/2026-11/JOURNAL.md`。2026-11-13 八页都已做完（面包房工作台和预订页、长文阅读、实验对比看板、书店活动页、通知设置、树叶图鉴、作品《昼长》），手记末尾有“八页做完之后”的总结；技能本身还没有改，下一步是把手记提炼进技能，开始前先把方案讲给用户。用户强调：他的选择里要分清普遍的道理和个人口味，口味不写成规则。模型：以 `deepseek-flash` 为主，摸底和最终复测各加一次 `gpt-6.1-sol`。
- **2026-11-13 第一批提炼已做完。** frontend-craft 0.6.0、product-design 0.3.0：四个起步样例（工作台、看板、设置、图鉴检索）、场景文档开头的类别对照表、`scripts/pagecheck.mjs` 检查脚本、产品设计的四个取舍问题。用 deepseek-flash 各跑一次：新题目“东门驿站”上看板一类差别明显（旧版替读者下结论，新版只摆数据），工作台差别不大；面包房任务（拿掉了工作台样例，因为它就是面包房的页面）好坏参半，顾客预订页在手机上第一屏变成了说明。记录在 `maintenance/frontend-craft/reports/frontend-craft-0.6.0-batch1-2026-11-13.md`。同一天用 gpt-6.1-sol 在驿站题上新旧各跑一次：它没有读场景文档，也没有打开样例，检查脚本报的问题大部分没改，新旧成品很接近——新加的东西对只读必要内容的模型基本没起作用，于是改成 0.6.1：对照表放进 SKILL.md 第 1 步，看样例、处理检查结果写成明确步骤，检查脚本加了“算错的值（NaN、undefined）”一项。复测：gpt-6.1-sol 这次读了样例、跑了 3 次检查，看板不再给建议；deepseek 第一次没有触发技能（作废），第二次正常，但看板有一列 NaN 没发现，这也是检查脚本加那一项的起因。用户盲看后表示都不错，分不出好坏；对应关系和结论已补进记录。收尾时又用 deepseek 跑了一次面包房（0.6.1）：顾客预订页这次认作表单，手机第一屏就能选面包（第一款离顶部 398 px，0.6.0 时 944 px）。用户决定就此收尾：第二批样例（阅读、活动展示、艺术展示、局部 3D、手机表单）暂缓，等以后有真实页面出问题时再做。
- **（已回答）** 第三阶段的摸底用哪个模型跑：用户定的是 `deepseek-flash` 为主，`gpt-6.1-sol` 做对照；GPT 每次开跑前先问，因为用订阅额度。

三个展示技能（frontend-craft、presentation-craft、video-craft）现在互不引用，各自重复写了参考选用、配色字体层级和看图审查。presentation-craft 两次实测的成品也有“标题与正文尺度对比偏弱”的观感，和前端的问题相似，可以一并留意。

## 七、零散的未决事项

- readable-reply：用户盲评 `maintenance/readable-reply/evals/raw/` 里的原始回复；可选再用 GPT 跑一遍同样的测试。
- git-governance：用户是否有固定的“私人文件夹”约定。
- presentation-craft：近似预览不收（已定）；字号阈值留 16 pt，改为要求标题约为正文 2 倍（用户盲选两组对照，已定）。
- 远端的 `product` 分支是很早以前的旧分支，这轮没有动过。
- docvision：MinerU 环境缺的依赖是否装进环境（现在靠用户目录补），待用户决定；面向“给 AI 做大批量识别”的批量任务还没测。
- imagecraft：用户提过论文配图要按论文格式出，这次测试的提示词没写这个要求，可以单独测一次。
- frontend-craft：第二批样例暂缓；样例配色可能被原样搬到别的题材；检查写成必须处理后出现过用 `!important` 补字号的写法。
- 本地 dev、main 都没有推送，推送要用户开口。

## 八、没有随仓库带走的东西

- 两次 PPT 实测和三次生图实测的完整日志（每次几十到一百 MB）。成品和模型的交付说明已收进各自的维护目录；工具调用清单含原环境的内部路径和代理信息，没有入库，记录里的统计数字来自它。
- 原环境里临时装的工具（ffmpeg 静态包、playwright-core）和虚拟环境，到新环境按需重装。
- 原环境的资源申请文档，迁移后不再适用。

## 九、这轮犯过的错

写下来是为了不再犯：

- 没查清就说“这台机器没有显卡”。实际是沙箱挡住了显卡设备。imagecraft 和 docvision 的检测代码有同样的毛病，已修。
- 没问用户就用更贵的模型起了一次实测，被叫停。
- 提交说明的标题和正文之间漏了空行，重写过一次提交。
- 第三阶段一开始就用弱模型跑摸底，用户要的是先亲手做页面、有了自己的判断再改技能，被叫停。
- 把用户个人口味的选择写成“我押错了”并想据此改规则；用户提醒要分清普遍的道理和个人口味。
- 没量过的数字写进手记两次（手机筛选区高度、夜晚所占比例），之后各用一次提交更正。
- 统计检查脚本的运行次数时把“读脚本文件”也算了进去，记录写多了，另提交更正。
- 差点用面包房页面做成的样例去测面包房任务，等于让模型抄答案；开跑前发现，改用拿掉这个样例的版本和新题目。
