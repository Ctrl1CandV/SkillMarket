// scene.js — 斜拉物块最省力倾角与摩擦角几何证明（课程与讲题轨标杆实验样片）
// Single-source physics from ./data.js; offline MathJax SVG formulas + FLIP morph + word-level audio sync from kit/lesson.js.

import { clamp, lerp, ease, seg, register, FONT_STACK } from '../../../../video-craft/kit/kit.js';
import {
  THEMES, svgEl, clearEl, loadMath, compileFormula, drawFormula, morphFormula, highlightPart,
  buildTimeline, cameraAt, applyCamera, drawStageBackground, drawProblemHeader,
  svgSurface, svgBlock, svgArrow, svgAngleArc, svgAxes, svgPlot,
} from '../../../../video-craft/kit/lesson.js';
import {
  MU, PHI_DEG, pullRatio, normalRatio, frictionRatio, pushRatio, F_HORIZ, F_MIN, SAVING_PCT, LOCK_DEG,
} from './data.js';

const W = 1920, H = 1080, FPS = 30;
const T = THEMES.slate;
const svg = document.getElementById('svg');
const measureHost = svgEl('g', { visibility: 'hidden' }, svg);

// Load word-aligned narration timing (prefers local VoxCPM `vo/words.js`, falls back to `vo-edge/words.js`, then char estimate)
let WORDS = {};
try {
  WORDS = (await import('./vo/words.js')).default;
} catch {
  try { WORDS = (await import('./vo-edge/words.js')).default; } catch { WORDS = {}; }
}

const CUE_SPEC = [
  { id: 'c01', gap: 0.45, text: '粗糙水平地面上有一个物块，动摩擦因数是零点七五。用斜向上的力拉它匀速前进，拉力跟水平面成多大角度最省力？' },
  { id: 'c02', gap: 0.50, text: '很多人第一反应是水平拉，觉得力全用在前进上。可你看，如果把拉力稍微往上抬一点，虽然水平分力小了，但它把物块往上托，支持力变小，摩擦力也跟着变小了。' },
  { id: 'c03', gap: 0.40, text: '一增一减，到底谁占便宜？我们直接在原图上做正交分解：竖直方向有向下的重力，向上的支持力，还有拉力向上的分力。' },
  { id: 'c04', gap: 0.45, text: '水平方向，拉力向右的分力，恰好平衡向左的滑动摩擦力。' },
  { id: 'c05', gap: 0.50, text: '把支持力代入摩擦力的式子，再把含拉力的两项移到左边合并，就能解出拉力随角度变化的函数。' },
  { id: 'c06', gap: 0.45, text: '怎么求分母的最大值？遇到余弦加正弦，立刻构造直角三角形配辅助角。令正切等于动摩擦因数四分之三，刚好是三比四比五的直角三角形，摩擦角约三十七度。' },
  { id: 'c07', gap: 0.55, text: '这样分母就化成了四分之五倍的余弦。当拉力的仰角恰好等于摩擦角三十七度时，余弦取到最大值一，最小拉力只有重力的五分之三，比水平拉整整省了百分之二十。' },
  { id: 'c08', gap: 0.55, text: '从几何上看更直观：支持力与摩擦力的合力叫全反力，它跟法线的夹角恒为摩擦角，方向固定不变。三力平衡构成闭合三角形，点到直线垂线段最短，拉力垂直于全反力时自然最短。' },
  { id: 'c09', gap: 0.40, text: '考场上还要小心它的反面：如果改成斜向下推，分母变成相减。一旦推角超过五十三度，分母小于等于零，无论用多大力都推不动，这就是工程上的自锁现象。' },
];

const TL = buildTimeline(CUE_SPEC, WORDS, { leadIn: 0.5, tailOut: 2.2 });
const C = TL.byId;

// Exact word-level cue timestamps!
const W_T = {
  liftUp: TL.word('c02', '往上抬', 0.36),
  fnShrink: TL.word('c02', '支持力变小', 0.72),
  fShrink: TL.word('c02', '摩擦力', 0.84),

  ortho: TL.word('c03', '正交分解', 0.32),
  gravity: TL.word('c03', '重力', 0.58),
  normal: TL.word('c03', '支持力', 0.72),
  fSin: TL.word('c03', '向上的分力', 0.86),

  fCos: TL.word('c04', '向右的分力', 0.28),
  friction: TL.word('c04', '滑动摩擦力', 0.68),

  subIn: TL.word('c05', '代入', 0.14),
  mergeLeft: TL.word('c05', '移到左边', 0.45),
  solveFn: TL.word('c05', '函数', 0.78),

  auxTri: TL.word('c06', '直角三角形', 0.36),
  tanMu: TL.word('c06', '四分之三', 0.62),
  deg37: TL.word('c06', '三十七度', 0.88),

  fiveFourths: TL.word('c07', '四分之五', 0.16),
  optAngle: TL.word('c07', '三十七度', 0.42),
  minForce: TL.word('c07', '五分之三', 0.72),
  save20: TL.word('c07', '百分之二十', 0.88),

  totalR: TL.word('c08', '全反力', 0.22),
  fixedPhi: TL.word('c08', '摩擦角', 0.36),
  closedTri: TL.word('c08', '闭合三角形', 0.58),
  perpShort: TL.word('c08', '垂线段最短', 0.75),

  pushDown: TL.word('c09', '斜向下推', 0.22),
  deg53: TL.word('c09', '五十三度', 0.48),
  selfLock: TL.word('c09', '自锁', 0.85),
};

await loadMath();

