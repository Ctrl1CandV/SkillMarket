// List the elements that stick out past the right edge of the viewport. Usage: node overflow.mjs <page.html> [width]
import { createRequire } from 'node:module'; import path from 'node:path'; import { pathToFileURL } from 'node:url';
const require = createRequire(path.join(process.env.FC_NODE_MODULES, 'x.js')); const { chromium } = require('playwright-core');
const browser = await chromium.launch({ executablePath: process.env.FC_CHROME, headless: true }); const w = +(process.argv[3] || 390);
const page = await browser.newPage({ viewport: { width: w, height: 844 }, isMobile: w < 700, hasTouch: w < 700 }); await page.goto(pathToFileURL(process.argv[2]).href); await page.waitForTimeout(400);
console.log(await page.evaluate(() => { const vw = document.documentElement.clientWidth, out = [];
  for (const el of document.querySelectorAll('body *')) { const r = el.getBoundingClientRect(); if (r.right > vw + 1 && r.width > 0) { let scroller = false; for (let p = el.parentElement; p; p = p.parentElement) if (/(auto|scroll|hidden)/.test(getComputedStyle(p).overflowX)) scroller = true;
      if (!scroller) out.push(`${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}.${String(el.className.baseVal ?? el.className).split(' ')[0]} right=${Math.round(r.right)} width=${Math.round(r.width)}`); } }
  return `viewport ${vw}, page ${document.documentElement.scrollWidth}\n` + out.slice(0, 12).join('\n'); }));
await browser.close();
