// scene.js — 斜拉极值与空间矢量闭合（lesson.js 示例工程：矢量剥离与公式变形）
// 本片的设计决定（换成你的题目时，先重写这三条决定，切勿原样照搬本片的 #060A12 深空底色与左右坐标）：
//   1. 核心视觉隐喻：因为本题要打通“代数辅助角”与“全反力矢量三角形垂线段最短”，所以滑块底面画出随正压力变化的摩擦热光晕，并在第 2 幕让三根力矢量直接脱离物块升空闭合成直角三角形。
//   2. 空间组织：第 1 幕左物块轨迹扇 + 右公式变形与曲线联动；第 2 幕右侧旧式与曲线全部清场，把中右舞台让给全反力恒定方向线与闭合矢量三角形。
//   3. 色调与语义色：因需表现摩擦发光与极坐标扫掠辉光而采用深色光学底；若换作常规数学推导、算法或统计讲题，可改用 THEMES.ivory / paper / blueprint 或自定义明快配色。

import { clamp, lerp, ease, seg, register, FONT_STACK } from '../../kit/kit.js';
import {
  THEMES, svgEl, clearEl, loadMath, compileFormula, drawFormula, morphFormula, highlightPart,
  buildTimeline, actAt, drawChapterTitle, svgCard, cameraAt, applyCamera, drawStageBackground,
  svgSurface, svgBlock, svgArrow, svgMorphArrow, svgLocusFan, svgAngleArc, svgAxes, svgPlot,
} from '../../kit/lesson.js';
import {
  PHI_DEG, PHI_RAD, pullRatio, normalRatio, frictionRatio, F_HORIZ, F_MIN, SAVING_PCT,
} from './data.js';

const W = 1920, H = 1080, FPS = 30;
// 配色属于本题题材；新题可直接选用 THEMES.ivory / paper / blueprint / chalk 或传入自定义 { bg, ink, accent, primary, danger, success }
const T = {
  ...THEMES.slate,
  bg: '#060A12',
  bgGlow: '#12223D',
  grid: 'rgba(148, 163, 184, 0.055)',
};
document.body.style.background = T.bg;

const svg = document.getElementById('svg');
const measureHost = svgEl('g', { visibility: 'hidden' }, svg);

let WORDS = {};
try { WORDS = (await import('./vo/words.js')).default; } catch { WORDS = {}; }

const CUE_SPEC = [
  { id: 'c07', gap: 0.65, text: '这样分母就化成了四分之五倍的余弦。当拉力的仰角恰好等于摩擦角三十七度时，余弦取到最大值一，最小拉力只有重力的五分之三，比水平拉整整省了百分之二十。' },
  { id: 'c08', gap: 0.40, text: '从几何上看更直观：支持力与摩擦力的合力叫全反力，它跟法线的夹角恒为摩擦角，方向固定不变。三力平衡构成闭合三角形，点到直线垂线段最短，拉力垂直于全反力时自然最短。' },
];

const TL = buildTimeline(CUE_SPEC, WORDS, { leadIn: 0.55, tailOut: 1.65 });
const C = TL.byId;

const W_T = {
  fiveFourths: TL.word('c07', '四分之五', 0.14),
  sweepStart: TL.word('c07', '仰角', 0.30),
  optAngle: TL.word('c07', '三十七度', 0.43),
  maxVal: TL.word('c07', '最大值', 0.56),
  minForce: TL.word('c07', '五分之三', 0.74),
  save20: TL.word('c07', '百分之二十', 0.92),

  supportFric: TL.word('c08', '支持力', 0.15),
  totalR: TL.word('c08', '全反力', 0.26),
  fixedPhi: TL.word('c08', '摩擦角', 0.42),
  fixedDir: TL.word('c08', '方向固定', 0.48),
  threeForce: TL.word('c08', '三力平衡', 0.58),
  closedTri: TL.word('c08', '闭合三角形', 0.65),
  perpShort: TL.word('c08', '垂线段最短', 0.78),
  perpR: TL.word('c08', '垂直于全反力', 0.89),
};

await loadMath();