// Pre-compile all formulas once at startup (synchronous & cached)
const FM = {
  // Vector labels
  vecF: compileFormula(measureHost, String.raw`\vec{F}`, { size: 36, color: T.amber }),
  vecPush: compileFormula(measureHost, String.raw`\vec{F}_{\text{推}}`, { size: 34, color: T.amber }),
  vecFN: compileFormula(measureHost, String.raw`\vec{F}_N`, { size: 34, color: T.cyan }),
  vecG: compileFormula(measureHost, String.raw`mg`, { size: 34, color: T.ink }),
  vecFr: compileFormula(measureHost, String.raw`f = \mu F_N`, { size: 32, color: T.coral }),
  vecR: compileFormula(measureHost, String.raw`\vec{R}`, { size: 36, color: T.emerald }),
  compCos: compileFormula(measureHost, String.raw`F\cos\alpha`, { size: 30, color: T.amber }),
  compSin: compileFormula(measureHost, String.raw`F\sin\alpha`, { size: 30, color: T.amber }),
  alpha: compileFormula(measureHost, String.raw`\alpha`, { size: 30, color: T.violet }),
  theta: compileFormula(measureHost, String.raw`\theta`, { size: 30, color: T.coral }),
  phi: compileFormula(measureHost, String.raw`\varphi`, { size: 30, color: T.emerald }),

  // Problem statement & intuition formulas
  given: compileFormula(measureHost, String.raw`\mu = 0.75 = \frac{3}{4}, \quad v = \text{const} \implies \sum \vec{F} = \vec{0}`, { size: 36, color: T.ink }),
  ask: compileFormula(measureHost, String.raw`\alpha^* = \text{?}, \qquad F_{\min} = \text{?}`, { size: 40, color: T.amber }),
  horizCase: compileFormula(measureHost, String.raw`\alpha = 0^\circ \implies F(0^\circ) = \mu mg = 0.75\,mg`, { size: 36, color: T.muted }),

  // Step-by-step derivation formulas (with \id{key}{...} tags for TransformMatchingTex!)
  eqVert: compileFormula(measureHost, String.raw`F_N + F\sin\alpha = mg \implies \id{fnDef}{F_N = mg - F\sin\alpha}`, { size: 36, color: T.ink }),
  eqHoriz: compileFormula(measureHost, String.raw`\id{F}{F}\id{cos}{\cos\alpha} = \id{mu}{\mu}\id{fn}{F_N}`, { size: 42, color: T.ink }),
  eqSub: compileFormula(measureHost, String.raw`\id{F}{F}\id{cos}{\cos\alpha} = \id{mu}{\mu}\big(\id{mg}{mg} - \id{F2}{F}\id{sin}{\sin\alpha}\big)`, { size: 42, color: T.ink }),
  eqGroup: compileFormula(measureHost, String.raw`\id{F}{F}\big(\id{cos}{\cos\alpha} + \id{mu}{\mu}\id{sin}{\sin\alpha}\big) = \id{mu}{\mu}\id{mg}{mg}`, { size: 42, color: T.ink }),
  eqFrac: compileFormula(measureHost, String.raw`\id{F}{F(\alpha)} = \frac{\id{mu}{\mu}\id{mg}{mg}}{\id{den}{\cos\alpha + \mu\sin\alpha}}`, { size: 46, color: T.ink }),
  eqAux: compileFormula(measureHost, String.raw`\id{F}{F(\alpha)} = \frac{\id{mu}{\frac{3}{4}}\id{mg}{mg}}{\id{den}{\frac{5}{4}\cos(\alpha - 37^\circ)}}`, { size: 46, color: T.ink }),

  // Auxiliary triangle formulas
  tanPhi: compileFormula(measureHost, String.raw`\tan\varphi = \mu = \frac{3}{4} \implies \varphi \approx 37^\circ`, { size: 31, color: T.violet }),
  resultBox: compileFormula(measureHost, String.raw`\alpha^* = \varphi \approx 37^\circ, \quad F_{\min} = \frac{3}{5}mg = 0.60\,mg`, { size: 38, color: T.emerald }),

  // Geometric proof formulas
  geoR: compileFormula(measureHost, String.raw`\tan\varphi = \frac{f}{F_N} = \mu \implies \varphi \approx 37^\circ\;\text{(恒定)}`, { size: 34, color: T.emerald }),
  geoTri: compileFormula(measureHost, String.raw`\vec{G} + \vec{R} + \vec{F} = \vec{0}, \quad \vec{F} \perp \vec{R} \implies F_{\min} = mg\sin\varphi = \frac{3}{5}mg`, { size: 36, color: T.ink }),

  // Self-locking downward push formulas
  eqPush: compileFormula(measureHost, String.raw`F_{\text{推}}(\theta) = \frac{\mu mg}{\id{lockDen}{\cos\theta - \mu\sin\theta}}`, { size: 46, color: T.ink }),
  lockCond: compileFormula(measureHost, String.raw`\cos\theta - \mu\sin\theta \le 0 \iff \theta \ge 90^\circ - \varphi \approx 53^\circ \;\text{(自锁)}`, { size: 34, color: T.coral }),
};

const PART_COLORS = {
  F: T.amber,
  F2: T.amber,
  mu: T.coral,
  fn: T.cyan,
  fnDef: T.cyan,
  den: T.violet,
  lockDen: T.coral,
};

// Helper for crisp SVG text
function text(parent, str, x, y, { size = 24, weight = 700, fill = T.ink, align = 'left', alpha = 1 } = {}) {
  if (alpha <= 0.01) return null;
  const el = svgEl('text', {
    x, y, fill, opacity: clamp(alpha).toFixed(3),
    'font-family': FONT_STACK.sans, 'font-size': size, 'font-weight': weight,
    'text-anchor': align === 'center' ? 'middle' : align === 'right' ? 'end' : 'start',
  }, parent);
  el.textContent = str;
  return el;
}

function panel(parent, x, y, w, h, { title = '', accent = T.cyan, alpha = 1 } = {}) {
  if (alpha <= 0.01) return null;
  const g = svgEl('g', { opacity: clamp(alpha).toFixed(3) }, parent);
  svgEl('rect', { x, y, width: w, height: h, rx: 16, fill: T.panel, 'fill-opacity': '0.78', stroke: T.panelStroke, 'stroke-width': 1.5 }, g);
  if (title) {
    svgEl('rect', { x: x + 24, y: y + 22, width: 6, height: 24, rx: 3, fill: accent }, g);
    text(g, title, x + 42, y + 42, { size: 23, weight: 700, fill: T.muted });
  }
  return g;
}

