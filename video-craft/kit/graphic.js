// graphic.js — Canvas 2D parts for designed motion graphics: paper and grid, big type that rises or lands,
// small mono labels that decode, corner marks, image cards, slanted colour bands, HUD rings and rulers,
// waveforms, a flat-shaded 3D surface, and mask transitions (wipe, iris, halftone).
// Colours are '#rrggbb' strings (rgba() strings also work where a part only strokes or fills).
// Pure functions of their inputs. Parts that draw on take k (0..1); parts with their own choreography take
// s = seconds since the part started (negative: not yet) and an optional exit = seconds since it began leaving.
// The list of effects follows the HyperFrames registry (github.com/heygen-com/hyperframes, Apache-2.0);
// the code is written for this kit. When to use which: references/graphic.md.
import { clamp, lerp, rng, ease, rgba, hex, FONT_STACK } from './kit.js';
import { layer } from './draw.js';

export const MONO = '"JetBrains Mono", "IBM Plex Mono", "Cascadia Mono", Consolas, "Courier New", monospace';
export const SANS = FONT_STACK.sans;
const TAU = Math.PI * 2;

// ---- ground and layout ------------------------------------------------------------------------------------

// flat paper (or dark card) with fixed fine grain and faint fibres; cached, so keep the colour constant per scene
const paperCache = new Map();
export function paper(ctx, color, { grain = 0.05, fibres = 0.04, seed = 3 } = {}) {
  const { width: W, height: H } = ctx.canvas, key = `${W}x${H}:${color}:${grain}:${fibres}:${seed}`;
  let c = paperCache.get(key);
  if (!c) {
    c = layer(W, H);
    const g = c.getContext('2d');
    g.fillStyle = color; g.fillRect(0, 0, W, H);
    const w = W >> 1, h = H >> 1, n = layer(w, h), nx = n.getContext('2d'), im = nx.createImageData(w, h), r = rng(seed);
    for (let i = 0; i < im.data.length; i += 4) {
      const v = r() < 0.5 ? 0 : 255;
      im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255 * grain * r();
    }
    nx.putImageData(im, 0, 0);
    g.drawImage(n, 0, 0, W, H);
    const f = rng(seed + 1);
    g.lineWidth = 1;
    for (let i = 0; i < (W * H) / 9000; i++) {
      const x = f() * W, y = f() * H, a = f() * Math.PI, l = 6 + f() * 22;
      g.strokeStyle = `rgba(${f() < 0.5 ? '0,0,0' : '255,255,255'},${fibres * (0.4 + f() * 0.6)})`;
      g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * l, y + Math.sin(a) * l); g.stroke();
    }
    if (paperCache.size > 8) paperCache.delete(paperCache.keys().next().value);
    paperCache.set(key, c);
  }
  ctx.drawImage(c, 0, 0);
}

// layout grid of cols × rows inside a box; lines draw on with k. Returns the line positions to place things on.
export function grid(ctx, k = 1, { x = 0, y = 0, w = ctx.canvas.width, h = ctx.canvas.height, cols = 12, rows = 6, color = 'rgba(0,0,0,.12)', width = 1.5, dots = false } = {}) {
  const X = Array.from({ length: cols + 1 }, (_, i) => x + (w * i) / cols);
  const Y = Array.from({ length: rows + 1 }, (_, j) => y + (h * j) / rows);
  const at = (i, n) => ease.out(clamp(k * 1.5 - (i / n) * 0.5));
  ctx.save(); ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = width;
  if (dots) {
    X.forEach((a, i) => { const kk = at(i, X.length); if (kk > 0) { ctx.globalAlpha = kk; for (const b of Y) ctx.fillRect(a - 1.5, b - 1.5, 3, 3); } });
  } else {
    ctx.beginPath();
    X.forEach((a, i) => { const kk = at(i, X.length); if (kk > 0) { ctx.moveTo(a, y); ctx.lineTo(a, y + h * kk); } });
    Y.forEach((b, j) => { const kk = at(j, Y.length); if (kk > 0) { ctx.moveTo(x, b); ctx.lineTo(x + w * kk, b); } });
    ctx.stroke();
  }
  ctx.restore();
  return { x: X, y: Y, col: w / cols, row: h / rows };
}

