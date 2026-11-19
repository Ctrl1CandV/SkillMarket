// draw.js — Canvas 2D building blocks for pictures that look lit and layered. Pure functions of their inputs.
// See references/drawing.md for when to use each one.
import { clamp, lerp, rng } from './kit.js';

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

// soft radial light; color = [r,g,b]
export function glow(ctx, x, y, r, color, alpha = 1) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  const [R, G, B] = color;
  g.addColorStop(0, `rgba(${R},${G},${B},${alpha})`);
  g.addColorStop(0.25, `rgba(${R},${G},${B},${alpha * 0.35})`);
  g.addColorStop(1, `rgba(${R},${G},${B},0)`);
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = g;
  ctx.fillRect(x - r, y - r, 2 * r, 2 * r); ctx.restore();
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
