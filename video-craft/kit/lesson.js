// lesson.js — General-purpose STEM & course explanation toolkit for seekable SVG/HTML scenes.
// Provides:
//   1. Offline synchronous LaTeX → SVG rendering via MathJax v3 (`\id{key}{expr}` sub-expression addressing)
//   2. Manim-style FLIP formula morphing (`morphFormulas`) and sub-term signaling boxes (`highlightTerm`)
//   3. Word-level narration timeline & semantic cue lookup (`buildTimeline`)
//   4. World-coordinate FocusCamera (`applyCamera`, `cameraFrame`) and engineering/math SVG primitives
//      (axes, function/parametric curves, force vectors, hatched surfaces, rigid blocks, springs, angle arcs, callouts).
// Every visual helper is a deterministic pure function of scene time `t`.

import { clamp, lerp, ease, FONT_STACK } from './kit.js';

const SVG_NS = 'http://www.w3.org/2000/svg';

export const THEMES = {
  slate: {
    bg: '#0C1220',
    bgGlow: '#162238',
    panel: '#131C2E',
    panelStroke: 'rgba(148, 163, 184, 0.20)',
    grid: 'rgba(148, 163, 184, 0.08)',
    ink: '#F1F5F9',
    muted: '#94A3B8',
    faint: '#475569',
    amber: '#F59E0B',   // primary focus / applied force / key extremum
    cyan: '#38BDF8',    // normal force / primary function / geometry
    coral: '#FB7185',   // friction / error trap / opposing term
    emerald: '#34D399', // resultant / verified conclusion
    violet: '#A78BFA',  // auxiliary angle / substitution variable
  },
  ivory: {
    bg: '#F6F4EE',
    bgGlow: '#FFFFFF',
    panel: '#EFECE4',
    panelStroke: 'rgba(24, 24, 27, 0.14)',
    grid: 'rgba(24, 24, 27, 0.06)',
    ink: '#18181B',
    muted: '#52525B',
    faint: '#A1A1AA',
    amber: '#D97706',
    cyan: '#0284C7',
    coral: '#E11D48',
    emerald: '#059669',
    violet: '#7C3AED',
  },
};

export function svgEl(tag, attrs = {}, parent = null) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v != null) el.setAttribute(k, String(v));
  }
  if (parent) parent.appendChild(el);
  return el;
}

export function clearEl(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
}

// ---- 1. Offline MathJax v3 SVG loader & \id{key}{expr} compiler ---------------------------------------------

let mathReady = false;

export async function loadMath(customUrl) {
  if (mathReady && window.MathJax?.tex2svg) return;
  const scriptUrl = customUrl || new URL('./vendor/mathjax/tex-svg-full.js', import.meta.url).href;
  window.MathJax = {
    tex: {
      packages: { '[+]': ['ams', 'mathtools', 'cancel', 'cases', 'html', 'color', 'boldsymbol', 'physics'] },
    },
    svg: { fontCache: 'none' }, // self-contained <path> glyphs so cloned/morphed sub-trees never lose <defs>
    startup: { typeset: false },
  };
  await new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = scriptUrl;
    s.onload = resolve;
    s.onerror = () => reject(new Error(`Failed to load MathJax bundle at ${scriptUrl}`));
    document.head.appendChild(s);
  });
  if (window.MathJax?.startup?.promise) await window.MathJax.startup.promise;
  mathReady = true;
}

// Expand `\id{key}{balanced expr}` into `\cssId{prefix__key}{balanced expr}` with proper nested brace matching.
export function expandIds(tex, prefix) {
  let out = '', i = 0;
  while (i < tex.length) {
    if (tex.startsWith('\\id{', i)) {
      const kStart = i + 4;
      const kEnd = tex.indexOf('}', kStart);
      if (kEnd > kStart && tex[kEnd + 1] === '{') {
        const key = tex.slice(kStart, kEnd).trim();
        let depth = 1, j = kEnd + 2;
        while (j < tex.length && depth > 0) {
          if (tex[j] === '\\') { j += 2; continue; }
          if (tex[j] === '{') depth++;
          else if (tex[j] === '}') depth--;
          j++;
        }
        if (depth === 0) {
          const inner = expandIds(tex.slice(kEnd + 2, j - 1), prefix);
          out += `\\cssId{${prefix}__${key}}{${inner}}`;
          i = j;
          continue;
        }
      }
    }
    out += tex[i++];
  }
  return out;
}

let formulaSeq = 0;

/**
 * Compile a LaTeX string into a measured, positionable SVG group.
 * Call once during scene setup (outside seek(t)), then manipulate transforms/opacity/highlights inside seek(t),
 * or use cached `texGroup()` which memoizes automatically!
 */
const texCache = new Map();

export function compileFormula(measureHost, tex, { size = 42, color = '#F1F5F9', display = true, idPrefix } = {}) {
  const uid = idPrefix || `fm${++formulaSeq}`;
  const key = `${uid}::${size}::${display}::${tex}`;
  if (texCache.has(key)) return texCache.get(key);
  if (!window.MathJax?.tex2svg) throw new Error('Call `await loadMath()` before compiling formulas.');

  const expanded = expandIds(tex, uid);
  const wrapper = window.MathJax.tex2svg(expanded, { display });
  const rawSvg = wrapper.querySelector('svg');
  if (!rawSvg) throw new Error(`MathJax produced no SVG for: ${tex}`);

  // MathJax sizes SVG in `ex`; 1 ex ≈ 0.46 * fontSize px. Convert to crisp scene pixels.
  const exW = parseFloat(rawSvg.getAttribute('width') || '1');
  const exH = parseFloat(rawSvg.getAttribute('height') || '1');
  const vb = (rawSvg.getAttribute('viewBox') || '0 0 1000 1000').split(/\s+/).map(Number);
  const pxW = exW * size * 0.48;
  const pxH = exH * size * 0.48;
  const sx = pxW / (vb[2] || 1);
  const sy = pxH / (vb[3] || 1);

  // Measure inside hidden SVG group in scene pixel space so getBBox() is exact and synchronous.
  // Note: MathJax SVG uses `fill="currentColor"`, which inherits from CSS `color`! Always set `color` alongside `fill`.
  const root = svgEl('g', { 'data-formula': uid, color, fill: color, stroke: color });
  const inner = svgEl('g', { transform: `scale(${sx}, ${sy}) translate(${-vb[0]}, ${-vb[1]})` }, root);
  for (const child of [...rawSvg.childNodes]) inner.appendChild(child.cloneNode(true));

  measureHost.appendChild(root);
  const fullBox = root.getBBox();

  // Map every `\id{part}{...}` sub-expression's bounding box in local formula pixel space (origin = formula top-left).
  const parts = {};
  const partNodes = root.querySelectorAll(`[id^="${uid}__"]`);
  const rootCTM = root.getScreenCTM();
  for (const node of partNodes) {
    const partName = node.getAttribute('id').slice(uid.length + 2);
    node.setAttribute('data-part', partName);
    const b = node.getBBox();
    const nCTM = node.getScreenCTM();
    if (rootCTM && nCTM && b.width > 0 && b.height > 0) {
      const m = rootCTM.inverse().multiply(nCTM);
      const x0 = m.a * b.x + m.c * b.y + m.e;
      const y0 = m.b * b.x + m.d * b.y + m.f;
      const x1 = m.a * (b.x + b.width) + m.c * (b.y + b.height) + m.e;
      const y1 = m.b * (b.x + b.width) + m.d * (b.y + b.height) + m.f;
      parts[partName] = {
        x: Math.min(x0, x1) - fullBox.x,
        y: Math.min(y0, y1) - fullBox.y,
        w: Math.abs(x1 - x0),
        h: Math.abs(y1 - y0),
      };
    }
  }
  measureHost.removeChild(root);

  // Normalize local origin so (0, 0) is the top-left of `fullBox`.
  const normRoot = svgEl('g', { 'data-formula': uid });
  const shift = svgEl('g', { transform: `translate(${-fullBox.x}, ${-fullBox.y})` }, normRoot);
  while (root.firstChild) shift.appendChild(root.firstChild);

  const compiled = {
    uid,
    tex,
    size,
    color,
    width: fullBox.width,
    height: fullBox.height,
    parts,
    template: normRoot,
  };
  texCache.set(key, compiled);
  return compiled;
}

