// Screenshot a live site and measure its type scale, fonts and colors. Usage: node refshot.mjs <url> <out-stem> [WxH]
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
const require = createRequire(path.join(process.env.FC_NODE_MODULES, 'x.js'));
const { chromium } = require('playwright-core');
const [url, stem, size] = process.argv.slice(2);
const [w, h] = (size || '1440x900').split('x').map(Number);
const browser = await chromium.launch({ executablePath: process.env.FC_CHROME, headless: true });
const ctx = await browser.newContext({ viewport: { width: w, height: h }, isMobile: w < 700, hasTouch: w < 700,
  userAgent: w < 700 ? 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1' : undefined });
const page = await ctx.newPage();
try { await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 }); } catch (e) { console.log('goto:', String(e.message).split('\n')[0]); }
await page.waitForTimeout(3500);
await page.screenshot({ path: stem + '.png' });
const m = await page.evaluate(() => {
  const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && r.top < innerHeight * 2 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const sizes = {}, fonts = {}, colors = {}, weights = {}, lh = {};
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) { const t = walker.currentNode.textContent.replace(/\s+/g, ''); const el = walker.currentNode.parentElement;
    if (!t || !el || !vis(el)) continue; const s = getComputedStyle(el); const k = Math.round(parseFloat(s.fontSize) * 10) / 10;
    sizes[k] = (sizes[k] || 0) + t.length; const f = s.fontFamily.split(',')[0].replace(/["']/g, '').trim(); fonts[f] = (fonts[f] || 0) + t.length;
    colors[s.color] = (colors[s.color] || 0) + t.length; weights[s.fontWeight] = (weights[s.fontWeight] || 0) + t.length;
    const l = parseFloat(s.lineHeight) / parseFloat(s.fontSize); if (l) { const lk = k + 'px@' + l.toFixed(2); lh[lk] = (lh[lk] || 0) + t.length; } }
  const top = (o, n) => Object.entries(o).sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, v]) => `${k}(${v})`).join('  ');
  const bg = getComputedStyle(document.body).backgroundColor;
  return { sizes: top(sizes, 8), fonts: top(fonts, 4), colors: top(colors, 6), weights: top(weights, 5), lineHeights: top(lh, 5), bodyBg: bg, title: document.title.slice(0, 60) };
});
console.log(JSON.stringify(m, null, 1));
await browser.close();