const FM = {
  vecF: compileFormula(measureHost, String.raw`\vec{F}`, { size: 38, color: T.amber }),
  vecFN: compileFormula(measureHost, String.raw`\vec{F}_N`, { size: 34, color: T.cyan }),
  vecG: compileFormula(measureHost, String.raw`\vec{G} = mg`, { size: 35, color: T.ink }),
  vecGShort: compileFormula(measureHost, String.raw`mg`, { size: 34, color: T.ink }),
  vecFr: compileFormula(measureHost, String.raw`\vec{f}`, { size: 34, color: T.coral }),
  vecR: compileFormula(measureHost, String.raw`\vec{R}`, { size: 40, color: T.emerald }),
  alpha: compileFormula(measureHost, String.raw`\alpha`, { size: 30, color: T.violet }),
  phi: compileFormula(measureHost, String.raw`\varphi`, { size: 31, color: T.emerald }),

  eqFrac: compileFormula(measureHost, String.raw`\id{F}{F(\alpha)} = \frac{\id{mu}{\mu}\id{mg}{mg}}{\id{den}{\cos\alpha + \mu\sin\alpha}}`, { size: 50, color: T.ink }),
  eqAux: compileFormula(measureHost, String.raw`\id{F}{F(\alpha)} = \frac{\id{mu}{\frac{3}{4}}\id{mg}{mg}}{\id{den}{\frac{5}{4}\cos(\alpha - 37^\circ)}}`, { size: 50, color: T.ink }),
  resultHero: compileFormula(measureHost, String.raw`F_{\min} = \frac{3}{5}mg = 0.60\,mg`, { size: 44, color: T.emerald }),

  geoR: compileFormula(measureHost, String.raw`\tan\varphi = \frac{f}{F_N} = \mu = \frac{3}{4} \implies \varphi \approx 37^\circ`, { size: 38, color: T.emerald }),
  geoTri: compileFormula(measureHost, String.raw`\vec{G} + \vec{F} + \vec{R} = \vec{0}, \quad \vec{F} \perp \vec{R} \implies F_{\min} = mg\sin 37^\circ = \frac{3}{5}mg`, { size: 38, color: T.ink }),
};

const PART_COLORS = { F: T.amber, mu: T.coral, den: T.violet };

function text(parent, str, x, y, { size = 23, weight = 700, fill = T.ink, align = 'left', alpha = 1, mono = false } = {}) {
  if (alpha <= 0.01) return null;
  const el = svgEl('text', {
    x: x.toFixed(1), y: y.toFixed(1), fill, opacity: clamp(alpha).toFixed(3),
    'font-family': mono ? FONT_STACK.mono : FONT_STACK.sans,
    'font-size': size, 'font-weight': weight,
    'text-anchor': align === 'center' ? 'middle' : align === 'right' ? 'end' : 'start',
  }, parent);
  el.textContent = str;
  return el;
}

function currentAlpha(t) {
  if (t < C.c08.t0) {
    if (t < W_T.sweepStart - 0.3) return 0;
    if (t < W_T.optAngle) return lerp(0, PHI_DEG, seg(t, W_T.sweepStart - 0.3, W_T.optAngle - (W_T.sweepStart - 0.3), ease.inOut));
    if (t < W_T.maxVal + 0.2) return PHI_DEG;
    const probeUp = seg(t, W_T.maxVal + 0.2, 1.05, ease.inOut);
    const lockBack = seg(t, W_T.minForce - 0.65, 0.95, ease.inOut);
    return lerp(lerp(PHI_DEG, 68, probeUp), PHI_DEG, lockBack);
  }
  if (t < W_T.threeForce) {
    const u = seg(t, W_T.fixedDir - 0.2, 0.85, ease.inOut);
    const v = seg(t, W_T.fixedDir + 0.75, 0.85, ease.inOut);
    return lerp(lerp(PHI_DEG, 18, u), PHI_DEG, v);
  }
  if (t < W_T.closedTri + 0.3) return lerp(PHI_DEG, 14, seg(t, W_T.threeForce, 1.1, ease.inOut));
  const sweepHi = seg(t, W_T.closedTri + 0.3, 1.35, ease.inOut);
  const lockPerp = seg(t, W_T.perpShort - 0.45, 0.85, ease.out);
  return lerp(lerp(14, 58, sweepHi), PHI_DEG, lockPerp);
}

