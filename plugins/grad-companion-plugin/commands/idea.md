---
description: 登记候选方向到选题台账，或流转状态（选入/否决）、查看停滞计数。
argument-hint: "<登记|列表|选入|否决|停滞> [内容或 id]"
skill: idea-ledger
---

按意图分流：登记则跑 idea_ledger.py add（--text 一句话，来源给 arXiv id 或一句话，排序理由用 --why-not-selected 显式化）；选入/否决/回切则跑 update（否决必须向用户要到方法级否定理由——环境性失败会触发警告并如实转述给用户确认）；列表与停滞计数分别跑 list 与 stagnation（stagnation 是纯计数提醒，不裁决）。台账只追加，同 id 最后一行为当前。
