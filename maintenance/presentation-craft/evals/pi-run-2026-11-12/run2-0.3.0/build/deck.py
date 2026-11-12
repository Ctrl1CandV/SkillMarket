"""Build the progress deck: out/progress.pptx  (+ approximate preview PNGs).

One layout description, two backends (see kit.py):
  python build/deck.py                     -> out/progress.pptx
  python build/deck.py --preview qa/pv-02  -> PNG preview of the same geometry
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kit import CW, FOOT_Y, ML, MR, SH, SW, PreviewCanvas, PptxCanvas
import data

D = data.load()

BG = "F6FAF8"
TEXT = "183C36"
MUTED = "4B665F"
ACCENT = "166B5B"
SECOND = "657B72"
SURFACE = "E8F1EC"
RULE = "B5CFC4"
LIGHT = "8FB3A6"
MID = "2F8A78"
PALE = "C3D8CE"
GHOST = "DCE8E1"
WHITE = "FFFFFF"
TINT = "EAF3EE"

PAGES = 10
T_TITLE = 26
T_BODY = 16
T_SMALL = 15
T_TAB = 16
T_TABH = 14.5
T_FOOT = 10.5


def xmap(v, v0, v1, x0, x1):
    return x0 + (v - v0) * (x1 - x0) / (v1 - v0)


def head(c, kicker, title):
    c.text(ML, 0.30, CW, 0.26, kicker, size=11.5, bold=True, color=ACCENT)
    c.text(ML, 0.58, CW, 0.55, title, size=T_TITLE, bold=True, color=TEXT, leading=1.18)


def foot(c, page, src=""):
    c.rect(ML, 6.90, CW, 0.01, RULE)
    c.text(ML, FOOT_Y, CW - 1.6, 0.26, src, size=T_FOOT, color=MUTED)
    c.text(SW - MR - 1.2, FOOT_Y, 1.2, 0.26, f"{page} / {PAGES}", size=T_FOOT,
           color=MUTED, align="r")


def label(c, x, y, s, color=ACCENT):
    c.text(x, y, 3.4, 0.24, s, size=11.5, bold=True, color=color)


def panel(c, x, y, w, bullets, step=1.05, size=16, leading=1.45):
    for i, b in enumerate(bullets):
        c.text(x, y + i * step, w, step - 0.06, b, size=size, color=TEXT, leading=leading)


def arrow(c, x1, x2, y):
    c.rect(x1, y - 0.006, x2 - x1 - 0.05, 0.012, LIGHT)
    c.oval(x2 - 0.045, y, 0.033, LIGHT)


# ------------------------------------------------------------------ slides
def s01_cover(c):
    c.new_slide(BG)
    c.text(ML, 0.62, 8.0, 0.28, "研究生组会 · 进展汇报", size=12, bold=True, color=ACCENT)
    c.rect(ML, 1.30, 0.075, 2.10, ACCENT)
    c.text(ML + 0.32, 1.30, 10.3, 2.10, "查询改写 + 交叉编码器重排\n多跳 RAG 的两周实验进展",
           size=36, bold=True, color=TEXT, leading=1.24)
    c.rect(ML, 3.78, 11.90, 0.012, RULE)
    c.text(ML, 4.06, 11.4, 1.1,
           "HotpotQA、2Wiki 上 Recall@5 比 Dense+CE 高 4.5 / 5.2 点，三个种子方向一致；\n"
           "MuSiQue 只高 1.1 点，与种子波动同量级——暂时不能算有效。",
           size=17.5, color=TEXT, leading=1.55)
    label(c, ML, 5.42, "内容")
    c.text(1.30, 5.39, 10.7, 0.32,
           "方法　→　主结果　→　延迟　→　消融与训练诊断　→　错例　→　讨论",
           size=T_SMALL, color=MUTED)
    c.text(ML, 6.52, 11.9, 0.30,
           "实验周期 2026-10-29 – 11-11　|　汇报 2026-11-17　|　3 数据集 × 3 seeds，数据见 data/*.csv",
           size=11.5, color=MUTED)
    c.set_notes(
        "开场（约 20 秒）：这两周按上次定的方向把「查询改写 + 交叉编码器重排」做出来了，"
        "也在三个数据集上跑完 3 seeds。先说结论：两个数据集上确实有效，第三个数据集上还不敢说；"
        "代价是延迟 3.4 倍。最后想请老师定方向。")


def s02_work(c):
    c.new_slide(BG)
    head(c, "本轮做了什么", "两周五件事：基线、方法、主结果、消融、错例")
    c.text(ML, 1.24, CW, 0.60,
           "上次组会定的方向是「查询改写 + 交叉编码器重排」。本轮要回答：召回真的提上来了吗？"
           "代价多大？在哪个数据集上不管用？",
           size=T_SMALL, color=MUTED, leading=1.4)
    c.rect(ML, 1.98, CW, 0.01, RULE)

    rows = [
        ("复现三个基线", "BM25 / Dense / Dense+CE，同语料、同交叉编码器结构"),
        ("实现 QR+CE", "改写 → 多路检索合并 → 难负例重训的重排；3 数据集 × 3 seeds"),
        ("四项消融", "去改写 / 去难负例 / 重排深度 20·50·100（在 2Wiki 上做）"),
        ("延迟分项计时", "把 3.4 倍拆成改写、检索、重排三块，看钱花在哪"),
        ("60 条错例人工判读", "MuSiQue 答错的样本分类，给出下一步假设"),
    ]
    y = 2.12
    for i, (a, b) in enumerate(rows):
        c.text(ML, y + 0.16, 0.42, 0.34, f"{i+1}", size=15, bold=True, color=ACCENT)
        c.text(1.12, y + 0.14, 3.70, 0.38, a, size=16.5, bold=True, color=TEXT)
        c.text(4.95, y + 0.17, 7.75, 0.34, b, size=16, color=MUTED)
        if i < len(rows) - 1:
            c.rect(ML, y + 0.74, CW, 0.009, RULE)
        y += 0.78

    c.rect(ML, 6.06, CW, 0.58, SURFACE)
    c.text(ML + 0.18, 6.06, CW - 0.36, 0.58,
           "一句话：两个数据集上有效，第三个数据集上证据不足；代价是 3.4 倍延迟。",
           size=16.5, bold=True, color=TEXT, anchor="m")
    foot(c, 2, "全部在 3 seeds 下跑完，没有未完成的对照")
    c.set_notes(
        "（约 1 分钟）五件事按依赖顺序讲：先有基线，再有自己的方法，然后主结果、消融、错例。"
        "重点不在工作量，而在最后一句：有效的地方很稳，不稳的地方我直接标出来。")


def _block(c, x, y, w, h, s, hot=False, size=16):
    c.rect(x, y, w, h, ACCENT if hot else SURFACE, radius=0.06)
    c.text(x + 0.08, y, w - 0.16, h, s, size=size, bold=hot, anchor="m", align="c",
           color=WHITE if hot else TEXT, leading=1.25)


def s03_method(c):
    c.new_slide(BG)
    head(c, "方法", "QR+CE 把改写放在检索之前：查询变了，候选池才会变大")

    yA, hA = 1.86, 0.80
    c.text(ML, yA, 1.55, hA, "Dense+CE", size=14.5, bold=True, color=SECOND, anchor="m")
    x = 2.30
    seqA = [(1.00, "问题"), (1.95, "稠密检索\ntop-20"),
            (2.00, "交叉编码器重排\ndepth 50"), (1.50, "top-5 证据"), (1.00, "生成")]
    for i, (w, s) in enumerate(seqA):
        _block(c, x, yA, w, hA, s)
        if i < len(seqA) - 1:
            arrow(c, x + w + 0.06, x + w + 0.28, yA + hA / 2)
        x += w + 0.34

    yB, hB = 3.22, 0.86
    c.text(ML, yB, 1.62, hB, "QR+CE\n（本轮）", size=14.5, bold=True, color=ACCENT,
           anchor="m", leading=1.15)
    x = 2.30
    seqB = [(1.00, "问题", False), (2.05, "改写成 2–3 个\n子查询", True),
            (2.15, "多路检索\n合并候选", True), (1.80, "交叉编码器重排\ndepth 50", False),
            (1.35, "top-5 证据", False)]
    for i, (w, s, hot) in enumerate(seqB):
        _block(c, x, yB, w, hB, s, hot=hot)
        if i < len(seqB) - 1:
            arrow(c, x + w + 0.06, x + w + 0.24, yB + hB / 2)
        x += w + 0.30
    c.text(x + 0.06, yB, 0.80, hB, "生成\n（未改）", size=12, color=MUTED,
           anchor="m", leading=1.2, align="c")

    c.rect(2.30, 4.48, 8.10, 0.012, RULE)
    label(c, ML, 4.62, "为什么可能有效")
    c.text(ML, 4.88, 5.45, 1.7,
           "第二跳的实体很少出现在原问题的检索结果里；拆成子查询后，候选池才覆盖到它。"
           "这是假设，本轮只验证了「有它和没它差多少」。",
           size=16, color=TEXT, leading=1.5)
    c.rect(6.42, 4.56, 0.01, 1.95, RULE)
    label(c, 6.72, 4.62, "改动范围与代价")
    c.text(6.72, 4.88, 5.95, 1.7,
           "只改检索侧：生成器、CE 结构、重排深度都不变，差异可归因到检索。\n"
           "代价：每问多 1 次小模型推理和 2–3 次检索。",
           size=16, color=TEXT, leading=1.5)
    foot(c, 3, "「top-20」是送入重排的候选数；depth 50 指截断到 50 条再重排")
    c.set_notes(
        "（约 1.5 分钟）先看上面一条：原来的做法是问题直接检索、再重排。"
        "我们改的是检索前一步：先用小模型把问题拆成 2–3 个子查询，各自检索后合并候选，再统一重排。"
        "深色的两块就是新增部分。强调一点：生成器和重排结构没动，所以主结果的差别只能是检索带来的。")


def s04_main(c):
    c.new_slide(BG)
    head(c, "主结果", "HotpotQA、2Wiki 提升 4.5–5.2 点；MuSiQue 只涨 1.1")

    label(c, ML, 1.62, "设置")
    c.text(ML, 1.92, 2.42, 3.5,
           "数据\nHotpotQA（distractor）\n2Wiki、MuSiQue\n\n"
           "种子\n3 个种子，表内均值\n（括号内 SD）\n\n"
           "指标\nRecall@5 ↑、EM ↑\n\n"
           "控制\n同语料、同重排深度 50\n粗体 = 该列最好值",
           size=14.5, color=TEXT, leading=1.3)

    m = D["m"]
    hdr1 = ["", "HotpotQA", "", "2Wiki", "", "MuSiQue", ""]
    hdr2 = ["方法", "R@5 ↑", "EM ↑", "R@5 ↑", "EM ↑", "R@5 ↑", "EM ↑"]
    rows = [hdr1, hdr2]
    for meth in D["methods"]:
        row = [meth]
        for ds in D["datasets"]:
            r = m[(ds, meth)]
            row += [f"{r['recall_at_5_mean']:.1f} ({r['recall_at_5_std']:.1f})",
                    f"{r['em_mean']:.1f} ({r['em_std']:.1f})"]
        rows.append(row)
    fills = {(0, j): SURFACE for j in range(7)}
    fills.update({(5, j): TINT for j in range(7)})
    c.table(3.24, 1.80, [2.05, 1.33, 1.20, 1.33, 1.20, 1.33, 1.20], rows,
            [0.36, 0.34, 0.50, 0.50, 0.50, 0.50], header_rows=2,
            size=T_TAB, header_size=T_TABH, header_fill=BG,
            aligns=["l", "c", "c", "c", "c", "c", "c"],
            cell_fills=fills, bold_cells={(5, j) for j in range(7)},
            spans=[(0, 1, 2), (0, 3, 2), (0, 5, 2)])

    c.rect(3.24, 4.60, 9.44, 0.012, RULE)
    c.text(3.24, 4.74, 9.44, 2.0,
           "· QR+CE 在三个数据集、两个指标上都最高；相对 Dense+CE：R@5 +4.5 / +5.2 / +1.1，"
           "EM +2.6 / +3.2 / +0.6。\n"
           "· 差距的解读：HotpotQA、2Wiki 远超 SD（≤0.5）；MuSiQue 的 1.1 点与 SD（0.7–0.9）"
           "同量级，下一页单独看。",
           size=T_BODY, color=TEXT, leading=1.5, space_after=8)
    foot(c, 4, "数据：data/main_results.csv（n_seeds=3）")
    c.set_notes(
        "（约 1.5 分钟）读法：横向比同一数据集里的方法，纵向比数据集。"
        "两个数据集上提升 4.5 和 5.2 点，EM 也涨了 2.6 和 3.2 点，三个种子方向一致。"
        "MuSiQue 只有 1.1 点，先别当结论，下一页说明为什么。")


def s05_uncertainty(c):
    c.new_slide(BG)
    head(c, "不确定性", "MuSiQue 的 +1.1 点没有走出种子噪声，另外两个走出来了")

    ax0, ax1 = 2.52, 6.88
    v0, v1 = 0.0, 6.0
    rows = [("HotpotQA", 2.60), ("2Wiki", 3.62), ("MuSiQue", 4.64)]
    m = D["m"]

    c.rect(ax0, 2.22, 0.012, 2.86, MUTED)
    for i in range(7):
        xx = xmap(i, v0, v1, ax0, ax1)
        if i:
            c.rect(xx, 2.26, 0.008, 2.80, RULE)
        c.text(xx - 0.28, 5.14, 0.56, 0.26, str(i), size=12.5, color=MUTED, align="c")

    for ds, y in rows:
        a, b = m[(ds, "Dense+CE")], m[(ds, "QR+CE")]
        delta = b["recall_at_5_mean"] - a["recall_at_5_mean"]
        noise = (a["recall_at_5_std"] ** 2 + b["recall_at_5_std"] ** 2) ** 0.5
        c.text(ML, y - 0.20, 1.86, 0.40, ds, size=15, bold=True, color=TEXT,
               align="r", anchor="m")
        xd = xmap(delta, v0, v1, ax0, ax1)
        xl = xmap(delta - noise, v0, v1, ax0, ax1)
        xr = xmap(delta + noise, v0, v1, ax0, ax1)
        c.rect(xl, y - 0.008, max(xr - xl, 0.02), 0.016, SECOND)
        c.rect(xl, y - 0.09, 0.014, 0.18, SECOND)
        c.rect(xr - 0.014, y - 0.09, 0.014, 0.18, SECOND)
        c.oval(xd, y, 0.105, ACCENT)
        c.text(7.02, y - 0.24, 0.90, 0.32, f"+{delta:.1f}", size=16, bold=True, color=TEXT)
        c.text(7.02, y + 0.01, 0.90, 0.26, f"±{noise:.1f}", size=12, color=MUTED)

    c.text(ax0, 5.46, 5.60, 0.26, "Δ Recall@5（QR+CE − Dense+CE），单位：点",
           size=12.5, color=MUTED)

    label(c, 8.36, 1.66, "怎么读")
    panel(c, 8.36, 1.96, 4.34, [
        "· HotpotQA +4.5、2Wiki +5.2：整条灰线都在 0 的右侧，种子同向。",
        "· MuSiQue +1.1：51.8±0.7 vs 52.9±0.9，灰线跨过 0，提升和波动分不开。",
        "· 只有 3 个种子的均值与 SD，没存逐 seed 结果，补不了配对检验。",
    ], step=1.06)

    c.rect(ML, 5.86, CW, 0.012, RULE)
    c.text(ML, 5.98, CW, 0.55,
           "灰线 = 两个方法各自种子 SD 的合成（MuSiQue：0.7 与 0.9 → ±1.1），只作噪声尺度，不是置信区间。",
           size=11.5, color=MUTED)
    foot(c, 5, "数据：data/main_results.csv")
    c.set_notes(
        "（约 1.3 分钟）这张图只回答一个问题：差值跟噪声比有多大。"
        "前两个数据集的差值远离 0；MuSiQue 的 1.1 点和两个方法的 SD 是同一量级，灰线跨过 0。"
        "如果老师问显著性：我没有做配对检验，也没有逐 seed 明细，这一点会说清楚。")


def s06_latency(c):
    c.new_slide(BG)
    head(c, "延迟", "有效的地方慢了 3.4 倍，增量几乎全在改写那一步")

    lat = {r["method"]: r for r in D["latency"]}
    ax0, ax1 = 1.80, 8.05
    vmax = 450
    for i in range(5):
        xx = xmap(i * 100, 0, vmax, ax0, ax1)
        c.rect(xx, 2.06, 0.008, 2.62, RULE)
        c.text(xx - 0.24, 4.76, 0.48, 0.24, str(i * 100), size=12, color=MUTED, align="c")
    c.rect(ax0, 2.06, 0.012, 2.62, MUTED)
    c.text(ax0, 5.04, 6.25, 0.26, "单条查询耗时（ms），按阶段拆分", size=12.5, color=MUTED)

    seg_def = [("retrieve_ms", LIGHT, TEXT), ("rewrite_ms", ACCENT, WHITE),
               ("rerank_ms", SECOND, WHITE)]
    order = ["BM25", "Dense", "Dense+CE", "QR+CE"]
    y = 2.18
    for meth in order:
        r = lat[meth]
        c.text(ML, y - 0.20, 1.05, 0.40, meth, size=16, bold=True, color=TEXT,
               align="r", anchor="m")
        acc = 0
        for key, col, fg in seg_def:
            val = r[key]
            if not val:
                continue
            xa = xmap(acc, 0, vmax, ax0, ax1)
            xb = xmap(acc + val, 0, vmax, ax0, ax1)
            c.rect(xa, y, xb - xa, 0.42, col)
            if xb - xa > 0.45:
                c.text(xa, y, xb - xa, 0.42, str(val), size=12.5, color=fg,
                       align="c", anchor="m")
            acc += val
        c.text(xmap(acc, 0, vmax, ax0, ax1) + 0.10, y - 0.04, 1.3, 0.50,
               f"{acc} ms", size=15, bold=True, color=TEXT, anchor="m")
        y += 0.64

    lx = 2.30
    for col, s in [(LIGHT, "检索"), (ACCENT, "改写"), (SECOND, "重排")]:
        c.rect(lx, 1.78, 0.20, 0.13, col)
        c.text(lx + 0.26, 1.72, 0.90, 0.26, s, size=12, color=MUTED)
        lx += 0.98

    c.rect(8.62, 1.70, 0.012, 3.30, RULE)
    c.text(8.90, 1.62, 3.80, 0.85, "3.4×", size=42, bold=True, color=ACCENT)
    c.text(8.90, 2.40, 3.80, 0.30, "412 ms vs 121 ms", size=15, bold=True, color=TEXT)
    c.text(8.90, 2.82, 3.80, 1.9,
           "· 改写 245 ms，占 59%\n· 多路检索 71 ms（2.8 倍）\n· 重排 96 ms，同 Dense+CE",
           size=16, color=TEXT, leading=1.7)
    c.text(8.90, 4.30, 3.80, 0.60, "重排不是矛盾所在", size=14, bold=True, color=ACCENT)

    c.rect(ML, 5.48, CW, 0.012, RULE)
    c.text(ML, 5.62, CW, 0.90,
           "→ 要压延迟，先压改写和它牵出来的多路检索；把重排深度固定成 50（而不是 100）省下的那 93 ms，"
           "在这里只是小头。",
           size=T_BODY, color=TEXT, leading=1.5)
    foot(c, 6, "数据：data/latency.csv（单条查询分项，未含生成）")
    c.set_notes(
        "（约 1 分钟）延迟按阶段拆开：总 412 ms，Dense+CE 是 121 ms，3.4 倍。"
        "多出来的 291 ms 里，245 ms 是改写模型，46 ms 是多路检索。"
        "重排那 96 ms 跟基线一模一样，所以问题不在重排。这也决定了后面优化的方向。")


def s07_ablation(c):
    c.new_slide(BG)
    head(c, "消融", "改写的贡献最大；重排深度 50 就够，100 只多 0.2 点却翻倍")

    label(c, ML, 1.62, "设置")
    c.text(ML, 1.92, 2.44, 3.2,
           "数据\n2Wiki，3 seeds\n其余同主结果\n\n"
           "参照\nQR+CE 完整模型\n（depth=50）\n\n"
           "Δ\n相对完整模型的\nR@5 点数差",
           size=14.5, color=TEXT, leading=1.3)

    rows = [["设置（2Wiki）", "R@5 ↑", "Δ R@5", "EM ↑", "重排 ms"]]
    labels = {
        "QR+CE (full; depth=50)": "QR+CE（完整，depth=50）",
        "w/o query rewrite": "去掉查询改写",
        "w/o hard negatives": "去掉难负例",
        "rerank depth=20": "重排深度 = 20",
        "rerank depth=100": "重排深度 = 100",
    }
    deltas = {"QR+CE (full; depth=50)": "—", "w/o query rewrite": "−4.5",
              "w/o hard negatives": "−1.8", "rerank depth=20": "−2.6",
              "rerank depth=100": "+0.2"}
    for a in D["ablation"]:
        key = a["setting"]
        rows.append([labels.get(key, key), f"{a['r5']:.1f} ({a['r5sd']:.1f})",
                     deltas.get(key, ""), f"{a['em']:.1f} ({a['emsd']:.1f})",
                     str(a["rerank"])])
    c.table(3.30, 1.80, [3.55, 1.42, 1.20, 1.42, 1.55], rows,
            [0.40, 0.48, 0.48, 0.48, 0.48, 0.48], header_rows=1,
            size=T_TAB, header_size=T_TABH, header_fill=SURFACE,
            aligns=["l", "c", "c", "c", "c"], bold_cells={(1, j) for j in range(5)})
    c.text(3.30, 4.70, 9.40, 0.26,
           "括号内为 3 个种子的 SD；「重排 ms」是该配置下单条查询的重排耗时。",
           size=11.5, color=MUTED)
    c.rect(3.30, 5.00, 9.40, 0.012, RULE)
    c.text(3.30, 5.12, 9.40, 1.5,
           "· 去改写掉 4.5 点，四项里最大：收益主要来自「先换查询」，不是重排变强。\n"
           "· 去难负例掉 1.8 点，与训练曲线两条线的终点差（77.9 vs 76.5）量级一致。\n"
           "· 深度 20 少 2.6 点；深度 100 多 0.2 点（SD 内）却翻倍 → 后续固定 50。",
           size=T_BODY, color=TEXT, leading=1.6)
    foot(c, 7, "数据：data/ablation.csv（消融只在 2Wiki 上做，未在其他数据集复核）")
    c.set_notes(
        "（约 1.2 分钟）消融在 2Wiki 上做，就一个目的：拆开看每块贡献。"
        "改写是最主要的（-4.5），难负例 -1.8，重排深度从 50 加到 100 只多 0.2 点但重排时间翻倍，"
        "所以后面统一固定 50。消融没在其他数据集上做，这个限制我写在页脚了。")


def s08_curve(c):
    c.new_slide(BG)
    head(c, "训练诊断", "难负例的收益在 6k 步之后才出现：一条继续涨，一条早早持平")

    ax0, ax1 = 1.45, 7.58
    ay0, ay1 = 2.34, 5.02
    X0, X1 = 0, 15000
    Y0, Y1 = 58, 80

    for v in (60, 65, 70, 75):
        yy = ay1 - (v - Y0) * (ay1 - ay0) / (Y1 - Y0)
        c.rect(ax0, yy, ax1 - ax0, 0.008, RULE)
        c.text(ax0 - 0.58, yy - 0.12, 0.50, 0.24, str(v), size=11.5, color=MUTED, align="r")
    c.rect(ax0, ay1, ax1 - ax0, 0.012, MUTED)
    for v in (0, 3000, 6000, 9000, 12000, 15000):
        xx = xmap(v, X0, X1, ax0, ax1)
        c.text(xx - 0.32, ay1 + 0.10, 0.64, 0.24, f"{v//1000}k" if v else "0",
               size=11.5, color=MUTED, align="c")
    c.text(ax0 - 0.60, 1.94, 2.6, 0.26, "dev Recall@5 ↑", size=11.5, color=MUTED)

    cur = D["curve"]
    x6 = xmap(6000, X0, X1, ax0, ax1)
    c.rect(x6, ay0, 0.008, ay1 - ay0, LIGHT)
    c.text(x6 + 0.12, 2.58, 1.00, 0.26, "6k 后持平", size=11.5, color=MUTED)

    # legend inside the empty top-left area
    for i, (col, name) in enumerate([(ACCENT, "有难负例"), (SECOND, "无难负例")]):
        ly = 2.40 + i * 0.28
        c.rect(1.55, ly + 0.09, 0.34, 0.035, col)
        c.text(1.98, ly, 1.2, 0.24, name, size=11.5, bold=True, color=col)

    for key, col in [("dev_recall5_nohardneg", SECOND), ("dev_recall5_hardneg", ACCENT)]:
        pts = [(xmap(r["step"], X0, X1, ax0, ax1),
                ay1 - (r[key] - Y0) * (ay1 - ay0) / (Y1 - Y0)) for r in cur]
        c.polyline(pts, col, 2.2)
        for px, py in pts:
            c.oval(px, py, 0.042, col)

    c.rect(7.98, 1.70, 0.012, 3.60, RULE)
    label(c, 8.22, 1.66, "怎么读")
    panel(c, 8.22, 1.96, 4.48, [
        "· 无难负例：6k 后停在 75.7–76.5，loss 还在降（0.86 → 0.12）。",
        "· 有难负例：起步慢，12k 追上，15k 到 77.9，还没走平。",
        "· 终点差 1.4 点，与消融的 −1.8 点同量级；无难负例更像在拟合容易的负例。",
    ], step=1.10)

    c.rect(ML, 5.62, CW, 0.012, RULE)
    c.text(ML, 5.74, CW, 0.80,
           "两条曲线各来自一次训练，不是 3 seeds 平均；训练也没跑满，继续训是否还涨，下一步补。",
           size=T_BODY, color=TEXT, leading=1.5)
    foot(c, 8, "数据：data/train_curve.csv（重排器训练过程，dev 集为 2Wiki；横轴为训练步数）")
    c.set_notes(
        "（约 50 秒）这张图解释难负例为什么有用：没有难负例时，6k 步之后 dev 基本不动了，"
        "训练 loss 还在掉，说明在拟合容易的负例；加了难负例，12k 之后还能继续涨。"
        "两条曲线都只有一次训练，所以只看趋势，不当稳定结论。")


def s09_errors(c):
    c.new_slide(BG)
    head(c, "错误分析", "60 条 MuSiQue 错例：38% 卡在桥接实体根本没被检索到")

    lab_map = {
        "bridge entity not retrieved": ("桥接实体没检索到", "检索", ACCENT),
        "comparison question": ("比较类问题做错", "生成", LIGHT),
        "rewrite drift": ("改写漂移", "改写", MID),
        "annotation noise": ("标注噪声", "数据", PALE),
        "other": ("其他", "混合", GHOST),
    }
    total = D["err_total"]
    ax0 = 3.36
    scale = 3.60 / 23.0
    y = 2.04
    for e in D["errors"]:
        name, stage, col = lab_map[e["error_type"]]
        c.text(ML, y - 0.06, 2.56, 0.32, name, size=14.5, bold=True, color=TEXT,
               align="r", anchor="m")
        c.text(ML, y + 0.24, 2.56, 0.24, stage, size=11.5, color=MUTED, align="r")
        w = e["count"] * scale
        c.rect(ax0, y, w, 0.46, col)
        c.text(ax0 + w + 0.14, y - 0.02, 1.20, 0.50,
               f"{e['count']}（{e['count']/total*100:.0f}%）", size=14.5, bold=True,
               color=TEXT, anchor="m")
        y += 0.72

    c.rect(8.42, 1.70, 0.012, 3.55, RULE)
    label(c, 8.66, 1.66, "怎么读")
    panel(c, 8.66, 1.96, 4.05, [
        "· 桥接 + 漂移 34 条（57%）发生在检索之前：问题拆错，重排也救不回。",
        "· 比较类 14 条证据都齐了，错在生成，不属检索侧。",
        "· 标注噪声 7 条：召回上界本身有约 10% 不确定。",
    ], step=1.06)

    c.rect(ML, 5.62, CW, 0.64, SURFACE)
    c.text(ML + 0.16, 5.62, 11.10, 0.64,
           "我的判断（待验证）：3–4 跳上一次性改写拿不到中间实体，这是 MuSiQue 提升小的主因。",
           size=16, color=TEXT, anchor="m")
    foot(c, 9, "数据：data/error_types.csv（人工判读 60 条 MuSiQue 答错样本，单次判读）")
    c.set_notes(
        "（约 1.2 分钟）60 条错例逐条看过。最大一类是桥接实体没被检索到，23 条；"
        "加上改写把限定条件丢掉的 11 条，一共 34 条是检索前就错了。"
        "比较类 14 条证据其实都检索到了，是生成比错了，所以我不打算这次动它。"
        "这也解释了 MuSiQue 为什么提升小——我们的假设是，一次性改写拿不到中间实体。")


def s10_discuss(c):
    c.new_slide(BG)
    head(c, "讨论", "三件需要定的事，和接下来两周的最小实验")

    lx, lw = ML, 5.55
    items = [
        ("① MuSiQue 上要不要换成迭代式改写（读完第一跳再改第二跳）？",
         "先做最小版本，只放 MuSiQue；延迟预计 700 ms 以上。"),
        ("② 3.4 倍延迟在我们的场景里能不能接受？",
         "这条得您定；不接受就先试蒸馏或缓存改写器。"),
        ("③ 比较类问题的 14 条错误，这次要不要管？",
         "先不管：证据都检索到了，属生成侧问题。"),
    ]
    y = 1.70
    for q, t in items:
        c.text(lx, y, lw, 0.66, q, size=16, bold=True, color=TEXT, leading=1.4)
        c.text(lx, y + 0.70, lw, 0.66, "倾向：" + t, size=16, color=MUTED, leading=1.45)
        y += 1.55

    c.rect(6.52, 1.66, 0.012, 4.10, RULE)
    label(c, 6.82, 1.70, "接下来两周")
    plan = [
        ("迭代式改写最小版（仅 MuSiQue）", "判据：桥接实体缺失类错例明显下降"),
        ("重排深度固定 50，重测端到端延迟", "判据：R@5 不掉，延迟低于 412 ms"),
        ("改写加「限定条件保留」检查", "判据：改写漂移 11 条下降"),
    ]
    y = 2.04
    for a, b in plan:
        c.rect(6.82, y + 0.06, 0.09, 0.09, ACCENT)
        c.text(7.04, y - 0.02, 5.60, 0.32, a, size=15, bold=True, color=TEXT)
        c.text(7.04, y + 0.32, 5.60, 0.28, b, size=13, color=MUTED)
        y += 0.92

    c.rect(ML, 6.04, CW, 0.60, SURFACE)
    c.text(ML + 0.18, 6.04, CW - 0.36, 0.60,
           "最想先讨论的：如果迭代式改写把延迟推到 700 ms 以上，这个场景能接受吗？",
           size=16, bold=True, color=TEXT, anchor="m")
    foot(c, 10, "计划里的判据都是相对本轮结果的；没有预算或截止时间的假设")
    c.set_notes(
        "（约 1.5 分钟）最后三件事想请老师定。第一，MuSiQue 要不要走迭代式改写——我倾向先做最小版本，"
        "但延迟会到 700 ms 以上。第二，3.4 倍延迟能不能接受，这个我定不了。"
        "第三，比较类错误这次要不要管，我倾向先不管。右边是接下来两周的最小实验和判据。")


BUILDERS = [s01_cover, s02_work, s03_method, s04_main, s05_uncertainty,
            s06_latency, s07_ablation, s08_curve, s09_errors, s10_discuss]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out/progress.pptx")
    ap.add_argument("--preview", default=None, help="directory for approximate PNG previews")
    ap.add_argument("--fonts", default="assets")
    args = ap.parse_args()

    c = PptxCanvas()
    for fn in BUILDERS:
        fn(c)
    c.save(args.out)
    print("wrote", args.out)

    if args.preview:
        os.makedirs(args.preview, exist_ok=True)
        pv = PreviewCanvas(args.fonts)
        for i, fn in enumerate(BUILDERS, 1):
            fn(pv)
            pv.save(os.path.join(args.preview, f"p{i:02d}.png"))
        print("previews ->", args.preview)


if __name__ == "__main__":
    main()
