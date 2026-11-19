import { clamp, ease, kf, lerp, mixHex, register, rng, seg } from '../../kit/kit.js';
import { DURATION, EVENTS, MELODY, PHRASES } from './phrases.js';

const W = 1080;
const H = 1920;
const FPS = 30;
const TAU = 2 * Math.PI;
const ctx = document.getElementById('film').getContext('2d', { alpha: false });
const [, lift, below, reprise] = PHRASES;
const { dip, pull, lift: liftBlade, wake } = Object.fromEntries(
  EVENTS.filter((event) => event.gesture).map(({ gesture, t }) => [gesture, t]),
);

const random = rng(841);
const points = (count, make) => Array.from({ length: count }, (_, i) => make(random, i));
const motes = points(135, (r) => [r(), r(), r(), r()]);
const streaks = points(240, (r) => [r(), r(), r(), r()]);
const abrasions = points(1200, (r) => [r() * 2 - 1, r() * 2 - 1, r(), r()]);

const grainCanvas = document.createElement('canvas');
grainCanvas.width = grainCanvas.height = 320;
const grainContext = grainCanvas.getContext('2d');
const pixels = grainContext.createImageData(320, 320);
for (let i = 0; i < pixels.data.length; i += 4) {
  const shade = Math.round(random() * 255);
  pixels.data[i] = pixels.data[i + 1] = pixels.data[i + 2] = shade;
  pixels.data[i + 3] = 255;
}
grainContext.putImageData(pixels, 0, 0);
const grain = ctx.createPattern(grainCanvas, 'repeat');

function vertical(top, bottom, stops) {
  const gradient = ctx.createLinearGradient(0, top, 0, bottom);
  for (const [offset, color] of stops) gradient.addColorStop(offset, color);
  return gradient;
}

function circle(x, y, radius) {
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, TAU);
}

function bloom(x, y, radius, color) {
  const glow = ctx.createRadialGradient(x, y, 0, x, y, radius);
  glow.addColorStop(0, color);
  glow.addColorStop(1, 'transparent');
  ctx.fillStyle = glow;
  ctx.fillRect(x - radius, y - radius, 2 * radius, 2 * radius);
}

function drawDisk(x, y, radius, light, submerged) {
  bloom(x, y, radius * 2.25, submerged ? '#e9916728' : '#f5876166');
  ctx.save();
  circle(x, y, radius);
  ctx.clip();
  ctx.fillStyle = vertical(y - radius, y + radius, [
    [0, mixHex('#fdd8a4', '#ffe1b5', light)],
    [0.55, mixHex('#e78568', '#ffae70', light)],
    [1, mixHex('#a93849', '#bc5145', light)],
  ]);
  ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
  for (const [dx, dy, size, shade] of abrasions) {
    ctx.fillStyle = shade < 0.58 ? '#67224417' : '#fff9db37';
    ctx.fillRect(x + dx * radius, y + dy * radius, 1 + 10 * size, 0.8 + 2.4 * shade);
  }
  ctx.fillStyle = vertical(y - radius, y + radius, [
    [0, 'transparent'], [0.62, 'transparent'], [0.94, '#58314a45'], [1, '#321e3e58'],
  ]);
  ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
  ctx.restore();
  circle(x, y, radius - 0.8);
  ctx.lineWidth = 2;
  ctx.strokeStyle = '#ffddad84';
  ctx.stroke();
}

function relief(x, phase) {
  return 0.55 * Math.sin(x * 0.0047 + phase)
    + 0.22 * Math.sin(x * 0.012 + phase * 2.6)
    + 0.13 * Math.sin(x * 0.031 + phase * 3.2)
    + 0.05 * Math.sin(x * 0.094 - phase)
    + 0.018 * Math.sin(x * 0.197 + phase);
}

