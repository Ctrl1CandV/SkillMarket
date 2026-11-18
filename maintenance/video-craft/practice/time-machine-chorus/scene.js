// time machine · chorus (song 1:52.2–2:26.6). Practice piece for video-craft 0.7, made by hand.
// Idea from the lyrics: he only meets her when he sleeps; stars are where he looks for her.
// People are drawn the way the sky already draws people: constellations. The sky's own clock, star
// trails around the pole, runs backwards for "going back in a time machine"; dawn erases them on "will end".
import { clamp, lerp, inv, ease, kf, rng, register, songAt, pulse } from '../../../../video-craft/kit/kit.js';
import song from './song.js';

const W = 1920, H = 1080, FPS = 30, TAU = Math.PI * 2;
const T0 = 112.227;              // song time of film 0 (a downbeat)
const DUR = 34.4;
const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
const layer = (w = W, h = H) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
const starL = layer(), starX = starL.getContext('2d');
const figL = layer(), figX = figL.getContext('2d');

// ------------------------------------------------------------------ palette (night, lamp, dawn)
const NIGHT = { top: [3, 5, 14], mid: [9, 17, 44], low: [24, 36, 78], glow: [58, 44, 70] };
const DAWN = { top: [34, 46, 98], mid: [122, 120, 170], low: [243, 168, 128], glow: [255, 206, 160] };
const mixc = (a, b, k) => a.map((v, i) => Math.round(lerp(v, b[i], k)));
const css = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
const HER = [255, 214, 158], HIM = [196, 220, 255];

// ------------------------------------------------------------------ noise and the stars
const R = rng(1118);
const perm = Array.from({ length: 512 }, () => R());
const hash = (x, y) => perm[((x * 73 + y * 151) & 255) + ((y * 37) & 255)];
function vnoise(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  return lerp(lerp(hash(xi, yi), hash(xi + 1, yi), u), lerp(hash(xi, yi + 1), hash(xi + 1, yi + 1), u), v);
}
const fbm = (x, y) => vnoise(x, y) * 0.5 + vnoise(x * 2.1, y * 2.1) * 0.25 + vnoise(x * 4.3, y * 4.3) * 0.15 + vnoise(x * 8.7, y * 8.7) * 0.1;

const STARS = Array.from({ length: 14000 }, () => {
  const b = Math.pow(R(), 7);
  const w = R();
  return { r: 3400 * Math.sqrt(R()), a: R() * TAU, b, size: 0.6 + 3.0 * b,
    col: w < 0.14 ? [255, 196, 150] : w < 0.24 ? [255, 228, 196] : w < 0.7 ? [236, 240, 255] : [170, 196, 255], tw: R() * TAU, tws: 0.8 + R() * 2.4 };
});

// Milky Way baked once in sky-plane coordinates around the pole: a band, dust lanes, fine star dust.
const MW = layer(1024, 1024);
{
  const g = MW.getContext('2d'), img = g.createImageData(1024, 1024), d = img.data;
  const nx = Math.cos(0.9), ny = Math.sin(0.9);
  for (let y = 0; y < 1024; y++) for (let x = 0; x < 1024; x++) {
    const px = x / 1024 - 0.5, py = y / 1024 - 0.5;
    const dist = Math.abs((px - 0.06) * nx + (py + 0.12) * ny);
    const band = Math.exp(-((dist / 0.085) ** 2));
    const cloud = fbm(x / 70, y / 70), lane = fbm(x / 38 + 9, y / 38 + 3);
    let k = band * (0.35 + 0.9 * cloud) * (1 - 0.75 * clamp((lane - 0.48) * 4));
    const core = Math.exp(-(((px - 0.2) ** 2 + (py + 0.05) ** 2) / 0.02));
    const i = (y * 1024 + x) * 4;
    d[i] = 120 + 110 * core; d[i + 1] = 118 + 60 * core; d[i + 2] = 190 - 30 * core; d[i + 3] = 255 * clamp(k * 0.42);
  }
  g.putImageData(img, 0, 0);
}
const MW_R = 3400;

// sky rotation (radians). The sky turns slowly forward, then runs back hard on "time machine",
// then stops dead when the two hands meet.
const PHI = [[0, 0], [128.23, 0.06, ease.linear], [129.0, 0.045], [131.4, -0.9, ease.in], [134.23, -2.6, ease.linear],
  [135.6, -3.05, ease.out], [136.23, -3.1, ease.out], [146.7, -3.12]];
const phiAt = (s) => kf(s, PHI);

