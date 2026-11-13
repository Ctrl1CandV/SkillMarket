// Poem page: catch the reveal mid-way and at rest, step through all couplets, check phone and tablet.
import { createRequire } from 'node:module'; import path from 'node:path'; import fs from 'node:fs'; import { pathToFileURL } from 'node:url';
const require = createRequire(path.join(process.env.FC_NODE_MODULES, 'x.js')); const { chromium } = require('playwright-core');
const [file, out] = process.argv.slice(2); const url = pathToFileURL(file).href; fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.FC_CHROME, headless: true }); const errors = [];
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } }); page.on('pageerror', e => errors.push(e.message));
await page.goto(url + '#1'); await page.waitForTimeout(1500); await page.screenshot({ path: path.join(out, 'p1-mid.png') });
await page.waitForTimeout(3800); await page.screenshot({ path: path.join(out, 'p1-rest.png') });
console.log('font used:', await page.evaluate(() => document.fonts.check('100px "STXingkai"') ? 'STXingkai available' : 'fallback'), '| title', await page.title());
for (let k = 2; k <= 5; k++) { await page.mouse.click(700, 450); await page.waitForTimeout(5600); await page.screenshot({ path: path.join(out, `p${k}-rest.png`) }); console.log('couplet', k, ':', (await page.locator('#poem').innerText()).replace(/\s+/g, ''), '|', await page.locator('#by').innerText()); }
console.log('hint gone:', await page.locator('#hint').evaluate(el => el.classList.contains('gone')));
const rm = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' }); await rm.goto(url + '#3'); await rm.waitForTimeout(300); console.log('reduced motion, first char opacity at 0.3s:', await rm.locator('.ch').first().evaluate(el => getComputedStyle(el).opacity));
for (const [w, h] of [[390, 844], [1024, 768], [1920, 1080]]) { const p = await browser.newPage({ viewport: { width: w, height: h }, isMobile: w < 700, hasTouch: w < 700 }); await p.goto(url + '#2'); await p.waitForTimeout(5400); await p.screenshot({ path: path.join(out, `w-${w}.png`) });
  console.log(w, 'overflow:', await p.evaluate(() => { const r = document.getElementById('poem').getBoundingClientRect(); return { top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right), vh: innerHeight, vw: innerWidth }; })); await p.close(); }
console.log('errors:', errors.length, errors.slice(0, 2)); await browser.close();
