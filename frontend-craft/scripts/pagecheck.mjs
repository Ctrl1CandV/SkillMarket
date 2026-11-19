#!/usr/bin/env node
// pagecheck.mjs — open a page at several widths, save screenshots, and report the problems that can be measured.
//
//   node pagecheck.mjs <page.html | url> [--out <dir>] [--sizes 1440x900,1024x768,390x844,320x640] [--query "?tab=2"]
//
// It finds: sideways scrolling and what causes it, script errors, values a script failed to compute (NaN, undefined)
// in text, tooltips or sizes, text that is too small (also inside scaled SVG),
// low contrast, clipped text, text drawn on top of other text, punctuation pushed to the start of a line,
// text squeezed into one character per line, small touch targets, how many font sizes the page really uses,
// text that spills out of its box when the reader widens text spacing (WCAG 1.4.12), font sizes set in px,
// and a missing color-scheme. It also counts the colored hues in the first screen (to compare with what should carry color),
// and saves a forced-colors screenshot, and a dark one when the page supports dark.
// It cannot tell whether the page is good. A clean report means "nothing measurable is wrong": still open the screenshots.
import fs from 'node:fs';
import path from 'node:path';
import { launch, open } from './env.mjs';

const args = process.argv.slice(2);
const opt = (name, fallback) => { const i = args.indexOf('--' + name); return i >= 0 ? args.splice(i, 2)[1] : fallback; };
const sizes = opt('sizes', '1440x900,1024x768,390x844,320x640').split(',').map((s) => s.split('x').map(Number));
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
    if (el.checkVisibility && !el.checkVisibility()) return true;   // e.g. inside a closed <details>: it still has a box, but is not drawn
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const s = css(e); if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity <= 0.05) return true;
      if (e === document.body) break;
      const r = e.getBoundingClientRect(); if ((r.width <= 2 || r.height <= 2) && /hidden|clip/.test(s.overflow + s.overflowX + s.overflowY)) return true;
    }
    return false;
  };
  const floating = (el) => { for (let e = el; e && e !== document.body; e = e.parentElement) if (/fixed|sticky/.test(css(e).position)) return true; return false; };
  // Let the browser turn any CSS color (oklab, oklch, color-mix, color()) into sRGB; reading the digits out of the string gets these wrong.
  const cv = document.createElement('canvas'); cv.width = cv.height = 1; const cx = cv.getContext('2d', { willReadFrequently: true }); const colors = new Map();
  const rgb = (c) => { if (colors.has(c)) return colors.get(c); cx.clearRect(0, 0, 1, 1); cx.fillStyle = '#000'; cx.fillStyle = c; cx.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = cx.getImageData(0, 0, 1, 1).data, v = [r, g, b, a / 255]; colors.set(c, v); return v; };
  const lum = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  // the first opaque background that is really behind the text; a label positioned outside its parent (above a bar, say) is not on the parent's color
  const behind = (e, box) => { if (!box) return true; const r = e.getBoundingClientRect(), x = (box.left + box.right) / 2, y = (box.top + box.bottom) / 2; return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom; };
  // translucent fills (rgba, color-mix with transparent) are laid over what is under them
  const backdrop = (el, box) => { const layers = [];
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const s = css(e); if (!behind(e, box)) continue; if (s.backgroundImage && s.backgroundImage !== 'none') return null;
      const c = rgb(s.backgroundColor); if (c[3] > 0.9) { layers.push(c); break; } if (c[3] > 0.02) layers.push(c); }
    if (!layers.length || layers[layers.length - 1][3] <= 0.9) layers.push([255, 255, 255, 1]);
    let out = layers.pop().slice(0, 3);
    while (layers.length) { const [r, g, b, a] = layers.pop(); out = [r * a + out[0] * (1 - a), g * a + out[1] * (1 - a), b * a + out[2] * (1 - a)]; }
    return out; };
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
    if (!decor) items.push({ el, box, rects: rects.slice(0, 6), text: short(raw, 16), floating: floating(el) });
    if (!decor && !el.closest('[disabled], [aria-disabled="true"]')) {
      const bg = backdrop(el, box), fg = rgb(s.color);
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
    // compare line by line: text that wraps has an outer box covering the whole width, which is not where it is drawn
    const area = (r) => (r.right - r.left) * (r.bottom - r.top);
    const hit = a.rects.some((ra) => b.rects.some((rb) => { const x = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left), y = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
      return x > 1 && y > 1 && x * y > 0.3 * Math.min(area(ra), area(rb)); }));
    if (hit) { overlap.push({ a: a.text, b: b.text }); break; }
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
  // values a script failed to compute: NaN / undefined / Infinity / [object Object] in what is shown, in tooltips, or in sizes and shapes
  // In visible text a page may also talk about NaN ("the loss became NaN"), and "Infinity" is an ordinary word.
  // So text counts only when it looks like a number slot: a short run of text, or the token next to a digit or a percent sign.
  const BROKEN = /\b(?:NaN|undefined|Infinity)\b|\[object Object\]/, broken = [];
  const brokenText = (s) => /\[object Object\]/.test(s) || (/\b(?:NaN|undefined)\b/.test(s) && (s.trim().length <= 12 || /(?:NaN|undefined)\s?[%‰]|[\d¥$]\s?(?:NaN|undefined)/.test(s)));
  for (const el of document.body.querySelectorAll('*')) {
    if (/^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE)$/.test(el.tagName)) continue;
    for (const n of el.childNodes) if (n.nodeType === 3 && brokenText(n.textContent) && !hidden(el)) broken.push({ el: name(el), where: 'text', value: short(n.textContent, 40) });
    for (const a of ['style', 'title', 'aria-label', 'd', 'points', 'width', 'height', 'x', 'y', 'cx', 'cy', 'r', 'transform', 'value'])
      if (el.hasAttribute(a) && BROKEN.test(el.getAttribute(a))) broken.push({ el: name(el), where: a, value: short(el.getAttribute(a), 40) });
  }
  // how many colored hues the first screen uses (text, fills, borders); grays and near-whites do not count
  const vh = window.innerHeight, hues = new Map();
  const hueOf = ([r, g, b, a]) => { if (a !== undefined && a < 0.3) return null; const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn, l = (mx + mn) / 510;
    if (d < 40 || l > 0.94) return null; const s = d / 255 / (1 - Math.abs(2 * l - 1)); if (s < 0.25) return null;
    let h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h = (h * 60 + 360) % 360; return Math.round(h / 30) % 12; };
  for (const el of document.body.querySelectorAll('*')) {
    const r = el.getBoundingClientRect(); if (r.width < 2 || r.height < 2 || r.top >= vh || r.bottom <= 0 || hidden(el)) continue;
    const s = css(el), add = (c, weight) => { const h = hueOf(rgb(c)); if (h !== null) hues.set(h, (hues.get(h) || 0) + weight); };
    if ([...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) add(s.color, 1);
    add(s.backgroundColor, 1);
    if (parseFloat(s.borderTopWidth) + parseFloat(s.borderLeftWidth) + parseFloat(s.borderBottomWidth) > 0.5) add(s.borderTopColor !== 'rgba(0, 0, 0, 0)' ? s.borderTopColor : s.borderLeftColor, 1);
  }
  const ranked = Object.entries(sizeChars).map(([k, v]) => [+k, v]).sort((a, b) => b[1] - a[1]), body = ranked.length ? ranked[0][0] : null, largest = ranked.length ? Math.max(...ranked.map((r) => r[0])) : null;
  const used = ranked.filter(([, n]) => n >= 3).map(([k]) => k).sort((a, b) => a - b);
  return { scroll_x: scrollX, sticking_out: culprits.slice(0, 8), page_height: document.documentElement.scrollHeight, chars: total, body_size: body, largest_size: largest,
    largest_to_body: body ? +(largest / body).toFixed(2) : null, sizes_in_use: used, small_text: small.slice(0, 10), small_text_count: small.length,
    low_contrast: lowContrast.slice(0, 10), low_contrast_count: lowContrast.length, clipped: clipped.slice(0, 8), overlapping: overlap, line_start_punctuation: lineStart.slice(0, 8),
    one_char_per_line: squeezed.slice(0, 8), small_taps: taps.slice(0, 10), small_taps_count: taps.length, broken_values: broken.slice(0, 10), broken_values_count: broken.length,
    first_screen_hues: [...hues.entries()].filter(([, n]) => n >= 2).map(([h]) => h * 30).sort((a, b) => a - b) };
}

