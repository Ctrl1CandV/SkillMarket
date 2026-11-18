import { lerp, rng, seg, ease } from '../../kit/kit.js';
import { time } from './timeline.js';
import { W, H, polygon, line, linear, radial, light, texture } from './paint.js';

const rust = texture(876, 480, 260, (x, y, cloud, grain) => {
  const surface = (cloud - 0.55) * 66 + (grain - 0.5) * 22;
  const lit = 21 * (1 - y) * (1 - x);
  return [28 + surface + lit, 38 + surface + lit, 42 + surface + lit, 255];
});

function bolt(g, x, y, r) {
  g.fillStyle = radial(g, x - r * 0.25, y - r * 0.4, r * 1.6, [[0, '#777971'], [0.45, '#414947'], [0.62, '#1b252b'], [1, '#06111a']]);
  g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
  line(g, [[x - r * 0.42, y + r * 0.22], [x + r * 0.46, y - r * 0.25]], '#121d24', Math.max(1, r * 0.2));
}

function window(g, t) {
  const glass = [[0, 0], [333, 0], [308, 334], [0, 353]];
  polygon(g, glass, linear(g, 0, 20, 260, 370, [[0, '#4c6774'], [0.47, '#6b8790'], [1, '#1c333f']]), '#17242a', 12);
  g.save(); g.clip();
  for (let i = 0; i < 23; i++) {
    const y = 65 + i * 13;
    const x = Math.sin(i * 7.63 + t * 1.2) * 63;
    line(g, [[x, y], [x + 116, y + 2], [x + 244, y - 6]], i > 10 ? '#153542a3' : '#c7dce019', 6.8);
  }
  light(g, 166 - 17 * (t - time.switchShot), 234, 11, 8, [[0, '#f6adaa'], [0.33, '#eeb27b9e'], [1, '#f5bc8600']]);
  const random = rng(23);
  for (let i = 0; i < 95; i++) {
    const speed = 18 + random() * 194, x0 = (random() * 380 + t * (5 + speed * 0.06)) % 370 - 30;
    const y = (random() * 425 + t * speed) % 425 - 55;
    const trail = 9 + random() * 80, fill = linear(g, x0 - 9, y - trail, x0, y, [[0, '#bbcbd000'], [0.93, '#c3d5d640'], [1, '#d4dddc89']]);
    line(g, [[x0 - 9, y - trail], [x0 - 2, y - trail * 0.46], [x0, y]], fill, 0.4 + random());
  }
  line(g, [[89, 0], [76, 344]], '#182933', 11);
  line(g, [[0, 142], [324, 126]], '#152831', 9);
  line(g, [[91, 1], [78, 344]], '#75878a55', 2);
  g.restore();
  polygon(g, [[0, 343], [311, 321], [327, 345], [0, 369]], '#19272e', '#516168', 2);
}

function cable(g, x, y, left) {
  const color = left ? '#31454b' : '#49362b';
  g.beginPath(); g.moveTo(x, y); g.bezierCurveTo(x - 16, y + 93, x + 61, y + 104, x + 56, y + 183);
  g.lineWidth = 19; g.strokeStyle = '#0c1921'; g.stroke();
  g.lineWidth = 13; g.strokeStyle = color; g.stroke();
  g.lineWidth = 2; g.strokeStyle = '#8b8e8158'; g.stroke();
}

