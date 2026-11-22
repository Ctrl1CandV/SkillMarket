"""Round-2 objective metrics for de-ai-flavor (A no-skill vs B 3.0.0 vs C 3.1.0)."""
from pathlib import Path
import math
import re

RAW = Path(__file__).resolve().parent / "raw"

EXPLICIT_CONN = re.compile(r"因此|然而|此外|与此同时|值得注意的是|换言之|总而言之|综上所述|归根结底|具体而言|不可否认")
SUBTLE_AI = re.compile(
    r"不是[^。！？\n]{1,26}而是|是[^。！？\n]{1,26}而非|与其说[^。！？\n]{1,26}不如说|不仅[^。！？\n]{1,26}更"
    r"|只有当[^。！？\n]{1,32}才|——|你有没有想过|听起来.{0,10}抽象|别急|神秘面纱|折射出|奠定了坚实基础"
    r"|先给结论[：:]|结论先说[：:]|先说结论[：:]|先把账算清楚[：:]|压成一句话[：:]|绕回开头那个问题[：:]"
    r"|赋能|抓手|闭环|探索之旅|小小波折|小小挑战|进行.{1,10}(?:操作|处理)|在.{1,10}层面"
)
BOLD_CARD = re.compile(r"(?m)^\s*(?:[-*]\s*)?\*\*[^*\n]{2,18}[：:]\*\*")
TRAILING_NOTE = re.compile(
    r"改动说明|修改说明|交付说明|备注[：:]|(?<!卡片)说明[：:]|原文里的|已经删掉|已删去|已移除|未引入外部"
)

PROMPT_ANCHORS = {
    "01-regression-fact-anchors": {
        "required": ["400", "30", "100%", "5%", "28", "初测", "订单服务", "7", "网关", "支付", "下周二"],
        "forbidden": [r"本周一", r"已经评估", r"已通过评审"],
    },
    "02-subtle-long-essay": {
        "required": ["40", "两个月", "35%", "一倍", "结算", "资金"],
        "forbidden": [r"赋能", r"抓手", r"闭环"],
    },
    "03-lecture-script": {
        "required": ["对称加密", "非对称加密", "公钥", "私钥", "会话密钥"],
        "forbidden": [r"搬运工", r"保险箱管家", r"安全卫士", r"神秘面纱", r"你有没有想过", r"别急"],
    },
    "04-voice-imitation-long": {
        "required": ["8000", "ALTER TABLE", "20", "gh-ost", "pt-online-schema-change"],
        "forbidden": [r"赋能", r"总而言之", r"值得注意的是"],
    },
    "05-ui-notice-clean": {
        "required": ["90", "30,000|30000|3万", "下载明细", "02:00", "03:30", "45", "王工", "赵工", "01:45", "查看降级预案"],
        "forbidden": [r"v3\.1", r"三栏", r"自适应网格", r"探索之旅", r"小波折", r"原文里的", r"已经删掉", r"已删"],
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


def check_anchors(stem: str, text: str):
    for key, spec in PROMPT_ANCHORS.items():
        if key in stem:
            missing = [tok for tok in spec["required"] if not re.search(tok, text)]
            bad = [pat for pat in spec["forbidden"] if re.search(pat, text)]
            return missing, bad
    return [], []


print("| 样本 | 读文件(含ref) | 字数 | 句长CV(短句%) | 显性连接 | 隐性AI命中 | 粗体卡片 | 尾注泄漏 | 锚点缺/违 |")
print("|---|---:|---:|---:|---:|---:|---:|---|---|")

for p in sorted(RAW.glob("*.md")):
    text = p.read_text(encoding="utf-8").strip()
    chars = len(re.findall(r"[^\s]", text))
    tools_file = p.with_suffix(".tools.txt")
    tool_lines = [l for l in tools_file.read_text(encoding="utf-8").splitlines() if l.strip()] if tools_file.exists() else []
    ref_reads = sum(1 for l in tool_lines if "references" in l)
    cv, sr = sent_stats(text)
    conn = len(EXPLICIT_CONN.findall(text))
    subtle = len(SUBTLE_AI.findall(text))
    cards = len(BOLD_CARD.findall(text))
    note = "是" if TRAILING_NOTE.search(text) else "否"
    missing, bad = check_anchors(p.stem, text)
    anchor_str = f"缺{len(missing)}/违{len(bad)}"
    if missing or bad:
        detail = []
        if missing:
            detail.append("缺:" + ",".join(missing))
        if bad:
            detail.append("违:" + ",".join(bad))
        anchor_str += " (" + "; ".join(detail) + ")"
    print(f"| {p.stem} | {len(tool_lines)}({ref_reads}) | {chars} | {cv:.2f}({int(sr*100)}%) | {conn} | {subtle} | {cards} | {note} | {anchor_str} |")
