// Distant Mountains v2: still frames at several times of day and seeds, then interaction and frame rate with motion on.
import { createRequire } from 'node:module'; import path from 'node:path'; import fs from 'node:fs'; import { pathToFileURL } from 'node:url';
const require = createRequire(path.join(process.env.FC_NODE_MODULES, 'x.js')); const { chromium } = require('playwright-core');
const [file, out] = process.argv.slice(2); const url = pathToFileURL(file).href; fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.FC_CHROME, headless: true }); const errors = [];
const shots = (process.argv[4] || '3000,0.05;3000,0.27;3000,0.5;3000,0.58;3000,0.8;4003,0.1;4003,0.55;5001,0.86').split(';');
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } }); page.on('pageerror', e => errors.push(e.message));
for (const s of shots) { await page.goto(url + '?still=1#' + s); await page.reload(); await page.waitForTimeout(350); await page.screenshot({ path: path.join(out, `t-${s.replace(',', '-')}.png`) }); }
if (!process.argv[5]) {
  await page.goto(url + '#3000,0.05'); await page.reload(); await page.waitForTimeout(2600);   // let the entrance finish
  await page.screenshot({ path: path.join(out, 'live-1.png') });
  const fps = await page.evaluate(() => new Promise(res => { let n = 0; const t = performance.now(); const f = () => { n++; if (performance.now() - t < 2000) requestAnimationFrame(f); else res(Math.round(n / 2)); }; requestAnimationFrame(f); }));
  const cost = await page.evaluate(() => new Promise(res => { const t = []; let last = performance.now(), n = 0; const f = (now) => { t.push(now - last); last = now; if (++n < 90) requestAnimationFrame(f); else { t.sort((a, b) => a - b); res({ median: +t[45].toFixed(1), p95: +t[85].toFixed(1) }); } }; requestAnimationFrame(f); }));
  console.log('frames per second (headless, 1440x900):', fps, '| frame gap ms', JSON.stringify(cost));
  const box = await page.locator('#c').boundingBox();
  await page.mouse.click(box.x + 700, box.y + 400); await page.waitForTimeout(700); await page.screenshot({ path: path.join(out, 'live-2-morphing.png') }); await page.waitForTimeout(1600);
  console.log('after click : hash', page.url().split('#')[1], '| live:', await page.locator('#live').innerText(), '| hint quiet', await page.locator('#hint').evaluate(el => el.classList.contains('quiet')));
  await page.mouse.move(box.x + 300, box.y + 400); await page.mouse.down(); await page.mouse.move(box.x + 1000, box.y + 420, { steps: 12 }); await page.mouse.up(); await page.waitForTimeout(300);
  console.log('after drag  : hash', page.url().split('#')[1], '| seal', await page.locator('#seal').innerText());
  await page.keyboard.press('ArrowRight'); await page.keyboard.press('ArrowRight'); console.log('after keys  : hash', page.url().split('#')[1]);
  console.log('text on page:', (await page.locator('body').innerText()).replace(/\s+/g, ' ').trim());
  for (const [w, h] of [[390, 844], [1024, 768], [1920, 1080]]) { const p = await browser.newPage({ viewport: { width: w, height: h }, isMobile: w < 700, hasTouch: w < 700 }); p.on('pageerror', e => errors.push(e.message)); await p.goto(url + '?still=1#3000,0.6'); await p.waitForTimeout(400); await p.screenshot({ path: path.join(out, `w-${w}.png`) }); await p.close(); }
}
console.log('errors:', errors.length, errors.slice(0, 2)); await browser.close();