/**
 * Place a compiled formula onto `parent` at `(x, y)` (anchor: 'left' | 'center' | 'right', vAnchor: 'top' | 'middle').
 * `partColors`: `{ key: '#38BDF8' }` colours tagged sub-expressions; `dimOthers`: 0..1 dims untagged/non-highlighted parts.
 */
export function drawFormula(parent, fm, x, y, {
  anchor = 'left',
  vAnchor = 'middle',
  alpha = 1,
  scale = 1,
  color = fm.color,
  partColors = {},
  partAlphas = {},
  hideParts = [],
} = {}) {
  if (alpha <= 0.001) return null;
  const ox = anchor === 'center' ? x - (fm.width * scale) / 2 : anchor === 'right' ? x - fm.width * scale : x;
  const oy = vAnchor === 'middle' ? y - (fm.height * scale) / 2 : vAnchor === 'bottom' ? y - fm.height * scale : y;
  const g = fm.template.cloneNode(true);
  g.setAttribute('transform', `translate(${ox}, ${oy}) scale(${scale})`);
  g.setAttribute('opacity', String(clamp(alpha)));
  g.setAttribute('color', color);
  g.style.color = color;
  g.setAttribute('fill', color);
  g.setAttribute('stroke', color);

  for (const [part, col] of Object.entries(partColors)) {
    if (!col) continue;
    for (const n of g.querySelectorAll(`[data-part="${part}"]`)) {
      n.setAttribute('color', col);
      n.style.color = col;
      n.setAttribute('fill', col);
      n.setAttribute('stroke', col);
    }
  }
  for (const [part, a] of Object.entries(partAlphas)) {
    for (const n of g.querySelectorAll(`[data-part="${part}"]`)) {
      n.setAttribute('opacity', String(clamp(a)));
    }
  }
  for (const part of hideParts) {
    for (const n of g.querySelectorAll(`[data-part="${part}"]`)) {
      n.setAttribute('opacity', '0');
    }
  }
  parent.appendChild(g);

  // Return world-space bounding boxes for the formula and each tagged part so callouts/boxes can attach!
  const worldParts = {};
  for (const [k, b] of Object.entries(fm.parts)) {
    worldParts[k] = {
      x: ox + b.x * scale,
      y: oy + b.y * scale,
      w: b.w * scale,
      h: b.h * scale,
      cx: ox + (b.x + b.w / 2) * scale,
      cy: oy + (b.y + b.h / 2) * scale,
    };
  }
  return { x: ox, y: oy, w: fm.width * scale, h: fm.height * scale, parts: worldParts, el: g };
}

/**
 * Manim-style `TransformMatchingTex` between two compiled formulas `fmA` (at posA) and `fmB` (at posB) over progress `k` in [0, 1].
 * Shared `\id{key}{...}` parts smoothly glide and scale from their exact bbox in A to their exact bbox in B!
 * Unmatched parts in A fade out upward; unmatched parts in B fade in cleanly.
 */
export function morphFormula(parent, fmA, posA, fmB, posB, k, {
  anchor = 'left',
  vAnchor = 'middle',
  color = fmB.color,
  partColorsA = {},
  partColorsB = {},
} = {}) {
  const p = clamp(k);
  if (p <= 0.001) return drawFormula(parent, fmA, posA[0], posA[1], { anchor, vAnchor, color: fmA.color, partColors: partColorsA });
  if (p >= 0.999) return drawFormula(parent, fmB, posB[0], posB[1], { anchor, vAnchor, color, partColors: partColorsB });

  const e = ease.inOut(p);
  const shared = Object.keys(fmA.parts).filter((id) => id in fmB.parts);

  // Compute world positions of A and B
  const oxA = anchor === 'center' ? posA[0] - fmA.width / 2 : anchor === 'right' ? posA[0] - fmA.width : posA[0];
  const oyA = vAnchor === 'middle' ? posA[1] - fmA.height / 2 : posA[1];
  const oxB = anchor === 'center' ? posB[0] - fmB.width / 2 : anchor === 'right' ? posB[0] - fmB.width : posB[0];
  const oyB = vAnchor === 'middle' ? posB[1] - fmB.height / 2 : posB[1];

  const morphGroup = svgEl('g', { 'data-formula': `${fmA.uid}_to_${fmB.uid}` }, parent);

  // 1. Outgoing unmatched structure of A fades out in first 55%
  const outAlpha = 1 - ease.out(clamp(p / 0.55));
  if (outAlpha > 0.005) {
    const outRes = drawFormula(morphGroup, fmA, posA[0], posA[1] - 10 * ease.in(clamp(p / 0.55)), {
      anchor, vAnchor, alpha: outAlpha, color: fmA.color, partColors: partColorsA, hideParts: shared,
    });
    outRes?.el?.removeAttribute('data-formula');
  }

  // 2. Incoming unmatched structure of B fades in over [0.35, 1.0]
  const inAlpha = ease.out(clamp((p - 0.35) / 0.65));
  let laidB = null;
  if (inAlpha > 0.005) {
    laidB = drawFormula(morphGroup, fmB, posB[0], posB[1] + 10 * (1 - inAlpha), {
      anchor, vAnchor, alpha: inAlpha, color, partColors: partColorsB, hideParts: shared,
    });
    laidB?.el?.removeAttribute('data-formula');
  }

  // 3. Shared tagged sub-expressions glide & scale uniformly (center-to-center, no rubbery aspect distortion)
  const morphedParts = {};
  for (const id of shared) {
    const a = fmA.parts[id], b = fmB.parts[id];
    const acx = oxA + a.x + a.w / 2, acy = oyA + a.y + a.h / 2;
    const bcx = oxB + b.x + b.w / 2, bcy = oyB + b.y + b.h / 2;
    const dx = bcx - acx, dy = bcy - acy;
    const arc = Math.abs(dx) > 36 && Math.abs(dy) < 28 ? -Math.sign(dx) * Math.sin(e * Math.PI) * Math.min(34, Math.abs(dx) * 0.16) : 0;
    const curCx = lerp(acx, bcx, e), curCy = lerp(acy, bcy, e) + arc;
    const ratioH = b.h / Math.max(1, a.h);
    const sA = lerp(1, clamp(ratioH, 0.65, 1.5), e);
    const sB = lerp(clamp(1 / ratioH, 0.65, 1.5), 1, e);

    const colA = partColorsA[id] || fmA.color;
    const colB = partColorsB[id] || color;

    const drawIsolatedPart = (fm, partBox, sc, op, col) => {
      if (op <= 0.01) return;
      const clone = fm.template.cloneNode(true);
      clone.removeAttribute('data-formula');
      const target = clone.querySelector(`[data-part="${id}"]`);
      if (!target) return;
      const keep = new Set();
      for (let cur = target; cur; cur = cur.parentElement) keep.add(cur);
      const prune = (node) => {
        for (const ch of [...node.children]) {
          if (ch === target) continue;
          if (keep.has(ch)) prune(ch);
          else ch.remove();
        }
      };
      prune(clone);
      for (const el of [clone, target]) {
        el.setAttribute('color', col);
        el.style.color = col;
        el.setAttribute('fill', col);
        el.setAttribute('stroke', col);
      }
      clone.setAttribute('opacity', String(clamp(op)));
      const pcx = partBox.x + partBox.w / 2, pcy = partBox.y + partBox.h / 2;
      clone.setAttribute('transform', `translate(${curCx.toFixed(2)}, ${curCy.toFixed(2)}) scale(${sc.toFixed(4)}) translate(${(-pcx).toFixed(2)}, ${(-pcy).toFixed(2)})`);
      morphGroup.appendChild(clone);
    };

    const exactSameGlyph = Math.abs(a.w - b.w) < 2 && Math.abs(a.h - b.h) < 2 && colA === colB;
    if (exactSameGlyph) {
      drawIsolatedPart(fmB, b, 1, 1, colB);
    } else {
      const crossA = clamp(1 - (e - 0.25) / 0.45);
      const crossB = clamp((e - 0.25) / 0.45);
      drawIsolatedPart(fmA, a, sA, crossA, colA);
      drawIsolatedPart(fmB, b, sB, crossB, colB);
    }

    const cw = lerp(a.w, b.w, e), ch = lerp(a.h, b.h, e);
    morphedParts[id] = { x: curCx - cw / 2, y: curCy - ch / 2, w: cw, h: ch, cx: curCx, cy: curCy };
  }

  return {
    x: lerp(oxA, oxB, e),
    y: lerp(oyA, oyB, e),
    w: lerp(fmA.width, fmB.width, e),
    h: lerp(fmA.height, fmB.height, e),
    parts: { ...(laidB?.parts || {}), ...morphedParts },
  };
}