function sky(c, s, cam, look) {
  // background gradient, Milky Way, star trails. look: { pole, horizon, dawn, gain, exposure }
  const { pole, horizon, dawn = 0, gain = 1, exposure = 0.9, mw = 0 } = look;
  const z = cam.z, tx = (x) => cam.x + (x - cam.cx) * z, ty = (y) => cam.y + (y - cam.cy) * z;
  const top = mixc(NIGHT.top, DAWN.top, dawn), mid = mixc(NIGHT.mid, DAWN.mid, dawn), low = mixc(NIGHT.low, DAWN.low, dawn);
  const gr = c.createLinearGradient(0, ty(horizon - 900), 0, ty(horizon));
  gr.addColorStop(0, css(top)); gr.addColorStop(0.62, css(mid)); gr.addColorStop(1, css(low));
  c.fillStyle = gr; c.fillRect(0, 0, W, H);
  const glow = c.createRadialGradient(tx(1250), ty(horizon), 0, tx(1250), ty(horizon), 900 * z);
  glow.addColorStop(0, css(mixc(NIGHT.glow, DAWN.glow, dawn), 0.55)); glow.addColorStop(1, css(NIGHT.glow, 0));
  c.fillStyle = glow; c.fillRect(0, 0, W, H);

  const phi = phiAt(s), phiPast = phiAt(s - exposure);
  const P = { x: tx(pole.x), y: ty(pole.y) };
  const fade = (y) => clamp(1 - dawn * 1.25 * (0.35 + 0.65 * clamp((y - ty(horizon - 700)) / (700 * z)))) * clamp((ty(horizon) - y) / (90 * z) + 0.15);
  c.save();
  c.globalAlpha = (0.9 - 0.85 * dawn) * gain * clamp(1.6 - z * 0.45);
  c.translate(P.x, P.y); c.rotate(phi + mw);
  c.drawImage(MW, -MW_R * z, -MW_R * z, 2 * MW_R * z, 2 * MW_R * z);
  c.restore();

  starX.clearRect(0, 0, W, H);
  starX.globalCompositeOperation = 'lighter'; starX.lineCap = 'round';
  const beat = songAt(song, s);
  const kick = beat.kick * 0.35 + beat.energy * 0.25;
  for (const st of STARS) {
    const r = st.r * z, a = st.a + phi;
    const x = P.x + r * Math.cos(a), y = P.y + r * Math.sin(a);
    const arc = phi - phiPast, reach = Math.abs(arc) * r + 60;
    if (x < -reach || x > W + reach || y < -reach || y > ty(horizon) + 20) continue;
    const tw = 0.72 + 0.28 * Math.sin(s * st.tws + st.tw);
    const alpha = gain * fade(y) * (0.22 + 0.78 * st.b) * tw * (1 + kick * st.b * 2);
    if (alpha < 0.02) continue;
    const size = st.size * Math.min(1.6, Math.sqrt(z));
    if (Math.abs(arc) * r > 1.2) {
      starX.strokeStyle = css(st.col, alpha * 0.85); starX.lineWidth = size * 0.85;
      starX.beginPath();
      if (arc > 0) starX.arc(P.x, P.y, r, a - arc, a); else starX.arc(P.x, P.y, r, a, a - arc);
      starX.stroke();
    } else if (size < 1.3) {
      starX.fillStyle = css(st.col, alpha); starX.fillRect(x - size / 2, y - size / 2, size, size);
    } else {
      starX.fillStyle = css(st.col, alpha); starX.beginPath(); starX.arc(x, y, size * 0.6, 0, TAU); starX.fill();
    }
  }
  bloom(c, starL, 1, 0.55 + kick * 0.5);
}

function bloom(c, src, base = 1, amount = 0.6) {
  c.save();
  c.globalCompositeOperation = 'lighter';
  c.globalAlpha = base; c.drawImage(src, 0, 0);
  c.filter = 'blur(4px)'; c.globalAlpha = amount; c.drawImage(src, 0, 0);
  c.filter = 'blur(16px)'; c.globalAlpha = amount * 0.8; c.drawImage(src, 0, 0);
  c.restore();
}

// ------------------------------------------------------------------ the land on the horizon
const ROOFS = (() => {
  const r = rng(7), out = [];
  let x = -200;
  while (x < 3400) {
    const w = 50 + r() * 120, h = 30 + r() * 90, roof = r() < 0.55 ? 18 + r() * 34 : 0;
    const wins = Array.from({ length: Math.floor(r() * 4) }, () => ({ u: 0.15 + r() * 0.7, v: 0.25 + r() * 0.5, on: r(), off: 118 + r() * 30 }));
    out.push({ x, w, h, roof, wins, chimney: r() < 0.25 });
    x += w + r() * 14;
  }
  return out;
})();
function land(c, cam, horizon, dawn, s) {
  const z = cam.z, tx = (x) => cam.x + (x - cam.cx) * z, ty = (y) => cam.y + (y - cam.cy) * z;
  // far hills
  c.fillStyle = css(mixc([10, 14, 32], [70, 66, 104], dawn));
  c.beginPath(); c.moveTo(0, H);
  for (let x = -40; x <= W + 40; x += 20) {
    const wx = cam.cx + (x - cam.x) / z;
    c.lineTo(x, ty(horizon - 58 - 46 * fbm(wx / 380, 3.1) - 20 * Math.sin(wx / 610)));
  }
  c.lineTo(W, H); c.fill();
  // rooftops
  const ink = css(mixc([4, 6, 14], [40, 38, 66], dawn * 0.8));
  c.fillStyle = ink;
  for (const b of ROOFS) {
    const x0 = tx(b.x - 600), x1 = tx(b.x - 600 + b.w);
    if (x1 < -20 || x0 > W + 20) continue;
    const yb = ty(horizon + 30), yt = ty(horizon - b.h);
    c.fillRect(x0, yt, x1 - x0, yb - yt + 400 * z);
    if (b.roof) { c.beginPath(); c.moveTo(x0 - 4 * z, yt); c.lineTo((x0 + x1) / 2, yt - b.roof * z); c.lineTo(x1 + 4 * z, yt); c.fill(); }
    if (b.chimney) c.fillRect(x0 + (x1 - x0) * 0.7, yt - (b.roof || 10) * z * 0.9, 9 * z, 30 * z);
    for (const w of b.wins) {
      if (w.on > 0.45 || s > w.off) continue;
      c.fillStyle = `rgba(255,196,120,${0.75 * (1 - dawn)})`;
      c.fillRect(x0 + (x1 - x0) * w.u, yt + (yb - yt) * w.v, 6 * z, 8 * z);
      c.fillStyle = ink;
    }
  }
  c.fillRect(0, ty(horizon + 28), W, H);
}

