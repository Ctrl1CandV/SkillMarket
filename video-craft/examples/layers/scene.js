// layers — 10 s of a valley at dusk, drawn only with code. A reference for what "finished" means in Canvas 2D:
// sky gradient, five ridges fading with distance, fog between them, one warm light that the whole frame answers
// to (window, its reflection, fireflies), a slow camera with parallax, bloom, vignette and grain.
import { register, kf, ease, rng, clamp, lerp } from '../../kit/kit.js';
import { layer, noise, bloom, glow, ridge, fillRidge, view, finish, mix, css } from '../../kit/draw.js';

const W = 1920, H = 1080, FPS = 30, DUR = 10;
const ctx = document.getElementById('cv').getContext('2d');
const above = layer(W, H), aX = above.getContext('2d');
const lights = layer(W, H), lX = lights.getContext('2d');
const WATER = 760;                                   // waterline in world units

// palette: dusk sky going to night, one warm lamp
const SKY = { top: [[18, 26, 58], [6, 9, 24]], low: [[226, 146, 120], [52, 50, 96]] };
const LAMP = [255, 190, 120];
const NEAR = [12, 14, 28];

// far ridges sit just darker than the sky behind them; each nearer one is darker and less tinted
const RIDGES = [0, 1, 2, 3].map((i) => ({
  depth: 0.15 + i * 0.22,                             // parallax depth
  ys: ridge(40 + i, W + 400, { base: 560 + i * 50, amp: 240 - i * 40, scale: 0.0022 + i * 0.0009, oct: 5 }),
  k: 0.12 + i * 0.19,                                 // how far from sky colour toward the near dark
})).map((r) => ({ ...r, crest: Math.min(...r.ys) }));   // highest point: the sky there is what it is seen against
// the near shore: low, so the cabin stands against the lit mid-distance instead of a black hill
const SHORE = ridge(77, W + 400, { base: WATER + 4, amp: 46, scale: 0.003, oct: 3 });

// fog texture once at low resolution; it is drawn stretched and drifting, so softness is fine
const FOG = layer(480, 140);
{
  const n = noise(7), g = FOG.getContext('2d'), im = g.createImageData(480, 140);
  for (let y = 0; y < 140; y++) for (let x = 0; x < 480; x++) {
    const v = clamp((n.fbm(x / 60, y / 25, 5) - 0.35) * 2.2) * Math.sin(Math.PI * y / 140);
    const i = (y * 480 + x) * 4; im.data[i] = 200; im.data[i + 1] = 196; im.data[i + 2] = 222; im.data[i + 3] = 255 * v;
  }
  g.putImageData(im, 0, 0);
}

const R = rng(3);
const STARS = Array.from({ length: 2600 }, () => ({ x: R() * (W + 400) - 200, y: R() * 560, b: Math.pow(R(), 5), tw: R() * 6.28 }));
const FLIES = Array.from({ length: 40 }, () => ({ x: 960 + R() * 520, y: 680 + R() * 60, ph: R() * 6.28, sp: 0.4 + R() * 0.8, on: 1.5 + R() * 5 }));
const CABIN = { x: 1180, y: 742 };
// a village across the lake switching its lamps on, one after another along the far shore
const VILLAGE = Array.from({ length: 22 }, (_, i) => { const x = 260 + i * 34 + R() * 20; return { x, on: 3.0 + i * 0.16 + R() * 0.25, s: 0.5 + R() * 0.6 }; });

