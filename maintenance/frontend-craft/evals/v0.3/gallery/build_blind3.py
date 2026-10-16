import base64, json, random, pathlib, subprocess, os, html
E = pathlib.Path('/home/claude-dev/.local/share/fc-eval'); G = E / 'gallery'; J = G / 'blind-img'; J.mkdir(exist_ok=True)
BRIEF = {
 1: ("论文筛选工具页", "“我在读 Agent 方向的论文，这是我整理的一批论文和阅读记录。帮我做一个论文筛选页面：能快速浏览、按方向筛选、看出哪些读过，方便我挑下一篇要读的。”"),
 2: ("中文导读阅读页", "“这是我写的一篇 ReAct 论文导读，帮我做成一个网页，电脑和手机上都要好读。”"),
 3: ("杂乱材料整理页", "“这是我们课题组招新的原始材料，写得比较乱。帮我做成一个招新页面，信息不要漏。”"),
 4: ("局部精修", "“这个页面首屏和手机上看着不太对，帮我修一下。”（原页面见本组第一列）"),
 5: ("订单管理后台（留出案例）", "“这是我们咖啡小店最近的订单数据。帮我做一个订单管理后台页面：一眼能看出今天要处理什么，能快速找到某个订单，能处理发货和退款。”"),
}
groups = [
 (5, 'Opus 5.5', {'v0.3.2': 'runs2/case5-opus-v032', 'v0.3': 'runs2/case5-opus-v03'}),
]
rng = random.Random(1016)
key, jobs_d, jobs_m = {}, [], []
def jpg(run, view):
    out = J / f"{run.replace('/', '_')}-{view}.jpg"
    src = E / run / 'final' / f'{view}-full.png'
    (jobs_d if view == 'desktop' else jobs_m).append(f'{src}={out}')
    return out
plan = []
for c, model, conds in groups:
    names = list(conds); rng.shuffle(names)
    gid = f'r3-c{c}-{model.split()[0].lower()}'
    key[gid] = {chr(65 + i): n for i, n in enumerate(names)}
    plan.append((gid, c, model, [(chr(65 + i), conds[n]) for i, n in enumerate(names)]))
    for _, run in plan[-1][3]:
        jpg(run, 'desktop'); jpg(run, 'mobile')
env = dict(os.environ, LD_LIBRARY_PATH=str(E / 'render/libs/lib'))
subprocess.run(['node', str(E / 'render/tojpeg2.mjs'), '960', '55', *jobs_d], check=True, env=env, cwd=E / 'render')
subprocess.run(['node', str(E / 'render/tojpeg2.mjs'), '390', '60', *jobs_m], check=True, env=env, cwd=E / 'render')
(G / 'blind3-key.json').write_text(json.dumps(key, ensure_ascii=False, indent=1))
def b64(p): return 'data:image/jpeg;base64,' + base64.b64encode(pathlib.Path(p).read_bytes()).decode()
def col(label, run, extra=''):
    d, m = jpg(run, 'desktop'), jpg(run, 'mobile')
    return (f'<div class="cond{extra}"><h4>{label}</h4><div class="pair">'
            f'<figure class="shot desk"><div class="scroll" tabindex="0" aria-label="{label} 桌面整页，可滚动"><img src="{b64(d)}" alt="{label} 桌面 1280 整页" loading="lazy"></div><figcaption><span>桌面 1280</span><button type="button" class="zoom" data-w="1280">原尺寸</button></figcaption></figure>'
            f'<figure class="shot phone"><div class="scroll" tabindex="0" aria-label="{label} 手机整页，可滚动"><img src="{b64(m)}" alt="{label} 手机 390 整页" loading="lazy"></div><figcaption><span>手机 390</span><button type="button" class="zoom" data-w="390">原尺寸</button></figcaption></figure>'
            f'</div></div>')
sections = []
last_case = None
for gid, c, model, cols in plan:
    head = ''
    if c != last_case:
        name, brief = BRIEF[c]
        head = f'<header class="case-head"><p class="case-no">案例 {c}</p><h2>{name}</h2><p class="brief">{html.escape(brief)}</p></header>'
        last_case = c
    letters = [l for l, _ in cols]
    cells = ''.join(col(l, r) for l, r in cols)
    if c == 4: cells = col('修改前（参照）', 'runs/case4-original', ' ref') + cells
    opts = ''.join(f'<label><input type="radio" name="{gid}" value="{l}" id="{gid}-{l}"> {l}</label>' for l in letters)
    opts += f'<label><input type="radio" name="{gid}" value="差不多" id="{gid}-same"> 差不多</label><label><input type="radio" name="{gid}" value="都不好" id="{gid}-bad"> 都不好</label>'
    sections.append(f'''{head}<section class="group" data-gid="{gid}" data-title="案例{c} {model}">
<h3>{model}</h3><div class="conds n{len(cols) + (1 if c == 4 else 0)}">{cells}</div>
<fieldset class="pick"><legend>这一组你最喜欢哪一版？</legend><div class="opts">{opts}</div>
<label class="why" for="{gid}-why">一句理由</label><input type="text" id="{gid}-why" class="why-in" placeholder="比如：B 的列表一眼能扫完，A 太空"></fieldset></section>''')
page = (G / 'blind3-template.html').read_text(encoding='utf-8').replace('{{GROUPS}}', '\n'.join(sections))
(G / 'blind3.html').write_text(page, encoding='utf-8')
print(len(page) // 1024, 'KB')