function drawCrosshairs(parent, alpha = 0.35) {
  const g = svgEl('g', { opacity: alpha.toFixed(2) }, parent);
  for (const x of [360, 760, 1160, 1560]) {
    for (const y of [240, 540, 840]) {
      svgEl('line', { x1: x - 7, y1: y, x2: x + 7, y2: y, stroke: T.faint, 'stroke-width': 1.4 }, g);
      svgEl('line', { x1: x, y1: y - 7, x2: x, y2: y + 7, stroke: T.faint, 'stroke-width': 1.4 }, g);
    }
  }
}

function drawPhysicalWorld(world, t, alphaDeg) {
  const OX = 450, OY = 576, SCALE = 268;
  const BW = 160, BH = 114;
  const groundY = OY + BH / 2;

  const detach = seg(t, W_T.threeForce, 1.25, ease.inOut);
  const bodyDim = lerp(1, 0.34, detach);

  const fRatio = pullRatio(alphaDeg);
  const nRatio = normalRatio(alphaDeg);
  const frRatio = frictionRatio(alphaDeg);
  const aRad = (alphaDeg * Math.PI) / 180;
  const fx = SCALE * fRatio * Math.cos(aRad);
  const fy = SCALE * fRatio * Math.sin(aRad);
  const fnPx = SCALE * nRatio;
  const frPx = SCALE * frRatio;

  const gBase = svgEl('g', { opacity: bodyDim.toFixed(3) }, world);
  svgSurface(gBase, [84, groundY], [900, groundY], 1, {
    color: '#64748B', hatchColor: 'rgba(148, 163, 184, 0.34)', spacing: 26, scroll: -t * 96,
  });

  const heatAlpha = clamp((frRatio / 0.75) * 0.68, 0.10, 0.72);
  svgEl('ellipse', {
    cx: OX - 8, cy: groundY,
    rx: (46 + frRatio * 56).toFixed(1), ry: (6 + frRatio * 9).toFixed(1),
    fill: T.coral, 'fill-opacity': heatAlpha.toFixed(3), filter: 'url(#vc-glow)',
  }, gBase);

  for (let i = 0; i < 3; i++) {
    const wy = OY - 26 + i * 26;
    const phase = ((t * 140 + i * 47) % 110) / 110;
    const wx1 = OX - BW / 2 - 18 - phase * 95;
    svgEl('line', {
      x1: wx1.toFixed(1), y1: wy, x2: (wx1 - 34).toFixed(1), y2: wy,
      stroke: T.cyan, 'stroke-width': 1.8, 'stroke-linecap': 'round', opacity: ((1 - phase) * 0.28).toFixed(3),
    }, gBase);
  }

  svgBlock(gBase, OX, OY, BW, BH, { fill: '#132036', stroke: '#E2E8F0', label: 'm' });
  svgEl('line', { x1: OX, y1: OY, x2: OX + 235, y2: OY, stroke: T.faint, 'stroke-width': 1.6, 'stroke-dasharray': '6 6' }, gBase);

  const fanFadeOut = 1 - seg(t, C.c08.t0 - 0.45, 0.75);
  if (fanFadeOut > 0.01) {
    const gFan = svgEl('g', { opacity: fanFadeOut.toFixed(3) }, world);
    const xHoriz = OX + SCALE * F_HORIZ;
    svgArrow(gFan, [OX, OY], [xHoriz, OY], 1, { color: T.muted, width: 3, dashed: true, alpha: 0.52 });
    text(gFan, '水平拉 0.75 mg', xHoriz + 12, OY + 28, { size: 20, fill: T.muted, alpha: 0.82 });

    const kMinArc = seg(t, W_T.optAngle - 0.35, 0.75);
    if (kMinArc > 0.01) {
      const rMin = SCALE * F_MIN;
      const a0 = (-72 * Math.PI) / 180;
      const sx = OX + rMin * Math.cos(a0), sy = OY + rMin * Math.sin(a0);
      svgEl('path', {
        d: `M ${sx.toFixed(1)} ${sy.toFixed(1)} A ${rMin.toFixed(1)} ${rMin.toFixed(1)} 0 0 1 ${(OX + rMin).toFixed(1)} ${OY.toFixed(1)}`,
        fill: 'none', stroke: T.emerald, 'stroke-width': 2, 'stroke-dasharray': '6 6', opacity: (0.62 * kMinArc).toFixed(3),
      }, gFan);
    }

    const kSweep1 = seg(t, W_T.sweepStart - 0.2, W_T.optAngle - (W_T.sweepStart - 0.2), ease.inOut);
    const kSweep2 = seg(t, W_T.maxVal + 0.2, 1.05, ease.inOut);
    const maxSweptDeg = lerp(lerp(0, PHI_DEG, kSweep1), 70, kSweep2);
    if (maxSweptDeg > 1) {
      svgLocusFan(gFan, [OX, OY], (deg) => {
        const r = SCALE * pullRatio(deg), rad = (deg * Math.PI) / 180;
        return [OX + r * Math.cos(rad), OY - r * Math.sin(rad)];
      }, maxSweptDeg / 70, { domain: [0, 70], spokeStep: 9.25, color: T.amber, fillAlpha: 0.09, glow: 'soft' });
    }

    if (t >= W_T.optAngle - 0.05) {
      const kOpt = seg(t, W_T.optAngle - 0.05, 0.55);
      const px = OX + SCALE * F_MIN * Math.cos(PHI_RAD), py = OY - SCALE * F_MIN * Math.sin(PHI_RAD);
      svgEl('circle', {
        cx: px.toFixed(1), cy: py.toFixed(1), r: 10,
        fill: T.emerald, stroke: '#FFFFFF', 'stroke-width': 2.5, filter: 'url(#vc-glow-soft)', opacity: kOpt.toFixed(3),
      }, gFan);
      svgEl('line', {
        x1: (px + 8).toFixed(1), y1: (py - 10).toFixed(1), x2: (px + 22).toFixed(1), y2: (py - 40).toFixed(1),
        stroke: T.emerald, 'stroke-width': 1.8, opacity: (0.75 * kOpt).toFixed(3),
      }, gFan);
      text(gFan, '最短垂点 0.60 mg (α = 37°)', px + 26, py - 46, { size: 21, fill: T.emerald, alpha: kOpt });
    }
  }

  const inAct2 = t >= C.c08.t0;
  const fuseR = seg(t, W_T.totalR - 0.25, 0.7);
  const compAlpha = lerp(1, 0.24, fuseR) * bodyDim;
  const frY = lerp(OY + 32, OY, seg(t, C.c08.t0, 0.7, ease.inOut));

  svgArrow(world, [OX, OY], [OX, OY - fnPx], 1, {
    color: T.cyan, width: 4.2, alpha: compAlpha,
    formula: (!inAct2 || fuseR < 0.35) && detach < 0.3 ? FM.vecFN : null, labelOffset: [-18, 4], labelAnchor: 'right',
  });
  svgArrow(world, [OX, frY], [OX - frPx, frY], 1, {
    color: T.coral, width: 4.2, alpha: compAlpha,
    formula: (!inAct2 || fuseR < 0.35) && detach < 0.3 ? FM.vecFr : null, labelOffset: [-14, -20], labelAnchor: 'right',
  });

  if (inAct2 && bodyDim > 0.05) {
    const kRect = seg(t, W_T.supportFric, 0.55) * bodyDim;
    if (kRect > 0.01) {
      svgEl('line', { x1: OX, y1: OY - fnPx, x2: OX - frPx, y2: OY - fnPx, stroke: T.coral, 'stroke-width': 1.8, 'stroke-dasharray': '5 5', opacity: (0.55 * kRect).toFixed(3) }, world);
      svgEl('line', { x1: OX - frPx, y1: OY, x2: OX - frPx, y2: OY - fnPx, stroke: T.cyan, 'stroke-width': 1.8, 'stroke-dasharray': '5 5', opacity: (0.55 * kRect).toFixed(3) }, world);
    }
    const kCone = seg(t, W_T.fixedPhi - 0.2, 0.65) * bodyDim;
    if (kCone > 0.01) {
      svgEl('line', { x1: OX, y1: OY, x2: OX, y2: OY - 215, stroke: T.muted, 'stroke-width': 1.6, 'stroke-dasharray': '5 5', opacity: (0.65 * kCone).toFixed(3) }, world);
      svgEl('line', { x1: OX, y1: OY, x2: OX - 250 * Math.sin(PHI_RAD), y2: OY - 250 * Math.cos(PHI_RAD), stroke: T.emerald, 'stroke-width': 2.4, 'stroke-dasharray': '8 6', opacity: (0.82 * kCone).toFixed(3) }, world);
      svgAngleArc(world, [OX, OY], -90 - PHI_DEG, -90, 84, kCone, { color: T.emerald, formula: detach < 0.4 ? FM.phi : null, labelRadiusOffset: 24 });
    }
  }

  if (alphaDeg > 2.5 && detach < 0.85) {
    svgAngleArc(world, [OX, OY], -alphaDeg, 0, 64, 1 - detach, { color: T.violet, formula: detach < 0.35 ? FM.alpha : null, labelRadiusOffset: 22 });
  }

  if (detach > 0.02) {
    const ghostA = 0.22 * detach;
    svgArrow(world, [OX, OY], [OX, OY + SCALE], 1, { color: T.ink, width: 3.2, alpha: ghostA });
    svgArrow(world, [OX, OY], [OX + fx, OY - fy], 1, { color: T.amber, width: 3.2, alpha: ghostA });
    svgArrow(world, [OX, OY], [OX - frPx, OY - fnPx], 1, { color: T.emerald, width: 3.2, alpha: ghostA });
  }

  const PTop = [1150, 286], G_LEN = 432, PBot = [PTop[0], PTop[1] + G_LEN];
  const Q = [PBot[0] + G_LEN * fRatio * Math.cos(aRad), PBot[1] - G_LEN * fRatio * Math.sin(aRad)];

  if (detach > 0.25) {
    const kTriBg = clamp((detach - 0.25) / 0.75);
    const rayDir = [Math.sin(PHI_RAD), Math.cos(PHI_RAD)];
    const rayEnd = [PTop[0] + rayDir[0] * 525, PTop[1] + rayDir[1] * 525];

    if (detach > 0.85) {
      svgEl('polygon', {
        points: `${PTop[0]},${PTop[1]} ${PBot[0]},${PBot[1]} ${Q[0].toFixed(1)},${Q[1].toFixed(1)}`,
        fill: T.emerald, 'fill-opacity': (clamp((detach - 0.85) / 0.15) * 0.07).toFixed(3),
      }, world);
    }

    svgEl('line', {
      x1: PTop[0], y1: PTop[1], x2: lerp(PTop[0], rayEnd[0], kTriBg), y2: lerp(PTop[1], rayEnd[1], kTriBg),
      stroke: T.emerald, 'stroke-width': 2.5, 'stroke-dasharray': '9 7', opacity: (0.82 * kTriBg).toFixed(3),
    }, world);
    svgAngleArc(world, PTop, 90 - PHI_DEG, 90, 78, kTriBg, { color: T.emerald, formula: FM.phi, labelRadiusOffset: 24 });
    text(world, '全反力 R 恒定方向线 (φ = 37°)', PTop[0] + rayDir[0] * 245 + 42, PTop[1] + rayDir[1] * 245 - 2, {
      size: 21, fill: T.emerald, alpha: kTriBg,
    });

    const qHoriz = [PTop[0] + G_LEN * Math.tan(PHI_RAD), PBot[1]];
    svgEl('line', { x1: PBot[0], y1: PBot[1], x2: qHoriz[0], y2: qHoriz[1], stroke: T.muted, 'stroke-width': 2, 'stroke-dasharray': '5 6', opacity: (0.48 * kTriBg).toFixed(3) }, world);
    text(world, '水平拉 α = 0° (0.75 mg)', (PBot[0] + qHoriz[0]) / 2, PBot[1] + 34, { size: 20, fill: T.muted, align: 'center', alpha: 0.78 * kTriBg });

    const kSearch = seg(t, W_T.closedTri + 0.35, 1.25);
    if (kSearch > 0.02) {
      svgLocusFan(world, PBot, (deg) => {
        const r = G_LEN * pullRatio(deg), rad = (deg * Math.PI) / 180;
        return [PBot[0] + r * Math.cos(rad), PBot[1] - r * Math.sin(rad)];
      }, kSearch, { domain: [14, 58], spokeStep: 11, color: T.amber, fillAlpha: 0.05, width: 2, glow: false });
    }
  }

  svgMorphArrow(world, [OX, OY], [OX, OY + SCALE], PTop, PBot, detach, {
    arc: 26, color: T.ink, width: 5, formula: detach < 0.45 ? FM.vecGShort : null, labelOffset: [16, -8],
  });
  if (fuseR > 0.01) {
    svgMorphArrow(world, [OX, OY], [OX - frPx, OY - fnPx], Q, PTop, detach, {
      k: fuseR, arc: 44, color: T.emerald, width: 5.5, glow: 'soft', formula: detach < 0.45 ? FM.vecR : null, labelOffset: [-18, -10], labelAnchor: 'right',
    });
  }
  svgMorphArrow(world, [OX, OY], [OX + fx, OY - fy], PBot, Q, detach, {
    arc: -32, color: T.amber, width: 5.8, glow: true, formula: detach < 0.45 ? FM.vecF : null, labelOffset: [16, -12],
  });

  if (detach > 0.55) {
    const la = clamp((detach - 0.55) / 0.45);
    drawFormula(world, FM.vecG, PTop[0] - 28, (PTop[1] + PBot[1]) / 2, { anchor: 'right', alpha: la, color: T.ink });
    drawFormula(world, FM.vecR, PTop[0] + 118, PTop[1] + 92, { anchor: 'left', alpha: la, color: T.emerald });
    const fMid = [(PBot[0] + Q[0]) / 2, (PBot[1] + Q[1]) / 2];
    drawFormula(world, FM.vecF, fMid[0] + 18, fMid[1] + 28, { anchor: 'left', alpha: la, color: T.amber });
  }

  const kPerp = seg(t, W_T.perpShort - 0.1, 0.5);
  if (kPerp > 0.01 && Math.abs(alphaDeg - PHI_DEG) < 2.5) {
    const rayDir = [Math.sin(PHI_RAD), Math.cos(PHI_RAD)];
    const uF = [-Math.cos(aRad), Math.sin(aRad)], uR = [-rayDir[0], -rayDir[1]], sz = 22;
    const p1 = [Q[0] + uF[0] * sz, Q[1] + uF[1] * sz];
    const p2 = [p1[0] + uR[0] * sz, p1[1] + uR[1] * sz];
    const p3 = [Q[0] + uR[0] * sz, Q[1] + uR[1] * sz];
    svgEl('polyline', {
      points: `${p1[0].toFixed(1)},${p1[1].toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)} ${p3[0].toFixed(1)},${p3[1].toFixed(1)}`,
      fill: 'none', stroke: T.amber, 'stroke-width': 3.2, filter: 'url(#vc-glow-soft)', opacity: kPerp.toFixed(3),
    }, world);

    const pulseP = seg(t, W_T.perpShort, 1.1, ease.out);
    if (pulseP > 0 && pulseP < 1) {
      svgEl('circle', {
        cx: Q[0].toFixed(1), cy: Q[1].toFixed(1), r: lerp(10, 52, pulseP).toFixed(1),
        fill: 'none', stroke: T.emerald, 'stroke-width': 2.5, opacity: ((1 - pulseP) * 0.85).toFixed(3),
      }, world);
    }
    text(world, '垂线段最短！F ⊥ R  (0.60 mg)', Q[0] + 34, Q[1] + 8, { size: 25, fill: T.amber, alpha: kPerp });
  }
}

