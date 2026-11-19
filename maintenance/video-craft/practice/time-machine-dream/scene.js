// time machine · dream (song 1:52.2–2:26.6). Practice piece for video-craft 0.8: the same chorus as
// ../time-machine-chorus, redone from a content design instead of a visual idea (see brief.md).
// Who it is for: someone separated from a person they love, who only meets them in dreams.
// What it should say: he longs to sleep because she is there, and dreads waking because she leaves again.
// Temperature: quiet. No machines, no star trails. The dream is an ordinary morning; waking is the same room, empty.
// Needs out/song/songmap.js (songmap.py on the recording) and lyrics.mjs (captions.mjs on lyrics.srt);
// neither is committed because both carry the song's text.
import { clamp, lerp, ease, kf, rng, register } from '../../../../video-craft/kit/kit.js';
import { layer, noise, view, finish, mix } from '../../../../video-craft/kit/draw.js';
import { capsule, profile, back, pointingArm, headTurn, hand } from './figures.js';
import SONG from './out/song/songmap.js';
import cues from './lyrics.mjs';

const W = 1920, H = 1080, FPS = 30;
const T0 = 112.227;                       // song seconds at film 0 (a downbeat)
const DUR = 34.4;
const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
const N = noise(19);
const smooth = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };

// film seconds of the beat nearest x: every cut lands on the recording's own beats
const BEATS = SONG.beats.map((b) => b - T0).filter((b) => b > -1 && b < DUR + 1);
const beat = (x) => BEATS.reduce((p, q) => (Math.abs(q - x) < Math.abs(p - x) ? q : p));
const CUT = {
  bed: beat(6), close: beat(10), dream: beat(12), together: beat(14), mugs: beat(16), balcony: beat(19),
  turn: beat(22), fade: beat(25), dawn: beat(29.5), lamp: beat(31.5), click: beat(32.5),
};

// ------------------------------------------------------------------ light
// Materials are albedos; each frame multiplies them by the ambient colour of its light state, then adds
// its own light (moon or sun through the window, the lamp).
const AMB = { moon: [36, 46, 82], sun: [255, 228, 196], dawn: [100, 116, 150], lamp: [150, 96, 52], ceil: [214, 176, 132] };
function ambient(L) {
  const out = [6, 7, 12];
  for (const k of Object.keys(AMB)) if (L[k]) for (let i = 0; i < 3; i++) out[i] += AMB[k][i] * L[k];
  return out;
}
const tint = (alb, amb, k = 1) => `rgb(${alb.map((a, i) => Math.round(clamp(a * amb[i] * k, 0, 255))).join(',')})`;
const tintA = (alb, amb, k = 1) => alb.map((a, i) => Math.round(clamp(a * amb[i] * k, 0, 255)));
const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
const L0 = { moon: 0, sun: 0, dawn: 0, lamp: 0, ceil: 0 };

const ALB = {
  wall: [0.9, 0.85, 0.78], floor: [0.56, 0.4, 0.27], wood: [0.46, 0.31, 0.2],
  sheet: [0.95, 0.94, 0.91], blanket: [0.6, 0.64, 0.74], curtain: [0.8, 0.68, 0.56], shade: [0.97, 0.92, 0.82],
  skin: [0.86, 0.68, 0.56], sleeve: [0.3, 0.32, 0.38], herSleeve: [0.84, 0.78, 0.74], hair: [0.1, 0.08, 0.07],
  mugBlue: [0.28, 0.42, 0.66], mugWhite: [0.95, 0.94, 0.91], counter: [0.78, 0.76, 0.72], tile: [0.88, 0.88, 0.86],
  leaf: [0.32, 0.52, 0.34], pot: [0.72, 0.46, 0.32], rack: [0.7, 0.72, 0.74],
};

function poly(c, pts) { c.beginPath(); c.moveTo(pts[0][0], pts[0][1]); for (const p of pts.slice(1)) c.lineTo(p[0], p[1]); c.closePath(); }
function fillPoly(c, pts, style) { poly(c, pts); c.fillStyle = style; c.fill(); }
function vgrad(c, y0, y1, stops) { const g = c.createLinearGradient(0, y0, 0, y1); stops.forEach(([o, col]) => g.addColorStop(o, col)); return g; }
function radial(c, x, y, r, col, a) {
  const g = c.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, rgba(col, a)); g.addColorStop(0.35, rgba(col, a * 0.4)); g.addColorStop(1, rgba(col, 0));
  return g;
}
function addLight(c, fn, blur = 0) { c.save(); c.globalCompositeOperation = 'screen'; if (blur) c.filter = `blur(${blur}px)`; fn(c); c.restore(); }

// a silhouette lit from behind: the whole shape in the rim colour, then the dark body shifted away from
// the light and clipped to the shape, so only a thin edge on the lit side keeps the rim colour
function rimmed(c, build, dark, rim, [dx, dy], alpha = 1) {
  c.save(); c.globalAlpha = alpha;
  c.beginPath(); build(c); c.fillStyle = rim; c.fill();
  c.clip();
  c.translate(dx, dy); c.beginPath(); build(c); c.fillStyle = dark; c.fill();
  c.restore();
}

// highlights bleed a little into the dark around them: keep only the bright parts of a small copy
// of the frame (multiplying it by itself) and add it back blurred
const GA = layer(W / 4, H / 4), ga = GA.getContext('2d'), GB = layer(W / 4, H / 4), gb = GB.getContext('2d');
function glowPass(amount) {
  if (amount <= 0) return;
  ga.globalCompositeOperation = 'copy'; ga.drawImage(cv, 0, 0, W / 4, H / 4);
  for (let i = 0; i < 2; i++) {
    gb.globalCompositeOperation = 'copy'; gb.drawImage(GA, 0, 0);
    ga.globalCompositeOperation = 'multiply'; ga.drawImage(GB, 0, 0);
  }
  ctx.save(); ctx.globalCompositeOperation = 'screen'; ctx.globalAlpha = amount; ctx.filter = 'blur(26px)';
  ctx.drawImage(GA, 0, 0, W, H); ctx.filter = 'blur(6px)'; ctx.globalAlpha = amount * 0.6; ctx.drawImage(GA, 0, 0, W, H);
  ctx.restore();
}

// ------------------------------------------------------------------ outside the windows
const CITY = (() => {
  const r = rng(77), b = [];
  let x = -40;
  while (x < 2000) { const w = 40 + r() * 110; b.push({ x, w, h: 40 + r() * 220, lit: Array.from({ length: 48 }, () => r()) }); x += w + r() * 10; }
  return b;
})();
const STARS = (() => { const r = rng(5); return Array.from({ length: 300 }, () => ({ x: r(), y: r(), b: Math.pow(r(), 4), tw: r() * 6.28 })); })();

