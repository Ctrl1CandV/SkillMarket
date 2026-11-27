# video-craft 1.2.0 第二阶段（产品宣传 / MV 双档视效体系）待显卡空闲盲评预案

> **当前状态**：`1.2.0` 的双档视效引擎（第一档 `kit/stage.js` + `draw.js`；第二档重装绚丽视效 `kit/stage3d.js` + 离线 Three.js r160 PBR/HDR 泛光引擎 + `kit/shader.js` `{ sdf: true }` 光线步进库 + 可选 `kit/blender_bridge.py`；共享音频 `kit/sound.js` 阻尼混响与新乐器拟音；质检脚本 `captions.mjs`、`textcheck.mjs`、`shotlist.py`、`doctor.mjs`）及全套轨道 B 文档均已在 `dev` 分支落地，并通过零 GPU 六项全链路单测（`check-phase2-kit.mjs`、`check-captions.mjs`、`doctor.mjs`）。
> 因本机 `RTX 4070 Ti SUPER` 正被其他重任务占用，遵照用户安排，**成片渲染盲评待显卡释放后执行**。

---

## 一、验收重点：同时检验「第一档清晰实操」与「第二档重装震撼绚丽视效」

用户明确提出：产品宣传与 MV 分为两档——常规清晰实操走第一档，特殊需求要**视觉效果震撼、视频画面绚丽**（媲美 Blender / C4D / 发布会大片质感）时走第二档。因此显卡释放后重点验证**第二档（重装绚丽视效档）**能否真正打破普通平面感，同时可选对照第一档：

1. **零重题、零示例泄漏**：不碰群聊算账、演出改期、带伞/CO2灯、夜湖码头或《time machine》/《Toyland》。
2. **检验第二档五项大片指标（反“2005 廉价屏保方块”）**：
   - 路由准确性：提示词提出“视觉震撼、画面绚丽、流光溢彩大片感”时，模型是否主动切入第二档阅读 `references/spectacle-3d.md`，使用 `stage3d.js`（圆角切面金属/折射水晶/薄膜虹彩 + 程序化摄影棚柔光箱 `studioEnv` + 5 级防闪烁 HDR 泛光 + `ACESFilmic` 色调映射）与/或 `shader.js` `{ sdf: true }` 光线步进；
   - 画面层次与分镜：是否具备三档材质粗糙度反差、窄焦微距掠光切入全景的真实 `SHOTS` 镜头调度（而非一个直角方块原地转 30 秒），且文字依然采用锐利的 2D 叠加；
   - 开放创造力：不在提示词里锁死颜色，检验能否根据具体产品/歌曲长出独特美学世界（如高调日光水晶影棚、精密钛金属微距、液态虹彩流变等，而非千篇一律黑底紫雾）。

---

## 二、待跑验收题单

### 1. 旗舰产品震撼揭晓大片（第二档 · 轨道 B1，25–30 秒，合成配音/配乐）

- **题目设定**：桌面声学旗舰解码耳放一体机 **「棱镜 Prism Audio One」**（整块阳极氧化深空钛金属与高折射光学水晶旋钮咬合，转动阻尼旋钮时内部光纤导光环随采样率从琥珀金流转至冰川蓝，声底信噪比 132 dB）。要求做出发布会级别的震撼绚丽三维产品大片，既有贴近倒角切面与水晶折射的微距掠光镜头，也有声波能量场展开与核心规格定格。
- **可选第一档轻快对照题**：桌面剪贴板时间轴软件 **「拾贴 SnapShelf」**（检验 `stage.js` 零过冲弧线指针与正视工作台真实交互闭环）。

### 2. 高燃流光视听奇观 MV（第二档 · 轨道 B2，35–45 秒，真实原声拍点切镜 + 校对双语字幕）

- **题目设定**：选用一首技能与历史评测中从未出现过的 CC BY 授权高能量电子/独立流行人声曲目选段（放入 `media/song.m4a` 与 `source.txt` 官方歌词及署名信息），明确要求做出**画面绚丽、极具视觉冲击力的第二档视效 MV**。
- **考察点**：
  - `songmap.py --lyrics` → 校改 `lyrics.srt` → `captions.mjs --no-overlap` 零报错；
  - 用 `stage3d.js` `instancedField` 千枚三维实例场或 `shader.js` `{ sdf: true }` 液态/晶体光线步进与歌曲 `downbeats`、`kick`、`energy` 精准共振，副歌回归时空间尺度与光色明显递进；
  - `shotlist.py --song`、`textcheck.mjs` 与 `1920×1080 @ 30fps` 原声封装全过。

---

## 三、显卡释放后的开跑命令序

1. `node video-craft/kit/doctor.mjs` 确认 `gpu.busy === false`（硬件 WebGL2 全速开启，无需 `VC_SOFTWARE_GL=1`）。
2. 在 `%LOCALAPPDATA%\vc-eval\2026-11-XX-phase2-spectacle\` 建立隔离工作区，跑 `deepseek/deepseek-flash`（按需加 `openai/gpt-6.1-sol` 对照，开跑 GPT 前先征得用户同意）。
3. 导出联系表、原尺寸关键帧、`shotlist.py` 与音轨指标交用户盲看验收；验收通过后合并 `main` 并按用户指示推送。
