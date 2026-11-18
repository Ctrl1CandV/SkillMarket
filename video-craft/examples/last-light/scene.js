// last-light — an MV cut to a recording it knows only through its song map (map/songmap.js, from songmap.py).
// Every time comes from the map: shots start and end on SONG.downbeats, far windows light on the verse accents,
// go dark on the bridge's piano notes (SONG.hits.mid). Nothing is computed from the BPM. Concept: brief.md.
import SONG from './map/songmap.js';
import { register, songAt, kf, ease, rng, clamp, lerp } from '../../kit/kit.js';
import { layer, noise, bloom, glow, ridge, fillRidge, view, finish, mix, css } from '../../kit/draw.js';
import { shader } from '../../kit/shader.js';

const W = 1920, H = 1080, FPS = 30, DUR = SONG.duration;
const ctx = document.getElementById('cv').getContext('2d');

// ---------- the song, read from its map
if (SONG.downbeats.length < 20) throw new Error('last-light: the shot list uses bars 0-19; this song map has ' + SONG.downbeats.length + ' bars. Rewrite SHOTS for your song.');
const bar = (n, beat = 1) => {                       // song seconds of bar n ("first bar" in songmap.md), beat 1-4
  const d = SONG.downbeats, a = d[n], b = d[n + 1] ?? a + (a - d[n - 1]);
  return a + (beat - 1) * (b - a) / SONG.meter;
};
// times of the hits in [a, b); when a song has none there, evenly spaced bar lines instead, so nothing goes NaN
const orBars = (list, a, b) => (list.length ? list : SONG.downbeats.filter((t) => t >= a && t < b));
const hitsIn = (list, a, b, min = 0) => list.filter(([t, v]) => t >= a && t < b && v >= min).map(([t]) => t);

const LAMP_ON = bar(0);                              // first downbeat: he lights the lamp, as every night
const LAMP_OUT = bar(14);                            // the last chorus: he puts it out himself
const R = rng(11);

// the far shore's windows: the same 22 in every shot that shows the village
const VILLAGE = Array.from({ length: 22 }, (_, i) => ({ x: 250 + i * 34 + R() * 20, s: 0.5 + R() * 0.6, a: R(), b: R() }));
{
  // on: verse accents light a few at a time; the chorus downbeat lights the rest together
  const verse = orBars([...hitsIn(SONG.accents.low, bar(2), bar(6)), ...hitsIn(SONG.accents.high, bar(2), bar(6))].sort((p, q) => p - q), bar(2), bar(6));
  [...VILLAGE].sort((p, q) => p.a - q.a).forEach((v, k) => {
    v.on = k < 14 ? verse[Math.floor(k * verse.length / 14)] + R() * 0.12 : bar(6) + R() * 0.3;
  });
  // off: the bridge has no drums; each of its piano notes puts a few windows out
  const notes = orBars(hitsIn(SONG.hits.mid, bar(10), bar(13), 0.3), bar(10), bar(13));
  [...VILLAGE].sort((p, q) => p.b - q.b).forEach((v, k) => { v.off = notes[Math.floor(k * notes.length / VILLAGE.length)] + R() * 0.25; });
}
const BY_X = [...VILLAGE].sort((p, q) => p.x - q.x);
const litAt = (v, s) => clamp((s - v.on) / 0.12) * (1 - clamp((s - v.off) / 0.5));

// three boats come home in the verse; his does not
const BOATS = [[bar(2), bar(5, 3)], [bar(3), bar(6)], [bar(4), bar(7)]].map(([t0, t1], i) => ({ t0, t1, i, off: BY_X[3 + i * 4].off }));
const boatK = (b, s) => ease.inOutSoft(clamp((s - b.t0) / (b.t1 - b.t0)));
const lanternAt = (b, s) => clamp((s - b.t0 + 1) / 0.5) * (1 - clamp((s - b.off) / 0.5));

// ---------- time of night, the lamp, the sky
const SKY = { top: [[20, 28, 62], [4, 7, 20]], low: [[222, 140, 116], [32, 36, 78]] };
const LAMP = [255, 188, 112], NEAR = [10, 12, 24], WOOD = [128, 88, 58];
const nightAt = (s) => kf(s, [[0, 0], [bar(6), 0.7, ease.inOutSoft], [bar(10), 1, ease.inOutSoft]]);
const lampAt = (s) => clamp((s - LAMP_ON) / 0.25) * (1 - ease.out(clamp((s - LAMP_OUT) / 0.45)))
  * (0.93 + 0.07 * Math.sin(s * 23) * Math.sin(s * 7.3));
// once his lamp is out, the eyes adjust and the Milky Way comes up over the lake
const mwAt = (s) => 0.1 * nightAt(s) + 0.9 * ease.inOutSoft(clamp((s - LAMP_OUT - 0.4) / (bar(16) - LAMP_OUT)));

const STARS = Array.from({ length: 3200 }, () => ({ x: R() * (W + 600) - 300, y: R() * (H + 900) - 900, b: Math.pow(R(), 6), tw: R() * 6.28 }));
const DUST = Array.from({ length: 16000 }, () => ({ x: R() * (W + 600) - 300, y: R() * (H + 900) - 900, b: 0.3 + R() * 0.7 }));
const MW = shader(W, H, `
void main() {
  vec2 p = (gl_FragCoord.xy - 0.5 * res) / res.y / zoom + off;
  vec2 d = normalize(vec2(1.0, 0.42));
  float along = dot(p, d), across = dot(p, vec2(-d.y, d.x)) - 0.12 * sin(along * 1.3);
  float w = 0.2 + 0.06 * fbm(vec2(along * 0.8, 3.0));
  float band = exp(-across * across / (w * w));
  float body = band * (0.4 + 0.9 * fbm(vec2(along * 1.6, across * 5.0) + 1.7));
  float lane = smoothstep(0.42, 0.7, fbm(vec2(along * 3.2, across * 13.0) + 8.3)) * exp(-across * across / (w * w * 0.2));
  float v = body * (1.0 - 0.8 * lane);
  vec3 c = mix(vec3(0.36, 0.44, 0.84), vec3(1.0, 0.88, 0.76), smoothstep(0.55, 1.1, v)) * v * 0.46;
  o = vec4(c * amt, 1.0);
}`, { scale: 0.5 });
const BD = [1 / Math.hypot(1, 0.42), 0.42 / Math.hypot(1, 0.42)];
function bandAt(x, y, off) {                          // the shader's band, in JS, so the stars can crowd into it
  const px = (x - W / 2) / H + off[0], py = (H / 2 - y) / H + off[1];
  const along = px * BD[0] + py * BD[1], across = -px * BD[1] + py * BD[0] - 0.12 * Math.sin(along * 1.3);
  return Math.exp(-across * across / 0.05);
}