/**
 * Draw a signaling highlight box / underline / callout badge around a formula sub-part bbox (Mayer's Signaling Principle).
 */
export function highlightPart(parent, partBox, k, {
  color = '#F59E0B',
  pad = 8,
  mode = 'box', // 'box' | 'underline'
  label = '',
  labelSide = 'bottom', // 'top' | 'bottom'
  exit = -1,
} = {}) {
  if (!partBox || k <= 0) return;
  const p = ease.out(clamp(k));
  const out = exit >= 0 ? 1 - ease.in(clamp(exit)) : 1;
  const alpha = p * out;
  if (alpha <= 0.01) return;

  const x = partBox.x - pad, y = partBox.y - pad, w = partBox.w + pad * 2, h = partBox.h + pad * 2;
  const g = svgEl('g', { opacity: alpha.toFixed(3) }, parent);
  if (mode === 'underline') {
    svgEl('line', {
      x1: x, y1: y + h, x2: x + w * p, y2: y + h,
      stroke: color, 'stroke-width': 3.5, 'stroke-linecap': 'round',
    }, g);
  } else {
    const perim = 2 * (w + h);
    svgEl('rect', {
      x, y, width: w, height: h, rx: 8,
      fill: color, 'fill-opacity': '0.11',
      stroke: color, 'stroke-width': 2.4,
      'stroke-dasharray': `${(perim * p).toFixed(1)} ${perim.toFixed(1)}`,
    }, g);
  }
  if (label) {
    const ly = labelSide === 'top' ? y - 12 : y + h + 26;
    const t = svgEl('text', {
      x: x + w / 2, y: ly,
      fill: color, 'font-family': FONT_STACK.sans, 'font-size': 22, 'font-weight': 700,
      'text-anchor': 'middle', opacity: clamp((p - 0.25) / 0.75).toFixed(3),
    }, g);
    t.textContent = label;
  }
}

// ---- 2. Word-Synced Narration Timeline ---------------------------------------------------------------------

const normToken = (s) => String(s || '')
  .toLowerCase()
  .replace(/[0-9]/g, (d) => '零一二三四五六七八九'[+d])
  .replace(/[^\u4e00-\u9fff\w]/g, '');

/**
 * Build global scene timeline from `cuesSpec = [{ id, text, gap }]` and optional `wordsData` (`vo/words.js`).
 * Exposes `tl.cue(id)` and `tl.word(id, phrase, fallbackFrac)` returning exact global scene timestamps!
 */
export function buildTimeline(cuesSpec, wordsData = {}, { leadIn = 0.45, tailOut = 2.4, charsPerSec = 4.3 } = {}) {
  let cursor = leadIn;
  const cues = [];
  const byId = {};

  for (const item of cuesSpec) {
    const rec = wordsData?.[item.id];
    const dur = rec?.duration ?? (typeof rec === 'number' ? rec : Math.max(1.8, [...item.text].length / charsPerSec));
    const words = Array.isArray(rec?.words) ? rec.words : [];
    const t0 = +cursor.toFixed(3);
    const t1 = +(t0 + dur).toFixed(3);
    const entry = { id: item.id, text: item.text, t0, t1, dur: +dur.toFixed(3), gap: item.gap ?? 0.4, words };
    cues.push(entry);
    byId[item.id] = entry;
    cursor = t1 + entry.gap;
  }

  const duration = +(cursor + tailOut).toFixed(2);

  function word(cueId, targetPhrase, fallbackFrac = null, occurrence = 0) {
    const c = byId[cueId];
    if (!c) throw new Error(`Unknown cue id: ${cueId}`);
    const needle = normToken(targetPhrase);
    if (needle && c.words.length) {
      // Match single token or sliding concatenation of tokens (handles split Chinese words & nth occurrence)
      let concat = '';
      const spans = [];
      for (const w of c.words) {
        const nw = normToken(w.w);
        if (!nw) continue;
        spans.push({ startIdx: concat.length, endIdx: concat.length + nw.length, t0: w.t0, t1: w.t1 });
        concat += nw;
      }
      let pos = -1, fromIdx = 0;
      for (let k = 0; k <= occurrence; k++) {
        pos = concat.indexOf(needle, fromIdx);
        if (pos < 0) break;
        fromIdx = pos + needle.length;
      }
      if (pos >= 0) {
        const hit = spans.find((s) => s.endIdx > pos);
        if (hit) return +(c.t0 + hit.t0).toFixed(3);
      }
    }
    // Graceful character-offset fallback when running before TTS or if a proper noun was transcribed differently
    if (fallbackFrac != null) return +(c.t0 + c.dur * clamp(fallbackFrac)).toFixed(3);
    const idx = c.text.indexOf(targetPhrase);
    const frac = idx >= 0 ? idx / Math.max(1, c.text.length) : 0.25;
    return +(c.t0 + c.dur * frac).toFixed(3);
  }

  return { cues, byId, duration, cue: (id) => byId[id], word };
}