// Compute current angle α(t) in degrees so the block's vectors are ALWAYS alive and physically exact
function currentAlpha(t) {
  if (t < C.c02.t0) return lerp(24, 30, seg(t, 0, C.c01.t1, ease.inOut));
  if (t < C.c03.t0) {
    // c02: starts at 0° ("水平拉"), then lifts up smoothly to 32° when "往上抬" is spoken!
    return lerp(0, 32, seg(t, W_T.liftUp, 2.2, ease.inOut));
  }
  if (t < C.c07.t0) return 32;
  if (t < C.c08.t0) {
    // c07: sweeps from 0° through optimal 36.87° up to 72°, then settles back onto optimal 36.87°!
    if (t < W_T.optAngle) return lerp(32, 0, seg(t, C.c07.t0, 0.9, ease.inOut));
    if (t < W_T.minForce + 0.6) return lerp(0, PHI_DEG, seg(t, W_T.optAngle, 1.4, ease.inOut));
    const sweepOut = seg(t, W_T.minForce + 0.6, 1.3, ease.inOut);
    const settleBack = seg(t, W_T.save20, 1.0, ease.inOut);
    return lerp(lerp(PHI_DEG, 68, sweepOut), PHI_DEG, settleBack);
  }
  if (t < C.c09.t0) {
    // c08: sweeps slightly around φ = 36.87° to demonstrate shortest perpendicular, settling on φ
    const u = seg(t, W_T.closedTri, 1.8, ease.inOut);
    const v = seg(t, W_T.perpShort, 1.1, ease.out);
    return lerp(lerp(12, 58, u), PHI_DEG, v);
  }
  // c09: downward push angle θ sweeps from 18° toward critical 52°!
  return lerp(18, 51.5, seg(t, W_T.pushDown, W_T.selfLock - W_T.pushDown, ease.inOut));
}

