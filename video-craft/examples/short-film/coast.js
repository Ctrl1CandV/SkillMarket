import { clamp, lerp, rng, seg, ease } from '../../kit/kit.js';
import { time } from './timeline.js';
import { W, H, line, polygon, linear, light, rainfall, texture } from './paint.js';

const sky = texture(975, 680, 305, (x, y, cloud, grain) => {
  const color = (cloud - 0.55) * 101 + Math.sin(cloud * 7 + y * 18 - x * 2) * 5 + (grain - 0.5) * 5;
  const horizon = Math.max(0, 1 - Math.abs(y - 0.64) * 2.7);
  return [23 + color + horizon * 29, 38 + color + horizon * 37, 52 + color + horizon * 41, 255];
});

const mist = texture(843, 500, 130, (_, y, cloud) => [125, 157, 164, clamp((cloud - 0.45) * 168) * Math.sin(Math.PI * y) ** 3 * 90]);

const waves = (() => {
  const random = rng(2365);
  return Array.from({ length: 1380 }, () => [random(), random() ** 1.65, random(), random(), random()]);
})();

function skyAndWater(g, t, horizon, illumination = 0) {
  g.drawImage(sky, -36 + 16 * Math.sin(t * 0.065), -155 + horizon * 0.25, W + 70, horizon + 155);
  g.fillStyle = linear(g, 0, horizon, 0, H, [[0, '#314754'], [0.13, '#253e50'], [0.55, '#152e3c'], [1, '#091a25']]);
  g.fillRect(0, horizon, W, H - horizon);
  light(g, 900, horizon, 710, 110, [[0, '#92adb130'], [1, '#92adb100']]);
  g.drawImage(mist, -170 + t * 4.3, horizon - 107, W + 290, 159);

  for (const [u, z, phase, size, crest] of waves) {
    const y = horizon + z * (H - horizon + 5);
    const x = ((u * 1450 + t * (7 + z * 65) + 1450) % 1450) - 90;
    const roll = Math.sin(y * 0.218 + t * (2 + z) + x * 0.029 + phase * 5);
    const l = (4 + 73 * z) * (0.2 + size * 0.8);
    const glint = clamp((roll + 0.18) * 0.8, 0, 1) * crest;
    g.fillStyle = glint > 0.28 ? `rgba(123,169,177,${glint * (0.19 + z * 0.22)})` : `rgba(3,18,29,${(1 - glint) * (0.16 + z * 0.37)})`;
    g.fillRect(x, y + roll * (0.5 + 5 * z), l, 0.5 + z * (0.6 + size * 2.4));
    const warmth = illumination * glint * clamp(1 - Math.abs(x - 800) / 550);
    if (warmth > 0.03) {
      g.fillStyle = `rgba(238,187,120,${warmth * 0.48})`;
      g.fillRect(x, y + roll * (0.5 + 5 * z), l * 0.84, 0.7 + z * 1.5);
    }
  }

  g.drawImage(mist, -155 + t * 1.6, horizon + 17, W + 210, 96);
}

function landProfile(g, points, tone, seed) {
  const ridge = linear(g, 0, Math.min(...points.map(([, y]) => y)), 0, H, [[0, tone], [1, '#050e16']]);
  polygon(g, points, ridge);
  g.save();
  g.clip();
  const random = rng(seed);
  const strata = ['#2e4a5768', '#4d646943', '#151f2988', '#050c16aa'];
  for (let i = 0; i < 205; i++) {
    const x = random() * 545 - 55, y = random() * 300 + 245, size = 6 + random() * 73;
    polygon(g, [[x, y], [x + 3, y - size * 0.31], [x + size * 0.97, y - size * 0.58], [x + size * 0.71, y - size * 0.2], [x + size * 0.39, y + 4]], strata[i % strata.length]);
  }
  g.restore();
}

const farCliff = [[0, 349], [80, 343], [174, 344], [252, 351], [303, 345], [355, 354], [405, 371], [456, 374], [468, 383], [507, 393], [520, 407], [473, 416], [412, 410], [329, 430], [0, 491]];
const nearCliff = [[-35, 412], [35, 373], [105, 369], [146, 354], [186, 355], [213, 339], [253, 334], [267, 340], [314, 338], [340, 348], [368, 357], [394, 377], [392, 384], [414, 398], [398, 410], [442, 419], [481, 447], [445, 454], [406, 457], [350, 476], [244, 484], [169, 514], [86, 534], [-20, 546]];
const foregroundCliff = [[-25, 305], [56, 327], [78, 362], [129, 353], [180, 386], [192, 412], [238, 422], [253, 442], [297, 453], [339, 475], [330, 494], [392, 518], [432, 543], [381, 578], [-25, 580]];

const foam = (() => {
  const random = rng(932);
  return Array.from({ length: 410 }, () => [random(), random(), random(), random()]);
})();

