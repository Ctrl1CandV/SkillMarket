import { clamp, lerp, inv, ease, seg, rng, loadFonts, register } from '../../kit/kit.js';
import { createSky, project } from './atmo.js';
import { drawLand, eyeOf } from './land.js';
import { WAVES, UF, mapT, drawWave, drawBeam, initSprites, makeMolecules, drawMolecule, moleculePos, drawRings, makeBokeh, drawMicroBg, rgba } from './micro.js';
import { drawSpace } from './space.js';

const W = 1920, H = 1080, FPS = 30, DUR = 59, D = Math.PI / 180;
const cv = document.getElementById('cv'), ctx = cv.getContext('2d');
const sky = createSky(640, 360);

// ---------- keyframe tracks ----------
function kf(t, keys, log = false) {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [t1, v1, e] = keys[i], [t0, v0] = keys[i - 1];
    if (t <= t1) { const p = (e || ease.inOut)(clamp((t - t0) / Math.max(1e-6, t1 - t0))); return log ? Math.exp(lerp(Math.log(v0), Math.log(v1), p)) : lerp(v0, v1, p); }
  }
  return keys[keys.length - 1][1];
}
const PITCH = [[0, 5], [5.4, 27], [9.0, 38], [29.99, 38], [30.0, 14], [36.2, 14], [40.4, 4], [43.3, -9, ease.in], [49.6, -12], [52.6, 4, ease.inOut], [59, 4.6]];
const FOV = [[0, 50], [29.99, 50], [30.0, 38], [31.4, 50, ease.out], [55, 50], [59, 44.5, ease.inOut]];
const ALT = [[0, 300], [40.6, 300], [43.4, 120000, ease.in], [49.6, 80000], [52.4, 300, ease.inOut], [59, 300]];
const SUN_EL = [[0, 52], [36.2, 52], [40.4, 2.2], [49.6, 2.2], [49.61, 1.4], [55, 1.1], [59, 0.6]];
const SUN_AZ = [[0, -24], [36.2, -24], [40.4, -7], [59, -7]];
function camAt(t) {
  const cam = { pitch: kf(t, PITCH) * D, fov: kf(t, FOV) * D, alt: kf(t, ALT, true) };
  const sun = { el: kf(t, SUN_EL) * D, az: kf(t, SUN_AZ) * D };
  return { cam, sun };
}