// sky gradient, the dusk glow, the Milky Way and stars, in screen space; sx/sy move it with the camera
function sky(c, s, m, { horizon, sx = 0, sy = 0, off = [0, 0], sunX = 380 }) {
  const n = nightAt(s), amt = mwAt(s), o = [off[0] - sx / H, off[1] + sy / H];
  const g = c.createLinearGradient(0, horizon - 1000, 0, horizon);
  g.addColorStop(0, css(mix(SKY.top[0], SKY.top[1], n)));
  g.addColorStop(1, css(mix(SKY.low[0], SKY.low[1], n)));
  c.fillStyle = g; c.fillRect(0, 0, W, H);
  if (n < 1) {
    const r = c.createRadialGradient(sunX, horizon - 50, 0, sunX, horizon - 50, 950);
    r.addColorStop(0, `rgba(255,168,118,${0.38 * (1 - n)})`); r.addColorStop(1, 'rgba(255,168,118,0)');
    c.fillStyle = r; c.fillRect(0, 0, W, Math.min(H, horizon + 10));
  }
  if (amt > 0.01) {
    MW.draw(s, { amt, off: o, zoom: 1 });
    c.save(); c.globalCompositeOperation = 'lighter'; c.drawImage(MW.canvas, 0, 0, W, H); c.restore();
  }
  const vis = clamp((n - 0.15) * 1.5);
  for (const st of STARS) {
    const x = st.x + sx, y = st.y + sy;
    if (x < -3 || x > W + 3 || y < -3 || y > horizon - 4) continue;
    const a = vis * (0.22 + st.b) * (0.65 + 0.35 * Math.sin(s * 2 + st.tw)) * (1 + 1.6 * bandAt(x, y, o) * amt)
      * (1 + (st.b > 0.35 ? 1.4 * m.snap : 0)) * clamp((horizon - y) / 160);
    if (a < 0.02) continue;
    const r = 1 + st.b * 2.2;
    c.fillStyle = `rgba(236,240,255,${Math.min(1, a)})`; c.fillRect(x, y, r, r);
  }
  if (amt > 0.04) {
    for (const d of DUST) {
      const x = d.x + sx, y = d.y + sy;
      if (x < 0 || x > W || y < 0 || y > horizon - 4) continue;
      const a = amt * bandAt(x, y, o) * 0.85 * d.b * clamp((horizon - y) / 200);
      if (a > 0.03) { c.fillStyle = `rgba(226,230,255,${Math.min(1, a)})`; const r = d.b > 0.85 ? 1.6 : 1; c.fillRect(x, y, r, r); }
    }
  }
}

const wob = noise(11);
// a mirror lake below `wl`: the picture above it, flipped row by row; each row shifts on its own, so lights
// break into slivers instead of shearing; a slight blur, then darkened
const MIRROR = layer(W, H), mX = MIRROR.getContext('2d');
function lake(c, src, wl, s, { dark = 0.4, amp = 1, blur = 1.2 } = {}) {
  mX.clearRect(0, 0, W, H);
  for (let y = Math.max(0, wl); y < H; y += 2) {
    const d = y - wl, from = wl - d - 1;
    if (from < 0) break;
    const dx = (Math.sin(d * 0.09 - s * 2.4) * (1 + d * 0.02) + (wob(d * 3.7, s * 1.5) - 0.5) * (1.5 + d * 0.05)) * amp;
    mX.drawImage(src, 0, from, W, 2, dx - 24, y, W + 48, 2);
  }
  c.save(); if (blur) c.filter = `blur(${blur}px)`; c.drawImage(MIRROR, 0, 0); c.restore();
  c.fillStyle = `rgba(6,10,26,${dark})`; c.fillRect(0, wl, W, H - wl);
}
// a light's broken streak on the water
function streak(c, x, y0, len, col, a, s, { seed = 0, width = 1 } = {}) {
  for (let k = 0, n = Math.ceil(len / 6); k < n; k++) {
    const f = k / n, y = y0 + k * 6 + wob(k + seed, s * 2) * 3, w = wob(k * 0.7 + seed, s * 1.6);
    const ww = (3 + 16 * w) * (1 - f * 0.8) * width, al = a * (1 - f) * clamp(w * 1.6 - 0.2);
    if (al > 0.01) { c.fillStyle = css(col, al); c.fillRect(x - ww / 2 + (wob(k + seed, 5 + s) - 0.5) * 10 * width, y, ww, 2); }
  }
}
const toScreen = (cam, d, x, y) => { const z = 1 + (cam.z - 1) * d; return [W / 2 + (x - W / 2 - cam.x * d) * z, H / 2 + (y - H / 2 - cam.y * d) * z, z]; };

const above = layer(W, H), aX = above.getContext('2d');
const lights = layer(W, H), lX = lights.getContext('2d');
const FOG = layer(480, 140);
{
  const n = noise(7), g = FOG.getContext('2d'), im = g.createImageData(480, 140);
  for (let y = 0; y < 140; y++) for (let x = 0; x < 480; x++) {
    const v = clamp((n.fbm(x / 60, y / 25, 5) - 0.35) * 2.2) * Math.sin(Math.PI * y / 140);
    const i = (y * 480 + x) * 4; im.data[i] = 200; im.data[i + 1] = 196; im.data[i + 2] = 222; im.data[i + 3] = 255 * v;
  }
  g.putImageData(im, 0, 0);
}
function ridgeColor(s, crestY, horizon, k) {
  const n = nightAt(s), behind = mix(mix(SKY.top[0], SKY.top[1], n), mix(SKY.low[0], SKY.low[1], n), clamp(1 - (horizon - crestY) / 1000));
  return css(mix(mix(behind, [0, 0, 0], 0.15), NEAR, k));
}

// ================= WIDE: the valley, his cabin and jetty on the near shore, the village across the lake
const WATER = 760;
const RIDGES = [0, 1, 2, 3].map((i) => ({
  depth: 0.15 + i * 0.22, k: 0.12 + i * 0.19,
  ys: ridge(40 + i, W + 400, { base: 560 + i * 50, amp: 240 - i * 40, scale: 0.0022 + i * 0.0009, oct: 5 }),
})).map((r) => ({ ...r, crest: Math.min(...r.ys) }));
const SHORE = ridge(77, W + 400, { base: WATER + 4, amp: 46, scale: 0.003, oct: 3 });
const CABIN = { x: 1180, y: 742 };
const JETTY = [[1236, 764], [1440, 852]];             // from the cabin toward us; the mooring post at its tip
const FLIES = Array.from({ length: 46 }, () => ({ x: 900 + R() * 900, y: 640 + R() * 140, ph: R() * 6.28, sp: 0.4 + R() * 0.8, rise: 40 + R() * 120 }));

