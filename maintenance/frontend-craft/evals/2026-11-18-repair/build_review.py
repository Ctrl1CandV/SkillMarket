# 组装盲选页：把三份成品（带技能、不带技能、优化者手做）匿名成 甲 / 乙 / 丙，生成 review/index.html。
#   python build_review.py <截图目录> <S 成品目录> <N 成品目录> <手做练习目录>
# 截图目录里要有 S/、N/、mine/ 三个子目录，各含 list.png、detail.png、new.png、stats.png、list-390.png。
# 对应关系写在 review/KEY.md，看完再打开。
import random, shutil, sys
from pathlib import Path
from PIL import Image

shots, s_dir, n_dir, mine_dir = [Path(p) for p in sys.argv[1:5]]
here = Path(__file__).parent
out = here / 'review'
if out.exists():
    shutil.rmtree(out)
out.mkdir()

arms = ['S', 'N', 'mine']
random.Random(1118).shuffle(arms)
labels = dict(zip(arms, ['甲', '乙', '丙']))
slots = dict(zip(arms, ['p1', 'p2', 'p3']))
entry = {'S': 'index.html', 'N': 'index.html', 'mine': 'a/index.html'}
skip = shutil.ignore_patterns('BRIEF.md', 'ENV.md', 'checks', 'tests', '*.md', 'b', 'shots', 'node_modules')
shutil.copytree(s_dir, out / slots['S'], ignore=skip)
shutil.copytree(n_dir, out / slots['N'], ignore=skip)
shutil.copytree(mine_dir, out / slots['mine'], ignore=skip)

pages = [('list', '工单列表'), ('detail', '工单详情'), ('new', '新建报修'), ('stats', '近两周情况')]
for arm in arms:
    d = out / 'img' / slots[arm]
    d.mkdir(parents=True)
    for name, _ in pages:
        im = Image.open(shots / arm / f'{name}.png').convert('RGB').crop((0, 0, 1440, 900))
        im.save(d / f'{name}.jpg', quality=88)
    im = Image.open(shots / arm / 'list-390.png').convert('RGB')
    im.crop((0, 0, 390, 844)).save(d / 'phone.jpg', quality=88)

blocks = []
for arm in sorted(arms, key=lambda a: '甲乙丙'.index(labels[a])):
    s = slots[arm]
    figs = ''.join(f'<figure><a href="img/{s}/{n}.jpg"><img src="img/{s}/{n}.jpg" alt="{labels[arm]}：{t}" loading="lazy"></a><figcaption>{t}</figcaption></figure>' for n, t in pages[1:])
    blocks.append(f'''<section>
<h2>{labels[arm]} <a class="open" href="{s}/{entry[arm]}">打开来操作 →</a></h2>
<figure class="main"><a href="img/{s}/list.jpg"><img src="img/{s}/list.jpg" alt="{labels[arm]}：工单列表"></a><figcaption>工单列表，1440 宽的第一屏</figcaption></figure>
<div class="more">{figs}<figure class="phone"><a href="img/{s}/phone.jpg"><img src="img/{s}/phone.jpg" alt="{labels[arm]}：手机上的工单列表" loading="lazy"></a><figcaption>手机</figcaption></figure></div>
</section>''')

html = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>报修处理台：三份成品</title>
<style>
:root {{ color-scheme: light; }}
body {{ margin: 0; padding: 2rem max(1.5rem, calc((100vw - 76rem) / 2)) 4rem; background: #f3f3f1; color: #1b1d1f; font: 1rem/1.6 "Microsoft YaHei UI", "Microsoft YaHei", system-ui, sans-serif; }}
h1 {{ font-size: 1.5rem; margin: 0 0 0.25rem; }}
p {{ margin: 0.25rem 0; max-width: 46rem; color: #454a4f; }}
section {{ margin-top: 3rem; padding-top: 1.25rem; border-top: 2px solid #1b1d1f; }}
h2 {{ display: flex; align-items: baseline; gap: 1rem; margin: 0 0 1rem; font-size: 1.75rem; }}
h2 .open {{ font-size: 1rem; font-weight: 400; color: #1b1d1f; }}
figure {{ margin: 0; }}
img {{ display: block; width: 100%; height: auto; border: 1px solid #c9ccce; background: #fff; }}
figcaption {{ margin-top: 0.375rem; font-size: 0.8125rem; color: #5c6268; }}
.more {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)) minmax(0, 0.42fr); gap: 1rem; margin-top: 1rem; align-items: start; }}
@media (max-width: 800px) {{ .more {{ grid-template-columns: 1fr 1fr; }} }}
</style></head><body>
<h1>报修处理台：三份成品</h1>
<p>同一份任务说明、同一份数据。三份里有一份带技能、一份不带技能（都是 gpt-6.1-sol，各跑一次），一份是优化者手做的。顺序是打乱的，对应关系在 KEY.md，选完再看。</p>
<p>请按“好用、好看”排个名次，再说说最好的那份好在哪、最差的那份差在哪。点图片看原图，点“打开来操作”可以真的用。</p>
{''.join(blocks)}
</body></html>'''
(out / 'index.html').write_text(html, encoding='utf-8')
names = {'S': '带技能（frontend-craft 0.7.0 + product-design 0.3.0，gpt-6.1-sol）', 'N': '不带技能（gpt-6.1-sol）', 'mine': '优化者手做（方向 A）'}
(out / 'KEY.md').write_text('# 对应关系\n\n' + '\n'.join(f'- {labels[a]}：{names[a]}' for a in sorted(arms, key=lambda a: '甲乙丙'.index(labels[a]))) + '\n', encoding='utf-8')
print({labels[a]: a for a in arms})