// Left Panel: Free-body diagram (used throughout c01..c09, morphing smoothly across states)
function drawMechanicsPanel(world, t, alphaDeg) {
  const isPush = t >= C.c09.t0;
  const isGeo = t >= C.c08.t0 && t < C.c09.t0;
  const pTitle = isPush ? '斜向下推：正压力与摩擦力剧增' : isGeo ? '支持力 + 摩擦力 = 恒定方向全反力 R' : '物块受力与正交分解（匀速平衡）';
  const g = panel(world, 56, 104, 772, 924, { title: pTitle, accent: isPush ? T.coral : isGeo ? T.emerald : T.amber });

  const OX = 440, OY = 590;
  const SCALE = 215; // 1.00 mg = 215 px

  // Ground surface & block (bottom at OY + 56 = 646)
  svgSurface(g, [110, 648], [774, 648], 1, { color: T.muted });
  svgBlock(g, OX, OY, 148, 112, { fill: '#17253B', stroke: T.ink, label: 'm' });

  // Horizontal reference line from O
  svgEl('line', { x1: OX, y1: OY, x2: OX + 220, y2: OY, stroke: T.faint, 'stroke-width': 1.8, 'stroke-dasharray': '6 6' }, g);

  if (!isPush) {
    const fRatio = pullRatio(alphaDeg);
    const nRatio = normalRatio(alphaDeg);
    const frRatio = frictionRatio(alphaDeg);
    const rad = (alphaDeg * Math.PI) / 180;
    const fLen = SCALE * fRatio;
    const fx = fLen * Math.cos(rad), fy = fLen * Math.sin(rad);
    const tipF = [OX + fx, OY - fy];

    // Before c03, show key forces intuitively; in c03..c04, reveal strictly on spoken word cues!
    const inDecomp = t >= C.c03.t0 && t < C.c05.t0;
    const kG = inDecomp ? seg(t, W_T.gravity, 0.55) : 1;
    const kN = inDecomp ? seg(t, W_T.normal, 0.55) : (t < C.c02.t0 ? 0 : 1);
    const kFr = t < C.c02.t0 ? 0 : (t >= C.c03.t0 && t < C.c04.t0 ? 0.25 : (inDecomp ? Math.max(0.25, seg(t, W_T.friction, 0.55)) : 1));
    const dimDecomp = isGeo ? 0.35 : 1;

    // 1. Gravity mg
    svgArrow(g, [OX, OY], [OX, OY + SCALE], kG, { color: T.ink, formula: FM.vecG, labelOffset: [16, -6] });

    // 2. Normal force F_N
    if (nRatio > 0.02) {
      svgArrow(g, [OX, OY], [OX, OY - SCALE * nRatio], kN, {
        color: T.cyan, alpha: dimDecomp, formula: FM.vecFN, labelOffset: [-18, 4], labelAnchor: 'right',
      });
    }

    // 3. Kinetic friction f = μ F_N (label anchored to the left of tip so it never crosses block wall!)
    if (frRatio > 0.02) {
      svgArrow(g, [OX, OY + 28], [OX - SCALE * frRatio, OY + 28], kFr, {
        color: T.coral, alpha: dimDecomp, formula: FM.vecFr, labelOffset: [-10, -18], labelAnchor: 'right',
      });
    }

    // 4. Orthogonal components F cos α & F sin α (labels placed outside block wall & away from F tip!)
    const showComp = t >= W_T.ortho && t < C.c08.t0;
    if (showComp && alphaDeg > 2) {
      const kSin = seg(t, W_T.fSin, 0.55);
      const kCos = t >= C.c04.t0 ? seg(t, W_T.fCos, 0.55) : 0;
      if (kCos > 0.01) {
        svgArrow(g, [OX, OY], [OX + fx, OY], kCos, {
          color: T.amber, width: 3.2, dashed: true, alpha: 0.85,
        });
        drawFormula(g, FM.compCos, Math.max(OX + 84, OX + fx * 0.55), OY + 28, { anchor: 'left', alpha: kCos * 0.9, scale: 0.90 });
      }
      if (kSin > 0.01) {
        svgArrow(g, [OX + fx, OY], tipF, kSin, {
          color: T.amber, width: 3.2, dashed: true, alpha: 0.85,
        });
        drawFormula(g, FM.compSin, OX + fx + 16, OY - fy * 0.45, { anchor: 'left', alpha: kSin * 0.9, scale: 0.90 });
      }
    }

    // 5. Total Reaction Force R = F_N + f during c08
    if (isGeo) {
      const kR = seg(t, W_T.totalR, 0.7);
      const rx = -SCALE * frRatio, ry = -SCALE * nRatio;
      svgArrow(g, [OX, OY], [OX + rx, OY + ry], kR, {
        color: T.emerald, width: 5, formula: FM.vecR, labelOffset: [-16, -10], labelAnchor: 'right',
      });
      // Vertical normal dashed reference + friction angle φ
      svgEl('line', { x1: OX, y1: OY, x2: OX, y2: OY - 210, stroke: T.muted, 'stroke-width': 1.8, 'stroke-dasharray': '5 5', opacity: kR.toFixed(2) }, g);
      svgAngleArc(g, [OX, OY], -90 - PHI_DEG, -90, 86, kR, { color: T.emerald, formula: FM.phi, labelRadiusOffset: 24 });
    }

    // 6. Applied Pull Force F & angle α
    svgArrow(g, [OX, OY], tipF, seg(t, 0.2, 0.7), { color: T.amber, width: 5, formula: FM.vecF, labelOffset: [14, -8] });
    if (alphaDeg > 3) {
      svgAngleArc(g, [OX, OY], -alphaDeg, 0, 68, 1, { color: T.violet, formula: FM.alpha, labelRadiusOffset: 22 });
    }

    // Live quantitative meter bar at bottom of Left Panel
    const meterY = 928;
    svgEl('rect', { x: 88, y: meterY - 38, width: 708, height: 96, rx: 12, fill: '#0B111E', stroke: T.panelStroke }, g);
    text(g, `仰角 α = ${alphaDeg.toFixed(0)}°`, 112, meterY + 18, { size: 23, fill: T.violet });
    text(g, `正压力 F_N = ${nRatio.toFixed(2)} mg`, 316, meterY + 18, { size: 23, fill: T.cyan });
    text(g, `拉力 F = ${fRatio.toFixed(2)} mg`, 584, meterY + 18, { size: 24, fill: Math.abs(alphaDeg - PHI_DEG) < 1.5 ? T.emerald : T.amber });
  } else {
    // c09: Downward push at angle θ below horizontal!
    const theta = alphaDeg;
    const rad = (theta * Math.PI) / 180;
    const rawF = pushRatio(theta);
    const fDisp = Math.min(1.55, rawF);
    const nDisp = Math.min(1.65, 1 + fDisp * Math.sin(rad));
    const frDisp = Math.min(1.35, MU * nDisp);
    const fLen = SCALE * fDisp * 0.78;
    const tipPush = [OX + fLen * Math.cos(rad), OY + fLen * Math.sin(rad)];

    svgArrow(g, [OX, OY], [OX, OY + SCALE * 0.85], 1, { color: T.ink, formula: FM.vecG, labelOffset: [16, 0] });
    svgArrow(g, [OX, OY], [OX, OY - SCALE * nDisp * 0.75], 1, { color: T.cyan, formula: FM.vecFN, labelOffset: [14, 0] });
    svgArrow(g, [OX, OY + 28], [OX - SCALE * frDisp * 0.8, OY + 28], 1, { color: T.coral, width: 5.5, formula: FM.vecFr, labelOffset: [-10, -18], labelAnchor: 'right' });
    svgArrow(g, [OX, OY], tipPush, 1, { color: T.amber, width: 5, formula: FM.vecPush, labelOffset: [14, 12] });
    svgAngleArc(g, [OX, OY], 0, theta, 68, 1, { color: T.coral, formula: FM.theta, labelRadiusOffset: 24 });

    const meterY = 928;
    svgEl('rect', { x: 88, y: meterY - 38, width: 708, height: 96, rx: 12, fill: '#1A1019', stroke: T.coral }, g);
    text(g, `下推角 θ = ${theta.toFixed(0)}°`, 112, meterY + 18, { size: 23, fill: T.coral });
    text(g, theta >= 50 ? '逼近 53° 临界：F → ∞（自锁推不动）' : `所需推力 F = ${rawF.toFixed(2)} mg（急剧增大）`, 336, meterY + 18, { size: 23, fill: T.amber });
  }
}

