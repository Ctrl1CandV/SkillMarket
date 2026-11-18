# 生成报修工单的示例数据（固定随机种子，重跑结果相同）。人名、电话都是编的。
#   python make_data.py   ->  data/tickets.json
import json, random
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

R = random.Random(20261118)
NOW = datetime(2026, 11, 18, 15, 20)
BUILDINGS = ['梅园 1 栋', '梅园 2 栋', '竹园 1 栋', '竹园 2 栋', '兰园 1 栋']
WORKERS = [
    {'id': 'w1', 'name': '周师傅', 'trade': '水暖', 'phone': '138-0000-1101'},
    {'id': 'w2', 'name': '冯师傅', 'trade': '水暖', 'phone': '138-0000-1102'},
    {'id': 'w3', 'name': '蒋师傅', 'trade': '电工', 'phone': '138-0000-1103'},
    {'id': 'w4', 'name': '韩师傅', 'trade': '电工', 'phone': '138-0000-1104', 'note': '也修空调'},
    {'id': 'w5', 'name': '陶师傅', 'trade': '门窗家具', 'phone': '138-0000-1105'},
]
# (类别, 报修内容, 是否紧急, 师傅处理后的说明)
ITEMS = [
    ('水暖', '卫生间洗手池下面的水管漏水，地上积了一滩', False, '换了下水软管和密封圈'),
    ('水暖', '热水器不出热水，指示灯是亮的', False, '加热棒坏了，已更换'),
    ('水暖', '马桶水箱一直流水，停不下来', False, '换了进水阀'),
    ('水暖', '阳台水龙头关不紧，一直在滴', False, '换了阀芯'),
    ('水暖', '淋浴花洒出水很小，洗澡要洗很久', False, '清了花洒和角阀里的水垢'),
    ('水暖', '洗手池堵了，水下不去', False, '疏通了存水弯，掏出一团头发'),
    ('水暖', '暖气片不热，隔壁宿舍是热的', False, '放了气，半小时后温度正常'),
    ('水暖', '卫生间天花板往下滴水，可能是楼上漏了', True, '楼上地漏接口松了，重新打胶'),
    ('水暖', '水管爆了，水往走廊里流，已经关了宿舍总阀', True, '换了一段进水管'),
    ('电', '整间宿舍没电，隔壁正常', True, '空开跳闸，查出是插排短路，已复位'),
    ('电', '书桌上方的灯管一闪一闪的', False, '换了灯管和启辉器'),
    ('电', '靠门那个插座没电，别的插座正常', False, '插座内部接线松了，重新接好'),
    ('电', '卫生间的灯不亮，自己换过灯泡也不行', False, '灯座烧了，换了灯座'),
    ('电', '空调开了不制热，外机没有动静', False, '外机电容坏了，已更换'),
    ('电', '走廊的声控灯一直亮着不灭', False, '换了声控开关'),
    ('电', '插座有焦味，已经把插头都拔了', True, '插座烧黑，整个换新，叮嘱不要接大功率电器'),
    ('电', '空调遥控器按了没反应，换过电池', False, '接收板坏了，换了接收板'),
    ('门窗家具', '门锁转不动，钥匙插进去拧不开，人进不去', True, '锁芯卡死，换了锁芯，新钥匙 4 把已交给宿舍长'),
    ('门窗家具', '阳台推拉门脱轨了，关不上', False, '换了下滑轮，重新上轨'),
    ('门窗家具', '衣柜门的合页掉了，门挂不住', False, '换了两个合页'),
    ('门窗家具', '上铺床板断了一根横档', False, '加了一根横档并加固'),
    ('门窗家具', '窗户把手断了，窗关不严，晚上漏风', False, '换了把手'),
    ('门窗家具', '椅子靠背松了，一靠就晃', False, '紧了螺丝，加了垫片'),
    ('门窗家具', '纱窗破了个洞，晚上进蚊子', False, '换了纱网'),
    ('门窗家具', '抽屉滑轨坏了，拉不出来', False, '换了一副滑轨'),
    ('网络', '墙上的网口没信号，换了网线也不行', False, ''),
    ('网络', '宿舍里无线信号很弱，经常断', False, ''),
    ('网络', '校园网登录页打不开，室友的电脑可以', False, ''),
]
SUR = '王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许邓冯韩曹'
GIVEN = ['一鸣', '雨桐', '子涵', '浩然', '思远', '佳怡', '晨曦', '宇航', '梓萱', '明轩', '欣妍', '嘉豪', '若溪',
         '俊杰', '静怡', '天佑', '可馨', '文博', '语嫣', '志强', '晓彤', '睿', '楠', '悦', '晗']