// sky and city through an opening (x0..x1, y0..y1), horizon at hy; light state L (moon / sun / dawn weights)
function outside(c, [x0, y0, x1, y1], hy, L, s, { moonAt = [0.25, 0.22], sunAt = [0.8, 0.1], cityScale = 1 } = {}) {
  c.save(); c.beginPath(); c.rect(x0, y0, x1 - x0, y1 - y0); c.clip();
  const night = L.moon || 0, sun = L.sun || 0, dawn = L.dawn || 0;
  const top = mix(mix([7, 12, 32], [178, 210, 236], sun), [70, 88, 132], dawn);
  const low = mix(mix([30, 40, 82], [255, 240, 214], sun), [226, 176, 160], dawn);
  c.fillStyle = vgrad(c, y0, hy, [[0, rgba(top, 1)], [1, rgba(low, 1)]]); c.fillRect(x0, y0, x1 - x0, y1 - y0);
  const w = x1 - x0, h = hy - y0;
  if (night > 0.05) {
    for (const st of STARS) {
      const a = night * (0.25 + 0.75 * st.b) * (0.75 + 0.25 * Math.sin(s * 1.7 + st.tw));
      c.fillStyle = `rgba(230,236,255,${a})`;
      c.fillRect(x0 + st.x * w, y0 + st.y * h * 0.8, 1.2 + 2 * st.b, 1.2 + 2 * st.b);
    }
    const mx = x0 + moonAt[0] * w, my = y0 + moonAt[1] * h;
    c.fillStyle = radial(c, mx, my, 170, [190, 205, 255], 0.35 * night); c.fillRect(mx - 170, my - 170, 340, 340);
    c.fillStyle = `rgba(244,240,226,${night})`; c.beginPath(); c.arc(mx, my, 24, 0, 6.283); c.fill();
  }
  if (sun > 0.05) {
    const sx = x0 + sunAt[0] * w, sy = y0 + sunAt[1] * h;
    c.fillStyle = radial(c, sx, sy, 760, [255, 250, 232], sun); c.fillRect(x0, y0, w, y1 - y0);
  }
  for (const [depth, near] of [[0.55, false], [1, true]]) {
    const col = mix(mix([16, 22, 44], [206, 204, 204], sun), [46, 54, 82], dawn).map((v) => (near ? v * 0.8 : v + 18));
    for (const b of CITY) {
      const bx = x0 + (b.x / 2000) * w, bw = (b.w / 2000) * w, bh = b.h * depth * cityScale * (h / 520);
      if (bx > x1 || bx + bw < x0) continue;
      c.fillStyle = rgba(col, sun > 0.5 ? 0.55 : 1);
      c.fillRect(bx, hy - bh, bw + 1, y1 - hy + bh);
      if (near && night + dawn * 0.5 > 0.1) {
        for (let i = 0; i < b.lit.length; i++) {
          if (b.lit[i] > 0.36 * (1 + dawn)) continue;
          const wx = bx + 6 + (i % 5) * (bw - 10) / 5, wy = hy - bh + 8 + Math.floor(i / 5) * 18 * cityScale;
          if (wy > y1) continue;
          c.fillStyle = `rgba(255,${190 + 30 * b.lit[i]},120,${(night + dawn * 0.4) * 0.8})`;
          c.fillRect(wx, wy, 4 * cityScale, 6 * cityScale);
        }
      }
    }
  }
  c.restore();
}

// ------------------------------------------------------------------ the bedroom, framing A
// Camera at the foot of the bed. He sleeps on the left; the window is behind her side, so in every light
// she (or her empty pillow) is what the window lights.
const WIN = [620, 104, 1220, 470];
const MOTES = (() => { const r = rng(3); return Array.from({ length: 160 }, () => ({ x: r(), y: r(), z: r(), p: r() * 6.28 })); })();

