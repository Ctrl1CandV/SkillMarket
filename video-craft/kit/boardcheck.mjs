// boardcheck.mjs — layout-agnostic geometric & visual hygiene inspector for seekable video scenes.
// Checks sampled frames at target resolution for:
//   1. Off-screen / safe-margin overflow of text and formula blocks
//   2. Pairwise bounding-box collisions between distinct text / formula blocks
//   3. Tiny unreadable text (< 18 px at 1080p equivalent)
//   4. Solid stroke crossing text core (respecting opaque background label pills)
//   5. Global display-formula crowding & multi-box dashboard fragmentation ("card soup")
//   6. Nearly empty frames (`--min-active 0.008`)
// usage: node boardcheck.mjs <page.html> [--every 3] [--times 1,5,12] [--margin 36] [--min-px 18] [--max-formulas 3] [--min-active 0.008]
import { launch, fileUrl } from './env.mjs';

const [pagePath, ...rest] = process.argv.slice(2);
const opt = (k, d) => { const i = rest.indexOf('--' + k); return i >= 0 ? rest[i + 1] : d; };

const browser = await launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(fileUrl(pagePath));
await page.waitForFunction(() => window.__video, null, { timeout: 60000 });
const v = await page.evaluate(() => window.__video);
await page.setViewportSize({ width: v.width, height: v.height });

const margin = +opt('margin', String(Math.round(v.height * 0.03)));
const baseMinPx = +opt('min-px', '18');
const maxFormulas = +opt('max-formulas', '3');
const minActive = +opt('min-active', '0.008');
const every = +opt('every', '3');
const times = opt('times')
  ? opt('times').split(',').map(Number)
  : Array.from({ length: Math.max(2, Math.ceil(v.duration / every)) }, (_, i) => Math.min(v.duration - 0.05, +(i * every + 0.4).toFixed(2)));

const issues = [];
const warnings = [];
const stats = [];