function glove(g, x, y, reached, t) {
  g.save(); g.translate(x, y);
  // Sleeve folds point back toward the edge of frame. The glove stays wrapped around the lever.
  const sleeve = [[79, 19], [154, 3], [289, 64], [620, 168], [661, 333], [497, 406], [239, 258], [120, 189], [55, 115]];
  polygon(g, sleeve, linear(g, 70, 15, 380, 252, [[0, '#263b41'], [0.23, '#43514e'], [0.4, '#3e4640'], [0.63, '#1d2d31'], [1, '#101e27']]), '#182932', 2.5);
  for (const [pts, tone, width] of [
    [[[99, 37], [184, 48], [326, 96], [540, 218]], '#67736e58', 3],
    [[[97, 48], [166, 64], [239, 72], [455, 186]], '#223339', 7],
    [[[104, 123], [160, 171], [242, 184], [436, 301]], '#0f232b9c', 14],
    [[[106, 112], [168, 145], [221, 159], [409, 269]], '#5663604d', 4],
    [[[111, 135], [173, 176], [233, 194]], '#4b5b5940', 6],
  ]) line(g, pts, tone, width);

  polygon(g, [[54, 10], [122, 3], [146, 41], [130, 147], [88, 145], [53, 115]], linear(g, 113, -8, 96, 149, [[0, '#172835'], [0.36, '#526062'], [0.56, '#364545'], [1, '#121f2b']]), '#16242c', 2);
  for (let i = 0; i < 7; i++) line(g, [[61 + i * 7, 16 - i * 0.6], [71 + i * 7, 44 + i * 2], [59 + i * 10, 111 + i * 4]], i % 2 ? '#15252d77' : '#afb2a23d', 0.9);

  const fingers = 1 - reached, shift = fingers * 12 + Math.sin(t * 6.5) * fingers * 3;
  g.beginPath();
  g.moveTo(87, 22); g.bezierCurveTo(63, 8, 53, -31, 27, -49);
  g.bezierCurveTo(7, -64, -4, -65, -17 - shift, -57 - shift);
  g.bezierCurveTo(-32 - shift, -52, -42 - shift, -36, -39 - shift, -25);
  g.bezierCurveTo(-48 - shift, -16, -43 - shift, -8, -43 - shift, 3);
  g.bezierCurveTo(-44 - shift, 15, -38 - shift, 24, -31, 30);
  g.bezierCurveTo(-27, 46, -6, 45, 6, 48);
  g.bezierCurveTo(29, 55, 56, 68, 60, 91); g.lineTo(105, 90); g.closePath();
  g.fillStyle = linear(g, 8, -64, 35, 94, [[0, '#596967'], [0.19, '#455759'], [0.4, '#35494f'], [0.71, '#212f31'], [1, '#182a32']]);
  g.fill(); g.strokeStyle = '#12222b'; g.lineWidth = 3; g.stroke();
  line(g, [[-33 - shift, -28], [-21, -34], [-10, -26], [2, -14]], '#8190918a', 2);
  line(g, [[-38 - shift, -12], [-26, -18], [-16, -12], [-7, -2]], '#142932', 3);
  line(g, [[-40 - shift, 1], [-28, -1], [-17, 5]], '#71818088', 2);
  line(g, [[-32 - shift, 14], [-21, 11], [-9, 19]], '#132630', 2);
  line(g, [[7, -45], [25, -28], [42, 12], [71, 33]], '#83908875', 2.3);
  line(g, [[1, -44], [26, -17], [28, 6], [45, 26], [69, 37]], '#253a40', 3.6);
  for (let i = 0; i < 14; i++) {
    const p = i / 14;
    const ax = 11 + 57 * p, ay = -39 + Math.sin(p * 1.54) * 69;
    line(g, [[ax - 2, ay], [ax, ay + 1.9]], '#a2a99c82', 0.7);
  }
  g.restore();
}

