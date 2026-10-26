# Wikipedia 正文与来源定位补证

阶段：独立终审发现 R27 缺口后的资源补充研究；未参加已完成的六次对比构建。

目标：[Attention Is All You Need](https://en.wikipedia.org/wiki/Attention_Is_All_You_Need) 的 `Attention with seq2seq` 连续正文。2026-10-26 的网页文本读取显示：首段 2014 年两篇 seq2seq 研究的说明带有引用 [21] 与 [22]；[21] 对应 Cho 等人的 *Learning Phrase Representations using RNN Encoder–Decoder for Statistical Machine Translation*（EMNLP 2014），[22] 对应 Sutskever、Vinyals、Le 的 *Sequence to Sequence Learning with Neural Networks*（2014）。参考列表带回到正文位置的回链。

初期打开网页在工具初始快照阶段超时；之后根执行者对已加载标签分别使用更长工具时限，成功读取并截取真实页面。现已保存 `frontend-craft/assets/references/wikipedia-attention/body-citation.jpg` 与 `source-location.jpg`；根执行者实际点击正文首处 [21]，确认定位到 Cho 等人 2014 的第 21 条参考文献，原站显示浅蓝高亮、ACL/DOI 外部来源链接和两个正文回链。采集动作与 DOM 状态见同目录 `wikipedia-source-capture.json`。

参考核验者已通过本地图像工具逐张以原尺寸查看两张保存图，独立终审也核对了对应关系。正文图为 `#Attention_with_seq2seq`，CSS1440×1000，scrollY3647.199951；精确初次捕获元数据因内核重置丢失，2026-10-26T03:51:02Z 仅为文件保存时间。来源图捕获记录为2026-10-26T03:58:14.086Z，URL `#cite_note-:22-23`，scrollY8487.2001953125。两图原始JPEG均1425×990，未经裁切、重绘或缩放。回链后续验证由根执行者另存原始记录，不以静态截图替代动作。

许可依据：[Wikipedia:Copyrights](https://en.wikipedia.org/wiki/Wikipedia:Copyrights) 的 Re-use of text 要求署名、许可声明和修改说明，并允许通过原页面链接提供作者归属。文章正文采用 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)；[编辑历史与作者](https://en.wikipedia.org/w/index.php?action=history&title=Attention_Is_All_You_Need)。网页文本返回的固定版本为 [oldid=1381682429](https://en.wikipedia.org/w/index.php?title=Attention_Is_All_You_Need&oldid=1381682429)。本次正文及书目画面没有第三方架构图；来源图页脚的 Wikimedia/MediaWiki 小标识单独依据[官方商标政策](https://foundation.wikimedia.org/wiki/Policy:Trademark_policy)第3.6节和FAQ3.16的说明/教育性截图范围使用，不因正文CC许可而泛化标识权利，不暗示背书。运行资产目录 SOURCE.md 与 ATTRIBUTION.md 随图保留来源、许可链接及未修改说明。

本记录由备用研究更新为真实正文—引用—来源定位证据。索引状态与 R27 是否满足由根执行者合并后交独立终审判断；本次没有修改已冻结对比构建，也不声称这些新资源促成了此前生成结果。仍不将此例视为完整 AI/PDF 多段证据核验、窄屏或键盘流程的全面证明。
