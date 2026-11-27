// draw.js — Canvas 2D building blocks for pictures that look lit and layered. Pure functions of their inputs.
// See references/drawing.md for when to use each one.
import { clamp, lerp, rng, hex } from './kit.js';

const toRgb = (c) => (typeof c === 'string' && c.startsWith('#') ? hex(c) : c);

// offscreen canvas for a layer you composite later (glow, figures, cached backgrounds)
export function layer(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return c;
}

// ---- noise: smooth value noise in 0..1 and its fractal sum (clouds, fog, ridgelines, wobble)
export function noise(seed = 1) {
  const r = rng(seed), p = Float32Array.from({ length: 1024 }, r);
  const h = (x, y) => p[(((x * 374761393) ^ (y * 668265263)) >>> 0) & 1023];
  const n2 = (x, y) => {
    const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
    const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
    return lerp(lerp(h(xi, yi), h(xi + 1, yi), u), lerp(h(xi, yi + 1), h(xi + 1, yi + 1), u), v);
  };
  n2.fbm = (x, y, oct = 4) => {
    let s = 0, a = 0.5, f = 1, norm = 0;
    for (let i = 0; i < oct; i++) { s += a * n2(x * f + i * 17.3, y * f - i * 9.1); norm += a; a *= 0.5; f *= 2.03; }
    return s / norm;
  };
  return n2;
}

// ---- light: draw `src` additively with two blurred copies, the cheap bloom that makes light read as light
export function bloom(ctx, src, { base = 1, amount = 0.6, radii = [4, 18] } = {}) {
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = base; ctx.drawImage(src, 0, 0);
  radii.forEach((r, i) => { ctx.filter = `blur(${r}px)`; ctx.globalAlpha = amount * (i ? 0.8 : 1); ctx.drawImage(src, 0, 0); });
  ctx.restore();
}

// soft radial light; color = [r,g,b] or '#rrggbb'
export function glow(ctx, x, y, r, color, alpha = 1) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  const [R, G, B] = toRgb(color);
  g.addColorStop(0, `rgba(${R},${G},${B},${alpha})`);
  g.addColorStop(0.25, `rgba(${R},${G},${B},${alpha * 0.35})`);
  g.addColorStop(1, `rgba(${R},${G},${B},0)`);
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = g;
  ctx.fillRect(x - r, y - r, 2 * r, 2 * r); ctx.restore();
}

// soft volumetric shaft (window sunbeam, streetlamp cone, stage shaft) without expensive per-frame ctx.filter blur.
// Nested cones feather the lateral edges; pass `blend: 'source-over'` on bright/daylight scenes where 'lighter' washes out.
export function lightBeam(ctx, x0, y0, x1, y1, w0, w1, color, alpha = 0.24, { layers = 4, blend = 'lighter' } = {}) {
  const dx = x1 - x0, dy = y1 - y0, len = Math.hypot(dx, dy);
  if (len < 1e-3 || alpha <= 0) return;
  const nx = -dy / len, ny = dx / len;
  const [R, G, B] = toRgb(color);
  const n = Math.max(1, layers | 0);
  ctx.save();
  ctx.globalCompositeOperation = blend;
  for (let i = 0; i < n; i++) {
    const frac = 1 - (i / n) * 0.68;
    const hw0 = w0 * 0.5 * frac, hw1 = w1 * 0.5 * frac;
    const layerAlpha = (alpha / n) * (1 + i * 0.35);
    const g = ctx.createLinearGradient(x0, y0, x1, y1);
    g.addColorStop(0, `rgba(${R},${G},${B},${layerAlpha})`);
    g.addColorStop(0.55, `rgba(${R},${G},${B},${layerAlpha * 0.42})`);
    g.addColorStop(1, `rgba(${R},${G},${B},0)`);
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(x0 + nx * hw0, y0 + ny * hw0);
    ctx.lineTo(x1 + nx * hw1, y1 + ny * hw1);
    ctx.lineTo(x1 - nx * hw1, y1 - ny * hw1);
    ctx.lineTo(x0 - nx * hw0, y0 - ny * hw0);
    ctx.closePath();
    ctx.fill();
  }
  ctx.restore();
}