function wide(s, m, cam, { flies = 0, mist = 0 } = {}) {
  const n = nightAt(s), lamp = lampAt(s);
  const wl = Math.round(H / 2 + (WATER - H / 2 - cam.y) * cam.z);
  aX.clearRect(0, 0, W, H);
  sky(aX, s, m, { horizon: wl, sx: -cam.x * 0.05, sy: -cam.y * 0.05, off: [0.24, 0.05] });   // the band rises from the far shore, so the lake can mirror it
  for (const f of SHOWER) if (s > f.t && s < f.t + 0.6) meteor(aX, (s - f.t) / 0.6, f.x, f.y, f.size);
  RIDGES.forEach((r, i) => view(aX, cam, r.depth, (c) => {
    fillRidge(c, r.ys, ridgeColor(s, r.crest, WATER, r.k), { dx: -200, bottom: WATER + 400 });
    if (i === 1 || i === 2) {
      c.globalAlpha = 0.16 + 0.12 * (1 - n);
      c.drawImage(FOG, -300 + ((s * (8 + i * 6)) % 400), 500 + i * 60, W + 800, 220);
      c.globalAlpha = 1;
    }
  }));
  view(aX, cam, 0.62, (c) => {
    for (const v of VILLAGE) { const a = litAt(v, s); if (a > 0) { c.fillStyle = css(LAMP, a * 0.95); c.fillRect(v.x, WATER - 14 - v.s * 10, 3, 3); } }
  });
  view(aX, cam, 1, (c) => {
    fillRidge(c, SHORE, css(NEAR), { dx: -200, bottom: WATER + 400 });
    c.fillStyle = css(NEAR);
    c.beginPath(); c.moveTo(CABIN.x - 70, WATER); c.lineTo(CABIN.x - 70, CABIN.y - 40); c.lineTo(CABIN.x, CABIN.y - 95);
    c.lineTo(CABIN.x + 70, CABIN.y - 40); c.lineTo(CABIN.x + 70, WATER); c.fill();
    c.fillRect(CABIN.x + 30, CABIN.y - 98, 12, 30);    // chimney
    c.fillStyle = lamp > 0.02 ? css(LAMP, lamp) : 'rgb(16,18,34)';
    c.fillRect(CABIN.x - 18, CABIN.y - 34, 30, 22);
  });

  lX.clearRect(0, 0, W, H);
  view(lX, cam, 1, (c) => glow(c, CABIN.x - 3, CABIN.y - 23, 80, LAMP, 0.45 * lamp * (1 + 0.3 * m.kick)));
  view(lX, cam, 0.62, (c) => {
    for (const v of VILLAGE) { const a = litAt(v, s); if (a > 0) glow(c, v.x + 1.5, WATER - 13 - v.s * 10, 16, LAMP, 0.5 * a); }
  });
  if (flies > 0) view(lX, cam, 1, (c) => {
    for (const f of FLIES) {
      const a = flies * (0.45 + 0.55 * Math.sin(s * 3 * f.sp + f.ph)) * (1 + 0.8 * m.snap);
      if (a <= 0.02) continue;
      const x = f.x + Math.sin(s * f.sp + f.ph) * 30, y = f.y - f.rise * flies + Math.cos(s * f.sp * 1.3 + f.ph) * 14;
      glow(c, x, y, 13, [255, 226, 140], Math.min(1, 0.7 * a));
    }
  });

  ctx.fillStyle = css(NEAR); ctx.fillRect(0, 0, W, H);
  ctx.drawImage(above, 0, 0);
  lake(ctx, above, wl, s, { dark: 0.3 + 0.22 * n });
  // the lamps' streaks on the water
  const [cx, cy] = toScreen(cam, 1, CABIN.x - 3, WATER);
  streak(ctx, cx, wl + 6, 230 * cam.z, LAMP, 0.5 * lamp, s, { seed: 1, width: cam.z });
  for (const v of VILLAGE) {
    const a = litAt(v, s); if (a <= 0) continue;
    const [vx] = toScreen(cam, 0.62, v.x + 1.5, 0);
    streak(ctx, vx, wl + 3, 34, LAMP, 0.35 * a, s, { seed: v.x, width: 0.25 });
  }
  // boats: hull, lantern, its streak
  for (const b of BOATS) {
    const k = boatK(b, s), la = lanternAt(b, s);
    if (s < b.t0 - 1) continue;
    const [x, y, z] = toScreen(cam, 0.8, lerp(1680 + 70 * b.i, 430 + 130 * b.i, k), lerp(WATER + 46 + 16 * b.i, WATER + 7, k));
    ctx.fillStyle = css(NEAR); ctx.fillRect(x - 13 * z, y - 3 * z, 26 * z, 4 * z); ctx.fillRect(x - 1, y - 16 * z, 1.5, 13 * z);
    if (la > 0) { ctx.fillStyle = css(LAMP, la); ctx.fillRect(x + 4 * z, y - 12 * z, 3, 3); streak(ctx, x + 5 * z, y + 2, 40, LAMP, 0.4 * la, s, { seed: 30 + b.i, width: 0.35 }); }
    if (la > 0) glow(lX, x + 5 * z, y - 11 * z, 18, LAMP, 0.5 * la);
  }
  // his jetty and the empty mooring post
  view(ctx, cam, 1, (c) => {
    const [a, b] = JETTY;
    c.fillStyle = css(NEAR);
    c.beginPath(); c.moveTo(a[0], a[1] - 2); c.lineTo(b[0] + 6, b[1] - 7); c.lineTo(b[0] + 3, b[1] + 6); c.lineTo(a[0] - 2, a[1] + 3); c.fill();
    for (let k = 0.12; k < 1; k += 0.2) c.fillRect(lerp(a[0], b[0], k) - 1.5, lerp(a[1], b[1], k), 3, 8 + k * 12);
    c.fillRect(b[0] - 3, b[1] - 36, 7, 46);
    if (lamp > 0.02) { c.strokeStyle = css(LAMP, 0.22 * lamp); c.lineWidth = 1.5; c.beginPath(); c.moveTo(a[0], a[1] - 2); c.lineTo(b[0] + 6, b[1] - 7); c.stroke(); }
  });
  if (mist > 0) view(ctx, cam, 0.9, (c) => {           // mist creeping over the water, left to right
    c.globalAlpha = 0.14 * mist;
    c.drawImage(FOG, -500 + ((s * 22) % 600), WATER - 40, W + 1000, 120);
    c.drawImage(FOG, -800 + ((s * 14 + 300) % 600), WATER + 10, W + 1200, 160);
    c.globalAlpha = 1;
  });
  bloom(ctx, lights, { base: 1, amount: 0.7 });
}

// ================= FAR SHORE: across the lake, the village close; boats come in to its jetty
const FWL = 700;                                      // waterline on screen
const FAR = [0, 1].map((i) => ({ depth: 0.15 + i * 0.25, k: 0.1 + i * 0.2, ys: ridge(140 + i, W + 400, { base: FWL - 60 + i * 30, amp: 280 - i * 110, scale: 0.0018 + i * 0.001, oct: 5 }) }))
  .map((r) => ({ ...r, crest: Math.min(...r.ys) }));
