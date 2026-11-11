// micro.js — the world inside the air: light waves in "beam space", molecules with depth of field, scattering rings.
import { rng, clamp, lerp } from '../../kit/kit.js';

export const WAVES = [
  { nm: 700, color: '#FF4B3E', v: -300 },
  { nm: 610, color: '#FF8F2B', v: -180 },
  { nm: 575, color: '#FFD63E', v: -60 },
  { nm: 530, color: '#59E26C', v: 60 },
  { nm: 450, color: '#4F86FF', v: 180 },
  { nm: 410, color: '#9C6CFF', v: 300 },
];
export const lam = (nm) => nm * 0.26;      // wavelength in micro px
export const SPEED = 300;                   // micro px per second
export const UF = 3600;                     // the stretch of beam we zoom into

// beam space (u along the light, v across it) → screen
export const mapT = (T, u, v) => [T.ox + T.k * (u * Math.cos(T.th) - v * Math.sin(T.th)), T.oy + T.k * (u * Math.sin(T.th) + v * Math.cos(T.th))];

const hex = (h) => { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
export const rgba = (h, a) => { const [r, g, b] = hex(h); return `rgba(${r},${g},${b},${a})`; };

// a glowing sine wave along v = const between u0 and u1
export function drawWave(ctx, T, w, t, { amp = 48, u0 = 0, u1 = 9000, alpha = 1, vOff = 0, decay = 0, width = 1 } = {}) {
  if (alpha <= 0 || u1 <= u0) return;
  const L = lam(w.nm), ph = (2 * Math.PI * SPEED * t) / L;
  const step = Math.max(2, L / 24 / Math.max(T.k, 0.15));
  const pts = [];
  for (let u = u0; u <= u1 + step; u += step) {
    const uu = Math.min(u, u1), a = amp * (decay ? Math.exp(-(uu - u0) / decay) : 1);
    pts.push(mapT(T, uu, w.v + vOff + a * Math.sin((2 * Math.PI * uu) / L - ph)));
  }
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  for (const [lw, a] of [[18, 0.10], [8, 0.28], [2.6, 1]]) {
    ctx.strokeStyle = rgba(w.color, a * alpha); ctx.lineWidth = Math.max(1, lw * Math.min(1, T.k * 1.4) * width);
    ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke();
  }
  ctx.restore();
}

// white beam (all colours on top of each other)
export function drawBeam(ctx, T, u0, u1, alpha) {
  if (alpha <= 0 || u1 <= u0) return;
  const [x0, y0] = mapT(T, u0, 0), [x1, y1] = mapT(T, u1, 0);
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
  for (const [lw, a] of [[46, 0.06], [22, 0.14], [9, 0.35], [3, 0.9]]) {
    ctx.strokeStyle = `rgba(255,250,240,${a * alpha})`; ctx.lineWidth = lw; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
  }
  ctx.restore();
}

// ---- molecules ----
function sphereSprite(r, tint, blur) {
  const pad = Math.ceil(blur * 2.5) + 2, s = Math.ceil(r * 2 + pad * 2);
  const c = document.createElement('canvas'); c.width = c.height = s;
  const g = c.getContext('2d'); if (blur > 0) g.filter = `blur(${blur}px)`;
  const cx = s / 2, gr = g.createRadialGradient(cx - r * 0.38, cx - r * 0.42, r * 0.05, cx, cx, r);
  gr.addColorStop(0, '#FFFFFF'); gr.addColorStop(0.35, tint[0]); gr.addColorStop(0.85, tint[1]); gr.addColorStop(1, tint[2]);
  g.fillStyle = gr; g.beginPath(); g.arc(cx, cx, r, 0, Math.PI * 2); g.fill();
  return c;
}
const TINTS = { N2: ['#D8E6FF', '#6F8FD0', '#31477A'], O2: ['#FFE0E6', '#C98AA0', '#6B3A55'] };
const BLURS = [0, 2.5, 5, 9];
const SPR = {};
export function initSprites() {
  for (const k of Object.keys(TINTS)) SPR[k] = BLURS.map((b) => sphereSprite(40, TINTS[k], b));
}

export function makeMolecules(seed = 5, n = 46) {
  const r = rng(seed), list = [];
  for (let i = 0; i < n; i++) list.push({ u: UF + (r() - 0.5) * 2600, v: (r() - 0.5) * 1400, z: 0.55 + r() * 1.3, type: r() < 0.78 ? 'N2' : 'O2', a0: r() * 6.28, p: r() * 6.28, emit: null });
  // emitters: molecules sitting on the red and blue paths in the scattering scene
  const add = (v, wave, count) => { for (let i = 0; i < count; i++) list.push({ u: UF - 820 + i * (1640 / (count - 1)) + (r() - 0.5) * 120, v: v + (r() - 0.5) * 40, z: 0.92 + r() * 0.16, type: r() < 0.78 ? 'N2' : 'O2', a0: r() * 6.28, p: r() * 6.28, emit: wave }); };
  add(-190, 'red', 6); add(190, 'blue', 6);
  return list.sort((a, b) => b.z - a.z);
}

export function moleculePos(m, t) {
  return { u: m.u + Math.sin(t * 0.31 + m.p) * 22, v: m.v + Math.cos(t * 0.27 + m.p * 1.3) * 16, ang: m.a0 + t * 0.35 * (m.p > 3 ? 1 : -1) };
}

export function drawMolecule(ctx, T, m, t, alpha = 1, glow = 0, glowColor = '#4F86FF') {
  const { u, v, ang } = moleculePos(m, t);
  const [x, y] = mapT(T, u, v);
  const r = (17 / m.z) * T.k;
  if (r < 0.6 || alpha <= 0) return;
  const blur = Math.min(3, Math.round(Math.abs(m.z - 1) * 4.2));
  const spr = SPR[m.type][blur], sc = (r / 40);
  const dx = Math.cos(ang) * r * 0.62, dy = Math.sin(ang) * r * 0.62;
  ctx.save(); ctx.globalAlpha = alpha * (m.z > 1.45 ? 0.75 : 1);
  for (const sgn of [-1, 1]) { const w = spr.width * sc; ctx.drawImage(spr, x + sgn * dx - w / 2, y + sgn * dy - w / 2, w, w); }
  if (glow > 0) {
    ctx.globalCompositeOperation = 'lighter';
    const g = ctx.createRadialGradient(x, y, 0, x, y, r * 4);
    g.addColorStop(0, rgba(glowColor, 0.75 * glow)); g.addColorStop(1, rgba(glowColor, 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r * 4, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

// expanding rings emitted at fixed intervals since `start`
export function drawRings(ctx, x, y, t, { start, every, color, strength = 1, speed = 230, life = 2.0, k = 1, until = 1e9 }) {
  if (t < start) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const n0 = Math.max(0, Math.floor((t - start - life) / every)), n1 = Math.floor((Math.min(t, until) - start) / every);
  for (let i = n0; i <= n1; i++) {
    const age = t - (start + i * every);
    if (age < 0 || age > life) continue;
    const rr = (12 + age * speed) * k, a = strength * Math.pow(1 - age / life, 1.6);
    for (const [lw, aa] of [[9, 0.12], [2.2, 0.85]]) { ctx.strokeStyle = rgba(color, a * aa); ctx.lineWidth = lw * Math.max(0.4, k); ctx.beginPath(); ctx.arc(x, y, rr, 0, Math.PI * 2); ctx.stroke(); }
  }
  ctx.restore();
}

// soft background particles for depth
export function makeBokeh(seed = 9, n = 70) { const r = rng(seed); return Array.from({ length: n }, () => ({ x: r(), y: r(), s: 6 + r() * 40, a: 0.03 + r() * 0.08, p: r() * 6.28, sp: 0.2 + r() * 0.6 })); }
export function drawMicroBg(ctx, W, H, t, bokeh, alpha = 1) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha = alpha;
  const g = ctx.createRadialGradient(W * 0.5, H * 0.45, 50, W * 0.5, H * 0.5, W * 0.75);
  g.addColorStop(0, '#13285A'); g.addColorStop(0.55, '#0A1736'); g.addColorStop(1, '#040915');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  ctx.globalCompositeOperation = 'lighter';
  for (const b of bokeh) {
    const x = ((b.x * W + t * 12 * b.sp) % (W + 100)) - 50, y = b.y * H + Math.sin(t * 0.4 + b.p) * 14;
    const gg = ctx.createRadialGradient(x, y, 0, x, y, b.s); gg.addColorStop(0, `rgba(120,160,255,${b.a})`); gg.addColorStop(1, 'rgba(120,160,255,0)');
    ctx.fillStyle = gg; ctx.beginPath(); ctx.arc(x, y, b.s, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}
