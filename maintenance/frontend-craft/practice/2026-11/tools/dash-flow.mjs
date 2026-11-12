// Click through the dashboard: loss metric, focus one method, hover the chart; desktop and phone.
import { createRequire } from 'node:module'; import path from 'node:path'; import { pathToFileURL } from 'node:url';
const require = createRequire(path.join(process.env.FC_NODE_MODULES, 'x.js')); const { chromium } = require('playwright-core');
const [file, out] = process.argv.slice(2); const url = pathToFileURL(file).href;
const browser = await chromium.launch({ executablePath: process.env.FC_CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } }); const errors = []; page.on('pageerror', e => errors.push(e.message));
await page.goto(url); await page.screenshot({ path: path.join(out, 'd1-default.png') });
await page.locator('#hit').hover({ position: { x: 300, y: 120 } }); console.log('tip:', (await page.locator('.tip').innerText()).replace(/\n/g, ' | '));
await page.screenshot({ path: path.join(out, 'd2-hover.png') });
await page.locator('button[data-m="loss"]').click(); await page.screenshot({ path: path.join(out, 'd3-loss.png') });
await page.locator('button[data-m="acc"]').click(); await page.locator('.rrow[data-m="ls"]').click();
console.log('sub after focus:', await page.locator('#runs-sub').innerText(), '| dim rows:', await page.locator('tr.dim').count());
await page.screenshot({ path: path.join(out, 'd4-focus.png'), fullPage: true });
const m = await browser.newPage({ viewport: { width: 390, height: 844 } }); await m.goto(url); await m.screenshot({ path: path.join(out, 'm1.png'), fullPage: true });
console.log('errors:', errors.length, errors.slice(0, 2)); await browser.close();