function seek(t) {
  const night = ease.inOutSoft(clamp(t / DUR));
  const cam = { x: kf(t, [[0, -60], [DUR, 70, ease.inOutSoft]]), y: kf(t, [[0, 20], [DUR, -10, ease.inOutSoft]]), z: kf(t, [[0, 1.0], [DUR, 1.12, ease.inOutSoft]]) };
  const lamp = clamp((t - 1.2) / 0.25) * (0.92 + 0.08 * Math.sin(t * 23) * Math.sin(t * 7));

  // ---- everything above the water, drawn once, then mirrored into the lake
  aX.clearRect(0, 0, W, H);
  const sky = aX.createLinearGradient(0, 0, 0, WATER);
  sky.addColorStop(0, css(mix(SKY.top[0], SKY.top[1], night)));
  sky.addColorStop(1, css(mix(SKY.low[0], SKY.low[1], night)));
  aX.fillStyle = sky; aX.fillRect(0, 0, W, H);
  view(aX, cam, 0.05, (c) => {
    for (const s of STARS) {
      const a = clamp((night - 0.25 - (1 - s.b) * 0.4) * 3) * (0.6 + 0.4 * Math.sin(t * 2 + s.tw));
      if (a > 0.01) { c.fillStyle = `rgba(235,238,255,${a * (0.25 + s.b)})`; c.fillRect(s.x, s.y, 1 + s.b * 2, 1 + s.b * 2); }
    }
  });
  // where the sun went down: a warm bloom low on the left, fading with the dusk
  const sun = aX.createRadialGradient(380, WATER - 60, 0, 380, WATER - 60, 900);
  sun.addColorStop(0, `rgba(255,170,120,${0.35 * (1 - night)})`); sun.addColorStop(1, 'rgba(255,170,120,0)');
  aX.fillStyle = sun; aX.fillRect(0, 0, W, WATER);
  const skyTop = mix(SKY.top[0], SKY.top[1], night), skyLow = mix(SKY.low[0], SKY.low[1], night);
  RIDGES.forEach((r, i) => {
    // colour from the sky just above the crest, darkened: a far ridge must never be brighter than the sky behind it
    const behind = mix(skyTop, skyLow, clamp(r.crest / WATER));
    view(aX, cam, r.depth, (c) => {
      fillRidge(c, r.ys, css(mix(mix(behind, [0, 0, 0], 0.15), NEAR, r.k)), { dx: -200, bottom: WATER + 400 });
      if (i === 1 || i === 2) {                       // fog sits between ridges and drifts
        c.globalAlpha = 0.16 + 0.12 * (1 - night);
        c.drawImage(FOG, -300 + ((t * (8 + i * 6)) % 400), 500 + i * 60, W + 800, 220);
        c.globalAlpha = 1;
      }
    });
  });
  view(aX, cam, 0.62, (c) => {                         // the village sits on the far shore's waterline
    for (const v of VILLAGE) {
      const a = clamp((t - v.on) / 0.12) * (0.85 + 0.15 * Math.sin(t * 5 + v.x));
      if (a > 0) { c.fillStyle = css(LAMP, a); c.fillRect(v.x, WATER - 14 - v.s * 10, 3, 3); }
    }
  });
  // cabin silhouette on the near shore, window lit
  view(aX, cam, 1, (c) => {
    fillRidge(c, SHORE, css(NEAR), { dx: -200, bottom: WATER + 400 });
    c.fillStyle = css(NEAR);
    c.beginPath(); c.moveTo(CABIN.x - 70, WATER); c.lineTo(CABIN.x - 70, CABIN.y - 40); c.lineTo(CABIN.x, CABIN.y - 95);
    c.lineTo(CABIN.x + 70, CABIN.y - 40); c.lineTo(CABIN.x + 70, WATER); c.fill();
    c.fillStyle = css(LAMP, lamp); c.fillRect(CABIN.x - 18, CABIN.y - 34, 30, 22);
  });

  // ---- light layer (added on top with bloom): window, lantern path, fireflies
  lX.clearRect(0, 0, W, H);
  view(lX, cam, 1, (c) => {
    glow(c, CABIN.x - 3, CABIN.y - 23, 70, LAMP, 0.4 * lamp);
    });
  view(lX, cam, 0.62, (c) => {
    for (const v of VILLAGE) { const a = clamp((t - v.on) / 0.12); if (a > 0) glow(c, v.x + 1.5, WATER - 13 - v.s * 10, 16, LAMP, 0.5 * a); }
  });
  view(lX, cam, 1, (c) => {
    for (const f of FLIES) {
      const a = clamp((t - f.on) / 0.6) * (0.5 + 0.5 * Math.sin(t * 3 * f.sp + f.ph));
      if (a <= 0) continue;
      const x = f.x + Math.sin(t * f.sp + f.ph) * 30, y = f.y + Math.cos(t * f.sp * 1.3 + f.ph) * 14;
      glow(c, x, y, 14, [255, 226, 140], 0.7 * a);
    }
  });

  // ---- compose: sky and land, lake as a rippled mirror, lights with bloom, then finish
  ctx.fillStyle = css(NEAR); ctx.fillRect(0, 0, W, H);
  ctx.drawImage(above, 0, 0);
  const wl = Math.round(H / 2 + (WATER - H / 2 - cam.y) * cam.z);  // waterline on screen
  for (let y = wl; y < H; y += 2) {
    const d = y - wl, src = wl - d - 1;
    if (src < 0) break;
    const dx = Math.sin(d * 0.09 - t * 2.4) * (1 + d * 0.025);
    ctx.drawImage(above, 0, src, W, 2, dx - 24, y, W + 48, 2);
  }
  ctx.fillStyle = `rgba(8,12,28,${0.35 + 0.25 * night})`; ctx.fillRect(0, wl, W, H - wl);
  bloom(ctx, lights, { base: 1, amount: 0.7 });
  // the window's reflection: a broken vertical streak in the water
  const rx = W / 2 + (CABIN.x - 3 - W / 2 - cam.x) * cam.z;
  const wob = noise(11);
  for (let k = 0; k < 40; k++) {
    const y = wl + 6 + k * 6 + wob(k, t * 2) * 4, n = wob(k * 0.7, t * 1.6);
    const w = (6 + 26 * n) * (1 - k / 48), a = 0.45 * lamp * (1 - k / 40) * clamp(n * 1.6 - 0.2);
    if (a > 0) { ctx.fillStyle = css(LAMP, a); ctx.fillRect(rx - w / 2 + (wob(k, 5 + t) - 0.5) * 14 * cam.z, y, w, 2); }
  }
  finish(ctx, Math.round(t * FPS), { vignette: 0.55, grain: 0.06 });
}

register({ duration: DUR, fps: FPS, width: W, height: H, seek });
seek(0);