// ------------------------------------------------------------------ constellation figures
// joints in figure units (height 1, feet at 0). Poses are interpolated joint by joint.
const J = ['head', 'neck', 'shL', 'shR', 'elL', 'elR', 'hL', 'hR', 'hip', 'hipL', 'hipR', 'kL', 'kR', 'fL', 'fR'];
const BONES = [['head', 'neck'], ['neck', 'shL'], ['neck', 'shR'], ['shL', 'elL'], ['elL', 'hL'], ['shR', 'elR'], ['elR', 'hR'],
  ['neck', 'hip'], ['hip', 'hipL'], ['hip', 'hipR'], ['hipL', 'kL'], ['kL', 'fL'], ['hipR', 'kR'], ['kR', 'fR']];
const POSE = {
  stand: { head: [0, -0.95], neck: [0, -0.81], shL: [-0.12, -0.78], shR: [0.12, -0.78], elL: [-0.16, -0.58], elR: [0.165, -0.585],
    hL: [-0.17, -0.38], hR: [0.18, -0.39], hip: [0, -0.47], hipL: [-0.075, -0.45], hipR: [0.075, -0.45], kL: [-0.085, -0.23], kR: [0.08, -0.235], fL: [-0.09, 0], fR: [0.095, 0] },
  look: { head: [0.03, -0.965], neck: [0.01, -0.815] },
  reach: { shR: [0.12, -0.785], elR: [0.3, -0.7], hR: [0.47, -0.66], head: [0.035, -0.955] },
  hold: { shR: [0.12, -0.78], elR: [0.25, -0.63], hR: [0.37, -0.52], head: [0.05, -0.95] },
  holdL: { shL: [-0.12, -0.78], elL: [-0.24, -0.6], hL: [-0.348, -0.489], head: [-0.05, -0.95] },
};
const pose = (...names) => Object.assign({}, POSE.stand, ...names.map((n) => POSE[n]));
const blendPose = (a, b, k) => Object.fromEntries(J.map((j) => [j, [lerp(a[j][0], b[j][0], k), lerp(a[j][1], b[j][1], k)]]));
const MAG = { head: 1.25, neck: 0.5, shL: 0.75, shR: 0.75, elL: 0.5, elR: 0.5, hL: 1.0, hR: 1.0, hipL: 0.6, hipR: 0.6, kL: 0.45, kR: 0.45, fL: 0.8, fR: 0.8 };
const HAIR = [[-0.05, -1.0], [-0.075, -0.93], [-0.07, -0.86]];

