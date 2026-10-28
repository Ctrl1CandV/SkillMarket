# 精读包实际看图记录

来源：公开 Attention Is All You Need v7，原 PDF 第3页 `p3-b0` 与第4页 `p4-b5`。本地解析使用原PDF与物理页码3、4、8；没有上传。

实际执行 `triage` 与 `refine --provider packet`，用图像查看工具打开300 DPI裁图，而非仅查看路径。

## 架构图

图像保留左右两组结构、模块文字和连线，可直接观察：

- 左侧 Inputs 经 Input Embedding 与 Positional Encoding 相加，进入 Multi-Head Attention、Add & Norm、Feed Forward、Add & Norm；标有 N×。
- 右侧输入为 Outputs (shifted right)，经 Output Embedding 和位置编码相加；底层为 Masked Multi-Head Attention，上方还有一个 Multi-Head Attention 与 Feed Forward，各有 Add & Norm。
- 左侧编码分支的顶部输出有连线进入右侧中间的 Multi-Head Attention，右侧底层结果也向该模块输入。
- 多个子层边缘可见绕过子层、回到 Add & Norm 的残差连线。
- 右侧顶部依次为 Linear、Softmax、Output Probabilities。

限定：图只标 N×，本次裁图没有给出 N 的具体值；没有凭熟悉这篇论文补成6。图中未直接标注Q/K/V角色或张量维度，这些需结合正文解释，不能当成已从图中文字读出。裁图和邻块上下文能支持上述观察；本记录证明精读包可供看图，不证明外部Gemini API已测试。

## 公式

第4页裁图包含完整 attention 公式、分母平方根、转置上标与右侧编号(1)，人工对照看图与本地转写一致。随后对同一裁图执行 `refine --provider mineru-local --task formula`，生成独立 recognized 结果、qa pass，并保留 source.page=4 与原 bbox；初稿未覆盖。

单个公式正确不能代表密集公式总体准确率。原图与完整输出仅保存在本机临时目录，本记录不收入论文文件。