// ---- 3. FocusCamera (MovingCameraScene in SVG world coordinates) -------------------------------------------

/**
 * Interpolate camera viewport `{ cx, cy, w }` across keyframes `[[t, { cx, cy, w }, easeFn?], ...]`.
 * Default full frame is `{ cx: 960, cy: 540, w: 1920 }` (16:9 aspect preserved automatically).
 */
export function cameraAt(t, keys, { width = 1920, height = 1080 } = {}) {
  const aspect = height / width;
  const full = { cx: width / 2, cy: height / 2, w: width };
  if (!keys || !keys.length) return { ...full, h: height, scale: 1 };
  const norm = (f) => ({ cx: f.cx ?? full.cx, cy: f.cy ?? full.cy, w: f.w ?? full.w });
  if (t <= keys[0][0]) {
    const a = norm(keys[0][1]);
    return { ...a, h: a.w * aspect, scale: width / a.w };
  }
  for (let i = 1; i < keys.length; i++) {
    const [t1, rawB, eFn] = keys[i];
    const [t0, rawA] = keys[i - 1];
    if (t <= t1) {
      const a = norm(rawA), b = norm(rawB);
      const p = (eFn || ease.inOut)(clamp((t - t0) / Math.max(1e-6, t1 - t0)));
      const w = Math.exp(lerp(Math.log(a.w), Math.log(b.w), p));
      return { cx: lerp(a.cx, b.cx, p), cy: lerp(a.cy, b.cy, p), w, h: w * aspect, scale: width / w };
    }
  }
  const last = norm(keys[keys.length - 1][1]);
  return { ...last, h: last.w * aspect, scale: width / last.w };
}

export function applyCamera(worldGroup, cam, { width = 1920, height = 1080 } = {}) {
  const s = cam.scale;
  const tx = width / 2 - cam.cx * s;
  const ty = height / 2 - cam.cy * s;
  worldGroup.setAttribute('transform', `translate(${tx.toFixed(2)}, ${ty.toFixed(2)}) scale(${s.toFixed(4)})`);
}

// ---- 4. STEM, Mechanics & Geometry SVG Primitives ----------------------------------------------------------

export function drawStageBackground(svg, theme = THEMES.slate, { gridStep = 60, width = 1920, height = 1080, glow = true, spotlight = [0.52, 0.46], vignette = 0.42 } = {}) {
  const defs = svgEl('defs', {}, svg);
  const spX = spotlight[0] > 1.5 ? spotlight[0] / width : spotlight[0];
  const spY = spotlight[1] > 1.5 ? spotlight[1] / height : spotlight[1];
  const grad = svgEl('radialGradient', {
    id: 'vc-stage-bg',
    cx: `${Math.round(clamp(spX, 0, 1) * 100)}%`,
    cy: `${Math.round(clamp(spY, 0, 1) * 100)}%`,
    r: '72%',
  }, defs);
  svgEl('stop', { offset: '0%', 'stop-color': theme.bgGlow }, grad);
  svgEl('stop', { offset: '100%', 'stop-color': theme.bg }, grad);

  if (glow) {
    // Soft optical bloom filter (`url(#vc-glow)`) for hero vectors, curves, and focal points
    const flt = svgEl('filter', { id: 'vc-glow', x: '-40%', y: '-40%', width: '180%', height: '180%' }, defs);
    svgEl('feGaussianBlur', { in: 'SourceGraphic', stdDeviation: '5.5', result: 'blur1' }, flt);
    svgEl('feGaussianBlur', { in: 'SourceGraphic', stdDeviation: '14', result: 'blur2' }, flt);
    const merge = svgEl('feMerge', {}, flt);
    svgEl('feMergeNode', { in: 'blur2' }, merge);
    svgEl('feMergeNode', { in: 'blur1' }, merge);
    svgEl('feMergeNode', { in: 'SourceGraphic' }, merge);

    const soft = svgEl('filter', { id: 'vc-glow-soft', x: '-30%', y: '-30%', width: '160%', height: '160%' }, defs);
    svgEl('feGaussianBlur', { in: 'SourceGraphic', stdDeviation: '3.2', result: 'b' }, soft);
    const m2 = svgEl('feMerge', {}, soft);
    svgEl('feMergeNode', { in: 'b' }, m2);
    svgEl('feMergeNode', { in: 'SourceGraphic' }, m2);
  }

  svgEl('rect', { x: 0, y: 0, width, height, fill: 'url(#vc-stage-bg)' }, svg);

  if (gridStep > 0) {
    const g = svgEl('g', { stroke: theme.grid, 'stroke-width': 1 }, svg);
    for (let x = gridStep; x < width; x += gridStep) svgEl('line', { x1: x, y1: 0, x2: x, y2: height }, g);
    for (let y = gridStep; y < height; y += gridStep) svgEl('line', { x1: 0, y1: y, x2: width, y2: y }, g);
  }

  if (vignette > 0) {
    const vg = svgEl('radialGradient', { id: 'vc-vignette', cx: '50%', cy: '50%', r: '72%' }, defs);
    svgEl('stop', { offset: '55%', 'stop-color': '#000000', 'stop-opacity': '0' }, vg);
    svgEl('stop', { offset: '100%', 'stop-color': '#000000', 'stop-opacity': String(vignette) }, vg);
    svgEl('rect', { x: 0, y: 0, width, height, fill: 'url(#vc-vignette)', 'pointer-events': 'none' }, svg);
  }
}

export function drawProblemHeader(parent, {
  tag = '例题精讲',
  title = '',
  stepLabel = '',
  progress = 0,
  theme = THEMES.slate,
  width = 1920,
} = {}) {
  const g = svgEl('g', { 'data-role': 'header' }, parent);
  svgEl('rect', { x: 0, y: 0, width, height: 78, fill: theme.panel, 'fill-opacity': '0.88' }, g);
  svgEl('line', { x1: 0, y1: 78, x2: width, y2: 78, stroke: theme.panelStroke, 'stroke-width': 1.5 }, g);
  if (progress > 0) {
    svgEl('line', { x1: 0, y1: 78, x2: width * clamp(progress), y2: 78, stroke: theme.amber, 'stroke-width': 3 }, g);
  }
  // Tag pill
  svgEl('rect', { x: 56, y: 20, width: 124, height: 38, rx: 8, fill: theme.amber, 'fill-opacity': '0.16', stroke: theme.amber, 'stroke-width': 1.5 }, g);
  const tTag = svgEl('text', { x: 118, y: 46, fill: theme.amber, 'font-family': FONT_STACK.sans, 'font-size': 20, 'font-weight': 700, 'text-anchor': 'middle' }, g);
  tTag.textContent = tag;

  const tTitle = svgEl('text', { x: 202, y: 48, fill: theme.ink, 'font-family': FONT_STACK.sans, 'font-size': 27, 'font-weight': 700 }, g);
  tTitle.textContent = title;

  if (stepLabel) {
    const tStep = svgEl('text', { x: width - 56, y: 47, fill: theme.cyan, 'font-family': FONT_STACK.sans, 'font-size': 22, 'font-weight': 700, 'text-anchor': 'end' }, g);
    tStep.textContent = stepLabel;
  }
  return g;
}