// a thin rule or accent bar drawing on (from 'left', 'right' or 'center')
export function rule(ctx, x, y, w, k = 1, { color = '#111', width = 2, from = 'left' } = {}) {
  const kk = ease.out(clamp(k));
  if (kk <= 0) return;
  const len = w * kk, x0 = from === 'center' ? x + (w - len) / 2 : from === 'right' ? x + w - len : x;
  ctx.save(); ctx.fillStyle = color; ctx.fillRect(x0, y - width / 2, len, width); ctx.restore();
}

// corner marks (crop brackets) just outside a box, drawing on with k
export function marks(ctx, x, y, w, h, k = 1, { len = 18, gap = 10, color = '#111', width = 2 } = {}) {
  const kk = ease.out(clamp(k));
  if (kk <= 0) return;
  const L = len * kk, x0 = x - gap, y0 = y - gap, x1 = x + w + gap, y1 = y + h + gap;
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineCap = 'square'; ctx.beginPath();
  for (const [cx, cy, sx, sy] of [[x0, y0, 1, 1], [x1, y0, -1, 1], [x0, y1, 1, -1], [x1, y1, -1, -1]]) {
    ctx.moveTo(cx + sx * L, cy); ctx.lineTo(cx, cy); ctx.lineTo(cx, cy + sy * L);
  }
  ctx.stroke(); ctx.restore();
}

// a slanted colour band over the full height (the diagonal panel of editorial layouts); animate x and w yourself
export function slant(ctx, x, w, { angle = 14, color = '#E8412C', y0 = 0, y1 = ctx.canvas.height } = {}) {
  const off = (Math.tan((angle * Math.PI) / 180) * (y1 - y0)) / 2;
  ctx.save(); ctx.fillStyle = color; ctx.beginPath();
  ctx.moveTo(x + off, y0); ctx.lineTo(x + w + off, y0); ctx.lineTo(x + w - off, y1); ctx.lineTo(x - off, y1);
  ctx.closePath(); ctx.fill(); ctx.restore();
}

// ---- type ----------------------------------------------------------------------------------------------

const POOL = { d: '0123456789', u: 'ABCDEFGHJKLMNPQRSTUVWXYZ', l: 'abcdefghijkmnopqrstuvwxyz', h: '口日目田山川工土王中石木月' };
const glyphClass = (ch) => (/[0-9]/.test(ch) ? 'd' : /[A-Z]/.test(ch) ? 'u' : /[a-z]/.test(ch) ? 'l' : /[㐀-鿿]/.test(ch) ? 'h' : null);

// the text at progress k: the first part is final, the rest rolls through look-alike glyphs (digits stay digits)
export function scramble(text, k, tick = 0, seed = 1) {
  const chars = [...text], n = Math.floor(clamp(k) * chars.length + 1e-6);
  return chars.map((ch, i) => {
    const c = i < n ? null : glyphClass(ch);
    if (!c) return ch;
    const pool = POOL[c];
    return pool[Math.floor(rng(seed * 7919 + i * 131 + tick * 17)() * pool.length)];
  }).join('');
}

// small mono label (tracked caps, index numbers, units, readouts): fades in while its characters decode left to right
export function label(ctx, text, x, y, s, { size = 20, color = '#111', track = 0.18, weight = 500, font = MONO, align = 'left', dur, seed = 1, exit } = {}) {
  if (s < 0) return 0;
  const D = dur ?? clamp(0.3 + 0.05 * [...text].length, 0.45, 1.4);
  const a = clamp(s / 0.15) * (exit == null ? 1 : 1 - clamp(exit / 0.3));
  if (a <= 0) return 0;
  ctx.save();
  ctx.globalAlpha *= a; ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = 'alphabetic';
  ctx.font = `${weight} ${size}px ${font}`; ctx.letterSpacing = `${track * size}px`;
  ctx.fillText(scramble(text, ease.outSoft(clamp(s / D)), Math.floor(s * 20), seed), x, y);
  const w = ctx.measureText(text).width;
  ctx.restore();
  return w;
}

