"""统计 de-ai-flavor 试跑 raw/ 下各回复的客观指标与触发情况。"""
import pathlib, re, sys

raw = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).parent / "raw")
CONNECTORS = re.compile(r"因此|然而|此外|与此同时|值得注意的是|总而言之|综上所述|具体而言|显而易见|不言而喻")
WRAPPERS = re.compile(r"进行[^，。；\n]{1,8}的|在[^，。；\n]{1,10}层面|实现了?对|奠定了?[^，。；\n]{0,6}基础|赋能")
META_TAIL = re.compile(r"(^|\n)\s*(改动说明|交付说明|修改说明|备注)\s*[：:]")

print("| 样本 | 触发技能(读文件数) | 字数 | 显性连接词 | 虚词包裹/套话 | 额外附带修改备注 |")
print("|---|---|---:|---:|---:|---|")
for f in sorted(raw.glob("*.md")):
    txt = f.read_text(encoding="utf-8", errors="replace")
    tools_f = f.with_suffix(".tools.txt")
    tools = [l for l in tools_f.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()] if tools_f.is_file() else []
    words = len(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", txt))
    conn = len(CONNECTORS.findall(txt))
    wrap = len(WRAPPERS.findall(txt))
    has_meta = bool(META_TAIL.search(txt))
    print(f"| {f.stem} | {len(tools)} | {words} | {conn} | {wrap} | {'是' if has_meta else '否'} |")