/**
 * Crisp physics/math vector arrow from `p0` to `p1` with progressive draw-on `k` (0..1) and optional compiled formula or text label.
 */
export function svgArrow(parent, p0, p1, k = 1, {
  color = '#F59E0B',
  width = 4.5,
  headLen = 18,
  headWidth = 13,
  dashed = false,
  glow = false,
  alpha = 1,
  label = '',
  formula = null,
  labelOffset = [14, -10],
  labelAnchor = 'left',
} = {}) {
  const p = ease.out(clamp(k));
  if (p <= 0.005 || alpha <= 0.005) return null;
  const dx = p1[0] - p0[0], dy = p1[1] - p0[1];
  const len = Math.hypot(dx, dy);
  if (len < 1e-3) return null;
  const ux = dx / len, uy = dy / len;
  const curLen = len * p;
  const tip = [p0[0] + ux * curLen, p0[1] + uy * curLen];
  const hl = Math.min(headLen, curLen * 0.65);
  const hw = headWidth * (hl / headLen);
  const shaftEnd = [tip[0] - ux * hl * 0.78, tip[1] - uy * hl * 0.78];

  const g = svgEl('g', { opacity: String(clamp(alpha)) }, parent);
  const vecG = glow ? svgEl('g', { filter: glow === 'soft' ? 'url(#vc-glow-soft)' : 'url(#vc-glow)' }, g) : g;
  const lineAttrs = {
    x1: p0[0], y1: p0[1], x2: shaftEnd[0], y2: shaftEnd[1],
    stroke: color, 'stroke-width': width, 'stroke-linecap': 'round',
  };
  if (dashed) lineAttrs['stroke-dasharray'] = '9 7';
  svgEl('line', lineAttrs, vecG);

  const nx = -uy, ny = ux;
  const b1 = [tip[0] - ux * hl + nx * hw * 0.5, tip[1] - uy * hl + ny * hw * 0.5];
  const b2 = [tip[0] - ux * hl - nx * hw * 0.5, tip[1] - uy * hl - ny * hw * 0.5];
  svgEl('polygon', {
    points: `${tip[0]},${tip[1]} ${b1[0]},${b1[1]} ${b2[0]},${b2[1]}`,
    fill: color,
  }, vecG);

  const labAlpha = clamp((p - 0.35) / 0.65) * alpha;
  if (labAlpha > 0.01) {
    const lx = tip[0] + labelOffset[0], ly = tip[1] + labelOffset[1];
    if (formula) {
      drawFormula(g, formula, lx, ly, { anchor: labelAnchor, vAnchor: 'middle', alpha: labAlpha, color });
    } else if (label) {
      const t = svgEl('text', {
        x: lx, y: ly + 8, fill: color, opacity: labAlpha.toFixed(3),
        'font-family': FONT_STACK.sans, 'font-size': 25, 'font-weight': 700,
        'text-anchor': labelAnchor === 'center' ? 'middle' : labelAnchor === 'right' ? 'end' : 'start',
      }, g);
      t.textContent = label;
    }
  }
  return { tip, g };
}

/**
 * Engineering ground / wall / inclined-plane surface line with standard 45° hatch ticks on the solid side.
 */
export function svgSurface(parent, p0, p1, k = 1, {
  color = '#94A3B8',
  hatchColor = 'rgba(148, 163, 184, 0.38)',
  width = 3.5,
  hatchLen = 16,
  spacing = 22,
  side = 1, // 1 = below/right of directed segment p0->p1, -1 = above/left
  scroll = 0, // pixel phase offset along surface (e.g. -t * 95 for rightward block motion)
  alpha = 1,
} = {}) {
  const p = ease.out(clamp(k));
  if (p <= 0.005 || alpha <= 0.005) return;
  const dx = p1[0] - p0[0], dy = p1[1] - p0[1], len = Math.hypot(dx, dy) || 1;
  const ux = dx / len, uy = dy / len;
  const nx = -uy * side, ny = ux * side;
  const visLen = len * p;
  const g = svgEl('g', { opacity: clamp(alpha).toFixed(3) }, parent);
  svgEl('line', {
    x1: p0[0], y1: p0[1], x2: p0[0] + dx * p, y2: p0[1] + dy * p,
    stroke: color, 'stroke-width': width, 'stroke-linecap': 'round',
  }, g);
  const phase = ((scroll % spacing) + spacing) % spacing;
  for (let d = phase; d <= visLen - 4; d += spacing) {
    if (d < 6) continue;
    const edgeFade = Math.min(1, d / 28, (visLen - d) / 28);
    const sx = p0[0] + ux * d, sy = p0[1] + uy * d;
    const ex = sx - ux * hatchLen * 0.65 + nx * hatchLen, ey = sy - uy * hatchLen * 0.65 + ny * hatchLen;
    svgEl('line', {
      x1: sx, y1: sy, x2: ex, y2: ey,
      stroke: hatchColor, 'stroke-width': 2, opacity: edgeFade.toFixed(2),
    }, g);
  }
}

/**
 * Rigid body block resting on or rotated at `angleDeg` (0 = horizontal; SVG y-down clockwise degrees).
 */
export function svgBlock(parent, cx, cy, w, h, {
  angleDeg = 0,
  fill = '#162338',
  stroke = '#E2E8F0',
  strokeWidth = 2.8,
  bevel = true,
  alpha = 1,
  formula = null,
  label = '',
} = {}) {
  if (alpha <= 0.005) return null;
  const g = svgEl('g', {
    transform: `translate(${cx.toFixed(2)}, ${cy.toFixed(2)}) rotate(${angleDeg.toFixed(2)})`,
    opacity: String(clamp(alpha)),
  }, parent);
  svgEl('rect', {
    x: -w / 2, y: -h / 2, width: w, height: h, rx: 9,
    fill, stroke, 'stroke-width': strokeWidth,
  }, g);
  if (bevel) {
    svgEl('line', {
      x1: -w / 2 + 8, y1: -h / 2 + 3, x2: w / 2 - 8, y2: -h / 2 + 3,
      stroke: '#FFFFFF', 'stroke-opacity': '0.26', 'stroke-width': 2, 'stroke-linecap': 'round',
    }, g);
  }
  // Subtle center-of-mass dot
  svgEl('circle', { cx: 0, cy: 0, r: 4.5, fill: stroke }, g);
  if (formula) {
    const fg = svgEl('g', { transform: `rotate(${(-angleDeg).toFixed(2)})` }, g);
    drawFormula(fg, formula, 0, -26, { anchor: 'center', vAnchor: 'middle', color: stroke });
  } else if (label) {
    // Place block mass label in upper-left quadrant so vertical force vectors from (0,0) never cross it
    const t = svgEl('text', {
      x: -w * 0.30, y: -h * 0.18, fill: stroke, 'font-family': FONT_STACK.sans, 'font-size': 23, 'font-weight': 700,
      'text-anchor': 'middle', transform: `rotate(${(-angleDeg).toFixed(2)})`,
    }, g);
    t.textContent = label;
  }
  return g;
}

