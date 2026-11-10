// scene.js — 「两清」 promo, 30 s at 120 BPM (beat 0.5 s). Every number on screen is computed from EXP.
import { clamp, lerp, ease, seg, spring, rng, loadFonts, register } from '../../kit/kit.js';

const W = 1920, H = 1080, FPS = 30, DUR = 28;
const $ = (s) => document.querySelector(s);
const stage = $('#stage');

// ---------- data ----------
const P = [
  { n: '小林', c: '林', col: '#2F6BFF' }, { n: '阿杰', c: '杰', col: '#EE9512' }, { n: '美美', c: '美', col: '#E5487D' },
  { n: '老周', c: '周', col: '#1C9E95' }, { n: '安安', c: '安', col: '#8A5CF5' },
];
// title, payer, amount, category glyph, tint, glyph colour
const EXP = [
  ['酒店 2 晚', 0, 1260, '住', '#E6EDFF', '#2F6BFF'], ['景区门票', 1, 480, '票', '#FFF0D9', '#B86E00'], ['火锅', 2, 650, '食', '#FFE5EE', '#CF3468'],
  ['租车 + 油费', 3, 900, '车', '#DAF3F0', '#13807A'], ['奶茶咖啡', 4, 210, '饮', '#EDE6FF', '#6F45DB'],
];
const TOTAL = EXP.reduce((s, e) => s + e[2], 0), SHARE = TOTAL / P.length;
const NET = P.map((_, i) => EXP.filter((e) => e[1] === i).reduce((s, e) => s + e[2], 0) - SHARE);
const NAIVE = []; P.forEach((_, i) => P.forEach((_, j) => { if (i !== j) NAIVE.push([i, j]); }));
const SETTLE = (() => {
  const deb = NET.map((v, i) => [i, -v]).filter((x) => x[1] > 0).sort((a, b) => b[1] - a[1]);
  const cre = NET.map((v, i) => [i, v]).filter((x) => x[1] > 0).sort((a, b) => b[1] - a[1]);
  const out = [];
  while (deb.length && cre.length) { const d = deb[0], c = cre[0], x = Math.min(d[1], c[1]); out.push([d[0], c[0], x]); d[1] -= x; c[1] -= x; if (!d[1]) deb.shift(); if (!c[1]) cre.shift(); }
  return out;
})();
const fmt = (n) => Math.round(n).toLocaleString('en-US');
const sgn = (v) => (v > 0 ? '+' + fmt(v) : v < 0 ? '−' + fmt(-v) : '0');
const av = (i, cls = '') => `<div class="av ${cls}" style="background:${P[i].col}">${P[i].c}</div>`;

// ---------- timeline (seconds; beat = 0.5) ----------
// [person, text, time, expense index or -1, x, y, rotation] — a messy pile, every bubble stays in frame
const MSG = [
  [0, '酒店我先付了，<b>1260</b>', -0.75, 0, 850, 480, -2], [1, '门票 <b>480</b> 我出的', -0.5, 1, 1330, 640, 2], [2, '昨晚火锅我买的单，<b>650</b>', -0.25, 2, 1240, 100, -1.5],
  [4, '奶茶咖啡算我的～<b>210</b>', 0.5, 4, 880, 300, 1.5], [3, '租车加油一共 <b>900</b>', 1.0, 3, 1300, 820, -1], [1, '所以我该转谁多少？', 1.5, -1, 900, 680, 1.5],
  [2, '等下，酒店几个人分？', 2.0, -1, 1330, 290, -2], [4, '我转了没？忘了', 2.5, -1, 860, 120, 2], [0, '没收到啊', 2.75, -1, 870, 860, -1.5],
  [3, '要不拉个表格…', 3.0, -1, 1350, 460, 1], [1, '？？？', 3.25, -1, 1060, 600, -3], [2, '我已经晕了', 3.5, -1, 1180, 240, 2.5],
];
const T = { reveal: 4.0, morph: 4.15, fly: 4.5, count: 6.0, finger: 8.0, tap: 8.5, push: 9.0, graph: 10.0, naive: 10.5, clear: 14.0, bold: 15.0, note: 17.0, pull: 18.0, finger2: 19.0, tap2: 19.5, check: 20.0, stamp: 21.84, logo: 24.0, tag: 25.0 };
const LAND = EXP.map((_, k) => T.fly + k * 0.125 + 0.625);   // a chip lands in its row