// big type. lines: ['耳朵先到', { text: '眼睛再跟上', size: 80, color: '#333', accent: [0, 2, '#E8412C'] }]
// (x, y) is the top-left of the block (top-centre / top-right with align). accent colours characters [from, to).
// mode: 'rise' characters rise out of a mask one after another · 'slam' the block lands from 1.5× with a short shake
//       'track' letter-spacing closes in · 'glitch' torn slices settle · 'cut' just there
// exit (seconds since leaving; negative = not leaving yet): exitMode 'up' leaves upward, 'fade' fades. Returns the block box.
let typeLayer = null;
export function headline(ctx, lines, x, y, s, { size = 120, lead = 1.15, weight = 900, font = SANS, color = '#111', align = 'left', mode = 'rise', unit = 'char', stagger = 0.035, lineGap = 0.12, dur = 0.6, exit, exitMode = 'up', seed = 1 } = {}) {
  if (s < 0) return null;
  const rows = [];
  let yy = y;
  ctx.save();
  for (const l of lines.map((v) => (typeof v === 'string' ? { text: v } : v))) {
    const sz = l.size ?? size;
    ctx.font = `${l.weight ?? weight} ${sz}px ${l.font ?? font}`; ctx.letterSpacing = '0px';
    const chars = unit === 'line' ? [l.text] : [...l.text], ws = chars.map((c) => ctx.measureText(c).width);
    const w = ws.reduce((a, b) => a + b, 0);
    rows.push({ ...l, sz, chars, ws, w, top: yy, base: yy + sz * 0.88 });
    yy += sz * lead;
  }
  ctx.restore();
  const W = Math.max(...rows.map((r) => r.w)), box = { x: align === 'center' ? x - W / 2 : align === 'right' ? x - W : x, y, w: W, h: yy - y };
  const out = exit == null ? 0 : exit;
  const drawRows = (c, perChar) => {
    rows.forEach((r, i) => {
      c.font = `${r.weight ?? weight} ${r.sz}px ${r.font ?? font}`; c.textBaseline = 'alphabetic'; c.textAlign = 'left';
      let cx = align === 'center' ? x - r.w / 2 : align === 'right' ? x - r.w : x;
      r.chars.forEach((ch, j) => {
        const acc = r.accent && j >= r.accent[0] && j < r.accent[1];
        c.fillStyle = acc ? r.accent[2] : r.color ?? color;
        perChar(c, r, i, j, ch, cx);
        cx += r.ws[j];
      });
    });
  };
  ctx.save();
  if (exit != null && exitMode === 'fade') ctx.globalAlpha *= 1 - clamp(out / 0.35);
  if (mode === 'rise') {
    drawRows(ctx, (c, r, i, j, ch, cx) => {
      const p = ease.out(clamp((s - i * lineGap - j * stagger) / dur));
      let dy = (1 - p) * r.sz * 1.1;
      if (exit != null && exitMode === 'up') dy -= ease.in(clamp((out - i * 0.05 - j * 0.02) / 0.45)) * r.sz * 1.15;
      if (p <= 0) return;
      c.save(); c.beginPath(); c.rect(cx - r.sz * 0.2, r.base - r.sz * 0.98, r.ws[j] + r.sz * 0.4, r.sz * 1.28); c.clip();
      c.fillText(ch, cx, r.base + dy); c.restore();
    });
  } else if (mode === 'track') {
    const p = ease.outSoft(clamp(s / 0.9));
    ctx.globalAlpha *= clamp(s / 0.3);
    if (exit != null && exitMode === 'up') ctx.globalAlpha *= 1 - clamp(out / 0.35);
    drawRows(ctx, (c, r, i, j, ch, cx) => {
      const spread = (1 - p) * r.sz * 0.45, mid = (r.chars.length - 1) / 2;
      c.fillText(ch, cx + (j - mid) * spread, r.base + (1 - p) * 10);
    });
  } else if (mode === 'slam') {
    const p = ease.out(clamp(s / 0.72)), sc = lerp(1.5, 1, p), [dx, dy] = shake(s - 0.42, { amp: size * 0.1, seed });
    ctx.globalAlpha *= clamp(s / 0.12);
    if (exit != null && exitMode === 'up') { ctx.globalAlpha *= 1 - clamp(out / 0.4); ctx.translate(0, -ease.in(clamp(out / 0.45)) * size * 0.8); }
    const cx = box.x + box.w / 2, cy = box.y + box.h / 2;
    ctx.translate(cx + dx, cy + dy); ctx.scale(sc, sc); ctx.translate(-cx, -cy);
    drawRows(ctx, (c, r, i, j, ch, x0) => c.fillText(ch, x0, r.base));
  } else if (mode === 'glitch') {
    const { width: CW, height: CH } = ctx.canvas;
    if (!typeLayer || typeLayer.width !== CW || typeLayer.height !== CH) typeLayer = layer(CW, CH);
    const g = typeLayer.getContext('2d');
    g.clearRect(0, 0, CW, CH);
    drawRows(g, (c, r, i, j, ch, x0) => c.fillText(ch, x0, r.base));
    if (exit != null && exitMode === 'up') ctx.globalAlpha *= 1 - clamp(out / 0.35);
    glitch(ctx, typeLayer, clamp(s / 0.55), { seed, amp: size * 0.7, area: [box.x - size, box.y - size * 0.2, box.w + size * 2, box.h + size * 0.4] });
  } else {
    if (exit != null && exitMode === 'up') ctx.globalAlpha *= 1 - clamp(out / 0.35);
    drawRows(ctx, (c, r, i, j, ch, x0) => c.fillText(ch, x0, r.base));
  }
  ctx.restore();
  return box;
}