/**
 * Mechanical coil/zigzag spring between `p0` and `p1`.
 */
export function svgSpring(parent, p0, p1, { coils = 9, amp = 12, color = '#94A3B8', width = 3, alpha = 1 } = {}) {
  if (alpha <= 0.005) return;
  const dx = p1[0] - p0[0], dy = p1[1] - p0[1], len = Math.hypot(dx, dy) || 1;
  const ux = dx / len, uy = dy / len, nx = -uy, ny = ux;
  const pad = Math.min(20, len * 0.14);
  const body = len - 2 * pad;
  const pts = [p0, [p0[0] + ux * pad, p0[1] + uy * pad]];
  const steps = coils * 2;
  for (let i = 1; i <= steps; i++) {
    const u = (i - 0.5) / steps;
    const sgn = i % 2 ? 1 : -1;
    pts.push([p0[0] + ux * (pad + body * u) + nx * amp * sgn, p0[1] + uy * (pad + body * u) + ny * amp * sgn]);
  }
  pts.push([p1[0] - ux * pad, p1[1] - uy * pad], p1);
  svgEl('polyline', {
    points: pts.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' '),
    fill: 'none', stroke: color, 'stroke-width': width, 'stroke-linejoin': 'round', 'stroke-linecap': 'round',
    opacity: String(clamp(alpha)),
  }, parent);
}

/**
 * Angle arc (or right-angle marker) at `vertex` between `deg0` and `deg1` (standard screen degrees: 0 = +x right, -90 = up).
 */
export function svgAngleArc(parent, vertex, deg0, deg1, r = 46, k = 1, {
  color = '#A78BFA',
  width = 2.6,
  fillAlpha = 0.14,
  formula = null,
  label = '',
  labelRadiusOffset = 24,
} = {}) {
  const p = ease.out(clamp(k));
  if (p <= 0.01) return;
  const a0 = (deg0 * Math.PI) / 180;
  const a1 = ((deg0 + (deg1 - deg0) * p) * Math.PI) / 180;
  const x0 = vertex[0] + Math.cos(a0) * r, y0 = vertex[1] + Math.sin(a0) * r;
  const x1 = vertex[0] + Math.cos(a1) * r, y1 = vertex[1] + Math.sin(a1) * r;
  const sweep = deg1 >= deg0 ? 1 : 0;
  const large = Math.abs((deg1 - deg0) * p) > 180 ? 1 : 0;

  const g = svgEl('g', {}, parent);
  if (fillAlpha > 0) {
    svgEl('path', {
      d: `M ${vertex[0]} ${vertex[1]} L ${x0} ${y0} A ${r} ${r} 0 ${large} ${sweep} ${x1} ${y1} Z`,
      fill: color, 'fill-opacity': String(fillAlpha * p),
    }, g);
  }
  svgEl('path', {
    d: `M ${x0} ${y0} A ${r} ${r} 0 ${large} ${sweep} ${x1} ${y1}`,
    fill: 'none', stroke: color, 'stroke-width': width,
  }, g);

  const mid = ((deg0 + deg1) / 2) * (Math.PI / 180);
  const lx = vertex[0] + Math.cos(mid) * (r + labelRadiusOffset);
  const ly = vertex[1] + Math.sin(mid) * (r + labelRadiusOffset);
  const la = clamp((p - 0.35) / 0.65);
  if (la > 0.01) {
    if (formula) drawFormula(g, formula, lx, ly, { anchor: 'center', vAnchor: 'middle', alpha: la, color });
    else if (label) {
      const t = svgEl('text', {
        x: lx, y: ly + 8, fill: color, opacity: la.toFixed(3),
        'font-family': FONT_STACK.sans, 'font-size': 22, 'font-weight': 700, 'text-anchor': 'middle',
      }, g);
      t.textContent = label;
    }
  }
}

/**
 * 2D Cartesian coordinate system inside pixel box `{ x, y, w, h }`. Returns mapper `{ x(v), y(v), pt(vx, vy) }`.
 */
export function svgAxes(parent, box, {
  xDomain = [0, 90],
  yDomain = [0, 1.2],
  xTicks = [],
  yTicks = [],
  xLabel = '',
  yLabel = '',
  color = '#94A3B8',
  gridColor = 'rgba(148, 163, 184, 0.12)',
  k = 1,
} = {}) {
  const p = ease.out(clamp(k));
  const mapX = (v) => box.x + ((v - xDomain[0]) / (xDomain[1] - xDomain[0])) * box.w;
  const mapY = (v) => box.y + box.h - ((v - yDomain[0]) / (yDomain[1] - yDomain[0])) * box.h;
  const pt = (vx, vy) => [mapX(vx), mapY(vy)];

  if (p > 0.01) {
    const g = svgEl('g', { opacity: p.toFixed(3) }, parent);
    for (const [tv] of xTicks) {
      const px = mapX(tv);
      svgEl('line', { x1: px, y1: box.y, x2: px, y2: box.y + box.h, stroke: gridColor, 'stroke-width': 1, 'stroke-dasharray': '5 5' }, g);
      svgEl('line', { x1: px, y1: box.y + box.h, x2: px, y2: box.y + box.h + 7, stroke: color, 'stroke-width': 2 }, g);
    }
    for (const [tv] of yTicks) {
      const py = mapY(tv);
      svgEl('line', { x1: box.x, y1: py, x2: box.x + box.w, y2: py, stroke: gridColor, 'stroke-width': 1, 'stroke-dasharray': '5 5' }, g);
      svgEl('line', { x1: box.x - 7, y1: py, x2: box.x, y2: py, stroke: color, 'stroke-width': 2 }, g);
    }
    // Axes arrows
    svgArrow(g, [box.x, box.y + box.h], [box.x + box.w + 22, box.y + box.h], p, { color, width: 2.8, headLen: 13, headWidth: 9, label: xLabel, labelOffset: [8, 6] });
    svgArrow(g, [box.x, box.y + box.h], [box.x, box.y - 22], p, { color, width: 2.8, headLen: 13, headWidth: 9, label: yLabel, labelOffset: [-8, -16], labelAnchor: 'center' });

    for (const [tv, lab] of xTicks) {
      const t = svgEl('text', { x: mapX(tv), y: box.y + box.h + 30, fill: color, 'font-family': FONT_STACK.sans, 'font-size': 20, 'text-anchor': 'middle' }, g);
      t.textContent = lab ?? String(tv);
    }
    for (const [tv, lab] of yTicks) {
      const t = svgEl('text', { x: box.x - 14, y: mapY(tv) + 7, fill: color, 'font-family': FONT_STACK.sans, 'font-size': 20, 'text-anchor': 'end' }, g);
      t.textContent = lab ?? String(tv);
    }
  }
  return { x: mapX, y: mapY, pt, box };
}

/**
 * Plot `y = fn(x)` on `axes` over `[x0, x1]` with progressive draw-on `k` (0..1), returning the current pen tip `[px, py, vx, vy]`.
 */