// draw: 0..1 per bone (line growth), stars light as their bone arrives; brk: 0..1 lines break and drift
function figure(c, s, at, pz, col, { draw = 1, brk = 0, glow = 1, hair = false, seed = 1, dust = 0 }) {
  const rr = rng(seed);
  const jitter = J.map(() => [rr() - 0.5, rr() - 0.5]);
  const beat = songAt(song, s);
  const P = (j) => { const k = J.indexOf(j); const d = brk * brk * 0.35; return [at.x + (pz[j][0] + jitter[k][0] * d) * at.h, at.y + (pz[j][1] + jitter[k][1] * d) * at.h]; };
  c.save(); c.globalCompositeOperation = 'lighter'; c.lineCap = 'round';
  const n = BONES.length, lit = new Set();
  BONES.forEach(([a, b], i) => {
    const k = clamp(draw * n - i);
    if (k <= 0) return;
    lit.add(a); if (k > 0.85) lit.add(b);
    const [x0, y0] = P(a), [x1, y1] = P(b);
    const gap = brk * 0.5;   // breaking: a gap opens in the middle of each line
    const m = (u) => [lerp(x0, x1, u), lerp(y0, y1, u)];
    c.strokeStyle = css(col, 0.34 * glow * (1 - brk));
    c.lineWidth = 1.2 + Math.min(1.4, at.h / 1000);
    c.beginPath();
    const e = Math.min(k, 0.5 - gap / 2);
    if (e > 0) { const [ax, ay] = m(0.04), [bx, by] = m(Math.max(0.04, e)); c.moveTo(ax, ay); c.lineTo(bx, by); }
    if (k > 0.5 + gap / 2) { const [ax, ay] = m(0.5 + gap / 2), [bx, by] = m(Math.min(k, 0.96)); c.moveTo(ax, ay); c.lineTo(bx, by); }
    c.stroke();
  });
  // Seen closer, each line is a stream of fine star dust flowing along the bone; on "will end" it drifts off.
  if (dust > 0) {
    const dr = rng(seed * 97);
    BONES.forEach(([a, b], i) => {
      if (clamp(draw * n - i) < 1) return;
      const [x0, y0] = P(a), [x1, y1] = P(b), len = Math.hypot(x1 - x0, y1 - y0), nx = -(y1 - y0) / len, ny = (x1 - x0) / len;
      const count = Math.round(len / 3);
      for (let k = 0; k < count; k++) {
        const u = (dr() + s * (0.04 + dr() * 0.05)) % 1, off = (dr() + dr() + dr() - 1.5) * 7 * Math.min(2, at.h / 600);
        const drift = brk * brk * (120 + dr() * 260), da = dr() * TAU;
        const x = lerp(x0, x1, u) + nx * off + Math.cos(da) * drift, y = lerp(y0, y1, u) + ny * off + Math.sin(da) * drift - brk * 60 * dr();
        const al = dust * (0.25 + 0.6 * dr()) * glow * (1 - brk * 0.6) * (0.6 + 0.4 * Math.sin(s * 3 + k));
        c.fillStyle = css(dr() < 0.2 ? [255, 255, 255] : col, al);
        const sz = dr() < 0.1 ? 2.2 : 1.3;
        c.fillRect(x - sz / 2, y - sz / 2, sz, sz);
      }
    });
  }
  const stars = [...lit].filter((j) => MAG[j]).map((j) => [...P(j), MAG[j]]);
  if (hair && draw > 0.95) HAIR.forEach(([u, v]) => stars.push([at.x + (u + pz.head[0]) * at.h, at.y + (v - (-0.95) + pz.head[1]) * at.h, 0.45]));
  const unit = Math.min(1.8, 0.75 + at.h / 900);   // stars stay point-like when the figure is framed closer
  stars.forEach(([x, y, mag], i) => {
    const tw = 0.85 + 0.15 * Math.sin(s * (2 + i * 0.37) + i);
    const fl = 1 + (beat.kick * 0.6 + beat.snap * 0.35) * mag;
    const r0 = 2.4 * mag * unit * glow * tw * fl;
    const g = c.createRadialGradient(x, y, 0, x, y, r0 * 5);
    g.addColorStop(0, css([255, 255, 255], 0.95 * glow)); g.addColorStop(0.18, css(col, 0.75 * glow)); g.addColorStop(1, css(col, 0));
    c.fillStyle = g; c.beginPath(); c.arc(x, y, r0 * 5, 0, TAU); c.fill();
    if (mag >= 1) {   // diffraction spikes on the brightest stars only
      c.strokeStyle = css(col, 0.28 * glow * tw); c.lineWidth = 1;
      c.beginPath(); c.moveTo(x - r0 * 8, y); c.lineTo(x + r0 * 8, y); c.moveTo(x, y - r0 * 8); c.lineTo(x, y + r0 * 8); c.stroke();
    }
  });
  c.restore();
  return P;
}