// Right Zone Mode A (c01..c02): Problem Hook & Intuition Conflict
function drawHookRight(world, t, alphaDeg) {
  const g = panel(world, 860, 104, 1004, 924, { title: '审题抓题眼：水平拉真的最省力吗？', accent: T.amber });

  drawFormula(g, FM.given, 912, 225, { alpha: seg(t, 0.3, 0.6) });
  drawFormula(g, FM.ask, 912, 315, { alpha: seg(t, C.c01.t0 + 1.8, 0.6) });

  if (t >= C.c02.t0) {
    const k0 = seg(t, C.c02.t0, 0.5);
    svgEl('rect', { x: 904, y: 392, width: 916, height: 112, rx: 12, fill: '#162236', stroke: T.panelStroke, opacity: k0.toFixed(2) }, g);
    text(g, '常见直觉：', 936, 458, { size: 25, fill: T.muted, alpha: k0 });
    drawFormula(g, FM.horizCase, 1080, 448, { alpha: k0 });

    // Trade-off causal cards triggered by exact words in c02!
    const kLift = seg(t, W_T.liftUp, 0.5);
    if (kLift > 0.01) {
      // Loss card
      svgEl('rect', { x: 904, y: 544, width: 438, height: 196, rx: 14, fill: '#1E1624', stroke: T.coral, 'stroke-width': 2, opacity: kLift.toFixed(2) }, g);
      text(g, '代价：水平前进分力变小', 936, 598, { size: 25, fill: T.coral, alpha: kLift });
      text(g, 'F cos α 随仰角增大而折损', 936, 650, { size: 22, weight: 400, fill: T.ink, alpha: kLift });
      text(g, `当前 cos α = ${Math.cos((alphaDeg * Math.PI) / 180).toFixed(2)}`, 936, 700, { size: 22, fill: T.muted, alpha: kLift });
    }

    const kGain = seg(t, W_T.fnShrink, 0.5);
    if (kGain > 0.01) {
      // Gain card
      svgEl('rect', { x: 1382, y: 544, width: 438, height: 196, rx: 14, fill: '#10262E', stroke: T.emerald, 'stroke-width': 2, opacity: kGain.toFixed(2) }, g);
      text(g, '收益：上托减重 → 摩擦力变小', 1414, 598, { size: 25, fill: T.emerald, alpha: kGain });
      text(g, 'F_N = mg − F sin α 减小', 1414, 650, { size: 22, weight: 400, fill: T.cyan, alpha: kGain });
      text(g, `滑动摩擦力 f = μF_N = ${frictionRatio(alphaDeg).toFixed(2)} mg`, 1414, 700, { size: 22, fill: T.emerald, alpha: seg(t, W_T.fShrink, 0.4) });
    }

    const kQ = seg(t, C.c02.t1 - 1.1, 0.5);
    if (kQ > 0.01) {
      svgEl('rect', { x: 904, y: 786, width: 916, height: 92, rx: 12, fill: T.amber, 'fill-opacity': '0.13', stroke: T.amber, 'stroke-width': 2, opacity: kQ.toFixed(2) }, g);
      text(g, '核心矛盾：水平分力折损 vs 摩擦力减小 —— 哪个角度净省力最多？', 1362, 842, { size: 26, fill: T.amber, align: 'center', alpha: kQ });
    }
  }
}

// Helper: 3-4-5 Auxiliary Angle Right Triangle on the upper-right derivation board
function drawAuxTriangle(parent, x, y, k) {
  const p = ease.out(clamp(k));
  if (p <= 0.01) return;
  const g = svgEl('g', { opacity: p.toFixed(3) }, parent);
  svgEl('rect', { x, y, width: 344, height: 256, rx: 12, fill: '#162033', stroke: T.violet, 'stroke-width': 1.8 }, g);
  text(g, '辅助角构造（3 : 4 : 5）', x + 22, y + 34, { size: 21, fill: T.violet });

  // Triangle vertices raised slightly so leg label '4' has generous room above tanPhi formula
  const A = [x + 54, y + 158], B = [x + 226, y + 158], C = [x + 226, y + 54];
  svgEl('polygon', { points: `${A[0]},${A[1]} ${B[0]},${B[1]} ${C[0]},${C[1]}`, fill: T.violet, 'fill-opacity': '0.12', stroke: T.violet, 'stroke-width': 3 }, g);
  svgEl('polyline', { points: `${B[0] - 15},${B[1]} ${B[0] - 15},${B[1] - 15} ${B[0]},${B[1] - 15}`, fill: 'none', stroke: T.muted, 'stroke-width': 2 }, g);
  svgAngleArc(g, A, -31, 0, 42, p, { color: T.emerald, label: 'φ', labelRadiusOffset: 18 });

  text(g, '4', (A[0] + B[0]) / 2, B[1] + 24, { size: 22, fill: T.ink, align: 'center' });
  text(g, '3', B[0] + 20, (B[1] + C[1]) / 2 + 8, { size: 22, fill: T.coral });
  text(g, '5', (A[0] + C[0]) / 2 - 18, (A[1] + C[1]) / 2 - 8, { size: 22, fill: T.cyan, align: 'center' });
  drawFormula(g, FM.tanPhi, x + 172, y + 226, { anchor: 'center', scale: 0.74 });
}

