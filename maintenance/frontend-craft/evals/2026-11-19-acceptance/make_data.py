# 统一验收三道新题的示例数据（固定随机种子，重跑结果相同）。人名、试剂批号、论文题目、文档内容都是编的。
#   python make_data.py   ->  reagents/data、defense/data、translate/data 下各一份 .json 和同内容的 .js
import json, random
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
SUR = '王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许邓冯韩曹彭曾萧田董潘袁蔡蒋余于杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江'
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


# ---------- 1. 课题组试剂与耗材库 ----------
def reagents():
    r = random.Random(1901)
    now = datetime(2026, 11, 19, 10, 0)
    members = ['周老师', '何雨桐', '陈思远', '林晨曦', '赵子墨', '孙佳怡', '吴浩宇', '郑可馨']
    me = '何雨桐'
    places = ['4℃ 冰箱 A 上层', '4℃ 冰箱 A 下层', '-20℃ 冰箱 B', '-80℃ 冰箱 第 2 架', '试剂柜 1（常温）', '试剂柜 2（常温）', '易燃品柜', '酸碱柜', '耗材架 左', '耗材架 右']
    items = [
        # 名称, 类别, 规格单位, 存放, 危险, 每批数量范围
        ('无水乙醇', '溶剂', 'mL', '易燃品柜', '易燃', (500, 2500)), ('甲醇（色谱纯）', '溶剂', 'mL', '易燃品柜', '易燃 有毒', (500, 4000)),
        ('乙腈（色谱纯）', '溶剂', 'mL', '易燃品柜', '易燃 有毒', (500, 4000)), ('丙酮', '溶剂', 'mL', '易燃品柜', '易燃', (500, 2500)),
        ('二甲基亚砜 DMSO', '溶剂', 'mL', '试剂柜 1（常温）', '', (100, 500)), ('浓盐酸 37%', '酸碱', 'mL', '酸碱柜', '腐蚀', (250, 1000)),
        ('氢氧化钠', '酸碱', 'g', '酸碱柜', '腐蚀', (100, 500)), ('冰醋酸', '酸碱', 'mL', '酸碱柜', '腐蚀 易燃', (250, 500)),
        ('Tris 碱', '缓冲液', 'g', '试剂柜 1（常温）', '', (100, 500)), ('PBS 缓冲液 10×', '缓冲液', 'mL', '4℃ 冰箱 A 下层', '', (500, 1000)),
        ('HEPES', '缓冲液', 'g', '试剂柜 1（常温）', '', (25, 100)), ('EDTA 二钠', '缓冲液', 'g', '试剂柜 1（常温）', '', (100, 250)),
        ('胎牛血清 FBS', '细胞培养', 'mL', '-20℃ 冰箱 B', '', (50, 500)), ('DMEM 高糖培养基', '细胞培养', 'mL', '4℃ 冰箱 A 上层', '', (500, 500)),
        ('胰蛋白酶 0.25%', '细胞培养', 'mL', '-20℃ 冰箱 B', '', (100, 100)), ('青霉素-链霉素 100×', '细胞培养', 'mL', '-20℃ 冰箱 B', '', (100, 100)),
        ('Taq DNA 聚合酶', '分子生物学', 'U', '-20℃ 冰箱 B', '', (500, 1000)), ('dNTP 混合液', '分子生物学', 'μL', '-20℃ 冰箱 B', '', (200, 500)),
        ('琼脂糖', '分子生物学', 'g', '试剂柜 2（常温）', '', (50, 250)), ('核酸染料（替代 EB）', '分子生物学', 'μL', '4℃ 冰箱 A 上层', '', (500, 500)),
        ('DNA Marker 2000', '分子生物学', 'μL', '-20℃ 冰箱 B', '', (250, 500)), ('逆转录试剂盒', '分子生物学', '次', '-20℃ 冰箱 B', '', (50, 100)),
        ('质粒小提试剂盒', '分子生物学', '次', '试剂柜 2（常温）', '', (50, 200)), ('BCA 蛋白定量试剂盒', '蛋白', '次', '4℃ 冰箱 A 下层', '', (100, 500)),
        ('RIPA 裂解液', '蛋白', 'mL', '4℃ 冰箱 A 下层', '', (100, 100)), ('蛋白酶抑制剂', '蛋白', '片', '-20℃ 冰箱 B', '', (20, 20)),
        ('SDS', '蛋白', 'g', '试剂柜 2（常温）', '有害', (100, 500)), ('丙烯酰胺溶液 30%', '蛋白', 'mL', '4℃ 冰箱 A 下层', '有毒', (500, 500)),
        ('TEMED', '蛋白', 'mL', '4℃ 冰箱 A 下层', '易燃 腐蚀', (25, 50)), ('过硫酸铵', '蛋白', 'g', '试剂柜 2（常温）', '氧化', (25, 100)),
        ('脱脂奶粉', '蛋白', 'g', '试剂柜 2（常温）', '', (250, 500)), ('ECL 发光液', '蛋白', 'mL', '4℃ 冰箱 A 上层', '', (100, 200)),
        ('一抗 β-actin', '抗体', 'μL', '-80℃ 冰箱 第 2 架', '', (100, 200)), ('二抗 羊抗兔 HRP', '抗体', 'μL', '-20℃ 冰箱 B', '', (100, 200)),
        ('二抗 羊抗鼠 HRP', '抗体', 'μL', '-20℃ 冰箱 B', '', (100, 200)), ('DAPI 染液', '抗体', 'μL', '4℃ 冰箱 A 上层', '有害', (500, 1000)),
        ('1.5 mL 离心管', '耗材', '个', '耗材架 左', '', (500, 2000)), ('PCR 八连管', '耗材', '条', '耗材架 左', '', (100, 500)),
        ('10 μL 枪头（盒装）', '耗材', '盒', '耗材架 左', '', (10, 40)), ('200 μL 枪头（盒装）', '耗材', '盒', '耗材架 左', '', (10, 40)),
        ('1 mL 枪头（盒装）', '耗材', '盒', '耗材架 左', '', (10, 30)), ('15 mL 离心管', '耗材', '个', '耗材架 右', '', (100, 500)),
        ('50 mL 离心管', '耗材', '个', '耗材架 右', '', (100, 300)), ('细胞培养皿 10 cm', '耗材', '个', '耗材架 右', '', (50, 200)),
        ('六孔板', '耗材', '个', '耗材架 右', '', (20, 100)), ('0.22 μm 滤器', '耗材', '个', '耗材架 右', '', (50, 100)),
        ('丁腈手套 M', '耗材', '盒', '耗材架 右', '', (5, 20)), ('丁腈手套 S', '耗材', '盒', '耗材架 右', '', (5, 20)),
        ('称量纸', '耗材', '包', '耗材架 左', '', (5, 20)), ('封口膜', '耗材', '卷', '耗材架 左', '', (2, 6)),
    ]
    reagents, usage = [], []
    for i, (name, cat, unit, place, hazard, (lo, hi)) in enumerate(items):
        nb = 1 if cat == '耗材' else r.choice([1, 1, 2, 2, 3])
        batches = []
        for b in range(nb):
            qty = r.randint(lo, hi)
            exp = None if cat == '耗材' else (now + timedelta(days=r.choice([-20, 8, 20, 45, 90, 200, 400, 700])))
            left = qty if b < nb - 1 else int(qty * r.choice([0.02, 0.08, 0.15, 0.3, 0.5, 0.7, 0.9, 1.0]))
            batches.append({'lot': f'{r.choice("ABCDEFGHKLMN")}{r.randint(10000, 99999)}', 'opened': fmt(now - timedelta(days=r.randint(3, 200))) if left < qty else None,
                            'qty': qty, 'left': left, 'expires': exp.strftime('%Y-%m-%d') if exp else None})
        total = sum(b['left'] for b in batches)
        reorder = max(1, int(sum(b['qty'] for b in batches) / max(1, nb) * 0.2))
        reagents.append({'id': f'R{i + 1:03d}', 'name': name, 'category': cat, 'unit': unit, 'place': place, 'hazard': hazard,
                         'supplier': r.choice(['国药', '阿拉丁', '麦克林', 'Thermo', 'Sigma', '碧云天', '生工', '耗材供应商甲']),
                         'cas': '' if cat in ('耗材', '抗体', '细胞培养', '分子生物学') else f'{r.randint(50, 9999)}-{r.randint(10, 99)}-{r.randint(0, 9)}',
                         'reorder_at': reorder, 'batches': batches, 'in_stock': total})
        for k in range(r.randint(0, 5)):
            who = r.choice(members[1:])
            usage.append({'reagent': f'R{i + 1:03d}', 'who': who, 'amount': max(1, int(reorder * r.uniform(0.1, 0.8))), 'at': fmt(now - timedelta(days=r.randint(0, 30), minutes=r.randint(0, 600))),
                          'purpose': r.choice(['Western', 'PCR', '细胞传代', '配缓冲液', '清洗', '预实验', '课题 A', '课题 B', ''])})
    usage.sort(key=lambda u: u['at'], reverse=True)
    requests = [
        {'id': 'Q01', 'reagent': 'R013', 'by': '林晨曦', 'at': fmt(now - timedelta(days=2)), 'qty': '500 mL × 2', 'status': '待采购', 'note': '下周要扩增细胞'},
        {'id': 'Q02', 'reagent': 'R039', 'by': '赵子墨', 'at': fmt(now - timedelta(days=5)), 'qty': '20 盒', 'status': '已下单', 'note': ''},
        {'id': 'Q03', 'reagent': 'R033', 'by': '陈思远', 'at': fmt(now - timedelta(days=1)), 'qty': '200 μL', 'status': '待采购', 'note': '旧批次过期了'},
        {'id': 'Q04', 'reagent': 'R047', 'by': '孙佳怡', 'at': fmt(now - timedelta(days=9)), 'qty': '10 盒', 'status': '已到货', 'note': ''},
        {'id': 'Q05', 'reagent': 'R002', 'by': '何雨桐', 'at': fmt(now - timedelta(hours=20)), 'qty': '4 L', 'status': '待采购', 'note': 'HPLC 流动相'},
        {'id': 'Q06', 'reagent': 'R022', 'by': '吴浩宇', 'at': fmt(now - timedelta(days=3)), 'qty': '2 盒', 'status': '已下单', 'note': ''},
    ]
    write('reagents', 'reagents', {'now': fmt(now), 'me': me, 'admin': '周老师', 'members': members, 'places': places, 'reagents': reagents, 'usage': usage, 'requests': requests}, 'REAGENT_DATA')
    print('reagents', len(reagents), 'items', len(usage), 'usage')


