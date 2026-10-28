# docvision 混合精读优化：当前计划与验证记录

## 目标与决定

用户已授权在当前首版基础上实施优化，复用或替换技能参考、底层模型，以日常 PNG/PDF 与论文公式、表格、图表、架构图的准确率和速度为准。用户明确提出本地批量与免费额度 API 精读相结合，并表示现有场景要求已经完整，本轮直接实施，不重复走设计批准。

在现有 dev 工作区局部修改 docvision 与对应 maintenance 资料；保留已有未跟踪报告，不提交或推送。不修改其他技能。沿用 Python/现有多 provider 架构，不建设新平台。

当前有效方案 v1：

1. 本地批量继续使用 MinerU，增加 economy→basic 档位，让低开销 OCR 与纯文字 fast 有明确区别；默认 standard 保持兼容。引擎发现短路，单并发为默认建议。
2. 新增 triage：按已识别块类型、公式/合并表格/图块及结构问题生成复核候选。只标复核优先级，不冒充准确率预测。
3. 新增 refine：针对既有输出中的单页、块或归一化 bbox，以高分辨率原图制作精读输入。优先裁块，必要时选单页，不默认上传整篇。
4. refine 保存独立版本、原页/bbox、输入哈希、provider/task/model、状态和原始结果；本地结果保留。相同请求可缓存，改变任务/参数不误复用；不自动重试上传或切换多个云端。
5. 任务区分 transcription/formula/table/chart/figure；公式和表格用专业 OCR，图表与架构关系使用支持视觉解释的模型或当前宿主实际看图。没有 API key 时生成可直接查看的图片与上下文包，状态明确为需要视觉复核。
6. 调研证实官方 PaddleOCR 托管免费额度接口后接入 paddleocr-cloud；MinerU Standard 继续可选，Gemini 用于图形解释。自动路线仅使用已配置、适合任务的服务，精读仍要求显式 --allow-remote。免费额度、频限和账号资格以服务方为准。
7. 修复完整页集合 QA、空正文判定、resume 请求匹配、Paddle 图引用、DPI 缓存和 core 环境执行；改进 Paddle 依赖检查，修复本机必要依赖后真实试跑。
8. 更新 SKILL 与相关路由/阅读/评测文档，使 AI 知道何时本地、何时精读、如何实际查看原图和使用复核结果。

## 验收

- 保留已有五项适配器测试；为缺页、空正文、缓存参数、图资源、DPI 和精读边界补真实回归断言。
- 不同任务或区域的精读缓存不混用，失败不伪装完成；无授权时不上传，单次 refine 只处理一个指定区域/页。
- 免费 API 适配按官方契约测试，不把 mock 视为实际识别。缺账号时如实记录，提供明确配置入口，不索要用户在聊天中发送密钥。
- 用公开 Attention 论文的公式、表格、架构图试跑本地与精读包；检查原图、页码、关键公式和合并关系。
- 修复后运行最终相关测试、CLI smoke 与一次实际本地推理；由未参与实现的代理独立审查关键边界。

## 分工与修改范围

- 完整性与缓存：verify.py、output.py 的空正文、read.py 的 DPI、独立 cache 模块与对应测试；CLI 集成由主代理完成。
- 本地环境与速度：config.py、detect.py、setup_cmd.py、doctor.py、util.py、docvision.py、Paddle/MinerU 本地 provider 与对应测试。不得改主 CLI 或精读模块。
- 主代理：精读与 triage 模块、CLI 集成、文档和实际样本验证。
- 调研代理：官方免费 API 契约与技能参考，随后可独立实现新云端 provider。

## 方案质疑与处置

- OCR 的结构 pass 不能证明公式正确：QA 修完整性；关键区域仍以原图和第二结果核对。
- 云端不一定优于本地：保留两份输出和来源，不按云端身份自动覆盖正文；用同页样本决定是否采用。
- 图形解释与 OCR 不同：figure/chart 任务输出模块、箭头、轴/图例与不确定项，宿主须实际查看图块。
- 免费额度可能改变：记录核验日期，不承诺永久免费，不自动切换付费 provider。
- 8 GB 未实测：不宣称真机适配完成；提供 economy、单并发和单页/裁块路线。

## 进展与证据

此前审查记录见 review-2026-10-28.md。当前实现版本为 0.2.0-rc.1；以下为实际实施结果。

### 已落地

- 新增 economy、triage、refine 与宿主视觉精读包。按指定页/块/bbox处理，局部仅附选中/重叠块及相邻块，dry-run/record显示上下文块ID与字数。
- 专业OCR与图形语义任务分开；自动精读优先已配置Paddle官方免费额度API、MinerU Standard、Gemini，图形解释用Gemini/本地视觉或当前宿主看图；不会自动选择其他付费provider。
- 新增Paddle官方异步HTTP provider：单次提交、受限轮询、原页映射、JSONL、图资源落盘；未知/超过页数限制明确拒绝，未真实调用服务。
- 精读结果独立保留原稿；缓存纳入原文件、区域、任务、DPI、提示词、上下文、端点/模型、运行时版本/元数据指纹。签名只存敏感配置哈希。中断不重传，并发相同请求原子占用目录防止重复上传；force保留旧尝试。
- 修复源页集合/空正文QA、请求参数resume、DPI缓存、Paddle图片/图表文字/脚注遗漏、core环境执行、发现全部引擎的固定开销；截断视觉响应不被接受为完成。
- 轻量引擎发现不再导入Paddle；详细doctor检查extras/import/CUDA，明确尚未运行的管线验证。Paddle缓存读取隔离环境dist-info，包升级改变身份；无法识别版本时不安全复用。