function drawAct1FloatingMath(world, t, alphaDeg) {
  const out = 1 - seg(t, C.c08.t0 - 0.5, 0.7, ease.in);
  if (out <= 0.01) return;
  const g = svgEl('g', { opacity: out.toFixed(3), transform: `translate(0, ${(-22 * (1 - out)).toFixed(1)})` }, world);

  const eqPos = [1405, 242];
  const hg = svgEl('radialGradient', { id: 'vc-eq-halo', cx: '50%', cy: '50%', r: '50%' }, g);
  svgEl('stop', { offset: '0%', 'stop-color': '#1E3A5F', 'stop-opacity': '0.36' }, hg);
  svgEl('stop', { offset: '100%', 'stop-color': '#1E3A5F', 'stop-opacity': '0' }, hg);
  svgEl('ellipse', { cx: eqPos[0], cy: eqPos[1], rx: 360, ry: 150, fill: 'url(#vc-eq-halo)' }, g);

  const laid = morphFormula(g, FM.eqFrac, eqPos, FM.eqAux, eqPos, (t - W_T.fiveFourths) / 0.9, {
    anchor: 'center', partColorsA: PART_COLORS, partColorsB: PART_COLORS,
  });
  if (t >= W_T.optAngle && laid?.parts?.den) {
    highlightPart(g, laid.parts.den, seg(t, W_T.optAngle, 0.45), {
      color: T.emerald, mode: 'underline', label: 'α = 37° 时 cos 0° = 1，分母达最大',
    });
  }

  if (t >= W_T.minForce) {
    drawFormula(g, FM.resultHero, eqPos[0], 424, { anchor: 'center', alpha: seg(t, W_T.minForce, 0.55) });
    if (t >= W_T.save20) {
      text(g, `比水平拉 (0.75 mg) 整整省力 ${SAVING_PCT}%`, eqPos[0], 516, {
        size: 24, fill: T.amber, align: 'center', alpha: seg(t, W_T.save20, 0.45),
      });
    }
  }

  const axes = svgAxes(g, { x: 1040, y: 618, w: 720, h: 248 }, {
    xDomain: [0, 75], yDomain: [0.48, 0.96],
    xTicks: [[0, '0°'], [37, '37°(φ)'], [70, '70°']],
    yTicks: [[0.60, '0.60'], [0.75, '0.75'], [0.90, '0.90']],
    xLabel: 'α', yLabel: 'F / mg', k: seg(t, 0.2, 0.7),
  });
  const y075 = axes.y(F_HORIZ);
  svgEl('line', { x1: axes.x(0), y1: y075, x2: axes.x(75), y2: y075, stroke: T.faint, 'stroke-width': 1.6, 'stroke-dasharray': '6 6' }, g);
  svgPlot(g, axes, pullRatio, seg(t, 0.5, 1.1), { domain: [0, 73], color: T.cyan, width: 4, fillAlpha: 0.08, glow: 'soft' });

  const cA = clamp(alphaDeg, 0, 73);
  const [dx, dy] = axes.pt(cA, pullRatio(cA));
  svgEl('circle', {
    cx: dx.toFixed(1), cy: dy.toFixed(1), r: 8.5,
    fill: Math.abs(cA - PHI_DEG) < 1.8 ? T.emerald : T.amber, stroke: '#FFFFFF', 'stroke-width': 2.2, filter: 'url(#vc-glow-soft)',
  }, g);

  if (t >= W_T.optAngle) {
    const kVal = seg(t, W_T.optAngle, 0.5);
    const [mx, my] = axes.pt(PHI_DEG, F_MIN);
    svgEl('line', { x1: mx - 58, y1: my, x2: mx + 58, y2: my, stroke: T.emerald, 'stroke-width': 2.5, opacity: kVal.toFixed(3) }, g);
    text(g, '极小值谷底 0.60 mg', mx, my - 24, { size: 21, fill: T.emerald, align: 'center', alpha: kVal });
  }
}