// Runs inside the page after the WCAG 1.4.12 spacing has been applied: text that no longer fits its box.
function spacing() {
  const css = (el) => getComputedStyle(el), out = [];
  for (const el of document.body.querySelectorAll('*')) {
    if (/^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE|svg)$/i.test(el.tagName) || el.closest('svg')) continue;
    if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
    const s = css(el); if (s.display === 'inline' || s.display === 'contents' || s.display === 'none' || s.visibility === 'hidden' || el.clientHeight < 2) continue;
    const scrolls = (o) => /auto|scroll/.test(o), cut = (o) => /hidden|clip/.test(o);
    const down = el.scrollHeight > el.clientHeight + 2 && !scrolls(s.overflowY), across = el.scrollWidth > el.clientWidth + 2 && cut(s.overflowX) && s.textOverflow !== 'ellipsis';
    if (down || across) out.push({ text: el.textContent.replace(/\s+/g, ' ').trim().slice(0, 22), box: `${el.clientWidth}x${el.clientHeight}`, needs: `${el.scrollWidth}x${el.scrollHeight}` });
  }
  return out;
}
// Runs inside the page once: author font sizes written in px, and the declared color-scheme.
function pageLevel() {
  const px = [];
  const walk = (rules) => { for (const r of rules) { if (r.cssRules) walk(r.cssRules); if (r.style && /px$/.test(r.style.fontSize || '')) px.push(r.selectorText || '(rule)'); } };
  for (const sheet of document.styleSheets) { try { walk(sheet.cssRules); } catch { /* another site's stylesheet: not the author's to fix */ } }
  for (const el of document.querySelectorAll('[style*="font-size"]')) if (/px$/.test(el.style.fontSize)) px.push(el.tagName.toLowerCase() + '[style]');
  const meta = document.querySelector('meta[name="color-scheme"]');
  // In a Chinese page: short all-caps English labels set as decoration (CAMPUS LIFE, INSTRUMENT / 01). They tell a Chinese reader nothing.
  // Content in English stays quiet: titles in normal case, model numbers and venues (SU8010, ICML 2025), code, anything marked lang="en".
  const all = document.body.innerText || '', cjk = (all.match(/[\u4e00-\u9fff]/g) || []).length;
  const eyebrows = [];
  if (/^zh/i.test(document.documentElement.lang) || cjk > all.length * 0.2) {
    const seen = new Set(), tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n; (n = tw.nextNode());) {
      const el = n.parentElement, raw = n.textContent.replace(/\s+/g, ' ').trim();
      // "WORKSPACE / 研究空间": an English label glued to its Chinese translation counts as the English part
      const glued = raw.match(/^([A-Za-z][A-Za-z .&'-]{3,}?)\s*[/·|]\s*[\u4e00-\u9fff]/), s = glued ? glued[1].trim() : raw;
      if (!el || !s || s.length > 48 || /[^\x20-\x7e·•—–]/.test(s) || el.closest('code, pre, kbd, samp, script, style, svg, [lang^="en"]')) continue;
      const r = el.getBoundingClientRect(), cs = getComputedStyle(el); if (r.width < 1 || r.height < 1 || cs.visibility === 'hidden') continue;
      const caps = cs.textTransform === 'uppercase' ? s.toUpperCase() : s, words = caps.match(/[A-Za-z]{2,}/g) || [];
      if (caps !== caps.toUpperCase() || !words.some((w) => w.length >= 4)) continue;
      const spaced = parseFloat(cs.letterSpacing) >= 0.05 * parseFloat(cs.fontSize);
      if (!(words.length >= 2 || (spaced && words.length >= 1))) continue;
      if (!seen.has(caps)) { seen.add(caps); eyebrows.push(caps.slice(0, 32)); }
    }
  }
  return { px_font_rules: px.length, px_font_examples: px.slice(0, 8), color_scheme: getComputedStyle(document.documentElement).colorScheme, color_scheme_meta: meta ? meta.content : null, english_eyebrows: eyebrows.slice(0, 12), english_eyebrows_count: eyebrows.length };
}
const SPACING = '* { line-height: 1.5 !important; letter-spacing: .12em !important; word-spacing: .16em !important; } p { margin-block-end: 2em !important; }';

const browser = await launch();
const report = { page: input, views: [] };
for (const [width, height] of sizes) {
  const { page, context, errors, mobile } = await open(browser, input, { width, height, query });
  const shots = [`${stem}-${width}-first.png`, `${stem}-${width}-full.png`];
  await page.screenshot({ path: path.join(outDir, shots[0]) });
  await page.screenshot({ path: path.join(outDir, shots[1]), fullPage: true });
  const m = await page.evaluate(measure, mobile);
  if (!report.page_level) report.page_level = await page.evaluate(pageLevel);
  await page.addStyleTag({ content: SPACING }); await page.waitForTimeout(100);
  const spill = await page.evaluate(spacing);
  report.views.push({ viewport: `${width}x${height}`, script_errors: errors, ...m, spacing_spill: spill.slice(0, 8), spacing_spill_count: spill.length, screenshots: shots });
  await context.close();
}
// how the page looks in forced colors (Windows high contrast), and in dark when it says it supports dark
// (a page that switches themes by script may compute as light here, so its <meta name=color-scheme> counts too)
{
  const [width, height] = sizes[0], extra = [];
  const modes = [['forced', { forcedColors: 'active' }]];
  if (/dark/.test(report.page_level.color_scheme + ' ' + (report.page_level.color_scheme_meta || ''))) modes.push(['dark', { colorScheme: 'dark' }]);
  for (const [tag, emulate] of modes) {
    const { page, context } = await open(browser, input, { width, height, query, emulate });
    const shot = `${stem}-${width}-${tag}.png`; await page.screenshot({ path: path.join(outDir, shot) }); extra.push(shot); await context.close();
  }
  report.extra_screenshots = extra;
}
await browser.close();
fs.writeFileSync(path.join(outDir, `${stem}-check.json`), JSON.stringify(report, null, 2));

let kinds = 0;
const eg = (list, fmt) => list.slice(0, 3).map(fmt).join('; ');
for (const v of report.views) {
  const lines = [];
  if (v.script_errors.length) lines.push(`script errors: ${v.script_errors.length} — ${v.script_errors[0]}`);
  if (v.broken_values_count) lines.push(`values the script failed to compute: ${v.broken_values_count} — ${eg(v.broken_values, (o) => `${o.el} ${o.where} "${o.value}"`)}`);
  if (v.scroll_x) lines.push(`scrolls sideways — sticking out: ${eg(v.sticking_out, (c) => `${c.el} (right edge ${c.right}, width ${c.width})`) || 'not found'}`);
  if (v.overlapping.length) lines.push(`text on top of text: ${v.overlapping.length} — ${eg(v.overlapping, (o) => `"${o.a}" × "${o.b}"`)}`);
  if (v.one_char_per_line.length) lines.push(`squeezed to one character per line: ${eg(v.one_char_per_line, (o) => `"${o.text}" (${o.width}px wide)`)}`);
  if (v.line_start_punctuation.length) lines.push(`punctuation at the start of a line: ${eg(v.line_start_punctuation, (o) => o.text)}`);
  if (v.small_text_count) lines.push(`text under 12px: ${v.small_text_count} — ${eg(v.small_text, (o) => `"${o.text}" ${o.size}px${o.svg ? ' (inside a scaled SVG)' : ''}`)}`);
  if (v.low_contrast_count) lines.push(`low contrast: ${v.low_contrast_count} — ${eg(v.low_contrast, (o) => `"${o.text}" ${o.ratio}:1 at ${o.size}px`)}`);
  if (v.clipped.length) lines.push(`clipped text: ${eg(v.clipped, (o) => `"${o.text}" needs ${o.needs}px, has ${o.box}px`)}`);
  if (v.spacing_spill_count) lines.push(`text spills out of its box when the reader widens text spacing (WCAG 1.4.12): ${v.spacing_spill_count} — ${eg(v.spacing_spill, (o) => `"${o.text}" box ${o.box}, needs ${o.needs}`)}; let content set the height (min-block-size)`);
  if (v.small_taps_count) lines.push(`touch targets under 40px: ${v.small_taps_count} — ${eg(v.small_taps, (o) => `${o.el} "${o.text}" ${o.w}x${o.h}`)}`);
  if (v.sizes_in_use.length > 9) lines.push(`${v.sizes_in_use.length} font sizes in use (${v.sizes_in_use.join(', ')}): close sizes read as untidy, merge them into fewer steps`);
  kinds += lines.length;
  console.log(`== ${v.viewport} ==  body ${v.body_size}px, largest ${v.largest_size}px (x${v.largest_to_body}), sizes ${v.sizes_in_use.join('/')}, page height ${v.page_height}px, colored hues in first screen ${v.first_screen_hues.length}${v.first_screen_hues.length ? ' (' + v.first_screen_hues.join('°/') + '°)' : ''}`);
  for (const line of lines) console.log('  ! ' + line);
}
const pl = report.page_level, pageLines = [];
if (pl.px_font_rules) pageLines.push(`font sizes set in px: ${pl.px_font_rules} rule(s) — ${pl.px_font_examples.slice(0, 3).join('; ')}: use rem so the reader's own font-size setting applies`);
if (pl.english_eyebrows_count) pageLines.push(`decorative English labels in a Chinese page: ${pl.english_eyebrows_count} — ${pl.english_eyebrows.slice(0, 4).map((s) => `"${s}"`).join(', ')}: they read as a template and tell the reader nothing; write the label in Chinese, drop it, or say why it stays`);
if (pl.color_scheme === 'normal') pageLines.push('no color-scheme declared: form controls and scrollbars will not follow the page; declare color-scheme (light, or light dark with light-dark() colors) on :root and in a <meta>');
if (pageLines.length) { console.log('== whole page =='); for (const line of pageLines) console.log('  ! ' + line); kinds += pageLines.length; }
console.log(`Also look at: ${report.extra_screenshots.join(', ')} (forced colors${report.extra_screenshots.length > 1 ? ', dark' : ''}).`);
console.log(kinds ? `${kinds} finding(s). Details: ${path.join(outDir, stem + '-check.json')}` : 'Nothing measurable found.');
console.log(`Screenshots are in ${outDir}. Open them: this script cannot see layout, emphasis or taste.`);
