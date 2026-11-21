"""统计 write-with-judgment 试跑 raw/ 下各回复的客观指标与触发情况。"""
import pathlib, re, sys

raw = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).parent / "raw")
CONNECTORS = re.compile(r"因此|然而|此外|与此同时|值得注意的是|总而言之|综上所述|由此可见")
META_NOTE = re.compile(r"(^|\n)\s*(改动说明|几点说明|改动只落在|改写后可直接用于|文中.*未引入外部数据)")

print("| 样本 | 触发技能(读文件数) | 字数 | 标题/小节数 | 列表项 | 显性连接词 | 正文外附带说明 |")
print("|---|---|---:|---:|---:|---:|---|")
for f in sorted(raw.glob("*.md")):
    txt = f.read_text(encoding="utf-8", errors="replace")
    tools_f = f.with_suffix(".tools.txt")
    tools = [l for l in tools_f.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()] if tools_f.is_file() else []
    words = len(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", txt))
    heads = len(re.findall(r"^(?:#{1,6}\s|\*\*[一二三四五六七八九十]+[、.．])", txt, flags=re.M))
    items = len(re.findall(r"^\s*(?:[-*+]|\d+[.)])\s", txt, flags=re.M))
    conn = len(CONNECTORS.findall(txt))
    has_meta = bool(META_NOTE.search(txt))
    print(f"| {f.stem} | {len(tools)} | {words} | {heads} | {items} | {conn} | {'是' if has_meta else '否'} |")
