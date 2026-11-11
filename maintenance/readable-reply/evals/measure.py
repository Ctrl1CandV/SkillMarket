"""统计 raw/ 下每个回复的客观指标。只读，不改任何文件。
用法：python3 -I measure.py [raw目录]   输出 Markdown 表。
关键点命中与“第一句是否直接回答”需人工阅读判断，不在此统计。"""
import re, sys, pathlib

raw = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).parent / "raw")
SUMMARY = re.compile(r"(综上|总结一下|总之|希望(这|以上|对你)|如果还有|如有(任何)?问题|欢迎继续|Hope this|In summary|To summarize)")
OPENER = re.compile(r"^\s*(好的|当然|没问题|这是个|这是一个|下面|让我|我来|Sure|Certainly|Great question|Let me)")

def strip_code(t):
    return re.sub(r"```.*?```", "", t, flags=re.S)

rows = []
for f in sorted(raw.glob("*.md")):
    t = f.read_text(encoding="utf-8", errors="replace")
    body = strip_code(t)
    words = len(re.findall(r"[一-鿿]|[A-Za-z0-9_]+", body))
    heads = len(re.findall(r"^#{1,6}\s", body, flags=re.M))
    bold = len(re.findall(r"\*\*[^*\n]+\*\*", body))
    items = len(re.findall(r"^\s*(?:[-*+]|\d+[.)])\s", body, flags=re.M))
    tail = body.strip()[-200:]
    first = next((l for l in body.splitlines() if l.strip()), "")
    rows.append((f.stem, words, heads, bold, items, bool(SUMMARY.search(tail)), bool(OPENER.search(first))))

print("| 文件 | 字数 | 标题 | 加粗 | 列表项 | 结尾总结/客套 | 开头客套 |")
print("|---|---|---|---|---|---|---|")
for r in rows:
    print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {'是' if r[5] else '否'} | {'是' if r[6] else '否'} |")