AVAIL = ['', '', '', '白天有课，下午 4 点以后有人', '全天有人', '周三下午没课', '中午 12 点到 2 点在', '晚上 7 点以后', '来之前请先打电话']
WAIT_PARTS = ['等配件，厂家说周五到', '要和楼上宿舍约时间一起看', '需要停水半天，等楼管通知']
TRADE_OF = {'水暖': ['w1', 'w2'], '电': ['w3', 'w4'], '门窗家具': ['w5']}


def fmt(t):
    return t.strftime('%Y-%m-%dT%H:%M')


def daytime(t):
    """学生一般在 8:00 到 21:30 之间报修。"""
    if t.hour < 8:
        t = t.replace(hour=8, minute=R.randint(0, 59))
    if t.hour >= 22:
        t = t.replace(hour=21, minute=R.randint(0, 29))
    return t


def name_of(wid):
    return next(x['name'] for x in WORKERS if x['id'] == wid)


def build(seq, d):
    cat, text, urgent, fix = R.choice(ITEMS)
    created = daytime((NOW - timedelta(days=d)).replace(hour=R.randint(7, 22), minute=R.randint(0, 59)))
    if created > NOW - timedelta(minutes=10):
        created = NOW - timedelta(minutes=R.randint(12, 300))
    t = {
        'id': f'BX{created:%m%d}-{seq:03d}',
        'building': R.choice(BUILDINGS), 'room': f'{R.randint(1, 6)}{R.randint(1, 32):02d}',
        'category': cat, 'urgent': urgent, 'description': text,
        'reporter': R.choice(SUR) + R.choice(GIVEN), 'phone': f'139-0000-{R.randint(2000, 9999)}',
        'available': R.choice(AVAIL), 'photos': R.choice([0, 0, 1, 1, 2, 3]),
        'created': fmt(created), 'status': '', 'worker': None, 'events': [],
    }
    ev = t['events']
    ev.append({'at': fmt(created), 'what': '报修', 'who': t['reporter'],
               'note': R.choice(['电话报修，值班员代录', '学生在楼管处登记', '电话报修，值班员代录'])})
    age_h = (NOW - created).total_seconds() / 3600
    if cat == '网络':
        at = created + timedelta(minutes=R.randint(10, 90))
        if at < NOW:
            ev.append({'at': fmt(at), 'what': '转交', 'who': '值班员', 'note': '网络问题归信息中心，已转交，电话 8800-1234'})
            t['status'] = '已转交'
        else:
            t['status'] = '待派单'
        return t
    assign = created + timedelta(minutes=R.randint(5, 25) if urgent else R.randint(20, 300))
    if assign.hour >= 18 and not urgent:
        assign = (assign + timedelta(days=1)).replace(hour=8, minute=R.randint(5, 50))
    if assign > NOW:
        t['status'] = '待派单'
        return t
    if age_h < 60 and R.random() < 0.06:
        ev.append({'at': fmt(created + timedelta(minutes=R.randint(30, 200))), 'what': '取消', 'who': t['reporter'],
                   'note': R.choice(['自己修好了', '重复报修，和同宿舍的另一张单是同一件事'])})
        t['status'] = '已取消'
        return t
    w = R.choice(TRADE_OF[cat])
    t['worker'] = w
    ev.append({'at': fmt(assign), 'what': '派单', 'who': '值班员', 'note': '派给' + name_of(w)})
    start = assign + timedelta(minutes=R.randint(15, 60) if urgent else R.randint(40, 1500))
    if start.hour < 8:
        start = start.replace(hour=8, minute=30)
    if start.hour >= 18:
        start = (start + timedelta(days=1)).replace(hour=9, minute=R.randint(0, 50))
    if start > NOW:
        t['status'] = '已派单'
        return t
    ev.append({'at': fmt(start), 'what': '开始处理', 'who': name_of(w), 'note': ''})
    if R.random() < 0.12:
        ev.append({'at': fmt(start + timedelta(minutes=R.randint(20, 50))), 'what': '备注', 'who': name_of(w), 'note': R.choice(WAIT_PARTS)})
        done = start + timedelta(hours=R.randint(50, 110))
    else:
        done = start + timedelta(minutes=R.randint(20, 150))
    if done > NOW:
        t['status'] = '处理中'
        return t
    ev.append({'at': fmt(done), 'what': '修好', 'who': name_of(w), 'note': fix})
    confirm = done + timedelta(minutes=R.randint(30, 1700))
    if confirm > NOW:
        t['status'] = '待确认'
        return t
    ev.append({'at': fmt(confirm), 'what': '确认', 'who': t['reporter'], 'note': R.choice(['', '', '', '修好了，谢谢师傅', '好了'])})
    t['status'] = '已完成'
    return t


days = []
for d in range(13, -1, -1):
    day = NOW - timedelta(days=d)
    days += [d] * (R.choice([3, 4, 4, 5, 5, 6]) if day.weekday() < 5 else R.choice([1, 2, 2]))
