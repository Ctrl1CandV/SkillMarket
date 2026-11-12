"""Deterministic charts from task data (matplotlib -> PNG at final slide size)."""
import csv
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.ticker import MultipleLocator

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
DATA = os.path.join(TASK, "data")
FONTS = os.path.join(TASK, ".work", "fonts")
OUT = os.path.join(HERE, "charts")
os.makedirs(OUT, exist_ok=True)

for f in ("NotoSansSC-Regular.otf", "NotoSansSC-Bold.otf"):
    fm.fontManager.addfont(os.path.join(FONTS, f))

INK = "#183C36"
MUTED = "#4B665F"
ACCENT = "#166B5B"
SECOND = "#657B72"
PALE = "#B5CFC4"
GRID = "#D9E5DF"
SURF = "#E8F1EC"

plt.rcParams.update({
    "font.family": "Noto Sans SC",
    "font.size": 15,
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.edgecolor": PALE,
    "axes.linewidth": 0.9,
    "savefig.transparent": True,
    "axes.unicode_minus": False,
    "figure.dpi": 220,
})


def _read(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _clean(ax, spines=("top", "right")):
    for s in spines:
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0, pad=6)


# ------------------------------------------------------------------ 1. MuSiQue
def chart_musiqe():
    rows = _read("main_results.csv")
    picks = {}
    for r in rows:
        if r["dataset"] == "MuSiQue" and r["method"] in ("Dense+CE", "QR+CE"):
            picks[r["method"]] = r
    base, ours = picks["Dense+CE"], picks["QR+CE"]

    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.95))
    panels = [("Recall@5", "recall_at_5_mean", "recall_at_5_std", (50.0, 55.6), "+1.1"),
              ("EM", "em_mean", "em_std", (23.4, 28.6), "+0.6")]
    for ax, (label, mk, sk, xlim, delta) in zip(axes, panels):
        b, sb = float(base[mk]), float(base[sk])
        o, so = float(ours[mk]), float(ours[sk])
        for m, s, yv, col in ((b, sb, 1, SECOND), (o, so, 0, ACCENT)):
            ax.errorbar(m, yv, xerr=s, fmt="o", ms=12, color=col, ecolor=col,
                        elinewidth=2.4, capsize=5, capthick=2.4, zorder=3)
            ax.text(m, yv + 0.17, f"{m:.1f} ± {s:.1f}", ha="center", va="bottom",
                    fontsize=16.5, fontweight="bold", color=col)
        ax.annotate("", xy=(o, 0.5), xytext=(b, 0.5),
                    arrowprops=dict(arrowstyle="<->", color=ACCENT, lw=1.2,
                                    shrinkA=1, shrinkB=1))
        ax.text((o + b) / 2, 0.58, f"Δ {delta}", ha="center", va="bottom",
                fontsize=15.5, color=ACCENT, fontweight="bold")
        ax.set_xlim(*xlim)
        ax.set_ylim(-0.62, 1.72)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["QR+CE", "Dense+CE"], fontsize=15.5)
        ax.set_title(label, fontsize=16.5, color=INK, loc="left", pad=10)
        ax.xaxis.grid(True, color=GRID, lw=0.9)
        ax.set_axisbelow(True)
        _clean(ax, ("top", "right", "left"))
        ax.tick_params(axis="y", length=0)
    fig.subplots_adjust(left=0.185, right=0.985, top=0.85, bottom=0.13, wspace=0.62)
    p = os.path.join(OUT, "musique.png")
    fig.savefig(p, dpi=220)
    plt.close(fig)
    return p


# ------------------------------------------------------------------ 2. train
def chart_train():
    rows = _read("train_curve.csv")
    steps = [int(r["step"]) for r in rows]
    hard = [float(r["dev_recall5_hardneg"]) for r in rows]
    soft = [float(r["dev_recall5_nohardneg"]) for r in rows]

    fig, ax = plt.subplots(figsize=(7.9, 3.6))
    l1, = ax.plot(steps, soft, color=PALE, lw=3.0, marker="o", ms=4.2,
                  mfc="white", mew=1.3, zorder=2, label="无难负例")
    l2, = ax.plot(steps, hard, color=ACCENT, lw=3.0, marker="o", ms=4.2,
                  mfc="white", mew=1.3, zorder=3, label="有难负例")
    ax.legend(handles=[l2, l1], loc="upper left", frameon=False, fontsize=14,
              handlelength=1.6, labelspacing=0.35, borderaxespad=0.2)
    ax.annotate("6k 之后基本持平", xy=(6800, 75.9), xytext=(7400, 80.4),
                fontsize=14.5, color=SECOND, va="bottom",
                arrowprops=dict(arrowstyle="-", color=PALE, lw=1.3,
                                connectionstyle="arc3,rad=-0.25"))
    ax.annotate("约 10k 追平，之后继续涨", xy=(10800, 76.6), xytext=(6100, 61.6),
                fontsize=14.5, color=ACCENT, va="bottom",
                arrowprops=dict(arrowstyle="-", color=PALE, lw=1.3,
                                connectionstyle="arc3,rad=0.25"))
    ax.set_xlim(-400, 15800)
    ax.set_ylim(58.5, 83.6)
    ax.set_xticks([0, 3000, 6000, 9000, 12000, 15000])
    ax.set_xticklabels(["0", "3k", "6k", "9k", "12k", "15k"])
    ax.set_yticks([60, 65, 70, 75, 80])
    ax.set_xlabel("训练步数", fontsize=14.5, labelpad=5)
    ax.set_ylabel("dev Recall@5", fontsize=14.5, labelpad=4)
    ax.grid(axis="y", color=GRID, lw=0.9)
    ax.set_axisbelow(True)
    _clean(ax)
    fig.subplots_adjust(left=0.095, right=0.985, top=0.965, bottom=0.175)
    p = os.path.join(OUT, "train.png")
    fig.savefig(p, dpi=220)
    plt.close(fig)
    return p


