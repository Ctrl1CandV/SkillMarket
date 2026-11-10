// space.js — Earth cross-section: sunlight from the left, a short path at noon and a long grazing path at sunset.
import { rng, clamp, lerp, ease, seg } from '../../kit/kit.js';
import { rgba } from './micro.js';

export const E = { cx: 1150, cy: 640, R: 430, A: 46 };
const NOON_Y = E.cy, SUNSET_Y = E.cy - E.R;
const SUNSET_IN = E.cx - Math.sqrt((E.R + E.A) ** 2 - E.R ** 2);   // where the grazing ray enters the air
const STARS = (() => { const r = rng(404); return Array.from({ length: 260 }, () => ({ x: r() * 1920, y: r() * 1080, s: r() < 0.9 ? 1 + r() * 1.2 : 2 + r() * 1.5, a: 0.25 + r() * 0.6, p: r() * 6.28 })); })();
const SPARKS = (() => { const r = rng(808); return Array.from({ length: 90 }, (_, i) => ({ f: r(), ang: (r() < 0.5 ? -1 : 1) * (0.5 + r() * 2.2), sp: 40 + r() * 70, born: i * 0.045 + r() * 0.03 })); })();

// colour of the sunset beam after travelling a fraction f of its path through the air
function beamColor(f) {
  const stops = [[0, [255, 252, 240]], [0.3, [255, 226, 140]], [0.6, [255, 160, 70]], [1, [255, 82, 50]]];
  for (let i = 1; i < stops.length; i++) if (f <= stops[i][0]) { const [a, ca] = stops[i - 1], [b, cb] = stops[i], k = (f - a) / (b - a); return ca.map((v, j) => Math.round(lerp(v, cb[j], k))); }
  return stops[stops.length - 1][1];
}

function glowLine(ctx, x0, y0, x1, y1, c, alpha, wMul = 1) {
  for (const [lw, a] of [[30, 0.07], [14, 0.18], [6, 0.45], [2.4, 1]]) { ctx.strokeStyle = `rgba(${c[0]},${c[1]},${c[2]},${a * alpha})`; ctx.lineWidth = lw * wMul; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke(); }
}