function ridge(horizon, t, phase, depth, light) {
  const offset = phase * 400 - t * (3.2 + depth * 3.7);
  const silhouette = (x) => {
    const valley = Math.exp(-(((x - 540 - t * 2) / (290 - depth * 80)) ** 2));
    const profile = relief(x + offset, phase) * (0.68 - 0.5 * valley);
    return horizon - (120 + depth * 210) * (0.08 + profile + (1 - valley) * 0.61);
  };
  ctx.beginPath();
  ctx.moveTo(-5, horizon + 3);
  for (let x = -5; x <= W + 5; x += 5) ctx.lineTo(x, Math.min(horizon, silhouette(x)));
  ctx.lineTo(W + 5, horizon + 3);
  ctx.closePath();
  ctx.fillStyle = vertical(horizon - 280, horizon + 5, [
    [0, mixHex('#504159', '#b66e60', light)],
    [1, mixHex('#161b29', '#322639', light)],
  ]);
  ctx.fill();
  ctx.strokeStyle = mixHex('#664d59', '#df8b66', light);
  ctx.lineWidth = 1.5;
  ctx.globalAlpha = 0.36 - depth * 0.3;
  ctx.stroke();
  ctx.globalAlpha = 1;
}

function water(t, horizon, disk, light, energy) {
  ctx.fillStyle = vertical(horizon, H, [
    [0, mixHex('#3e343f', '#885a4a', light)],
    [0.34, mixHex('#242739', '#513a46', light)],
    [1, mixHex('#0a1523', '#171e2b', light)],
  ]);
  ctx.fillRect(0, horizon, W, H - horizon);

  ctx.save();
  ctx.beginPath();
  ctx.rect(0, horizon, W, H - horizon);
  ctx.clip();
  ctx.globalAlpha = 0.32 + light * 0.25;
  bloom(disk.x, horizon + 208, 598, mixHex('#c25962', '#ee9754', light));
  const reflection = vertical(horizon, H, [[0, '#ffcf9ebd'], [0.48, '#ef9f7280'], [1, '#be565625']]);
  for (const [s, wall, shape, flare] of streaks) {
    const p = (s * 0.88 + t * (0.016 + wall * 0.007)) % 1;
    const y = horizon + p ** 1.8 * (H - horizon);
    const x = wall * W + Math.sin(t * 1.3 + s * 80) * (3 + p * 20);
    const drift = Math.sin(y * 0.031 + t * 1.8) * (6 + p * 44);
    const distance = (x - disk.x - drift) / (38 + p * 172);
    const nearDisk = Math.exp(-(distance ** 2));
    const width = 8 + shape * (30 + p * 168);
    ctx.globalAlpha = nearDisk * (0.65 + 0.25 * energy) + 0.12;
    ctx.fillStyle = nearDisk > 0.26 ? reflection : '#85768855';
    ctx.fillRect(x - width / 2, y, width, 1 + flare * (1.2 + p * 4.8));
  }
  ctx.restore();
}

function drawSkiff(x, y, scale, t, overhead) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(scale, scale);
  const swell = Math.sin(t * 1.7) * 0.022;
  ctx.rotate(overhead ? -0.65 + swell : swell);

  ctx.lineWidth = overhead ? 2.8 : 1.8;
  for (const direction of [-1, 1]) {
    const wake = ctx.createLinearGradient(-215, 0, -20, 0);
    wake.addColorStop(0, '#f4be9700');
    wake.addColorStop(1, overhead ? '#a7cab590' : '#dba78e91');
    ctx.strokeStyle = wake;
    ctx.beginPath();
    ctx.moveTo(-26, overhead ? direction * 7 : 7);
    ctx.quadraticCurveTo(-92, 12 + direction * 10, -217, 18 + direction * 19);
    ctx.stroke();
  }

  ctx.beginPath();
  ctx.moveTo(-83, -8);
  ctx.quadraticCurveTo(-2, overhead ? -20 : 3, 87, -12);
  ctx.quadraticCurveTo(68, 16, 23, 18);
  ctx.quadraticCurveTo(-52, 19, -71, 10);
  ctx.closePath();
  ctx.fillStyle = '#10141e';
  ctx.fill();
  ctx.strokeStyle = '#d5a28594';
  ctx.lineWidth = 1.4;
  ctx.stroke();
  if (!overhead) {
    ctx.fillStyle = '#141722';
    ctx.beginPath();
    ctx.moveTo(-23, 0);
    ctx.quadraticCurveTo(-21, -26, -10, -30);
    ctx.quadraticCurveTo(3, -29, 10, -12);
    ctx.lineTo(27, -1);
    ctx.closePath();
    ctx.fill();
    circle(-10, -36, 7.5);
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(3, -20);
    ctx.lineTo(47, 17 + Math.sin(t * 2.1) * 4);
    ctx.strokeStyle = '#2b212a';
    ctx.lineWidth = 3.3;
    ctx.stroke();
  }
  ctx.restore();
}