function breakers(g, t, close) {
  for (const [u, v, step, size] of foam) {
    const surge = (1 + Math.sin(t * 2.15 - u * 10 + step * 2)) * 0.5;
    const x = (close ? 290 : 380) + u * (close ? 193 : 165) + (v - 0.5) * 68 + surge * 23;
    const y = (close ? 487 : 422) + u * (close ? 68 : 13) + (v - 0.5) * 38 + surge * 15;
    g.fillStyle = `rgba(136,181,191,${surge * size * size * (close ? 0.54 : 0.34)})`;
    g.fillRect(x, y, (1 + size * 8) * (close ? 1.6 : 1), 0.8 + size * 1.4);
  }
}

function lantern(g, on) {
  g.save();
  g.translate(283, 338);

  polygon(g, [[-79, 0], [-85, -20], [-85, -31], [-63, -58], [-39, -60], [-13, -39], [2, -32], [18, -31], [16, 4]], '#18252b', '#31404a');
  polygon(g, [[-91, -30], [-64, -62], [-41, -66], [-12, -38], [-7, -30], [-24, -34], [-40, -50], [-60, -51], [-80, -30]], '#101c24', '#42515a');
  g.fillStyle = '#5d6667'; g.fillRect(-69, -51, 6, 25); g.fillRect(-33, -48, 6, 24);
  g.fillStyle = '#28343a'; g.fillRect(-62, -30, 13, 10); g.fillRect(-38, -30, 12, 10);

  const tower = [[-27, 2], [-20, -44], [-12, -138], [19, -138], [22, -66], [31, 2]];
  polygon(g, tower, linear(g, -30, 0, 36, 0, [[0, '#0d1a23'], [0.29, '#3d4848'], [0.57, '#62625a'], [1, '#36444c']]), '#12232b');
  g.save(); g.clip();
  for (let row = 0; row < 18; row++) {
    const y = -row * 8.5;
    line(g, [[-30, y], [32, y - 1]], row % 3 ? '#23303865' : '#b3b3a137', 1);
    for (let col = 0; col < 3; col++) {
      const x = col * 23 - 32 + (row % 2) * 10;
      line(g, [[x, y], [x + 0.5, y - 8.5]], '#202d3570', 1);
    }
  }
  g.restore();
  g.fillStyle = '#10202a'; g.fillRect(7, -90, 5, 14); g.fillRect(1, -49, 6, 16);
  polygon(g, [[-26, -135], [30, -135], [29, -144], [-27, -144]], '#202f38', '#52616c');
  g.fillStyle = '#283e48'; g.fillRect(-17, -174, 42, 29);
  g.fillStyle = on ? '#f6cb84' : '#12232c'; g.fillRect(-13, -172, 34, 25);
  g.fillStyle = on ? '#fff0ce' : '#344955'; g.fillRect(-3, -172, 14, 25);
  for (const x of [-18, -6, 9, 22]) line(g, [[x, -176], [x, -144]], '#111e27', 2);
  line(g, [[-26, -157], [-26, -145], [32, -145], [32, -157]], '#678087', 1);
  for (let x = -26; x <= 32; x += 8) line(g, [[x, -154], [x, -144]], '#293a44', 1);
  polygon(g, [[-22, -176], [0, -195], [7, -196], [29, -176]], '#101f2a', '#405665');
  line(g, [[-22, -176], [2, -178], [31, -176]], '#657582', 1.5);
  line(g, [[5, -195], [5, -206]], '#192c37', 2);
  g.restore();

  if (on) {
    light(g, 287, 178, 53, 56, [[0, '#fff0cbee'], [0.15, '#ffcf8c74'], [0.59, '#eab16b20'], [1, '#eab16b00']]);
  }
}

function lighthouseBeam(g, t) {
  const yaw = 0.5 + 0.5 * Math.sin((t - time.wideShot) * 1.18 - 0.53);
  const strength = 0.23 + 0.77 * yaw;
  const x1 = 560 + 950 * yaw, y1 = 68 + 213 * yaw;
  g.save();
  g.globalCompositeOperation = 'screen';
  for (let i = 12; i >= 0; i--) {
    const size = 5 + i * 3.7 + yaw * 13;
    const fill = linear(g, 285, 178, x1, y1, [[0, `rgba(252,208,154,${0.073 * strength})`], [0.23, `rgba(231,191,138,${0.11 * strength})`], [0.66, `rgba(195,165,123,${0.052 * strength})`], [1, '#bf995400']]);
    polygon(g, [[288, 175 - i * 0.16], [x1, y1 - size], [x1, y1 + size], [288, 181 + i * 0.15]], fill);
  }
  g.restore();
}