function drawAct2FloatingMath(world, t) {
  if (t < C.c08.t0) return;
  const kTop = seg(t, W_T.totalR, 0.6) * (1 - seg(t, W_T.threeForce, 0.65) * 0.35);
  if (kTop > 0.01) {
    const shift = seg(t, W_T.threeForce, 1.1, ease.inOut);
    drawFormula(world, FM.geoR, lerp(1360, 1430, shift), lerp(248, 178, shift), {
      anchor: 'center', alpha: kTop, scale: lerp(1, 0.86, shift),
    });
  }
  const kBot = seg(t, W_T.perpR - 0.25, 0.6);
  if (kBot > 0.01) drawFormula(world, FM.geoTri, 1320, 918, { anchor: 'center', alpha: kBot, scale: 0.94 });
}

const ACTS = [
  { id: 'act1', t0: 0 },
  { id: 'act2', t0: C.c08.t0 },
];

function drawEditorialHud(t, alphaDeg) {
  const act = actAt(t, ACTS, { duration: TL.duration });
  const inAct2 = act.id === 'act2';
  const dotCol = inAct2 ? T.emerald : T.amber;
  drawChapterTitle(svg, {
    kicker: inAct2 ? '02 / 02  ·  几何证法' : '01 / 02  ·  代数极值',
    title: inAct2 ? '全反力恒定方向与矢量空间闭合' : '辅助角极值与力空间轨迹涌现',
    x: 76, y: 26, width: W - 152, theme: T,
  });

  const opt = Math.abs(alphaDeg - PHI_DEG) < 1.5;
  svgCard(svg, W - 376, 32, 300, 68, 1, {
    accent: opt ? T.emerald : T.amber, corners: true, shadow: false, theme: T,
  });
  text(svg, `α = ${alphaDeg.toFixed(0).padStart(2, ' ')}°  ·  F = ${pullRatio(alphaDeg).toFixed(2)} mg`, W - 226, 74, {
    size: 21, weight: 700, fill: opt ? T.emerald : T.amber, align: 'center', mono: true,
  });
  svgEl('line', { x1: 0, y1: H - 3, x2: (W * clamp(t / TL.duration)).toFixed(1), y2: H - 3, stroke: dotCol, 'stroke-width': 3 }, svg);
}