function landscape(t, returned, energy) {
  const opening = seg(t, 0, lift.t, ease.inOutSoft);
  const rising = seg(t, reprise.t, 4.1, ease.inOutSoft);
  const light = returned ? 0.49 + 0.46 * rising : 0.18 + opening * 0.1;
  const horizon = returned ? lerp(1090, 1150, rising) : lerp(1120, 1040, opening);
  const disk = returned
    ? { x: lerp(540, 581, rising), y: lerp(860, 670, rising), radius: lerp(206, 223, rising) }
    : { x: lerp(620, 578, opening), y: lerp(675, 645, opening), radius: lerp(219, 205, opening) };

  ctx.fillStyle = vertical(0, horizon, [
    [0, mixHex('#141729', '#443141', light)],
    [0.53, mixHex('#412f49', '#a15b60', light)],
    [1, mixHex('#b06b68', '#f6ab7b', light)],
  ]);
  ctx.fillRect(0, 0, W, horizon + 3);
  bloom(disk.x - 38, disk.y + 190, 750, '#eb827e44');
  ctx.fillStyle = '#ffe1c3';
  for (const [x, y, phase, size] of motes) {
    if (phase < light * 0.7) continue;
    ctx.globalAlpha = (1 - y) * size * 0.68;
    const drift = (x * W + t * (size * 1.4 + 1.8)) % W;
    ctx.fillRect(drift, y * (horizon - 160), 1 + 2 * phase, 1 + 1.4 * phase);
  }
  ctx.globalAlpha = 1;
  drawDisk(disk.x, disk.y, disk.radius, light, false);

  for (const [cx, cy, width, seed] of [[0.06, 0.42, 0.37, 1], [0.64, 0.71, 0.28, 3], [-0.05, 0.83, 0.48, 7]]) {
    const x = W * cx + t * (2 + seed / 3);
    const y = horizon * cy + 7 * Math.sin(t * 0.21 + seed);
    const span = W * width;
    const mist = ctx.createLinearGradient(x, y, x + span, y);
    mist.addColorStop(0, '#f5ae9b00');
    mist.addColorStop(0.45, '#f5ae9b59');
    mist.addColorStop(1, '#f5ae9b00');
    ctx.fillStyle = mist;
    for (let line = 0; line < 13; line++) {
      const f = line / 13;
      ctx.globalAlpha = Math.sin(f * Math.PI) * (0.19 + light * 0.13);
      ctx.fillRect(x + (relief(line * 30, seed) + f) * 78, y + line * 3.8, span * (1 - f * 0.45), 1.4 + f * 3);
    }
  }
  ctx.globalAlpha = 1;
  ridge(horizon, t, 1.3, 0.35, light);
  ridge(horizon, t, 3.77, 0.79, light * 0.7);
  water(t, horizon, disk, light, energy);
  if (returned) {
    drawSkiff(638 + 91 * (t - reprise.t), lerp(1320, 1240, rising), lerp(0.69, 0.32, rising), t, false);
    const finalRipple = seg(t, wake, DURATION - wake, ease.outSoft);
    if (finalRipple > 0) {
      ctx.save();
      ctx.globalAlpha = seg(t, wake, 0.12) * (1 - seg(t, wake + 0.32, DURATION - wake - 0.32));
      waterArc(757, 1288 + finalRipple * 25, 92 + 148 * finalRipple, 12 + finalRipple * 12, '#ffd4a1c2', 5, Math.PI * 0.13, Math.PI * 0.87);
      waterArc(757, 1298 + finalRipple * 21, 59 + 126 * finalRipple, 9 + finalRipple * 8, '#ffd4a182', 3, Math.PI * 0.14, Math.PI * 0.86);
      ctx.restore();
    }
  } else drawSkiff(238 + 58 * t, lerp(1480, 1335, t / lift.t), lerp(1.06, 0.66, t / lift.t), t, false);
}