const BANK = ridge(150, W + 400, { base: FWL + 2, amp: 26, scale: 0.004, oct: 3 });
// the village in clusters along the shore: a back row set higher and paler, a front row, trees between, one tower
const HOUSES = (() => {
  const out = [], r = rng(21);
  for (const [cx, n] of [[150, 4], [560, 4], [960, 6], [1390, 4], [1760, 3]]) {
    let x = cx - n * 40;
    for (let j = 0; j < n; j++) {
      const back = r() < 0.4, w = 54 + r() * 76, h = 30 + r() * 50;
      out.push({ x: x + (back ? 16 : 0), w, h, back, roof: 16 + r() * 26, gable: r() > 0.25, chim: r() > 0.6, base: FWL - 4 - (back ? 16 + r() * 8 : r() * 5) });
      x += w * (0.75 + r() * 0.55);
    }
  }
  out.push({ x: 1010, w: 30, h: 120, back: true, roof: 64, gable: true, chim: false, base: FWL - 22 });
  out.sort((a, b) => b.back - a.back);
  const wins = [];
  for (const h of out) {
    const n = h.w > 100 ? 2 : h.h > 100 ? 1 : r() < 0.85 ? 1 : 0;
    h.wins = Array.from({ length: n }, (_, j) => ({ dx: (j + 0.5) / n * h.w - 6 + (r() - 0.5) * 10, dy: h.h * (0.35 + r() * 0.3) }));
    wins.push(...h.wins.map((wd) => ({ wd, x: h.x + wd.dx })));
  }
  wins.sort((p, q) => p.x - q.x).forEach((w, i) => { w.wd.v = BY_X[Math.floor(i * BY_X.length / wins.length)]; });
  return out;
})();
const TREES = [330, 780, 1220, 1590].flatMap((tx, i) => Array.from({ length: 6 }, () => ({ x: tx + (R() - 0.5) * 110, y: FWL - 18 - R() * 40, r: 16 + R() * 26, i })));
const REEDS = Array.from({ length: 64 }, (_, i) => {
  const left = i < 34;
  return { x: left ? -40 + R() * 360 : 1620 + R() * 340, h: 140 + R() * 300, bend: (R() - 0.5) * 90, ph: R() * 6.28, w: 4 + R() * 6 };
});
function farShore(s, m, k) {
  const cam = { x: lerp(60, -60, k), y: 0, z: 1 };
  aX.clearRect(0, 0, W, H);
  sky(aX, s, m, { horizon: FWL, sx: -cam.x * 0.05, off: [0.2, -0.3], sunX: 1500 });
  FAR.forEach((r) => view(aX, cam, r.depth, (c) => fillRidge(c, r.ys, ridgeColor(s, r.crest, FWL, r.k), { dx: -200, bottom: FWL + 400 })));
  const n = nightAt(s), haze = mix(SKY.low[0], SKY.low[1], n);
  const frontCol = css(mix(NEAR, haze, 0.08)), backCol = css(mix(NEAR, haze, 0.2));
  lX.clearRect(0, 0, W, H);
  const house = (c, h, col) => {
    const top = h.base - h.h;
    c.fillStyle = col;
    c.fillRect(h.x, top, h.w, h.h + 14);
    c.beginPath();
    if (h.gable) { c.moveTo(h.x - 6, top); c.lineTo(h.x + h.w / 2, top - h.roof); c.lineTo(h.x + h.w + 6, top); }
    else { c.moveTo(h.x - 5, top); c.lineTo(h.x - 5, top - h.roof * 0.55); c.lineTo(h.x + h.w + 5, top - 3); }
    c.fill();
    if (h.chim) c.fillRect(h.x + h.w * 0.7, top - h.roof * 0.85, 9, h.roof * 0.6);
    for (const wdw of h.wins) {
      const a = litAt(wdw.v, s), x = h.x + wdw.dx, y = h.base - wdw.dy - 15;
      c.fillStyle = a > 0.02 ? css(mix([40, 30, 34], LAMP, a)) : css(mix(NEAR, haze, 0.1));
      c.fillRect(x, y, 12, 15);
      if (a > 0.02) { c.fillStyle = col; c.fillRect(x + 5, y, 2, 15); }
    }
  };
  view(aX, cam, 0.5, (c) => { c.globalAlpha = 0.22; c.drawImage(FOG, -300 + ((s * 10) % 400), FWL - 150, W + 800, 160); c.globalAlpha = 1; });
  view(aX, cam, 0.75, (c) => {
    for (const h of HOUSES) if (h.back) house(c, h, backCol);
    c.fillStyle = css(mix(NEAR, haze, 0.24));                // trees between the clusters, then the bank
    for (const t of TREES) { c.beginPath(); c.arc(t.x, t.y, t.r, 0, 6.29); c.fill(); }
    fillRidge(c, BANK, frontCol, { dx: -200, bottom: FWL + 400 });
    for (const h of HOUSES) if (!h.back) house(c, h, frontCol);
  });
  view(lX, cam, 0.75, (c) => { for (const h of HOUSES) for (const wdw of h.wins) { const a = litAt(wdw.v, s); if (a > 0) glow(c, h.x + wdw.dx + 6, h.base - wdw.dy - 8, 30, LAMP, 0.32 * a); } });

  ctx.fillStyle = css(NEAR); ctx.fillRect(0, 0, W, H);
  ctx.drawImage(above, 0, 0);
  lake(ctx, above, FWL, s, { dark: 0.32, amp: 1.3 });
  for (const h of HOUSES) for (const wdw of h.wins) {
    const a = litAt(wdw.v, s); if (a <= 0) continue;
    const [x] = toScreen(cam, 0.75, h.x + wdw.dx + 6, 0);
    streak(ctx, x, FWL + (FWL - (h.base - wdw.dy - 8)) - 8, 90, LAMP, 0.38 * a, s, { seed: x, width: 0.6 });
  }
  // the jetty and the boats
  view(ctx, cam, 1, (c) => {
    c.fillStyle = css(mix(NEAR, [40, 44, 74], 0.15));
    c.fillRect(720, FWL + 14, 520, 8);
    for (let x = 740; x < 1240; x += 64) c.fillRect(x, FWL + 14, 6, 26);
  });
  for (const b of BOATS) {
    const q = boatK(b, s), la = lanternAt(b, s);
    if (s < b.t0 - 1) continue;
    const sc = lerp(1.6, 0.72, q), bob = Math.sin(s * 1.6 + b.i * 2) * 2.5 * sc;
    const [x, y] = toScreen(cam, lerp(1.4, 1, q), lerp(W + 160 + 170 * b.i, 800 + 150 * b.i, q), lerp(960 + 50 * b.i, FWL + 34, q) + bob);
    const moving = clamp(1 - q) * clamp(q * 8);
    if (moving > 0.02) {                             // the wake: two lines opening behind the boat
      ctx.strokeStyle = `rgba(150,160,210,${0.16 * moving})`; ctx.lineWidth = 2 * sc;
      ctx.beginPath(); ctx.moveTo(x + 60 * sc, y + 4 * sc); ctx.lineTo(x + 300 * sc, y - 18 * sc);
      ctx.moveTo(x + 60 * sc, y + 6 * sc); ctx.lineTo(x + 300 * sc, y + 34 * sc); ctx.stroke();
    }
    ctx.fillStyle = css(NEAR);
    ctx.beginPath(); ctx.moveTo(x - 80 * sc, y - 14 * sc); ctx.quadraticCurveTo(x, y + 26 * sc, x + 80 * sc, y - 16 * sc);
    ctx.lineTo(x + 70 * sc, y - 6 * sc); ctx.lineTo(x - 72 * sc, y - 6 * sc); ctx.fill();
    ctx.fillRect(x - 2 * sc, y - 110 * sc, 3 * sc, 104 * sc);
    ctx.fillRect(x + 40 * sc, y - 46 * sc, 2 * sc, 36 * sc);
    if (la > 0) {
      ctx.fillStyle = css([255, 214, 150], la); ctx.fillRect(x + 36 * sc, y - 56 * sc, 10 * sc, 12 * sc);
      glow(lX, x + 41 * sc, y - 50 * sc, 70 * sc, LAMP, 0.6 * la * (1 + 0.25 * m.kick));
      streak(ctx, x + 41 * sc, y + 10 * sc, 90 * sc, LAMP, 0.4 * la, s, { seed: 50 + b.i, width: sc * 0.8 });
    }
  }
  bloom(ctx, lights, { base: 1, amount: 0.75 });
  // reeds in the foreground, out of focus, swaying
  ctx.save(); ctx.filter = 'blur(4px)'; ctx.strokeStyle = 'rgb(3,4,10)'; ctx.lineCap = 'round';
  for (const r of REEDS) {
    const x = r.x - cam.x * 1.5, sway = Math.sin(s * 0.9 + r.ph) * 10;
    ctx.lineWidth = r.w; ctx.beginPath(); ctx.moveTo(x, H + 10); ctx.quadraticCurveTo(x + r.bend * 0.3, H - r.h * 0.6, x + r.bend + sway, H - r.h); ctx.stroke();
  }
  ctx.restore();
}

