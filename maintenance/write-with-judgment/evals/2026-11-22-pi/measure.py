"""Round-2 objective metrics for write-with-judgment (A no-skill vs B 1.0.0 vs C 1.1.0)."""
from pathlib import Path
import math
import re

RAW = Path(__file__).resolve().parent / "raw"

EXPLICIT_CONN = re.compile(r"因此|然而|此外|与此同时|值得注意的是|换言之|总而言之|综上所述|归根结底")
HEADING = re.compile(r"(?m)^(?:#{1,4}\s+|(?:一|二|三|四|五)、|\*\*(?:一|二|三|四|五)、)")
LIST_ITEM = re.compile(r"(?m)^\s*(?:[-*•]|\d+\.)\s+")
BOLD_CARD = re.compile(r"(?m)^\s*(?:[-*]\s*)?\*\*[^*\n]{2,18}[：:]\*\*")
META_LEAK = re.compile(
    r"改动说明|修改说明|交付说明|备注[：:]|未引入外部数据|因此这里不给|这里不给原因判断|以免误导|以下区分已知与未知"
    r"|先给结论[：:]|结论先说[：:]|先说结论[：:]|先把账算清楚[：:]|我的意见是[：:]"
)

PROMPT_CHECKS = {
    "01-data-reasoning-denom": {
        "required": ["195", "25.5", "53.3", "320|125"],
        "forbidden": [r"一共只摊到.{0,12}25\s*分钟|摊到.{0,10}每票\s*25\s*分钟"],
    },
    "02-narrative-nonfiction": {
        "required": ["字典", "泛黄", "下车报平安", "七年", "说不清"],
        "forbidden": [r"折痕|褶皱|发毛|毛边|蓝墨水|圆珠笔|铅笔|字迹|发硬|发脆|冰凉|发沉|粗糙"],
    },
    "03-timing-tense-boundary": {
        "required": ["1 MB|1MB", r"search\.write\.ratelimit=on", "cluster failover", "下周一", "十点|10点|10:00"],
        "forbidden": [r"已(?:经)?(?:与|和)算法组|已回放|截至目前还没有定位|因此这里不给|以免误导"],
    },
    "04-long-proposal-judgment": {
        "required": ["1,800|1800", "680", "85%", "40%", "14", r"2\s*个月|两个月"],
        "forbidden": [r"奠定坚实基础|统筹权衡利弊|审慎推进"],
    },
    "05-diagnosis-only": {
        "required": ["17", "90", "微信群", "失效"],
        "forbidden": [],
    },
}


def sent_stats(text: str):
    sents = [s.strip() for s in re.split(r"[。！？!?;\n]+", text) if len(re.sub(r"\s+", "", s)) >= 3]
    if not sents:
        return 0.0, 0.0
    lens = [len(re.sub(r"\s+", "", s)) for s in sents]
    mean = sum(lens) / len(lens)
    var = sum((x - mean) ** 2 for x in lens) / len(lens)
    cv = (math.sqrt(var) / mean) if mean > 0 else 0.0
    short_ratio = sum(1 for x in lens if x <= 15) / len(lens)
    return cv, short_ratio


def check_spec(stem: str, text: str):
    for key, spec in PROMPT_CHECKS.items():
        if key in stem:
            missing = [tok for tok in spec["required"] if not re.search(tok, text)]
            bad = [pat for pat in spec["forbidden"] if re.search(pat, text)]
            return missing, bad
    return [], []


print("| 样本 | 读文件(含ref) | 字数 | 标题/列表/卡片 | 句长CV(短句%) | 显性连接 | 元话语/尾注 | 边界缺/违 |")
print("|---|---:|---:|---|---:|---:|---|---|")

for p in sorted(RAW.glob("*.md")):
    text = p.read_text(encoding="utf-8").strip()
    chars = len(re.findall(r"[^\s]", text))
    tools_file = p.with_suffix(".tools.txt")
    tool_lines = [l for l in tools_file.read_text(encoding="utf-8").splitlines() if l.strip()] if tools_file.exists() else []
    ref_reads = sum(1 for l in tool_lines if "references" in l)
    h = len(HEADING.findall(text))
    li = len(LIST_ITEM.findall(text))
    bc = len(BOLD_CARD.findall(text))
    cv, sr = sent_stats(text)
    conn = len(EXPLICIT_CONN.findall(text))
    leak = "是" if META_LEAK.search(text) else "否"
    missing, bad = check_spec(p.stem, text)
    chk = f"缺{len(missing)}/违{len(bad)}"
    if missing or bad:
        detail = []
        if missing:
            detail.append("缺:" + ",".join(missing))
        if bad:
            detail.append("违:" + ",".join(bad))
        chk += " (" + "; ".join(detail) + ")"
    print(f"| {p.stem} | {len(tool_lines)}({ref_reads}) | {chars} | {h}/{li}/{bc} | {cv:.2f}({int(sr*100)}%) | {conn} | {leak} | {chk} |")
