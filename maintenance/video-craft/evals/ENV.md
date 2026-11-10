# 本机环境说明

以下路径只读，不要修改它们下面的文件。所有产出只写在当前工作目录内。

- 无法联网安装依赖：npm install、pip install 都不可用。
- Node.js 24，可直接运行 .mjs 脚本。
- Python 3.10，只有标准库（没有 Pillow、numpy）。
- playwright-core 已安装，在你的 Node 脚本里这样引入：

  ```js
  import { createRequire } from 'node:module';
  const require = createRequire('/home/claude-dev/.local/share/fc-eval/render/package.json');
  const { chromium } = require('playwright-core');
  ```

- 无头 Chromium：`/home/claude-dev/.cache/ms-playwright/chromium_headless_shell-1187/chrome-linux/headless_shell`
  （`chromium.launch({ executablePath: ... })`）。运行 node 前必须设置两个环境变量：

  ```text
  LD_LIBRARY_PATH=/home/claude-dev/.local/share/fc-eval/render/libs/lib
  FONTCONFIG_FILE=/home/claude-dev/.local/share/fc-eval/render/fonts.conf
  ```

- 中文字体文件（思源黑体、思源宋体，OFL 许可），目录 `/home/claude-dev/.local/share/fc-eval/render/fonts/`：
  `NotoSansSC-Regular.otf`、`NotoSansSC-Bold.otf`、`NotoSerifSC-Regular.otf`、`NotoSerifSC-Bold.otf`。系统里没有其他中文字体。
- 没有完整的 ffmpeg/ffprobe。只有 Playwright 自带的精简版 `/home/claude-dev/.cache/ms-playwright/ffmpeg-1011/ffmpeg-linux`，它只能：
  - 把 JPEG 图片经标准输入管道编码成 VP8 WebM：`-f image2pipe -c:v mjpeg -framerate 30 -i pipe:0 -c:v libvpx -b:v 8M out.webm`（输入必须写 `pipe:0`）；
  - 把 WebM 解码成单帧 PNG：`-ss <秒> -i in.webm -frames:v 1 out.png`。
  
  不支持 PNG 或 H.264 输入、H.264 输出、音频，滤镜只有 scale、crop、pad。
- 没有 TTS、音乐和音效素材。
