// boardcheck.mjs — geometric & visual hygiene inspector for seekable video scenes.
// Checks sampled frames at target resolution for:
//   1. Off-screen / safe-margin overflow of text and formula blocks
//   2. Pairwise bounding-box collisions between distinct text / formula / card blocks
//   3. Tiny unreadable text (< 18 px at 1080p equivalent)
//   4. Frame occupancy & left/right dead-space imbalance (pixel activity analysis)
// usage: node boardcheck.mjs <page.html> [--every 3] [--times 1,5,12] [--margin 36]
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
const every = +opt('every', '3');
const times = opt('times')
  ? opt('times').split(',').map(Number)
  : Array.from({ length: Math.max(2, Math.ceil(v.duration / every)) }, (_, i) => Math.min(v.duration - 0.05, +(i * every + 0.4).toFixed(2)));

const issues = [];
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

    const segHitsRect = (x1, y1, x2, y2, rx, ry, rw, rh) => {
      // Liang-Barsky clip of segment (x1,y1)->(x2,y2) against [rx, rx+rw] x [ry, ry+rh]
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

    const items = [];
    // Collect top-level formula blocks (`[data-formula]`) and standalone text elements not inside a formula
    for (const fm of document.querySelectorAll('[data-formula]')) {
      if (!vis(fm)) continue;
      const r = fm.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      items.push({ kind: 'formula', label: fm.getAttribute('data-formula'), x: r.left, y: r.top, w: r.width, h: r.height });
    }
    for (const tx of document.querySelectorAll('svg text, #stage p, #stage h1, #stage h2, #stage h3, #stage .cap, #stage .note')) {
      if (tx.closest('[data-formula]') || !vis(tx)) continue;
      const txt = (tx.textContent || '').trim();
      if (!txt) continue;
      const r = tx.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      const px = parseFloat(getComputedStyle(tx).fontSize) || r.height;
      items.push({ kind: 'text', label: txt.slice(0, 24), x: r.left, y: r.top, w: r.width, h: r.height, fontSize: px });
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
      strokes.push([sx1, sy1, sx2, sy2]);
    }

    const frameIssues = [];
    const minPx = (H / 1080) * BASE_MIN_PX;
    const onScreen = [];
    for (const it of items) {
      // Elements completely panned outside the camera viewport are off-camera, not clipped at the margin.
      if (it.x + it.w <= 2 || it.x >= W - 2 || it.y + it.h <= 2 || it.y >= H - 2) continue;
      onScreen.push(it);
      if (it.x < M * 0.5 || it.y < M * 0.4 || it.x + it.w > W - M * 0.5 || it.y + it.h > H - M * 0.4) {
        frameIssues.push({ type: 'margin_overflow', item: it.label, box: [Math.round(it.x), Math.round(it.y), Math.round(it.w), Math.round(it.h)] });
      }
      if (it.kind === 'text' && it.fontSize < minPx) {
        frameIssues.push({ type: 'tiny_text', item: it.label, fontSize: +it.fontSize.toFixed(1), minPx: +minPx.toFixed(1) });
      }
      // Check if any solid vector/ray line slices right through the central glyph core of this label
      if (it.w >= 26 && it.h >= 14) {
        const cx = it.x + it.w * 0.16, cy = it.y + it.h * 0.24, cw = it.w * 0.68, ch = it.h * 0.52;
        for (const [x1, y1, x2, y2] of strokes) {
          // Ignore horizontal underlines near top/bottom edge
          if (Math.abs(y2 - y1) < 2 && (Math.abs(y1 - it.y) < 8 || Math.abs(y1 - (it.y + it.h)) < 8)) continue;
          if (segHitsRect(x1, y1, x2, y2, cx, cy, cw, ch)) {
            frameIssues.push({ type: 'line_crosses_label', item: it.label });
            break;
          }
        }
      }
    }

    // Guard against stacking a wall of full display equations simultaneously (short diagram vector labels <210px excluded)
    const visFormulas = onScreen.filter((it) => it.kind === 'formula' && it.w >= 210);
    const rightFormulas = visFormulas.filter((it) => it.x + it.w / 2 > W * 0.45);
    if (visFormulas.length > MAX_FM || rightFormulas.length > Math.max(2, MAX_FM - 1)) {
      frameIssues.push({
        type: 'formula_crowding',
        formulasOnScreen: visFormulas.length,
        rightHalfFormulas: rightFormulas.length,
        hint: 'Too many display formulas stacked simultaneously. Keep <= 2 active main formulas per act: morph in-place or fade out completed intermediate steps.',
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
    return { count: items.length, frameIssues };
  }, { W: v.width, H: v.height, M: margin, BASE_MIN_PX: baseMinPx, MAX_FM: maxFormulas });

  // Pixel occupancy & left/right balance check on a small thumbnail
  const shotBuf = await page.screenshot({ type: 'jpeg', quality: 75 });
  const pix = await page.evaluate(async (b64) => {
    const img = new Image();
    await new Promise((res) => { img.onload = res; img.src = 'data:image/jpeg;base64,' + b64; });
    const W = 160, H = 90;
    const c = new OffscreenCanvas(W, H), x = c.getContext('2d');
    x.drawImage(img, 0, 0, W, H);
    const d = x.getImageData(0, 0, W, H).data;
    // Estimate background luminance from corners (below header y=10)
    const lum = (px, py) => { const k = (py * W + px) * 4; return 0.299 * d[k] + 0.587 * d[k + 1] + 0.114 * d[k + 2]; };
    const bg = (lum(4, 12) + lum(W - 5, 12) + lum(4, H - 5) + lum(W - 5, H - 5)) / 4;
    let activeL = 0, activeR = 0;
    for (let py = 10; py < H - 4; py++) {
      for (let px = 4; px < W - 4; px++) {
        if (Math.abs(lum(px, py) - bg) > 22) {
          if (px < W / 2) activeL++; else activeR++;
        }
      }
    }
    const bodyPx = (W - 8) * (H - 14);
    return { activeShare: +((activeL + activeR) / bodyPx).toFixed(3), leftShare: +(activeL / Math.max(1, activeL + activeR)).toFixed(2) };
  }, shotBuf.toString('base64'));

  if (pix.activeShare < 0.015) {
    domCheck.frameIssues.push({ type: 'nearly_empty_frame', activeShare: pix.activeShare });
  }
  for (const f of domCheck.frameIssues) issues.push({ t, ...f });
  stats.push({ t, items: domCheck.count, activeShare: pix.activeShare, leftShare: pix.leftShare });
}

console.log(JSON.stringify({ framesChecked: times.length, issueCount: issues.length, issues, stats }, null, 2));
await browser.close();
process.exit(issues.length ? 1 : 0);