// a picture (a canvas you drew into) torn into horizontal slices that settle back over k 0→1.
// area = [x, y, w, h] limits the work to where the picture is; bars = colour of the odd block that flashes in
export function glitch(ctx, src, k, { x = 0, y = 0, amp = 80, slices = 16, seed = 1, bars = '#E8412C', area } = {}) {
  if (k >= 1) { ctx.drawImage(src, x, y); return; }
  if (k <= 0) return;
  const [ax, ay, aw, ah] = area ?? [0, 0, src.width, src.height];
  const r = rng(seed * 101 + Math.floor(k * 12)), decay = 1 - ease.inOut(k);
  let yy = Math.max(0, ay);
  const y1 = Math.min(src.height, ay + ah);
  ctx.save();
  while (yy < y1) {
    const sh = Math.min(y1 - yy, Math.max(3, ((0.3 + r() * 1.7) * ah) / slices));
    const dx = (r() - 0.5) * 2 * amp * decay * (r() < 0.55 ? 1 : 0.12);
    ctx.drawImage(src, ax, yy, aw, sh, x + ax + dx, y + yy, aw, sh);
    if (bars && r() < 0.2 * decay) { ctx.fillStyle = bars; ctx.fillRect(x + ax + r() * aw * 0.7 + dx, y + yy, aw * (0.04 + r() * 0.2), sh * 0.7); }
    yy += sh;
  }
  ctx.restore();
}

// impact shake: a few frames of decaying offset after a landing at s = 0 → [dx, dy]
export function shake(s, { amp = 14, frames = 3, fps = 30, seed = 1 } = {}) {
  const f = Math.floor(s * fps);
  if (s < 0 || f >= frames) return [0, 0];
  const r = rng(seed * 31 + f), d = amp * (1 - f / frames);
  return [(r() - 0.5) * 2 * d, (r() - 0.5) * 2 * d];
}

// ---- pictures in the layout ----------------------------------------------------------------------------

