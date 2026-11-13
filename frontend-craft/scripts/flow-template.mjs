#!/usr/bin/env node
// flow-template.mjs — copy this next to your page and edit it: a few checks that only this page needs.
// pagecheck.mjs measures what every page shares. It cannot know that "the total must be 24 after one more order",
// or that "the title on each book spine must fit inside the spine". Write those down here and run them after every change.
//
//   node flow-template.mjs <page.html | url> [<out-dir>]
import path from 'node:path';
import fs from 'node:fs';
import { launch, open } from './env.mjs';   // when you copy this file elsewhere, point this at <skill>/scripts/env.mjs

const [input, outDir = '_flow'] = process.argv.slice(2);
if (!input) { console.error('usage: node flow-template.mjs <page.html | url> [<out-dir>]'); process.exit(2); }
fs.mkdirSync(outDir, { recursive: true });
const browser = await launch();
let failed = 0;
const check = (label, pass, detail = '') => { console.log(`${pass ? 'ok  ' : 'FAIL'} ${label}${detail ? ' — ' + detail : ''}`); if (!pass) failed++; };

// 1. Walk the main task once, the way a person would, and look at what the page says afterwards.
const desk = await open(browser, input, { width: 1440, height: 900 });
//    await desk.page.fill('#q', '5678');
//    await desk.page.locator('button[data-act="pick"]').first().click();
//    check('one order is found by the last four digits', await desk.page.locator('.row').count() === 1);
await desk.page.screenshot({ path: path.join(outDir, 'after-main-task.png') });

// 2. Assert what is specific to this page: numbers that must add up, text that must fit, a state that must survive a reload.
//    const total = await desk.page.locator('#total').innerText();
//    check('total counts the new order', total === '24', `got ${total}`);
//    const overflow = await desk.page.evaluate(() => [...document.querySelectorAll('.label')].filter(el => el.scrollHeight > el.clientHeight + 1).length);
//    check('every label fits its box', overflow === 0, `${overflow} overflow`);

// 3. Repeat the part that changes shape on a phone.
const phone = await open(browser, input, { width: 390, height: 844 });
await phone.page.screenshot({ path: path.join(outDir, 'phone.png'), fullPage: true });

check('no script errors', desk.errors.length + phone.errors.length === 0, [...desk.errors, ...phone.errors][0] || '');
await browser.close();
console.log(failed ? `${failed} check(s) failed` : 'all checks passed', `— screenshots in ${path.resolve(outDir)}`);
process.exit(failed ? 1 : 0);