// ---------- build DOM ----------
const chat = $('#chat');
const msgEls = MSG.map(([p, html]) => {
  const d = document.createElement('div'); d.className = 'msg';
  d.innerHTML = `${av(p)}<div><div class="who">${P[p].n}</div><div class="bub">${html}</div></div>`;
  chat.appendChild(d); return d;
});
const fly = document.createElement('div'); fly.className = 'abs'; fly.style.inset = '0'; stage.insertBefore(fly, $('#seal'));
const chips = EXP.map((e) => {
  const d = document.createElement('div'); d.className = 'abs';
  d.style.cssText = 'left:0;top:0;transform-origin:0 0;border-radius:16px;display:flex;align-items:center;gap:14px;padding:0 20px;font:700 26px "Noto Sans SC";white-space:nowrap;overflow:hidden';
  d.innerHTML = `<span>${e[0]}</span><span style="margin-left:auto;font-family:Ubuntu">¥${fmt(e[2])}</span>`;
  fly.appendChild(d); return d;
});
for (const id of ['#finger', '#ripple']) stage.insertBefore($(id), $('#seal'));

$('#ledger').innerHTML = `
  <div class="trip">杭州 · 五一 4 天</div><div class="sub">5 人 · <span id="cnt">0</span> 笔账单</div>
  <div class="avs">${P.map((_, i) => av(i)).join('')}</div><div class="label">账单</div>
  ${EXP.map((e, k) => `<div class="row" id="row${k}"><div class="cat" style="background:${e[4]};color:${e[5]}">${e[3]}</div><div><div class="t">${e[0]}</div><div class="p">${P[e[1]].n} 付</div></div><div class="amt">¥${fmt(e[2])}</div></div>`).join('')}
  <div class="sum" id="sum"><div><div class="k">共</div><div class="v"><small>¥</small><span id="tot">0</span></div></div><div><div class="k" style="text-align:right">每人</div><div class="v2">¥<span id="per">0</span></div></div></div>
  <div class="go" id="go">算一算</div>`;
$('#transfers').innerHTML = `
  <div class="trip">怎么转最少</div><div class="sub">${SETTLE.length} 笔就两清</div>
  <div class="bal">${P.map((p, i) => `<div class="one">${av(i)}<div class="n" id="bal${i}"></div></div>`).join('')}</div>
  <div class="label">转账</div>
  ${SETTLE.map(([a, b, x], k) => `<div class="tr" id="tr${k}">${av(a)}<div class="arrow"></div>${av(b)}<div class="amt">¥${fmt(x)}</div>
     <div class="st"><div class="a">提醒</div><div class="b">已提醒</div><div class="c"><svg width="20" height="20" viewBox="0 0 20 20"><path d="M4 10.5l4 4 8-9" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>已到账</div></div></div>`).join('')}
  <div class="remind" id="remind">一键提醒</div>`;