// ================= PIER: on his jetty, looking along it to the empty post and the village across the water
const PH = 560, K = 520, VPX = 1000, PIER_END = 7;
const PLANKS = (() => { const out = [], r = rng(31); for (let d = 0.45; d < PIER_END; d += 0.33) out.push({ d, tone: r() }); return out; })();
const SPARKS = Array.from({ length: 220 }, () => ({ x: R() * W, y: PH + 12 + Math.pow(R(), 1.6) * (H - PH), ph: R() * 6.28, w: 6 + R() * 22 }));
const PFAR = [0, 1].map((i) => ({ k: 0.2 + i * 0.3, ys: ridge(240 + i, W + 400, { base: PH - 4, amp: 150 - i * 70, scale: 0.002 + i * 0.0012, oct: 5 }) })).map((r) => ({ ...r, crest: Math.min(...r.ys) }));
function pierShot(s, m, { walk = 0, flies = 0 }) {
  const lamp = lampAt(s), amt = mwAt(s);
  aX.clearRect(0, 0, W, H);
  sky(aX, s, m, { horizon: PH, off: [-0.13, -0.27], sunX: 420 });
  PFAR.forEach((r) => fillRidge(aX, r.ys, ridgeColor(s, r.crest, PH, r.k), { dx: -200, bottom: PH + 400 }));
  for (const v of VILLAGE) { const a = litAt(v, s); if (a > 0) { aX.fillStyle = css(LAMP, a); aX.fillRect(330 + (v.x - 250) * 1.1, PH - 5 - v.s * 4, 2, 2); } }
  ctx.fillStyle = css(NEAR); ctx.fillRect(0, 0, W, H);
  ctx.drawImage(above, 0, 0);
  lake(ctx, above, PH, s, { dark: 0.22, amp: 0.8 });
  lX.clearRect(0, 0, W, H);
  for (const v of VILLAGE) { const a = litAt(v, s); if (a > 0) { const x = 330 + (v.x - 250) * 1.1; streak(ctx, x, PH + 3, 140, LAMP, 0.35 * a, s, { seed: v.x, width: 0.3 }); glow(lX, x, PH - 4, 10, LAMP, 0.6 * a); } }
  // glints on the water: warm from his window behind us, cool from the sky once it is out
  for (const p of SPARKS) {
    const near = (p.y - PH) / (H - PH), f = 0.5 + 0.5 * Math.sin(s * 2.2 + p.ph + p.x * 0.01);
    const warm = lamp * near * 0.35 * f, cool = amt * 0.22 * f * (1 - near * 0.5);
    if (warm > 0.02) { ctx.fillStyle = css(LAMP, warm); ctx.fillRect(p.x, p.y, p.w * (0.4 + near), 1.5); }
    if (cool > 0.02) { ctx.fillStyle = `rgba(190,200,255,${cool})`; ctx.fillRect(p.x + 7, p.y + 3, p.w * 0.6, 1); }
  }
  // the jetty in perspective: y = PH + K * height / distance; planks at height 1, the water at 1.35
  const Y = (d, h = 1) => PH + K * h / d, X = (d, side) => VPX + side * 470 / d;
  const lit = (d) => clamp(lamp * 0.95 / (0.6 + d * 0.55)), cool = 0.3 * amt;
  const near = 0.5, end = PIER_END - walk;
  const quad = (pts, fill) => { ctx.fillStyle = fill; ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.fill(); };
  if (end > near) {
    for (const pd of [1.4, 2.8, 4.2, 5.6, PIER_END - 0.1]) for (const side of [-1, 1]) {      // piles into the water, and their reflections
      const d = pd - walk; if (d < near) continue;
      const x = X(d, side) - 22 / d, w = 44 / d;
      ctx.fillStyle = css(mix([8, 8, 14], [40, 32, 30], lit(d) * 0.4)); ctx.fillRect(x, Y(d, 1.1), w, K * 0.25 / d);
      ctx.fillStyle = 'rgba(4,5,12,0.55)';
      for (let q = 0; q < 6; q++) ctx.fillRect(x + (wob(q + pd * 7, s * 2) - 0.5) * 10 / d, Y(d, 1.35) + q * K * 0.05 / d, w, K * 0.045 / d);
    }
    quad([[X(near, -1), Y(near)], [X(end, -1), Y(end)], [X(end, 1), Y(end)], [X(near, 1), Y(near)]], 'rgb(5,5,10)');   // underside: the gaps read dark
    for (const side of [-1, 1]) {                    // side boards
      quad([[X(near, side), Y(near)], [X(end, side), Y(end)], [X(end, side), Y(end, 1.1)], [X(near, side), Y(near, 1.1)]],
        css(mix(mix([14, 12, 18], [64, 46, 34], lit(2) * 0.7), [40, 46, 80], cool)));
    }
  }
  for (const p of PLANKS) {
    const d1 = p.d + 0.29 - walk, a = Math.max(p.d - walk, near); if (d1 <= a) continue;
    let col = mix(mix([30, 26, 30], [44, 38, 40], p.tone), WOOD, lit(a) * 0.75);
    col = mix(col, [66, 76, 120], cool);
    const j = (p.tone - 0.5) * 30;                    // planks are not cut quite square
    quad([[X(a, -1) - j / a, Y(a)], [X(a, 1) + j / a, Y(a)], [X(d1, 1) + j / d1, Y(d1)], [X(d1, -1) - j / d1, Y(d1)]], css(col));
    const grain = css(mix(col, [0, 0, 0], 0.22));
    for (const g of [0.3, 0.55, 0.8]) {
      const dg = lerp(d1, a, g), y = Y(dg);
      ctx.fillStyle = grain; ctx.fillRect(X(dg, -1) + (p.tone * 200 * g % 60) / dg, y, (X(dg, 1) - X(dg, -1)) * (0.4 + 0.5 * ((p.tone * 7 + g) % 1)), Math.max(1, 2.4 / dg));
    }
    ctx.fillStyle = css(mix(col, [255, 226, 180], 0.1 + 0.25 * lit(a)));   // the near edge catches the light from the window behind us
    ctx.fillRect(X(a, -1) - j / a, Y(a) - Math.max(1, 5 / a), X(a, 1) - X(a, -1) + 2 * j / a, Math.max(1, 5 / a));
  }
  // the mooring post at the end, a rope looped on it and coiled at its foot; nothing tied to it
  const d = PIER_END - 0.25 - walk;
  if (d > 0.5) {
    const x = X(d, 0.82), top = Y(d, 0.1), foot = Y(d), w = 60 / d;
    const g = ctx.createLinearGradient(x - w / 2, 0, x + w / 2, 0);
    const side = mix(mix([22, 20, 24], WOOD, lit(d) * 0.6), [80, 90, 140], cool * 0.8);
    g.addColorStop(0, css(mix(side, NEAR, 0.6))); g.addColorStop(0.4, css(side)); g.addColorStop(1, css(NEAR));
    ctx.fillStyle = g; ctx.fillRect(x - w / 2, top, w, foot - top);
    ctx.fillStyle = css(mix(side, [255, 255, 255], 0.08)); ctx.beginPath(); ctx.ellipse(x, top, w / 2, w / 6, 0, 0, 6.29); ctx.fill();
    ctx.strokeStyle = css(mix([120, 104, 86], [150, 160, 200], cool), 0.9); ctx.lineWidth = 7 / d;
    for (let j = 0; j < 3; j++) { ctx.beginPath(); ctx.ellipse(x, top + (0.3 + j * 0.06) * (foot - top), w * 0.55, w * 0.16, 0, 0.1, Math.PI - 0.1); ctx.stroke(); }
    ctx.beginPath(); ctx.moveTo(x - w * 0.5, top + 0.36 * (foot - top));
    ctx.quadraticCurveTo(x - w * 1.6, top + 0.8 * (foot - top), x - w * 2.2, foot - 4 / d); ctx.stroke();
    for (let j = 0; j < 3; j++) { ctx.beginPath(); ctx.ellipse(x - w * 2.6, foot - (2 + j * 3) / d, w * (1.1 - j * 0.2), w * (0.28 - j * 0.05), 0, 0, 6.29); ctx.stroke(); }
  }
  if (flies > 0) for (const f of FLIES.slice(0, 16)) {
    const a = flies * (0.45 + 0.55 * Math.sin(s * 3 * f.sp + f.ph)) * (1 + 0.8 * m.snap);
    glow(lX, 900 + (f.x - 900) * 0.9 + Math.sin(s * f.sp + f.ph) * 60, 420 + (f.y - 640) * 2 + Math.cos(s * f.sp * 1.3 + f.ph) * 40, 22, [255, 226, 140], Math.min(1, 0.6 * a));
  }
  bloom(ctx, lights, { base: 1, amount: 0.7 });
}

