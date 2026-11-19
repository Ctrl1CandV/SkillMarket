// People for time machine · dream. Everyone is a silhouette or a pair of hands: profiles against a
// window or the sky, backs at a railing, hands on a pillow or round a mug. Each function only builds
// a path (or draws a hand on a layer) so the scene decides the colour and the light.
import { clamp, lerp } from '../../../../video-craft/kit/kit.js';
import { layer } from '../../../../video-craft/kit/draw.js';

// a limb as one clockwise sub-path: a tapered capsule from p (half-width w0) to q (half-width w1)
export function capsule(c, p, q, w0, w1) {
  const d = [q[0] - p[0], q[1] - p[1]], L = Math.hypot(...d) || 1, n = [-d[1] / L, d[0] / L];
  c.moveTo(p[0] - n[0] * w0, p[1] - n[1] * w0); c.lineTo(q[0] - n[0] * w1, q[1] - n[1] * w1);
  c.arc(q[0], q[1], w1, Math.atan2(-n[1], -n[0]), Math.atan2(n[1], n[0]));
  c.lineTo(p[0] + n[0] * w0, p[1] + n[1] * w0);
  c.arc(p[0], p[1], w0, Math.atan2(n[1], n[0]), Math.atan2(-n[1], -n[0]));
  c.closePath();
}

// ------------------------------------------------------------------ profile, facing right (dir -1 faces left)
// Origin is the neck pivot (where the head turns). One unit is about 1/270 of the figure's head-to-chest height.
// tilt: radians, negative looks up. hair: 'short' or 'long'. open: mouth open 0..1 (laughing).
// arm: none, 'down' (forearm resting forward, as when sitting in bed) or 'hold' (hand at the chest).
export function profile(c, x, y, k, { dir = 1, tilt = 0, hair = 'short', open = 0, torso = true, body = 175, arm = null } = {}) {
  c.save(); c.translate(x, y); c.scale(k * dir, k);
  if (torso) {
    // a neck about half the head's depth, the trapezius sloping into the back, the chest in front
    c.moveTo(10, -10);
    c.lineTo(12, 26);
    c.bezierCurveTo(20, 44, 38, 58, 46, 92);
    c.lineTo(50, body); c.lineTo(-82, body); c.lineTo(-86, 96);
    c.bezierCurveTo(-86, 62, -70, 44, -44, 36);
    c.bezierCurveTo(-32, 24, -30, 6, -34, -12);
    c.closePath();
    if (arm === 'down' || arm === 'lap') {
      capsule(c, [-16, 52], [-6, 162], 24, 19);
      capsule(c, [-6, 162], [80, 178], 18, 14);
      c.moveTo(118, 182); c.ellipse(98, 182, 20, 12, 0.1, 0, 6.283);
    } else if (arm === 'hold') {
      capsule(c, [-16, 52], [-8, 150], 24, 19);
      capsule(c, [-8, 150], [64, 104], 18, 14);
      c.moveTo(94, 96); c.ellipse(76, 98, 18, 13, -0.5, 0, 6.283);
    }
  }
  c.rotate(tilt);
  // head
  const m = open * 6;
  c.moveTo(-8, -132);
  c.bezierCurveTo(30, -134, 50, -114, 52, -92);
  c.bezierCurveTo(53, -84, 55, -80, 54, -76);
  c.bezierCurveTo(60, -64, 66, -56, 68, -50);
  c.bezierCurveTo(64, -47, 59, -46, 56, -45);
  c.bezierCurveTo(58, -42, 58, -39, 56, -37);
  c.lineTo(54 - m * 0.5, -35 + m * 0.3);
  c.bezierCurveTo(57, -33 + m, 57, -29 + m, 54, -27 + m);
  c.lineTo(51, -24 + m);
  c.bezierCurveTo(54, -18 + m, 50, -12 + m, 40, -10 + m);
  c.bezierCurveTo(28, -8 + m, 18, -6, 14, 2);
  c.lineTo(-36, -6);
  c.bezierCurveTo(-56, -24, -66, -70, -56, -100);
  c.bezierCurveTo(-48, -122, -30, -132, -8, -132);
  c.closePath();
  if (hair === 'short') {
    c.moveTo(-12, -137);
    c.bezierCurveTo(26, -142, 50, -126, 54, -104);
    c.bezierCurveTo(40, -112, 6, -116, -24, -104);
    c.bezierCurveTo(-44, -96, -58, -84, -62, -66);
    c.bezierCurveTo(-68, -96, -50, -134, -12, -137);
    c.closePath();
  } else if (hair === 'long') {
    c.moveTo(-10, -138);
    c.bezierCurveTo(30, -144, 54, -124, 54, -102);
    c.bezierCurveTo(46, -108, 30, -110, 20, -108);
    c.bezierCurveTo(-10, -104, -30, -90, -36, -60);
    c.bezierCurveTo(-40, -30, -30, 20, -22, 60);
    c.bezierCurveTo(-36, 92, -70, 100, -92, 84);
    c.bezierCurveTo(-78, 50, -78, 10, -74, -40);
    c.bezierCurveTo(-72, -100, -48, -136, -10, -138);
    c.closePath();
  }
  c.restore();
}

