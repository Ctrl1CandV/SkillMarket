# video-craft 实验室（2026-11-10 起）

用户决定（2026-11-10）：先自己调研、思考、动手做视频，做到“我觉得好、用户也觉得好”，再把经验和成果转成技能或插件。0.1.x 的规则手册路线暂停，其评测与复盘作为参考（`../evals/`）。

## 路线

1. 调研：好的讲解视频、竖屏科普、产品宣传片为什么好；代码视频的强项；声音的作用。结论写入 `research.md`，每条带来源。
2. 实验：用两道旧题（排队悖论竖屏科普、拾光笔记横屏宣传）自己做，逐轮记录做法、看到的问题、改法和效果，写入 `log.md`。工作区 `~/.local/share/vc-lab/`（不进仓库）。
3. 用户评审：给成片和对比页，按用户意见再改。
4. 提炼：只把实验中证明有效的做法、零件和检查转成技能或插件。

## 本机条件（2026-11-10）

- shell 无网络（开发代理 17892 拒绝连接）：不能装 ffmpeg 完整版、GSAP、Remotion、TTS。
- 可用：headless_shell 140（WebCodecs：VP9、AV1、Opus；无 H.264、无 AAC；无系统语音）；Playwright ffmpeg-1013（png/mjpeg 输入 → VP9 WebM，无音频编码，滤镜只有缩放裁切）；npm 离线缓存有 d3 全家、three、katex、roughjs、react、vite、@napi-rs/canvas；Noto Sans/Serif SC 字体（fc-eval/render）。
- 完整 chrome 在沙箱里因 socket 权限启动失败，用 headless_shell。
