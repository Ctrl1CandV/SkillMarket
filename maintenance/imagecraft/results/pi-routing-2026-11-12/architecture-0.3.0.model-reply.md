图画好了，放在 `docs/` 下：

| 文件 | 说明 |
|---|---|
| `docs/architecture.svg` | 主文件，矢量、可带进 README，11.9 KB |
| `docs/architecture.png` | 2 倍图（2800×1900），给不支持 SVG 的场合备用 |

README 里引用：

```md
## 系统架构

![系统架构](docs/architecture.svg)
```

**图里的内容**（全部按你给的拓扑，未加没提到的组件）：

- 双色实线：浏览器前端(React) →`HTTPS`→ API 网关(Nginx) → 用户 / 订单 / 检索三个服务
- 数据层在右侧：用户、订单 → PostgreSQL；三个服务各一条→ Redis；检索 → Elasticsearch
- 琥珀色单独一条异步链：订单服务 →`下单消息`→ RabbitMQ →`消费`→ 通知服务(Worker) →`SMTP`→ 邮件
- 灰色虚线：四个服务（含 Worker）的日志汇入底部 Loki 条
- 左上角有图例（实线=请求/数据流，虚线=日志；按层着色）；节点带技术/角色副标题

**后续要改**：SVG 是手写坐标生成的，改文案或加节点改 `.imagecraft/scratch/gen_arch.py` 后重跑即可，别直接改 SVG：

```bash
python3 .imagecraft/scratch/gen_arch.py docs/architecture.svg
/usr/bin/python3 -c "import cairosvg; cairosvg.svg2png(url='docs/architecture.svg', write_to='docs/architecture.png', scale=2)"
```

**两点如实说明**：

1. 图里有两处“跨越”用了白色断口表示不相连（订单→PostgreSQL 越过用户→Redis 的竖线；订单→MQ 越过网关→检索的横线）。这是为了在平面里画清楚，不是数据关系。
2. 文字用系统字体栈（微软雅黑 / 苹方 / Noto Sans CJK）。SVG 在缺中文字体的机器上会显示豆腐块，这种场合用 PNG。

`.imagecraft/` 里是 brief、预览和生成脚本，属于临时工作区，建议加进 `.gitignore`（确认不需要后再整体删）。