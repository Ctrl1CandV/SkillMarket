# 外部参考采集记录（2026-10-26）

六张在线原始页面截图来自四个独立主体，覆盖连续阅读与来源核对、密集操作与内容展示。使用 Codex cua_repl 的 IAB 标签；每个状态读取 DOM 视口确认 CSS 1440×1000，再保存 `tab.screenshot({fullPage:false})` 的原始字节。所有输出为 JPEG 1425×990；这是工具实际输出与 CSS 视口的差异，未裁切、重画或缩放。保存后逐张查看。未进行图像生成或人工模拟外部网站。Wikipedia 的两图是六次配对构建冻结后的覆盖补充。

| 运行资产路径（相对仓库） | 页面/状态 | 实际观察与许可 |
| --- | --- | --- |
| `frontend-craft/assets/references/tufte-css/desktop.jpg` | 官方 Tufte CSS Sidenotes 章节，旁注编号 3 | 连续正文与较小旁注邻近；原始说明、代码采用仓库 MIT；没有第三方插图进入截图 |
| `frontend-craft/assets/references/tabler/desktop.jpg` | 官方 Tabler DataTables；实际点击 Name 升序，定位 #content | 15 行 7 列、连续表面、轻分隔、蓝色进度；仓库 MIT；没有头像照片或第三方图表 |
| `frontend-craft/assets/references/photoswipe/gallery.jpg` | 官方 PhotoSwipe 首页五图画廊 | 大竖图和四张横图、标题和署名；网页代码 MIT，Luca Bravo 摄影依据 Unsplash 单独许可 |
| `frontend-craft/assets/references/photoswipe/lightbox.jpg` | 实际打开第一图，1 / 5 灯箱 | 原图比例与暗背景、外围控件；只验证打开，不声称全面测试 |
| `frontend-craft/assets/references/wikipedia-attention/body-citation.jpg` | Attention with seq2seq 正文第一段 [21][22] | 连续正文与来源编号；原页 original research? 提示照录；不替科学结论背书 |
| `frontend-craft/assets/references/wikipedia-attention/source-location.jpg` | 实际点击第一处 [21]，Cho 2014 来源高亮 | 作者/题名/链接与返回入口；第一回链实际回到正文，状态记录单独保存 |

前三个来源的运行目录附有完整原始 MIT 文本及 SOURCE.md / ATTRIBUTION.md；Wikipedia 的文字 CC BY-SA 4.0、编辑历史、固定版本与页脚标识说明见其 SOURCE/ATTRIBUTION。详细字段在 `frontend-craft/references/exemplar-index.json`，只为真实采集并查看的状态标记 verified_visual。PhotoSwipe 与 Wikipedia 各两个状态，分别只计一个主体。

许可核验使用原作者的 GitHub 文件与官方 Unsplash 许可页。Tufte 的 gh-pages 原始 index.html 对应旁注说明；Tabler dev 原始 datatables.astro 与 rollercoasters.json 对应表格；PhotoSwipe master 的 demo-docs-website/src/pages/_index-gallery-header.js 明示 Luca Bravo 与 Unsplash 图片 ID。完整上游 URL 保存在各运行资产 SOURCE.md / ATTRIBUTION.md 与索引。来源页面是采集当时在线版本，未声称与某个固定代码 commit 完全一致。

Oil UI 的旧 reader/minutes/mail/folio 条目保持 candidate：虽然仓库有 MIT 代码许可，当前核对的树没有找到这些旧站点作品；不能据此推定网站图片也可再分发。Linear、Carbon、Letterform 的方法资料维持 documented，未以文字核验冒充本地画面。

这些参考的适用边界必须保留：Tufte 的短英文旁注不等于长 AI 证据核验；Wikipedia 只证明正文来源定位而非结论真实性，其回链目标贴近顶边；Tabler 的短英文数据不等于中文长字段；PhotoSwipe 的照片构图不等于完整档案产品。本轮未验证这些外部页面的移动端和所有交互。Wikipedia 的正文精确捕获调用时间在工具超时中丢失，仅记录保存日期和文件保存时间；来源图及回链的独立 JSON、未入运行资源的 Distill 尝试研究均留在本目录。