# ---------- 2. 研究生答辩安排 ----------
def defense():
    r = random.Random(1902)
    now = datetime(2026, 11, 19, 15, 0)
    faculty = [f'{s}老师' for s in '王李张刘陈杨黄赵吴周徐孙马朱胡']
    topics = ['图神经网络的可解释性', '低资源机器翻译', '联邦学习中的隐私保护', '时间序列异常检测', '多模态情感分析', '代码大模型的缺陷定位', '医学影像分割',
              '推荐系统的冷启动', '强化学习的样本效率', '知识图谱补全', '语音识别的方言适配', '无人机路径规划', '边缘设备上的模型压缩', '对比学习的负样本选择',
              '金融文本的事件抽取', '交通流预测', '小样本目标检测', '蛋白质结构预测的加速', '在线教育的知识追踪', '法律文书的自动摘要', '遥感图像变化检测',
              '工业缺陷检测', '对话系统的一致性', '图像超分辨率', '自动驾驶中的轨迹预测', '个性化文本生成', '因果推断在广告中的应用', '分布式训练的通信优化']
    rooms = ['计算机楼 301', '计算机楼 305', '学术报告厅 B', '图书馆研讨室 4']
    sessions = []
    days = [now.date() + timedelta(days=d) for d in (6, 6, 7, 8, 13, 14)]
    for i, d in enumerate(days):
        start = datetime.combine(d, datetime.min.time()).replace(hour=9 if i % 2 == 0 else 14)
        chair = faculty[i * 2 % len(faculty)]
        members = [chair] + r.sample([f for f in faculty if f != chair], 4)
        sessions.append({'id': f'S{i + 1}', 'start': fmt(start), 'room': rooms[i % len(rooms)], 'chair': chair, 'committee': members, 'secretary': '唐文博',
                         'capacity': 5, 'external': members[-1] + '（外校）'})
    students = []
    for i, topic in enumerate(topics):
        name = person(r)
        adv = r.choice(faculty)
        review = r.choice(['两份都通过', '两份都通过', '两份都通过', '一份通过，一份修改后通过', '一份还没返回', '两份都还没返回'])
        dup = r.choice([4.2, 6.8, 9.5, 11.3, 13.7, 3.1, 16.4, None])
        sess = None
        if review != '两份都还没返回' and i < 24:
            sess = sessions[min(i // 5, 5)]['id']
        students.append({'id': f'D{i + 1:02d}', 'name': name, 'student_id': f'2023{r.randint(10000, 99999)}', 'advisor': adv, 'degree': r.choice(['学硕', '学硕', '专硕']),
                         'title': f'面向{topic}的方法研究', 'review': review, 'duplicate_rate': dup,
                         'materials': {'答辩申请表': r.random() < 0.85, '论文终稿 PDF': r.random() < 0.7, '导师意见书': r.random() < 0.8, '成果清单': r.random() < 0.6},
                         'session': sess, 'order': None})
    for s in sessions:
        k = 1
        for st in students:
            if st['session'] == s['id']:
                st['order'] = k; k += 1
    me = students[7]['id']
    write('defense', 'defense', {'now': fmt(now), 'me': me, 'secretary': '唐文博', 'rules': {'duplicate_max': 10, 'minutes_each': 40, 'materials_due': '2026-11-23'},
                                 'faculty': faculty, 'sessions': sessions, 'students': students}, 'DEFENSE_DATA')
    print('defense', len(sessions), 'sessions', len(students), 'students')


# ---------- 3. 开源文档翻译协作 ----------
def translate():
    r = random.Random(1903)
    now = datetime(2026, 11, 19, 21, 0)
    parts = [('Getting Started', ['Installation', 'Your First Project', 'Project Structure', 'Configuration Basics', 'Running in Development']),
             ('Core Concepts', ['Components', 'State and Props', 'Lifecycle', 'Events', 'Rendering Lists', 'Conditional Rendering', 'Forms']),
             ('Routing', ['Defining Routes', 'Dynamic Segments', 'Nested Layouts', 'Navigation', 'Redirects', 'Route Guards']),
             ('Data Fetching', ['Fetching on the Server', 'Fetching on the Client', 'Caching', 'Revalidation', 'Error Handling', 'Loading States', 'Streaming']),
             ('Styling', ['CSS Modules', 'Global Styles', 'Theming', 'Dark Mode', 'Responsive Design']),
             ('Testing', ['Unit Tests', 'Component Tests', 'End-to-End Tests', 'Mocking Network Requests', 'Snapshot Testing']),
             ('Deployment', ['Building for Production', 'Static Export', 'Environment Variables', 'Deploying to a Server', 'Monitoring']),
             ('Advanced', ['Performance', 'Code Splitting', 'Internationalization', 'Accessibility', 'Security Headers', 'Migrating from v3', 'Plugin API', 'Custom Compiler Options']),
             ('API Reference', ['Configuration File', 'Command Line', 'Hooks', 'Utilities', 'Error Codes', 'Glossary of Terms'])]
    vols = list(dict.fromkeys(person(r) for _ in range(40)))[:26]
    me = vols[3]
    reviewers = vols[:5]
    chapters, n = [], 0
    for pi, (part, titles) in enumerate(parts):
        for ti, title in enumerate(titles):
            n += 1
            words = r.randint(400, 3800)
            st = r.choices(['未认领', '翻译中', '待审校', '审校中', '已完成'], [3, 3, 2, 1, 4])[0]
            if pi >= 7: st = r.choice(['未认领', '未认领', '翻译中'])
            who = None if st == '未认领' else r.choice(vols)
            if n in (4, 11, 19, 27): who, st = me, ['翻译中', '待审校', '翻译中', '已完成'][[4, 11, 19, 27].index(n)]
            claimed = now - timedelta(days=r.randint(1, 40)) if who else None
            due = claimed + timedelta(days=21) if claimed and st in ('翻译中',) else None
            comments = []
            if st in ('审校中', '已完成') or n == 11:
                for _ in range(r.randint(1, 4)):
                    comments.append({'by': r.choice(reviewers), 'para': r.randint(1, 12), 'text': r.choice(['“render”这里译成“渲染”，和术语表一致。', '这句语序太像英文，建议拆成两句。',
                                     '代码块里的注释也要译。', '链接文字不要译成“点击这里”。', '“hydration”术语表里是“水合”，不要写成“注水”。', '这段漏译了最后一句。', '数字和单位之间加空格。'])})
            chapters.append({'id': f'C{n:03d}', 'part': part, 'title': title, 'words': words, 'status': st, 'translator': who,
                             'reviewer': r.choice(reviewers) if st in ('审校中', '已完成', '待审校') and r.random() < 0.8 else None,
                             'claimed_at': fmt(claimed) if claimed else None, 'due': due.strftime('%Y-%m-%d') if due else None,
                             'source_updated': (now - timedelta(days=r.randint(0, 90))).strftime('%Y-%m-%d'),
                             'outdated': st == '已完成' and r.random() < 0.15, 'review_comments': comments})
    sample = ['A component is a piece of UI that has its own logic and appearance.', 'Components can be as small as a button, or as large as an entire page.',
              'You can nest components inside other components.', 'When the state changes, the framework re-renders the component.',
              'During hydration, the client attaches event handlers to the HTML sent by the server.', 'Props are read-only snapshots: every render receives a new version of props.']
    terms_en = ['component', 'props', 'state', 'render', 'hydration', 'route', 'layout', 'segment', 'middleware', 'cache', 'revalidate', 'streaming', 'suspense', 'boundary',
                'hook', 'effect', 'ref', 'context', 'reducer', 'selector', 'bundle', 'chunk', 'tree shaking', 'code splitting', 'static export', 'server action', 'edge runtime',
                'environment variable', 'build', 'deploy', 'preview', 'fallback', 'placeholder', 'skeleton', 'payload', 'handler', 'endpoint', 'locale', 'polyfill', 'snapshot',
                'mock', 'fixture', 'assertion', 'test runner', 'coverage', 'lint', 'formatter', 'plugin', 'compiler', 'transpile']
    terms_zh = ['组件', 'props（不译）', '状态', '渲染', '水合', '路由', '布局', '路由段', '中间件', '缓存', '重新验证', '流式传输', 'Suspense（不译）', '边界',
                'Hook（不译）', '副作用', 'ref（不译）', '上下文', 'reducer（不译）', '选择器', '包', '分块', '摇树优化', '代码分割', '静态导出', '服务器操作', 'Edge 运行时',
                '环境变量', '构建', '部署', '预览', '回退', '占位', '骨架屏', '负载', '处理函数', '端点', '语言区域', '兼容补丁', '快照',
                '模拟', '测试夹具', '断言', '测试运行器', '覆盖率', '代码检查', '格式化工具', '插件', '编译器', '转译']
    glossary = [{'en': e, 'zh': z, 'note': r.choice(['', '', '', '首次出现时括注英文', '社区有争议，暂定', '与 v3 文档保持一致'])} for e, z in zip(terms_en, terms_zh)]
    proposals = [{'en': 'island', 'zh': '岛屿', 'by': vols[7], 'votes': 3, 'note': '也有人译“孤岛组件”'}, {'en': 'prefetch', 'zh': '预取', 'by': vols[9], 'votes': 5, 'note': ''},
                 {'en': 'opt-in', 'zh': '主动启用', 'by': me, 'votes': 1, 'note': '“选择加入”太生硬'}]
    write('translate', 'translate', {'now': fmt(now), 'project': '某开源前端框架 v4 中文文档', 'me': me, 'reviewers': reviewers, 'volunteers': vols, 'chapters': chapters,
                                     'sample_paragraphs': sample, 'glossary': glossary, 'term_proposals': proposals}, 'TRANSLATE_DATA')
    print('translate', len(chapters), 'chapters', len(glossary), 'terms')


reagents(); defense(); translate()