# ------------------------------------------------------------------ 3. errors
def chart_errors():
    rows = _read("error_types.csv")
    zh = {
        "bridge entity not retrieved": ("桥接实体未检索到", "检索"),
        "comparison question": ("比较类问题判断错", "生成"),
        "rewrite drift": ("改写漂移", "改写"),
        "annotation noise": ("标注噪声", "数据"),
        "other": ("其他", "混合"),
    }
    stage_col = {"检索": ACCENT, "改写": SECOND, "生成": "#8A9E96",
                 "数据": "#BAC9C2", "混合": "#D3DED8"}
    items = [(zh[r["error_type"]][0], zh[r["error_type"]][1], int(r["count"]))
             for r in rows]
    items.sort(key=lambda t: t[2])

    fig, ax = plt.subplots(figsize=(6.5, 3.9))
    ys = range(len(items))
    for y, (label, stage, n) in zip(ys, items):
        ax.barh(y, n, height=0.56, color=stage_col[stage], zorder=2)
        ax.text(n + 0.35, y, str(n), va="center", ha="left", fontsize=16,
                fontweight="bold", color=INK)
        ax.text(0.32, y, label, va="center", ha="left", fontsize=14.5,
                color="white" if stage == "检索" else INK)
        ax.text(n - 0.55, y, stage, va="center", ha="right", fontsize=12,
                color="white" if stage == "检索" else MUTED)
    ax.set_yticks([])
    ax.set_xlim(0, 26.5)
    ax.set_ylim(-0.6, len(items) - 0.4)
    ax.set_xticks([0, 5, 10, 15, 20, 25])
    ax.set_xlabel("错例数（共 60 条 MuSiQue 错例）", fontsize=14, labelpad=6)
    ax.grid(axis="x", color=GRID, lw=0.9)
    ax.set_axisbelow(True)
    _clean(ax, ("top", "right", "left"))
    fig.subplots_adjust(left=0.015, right=0.975, top=0.965, bottom=0.20)
    p = os.path.join(OUT, "errors.png")
    fig.savefig(p, dpi=220)
    plt.close(fig)
    return p


# ------------------------------------------------------------------ 4. latency
def chart_latency():
    rows = _read("latency.csv")
    order = ["BM25", "Dense", "Dense+CE", "QR+CE"]
    by = {r["method"]: r for r in rows}
    fig, ax = plt.subplots(figsize=(7.55, 3.95))
    parts = [("rewrite_ms", "改写", "#9DBDB2"),
             ("retrieve_ms", "检索", PALE),
             ("rerank_ms", "重排", ACCENT)]
    ys = list(range(len(order)))[::-1]
    for y, m in zip(ys, order):
        left = 0.0
        for key, label, col in parts:
            v = float(by[m][key])
            if v <= 0:
                continue
            ax.barh(y, v, left=left, height=0.62, color=col, zorder=2,
                    edgecolor="white", linewidth=1.8)
            if v >= 60:
                ax.text(left + v / 2, y, f"{label} {v:.0f}", va="center",
                        ha="center", fontsize=13.5,
                        color="white" if col in (ACCENT, "#9DBDB2") else INK)
            left += v
        total = float(by[m]["total_ms"])
        ax.text(total + 9, y, f"{total:.0f} ms", va="center", ha="left",
                fontsize=16.5, fontweight="bold", color=INK)
        ax.text(-9, y, m, va="center", ha="right", fontsize=16)
    ax.set_yticks([])
    ax.set_xlim(0, 470)
    ax.set_ylim(-0.55, len(order) - 0.45)
    ax.set_xticks([0, 100, 200, 300, 400])
    ax.set_xlabel("单条查询端到端延迟（ms）", fontsize=14.5, labelpad=6)
    ax.grid(axis="x", color=GRID, lw=0.9)
    ax.set_axisbelow(True)
    _clean(ax, ("top", "right", "left"))
    fig.subplots_adjust(left=0.195, right=0.885, top=0.975, bottom=0.175)
    p = os.path.join(OUT, "latency.png")
    fig.savefig(p, dpi=220)
    plt.close(fig)
    return p


if __name__ == "__main__":
    for fn in (chart_musiqe, chart_train, chart_errors, chart_latency):
        print(fn())