function cabinWindow(g, x, y, size, strength) {
  light(g, x + size * 0.5, y + size * 0.5, size * 4, size * 2.3, [[0, `rgba(247,185,110,${strength * 0.46})`], [1, '#f0b87500']]);
  g.fillStyle = '#e1aa6d'; g.fillRect(x, y, size, size * 0.66);
  g.fillStyle = '#ffe4b1'; g.fillRect(x + 0.6, y + 0.55, size * 0.61, size * 0.22);
}

function vessel(g, t, x, y, size, heading, exposure = 0) {
  g.save();
  g.translate(x, y + Math.sin(t * 2.18) * size * 1.4);
  g.rotate(Math.sin(t * 2.18 + 0.7) * 0.047);
  g.scale(size * heading, size);

  // Positive x is the bow in every view. The wake always lies behind the stern.
  const wash = linear(g, -163, 0, 69, 0, [[0, '#abdae200'], [0.44, '#8fbec54c'], [1, '#d2e5e765']]);
  for (let i = 0; i < 13; i++) {
    const wave = Math.sin(t * 3.5 + i * 2.2);
    const x0 = -161 + i * 7 + wave * 10, y0 = 3 + i * 1.3 + wave * 3.6;
    g.beginPath(); g.moveTo(x0, y0);
    g.bezierCurveTo(x0 + 24, y0 - 2, x0 + 38, y0 + 6, x0 + 74, y0 + 3);
    g.strokeStyle = wash; g.lineWidth = 0.5 + (i % 4) * 0.24; g.stroke();
  }
  polygon(g, [[-89, -17], [-57, -18], [22, -17], [64, -22], [92, -32], [78, -8], [54, 5], [-58, 5], [-81, -4]], linear(g, 0, -30, 0, 5, [[0, '#607785'], [0.37, '#293c47'], [0.52, '#14262d'], [1, '#10212d']]), '#112a37');
  polygon(g, [[-83, -3], [-64, -1], [56, -1], [77, -10], [56, 4], [-59, 5]], '#523b39');
  line(g, [[-87, -17], [-44, -16], [46, -18], [91, -32]], exposure ? '#c4b7a3' : '#788b91', 1.35);
  line(g, [[-75, -12], [42, -10], [74, -19]], '#7a8a893c', 1.1);

  polygon(g, [[-64, -18], [-59, -33], [-43, -34], [-41, -53], [15, -53], [27, -37], [39, -35], [44, -19]], linear(g, 0, -56, 0, -16, [[0, '#7c8786'], [0.39, '#536269'], [1, '#263942']]), '#1c303d');
  polygon(g, [[-48, -49], [22, -49], [14, -56], [-43, -56]], '#2a3c48', '#829096');
  polygon(g, [[-38, -47], [14, -47], [22, -38], [-35, -38]], '#0d212d');
  for (let i = 0; i < 6; i++) cabinWindow(g, -35 + i * 8.4, -45.5, 5.2, 0.94);
  for (const x of [-53, -31, -20, 0, 18, 30]) { g.fillStyle = '#231e1d'; g.fillRect(x, -31, 5, 6); cabinWindow(g, x + 0.7, -29.6, 3.2, 0.32); }
  line(g, [[-54, -21], [-51, -29], [-27, -29]], '#acb2a67d', 0.8);
  for (const x of [-79, -71, 46, 56, 66, 76, 86]) line(g, [[x, -19 - Math.max(0, x - 46) * 0.28], [x, -24 - Math.max(0, x - 46) * 0.28]], '#617784', 0.7);
  line(g, [[46, -24], [90, -36]], '#85979a', 0.8);
  polygon(g, [[-29, -56], [-28, -69], [-15, -69], [-12, -55]], '#20343e', '#5d7079');
  line(g, [[-28, -69], [-15, -69]], '#804933', 1.6);
  line(g, [[0, -55], [1, -86]], '#788b95', 1.5);
  line(g, [[-9, -75], [10, -75]], '#80939b', 0.8);
  line(g, [[-32, -56], [0, -83], [51, -24]], '#60788298', 0.62);
  cabinWindow(g, -0.1, -85, 2.4, 0.63);
  g.fillStyle = '#c56b47'; g.fillRect(-83, -19, 2.5, 2.5);
  if (exposure > 0.02) {
    light(g, 1, -48, 83, 36, [[0, `rgba(232,203,153,${exposure * 0.23})`], [1, '#e8cb9900']]);
  }
  const surface = linear(g, 0, -4, 0, 12, [[0, '#10273200'], [0.5, '#152b36ad'], [1, '#152b3600']]);
  g.fillStyle = surface; g.fillRect(-91, -3, 165, 14);
  for (let i = 0; i < 15; i++) {
    const x = -97 + i * 11 + Math.sin(i + t * 7.8) * 5, y = 3 + Math.sin(i * 1.4 + t * 4.7) * 5;
    line(g, [[x, y], [x + 6 + i % 7, y - 0.55]], i % 3 ? '#5d83888b' : '#92b6ba9c', 0.62 + i % 4 * 0.28);
  }
  g.restore();
  for (let i = 0; i < 20; i++) {
    const p = Math.sin(i * 3.18 + t * 5), dy = i * size * 0.52;
    g.fillStyle = `rgba(243,180,108,${(1 - i / 20) ** 2 * (p * 0.07 + 0.1)})`;
    g.fillRect(x + p * i * size * 0.64 - (i % 5 + 1) * size, y + 7 + dy, (i % 5 + 2) * size, size * 0.68);
  }
}

