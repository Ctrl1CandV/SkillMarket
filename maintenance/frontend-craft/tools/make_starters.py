"""Turn four practice pages into the starters that ship with frontend-craft: clean up what the checker found, add a header that says what the page is for."""
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
src = root / "maintenance/frontend-craft/practice/2026-11"
dst = root / "frontend-craft/assets/starters"


def header(title, decisions, replace):
    lines = ["<!--", f"  起步样例：{title}", "  这是一页能直接打开、能操作的完整页面。做同类页面时复制它再改，不要从空白开始。", "", "  这一类页面里起作用的决定："]
    lines += [f"  - {d}" for d in decisions]
    lines += ["", "  换成自己的内容时："] + [f"  - {r}" for r in replace] + ["-->"]
    return "\n".join(lines) + "\n"


def put(text, head):
    assert text.startswith("<!doctype html>"), text[:30]
    return "<!doctype html>\n" + head + text[len("<!doctype html>\n"):]


def sub(t, old, new, n=1):
    assert t.count(old) == n, (old[:60], t.count(old))
    return t.replace(old, new)


def scale(t, mapping):
    for a, b in mapping.items():
        t = re.sub(rf"font-size: {a}px", f"font-size: {b}px", t)
    return t


# ---- 1. workbench: the bakery owner's page ----
out = dst / "workbench"; out.mkdir(parents=True, exist_ok=True)
for name in ("base.css", "store.js", "data.js"):
    (out / name).write_text((src / "bakery" / name).read_text(encoding="utf-8"), encoding="utf-8")
t = (src / "bakery/owner.html").read_text(encoding="utf-8")
t = scale(t, {15: 16, 17: 16, 19: 18, 22: 24, 26: 24})   # 12 sizes down to 14 / 16 / 18 / 20 / 24 / 30 / 34 plus the big board numbers
t = sub(t, "  .cap { display: flex; align-items: center; gap: 12px; margin-top: 8px; font-size: 16px; color: var(--ink-2); }", "  .cap { display: flex; align-items: center; gap: 12px; margin-top: 8px; font-size: 14px; color: var(--ink-2); white-space: nowrap; }")   # at 16px this line wrapped on a tablet
t = put(t, header("工作台（店里的平板和笔记本用）",
    ["先分清有几个时刻、几种姿势。备货时人在操作台、隔着两米看；取货时人在柜台、要找要点。所以是两个视图，按时间自动选默认的，不做成一张总览。",
     "最大的字给真正用来认人、认东西的那个标识（这里是手机后四位），不一定是名称。",
     "强调色有预算：只留给容易出错、必须被看见的东西（数量 2 以上、订满了），成排的按钮用描边。",
     "表头只写一次；同样的话合并成一行；改不了的东西不做成控件。",
     "排法跟着数据的多少变：品种 6 款以内每款一列，更多时自动改成逐项列出。",
     "手机上重新安排每一行，不是把桌面的格子竖着摞起来。"],
    ["数据在 data.js 和 store.js，页面只管显示和操作。先换数据，看内容的真实形状（几种、几条、多长），再动版式。",
     "颜色和字体在 base.css 的开头。换配色只改那几行。",
     "网址加 ?now=05:10 可以换示例时间，?view=prep 或 pick 指定视图，?layout=list 或 matrix 指定排法。"]))
(out / "index.html").write_text(t, encoding="utf-8")

