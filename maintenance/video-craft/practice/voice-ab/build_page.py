"""Build the blind listening page (one self-contained HTML, audio embedded)."""
import base64
import json
from pathlib import Path
import random

HERE = Path(__file__).resolve().parent
L = HERE / "out" / "listen"
check = {r["file"]: r for r in json.loads((HERE / "out" / "check.json").read_text(encoding="utf-8"))}

PASSAGES = [
    ("lesson", "教学讲解", "老师（女）",
     "九枚硬币里，有一枚轻一些，其余八枚一样重。只有一架天平。怎样只称两次，就找出那枚轻币？先把硬币分成三堆，每堆三枚。一到三号放左盘，四到六号放右盘。留下一堆。",
     {"A": "takes-lesson-A-0.m4a", "B": "takes-lesson-B-0.m4a", "C": "takes-lesson-C-0.m4a"}),
    ("spot", "产品广告", "年轻男声",
     "今晚，开场提前十五分钟。灯光几点到？音响呢？用倒场，改一个开场时间。灯光、音响、入场，全都跟着走。",
     {"A": "takes-spot-A-0.m4a", "B": "takes-spot-B-1.m4a", "C": "takes-spot-C-0.m4a"}),
    ("story", "叙事短片", "中年男声",
     "那年冬天，海边的灯塔还亮着。每天傍晚，他都会爬上去，看最后一艘船回港。后来船不来了，他还是去，只是看得更久一些。",
     {"A": "takes-story-A-0.m4a", "B": "takes-story-B-0.m4a", "C": "takes-story-C-0.m4a"}),
]
WHO = {"A": "Edge 在线声音（0.6 用的引擎，这里整段生成）",
       "B": "VoxCPM1.5 · 小模型约 2 GB",
       "C": "VoxCPM2 · 大模型约 5 GB"}


def data_uri(name):
    return "data:audio/mp4;base64," + base64.b64encode((L / name).read_bytes()).decode()


rnd = random.Random(1118)
blocks = []
for key, title, role, text, files in PASSAGES:
    order = list(files)
    rnd.shuffle(order)
    rows = []
    for i, tag in enumerate(order):
        c = check[files[tag]]
        rows.append(f'''<div class="take" data-tag="{tag}">
  <button class="play" data-src="{data_uri(files[tag])}" aria-label="播放 {'甲乙丙'[i]}">▶</button>
  <span class="name">{'甲乙丙'[i]}</span>
  <span class="dur">{c['dur']:.1f} 秒</span>
  <span class="reveal">{WHO[tag]}</span>
  <label class="pick"><input type="radio" name="{key}" value="{'甲乙丙'[i]}"> 最自然</label>
</div>''')
    blocks.append(f'''<section>
  <h2>{title} <small>{role}</small></h2>
  <p class="text">{text}</p>
  {''.join(rows)}
</section>''')

cards = []
for role, label in (("teacher", "老师"), ("promo", "广告"), ("story", "叙事")):
    chosen = json.loads((HERE / "out" / "cards" / "chosen.json").read_text())[role]
    name = f"cards-{role}-{chosen}.m4a"
    cards.append(f'<div class="take"><button class="play" data-src="{data_uri(name)}">▶</button>'
                 f'<span class="name">{label}</span><span class="dur">{check[name]["dur"]:.1f} 秒</span></div>')

shipped = f'''<div class="take"><button class="play" data-src="{data_uri('shipped-lesson.m4a')}">▶</button>
<span class="name">0.6 现状</span><span class="dur">示例《九枚硬币》开头 18 秒，Edge 逐句生成后按画面拼接</span></div>'''

html = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>旁白盲听</title>
<style>
:root {{ --bg:#f6f5f2; --fg:#1d1d1f; --mute:#6b6b70; --line:#dedcd6; --accent:#b4532a; --card:#fff; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#17171a; --fg:#ececee; --mute:#9a9aa2; --line:#2e2e34; --accent:#e08a5c; --card:#1f1f23; }} }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.7 "PingFang SC","Microsoft YaHei",system-ui,sans-serif; }}
main {{ max-width: 760px; margin: 0 auto; padding: 40px 16px 80px; }}
h1 {{ font-size: 26px; margin: 0 0 6px; }}
.lead {{ color: var(--mute); margin: 0 0 28px; }}
section {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 18px 20px 10px; margin: 0 0 18px; }}
h2 {{ font-size: 19px; margin: 0; }} h2 small {{ color: var(--mute); font-weight: 400; font-size: 14px; margin-left: 8px; }}
.text {{ color: var(--mute); font-size: 14px; margin: 6px 0 10px; }}
.take {{ display: flex; align-items: center; gap: 12px; padding: 8px 0; border-top: 1px solid var(--line); flex-wrap: wrap; }}
.play {{ width: 40px; height: 40px; border-radius: 50%; border: 1px solid var(--line); background: var(--bg); color: var(--fg); font-size: 15px; cursor: pointer; }}
.play.on {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
.name {{ font-weight: 600; min-width: 2.2em; }}
.dur {{ color: var(--mute); font-size: 14px; }}
.reveal {{ color: var(--accent); font-size: 14px; display: none; }}
body.shown .reveal {{ display: inline; }}
.pick {{ margin-left: auto; font-size: 14px; color: var(--mute); cursor: pointer; }}
.bar {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin: 26px 0 0; }}
.bar button {{ padding: 9px 16px; border-radius: 8px; border: 1px solid var(--line); background: var(--card); color: var(--fg); cursor: pointer; font: inherit; }}
#summary {{ color: var(--mute); font-size: 14px; }}
h3 {{ font-size: 16px; margin: 34px 0 4px; }}
</style></head><body><main>
<h1>旁白盲听</h1>
<p class="lead">每段文字由三种引擎各读一遍，甲乙丙顺序已打乱，响度统一到 −16 LUFS。三条都没有读错字。请戴耳机，每段选一条听起来最像真人在说话的，再点“揭晓”。</p>
{''.join(blocks)}
<div class="bar"><button id="show">揭晓</button><span id="summary"></span></div>
<h3>参考</h3>
<section>{shipped}</section>
<h3>三张声音卡</h3>
<p class="lead">两种本地模型都照着同一张卡读。卡由大模型按一句文字描述设计，同一描述试了三次，取音高和语速最合适的一条。</p>
<section>{''.join(cards)}</section>
</main>
<script>
const audio = new Audio(); let cur = null;
document.querySelectorAll('.play').forEach(b => b.addEventListener('click', () => {{
  if (cur === b && !audio.paused) {{ audio.pause(); b.classList.remove('on'); b.textContent = '▶'; return; }}
  if (cur) {{ cur.classList.remove('on'); cur.textContent = '▶'; }}
  audio.src = b.dataset.src; audio.currentTime = 0; audio.play(); cur = b; b.classList.add('on'); b.textContent = '❚❚';
}}));
audio.addEventListener('ended', () => {{ if (cur) {{ cur.classList.remove('on'); cur.textContent = '▶'; }} }});
document.getElementById('show').addEventListener('click', () => {{
  document.body.classList.add('shown');
  const out = [];
  document.querySelectorAll('section').forEach(s => {{
    const r = s.querySelector('input:checked'); if (!r) return;
    const tag = r.closest('.take').dataset.tag, h = s.querySelector('h2').firstChild.textContent.trim();
    out.push(h + '：' + {{A:'Edge', B:'VoxCPM1.5', C:'VoxCPM2'}}[tag]);
  }});
  document.getElementById('summary').textContent = out.length ? '你选的：' + out.join('，') : '';
}});
</script></body></html>'''
(HERE / "index.html").write_text(html, encoding="utf-8")
print("wrote", HERE / "index.html", round(len(html) / 1e6, 1), "MB")