function bedroom(c, s, L, P) {
  const amb = ambient({ ...L, lamp: 0 }), sunny = (L.sun || 0) > 0.2;   // the lamp lights only its own island
  c.fillStyle = tint(ALB.wall, amb, 0.6); c.fillRect(-400, -300, W + 800, H + 700);
  fillPoly(c, [[150, 40], [1770, 40], [1770, 650], [150, 650]], tint(ALB.wall, amb, 0.9));
  fillPoly(c, [[-400, -300], [150, 40], [150, 650], [-400, 1000]], tint(ALB.wall, amb, 0.68));
  fillPoly(c, [[1770, 40], [2320, -300], [2320, 1000], [1770, 650]], tint(ALB.wall, amb, 0.76));
  fillPoly(c, [[-400, -300], [2320, -300], [1770, 40], [150, 40]], tint(ALB.wall, amb, 0.58));
  fillPoly(c, [[-400, 1000], [150, 650], [1770, 650], [2320, 1000], [2320, 1500], [-400, 1500]], tint(ALB.floor, amb, 0.85));
  c.save(); poly(c, [[-400, 1000], [150, 650], [1770, 650], [2320, 1000], [2320, 1500], [-400, 1500]]); c.clip();
  c.strokeStyle = tint(ALB.floor, amb, 0.62); c.lineWidth = 2;
  for (let i = -10; i <= 10; i++) { c.beginPath(); c.moveTo(960 + i * 95, 650); c.lineTo(960 + i * 330, 1500); c.stroke(); }
  c.restore();
  c.fillStyle = vgrad(c, 40, 650, [[0, 'rgba(0,0,0,0.26)'], [0.5, 'rgba(0,0,0,0.04)'], [1, 'rgba(0,0,0,0.12)']]);
  c.fillRect(150, 40, 1620, 610);
  c.fillStyle = tint(ALB.wall, amb, 0.7); c.fillRect(150, 634, 1620, 16);

  // the window and the light it throws on the wall around it
  const [x0, y0, x1, y1] = WIN;
  if (sunny || L.dawn) {
    c.fillStyle = radial(c, (x0 + x1) / 2, (y0 + y1) / 2, 720, sunny ? [255, 226, 180] : [150, 170, 210], sunny ? 0.45 * L.sun : 0.12 * L.dawn);
    c.fillRect(-400, -300, W + 800, 1000);
  }
  outside(c, [x0 + 14, y0 + 14, x1 - 14, y1 - 14], y1 - 70, L, s, { moonAt: [0.18, 0.2], sunAt: [0.78, 0.12] });
  c.fillStyle = tint(ALB.wall, amb, sunny ? 1.0 : 0.95);
  c.fillRect(x0, y0, x1 - x0, 14); c.fillRect(x0, y1 - 14, x1 - x0, 14); c.fillRect(x0, y0, 14, y1 - y0); c.fillRect(x1 - 14, y0, 14, y1 - y0);
  c.fillRect((x0 + x1) / 2 - 6, y0, 12, y1 - y0); c.fillRect(x0, y0 + 118, x1 - x0, 10);
  c.fillStyle = tint(ALB.wall, amb, 1.02); c.fillRect(x0 - 22, y1, x1 - x0 + 44, 14);
  for (const [cx0, cx1] of [[540, 620], [1220, 1300]]) {
    for (let x = cx0; x < cx1; x += 5) {
      const k = 0.74 + 0.26 * Math.sin((x - cx0) * 0.2 + 1.3);
      c.fillStyle = tint(ALB.curtain, amb, k); c.fillRect(x, 92, 5.5, 560);
    }
  }
  c.fillStyle = tint(ALB.wood, amb, 0.7); c.fillRect(520, 84, 800, 9);
  // morning sun: a soft shaft and a little dust in it, behind everything in the room
  if (sunny) {
    addLight(c, (g) => {
      g.globalAlpha = 0.2 * L.sun;
      const gr = g.createLinearGradient(1000, 200, 900, 900);
      gr.addColorStop(0, 'rgba(255,232,190,1)'); gr.addColorStop(1, 'rgba(255,232,190,0)');
      g.fillStyle = gr; poly(g, [[640, 120], [1200, 120], [1290, 900], [560, 900]]); g.fill();
    }, 30);
    for (const m of MOTES.slice(0, 70)) {
      const mx = 640 + m.x * 620 + Math.sin(s * 0.3 + m.p) * 18, my = 140 + ((m.y * 680 + s * 7 * (0.3 + m.z)) % 680);
      c.fillStyle = `rgba(255,238,206,${0.3 * L.sun * (0.3 + m.z)})`;
      c.fillRect(mx, my, 1.4 + m.z * 1.6, 1.4 + m.z * 1.6);
    }
  }

  // nightstands: his (left), hers (right) with the lamp
  for (const [nx, nw] of [[190, 130], [1140, 150]]) {
    fillPoly(c, [[nx, 600], [nx + nw, 600], [nx + nw, 772], [nx, 772]], tint(ALB.wood, amb, 0.78));
    fillPoly(c, [[nx - 8, 588], [nx + nw + 8, 588], [nx + nw, 602], [nx, 602]], tint(ALB.wood, amb, 1.0));
    c.fillStyle = tint(ALB.wood, amb, 0.55); c.fillRect(nx + 12, 642, nw - 24, 3);
  }
  c.fillStyle = tint(ALB.wood, amb, 0.5); c.fillRect(1212, 514, 6, 72);
  c.fillStyle = tint(ALB.wood, amb, 0.7); c.beginPath(); c.ellipse(1215, 586, 26, 6, 0, 0, 6.283); c.fill();
  const shade = [[1180, 452], [1250, 452], [1272, 516], [1158, 516]];
  fillPoly(c, shade, tint(ALB.shade, amb, 0.85));

  // the bed
  fillPoly(c, [[330, 462], [1080, 462], [1080, 548], [330, 548]], tint(ALB.wood, amb, 0.85));
  c.fillStyle = tint(ALB.wood, amb, 1.08); c.fillRect(326, 456, 758, 12);
  fillPoly(c, [[150, 862], [1262, 862], [1262, 950], [150, 950]], tint(ALB.sheet, amb, 0.6));
  c.fillStyle = tint(ALB.wood, amb, 0.5); c.fillRect(160, 950, 30, 60); c.fillRect(1222, 950, 30, 60);
  fillPoly(c, [[345, 540], [1065, 540], [1262, 862], [150, 862]], tint(ALB.sheet, amb, 0.84));
  pillow(c, 525, 566, amb, 0);
  pillow(c, 885, 566, amb, P.dent || 0);

  // her, in the dream: sitting up against the headboard, turned toward him, against the window
  const rimWarm = 'rgba(255,226,186,1)', rimCool = 'rgba(176,196,244,0.9)';
  const dark = tint(ALB.hair, amb, sunny ? 1.6 : 0.9);
  if (P.her && P.herA > 0.01) {
    rimmed(c, (g) => profile(g, 915, 405, 0.92, { dir: -1, tilt: -0.06 - (P.laugh || 0) * 0.12, hair: 'long', arm: 'lap' }), dark, rimWarm, [-2, 4], P.herA);
  }
  // him
  if (P.him === 'propped') {
    // up on his left elbow, turned toward her: the forearm flat on the mattress, the upper arm up to the shoulder
    rimmed(c, (g) => {
      g.save(); g.translate(640, 520); g.rotate(0.5);
      profile(g, 0, 0, 0.9, { tilt: -0.66, hair: 'short' });
      g.restore();
    }, dark, rimWarm, [3, 4]);
  } else if (P.him === 'sit') {
    // pushing up from the pillow to sit, then looking down at her side of the bed
    const r = smooth(P.rise ?? 1);
    rimmed(c, (g) => profile(g, lerp(545, 560, r), lerp(590, 410, r), 0.95, { tilt: lerp(-1.1, 0.32, smooth((P.rise ?? 1) * 1.3 - 0.3)), hair: 'short', body: 240, arm: 'down' }),
      dark, 'rgba(255,190,120,0.95)', [-4, 2]);
  } else if (P.him === 'side' || P.him === 'back') {
    // lying down, seen from the foot of the bed: his head on the pillow above the hill his body makes in the
    // blanket, in silhouette like everywhere else. Crown toward the headboard, the face toward her side
    // (side) or turned up toward the ceiling, awake (back)
    const side = P.him === 'side';
    rimmed(c, (g) => profile(g, side ? 560 : 548, side ? 580 : 590, 0.66, { torso: false, tilt: side ? 0.15 : -0.55, hair: 'short' }),
      dark, rimCool, [0, 4]);
  }

  // blanket over whoever is in bed: a mound for his shoulder, one for her lap in the dream
  const edge = [];
  for (let i = 0; i <= 48; i++) {
    const u = i / 48, x = lerp(300, 1110, u);
    let y = 640 + 8 * Math.sin(u * 9 + 1);
    const hm = { side: 72, back: 50, propped: 96, sit: 60 }[P.him] || 0;
    const hc = { side: 600, back: 530, propped: 660 }[P.him] || 570, hw = { side: 120, back: 170 }[P.him] || 150;
    y -= hm * Math.exp(-(((x - hc) / hw) ** 2));
    y -= 104 * Math.exp(-(((x - 930) / 125) ** 2)) * (P.her ? P.herA : 0);
    if (P.him === 'sit') y = Math.max(y, 616 - 20 * Math.exp(-(((x - 560) / 130) ** 2)));
    edge.push([x, y]);
  }
  const blanket = [...edge, [1262, 940], [150, 940]];
  fillPoly(c, blanket, tint(ALB.blanket, amb, 0.85));
  c.save(); poly(c, blanket); c.clip();
  for (let k = 0; k < 9; k++) {
    const fx = 330 + k * 100 + 30 * N(k, 2), g = c.createLinearGradient(fx - 30, 0, fx + 30, 0);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(0.5, `rgba(0,0,0,${0.1 + 0.06 * N(k, 7)})`); g.addColorStop(1, 'rgba(0,0,0,0)');
    c.fillStyle = g; poly(c, [[fx - 20, 560], [fx + 20, 560], [fx * 1.18 - 140, 950], [fx * 1.18 - 210, 950]]); c.fill();
  }
  c.fillStyle = vgrad(c, 560, 950, [[0, 'rgba(255,255,255,0.08)'], [1, 'rgba(0,0,0,0.25)']]); c.fillRect(0, 540, W, 420);
  c.restore();

  // in the dream he props himself on his elbow, the arm out over the blanket toward her
  if (P.him === 'propped') {
    rimmed(c, (g) => {
      capsule(g, [606, 552], [598, 612], 15, 12);
      capsule(g, [598, 612], [690, 606], 12, 10);
      g.moveTo(718, 604); g.ellipse(704, 604, 14, 9, 0, 0, 6.283);
    }, dark, rimWarm, [3, 4]);
  }

  // light through the window: a patch across both pillows and the blanket, crossed by the mullions
  const beam = Math.max(L.moon || 0, (L.sun || 0) * 1.1);
  if (beam > 0.01) {
    const col = sunny ? [255, 214, 160] : [150, 176, 255];
    c.save(); poly(c, [[345, 540], [1065, 540], [1262, 862], [1262, 950], [150, 950], [150, 862]]); c.clip();
    addLight(c, (g) => {
      g.globalAlpha = clamp(beam) * (sunny ? 0.42 : 0.4);
      g.fillStyle = rgba(col, 1);
      poly(g, [[700, 548], [1160, 548], [1250, 860], [640, 880]]); g.fill();
      g.globalCompositeOperation = 'destination-out'; g.globalAlpha = 1; g.fillStyle = '#000';
      poly(g, [[916, 548], [928, 548], [966, 880], [948, 880]]); g.fill();
      poly(g, [[690, 610], [1180, 610], [1188, 626], [684, 628]]); g.fill();
    }, 12);
    c.restore();
  }
  // his arm across to her pillow (night), the hand resting where her head would be. Drawn over the window's
  // light (lit on its own) so the mullion shadows don't cut across it and make it look transparent
  if (P.him === 'side' && (P.arm || 0) > 0) {
    const k = smooth(P.arm);
    const sh = [640, 586], hx = lerp(700, 790, k), hy = lerp(632, 566, k);
    c.save(); c.lineCap = 'round'; c.strokeStyle = tint(ALB.sleeve, amb, 0.9); c.lineWidth = 34;
    c.beginPath(); c.moveTo(...sh); c.quadraticCurveTo(lerp(670, 720, k), lerp(616, 590, k), hx, hy); c.stroke(); c.restore();
    hand(c, { x: hx - 10, y: hy, s: 0.6, arm: 50, rot: lerp(0.5, -0.1, k), curl: lerp(0.5, 0.3, k), skin: tintA(ALB.skin, amb, 1.9), light: [200, 214, 255], shadow: 0.25 });
  }
  // the lamp, when on: a small warm island on her lamp and her pillow; the rest of the room stays cold
  if (L.lamp > 0.01) {
    addLight(c, (g) => {
      g.fillStyle = radial(g, 1215, 500, 430, [255, 170, 90], 0.75 * L.lamp); g.fillRect(700, 60, 1030, 900);
      g.save(); g.translate(900, 570); g.scale(1, 0.45);
      g.fillStyle = radial(g, 0, 0, 300, [255, 176, 100], 0.45 * L.lamp); g.fillRect(-300, -300, 600, 600);
      g.restore();
      g.fillStyle = radial(g, 1215, 492, 90, [255, 236, 200], L.lamp); g.fillRect(1100, 380, 240, 240);
    });
    fillPoly(c, shade, `rgba(255,224,170,${0.9 * L.lamp})`);
  }
}