// Right Zone Mode B (c03..c07): Continuous Equation Morphing + Auxiliary Triangle + F(α) Extremum Plot
function drawDerivationRight(world, t, alphaDeg) {
  const gTop = panel(world, 860, 104, 1004, 476, { title: '正交平衡列式与辅助角恒等变形', accent: T.cyan });

  // Row 1: Vertical equilibrium (fades cleanly once AuxTriangle arrives so upper-right stays spacious)
  const kVert = seg(t, W_T.gravity, 0.6) * (1 - seg(t, W_T.auxTri - 0.1, 0.45));
  const vertDim = t >= W_T.mergeLeft ? 0.48 : 1;
  if (kVert > 0.01) {
    text(gTop, '竖直：', 900, 212, { size: 23, fill: T.muted, alpha: kVert * vertDim });
    const vLaid = drawFormula(gTop, FM.eqVert, 984, 204, { alpha: kVert * vertDim, scale: t >= W_T.mergeLeft ? 0.86 : 0.95, partColors: PART_COLORS });
    if (t >= W_T.subIn && t < W_T.mergeLeft && vLaid?.parts?.fnDef) {
      highlightPart(gTop, vLaid.parts.fnDef, seg(t, W_T.subIn, 0.35), { color: T.cyan, mode: 'underline' });
    }
  }

  // Row 2: Horizontal equilibrium -> morphs step-by-step all the way to F(α) = (3/4 mg) / (5/4 cos(α - 37°))!
  if (t >= C.c04.t0) {
    const eqPos = [984, 344];
    const eqPosCompact = [898, 308];
    let laid = null;

    if (t < W_T.subIn) {
      const kH = seg(t, W_T.fCos, 0.6);
      text(gTop, '水平：', 900, 352, { size: 23, fill: T.muted, alpha: kH });
      laid = drawFormula(gTop, FM.eqHoriz, eqPos[0], eqPos[1], { alpha: kH, partColors: PART_COLORS });
    } else if (t < W_T.mergeLeft) {
      laid = morphFormula(gTop, FM.eqHoriz, eqPos, FM.eqSub, eqPos, (t - W_T.subIn) / 0.75, {
        partColorsA: PART_COLORS, partColorsB: PART_COLORS,
      });
    } else if (t < W_T.solveFn) {
      laid = morphFormula(gTop, FM.eqSub, eqPos, FM.eqGroup, eqPos, (t - W_T.mergeLeft) / 0.8, {
        partColorsA: PART_COLORS, partColorsB: PART_COLORS,
      });
    } else if (t < W_T.fiveFourths) {
      const shiftLeft = seg(t, W_T.auxTri, 0.7, ease.inOut);
      const targetPos = [lerp(eqPos[0], eqPosCompact[0], shiftLeft), lerp(eqPos[1], eqPosCompact[1], shiftLeft)];
      laid = morphFormula(gTop, FM.eqGroup, eqPos, FM.eqFrac, targetPos, (t - W_T.solveFn) / 0.8, {
        partColorsA: PART_COLORS, partColorsB: PART_COLORS,
      });
      if (t >= C.c06.t0 && laid?.parts?.den) {
        highlightPart(gTop, laid.parts.den, seg(t, C.c06.t0 + 0.2, 0.45), {
          color: T.violet, label: '目标：求分母最大值', labelSide: 'bottom',
        });
      }
    } else {
      laid = morphFormula(gTop, FM.eqFrac, eqPosCompact, FM.eqAux, eqPosCompact, (t - W_T.fiveFourths) / 0.85, {
        partColorsA: PART_COLORS, partColorsB: PART_COLORS,
      });
      if (t >= W_T.optAngle && laid?.parts?.den) {
        highlightPart(gTop, laid.parts.den, seg(t, W_T.optAngle, 0.45), {
          color: T.emerald, label: 'α = 37° 时 cos 0° = 1 取最大！', labelSide: 'bottom',
        });
      }
    }

    // Auxiliary 3-4-5 right triangle appears on the right of gTop from c06 onward
    if (t >= W_T.auxTri) {
      drawAuxTriangle(gTop, 1492, 172, (t - W_T.auxTri) / 0.65);
    }

    // Final result banner at bottom of gTop when minForce is spoken
    if (t >= W_T.minForce) {
      const kRes = seg(t, W_T.minForce, 0.5);
      svgEl('rect', { x: 900, y: 482, width: 928, height: 76, rx: 12, fill: '#0E2925', stroke: T.emerald, 'stroke-width': 2, opacity: kRes.toFixed(2) }, gTop);
      drawFormula(gTop, FM.resultBox, 930, 520, { alpha: kRes, scale: 0.9 });
      if (t >= W_T.save20) {
        text(gTop, `较水平拉省力 ${SAVING_PCT}%`, 1796, 528, { size: 25, fill: T.amber, align: 'right', alpha: seg(t, W_T.save20, 0.4) });
      }
    }
  }

  // Lower Panel: F(α)/mg Function Plot & Extremum Verification
  const gBot = panel(world, 860, 600, 1004, 428, { title: '函数图像验证：拉力 F(α) / mg 随仰角的变化曲线', accent: T.emerald });
  const kAxes = seg(t, C.c05.t0 + 0.8, 0.8);
  if (kAxes <= 0.01) {
    text(gBot, '推导完成后在此绘制 F(α) 极值曲线…', 1362, 825, { size: 23, fill: T.faint, align: 'center', alpha: 0.7 });
    return;
  }

  const axes = svgAxes(gBot, { x: 966, y: 706, w: 820, h: 258 }, {
    xDomain: [0, 80],
    yDomain: [0.45, 1.05],
    xTicks: [[0, '0°'], [20, '20°'], [37, '37°(φ)'], [60, '60°'], [80, '80°']],
    yTicks: [[0.60, '0.60'], [0.75, '0.75'], [1.00, '1.00']],
    xLabel: 'α',
    yLabel: 'F / mg',
    k: kAxes,
  });

  // Horizontal dashed reference line at F(0°) = 0.75 mg
  const y075 = axes.y(F_HORIZ);
  svgEl('line', {
    x1: axes.x(0), y1: y075, x2: axes.x(80), y2: y075,
    stroke: T.muted, 'stroke-width': 1.8, 'stroke-dasharray': '7 6', opacity: (0.7 * kAxes).toFixed(2),
  }, gBot);
  text(gBot, '水平拉 0.75 mg', axes.x(62), y075 - 12, { size: 19, fill: T.muted, align: 'center', alpha: kAxes });

  // Plot curve progressively
  const kCurve = seg(t, W_T.solveFn, 1.4);
  svgPlot(gBot, axes, pullRatio, kCurve, { domain: [0, 78], color: T.cyan, width: 4, fillAlpha: 0.10 });

  // Live moving dot tracking `alphaDeg` on the curve!
  if (kCurve > 0.2) {
    const clampedA = clamp(alphaDeg, 0, 78);
    const [px, py] = axes.pt(clampedA, pullRatio(clampedA));
    svgEl('circle', { cx: px, cy: py, r: 8, fill: T.amber, stroke: '#0C1220', 'stroke-width': 2.5 }, gBot);
  }

  // Highlight minimum point (36.87°, 0.60) in c07 — label sits cleanly inside the concave valley above the curve!
  if (t >= W_T.optAngle) {
    const kMin = seg(t, W_T.optAngle, 0.5);
    const [mx, my] = axes.pt(PHI_DEG, F_MIN);
    svgEl('line', { x1: mx, y1: my, x2: mx, y2: axes.box.y + axes.box.h, stroke: T.emerald, 'stroke-width': 2.2, 'stroke-dasharray': '5 5', opacity: kMin.toFixed(2) }, gBot);
    svgEl('line', { x1: mx - 68, y1: my, x2: mx + 68, y2: my, stroke: T.emerald, 'stroke-width': 2.5, opacity: kMin.toFixed(2) }, gBot);
    svgEl('circle', { cx: mx, cy: my, r: 9.5, fill: T.emerald, stroke: '#fff', 'stroke-width': 2.5, opacity: kMin.toFixed(2) }, gBot);
    text(gBot, '极小值点 (37°, 0.60 mg)', mx, my - 26, { size: 22, fill: T.emerald, align: 'center', alpha: kMin });
  }
}

