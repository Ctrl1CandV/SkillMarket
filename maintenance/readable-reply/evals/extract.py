"""从 pi 的 --mode json 事件流里提取：最终回复文本、工具调用记录。
用法：python3 -I extract.py <events.jsonl> <out.md> <out.tools.txt>"""
import json, sys

src, out_md, out_tools = sys.argv[1:4]
final_text, tools, err = "", [], ""
with open(src, encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = ev.get("type")
        if t == "tool_execution_start":
            a = ev.get("args") or {}
            tools.append(f"{ev.get('toolName')} {a.get('path') or a.get('file_path') or a.get('command') or ''}".strip())
        elif t == "message_end":
            m = ev.get("message") or {}
            if m.get("role") == "assistant":
                c = m.get("content")
                if isinstance(c, str):
                    txt = c
                else:
                    txt = "".join(b.get("text", "") for b in (c or []) if b.get("type") == "text")
                if txt.strip():
                    final_text = txt          # 取最后一条有文本的助手消息
                if m.get("errorMessage"):
                    err = str(m["errorMessage"])
open(out_md, "w", encoding="utf-8").write(final_text)
open(out_tools, "w", encoding="utf-8").write("\n".join(tools) + ("\n" if tools else "") + (f"ERROR: {err}\n" if err else ""))
