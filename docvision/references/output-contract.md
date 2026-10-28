# 输出契约

每次转换写一个目录，目录内文件稳定，供人或 AI 直接读取。不要把 provider 原始 JSON 当成交付；统一契约在 `content.json`。

## 目录

```text
<out>/<doc>/
  <doc>.md         主 Markdown，带 docvision 头和可选页标记
  content.json     逐页、逐块的内容与定位
  meta.json        来源、引擎、选项、耗时、隐私、警告
  qa.json          确定性检查
  assets/          Markdown 引用的图片/图表/表格图
  pages/           按需生成的页面 PNG
  crops/           按需生成的局部图
  raw/             --keep-raw 时的 provider 原始 JSON/Markdown
  refinements/     独立精读请求、原页/bbox、裁图、上下文与结果
```

目录名来自原文件名（保留中文，替换 Windows 非法字符）；同名输入会加短哈希，不覆盖已有结果。`--resume` 比较源指纹、请求签名和 QA；改变档位、mode、页范围、provider、model/配置等会重跑。旧版无签名输出不直接复用。

## `content.json` 字段

```json
{
  "schema": "docvision.content/1",
  "source": {
    "name": "paper.pdf",
    "path": "D:\\docs\\paper.pdf",
    "sha256": "…",
    "bytes": 1234567,
    "pages": 12
  },
  "provider": "mineru-local",
  "model": "MinerU 4 (4.0.12)",
  "privacy": "local",
  "pages": [
    {
      "page": 1,
      "width": 595.0,
      "height": 842.0,
      "markdown_chars": 1834,
      "blocks": [
        {
          "id": "p1-b0",
          "type": "heading",
          "markdown": "## 1 Introduction",
          "text": "1 Introduction",
          "bbox": [0.12, 0.07, 0.42, 0.09],
          "bbox_space": "normalized",
          "level": 2,
          "asset": null,
          "confidence": null,
          "meta": {"provider_type": "paragraph_title", "index": 0}
        }
      ]
    }
  ],
  "assets": {
    "page_2_figure_4.jpg": {"page": 2, "type": "image", "block": "p2-b4"}
  },
  "warnings": []
}
```

约定：

- `page` 从 1 开始；`bbox` 是 `[x0,y0,x1,y1]`，`bbox_space` 为 `normalized` 时相对页面宽高（0-1）。缺失时为 `null`，不要猜。
- `type`：`heading | text | table | formula | image | chart | list | code | other`。
- `markdown` 是该块可直接放进 Markdown 的文本；`text` 是纯文本/HTML 内容，便于检索。
- `id` 形如 `p<page>-b<index>`，用于 `read --block` / `crop --block`。
- `asset` 指向 `assets/` 下的文件；表格块可能同时有 HTML 和区域截图。
- `source.path` 是本机绝对路径，方便之后渲染/裁剪；远程转换后原始文件不在本机时，`read --format image` 会明确报错。
- `privacy` 只有 `local` / `uploaded`；`uploaded` 时 `meta.route.remote=true`。

## `meta.json`

关键字段：

- `generated_at`、`elapsed_seconds`
- `route`：`provider`、`label`、`privacy`、`remote`
- `options`：`tier`、`mode`、`pages`、`lang`、`device`
- `pages`、`assets`、`warnings`
- `usage`：provider 返回的 token/耗时/command（视引擎）
- `raw_meta`：任务 ID、命令、endpoint 等排障信息
- `raw_meta.cache_request`：影响输出的请求签名；extra/context 只存哈希，避免意外存入密钥。

不记录 API key、token、cookie。

## `qa.json`

`status` 为 `pass | warn | fail`；`issues[]` 每项含 `severity`、`code`、`message`。

检查项：

- 主 Markdown 是否有实际正文/图片，只有元信息头不算内容
- 实际页集合是否与源页数/选页集合一致；未知源页数明确 warn，不能宣称完整
- Markdown 图片引用是否能在 `assets/` 找到
- HTML `<table>` 开闭是否平衡
- 未转义 `$` 是否为偶数
- U+FFFD 替换字符比例
- 重复页文本（缓存/页循环错误的信号）
- 页标记覆盖（若有页标记）

`pass` 不代表 OCR 正确；`fail` 必须修或换引擎。`warn` 要人看页面图。

## 精读记录

`refinements/<签名>/record.json` 使用 `docvision.refinement/1`，保存 `source.page/block/bbox/sha256`、task、provider、dpi、输入/上下文路径、模型、状态、结果路径与 `accuracy_verified=false`。独立结果的页 1 表示裁图输入，引用论文时必须使用 record.source.page，不能写成原文第 1 页。

状态为 planned、review_required、submitted、recognized、failed。planned 不联网；review_required 是图包已准备；recognized 只代表识别返回且结构未失败。submitted 中断状态需检查远程任务，默认不自动重传。`--force` 保留旧记录并新建尝试。

主 Markdown 不会被精读覆盖；`read` 另列关联记录。图片缓存名含实际源文件SHA、页码与DPI；源内容改变或强制重转后不会复用旧图。

批量输出目录以原子操作预留，同名输入也独立保存。`--force` 只复用来源路径相同的已有文档；已有写入占用时明确拒绝，避免覆盖正在生成的结果。异常终止遗留锁时，先确认没有写入进程，再按错误提示清理该锁。

## 页与引用

- 主 Markdown 不一定有页标记：MinerU 的 `markdown.md` 是整篇，Paddle 是按页拼接。**引用时用 `read --page` 或 `content.json` 的 `page`，不要靠 Markdown 里的位置猜。**
- 需要页码证据时，用 `read <dir> --page N`；需要看原图时用 `read --format image` 或 `crop`。
- 表格的 HTML 块优先于 Markdown 表格；合并单元格/跨页表必须看页面图。
- 公式以 LaTeX 保存；`formula` 块和正文中的 `$...$` 都可能出现。不要为了让 Markdown 好看而改写公式。

## 资产

- `assets/` 是扁平命名，避免路径穿越和 provider 子目录差异。
- 图片引用会从 `images/...`、`imgs/...`、`assets/...` 重写为 `assets/...`。
- 远程 provider 返回 base64 图片时，会落盘为文件；只有 URL 且下载失败时保留原 URL，并在 `qa` 里提示。
- 不是所有 provider 都给图片：本地视觉模型或纯文本输出端点没有资产；`content.json` 会如实缺失，不伪造。

## 兼容与版本

- `schema` 目前为 `docvision.content/1`；未来变更会提升版本，不静默改字段含义。
- `meta.schema` 为 `docvision.meta/1`，`qa.schema` 为 `docvision.qa/1`。
- 旧的 provider 输出（MinerU 4 `middle_json`、MinerU 云 `layout.json/content_list.json`）在适配层转换，不直接暴露给下游。