// ================= WINDOW: his cabin from outside; the lamp on the sill; the lake and the village to the left
const WIN = { x: 1040, y: 280, w: 480, h: 500 };
const LAMPPOS = { x: 1300, y: 742 };
const BOARDS = Array.from({ length: 22 }, (_, i) => ({ x: 700 + i * 60, tone: R() }));
const WFAR = ridge(260, W + 400, { base: 600, amp: 170, scale: 0.0025, oct: 5 });
const MOTHS = Array.from({ length: 4 }, (_, i) => ({ r: 70 + i * 35, sp: 1.4 + i * 0.5, ph: i * 1.7, y: 560 + i * 30 }));
function push(c, cx, cy, z, fn) { c.save(); c.translate(cx, cy); c.scale(z, z); c.translate(-cx, -cy); fn(c); c.restore(); }
function windowShot(s, m, { z = 1, moths = 0 }) {
  const lamp = lampAt(s), amt = mwAt(s), n = nightAt(s);
  // outside on the left: the lake at night, small
  aX.clearRect(0, 0, W, H);
  sky(aX, s, m, { horizon: 610, off: [0.35, -0.2], sunX: 200 });
  fillRidge(aX, WFAR, ridgeColor(s, Math.min(...WFAR), 610, 0.35), { dx: -200, bottom: 1000 });
  for (const v of VILLAGE) { const a = litAt(v, s); if (a > 0) { aX.fillStyle = css(LAMP, a); aX.fillRect(70 + (v.x - 250) * 0.75, 604 - v.s * 4, 2, 2); } }
  ctx.fillStyle = css(NEAR); ctx.fillRect(0, 0, W, H);
  lX.clearRect(0, 0, W, H);
  push(ctx, 1280, 520, z, (c) => {
    c.drawImage(above, 0, 0);
    lake(c, above, 610, s, { dark: 0.3, amp: 0.6 });
    // the wall: boards, warm where the window light reaches, a little cool from the sky once it is out
    for (const b of BOARDS) {
      c.fillStyle = css(mix(mix([20, 16, 20], [34, 26, 28], b.tone), [36, 42, 70], amt * 0.35)); c.fillRect(b.x, 0, 60, H);
      c.fillStyle = 'rgba(0,0,0,0.5)'; c.fillRect(b.x, 0, 3, H);
    }
    c.fillStyle = css(NEAR); c.fillRect(690, 0, 34, H);                        // corner post
    c.beginPath(); c.moveTo(640, 0); c.lineTo(W, 0); c.lineTo(W, 60); c.lineTo(640, 130); c.fill();   // eave
    const spill = c.createRadialGradient(1280, 560, 60, 1280, 560, 760);
    spill.addColorStop(0, css(LAMP, 0.3 * lamp)); spill.addColorStop(1, css(LAMP, 0));
    c.save(); c.globalCompositeOperation = 'lighter'; c.fillStyle = spill; c.fillRect(700, 0, W - 700, H); c.restore();
    // inside the glass
    const { x, y, w, h } = WIN;
    const room = c.createLinearGradient(0, y, 0, y + h);
    room.addColorStop(0, css(mix([10, 12, 26], [92, 56, 34], lamp))); room.addColorStop(1, css(mix([14, 16, 32], [150, 92, 52], lamp)));
    c.fillStyle = room; c.fillRect(x, y, w, h);
    if (lamp < 0.98) {                                // dark glass shows a little of the sky
      c.save(); c.beginPath(); c.rect(x, y, w, h); c.clip();
      c.globalAlpha = (1 - lamp) * 0.5;
      for (let i = 0; i < 260; i++) { const st = STARS[i]; c.fillStyle = 'rgba(220,226,255,0.7)'; c.fillRect(x + ((st.x + 300) % w), y + ((st.y + 900) % h), 1.5, 1.5); }
      c.globalAlpha = 1; c.restore();
    }
    // curtain on the left pane, lit from behind
    c.fillStyle = css(mix([26, 22, 28], [196, 120, 74], lamp), 0.85);
    c.beginPath(); c.moveTo(x, y); c.lineTo(x + 150, y); c.bezierCurveTo(x + 110, y + 200, x + 70, y + 330, x + 40, y + h * 0.78); c.lineTo(x, y + h * 0.8); c.fill();
    // the lamp: base, glass chimney, flame
    const L = LAMPPOS;
    c.fillStyle = css(mix([30, 24, 26], [90, 60, 40], lamp));
    c.beginPath(); c.ellipse(L.x, L.y + 26, 38, 10, 0, 0, 6.29); c.fill();
    c.beginPath(); c.moveTo(L.x - 30, L.y + 26); c.quadraticCurveTo(L.x - 36, L.y - 4, L.x - 12, L.y - 12); c.lineTo(L.x + 12, L.y - 12); c.quadraticCurveTo(L.x + 36, L.y - 4, L.x + 30, L.y + 26); c.fill();
    c.fillStyle = `rgba(255,226,190,${0.12 + 0.18 * lamp})`;
    c.beginPath(); c.ellipse(L.x, L.y - 50, 22, 42, 0, 0, 6.29); c.fill();
    c.strokeStyle = `rgba(255,240,220,${0.15 + 0.35 * lamp})`; c.lineWidth = 2; c.stroke();
    if (lamp > 0.01) {
      const fl = 1 + 0.08 * Math.sin(s * 19) + 0.12 * m.kick;
      c.fillStyle = css([255, 214, 140], lamp);
      c.beginPath(); c.moveTo(L.x, L.y - 70 * fl * lamp); c.quadraticCurveTo(L.x + 9, L.y - 40, L.x, L.y - 30); c.quadraticCurveTo(L.x - 9, L.y - 40, L.x, L.y - 70 * fl * lamp); c.fill();
      c.fillStyle = css([255, 248, 230], lamp); c.beginPath(); c.ellipse(L.x, L.y - 40, 3, 7 * lamp, 0, 0, 6.29); c.fill();
    }
    // smoke after he blows it out
    const since = s - LAMP_OUT;
    if (since > 0.1 && since < 5) {
      c.save(); c.filter = 'blur(2px)'; c.lineWidth = 3; c.lineCap = 'round';
      for (let j = 0; j < 2; j++) {
        c.strokeStyle = `rgba(170,170,190,${0.45 * (1 - since / 5) * (j ? 0.5 : 1)})`;
        c.beginPath();
        for (let q = 0; q <= 40; q++) {
          const hh = q / 40 * Math.min(1, since / 1.6) * 330, px = L.x + Math.sin(hh * 0.03 + s * 1.3 + j) * hh * 0.12 + wob(hh * 0.02, s * 0.5 + j) * hh * 0.15;
          if (q) c.lineTo(px, L.y - 92 - hh); else c.moveTo(px, L.y - 92 - hh);
        }
        c.stroke();
      }
      c.restore();
    }
    // frame, mullions, sill and the pot on it
    c.fillStyle = css(mix([24, 20, 22], [70, 48, 34], lamp * 0.6));
    c.fillRect(x - 26, y - 26, w + 52, 26); c.fillRect(x - 26, y + h, w + 52, 24); c.fillRect(x - 26, y, 26, h); c.fillRect(x + w, y, 26, h);
    c.fillRect(x + w / 2 - 7, y, 14, h); c.fillRect(x, y + h / 2 - 7, w, 14);
    c.fillStyle = css(NEAR); c.fillRect(x - 46, y + h + 20, w + 92, 18);
    c.beginPath(); c.moveTo(x + w - 60, y + h + 20); c.lineTo(x + w - 54, y + h - 22); c.lineTo(x + w - 14, y + h - 22); c.lineTo(x + w - 8, y + h + 20); c.fill();
    for (let j = 0; j < 7; j++) { c.strokeStyle = css(NEAR); c.lineWidth = 4; c.beginPath(); c.moveTo(x + w - 34, y + h - 22); c.quadraticCurveTo(x + w - 34 + (j - 3) * 14, y + h - 70, x + w - 34 + (j - 3) * 24, y + h - 92 - (j % 3) * 18); c.stroke(); }
  });
  push(lX, 1280, 520, z, (c) => {
    glow(c, LAMPPOS.x, LAMPPOS.y - 46, 300, LAMP, 0.5 * lamp * (1 + 0.2 * m.kick));
    glow(c, LAMPPOS.x, LAMPPOS.y - 46, 50, [255, 236, 200], 0.8 * lamp);
    for (const v of VILLAGE) { const a = litAt(v, s); if (a > 0) glow(c, 71 + (v.x - 250) * 0.75, 603 - v.s * 4, 9, LAMP, 0.5 * a); }
    for (const mo of MOTHS) {
      const a = moths * lamp; if (a <= 0.02) continue;
      const ang = s * mo.sp + mo.ph, mx = LAMPPOS.x + Math.cos(ang) * mo.r, my = mo.y + Math.sin(ang * 1.7) * 40;
      glow(c, mx, my, 10, [255, 230, 190], 0.6 * a);
    }
  });
  bloom(ctx, lights, { base: 1, amount: 0.8 });
}