// load an image file next to the page (works from file://, unlike fetch); await it before register()
export const image = (url) => new Promise((res, rej) => {
  const im = new Image();
  im.onload = () => res(im); im.onerror = () => rej(new Error(`image not loaded: ${url}`)); im.src = url;
});

// draw an image (or a canvas) to fill a box, cropping the overflow; zoom > 1 pushes in around the focus (fx, fy in 0..1)
export function cover(ctx, img, x, y, w, h, { zoom = 1, fx = 0.5, fy = 0.5 } = {}) {
  const iw = img.naturalWidth || img.width, ih = img.naturalHeight || img.height;
  const sc = Math.max(w / iw, h / ih) * zoom, dw = iw * sc, dh = ih * sc;
  ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
  ctx.drawImage(img, x + (w - dw) * fx, y + (h - dh) * fy, dw, dh);
  ctx.restore();
}

// an image card set into the layout: revealed by a wipe from one side, pushing in slowly, with an optional
// offset block shadow, a frame colour around it (pad px) and corner marks
export function card(ctx, img, x, y, w, h, s, { dur = 0.8, from = 'left', push = 0.008, fx, fy, shadow, frame, pad = 0, markColor, exit } = {}) {
  if (s < 0) return;
  const vis = ease.out(clamp(s / dur)) * (exit == null ? 1 : 1 - ease.in(clamp(exit / 0.45)));
  if (vis <= 0) return;
  let rx = x, ry = y, rw = w, rh = h;
  if (from === 'left') rw = w * vis;
  else if (from === 'right') { rw = w * vis; rx = x + w - rw; }
  else if (from === 'bottom') { rh = h * vis; ry = y + h - rh; }
  else rh = h * vis;
  ctx.save();
  if (shadow) { ctx.fillStyle = shadow.color ?? 'rgba(0,0,0,.18)'; ctx.fillRect(rx + (shadow.dx ?? 14), ry + (shadow.dy ?? 14), rw, rh); }
  if (frame) { ctx.fillStyle = frame; ctx.fillRect(rx, ry, rw, rh); }
  ctx.beginPath(); ctx.rect(rx, ry, rw, rh); ctx.clip();
  cover(ctx, img, x + pad, y + pad, w - 2 * pad, h - 2 * pad, { zoom: 1.02 + push * s, fx, fy });
  ctx.restore();
  if (markColor) marks(ctx, x, y, w, h, clamp((s - dur * 0.6) / 0.5) * (exit == null ? 1 : 1 - clamp(exit / 0.2)), { color: markColor });
}

// darken one side of a photo so type over it reads: side 'left' | 'right' | 'top' | 'bottom'; reach = share of the frame
export function scrim(ctx, { side = 'left', color = '#000000', alpha = 0.65, reach = 0.6 } = {}) {
  const { width: W, height: H } = ctx.canvas;
  const [x0, y0, x1, y1] = { left: [0, 0, W * reach, 0], right: [W, 0, W * (1 - reach), 0], top: [0, 0, 0, H * reach], bottom: [0, H, 0, H * (1 - reach)] }[side];
  const g = ctx.createLinearGradient(x0, y0, x1, y1);
  g.addColorStop(0, rgba(color, alpha)); g.addColorStop(0.55, rgba(color, alpha * 0.45)); g.addColorStop(1, rgba(color, 0));
  ctx.save(); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
}

// ---- instruments: rings, rulers, waveforms ---------------------------------------------------------------

// HUD ring: an arc that sweeps on with k, optional tick marks along it; rot spins the ring (radians)
export function ring(ctx, x, y, r, k = 1, { from = -Math.PI / 2, sweep = TAU, width = 2, color = '#111', ticks = 0, tickLen = 10, tickWidth = 1.5, rot = 0, cap = 'butt' } = {}) {
  const kk = ease.out(clamp(k));
  if (kk <= 0) return;
  ctx.save(); ctx.strokeStyle = color; ctx.lineCap = cap;
  if (width > 0) { ctx.lineWidth = width; ctx.beginPath(); ctx.arc(x, y, r, from + rot, from + rot + sweep * kk); ctx.stroke(); }
  if (ticks) {
    ctx.lineWidth = tickWidth; ctx.beginPath();
    for (let i = 0, n = Math.round(ticks * kk); i < n; i++) {
      const a = from + rot + (i * sweep) / ticks, c = Math.cos(a), sn = Math.sin(a), r0 = r + width / 2 + 6;
      ctx.moveTo(x + c * r0, y + sn * r0); ctx.lineTo(x + c * (r0 + tickLen), y + sn * (r0 + tickLen));
    }
    ctx.stroke();
  }
  ctx.restore();
}