const CAM_KEYS = [
  [0, { cx: 960, cy: 525, w: 1920 }],
  [W_T.optAngle, { cx: 945, cy: 522, w: 1890 }],
  [C.c08.t0, { cx: 960, cy: 525, w: 1920 }],
  [W_T.closedTri + 0.8, { cx: 982, cy: 528, w: 1890 }],
  [TL.duration, { cx: 960, cy: 525, w: 1920 }],
];

function seek(t) {
  clearEl(svg);
  const spotX = lerp(0.36, 0.62, seg(t, C.c08.t0, 2.2, ease.inOut));
  drawStageBackground(svg, T, { gridStep: 0, glow: true, spotlight: [spotX, 0.50], vignette: 0.48 });
  drawCrosshairs(svg, 0.42);

  const world = svgEl('g', { id: 'world' }, svg);
  applyCamera(world, cameraAt(t, CAM_KEYS));

  const alpha = currentAlpha(t);
  drawPhysicalWorld(world, t, alpha);
  drawAct1FloatingMath(world, t, alpha);
  drawAct2FloatingMath(world, t);
  drawEditorialHud(t, alpha);
}

const sfx = [
  { t: W_T.fiveFourths, kind: 'pop', gain: 0.038 },
  { t: W_T.optAngle, kind: 'chime', note: 'G5', gain: 0.036 },
  { t: C.c08.t0 - 0.12, kind: 'whoosh', gain: 0.035 },
  { t: W_T.threeForce, kind: 'pluck', note: 'E5', gain: 0.042 },
  { t: W_T.perpShort, kind: 'chime', note: 'A5', gain: 0.04 },
];

register({ duration: TL.duration, fps: FPS, width: W, height: H, seek, meta: { cues: TL.cues, sfx } });
seek(0);
