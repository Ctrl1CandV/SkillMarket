"""Round-3 zero-spoiler metrics for write-with-judgment (A no-skill vs B 1.1.0 vs C 1.2.0)."""
from pathlib import Path
import math
import re

RAW = Path(__file__).resolve().parent / "raw"

META_OPENER = re.compile(
    r"先给结论[：:]|结论先说[：:]|先说结论[：:]|先把账算清楚[：:]|先看一个具体|我们先从一个问题说起|压成一句话[：:]|我的意见是[：:]"
)
DASH = re.compile(r"——")
FAKE_DICHOT = re.compile(r"不是[^。！？\n]{1,28}而是|是[^。！？\n]{1,28}而非|与其说[^。！？\n]{1,28}不如说|不仅[^。！？\n]{1,28}更|从来不是[^。！？\n]{1,28}而是")
BOLD_CARD = re.compile(r"(?m)^\s*(?:[-*]|\d+\.)?\s*\*\*[^*\n]{2,20}[：:。]\*\*")
EXPLICIT_CONN = re.compile(r"因此|然而|此外|与此同时|值得注意的是|换言之|总而言之|综上所述|归根结底")
TRAILING_NOTE = re.compile(r"改动说明|修改说明|交付说明|备注[：:]|未引入外部|比草稿里那句|因此这里不给")


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


def para_stats(text: str):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if len(re.sub(r"\s+", "", p)) >= 10]
    if len(paras) < 2:
        return len(paras), 0.0
    lens = [len(re.sub(r"\s+", "", p)) for p in paras]
    max_share = max(lens) / sum(lens)
    return len(paras), max_share


print("| 样本 | 读文件(ref) | 字数 | 段数(最大段%) | 句长CV(短%) | 报幕 | 假二分 | 破折号 | 粗体卡 | 连接词 | 尾注 |")
print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")

for p in sorted(RAW.glob("*.md")):
    text = p.read_text(encoding="utf-8").strip()
    chars = len(re.findall(r"[^\s]", text))
    tf = p.with_suffix(".tools.txt")
    tl = [l for l in tf.read_text(encoding="utf-8").splitlines() if l.strip()] if tf.exists() else []
    refs = sum(1 for l in tl if "references" in l)
    pn, mshare = para_stats(text)
    cv, sr = sent_stats(text)
    mo = len(META_OPENER.findall(text))
    fd = len(FAKE_DICHOT.findall(text))
    da = len(DASH.findall(text))
    bc = len(BOLD_CARD.findall(text))
    ec = len(EXPLICIT_CONN.findall(text))
    tn = "是" if TRAILING_NOTE.search(text) else "否"
    print(f"| {p.stem} | {len(tl)}({refs}) | {chars} | {pn}({int(mshare*100)}%) | {cv:.2f}({int(sr*100)}%) | {mo} | {fd} | {da} | {bc} | {ec} | {tn} |")