// ruler: n ticks along a line, every `major`-th one longer; draws on with k
export function ruler(ctx, x, y, len, k = 1, { n = 40, major = 5, h = 8, hMajor = 18, color = '#111', width = 1.5, vertical = false } = {}) {
  const m = Math.round((n + 1) * ease.out(clamp(k)));
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = width; ctx.beginPath();
  for (let i = 0; i < m; i++) {
    const d = (i * len) / n, l = i % major === 0 ? hMajor : h;
    if (vertical) { ctx.moveTo(x, y + d); ctx.lineTo(x + l, y + d); } else { ctx.moveTo(x + d, y); ctx.lineTo(x + d, y - l); }
  }
  ctx.stroke(); ctx.restore();
}

// waveform as bars centred on y: values(u, i) → 0..1 for u in 0..1 (a formula, or songAt energies), or an array.
// head (0..1) colours the bars before it with `accent` — a playhead; k draws the bars on from the left
export function wave(ctx, x, y, w, h, values, k = 1, { bars = 96, gap = 0.45, color = '#111', accent, head = 0 } = {}) {
  const bw = w / bars, kk = ease.out(clamp(k));
  ctx.save();
  for (let i = 0; i < bars; i++) {
    const u = (i + 0.5) / bars;
    if (u > kk) break;
    const v = clamp(typeof values === 'function' ? values(u, i) : values[Math.min(values.length - 1, Math.floor(u * values.length))]);
    const bh = Math.max(2, v * h);
    ctx.fillStyle = accent && u <= head ? accent : color;
    ctx.fillRect(x + i * bw + (bw * gap) / 2, y - bh / 2, bw * (1 - gap), bh);
  }
  ctx.restore();
}

// ---- a 3D form ---------------------------------------------------------------------------------------------