function pillow(c, x, y, amb, dent) {
  c.save();
  c.fillStyle = tint(ALB.sheet, amb, 0.95);
  c.beginPath(); c.moveTo(x - 160, y - 30);
  c.bezierCurveTo(x - 80, y - 52, x + 80, y - 52, x + 160, y - 30);
  c.bezierCurveTo(x + 172, y, x + 172, y + 16, x + 160, y + 38);
  c.bezierCurveTo(x + 80, y + 48, x - 80, y + 48, x - 160, y + 38);
  c.bezierCurveTo(x - 172, y + 16, x - 172, y, x - 160, y - 30); c.fill();
  c.fillStyle = 'rgba(0,0,0,0.14)'; c.beginPath(); c.ellipse(x, y + 30, 150, 12, 0, 0, 3.14); c.fill();
  if (dent > 0) { c.fillStyle = `rgba(0,0,0,${0.16 * dent})`; c.beginPath(); c.ellipse(x - 10, y - 4, 70, 20, 0, 0, 6.283); c.fill(); }
  c.restore();
}

// ------------------------------------------------------------------ the pillow, close (S3 night, S4 dream)
// close: 0..1, his fingers closing over her hand (drawn again on top of it)
function pillowClose(c, s, L, t, { her = 0, curl = 0.3, close = 0 }) {
  const amb = ambient(L), sunny = (L.sun || 0) > 0.2;
  c.fillStyle = tint(ALB.wood, amb, 0.6); c.fillRect(-300, -300, W + 600, H + 600);   // headboard beyond
  // pillow filling the frame, its top seam crossing the upper third
  const top = 250;
  c.fillStyle = tint(ALB.sheet, amb, 0.92);
  c.beginPath(); c.moveTo(-300, top + 60); c.bezierCurveTo(400, top - 30, 1400, top - 40, 2220, top + 50); c.lineTo(2220, 1400); c.lineTo(-300, 1400); c.closePath(); c.fill();
  // soft folds and the dip where a head would lie
  for (let k = 0; k < 7; k++) {
    const fx = 120 + k * 290 + 60 * N(k, 4), fy = 520 + 260 * N(k, 9);
    c.save(); c.translate(fx, fy); c.scale(1.8, 0.5); c.fillStyle = radial(c, 0, 0, 260, [0, 0, 0], 0.1); c.fillRect(-300, -300, 600, 600); c.restore();
  }
  c.fillStyle = vgrad(c, top - 40, top + 120, [[0, 'rgba(0,0,0,0.3)'], [1, 'rgba(0,0,0,0)']]); c.fillRect(-300, top - 60, W + 600, 200);
  // the window's light across the pillow
  addLight(c, (g) => {
    g.globalAlpha = sunny ? 0.5 : 0.42; g.fillStyle = sunny ? 'rgb(255,214,160)' : 'rgb(140,168,250)';
    poly(g, [[560, top + 20], [1700, top + 10], [1900, 1100], [700, 1100]]); g.fill();
    g.globalCompositeOperation = 'destination-out'; g.globalAlpha = 1; g.fillStyle = '#000';
    poly(g, [[1100, top], [1130, top], [1290, 1100], [1250, 1100]]); g.fill();
  }, 22);
  // his hand, palm up on her side, from the lower left, kept above the subtitles; moonlit at night
  const his = (o) => hand(c, { x: 330, y: 760, s: 2.5, rot: -0.42, palm: true, curl,
    skin: sunny ? tintA(ALB.skin, amb, 1.0) : tintA(ALB.skin, [150, 168, 226]), light: sunny ? [255, 230, 190] : [180, 200, 255],
    sleeve: tintA(ALB.sleeve, sunny ? amb : [90, 100, 140], 1), shadow: 0.3, ...o });
  his({});
  // her hand, palm down, from her side of the bed at pillow height, laid across his fingers
  if (her > 0) {
    const k = smooth(her);
    hand(c, { x: lerp(2500, 720, k), y: lerp(700, 645, k), s: 2.0, rot: Math.PI + 0.05, side: 1, palm: false, curl: 0.25,
      skin: tintA([0.9, 0.72, 0.6], amb, 1.0), light: [255, 236, 200], sleeve: tintA(ALB.herSleeve, amb, 0.95), shadow: 0.35 });
    if (close > 0) his({ fingersOnly: true, shadow: 0.2, alpha: clamp(close * 3) });
  }
}

// ------------------------------------------------------------------ the kitchen counter (S1 night, S6 dream morning)
// Her white mug has a small chip in its rim; it has stood upside down on the rack since she left.
// the handle alone: drawn again over a gripping hand so the fingers read as going through it
function mugHandle(c, x, y, { w = 190, h = 230, alb, amb, handle = 1, alpha = 1 }) {
  if (alpha <= 0) return;
  const base = tintA(alb, amb, 1);
  c.save(); c.globalAlpha = alpha;
  c.lineCap = 'round'; c.strokeStyle = rgba(base.map((v) => v * 0.8), 1); c.lineWidth = 24;
  c.beginPath(); c.moveTo(x + handle * w * 0.46, y - h * 0.78); c.bezierCurveTo(x + handle * (w * 0.5 + 92), y - h * 0.78, x + handle * (w * 0.5 + 92), y - h * 0.24, x + handle * w * 0.46, y - h * 0.24); c.stroke();
  c.restore();
}