// graph
const GC = [1250, 520], GR = 320;
const NODE = P.map((_, i) => { const a = (-90 + i * 72) * Math.PI / 180; return [GC[0] + GR * Math.cos(a), GC[1] + GR * Math.sin(a)]; });
const graph = $('#graph'), svg = $('#gsvg'), NS = 'http://www.w3.org/2000/svg';
const nodeEls = P.map((p, i) => {
  const d = document.createElement('div'); d.className = 'node';
  d.innerHTML = `${av(i)}<div class="nm">${p.n}</div><div class="net" style="background:${NET[i] > 0 ? '#DDF3EA' : '#FDE5DE'};color:${NET[i] > 0 ? '#118457' : '#D4502F'}">${sgn(NET[i])}</div>`;
  d.style.left = NODE[i][0] + 'px'; d.style.top = NODE[i][1] - 60 + 'px'; graph.appendChild(d); return d;
});
function curve(i, j, off, shrink) {
  const [ax, ay] = NODE[i], [bx, by] = NODE[j], dx = bx - ax, dy = by - ay, L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L;
  const A = [ax + ux * shrink, ay + uy * shrink], B = [bx - ux * shrink, by - uy * shrink], C = [(A[0] + B[0]) / 2 - uy * off, (A[1] + B[1]) / 2 + ux * off];
  return { A, B, C };
}
const qpt = ({ A, B, C }, t) => [0, 1].map((k) => (1 - t) ** 2 * A[k] + 2 * (1 - t) * t * C[k] + t * t * B[k]);
function mkArrow(stroke, width, head) {
  const path = document.createElementNS(NS, 'path'), tip = document.createElementNS(NS, 'path');
  path.setAttribute('fill', 'none'); path.setAttribute('stroke', stroke); path.setAttribute('stroke-width', width); path.setAttribute('stroke-linecap', 'round');
  tip.setAttribute('fill', stroke); tip.setAttribute('d', `M0 0 L${-head} ${head * 0.55} L${-head * 0.72} 0 L${-head} ${-head * 0.55} Z`);
  svg.appendChild(path); svg.appendChild(tip); return { path, tip };
}
function drawArrow(a, cv, p, alpha) {
  if (p <= 0 || alpha <= 0) { a.path.style.opacity = 0; a.tip.style.opacity = 0; return; }
  const { A, C } = cv, E = qpt(cv, p), M = [A[0] + p * (C[0] - A[0]), A[1] + p * (C[1] - A[1])];
  a.path.setAttribute('d', `M${A[0]} ${A[1]} Q${M[0]} ${M[1]} ${E[0]} ${E[1]}`);
  const ang = Math.atan2(E[1] - M[1], E[0] - M[0]) * 180 / Math.PI;
  a.tip.setAttribute('transform', `translate(${E[0]} ${E[1]}) rotate(${ang})`);
  a.path.style.opacity = alpha; a.tip.style.opacity = alpha;
}
const naive = NAIVE.map(([i, j], k) => ({ cv: curve(i, j, 34, 76), a: mkArrow('#EE6A4C', 3, 15), t0: T.naive + k * 0.125 }));
const bold = SETTLE.map(([i, j, x], k) => {
  const cv = curve(i, j, 30, 84), a = mkArrow('#151A22', 8, 28), m = document.createElement('div');
  m.className = 'money'; m.textContent = '¥' + fmt(x); graph.appendChild(m);
  return { cv, a, m, t0: T.bold + k * 0.5 };
});
for (const n of nodeEls) graph.appendChild(n);   // nodes above arrows
for (const b of bold) graph.appendChild(b.m);     // money above nodes

// captions
const CAPS = [
  [-1.0, 3.75, ['旅行回来，', '账算不清？'], 'dark'],
  [4.5, 7.75, ['把群聊交给<em>「两清」</em>', '每一笔，自动记好'], ''],
  [8.25, 9.05, ['谁该转谁？'], ''],
  [19.0, 23.25, ['一键提醒，', '到账自动打勾'], ''],
];
const capEls = CAPS.map(([, , lines, cls]) => {
  const d = document.createElement('div'); d.className = 'cap ' + cls;
  d.innerHTML = lines.map((l) => `<div class="ln"><span>${l}</span></div>`).join(''); $('#caps').appendChild(d); return d;
});