export function switchRoom(g, t) {
  g.drawImage(rust, 0, 0, W, H);
  light(g, 264, 165, 735, 830, [[0, '#7799af4f'], [1, '#7799af00']]);
  window(g, t);
  for (const x of [353, 990, 1115]) {
    line(g, [[x + 16, 0], [x, H]], '#07131d', 16);
    line(g, [[x + 26, 0], [x + 3, H]], '#637a7e69', 3);
  }

  g.save();
  const drift = seg(t, time.switchShot, time.lensShot - time.switchShot, ease.inOutSoft);
  g.translate(-drift * 13, -drift * 7);
  g.scale(1 + 0.023 * drift, 1 + 0.023 * drift);
  const panel = [[447, 125], [884, 105], [907, 162], [902, 455], [466, 482], [429, 418], [423, 170]];
  polygon(g, panel.map(([x, y]) => [x + 19, y + 34]), '#07141da0');
  polygon(g, panel, linear(g, 463, 114, 873, 476, [[0, '#637176'], [0.19, '#39484c'], [0.38, '#38474a'], [0.57, '#172931'], [0.8, '#303d3d'], [1, '#071923']]), '#172731', 4);
  g.save(); g.clip(); g.globalAlpha = 0.3; g.drawImage(rust, 420, 100, 500, 400); g.restore();
  polygon(g, [[451, 159], [873, 139], [878, 426], [465, 454]], null, '#8390914f', 1.7);
  for (const [x, y] of [[449, 156], [866, 136], [465, 435], [878, 419], [665, 144]]) bolt(g, x, y, 6.6);
  cable(g, 559, 469, true); cable(g, 794, 440, false);

  polygon(g, [[623, 172], [721, 167], [734, 198], [630, 203]], '#15252e', '#8f9b9565');
  for (let i = 0; i < 10; i++) line(g, [[634 + i * 8.1, 182], [637 + i * 8.1, 192]], '#aaa28c99', 1.2);
  const socket = [[679, 228], [757, 223], [762, 254], [681, 265], [669, 252]];
  polygon(g, socket, linear(g, 684, 223, 752, 270, [[0, '#a2a9a0'], [0.45, '#777a69'], [1, '#202e33']]), '#19282f', 2);
  for (let i = 0; i < 4; i++) line(g, [[678 + i * 5, 232], [679 + i * 5, 257]], '#333e3d', 2.4);
  polygon(g, [[710, 229], [745, 228], [750, 250], [714, 255]], '#141e21', '#af9671');
  bolt(g, 753, 236, 4.8);

  const engaged = seg(t, time.pull, time.contact - time.pull, ease.inOutSoft);
  const settle = Math.sin((t - time.contact) * 43) * (1 - seg(t, time.contact, 0.28)) * (t >= time.contact ? 0.029 : 0);
  const pivot = [563, 382];
  const angle = lerp(-2.55, -0.733, engaged) + settle;
  const handle = [pivot[0] + 219 * Math.cos(angle), pivot[1] + 219 * Math.sin(angle)];

  polygon(g, [[511, 368], [613, 357], [629, 395], [625, 429], [518, 439], [504, 416]], linear(g, 566, 355, 575, 433, [[0, '#858d89'], [0.41, '#4d605e'], [1, '#1c2b32']]), '#172630', 3);
  for (const [x, y] of [[523, 382], [612, 375], [533, 425], [614, 413]]) bolt(g, x, y, 5.4);
  g.save(); g.translate(...pivot); g.rotate(angle);
  polygon(g, [[0, -17], [153, -14], [233, -10], [234, 9], [137, 19], [-10, 16]], linear(g, 0, -19, 0, 21, [[0, '#d1b58a'], [0.19, '#92856e'], [0.34, '#6c695b'], [0.67, '#4a504a'], [0.79, '#303d3d'], [1, '#111f28']]), '#172830', 2);
  line(g, [[15, -9], [85, -9], [222, -5]], '#cab69763', 1.5);
  polygon(g, [[164, -22], [229, -20], [248, -12], [246, 11], [220, 21], [164, 19]], linear(g, 0, -21, 0, 25, [[0, '#614943'], [0.37, '#3d3833'], [0.57, '#1b2930'], [1, '#102630']]), '#152731', 2);
  for (let i = 0; i < 9; i++) line(g, [[168 + i * 7.5, -20], [166 + i * 8.1, 19]], '#a28d7355', 0.9);
  g.restore();
  bolt(g, ...pivot, 25); bolt(g, ...pivot, 10);

  if (t >= time.glove - 0.62) {
    const approach = seg(t, time.glove - 0.62, 0.62, ease.outSoft);
    const retreat = seg(t, time.contact + 0.24, 0.38, ease.in);
    glove(g, handle[0] + 32 + 590 * (1 - approach) + 535 * retreat, handle[1] + 27 + 305 * (1 - approach) + 305 * retreat, approach * (1 - retreat), t);
  }
  const flash = seg(t, time.contact - 0.02, 0.04, ease.linear) * (1 - seg(t, time.contact + 0.03, 0.2));
  if (flash > 0) {
    light(g, 738, 239, 94, 68, [[0, `rgba(255,224,174,${flash})`], [0.18, `rgba(255,163,68,${flash * 0.55})`], [1, '#e2854700']]);
    for (let i = 0; i < 6; i++) {
      const theta = i * 3.841, length = (9 + i * 2) * flash;
      line(g, [[738, 239], [738 + Math.cos(theta) * length, 239 + Math.sin(theta) * length]], '#ffd195', 0.8);
    }
  }
  if (t >= time.contact) {
    light(g, 838, 192, 19, 14, [[0, '#ff8c45'], [0.22, '#e36d3c97'], [1, '#e36d3c00']]);
  } else {
    bolt(g, 838, 192, 4);
  }
  g.restore();
}

function ellipse(g, x, y, rx, ry, stroke, width) {
  g.beginPath(); g.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
  g.strokeStyle = stroke; g.lineWidth = width; g.stroke();
}