// ------------------------------------------------------------------ the bedroom
const WIN = { x: 1060, y: 150, w: 600, h: 720 };
function room(c, s, cam, { lamp = 0, dawn = 0 }) {
  const z = cam.z, tx = (x) => cam.x + (x - cam.cx) * z, ty = (y) => cam.y + (y - cam.cy) * z;
  const wall = mixc(mixc([10, 14, 30], [38, 27, 26], lamp), [52, 58, 82], dawn);
  c.save();
  // wall with the window cut out
  c.fillStyle = css(wall);
  c.beginPath(); c.rect(-10, -10, W + 20, H + 20); c.rect(tx(WIN.x + WIN.w), ty(WIN.y), -(WIN.w * z), WIN.h * z); c.fill('evenodd');
  // floor
  const fy = ty(905);
  const fl = c.createLinearGradient(0, fy, 0, H);
  fl.addColorStop(0, css(mixc(wall, [0, 0, 0], 0.25))); fl.addColorStop(1, css(mixc(wall, [0, 0, 0], 0.65)));
  c.fillStyle = fl; c.fillRect(0, fy, W, H - fy);
  // light: the lamp warms the left wall; with the lamp off, moonlight throws the panes onto the floor;
  // at dawn the panes turn warm and climb the wall.
  if (lamp > 0.01) {
    const g = c.createRadialGradient(tx(470), ty(545), 0, tx(470), ty(545), 820 * z);
    g.addColorStop(0, `rgba(255,178,102,${0.55 * lamp})`); g.addColorStop(0.35, `rgba(255,150,90,${0.18 * lamp})`); g.addColorStop(1, 'rgba(255,150,90,0)');
    c.globalCompositeOperation = 'lighter'; c.fillStyle = g; c.fillRect(0, 0, W, H); c.globalCompositeOperation = 'source-over';
  }
  const moon = (1 - lamp) * (1 - dawn) * 0.16 + dawn * 0.3;
  if (moon > 0.01) {
    const col = dawn > 0.3 ? [255, 196, 150] : [150, 176, 255];
    c.fillStyle = css(col, moon);
    const sk = -0.55 + dawn * 0.25, drop = 0.55 - dawn * 0.4;
    for (const [px, py] of [[0, 0], [0.5, 0], [0, 0.42], [0.5, 0.42]]) {
      const x0 = WIN.x + WIN.w * px, y0 = 905 - 150 * drop + WIN.h * py * drop * 0.35, w = WIN.w * 0.47, h = WIN.h * 0.4 * drop * 0.35 + 30;
      c.beginPath();
      c.moveTo(tx(x0 + sk * (905 - y0)), ty(y0)); c.lineTo(tx(x0 + w + sk * (905 - y0)), ty(y0));
      c.lineTo(tx(x0 + w + sk * (905 - y0 - h) - 160), ty(y0 + h)); c.lineTo(tx(x0 + sk * (905 - y0 - h) - 160), ty(y0 + h));
      c.fill();
    }
  }
  // window frame, mullions, sill
  const frame = css(mixc([6, 8, 16], [30, 30, 44], dawn));
  c.fillStyle = frame;
  const fx = (x, y, w, h) => c.fillRect(tx(x), ty(y), w * z, h * z);
  fx(WIN.x - 24, WIN.y - 24, WIN.w + 48, 24); fx(WIN.x - 24, WIN.y + WIN.h, WIN.w + 48, 22);
  fx(WIN.x - 24, WIN.y, 24, WIN.h); fx(WIN.x + WIN.w, WIN.y, 24, WIN.h);
  fx(WIN.x + WIN.w / 2 - 7, WIN.y, 14, WIN.h); fx(WIN.x, WIN.y + WIN.h * 0.42 - 7, WIN.w, 14);
  c.fillStyle = css(mixc(wall, [255, 255, 255], 0.06 + dawn * 0.1)); fx(WIN.x - 40, WIN.y + WIN.h + 22, WIN.w + 80, 16);
  // curtains, folds swaying a little
  for (const [x0, x1, side] of [[880, 1062, -1], [1658, 1830, 1]]) {
    for (let k = 0; k < 7; k++) {
      const u0 = k / 7, sway = Math.sin(s * 0.9 + k * 0.8) * 3 * side;
      const g = c.createLinearGradient(tx(lerp(x0, x1, u0)), 0, tx(lerp(x0, x1, u0 + 1 / 7)), 0);
      const base = mixc(mixc([18, 22, 44], [70, 42, 36], lamp), [84, 88, 118], dawn);
      g.addColorStop(0, css(mixc(base, [0, 0, 0], 0.35))); g.addColorStop(0.55, css(base)); g.addColorStop(1, css(mixc(base, [0, 0, 0], 0.5)));
      c.fillStyle = g;
      c.beginPath();
      c.moveTo(tx(lerp(x0, x1, u0)), ty(90)); c.lineTo(tx(lerp(x0, x1, u0 + 1 / 7) + 1), ty(90));
      c.lineTo(tx(lerp(x0, x1, u0 + 1 / 7) + 1 + sway * 1.6), ty(1000)); c.lineTo(tx(lerp(x0, x1, u0) + sway * 1.6), ty(1000));
      c.fill();
    }
  }
  // desk, lamp, a photo that faces the bed
  c.fillStyle = css(mixc([5, 6, 12], [26, 22, 30], lamp * 0.6 + dawn * 0.4));
  fx(300, 700, 560, 26); fx(330, 726, 22, 200); fx(810, 726, 22, 200);
  fx(420, 684, 110, 16); fx(466, 520, 12, 168);
  c.beginPath(); c.moveTo(tx(410), ty(545)); c.lineTo(tx(536), ty(545)); c.lineTo(tx(502), ty(462)); c.lineTo(tx(444), ty(462)); c.fill();
  if (lamp > 0.01) {
    c.fillStyle = `rgba(255,214,150,${0.9 * lamp})`;
    c.beginPath(); c.ellipse(tx(473), ty(545), 63 * z, 7 * z, 0, 0, TAU); c.fill();
    c.fillStyle = `rgba(255,190,120,${0.35 * lamp})`; fx(140, 700, 600, 4);
  }
  c.save(); c.translate(tx(700), ty(700)); c.rotate(-0.08);
  c.fillStyle = css(mixc([24, 26, 38], [210, 196, 170], lamp * 0.8 + dawn * 0.5)); c.fillRect(-46 * z, -108 * z, 92 * z, 108 * z);
  c.fillStyle = css(mixc([10, 12, 22], [90, 70, 80], lamp * 0.7 + dawn * 0.5)); c.fillRect(-38 * z, -100 * z, 76 * z, 74 * z);
  c.restore();
  // the bed's corner, nearest to us: a dark mass with the light from the room on its edge
  const bed = css(mixc([3, 4, 9], [20, 18, 26], dawn));
  c.fillStyle = bed;
  c.beginPath(); c.moveTo(tx(-60), ty(1100)); c.lineTo(tx(-60), ty(905));
  c.bezierCurveTo(tx(220), ty(880), tx(420), ty(930), tx(560), ty(1000)); c.lineTo(tx(640), ty(1100)); c.fill();
  c.strokeStyle = lamp > 0.01 ? `rgba(255,170,110,${0.35 * lamp})` : `rgba(150,170,230,${0.12 + dawn * 0.15})`; c.lineWidth = 2 * z;
  c.beginPath(); c.moveTo(tx(-60), ty(905)); c.bezierCurveTo(tx(220), ty(880), tx(420), ty(930), tx(560), ty(1000)); c.stroke();
  c.restore();
}