// flat-shaded surface from f(u, v) → [x, y, z] (u, v in 0..1; about −1..1 across), drawn far to near.
// rot = [rx, ry, rz] radians; size = pixels per unit; front/back colours for the two sides; edge = colour of the
// u-running borders (a rim); burst 0..1 throws the facets apart like a shatter (use nu 30–40 so the shards are big).
// Shapes to start from: shapes.*
export function surface(ctx, f, { x = ctx.canvas.width / 2, y = ctx.canvas.height / 2, size = 300, rot = [0, 0, 0], nu = 96, nv = 6, front = '#EDEBE6', back = '#7FD3DC', edge, edgeWidth = 3, light = [-0.4, -0.7, 0.6], ambient = 0.42, dist = 5, burst = 0, seed = 1 } = {}) {
  const [cx, sx] = [Math.cos(rot[0]), Math.sin(rot[0])], [cy, sy] = [Math.cos(rot[1]), Math.sin(rot[1])], [cz, sz] = [Math.cos(rot[2]), Math.sin(rot[2])];
  const R = ([px, py, pz]) => {
    let a = py * cx - pz * sx, b = py * sx + pz * cx; py = a; pz = b;          // about x
    a = px * cy + pz * sy; b = -px * sy + pz * cy; px = a; pz = b;              // about y
    a = px * cz - py * sz; b = px * sz + py * cz; return [a, b, pz];            // about z
  };
  const P = [];
  for (let i = 0; i <= nu; i++) { P.push([]); for (let j = 0; j <= nv; j++) P[i].push(R(f(i / nu, j / nv))); }
  const Ln = Math.hypot(...light), L = light.map((v) => v / Ln), F = hex(front), B = hex(back), r = rng(seed);
  const faces = [];
  for (let i = 0; i < nu; i++) for (let j = 0; j < nv; j++) {
    let q = [P[i][j], P[i + 1][j], P[i + 1][j + 1], P[i][j + 1]];
    const ux = q[2][0] - q[0][0], uy = q[2][1] - q[0][1], uz = q[2][2] - q[0][2], vx = q[3][0] - q[1][0], vy = q[3][1] - q[1][1], vz = q[3][2] - q[1][2];
    let n = [uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx];
    const nl = Math.hypot(...n) || 1; n = n.map((v) => v / nl);
    const rx = r(), ry = r(), rz = r();
    if (burst > 0) {
      const c = [0, 1, 2].map((d) => (q[0][d] + q[1][d] + q[2][d] + q[3][d]) / 4), cl = Math.hypot(...c) || 1;
      const off = c.map((v, d) => ((v / cl) * (0.4 + rx) * 0.7 + n[d] * (ry - 0.5) * 0.8 + (d === 1 ? (rz - 0.3) * 0.5 : 0)) * burst);
      const shrink = 1 - 0.35 * burst;
      q = q.map((p) => p.map((v, d) => c[d] + (v - c[d]) * shrink + off[d]));
    }
    const facing = n[2] >= 0, shade = ambient + (1 - ambient) * Math.abs(n[0] * L[0] + n[1] * L[1] + n[2] * L[2]);
    const col = (facing ? F : B).map((v) => Math.round(Math.min(255, v * shade)));
    faces.push({ q, z: (q[0][2] + q[1][2] + q[2][2] + q[3][2]) / 4, col, rim: edge && (j === 0 || j === nv - 1) ? j : -1 });
  }
  faces.sort((a, b) => a.z - b.z);
  const pr = ([px, py, pz]) => { const k = dist / Math.max(0.2, dist - pz); return [x + px * size * k, y + py * size * k]; };
  ctx.save(); ctx.lineJoin = 'round';
  for (const fc of faces) {
    const p = fc.q.map(pr);
    ctx.fillStyle = ctx.strokeStyle = `rgb(${fc.col})`; ctx.lineWidth = 0.8;
    ctx.beginPath(); ctx.moveTo(...p[0]); ctx.lineTo(...p[1]); ctx.lineTo(...p[2]); ctx.lineTo(...p[3]); ctx.closePath(); ctx.fill(); ctx.stroke();
    if (fc.rim >= 0) {
      ctx.strokeStyle = edge; ctx.lineWidth = edgeWidth; ctx.beginPath();
      if (fc.rim === 0) { ctx.moveTo(...p[0]); ctx.lineTo(...p[1]); } else { ctx.moveTo(...p[3]); ctx.lineTo(...p[2]); }
      ctx.stroke();
    }
  }
  ctx.restore();
}

export const shapes = {
  // a twisted band; twists = half turns along the loop (1 = Möbius), wobble bends the loop; vary phase over time
  ribbon: ({ twists = 1, width = 0.42, wobble = 0.22, phase = 0 } = {}) => (u, v) => {
    const a = u * TAU, tw = (a * twists) / 2 + phase, w = (v - 0.5) * width, Rr = 1 + wobble * Math.sin(a * 3 + phase);
    return [(Rr + w * Math.cos(tw)) * Math.cos(a), w * Math.sin(tw) + wobble * 0.6 * Math.sin(a * 2 - phase), (Rr + w * Math.cos(tw)) * Math.sin(a)];
  },
  // a rippling sheet (sound, cloth, terrain); phase moves the ripple
  sheet: ({ amp = 0.22, freq = 1.5, phase = 0 } = {}) => (u, v) => [u * 2 - 1, amp * Math.sin((u * freq + phase) * TAU) * Math.cos((v - 0.5) * 2.4), v * 1.2 - 0.6],
  // a torus (ring, tyre, donut): use nv ≈ nu / 3
  torus: ({ r = 0.35 } = {}) => (u, v) => {
    const a = u * TAU, b = v * TAU;
    return [(1 + r * Math.cos(b)) * Math.cos(a), r * Math.sin(b), (1 + r * Math.cos(b)) * Math.sin(a)];
  },
};