function mug(c, x, y, { w = 190, h = 230, up = true, alb, amb, chip = false, handle = 1, light = [255, 255, 255], lit = 0.5 }) {
  const ry = w * 0.13, base = tintA(alb, amb, 1);
  mugHandle(c, x, y, { w, h, alb, amb, handle });
  c.save();
  const g = c.createLinearGradient(x - w / 2, 0, x + w / 2, 0);
  g.addColorStop(0, rgba(base.map((v) => v * 0.55), 1)); g.addColorStop(0.35 - lit * 0.1, rgba(base.map((v) => Math.min(255, v * 1.08)), 1));
  g.addColorStop(0.7, rgba(base.map((v) => v * 0.82), 1)); g.addColorStop(1, rgba(base.map((v) => v * 0.5), 1));
  c.fillStyle = g;
  c.beginPath(); c.moveTo(x - w / 2, y - h); c.lineTo(x - w / 2, y); c.ellipse(x, y, w / 2, ry, 0, Math.PI, 0, true); c.lineTo(x + w / 2, y - h); c.ellipse(x, y - h, w / 2, ry, 0, 0, Math.PI, false); c.closePath(); c.fill();
  // rim lights on both edges from the window behind
  c.strokeStyle = rgba(light, 0.35 + 0.3 * (1 - lit)); c.lineWidth = 3;
  c.beginPath(); c.moveTo(x - w / 2 + 2, y - h + 4); c.lineTo(x - w / 2 + 2, y - 4); c.stroke();
  c.beginPath(); c.moveTo(x + w / 2 - 2, y - h + 4); c.lineTo(x + w / 2 - 2, y - 4); c.stroke();
  // top: the opening (upright) or the foot ring (upside down)
  if (up) {
    c.fillStyle = rgba(base.map((v) => v * 1.05), 1); c.beginPath(); c.ellipse(x, y - h, w / 2, ry, 0, 0, 6.283); c.fill();
    c.fillStyle = rgba(tintA([0.32, 0.2, 0.12], amb, 1), 1); c.beginPath(); c.ellipse(x, y - h + 3, w / 2 - 9, ry - 4, 0, 0, 6.283); c.fill();
  } else {
    c.fillStyle = rgba(base.map((v) => v * 0.92), 1); c.beginPath(); c.ellipse(x, y - h, w / 2, ry, 0, 0, 6.283); c.fill();
    c.strokeStyle = rgba(base.map((v) => v * 0.7), 1); c.lineWidth = 3; c.beginPath(); c.ellipse(x, y - h, w / 2 - 16, ry - 5, 0, 0, 6.283); c.stroke();
  }
  if (chip) {
    // a small notch in the rim, front left: at the top when upright, at the bottom when upside down
    const cx = x - w * 0.2, cy = up ? y - h + ry * 0.92 : y + ry * 0.9, d = up ? 1 : -1;
    c.fillStyle = rgba(base.map((v) => v * 0.38), 1);
    c.beginPath(); c.moveTo(cx - 24, cy); c.lineTo(cx - 6, cy + d * 26); c.lineTo(cx + 20, cy + d * 5); c.closePath(); c.fill();
    c.strokeStyle = rgba(light, 0.7); c.lineWidth = 2.5;
    c.beginPath(); c.moveTo(cx - 6, cy + d * 26); c.lineTo(cx + 20, cy + d * 5); c.stroke();
  }
  c.restore();
}

