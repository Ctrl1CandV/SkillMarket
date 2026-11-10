// land.js — layered landscape tied to the sky camera, a person looking up, a tree.
import { rng, lerp, clamp } from '../../kit/kit.js';

const D = Math.PI / 180;

function noise1(seed) {
  const r = rng(seed), pts = Array.from({ length: 64 }, () => r());
  const v = (x) => { const i = Math.floor(x), f = x - i, a = pts[((i % 64) + 64) % 64], b = pts[(((i + 1) % 64) + 64) % 64], s = f * f * (3 - 2 * f); return a + (b - a) * s; };
  return (x) => v(x) * 0.62 + v(x * 2.13 + 7) * 0.26 + v(x * 4.7 + 3) * 0.12;
}

export const LAYERS = [
  { n: noise1(11), base: 1.0, amp: 3.4, sc: 0.0016, haze: 0.30 },
  { n: noise1(23), base: 0.2, amp: 1.9, sc: 0.0027, haze: 0.55 },
  { n: noise1(37), base: -1.6, amp: 1.5, sc: 0.0021, haze: 0.78 },
];
const FG = noise1(51);
// foreground hill: rises to the right where the person stands (elevation in degrees, x in px at the reference fov)
export const fgEl = (x) => -8.5 + 6.6 * clamp((x - 650) / 900) ** 0.7 + 0.5 * FG(x * 0.004);
export const PERSON_X = 1380, TREE_X = 1585;

// screen y of an elevation angle for the camera (ignores azimuth: the landscape only tilts and zooms)
export const yOf = (cam, el, H) => H / 2 - Math.tan(el - cam.pitch) * (1 / Math.tan(cam.fov / 2)) * (H / 2);
// screen x scales about the centre with the field of view
const xOf = (cam, x, W) => W / 2 + (x - W / 2) * (Math.tan(25 * D) / Math.tan(cam.fov / 2));
const xInv = (cam, x, W) => W / 2 + (x - W / 2) * (Math.tan(cam.fov / 2) / Math.tan(25 * D));

const mixc = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
const css = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;

export function drawLand(ctx, cam, W, H, { horizon, shadow, backlit = 0, drop = 0, alpha = 1, rim = 0, rimColor = [255, 170, 110], sunX = 0 }) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha = alpha; ctx.translate(0, drop);
  LAYERS.forEach((L, li) => {
    const hz = L.haze + (1 - L.haze) * 0.6 * backlit;
    const col = mixc(horizon, shadow, hz), top = mixc(horizon, shadow, hz * 0.8);
    ctx.beginPath(); ctx.moveTo(-10, H + 10);
    let minY = H;
    for (let x = -10; x <= W + 10; x += 6) {
      const y = yOf(cam, (L.base + L.amp * L.n(xInv(cam, x, W) * L.sc + li * 9)) * D, H);
      minY = Math.min(minY, y); ctx.lineTo(x, y);
    }
    ctx.lineTo(W + 10, H + 10); ctx.closePath();
    const g = ctx.createLinearGradient(0, minY, 0, minY + 260); g.addColorStop(0, css(top)); g.addColorStop(1, css(col));
    ctx.fillStyle = g; ctx.fill();
  });
  // foreground hill
  const fgCol = mixc(horizon, shadow, 0.93);
  ctx.beginPath(); ctx.moveTo(-10, H + 10);
  const ridge = [];
  for (let x = -10; x <= W + 10; x += 5) { const y = yOf(cam, fgEl(xInv(cam, x, W)) * D, H); ridge.push([x, y]); ctx.lineTo(x, y); }
  ctx.lineTo(W + 10, H + 10); ctx.closePath(); ctx.fillStyle = css(fgCol); ctx.fill();
  if (rim > 0) {
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineWidth = 2.5;
    const g = ctx.createLinearGradient(0, 0, W, 0); g.addColorStop(0, css(rimColor, 0.9 * rim)); g.addColorStop(clamp(sunX / W), css(rimColor, 0.7 * rim)); g.addColorStop(1, css(rimColor, 0.15 * rim));
    ctx.strokeStyle = g; ctx.beginPath(); ridge.forEach(([x, y], i) => (i ? ctx.lineTo(x, y + 1.2) : ctx.moveTo(x, y + 1.2))); ctx.stroke(); ctx.restore();
  }
  // grass along the ridge
  const gr = rng(77); ctx.strokeStyle = css(fgCol); ctx.lineWidth = 2;
  for (let i = 0; i < ridge.length; i += 2) { const [x, y] = ridge[i]; const h = 6 + gr() * 12; ctx.beginPath(); ctx.moveTo(x, y + 2); ctx.lineTo(x + (gr() - 0.5) * 6, y - h); ctx.stroke(); }
  // tree and person, scaled with the field of view
  const k = Math.tan(25 * D) / Math.tan(cam.fov / 2);
  const groundY = (x0) => yOf(cam, fgEl(x0) * D, H);
  drawTree(ctx, xOf(cam, TREE_X, W), groundY(TREE_X) + 4, 250 * k, fgCol, rim, rimColor);
  drawPerson(ctx, xOf(cam, PERSON_X, W), groundY(PERSON_X) + 3, 150 * k, fgCol, rim, rimColor);
  ctx.restore();
}