function waterArc(x, y, radius, depth, color, width, from, to) {
  ctx.beginPath();
  ctx.ellipse(x, y, radius, depth, 0, from, to);
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.stroke();
}

function paddle(t) {
  const x = kf(t, [[lift.t, 875], [dip, 676, ease.in], [pull, 579, ease.outSoft], [liftBlade - 0.56, 333], [liftBlade + 0.69, 165, ease.in]]);
  const y = kf(t, [[lift.t, 770], [dip, 1114, ease.in], [pull, 1189, ease.out], [liftBlade - 0.48, 1230], [liftBlade, 1118], [liftBlade + 0.69, 410, ease.in]]);
  const turn = kf(t, [[lift.t, -0.57], [dip, -0.47], [pull, -0.74], [liftBlade - 0.58, -1.02], [liftBlade + 0.69, -1.15]]);
  const clear = seg(t, liftBlade, 0.85, ease.in);
  ctx.save();
  ctx.globalAlpha = 1 - clear;
  ctx.translate(x, y);
  ctx.rotate(turn);
  ctx.beginPath();
  ctx.moveTo(-17, -1600);
  ctx.lineTo(20, -1600);
  ctx.bezierCurveTo(18, -940, 12, -358, 26, -259);
  ctx.bezierCurveTo(39, -201, 68, -183, 73, -58);
  ctx.quadraticCurveTo(72, 0, 38, 5);
  ctx.quadraticCurveTo(0, 14, -48, -9);
  ctx.quadraticCurveTo(-73, -30, -68, -62);
  ctx.bezierCurveTo(-64, -171, -34, -204, -24, -261);
  ctx.closePath();
  const wood = ctx.createLinearGradient(-75, 0, 75, 0);
  wood.addColorStop(0, '#f9aa73');
  wood.addColorStop(0.14, '#ab593c');
  wood.addColorStop(0.42, '#633930');
  wood.addColorStop(0.72, '#361f25');
  wood.addColorStop(1, '#1b1722');
  ctx.fillStyle = wood;
  ctx.fill();
  ctx.clip();
  for (let i = 0; i < 12; i++) {
    const column = i * 12 - 67;
    ctx.beginPath();
    ctx.moveTo(column, -8);
    ctx.bezierCurveTo(column - 27, -144, column + 45, -208, column, -330);
    ctx.strokeStyle = i % 3 === 0 ? '#ffbc8e59' : '#250f2238';
    ctx.lineWidth = i % 3 === 0 ? 2 : 3;
    ctx.stroke();
  }
  ctx.restore();
}

