# 三道系统题的示例数据（固定随机种子，重跑结果相同）。人名、电话、论文都是编的。
#   python make_data.py   ->  clubs/data、lab/data、papers/data 下各一份 .json 和同内容的 .js
import json, random
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
SUR = '王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许邓冯韩曹彭曾萧田董潘袁蔡蒋余于杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤'
GIVEN = ['一鸣', '雨桐', '子涵', '浩然', '思远', '佳怡', '晨曦', '宇航', '梓萱', '明轩', '欣妍', '嘉豪', '若溪', '俊杰', '静怡', '天佑', '可馨',
         '文博', '语嫣', '志强', '晓彤', '睿', '楠', '悦', '晗', '一诺', '子墨', '诗涵', '浩宇', '雅琪', '博文', '心怡', '俊熙', '梦瑶']


def person(r):
    return r.choice(SUR) + r.choice(GIVEN)


def fmt(t):
    return t.strftime('%Y-%m-%dT%H:%M')


def write(task, name, obj, var):
    d = HERE / task / 'data'
    d.mkdir(parents=True, exist_ok=True)
    (d / f'{name}.json').write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')
    (d / f'{name}.js').write_text(f'window.{var} = ' + json.dumps(obj, ensure_ascii=False) + ';\n', encoding='utf-8')