// ------------------------------------------------------------------ seen from behind, standing (balcony)
// Origin at the base of the neck; the body runs down to y `len` (below the frame or behind the railing).
// All sub-paths run clockwise so one fill() unions them. turn: -1..1 shifts the head toward screen
// left/right; head: false leaves the head out (the caller draws a turning head with headTurn()).
export function back(c, x, y, k, { hair = 'short', turn = 0, lean = 0, raise = 0, len = 340, head = true } = {}) {
  const her = hair === 'long', sw = her ? 88 : 108, hw = her ? 40 : 45, hh = her ? 52 : 57;
  c.save(); c.translate(x, y); c.rotate(lean); c.scale(k, k);
  // torso: trapezius slope from the neck to the shoulder points, the back narrowing to the waist
  c.moveTo(22, -14);
  c.bezierCurveTo(30, 4, sw * 0.8, 12, sw, 34 - raise * 16);
  c.bezierCurveTo(sw + 4, 60, sw - 10, 110, sw - 18, 150);
  c.lineTo(sw - 26, len); c.lineTo(-sw + 26, len); c.lineTo(-sw + 18, 150);
  c.bezierCurveTo(-sw + 10, 110, -sw - 4, 60, -sw, 34);
  c.bezierCurveTo(-sw * 0.8, 12, -30, 4, -22, -14);
  c.closePath();
  // arms hanging, a sliver of light between arm and waist (the right one is skipped when raised)
  const al = Math.min(len, 330);
  for (const sd of raise > 0 ? [-1] : [-1, 1]) {
    c.moveTo(sd * (sw - 6), 36);
    if (sd < 0) {
      c.lineTo(-sw + 10, 160); c.lineTo(-sw + 14, al); c.lineTo(-sw - 8, al); c.lineTo(-sw - 16, 180);
      c.bezierCurveTo(-sw - 22, 110, -sw - 22, 50, -(sw - 6), 36); c.closePath();
    } else {
      c.bezierCurveTo(sw + 22, 50, sw + 22, 110, sw + 16, 180);
      c.lineTo(sw + 8, al); c.lineTo(sw - 14, al); c.lineTo(sw - 10, 160); c.closePath();
    }
    c.moveTo(sd * (sw + 3) + 15, al); c.ellipse(sd * (sw + 3), al, 15, 24, 0, 0, 6.283);   // the hand
  }
  // neck
  c.moveTo(-18, -44); c.lineTo(18, -44); c.lineTo(22, -8); c.lineTo(-22, -8); c.closePath();
  if (!head) { c.restore(); return; }
  // head and ears; turning shifts the head and shows one ear more
  const hx = turn * 10;
  c.moveTo(hx + hw, -64); c.ellipse(hx, -64, hw - Math.abs(turn) * 3, hh, 0, 0, 6.283);
  for (const sd of [-1, 1]) {
    const ex = hx + sd * (hw - 3 + (sd === Math.sign(turn) ? -4 : 2) * Math.abs(turn));
    c.moveTo(ex + 9, -60); c.ellipse(ex, -60, 9, 15, 0, 0, 6.283);
  }
  if (her) {
    // hair falling over the shoulders to the shoulder blades, slightly uneven at the ends
    c.moveTo(hx - 6, -122);
    c.bezierCurveTo(hx + 40, -122, hx + 52, -90, hx + 50, -50);
    c.bezierCurveTo(hx + 50, -10, 56, 40, 58, 92);
    c.bezierCurveTo(44, 104, 30, 98, 18, 108);
    c.bezierCurveTo(4, 100, -8, 110, -22, 104);
    c.bezierCurveTo(-36, 98, -46, 106, -58, 94);
    c.bezierCurveTo(-56, 40, -50, -10, hx - 50, -50);
    c.bezierCurveTo(hx - 52, -92, hx - 40, -122, hx - 6, -122);
    c.closePath();
  } else {
    c.moveTo(hx - 4, -124);
    c.bezierCurveTo(hx + 36, -126, hx + 50, -100, hx + 47, -66);
    c.lineTo(hx - 47, -66);
    c.bezierCurveTo(hx - 50, -100, hx - 40, -124, hx - 4, -124);
    c.closePath();
  }
  c.restore();
}

