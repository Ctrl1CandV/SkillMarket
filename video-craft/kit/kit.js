// kit.js — deterministic, seekable animation helpers. Every value is a pure function of time.
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const inv = (a, b, x) => clamp((x - a) / (b - a));

// cubic-bezier easing, same approach as WebKit UnitBezier (Newton + bisection)
export function bezier(x1, y1, x2, y2) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const sx = (t) => ((ax * t + bx) * t + cx) * t;
  const sy = (t) => ((ay * t + by) * t + cy) * t;
  const dx = (t) => (3 * ax * t + 2 * bx) * t + cx;
  const solve = (x) => {
    let t = x;
    for (let i = 0; i < 8; i++) {
      const e = sx(t) - x;
      if (Math.abs(e) < 1e-6) return t;
      const d = dx(t);
      if (Math.abs(d) < 1e-6) break;
      t -= e / d;
    }
    let lo = 0, hi = 1; t = x;
    while (lo < hi) {
      const v = sx(t);
      if (Math.abs(v - x) < 1e-6) return t;
      if (x > v) lo = t; else hi = t;
      t = (lo + hi) / 2;
      if (hi - lo < 1e-7) break;
    }
    return t;
  };
  return (x) => (x <= 0 ? 0 : x >= 1 ? 1 : sy(solve(x)));
}

export const ease = {
  linear: (t) => t,
  out: bezier(0.16, 1, 0.3, 1),      // expo-like out: entrances, landings
  outSoft: bezier(0.22, 1, 0.36, 1), // quint out
  in: bezier(0.7, 0, 0.84, 0),       // exits
  inOut: bezier(0.65, 0, 0.35, 1),   // camera moves, travel
  inOutSoft: bezier(0.45, 0, 0.55, 1),
  back: bezier(0.34, 1.56, 0.64, 1), // small overshoot
};

// progress of a segment that starts at t0 and lasts dur seconds
export const seg = (t, t0, dur, e = ease.out) => e(clamp((t - t0) / dur));

// keyframe track: keys = [[t, value, easeIntoThisKey?], …]; log = interpolate in log space (zoom, altitude)
export function kf(t, keys, log = false) {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [t1, v1, e] = keys[i], [t0, v0] = keys[i - 1];
    if (t <= t1) { const p = (e || ease.inOut)(clamp((t - t0) / Math.max(1e-6, t1 - t0))); return log ? Math.exp(lerp(Math.log(v0), Math.log(v1), p)) : lerp(v0, v1, p); }
  }
  return keys[keys.length - 1][1];
}

// damped spring step response (0 → 1), s = seconds since start
export function spring(s, { stiffness = 170, damping = 26, mass = 1 } = {}) {
  if (s <= 0) return 0;
  const w0 = Math.sqrt(stiffness / mass);
  const z = damping / (2 * Math.sqrt(stiffness * mass));
  if (z < 1) {
    const wd = w0 * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w0 * s) * (Math.cos(wd * s) + (z * w0 / wd) * Math.sin(wd * s));
  }
  if (z === 1) return 1 - Math.exp(-w0 * s) * (1 + w0 * s);
  const r1 = -w0 * (z - Math.sqrt(z * z - 1)), r2 = -w0 * (z + Math.sqrt(z * z - 1));
  return 1 + (r2 * Math.exp(r1 * s) - r1 * Math.exp(r2 * s)) / (r1 - r2);
}

// seeded RNG (mulberry32)
export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// colors
export function hex(h) {
  const n = parseInt(h.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
export function mixHex(a, b, t) {
  const A = hex(a), B = hex(b);
  return `rgb(${A.map((v, i) => Math.round(lerp(v, B[i], t))).join(',')})`;
}
export const rgba = (h, a) => { const [r, g, b] = hex(h); return `rgba(${r},${g},${b},${a})`; };

// load fonts before the first frame
// a missing file only warns: CSS font stacks should list system fallbacks (see FONT_STACK)
export async function loadFonts(list) {
  await Promise.all(list.map(async ([family, url, desc]) => {
    try { const f = new FontFace(family, `url(${url})`, desc || {}); await f.load(); document.fonts.add(f); }
    catch { console.warn(`font not loaded: ${family} from ${url} — using fallbacks`); }
  }));
  await document.fonts.ready;
}
export const FONT_STACK = {
  sans: '"Noto Sans SC", "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
  serif: '"Noto Serif SC", "Source Han Serif SC", "Songti SC", "SimSun", serif',
};

// register the seek entry point used by the renderer
export function register({ duration, fps = 30, width, height, seek, meta = {} }) {
  window.__video = { duration, fps, width, height, meta };
  window.__seek = (t) => { seek(t); return true; };
}
