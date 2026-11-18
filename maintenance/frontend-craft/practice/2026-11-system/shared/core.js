// 报修处理台：数据、规则和操作。两套界面（a/、b/）共用这一份。
// “现在”固定在示例数据给的时间（2026-11-18 15:20），操作记录也记在这个时间。
(function () {
  'use strict';
  const D = window.REPAIR_DATA;
  const NOW = new Date(D.now);
  const KEY = 'repair-practice-v1';
  const OPEN = ['待派单', '已派单', '处理中', '待确认'];
  const TRADE = { 水暖: '水暖', 电: '电工', 门窗家具: '门窗家具' };
  const URGENT_WORDS = /漏水|滴水|爆了|水管爆|没电|断电|焦味|冒烟|进不去|打不开|锁在/;
  const MIN = 60000;

  let state = read();
  let undoSnapshot = null;

  function read() {
    try {
      const s = JSON.parse(localStorage.getItem(KEY));
      if (s && Array.isArray(s.tickets)) return s;
    } catch (e) { /* 本地存储不可用时退回示例数据 */ }
    return { tickets: JSON.parse(JSON.stringify(D.tickets)) };
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* 存不了就只在这次打开期间有效 */ }
  }
  function reset() {
    try { localStorage.removeItem(KEY); } catch (e) { /* 忽略 */ }
    state = read();
  }

  const pad = (n) => String(n).padStart(2, '0');
  const stamp = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  const minutesBetween = (a, b) => Math.round((new Date(b) - new Date(a)) / MIN);
  const dayStart = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());

  // 时长：不到 1 小时写分钟，不到 2 天写小时，再往上写天。
  function dur(min) {
    min = Math.max(0, Math.round(min));
    if (min < 60) return `${min} 分钟`;
    if (min < 48 * 60) {
      const h = min / 60;
      return h < 10 && Math.round(h * 2) % 2 ? `${Math.floor(h)} 个半小时` : `${Math.round(h)} 小时`;
    }
    return `${Math.round(min / 1440)} 天`;
  }
  // 时刻：今天只写钟点，昨天写“昨天”，更早写日期。
  function when(at) {
    const d = new Date(at);
    const days = Math.round((dayStart(NOW) - dayStart(d)) / 86400000);
    const hm = `${d.getHours()}:${pad(d.getMinutes())}`;
    if (days === 0) return hm;
    if (days === 1) return `昨天 ${hm}`;
    return `${d.getMonth() + 1}月${d.getDate()}日 ${hm}`;
  }
  const WEEK = '日一二三四五六';
  const dateLabel = (d) => `${d.getMonth() + 1}月${d.getDate()}日 周${WEEK[d.getDay()]}`;

  const worker = (id) => D.workers.find((w) => w.id === id) || null;
  const find = (id) => state.tickets.find((t) => t.id === id) || null;
  const lastEvent = (t, what) => [...t.events].reverse().find((e) => e.what === what) || null;
  const place = (t) => `${t.building} ${t.room}`;

  // 每张单现在的处境：等了多久、期限是什么、超没超。
  function view(t) {
    const waited = minutesBetween(t.created, NOW);
    const v = { waited, late: false, lateBy: 0, left: null, rule: '', since: t.created };
    if (t.status === '待派单') {
      const limit = t.urgent ? 30 : 24 * 60;
      v.rule = t.urgent ? '紧急单 30 分钟内派出' : '普通单 24 小时内派出';
      v.left = limit - waited;
    } else if (t.status === '已派单' || t.status === '处理中') {
      const a = [...t.events].reverse().find((e) => e.what === '派单' || e.what === '改派');
      v.since = a ? a.at : t.created;
      v.rule = '派单后 48 小时内修好';
      v.left = 48 * 60 - minutesBetween(v.since, NOW);
    } else if (t.status === '待确认') {
      const f = lastEvent(t, '修好');
      v.since = f ? f.at : t.created;
    }
    if (v.left !== null && v.left < 0) { v.late = true; v.lateBy = -v.left; }
    const fixed = lastEvent(t, '修好');
    v.fixMinutes = fixed ? minutesBetween(t.created, fixed.at) : null;
    return v;
  }

  const inHand = (wid) => state.tickets.filter((t) => t.worker === wid && (t.status === '已派单' || t.status === '处理中'));
  // 能接这张单的师傅，手上活少的排前面；空调单把会修空调的排前面。
  function candidates(t) {
    const trade = TRADE[t.category];
    const aircon = /空调/.test(t.description);
    return D.workers.filter((w) => w.trade === trade)
      .map((w) => ({ worker: w, load: inHand(w.id).length, aircon: aircon && /空调/.test(w.note || ''), nearby: inHand(w.id).filter((x) => x.building === t.building).length }))
      .sort((a, b) => (b.aircon - a.aircon) || (a.load - b.load));
  }

  function act(label, fn) {
    undoSnapshot = { label, json: JSON.stringify(state) };
    fn();
    save();
    return label;
  }
  function undo() {
    if (!undoSnapshot) return false;
    state = JSON.parse(undoSnapshot.json);
    undoSnapshot = null;
    save();
    return true;
  }
  const push = (t, what, who, note) => t.events.push({ at: stamp(NOW), what, who, note: note || '' });

  const actions = {
    assign(id, wid) {
      const t = find(id), w = worker(wid);
      const again = Boolean(t.worker);
      return act(`${place(t)} 已${again ? '改派' : '派'}给${w.name}`, () => {
        t.worker = wid;
        t.status = '已派单';
        push(t, again ? '改派' : '派单', '值班员', `派给${w.name}`);
      });
    },
    transfer(id) {
      const t = find(id);
      return act(`${place(t)} 已转交信息中心`, () => { t.status = '已转交'; t.worker = null; push(t, '转交', '值班员', '网络问题归信息中心，电话 8800-1234'); });
    },
    start(id) {
      const t = find(id);
      return act(`${place(t)} 已记为处理中`, () => { t.status = '处理中'; push(t, '开始处理', worker(t.worker).name, ''); });
    },
    fixed(id, note) {
      const t = find(id);
      return act(`${place(t)} 已记为修好，等学生确认`, () => { t.status = '待确认'; push(t, '修好', worker(t.worker).name, note); });
    },
    confirm(id) {
      const t = find(id);
      return act(`${place(t)} 已完成`, () => { t.status = '已完成'; push(t, '确认', t.reporter, '值班员电话回访'); });
    },
    reopen(id, note) {
      const t = find(id);
      return act(`${place(t)} 退回处理中`, () => { t.status = '处理中'; push(t, '没修好', t.reporter, note || '学生说还没好'); });
    },
    cancel(id, note) {
      const t = find(id);
      return act(`${place(t)} 已取消`, () => { t.status = '已取消'; push(t, '取消', '值班员', note); });
    },
    note(id, text) {
      const t = find(id);
      return act('备注已加上', () => push(t, '备注', '值班员', text));
    },
    create(f) {
      const seq = Math.max(...state.tickets.map((t) => Number(t.id.slice(-3)))) + 1;
      const t = {
        id: `BX${pad(NOW.getMonth() + 1)}${pad(NOW.getDate())}-${String(seq).padStart(3, '0')}`,
        building: f.building, room: f.room, category: f.category, urgent: Boolean(f.urgent), description: f.description,
        reporter: f.reporter, phone: f.phone, available: f.available || '', photos: 0,
        created: stamp(NOW), status: '待派单', worker: null, events: [],
      };
      act(`${place(t)} 已录入`, () => { push(t, '报修', t.reporter, '电话报修，值班员代录'); state.tickets.push(t); });
      return t;
    },
  };

  // 待办的排序：紧急的在前，其次超时的，再按等得久的。
  function byPressure(a, b) {
    const va = view(a), vb = view(b);
    return (b.urgent - a.urgent) || (vb.late - va.late) || (vb.waited - va.waited);
  }
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  window.Repair = {
    data: D, NOW, OPEN, TRADE, URGENT_WORDS,
    get tickets() { return state.tickets; },
    find, worker, view, inHand, candidates, actions, undo, reset, byPressure,
    get canUndo() { return Boolean(undoSnapshot); },
    fmt: { dur, when, dateLabel, place, esc, minutesBetween },
  };
})();