// the right arm raised toward the sky, pointing; reach 0 hangs down, 1 points up and out. The upper arm
// leads and the forearm follows, so the elbow bends on the way up.
// Builds clockwise sub-paths in the same frame as back() (call with the same x, y, k).
export function pointingArm(c, x, y, k, { reach = 1, sw = 88, up = [-1.05, -1.25] } = {}) {
  const r = clamp(reach), e = (v) => v * v * (3 - 2 * v);
  const sh = [sw - 10, 40];
  const a1 = lerp(1.62, up[0], e(clamp(r / 0.85))), a2 = lerp(1.6, up[1], e(clamp((r - 0.1) / 0.9)));
  const el = [sh[0] + Math.cos(a1) * 120, sh[1] + Math.sin(a1) * 120];
  const wr = [el[0] + Math.cos(a2) * 112, el[1] + Math.sin(a2) * 112];
  c.save(); c.translate(x, y); c.scale(k, k);
  capsule(c, sh, el, 25, 20);
  capsule(c, el, wr, 20, 14);
  // the hand: folded fingers along the far side, the index finger out along the forearm
  const fx = Math.cos(a2), fy = Math.sin(a2), nx = -fy, ny = fx;
  const fist = [wr[0] + fx * 20, wr[1] + fy * 20];
  c.moveTo(fist[0] + 21, fist[1]); c.ellipse(fist[0], fist[1], 21, 15, a2, 0, 6.283);
  for (let i = 0; i < 3; i++) {
    const kx = fist[0] + fx * (2 - i * 9) + nx * 13, ky = fist[1] + fy * (2 - i * 9) + ny * 13;
    c.moveTo(kx + 7, ky); c.arc(kx, ky, 7, 0, 6.283);
  }
  capsule(c, [fist[0] + fx * 10 - nx * 5, fist[1] + fy * 10 - ny * 5], [fist[0] + fx * 50 - nx * 7, fist[1] + fy * 50 - ny * 7], 6.5, 4.5);
  c.restore();
  return [x + (fist[0] + fx * 54) * k, y + (fist[1] + fy * 54) * k];
}

// a head seen from behind that turns to show its profile: turn 0 faces away (an oval), 1 faces screen
// right in profile. Same frame as back() with head: false.
// The ears are visible at the sides only while the head faces away. The profile is scaled to the oval's
// height and squeezed in x by turn, so the face comes past the oval's edge only late in the turn.
export function headTurn(c, x, y, k, turn, { hair = 'short', tilt = 0 } = {}) {
  // The far ear goes first and the near one slides in slowly, so the turn has a direction from its first frame
  const u = clamp(turn), hw = 45 - 8 * u, ox = -6 * u, s3 = (v) => v * v * (3 - 2 * v);
  const far = lerp(42, 18, s3(clamp(u / 0.35))), near = lerp(42, 14, u);
  c.save(); c.translate(x, y); c.scale(k, k);
  c.moveTo(ox + hw, -64); c.ellipse(ox, -64, hw, 57, 0, 0, 6.283);
  c.moveTo(ox - far + 9, -60); c.ellipse(ox - far, -60, 9, 15, 0, 0, 6.283);
  c.moveTo(ox + near + 9, -60); c.ellipse(ox + near, -60, 9, 15, 0, 0, 6.283);
  c.restore();
  if (u > 0.02) {
    c.save(); c.translate(x, y); c.scale(lerp(0.55, 1, u), 1);
    profile(c, 0, -10 * k, k * 0.82, { torso: false, tilt, hair });
    c.restore();
  }
}