export function wideCoast(g, t, finalShot) {
  const horizon = 343;
  const pan = finalShot ? -13 + 13 * seg(t, 17, 4, ease.inOutSoft) : 15 * seg(t, 0, 4.5, ease.inOutSoft);
  skyAndWater(g, t, horizon, finalShot ? 0.38 : 0);
  g.save(); g.translate(-pan, 0);
  polygon(g, [[0, 346], [0, 317], [101, 299], [196, 323], [276, 306], [342, 325], [410, 326], [507, 342], [571, 351], [0, 357]], '#3c505a');
  landProfile(g, farCliff, '#23343e', 345);
  breakers(g, t, false);
  landProfile(g, nearCliff, '#233540', 346);
  lantern(g, finalShot);

  if (finalShot) {
    lighthouseBeam(g, t);
    const p = seg(t, time.wideShot, 4, ease.linear);
    vessel(g, t, lerp(919, 1117, p), lerp(393, 365, p), lerp(0.79, 0.49, p), 1, 0.26);
  } else {
    const p = seg(t, 0, time.switchShot, ease.linear);
    vessel(g, t, lerp(1050, 825, p), lerp(380, 414, p), lerp(0.56, 0.84, p), -1);
  }
  g.restore();
  rainfall(g, t, finalShot ? 0.46 : 0.78, finalShot);
}

export function turningVessel(g, t) {
  const beam = seg(t, time.beam, 0.85, ease.outSoft) * (1 - 0.45 * seg(t, 14.4, 1.8));
  skyAndWater(g, t, 250, beam * 0.72);
  // Fog carries the sweep beside and behind the hull before the face of the boat catches it.
  light(g, 400 + beam * 482, 242, 745, 144, [[0, `rgba(222,190,139,${beam * 0.37})`], [0.55, `rgba(166,149,119,${beam * 0.19})`], [1, '#d5c39100']]);
  const sweep = seg(t, time.beam - 0.16, 1.15, ease.inOutSoft);
  const shaft = Math.sin(Math.PI * sweep);
  if (shaft > 0.02) {
    g.save(); g.translate(603, 149 + 159 * sweep); g.rotate(0.08 + sweep * 0.06);
    light(g, 0, 0, 890, 16 + 10 * sweep, [[0, `rgba(233,212,167,${shaft * 0.3})`], [0.65, `rgba(214,183,136,${shaft * 0.1})`], [1, '#ccac7200']]);
    g.restore();
  }
  landProfile(g, foregroundCliff, '#263946', 431);
  breakers(g, t, true);
  const angle = lerp(Math.PI, 0, seg(t, time.turn, 2.65, ease.inOutSoft));
  const drift = -67 * seg(t, time.seaShot, 1.8, ease.outSoft) + 236 * seg(t, time.turn + 0.42, 3.42, ease.inOutSoft);
  const heading = Math.cos(angle);
  const x = 735 + drift, y = 376 - seg(t, time.turn + 0.8, 3, ease.inOut) * 40;
  const scale = lerp(2.12, 1.49, seg(t, time.turn + 0.7, 3.1, ease.inOut));
  vessel(g, t, x, y, scale, heading, beam);
  const bow = Math.sin(angle) ** 4;
  if (bow > 0.015) {
    // A head-on insert within the turn gives the hull width as its side profile disappears.
    g.save(); g.translate(x, y + Math.sin(t * 2.18) * scale * 1.4); g.scale(scale, scale); g.globalAlpha = bow;
    polygon(g, [[-27, -23], [0, -30], [27, -23], [14, 0], [0, 6], [-14, 0]], linear(g, -27, 0, 27, 0, [[0, '#101e2a'], [0.48, '#414b4d'], [1, '#162c39']]), '#61747b');
    polygon(g, [[-20, -28], [-15, -48], [15, -48], [20, -28]], '#536066', '#203d4d');
    for (const i of [-12, -4, 4]) cabinWindow(g, i, -44, 5.5, 0.8);
    line(g, [[0, -29], [0, 5]], '#6e7b80', 1);
    g.restore();
  }
  rainfall(g, t, 1, beam > 0.5);
}
