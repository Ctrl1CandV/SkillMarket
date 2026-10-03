# 主会话浏览器检查

2026-10-03。通过官方 ZCode IAB 运行根目录两份HTML；未修改已安装技能。

- evening-radio.html 在1280×720加载，DOM呈现节目单、筛选、播放台。尝试点击“雨夜”超时，重新快照确认仍为全部9段；不得将mock成功当真实点击成功。未进一步完成键盘、选择与播放路径。
- 电台390×844测得innerWidth=390、documentElement.scrollWidth=375，无当前文档级横向溢出。
- field-notes.html 在390×844及1280×900加载，scrollWidth分别375、1265，无当前文档级横向溢出。
- 两页各生成桌面/手机截图。工具仅返回工件路径，当前未获得可靠可判读画面，不声称视觉通过；未完成真实看图后的修订、长页下半部、缩放和屏幕阅读器测试。

截图存于当前会话artifacts（非运行包）：电台 call_9uu2wbsjdXQDPUxNVGacf0Xs；植物志 call_P0zfUmzv1O5qKR9EYIhPFvf2。

复跑维护检查：新小样371项静态/mock断言与16组声明色对比度检查通过；旧样例/当前技能引用45项通过；git diff --check通过。这些数量不是视觉评分，也不是对新skill效果的独立A/B证据。