// ---- transitions -------------------------------------------------------------------------------------------
// Draw the outgoing picture first, then call one of these with k (0..1, linear) and a function that draws the
// incoming picture. Each eases k itself. Lengths that read well: wipe 0.5–0.7 s, iris 0.6–0.9 s, halftone 1.0–1.4 s.

function within(ctx, path, draw) { ctx.save(); ctx.beginPath(); path(ctx); ctx.clip(); draw(ctx); ctx.restore(); }

// a slanted edge sweeps across; color adds a solid band leading the edge
export function wipe(ctx, k, drawNext, { angle = 14, from = 'left', color, band = 120 } = {}) {
  const { width: W, height: H } = ctx.canvas, p = ease.inOut(clamp(k));
  if (p <= 0) return;
  const off = (Math.tan((angle * Math.PI) / 180) * H) / 2, bw = color ? band : 0, e = lerp(-bw - off, W + off, p);
  const X = (v) => (from === 'right' ? W - v : v);
  const poly = (c, a, b) => { c.moveTo(X(a + off), 0); c.lineTo(X(b + off), 0); c.lineTo(X(b - off), H); c.lineTo(X(a - off), H); c.closePath(); };
  within(ctx, (c) => poly(c, -off - W, e), drawNext);
  if (color) { ctx.save(); ctx.fillStyle = color; ctx.beginPath(); poly(ctx, e, e + bw); ctx.fill(); ctx.restore(); }
}

// a circle opens from (x, y); ring = colour of a line riding its edge
export function iris(ctx, k, drawNext, { x = ctx.canvas.width / 2, y = ctx.canvas.height / 2, ring: line, width = 4 } = {}) {
  const { width: W, height: H } = ctx.canvas, p = ease.inOut(clamp(k));
  if (p <= 0) return;
  const R = p * Math.hypot(Math.max(x, W - x), Math.max(y, H - y));
  within(ctx, (c) => c.arc(x, y, R, 0, TAU), drawNext);
  if (line && p < 1) { ctx.save(); ctx.strokeStyle = line; ctx.lineWidth = width; ctx.beginPath(); ctx.arc(x, y, R, 0, TAU); ctx.stroke(); ctx.restore(); }
}

// the next picture arrives through a growing dot field: ink dots appear, open into windows and merge.
// order 'center' | 'ltr' | 'noise'
export function halftone(ctx, k, drawNext, { pitch = 48, color = '#111', order = 'center', seed = 1 } = {}) {
  const { width: W, height: H } = ctx.canvas, r = rng(seed), dots = [];
  if (k <= 0) return;
  const maxD = Math.hypot(W / 2, H / 2);
  for (let gy = 0; gy <= H / (pitch * 0.87) + 1; gy++) for (let gx = 0; gx <= W / pitch + 1; gx++) {
    const x = gx * pitch + (gy % 2 ? pitch / 2 : 0), y = gy * pitch * 0.87, j = r() * 0.12;
    const th = order === 'ltr' ? x / W : order === 'noise' ? r() : Math.hypot(x - W / 2, y - H / 2) / maxD;
    const p = ease.out(clamp((k * 1.6 - clamp(th * 0.88 + j)) / 0.6));
    if (p > 0) dots.push([x, y, p * pitch * 0.78]);
  }
  ctx.save(); ctx.fillStyle = color; ctx.beginPath();
  for (const [x, y, rr] of dots) { ctx.moveTo(x + rr * 1.18 + 2, y); ctx.arc(x, y, rr * 1.18 + 2, 0, TAU); }
  ctx.fill(); ctx.restore();
  within(ctx, (c) => { for (const [x, y, rr] of dots) { c.moveTo(x + rr, y); c.arc(x, y, rr, 0, TAU); } }, drawNext);
}
