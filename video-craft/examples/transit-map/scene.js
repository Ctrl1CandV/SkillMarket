// transit-map — 18 s explainer in a designed, editorial look (paper, grid, big type, mono labels, one red accent).
// Why two stations that sit next to each other on a subway map can be a twenty-minute walk apart.
// Core picture: the same three lines drawn as streets (curved, uneven, a river between two stops) straighten and
// space out into the map; the long gap between 河西 and 东桥 shrinks to one step. Parts from kit/graphic.js.
import { register, ease, clamp, lerp } from '../../kit/kit.js';
import { layer, strokeTo, finish } from '../../kit/draw.js';
import { paper, grid, rule, label, headline, card, ring, ruler, wipe, iris, SANS, MONO } from '../../kit/graphic.js';

const W = 1920, H = 1080, FPS = 30, DUR = 18;
const PAPER = '#ECE7DC', SHEET = '#F5F2EB', INK = '#16181D', RED = '#E2432E', BLUE = '#2B55E6', AMBER = '#D99A2B', RIVER = '#223047';
const ctx = document.getElementById('cv').getContext('2d');

// shot times: cuts sit on bar lines of the 120 BPM score (one bar = 2 s)
const T = { street: 4.0, walk: 2.9, walkDur: 2.3, morph: 9.4, morphEnd: 12.4, rule: 14.0, end: 18 };   // walk: seconds into the street shot

// ---- the network: each stop is [street x, street y, map x, map y] in map units; bends curve the street segments
const LINES = [
  { color: RED, stops: [[0.5, 5.6, 0.6, 4.4], [1.6, 5.1, 1.7, 4.4], [2.5, 4.7, 2.8, 4.4], [3.3, 4.2, 3.9, 4.4], [4.0, 3.8, 5.0, 4.4], [8.6, 3.0, 6.1, 4.4], [9.4, 2.4, 7.2, 4.4]], bends: [0.3, -0.25, 0.3, -0.2, 0.22, -0.35] },
  { color: BLUE, stops: [[3.0, 0.6, 3.9, 0.8], [3.4, 1.6, 3.9, 2.0], [3.1, 2.7, 3.9, 3.2], [3.3, 4.2, 3.9, 4.4], [3.9, 5.4, 3.9, 5.6], [3.5, 6.6, 4.75, 6.45], [4.2, 7.6, 5.6, 7.3]], bends: [-0.3, 0.35, -0.25, 0.3, -0.3, 0.25] },
  { color: AMBER, stops: [[6.3, 0.4, 6.1, 0.8], [6.9, 1.3, 6.1, 2.0], [7.6, 2.2, 6.1, 3.2], [8.6, 3.0, 6.1, 4.4], [8.9, 4.3, 6.95, 5.25], [8.3, 5.7, 7.8, 6.1], [9.1, 6.9, 8.65, 6.95]], bends: [0.25, -0.3, 0.2, 0.3, -0.3, 0.25] },
];
const A = [0, 4], B = [0, 5];                        // 河西 and 东桥: neighbours on the red line, a river apart on the street
const SHARED = [[1, 3], [2, 3]];                     // stops drawn once as interchanges (with red 3 and red 5)

// fit a map-units rectangle into a pixel box
const fit = (bx, by, bw, bh, [x0, y0, x1, y1]) => { const s = Math.min(bw / (x1 - x0), bh / (y1 - y0)); return { x: bx + (bw - (x1 - x0) * s) / 2 - x0 * s, y: by + (bh - (y1 - y0) * s) / 2 - y0 * s, s }; };
const BIG = fit(800, 140, 1000, 800, [0.5, 0.4, 9.4, 7.6]);
const px = (box, [x, y]) => [box.x + x * box.s, box.y + y * box.s];
const stopAt = (li, si, m) => { const [gx, gy, dx, dy] = LINES[li].stops[si]; return [lerp(gx, dx, m), lerp(gy, dy, m)]; };

