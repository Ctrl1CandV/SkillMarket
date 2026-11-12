// Click through the reading page: chart controls, a sidenote on a narrow screen, theme switch.
import { createRequire } from 'node:module'; import path from 'node:path'; import { pathToFileURL } from 'node:url';
const require = createRequire(path.join(process.env.FC_NODE_MODULES, 'x.js')); const { chromium } = require('playwright-core');
const url = pathToFileURL(process.argv[2]).href;
const browser = await chromium.launch({ executablePath: process.env.FC_CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } }); const errors = []; page.on('pageerror', e => errors.push(e.message));
await page.goto(url);
const read = async () => (await page.locator('#readout').innerText()).replace(/\s+/g, ' ');
console.log('default :', await read());
await page.locator('button[data-h="8"]').click(); console.log('slow    :', await read());
await page.locator('button[data-h="3"]').click(); console.log('fast    :', await read());
await page.locator('button[data-h="5"]').click(); await page.locator('button[data-t="13"]').click(); console.log('13:00   :', await read());
await page.locator('button[data-t="17"]').click(); console.log('17:00   :', await read());
await page.locator('#theme').click(); console.log('theme   :', await page.evaluate(() => document.documentElement.dataset.theme + ' ' + getComputedStyle(document.body).backgroundColor));
const m = await browser.newPage({ viewport: { width: 390, height: 844 } }); await m.goto(url);
const note = m.locator('.sn small').first(); console.log('note hidden first:', !(await note.isVisible()));
await m.locator('.sn > button').first().click(); console.log('note shown after tap:', await note.isVisible());
console.log('errors:', errors.length); await browser.close();