// ------------------------------------------------------------------ hands, seen from above
// A hand is drawn on its own layer: solid shape first, then shading kept inside it (source-atop).
// Local frame: wrist at the origin, fingers along +x; one unit ~ 1/100 of the palm's length.
// side: +1 thumb toward -y (screen up when rot 0), -1 thumb toward +y. palm: true shows the palm.
// curl 0..1 per finger [thumb, index, middle, ring, little] or one number; spread widens the fan.
const FING = [
  { at: [98, -32], len: [44, 26, 20], w: 21, a: -0.12 },
  { at: [103, -10], len: [49, 30, 22], w: 22, a: -0.03 },
  { at: [99, 12], len: [45, 28, 21], w: 20.5, a: 0.06 },
  { at: [90, 32], len: [34, 22, 18], w: 17.5, a: 0.17 },
];

function fingerPoints(f, curl, spread) {
  // curl foreshortens the finger seen from above and swings the tip a little toward the palm centre;
  // past about 1 the outer joints fold back over the palm (a fist)
  const pts = [f.at];
  let ang = f.a * spread, x = f.at[0], y = f.at[1];
  f.len.forEach((L, j) => {
    const fs = Math.cos(curl * (0.5 + j * 0.35) * 1.45);
    ang += curl * f.a * -0.6;
    x += Math.cos(ang) * L * Math.max(-0.85, fs); y += Math.sin(ang) * L * Math.max(-0.85, fs);
    pts.push([x, y]);
  });
  return pts;
}

// arm: how far the forearm runs back from the wrist (long enough to leave the frame in close-ups)
export function handShape(c, { curl = 0.15, spread = 1, side = 1, sleeve = 0, fingersOnly = false, arm = 1000 } = {}) {
  const cl = Array.isArray(curl) ? curl : [curl, curl, curl, curl, curl];
  if (fingersOnly) {
    c.lineCap = 'round'; c.strokeStyle = c.fillStyle;
    const tips = FING.map((f, i) => {
      const pts = fingerPoints(f, cl[i + 1], spread);
      for (let j = 0; j < 3; j++) { c.lineWidth = f.w * (1 - j * 0.07); c.beginPath(); c.moveTo(...pts[j]); c.lineTo(...pts[j + 1]); c.stroke(); }
      return pts[3];
    });
    return { tips, thumb: null };
  }
  // palm: wrist, the little-finger edge, the knuckles, the thumb's base
  c.beginPath();
  c.moveTo(-6, -38);
  c.bezierCurveTo(20, -44, 60, -46, 96, -42);
  c.bezierCurveTo(106, -30, 108, 0, 104, 18);
  c.bezierCurveTo(100, 34, 96, 44, 84, 46);
  c.bezierCurveTo(60, 50, 26, 46, -6, 40);
  c.closePath();
  c.fill();
  // forearm
  c.beginPath(); c.moveTo(-6, -38); c.lineTo(-arm, -38 - arm * 0.018); c.lineTo(-arm, 40 + arm * 0.016); c.lineTo(-6, 40); c.closePath(); c.fill();
  // fingers: tapering round-capped segments
  c.lineCap = 'round'; c.strokeStyle = c.fillStyle;
  FING.forEach((f, i) => {
    const pts = fingerPoints(f, cl[i + 1], spread);
    for (let j = 0; j < 3; j++) {
      c.lineWidth = f.w * (1 - j * 0.07);
      c.beginPath(); c.moveTo(...pts[j]); c.lineTo(...pts[j + 1]); c.stroke();
    }
  });
  // thumb: from the base of the palm, out and forward
  const tc = cl[0];
  const tb = [24, -34], ta = -0.62 - 0.25 * spread + tc * 0.5;
  const t1 = [tb[0] + Math.cos(ta) * 44, tb[1] + Math.sin(ta) * 44];
  const t2 = [t1[0] + Math.cos(ta + 0.25 + tc * 0.6) * 32, t1[1] + Math.sin(ta + 0.25 + tc * 0.6) * 32];
  const t3 = [t2[0] + Math.cos(ta + 0.4 + tc * 1.0) * 24, t2[1] + Math.sin(ta + 0.4 + tc * 1.0) * 24];
  c.lineWidth = 30; c.beginPath(); c.moveTo(...tb); c.lineTo(...t1); c.stroke();
  c.lineWidth = 23; c.beginPath(); c.moveTo(...t1); c.lineTo(...t2); c.stroke();
  c.lineWidth = 21; c.beginPath(); c.moveTo(...t2); c.lineTo(...t3); c.stroke();
  // the fleshy base of the thumb
  c.beginPath(); c.ellipse(36, -26, 40, 22, -0.35, 0, 6.283); c.fill();
  if (sleeve) {
    c.save(); c.fillStyle = sleeve;
    c.beginPath(); c.moveTo(-70, -54); c.bezierCurveTo(-60, -20, -60, 20, -74, 56); c.lineTo(-1000, 70); c.lineTo(-1000, -70); c.closePath(); c.fill();
    c.restore();
  }
  return { tips: FING.map((f, i) => fingerPoints(f, cl[i + 1], spread)[3]), thumb: t3 };
}

