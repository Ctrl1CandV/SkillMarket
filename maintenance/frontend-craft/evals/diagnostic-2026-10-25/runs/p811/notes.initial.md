# 页间「纸面研究」首稿说明

## 交付

- `page.initial.html`：可直接打开的独立中文 HTML；CSS、JavaScript 和三张作品 SVG 数据均内嵌。
- 当前阶段仅完成实现与静态代码自检，未启动浏览器，未查看渲染截图。

## 内容与实现

面向刊物编辑挑选讨论作品的任务。首屏结构为「页间」标识、专题标题、作品筛选和三件作品；作品图区采用不同起点的三列排布，保留作品原始比例。窄屏改为单列。标题使用系统宋体常规字重，界面使用微软雅黑等系统字体；配色取暖纸色与作品中的朱红色。

三件作品均有图片与标题入口。详情以原生 dialog 展示大图、标题、年份、媒介和原文说明，提供关闭、收藏和前后作品切换。收藏按钮始终可见；已收藏筛选为空时提供「浏览全部作品」。按钮使用原生 button、可见焦点样式、明确名称和 aria-pressed 状态。已收藏筛选中取消收藏后，代码会将焦点移至仍可操作的作品或返回按钮；详情关闭会恢复入口焦点，入口已隐藏时则回到筛选按钮。

以上为代码实现描述，不代表已经通过浏览器交互或视觉验收。

## 实际读取的输入

- `common.md`
- `collection.md`
- `assets/work-01.svg`
- `assets/work-02.svg`
- `assets/work-03.svg`
- `skill/SKILL.md`
- `skill/references/content.md`
- `skill/references/layout.md`
- `skill/references/cjk-typography.md`
- `skill/references/visual-style.md`
- `skill/references/review.md`

另读取生成的 `output/page.initial.html` 进行静态自检；列举过 `assets/` 的文件名和大小。未联网，未读取仓库、其他工作包或其他设计技能，未调用其他代理。首次 shell 使用工具默认登录模式，环境自动执行 PowerShell profile 并输出 conda 编码告警；未主动打开或检查该 profile，后续 shell 均显式使用非登录模式。所有 shell 调用显式指定本工作包为 workdir。

## 已做检查

使用本机 Node.js v22.23.3 做静态检查，不创建额外测试文件：

- 内嵌 JavaScript 通过 `vm.Script` 语法解析。
- 19 个 HTML ID 无重复；aria-labelledby 与 aria-describedby 引用均存在。
- 3 个作品图片的 Base64 解码结果分别与给定 SVG 原始字节一致。
- 页面包含 3 个作品 article 和 3 个列表收藏按钮；各按钮有明确的 button 类型。
- 三段作品说明与输入一致。
- 静态扫描未发现远程 src / href、网络接口调用、localStorage 或 sessionStorage。
- 按声明的 sRGB 色值计算，纸色背景上的正文、次要文字、朱红色文字对比度分别为 13.17:1、4.61:1、6.19:1。此项为数值计算，未验证实际字体渲染。
- 最后将详情图片的宽高读取改为源图片的原始 width / height 属性，再次检查 JavaScript 语法。

## 本地模拟边界

收藏通过页面内存中的 Set 保存，初始为零。刷新或关闭页面后不保留；不请求账号、不发数据、不连接后台。图片及作品元信息来自本工作包。详情和筛选均在当前页面完成。没有下载、购买、线下展期或后台管理流程，也没有引入作品评价、获奖、机构或作者履历。

## 尚未验证

遵照本阶段要求未启动浏览器。桌面及手机的首屏、整页、空收藏状态和详情弹层尚未看图；实际点击、Tab / Enter / Space、Esc 关闭、焦点恢复、移动端滚动及浏览器原生 dialog 行为尚未操作验证。当前不作「无溢出」「兼容全部浏览器」「交互已通过」或审美效果声明，待统一截图后在同一上下文修订。