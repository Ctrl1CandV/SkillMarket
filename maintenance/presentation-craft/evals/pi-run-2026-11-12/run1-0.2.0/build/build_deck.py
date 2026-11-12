"""Build out/progress.pptx — 两周实验进展组会汇报 (10 min)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.dml import MSO_LINE_DASH_STYLE as DASH

import deckkit as K
from deckkit import (BG, INK, MUTED, ACCENT, SECOND, SURFACE, RULE, PALE,
                     LEFT, RIGHT, CW, W, H, add_text, add_rect, box_text,
                     add_line, add_arrow, add_table, cell_border)

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
CHARTS = os.path.join(HERE, "charts")
OUT = os.path.join(TASK, "out", "progress.pptx")

CONTENT_TOP = 1.86
FOOT_Y = 7.04


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def head(slide, kicker, title, size=28, width=CW):
    if kicker:
        add_text(slide, LEFT, 0.40, width, 0.28, kicker, size=12,
                 color=ACCENT, bold=True)
    add_text(slide, LEFT, 0.70, width, 0.92, title, size=size, color=INK,
             bold=True, line=1.14)


def foot(slide, n, source=""):
    if source:
        add_text(slide, LEFT, FOOT_Y, CW - 1.1, 0.26, source, size=10.5,
                 color=MUTED)
    add_text(slide, RIGHT - 0.8, FOOT_Y, 0.8, 0.26, f"{n}", size=10.5,
             color=MUTED, align=PP_ALIGN.RIGHT)


def label(slide, x, y, w, txt, size=12.5, color=MUTED):
    add_text(slide, x, y, w, 0.26, txt, size=size, color=color, bold=True)


def notes(slide, txt):
    slide.notes_slide.notes_text_frame.text = txt


# ===================================================================== 1 cover
def slide_cover(prs):
    s = blank(prs)
    add_rect(s, 0, 0, W, H, fill=BG)

    add_text(s, LEFT, 1.42, 9.0, 0.3, "组会汇报 · 实验进展", size=13,
             color=ACCENT, bold=True)
    add_text(s, LEFT, 1.86, 10.6, 1.9,
             "查询改写 + 重排，能不能把多跳证据\nRecall 提上去", size=38,
             color=INK, bold=True, line=1.16)

    add_line(s, LEFT, 4.06, LEFT + 4.2, 4.06, color=ACCENT, lw=2.2)

    add_text(s, LEFT, 4.36, 9.9, 1.0,
             [{"t": "HotpotQA 与 2Wiki 上 Recall@5 稳定 +4.5～5.2 点；"
                    "MuSiQue 只有 +1.1，落在种子波动内，代价是 3.4 倍延迟。",
               "size": 21, "color": INK, "line": 1.35}])

    add_text(s, LEFT, 6.28, 6.6, 0.3, "2026-11-17　·　10.29–11.11 的实验记录",
             size=13, color=MUTED)
    add_text(s, LEFT + 6.9, 6.28, 5.0, 0.3,
             "3 个数据集 × 3 个随机种子　·　QR+CE vs 3 个基线", size=13,
             color=MUTED, align=PP_ALIGN.RIGHT)

    notes(s, "开场 40 秒。上次组会定的是查询改写 + 交叉编码器重排，这两周把它做出来、"
             "并在三个多跳数据集上跑了三个种子。一句话结论：小数据集上有效，"
             "MuSiQue 上没看到明确提升，延迟是 3.4 倍。今天想请大家帮我在三个决策上给意见。")
    return s


# ============================================================== 2 what was done
def slide_work(prs):
    s = blank(prs)
    add_rect(s, 0, 0, W, H, fill=BG)
    head(s, "01 · 本轮工作", "沿上次定的方向做了四件事，并固定了验证设置", size=27)

    lx, lw = LEFT, 4.72
    add_text(s, lx, CONTENT_TOP + 0.02, lw, 0.26, "上次组会定的方向", size=12,
             color=MUTED, bold=True)
    add_text(s, lx, CONTENT_TOP + 0.30, lw, 0.72,
             "查询改写 + 交叉编码器重排，看能不能把多跳问答的证据召回提上去。",
             size=17, color=INK, line=1.3)

    add_text(s, lx, CONTENT_TOP + 1.24, lw, 0.26, "这两周做的四件事", size=12,
             color=MUTED, bold=True)

    items = [
        ("1", "复现三个基线：BM25、Dense、Dense+CE", 0.52),
        ("2", "实现 QR+CE：改写 2–3 个子查询 → 多路检索 → 合并 → CE 重排", 0.86),
        ("3", "重排器用难负例重训；重排深度固定 50", 0.54),
        ("4", "三数据集 × 3 seed；另做消融与 60 条 MuSiQue 错例分析", 0.86),
    ]
    y = CONTENT_TOP + 1.54
    for num, txt, _ in items:
        n = K.count_lines(txt, 15.5, lw - 0.32)
        add_text(s, lx, y + 0.02, 0.3, 0.3, num, size=14, color=ACCENT, bold=True)
        add_text(s, lx + 0.32, y, lw - 0.32, 0.72, txt, size=15.5, color=INK,
                 line=1.32)
        y += n * 0.315 + 0.26

    # right: setup table
    tx, tw = 5.72, 6.89
    label(s, tx, CONTENT_TOP + 0.02, tw, "验证设置（三个数据集一致）")
    rows = [
        ["项目", "设置"],
        ["数据集", "HotpotQA（distractor 设置）、2WikiMultihopQA、MuSiQue"],
        ["比较对象", "BM25、Dense（bge-base）、Dense+CE、QR+CE"],
        ["重复", "每个设置 3 个随机种子，报 mean ± SD"],
        ["指标", "Recall@5 ↑、EM ↑、F1 ↑"],
        ["重排器", "交叉编码器，难负例重训版，depth = 50"],
        ["延迟", "单条查询端到端，拆成改写 / 检索 / 重排三段"],
    ]
    add_table(s, tx, CONTENT_TOP + 0.34, [1.32, tw - 1.32],
              [0.40, 0.62, 0.52, 0.52, 0.46, 0.52, 0.62],
              rows, font=14.5, header_font=13, header_fill=SURFACE,
              aligns=[PP_ALIGN.LEFT, PP_ALIGN.LEFT], line=1.15,
              margins=(0.12, 0.12, 0.06, 0.06))
    add_text(s, tx, 6.28, tw, 0.5,
             "固定这些设置，是为了后面所有比较都只差“改了什么”这一项。",
             size=14, color=MUTED, line=1.25)

    foot(s, 2, "来源：本轮实验记录；基线与本组实现见 material.md")
    notes(s, "1 分钟。强调三点：基线是复现的、重排器是同一个结构只是换了训练数据、"
             "三个数据集都跑了三个种子。设置表里唯一想请大家注意的：延迟是端到端的查询侧延迟，"
             "不含生成，所以后面的 3.4 倍是比较检索链路的。")
    return s


# ================================================================= 3 method
def _flow_box(s, x, y, w, h, title, sub="", color=INK, fill=SURFACE,
              line=None, lw=1.0, size=14, sub_size=11.5, dash=None):
    b = add_rect(s, x, y, w, h, fill=fill, line=line, lw=lw, radius=0.08, dash=dash)
    tf = b.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.line_spacing = 1.05
    r = p.add_run()
    K._apply_run(r, title, size, color, True)
    if sub:
        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        p2.line_spacing = 1.05
        p2.space_before = Pt(2)
        r2 = p2.add_run()
        K._apply_run(r2, sub, sub_size, MUTED, False)
    return b


def slide_method(prs):
    s = blank(prs)
    add_rect(s, 0, 0, W, H, fill=BG)
    head(s, "02 · 方法", "相对 Dense+CE，只多了两处：子查询检索与候选合并", size=27)

    # baseline row
    label(s, LEFT, 1.74, 5.0, "Dense+CE（基线）", color=SECOND)
    y1, h1 = 2.04, 0.82
    _flow_box(s, LEFT, y1, 1.95, h1, "多跳问题", "原问题", color=MUTED,
              fill="EEF3F0")
    _flow_box(s, 2.95, y1, 2.3, h1, "稠密检索", "bge-base，top-k", color=MUTED,
              fill="EEF3F0")
    _flow_box(s, 8.42, y1, 2.05, h1, "交叉编码器重排", "depth = 50", color=MUTED,
              fill="EEF3F0")
    _flow_box(s, 10.82, y1, 1.79, h1, "top-5 证据", "", color=MUTED,
              fill="EEF3F0")
    add_arrow(s, 1.95, y1 + h1 / 2, 2.88, y1 + h1 / 2, color=PALE)
    add_arrow(s, 5.30, y1 + h1 / 2, 8.35, y1 + h1 / 2, color=PALE)
    add_text(s, 5.42, y1 + h1 / 2 + 0.12, 2.85, 0.28,
             "无改写：原问题单路检索直接进重排", size=11.5, color=MUTED)
    add_arrow(s, 10.48, y1 + h1 / 2, 10.75, y1 + h1 / 2, color=PALE)

    # ours row
    label(s, LEFT, 3.28, 6.0, "QR+CE（本轮）", color=ACCENT)
    y2, h2 = 3.60, 1.02
    _flow_box(s, LEFT, y2, 1.95, h2, "多跳问题", "", fill=SURFACE,
              line=PALE)
    _flow_box(s, 2.95, y2, 1.95, h2, "查询改写", "2–3 个子查询", color=ACCENT,
              fill="DDF0E8", line=ACCENT, lw=1.4)
    _flow_box(s, 5.18, y2, 2.0, h2, "并行检索 ×N", "BM25 + Dense", color=ACCENT,
              fill="DDF0E8", line=ACCENT, lw=1.4)
    _flow_box(s, 7.46, y2, 0.78, h2, "合并\n候选", "", color=ACCENT,
              fill="DDF0E8", line=ACCENT, lw=1.4, size=13)
    _flow_box(s, 8.42, y2, 2.05, h2, "交叉编码器重排", "depth = 50",
              fill=SURFACE, line=PALE)
    _flow_box(s, 10.82, y2, 1.79, h2, "top-5 证据", "", fill=SURFACE, line=PALE)

    for x0, x1 in ((1.95, 2.88), (4.90, 5.11), (7.18, 7.39), (8.24, 8.35),
                   (10.48, 10.75)):
        add_arrow(s, x0, y2 + h2 / 2, x1, y2 + h2 / 2, color=SECOND)

    # shared reranker marker
    add_line(s, 9.44, y1 + h1, 9.44, y2, color=ACCENT, lw=1.0, dash=DASH.DASH)
    add_text(s, 9.52, y1 + h1 + 0.22, 2.9, 0.3, "同一重排器、同一深度",
             size=11.5, color=ACCENT, bold=True)

    # why it may work
    add_line(s, LEFT, 5.20, RIGHT, 5.20, color=RULE, lw=0.9)
    label(s, LEFT, 5.34, 5.0, "为什么可能有效")
    add_text(s, LEFT, 5.64, 7.0, 1.0,
             "多跳问题的第二跳，常常要读到第一跳的文档才知道中间实体是谁；"
             "按跳拆开的子查询把更多相关文档拉进候选池，再由重排器做精度筛选。",
             size=15.5, color=INK, line=1.32)
    label(s, 7.95, 5.34, 4.5, "这次要检验的")
    add_text(s, 7.95, 5.64, 4.66, 1.0,
             "候选池变大后，重排能否把精度补回来——如果补不回来，"
             "召回涨了 EM 也不会涨。", size=15.5, color=INK, line=1.32)

    foot(s, 3, "示意图；实现细节见代码仓库，重排器结构与 Dense+CE 相同")
    notes(s, "1 分钟。先指上面一行：基线的链路。再指下面：我们加的是改写、多路检索、合并，"
             "重排器和深度完全一样（虚线标出来），所以两组差异只来自前半段。"
             "如果被问为什么子查询能帮上忙：多跳的第二跳依赖第一跳才出现的中间实体。")
    return s


# ================================================================ 4 main table
MAIN = [
    ("HotpotQA", "BM25", 62.3, 0.0, 41.8, 0.4, 54.6, 0.5),
    ("HotpotQA", "Dense", 68.9, 0.3, 45.2, 0.5, 58.1, 0.4),
    ("HotpotQA", "Dense+CE", 74.6, 0.4, 48.7, 0.3, 61.9, 0.4),
    ("HotpotQA", "QR+CE", 79.1, 0.5, 51.3, 0.4, 64.8, 0.5),
    ("2Wiki", "BM25", 58.7, 0.0, 33.5, 0.6, 40.2, 0.5),
    ("2Wiki", "Dense", 64.1, 0.4, 36.9, 0.5, 43.8, 0.6),
    ("2Wiki", "Dense+CE", 73.2, 0.5, 41.4, 0.4, 48.9, 0.5),
    ("2Wiki", "QR+CE", 78.4, 0.4, 44.6, 0.5, 52.3, 0.4),
    ("MuSiQue", "BM25", 38.4, 0.0, 17.9, 0.5, 26.3, 0.6),
    ("MuSiQue", "Dense", 44.6, 0.5, 21.3, 0.6, 30.5, 0.7),
    ("MuSiQue", "Dense+CE", 51.8, 0.7, 25.1, 0.8, 34.9, 0.8),
    ("MuSiQue", "QR+CE", 52.9, 0.9, 25.7, 0.7, 35.6, 0.9),
]
DS_LABEL = {"HotpotQA": "HotpotQA\n(distractor)", "2Wiki": "2Wiki\nMultihopQA",
            "MuSiQue": "MuSiQue"}


def _pm(m, s):
    return f"{m:.1f} ± {s:.1f}"


def slide_results(prs):
    s = blank(prs)
    add_rect(s, 0, 0, W, H, fill=BG)
    head(s, "03 · 主结果", "两个数据集稳定提升，MuSiQue 基本持平", size=28)

    rows = [["数据集", "方法", "Recall@5 ↑", "EM ↑", "F1 ↑"]]
    bold_rows, muted_rows = [], []
    for i, r in enumerate(MAIN, start=1):
        rows.append([DS_LABEL[r[0]] if r[1] == "BM25" else "",
                     r[1], _pm(r[2], r[3]), _pm(r[4], r[5]), _pm(r[6], r[7])])
        if r[1] == "QR+CE":
            bold_rows.append(i)
        if r[1] in ("BM25", "Dense"):
            muted_rows.append(i)

    col_w = [1.42, 1.72, 1.72, 1.46, 1.46]
    row_h = [0.40] + [0.315] * 12
    gf = add_table(s, LEFT, 1.80, col_w, row_h, rows, font=15.5,
                   header_font=13.5, header_fill=SURFACE,
                   aligns=[PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.RIGHT,
                           PP_ALIGN.RIGHT, PP_ALIGN.RIGHT],
                   bold_rows=bold_rows, muted_rows=muted_rows, line=1.05,
                   margins=(0.10, 0.10, 0.02, 0.02))
    tbl = gf.table
    for start, end in ((1, 4), (5, 8), (9, 12)):
        tbl.cell(start, 0).merge(tbl.cell(end, 0))
    for r in range(len(rows)):
        for c in range(5):
            cell_border(tbl.cell(r, c), "B", color=RULE if r == 0 else "DCE7E2",
                        lw=0.9 if r == 0 else 0.6)

    # right observations
    ox, ow = 8.72, 3.89
    label(s, ox, 1.80, ow, "相对 Dense+CE 的变化")
    blocks = [
        ("HotpotQA", "R@5 +4.5　EM +2.6", "3 个种子都稳定（SD ≤ 0.5），F1 +2.9", ACCENT),
        ("2Wiki", "R@5 +5.2　EM +3.2", "3 个种子都稳定（SD ≤ 0.5），F1 +3.4", ACCENT),
        ("MuSiQue", "R@5 +1.1　EM +0.6", "种子间 SD 在 0.7–0.9，提升与波动同量级",
         SECOND),
    ]
    y = 2.18
    for name, delta, note, col in blocks:
        add_text(s, ox, y, ow, 0.3, name, size=15.5, color=INK, bold=True)
        add_text(s, ox, y + 0.30, ow, 0.4, delta, size=20, color=col, bold=True)
        add_text(s, ox, y + 0.72, ow, 0.6, note, size=13, color=MUTED, line=1.25)
        y += 1.42

    add_line(s, ox, 6.10, RIGHT, 6.10, color=RULE, lw=0.8)
    add_text(s, ox, 6.22, ow, 0.6,
             "四个方法在两个增益大的数据集上名次一致；MuSiQue 上整体低约 25 点。",
             size=12.5, color=MUTED, line=1.25)

    foot(s, 4, "来源：data/main_results.csv；mean ± SD，n = 3 seeds；数值为 %")
    notes(s, "1 分 20 秒。先读列：Recall@5 和 EM，都是越高越好。再看 QR+CE 那一行（加粗）与"
             "同数据集 Dense+CE 的差。HotpotQA +4.5、2Wiki +5.2，EM 也分别 +2.6 / +3.2，"
             "三个种子方向一致。MuSiQue 只 +1.1，而它的 SD 是 0.7 和 0.9，所以这页先不给结论，下一页单独看。"
             "如果被问 F1：趋势一致，表里保留着。")
    return s


# ============================================================== 5 MuSiQue
def slide_musique(prs):
    s = blank(prs)
    add_rect(s, 0, 0, W, H, fill=BG)
    head(s, "04 · 不确定的地方", "MuSiQue 的 +1.1 点，和种子之间的波动一样大", size=27)

    s.shapes.add_picture(os.path.join(CHARTS, "musique.png"),
                         Inches(LEFT), Inches(1.98), width=Inches(7.6))

    ox, ow = 8.72, 3.89
    label(s, ox, 1.86, ow, "怎么读这张图")
    add_text(s, ox, 2.16, ow, 1.0,
             "点位置是 3 个种子的均值，横线是 ±SD。两个方法的误差区间大幅重叠。",
             size=15, color=INK, line=1.3)

    label(s, ox, 3.18, ow, "现在能说")
    add_text(s, ox, 3.46, ow, 0.9,
             [{"runs": [("在 MuSiQue 上", {}), ("没有观察到", {"bold": True}),
                        ("明确提升。", {})], "size": 15}],
             size=15, color=INK, line=1.3)

    label(s, ox, 4.10, ow, "现在不能说")
    add_text(s, ox, 4.38, ow, 1.1,
             "不能说 QR+CE 在 MuSiQue 上无效，也不能说它有效——样本不够。",
             size=15, color=INK, line=1.3)

    add_rect(s, ox, 5.44, ow, 1.18, fill=SURFACE, line=None, radius=0.06)
    add_text(s, ox + 0.18, 5.56, ow - 0.36, 0.9,
             "所以这周先把 MuSiQue 记成“未解决”，去查原因（第 8 页），不继续调参。",
             size=13.5, color=MUTED, line=1.28)

    foot(s, 5, "来源：data/main_results.csv，MuSiQue，3 seeds；横轴已截取到数据附近，不是从 0 起")
    notes(s, "1 分钟。这页是我最想让老师看的一页：+1.1 的差，和 ±0.7 / ±0.9 的种子波动同量级，"
             "所以我把它写成“未解决”，不当成有效。注意横轴是为了看清区间才截取的，"
             "点图不是柱状图，截轴不改变数值。下一步不是继续调，而是查原因。")
    return s


# ================================================================== 6 ablation
ABL = [
    ("QR+CE（完整；depth 50）", 78.4, 0.4, 44.6, 0.5, "96", "—", "—"),
    ("去掉查询改写", 73.9, 0.5, 41.8, 0.4, "95", "−4.5", "−2.8"),
    ("去掉难负例", 76.6, 0.6, 43.5, 0.5, "96", "−1.8", "−1.1"),
    ("重排深度 20", 75.8, 0.5, 42.9, 0.6, "41", "−2.6", "−1.7"),
    ("重排深度 100", 78.6, 0.4, 44.7, 0.5, "189", "+0.2", "+0.1"),
]


def slide_ablation(prs):
    s = blank(prs)
    add_rect(s, 0, 0, W, H, fill=BG)
    head(s, "05 · 消融", "增益主要来自改写；重排深度 50 之后没有额外收益", size=27)

    rows = [["设置", "Recall@5 ↑", "Δ R@5", "EM ↑", "Δ EM", "重排 ↓ (ms)"]]
    for name, rm, rs, em, es, ms, dr, de in ABL:
        rows.append([name, _pm(rm, rs), dr, _pm(em, es), de, ms])
    col_w = [2.90, 1.52, 0.92, 1.38, 0.92, 1.44]
    gf = add_table(s, LEFT, 1.86, col_w, [0.42] + [0.56] * 5, rows, font=15.5,
                   header_font=13.5, header_fill=SURFACE,
                   aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT,
                           PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT],
                   bold_rows=(1,), line=1.05,
                   margins=(0.10, 0.10, 0.04, 0.04))
    tbl = gf.table
    for r in range(len(rows)):
        for c in range(6):
            cell_border(tbl.cell(r, c), "B", color=RULE if r == 0 else "DCE7E2",
                        lw=0.9 if r == 0 else 0.6)
    add_text(s, LEFT, 5.30, 9.3, 0.3,
             "Δ 均为相对完整模型的差值；误差为 3 个种子的 SD。", size=12.5,
             color=MUTED)

    add_text(s, LEFT, 5.72, 9.3, 1.1,
             "去掉改写掉 4.5 点，是四项里最大的——增益不是靠重排器换训练数据得来的。"
             "depth 20 掉 2.6，depth 100 只多 0.2 但重排时间翻倍，所以后面固定 50。",
             size=15.5, color=INK, line=1.32)

    add_rect(s, 10.12, 1.86, 2.49, 2.96, fill=SURFACE, line=None, radius=0.05)
    add_text(s, 10.28, 2.00, 2.15, 0.26, "下一步取这个点", size=11.5, color=MUTED,
             bold=True)
    add_text(s, 10.28, 2.28, 2.15, 0.6, "depth = 50", size=24, color=ACCENT,
             bold=True)
    add_text(s, 10.28, 2.92, 2.15, 1.7,
             "重排 96 ms\n\n占比不到总延迟的 1/4，砍它省不了多少；但 100 也没换来精度。",
             size=12.5, color=MUTED, line=1.3)

    foot(s, 6, "来源：data/ablation.csv；2WikiMultihopQA，3 seeds；Δ 相对完整模型")
    notes(s, "50 秒。消融只在 2Wiki 上做。三句话：改写贡献最大（−4.5）；难负例值 1.8 个点，"
             "说明重排器重训这一步不能省；depth 从 50 加到 100 只多 0.2 个点却多花 93 ms，"
             "所以后面固定 50，也省掉一半重排时间。注意 depth 20 掉 2.6，别为了快砍太多。")
    return s


# ============================================================== 7 train curve
def slide_train(prs):
    s = blank(prs)
    add_rect(s, 0, 0, W, H, fill=BG)
    head(s, "06 · 重排器训练", "难负例前期更慢，6k 步之后才显出作用", size=27)

    s.shapes.add_picture(os.path.join(CHARTS, "train.png"),
                         Inches(LEFT), Inches(2.02), width=Inches(7.9))

    ox, ow = 8.86, 3.75
    label(s, ox, 1.90, ow, "读图顺序")
    add_text(s, ox, 2.18, ow, 1.0,
             "先看浅色线：无难负例在 3k 步就到 73.2，比深色线快得多。",
             size=15, color=INK, line=1.3)

    label(s, ox, 3.06, ow, "但 6k 之后就停了")
    add_text(s, ox, 3.34, ow, 0.9,
             "6k 之后只多 0.8 点，基本平了。",
             size=15, color=INK, line=1.3)

    label(s, ox, 4.06, ow, "有难负例的还在涨")
    add_text(s, ox, 4.34, ow, 1.2,
             "一直涨到 12k 附近，15k 时 77.9 对 76.5，反超 1.4 点。",
             size=15, color=INK, line=1.3)

    add_rect(s, ox, 5.36, ow, 1.26, fill=SURFACE, line=None, radius=0.06)
    add_text(s, ox + 0.18, 5.48, ow - 0.36, 1.0,
             "和消融里“去掉难负例 −1.8”量级一致，所以难负例保留；"
             "代价是训练更慢，要多跑约一倍步数。", size=13, color=MUTED, line=1.28)

    foot(s, 7, "来源：data/train_curve.csv；纵轴为训练期间的 dev Recall@5，横轴为步数")
    notes(s, "50 秒。这条曲线有个反直觉的地方先讲清楚：前 3k 步，不用难负例反而更好，"
             "训练也更快收敛；但 6k 之后它平了，用难负例的一直涨到 12k。"
             "这也解释了消融里那 1.8 个点从哪来。代价是训练预算大约翻倍。")
    return s


# ================================================================= 8 errors
def slide_errors(prs):
    s = blank(prs)
    add_rect(s, 0, 0, W, H, fill=BG)
    head(s, "07 · 错例分析", "最大的一类错误是：桥接实体根本没进候选", size=27)

    s.shapes.add_picture(os.path.join(CHARTS, "errors.png"),
                         Inches(LEFT), Inches(2.02), width=Inches(6.5))

    ox, ow = 7.52, 5.09
    label(s, ox, 1.86, ow, "这类错误长什么样")
    # mini chain
    bx, by, bw, bh = ox, 2.14, 1.40, 0.84
    b1 = add_rect(s, bx, by, bw, bh, fill=SURFACE, line=PALE, radius=0.08)
    box_text(b1, "子查询 1\n“A 的导演”", size=12.5, line=1.15)
    b2 = add_rect(s, bx + 1.72, by, 1.16, bh, fill="DDF0E8", line=ACCENT, lw=1.3,
                  radius=0.08)
    box_text(b2, "中间实体 B", size=12.5, color=ACCENT, bold=True, line=1.1)
    b3 = add_rect(s, bx + 3.20, by, 1.55, bh, fill=SURFACE, line=PALE, radius=0.08)
    box_text(b3, "子查询 2\n“B 的出生地”", size=12.5, line=1.15)
    add_arrow(s, bx + 1.44, by + bh / 2, bx + 1.68, by + bh / 2, color=SECOND)
    add_arrow(s, bx + 2.92, by + bh / 2, bx + 3.16, by + bh / 2, color=SECOND)
    add_text(s, ox, 3.02, ow, 0.52,
             "B 要先读第一跳的文档才知道，一次性改写拿不到它。",
             size=12.5, color=MUTED, line=1.22)

    label(s, ox, 3.66, ow, "我的理解（待验证）")
    add_text(s, ox, 3.94, ow, 1.0,
             "MuSiQue 多是 3–4 跳，一次性改写拿不到中间实体，这可能是它上面提升小的主因。",
             size=15, color=INK, line=1.3)

    label(s, ox, 5.06, ow, "不属于检索的部分")
    add_text(s, ox, 5.34, ow, 0.8,
             "比较类 14 条证据都检索到了，错在生成阶段；标注噪声 7 条不算方法的错。",
             size=15, color=INK, line=1.3)
    add_text(s, ox, 6.16, ow, 0.6,
             "→ 所以下一步只改改写方式（第 11 页），不动生成侧。", size=13,
             color=ACCENT, bold=True, line=1.25)

    foot(s, 8, "来源：data/error_types.csv；人工检查 60 条 MuSiQue 答错样本，单标注")
    notes(s, "1 分钟。60 条错例我人工分了一遍，最大的一类是桥接实体没被检索到，23 条。"
             "原因我个人判断是：改写是一次性的，而中间实体必须先读第一跳文档才出现，"
             "所以子查询里根本没有它。这个解释和数据一致，但还没被实验验证——"
             "验证办法就是迭代式改写。另外 14 条是比较类，证据都检到了，是生成错，不属于这次的范围。"
             "如果被问标注可靠性：单标注，没有第二个人复核，这也是个限制。")
    return s


# ================================================================ 9 latency
def slide_latency(prs):
    s = blank(prs)
    add_rect(s, 0, 0, W, H, fill=BG)
    head(s, "08 · 代价", "召回换来的代价是 3.4 倍延迟，主要在改写", size=28)

    s.shapes.add_picture(os.path.join(CHARTS, "latency.png"),
                         Inches(LEFT), Inches(2.10), width=Inches(7.55))

    ox, ow = 8.62, 3.99
    label(s, ox, 1.92, ow, "拆开看")
    add_text(s, ox, 2.20, ow, 1.2,
             "改写 245 ms，占了总延迟的六成；多路检索 71 ms（单路 25 ms）；"
             "重排 96 ms 两边一样。", size=15, color=INK, line=1.3)

    label(s, ox, 3.42, ow, "能省的地方")
    add_text(s, ox, 3.70, ow, 1.4,
             "depth 从 100 回到 50 已经省了 93 ms；再往下要靠改写模型蒸馏或子查询缓存。",
             size=15, color=INK, line=1.3)

    add_rect(s, ox, 4.96, ow, 1.58, fill=SURFACE, line=None, radius=0.05)
    add_text(s, ox + 0.18, 5.08, ow - 0.36, 0.3, "需要一起定的事", size=11.5,
             color=MUTED, bold=True)
    add_text(s, ox + 0.18, 5.36, ow - 0.36, 1.05,
             "3.4× 在目标场景能不能接受？如果场景是离线建库，这不是问题；"
             "如果是在线问答，得先有延迟预算。", size=13, color=INK, line=1.28)

    foot(s, 9, "来源：data/latency.csv；单条查询，端到端，不含生成；各段为单次测量")
    notes(s, "50 秒。延迟大头是改写模型（245 ms），不是检索也不是重排。重排 96 ms 两个方法一样，"
             "所以 3.4 倍不是重排造成的。depth 50 已经帮我们省了 93 ms。"
             "剩下的选择是蒸馏改写模型或者缓存子查询，这取决于场景要不要在线跑。")
    return s


# ============================================================== 10 conclusions
def slide_conclusion(prs):
    s = blank(prs)
    add_rect(s, 0, 0, W, H, fill=BG)
    head(s, "09 · 小结", "这一轮能下的结论，和还不能下的", size=28)

    lx, lw = LEFT, 5.9
    add_text(s, lx, 1.86, lw, 0.3, "能下的", size=13, color=ACCENT, bold=True)
    can = [
        ("有效且稳定", "HotpotQA / 2Wiki 上 R@5 +4.5 / +5.2，EM +2.6 / +3.2，3 个种子都稳定"),
        ("增益来自改写", "去掉改写掉 4.5 点，是四项消融里最大的；难负例次之（1.8）"),
        ("深度固定 50", "50 → 100 只多 0.2 点，重排时间翻倍；20 则掉 2.6"),
    ]
    y = 2.24
    for t, d in can:
        add_text(s, lx, y, lw, 0.3, t, size=17, color=INK, bold=True)
        add_text(s, lx, y + 0.34, lw, 0.8, d, size=14.5, color=MUTED, line=1.3)
        y += 1.40

    rx = 6.86
    add_text(s, rx, 1.86, 5.75, 0.3, "还不能下的", size=13, color=SECOND, bold=True)
    cant = [
        ("MuSiQue 上是否有效", "Δ 1.1 与种子 SD 同量级，需更多种子或换写法"),
        ("3.4× 延迟能否接受", "取决于在线/离线场景，目前没有延迟预算"),
        ("比较类错误谁负责", "14/60 属生成阶段，本轮没有改动，不能算检索的锅"),
    ]
    y = 2.24
    for t, d in cant:
        add_text(s, rx, y, 5.75, 0.3, t, size=17, color=INK, bold=True)
        add_text(s, rx, y + 0.34, 5.75, 0.8, d, size=14.5, color=MUTED, line=1.3)
        y += 1.40

    for yy in (3.46, 4.86):
        add_line(s, LEFT, yy, RIGHT, yy, color="DCE7E2", lw=0.7)
    add_line(s, LEFT, 6.14, RIGHT, 6.14, color=RULE, lw=0.9)
    add_text(s, LEFT, 6.30, CW, 0.4,
             "如果迭代改写能把桥接类错误降下来，就继续投入；否则回到改写质量本身。",
             size=17, color=INK, line=1.3)

    foot(s, 10, "")
    notes(s, "40 秒。左边三条是有数据支撑的；右边三条是我认为现在还不能写进论文的部分。"
             "特别想强调 MuSiQue 那条：不是效果差，是样本不够分辨，所以下一步要换方法而不是调参。")
    return s


# ============================================================== 11 discussion
def slide_discussion(prs):
    s = blank(prs)
    add_rect(s, 0, 0, W, H, fill=BG)
    head(s, "10 · 讨论", "三个需要定的事，和下两周的计划", size=28)

    rows = [
        ["待定问题", "可选做法", "代价 / 判别信号"],
        ["MuSiQue 要不要改\n迭代式改写？",
         "读完第一跳再改写第二跳，只在 MuSiQue 上做最小验证",
         "延迟可能 >700 ms；看桥接类错误是否明显减少"],
        ["3.4× 延迟能否\n接受？",
         "先测改写模型蒸馏、子查询缓存；或明确只做离线",
         "取决于场景的延迟预算，需要老师给个量级"],
        ["比较类 14 条\n要不要管？",
         "本轮不动，交给生成侧；只在论文里作为限制说明",
         "与检索主线无关，改了也不影响 R@5"],
    ]
    gf = add_table(s, LEFT, 1.86, [2.02, 3.40, 3.24],
                   [0.44, 1.16, 1.16, 1.16], rows, font=14, header_font=13,
                   header_fill=SURFACE,
                   aligns=[PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.LEFT],
                   line=1.26, margins=(0.12, 0.12, 0.06, 0.06),
                   valign=MSO_ANCHOR.TOP)
    tbl = gf.table
    for r in range(len(rows)):
        for c in range(3):
            cell_border(tbl.cell(r, c), "B", color=RULE if r == 0 else "DCE7E2",
                        lw=0.9 if r == 0 else 0.6)

    ox, ow = 9.68, 2.93
    add_text(s, ox, 1.90, ow, 0.3, "下两周（按依赖排）", size=12.5, color=MUTED,
             bold=True)
    plan = [
        ("1", "迭代式改写最小版，只在 MuSiQue 上验证"),
        ("2", "depth 固定 50，重测端到端延迟"),
        ("3", "改写加“限定条件保留”检查，压改造写漂移（11 条）"),
    ]
    y = 2.24
    for num, txt in plan:
        add_text(s, ox, y, 0.26, 0.3, num, size=13, color=ACCENT, bold=True)
        add_text(s, ox + 0.28, y - 0.02, ow - 0.28, 0.9, txt, size=13.5,
                 color=INK, line=1.26)
        y += 1.05

    add_line(s, ox, 5.36, RIGHT, 5.36, color=RULE, lw=0.8)
    add_text(s, ox, 5.48, ow, 1.0,
             "先做最小版本：如果桥接类错误没降，就不投入蒸馏和缓存。",
             size=13, color=ACCENT, bold=True, line=1.28)

    foot(s, 11, "计划基于第 8 页的错误类型；未定资源与截止时间")
    notes(s, "1 分钟，收尾。三个问题想请老师定：MuSiQue 要不要上迭代式改写（代价是更慢）；"
             "3.4 倍延迟在场景里能不能接受；比较类那 14 条要不要现在管。"
             "我的倾向是：先做迭代改写的最小版本，用它来判断桥接错误能不能降下来，"
             "降不下来就不再投入蒸馏，回头做改写质量。")
    return s


def main():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    slide_cover(prs)
    slide_work(prs)
    slide_method(prs)
    slide_results(prs)
    slide_musique(prs)
    slide_ablation(prs)
    slide_train(prs)
    slide_errors(prs)
    slide_latency(prs)
    slide_conclusion(prs)
    slide_discussion(prs)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    prs.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