// a line as a sampled polyline in map units; m = 0 street, 1 map (bends vanish, stops move to the grid)
function linePts(L, li, m) {
  const P = L.stops.map((_, si) => stopAt(li, si, m)), out = [P[0]];
  for (let i = 0; i < P.length - 1; i++) {
    const [ax, ay] = P[i], [bx, by] = P[i + 1], len = Math.hypot(bx - ax, by - ay) || 1, b = L.bends[i] * (1 - m) * 0.5;
    const cx = (ax + bx) / 2 - (by - ay) * b, cy = (ay + by) / 2 + (bx - ax) * b;
    for (let k = 1; k <= 14; k++) { const u = k / 14, v = 1 - u; out.push([v * v * ax + 2 * v * u * cx + u * u * bx, v * v * ay + 2 * v * u * cy + u * u * by]); }
  }
  return out;
}

// the point a share u (0..1) of the way along a polyline
function along(pts, u) {
  let total = 0; const d = [];
  for (let i = 1; i < pts.length; i++) { d.push(Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])); total += d[i - 1]; }
  let left = clamp(u) * total;
  for (let i = 1; i < pts.length; i++) { if (left <= d[i - 1]) { const f = left / (d[i - 1] || 1); return [lerp(pts[i - 1][0], pts[i][0], f), lerp(pts[i - 1][1], pts[i][1], f)]; } left -= d[i - 1]; }
  return pts[pts.length - 1];
}

// the whole map into box: m morph, k draw-on (0..1), lw line width
function drawMap(c, box, m, { k = 1, lw = 14, river = 0, stationFill = SHEET, trains = 0, t = 0, trainColor = SHEET } = {}) {
  if (river > 0) {                                   // the river only exists on the street drawing
    c.save(); c.globalAlpha = river; c.fillStyle = RIVER; c.beginPath();
    for (let y = -0.5; y <= 8.5; y += 0.25) c.lineTo(...px(box, [6.3 + 0.35 * Math.sin(y * 0.9), y]));
    for (let y = 8.5; y >= -0.5; y -= 0.25) c.lineTo(...px(box, [7.1 + 0.35 * Math.sin(y * 0.9 + 0.4), y]));
    c.fill(); c.restore();
  }
  c.save(); c.lineCap = 'round'; c.lineJoin = 'round'; c.lineWidth = lw;
  LINES.forEach((L, li) => { c.strokeStyle = L.color; strokeTo(c, linePts(L, li, m).map((p) => px(box, p)), clamp(k * 1.4 - li * 0.2)); });
  // stops appear as the line reaches them; interchanges are larger
  LINES.forEach((L, li) => L.stops.forEach((_, si) => {
    if (clamp(k * 1.4 - li * 0.2) < si / (L.stops.length - 1)) return;
    if (SHARED.some(([a, b]) => a === li && b === si)) return;
    const big = (li === 0 && (si === 3 || si === 5)), [x, y] = px(box, stopAt(li, si, m));
    c.fillStyle = stationFill; c.strokeStyle = INK; c.lineWidth = lw * (big ? 0.4 : 0.32);
    c.beginPath(); c.arc(x, y, lw * (big ? 1.25 : 0.8), 0, 7); c.fill(); c.stroke();
  }));
  // trains keep running: two on each line, back and forth, so the map is never still
  if (trains > 0 && k >= 1) {
    c.globalAlpha *= trains; c.fillStyle = trainColor;
    LINES.forEach((L, li) => {
      const pts = linePts(L, li, m).map((p) => px(box, p));
      for (const off of [0.1, 0.55]) {
        const ph = (t * 0.07 + off + li * 0.23) % 2, u = ph < 1 ? ph : 2 - ph, [x, y] = along(pts, u);
        c.beginPath(); c.arc(x, y, lw * 0.42, 0, 7); c.fill();
      }
    });
  }
  c.restore();
}