export function drawSpace(ctx, W, H, t, { alpha = 1, t0 = 44.0 }) {
  if (alpha <= 0) return;
  const lt = t - t0;
  ctx.save(); ctx.globalAlpha = alpha;
  ctx.fillStyle = '#03050B'; ctx.fillRect(0, 0, W, H);
  for (const s of STARS) { ctx.fillStyle = `rgba(220,230,255,${s.a * (0.75 + 0.25 * Math.sin(t * 2 + s.p))})`; ctx.fillRect(s.x, s.y, s.s, s.s); }
  // the sun, off to the left
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const sg = ctx.createRadialGradient(-260, 430, 20, -260, 430, 900); sg.addColorStop(0, 'rgba(255,248,230,0.85)'); sg.addColorStop(0.2, 'rgba(255,230,190,0.35)'); sg.addColorStop(1, 'rgba(255,220,180,0)');
  ctx.fillStyle = sg; ctx.fillRect(0, 0, W, H); ctx.restore();
  // atmosphere: blue on the day side, orange where day meets night
  ctx.save();
  const ag = ctx.createRadialGradient(E.cx, E.cy, E.R, E.cx, E.cy, E.R + E.A);
  ag.addColorStop(0, 'rgba(120,180,255,0.75)'); ag.addColorStop(0.55, 'rgba(90,150,255,0.35)'); ag.addColorStop(1, 'rgba(80,140,255,0)');
  ctx.fillStyle = ag; ctx.beginPath(); ctx.arc(E.cx, E.cy, E.R + E.A, 0, Math.PI * 2); ctx.fill();
  ctx.globalCompositeOperation = 'lighter';
  for (const sgn of [-1, 1]) {
    const og = ctx.createRadialGradient(E.cx, E.cy + sgn * E.R, 0, E.cx, E.cy + sgn * E.R, 230);
    og.addColorStop(0, 'rgba(255,140,70,0.55)'); og.addColorStop(1, 'rgba(255,120,60,0)');
    ctx.fillStyle = og; ctx.beginPath(); ctx.arc(E.cx, E.cy, E.R + E.A, 0, Math.PI * 2); ctx.arc(E.cx, E.cy, E.R, 0, Math.PI * 2, true); ctx.fill();
  }
  ctx.restore();
  // night side of the air fades out
  ctx.save(); ctx.beginPath(); ctx.arc(E.cx, E.cy, E.R + E.A + 2, 0, Math.PI * 2); ctx.clip();
  const ng = ctx.createLinearGradient(E.cx + 40, 0, E.cx + 300, 0); ng.addColorStop(0, 'rgba(3,5,11,0)'); ng.addColorStop(1, 'rgba(3,5,11,0.92)');
  ctx.fillStyle = ng; ctx.fillRect(E.cx, 0, W, H); ctx.restore();
  // the planet
  const eg = ctx.createLinearGradient(E.cx - E.R, 0, E.cx + E.R, 0);
  eg.addColorStop(0, '#3E78D0'); eg.addColorStop(0.4, '#24508F'); eg.addColorStop(0.53, '#0C1C3C'); eg.addColorStop(1, '#050A17');
  ctx.fillStyle = eg; ctx.beginPath(); ctx.arc(E.cx, E.cy, E.R, 0, Math.PI * 2); ctx.fill();
  ctx.save(); ctx.beginPath(); ctx.arc(E.cx, E.cy, E.R, 0, Math.PI * 2); ctx.clip();
  const sh = ctx.createLinearGradient(E.cx - 60, 0, E.cx + 120, 0); sh.addColorStop(0, 'rgba(3,6,14,0)'); sh.addColorStop(1, 'rgba(3,6,14,0.85)');
  ctx.fillStyle = sh; ctx.fillRect(E.cx - 60, 0, W, H); ctx.restore();

  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
  // noon beam: straight in, short path through the air
  const nf = seg(t, t0 + 0.4, 0.7, ease.inOut);
  if (nf > 0) {
    const xEnd = lerp(0, E.cx - E.R, nf), xIn = E.cx - E.R - E.A;
    glowLine(ctx, 0, NOON_Y, Math.min(xEnd, xIn), NOON_Y, [255, 252, 240], 1);
    if (xEnd > xIn) glowLine(ctx, xIn, NOON_Y, xEnd, NOON_Y, [255, 240, 205], 1);
  }
  // sunset beam: grazes the planet, long path through the air, turns red
  const sf = seg(t, t0 + 1.1, 1.3, ease.inOut);
  if (sf > 0) {
    const xEnd = lerp(0, E.cx, sf);
    glowLine(ctx, 0, SUNSET_Y, Math.min(xEnd, SUNSET_IN), SUNSET_Y, [255, 252, 240], 1);
    for (let x = SUNSET_IN; x < xEnd; x += 6) { const f = (x - SUNSET_IN) / (E.cx - SUNSET_IN); glowLine(ctx, x, SUNSET_Y, Math.min(x + 7, xEnd), SUNSET_Y, beamColor(f), 1); }
    // blue light scattered off the beam along the way
    for (const s of SPARKS) {
      const x = SUNSET_IN + s.f * (E.cx - SUNSET_IN), born = t0 + 1.1 + 1.3 * ((x) / E.cx) + s.born % 2.4;
      for (let rep = 0; rep < 3; rep++) {
        const age = t - (born + rep * 2.4); if (age < 0 || age > 1.6 || xEnd < x) continue;
        const px = x + Math.cos(s.ang) * s.sp * age * 0.4, py = SUNSET_Y + Math.sin(s.ang) * s.sp * age, a = (1 - age / 1.6) * (1 - s.f * 0.5);
        const g = ctx.createRadialGradient(px, py, 0, px, py, 9); g.addColorStop(0, `rgba(110,160,255,${0.9 * a})`); g.addColorStop(1, 'rgba(110,160,255,0)');
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(px, py, 9, 0, Math.PI * 2); ctx.fill();
      }
    }
  }
  ctx.restore();
  // observers and measured paths
  const lab = seg(t, t0 + 2.6, 0.5);
  if (lab > 0) {
    ctx.save(); ctx.globalAlpha = alpha * lab;
    marker(ctx, E.cx - E.R, NOON_Y, '#FFF1D6'); marker(ctx, E.cx, SUNSET_Y, '#FF8A5C');
    bracket(ctx, E.cx - E.R - E.A, E.cx - E.R, NOON_Y + 40, '#FFE6B8');
    bracket(ctx, SUNSET_IN, E.cx, SUNSET_Y - 40, '#FF9A6A');
    label(ctx, '正午', E.cx - E.R - 120, NOON_Y + 92, 34, '#FFF1D6');
    label(ctx, '穿过的空气 1 份', E.cx - E.R - 120, NOON_Y + 138, 28, 'rgba(255,241,214,0.75)');
    label(ctx, '日落', SUNSET_IN - 10, SUNSET_Y - 112, 34, '#FFB38F');
    label(ctx, '约 38 份', SUNSET_IN + 70, SUNSET_Y - 112, 34, '#FFB38F', 'left');
    ctx.restore();
  }
  const note = seg(t, t0 + 3.4, 0.6);
  if (note > 0) { ctx.save(); ctx.globalAlpha = alpha * note * 0.7; label(ctx, '示意图：大气层已放大，未按比例', W - 120, H - 70, 24, '#C8D0E0', 'right'); ctx.restore(); }
  ctx.restore();
}

function marker(ctx, x, y, c) { ctx.fillStyle = c; ctx.beginPath(); ctx.arc(x, y, 8, 0, Math.PI * 2); ctx.fill(); ctx.strokeStyle = 'rgba(255,255,255,0.6)'; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(x, y, 15, 0, Math.PI * 2); ctx.stroke(); }
function bracket(ctx, x0, x1, y, c) {
  ctx.strokeStyle = c; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(x0, y - 10); ctx.lineTo(x0, y); ctx.lineTo(x1, y); ctx.lineTo(x1, y - 10); ctx.stroke();
}
function label(ctx, s, x, y, px, c, align = 'center') { ctx.font = `700 ${px}px "Noto Sans SC", "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif`; ctx.fillStyle = c; ctx.textAlign = align; ctx.fillText(s, x, y); }
