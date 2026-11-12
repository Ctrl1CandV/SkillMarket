"""Generate the bakery sample data (fixed seed, synthetic customers). Usage: python make_data.py <out-dir>"""
import json
import random
import sys
from pathlib import Path

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
rng = random.Random(20261112)

products = [
    {"id": "toast", "name": "老面吐司", "price": 18, "unit": "条", "daily_limit": 30,
     "note": "老面发酵 18 小时，整条不切片；需要切片请备注"},
    {"id": "pretzel", "name": "碱水结", "price": 9, "unit": "个", "daily_limit": 50, "note": "外皮咸香，当天吃口感最好"},
    {"id": "walnut", "name": "全麦核桃包", "price": 15, "unit": "个", "daily_limit": 20, "note": "全麦粉约六成，少糖"},
    {"id": "croissant", "name": "可颂", "price": 12, "unit": "个", "daily_limit": 40, "note": "黄油可颂，出炉后两小时内最酥"},
    {"id": "floss", "name": "肉松小贝（4 个装）", "price": 22, "unit": "盒", "daily_limit": 12, "note": "含沙拉酱，需冷藏，当天食用"},
]
slots = [{"id": "morning", "label": "7:00–9:00"}, {"id": "noon", "label": "11:00–13:00"},
         {"id": "evening", "label": "17:00–19:00"}]
shop = {"name": "巷口面包房", "address": "梧桐路 128 号，小区东门对面", "phone": "0571-8812 3456",
        "bake_time": "06:00", "order_cutoff": "21:00", "pickup_date": "2026-11-13", "today": "2026-11-12"}

surnames = list("王李张刘陈杨黄赵周吴徐孙马朱胡郭何林罗高郑梁谢宋唐许韩冯邓曹彭曾萧田董潘袁蔡蒋余于杜叶程")
titles = ["阿姨", "叔叔", "先生", "女士", "老师", "师傅", ""]
notes = ["", "", "", "", "", "吐司帮忙切片", "可能晚到 10 分钟", "给老人买的，麻烦装袋", "小孩生日，可颂多装一个袋子",
         "到了打电话", "放前台就行"]
slot_weights = [0.55, 0.15, 0.30]
item_weights = {"toast": 0.6, "pretzel": 0.45, "walnut": 0.3, "croissant": 0.4, "floss": 0.3}
qty_choices = {"toast": [1, 1, 1, 2], "pretzel": [1, 2, 2, 3, 4], "walnut": [1, 1, 2],
               "croissant": [1, 2, 2, 3, 4], "floss": [1, 1, 2]}

orders, used = [], {p["id"]: 0 for p in products}
for n in range(1, 39):
    items = []
    for pid, weight in item_weights.items():
        if rng.random() < weight:
            q = rng.choice(qty_choices[pid])
            limit = next(p["daily_limit"] for p in products if p["id"] == pid)
            if used[pid] + q <= limit:
                items.append({"product": pid, "qty": q})
    if not items:
        room = [p["id"] for p in products if used[p["id"]] + 1 <= p["daily_limit"]]
        items.append({"product": room[0], "qty": 1})
    status = "cancelled" if n in (7, 23, 31) else "reserved"
    if status == "reserved":
        for it in items:
            used[it["product"]] += it["qty"]
    surname = rng.choice(surnames)
    title = rng.choice(titles)
    orders.append({
        "id": f"1113-{n:03d}",
        "name": surname + (title or rng.choice(["小姐", "同学"])),
        "phone": f"1{rng.choice('3578')}{rng.randint(0, 9)}{rng.randint(10000000, 99999999)}",
        "slot": rng.choices([s["id"] for s in slots], slot_weights)[0],
        "items": items,
        "note": rng.choice(notes),
        "status": status,
        "created_at": f"2026-11-12T{rng.randint(8, 20):02d}:{rng.randint(0, 59):02d}:00+08:00",
    })
orders.sort(key=lambda o: o["created_at"])

(out / "products.json").write_text(json.dumps({"shop": shop, "slots": slots, "products": products},
                                              ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(out / "orders-2026-11-13.json").write_text(json.dumps(orders, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print({p["id"]: f'{used[p["id"]]}/{p["daily_limit"]}' for p in products}, len(orders), "orders")
