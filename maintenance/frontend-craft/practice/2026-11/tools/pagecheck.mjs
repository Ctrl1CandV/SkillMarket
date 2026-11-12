// Prototype: screenshot a local page at several widths and report measurable layout problems.
// Usage: node pagecheck.mjs <page.html> <out-dir> [widths, default 1440x900,1024x768,390x844]
// Needs FC_NODE_MODULES (playwright-core) and FC_CHROME.
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const require = createRequire(path.join(process.env.FC_NODE_MODULES, 'x.js'));
const { chromium } = require('playwright-core');
const [page_, outDir, sizesArg] = process.argv.slice(2);
const sizes = (sizesArg || '1440x900,1024x768,390x844').split(',').map(s => s.split('x').map(Number));
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({ executablePath: process.env.FC_CHROME, headless: true });
const report = { page: path.resolve(page_), views: [] };
for (const [w, h] of sizes) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1,
    isMobile: w < 700, hasTouch: w < 700 });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(String(e.message).slice(0, 200)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  await page.goto(pathToFileURL(path.resolve(page_)).href + (process.env.FC_QUERY || ''), { waitUntil: 'load' });
  await page.waitForTimeout(400);
  const stem = `${path.basename(page_, '.html')}-${w}`;
  await page.screenshot({ path: path.join(outDir, `${stem}-first.png`) });
  await page.screenshot({ path: path.join(outDir, `${stem}-full.png`), fullPage: true });
  const m = await page.evaluate((mobile) => {
    const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.05; };
    const parse = c => (c.match(/[\d.]+/g) || []).map(Number);
    const lum = ([r, g, b]) => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
    const bgOf = el => { for (let e = el; e; e = e.parentElement) { const s = getComputedStyle(e);
      if (s.backgroundImage && s.backgroundImage !== 'none') return null;
      const c = parse(s.backgroundColor); if (c.length >= 3 && (c[3] === undefined || c[3] > 0.9)) return c; }
      return [255, 255, 255]; };
    const sizes = {}; let small = 0, total = 0; const low = []; const clipped = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const seen = new Set();
    while (walker.nextNode()) {
      const t = walker.currentNode.textContent.replace(/\s+/g, ''); const el = walker.currentNode.parentElement;
      if (!t || !el || !vis(el) || /^[·•–—|×+−-]+$/.test(t)) continue;   // punctuation used as decoration is not text to read
      const s = getComputedStyle(el); const fs_ = Math.round(parseFloat(s.fontSize));
      sizes[fs_] = (sizes[fs_] || 0) + t.length; total += t.length; if (fs_ < 12) small += t.length;
      if (seen.has(el)) continue; seen.add(el);
      const bg = bgOf(el); const fg = parse(s.color);
      if (bg && fg.length >= 3) { const a = lum(fg), b = lum(bg); const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
        const large = fs_ >= 24 || (fs_ >= 19 && +s.fontWeight >= 700);
        if (ratio < (large ? 3 : 4.5)) low.push({ text: t.slice(0, 24), ratio: +ratio.toFixed(2), size: fs_ }); }
      if (/(hidden|clip)/.test(s.overflowX + s.overflow) && el.scrollWidth > el.clientWidth + 1)
        clipped.push({ text: t.slice(0, 24), box: el.clientWidth, need: el.scrollWidth });
    }
    const ranked = Object.entries(sizes).map(([k, v]) => [+k, v]).sort((a, b) => b[1] - a[1]);
    const body = ranked[0] ? ranked[0][0] : null;
    const biggest = Math.max(...Object.keys(sizes).map(Number));
    const taps = [];
    if (mobile) for (const el of document.querySelectorAll('button, a[href], input:not([type=hidden]), select, textarea, [role=button], label[for]')) {
      if (!vis(el)) continue; const r = el.getBoundingClientRect();
      if (r.height < 40 || r.width < 40) taps.push({ el: el.tagName.toLowerCase(), text: (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 16), w: Math.round(r.width), h: Math.round(r.height) }); }
    return { horizontal_scroll: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      page_height: document.documentElement.scrollHeight, body_size: body, largest_size: biggest,
      title_to_body: body ? +(biggest / body).toFixed(2) : null, size_mix: ranked.slice(0, 6),
      chars_below_12px: small, chars_total: total, low_contrast: low.slice(0, 12), low_contrast_count: low.length,
      clipped_text: clipped.slice(0, 12), small_tap_targets: taps.slice(0, 12), small_tap_count: taps.length };
  }, w < 700);
  report.views.push({ viewport: `${w}x${h}`, errors, ...m, shots: [`${stem}-first.png`, `${stem}-full.png`] });
  await ctx.close();
}
await browser.close();
fs.writeFileSync(path.join(outDir, `${path.basename(page_, '.html')}-check.json`), JSON.stringify(report, null, 2));
for (const v of report.views) {
  console.log(`${v.viewport}: scroll-x ${v.horizontal_scroll ? 'YES' : 'no'}, body ${v.body_size}px, largest ${v.largest_size}px (x${v.title_to_body}), ` +
    `<12px ${v.chars_below_12px}/${v.chars_total} chars, low contrast ${v.low_contrast_count}, clipped ${v.clipped_text.length}, ` +
    `small taps ${v.small_tap_count}, errors ${v.errors.length}, height ${v.page_height}px`);
}
