// Screenshot several generated landscapes (still frames) and click through the interaction once.
import { createRequire } from 'node:module'; import path from 'node:path'; import fs from 'node:fs'; import { pathToFileURL } from 'node:url';
const require = createRequire(path.join(process.env.FC_NODE_MODULES, 'x.js')); const { chromium } = require('playwright-core');
const [file, out] = process.argv.slice(2); const url = pathToFileURL(file).href; fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.FC_CHROME, headless: true }); const errors = [];
const seeds = (process.argv[4] || '3000,3001,3002,4002,4003,4004').split(',');
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } }); page.on('pageerror', e => errors.push(e.message));
for (const s of seeds) { await page.goto(url + '?still=1#' + s); await page.reload(); await page.waitForTimeout(500); await page.screenshot({ path: path.join(out, `s-${s}.png`) }); }
// interaction with motion on
await page.goto(url + '#3000'); await page.reload(); await page.waitForTimeout(400);
const t0 = Date.now(); await page.locator('#c').click(); const build = Date.now() - t0;
await page.waitForTimeout(1200); console.log('after click: hash', page.url().split('#')[1], '| seal', await page.locator('#seal').innerText(), '| hint quiet', await page.locator('#hint').evaluate(el => el.classList.contains('quiet')), '| click-to-return ms', build);
await page.keyboard.press('Space'); await page.waitForTimeout(300); console.log('after space: seal', await page.locator('#seal').innerText(), '| live:', await page.locator('#live').innerText());
const fps = await page.evaluate(() => new Promise(res => { let n = 0; const t = performance.now(); const f = () => { n++; if (performance.now() - t < 1000) requestAnimationFrame(f); else res(n); }; requestAnimationFrame(f); }));
console.log('frames in one second (headless):', fps);
console.log('text on page:', (await page.locator('body').innerText()).replace(/\s+/g, ' ').trim());
for (const [w, h] of [[1024, 768], [390, 844], [1920, 1080]]) { const p = await browser.newPage({ viewport: { width: w, height: h }, isMobile: w < 700, hasTouch: w < 700 }); p.on('pageerror', e => errors.push(e.message)); await p.goto(url + '?still=1#3000'); await p.waitForTimeout(500); await p.screenshot({ path: path.join(out, `w-${w}.png`) }); await p.close(); }
console.log('errors:', errors.length, errors.slice(0, 2)); await browser.close();