function waterline(t, energy) {
  const tilt = seg(t, liftBlade + 0.4, below.t - liftBlade - 0.4, ease.inOutSoft);
  const x = lerp(586, 540, tilt);
  const y = lerp(1050, 600, tilt);
  const r = lerp(324, 152, tilt);
  const squeeze = lerp(0.36, 1, tilt);
  ctx.fillStyle = vertical(0, H, [
    [0, mixHex('#2a2439', '#091927', tilt)],
    [0.56, mixHex('#553541', '#163f49', tilt)],
    [1, mixHex('#101b2b', '#092331', tilt)],
  ]);
  ctx.fillRect(0, 0, W, H);
  bloom(x, y, 780, '#ce776944');
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(1, squeeze);
  drawDisk(0, 0, r, 0.12, true);
  ctx.restore();

  const impact = t >= dip ? Math.exp(-(t - dip) * 1.38) : 0;
  for (const [s, across, width, intensity] of streaks) {
    const sy = (s * 1.23 + t * 0.068) % 1;
    const lineY = sy * H;
    const gap = Math.abs(lineY - y) / (325 + tilt * 170);
    const lineX = across * W;
    const glint = clamp(1 - gap) * (1 - Math.abs(lineX - x) / W) * (0.7 + energy * 0.3);
    const reach = 10 + 280 * width * sy;
    ctx.globalAlpha = 0.08 + intensity * glint * (0.63 - 0.44 * tilt);
    ctx.fillStyle = intensity > 0.54 ? '#ffd1a7bf' : '#171b31bb';
    ctx.fillRect(lineX - reach / 2, lineY, reach, 0.6 + intensity * 3.3);
  }
  ctx.globalAlpha = 1;
  ctx.save();
  ctx.beginPath();
  ctx.ellipse(x, y, r, r * squeeze, 0, 0, TAU);
  ctx.clip();
  for (let row = 0; row < 22; row++) {
    const sy = (row / 22 + t * 0.063) % 1;
    const stripeY = y + (sy * 2 - 1) * r * squeeze;
    ctx.beginPath();
    ctx.moveTo(x - r - 5, stripeY);
    ctx.bezierCurveTo(x - 130, stripeY + 28 * impact, x + 140, stripeY - 18 - 92 * impact, x + r + 5, stripeY + 11);
    ctx.strokeStyle = row % 3 === 0 ? '#ffd5a478' : '#3d364d88';
    ctx.lineWidth = (row % 3 === 0 ? 2.5 : 3.4) + impact * (row % 5) * 10;
    ctx.stroke();
  }
  ctx.restore();

  paddle(t);
  if (t >= dip) {
    const age = t - dip;
    for (let n = 0; n < 7; n++) {
      const travel = clamp(age * 0.35 - n * 0.088);
      if (travel <= 0 || travel >= 1) continue;
      ctx.globalAlpha = (1 - tilt) * Math.sin(travel * Math.PI) ** 2;
      const origin = 676 - 48 * n;
      waterArc(origin, 1118 + n * 15, 24 + travel * 630, 10 + travel * 150, n % 2 ? '#f4af7ea6' : '#ffd9aaaf', n % 2 ? 3 : 5, -0.14, Math.PI * 1.13);
    }
    for (const [sx, sy, onset, size] of motes.slice(0, 27)) {
      const elapsed = age - onset * 0.18;
      if (elapsed <= 0 || elapsed >= 0.55) continue;
      ctx.globalAlpha = (1 - elapsed / 0.55) * 0.8;
      ctx.fillStyle = '#ffe2b7';
      circle(676 + (sx - 0.48) * elapsed * 450, 1118 - sy * 480 * elapsed + elapsed ** 2 * 730, 1.2 + size * 3.6);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }
}

function ripples(t, x, y, radius, energy) {
  const local = t - below.t;
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(-0.18 + 0.15 * local);
  for (let i = 0; i < 20; i++) {
    const travel = ((i + (i % 3) * 0.16) / 20 + local * 0.14) % 1;
    const distance = radius + 13 + 1120 * travel ** 1.55;
    ctx.beginPath();
    for (let p = 0; p <= 160; p++) {
      const angle = TAU * p / 160;
      const offset = 9 * Math.sin(angle * 3 + local * 1.3 + i * 0.7) + 3 * Math.sin(angle * 11 - local * 2 + i);
      const px = Math.cos(angle) * (distance + offset);
      const py = Math.sin(angle) * (distance + offset) * (0.74 + travel * 0.09);
      if (p === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.globalAlpha = Math.sin(travel * Math.PI) * (i % 4 === 0 ? 0.49 : 0.21) * (0.68 + energy * 0.32);
    ctx.lineWidth = i % 4 === 0 ? 2.8 : 1.4;
    ctx.strokeStyle = i % 6 === 0 ? '#e9b68d' : '#77b6b0';
    ctx.stroke();
  }
  ctx.restore();
}

function overhead(t, energy) {
  const local = t - below.t;
  const turn = seg(t, below.t, reprise.t - below.t, ease.inOutSoft);
  const x = 540 - Math.sin(turn * Math.PI) * 110;
  const y = lerp(600, 860, turn);
  const radius = lerp(152, 206, turn);
  ctx.fillStyle = vertical(0, H, [[0, '#091927'], [0.56, '#163f49'], [1, '#092331']]);
  ctx.fillRect(0, 0, W, H);
  bloom(x, y, 1020, '#75c0ab42');
  ctx.save();
  ctx.translate(140 - local * 28, 980 + local * 53);
  ctx.rotate(-0.58);
  for (let n = 0; n < 5; n++) {
    ctx.beginPath();
    ctx.moveTo(-1390, 2200);
    for (let sy = 2200; sy >= -2200; sy -= 8) {
      const sx = -30 - n * 13 + 38 * relief(sy, 4 + n * 0.06) + 128 * Math.sin(sy * 0.0028);
      ctx.lineTo(sx, sy);
    }
    ctx.lineTo(-1390, -2200);
    ctx.closePath();
    ctx.fillStyle = ['#8eb7a94f', '#41686e', '#315762', '#233845', '#112537'][n];
    ctx.fill();
  }
  ctx.restore();
  ripples(t, x, y, radius, energy);
  drawDisk(x, y, radius, 0.12, true);
  ctx.save();
  circle(x, y, radius);
  ctx.clip();
  ctx.strokeStyle = '#3f6a735c';
  for (let i = 0; i < 25; i++) {
    const stripe = y - radius + 15 * i + 7 * Math.sin(t * 2.5 + i);
    ctx.lineWidth = 1 + (i % 5) * 0.8;
    ctx.beginPath();
    ctx.moveTo(x - radius, stripe + 26);
    ctx.quadraticCurveTo(x, stripe - 37 + 13 * Math.sin(t + i * 0.5), x + radius, stripe + 14);
    ctx.stroke();
  }
  ctx.restore();
  drawSkiff(610 + local * 22, 1130 - local * 66, 0.42, t, true);
}

function finish() {
  const vignette = ctx.createRadialGradient(540, 890, 460, 540, 950, 1170);
  vignette.addColorStop(0, '#060b1400');
  vignette.addColorStop(1, '#060b146e');
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, W, H);
  ctx.save();
  ctx.globalCompositeOperation = 'soft-light';
  // Fixed paper grain keeps moving gradients from crawling after compression.
  ctx.globalAlpha = 0.13;
  ctx.fillStyle = grain;
  ctx.fillRect(0, 0, W, H);
  ctx.restore();
}

function seek(t) {
  const energy = MELODY.reduce((peak, [at, , weight]) => (
    at <= t ? Math.max(peak, weight * Math.exp(-(t - at) * 6)) : peak
  ), 0);
  if (t < lift.t) landscape(t, false, energy);
  else if (t < below.t) waterline(t, energy);
  else if (t < reprise.t) overhead(t, energy);
  else landscape(t, true, energy);
  finish();
}

register({ width: W, height: H, fps: FPS, duration: DURATION, seek, meta: { events: EVENTS, phrases: PHRASES } });
seek(0);