// grain
(() => { const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'), im = g.createImageData(256, 256), r = rng(9); for (let i = 0; i < im.data.length; i += 4) { const v = 128 + (r() - 0.5) * 255; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; } g.putImageData(im, 0, 0); $('#grain').style.backgroundImage = `url(${c.toDataURL()})`; })();

// seal ink: speckles and a ragged edge, so it reads as a stamp rather than a flat square
(() => { const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'), r = rng(77);
  g.fillStyle = '#000'; g.fillRect(0, 0, 256, 256); g.globalCompositeOperation = 'destination-out';
  for (let i = 0; i < 260; i++) { const x = r() * 256, y = r() * 256, rr = r() < 0.85 ? 0.5 + r() * 1.4 : 2 + r() * 3; g.globalAlpha = 0.35 + r() * 0.6; g.beginPath(); g.arc(x, y, rr, 0, 7); g.fill(); }
  for (let i = 0; i < 90; i++) { const e = r() * 4 | 0, u = r() * 256, x = [u, 256, u, 0][e], y = [0, u, 256, u][e]; g.globalAlpha = 0.9; g.beginPath(); g.arc(x, y, 1 + r() * 4, 0, 7); g.fill(); }
  const u = c.toDataURL(), el = $('#seal'); el.style.webkitMaskImage = `url(${u})`; el.style.maskImage = `url(${u})`; el.style.webkitMaskSize = '100% 100%'; el.style.maskSize = '100% 100%'; })();

// ---------- helpers ----------
const st = (el, o) => { for (const k in o) el.style[k] = o[k]; };
const show = (el, a) => { el.style.opacity = a.toFixed(3); el.style.visibility = a > 0.001 ? 'visible' : 'hidden'; };
const center = (el) => { const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2, r.width, r.height]; };

function phoneState(t) {
  // position relative to its layout spot (centre 1270, 540)
  let x = 0, y = 0, s = 1, ry = -16, rx = 5, rz = 1.5, o = 1;
  const up = t < T.reveal + 0.2 ? 0 : spring(t - T.reveal - 0.2, { stiffness: 120, damping: 17 });
  y = (1 - up) * 1100;
  ry += 4 * Math.sin(t * 0.35); rx += 1.2 * Math.sin(t * 0.5 + 1);
  // push into the screen, then pull back out
  const pin = seg(t, T.push, 0.85, (x) => x * x), pout = 1 - seg(t, T.pull, 1.1, ease.out);
  const k = t < T.pull ? pin : pout;
  if (k > 0) { s = Math.exp(lerp(0, Math.log(6.6), k)); x = lerp(0, -310, Math.min(1, k * 1.4)); ry *= 1 - k; rx *= 1 - k; rz *= 1 - k; }
  // exit for the end card
  const ex = seg(t, T.logo, 0.8, ease.in); y += ex * 1150;
  return { x, y, s, ry, rx, rz, o };
}

// ---------- the frame ----------
function seek(t) {
  // background: dark → light circle reveal
  const r = seg(t, T.reveal, 0.55, ease.inOut) * 2300;
  $('#light').style.clipPath = `circle(${r.toFixed(1)}px at 1270px 540px)`;
  // camera shake building up in the chat, and at the stamp
  const sh = (t < T.reveal ? Math.max(0, (t - 2.6) / 1.4) ** 2 * 7 : 0) + (t > T.stamp + 0.16 ? Math.exp(-(t - T.stamp - 0.16) * 14) * 14 : 0);
  const sr = rng(Math.floor(t * FPS) + 3);
  $('#world').style.transform = sh > 0.05 ? `translate(${((sr() - 0.5) * sh).toFixed(2)}px, ${((sr() - 0.5) * sh).toFixed(2)}px)` : 'none';

  // chat
  const chatOn = t < T.fly + 1.4;
  show(chat, chatOn ? 1 : 0);
  MSG.forEach(([, , t0, ex, x, y, rot], k) => {
    const el = msgEls[k];
    if (t < t0) { show(el, 0); return; }
    const a = clamp(spring(t - t0, { stiffness: 320, damping: 18 }), 0, 1.2);
    let alpha = clamp((t - t0) / 0.08), sc = 0.55 + 0.45 * a;
    if (t >= T.reveal) { if (ex < 0) { const q = seg(t, T.reveal + (k % 4) * 0.04, 0.22, ease.in); alpha *= 1 - q; sc *= 1 - 0.5 * q; } else alpha *= 1 - seg(t, T.morph, 0.15, ease.linear); }
    show(el, alpha); el.style.transform = `translate(${x}px, ${y}px) rotate(${rot}deg) scale(${sc.toFixed(3)})`;
  });

  // phone
  const ps = phoneState(t);
  $('#phone').style.transform = `translate(${ps.x}px, ${ps.y}px) perspective(2400px) rotateY(${ps.ry}deg) rotateX(${ps.rx}deg) rotateZ(${ps.rz}deg) scale(${ps.s})`;
  $('#phone').style.transformOrigin = '50% 46%';
  show($('#phone'), t >= T.reveal ? 1 - seg(t, T.logo + 0.5, 0.3) : 0);
  const onLedger = t < T.pull;
  show($('#ledger'), onLedger ? 1 - seg(t, T.push + 0.55, 0.3) : 0);
  show($('#transfers'), t >= T.pull ? seg(t, T.pull + 0.3, 0.4) : 0);
  // ledger rows land as their chips arrive
  EXP.forEach((_, k) => show($('#row' + k), seg(t, LAND[k] - 0.05, 0.12, ease.linear)));
  $('#cnt').textContent = String(EXP.filter((_, k) => t >= LAND[k]).length);
  const cnt = seg(t, T.count, 1.0, ease.inOutSoft);
  $('#tot').textContent = fmt(TOTAL * cnt); $('#per').textContent = fmt(SHARE * cnt);
  show($('#sum'), seg(t, T.count - 0.25, 0.3)); show($('#go'), seg(t, T.count + 0.5, 0.3));
  const press = t > T.tap && t < T.tap + 0.25 ? 0.95 : 1;
  $('#go').style.transform = `scale(${press})`;

  // chips: morph in place (bubble → ticket), then fly into the phone
  EXP.forEach((e, k) => {
    const ch = chips[k], mi = MSG.findIndex((m) => m[3] === k), bub = msgEls[mi].querySelector('.bub');
    if (t < T.morph || t > LAND[k] + 0.1) { show(ch, 0); return; }
    const morph = seg(t, T.morph, 0.4, ease.inOut), tf = seg(t, T.fly + k * 0.125, 0.625, ease.inOut);
    const b = bub.getBoundingClientRect(), rr = $('#row' + k).getBoundingClientRect();
    const w0 = lerp(b.width, 400, morph), h0 = lerp(b.height, 76, morph);
    const x = lerp(b.left, rr.left, tf), y = lerp(b.top + (b.height - h0) / 2, rr.top, tf), w = lerp(w0, rr.width, tf), h = lerp(h0, rr.height, tf);
    st(ch, { transform: `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`, width: w.toFixed(1) + 'px', height: h.toFixed(1) + 'px',
      background: morph < 1 ? `rgb(${Math.round(lerp(37, 255, morph))},${Math.round(lerp(44, 255, morph))},${Math.round(lerp(56, 255, morph))})` : '#fff',
      color: morph > 0.5 ? '#151A22' : '#EEF1F6', boxShadow: `0 ${14 * morph}px ${30 * morph}px rgba(20,30,40,${0.18 * morph})`, fontSize: lerp(30, 21, tf) + 'px' });
    show(ch, Math.min(1, morph * 3) * (1 - seg(t, LAND[k] - 0.02, 0.1, ease.linear)));
  });

  // finger + ripple
  const fingerTo = (t0, el) => {
    const [cx, cy] = center(el), a = seg(t, t0, 0.5, ease.out), out = seg(t, t0 + 0.8, 0.3);
    return { x: lerp(cx + 260, cx, a), y: lerp(cy + 320, cy, a), a: a * (1 - out) };
  };
  let f = null, rip = null;
  if (t >= T.finger && t < T.push + 0.2) { f = fingerTo(T.finger, $('#go')); rip = [T.tap, f]; }
  if (t >= T.finger2 && t < T.check + 0.4) { f = fingerTo(T.finger2, $('#remind')); rip = [T.tap2, f]; }
  if (f) { show($('#finger'), f.a * 0.9); $('#finger').style.transform = `translate(${f.x - 37}px, ${f.y - 37}px) scale(${t > rip[0] && t < rip[0] + 0.2 ? 0.9 : 1})`; } else show($('#finger'), 0);
  if (rip && t >= rip[0] && t < rip[0] + 0.6) { const q = seg(t, rip[0], 0.6); show($('#ripple'), 1 - q); $('#ripple').style.transform = `translate(${rip[1].x - 37}px, ${rip[1].y - 37}px) scale(${1 + q * 1.8})`; } else show($('#ripple'), 0);

  // graph scene
  const gA = t < T.pull ? seg(t, T.graph - 0.12, 0.12, ease.linear) : 1 - seg(t, T.pull + 0.05, 0.3, ease.linear);
  show(graph, gA); show($('#counter'), gA);
  // pulling back: the graph lives on the screen, so it shrinks with the phone while it fades
  const gs = t >= T.pull ? ps.s / 6.6 : 1, gx = t >= T.pull ? ps.x + 310 : 0, gy = t >= T.pull ? ps.y : 0;
  graph.style.transformOrigin = '960px 504px'; graph.style.transform = gs < 1 ? `translate(${gx}px, ${gy}px) scale(${gs.toFixed(4)})` : 'none';
  if (gA > 0) {
    nodeEls.forEach((n, i) => {
      const s = spring(t - (T.graph + i * 0.125), { stiffness: 220, damping: 16 });
      n.style.transform = `scale(${Math.max(0, s).toFixed(3)})`; n.style.opacity = clamp(s * 2).toFixed(3);
      const net = n.querySelector('.net'); show(net, seg(t, T.clear + 0.25 + i * 0.125, 0.3)); net.style.transform = `translateY(${(1 - seg(t, T.clear + 0.25 + i * 0.125, 0.3)) * 14}px)`;
    });
    naive.forEach((a, k) => drawArrow(a.a, a.cv, seg(t, a.t0, 0.35, ease.inOut), 0.62 * (1 - seg(t, T.clear + (19 - k) * 0.02, 0.35, ease.in))));
    bold.forEach((b) => {
      const p = seg(t, b.t0, 0.42, ease.inOut); drawArrow(b.a, b.cv, p, 1);
      const [mx, my] = qpt(b.cv, 0.5), ms = spring(t - b.t0 - 0.3, { stiffness: 260, damping: 15 });
      b.m.style.left = mx + 'px'; b.m.style.top = my + 'px'; b.m.style.transform = `translate(-50%, -50%) scale(${Math.max(0, ms).toFixed(3)})`; b.m.style.opacity = clamp(ms * 2).toFixed(3);
    });
    const started = naive.filter((a) => t >= a.t0).length, roll = seg(t, T.bold, 1.75, ease.inOutSoft);
    $('#num').textContent = String(t < T.bold ? started : Math.round(lerp(NAIVE.length, SETTLE.length, roll)));
    $('#num').style.color = roll > 0.98 ? '#179F6A' : '#151A22';
    const swap = seg(t, T.bold, 0.4, ease.inOut);
    $('#lab1').style.transform = `translateY(${-swap * 60}px)`; show($('#lab1'), 1 - swap);
    $('#lab2').style.transform = `translateY(${(1 - swap) * 60}px)`; show($('#lab2'), swap);
    show($('#note'), seg(t, T.note, 0.4)); $('#note').textContent = `少转 ${NAIVE.length - SETTLE.length} 笔`;
    $('#counter').style.transformOrigin = '820px 204px';
    $('#counter').style.transform = gs < 1 ? `translate(${gx}px, ${gy}px) scale(${gs.toFixed(4)})` : `translateY(${(1 - seg(t, T.graph, 0.5)) * 30}px)`;
  }

  // transfers: remind, then each transfer arrives on the beat; balances follow
  const bal = NET.slice();
  SETTLE.forEach(([a, b, x], k) => {
    const tc = T.check + k * 0.5, rem = seg(t, T.tap2 + 0.1 + k * 0.06, 0.15, ease.linear), chk = seg(t, tc, 0.18);
    const row = $('#tr' + k), [A, B, C] = row.querySelectorAll('.st > div');
    show(A, 1 - rem); show(B, rem * (1 - chk)); show(C, chk);
    C.style.transform = `scale(${t >= tc ? (0.6 + 0.4 * spring(t - tc, { stiffness: 300, damping: 14 })).toFixed(3) : 0.6})`;
    if (t >= tc) { bal[a] += x; bal[b] -= x; }
  });
  bal.forEach((v, i) => { const el = $('#bal' + i); el.textContent = sgn(v); st(el, { background: v === 0 ? '#DDF3EA' : v > 0 ? '#EAF0FF' : '#FDE5DE', color: v === 0 ? '#118457' : v > 0 ? '#2B57C8' : '#D4502F' }); });

  // the stamp, then the logo
  const seal = $('#seal');
  if (t >= T.stamp) {
    const [cx, cy] = center($('#screen')), slam = seg(t, T.stamp, 0.16, ease.in), mv = seg(t, T.logo, 0.9, ease.inOut);
    const x = lerp(cx, 960, mv), y = lerp(cy + 40, 390, mv), s = lerp(lerp(2.6, 1, slam), 1.5, mv) * (1 + 0.04 * seg(t, T.tag, 3.0, ease.inOutSoft)), rot = lerp(-9, -5, mv);
    show(seal, Math.min(1, slam * 3)); seal.style.transform = `translate(${x - 115}px, ${y - 115}px) rotate(${rot}deg) scale(${s.toFixed(3)})`;
  } else show(seal, 0);
  show($('#tag'), seg(t, T.tag, 0.6)); $('#tag').style.transform = `translateY(${(1 - seg(t, T.tag, 0.8)) * 30}px)`;
  show($('#tag2'), seg(t, T.tag + 0.5, 0.6)); $('#tag2').style.transform = `translateY(${(1 - seg(t, T.tag + 0.5, 0.8)) * 20}px)`;

  // captions: lines rise out of a mask; the next caption waits for the previous one to leave
  CAPS.forEach(([t0, t1], i) => {
    const el = capEls[i], vis = t >= t0 && t < t1 + 0.35; el.style.display = vis ? 'block' : 'none'; if (!vis) return;
    const out = seg(t, t1, 0.3, ease.in);
    [...el.children].forEach((ln, j) => { const a = seg(t, t0 + j * 0.5, 0.5); ln.firstElementChild.style.transform = `translateY(${((1 - a) * 110).toFixed(1)}%)`; ln.style.opacity = (1 - out).toFixed(3); });
  });

  const fr = rng(Math.floor(t * FPS) + 1);
  $('#grain').style.transform = `translate(${Math.floor(fr() * 256)}px, ${Math.floor(fr() * 256)}px)`;
}

// ---------- sound events ----------
function buildEvents() {
  const E = [], add = (t, type, o = {}) => E.push({ t: +t.toFixed(3), type, ...o });
  MSG.forEach(([, , t0], k) => { if (t0 >= 0) add(t0, 'msg', { k }); });
  add(T.morph, 'morph');
  add(T.reveal, 'reveal'); LAND.forEach((t, k) => add(t, 'land', { k }));
  add(T.count, 'count', { dur: 1.0 }); add(T.tap, 'tap'); add(T.push, 'push', { dur: 1.0 });
  P.forEach((_, i) => add(T.graph + i * 0.125, 'node', { i }));
  naive.forEach((a, k) => add(a.t0, 'naive', { k }));
  add(T.clear, 'clear'); P.forEach((_, i) => add(T.clear + 0.25 + i * 0.125, 'net', { i }));
  bold.forEach((b, k) => add(b.t0, 'bold', { k }));
  add(T.bold + 1.75, 'four'); add(T.note, 'note'); add(T.pull, 'pull', { dur: 1.1 });
  add(T.tap2, 'tap'); SETTLE.forEach((_, k) => add(T.check + k * 0.5, 'check', { k }));
  add(T.stamp + 0.16, 'stamp'); add(T.logo, 'logo', { dur: 0.9 }); add(T.tag, 'tag');
  return E.sort((a, b) => a.t - b.t);
}

await loadFonts([
  ['Noto Sans SC', 'fonts/NotoSansSC-Bold.otf', { weight: '700' }],
  ['Noto Sans SC', 'fonts/NotoSansSC-Regular.otf', { weight: '400' }],
  ['Noto Serif SC', 'fonts/NotoSerifSC-Bold.otf', { weight: '700' }],
  ['Ubuntu', 'fonts/Ubuntu-B.ttf', { weight: '700' }],
]);
register({ duration: DUR, fps: FPS, width: W, height: H, seek, meta: { events: buildEvents(), settle: SETTLE, net: NET } });
seek(0);