function kitchen(c, s, t, L, P) {
  const amb = ambient(L), sunny = (L.sun || 0) > 0.2;
  // tiled wall around a wide window
  c.fillStyle = tint(ALB.tile, amb, 0.8); c.fillRect(-300, -300, W + 600, 1000);
  c.strokeStyle = tint(ALB.tile, amb, 0.6); c.lineWidth = 2;
  for (let y = -300; y < 700; y += 46) {
    c.beginPath(); c.moveTo(-300, y); c.lineTo(W + 300, y); c.stroke();
    for (let x = -300 + (Math.round(y / 46) % 2 ? 46 : 0); x < W + 300; x += 92) { c.beginPath(); c.moveTo(x, y); c.lineTo(x, y + 46); c.stroke(); }
  }
  const win = [300, 20, 1620, 548];
  outside(c, win, 470, L, s, { moonAt: [0.56, 0.42], sunAt: [0.72, 0.18], cityScale: 1.5 });
  c.fillStyle = tint(ALB.wall, amb, 0.95);
  c.fillRect(win[0] - 14, win[1] - 14, win[2] - win[0] + 28, 16); c.fillRect(win[0] - 14, win[1], 16, win[3] - win[1]); c.fillRect(win[2] - 2, win[1], 16, win[3] - win[1]);
  c.fillRect(740, win[1], 12, win[3] - win[1]); c.fillRect(1170, win[1], 12, win[3] - win[1]);
  // the plant she left on the sill
  c.fillStyle = tint(ALB.pot, amb, 0.9); poly(c, [[1380, 548], [1470, 548], [1458, 470], [1392, 470]]); c.fill();
  for (let i = 0; i < 7; i++) {
    const a = -2.7 + i * 0.36 + Math.sin(s * 0.8 + i) * 0.02, L1 = 70 + 20 * N(i, 3);
    c.save(); c.translate(1425, 474); c.rotate(a);
    c.fillStyle = tint(ALB.leaf, amb, 0.62 + 0.1 * N(i, 5)); c.beginPath(); c.ellipse(L1 / 2, 0, L1 / 2, 12, 0, 0, 6.283); c.fill();
    c.strokeStyle = tint(ALB.leaf, amb, 0.4); c.lineWidth = 2; c.beginPath(); c.moveTo(0, 0); c.lineTo(L1 * 0.9, 0); c.stroke();
    c.restore();
  }
  // counter
  fillPoly(c, [[-300, 548], [W + 300, 548], [W + 300, 1500], [-300, 1500]], tint(ALB.counter, amb, 0.72));
  c.fillStyle = vgrad(c, 548, 1080, [[0, 'rgba(0,0,0,0.25)'], [0.3, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0.18)']]); c.fillRect(-300, 548, W + 600, 900);
  addLight(c, (g) => {
    g.globalAlpha = sunny ? 0.35 : 0.22; g.fillStyle = sunny ? 'rgb(255,226,180)' : 'rgb(120,140,210)';
    poly(g, [[300, 560], [1620, 560], [1800, 1000], [120, 1000]]); g.fill();
  }, 30);
  // the sink at the right, the faucet behind it (clear of the hands, which come from the left and right)
  fillPoly(c, [[1580, 588], [1960, 588], [1990, 680], [1556, 680]], tint(ALB.counter, amb, 0.42));
  c.fillStyle = tint(ALB.counter, amb, 0.9); c.fillRect(1556, 680, 434, 6);
  c.strokeStyle = tint([0.7, 0.72, 0.75], amb, 0.8); c.lineWidth = 24; c.lineCap = 'round';
  c.beginPath(); c.moveTo(1850, 584); c.lineTo(1850, 430); c.quadraticCurveTo(1850, 350, 1760, 350); c.lineTo(1716, 368); c.stroke();
  // the dish rack: tray, rails, wires. Only at night: in the dream the mugs are in use, not drying
  if (!P.up) {
    const rk = tintA(ALB.rack, amb, 1);
    fillPoly(c, [[520, 905], [1440, 905], [1470, 950], [490, 950]], rgba(rk.map((v) => v * 0.6), 1));
    c.strokeStyle = rgba(rk, 0.9); c.lineWidth = 6;
    for (const yy of [890, 760]) { c.beginPath(); c.moveTo(520, yy); c.lineTo(1440, yy); c.stroke(); }
    c.lineWidth = 4;
    for (let x = 540; x <= 1420; x += 40) { c.beginPath(); c.moveTo(x, 905); c.lineTo(x, 760 + (x % 80 ? 40 : 0)); c.stroke(); }
  }
  // the mugs
  const lit = sunny ? 0.6 : (L.ceil || 0);
  const light = sunny ? [255, 236, 200] : [170, 190, 240];
  if (P.up) {
    mug(c, 790, 895, { up: true, alb: ALB.mugBlue, amb, handle: -1, light, lit });
    mug(c, 1080, P.herY ?? 895, { up: true, alb: ALB.mugWhite, amb, chip: true, handle: 1, light, lit });
  } else {
    mug(c, 1080, 895, { up: false, alb: ALB.mugWhite, amb, chip: true, handle: 1, light, lit });
    if (P.his) mug(c, 790, P.his.y, { up: false, alb: ALB.mugBlue, amb, handle: -1, light, lit });
  }
  // water gathering on the rim of the mug he just washed and dripping onto the tray
  for (const [t0, dx] of P.drips || []) {
    const u = t - t0;
    if (u < 0 || u > 0.72) continue;
    const x = 790 + dx, grow = smooth(u / 0.4), fall = smooth((u - 0.4) / 0.14);
    if (fall < 1) {
      const y = lerp(918, 938, fall);
      c.fillStyle = rgba(light, 0.7); c.beginPath(); c.ellipse(x, y + 4 * grow, 3 + 3 * grow, 4 + 5 * grow * (1 + fall), 0, 0, 6.283); c.fill();
    } else {
      const k = (u - 0.54) / 0.18;
      c.strokeStyle = rgba(light, 0.55 * (1 - k)); c.lineWidth = 1.5;
      c.beginPath(); c.ellipse(x, 940, 4 + 26 * k, (4 + 26 * k) * 0.25, 0, 0, 6.283); c.stroke();
    }
  }
  // steam from the mugs in the dream
  if (P.steam) {
    c.save(); c.lineCap = 'round';
    for (const [mx, my, seed] of [[790, 650, 1], [1080, (P.herY ?? 895) - 245, 2]]) {
      for (let k = 0; k < 3; k++) {
        c.strokeStyle = `rgba(255,248,236,${0.16 * P.steam})`; c.lineWidth = 16 - k * 3;
        c.beginPath();
        for (let i = 0; i <= 20; i++) {
          const u = i / 20, yy = my - u * 260, xx = mx + (k - 1) * 22 + Math.sin(u * 6 + s * 2.2 + seed + k) * 18 * u;
          i ? c.lineTo(xx, yy) : c.moveTo(xx, yy);
        }
        c.stroke();
      }
    }
    c.restore();
  }
  if (L.ceil > 0.01) {
    addLight(c, (g) => { g.fillStyle = radial(g, 960, -200, 1300, [255, 210, 150], 0.35 * L.ceil); g.fillRect(-300, -300, W + 600, H + 600); });
  }
}

// ------------------------------------------------------------------ the balcony (a memory)
function balconySky(c, s, warm) {
  c.fillStyle = vgrad(c, -200, 1100, [[0, rgba(mix([8, 12, 34], [18, 14, 40], warm), 1)], [0.6, rgba(mix([26, 32, 70], [52, 36, 74], warm), 1)], [1, rgba(mix([64, 58, 92], [118, 72, 82], warm), 1)]]);
  c.fillRect(-300, -300, W + 600, H + 600);
  for (const st of STARS) {
    const a = (0.2 + 0.8 * st.b) * (0.7 + 0.3 * Math.sin(s * 1.7 + st.tw));
    c.fillStyle = `rgba(236,236,255,${a})`;
    c.fillRect(-200 + st.x * (W + 400), -200 + st.y * 900, 1.2 + 2.2 * st.b, 1.2 + 2.2 * st.b);
  }
}
function brightStar(c, x, y, s, k = 1) {
  const tw = 0.85 + 0.15 * Math.sin(s * 3.1);
  c.save(); c.globalCompositeOperation = 'screen';
  c.fillStyle = radial(c, x, y, 120 * k, [200, 214, 255], 0.55 * tw); c.fillRect(x - 130 * k, y - 130 * k, 260 * k, 260 * k);
  c.strokeStyle = `rgba(230,236,255,${0.5 * tw})`; c.lineWidth = 2;
  c.beginPath(); c.moveTo(x - 60 * k, y); c.lineTo(x + 60 * k, y); c.moveTo(x, y - 60 * k); c.lineTo(x, y + 60 * k); c.stroke();
  c.fillStyle = '#fff'; c.beginPath(); c.arc(x, y, 4.5 * k, 0, 6.283); c.fill();
  c.restore();
}
function cityBelow(c, s, hy) {
  c.save();
  for (const [depth, a] of [[0.4, 0.5], [0.7, 1]]) {
    for (const b of CITY) {
      const bx = -200 + (b.x / 2000) * (W + 400), bw = (b.w / 2000) * (W + 400), bh = b.h * depth;
      c.fillStyle = `rgba(14,12,26,${a})`; c.fillRect(bx, hy - bh, bw + 1, 600);
      if (depth > 0.5) for (let i = 0; i < b.lit.length; i++) {
        if (b.lit[i] > 0.4) continue;
        c.fillStyle = `rgba(255,${196 + 30 * b.lit[i]},130,0.85)`;
        c.fillRect(bx + 6 + (i % 5) * (bw - 10) / 5, hy - bh + 8 + Math.floor(i / 5) * 16, 4, 5);
      }
    }
  }
  c.fillStyle = vgrad(c, hy - 200, hy + 100, [[0, 'rgba(255,170,120,0)'], [1, 'rgba(255,170,120,0.18)']]); c.fillRect(-300, hy - 200, W + 600, 400);
  c.restore();
}
function railing(c, y, col) {
  c.fillStyle = col; c.fillRect(-300, y, W + 600, 22);
  for (let x = -280; x < W + 300; x += 64) c.fillRect(x, y + 22, 10, 600);
  c.fillRect(-300, y + 300, W + 600, 14);
}

// They stand on the balcony floor in front of the railing, the city below beyond it
function balconyWide(c, s, t) {
  balconySky(c, s, 0.6);
  brightStar(c, 1510, 210, s, 1 + 0.25 * smooth((t - 19.8) / 0.8));
  cityBelow(c, s, 900);
  railing(c, 800, '#09080f');
  const reach = smooth((t - 19.5) / 1.1);
  const dark = '#0b0a12';
  rimmed(c, (g) => back(g, 760, 560, 1.25, { hair: 'short', turn: 0.25, len: 700 }), dark, 'rgba(255,170,130,0.5)', [0, -3]);
  rimmed(c, (g) => { back(g, 1060, 580, 1.15, { hair: 'long', raise: reach, turn: 0.2, len: 700 }); pointingArm(g, 1060, 580, 1.15, { reach }); }, dark, 'rgba(255,170,130,0.5)', [0, -3]);
}

// closer, still from behind: she keeps pointing; he turns his head from the star to her
function balconyClose(c, s, t) {
  balconySky(c, s, 0.6);
  brightStar(c, 1790, 120, s, 0.8);
  cityBelow(c, s, 1060);
  railing(c, 900, '#09080f');
  const look = smooth((t - (CUT.turn + 1.3)) / 0.9);
  const dark = '#0b0a12', rim = 'rgba(210,190,255,0.72)';
  rimmed(c, (g) => { back(g, 1250, 700, 2.3, { hair: 'long', raise: 1, turn: 0.3, len: 700 }); pointingArm(g, 1250, 700, 2.3, { reach: 1, up: [-1.0, -1.15] }); }, dark, rim, [-3, 3]);
  rimmed(c, (g) => { back(g, 620, 760, 2.6, { hair: 'short', head: false, len: 700 }); headTurn(g, 620, 760, 2.6, look, { tilt: -0.04 }); }, dark, rim, [-3, 3]);
}

// ------------------------------------------------------------------ her, close, in the dream; then gone
// She is drawn on her own layer so she can soften and thin into the light as one shape
const HER = layer(W, H), herCtx = HER.getContext('2d');
function herClose(c, s, t) {
  const cool = smooth((t - (CUT.fade + 1.2)) / 2.6);              // the light cools toward dawn
  const gone = smooth((t - (CUT.fade + 2.0)) / 2.2);              // and she thins into it
  const L = { ...L0, sun: 1 - cool, dawn: cool };
  const amb = ambient(L);
  c.fillStyle = tint(ALB.wall, amb, 0.8); c.fillRect(-300, -300, W + 600, H + 600);
  const win = [640, -60, 1820, 820];
  outside(c, win, 820, L, s, { sunAt: [0.55, 0.18], cityScale: 0.5 });
  c.fillStyle = tint(ALB.wall, amb, 1); c.fillRect(1214, win[1], 18, win[3] - win[1]); c.fillRect(win[0], 200, win[2] - win[0], 16);
  c.fillRect(win[0] - 20, win[3], win[2] - win[0] + 40, 22);
  c.fillStyle = tint(ALB.wood, amb, 0.8); c.fillRect(-300, 842, W + 600, 300);
  addLight(c, (g) => { g.fillStyle = radial(g, 1250, 360, 1000, cool > 0.5 ? [200, 214, 240] : [255, 236, 200], 0.35 + 0.45 * gone); g.fillRect(-300, -300, W + 600, H + 600); });
  const smile = smooth((t - CUT.fade - 0.3) / 0.6) * (1 - smooth((t - CUT.fade - 1.7) / 0.9));   // one small lift of the head
  herCtx.setTransform(1, 0, 0, 1, 0, 0); herCtx.clearRect(0, 0, W, H); herCtx.setTransform(c.getTransform());
  rimmed(herCtx, (g) => profile(g, 1150, 650, 2.3, { dir: -1, tilt: -0.05 - smile * 0.07, hair: 'long', body: 260 }),
    tint(ALB.hair, amb, 1.4), cool > 0.5 ? 'rgba(220,230,255,1)' : 'rgba(255,228,190,1)', [-3, 6]);
  // the light takes her: her shape fills with the window's light first, and only then goes
  herCtx.save(); herCtx.setTransform(1, 0, 0, 1, 0, 0); herCtx.globalCompositeOperation = 'source-atop';
  herCtx.fillStyle = rgba(mix([255, 236, 206], [214, 224, 244], cool), 0.92 * smooth(gone / 0.7)); herCtx.fillRect(0, 0, W, H);
  herCtx.restore();
  const fade = smooth((gone - 0.55) / 0.45);
  if (fade < 1) {
    c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = 1 - fade; c.filter = `blur(${(gone * 16).toFixed(2)}px)`;
    c.drawImage(HER, 0, 0); c.restore();
  }
  // the blanket over her lap
  c.fillStyle = tint(ALB.blanket, amb, 0.85);
  c.beginPath(); c.moveTo(-300, 1000); c.bezierCurveTo(500, 960, 900, 930, 1150, 950); c.bezierCurveTo(1450, 970, 1800, 990, 2220, 1010); c.lineTo(2220, 1400); c.lineTo(-300, 1400); c.closePath(); c.fill();
  // his shoulder and the back of his head in the near foreground, out of focus
  c.save(); c.filter = 'blur(9px)';
  c.beginPath(); back(c, 200, 900, 3.4, { hair: 'short', turn: 0.8 }); c.fillStyle = '#0d0a09'; c.fill();
  c.restore();
}

// ------------------------------------------------------------------ her lamp, close; he turns it on
function lampClose(c, s, t) {
  const on = smooth((t - CUT.click) / 0.12);
  const L = { ...L0, dawn: 1, lamp: on };
  const amb = ambient({ ...L, lamp: 0 });
  c.fillStyle = tint(ALB.wall, amb, 0.75); c.fillRect(-300, -300, W + 600, H + 600);
  outside(c, [1240, -40, 2000, 700], 640, { ...L0, dawn: 1 }, s, { cityScale: 1.6 });
  c.fillStyle = tint(ALB.wall, amb, 0.95); c.fillRect(1226, -40, 18, 760); c.fillRect(1200, 700, 900, 20);
  for (let x = 1120; x < 1240; x += 6) { c.fillStyle = tint(ALB.curtain, amb, 0.7 + 0.3 * Math.sin(x * 0.18)); c.fillRect(x, -60, 6.5, 900); }
  fillPoly(c, [[-300, 760], [W + 300, 760], [W + 300, 1500], [-300, 1500]], tint(ALB.wood, amb, 0.85));
  c.fillStyle = tint(ALB.wood, amb, 1.1); c.fillRect(-300, 760, W + 600, 10);
  // the lamp: ceramic base, stem, shade
  const g = c.createLinearGradient(820, 0, 1060, 0);
  const base = tintA([0.86, 0.84, 0.8], amb, 1);
  g.addColorStop(0, rgba(base.map((v) => v * 0.6), 1)); g.addColorStop(0.4, rgba(base, 1)); g.addColorStop(1, rgba(base.map((v) => v * 0.5), 1));
  c.fillStyle = g; c.beginPath(); c.ellipse(940, 790, 120, 24, 0, 0, 6.283); c.fill();
  c.beginPath(); c.moveTo(830, 790); c.bezierCurveTo(820, 640, 880, 560, 920, 470); c.lineTo(960, 470); c.bezierCurveTo(1000, 560, 1060, 640, 1050, 790); c.closePath(); c.fill();
  c.fillStyle = tint(ALB.wood, amb, 0.5); c.fillRect(932, 280, 16, 200);
  const shadeP = [[760, 40], [1120, 40], [1220, 330], [660, 330]];
  fillPoly(c, shadeP, tint(ALB.shade, amb, 0.8));
  c.fillStyle = tint([0.3, 0.28, 0.27], amb, 1); c.beginPath(); c.ellipse(1010, 742, 18, 9, 0, 0, 6.283); c.fill();
  // his hand comes in from the left and presses the switch
  const reach = smooth((t - (CUT.lamp + 0.1)) / 0.8), press = Math.exp(-(((t - CUT.click + 0.06) / 0.1) ** 2));
  hand(c, { x: lerp(-500, 700, reach), y: lerp(760, 690, reach) + 10 * press, s: 1.7, rot: 0.08, palm: false, curl: lerp(0.4, 0.2, reach),
    skin: tintA(ALB.skin, ambient({ ...L, lamp: on * 0.6 }), 0.9), light: [200, 210, 240], sleeve: tintA(ALB.sleeve, amb, 0.9), shadow: 0.3 });
  if (on > 0) {
    addLight(c, (gg) => { gg.fillStyle = radial(gg, 940, 330, 1100, [255, 168, 88], 0.85 * on); gg.fillRect(-300, -300, W + 600, H + 600); });
    fillPoly(c, shadeP, `rgba(255,222,168,${0.92 * on})`);
    addLight(c, (gg) => { gg.fillStyle = radial(gg, 940, 340, 260, [255, 240, 210], on); gg.fillRect(600, 100, 700, 500); });
  }
}

// ------------------------------------------------------------------ shots
const cam = (x, y, z) => ({ x, y, z });
const SHOTS = [
  // S1: the kitchen at night. He sets his mug to dry beside hers, upside down where it has stood for months; the light goes off
  { a: 0, glow: 0.35, draw(s, t) {
    const down = smooth((t - 0.3) / 1.6), lift = smooth((t - 2.2) / 0.6);
    const off = smooth((t - beat(5.5)) / 0.08);
    const L = { ...L0, ceil: 1 - off, moon: 0.35 + 0.65 * off };
    view(ctx, cam(40, 130, kf(t, [[0, 1.0], [6, 1.04]])), 1, (c) => {
      const my = lerp(700, 895, down);
      kitchen(c, s, t, L, { up: false, his: { y: my }, drips: [[3.25, -60], [4.15, 30], [4.95, -22]] });
      if (lift < 1) {
        // the knuckles on the handle; letting go, the hand withdraws along the line of the forearm
        const D = lerp(0, 900, lift), hx = 533 - 0.81 * D, hy = my - 185 - 0.58 * D;
        const curl = lerp(0.88, 0.35, smooth((t - 2.0) / 0.4));
        hand(c, { x: hx, y: hy, s: 1.1, rot: 0.62, palm: false, curl,
          skin: tintA(ALB.skin, ambient(L), 0.95), light: [255, 220, 180], sleeve: tintA(ALB.sleeve, ambient(L), 1), shadow: 0.2 });
        mugHandle(c, 790, my, { alb: ALB.mugBlue, amb: ambient(L), handle: -1, alpha: smooth((curl - 0.5) / 0.2) });
      }
    });
  } },
  // S2: the bedroom at night. He lies on his side facing her side and lays his hand on her pillow
  { a: CUT.bed, glow: 0.35, draw(s, t) {
    const arm = smooth((t - 8.2) / 1.1);
    view(ctx, cam(-30, 10, kf(t, [[CUT.bed, 1.0], [CUT.close, 1.035, ease.inOut]])), 1, (c) => bedroom(c, s, { ...L0, moon: 1 }, { him: 'side', arm }));
  } },
  // S3: close on his open hand on her flat pillow. It closes into a fist, on nothing
  { a: CUT.close, glow: 0.3, draw(s, t) {
    view(ctx, cam(0, 0, kf(t, [[CUT.close, 1.0], [CUT.dream, 1.03]])), 1, (c) => pillowClose(c, s, { ...L0, moon: 1 }, t, { curl: lerp(0.1, 1.5, smooth((t - 10.5) / 1.3)) }));
  } },
  // S4: the same frame in morning light. The fist opens, her hand slides into it, and his fingers close over hers
  { a: CUT.dream, glow: 0.55, draw(s, t) {
    const open = smooth((t - CUT.dream) / 0.45), her = smooth((t - 12.4) / 0.8), close = smooth((t - 13.35) / 0.55);
    const curl = close > 0 ? lerp(0.15, 0.8, close) : lerp(1.5, 0.15, open);
    view(ctx, cam(0, 0, kf(t, [[CUT.dream, 1.03], [CUT.together, 1.05]])), 1, (c) => pillowClose(c, s, { ...L0, sun: 1 }, t, { her, curl, close }));
  } },
  // S5: framing A in the dream. She is there, sitting up, laughing once; he is propped on an elbow facing her
  { a: CUT.together, glow: 0.6, draw(s, t) {
    const laugh = smooth((t - CUT.together - 0.4) / 0.5) * (1 - smooth((t - CUT.together - 1.3) / 0.6));
    view(ctx, cam(-10, 0, kf(t, [[CUT.together, 1.03], [CUT.mugs, 1.0, ease.out]])), 1,
      (c) => bedroom(c, s, { ...L0, sun: 1 }, { him: 'propped', her: true, herA: 1, laugh, dent: 0.6 }));
  } },
  // S6: the kitchen in the dream, the same frame as S1. Both mugs upright and steaming; she picks hers up
  { a: CUT.mugs, glow: 0.55, draw(s, t) {
    const reach = smooth((t - 16.6) / 0.8), lift = smooth((t - 17.9) / 1.0);
    const L = { ...L0, sun: 1 };
    view(ctx, cam(40, 130, kf(t, [[CUT.mugs, 1.04], [CUT.balcony, 1.0]])), 1, (c) => {
      const my = 895 - 260 * lift;
      kitchen(c, s, t, L, { up: true, steam: 1, herY: my });
      // her knuckles on the handle's curve, the fingers through it, then the mug comes up with the hand
      const curl = lerp(0.3, 0.88, smooth((t - 17.3) / 0.4));
      hand(c, { x: lerp(2100, 1345, reach), y: lerp(420, my - 180, reach), s: 1.1, rot: Math.PI - 0.62, side: -1, palm: false, curl,
        skin: tintA([0.9, 0.72, 0.6], ambient(L), 0.95), light: [255, 236, 200], sleeve: tintA(ALB.herSleeve, ambient(L), 0.9), shadow: 0.2 });
      mugHandle(c, 1080, my, { alb: ALB.mugWhite, amb: ambient(L), handle: 1, alpha: smooth((curl - 0.5) / 0.2) });
    });
  } },
  // S7: the balcony, a memory. She points at the brightest star
  { a: CUT.balcony, glow: 0.45, draw(s, t) {
    view(ctx, cam(0, -20, kf(t, [[CUT.balcony, 1.0], [CUT.turn, 1.04]])), 1, (c) => balconyWide(c, s, t));
  } },
  // S8: closer, still from behind. She keeps pointing; he turns his head from the star to her
  { a: CUT.turn, glow: 0.45, draw(s, t) {
    view(ctx, cam(0, 0, kf(t, [[CUT.turn, 1.0], [CUT.fade, 1.03]])), 1, (c) => balconyClose(c, s, t));
  } },
  // S9: back in the dream, close on her against the window. The light cools and she thins into it
  { a: CUT.fade, glow: 0.7, draw(s, t) {
    view(ctx, cam(40, 0, kf(t, [[CUT.fade, 1.0], [CUT.dawn, 1.06, ease.inOut]])), 1, (c) => herClose(c, s, t));
  } },
  // S10: framing A at dawn. Her pillow is flat; he lies still, awake
  { a: CUT.dawn, glow: 0.25, draw(s, t) {
    view(ctx, cam(-30, 10, kf(t, [[CUT.dawn, 1.0], [CUT.lamp, 1.025]])), 1, (c) => bedroom(c, s, { ...L0, dawn: 1 }, { him: 'back' }));
  } },
  // S11: her lamp, close. His hand reaches over and presses the switch, so he won't fall asleep again
  { a: CUT.lamp, glow: 0.45, draw(s, t) {
    view(ctx, cam(0, 0, kf(t, [[CUT.lamp, 1.0], [CUT.click, 1.03]])), 1, (c) => lampClose(c, s, t));
  } },
  // S12: cut on the click to framing A, the lamp on in the cold room. He pushes up to sit and looks down at her pillow
  { a: CUT.click, glow: 0.4, draw(s, t) {
    const rise = smooth((t - (CUT.click + 0.2)) / 0.8);
    view(ctx, cam(-30, 10, kf(t, [[CUT.click, 1.0], [DUR, 1.025]])), 1, (c) => bedroom(c, s, { ...L0, dawn: 1, lamp: 1 }, { him: 'sit', rise }));
  } },
].map((x, i, all) => ({ ...x, b: all[i + 1] ? all[i + 1].a : DUR }));

// ------------------------------------------------------------------ subtitles (lyrics.mjs; see music-video.md)
const box = document.getElementById('lyric'), en = document.getElementById('lyric-en'), zh = document.getElementById('lyric-zh');
function drawLyrics(t) {
  const cue = cues.find((q) => q.start <= t && t < q.end);
  const [a = '', b = ''] = cue ? cue.text.split('\n') : [];
  en.textContent = a; zh.textContent = b;
  const edge = cue ? Math.min(t - cue.start, cue.end - t) : 0;
  box.style.opacity = Math.min(1, edge / 0.15);
}

function seek(t) {
  const s = T0 + t;
  const shot = SHOTS.find((x) => t >= x.a && t < x.b) || SHOTS[SHOTS.length - 1];
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.filter = 'none';
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  shot.draw(s, t);
  ctx.restore();
  glowPass(shot.glow);
  finish(ctx, Math.round(t * FPS), { vignette: 0.45, grain: 0.06 });
  const fadeIn = clamp(t / 0.4), out = clamp((DUR - t) / 0.3);
  if (fadeIn * out < 1) { ctx.fillStyle = `rgba(0,0,0,${1 - fadeIn * out})`; ctx.fillRect(0, 0, W, H); }
  drawLyrics(t);
}

register({ duration: DUR, fps: FPS, width: W, height: H, seek, meta: { T0, cuts: CUT, shots: SHOTS.map((x) => [x.a, x.b]) } });
seek(0);