// Right Zone Mode C (c08): Geometric Vector Triangle Proof ("Point to Line, Perpendicular is Shortest")
function drawGeometryProofRight(world, t, alphaDeg) {
  const g = panel(world, 860, 104, 1004, 924, { title: '几何秒解：全反力摩擦角与矢量三角形垂线段最短', accent: T.emerald });

  drawFormula(g, FM.geoR, 908, 208, { alpha: seg(t, C.c08.t0 + 0.2, 0.6) });

  // Progressive build starting right as "全反力" / "摩擦角" is spoken so c08 is visually rich from second 1!
  const kBase = seg(t, W_T.totalR + 0.2, 0.7);
  const kTri = seg(t, W_T.closedTri - 0.5, 0.7);
  if (kBase > 0.01) {
    const PTop = [1180, 304];
    const G_LEN = 390;
    const PBot = [PTop[0], PTop[1] + G_LEN];

    // 1. Gravity vector G: PTop -> PBot
    svgArrow(g, PTop, PBot, kBase, { color: T.ink, width: 5, formula: FM.vecG, labelOffset: [-24, -180], labelAnchor: 'right' });

    // 2. Fixed direction ray of Total Reaction R at φ = 36.87° from vertical
    const kRay = seg(t, W_T.fixedPhi - 0.3, 0.65);
    const phiRad = (PHI_DEG * Math.PI) / 180;
    const rayDir = [Math.sin(phiRad), Math.cos(phiRad)];
    const rayEnd = [PTop[0] + rayDir[0] * 485, PTop[1] + rayDir[1] * 485];
    if (kRay > 0.01) {
      svgEl('line', {
        x1: PTop[0], y1: PTop[1], x2: lerp(PTop[0], rayEnd[0], kRay), y2: lerp(PTop[1], rayEnd[1], kRay),
        stroke: T.emerald, 'stroke-width': 2.5, 'stroke-dasharray': '9 7', opacity: (0.85 * kRay).toFixed(2),
      }, g);
      text(g, '全反力 R 固定方向线（φ = 37°）', PTop[0] + rayDir[0] * 215 + 26, PTop[1] + rayDir[1] * 215 - 12, {
        size: 21, fill: T.emerald, align: 'left', alpha: kRay,
      });
      svgAngleArc(g, PTop, 90 - PHI_DEG, 90, 76, kRay, { color: T.emerald, formula: FM.phi, labelRadiusOffset: 24 });
    }

    if (kTri > 0.01) {
      // Ghost horizontal F(0°) dashed segment labeled cleanly below PBot-qHoriz
      const qHoriz = [PTop[0] + G_LEN * Math.tan(phiRad), PBot[1]];
      svgEl('line', {
        x1: PBot[0], y1: PBot[1], x2: qHoriz[0], y2: qHoriz[1],
        stroke: T.muted, 'stroke-width': 2, 'stroke-dasharray': '5 6', opacity: (0.45 * kTri).toFixed(2),
      }, g);
      text(g, '水平拉 α=0° (0.75 mg)', (PBot[0] + qHoriz[0]) / 2, PBot[1] + 34, { size: 20, fill: T.muted, align: 'center', alpha: 0.75 * kTri });

      // 3. Sweeping F vector from PBot to Q, and R from Q back to PTop
      const fRatio = pullRatio(alphaDeg);
      const aRad = (alphaDeg * Math.PI) / 180;
      const Q = [PBot[0] + G_LEN * fRatio * Math.cos(aRad), PBot[1] - G_LEN * fRatio * Math.sin(aRad)];

      svgArrow(g, PBot, Q, kTri, { color: T.amber, width: 5.5, formula: FM.vecF, labelOffset: [-6, 30], labelAnchor: 'center' });
      svgArrow(g, Q, PTop, kTri, { color: T.emerald, width: 5, formula: FM.vecR, labelOffset: [-22, -8], labelAnchor: 'right' });

      // 4. Right-angle perpendicular symbol when near optimal α = φ!
      const kPerp = seg(t, W_T.perpShort, 0.5);
      if (kPerp > 0.01 && Math.abs(alphaDeg - PHI_DEG) < 3) {
        const uF = [-Math.cos(aRad), Math.sin(aRad)];
        const uR = [-rayDir[0], -rayDir[1]];
        const sz = 20;
        const p1 = [Q[0] + uF[0] * sz, Q[1] + uF[1] * sz];
        const p2 = [p1[0] + uR[0] * sz, p1[1] + uR[1] * sz];
        const p3 = [Q[0] + uR[0] * sz, Q[1] + uR[1] * sz];
        svgEl('polyline', {
          points: `${p1[0].toFixed(1)},${p1[1].toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)} ${p3[0].toFixed(1)},${p3[1].toFixed(1)}`,
          fill: 'none', stroke: T.amber, 'stroke-width': 3, opacity: kPerp.toFixed(2),
        }, g);
        text(g, '垂线段最短！F ⊥ R', Q[0] + 28, Q[1] + 8, { size: 24, fill: T.amber, alpha: kPerp });
      }
    }
  }

  // Summary formula bar at bottom
  const kSum = seg(t, W_T.perpShort + 0.2, 0.5);
  if (kSum > 0.01) {
    svgEl('rect', { x: 900, y: 896, width: 924, height: 92, rx: 12, fill: '#0E2925', stroke: T.emerald, 'stroke-width': 2, opacity: kSum.toFixed(2) }, g);
    drawFormula(g, FM.geoTri, 1362, 942, { anchor: 'center', alpha: kSum, scale: 0.88 });
  }
}