// power-law out-of-focus depth orbs with parallax and seamless wrap (uses cached gradient sprite: fast on Software GL).
const bokehSprites = new Map();
const bokehSets = new Map();
export function bokeh(ctx, seed, count, cam = { x: 0, y: 0, z: 1 }, t = 0, {
  w = ctx.canvas.width, h = ctx.canvas.height, color = [255, 224, 176], depth = 0.35,
  rMin = 10, rMax = 62, alpha = 0.14, drift = 12, blend = 'lighter',
} = {}) {
  if (count <= 0 || alpha <= 0) return;
  const [R, G, B] = toRgb(color);
  const sKey = `${R},${G},${B}`;
  if (!bokehSprites.has(sKey)) {
    const sp = layer(128, 128), sx = sp.getContext('2d'), gr = sx.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, `rgba(${R},${G},${B},0.75)`);
    gr.addColorStop(0.62, `rgba(${R},${G},${B},0.55)`);
    gr.addColorStop(0.86, `rgba(${R},${G},${B},0.22)`);
    gr.addColorStop(1, `rgba(${R},${G},${B},0)`);
    sx.fillStyle = gr; sx.fillRect(0, 0, 128, 128);
    bokehSprites.set(sKey, sp);
  }
  const pKey = `${seed}:${count}`;
  if (!bokehSets.has(pKey)) {
    const r = rng(seed);
    bokehSets.set(pKey, Array.from({ length: count }, () => ({
      u: r(), v: r(), sizePow: Math.pow(r(), 2.8), lum: 0.25 + 0.75 * Math.pow(r(), 1.8),
      ph: r() * Math.PI * 2, sp: 0.4 + r() * 0.8,
    })));
  }
  const sprite = bokehSprites.get(sKey), pts = bokehSets.get(pKey);
  const spanW = w + rMax * 2, spanH = h + rMax * 2;
  const mod = (a, m) => ((a % m) + m) % m;
  ctx.save();
  ctx.globalCompositeOperation = blend;
  for (const p of pts) {
    const rad = rMin + p.sizePow * (rMax - rMin);
    const px = mod(p.u * spanW - (cam.x || 0) * depth + Math.sin(t * p.sp * 0.5 + p.ph) * drift, spanW) - rMax;
    const py = mod(p.v * spanH - (cam.y || 0) * depth - t * drift * p.sp * 0.35, spanH) - rMax;
    const tw = 0.75 + 0.25 * Math.sin(t * p.sp + p.ph);
    ctx.globalAlpha = clamp(alpha * p.lum * tw);
    ctx.drawImage(sprite, px - rad, py - rad, rad * 2, rad * 2);
  }
  ctx.restore();
}

// pure-function organic camera breath `{ dx, dy, rot }` and `withHandheld(cam, t, opts)` helper so held shots stay alive.
export function handheld(t, { amp = 6, rot = 0.0028, speed = 1, seed = 1 } = {}) {
  const s = t * speed, p = seed * 1.732;
  const dx = amp * (0.58 * Math.sin(s * 0.83 + p) + 0.29 * Math.sin(s * 1.97 + p * 2.1) + 0.13 * Math.cos(s * 3.41 + p * 0.7));
  const dy = amp * (0.54 * Math.cos(s * 0.71 + p * 1.3) + 0.31 * Math.sin(s * 1.63 + p * 2.9) + 0.15 * Math.sin(s * 3.11 + p));
  const drot = rot * (0.65 * Math.sin(s * 0.61 + p * 0.9) + 0.35 * Math.cos(s * 1.49 + p * 2.4));
  return { dx, dy, rot: drot };
}

export function withHandheld(cam = {}, t = 0, opts = {}) {
  const h = handheld(t, opts);
  return { ...cam, z: cam.z ?? 1, x: (cam.x ?? 0) + h.dx, y: (cam.y ?? 0) + h.dy, rot: (cam.rot ?? 0) + h.rot };
}