export function svgPlot(parent, axes, fn, k = 1, {
  domain,
  samples = 160,
  color = '#38BDF8',
  width = 4,
  fillAlpha = 0.12,
  dashed = false,
  glow = false,
} = {}) {
  const p = clamp(k);
  if (p <= 0.002) return null;
  const [d0, d1] = domain || [0, 1];
  const xEnd = lerp(d0, d1, p);
  const n = Math.max(2, Math.round(samples * p));
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const vx = lerp(d0, xEnd, i / n);
    const vy = fn(vx);
    pts.push(axes.pt(vx, vy));
  }
  const d = pts.map((q, i) => `${i ? 'L' : 'M'} ${q[0].toFixed(2)} ${q[1].toFixed(2)}`).join(' ');
  const g = svgEl('g', {}, parent);
  if (fillAlpha > 0 && pts.length > 1) {
    const baseY = axes.box.y + axes.box.h;
    svgEl('path', {
      d: `${d} L ${pts[pts.length - 1][0].toFixed(2)} ${baseY.toFixed(2)} L ${pts[0][0].toFixed(2)} ${baseY.toFixed(2)} Z`,
      fill: color, 'fill-opacity': String(fillAlpha),
    }, g);
  }
  const attrs = { d, fill: 'none', stroke: color, 'stroke-width': width, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' };
  if (dashed) attrs['stroke-dasharray'] = '8 6';
  if (glow) attrs.filter = glow === 'soft' ? 'url(#vc-glow-soft)' : 'url(#vc-glow)';
  svgEl('path', attrs, g);
  const last = pts[pts.length - 1];
  return { x: last[0], y: last[1], vx: xEnd, vy: fn(xEnd) };
}

// ---- 5. CS, Systems & Engineering Block / Array / Connector Primitives -------------------------------------

/**
 * Crisp node / state / system stage box centred at `(cx, cy)` with optional top badge, subtitle, or formula.
 */
export function svgNodeBox(parent, cx, cy, w, h, {
  title = '',
  sub = '',
  badge = '',
  formula = null,
  fill = '#162236',
  stroke = '#38BDF8',
  textColor = '#F1F5F9',
  subColor = '#94A3B8',
  rx = 12,
  alpha = 1,
  highlight = false,
} = {}) {
  if (alpha <= 0.005) return null;
  const x = cx - w / 2, y = cy - h / 2;
  const g = svgEl('g', { opacity: clamp(alpha).toFixed(3) }, parent);
  if (highlight) {
    svgEl('rect', { x: x - 5, y: y - 5, width: w + 10, height: h + 10, rx: rx + 4, fill: stroke, 'fill-opacity': '0.16' }, g);
  }
  svgEl('rect', { x, y, width: w, height: h, rx, fill, stroke, 'stroke-width': highlight ? 3 : 2 }, g);
  if (badge) {
    const bt = svgEl('text', { x: x + 14, y: y - 8, fill: stroke, 'font-family': FONT_STACK.sans, 'font-size': 18, 'font-weight': 700 }, g);
    bt.textContent = badge;
  }
  if (formula) {
    drawFormula(g, formula, cx, sub ? cy - 10 : cy, { anchor: 'center', vAnchor: 'middle', color: textColor });
  } else if (title) {
    const t = svgEl('text', {
      x: cx, y: sub ? cy - 4 : cy + 8, fill: textColor,
      'font-family': FONT_STACK.sans, 'font-size': 24, 'font-weight': 700, 'text-anchor': 'middle',
    }, g);
    t.textContent = title;
  }
  if (sub) {
    const st = svgEl('text', {
      x: cx, y: cy + 24, fill: subColor,
      'font-family': FONT_STACK.sans, 'font-size': 19, 'font-weight': 400, 'text-anchor': 'middle',
    }, g);
    st.textContent = sub;
  }
  return {
    cx, cy, x, y, w, h,
    top: [cx, y], bottom: [cx, y + h], left: [x, cy], right: [x + w, cy],
    el: g,
  };
}

/**
 * 1D array / queue / memory / pipeline strip starting at top-left `(x, y)`.
 * `activeColors`: `{ index: '#F59E0B' }`; `pointers`: `[{ index: 2, name: 'i', color: '#38BDF8', side: 'top'|'bottom' }]`.
 * Returns `{ cells: [{ cx, cy, x, y, w, h }, ...] }` for animating swaps, windows, or arrows.
 */
export function svgArray(parent, x, y, values, {
  cellW = 84,
  cellH = 68,
  gap = 4,
  fill = '#131C2E',
  stroke = 'rgba(148, 163, 184, 0.35)',
  textColor = '#F1F5F9',
  indexColor = '#64748B',
  showIndex = true,
  activeColors = {},
  pointers = [],
  alpha = 1,
} = {}) {
  if (alpha <= 0.005) return { cells: [] };
  const g = svgEl('g', { opacity: clamp(alpha).toFixed(3) }, parent);
  const cells = values.map((val, i) => {
    const cx = x + i * (cellW + gap) + cellW / 2, cy = y + cellH / 2;
    const col = activeColors[i];
    svgEl('rect', {
      x: cx - cellW / 2, y, width: cellW, height: cellH, rx: 8,
      fill: col ? col : fill, 'fill-opacity': col ? '0.20' : '0.90',
      stroke: col || stroke, 'stroke-width': col ? 2.8 : 1.8,
    }, g);
    const t = svgEl('text', {
      x: cx, y: cy + 9, fill: col || textColor,
      'font-family': FONT_STACK.sans, 'font-size': 25, 'font-weight': 700, 'text-anchor': 'middle',
    }, g);
    t.textContent = String(val);
    if (showIndex) {
      const idx = svgEl('text', {
        x: cx, y: y + cellH + 24, fill: indexColor,
        'font-family': FONT_STACK.sans, 'font-size': 18, 'text-anchor': 'middle',
      }, g);
      idx.textContent = String(i);
    }
    return { cx, cy, x: cx - cellW / 2, y, w: cellW, h: cellH };
  });

  for (const ptr of pointers) {
    const c = cells[ptr.index];
    if (!c) continue;
    const pCol = ptr.color || '#F59E0B';
    if (ptr.side === 'bottom') {
      const base = y + cellH + (showIndex ? 62 : 42);
      svgArrow(g, [c.cx, base], [c.cx, y + cellH + (showIndex ? 30 : 6)], 1, {
        color: pCol, width: 3.2, headLen: 12, headWidth: 9,
      });
      const pt = svgEl('text', { x: c.cx, y: base + 24, fill: pCol, 'font-family': FONT_STACK.sans, 'font-size': 21, 'font-weight': 700, 'text-anchor': 'middle' }, g);
      pt.textContent = ptr.name;
    } else {
      svgArrow(g, [c.cx, y - 42], [c.cx, y - 6], 1, {
        color: pCol, width: 3.2, headLen: 12, headWidth: 9,
      });
      const pt = svgEl('text', { x: c.cx, y: y - 50, fill: pCol, 'font-family': FONT_STACK.sans, 'font-size': 21, 'font-weight': 700, 'text-anchor': 'middle' }, g);
      pt.textContent = ptr.name;
    }
  }
  return { cells, g };
}

/**
 * Curved or straight directed connector from `p0` to `p1` (`bend` = perpendicular pixel arc offset, 0 = straight).
 */