export function fresnelLens(g, t) {
  g.fillStyle = '#122630'; g.fillRect(0, 0, W, H);
  g.drawImage(rust, 0, 0, W, H);
  const start = seg(t, time.ignition, 0.78, ease.outSoft);
  const flash = Math.sin(Math.PI * seg(t, time.ignition, 0.27, ease.linear)) * 0.7;
  const sweep = seg(t, time.ignition + 0.35, 2.82, ease.inOutSoft);
  const x = lerp(536, 789, sweep), y = 287 - 9 * sweep;
  const source = (a) => `rgba(255,191,91,${a * start})`;
  light(g, x, y, 670, 445, [[0, source(0.6)], [0.23, source(0.32)], [0.66, source(0.11)], [1, '#df9a4300']]);

  for (let i = -8; i <= 8; i++) {
    const row = y + i * 32.1, sin = Math.sin(i * 0.61 + sweep * 3.42);
    const stripe = linear(g, x - 495, row + 21, x + 485, row - 12, [[0, '#1d424b30'], [0.24, '#58748317'], [0.42, source(0.16 + sin * 0.08)], [0.58, source(0.2 + sin * 0.1)], [0.73, '#42616d60'], [1, '#1d424b15']]);
    polygon(g, [[0, row - 9], [417, row + sin * 6], [880, row - sin * 5], [W, row - 14], [W, row + 9], [860, row + 13], [438, row + 16], [0, row + 12]], stripe, '#69859138');
    line(g, [[0, row + 15], [480, row + 19 + sin * 3], [W, row + 11]], '#061a26a8', 2.2);
  }

  for (let i = 19; i >= 0; i--) {
    const rx = 48 + i * 23.2, ry = rx * (0.76 + 0.1 * sweep);
    const glass = linear(g, x - rx, y - ry, x + rx, y + ry, [[0, '#29465030'], [0.14, '#7896a39e'], [0.36, source(0.35 + (i % 4) * 0.07)], [0.5, '#ada28f56'], [0.64, source(0.54)], [0.86, '#8c9b9d71'], [1, '#102a3744']]);
    ellipse(g, x, y, rx, ry, '#0e2a368a', 11.5 + i * 0.11);
    ellipse(g, x - 2, y - 2, rx, ry, glass, 7.3 + i * 0.1);
    ellipse(g, x - 4, y - 4, rx + 2.8, ry + 1.1, '#bedce66b', 0.95);
    ellipse(g, x + 2.1, y + 2.1, rx - 4.9, ry - 3.1, '#0e253685', 1.9);
  }

  light(g, x, y, 129, 91, [[0, '#ede8d7'], [0.11, '#e6a779c3'], [0.4, '#b1674932'], [1, '#f3c18d00']]);
  const brightness = Math.min(1, start + flash);
  if (brightness > 0) {
    g.save(); g.globalCompositeOperation = 'screen';
    light(g, x, y, 241 + sweep * 98, 147, [[0, `rgba(255,242,200,${brightness})`], [0.19, `rgba(255,209,133,${brightness * 0.82})`], [0.45, `rgba(247,158,54,${brightness * 0.36})`], [1, '#f79e3600']]);
    light(g, x, y, 565, 9 + flash * 14, [[0, source(0.73)], [0.19, source(0.48)], [1, '#eaa36a00']]);
    light(g, x, y - 1, 155, 3, [[0, '#ffefce'], [0.37, '#ffe7b277'], [1, '#edc38600']]);
    g.restore();
  }

  for (const side of [0, 1]) {
    const k = side ? 1087 + sweep * 27 : 99 + sweep * 91;
    const frame = [[k - 51, -22], [k + 24, -22], [k + 91, 598], [k + 1, 598]];
    polygon(g, frame, linear(g, k - 40, 190, k + 72, 179, [[0, '#061923'], [0.36, '#223941'], [0.55, '#57676a'], [0.68, start ? '#776657' : '#283d44'], [0.92, '#14303a'], [1, '#071b24']]), '#071823', 2);
    line(g, [[k + 3, 0], [k + 68, H]], start ? '#b5956373' : '#7895a070', 2);
    for (let i = 0; i < 6; i++) bolt(g, k - 9 + i * 10.2, 44 + i * 92, 7.1);
  }
  const c = 1 - seg(t, time.ignition - 0.2, 0.2);
  if (c > 0) { g.fillStyle = `rgba(6,15,24,${c * 0.64})`; g.fillRect(0, 0, W, H); }
}