function drawTree(ctx, x, y, h, col, rim, rimColor) {
  ctx.fillStyle = css(col); ctx.strokeStyle = css(col); ctx.lineCap = 'round';
  ctx.lineWidth = h * 0.05; ctx.beginPath(); ctx.moveTo(x, y); ctx.quadraticCurveTo(x - h * 0.03, y - h * 0.3, x + h * 0.02, y - h * 0.55); ctx.stroke();
  ctx.lineWidth = h * 0.025;
  [[-0.2, -0.62], [0.18, -0.7], [-0.05, -0.8]].forEach(([dx, dy]) => { ctx.beginPath(); ctx.moveTo(x + h * 0.01, y - h * 0.45); ctx.lineTo(x + dx * h, y + dy * h); ctx.stroke(); });
  const blobs = [[-0.2, -0.66, 0.2], [0.17, -0.72, 0.19], [0, -0.86, 0.22], [-0.08, -0.62, 0.17], [0.1, -0.58, 0.15]];
  blobs.forEach(([dx, dy, r]) => { ctx.beginPath(); ctx.arc(x + dx * h, y + dy * h, r * h, 0, Math.PI * 2); ctx.fill(); });
  if (rim > 0) {
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.strokeStyle = css(rimColor, 0.55 * rim); ctx.lineWidth = 2;
    blobs.forEach(([dx, dy, r]) => { ctx.beginPath(); ctx.arc(x + dx * h, y + dy * h, r * h - 1, Math.PI * 0.95, Math.PI * 1.45); ctx.stroke(); });
    ctx.restore();
  }
}

// a person seen from the side, head tipped back, looking up and to the left
function drawPerson(ctx, x, y, h, col, rim, rimColor) {
  ctx.save(); ctx.translate(x, y); ctx.scale(h, h);
  ctx.fillStyle = css(col);
  const poly = (pts) => { ctx.beginPath(); pts.forEach(([a, b], i) => (i ? ctx.lineTo(a, b) : ctx.moveTo(a, b))); ctx.closePath(); ctx.fill(); };
  poly([[-0.075, 0], [-0.03, 0], [-0.01, -0.44], [-0.075, -0.44]]);            // back leg
  poly([[0.01, 0], [0.065, 0], [0.05, -0.44], [-0.01, -0.44]]);                // front leg
  poly([[-0.1, -0.42], [0.075, -0.42], [0.085, -0.62], [0.06, -0.77], [-0.07, -0.79], [-0.11, -0.62]]); // torso
  poly([[-0.02, -0.74], [0.035, -0.75], [0.03, -0.82], [-0.015, -0.82]]);       // neck
  ctx.beginPath(); ctx.ellipse(-0.005, -0.885, 0.072, 0.082, -0.5, 0, Math.PI * 2); ctx.fill(); // head tipped back
  poly([[0.055, -0.75], [0.09, -0.73], [0.1, -0.5], [0.07, -0.47]]);           // arm
  if (rim > 0) {
    ctx.globalCompositeOperation = 'lighter'; ctx.strokeStyle = css(rimColor, 0.8 * rim); ctx.lineWidth = 2.2 / h;
    ctx.beginPath(); ctx.ellipse(-0.005, -0.885, 0.07, 0.08, -0.5, Math.PI * 0.85, Math.PI * 1.55); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-0.07, -0.79); ctx.lineTo(-0.11, -0.62); ctx.lineTo(-0.1, -0.42); ctx.stroke();
  }
  ctx.restore();
}

// where the person's eyes are, for rays that converge on them
export function eyeOf(cam, W, H) {
  const k = Math.tan(25 * D) / Math.tan(cam.fov / 2);
  return [xOf(cam, PERSON_X, W) - 0.02 * 150 * k, yOf(cam, fgEl(PERSON_X) * D, H) + 3 - 0.9 * 150 * k];
}