export function svgConnect(parent, p0, p1, k = 1, {
  bend = 0,
  color = '#94A3B8',
  width = 3,
  dashed = false,
  label = '',
  formula = null,
  alpha = 1,
} = {}) {
  const p = ease.out(clamp(k));
  if (p <= 0.01 || alpha <= 0.005) return null;
  if (Math.abs(bend) < 1) return svgArrow(parent, p0, p1, p, { color, width, dashed, alpha, label, formula });

  const dx = p1[0] - p0[0], dy = p1[1] - p0[1], len = Math.hypot(dx, dy) || 1;
  const nx = -dy / len, ny = dx / len;
  const ctrl = [(p0[0] + p1[0]) / 2 + nx * bend, (p0[1] + p1[1]) / 2 + ny * bend];

  // Sample quadratic Bezier up to `p`
  const N = 28, pts = [];
  for (let i = 0; i <= N; i++) {
    const u = (i / N) * p, v = 1 - u;
    pts.push([v * v * p0[0] + 2 * v * u * ctrl[0] + u * u * p1[0], v * v * p0[1] + 2 * v * u * ctrl[1] + u * u * p1[1]]);
  }
  const tip = pts[pts.length - 1], prev = pts[Math.max(0, pts.length - 2)];
  const tdx = tip[0] - prev[0], tdy = tip[1] - prev[1], tlen = Math.hypot(tdx, tdy) || 1;
  const ux = tdx / tlen, uy = tdy / tlen, px = -uy, py = ux;
  const hl = 14, hw = 10;

  const g = svgEl('g', { opacity: clamp(alpha).toFixed(3) }, parent);
  const d = pts.map((q, i) => `${i ? 'L' : 'M'} ${q[0].toFixed(1)} ${q[1].toFixed(1)}`).join(' ');
  const attrs = { d, fill: 'none', stroke: color, 'stroke-width': width, 'stroke-linecap': 'round' };
  if (dashed) attrs['stroke-dasharray'] = '8 6';
  svgEl('path', attrs, g);
  svgEl('polygon', {
    points: `${tip[0]},${tip[1]} ${tip[0] - ux * hl + px * hw * 0.5},${tip[1] - uy * hl + py * hw * 0.5} ${tip[0] - ux * hl - px * hw * 0.5},${tip[1] - uy * hl - py * hw * 0.5}`,
    fill: color,
  }, g);

  if (p > 0.5 && (label || formula)) {
    const mid = [0.25 * p0[0] + 0.5 * ctrl[0] + 0.25 * p1[0] + nx * 16 * Math.sign(bend), 0.25 * p0[1] + 0.5 * ctrl[1] + 0.25 * p1[1] + ny * 16 * Math.sign(bend)];
    if (formula) drawFormula(g, formula, mid[0], mid[1], { anchor: 'center', alpha: (p - 0.5) * 2, color });
    else {
      const t = svgEl('text', { x: mid[0], y: mid[1] + 6, fill: color, 'font-family': FONT_STACK.sans, 'font-size': 20, 'font-weight': 700, 'text-anchor': 'middle' }, g);
      t.textContent = label;
    }
  }
  return { g, tip };
}

// ---- 6. Spatial Emergence: Vector Detach-Morph, Polar Locus Fan & 3D Projection ----------------------------

/**
 * Smoothly detach & fly a vector arrow from `[a0, a1]` (e.g. attached to a physical block) to `[b0, b1]`
 * (e.g. tip-to-tail in a free-floating closed vector polygon) over progress `m` in [0, 1], with optional arched flight.
 */
export function svgMorphArrow(parent, a0, a1, b0, b1, m, opts = {}) {
  const e = ease.inOut(clamp(m));
  const arc = opts.arc ?? 0;
  const lift = Math.sin(e * Math.PI) * arc;
  const p0 = [lerp(a0[0], b0[0], e), lerp(a0[1], b0[1], e) - lift];
  const p1 = [lerp(a1[0], b1[0], e), lerp(a1[1], b1[1], e) - lift];
  return svgArrow(parent, p0, p1, opts.k ?? 1, opts);
}

/**
 * Emergent polar / parametric vector locus fan directly in physical space!
 * Sweeps parameter `u` from `u0` to `lerp(u0, u1, clamp(k))`, drawing faint ghost spokes, shaded swept sector,
 * and a luminous locus curve through all vector tips `tipFn(u) -> [x, y]`.
 */
export function svgLocusFan(parent, origin, tipFn, k, {
  domain = [0, 75],
  samples = 90,
  spokeStep = 9,
  color = '#F59E0B',
  spokeColor = 'rgba(245, 158, 11, 0.20)',
  fillAlpha = 0.09,
  width = 3.5,
  glow = 'soft',
} = {}) {
  const p = clamp(k);
  if (p <= 0.005) return null;
  const [u0, u1] = domain;
  const uMax = lerp(u0, u1, p);
  const n = Math.max(2, Math.round(samples * p));
  const pts = [];
  for (let i = 0; i <= n; i++) pts.push(tipFn(lerp(u0, uMax, i / n)));

  const g = svgEl('g', {}, parent);
  const dCurve = pts.map((q, i) => `${i ? 'L' : 'M'} ${q[0].toFixed(2)} ${q[1].toFixed(2)}`).join(' ');

  if (fillAlpha > 0 && pts.length > 1) {
    svgEl('path', {
      d: `M ${origin[0].toFixed(2)} ${origin[1].toFixed(2)} L ${pts.map((q) => `${q[0].toFixed(2)} ${q[1].toFixed(2)}`).join(' L ')} Z`,
      fill: color, 'fill-opacity': String(fillAlpha),
    }, g);
  }

  for (let u = u0; u <= uMax + 1e-3; u += spokeStep) {
    const tp = tipFn(u);
    svgEl('line', {
      x1: origin[0], y1: origin[1], x2: tp[0], y2: tp[1],
      stroke: spokeColor, 'stroke-width': 1.5, 'stroke-dasharray': '4 5',
    }, g);
    svgEl('circle', { cx: tp[0], cy: tp[1], r: 2.8, fill: color, 'fill-opacity': '0.45' }, g);
  }

  const curveAttrs = {
    d: dCurve, fill: 'none', stroke: color, 'stroke-width': width, 'stroke-linecap': 'round',
  };
  if (glow) curveAttrs.filter = glow === 'soft' ? 'url(#vc-glow-soft)' : 'url(#vc-glow)';
  svgEl('path', curveAttrs, g);
  return { pts, last: pts[pts.length - 1], g };
}

/**
 * Lightweight 3D perspective camera projector `(x, y, z) -> [px, py, depth]` for 3D fields, surfaces & mechanics.
 * `yaw` (azimuth around vertical Z/Y) and `pitch` (elevation) in radians.
 */
export function makeCamera3D({ cx = 960, cy = 560, scale = 180, yaw = -0.65, pitch = 0.48, dist = 6.5 } = {}) {
  const cyaw = Math.cos(yaw), syaw = Math.sin(yaw);
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  return (x, y, z) => {
    // World: x right, y forward/depth, z up
    const rx = x * cyaw - y * syaw;
    const ry = x * syaw + y * cyaw;
    const vx = rx;
    const vy = z * cp - ry * sp;
    const vz = z * sp + ry * cp;
    const persp = dist / Math.max(0.4, dist + vz * 0.35);
    return [cx + vx * scale * persp, cy - vy * scale * persp, vz];
  };
}