// ---------- shared state ----------
const MOLS = makeMolecules();
const BOKEH = makeBokeh();
const SPARK = (() => { const r = rng(31); return Array.from({ length: 240 }, () => ({ x: r() * W, y: r(), s: 2 + r() * 4, a: r() * 6.28, sp: 10 + r() * 30, tw: r() * 6.28 })); })();
const RAYS = (() => { const r = rng(64); return Array.from({ length: 14 }, (_, i) => ({ x: 80 + (i / 13) * 1500 + (r() - 0.5) * 80, y: 60 + r() * 420, d: i * 0.07 + r() * 0.05 })); })();
const GRAIN = (() => { const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'), im = g.createImageData(256, 256), r = rng(2); for (let i = 0; i < im.data.length; i += 4) { const v = 128 + (r() - 0.5) * 255; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; } g.putImageData(im, 0, 0); return c; })();
let lastHorizon = [150, 180, 210];

// ---------- sky scene (landscape, sun) ----------
function drawSkyScene(t, alpha, extra) {
  if (alpha <= 0) return;
  const { cam, sun } = camAt(t);
  const el = sun.el;
  const exposure = lerp(2.9, 1.75, clamp(el / (18 * D)));
  sky.render(cam, sun, exposure, 1.12);
  ctx.save(); ctx.globalAlpha = alpha;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(sky.canvas, 0, 0, W, H);
  // horizon colour drives the haze of the mountains
  const hz = project(cam, 3 * D, 0, W, H);
  if (hz && hz[1] > 8 && hz[1] < H - 8) lastHorizon = sky.sample(0.85, clamp(hz[1] / H, 0.01, 0.99));
  // the sun
  const sp = project(cam, el, sun.az, W, H);
  const low = 1 - clamp((el - 2 * D) / (14 * D));
  if (sp && sp[0] > -600 && sp[0] < W + 600 && sp[1] > -600 && sp[1] < H + 600) {
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    const [x, y] = sp;
    const c1 = low > 0.5 ? '255,170,90' : '255,245,225';
    for (const [r, a] of [[lerp(380, 640, low), lerp(0.07, 0.34, low)], [lerp(140, 220, low), lerp(0.22, 0.5, low)], [56, 0.6]]) { const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, `rgba(${c1},${a})`); g.addColorStop(1, `rgba(${c1},0)`); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill(); }
    ctx.fillStyle = low > 0.5 ? '#FFD39A' : '#FFFDF4'; ctx.beginPath(); ctx.arc(x, y, lerp(20, 28, low), 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }
  const shadow = [lerp(24, 26, low), lerp(34, 13, low), lerp(46, 24, low)].map(Math.round);
  const altK = clamp(Math.log(cam.alt / 300) / Math.log(30));
  drawLand(ctx, cam, W, H, { horizon: lastHorizon, shadow, backlit: low, drop: altK * 1150, alpha: 1 - altK * 0.6, rim: low, sunX: sp ? sp[0] : 0 });
  if (extra) extra(cam, sun, sp);
  ctx.restore();
}

// ---------- beam / micro transforms ----------
function beamT_B(t) {
  const { cam, sun } = camAt(t);
  const sp = project(cam, sun.el, sun.az, W, H) || [600, -200];
  return { ox: sp[0], oy: sp[1], k: 0.25, th: 20 * D };
}
const T_MICRO = { ox: W / 2 - UF, oy: H / 2, k: 1, th: 0 };
function beamT(t) {
  if (t < 11.0) return beamT_B(t);
  if (t >= 12.8) return T_MICRO;
  const p = ease.inOut(clamp((t - 11.0) / 1.8)), B = beamT_B(11.0);
  const k = Math.exp(lerp(Math.log(B.k), 0, p)), th = lerp(B.th, 0, p);
  const f0 = mapT(B, UF, 0), fx = lerp(f0[0], W / 2, p), fy = lerp(f0[1], H / 2, p);
  return { k, th, ox: fx - k * UF * Math.cos(th), oy: fy - k * UF * Math.sin(th) };
}

function drawWaves(t, T, alpha) {
  // white beam grows out of the sun, then splits into colours
  const front = 5600 * seg(t, 6.4, 1.4, ease.inOut);
  const split = seg(t, 8.0, 1.8, ease.inOut);
  drawBeam(ctx, T, 0, front, alpha * (1 - seg(t, 8.0, 0.3, ease.linear)));
  if (t >= 8.0) {
    WAVES.forEach((w, i) => {
      let a = alpha, vOff = w.v * split - w.v, amp = 48 * split;
      // scattering scene keeps only red and blue
      const keep = w.nm === 700 || w.nm === 450;
      if (!keep) a *= 1 - seg(t, 15.4, 0.8, ease.inOut);
      if (w.nm === 700) vOff = lerp(w.v * split - w.v, -190 - w.v, seg(t, 15.5, 1.0, ease.inOut));
      if (w.nm === 450) vOff = lerp(w.v * split - w.v, 190 - w.v, seg(t, 15.5, 1.0, ease.inOut));
      const decay = w.nm === 450 ? lerp(0, 1, seg(t, 17.0, 2.0)) : 0;
      drawWave(ctx, T, w, t, { amp, u0: 0, u1: t < 12.8 ? front : 99999, alpha: a, vOff, decay: decay > 0 ? lerp(60000, 1700, decay) : 0 });
    });
  }
}

function drawMicroBack(t, alpha) {
  if (alpha <= 0) return;
  const T = beamT(t), molA = inv(0.32, 0.8, T.k);
  ctx.save(); ctx.globalAlpha = alpha;
  for (const m of MOLS) if (m.z > 1.0) drawMolecule(ctx, T, m, t, molA * (m.emit ? seg(t, 15.0, 0.8) : 1));
  ctx.restore();
}
function drawMicro(t, alpha) {
  if (alpha <= 0) return;
  const T = beamT(t);
  const molA = inv(0.32, 0.8, T.k);
  ctx.save(); ctx.globalAlpha = alpha;
  const scatterOn = t > 16.0;
  for (const m of MOLS) {
    if (!m.emit || !scatterOn) continue;
    const { u, v } = moleculePos(m, t), [x, y] = mapT(T, u, v);
    const start = 16.3 + (x / W) * 1.1;
    const blue = m.emit === 'blue';
    drawRings(ctx, x, y, t, { start, every: 0.42, color: blue ? '#4F86FF' : '#FF4B3E', strength: blue ? 0.9 : 0.9 / 5.9, life: 2.4, speed: 250, until: 24.6 });
  }
  for (const m of MOLS) {
    if (m.z > 1.0) continue;
    let glow = 0;
    if (m.emit && scatterOn) { const { u, v } = moleculePos(m, t), [x] = mapT(T, u, v); const st = 16.3 + (x / W) * 1.1; if (t > st) glow = (m.emit === 'blue' ? 0.8 : 0.15) * (0.6 + 0.4 * Math.cos(((t - st) / 0.42) * Math.PI * 2)); }
    drawMolecule(ctx, T, m, t, molA * (m.emit ? seg(t, 15.0, 0.8) : 1), glow, m.emit === 'red' ? '#FF4B3E' : '#4F86FF');
  }
  const nl = seg(t, 13.6, 0.5) * (1 - seg(t, 15.3, 0.3, ease.in));
  if (nl > 0) {
    const a = MOLS.find((m) => !m.emit && m.type === 'N2' && Math.abs(m.z - 1) < 0.18 && Math.abs(m.u - UF) < 600 && Math.abs(m.v) < 380);
    const b = MOLS.find((m) => !m.emit && m.type === 'O2' && Math.abs(m.z - 1) < 0.25 && Math.abs(m.u - UF) < 800 && Math.abs(m.v) < 420);
    for (const [m, s] of [[a, 'N₂ 氮气'], [b, 'O₂ 氧气']]) if (m) { const { u, v } = moleculePos(m, t), [x, y] = mapT(T, u, v); label(s, x, y - 52, 30, `rgba(230,238,255,${nl})`); }
  }
  const wl = seg(t, 16.4, 0.5) * (1 - seg(t, 24.0, 0.3, ease.in));
  if (wl > 0) { label('红光 700 nm', 150, H / 2 - 190 - 80, 32, rgba('#FF9C8C', wl), 'left'); label('蓝光 450 nm', 150, H / 2 + 190 - 80, 32, rgba('#9CC2FF', wl), 'left'); }
  ctx.restore();
}

function label(s, x, y, px, color, align = 'center') { ctx.font = `700 ${px}px "Noto Sans SC", "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif`; ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = 'alphabetic'; ctx.fillText(s, x, y); }

// ---------- comparison panels ----------
function drawPanels(t, alpha, scale = 1, cx = W / 2, cy = H / 2) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha = alpha;
  ctx.translate(cx, cy); ctx.scale(scale, scale); ctx.translate(-W / 2, -H / 2);
  drawMicroBg(ctx, W, H, t, BOKEH, 1);
  const panels = [{ x: 140, color: '#4F86FF', nm: 450, name: '蓝光 · 450 nm', txt: '#9CC2FF', s: 1, v: '6×' }, { x: 990, color: '#FF4B3E', nm: 700, name: '红光 · 700 nm', txt: '#FFA48A', s: 1 / 5.9, v: '1×' }];
  for (const P of panels) {
    const pw = 790, ph = 540, py = 130;
    ctx.save(); ctx.beginPath(); roundRect(P.x, py, pw, ph, 30); ctx.fillStyle = 'rgba(255,255,255,0.035)'; ctx.fill(); ctx.strokeStyle = 'rgba(255,255,255,0.09)'; ctx.lineWidth = 2; ctx.stroke(); ctx.clip();
    const mx = P.x + pw * 0.52, my = py + ph * 0.5;
    const T = { ox: P.x - 200, oy: my, k: 1, th: 0 };
    drawWave(ctx, T, { nm: P.nm, color: P.color, v: 0 }, t, { amp: 46, u0: 0, u1: pw + 400, alpha: 1 });
    drawRings(ctx, mx, my, t, { start: 24.4, every: 0.38, color: P.color, strength: P.s, life: 2.2, speed: 230 });
    const m = { u: 0, v: 0, z: 1, type: 'N2', a0: 0.6, p: 1.2 };
    drawMolecule(ctx, { ox: mx, oy: my, k: 1.5, th: 0 }, m, t, 1, P.s * 0.8 * (0.6 + 0.4 * Math.cos(((t - 24.4) / 0.38) * Math.PI * 2)), P.color);
    ctx.restore();
    label(P.name, P.x + 36, py + 64, 38, P.txt, 'left');
    // strength meter
    const f = seg(t, 25.2, 1.2, ease.out), mw = 560;
    ctx.fillStyle = 'rgba(255,255,255,0.08)'; ctx.beginPath(); roundRect(P.x + 36, py + ph + 52, mw, 16, 8); ctx.fill();
    ctx.fillStyle = P.color; ctx.beginPath(); roundRect(P.x + 36, py + ph + 52, Math.max(16, mw * P.s * f), 16, 8); ctx.fill();
    label('被弹开的强度', P.x + 36, py + ph + 36, 28, 'rgba(220,228,245,0.75)', 'left');
    label(P.v, P.x + 36 + mw + 24, py + ph + 74, 54, rgba(P.txt, f), 'left');
  }
  label('(700 ÷ 450)⁴ ≈ 5.9', W - 140, 1010 - 30, 26, `rgba(200,210,230,${0.65 * seg(t, 26.4, 0.6)})`, 'right');
  ctx.restore();
}
function roundRect(x, y, w, h, r) { ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }

// ---------- scattered blue light in the sky ----------
function skyExtrasF(t) {
  return (cam) => {
    const a = seg(t, 30.6, 1.0) * (1 - seg(t, 36.0, 0.7, ease.in));
    if (a <= 0) return;
    const hzY = project(cam, 0, 0, W, H)?.[1] ?? H;
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (const s of SPARK) {
      const y = s.y * (hzY - 80) + 20, x = s.x + Math.cos(s.a + t * 0.3) * s.sp * 0.6, yy = y + Math.sin(s.a + t * 0.4) * s.sp * 0.4;
      const tw = 0.55 + 0.45 * Math.sin(t * 3 + s.tw);
      const g = ctx.createRadialGradient(x, yy, 0, x, yy, s.s * 3); g.addColorStop(0, `rgba(150,195,255,${0.75 * a * tw})`); g.addColorStop(1, 'rgba(120,170,255,0)');
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, yy, s.s * 3, 0, Math.PI * 2); ctx.fill();
    }
    const [ex, ey] = eyeOf(cam, W, H);
    for (const r of RAYS) {
      const p = seg(t, 31.4 + r.d, 0.7, ease.inOut) * (1 - seg(t, 36.0, 0.6, ease.in));
      if (p <= 0) continue;
      const x1 = lerp(r.x, ex, p), y1 = lerp(r.y, ey, p);
      ctx.save(); ctx.globalCompositeOperation = 'source-over';
      for (const [lw, c] of [[9, `rgba(30,90,255,${0.22 * a})`], [3.6, `rgba(40,105,255,${0.85 * a})`], [1.2, `rgba(210,230,255,${0.9 * a})`]]) { ctx.strokeStyle = c; ctx.lineWidth = lw; ctx.beginPath(); ctx.moveTo(r.x, r.y); ctx.lineTo(x1, y1); ctx.stroke(); }
      ctx.restore();
      // photons travelling along the ray
      for (let k = 0; k < 3; k++) {
        const q = ((t - 32.2 - r.d + k * 0.33) / 1.0) % 1; if (t < 32.2 + r.d || q < 0) continue;
        const px = lerp(r.x, ex, q), py = lerp(r.y, ey, q), g = ctx.createRadialGradient(px, py, 0, px, py, 10);
        g.addColorStop(0, `rgba(200,225,255,${0.9 * a})`); g.addColorStop(1, 'rgba(160,200,255,0)'); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(px, py, 10, 0, Math.PI * 2); ctx.fill();
      }
    }
    ctx.restore();
  };
}

