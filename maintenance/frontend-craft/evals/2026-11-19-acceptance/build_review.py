# 统一验收的盲评页：每道题两份成品（不带技能、frontend-craft 0.9.0 工作版）各自打乱成甲、乙。
#   python build_review.py <运行目录> <截图目录> <pick.json> [组，默认 N,S10] [输出目录名，默认 review] [随机种子，默认 2611]
# 运行目录下有 reagents-N/task 这样的成品；截图目录下有 reagents-N/01-home.png 这样的截图；pick.json 写每份选哪四张图。
# 生成 review/index.html；对应关系写在 review/KEY.md，看完再打开。
import json, random, shutil, sys
from pathlib import Path
from PIL import Image

runs, shots, pick = Path(sys.argv[1]), Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text(encoding='utf-8'))
ARMS = sys.argv[4].split(',') if len(sys.argv) > 4 else ['N', 'S10']
out = Path(__file__).parent / (sys.argv[5] if len(sys.argv) > 5 else 'review')
if out.exists():
    shutil.rmtree(out)
out.mkdir()
TITLES = {'reagents': ('课题组试剂与耗材库', ['库存', '单个试剂', '我的领用', '采购清单']),
          'defense': ('研究生答辩安排', ['答辩安排', '场次详情', '我的答辩', '秘书台']),
          'translate': ('开源文档翻译协作', ['章节总览', '章节详情', '我的任务', '术语表'])}
NAMES = {'N': '不带技能', 'S7': 'frontend-craft 0.7.0', 'S8': 'frontend-craft 0.8.0', 'S9': 'frontend-craft 0.9.0', 'S10': 'frontend-craft 0.9.0 工作版（bc98c29）'}
skip = shutil.ignore_patterns('BRIEF.md', 'ENV.md', 'README.md', 'checks*', '_pagecheck', 'tests', 'test*.cjs', '*.log', '*.png')
rng = random.Random(int(sys.argv[6]) if len(sys.argv) > 6 else 2611)
key, sections = [], []
for task, (title, pages) in TITLES.items():
    arms = list(ARMS)
    rng.shuffle(arms)
    key.append(f'## {title}\n' + '\n'.join(f'- {"甲乙丙"[i]}：{NAMES[a]}' for i, a in enumerate(arms)))
    blocks = []
    for i, arm in enumerate(arms):
        label, slot = '甲乙丙'[i], f'{task}-{i + 1}'
        shutil.copytree(runs / f'{task}-{arm}' / 'task', out / slot, ignore=skip)
        img = out / 'img' / slot
        img.mkdir(parents=True)
        for k, name in enumerate(pick[task][arm]):
            Image.open(shots / f'{task}-{arm}' / f'{name}.png').convert('RGB').crop((0, 0, 1440, 900)).save(img / f'{k}.jpg', quality=86)
        Image.open(shots / f'{task}-{arm}' / '99-phone.png').convert('RGB').crop((0, 0, 390, 844)).save(img / 'phone.jpg', quality=86)
        figs = ''.join(f'<figure><a href="img/{slot}/{k}.jpg"><img src="img/{slot}/{k}.jpg" alt="{title}{label}：{p}" loading="lazy"></a><figcaption>{p}</figcaption></figure>' for k, p in enumerate(pages) if k)
        blocks.append(f'''<div class="arm"><h3>{label} <a href="{slot}/index.html">打开来操作 →</a></h3>
<figure class="main"><a href="img/{slot}/0.jpg"><img src="img/{slot}/0.jpg" alt="{title}{label}：{pages[0]}" loading="lazy"></a><figcaption>{pages[0]}，1440 宽的第一屏</figcaption></figure>
<div class="more">{figs}<figure><a href="img/{slot}/phone.jpg"><img src="img/{slot}/phone.jpg" alt="{title}{label}：手机" loading="lazy"></a><figcaption>手机</figcaption></figure></div></div>''')
    sections.append(f'<section><h2>{title}</h2>{"".join(blocks)}</section>')

html = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light">
<title>统一验收盲评</title>
<style>
:root {{ color-scheme: light; }}
body {{ margin: 0; padding: 2rem max(1.5rem, calc((100vw - 78rem) / 2)) 4rem; background: #f3f3f1; color: #1b1d1f; font: 1rem/1.6 "Microsoft YaHei UI", "Microsoft YaHei", system-ui, sans-serif; }}
h1 {{ font-size: 1.5rem; margin: 0 0 0.25rem; }}
p {{ margin: 0.25rem 0; max-width: 48rem; color: #454a4f; }}
section {{ margin-top: 3.5rem; padding-top: 1rem; border-top: 3px solid #1b1d1f; }}
h2 {{ font-size: 1.75rem; margin: 0 0 0.5rem; }}
.arm {{ margin-top: 2rem; }}
h3 {{ display: flex; align-items: baseline; gap: 1rem; margin: 0 0 0.75rem; font-size: 1.375rem; }}
h3 a {{ font-size: 1rem; font-weight: 400; color: #1b1d1f; }}
figure {{ margin: 0; }}
img {{ display: block; width: 100%; height: auto; border: 1px solid #c9ccce; background: #fff; }}
figcaption {{ margin-top: 0.375rem; font-size: 0.8125rem; color: #5c6268; }}
.more {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)) minmax(0, 0.42fr); gap: 1rem; margin-top: 1rem; align-items: start; }}
@media (max-width: 800px) {{ .more {{ grid-template-columns: 1fr 1fr; }} }}
</style></head><body>
<h1>统一验收盲评</h1>
<p>每道题 {len(ARMS)} 份成品，用同一份任务说明和数据，都是 gpt-6.1-sol 各跑一次。其中一份不带技能，一份带技能；每道题的顺序都单独打乱了，对应关系在 KEY.md，评完再看。</p>
<p>每道题选出你更喜欢的（多份时排个名次，比如“试剂库：乙 > 甲”），分不出高低也直接说“分不出”。有余力的话，说说最好的那份好在哪。点图片看原图，点“打开来操作”可以真的用。</p>
{"".join(sections)}
</body></html>'''
(out / 'index.html').write_text(html, encoding='utf-8')
(out / 'KEY.md').write_text('# 对应关系\n\n' + '\n\n'.join(key) + '\n', encoding='utf-8')
print('\n'.join(key))
