# 样式实验室实际验证

2026-10-26（Asia/Shanghai）。受审文件为仓库 `frontend-craft/assets/style-lab/`，与 rc.1 交付源码相同。本次未发现需要修改样张源码的阻塞问题。

## 环境和原始证据

- Windows，Codex 内置 Chromium 浏览器，通过 `cua_repl` 实际操作；本地 HTTP 为 `http://127.0.0.1:8766/frontend-craft/assets/style-lab/index.html`。
- 每次捕获前使用 viewport capability 设置尺寸，DOM 实测宽屏 `innerWidth=1440, innerHeight=1000`、窄屏 `390,844`。捕获工具直接返回的 JPEG 原件为 1425×990、375×811；工具截取区域与 CSS 视口不同，未缩放、重画或补边。正文实际尺寸判断使用显示原件和 DOM 尺寸，不能把 JPEG 尺寸冒充 CSS 视口。
- 只读 DOM 环境不暴露 `navigator.userAgent`，后通过本机诊断服务实际接收浏览器请求头，记录为 `Chrome/156.0.0.0`，见 [browser-request.json](../evidence/style-lab/browser-request.json)。这是浏览器声明的缩减版本，不冒充完整内部补丁构建号；全部配对在同一宿主浏览器执行。
- 正文计算字号 17 CSS px；无衬线栈为 PingFang SC、Microsoft YaHei、Noto Sans CJK SC、Noto Sans SC；纸面正文栈为 Noto Serif CJK SC、Noto Serif SC、Songti SC、SimSun。Windows 注册表确认 Microsoft YaHei、Noto Sans SC、Noto Serif SC、SimSun 已安装，未见 PingFang。按顺序推断此次中文主要使用 Microsoft YaHei / Noto Serif SC；工具没有逐字形实际命中字族接口，因此保留这个区别。截图中未见缺字或溢出。
- 原始截图和机器观察在 [evidence/style-lab](../evidence/style-lab/)，操作结果见 [interaction-checks.json](../evidence/style-lab/interaction-checks.json)，窄屏尺寸见 [mobile-checks.json](../evidence/style-lab/mobile-checks.json)。

## 实际观察

三主题均在宽屏和窄屏打开阅读视图。钴蓝以浅灰画布和白阅读面分出主体；深墨以较亮阅读面承托浅色正文，冰青集中在定位和选中；莓红同时改变纸面底调、衬线正文、标题字重和圆角。三者的区别超出替换按钮色。长标题完整，正文和工具文字具有明显尺度差，旁注比正文紧凑。正文标题上方的样张导航与身份说明占用一定高度，这是资源浏览器的框架，不建议一并复制到产品。

纸面主题查看列表过滤与摘要展开；浅色主题查看完整输入/反馈组件；纸面和深色查看选中、警告及键盘焦点组合。焦点外轮廓与选中填色分开，警告有符号和文字。所有状态均呈现为演示，不声称完成服务器保存。

窄屏三主题的 `scrollWidth=clientWidth=375`（含滚动条时 innerWidth 为 390），资料列表和组件视图也未出现页面横向溢出。正文保持自然滚动，核对面板在下方；顶部入口与段落引用可到达它。实际点击核对面板，再返回第二处原文，焦点分别落到 `evidence-panel` 和 `source-2`，目标上缘约 90 CSS px，未被固定导航遮挡。该样张说明的是可往返的关系，不证明长篇实际论文上的全部阅读位置策略。

## 已执行行为

- 三主题切换；阅读、列表、组件切换后标题获得焦点。
- 第二处引用定位与返回，桌面和窄屏均实际执行。
- 空批注提示错误，填写后仅在本页预览，反馈明确刷新后清除。
- 搜索无结果为 0/8，清空回到 8，待核对过滤为 3/8；摘要可展开。
- 空标题标记 `aria-invalid=true`；有效标题显示本页检查通过且未提交/保存。
- 手动加载、成功、错误、恢复状态逐个切换。
- 警告与选中同时存在；Tab 到组合条目，焦点轮廓可见且 `aria-describedby` 指向警告。
- 浏览器错误/警告日志为空。

51 组声明为不透明的文字、状态、输入边界和焦点角色对比通过，见 [contrast-check.json](../evidence/style-lab/contrast-check.json)。采用 [WCAG 文字对比](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) 与 [非文字对比](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) 的相对亮度计算；这不覆盖所有透明合成、字形渲染或辅助技术，也不是审美评分。

## 判断边界

本次支持这组三主题作为可运行、可观察的原创候选起点。未做其他浏览器、屏幕阅读器或真实设备输入法矩阵；未在真实产品使用，未宣称用户认可。配对生成与外部来源资源由各自证据判断，不能由样张通过替代。