# ---------- 1. 社团活动报名 ----------
def clubs():
    r = random.Random(1801)
    now = datetime(2026, 11, 18, 20, 30)
    club_list = [
        ('摄影社', '镜头里的校园'), ('天文社', '一起看星星'), ('辩论队', '把话说清楚'), ('徒步社', '周末去山里'),
        ('吉他社', '弹唱与合奏'), ('志愿者协会', '社区与支教'), ('机器人社', '造东西的人'), ('读书会', '每周一本书'),
        ('街舞社', 'Breaking 与 Popping'), ('围棋社', '黑白之间'), ('电影社', '放映与讨论'), ('烘焙社', '做点甜的'),
    ]
    places = ['图书馆报告厅', '大学生活动中心 201', '东区操场', '理科楼 B302', '艺术楼小剧场', '南门集合', '创新实验室', '二食堂三楼', '体育馆舞蹈室', '学术交流中心']
    kinds = ['讲座', '工作坊', '比赛', '户外', '演出', '放映', '志愿']
    templates = [
        ('摄影社', '工作坊', '夜景人像：用手机拍出好看的夜景', 25, 0, '带手机或相机；不需要基础。拍完当场挑三张讲评。'),
        ('摄影社', '户外', '银杏大道扫街', 30, 0, '早上 7 点光线最好，迟到不等。'),
        ('摄影社', '比赛', '“秋日校园”摄影比赛作品提交与评选', 200, 0, '每人最多交 3 张，评选结果在 12 月 1 日公布。'),
        ('天文社', '户外', '双子座流星雨观测夜', 40, 15, '凌晨 1 点到 4 点在东区操场，费用含热饮和防潮垫。下雨取消，会提前一天通知。'),
        ('天文社', '讲座', '从地面到深空：业余望远镜入门', 120, 0, '讲座后可以上手操作社团的两台望远镜。'),
        ('辩论队', '比赛', '新生杯辩论赛半决赛', 300, 0, '观众席，不需要报名也能来；报名的同学有前排座位。'),
        ('辩论队', '工作坊', '一小时学会立论', 30, 0, '会分组练习，请带纸笔。'),
        ('徒步社', '户外', '九峰山徒步（12 公里）', 35, 45, '费用含往返大巴和保险。需要穿登山鞋，体力一般的同学慎报。'),
        ('徒步社', '户外', '城市夜徒步：沿江 8 公里', 50, 0, '晚上 7 点南门集合，全程平路。'),
        ('吉他社', '演出', '冬季弹唱专场', 180, 0, '艺术楼小剧场，凭报名二维码入场。'),
        ('吉他社', '工作坊', '零基础四个和弦弹一首歌', 20, 0, '社团提供吉他 15 把，自带更好。'),
        ('志愿者协会', '志愿', '社区老人智能手机教学', 16, 0, '每位志愿者带两位老人，需参加周五晚上的 30 分钟培训。'),
        ('志愿者协会', '志愿', '图书馆旧书整理', 12, 0, '可以计志愿时长 3 小时。'),
        ('机器人社', '比赛', '校内循迹小车赛', 24, 0, '两人一队报名（报名一人即可，队友写在备注里）。小车社团提供。'),
        ('机器人社', '工作坊', 'Arduino 入门：让 LED 跟着音乐闪', 18, 20, '费用是材料费，做好的板子带走。'),
        ('读书会', '讲座', '《置身事内》共读第三次', 25, 0, '读到第五章即可参加。'),
        ('读书会', '讲座', '作者见面会：写作这件事', 150, 0, '提问环节请提前在报名备注里写问题。'),
        ('街舞社', '工作坊', 'Popping 基础律动', 30, 0, '穿运动鞋。'),
        ('街舞社', '演出', '年终 Battle', 260, 0, '体育馆，观众免费入场。'),
        ('围棋社', '比赛', '新人让子赛', 32, 0, '会下棋即可，社团按水平分组。'),
        ('电影社', '放映', '放映：《海上钢琴师》+ 讨论', 80, 0, '片长 2 小时 45 分钟。'),
        ('电影社', '放映', '短片之夜：学生作品展映', 80, 0, '有 5 部学生短片，导演在场。'),
        ('烘焙社', '工作坊', '圣诞姜饼人', 16, 30, '费用是材料费，烤好的饼干带走。名额少，报名后不来请提前取消。'),
        ('烘焙社', '工作坊', '戚风蛋糕零失败', 12, 35, ''),
        ('天文社', '讲座', '月球上的环形山都叫什么名字', 60, 0, ''),
        ('摄影社', '讲座', '胶片冲洗演示', 20, 0, '暗房一次只能进 10 人，分两批。'),
        ('志愿者协会', '志愿', '周末马拉松补给站', 40, 0, '早上 6 点集合，提供早餐和纪念 T 恤。'),
        ('辩论队', '讲座', '往届冠军经验分享', 100, 0, ''),
    ]
    acts = []
    for i, (club, kind, title, cap, fee, note) in enumerate(templates):
        day = now.date() + timedelta(days=r.randint(-3, 13))
        hour = {'户外': r.choice([7, 9]), '志愿': r.choice([9, 14])}.get(kind, r.choice([14, 16, 19, 19, 20]))
        if '夜' in title: hour = 19
        if '马拉松' in title: hour = 6
        if '流星雨' in title: day, hour = (now + timedelta(days=4)).date(), 1
        start = datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=r.choice([0, 0, 30]))
        length = {'户外': r.choice([3, 4, 6]), '演出': 2, '放映': 3, '比赛': r.choice([2, 3]), '志愿': r.choice([3, 4])}.get(kind, r.choice([1, 2]))
        deadline = start - timedelta(hours=r.choice([2, 12, 24, 48]))
        fill = r.random()
        signed = cap if fill > 0.82 else int(cap * (0.85 + 0.14 * r.random())) if fill > 0.6 else int(cap * r.random() * 0.8)
        if start < now: signed = min(cap, signed + r.randint(0, 3))
        waitlist = r.randint(1, 9) if signed >= cap and start > now else 0
        place = '东区操场' if '流星' in title else '南门集合' if '徒步' in title else '艺术楼小剧场' if '弹唱' in title else '体育馆舞蹈室' if '街舞' in club and kind == '工作坊' else '体育馆' if 'Battle' in title else r.choice(places)
        acts.append({'id': f'A{i + 1:02d}', 'club': club, 'kind': kind, 'title': title, 'start': fmt(start), 'end': fmt(start + timedelta(hours=length)),
                     'place': place, 'capacity': cap, 'signed': signed, 'waitlist': waitlist, 'fee': fee, 'deadline': fmt(deadline), 'note': note,
                     'contact': person(r) + ' 138-0000-' + str(r.randint(2000, 9999))})
    acts.sort(key=lambda a: a['start'])
    me = {'name': '林雨桐', 'student_id': '20240317', 'phone': '139-0000-5821'}
    mine = []
    for a in acts:
        if a['id'] in ('A02', 'A05', 'A08', 'A11', 'A21'):
            at = min(datetime.fromisoformat(a['start']) - timedelta(days=r.randint(2, 6)), now - timedelta(hours=r.randint(3, 60)))
            mine.append({'activity': a['id'], 'status': '候补第 3 位' if a['waitlist'] else '已报名', 'at': fmt(at)})
    # 摄影社负责人看到的名单
    roster = {}
    for a in acts:
        if a['club'] != '摄影社':
            continue
        people = []
        for k in range(min(a['signed'], 40)):
            people.append({'name': person(r), 'student_id': f'2024{r.randint(1000, 9999)}' if r.random() < 0.6 else f'2023{r.randint(1000, 9999)}',
                           'phone': f'139-0000-{r.randint(2000, 9999)}', 'at': fmt(datetime.fromisoformat(a['start']) - timedelta(days=r.randint(1, 8), minutes=r.randint(0, 900))),
                           'note': r.choice(['', '', '', '', '用手机拍', '想学夜景', '和室友一起', '第一次参加', '可能晚到 10 分钟']),
                           'checked_in': datetime.fromisoformat(a['start']) < now and r.random() < 0.85})
        roster[a['id']] = people
    write('clubs', 'clubs', {'now': fmt(now), 'me': me, 'clubs': [{'name': c, 'tagline': t} for c, t in club_list], 'activities': acts, 'my_signups': mine,
                             'manager_of': '摄影社', 'rosters': roster}, 'CLUB_DATA')
    print('clubs', len(acts), 'activities')