### 真实试跑

机器：Windows 10、RTX4070 Ti SUPER 16GB、约32GB RAM；模型已缓存，以下均为单次观察，不作严格速度排名。

| 操作 | 结果 |
|---|---|
| 原Attention PDF选择物理页3、4、8，MinerU standard+ocr | 15.99秒；source.pages=15，输出物理页[3,4,8]，QA pass，图资源存在 |
| triage | 选出p4-b5核心公式、p8-b0合并表格、p3-b0/p4-b0图块；不冒充错误检测 |
| 公式/架构图packet | 原页/bbox和邻近上下文正确；已用实际图像工具打开300DPI裁图 |
| 公式块本地refine | recognized，QA pass，Attention公式及编号保留；原文page=4，初稿不覆盖 |
| Paddle PDF单页（样本原论文第4页） | 修复环境后16.77秒，QA pass；图像、脚注保留 |
| Paddle PNG架构页 | 14.41秒，QA pass，无坏图链接；保留图像不等于理解其含义 |
| MinerU economy同一PDF单页 | 15.98秒，QA pass；main公式正确，脚注求和仍存在模型错误 |
| 干净core入口 | python -S运行pages成功，实际切到隔离core执行渲染 |

Paddle某处行内缩放公式把d_k读成d_x，而脚注求和比MinerU basic更完整；没有哪个引擎可在本样本中免复核。图像查看记录见 [visual-smoke](../evals/visual-smoke-2026-10-28.md)，本地环境与耗时证据见 [local-runtime](../evals/local-runtime-2026-10-28.json)。

### 环境操作

已在本机docvision-paddle隔离conda环境补齐缺失依赖，保留PaddleOCR3.7.0/PaddlePaddle3.2.1/PaddleX3.7.2；隔离pip check无破损，真实PDF/PNG已跑通。安装独立uv core环境并保存用户docvision配置中的core.python。未修改全局包、MinerU包或其他技能；具体包清单在local-runtime证据中。

### 验证与独立评审

- `python -m unittest discover -s maintenance/docvision/evals -p 'test_*.py'`：82项通过。
- `python maintenance/docvision/evals/check.py`：原5项通过。共87项自动检查；外部API部分使用本地HTTP mock和虚假token。
- `git diff --check`：无空白错误；仓库Windows换行提示不影响退出码。
- 实际CLI包括convert/triage/refine/read/verify，按源页[3,4,8]与单区域路径验证。
- 实际独立评审者hybrid_review未参与实现，发现局部上下文过宽、端点缓存遗漏和并发重复上传；三项已补失败回归并修复，独立复核通过。Paddle轻量版本身份补充问题也已实现元数据读取与集成。
- 收尾复核实际运行19项hybrid与20项local测试，通过；另验证未知Paddle身份要求显式force、同版本元数据指纹改变使缓存失效、图注保留和Gemini模型覆盖优先级，无新增阻塞。
- 技能frontmatter验证使用隔离Paddle Python的UTF-8模式运行quick_validate，输出Skill is valid；系统Python缺PyYAML不代表技能本身无效。

### 仍未证实

没有8GB真机、峰值显存、长文档吞吐/双并发基准或20–30页标注集。Paddle 官方云端已于收尾轮用真实 token 完成公式/合并表格裁图与本地同图对比，见[云端验证报告](paddle-cloud-verification-2026-10-28.md)；Gemini 与 MinerU 云端仍无真实令牌，只确认官方契约与本地协议兼容性，未宣称真实云端准确率或账号免费资格已验证。未自动注册账号或获取用户密钥。

### 参考依据（2026-10-28核验）

- [PaddleOCR官网免费额度公告](https://www.paddleocr.ai/main/index.html)：每日20,000页，以账号与服务规则为准。
- [PaddleOCR官方SDK协议](https://github.com/PaddlePaddle/PaddleOCR/tree/main/paddleocr/_api_client)与[官方skill](https://github.com/PaddlePaddle/PaddleOCR/blob/main/skills/paddleocr-doc-parsing/SKILL.md)。
- [MinerU官方skill](https://github.com/opendatalab/MinerU/blob/master/skills/mineru/SKILL.md)：吸收局部阅读、定位、邻近上下文与缓存实践，未安装或完整复制。
- [Gemini官方价格](https://ai.google.dev/gemini-api/docs/pricing)与[3.8 Flash模型说明](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)：可配置Flash免费层候选，仍需账号实际额度验证。
