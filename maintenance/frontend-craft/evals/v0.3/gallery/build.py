import base64, html, pathlib
G = pathlib.Path(__file__).parent

def img(name):
    return "data:image/jpeg;base64," + base64.b64encode((G / f"{name}.jpg").read_bytes()).decode()

CASES = [
  ("1", "论文筛选工具页", "“我在读 Agent 方向的论文，这是我整理的一批论文和阅读记录。帮我做一个论文筛选页面：能快速浏览、按方向筛选、看出哪些读过，方便我挑下一篇要读的。”",
   "12 篇真实 arXiv 论文的元数据，加上阅读状态和笔记",
   [("case1-none", "无技能"), ("case1-v02", "v0.2")],
   ["两组结构几乎一样：按“在读 → 未读 → 已读”分组，米色纸底，英文题名用宋体，单一朱红强调色。",
    "无技能组的桌面首屏能看到 3 篇论文。v0.2 组的页头占了约 240px，首屏只露出 2 篇；手机上，它的筛选区占了大半屏。",
    "两组都在浏览器里实际点过筛选和搜索，计数都对。"]),
  ("2", "中文导读阅读页", "“这是我写的一篇 ReAct 论文导读，帮我做成一个网页，电脑和手机上都要好读。”",
   "约 2500 字的导读，含 4 节、1 张对比表、1 个图注、英文术语和 5 条来源",
   [("case2-none", "无技能"), ("case2-v02", "v0.2")],
   ["两组也高度相似：纸色底、宋体正文、左侧目录，Thought / Action / Observation 做成三张卡片。",
    "无技能组的正文两端对齐。手机上首段字距被明显拉开（“基 本 是 分 开 研 究 的”），这是中英混排时两端对齐的典型问题。",
    "v0.2 组在手机上把目录收成可展开的块，正文直接从首屏开始，这一点更好。"]),
  ("3", "杂乱材料整理页", "“这是我们课题组招新的原始材料，写得比较乱。帮我做成一个招新页面，信息不要漏。”",
   "一份故意写乱的招新材料：重复、口号、六条空泛的“优势”、联系方式散落多处",
   [("case3-none", "无技能"), ("case3-v02", "v0.2")],
   ["两组都把截止日期、名额、开放日和邮箱放进首屏右侧的卡片，整体结构接近。",
    "v0.2 组把六条空泛的“优势”逐条对上具体事实，比如“算力充足”对应 8 张 A100，内容编辑更好。但它在开放日旁放了一条黄色“待核对”提示，这本该写在交付说明里，不该出现在页面上。",
    "两组都保留了“去年开放日改期”的旁注和“师兄师姐好相处”这类空话。",
    "材料把 2026 年 11 月 1 日写成了周六，实际是周日（这是我写材料时的笔误）。两组都发现了，也都没有擅自二选一。"]),
  ("4", "局部精修", "“这个页面首屏和手机上看着不太对，帮我修一下。”",
   "v0.2 自己的样例“晚间电台”，波形压住了文字，手机上每行都有一个按钮",
   [("case4-original", "修改前"), ("case4-none", "无技能"), ("case4-v02", "v0.2")],
   ["两组都靠截图自己发现了波形压字，并且修好了；首屏都能露出节目单。",
    "v0.2 组在桌面上把标题和导语改成左右并排，首屏能看到的内容更多；手机上曲目行改成单行。",
    "两组都没有清理画面上的制作说明：顶栏的“虚构电台 · 演示小样 · 无音源”，以及页脚的“frontend-craft v0.2.0 应用样例 · 检查记录”都还在。"]),
]

FINDINGS = [
  ("只要能截图，默认就会看图",
   "案例 4 中，没有技能的那组也自己发现并修好了遮挡。所以 v0.3 的看图部分，重点应该放在“看什么、按什么顺序修”，而不是“要不要看”。"),
  ("画面高度趋同",
   "无技能组和 v0.2 组几乎都是纸色底、宋体标题、一个暖色强调。v0.2 基本没有改变视觉方向，这正是常见的 AI 默认面孔。要拉开差距，得靠正面案例和具体手艺，不能只加规则。"),
  ("v0.2 的增益有限，也有副作用",
   "它的帮助主要在内容编辑（案例 3）和首屏利用（案例 4）；但也把写给用户的话放上了页面（案例 3 的“待核对”提示）。"),
  ("中文排版问题确实存在",
   "案例 2 的两端对齐字距问题，就是 cjk-typography 要专门讲的东西。"),
]

def frame(src, kind, label):
    view = "桌面 1280" if kind == "desk" else "手机 390"
    return (f'<figure class="shot {kind}"><div class="scroll" tabindex="0" aria-label="{label} {view} 整页截图，可滚动">'
            f'<img src="{src}" alt="{label} {view} 整页截图" loading="lazy"></div>'
            f'<figcaption><span>{view}</span><button type="button" class="zoom" data-label="{label} · {view}">原尺寸查看</button></figcaption></figure>')

out = []
for num, name, brief, inp, conds, notes in CASES:
    cols = []
    for run, label in conds:
        d, m = img(f"{run}-desktop"), img(f"{run}-mobile")
        cols.append(f'<div class="cond"><h3>{label}</h3><div class="pair">{frame(d,"desk",label)}{frame(m,"phone",label)}</div></div>')
    out.append(f'''<section class="case" id="case{num}">
<header class="case-head"><p class="case-no">案例 {num}</p><h2>{name}</h2>
<p class="brief">{html.escape(brief)}</p><p class="input">输入：{inp}</p></header>
<div class="conds n{len(conds)}">{"".join(cols)}</div>
<div class="notes"><h3>我的观察</h3><ul>{"".join(f"<li>{n}</li>" for n in notes)}</ul></div>
</section>''')

finds = "".join(f'<div class="finding"><h3>{t}</h3><p>{b}</p></div>' for t, b in FINDINGS)
page = (G / "template.html").read_text(encoding="utf-8").replace("{{FINDINGS}}", finds).replace("{{CASES}}", "\n".join(out))
(G / "baseline.html").write_text(page, encoding="utf-8")
print(len(page) // 1024, "KB")