# ---- 2. dashboard ----
out = dst / "dashboard"; out.mkdir(parents=True, exist_ok=True)
t = (src / "dashboard/index.html").read_text(encoding="utf-8")
t = sub(t, "    .card { padding: 14px 14px 12px; } .runs { padding: 14px 0 4px; }", "    .seg button, .ghost { height: 40px; }\n    .card { padding: 14px 14px 12px; } .runs { padding: 14px 0 4px; }")
t = sub(t, "练习页面：数据是合成的，用来练习“看板先回答问题”。", "示例数据是合成的。")
# the practice page also carried a "conclusion first" headline for comparison; a starter shows one way only
t = "\n".join(l for l in t.split("\n") if not l.lstrip().startswith(".answer "))
t = sub(t, '<section class="answer" id="answer"></section>', '<section class="kpis" id="kpis"></section>')
a, b = t.index("  // —— 结论 ——"), t.index("  // —— 曲线")
t = t[:a] + """  // —— 指标卡：数据和数据的可信程度（范围、完成了几个种子、还有几个在跑），不写结论 ——
  $('kpis').innerHTML = METHODS.map(m => { const st = stats[m.id], d = st.mean - stats.base.mean, total = RUNS.filter(r => r.mid === m.id && r.status !== 'failed').length, run = total - st.n;
    return `<div class="kpi"><div class="k"><i style="background:${m.color}"></i>${m.name}</div>
      <div class="v">${f1(st.mean)}<small>%</small>${m.id === 'base' ? '' : `<span class="delta">${d >= 0 ? '+' : ''}${f1(d)}</span>`}</div>
      <div class="d">范围 ${f1(st.min)}–${f1(st.max)} · ${st.n}/${total} 个种子${run ? `<span class="running"> · ${run} 个在跑</span>` : ''}</div></div>`; }).join('');

""" + t[b:]
t = sub(t, "'和基线的范围重叠，不能确认'", "'和基线的范围重叠'")   # say what the data shows; whether that is enough is the reader's call
assert "answer" not in t, [l[:80] for l in t.split("\n") if "answer" in l]
t = put(t, header("数据看板（给会自己分析的人反复看）",
    ["看板只摆数据，分析留给看的人。替读者下结论的话属于报告，是另一类页面。",
     "“还有 1 个种子在跑”“种子之间的范围”是数据，不是结论，放进指标卡。",
     "专门回答“差距是不是随机波动”：每个样本一个点，对照基线的范围。只画平均值回答不了。",
     "线尾直接标名字和数值，不用图例；基线用灰色，最重要的一组用最醒目的颜色。",
     "轴要盖住全部数据，或者裁掉横轴并写明原因；线不能贴着图框走。",
     "图按容器的实际宽度重画，不整体缩放，手机上图里的字才不会变小。",
     "数据多了要能看局部：在图上横向拖动放大一段，纵轴跟着这一段重新定范围。"],
    ["数据在脚本开头的 METHODS 和 PLAN，现在是按固定种子合成的；换成真实数据时保留“每次运行一行”的结构。",
     "颜色在 :root 里。系列超过 5 个时不要再靠颜色区分，改用点选高亮或者分面。"]))
(out / "index.html").write_text(t, encoding="utf-8")

# ---- 3. settings ----
out = dst / "settings"; out.mkdir(parents=True, exist_ok=True)
t = (src / "settings/index.html").read_text(encoding="utf-8")
t = put(t, header("设置页（选项多、互相有依赖）",
    ["按用户会问的问题分组（发到哪里、什么事提醒我、什么时候别打扰），不按后端的配置结构分。",
     "顶上用一段话说清“这些设置合起来是什么效果”，每改一项它都跟着变。它描述状态，不替用户下结论。",
     "两个维度交叉的选项（事情 × 渠道）排成一张表，列头只写一次。",
     "依赖关系看得见：上一级关了，下一级变灰、保留原来的值，并在原地写一句为什么不起作用。",
     "开关把状态写成字（开着 / 关着），不只靠颜色。",
     "始终说清保存状态。改错了代价小的设置用自动保存加撤销；代价大的（删除、权限、付费）用手动保存，网址加 ?save=manual 可以看到。",
     "改不了的东西不做成控件，用一句话说明。"],
    ["选项定义在脚本开头的 EVENTS 和 DEFAULTS；summary() 把设置翻译成人话，新增选项时要同步改它。",
     "生成的句子要像人写的句子一样逐字检查：标点、空格、数字单位。"]))
(out / "index.html").write_text(t, encoding="utf-8")

# ---- 4. catalog: browse and search a collection ----
out = dst / "catalog"; out.mkdir(parents=True, exist_ok=True)
(out / "leaves.js").write_text((src / "atlas/leaves.js").read_text(encoding="utf-8"), encoding="utf-8")
t = (src / "atlas/index.html").read_text(encoding="utf-8")
t = sub(t, "  .seg button { border: 0; background: transparent; height: 38px;", "  .seg button { border: 0; background: transparent; height: 40px;")
t = put(t, header("图鉴和检索（按样子找东西）",
    ["界面不带颜色，颜色都留给藏品本身；每格一样大，东西不撑满格子。",
     "筛选项用来找东西的人会说的话，括号里再给术语。只写术语的话，最需要这一页的人看不懂。",
     "每个筛选项后面写着点下去还剩几种，会得到 0 种的直接变灰，不会筛进死胡同。",
     "搜索要认人们实际的叫法（俗名、别名），并在结果上标出是按哪个名字找到的。",
     "详情从旁边出来，列表让开位置而不是被盖住；可以用左右键翻上一个、下一个。",
     "“容易和谁弄混”单独一栏。",
     "筛选条件写进网址，这一页的状态可以原样发给别人。",
     "手机上每组筛选压成一行、可以横向滑动，结果要在第一屏露出来。"],
    ["藏品资料和画法在 leaves.js。这里的图是按形态参数用代码画的示意；有照片时换成照片，格子大小保持一致。",
     "没有图片也画不出来时，不要用色块或者图标冒充藏品，先问有没有素材。",
     "几百件以上时，筛选项要重新设计（分层、可搜索的筛选），网格可以保留。"]))
(out / "index.html").write_text(t, encoding="utf-8")
print("ok", sorted(p.relative_to(dst).as_posix() for p in dst.rglob("*") if p.is_file()))