for (const t of times) {
  await page.evaluate((time) => window.__seek(time), t);
  const domCheck = await page.evaluate(({ W, H, M, BASE_MIN_PX, MAX_FM }) => {
    const vis = (el) => {
      for (let cur = el; cur && cur !== document.documentElement; cur = cur.parentElement) {
        const st = getComputedStyle(cur);
        if (st.display === 'none' || st.visibility === 'hidden' || parseFloat(st.opacity) < 0.08) return false;
      }
      return true;
    };

    const domOrder = new Map();
    let seq = 0;
    const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
    while (walk.nextNode()) domOrder.set(walk.currentNode, ++seq);

    const segHitsRect = (x1, y1, x2, y2, rx, ry, rw, rh) => {
      let t0 = 0, t1 = 1;
      const dx = x2 - x1, dy = y2 - y1;
      const checks = [[-dx, x1 - rx], [dx, rx + rw - x1], [-dy, y1 - ry], [dy, ry + rh - y1]];
      for (const [p, q] of checks) {
        if (Math.abs(p) < 1e-6) { if (q < 0) return false; }
        else {
          const r = q / p;
          if (p < 0) { if (r > t1) return false; if (r > t0) t0 = r; }
          else { if (r < t0) return false; if (r < t1) t1 = r; }
        }
      }
      return t0 <= t1;
    };

    // Collect opaque <rect> backgrounds (so dimension lines masked behind a label pill aren't false-flagged)
    // and count medium/large framed boxes to warn on >=5 dashboard "card soup".
    const maskRects = [];
    const cardBoxes = [];
    const screenArea = W * H;
    for (const rc of document.querySelectorAll('svg rect, body div, body section, body article')) {
      if (rc.closest('[data-formula]') || !vis(rc)) continue;
      const st = getComputedStyle(rc);
      const r = rc.getBoundingClientRect();
      if (r.width < 12 || r.height < 12) continue;
      const isSvg = rc.namespaceURI?.includes('svg');
      let hasOpaqueFill = false;
      let hasFrame = false;
      if (isSvg) {
        const fill = rc.getAttribute('fill') || st.fill || 'none';
        const fOp = parseFloat(rc.getAttribute('fill-opacity') || st.fillOpacity || '1');
        hasOpaqueFill = fill !== 'none' && fill !== 'transparent' && !fill.startsWith('url(') && fOp >= 0.65;
        const stroke = rc.getAttribute('stroke') || st.stroke || 'none';
        hasFrame = stroke !== 'none' && stroke !== 'transparent';
      } else {
        const bg = st.backgroundColor || '';
        const m = bg.match(/rgba?\(([^)]+)\)/);
        const alpha = m && m[1].split(',').length === 4 ? parseFloat(m[1].split(',')[3]) : (bg && bg !== 'transparent' ? 1 : 0);
        hasOpaqueFill = alpha >= 0.65;
        hasFrame = parseFloat(st.borderTopWidth || '0') >= 1;
      }
      const ord = domOrder.get(rc) || 0;
      if (hasOpaqueFill && r.width < W * 0.85) {
        maskRects.push({ ord, x: r.left, y: r.top, w: r.width, h: r.height });
      }
      const share = (r.width * r.height) / screenArea;
      if ((hasFrame || hasOpaqueFill) && share >= 0.038 && share <= 0.46 && r.width >= 180 && r.height >= 85) {
        cardBoxes.push([Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]);
      }
    }

    const items = [];
    for (const fm of document.querySelectorAll('[data-formula]')) {
      if (!vis(fm)) continue;
      const r = fm.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      items.push({
        kind: 'formula',
        role: fm.getAttribute('data-formula-role') || 'display',
        label: fm.getAttribute('data-formula'),
        ord: domOrder.get(fm) || 0,
        x: r.left, y: r.top, w: r.width, h: r.height,
      });
    }
    for (const tx of document.querySelectorAll('svg text, body p, body h1, body h2, body h3, body h4, body span, body div')) {
      if (tx.closest('[data-formula]') || !vis(tx)) continue;
      const isSvgText = tx.tagName.toLowerCase() === 'text';
      if (!isSvgText) {
        const hasDirectText = [...tx.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 0);
        if (!hasDirectText) continue;
      }
      const txt = (tx.textContent || '').trim();
      if (!txt) continue;
      const r = tx.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      const px = parseFloat(getComputedStyle(tx).fontSize) || r.height;
      items.push({ kind: 'text', label: txt.slice(0, 24), ord: domOrder.get(tx) || 0, x: r.left, y: r.top, w: r.width, h: r.height, fontSize: px });
    }

    // Collect solid geometry strokes (`svg line` with strokeWidth >= 2.5 outside formulas) to catch ray/vector crossing labels
    const strokes = [];
    for (const ln of document.querySelectorAll('svg line')) {
      if (ln.closest('[data-formula]') || !vis(ln)) continue;
      const st = getComputedStyle(ln);
      const sw = parseFloat(st.strokeWidth || ln.getAttribute('stroke-width') || '0');
      const dash = st.strokeDasharray || ln.getAttribute('stroke-dasharray') || 'none';
      if (sw < 2.5 || (dash && dash !== 'none')) continue;
      const ctm = ln.getScreenCTM();
      if (!ctm) continue;
      const x1 = +ln.getAttribute('x1') || 0, y1 = +ln.getAttribute('y1') || 0;
      const x2 = +ln.getAttribute('x2') || 0, y2 = +ln.getAttribute('y2') || 0;
      const sx1 = ctm.a * x1 + ctm.c * y1 + ctm.e, sy1 = ctm.b * x1 + ctm.d * y1 + ctm.f;
      const sx2 = ctm.a * x2 + ctm.c * y2 + ctm.e, sy2 = ctm.b * x2 + ctm.d * y2 + ctm.f;
      if (Math.hypot(sx2 - sx1, sy2 - sy1) < 24) continue;
      strokes.push({ ord: domOrder.get(ln) || 0, pts: [sx1, sy1, sx2, sy2] });
    }

    const frameIssues = [];
    const frameWarnings = [];
    const minPx = (H / 1080) * BASE_MIN_PX;
    const onScreen = [];
    for (const it of items) {
      if (it.x + it.w <= 2 || it.x >= W - 2 || it.y + it.h <= 2 || it.y >= H - 2) continue;
      onScreen.push(it);
      if (it.x < M * 0.5 || it.y < M * 0.4 || it.x + it.w > W - M * 0.5 || it.y + it.h > H - M * 0.4) {
        frameIssues.push({ type: 'margin_overflow', item: it.label, box: [Math.round(it.x), Math.round(it.y), Math.round(it.w), Math.round(it.h)] });
      }
      if (it.kind === 'text' && it.fontSize < minPx) {
        frameIssues.push({ type: 'tiny_text', item: it.label, fontSize: +it.fontSize.toFixed(1), minPx: +minPx.toFixed(1) });
      }
      if (it.w >= 26 && it.h >= 14) {
        const cx = it.x + it.w * 0.16, cy = it.y + it.h * 0.24, cw = it.w * 0.68, ch = it.h * 0.52;
        for (const s of strokes) {
          const [x1, y1, x2, y2] = s.pts;
          if (Math.abs(y2 - y1) < 2 && (Math.abs(y1 - it.y) < 8 || Math.abs(y1 - (it.y + it.h)) < 8)) continue;
          if (segHitsRect(x1, y1, x2, y2, cx, cy, cw, ch)) {
            const shielded = maskRects.some((mr) => mr.ord > s.ord && mr.ord < it.ord
              && mr.x <= cx + 2 && mr.y <= cy + 2 && mr.x + mr.w >= cx + cw - 2 && mr.y + mr.h >= cy + ch - 2);
            if (!shielded) {
              frameIssues.push({ type: 'line_crosses_label', item: it.label });
              break;
            }
          }
        }
      }
    }

    // Layout-agnostic display formula crowding check (no left/right split bias; short inline/diagram labels excluded)
    const visFormulas = onScreen.filter((it) => it.kind === 'formula' && it.role !== 'label' && (it.w >= 270 || it.h >= 70));
    if (visFormulas.length > MAX_FM) {
      frameIssues.push({
        type: 'formula_crowding',
        formulasOnScreen: visFormulas.length,
        maxAllowed: MAX_FM,
        hint: 'Too many full display formulas stacked simultaneously. Morph in-place or fade out completed intermediate steps.',
      });
    }

    if (cardBoxes.length >= 5) {
      frameWarnings.push({
        type: 'card_soup',
        cardCount: cardBoxes.length,
        hint: 'Screen is fragmented into >=5 separate framed cards/boxes. Give one primary dynamic visual world dominant stage space.',
      });
    }

    // Pairwise collision check among distinct visible on-screen items
    for (let i = 0; i < onScreen.length; i++) {
      for (let j = i + 1; j < onScreen.length; j++) {
        const a = onScreen[i], b = onScreen[j];
        const ix = Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x));
        const iy = Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));
        const area = ix * iy;
        if (area <= 0) continue;
        const smaller = Math.min(a.w * a.h, b.w * b.h);
        if (area / smaller > 0.16) {
          frameIssues.push({ type: 'overlap', a: a.label, b: b.label, share: +(area / smaller).toFixed(2) });
        }
      }
    }
    return { count: items.length, frameIssues, frameWarnings };
  }, { W: v.width, H: v.height, M: margin, BASE_MIN_PX: baseMinPx, MAX_FM: maxFormulas });

  // Dominant-mode background luminance & pixel occupancy check (handles split/gradient stages cleanly)
  const shotBuf = await page.screenshot({ type: 'jpeg', quality: 75 });
  const pix = await page.evaluate(async (b64) => {
    const img = new Image();
    await new Promise((res) => { img.onload = res; img.src = 'data:image/jpeg;base64,' + b64; });
    const W = 160, H = 90;
    const c = new OffscreenCanvas(W, H), x = c.getContext('2d');
    x.drawImage(img, 0, 0, W, H);
    const d = x.getImageData(0, 0, W, H).data;
    const lum = (px, py) => { const k = (py * W + px) * 4; return 0.299 * d[k] + 0.587 * d[k + 1] + 0.114 * d[k + 2]; };
    const bins = new Array(32).fill(0);
    const binSum = new Array(32).fill(0);
    for (let py = 10; py < H - 4; py += 2) {
      for (let px = 4; px < W - 4; px += 2) {
        const L = lum(px, py);
        const b = Math.min(31, Math.floor(L / 8));
        bins[b]++;
        binSum[b] += L;
      }
    }
    let bestBin = 0;
    for (let i = 1; i < 32; i++) if (bins[i] > bins[bestBin]) bestBin = i;
    const bg = binSum[bestBin] / Math.max(1, bins[bestBin]);

    let activeL = 0, activeR = 0;
    for (let py = 10; py < H - 4; py++) {
      for (let px = 4; px < W - 4; px++) {
        if (Math.abs(lum(px, py) - bg) > 20) {
          if (px < W / 2) activeL++; else activeR++;
        }
      }
    }
    const bodyPx = (W - 8) * (H - 14);
    return { activeShare: +((activeL + activeR) / bodyPx).toFixed(3), leftShare: +(activeL / Math.max(1, activeL + activeR)).toFixed(2) };
  }, shotBuf.toString('base64'));

  if (pix.activeShare < minActive) {
    domCheck.frameIssues.push({ type: 'nearly_empty_frame', activeShare: pix.activeShare, minActive });
  } else if (pix.activeShare < 0.024 && domCheck.count < 10) {
    domCheck.frameWarnings.push({
      type: 'low_visual_substance',
      activeShare: pix.activeShare,
      hint: 'Visual density is sparse (<2.4% active pixels with few elements). Inspect full-res stills to confirm intentional negative space rather than bare thin lines.',
    });
  }
  for (const f of domCheck.frameIssues) issues.push({ t, ...f });
  for (const w of domCheck.frameWarnings) warnings.push({ t, ...w });
  stats.push({ t, items: domCheck.count, activeShare: pix.activeShare, leftShare: pix.leftShare });
}

console.log(JSON.stringify({ framesChecked: times.length, issueCount: issues.length, warningCount: warnings.length, issues, warnings, stats }, null, 2));
await browser.close();
process.exit(issues.length ? 1 : 0);