// a shooting star: q 0..1 along its flight, starting at (x, y), falling left
function meteor(c, q, x, y, size) {
  const hx = x - 900 * size * q, hy = y + 340 * size * q, tx = hx + 260 * size, ty = hy - 98 * size;
  const g = c.createLinearGradient(hx, hy, tx, ty);
  g.addColorStop(0, `rgba(255,250,235,${0.9 * (1 - q)})`); g.addColorStop(1, 'rgba(255,250,235,0)');
  c.strokeStyle = g; c.lineWidth = 2.5 * size; c.beginPath(); c.moveTo(hx, hy); c.lineTo(tx, ty); c.stroke();
  glow(c, hx, hy, 26 * size, [255, 245, 225], 0.8 * (1 - q));
}
// in the last chorus's wide shot, a shooting star on each strong high accent
const SHOWER = SONG.accents.high.filter(([t, v]) => t >= bar(16) && t < bar(18) - 0.6 && v > 0.3).map(([t], i) => ({ t, x: 900 + ((i * 397) % 900), y: 60 + ((i * 131) % 220), size: 0.5 + ((i * 7) % 5) / 10 }));

// ================= SKY: crane up from his roof into the sky as it fills with stars
const PINE = (() => { const pts = [], r = rng(41); for (let j = 0; j < 9; j++) pts.push({ y: j / 9, w: 30 + j * 26 + r() * 20 }); return pts; })();
function skyShot(s, m, k) {
  const up = ease.inOutSoft(k);
  sky(ctx, s, m, { horizon: 1250 + 380 * up, sy: 200 * up, off: [0.02, 0.02], sunX: 300 });
  // a meteor on the strongest high accent in the shot
  if (s > METEOR && s < METEOR + 0.7) meteor(ctx, (s - METEOR) / 0.7, 1500, 120 + 200 * up, 1);
  const dy = 560 * up, rim = 0.15 + 0.35 * mwAt(s);
  ctx.fillStyle = css(NEAR);
  ctx.beginPath(); ctx.moveTo(-20, H + 20); ctx.lineTo(-20, 900 + dy); ctx.lineTo(1150, 760 + dy); ctx.lineTo(1940, 870 + dy); ctx.lineTo(1940, H + 20); ctx.fill();
  ctx.fillRect(1290, 640 + dy, 74, 150);
  ctx.strokeStyle = `rgba(150,160,220,${rim})`; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(-20, 900 + dy); ctx.lineTo(1150, 760 + dy); ctx.lineTo(1940, 870 + dy); ctx.stroke();
  ctx.strokeRect(1290, 640 + dy, 74, 1);
  // the pine beside the cabin, nearer, so it slides out faster
  const py = 330 + 820 * up;
  ctx.fillStyle = css(NEAR);
  for (const p of PINE) { ctx.beginPath(); ctx.moveTo(210, py + p.y * 760 - 60); ctx.lineTo(210 - p.w, py + p.y * 760 + 60); ctx.lineTo(210 + p.w, py + p.y * 760 + 60); ctx.fill(); }
  ctx.fillRect(200, py + 700, 20, 400);
}
const METEOR = (() => {
  const hi = SONG.accents.high.filter(([t]) => t >= bar(14, 3) + 0.4 && t < bar(16) - 0.8).sort((p, q) => q[1] - p[1]);
  return hi.length ? hi[0][0] : bar(15);
})();