// a dimension line between two points, offset to one side, with end ticks and a label
// returns where the label sits, so a readout can go under it
function dimension(c, p, q, k, text, s, { color = RED, off = 56, textColor = color, size = 26, exit } = {}) {
  const dx = q[0] - p[0], dy = q[1] - p[1], len = Math.hypot(dx, dy) || 1, nx = dy / len, ny = -dx / len;
  const a = [p[0] + nx * off, p[1] + ny * off], b = [p[0] + nx * off + dx * ease.out(clamp(k)), p[1] + ny * off + dy * ease.out(clamp(k))];
  if (k <= 0) return;
  c.save(); c.strokeStyle = color; c.lineWidth = 3; c.setLineDash([10, 8]); c.beginPath(); c.moveTo(...a); c.lineTo(...b); c.stroke();
  c.setLineDash([]); c.lineWidth = 3; c.beginPath();
  for (const e of [a, ...(k >= 1 ? [b] : [])]) { c.moveTo(e[0] - nx * 14, e[1] - ny * 14); c.lineTo(e[0] + nx * 14, e[1] + ny * 14); }
  c.font = `500 ${size}px ${MONO}`; const w = c.measureText(text).width + 0.08 * size * text.length;
  c.stroke(); c.restore();
  // keep the whole label clear of a sloped line: drop it by the slope over half its width
  const dir = Math.sign(ny * Math.sign(off)) || 1, drop = Math.abs(dy / (dx || 1)) * w / 2 + 16;
  const lx = (a[0] + p[0] + nx * off + dx) / 2, ly = (a[1] + p[1] + ny * off + dy) / 2 + dir * drop + (dir > 0 ? size * 0.78 : -size * 0.1);
  label(c, text, lx, ly, s, { size, color: textColor, align: 'center', track: 0.08, exit });
  return [lx, ly];
}

// station names next to 河西 and 东桥
function names(c, box, m, s, color) {
  const [ax, ay] = px(box, stopAt(...A, m)), [bx, by] = px(box, stopAt(...B, m)), sz = Math.round(Math.max(22, box.s * 0.28));
  c.save(); c.globalAlpha *= clamp(s / 0.3); c.fillStyle = color; c.font = `900 ${sz}px ${SANS}`; c.textAlign = 'center';
  c.fillText('河西', ax, ay - box.s * 0.45); c.fillText('东桥', bx, by - box.s * 0.45); c.restore();
}

// the map card used on paper: diagram only, on a lighter sheet
const MAPC = layer(640, 520), mc = MAPC.getContext('2d');
const SMALL = fit(30, 40, 580, 440, [0.6, 0.8, 8.65, 7.3]);
function drawCard(t, s) {
  mc.fillStyle = SHEET; mc.fillRect(0, 0, 640, 520);
  drawMap(mc, SMALL, 1, { lw: 8, trains: 1, t, trainColor: INK });
  const p = px(SMALL, stopAt(...A, 1)), q = px(SMALL, stopAt(...B, 1));
  ring(mc, p[0], p[1], 22, clamp(s / 0.6), { color: RED, width: 3, sweep: Math.PI * 1.5, rot: t * 0.8 });
  ring(mc, q[0], q[1], 22, clamp((s - 0.15) / 0.6), { color: RED, width: 3, sweep: Math.PI * 1.5, rot: -t * 0.8 });
  names(mc, SMALL, 1, s, INK);
  dimension(mc, p, q, (s - 1.4) / 0.5, '1 格', s - 1.5, { off: -44 });
}

// a slow push of a whole layout about the frame centre
const push = (c, z) => { c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-W / 2, -H / 2); };

// ---- shots ---------------------------------------------------------------------------------------------------
function shotMapOnPaper(c, t) {                       // 0–4 s: the confusion, stated over the map people use
  paper(c, PAPER);
  c.save(); push(c, 1 + 0.03 * clamp(t / 4));
  const g = grid(c, clamp(0.55 + t / 1.4), { x: 120, y: 120, w: 1680, h: 840, cols: 12, rows: 6, color: 'rgba(22,24,29,.09)' });
  rule(c, g.x[0], 150, 260, clamp(0.4 + t / 0.6), { color: RED, width: 6 });
  label(c, 'TRANSIT MAP / 01', g.x[0], 200, t + 1.2, { size: 22, color: INK });
  headline(c, ['图上两站挨着，', { text: '走起来二十分钟。', accent: [3, 7, RED] }], g.x[0], 300, t + 0.35, { size: 112 });
  headline(c, ['示意 · 站名与距离为虚构'], g.x[0], 610, t - 1.6, { size: 26, weight: 400, color: 'rgba(22,24,29,.7)', stagger: 0.015 });
  drawCard(t, t - 0.2);
  card(c, MAPC, 1100, 240, 600, 488, t + 0.2, { shadow: { color: 'rgba(22,24,29,.16)', dx: 16, dy: 16 }, markColor: INK, push: 0.012 });
  c.restore();
}