// Right Zone Mode D (c09): Downward Push Self-Locking Asymptote
function drawSelfLockRight(world, t, thetaDeg) {
  const g = panel(world, 860, 104, 1004, 924, { title: '考场易错边界：斜向下推与工程自锁现象', accent: T.coral });

  const kEq = seg(t, W_T.pushDown, 0.6);
  const laid = drawFormula(g, FM.eqPush, 1040, 238, { alpha: kEq, partColors: PART_COLORS });
  if (laid?.parts?.lockDen && t >= W_T.deg53 - 0.3) {
    highlightPart(g, laid.parts.lockDen, seg(t, W_T.deg53 - 0.3, 0.45), {
      color: T.coral, label: 'θ ≥ 53° 时分母 ≤ 0，方程无正数解！',
    });
  }

  // Plot F_push(θ)/mg blowing up at vertical asymptote θ = 53.13°!
  const axes = svgAxes(g, { x: 968, y: 406, w: 808, h: 420 }, {
    xDomain: [0, 70],
    yDomain: [0, 5.0],
    xTicks: [[0, '0°'], [20, '20°'], [40, '40°'], [53.1, '53°(临界)'], [70, '70°']],
    yTicks: [[0.75, '0.75'], [2, '2.0'], [4, '4.0']],
    xLabel: '下推角 θ',
    yLabel: 'F_推 / mg',
    k: kEq,
  });

  // Shaded self-locking dead zone [53.13°, 70°]
  const kLock = seg(t, W_T.deg53, 0.55);
  const xAsym = axes.x(LOCK_DEG);
  if (kLock > 0.01) {
    svgEl('rect', {
      x: xAsym, y: axes.box.y, width: axes.x(70) - xAsym, height: axes.box.h,
      fill: T.coral, 'fill-opacity': (0.16 * kLock).toFixed(3),
    }, g);
    svgEl('line', {
      x1: xAsym, y1: axes.box.y, x2: xAsym, y2: axes.box.y + axes.box.h,
      stroke: T.coral, 'stroke-width': 3, 'stroke-dasharray': '8 6', opacity: kLock.toFixed(2),
    }, g);
    text(g, '自锁区', (xAsym + axes.x(70)) / 2, axes.box.y + 180, { size: 28, fill: T.coral, align: 'center', alpha: kLock });
    text(g, 'F → ∞', (xAsym + axes.x(70)) / 2, axes.box.y + 220, { size: 24, fill: T.coral, align: 'center', alpha: kLock });
  }

  // Curve from 0° up to 48.2° (where pushRatio ≈ 4.95)
  const maxPlotTheta = lerp(18, 48.2, seg(t, W_T.pushDown, W_T.selfLock - W_T.pushDown, ease.inOut));
  svgPlot(g, axes, (th) => Math.min(4.95, pushRatio(th)), 1, {
    domain: [0, maxPlotTheta], color: T.amber, width: 4.5, fillAlpha: 0.08,
  });
  const [dotX, dotY] = axes.pt(maxPlotTheta, Math.min(4.95, pushRatio(maxPlotTheta)));
  svgEl('circle', { cx: dotX, cy: dotY, r: 8.5, fill: T.coral, stroke: '#fff', 'stroke-width': 2.5 }, g);

  // Takeaway bar
  const kTake = seg(t, W_T.selfLock, 0.5);
  if (kTake > 0.01) {
    svgEl('rect', { x: 900, y: 902, width: 924, height: 86, rx: 12, fill: '#26131D', stroke: T.coral, 'stroke-width': 2, opacity: kTake.toFixed(2) }, g);
    drawFormula(g, FM.lockCond, 1362, 945, { anchor: 'center', alpha: kTake, scale: 0.88 });
  }
}

// Subtle FocusCamera choreography: gently zooms into Auxiliary Triangle during c06, resets smoothly for curve & geometry
const CAM_KEYS = [
  [0, { cx: 960, cy: 540, w: 1920 }],
  [W_T.auxTri - 0.2, { cx: 960, cy: 540, w: 1920 }],
  [W_T.tanMu + 0.3, { cx: 1385, cy: 282, w: 1050 }],
  [C.c06.t1 + 0.1, { cx: 1385, cy: 282, w: 1050 }],
  [C.c07.t0 + 0.6, { cx: 960, cy: 540, w: 1920 }],
  [TL.duration, { cx: 960, cy: 540, w: 1920 }],
];

function currentStepLabel(t) {
  if (t < C.c03.t0) return '01 / 直觉陷阱与破题';
  if (t < C.c06.t0) return '02 / 正交分解与平衡方程';
  if (t < C.c08.t0) return '03 / 辅助角配凑与极值曲线';
  if (t < C.c09.t0) return '04 / 全反力摩擦角几何法';
  return '05 / 考场延伸：斜推自锁临界';
}

function seek(t) {
  clearEl(svg);
  drawStageBackground(svg, T, { gridStep: 60 });

  const world = svgEl('g', { id: 'world' }, svg);
  applyCamera(world, cameraAt(t, CAM_KEYS));

  const alpha = currentAlpha(t);
  drawMechanicsPanel(world, t, alpha);

  if (t < C.c03.t0) drawHookRight(world, t, alpha);
  else if (t < C.c08.t0) drawDerivationRight(world, t, alpha);
  else if (t < C.c09.t0) drawGeometryProofRight(world, t, alpha);
  else drawSelfLockRight(world, t, alpha);

  // Fixed HUD header outside camera zoom so title & step progress remain steady!
  drawProblemHeader(svg, {
    tag: '力学·极值精讲',
    title: '粗糙水平面斜拉物块：仰角 α 取多大最省力？（μ = 0.75）',
    stepLabel: currentStepLabel(t),
    progress: t / TL.duration,
    theme: T,
  });
}

// Subtle section transition chimes only (zero continuous background synth music!)
const chimes = [
  { t: C.c03.t0 - 0.15, freq: 587.33, gain: 0.028 },
  { t: W_T.optAngle, freq: 783.99, gain: 0.035 },
  { t: C.c08.t0 - 0.15, freq: 659.25, gain: 0.028 },
  { t: C.c09.t0 - 0.15, freq: 523.25, gain: 0.028 },
];

register({
  duration: TL.duration,
  fps: FPS,
  width: W,
  height: H,
  seek,
  meta: { cues: TL.cues, chimes },
});
seek(0);
