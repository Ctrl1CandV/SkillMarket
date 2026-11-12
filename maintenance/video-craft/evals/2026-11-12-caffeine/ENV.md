# 机器环境

- Windows 10，命令通过 Git Bash 执行。路径可以写成 `/c/Users/...` 或 `C:\Users\...`。
- 显卡 RTX 4070 Ti SUPER，浏览器里的 WebGL 走显卡。
- Node v24。`playwright-core` 装在环境变量 `VC_NODE_MODULES` 指向的目录，不在当前目录。
- 浏览器用本机 Chrome，路径在环境变量 `VC_CHROME` 里。
- ffmpeg 8.1.1 在 PATH 里，带 libx264、aac、libvpx-vp9、libopus。
- 中文字体是系统字体：微软雅黑（Microsoft YaHei）、黑体、宋体、楷体、等线，以及 Noto Sans SC（可变字重）。没有 Noto Serif SC、Ubuntu 字体文件。
- Python 3 可用（`python`），带 numpy、Pillow。
- 没有语音合成，没有外部素材。
- 你看不到也听不到视频。需要检查画面时，截图或抽帧，再用读文件工具看图片。