// ------------------------------------------------------------------ meteors running backwards (rising)
const METEORS = Array.from({ length: 26 }, (_, i) => { const r = rng(300 + i); return { t: 128.6 + r() * 5.4, x: 260 + r() * 1400, len: 120 + r() * 260, v: 900 + r() * 700, ang: -1.25 - r() * 0.5 }; });
function meteors(c, s, list, alpha = 1) {
  c.save(); c.globalCompositeOperation = 'lighter'; c.lineCap = 'round';
  for (const m of list) {
    const age = s - m.t;
    if (age < 0 || age > 0.9) continue;
    const head = { x: m.x + Math.cos(m.ang) * m.v * age, y: 880 + Math.sin(m.ang) * m.v * age };
    const tail = { x: head.x - Math.cos(m.ang) * m.len, y: head.y - Math.sin(m.ang) * m.len };
    const g = c.createLinearGradient(tail.x, tail.y, head.x, head.y);
    const a = alpha * Math.sin(Math.PI * age / 0.9);
    g.addColorStop(0, 'rgba(200,220,255,0)'); g.addColorStop(1, `rgba(240,246,255,${a})`);
    c.strokeStyle = g; c.lineWidth = 2.2; c.beginPath(); c.moveTo(tail.x, tail.y); c.lineTo(head.x, head.y); c.stroke();
  }
  c.restore();
}
// one falling star (forward time) seen through the window before he sleeps
const WISH = [{ t: 115.6, x: 1560, len: 210, v: 520, ang: 2.55 }];
function fallingStar(c, s) {
  for (const m of WISH) {
    const age = s - m.t;
    if (age < 0 || age > 0.75) continue;
    const head = { x: m.x + Math.cos(m.ang) * m.v * age, y: 230 + Math.sin(m.ang) * m.v * age };
    const tail = { x: head.x - Math.cos(m.ang) * m.len, y: head.y - Math.sin(m.ang) * m.len };
    const g = c.createLinearGradient(tail.x, tail.y, head.x, head.y);
    g.addColorStop(0, 'rgba(255,230,200,0)'); g.addColorStop(1, `rgba(255,248,236,${Math.sin(Math.PI * age / 0.75)})`);
    c.save(); c.globalCompositeOperation = 'lighter'; c.strokeStyle = g; c.lineWidth = 2.6; c.lineCap = 'round';
    c.beginPath(); c.moveTo(tail.x, tail.y); c.lineTo(head.x, head.y); c.stroke(); c.restore();
  }
}

// ------------------------------------------------------------------ finishing: grain, vignette
const GRAIN = layer(256, 256);
{
  const g = GRAIN.getContext('2d'), im = g.createImageData(256, 256), r = rng(5);
  for (let i = 0; i < im.data.length; i += 4) { const v = 128 + (r() - 0.5) * 90; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; }
  g.putImageData(im, 0, 0);
}
function finish(c, frame, dark = 0.5) {
  const v = c.createRadialGradient(W / 2, H / 2, H * 0.42, W / 2, H / 2, H * 1.05);
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, `rgba(0,0,0,${dark})`);
  c.fillStyle = v; c.fillRect(0, 0, W, H);
  c.save(); c.globalCompositeOperation = 'overlay'; c.globalAlpha = 0.07;
  const ox = (frame * 97) % 256, oy = (frame * 61) % 256;
  c.translate(-ox, -oy); c.fillStyle = c.createPattern(GRAIN, 'repeat'); c.fillRect(0, 0, W + 256, H + 256);
  c.restore();
}

// ------------------------------------------------------------------ shots (song seconds)
const SKY_A = { pole: { x: 1500, y: -520 }, horizon: 830, mw: 2.2 };          // looking out of his window, east
const SKY_N = { pole: { x: 960, y: 150 }, horizon: 905, mw: 0 };             // turned north: the pole is in frame
const HERE = { cx: 960, cy: 540, x: 960, y: 540 };
const cam = (z, cx = 960, cy = 540) => ({ z, cx, cy, x: 960, y: 540 });