function shotStreets(c, t, m, outS) {                  // 4–14 s: the same lines as streets, then straightened into the map
  c.fillStyle = INK; c.fillRect(0, 0, W, H);
  const s = t - T.street;
  grid(c, clamp(s / 1.2), { x: 120, y: 120, w: 1680, h: 840, cols: 12, rows: 6, color: 'rgba(236,231,220,.06)' });
  const z = 1 + 0.07 * ease.inOutSoft(clamp((t - T.street) / 10)), cx = 1300, cy = 540;       // slow push on the map
  const box = { x: cx - (cx - BIG.x) * z, y: cy - (cy - BIG.y) * z, s: BIG.s * z };
  drawMap(c, box, m, { k: clamp((s + 0.3) / 1.4), lw: 14, river: clamp(1 - m * 1.8), stationFill: PAPER, trains: 1, t, trainColor: PAPER });
  const p = px(box, stopAt(...A, m)), q = px(box, stopAt(...B, m));
  ring(c, p[0], p[1], 34, clamp((s - 1.5) / 0.6), { color: RED, width: 3, sweep: Math.PI * 1.5, rot: t * 0.8 });
  ring(c, q[0], q[1], 34, clamp((s - 1.65) / 0.6), { color: RED, width: 3, sweep: Math.PI * 1.5, rot: -t * 0.8 });
  names(c, box, m, s - 1.5, PAPER);
  // the measured gap: real distance on the street drawing, then one step on the map
  const onMap = m > 0.85;
  const lp = dimension(c, p, q, (s - 2.2) / 0.7, onMap ? '1 格' : '1.6 km · 步行约 20 分钟', onMap ? t - (T.morph + 2.6) : s - 2.4, { off: -64, textColor: PAPER, size: 36, exit: onMap ? undefined : t - T.morph });
  // someone walking it: a red dot crawls along the measured gap while a readout under the distance runs the minutes
  const w = ease.inOutSoft(clamp((s - T.walk) / T.walkDur)), wa = clamp(1 - clamp((t - T.morph) / 0.3));
  if (w > 0 && wa > 0 && lp) {
    const dx = q[0] - p[0], dy = q[1] - p[1], len = Math.hypot(dx, dy), nx = dy / len, ny = -dx / len;
    c.save(); c.globalAlpha *= wa; c.fillStyle = RED; c.beginPath(); c.arc(p[0] + dx * w - nx * 64, p[1] + dy * w - ny * 64, 11, 0, 7); c.fill();
    c.font = `500 26px ${MONO}`; c.textAlign = 'center'; c.fillStyle = RED; c.letterSpacing = '2px';
    c.fillText(`WALK ${String(Math.floor(w * 20)).padStart(2, '0')}:${String(Math.floor(w * 1200) % 60).padStart(2, '0')}`, lp[0], lp[1] + 50);
    c.restore();
  }
  // a street map has a scale bar; the subway map has none (1 km = 2.92 map units, from 1.6 km between the two stops)
  const scaleA = clamp(1 - m * 1.6), km = 2.92 * box.s;
  if (scaleA > 0) {
    c.save(); c.globalAlpha *= scaleA;
    ruler(c, 120, 930, km, clamp((s - 0.6) / 0.6), { n: 10, major: 5, color: PAPER, h: 8, hMajor: 20 });
    label(c, '0', 120, 970, s - 0.9, { size: 20, color: PAPER, track: 0.05 }); label(c, '1 km', 120 + km, 970, s - 1.0, { size: 20, color: PAPER, track: 0.05, align: 'center' });
    c.restore();
  }
  label(c, 'NO SCALE · 没有比例尺', 120, 940, t - (T.morph + 2.4), { size: 22, color: RED, track: 0.1, exit: outS });
  rule(c, 120, 150, 260, clamp(s / 0.5), { color: RED, width: 6 });
  if (t < T.morph + 0.3) label(c, 'STREETS / 02', 120, 200, s, { size: 22, color: PAPER, exit: t - T.morph });
  else label(c, 'DIAGRAM / 03', 120, 200, t - T.morph - 0.3, { size: 22, color: PAPER, exit: outS });
  headline(c, ['同样两站，', { text: '隔着一条河。', accent: [2, 5, '#7FA6FF'] }], 120, 300, s - 0.4, { size: 88, color: PAPER, exit: t - (T.morph - 0.5) });
  // the words land with the change they name
  headline(c, ['画成地铁图：'], 120, 300, t - T.morph, { size: 88, color: PAPER, exit: outS });
  headline(c, ['线拉直，'], 120, 420, t - (T.morph + 0.9), { size: 88, color: PAPER, exit: outS });
  headline(c, [{ text: '站隔得一样远。', accent: [3, 6, RED] }], 120, 540, t - (T.morph + 2.0), { size: 88, color: PAPER, exit: outS });
  return box;
}

