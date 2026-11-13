#!/usr/bin/env node
// pagecheck.mjs — open a page at several widths, save screenshots, and report the problems that can be measured.
//
//   node pagecheck.mjs <page.html | url> [--out <dir>] [--sizes 1440x900,1024x768,390x844] [--query "?tab=2"]
//
// It finds: sideways scrolling and what causes it, script errors, text that is too small (also inside scaled SVG),
// low contrast, clipped text, text drawn on top of other text, punctuation pushed to the start of a line,
// text squeezed into one character per line, small touch targets, and how many font sizes the page really uses.
// It cannot tell whether the page is good. A clean report means "nothing measurable is wrong": still open the screenshots.
import fs from 'node:fs';
import path from 'node:path';
import { launch, open } from './env.mjs';

const args = process.argv.slice(2);
const opt = (name, fallback) => { const i = args.indexOf('--' + name); return i >= 0 ? args.splice(i, 2)[1] : fallback; };
const sizes = opt('sizes', '1440x900,1024x768,390x844').split(',').map((s) => s.split('x').map(Number));
const query = opt('query', '');
const input = args[0];
if (!input) { console.error('usage: node pagecheck.mjs <page.html | url> [--out <dir>] [--sizes WxH,WxH] [--query "?a=1"]'); process.exit(2); }
const stem = path.basename(input.replace(/[?#].*$/, ''), path.extname(input.replace(/[?#].*$/, ''))) || 'page';
const outDir = path.resolve(opt('out', path.join(/^[a-z]+:\/\//i.test(input) ? '.' : path.dirname(input), '_pagecheck')));
fs.mkdirSync(outDir, { recursive: true });

// Runs inside the page.
function measure(mobile) {
  const vw = document.documentElement.clientWidth;
  const css = (el) => getComputedStyle(el);
  const hidden = (el) => {   // not shown, or shown only to screen readers
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const s = css(e); if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity <= 0.05) return true;
      if (e === document.body) break;
      const r = e.getBoundingClientRect(); if ((r.width <= 2 || r.height <= 2) && /hidden|clip/.test(s.overflow + s.overflowX + s.overflowY)) return true;
    }
    return false;
  };
  const floating = (el) => { for (let e = el; e && e !== document.body; e = e.parentElement) if (/fixed|sticky/.test(css(e).position)) return true; return false; };
  const rgb = (c) => (c.match(/[\d.]+/g) || []).map(Number);
  const lum = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const backdrop = (el) => { for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const s = css(e); if (s.backgroundImage && s.backgroundImage !== 'none') return null; const c = rgb(s.backgroundColor); if (c.length >= 3 && (c[3] === undefined || c[3] > 0.9)) return c; } return [255, 255, 255]; };
  const name = (el) => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\s+/)[0] : '');
  const short = (s, n = 22) => { s = s.replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n) + '…' : s; };
  const DECOR = /^[\p{P}\p{S}\s]+$/u, CLOSE = /[，。、；：！？）》」』”’]/;

  const sizeChars = {}, items = [], small = [], lowContrast = [], clipped = [], squeezed = [], lineStart = [];
  const seen = new Set(), walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT), range = document.createRange();
  let total = 0, node, prev = null, punctuationBudget = 500;
  const charBox = (n, i) => { range.setStart(n, i); range.setEnd(n, i + 1); const r = range.getClientRects()[0]; return r && r.width > 0 ? r : null; };
  const blockOf = (el) => { for (let e = el; e; e = e.parentElement) if (!/^inline/.test(css(e).display) || e === document.body) return e; return document.body; };
  while ((node = walker.nextNode())) {
    const raw = node.textContent, text = raw.replace(/\s+/g, ''), el = node.parentElement;
    if (!text || !el || /^(script|style|noscript|template)$/i.test(el.tagName) || hidden(el)) continue;
    range.selectNodeContents(node); const rects = [...range.getClientRects()].filter((r) => r.width > 0 && r.height > 0); if (!rects.length) continue;
    const box = { left: Math.min(...rects.map((r) => r.left)), top: Math.min(...rects.map((r) => r.top)), right: Math.max(...rects.map((r) => r.right)), bottom: Math.max(...rects.map((r) => r.bottom)) };
    const s = css(el); let px = parseFloat(s.fontSize);
    const svg = el.ownerSVGElement;   // text inside an SVG shrinks with the drawing: use the size it is really shown at
    if (svg && svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width) px *= svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
    const key = Math.round(px); sizeChars[key] = (sizeChars[key] || 0) + text.length; total += text.length;
    const decor = DECOR.test(text), horizontal = /^horizontal/.test(s.writingMode);
    if (px < 11.5 && !decor) small.push({ text: short(raw), size: +px.toFixed(1), svg: !!svg });
    if (!decor) items.push({ el, box, text: short(raw, 16), floating: floating(el) });
    if (!decor && !el.closest('[disabled], [aria-disabled="true"]')) {
      const bg = backdrop(el), fg = rgb(s.color);
      if (bg && fg.length >= 3 && !svg) { const a = lum(fg), b = lum(bg), ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05), large = px >= 24 || (px >= 18.5 && +s.fontWeight >= 700);
        if (ratio < (large ? 3 : 4.5)) lowContrast.push({ text: short(raw), ratio: +ratio.toFixed(2), size: key }); }
    }
    if (!seen.has(el)) { seen.add(el);
      // an ellipsis is a deliberate cut, so it is not reported
      if (/hidden|clip/.test(s.overflow + s.overflowX) && s.textOverflow !== 'ellipsis' && el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 2) clipped.push({ text: short(el.textContent), box: el.clientWidth, needs: el.scrollWidth });
      const own = el.textContent.replace(/\s+/g, ''), r = el.getBoundingClientRect();
      if (horizontal && !svg && own.length >= 4 && r.width < px * 1.7 && r.height > px * 3.2) squeezed.push({ text: short(el.textContent), width: Math.round(r.width) }); }
    // closing punctuation must not start a line
    if (horizontal && !svg && punctuationBudget > 0) for (let i = 0; i < raw.length; i++) {
      if (!CLOSE.test(raw[i])) continue; punctuationBudget--;
      const here = charBox(node, i); if (!here) continue;
      let before = null, ctx = '';
      for (let j = i - 1; j >= 0; j--) if (/\S/.test(raw[j])) { before = charBox(node, j); ctx = raw.slice(Math.max(0, j - 5), j + 1); break; }
      if (!before && prev && blockOf(prev.parentElement) === blockOf(el)) { const p = prev.textContent; for (let j = p.length - 1; j >= 0; j--) if (/\S/.test(p[j])) { before = charBox(prev, j); ctx = p.slice(Math.max(0, j - 5), j + 1); break; } }
      if (before && here.top > before.top + before.height * 0.5) lineStart.push({ text: short(ctx) + ' ⏎ ' + raw[i] });
    }
    prev = node;
  }
  // text drawn on top of other text
  const overlap = [], list = items.slice(0, 1500);
  for (let i = 0; i < list.length && overlap.length < 12; i++) for (let j = i + 1; j < list.length; j++) {
    const a = list[i], b = list[j]; if (a.el === b.el || a.floating || b.floating || a.el.contains(b.el) || b.el.contains(a.el)) continue;
    const w = Math.min(a.box.right, b.box.right) - Math.max(a.box.left, b.box.left), h = Math.min(a.box.bottom, b.box.bottom) - Math.max(a.box.top, b.box.top); if (w <= 1 || h <= 1) continue;
    const area = (r) => (r.right - r.left) * (r.bottom - r.top); if (w * h > 0.3 * Math.min(area(a.box), area(b.box))) { overlap.push({ a: a.text, b: b.text }); break; }
  }
  // what makes the page scroll sideways
  const scrollX = document.documentElement.scrollWidth > vw + 1, culprits = [];
  if (scrollX) for (const el of document.querySelectorAll('body *')) { const r = el.getBoundingClientRect(); if (r.width <= 0 || r.right <= vw + 1 || hidden(el)) continue;
    let inside = false; for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) if (/auto|scroll|hidden|clip/.test(css(p).overflowX)) { inside = true; break; }
    if (!inside) culprits.push({ el: name(el), right: Math.round(r.right), width: Math.round(r.width) }); }
  const taps = [];
  if (mobile) for (const el of document.querySelectorAll('button, a[href], input:not([type=hidden]), select, textarea, [role=button]')) {
    if (hidden(el) || (el.tagName === 'A' && /^inline$/.test(css(el).display))) continue;
    const own = el.getBoundingClientRect(), label = el.closest('label') || (el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`)), lr = label && !hidden(label) ? label.getBoundingClientRect() : own;
    const r = lr.width * lr.height > own.width * own.height ? lr : own;   // a small box inside a big label is fine; a hidden label does not count
    if (r.width > 0 && (r.height < 40 || r.width < 40)) taps.push({ el: name(el), text: short(el.innerText || el.value || el.getAttribute('aria-label') || '', 14), w: Math.round(r.width), h: Math.round(r.height) }); }
  const ranked = Object.entries(sizeChars).map(([k, v]) => [+k, v]).sort((a, b) => b[1] - a[1]), body = ranked.length ? ranked[0][0] : null, largest = ranked.length ? Math.max(...ranked.map((r) => r[0])) : null;
  const used = ranked.filter(([, n]) => n >= 3).map(([k]) => k).sort((a, b) => a - b);
  return { scroll_x: scrollX, sticking_out: culprits.slice(0, 8), page_height: document.documentElement.scrollHeight, chars: total, body_size: body, largest_size: largest,
    largest_to_body: body ? +(largest / body).toFixed(2) : null, sizes_in_use: used, small_text: small.slice(0, 10), small_text_count: small.length,
    low_contrast: lowContrast.slice(0, 10), low_contrast_count: lowContrast.length, clipped: clipped.slice(0, 8), overlapping: overlap, line_start_punctuation: lineStart.slice(0, 8),
    one_char_per_line: squeezed.slice(0, 8), small_taps: taps.slice(0, 10), small_taps_count: taps.length };
}

const browser = await launch();
const report = { page: input, views: [] };
for (const [width, height] of sizes) {
  const { page, context, errors, mobile } = await open(browser, input, { width, height, query });
  const shots = [`${stem}-${width}-first.png`, `${stem}-${width}-full.png`];
  await page.screenshot({ path: path.join(outDir, shots[0]) });
  await page.screenshot({ path: path.join(outDir, shots[1]), fullPage: true });
  const m = await page.evaluate(measure, mobile);
  report.views.push({ viewport: `${width}x${height}`, script_errors: errors, ...m, screenshots: shots });
  await context.close();
}
await browser.close();
fs.writeFileSync(path.join(outDir, `${stem}-check.json`), JSON.stringify(report, null, 2));

let kinds = 0;
const eg = (list, fmt) => list.slice(0, 3).map(fmt).join('; ');
for (const v of report.views) {
  const lines = [];
  if (v.script_errors.length) lines.push(`script errors: ${v.script_errors.length} — ${v.script_errors[0]}`);
  if (v.scroll_x) lines.push(`scrolls sideways — sticking out: ${eg(v.sticking_out, (c) => `${c.el} (right edge ${c.right}, width ${c.width})`) || 'not found'}`);
  if (v.overlapping.length) lines.push(`text on top of text: ${v.overlapping.length} — ${eg(v.overlapping, (o) => `"${o.a}" × "${o.b}"`)}`);
  if (v.one_char_per_line.length) lines.push(`squeezed to one character per line: ${eg(v.one_char_per_line, (o) => `"${o.text}" (${o.width}px wide)`)}`);
  if (v.line_start_punctuation.length) lines.push(`punctuation at the start of a line: ${eg(v.line_start_punctuation, (o) => o.text)}`);
  if (v.small_text_count) lines.push(`text under 12px: ${v.small_text_count} — ${eg(v.small_text, (o) => `"${o.text}" ${o.size}px${o.svg ? ' (inside a scaled SVG)' : ''}`)}`);
  if (v.low_contrast_count) lines.push(`low contrast: ${v.low_contrast_count} — ${eg(v.low_contrast, (o) => `"${o.text}" ${o.ratio}:1 at ${o.size}px`)}`);
  if (v.clipped.length) lines.push(`clipped text: ${eg(v.clipped, (o) => `"${o.text}" needs ${o.needs}px, has ${o.box}px`)}`);
  if (v.small_taps_count) lines.push(`touch targets under 40px: ${v.small_taps_count} — ${eg(v.small_taps, (o) => `${o.el} "${o.text}" ${o.w}x${o.h}`)}`);
  if (v.sizes_in_use.length > 9) lines.push(`${v.sizes_in_use.length} font sizes in use (${v.sizes_in_use.join(', ')}): close sizes read as untidy, merge them into fewer steps`);
  kinds += lines.length;
  console.log(`== ${v.viewport} ==  body ${v.body_size}px, largest ${v.largest_size}px (x${v.largest_to_body}), sizes ${v.sizes_in_use.join('/')}, page height ${v.page_height}px`);
  for (const line of lines) console.log('  ! ' + line);
}
console.log(kinds ? `${kinds} finding(s). Details: ${path.join(outDir, stem + '-check.json')}` : 'Nothing measurable found.');
console.log(`Screenshots are in ${outDir}. Open them: this script cannot see layout, emphasis or taste.`);