const SHOTS = [
  // 1 · his room at night; a star falls on "go back in time"
  { a: 112.227, b: 118.227, draw(s) {
    const z = kf(s, [[112.227, 1.0], [118.227, 1.12, ease.inOutSoft]]);
    sky(ctx, s, cam(z * 0.98 + 0.02, 1360, 510), { ...SKY_A, gain: 0.9 });
    land(ctx, cam(z * 0.98 + 0.02, 1360, 510), SKY_A.horizon, 0, s);
    fallingStar(ctx, s);
    room(ctx, s, cam(z, 1360, 510), { lamp: 1 });
  } },
  // 2 · "each time I fall asleep": the lamp goes out on the bar, the eyes adjust, and he goes through the window
  { a: 118.227, b: 122.227, draw(s) {
    const z = kf(s, [[118.227, 1.12], [121.55, 1.55, ease.inOut], [122.227, 12, ease.in]]);
    const lamp = s < 118.227 + 0.05 ? 1 : Math.exp(-(s - 118.277) * 14) * 0.6;
    const gain = kf(s, [[118.227, 0.55], [120.6, 1.15, ease.out]]);
    sky(ctx, s, cam(1.0, 1360, 510), { ...SKY_A, gain });
    land(ctx, cam(1.0, 1360, 510), SKY_A.horizon, 0, s);
    // push toward the middle of the upper-right pane so no mullion is left in frame when the room is gone
    const k = clamp((z - 1.12) / (9.5 - 1.12));
    const rc = { z, cx: lerp(1360, 1510, k), cy: lerp(510, 301, k), x: lerp(960, 960, k), y: 540 };
    room(ctx, s, rc, { lamp });
  } },
  // 3 · "I always see you there": her stars light one bone per eighth note
  { a: 122.227, b: 126.227, draw(s) {
    // tilt up off the rooftops as she is drawn, then hold her
    const c0 = { ...cam(kf(s, [[122.227, 1.0], [126.227, 1.12, ease.inOutSoft]]), 1360, 510), y: kf(s, [[122.227, 540], [125.4, 700, ease.inOutSoft]]) };
    sky(ctx, s, c0, { ...SKY_A, gain: 1.15 });
    land(ctx, c0, SKY_A.horizon, 0, s);
    figX.clearRect(0, 0, W, H);
    const draw = clamp((s - 122.6) / 3.3);
    figure(figX, s, { x: c0.x + (1180 - c0.cx) * c0.z, y: c0.y + (760 - c0.cy) * c0.z, h: 560 * c0.z }, pose('stand'), HER, { draw, hair: true, seed: 3 });
    bloom(ctx, figL, 1, 0.6);
  } },
  // 4 · closer: she turns her head to him and lifts a hand; dust turns around the hand
  { a: 126.227, b: 128.227, draw(s) {
    const c0 = { ...cam(kf(s, [[126.227, 1.9], [128.227, 2.15, ease.inOutSoft]]), 1290, 360), x: kf(s, [[126.227, 900], [128.227, 1010, ease.inOutSoft]]) };
    sky(ctx, s, c0, { ...SKY_A, gain: 1.2 });
    figX.clearRect(0, 0, W, H);
    const k = ease.inOut(clamp((s - 126.3) / 1.6));
    const P = figure(figX, s, { x: c0.x + (1180 - c0.cx) * c0.z, y: c0.y + (760 - c0.cy) * c0.z, h: 560 * c0.z }, blendPose(pose('stand'), pose('reach', 'look'), k), HER, { draw: 1, hair: true, seed: 3, dust: 1 });
    const [hx, hy] = P('hR');
    figX.save(); figX.globalCompositeOperation = 'lighter';
    const r = rng(9);
    for (let i = 0; i < 70; i++) {
      const rad = 30 + r() * 150, a = r() * TAU + s * (0.6 + r() * 0.8), al = r() * 0.6;
      figX.fillStyle = `rgba(255,226,180,${al})`;
      figX.fillRect(hx + Math.cos(a) * rad, hy + Math.sin(a) * rad * 0.6, 2, 2);
    }
    figX.restore();
    bloom(ctx, figL, 1, 0.7);
  } },
  // 5 · "going back in a time machine": face north; the sky's clock runs backwards around her
  { a: 128.227, b: 134.227, draw(s) {
    const c0 = cam(kf(s, [[128.227, 1.0], [134.227, 1.18, ease.inOutSoft]]), 960, 560);
    sky(ctx, s, c0, { ...SKY_N, gain: 1.15, exposure: 1.1 });
    meteors(ctx, s, METEORS, 0.9);
    land(ctx, c0, SKY_N.horizon, 0, s);
    figX.clearRect(0, 0, W, H);
    figure(figX, s, { x: c0.x + (960 - c0.cx) * c0.z, y: c0.y + (860 - c0.cy) * c0.z, h: 500 * c0.z }, pose('reach', 'look'), HER, { draw: 1, hair: true, seed: 3 });
    bloom(ctx, figL, 1, 0.7);
  } },
  // 6 · "when I wake up your time with me": he is drawn beside her and their hands meet on the bar
  { a: 134.227, b: 137.227, draw(s) {
    const c0 = cam(1.0, 960, 540);
    sky(ctx, s, c0, { ...SKY_A, pole: { x: 1300, y: -700 }, gain: 1.1, exposure: 1.1 });
    land(ctx, c0, SKY_A.horizon, 0, s);
    figX.clearRect(0, 0, W, H);
    const k = ease.inOut(clamp((s - 134.6) / 1.62));
    const her = blendPose(pose('stand', 'look'), pose('hold'), k), him = blendPose(pose('stand'), pose('holdL'), k);
    figure(figX, s, { x: 760, y: 780, h: 540 }, her, HER, { draw: 1, hair: true, seed: 3, dust: 0.45 });
    figure(figX, s, { x: 1160, y: 780, h: 575 }, him, HIM, { draw: clamp((s - 134.227) / 0.9), seed: 4, dust: 0.45 });
    const touch = Math.exp(-Math.max(0, s - 136.227) * 3) * (s >= 136.227 ? 1 : 0);
    if (touch > 0.01) {
      const hx = 960, hy = 499;
      const g = figX.createRadialGradient(hx, hy, 0, hx, hy, 34); g.addColorStop(0, `rgba(255,250,240,${touch})`); g.addColorStop(1, 'rgba(255,240,220,0)');
      figX.fillStyle = g; figX.fillRect(hx - 40, hy - 40, 80, 80);
      figX.strokeStyle = `rgba(255,236,210,${0.6 * touch})`; figX.lineWidth = 2;
      figX.beginPath(); figX.arc(hx, hy, 20 + (1 - touch) * 320, 0, TAU); figX.stroke();
      figX.beginPath(); figX.moveTo(hx - 260 * touch, hy); figX.lineTo(hx + 260 * touch, hy); figX.stroke();
    }
    bloom(ctx, figL, 1, 0.7);
  } },
  // 7 · insert: the two hand stars become one
  { a: 137.227, b: 138.227, draw(s) {
    const c0 = cam(5.2, 960, 505);
    sky(ctx, s, c0, { ...SKY_A, pole: { x: 1300, y: -700 }, gain: 1.2, exposure: 0.2 });
    figX.clearRect(0, 0, W, H);
    const her = pose('hold'), him = pose('holdL');
    const sc = (p, at) => ({ x: c0.x + (at.x - c0.cx) * c0.z, y: c0.y + (at.y - c0.cy) * c0.z, h: at.h * c0.z });
    figure(figX, s, sc(0, { x: 760, y: 780, h: 540 }), her, HER, { draw: 1, hair: true, seed: 3, dust: 1 });
    figure(figX, s, sc(0, { x: 1160, y: 780, h: 575 }), him, HIM, { draw: 1, seed: 4, dust: 1 });
    const ring = (s - 137.227) / 1.0;
    const cx = W / 2, cy = H / 2 + (499 - 505) * c0.z, sr = rng(41);
    figX.save(); figX.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 260; i++) {
      const a = sr() * TAU + ring * (2 + sr() * 3), rad = (40 + sr() * 520) * (1 - ease.out(ring) * 0.85);
      figX.fillStyle = css(sr() < 0.5 ? HER : HIM, 0.25 + 0.5 * sr());
      figX.fillRect(cx + Math.cos(a) * rad, cy + Math.sin(a) * rad * 0.8, 2, 2);
    }
    const g = figX.createRadialGradient(cx, cy, 0, cx, cy, 70);
    g.addColorStop(0, 'rgba(255,252,246,1)'); g.addColorStop(0.2, 'rgba(255,236,214,0.6)'); g.addColorStop(1, 'rgba(255,236,214,0)');
    figX.fillStyle = g; figX.fillRect(cx - 80, cy - 80, 160, 160);
    figX.restore();
    figX.save(); figX.globalCompositeOperation = 'lighter';
    figX.strokeStyle = `rgba(255,236,210,${0.5 * (1 - ring)})`; figX.lineWidth = 3;
    figX.beginPath(); figX.arc(W / 2, H / 2 - 30, 60 + ring * 700, 0, TAU); figX.stroke(); figX.restore();
    bloom(ctx, figL, 1, 0.8);
  } },
  // 8 · "will end, so don't let me fall asleep": dawn comes up; their lines break apart
  { a: 138.227, b: 142.227, draw(s) {
    const c0 = cam(kf(s, [[138.227, 1.1], [142.227, 0.96, ease.inOutSoft]]), 960, 560);
    const dawn = kf(s, [[138.227, 0.0], [142.227, 0.62, ease.inOutSoft]]);
    sky(ctx, s, c0, { ...SKY_A, pole: { x: 1300, y: -700 }, dawn, gain: 1.0, exposure: 0.2 });
    land(ctx, c0, SKY_A.horizon, dawn, s);
    figX.clearRect(0, 0, W, H);
    const brk = clamp((s - 140.58) / 1.65);
    const sc = (at) => ({ x: c0.x + (at.x - c0.cx) * c0.z, y: c0.y + (at.y - c0.cy) * c0.z, h: at.h * c0.z });
    figure(figX, s, sc({ x: 790, y: 780, h: 500 }), pose('hold'), HER, { draw: 1, hair: true, seed: 3, brk, glow: 1 - dawn * 0.55, dust: 0.8 });
    figure(figX, s, sc({ x: 1130, y: 780, h: 530 }), pose('holdL'), HIM, { draw: 1, seed: 4, brk, glow: 1 - dawn * 0.55, dust: 0.8 });
    bloom(ctx, figL, 1, 0.6);
  } },
  // 9 · he wakes: the same window, morning; the last star in it goes out
  { a: 142.227, b: T0 + DUR, draw(s) {
    const z = kf(s, [[142.227, 1.22], [146.627, 1.0, ease.inOutSoft]]);
    const dawn = kf(s, [[142.227, 0.7], [146.627, 0.95]]);
    sky(ctx, s, cam(z * 0.98 + 0.02, 1360, 510), { ...SKY_A, dawn, gain: 0.8 });
    land(ctx, cam(z * 0.98 + 0.02, 1360, 510), SKY_A.horizon, dawn, s);
    const last = clamp(1 - (s - 144.0) / 2.0);
    if (last > 0) {
      const c0 = cam(z * 0.98 + 0.02, 1360, 510), x = c0.x + (1480 - c0.cx) * c0.z, y = c0.y + (300 - c0.cy) * c0.z;
      const g = ctx.createRadialGradient(x, y, 0, x, y, 26); g.addColorStop(0, `rgba(255,236,200,${last})`); g.addColorStop(1, 'rgba(255,230,200,0)');
      ctx.fillStyle = g; ctx.fillRect(x - 30, y - 30, 60, 60);
    }
    room(ctx, s, cam(z, 1360, 510), { lamp: 0, dawn: dawn * 0.8 });
  } },
];

function seek(t) {
  const s = T0 + t;
  const shot = SHOTS.find((x) => s >= x.a && s < x.b) || SHOTS[SHOTS.length - 1];
  ctx.save(); ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1; ctx.filter = 'none';
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  shot.draw(s);
  ctx.restore();
  finish(ctx, Math.round(t * FPS), 0.55);
  const out = clamp((DUR - t) / 0.5);
  if (out < 1) { ctx.fillStyle = `rgba(0,0,0,${1 - out})`; ctx.fillRect(0, 0, W, H); }
}

register({ duration: DUR, fps: FPS, width: W, height: H, seek, meta: { T0, shots: SHOTS.map((x) => [x.a - T0, x.b - T0]) } });
seek(0);