// ================= the shot list: every cut on a bar line or half bar; lengths follow the song's sections
const SHOTS = [
  // intro: dusk; he lights the lamp on the first downbeat
  { a: 0, b: bar(2), draw: (s, m, k) => wide(s, m, { x: lerp(-60, 10, ease.inOutSoft(k)), y: lerp(20, 0, k), z: lerp(1.02, 1.1, ease.inOutSoft(k)) }) },
  // verse: the village lights up and boats come home; his post stays empty
  { a: bar(2), b: bar(4), draw: (s, m, k) => farShore(s, m, k) },
  { a: bar(4), b: bar(5), draw: (s, m, k) => pierShot(s, m, { walk: lerp(0, 0.5, k) }) },
  { a: bar(5), b: bar(6), draw: (s, m, k) => windowShot(s, m, { z: lerp(1, 1.04, k) }) },
  // chorus: everything is lit, fireflies rise, the cuts get shorter
  { a: bar(6), b: bar(8), draw: (s, m, k) => wide(s, m, { x: lerp(20, 90, k), y: lerp(10, -50, ease.inOutSoft(k)), z: lerp(1.04, 1.12, k) }, { flies: clamp(k * 3) }) },
  { a: bar(8), b: bar(9), draw: (s, m, k) => farShore(s, m, 0.4 + 0.3 * k) },
  { a: bar(9), b: bar(9, 3), draw: (s, m, k) => pierShot(s, m, { walk: lerp(4.7, 4.85, k), flies: 1 }) },
  { a: bar(9, 3), b: bar(10), draw: (s, m, k) => windowShot(s, m, { z: lerp(1.12, 1.16, k), moths: 1 }) },
  // bridge: one long take; the village goes to bed window by window, his lamp is the last light
  { a: bar(10), b: bar(13, 3), draw: (s, m, k) => wide(s, m, { x: lerp(90, -60, k), y: lerp(-50, 20, k), z: lerp(1.3, 1.0, ease.inOutSoft(k)) }, { mist: 1 }) },
  // last chorus: he puts it out on the downbeat; the sky comes up
  { a: bar(13, 3), b: bar(14, 3), draw: (s, m, k) => windowShot(s, m, { z: lerp(1.0, 1.06, k) }) },
  { a: bar(14, 3), b: bar(16), draw: (s, m, k) => skyShot(s, m, k) },
  { a: bar(16), b: bar(18), draw: (s, m, k) => wide(s, m, { x: lerp(-40, 50, k), y: lerp(-60, -140, ease.inOutSoft(k)), z: lerp(1.0, 1.2, ease.inOutSoft(k)) }, { mist: 0.3 }) },
  // outro: down the jetty to the post, the Milky Way on the water
  { a: bar(18), b: DUR + 1, draw: (s, m, k) => pierShot(s, m, { walk: lerp(2.6, 5.5, 0.8 * ease.outSoft(k) + 0.2 * k) }) },
];

function seek(t) {
  const s = t;                                       // the film is the whole song: film time = song time
  const m = songAt(SONG, s);
  const shot = SHOTS.find((x) => s >= x.a && s < x.b) ?? SHOTS.at(-1);
  shot.draw(s, m, clamp((s - shot.a) / (Math.min(shot.b, DUR) - shot.a)));
  finish(ctx, Math.round(t * FPS), { vignette: 0.5, grain: 0.05 });
  const f0 = Math.min(SONG.sound[1] + 0.4, DUR - 1.5), fade = clamp((s - f0) / (DUR - f0));   // after the last note rings out
  if (fade > 0) { ctx.fillStyle = `rgba(0,0,0,${fade * fade})`; ctx.fillRect(0, 0, W, H); }
}

register({ duration: DUR, fps: FPS, width: W, height: H, seek, meta: { shots: SHOTS.map((x) => +x.a.toFixed(3)) } });
seek(0);