// draw a hand with shading. o: {x, y, s, rot, side, palm, curl, spread, skin:[r,g,b], light:[r,g,b], dark, sleeve}
const HL = new Map();
export function hand(ctx, o) {
  const { x, y, s = 1, rot = 0, side = 1, palm = false, skin, light = [255, 255, 255], lightDir = -Math.PI / 2, sleeve } = o;
  const key = ctx.canvas.width + 'x' + ctx.canvas.height;
  if (!HL.has(key)) HL.set(key, layer(ctx.canvas.width, ctx.canvas.height));
  const L = HL.get(key), g = L.getContext('2d');
  g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, L.width, L.height);
  const T = ctx.getTransform();
  g.setTransform(T); g.translate(x, y); g.rotate(rot); g.scale(s, s * side);
  g.fillStyle = `rgb(${skin.join(',')})`;
  const geo = handShape(g, { curl: o.curl, spread: o.spread, side, fingersOnly: o.fingersOnly, arm: o.arm, sleeve: sleeve && `rgb(${sleeve.join(',')})` });
  // shading inside the shape: a soft gradient across the hand, darker toward the far edge
  g.globalCompositeOperation = 'source-atop';
  const sg = Math.sin(lightDir - rot) * side >= 0 ? 1 : -1;      // which side of the hand faces the light
  const gr = g.createLinearGradient(0, 64 * sg, 0, -64 * sg);
  gr.addColorStop(0, `rgba(${light.join(',')},0.26)`); gr.addColorStop(0.5, 'rgba(0,0,0,0)'); gr.addColorStop(1, 'rgba(0,0,0,0.26)');
  g.fillStyle = gr; g.fillRect(-1040, -200, 1400, 400);
  const fall = g.createLinearGradient(-200, 0, 20, 0);          // the forearm darkens away from the hand
  fall.addColorStop(0, 'rgba(0,0,0,0.25)'); fall.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = fall; g.fillRect(-1040, -200, 1060, 400);
  // creases: knuckle lines on the back, palm lines on the palm
  g.strokeStyle = 'rgba(70,36,20,0.13)'; g.lineWidth = 1.6; g.lineCap = 'round';
  if (palm) {
    g.beginPath(); g.moveTo(90, 26); g.bezierCurveTo(72, 14, 54, 10, 40, 14); g.stroke();
    g.beginPath(); g.moveTo(88, -30); g.bezierCurveTo(66, -18, 48, -14, 34, -18); g.stroke();
    g.beginPath(); g.moveTo(50, -34); g.bezierCurveTo(30, -18, 20, 2, 16, 24); g.stroke();
  } else {
    // nails
    g.fillStyle = `rgba(${light.join(',')},0.22)`;
    geo.tips.forEach((p, i) => { g.beginPath(); g.ellipse(p[0] - 6, p[1], 8, 6.5 - (i === 3 ? 1 : 0), 0, 0, 6.283); g.fill(); });
  }
  g.globalCompositeOperation = 'source-over';
  g.setTransform(1, 0, 0, 1, 0, 0);
  // a soft contact shadow under the hand, then the hand
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = o.shadow ?? 0.35; ctx.filter = 'blur(14px) brightness(0)'; ctx.drawImage(L, 6, 12);
  ctx.globalAlpha = o.alpha ?? 1; ctx.filter = 'none'; ctx.drawImage(L, 0, 0);
  ctx.restore();
  return geo;
}
