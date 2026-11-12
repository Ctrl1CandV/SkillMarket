// starter/scene.js — the smallest complete video page: timeline from narration (or voice-over), one core picture,
// captions that rise out of a mask, grain + vignette, sound events. Replace LINES and drawPicture with your own.
import { clamp, lerp, ease, seg, spring, rng, loadFonts, register, FONT_STACK } from '../../kit/kit.js';

const W = 1920, H = 1080, FPS = 30;
const cv = document.getElementById('cv'), ctx = cv.getContext('2d');

// ---- 1. narration: one entry per caption (and per voice clip vo/<id>.wav when there is voice-over) ----
const LINES = [
  { id: '01', kind: 'title', text: ['一杯水里，', '有多少个分子？'] },
  { id: '02', text: ['一杯水约 250 克'] },
  { id: '03', text: ['每 18 克水，含 6×10²³ 个分子'] },
  { id: '04', text: ['算下来，约 8×10²⁴ 个'] },
];
// measured clip lengths (node kit/vo.mjs vo vo/vo.js); without them, estimate ~4.5 Chinese characters per second
let VO = {}; try { VO = (await import('./vo/vo.js')).default; } catch { /* no voice-over yet */ }

// ---- 2. timeline: every time in the film hangs off these numbers ----
const TL = []; let t = 0.4;
for (const l of LINES) { const d = VO[l.id] ?? Math.max(1.8, l.text.join('').length / 4.5); TL.push({ ...l, t0: t, t1: t + d + 0.3 }); t += d + 0.7; }
const DUR = Math.ceil((t + 1.2) * 2) / 2;
const at = (id) => TL.find((x) => x.id === id);

// ---- 3. the core picture: here, a counter whose digits are computed, on a soft lit background ----
const GRAIN = (() => { const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'), im = g.createImageData(256, 256), r = rng(2); for (let i = 0; i < im.data.length; i += 4) { const v = 128 + (r() - 0.5) * 255; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; } g.putImageData(im, 0, 0); return c; })();
const MOLECULES = 250 / 18 * 6.022e23;   // ≈ 8.4e24, the number the last line states
function drawPicture(t) {
  const bg = ctx.createRadialGradient(W * 0.62, H * 0.45, 60, W * 0.6, H * 0.5, W * 0.8);
  bg.addColorStop(0, '#173A63'); bg.addColorStop(0.6, '#0B1B33'); bg.addColorStop(1, '#050B16');
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
  // a glass that fills, then the count
  const fill = seg(t, at('02').t0, 1.6, ease.inOut), cx = 1320, top = 300, h = 520;
  ctx.save(); ctx.lineWidth = 6; ctx.strokeStyle = 'rgba(220,235,255,0.75)'; ctx.beginPath(); ctx.moveTo(cx - 170, top); ctx.lineTo(cx - 130, top + h); ctx.lineTo(cx + 130, top + h); ctx.lineTo(cx + 170, top); ctx.stroke();
  const wy = top + h - (h - 60) * fill; ctx.fillStyle = 'rgba(90,170,255,0.55)'; ctx.beginPath(); ctx.moveTo(cx - 130 - 40 * (top + h - wy) / h, wy); ctx.lineTo(cx - 130, top + h); ctx.lineTo(cx + 130, top + h); ctx.lineTo(cx + 130 + 40 * (top + h - wy) / h, wy); ctx.fill(); ctx.restore();
  const k = seg(t, at('04').t0, 1.4, ease.out);
  if (k > 0) { const e = Math.log10(MOLECULES) * k, m = Math.pow(10, e - Math.floor(e)); ctx.save(); ctx.globalAlpha = Math.min(1, k * 3); ctx.fillStyle = '#FFFFFF'; ctx.font = `700 120px Ubuntu, ${FONT_STACK.sans}`; ctx.textAlign = 'left'; const base = `${m.toFixed(1)}×10`, bw = ctx.measureText(base).width, x0 = cx - bw / 2 - 30; ctx.fillText(base, x0, top - 70); ctx.font = `700 64px Ubuntu, ${FONT_STACK.sans}`; ctx.fillText(String(Math.floor(e)), x0 + bw + 8, top - 128); ctx.restore(); }
}
function finish(t) {
  const vg = ctx.createRadialGradient(W / 2, H / 2, H * 0.45, W / 2, H / 2, H * 1.05); vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,0.4)');
  ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);
  const r = rng(Math.floor(t * FPS) + 1); ctx.save(); ctx.globalAlpha = 0.06; ctx.globalCompositeOperation = 'overlay'; ctx.fillStyle = ctx.createPattern(GRAIN, 'repeat'); ctx.translate(-r() * 256, -r() * 256); ctx.fillRect(0, 0, W + 256, H + 256); ctx.restore();
}

// ---- 4. captions: the next one enters only after the previous one has left ----
const capEls = TL.map((l) => { const d = document.createElement('div'); d.className = 'cap ' + (l.kind || ''); d.innerHTML = l.text.map((s) => `<div class="ln"><span>${s}</span></div>`).join(''); document.getElementById('caps').appendChild(d); return d; });
function drawCaps(t) {
  TL.forEach((l, i) => {
    const el = capEls[i], vis = t >= (i === 0 ? -1 : l.t0) && t < l.t1 + 0.35; el.style.display = vis ? 'block' : 'none'; if (!vis) return;
    const out = seg(t, l.t1, 0.3, ease.in);
    const enter = i === 0 ? l.t0 - 1.0 : l.t0;   // the first frame already shows the title
    [...el.children].forEach((ln, j) => { const a = seg(t, enter + j * 0.12, 0.55, ease.out); ln.firstElementChild.style.transform = `translateY(${((1 - a) * 105).toFixed(1)}%)`; ln.style.opacity = (1 - out).toFixed(3); });
  });
}

// a slow push-in toward the glass: while a caption is being read the picture still breathes, never a frozen frame
function seek(t) { const z = 1 + 0.004 * t; ctx.setTransform(z, 0, 0, z, (1 - z) * 1320, (1 - z) * 560); drawPicture(t); ctx.setTransform(1, 0, 0, 1, 0, 0); finish(t); drawCaps(t); }

// ---- 5. sound events come from the same timeline ----
const events = [...TL.map((l) => ({ t: l.t0, type: 'line', id: l.id, end: l.t1 })), { t: at('04').t0, type: 'count' }];

await loadFonts([['Noto Sans SC', 'fonts/NotoSansSC-Bold.otf', { weight: '700' }], ['Ubuntu', 'fonts/Ubuntu-B.ttf', { weight: '700' }]]);
register({ duration: DUR, fps: FPS, width: W, height: H, seek, meta: { events } });
seek(0);
