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
// drag to zoom into the last part of training, then reset
await page.locator('.rrow[data-m="ls"]').click();
const hb = await page.locator('#hit').boundingBox();
await page.mouse.move(hb.x + hb.width * 0.70, hb.y + 80); await page.mouse.down(); await page.mouse.move(hb.x + hb.width * 0.98, hb.y + 90, { steps: 6 }); await page.mouse.up();
console.log('zoom sub:', await page.locator('#chart-sub').innerText(), '| reset shown:', await page.locator('#zoom').isVisible());
await page.screenshot({ path: path.join(out, 'd5-zoom.png') });
await page.locator('#zoom').click(); console.log('after reset:', await page.locator('#chart-sub').innerText());
const m = await browser.newPage({ viewport: { width: 390, height: 844 } }); await m.goto(url); await m.screenshot({ path: path.join(out, 'm1.png'), fullPage: true });
console.log('errors:', errors.length, errors.slice(0, 2)); await browser.close();