// ---- depth: a ridgeline (mountains, dunes, rooftops with `steps`) as y values across the width
// Make layers wider than the frame (e.g. W + 400, drawn with dx -200) so camera moves never show their ends.
export function ridge(seed, width, { base, amp = 120, scale = 0.004, steps = 0, oct = 4 } = {}) {
  if (!Number.isFinite(base)) throw new Error('ridge(): give { base } — the y of the ridge foot in pixels');
  const n = noise(seed), ys = new Float32Array(Math.ceil(width / 4) + 2);
  for (let i = 0; i < ys.length; i++) {
    let x = i * 4;
    if (steps) x = Math.floor(x / steps) * steps;           // flat tops: roofs, blocks, a city
    ys[i] = base - amp * n.fbm(x * scale, seed * 0.13, oct);
  }
  return ys;
}
// fill a ridge from its line down to `bottom`; shift by `dx` (parallax) — layers further back get lighter
export function fillRidge(ctx, ys, fill, { dx = 0, bottom } = {}) {
  ctx.beginPath();
  ctx.moveTo(-4 + dx, bottom ?? ctx.canvas.height);
  for (let i = 0; i < ys.length; i++) ctx.lineTo(i * 4 + dx, ys[i]);
  ctx.lineTo((ys.length - 1) * 4 + dx, bottom ?? ctx.canvas.height);
  ctx.closePath(); ctx.fillStyle = fill; ctx.fill();
}

// ---- camera: apply a 2D camera to everything drawn in `fn`. depth 1 = the subject plane; 0 = infinitely far
// cam = { x, y, z, rot } in world units centred on the frame; parallax comes from drawing layers at different depths
export function view(ctx, cam, depth, fn) {
  const { width: W, height: H } = ctx.canvas;
  const z = 1 + (cam.z - 1) * depth;
  ctx.save();
  ctx.translate(W / 2, H / 2);
  if (cam.rot) ctx.rotate(cam.rot * depth);
  ctx.scale(z, z);
  ctx.translate(-cam.x * depth, -cam.y * depth);
  ctx.translate(-W / 2, -H / 2);
  fn(ctx);
  ctx.restore();
}

// ---- drawing a line on: show the first k (0..1) of a polyline by length
export function strokeTo(ctx, pts, k) {
  if (k <= 0 || pts.length < 2) return null;
  let total = 0;
  const seg = [];
  for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(d); total += d; }
  let left = clamp(k) * total;
  ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
  let tip = pts[0];
  for (let i = 1; i < pts.length; i++) {
    if (left >= seg[i - 1]) { ctx.lineTo(pts[i][0], pts[i][1]); left -= seg[i - 1]; tip = pts[i]; continue; }
    const f = left / seg[i - 1];
    tip = [lerp(pts[i - 1][0], pts[i][0], f), lerp(pts[i - 1][1], pts[i][1], f)];
    ctx.lineTo(tip[0], tip[1]);
    break;
  }
  ctx.stroke();
  return tip; // where the pen is: put a spark here
}

// ---- finishing: vignette, then moving film grain. Do this last, on the whole frame.
const grainCache = new Map();
export function finish(ctx, frame, { vignette = 0.5, grain = 0.07 } = {}) {
  const { width: W, height: H } = ctx.canvas;
  if (vignette) {
    const v = ctx.createRadialGradient(W / 2, H / 2, H * 0.42, W / 2, H / 2, H * 1.05);
    v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, `rgba(0,0,0,${vignette})`);
    ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
  }
  if (grain) {
    if (!grainCache.has(1)) {
      const g = layer(256, 256), x = g.getContext('2d'), im = x.createImageData(256, 256), r = rng(5);
      for (let i = 0; i < im.data.length; i += 4) { const v = 128 + (r() - 0.5) * 90; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; }
      x.putImageData(im, 0, 0);
      grainCache.set(1, g);
    }
    ctx.save(); ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = grain;
    ctx.translate(-((frame * 97) % 256), -((frame * 61) % 256));
    ctx.fillStyle = ctx.createPattern(grainCache.get(1), 'repeat'); ctx.fillRect(0, 0, W + 256, H + 256);
    ctx.restore();
  }
}

// colour helpers on [r,g,b] arrays
export const mix = (a, b, k) => a.map((v, i) => Math.round(lerp(v, b[i], k)));
export const css = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