# ---------- 2. 共享仪器预约 ----------
def lab():
    r = random.Random(1802)
    now = datetime(2026, 11, 18, 10, 40)
    insts = [
        {'id': 'sem', 'name': '扫描电子显微镜', 'model': 'SU8010', 'room': '理科楼 B105', 'slot_hours': 2, 'needs_training': True, 'needs_approval': True, 'fee_per_hour': 150,
         'note': '样品需提前喷金；磁性样品不能上机。'},
        {'id': 'confocal', 'name': '激光共聚焦显微镜', 'model': 'LSM 900', 'room': '生科楼 312', 'slot_hours': 1, 'needs_training': True, 'needs_approval': False, 'fee_per_hour': 120,
         'note': '活细胞实验请预约 2 小时以上并自带培养皿。'},
        {'id': 'flow', 'name': '流式细胞仪', 'model': 'CytoFLEX S', 'room': '生科楼 310', 'slot_hours': 1, 'needs_training': True, 'needs_approval': False, 'fee_per_hour': 100,
         'note': '最后一位使用者负责清洗管路。'},
        {'id': 'xrd', 'name': 'X 射线衍射仪', 'model': 'D8 Advance', 'room': '材料楼 101', 'slot_hours': 1, 'needs_training': True, 'needs_approval': True, 'fee_per_hour': 80,
         'note': '粉末样品至少 0.2 克。'},
        {'id': 'lcms', 'name': '液相色谱质谱联用仪', 'model': '6545 Q-TOF', 'room': '化学楼 205', 'slot_hours': 4, 'needs_training': False, 'needs_approval': True, 'fee_per_hour': 200,
         'note': '由仪器管理员上机，预约时写清样品数和方法。'},
        {'id': 'print3d', 'name': '3D 打印机', 'model': 'Bambu X1', 'room': '创新实验室', 'slot_hours': 2, 'needs_training': False, 'needs_approval': False, 'fee_per_hour': 10,
         'note': '只打 PLA；超过 8 小时的打印请分段预约。'},
    ]
    groups = ['张老师课题组', '刘老师课题组', '陈老师课题组', '黄老师课题组', '周老师课题组', '吴老师课题组']
    users = [{'name': person(r), 'group': r.choice(groups), 'trained': [i['id'] for i in insts if i['needs_training'] and r.random() < 0.4]} for _ in range(18)]
    me = {'name': '许静怡', 'group': '陈老师课题组', 'trained': ['confocal', 'flow']}
    users.append(me)
    days = [(now.date() + timedelta(days=d)) for d in range(-2, 8)]
    bookings = []
    n = 0
    for inst in insts:
        for d in days:
            if d.weekday() >= 5 and r.random() < 0.7:
                continue
            h = 8
            while h + inst['slot_hours'] <= 22:
                if r.random() < (0.55 if h < 18 else 0.25):
                    u = r.choice(users[:-1])
                    length = inst['slot_hours'] * r.choice([1, 1, 1, 2])
                    if h + length > 22:
                        break
                    start = datetime.combine(d, datetime.min.time()).replace(hour=h)
                    status = '已确认'
                    if inst['needs_approval'] and start > now and r.random() < 0.3:
                        status = '待审批'
                    if start + timedelta(hours=length) <= now:
                        status = r.choice(['已完成', '已完成', '已完成', '未到场'])
                    n += 1
                    bookings.append({'id': f'B{n:03d}', 'instrument': inst['id'], 'user': u['name'], 'group': u['group'], 'start': fmt(start), 'end': fmt(start + timedelta(hours=length)),
                                     'status': status, 'purpose': r.choice(['样品形貌观察', '细胞成像', '凋亡检测', '晶型鉴定', '代谢物筛查', '零件打样', '预实验', '论文补实验']),
                                     'samples': r.randint(1, 12)})
                    h += length
                else:
                    h += inst['slot_hours']
    for b in bookings:   # 我自己的几条
        pass
    mine = [
        {'instrument': 'confocal', 'start': '2026-11-19T14:00', 'hours': 2, 'status': '已确认', 'purpose': '活细胞钙成像'},
        {'instrument': 'flow', 'start': '2026-11-20T09:00', 'hours': 1, 'status': '已确认', 'purpose': '凋亡检测'},
        {'instrument': 'sem', 'start': '2026-11-21T10:00', 'hours': 2, 'status': '待审批', 'purpose': '支架材料表面形貌'},
        {'instrument': 'flow', 'start': '2026-11-16T15:00', 'hours': 1, 'status': '已完成', 'purpose': '预实验'},
    ]
    for m in mine:
        s = datetime.fromisoformat(m['start'])
        clash = [b for b in bookings if b['instrument'] == m['instrument'] and not (datetime.fromisoformat(b['end']) <= s or datetime.fromisoformat(b['start']) >= s + timedelta(hours=m['hours']))]
        for c in clash:
            bookings.remove(c)
        n += 1
        bookings.append({'id': f'B{n:03d}', 'instrument': m['instrument'], 'user': me['name'], 'group': me['group'], 'start': m['start'], 'end': fmt(s + timedelta(hours=m['hours'])),
                         'status': m['status'], 'purpose': m['purpose'], 'samples': r.randint(2, 8)})
    bookings.sort(key=lambda b: (b['start'], b['instrument']))
    maintenance = [{'instrument': 'xrd', 'start': '2026-11-20T08:00', 'end': '2026-11-20T18:00', 'reason': '年度校准'}]
    write('lab', 'lab', {'now': fmt(now), 'me': me, 'admin_of': ['sem', 'xrd', 'lcms'], 'instruments': insts, 'users': users, 'bookings': bookings, 'maintenance': maintenance,
                         'rules': {'cancel_free_hours': 24, 'no_show_limit': 3, 'open_hours': '每天 8:00–22:00', 'book_ahead_days': 7}}, 'LAB_DATA')
    print('lab', len(bookings), 'bookings')