// ---------- finishing ----------
function finish(t) {
  ctx.save();
  const vg = ctx.createRadialGradient(W / 2, H / 2, H * 0.45, W / 2, H / 2, H * 1.05);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,0.42)');
  ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);
  // legibility for the narration in the lower left
  const sc = ctx.createLinearGradient(0, H, 0, H - 380); sc.addColorStop(0, 'rgba(0,0,0,0.38)'); sc.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = sc; ctx.fillRect(0, H - 380, W, 380);
  const f = Math.floor(t * FPS), r = rng(f + 1);
  ctx.globalAlpha = 0.07; ctx.globalCompositeOperation = 'overlay';
  ctx.fillStyle = ctx.createPattern(GRAIN, 'repeat');
  ctx.translate(-r() * 256, -r() * 256); ctx.fillRect(0, 0, W + 256, H + 256);
  ctx.restore();
}

// ---------- captions ----------
const CAPS = [
  ['title', 0.5, 4.9, ['天空为什么是蓝的？']],
  ['narr', 6.3, 8.5, ['阳光看起来是白色的']],
  ['narr', 8.95, 11.0, ['其实，它混着所有颜色']],
  ['narr', 12.1, 15.4, ['空气里，飘满了', '氮气和氧气分子']],
  ['narr', 16.2, 19.7, ['光碰到这些分子', '会被弹向四面八方']],
  ['narr', 20.1, 23.9, ['波长越短，', '被弹开的就越多']],
  ['narr', 24.6, 30.0, ['<em class="b">蓝光</em>被弹开的强度', '约是<em class="r">红光</em>的 6 倍']],
  ['narr', 31.0, 33.6, ['满天被弹开的<em class="b">蓝光</em>', '从各个方向进入你的眼睛']],
  ['narr', 34.0, 36.0, ['所以抬头看，天是蓝的']],
  ['title right', 36.6, 40.3, ['那为什么，', '晚霞是红的？']],
  ['narr', 44.6, 47.4, ['日落时，阳光斜着穿过大气', '要走的路长了几十倍']],
  ['narr', 47.8, 50.0, ['一路上，<em class="b">蓝光</em>差不多被弹光了']],
  ['narr', 51.6, 54.9, ['剩下照进你眼里的', '只有<em class="r">橙光和红光</em>']],
  ['end', 55.2, 99, ['蓝天与晚霞', '是同一种散射', '瑞利散射 · Rayleigh scattering']],
];
const capRoot = document.getElementById('caps');
const capEls = CAPS.map(([kind, , , lines]) => {
  const d = document.createElement('div'); d.className = 'cap ' + kind;
  d.innerHTML = lines.map((l) => `<div class="ln"><span>${l}</span></div>`).join('');
  capRoot.appendChild(d); return d;
});
function drawCaps(t) {
  CAPS.forEach(([kind, t0, t1], i) => {
    const el = capEls[i], vis = t >= t0 - 0.01 && t < t1 + 0.4;
    el.style.display = vis ? 'block' : 'none'; if (!vis) return;
    const out = seg(t, t1, 0.35, ease.in);
    [...el.children].forEach((ln, j) => {
      const a = seg(t, t0 + j * (kind === 'end' ? 0.35 : 0.12), kind === 'narr' ? 0.55 : 0.9, ease.out);
      const sp = ln.firstElementChild;
      sp.style.transform = `translateY(${((1 - a) * 105).toFixed(1)}%)`;
      ln.style.opacity = (1 - out).toFixed(3);
      ln.style.filter = kind === 'narr' || a > 0.995 ? 'none' : `blur(${((1 - a) * 6).toFixed(2)}px)`;
    });
  });
}

