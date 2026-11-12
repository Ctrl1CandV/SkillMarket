// Click through the settings page in both save modes and check that the summary follows every change.
import { createRequire } from 'node:module'; import path from 'node:path'; import { pathToFileURL } from 'node:url';
const require = createRequire(path.join(process.env.FC_NODE_MODULES, 'x.js')); const { chromium } = require('playwright-core');
const [file, out] = process.argv.slice(2); const url = pathToFileURL(file).href;
const browser = await chromium.launch({ executablePath: process.env.FC_CHROME, headless: true });
const errors = [];
const sum = async (p) => (await p.locator('#now').innerText()).replace(/\n/g, ' | ');
const bar = async (p) => (await p.locator('#bar-msg').innerText()).replace(/\s+/g, ' ');

// auto-save mode
let page = await browser.newPage({ viewport: { width: 1440, height: 900 } }); page.on('pageerror', e => errors.push(e.message));
await page.goto(url); await page.screenshot({ path: path.join(out, 's1-default.png') });
console.log('default  :', await sum(page));
await page.locator('[data-k="push"]').uncheck();
console.log('push off :', await sum(page));
console.log('  quiet disabled:', await page.locator('[data-k="quiet"]').isDisabled(), '| hint:', await page.locator('#quiet-d').innerText(), '| push col disabled:', await page.locator('input[data-c="push"]').first().isDisabled());
await page.screenshot({ path: path.join(out, 's2-push-off.png'), fullPage: true });
console.log('  bar:', await bar(page));
await page.locator('#undo').click(); console.log('undo     :', await sum(page));
await page.locator('[data-k="digest"]').selectOption('none'); console.log('no digest:', await sum(page));
await page.locator('[data-all="push"]').click(); console.log('all push :', (await sum(page)).slice(0, 90));
await page.locator('[data-pause="24"]').click(); console.log('paused   :', await sum(page), '|', (await page.locator('#paused').innerText()).replace(/\s+/g, ' ').slice(0, 40));
await page.reload(); console.log('reload keeps pause:', await page.locator('#paused').isVisible());
await page.locator('#resume').click(); await page.locator('#reset').click(); await page.locator('#reset').click();
console.log('reset    :', (await sum(page)) === (await sum(page)) ? await sum(page) : '');

// manual-save mode
page = await browser.newPage({ viewport: { width: 1440, height: 900 } }); page.on('pageerror', e => errors.push(e.message)); page.on('dialog', d => d.accept());
await page.goto(url + '?save=manual'); console.log('manual bar start:', await bar(page));
await page.locator('[data-k="weekend"]').check(); await page.locator('input[data-e="done"][data-c="push"]').check();
console.log('manual dirty    :', await bar(page), '| title:', await page.locator('#now-title').innerText());
await page.evaluate(() => scrollTo(0, 0)); await page.waitForTimeout(400); await page.screenshot({ path: path.join(out, 's3-manual-dirty.png') });
await page.locator('#undo').click(); console.log('manual discard  :', await bar(page));
await page.locator('[data-k="weekend"]').check(); await page.locator('#save').click(); console.log('manual saved    :', await bar(page));

const m = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }); await m.goto(url); await m.screenshot({ path: path.join(out, 'm1.png'), fullPage: true });
console.log('errors:', errors.length, errors.slice(0, 2)); await browser.close();