# ---------- 3. 课题组文献库 ----------
def papers():
    r = random.Random(1803)
    now = datetime(2026, 11, 18, 16, 0)
    members = ['陈老师', '许静怡', '唐文博', '梁可馨', '何雨桐', '罗俊杰']
    topics = {
        '长文本': ['Efficient Long-Context Attention via {x}', 'Scaling {x} to Million-Token Contexts', 'Where Does Long-Context Retrieval Fail? A {x} Study'],
        '检索增强': ['Retrieval-Augmented Generation with {x}', 'When to Retrieve: {x} for RAG', 'Faithful Citation in RAG through {x}'],
        '评测': ['A Benchmark for {x} in Language Models', 'Rethinking {x} Evaluation', 'Contamination-Aware {x} Evaluation'],
        '对齐': ['Preference Optimization with {x}', 'Reward Hacking in {x}', 'Self-Critique for {x}'],
        '推理': ['Chain-of-Thought {x}', 'Process Supervision for {x}', 'Test-Time Compute Scaling for {x}'],
        '多模态': ['Grounded {x} for Vision-Language Models', 'Document Understanding with {x}', 'Chart Question Answering via {x}'],
    }
    fills = ['Sparse Routing', 'Learned Memory', 'Hierarchical Chunking', 'Contrastive Signals', 'Uncertainty Estimates', 'Synthetic Data', 'Small Verifiers',
             'Curriculum Sampling', 'Latent Planning', 'Token Pruning', 'Mixture of Experts', 'Structured Prompts', 'Multi-Agent Debate', 'Calibration']
    venues = ['ACL', 'EMNLP', 'NAACL', 'NeurIPS', 'ICLR', 'ICML', 'arXiv', 'arXiv', 'arXiv', 'TACL', 'COLM', 'CVPR']
    last = ['Wang', 'Li', 'Zhang', 'Liu', 'Chen', 'Kim', 'Park', 'Smith', 'Garcia', 'Nguyen', 'Müller', 'Rossi', 'Tanaka', 'Singh', 'Cohen', 'Ivanova', 'Okafor']
    first = ['A.', 'B.', 'C.', 'D.', 'E.', 'F.', 'H.', 'J.', 'K.', 'L.', 'M.', 'N.', 'P.', 'R.', 'S.', 'T.', 'Y.']
    notes_pool = ['方法和我们的想法很像，区别在于它用了外部记忆。', '实验只在英文上做，中文效果存疑。', '表 3 的基线设置不公平，没调参。', '附录 B 的消融值得看。',
                  '代码开源了，可以直接复现。', '和组会上讲的那篇结论相反。', '主要贡献是数据集，方法一般。', '可以作为相关工作引用。', '推导没看懂，第 4 节需要再读。',
                  '用的指标我们也可以用。', '训练成本太高，我们做不了。', '这篇是综述，适合新人入门。']
    out = []
    for i in range(96):
        tag = r.choice(list(topics))
        title = r.choice(topics[tag]).format(x=r.choice(fills))
        year = r.choice([2023, 2024, 2024, 2025, 2025, 2025, 2026, 2026])
        venue = r.choice(venues)
        authors = [f'{r.choice(first)} {r.choice(last)}' for _ in range(r.randint(2, 8))]
        added = now - timedelta(days=r.randint(0, 200), hours=r.randint(0, 20))
        tags = sorted({tag} | ({r.choice(list(topics))} if r.random() < 0.35 else set()))
        reads = {}
        for m in members:
            p = r.random()
            if p < 0.18:
                reads[m] = '读完'
            elif p < 0.28:
                reads[m] = '在读'
        notes = [{'who': m, 'at': fmt(added + timedelta(days=r.randint(0, 30))), 'text': r.choice(notes_pool)} for m in reads if reads[m] == '读完' and r.random() < 0.55]
        doi = f'10.{r.randint(1000, 9999)}/{venue.lower()}.{year}.{r.randint(100, 999)}' if venue != 'arXiv' else ''
        arxiv = f'{str(year)[2:]}{r.randint(1, 12):02d}.{r.randint(10000, 29999)}'
        abstract = (f'We study {tag_en(tag)} and propose {title.split(" ")[-1].lower()}-based methods. Experiments on {r.randint(3, 9)} benchmarks show '
                    f'improvements of {r.randint(1, 9)}.{r.randint(0, 9)} points over strong baselines, with {r.choice(["lower", "comparable", "higher"])} compute cost. '
                    f'We release code and data.')
        out.append({'id': f'P{i + 1:03d}', 'title': title, 'authors': authors, 'year': year, 'venue': venue, 'doi': doi, 'arxiv': arxiv, 'tags': tags,
                    'added_by': r.choice(members), 'added': fmt(added), 'abstract': abstract, 'reading': reads, 'notes': notes,
                    'pdf': r.random() < 0.8, 'starred_by': [m for m in members if r.random() < 0.08]})
    out.sort(key=lambda p: p['added'], reverse=True)
    meeting = {'next': '2026-11-20T15:00', 'presenter': '唐文博', 'paper': out[3]['id'], 'queue': [{'presenter': m, 'paper': out[r.randint(5, 40)]['id'], 'date': d}
                                                                                                  for m, d in zip(['梁可馨', '何雨桐', '罗俊杰'], ['2026-11-27', '2026-12-04', '2026-12-11'])]}
    write('papers', 'papers', {'now': fmt(now), 'me': '许静怡', 'members': members, 'tags': list(topics), 'papers': out, 'meeting': meeting}, 'PAPER_DATA')
    print('papers', len(out), 'papers')


def tag_en(tag):
    return {'长文本': 'long-context modeling', '检索增强': 'retrieval augmentation', '评测': 'evaluation', '对齐': 'alignment', '推理': 'reasoning', '多模态': 'multimodal understanding'}[tag]


clubs()
lab()
papers()