// ---------- the frame ----------
function seek(t) {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = '#04070F'; ctx.fillRect(0, 0, W, H);
  // sky phases: A–B, F–H rise, I–J
  const skyA = t < 12.8 ? 1 - seg(t, 11.3, 1.3, ease.inOut) : 0;
  const skyF = t >= 30.0 && t < 44.4 ? seg(t, 30.0, 0.9, ease.inOut) * (1 - seg(t, 43.1, 0.9, ease.inOut)) : 0;
  const skyI = t >= 49.6 ? seg(t, 49.6, 0.9, ease.inOut) : 0;
  const microA = t >= 11.2 && t < 25.0 ? seg(t, 11.3, 1.3, ease.inOut) * (1 - seg(t, 24.0, 0.7, ease.inOut)) : 0;
  const panelA = t >= 24.0 && t < 31.2 ? seg(t, 24.0, 0.7, ease.inOut) * (1 - seg(t, 30.0, 1.0, ease.inOut)) : 0;
  const spaceA = t >= 43.0 && t < 50.6 ? seg(t, 43.0, 0.9, ease.inOut) * (1 - seg(t, 49.6, 0.9, ease.inOut)) : 0;

  if (microA > 0) { drawMicroBg(ctx, W, H, t, BOKEH, microA); drawMicroBack(t, microA); }
  if (skyA > 0) drawSkyScene(t, skyA);
  if (t > 6.0 && t < 24.8) { ctx.save(); ctx.globalAlpha = 1 - seg(t, 24.0, 0.7, ease.inOut); drawWaves(t, beamT(t), 1); ctx.restore(); drawMicroLabels(t); }
  if (microA > 0) drawMicro(t, microA);
  if (panelA > 0) { const out = seg(t, 30.0, 1.0, ease.inOut); drawPanels(t, panelA, lerp(1, 0.18, out), lerp(W / 2, 760, out), lerp(H / 2, 300, out)); }
  if (skyF > 0) drawSkyScene(t, skyF, skyExtrasF(t));
  if (spaceA > 0) {
    ctx.save();
    const pull = seg(t, 43.0, 1.9, ease.inOut), s0 = lerp(2.6, 1, pull);
    ctx.translate(1269, -196); ctx.scale(s0, s0); ctx.translate(-1269, 196);
    const push = lerp(1, 1.1, seg(t, 46.5, 3.5, ease.inOut)); ctx.translate(1000, 380); ctx.scale(push, push); ctx.translate(-1000, -380);
    drawSpace(ctx, W, H, t, { alpha: spaceA, t0: 44.0 }); ctx.restore();
  }
  if (skyI > 0) drawSkyScene(t, skyI);
  finish(t);
  drawCaps(t);
}
function drawMicroLabels(t) {
  const lab = seg(t, 9.3, 0.5) * (1 - seg(t, 10.9, 0.3, ease.in));
  if (lab <= 0) return;
  const T = beamT(t), pr = mapT(T, 4700, -300 - 90), pv = mapT(T, 4700, 300 + 110);
  label('波长长', pr[0], pr[1], 30, rgba('#FFB0A4', lab)); label('波长短', pv[0], pv[1], 30, rgba('#CDB8FF', lab));
}