function shotRule(c, t) {                             // 14–18 s: what to do with it
  const s = t - T.rule;
  paper(c, PAPER);
  c.save(); push(c, 1.03 - 0.03 * ease.out(clamp(s / 4)));
  grid(c, 1, { x: 120, y: 120, w: 1680, h: 840, cols: 12, rows: 6, color: 'rgba(22,24,29,.09)' });
  rule(c, 120, 150, 260, clamp((s + 0.3) / 0.5), { color: RED, width: 6 });
  label(c, 'HOW TO READ / 04', 120, 200, s + 0.2, { size: 22, color: INK });
  headline(c, [{ text: '看顺序和换乘，', accent: [1, 6, RED] }, '别看远近。'], 120, 300, s + 0.4, { size: 120 });
  headline(c, ['要走路，换成街道地图看一眼。'], 120, 600, s - 0.8, { size: 40, weight: 400, stagger: 0.015 });
  headline(c, ['1933 年起，伦敦地铁图改用 Harry Beck 的示意画法。'], 120, 880, s - 1.4, { size: 26, weight: 400, color: 'rgba(22,24,29,.7)', stagger: 0.008, unit: 'char' });
  drawCard(t, s + 0.3);
  card(c, MAPC, 1100, 240, 600, 488, s + 0.3, { from: 'bottom', shadow: { color: 'rgba(22,24,29,.16)', dx: 16, dy: 16 }, markColor: INK });
  c.restore();
}

function seek(t) {
  const frame = Math.round(t * FPS), m = ease.inOut(clamp((t - T.morph) / (T.morphEnd - T.morph)));
  ctx.clearRect(0, 0, W, H);
  if (t < T.street) {
    shotMapOnPaper(ctx, t);
    wipe(ctx, (t - (T.street - 0.35)) / 0.6, (c) => shotStreets(c, t, 0), { color: RED });
  } else if (t < T.rule) {
    if (t < T.street + 0.25) { shotMapOnPaper(ctx, t); wipe(ctx, (t - (T.street - 0.35)) / 0.6, (c) => shotStreets(c, t, 0), { color: RED }); }
    else {
      const box = shotStreets(ctx, t, m, t - (T.rule - 1.0));
      const a = px(box, stopAt(...A, 1));
      iris(ctx, (t - (T.rule - 0.5)) / 0.8, (c) => shotRule(c, t), { x: a[0], y: a[1], ring: RED });
    }
  } else {
    if (t < T.rule + 0.3) { const box = shotStreets(ctx, t, 1, t - (T.rule - 1.0)); const a = px(box, stopAt(...A, 1)); iris(ctx, (t - (T.rule - 0.5)) / 0.8, (c) => shotRule(c, t), { x: a[0], y: a[1], ring: RED }); }
    else shotRule(ctx, t);
  }
  finish(ctx, frame, { vignette: 0.12, grain: 0.035 });
}

// sound cues for score.js
const events = [
  { t: 0.05, type: 'rise' }, { t: 1.9, type: 'tick' }, { t: 3.65, type: 'wipe' },
  ...[0, 1, 2].map((i) => ({ t: T.street + 0.7 + i * 0.2, type: 'line', i })),        // each line reaches its end
  { t: T.street + 1.5, type: 'mark' }, { t: T.street + 2.2, type: 'measure', dur: 0.7 },
  { t: T.street + T.walk, type: 'walk', dur: T.walkDur }, { t: T.street + T.walk + T.walkDur, type: 'arrive' },
  { t: T.morph, type: 'morph', dur: T.morphEnd - T.morph }, { t: T.morph + 0.9, type: 'step', k: 0 }, { t: T.morph + 2.0, type: 'step', k: 1 },
  { t: T.morph + 2.6, type: 'tick' }, { t: T.rule - 0.5, type: 'iris', dur: 0.8 }, { t: T.rule + 0.1, type: 'land' }, { t: T.rule + 1.6, type: 'end' },
];

register({ duration: DUR, fps: FPS, width: W, height: H, seek, meta: { events } });
seek(0);
