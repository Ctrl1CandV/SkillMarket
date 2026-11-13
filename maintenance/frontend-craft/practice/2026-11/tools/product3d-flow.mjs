// 3D product page: screenshots per glaze and angle, drag / double-click / keyboard, frame time on GPU and on software rendering.
import { createRequire } from 'node:module'; import path from 'node:path'; import fs from 'node:fs'; import { pathToFileURL } from 'node:url';
const require = createRequire(path.join(process.env.FC_NODE_MODULES, 'x.js')); const { chromium } = require('playwright-core');
const [file, out] = process.argv.slice(2); const url = pathToFileURL(file).href; fs.mkdirSync(out, { recursive: true });
const errors = [];
async function run(label, args) {
  const browser = await chromium.launch({ executablePath: process.env.FC_CHROME, headless: true, args });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } }); page.on('pageerror', e => errors.push(label + ': ' + e.message)); page.on('console', m => m.type() === 'error' && errors.push(label + ': ' + m.text()));
  await page.goto(url + '?yaw=-0.5'); await page.waitForTimeout(800);
  const t = await page.evaluate(async () => { const c = document.getElementById('c'), gl = c.getContext('webgl'); const ms = []; for (let i = 0; i < 12; i++) { const a = performance.now(); window.__cup.draw(); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(4)); ms.push(performance.now() - a); } ms.sort((x, y) => x - y); return { median: +ms[6].toFixed(1), canvas: [c.width, c.height] }; });
  console.log(label, 'frame ms (drawn + read back):', JSON.stringify(t));
  if (label === 'gpu') {
    await page.screenshot({ path: path.join(out, 'g0-qinghui.png') });
    for (const [i, name] of [[1, 'yuebai'], [2, 'shihong'], [3, 'mohei']]) { await page.goto(url + `?glaze=${i}&yaw=2.35`); await page.waitForTimeout(600); await page.screenshot({ path: path.join(out, `g${i}-${name}.png`) }); }
    for (const yaw of [0.6, 1.9, 3.3]) { await page.goto(url + `?yaw=${yaw}`); await page.waitForTimeout(600); await page.locator('#stage').screenshot({ path: path.join(out, `y-${yaw}.png`) }); }
    await page.goto(url + '?yaw=-0.5'); await page.waitForTimeout(500); const box = await page.locator('#c').boundingBox();
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2); await page.mouse.down(); await page.mouse.move(box.x + box.width / 2 - 220, box.y + box.height / 2 - 120, { steps: 10 }); await page.mouse.up(); await page.waitForTimeout(400);
    await page.locator('#stage').screenshot({ path: path.join(out, 'drag.png') }); console.log('tip hidden after drag:', await page.locator('#tip').evaluate(el => el.classList.contains('gone')));
    await page.locator('#c').dblclick({ position: { x: box.width / 2, y: box.height / 2 } }); await page.waitForTimeout(900); await page.locator('#stage').screenshot({ path: path.join(out, 'reset.png') });
    await page.locator('#sw button[data-i="2"]').click(); await page.waitForTimeout(380); await page.locator('#stage').screenshot({ path: path.join(out, 'mid-glaze.png') }); await page.waitForTimeout(500);
    console.log('glaze label:', await page.locator('#gname').innerText(), '|', await page.locator('#gnote').innerText());
    await page.locator('#add').click(); console.log('added:', await page.locator('#added').innerText());
    for (const [w, h] of [[390, 844], [1024, 768]]) { const p = await browser.newPage({ viewport: { width: w, height: h }, isMobile: w < 700, hasTouch: w < 700 }); p.on('pageerror', e => errors.push(e.message)); await p.goto(url + '?yaw=-0.5'); await p.waitForTimeout(700); await p.screenshot({ path: path.join(out, `w-${w}.png`), fullPage: true }); await p.close(); }
    const ng = await browser.newPage(); await ng.addInitScript(() => { const orig = HTMLCanvasElement.prototype.getContext; HTMLCanvasElement.prototype.getContext = function (t, o) { return t === 'webgl' ? null : orig.call(this, t, o); }; });
    await ng.goto(url); await ng.waitForTimeout(300); console.log('no-webgl fallback:', (await ng.locator('.nogl').innerText()).replace(/\s+/g, ' '));
  }
  await browser.close();
}
await run('gpu', []);
await run('software', ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']);
console.log('errors:', errors.length, errors.slice(0, 3));
