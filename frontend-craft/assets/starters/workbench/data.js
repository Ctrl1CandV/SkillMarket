// 示例数据（合成，不是真实顾客）。由 evals/2026-11-12-bakery/data 生成。
window.BAKERY_SEED = {
 "shop": {
  "name": "巷口面包房",
  "address": "梧桐路 128 号，小区东门对面",
  "phone": "0571-8812 3456",
  "bake_time": "06:00",
  "order_cutoff": "21:00",
  "pickup_date": "2026-11-13",
  "today": "2026-11-12"
 },
 "slots": [
  {
   "id": "morning",
   "label": "7:00–9:00"
  },
  {
   "id": "noon",
   "label": "11:00–13:00"
  },
  {
   "id": "evening",
   "label": "17:00–19:00"
  }
 ],
 "products": [
  {
   "id": "toast",
   "name": "老面吐司",
   "price": 18,
   "unit": "条",
   "daily_limit": 30,
   "note": "老面发酵 18 小时，整条不切片；需要切片请备注"
  },
  {
   "id": "pretzel",
   "name": "碱水结",
   "price": 9,
   "unit": "个",
   "daily_limit": 50,
   "note": "外皮咸香，当天吃口感最好"
  },
  {
   "id": "walnut",
   "name": "全麦核桃包",
   "price": 15,
   "unit": "个",
   "daily_limit": 20,
   "note": "全麦粉约六成，少糖"
  },
  {
   "id": "croissant",
   "name": "可颂",
   "price": 12,
   "unit": "个",
   "daily_limit": 40,
   "note": "黄油可颂，出炉后两小时内最酥"
  },
  {
   "id": "floss",
   "name": "肉松小贝（4 个装）",
   "price": 22,
   "unit": "盒",
   "daily_limit": 12,
   "note": "含沙拉酱，需冷藏，当天食用"
  }
 ],
 "orders": [
  {
   "id": "1113-016",
   "name": "许阿姨",
   "phone": "17789809591",
   "slot": "morning",
   "items": [
    {
     "product": "toast",
     "qty": 1
    },
    {
     "product": "walnut",
     "qty": 1
    },
    {
     "product": "croissant",
     "qty": 2
    },
    {
     "product": "floss",
     "qty": 1
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T08:15:00+08:00"
  },
  {
   "id": "1113-019",
   "name": "胡师傅",
   "phone": "18131248368",
   "slot": "evening",
   "items": [
    {
     "product": "floss",
     "qty": 1
    }
   ],
   "note": "吐司帮忙切片",
   "status": "reserved",
   "created_at": "2026-11-12T08:31:00+08:00"
  },
  {
   "id": "1113-038",
   "name": "蒋先生",
   "phone": "18012976989",
   "slot": "evening",
   "items": [
    {
     "product": "toast",
     "qty": 1
    }
   ],
   "note": "可能晚到 10 分钟",
   "status": "reserved",
   "created_at": "2026-11-12T09:16:00+08:00"
  },
  {
   "id": "1113-011",
   "name": "程女士",
   "phone": "13779519619",
   "slot": "evening",
   "items": [
    {
     "product": "toast",
     "qty": 1
    },
    {
     "product": "pretzel",
     "qty": 1
    },
    {
     "product": "croissant",
     "qty": 3
    },
    {
     "product": "floss",
     "qty": 2
    }
   ],
   "note": "小孩生日，可颂多装一个袋子",
   "status": "reserved",
   "created_at": "2026-11-12T09:28:00+08:00"
  },
  {
   "id": "1113-021",
   "name": "董同学",
   "phone": "18471618307",
   "slot": "noon",
   "items": [
    {
     "product": "toast",
     "qty": 1
    }
   ],
   "note": "吐司帮忙切片",
   "status": "reserved",
   "created_at": "2026-11-12T09:49:00+08:00"
  },
  {
   "id": "1113-014",
   "name": "何小姐",
   "phone": "13015328623",
   "slot": "morning",
   "items": [
    {
     "product": "toast",
     "qty": 1
    },
    {
     "product": "croissant",
     "qty": 2
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T09:58:00+08:00"
  },
  {
   "id": "1113-027",
   "name": "赵叔叔",
   "phone": "13139807014",
   "slot": "evening",
   "items": [
    {
     "product": "toast",
     "qty": 1
    },
    {
     "product": "walnut",
     "qty": 1
    },
    {
     "product": "floss",
     "qty": 2
    }
   ],
   "note": "吐司帮忙切片",
   "status": "reserved",
   "created_at": "2026-11-12T09:58:00+08:00"
  },
  {
   "id": "1113-003",
   "name": "陈先生",
   "phone": "18440862772",
   "slot": "morning",
   "items": [
    {
     "product": "toast",
     "qty": 1
    },
    {
     "product": "pretzel",
     "qty": 2
    },
    {
     "product": "walnut",
     "qty": 1
    },
    {
     "product": "croissant",
     "qty": 4
    }
   ],
   "note": "放前台就行",
   "status": "reserved",
   "created_at": "2026-11-12T10:40:00+08:00"
  },
  {
   "id": "1113-018",
   "name": "程先生",
   "phone": "18363503388",
   "slot": "morning",
   "items": [
    {
     "product": "pretzel",
     "qty": 2
    },
    {
     "product": "floss",
     "qty": 2
    }
   ],
   "note": "放前台就行",
   "status": "reserved",
   "created_at": "2026-11-12T10:41:00+08:00"
  },
  {
   "id": "1113-028",
   "name": "孙老师",
   "phone": "15693727449",
   "slot": "noon",
   "items": [
    {
     "product": "toast",
     "qty": 1
    },
    {
     "product": "walnut",
     "qty": 2
    }
   ],
   "note": "到了打电话",
   "status": "reserved",
   "created_at": "2026-11-12T11:03:00+08:00"
  },
  {
   "id": "1113-012",
   "name": "孙叔叔",
   "phone": "13830500476",
   "slot": "morning",
   "items": [
    {
     "product": "pretzel",
     "qty": 2
    },
    {
     "product": "floss",
     "qty": 1
    }
   ],
   "note": "放前台就行",
   "status": "reserved",
   "created_at": "2026-11-12T11:18:00+08:00"
  },
  {
   "id": "1113-005",
   "name": "吴师傅",
   "phone": "13182983703",
   "slot": "noon",
   "items": [
    {
     "product": "toast",
     "qty": 1
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T11:21:00+08:00"
  },
  {
   "id": "1113-036",
   "name": "刘小姐",
   "phone": "13550228686",
   "slot": "evening",
   "items": [
    {
     "product": "toast",
     "qty": 2
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T11:35:00+08:00"
  },
  {
   "id": "1113-026",
   "name": "杜同学",
   "phone": "17217024725",
   "slot": "morning",
   "items": [
    {
     "product": "toast",
     "qty": 1
    },
    {
     "product": "walnut",
     "qty": 2
    },
    {
     "product": "croissant",
     "qty": 4
    },
    {
     "product": "floss",
     "qty": 1
    }
   ],
   "note": "给老人买的，麻烦装袋",
   "status": "reserved",
   "created_at": "2026-11-12T11:38:00+08:00"
  },
  {
   "id": "1113-035",
   "name": "许先生",
   "phone": "13631522007",
   "slot": "morning",
   "items": [
    {
     "product": "toast",
     "qty": 1
    },
    {
     "product": "walnut",
     "qty": 1
    }
   ],
   "note": "放前台就行",
   "status": "reserved",
   "created_at": "2026-11-12T11:42:00+08:00"
  },
  {
   "id": "1113-024",
   "name": "董叔叔",
   "phone": "13194981666",
   "slot": "morning",
   "items": [
    {
     "product": "floss",
     "qty": 1
    }
   ],
   "note": "到了打电话",
   "status": "reserved",
   "created_at": "2026-11-12T11:51:00+08:00"
  },
  {
   "id": "1113-023",
   "name": "萧老师",
   "phone": "13495446695",
   "slot": "noon",
   "items": [
    {
     "product": "toast",
     "qty": 2
    },
    {
     "product": "croissant",
     "qty": 4
    }
   ],
   "note": "",
   "status": "cancelled",
   "created_at": "2026-11-12T13:13:00+08:00"
  },
  {
   "id": "1113-020",
   "name": "曹叔叔",
   "phone": "13445980908",
   "slot": "morning",
   "items": [
    {
     "product": "toast",
     "qty": 1
    },
    {
     "product": "pretzel",
     "qty": 3
    },
    {
     "product": "croissant",
     "qty": 3
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T13:23:00+08:00"
  },
  {
   "id": "1113-022",
   "name": "彭老师",
   "phone": "17289986999",
   "slot": "morning",
   "items": [
    {
     "product": "toast",
     "qty": 1
    }
   ],
   "note": "到了打电话",
   "status": "reserved",
   "created_at": "2026-11-12T13:25:00+08:00"
  },
  {
   "id": "1113-009",
   "name": "萧先生",
   "phone": "17296325752",
   "slot": "noon",
   "items": [
    {
     "product": "pretzel",
     "qty": 2
    },
    {
     "product": "croissant",
     "qty": 2
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T13:42:00+08:00"
  },
  {
   "id": "1113-037",
   "name": "郑女士",
   "phone": "18383762955",
   "slot": "morning",
   "items": [
    {
     "product": "toast",
     "qty": 1
    },
    {
     "product": "walnut",
     "qty": 1
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T13:58:00+08:00"
  },
  {
   "id": "1113-004",
   "name": "张女士",
   "phone": "15497227828",
   "slot": "morning",
   "items": [
    {
     "product": "pretzel",
     "qty": 4
    },
    {
     "product": "walnut",
     "qty": 1
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T14:08:00+08:00"
  },
  {
   "id": "1113-002",
   "name": "梁师傅",
   "phone": "13193566360",
   "slot": "evening",
   "items": [
    {
     "product": "toast",
     "qty": 1
    },
    {
     "product": "floss",
     "qty": 1
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T14:24:00+08:00"
  },
  {
   "id": "1113-025",
   "name": "程先生",
   "phone": "17611406972",
   "slot": "morning",
   "items": [
    {
     "product": "toast",
     "qty": 1
    }
   ],
   "note": "到了打电话",
   "status": "reserved",
   "created_at": "2026-11-12T15:03:00+08:00"
  },
  {
   "id": "1113-001",
   "name": "郭女士",
   "phone": "17273656782",
   "slot": "morning",
   "items": [
    {
     "product": "toast",
     "qty": 1
    },
    {
     "product": "pretzel",
     "qty": 2
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T15:27:00+08:00"
  },
  {
   "id": "1113-008",
   "name": "田小姐",
   "phone": "13175524982",
   "slot": "evening",
   "items": [
    {
     "product": "toast",
     "qty": 1
    },
    {
     "product": "pretzel",
     "qty": 1
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T15:30:00+08:00"
  },
  {
   "id": "1113-006",
   "name": "胡小姐",
   "phone": "15821402118",
   "slot": "evening",
   "items": [
    {
     "product": "walnut",
     "qty": 1
    }
   ],
   "note": "可能晚到 10 分钟",
   "status": "reserved",
   "created_at": "2026-11-12T15:36:00+08:00"
  },
  {
   "id": "1113-010",
   "name": "邓阿姨",
   "phone": "15365461990",
   "slot": "noon",
   "items": [
    {
     "product": "pretzel",
     "qty": 4
    },
    {
     "product": "croissant",
     "qty": 3
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T15:42:00+08:00"
  },
  {
   "id": "1113-031",
   "name": "杜小姐",
   "phone": "13293174071",
   "slot": "morning",
   "items": [
    {
     "product": "pretzel",
     "qty": 4
    }
   ],
   "note": "吐司帮忙切片",
   "status": "cancelled",
   "created_at": "2026-11-12T16:13:00+08:00"
  },
  {
   "id": "1113-013",
   "name": "唐师傅",
   "phone": "15399866885",
   "slot": "noon",
   "items": [
    {
     "product": "croissant",
     "qty": 2
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T16:54:00+08:00"
  },
  {
   "id": "1113-034",
   "name": "高女士",
   "phone": "13890339560",
   "slot": "morning",
   "items": [
    {
     "product": "walnut",
     "qty": 1
    }
   ],
   "note": "吐司帮忙切片",
   "status": "reserved",
   "created_at": "2026-11-12T17:11:00+08:00"
  },
  {
   "id": "1113-029",
   "name": "林小姐",
   "phone": "17364245106",
   "slot": "morning",
   "items": [
    {
     "product": "walnut",
     "qty": 2
    }
   ],
   "note": "可能晚到 10 分钟",
   "status": "reserved",
   "created_at": "2026-11-12T18:01:00+08:00"
  },
  {
   "id": "1113-007",
   "name": "程阿姨",
   "phone": "15476158993",
   "slot": "morning",
   "items": [
    {
     "product": "toast",
     "qty": 2
    },
    {
     "product": "floss",
     "qty": 1
    }
   ],
   "note": "吐司帮忙切片",
   "status": "cancelled",
   "created_at": "2026-11-12T18:22:00+08:00"
  },
  {
   "id": "1113-032",
   "name": "程同学",
   "phone": "17514020239",
   "slot": "morning",
   "items": [
    {
     "product": "toast",
     "qty": 1
    }
   ],
   "note": "放前台就行",
   "status": "reserved",
   "created_at": "2026-11-12T18:43:00+08:00"
  },
  {
   "id": "1113-030",
   "name": "林女士",
   "phone": "18467637122",
   "slot": "morning",
   "items": [
    {
     "product": "pretzel",
     "qty": 3
    },
    {
     "product": "croissant",
     "qty": 4
    }
   ],
   "note": "到了打电话",
   "status": "reserved",
   "created_at": "2026-11-12T19:09:00+08:00"
  },
  {
   "id": "1113-033",
   "name": "郭叔叔",
   "phone": "17991296732",
   "slot": "morning",
   "items": [
    {
     "product": "toast",
     "qty": 2
    },
    {
     "product": "pretzel",
     "qty": 2
    },
    {
     "product": "walnut",
     "qty": 1
    },
    {
     "product": "croissant",
     "qty": 3
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T19:47:00+08:00"
  },
  {
   "id": "1113-015",
   "name": "田先生",
   "phone": "13692274116",
   "slot": "morning",
   "items": [
    {
     "product": "pretzel",
     "qty": 2
    },
    {
     "product": "walnut",
     "qty": 1
    }
   ],
   "note": "可能晚到 10 分钟",
   "status": "reserved",
   "created_at": "2026-11-12T20:16:00+08:00"
  },
  {
   "id": "1113-017",
   "name": "于师傅",
   "phone": "18632541532",
   "slot": "morning",
   "items": [
    {
     "product": "croissant",
     "qty": 1
    }
   ],
   "note": "",
   "status": "reserved",
   "created_at": "2026-11-12T20:24:00+08:00"
  }
 ]
};