// ---------- sound events (same timeline as the picture) ----------
function buildEvents() {
  const E = [];
  const add = (t, type, o = {}) => E.push({ t: +t.toFixed(3), type, ...o });
  add(0.5, 'title'); add(6.4, 'beam', { dur: 1.4 }); add(8.0, 'split', { dur: 1.8 }); add(11.0, 'zoomin', { dur: 1.8 });
  add(13.6, 'labels'); add(15.5, 'separate');
  // first ring of every emitter, panned by where it sits on screen
  for (const m of MOLS) {
    if (!m.emit) continue;
    const { u, v } = moleculePos(m, 16.3), [x] = mapT(T_MICRO, u, v);
    if (x < -40 || x > W + 40) continue;
    add(16.3 + (x / W) * 1.1, 'ring', { color: m.emit, pan: clamp((x / W) * 2 - 1, -0.8, 0.8) });
  }
  add(24.0, 'panels');
  for (let i = 0; 24.4 + i * 0.38 < 30.6; i++) add(24.4 + i * 0.38, 'pring', { i });
  add(25.2, 'meter', { dur: 1.2 });
  add(30.0, 'pullout', { dur: 1.0 }); add(30.6, 'sparks');
  for (const r of RAYS) add(31.4 + r.d + 0.7, 'ray', { pan: clamp((r.x / W) * 2 - 1, -0.8, 0.8) });
  add(34.0, 'resolve'); add(36.2, 'timelapse', { dur: 4.2 }); add(36.6, 'question');
  add(40.6, 'rise', { dur: 2.8 }); add(43.0, 'space', { dur: 1.9 });
  add(44.4, 'noonbeam', { dur: 0.7 }); add(45.1, 'sunsetbeam', { dur: 1.3 }); add(46.6, 'marks');
  add(49.6, 'dive', { dur: 3.0 }); add(52.4, 'land'); add(55.2, 'end');
  return E.sort((a, b) => a.t - b.t);
}

await loadFonts([
  ['Noto Sans SC', 'fonts/NotoSansSC-Bold.otf', { weight: '700' }],
  ['Noto Sans SC', 'fonts/NotoSansSC-Regular.otf', { weight: '400' }],
  ['Noto Serif SC', 'fonts/NotoSerifSC-Bold.otf', { weight: '700' }],
  ['Ubuntu', 'fonts/Ubuntu-M.ttf', { weight: '500' }],
]);
initSprites();
register({ duration: DUR, fps: FPS, width: W, height: H, seek, meta: { events: buildEvents() } });
seek(0);