tickets = [build(i + 1, d) for i, d in enumerate(days)]


def extra(created, building, room, cat, urgent, text, reporter, available, photos, status, worker=None, more=()):
    """手写的几张单，保证“现在”这一刻的待办有代表性：有紧急的、有拖过一天的、有刚派出去的。"""
    c = datetime.strptime(created, '%m-%d %H:%M').replace(year=2026)
    t = {'id': f'BX{c:%m%d}-{len(tickets) + 1:03d}', 'building': building, 'room': room, 'category': cat, 'urgent': urgent,
         'description': text, 'reporter': reporter, 'phone': f'139-0000-{R.randint(2000, 9999)}', 'available': available,
         'photos': photos, 'created': fmt(c), 'status': status, 'worker': worker,
         'events': [{'at': fmt(c), 'what': '报修', 'who': reporter, 'note': '电话报修，值班员代录'}]}
    for at, what, who, note in more:
        t['events'].append({'at': fmt(datetime.strptime(at, '%m-%d %H:%M').replace(year=2026)), 'what': what, 'who': who, 'note': note})
    tickets.append(t)


extra('11-18 15:04', '竹园 2 栋', '512', '水暖', True, '卫生间天花板往下滴水，越滴越快，已经拿盆接着了', '何雨桐', '全天有人', 2, '待派单')
extra('11-18 14:41', '梅园 1 栋', '318', '电', False, '空调开了不制热，外机没有动静', '郑浩然', '下午 4 点以后有人', 0, '待派单')
extra('11-18 13:52', '兰园 1 栋', '221', '门窗家具', False, '窗户把手断了，窗关不严，晚上漏风', '许静怡', '', 1, '待派单')
extra('11-18 15:11', '梅园 2 栋', '407', '网络', False, '墙上的网口没信号，换了网线也不行', '唐文博', '晚上 7 点以后', 0, '待派单')
extra('11-17 10:12', '竹园 1 栋', '115', '门窗家具', False, '上铺床板断了一根横档，现在睡在下铺同学那里', '梁可馨', '来之前请先打电话', 3, '待派单')
extra('11-18 11:20', '梅园 1 栋', '603', '水暖', False, '热水器不出热水，指示灯是亮的', '曹明轩', '中午 12 点到 2 点在', 1, '已派单', 'w2',
      [('11-18 11:48', '派单', '值班员', '派给冯师傅')])
extra('11-18 09:35', '兰园 1 栋', '430', '电', False, '靠门那个插座没电，别的插座正常', '高欣妍', '周三下午没课', 0, '已派单', 'w3',
      [('11-18 10:02', '派单', '值班员', '派给蒋师傅')])
extra('11-18 14:20', '竹园 2 栋', '208', '电', True, '插座有焦味，已经把插头都拔了', '罗俊杰', '全天有人', 2, '处理中', 'w4',
      [('11-18 14:26', '派单', '值班员', '派给韩师傅'), ('11-18 14:50', '开始处理', '韩师傅', '')])
extra('11-13 16:30', '梅园 2 栋', '120', '水暖', False, '暖气片不热，隔壁宿舍是热的', '谢思远', '', 0, '处理中', 'w1',
      [('11-14 08:20', '派单', '值班员', '派给周师傅'), ('11-14 10:05', '开始处理', '周师傅', ''),
       ('11-14 10:40', '备注', '周师傅', '阀门锈死，要换整组阀，等配件，厂家说周五到'),
       ('11-17 09:10', '备注', '值班员', '学生来电话催，已回复预计周五')])
tickets.sort(key=lambda x: x['created'])
for i, t in enumerate(tickets):
    t['id'] = t['id'][:7] + f'{i + 1:03d}'
out = {'now': fmt(NOW), 'buildings': BUILDINGS, 'categories': ['水暖', '电', '门窗家具', '网络'],
       'statuses': ['待派单', '已派单', '处理中', '待确认', '已完成', '已取消', '已转交'], 'workers': WORKERS, 'tickets': tickets}
target = Path(__file__).with_name('data')
target.mkdir(exist_ok=True)
(target / 'tickets.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
(target / 'tickets.js').write_text('window.REPAIR_DATA = ' + json.dumps(out, ensure_ascii=False) + ';\n', encoding='utf-8')
print(len(tickets), dict(Counter(x['status'] for x in tickets)), dict(Counter(x['category'] for x in tickets)), sum(x['urgent'] for x in tickets))
for x in tickets:
    if x['status'] in ('待派单', '已派单', '处理中', '待确认'):
        print(x['id'], x['status'], x['created'], x['building'], x['room'], x['category'], '急' if x['urgent'] else '-', x['description'][:16])
