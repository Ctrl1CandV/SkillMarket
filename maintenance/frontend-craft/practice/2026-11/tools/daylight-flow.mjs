// Click through the daylight piece and check the numbers and the claims made in its wall text.
import { createRequire } from 'node:module'; import path from 'node:path'; import { pathToFileURL } from 'node:url';
const require = createRequire(path.join(process.env.FC_NODE_MODULES, 'x.js')); const { chromium } = require('playwright-core');
const [file, out] = process.argv.slice(2); const url = pathToFileURL(file).href;
const browser = await chromium.launch({ executablePath: process.env.FC_CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } }); const errors = []; page.on('pageerror', e => errors.push(e.message));
const read = async (p = page) => (await p.locator('#read').innerText()).replace(/\s+/g, ' ').replace('在画上移动，或者按左右键，换一天。', '');
await page.goto(url + '#lat=39.9&view=band&day=172'); await page.waitForTimeout(400);
console.log('北京 夏至    :', await read()); await page.screenshot({ path: path.join(out, 'd1-beijing.png') });
await page.goto(url + '#lat=39.9&view=band&day=356'); await page.reload(); await page.waitForTimeout(300); console.log('北京 冬至    :', await read());
// claims in the wall text: latest sunrise is in early January, earliest sunset is before the winter solstice
const claim = await page.evaluate(() => { const RAD = Math.PI / 180, lat = 39.9; let late = [0, 0], early = [0, 9999];
  for (let n = 1; n <= 365; n++) { const g = 2 * Math.PI / 365 * (n - 1), eq = 229.18 * (0.000075 + 0.001868 * Math.cos(g) - 0.032077 * Math.sin(g) - 0.014615 * Math.cos(2 * g) - 0.040849 * Math.sin(2 * g)),
      d = 0.006918 - 0.399912 * Math.cos(g) + 0.070257 * Math.sin(g) - 0.006758 * Math.cos(2 * g) + 0.000907 * Math.sin(2 * g) - 0.002697 * Math.cos(3 * g) + 0.00148 * Math.sin(3 * g),
      ha = Math.acos(Math.cos(90.833 * RAD) / (Math.cos(lat * RAD) * Math.cos(d)) - Math.tan(lat * RAD) * Math.tan(d)) / RAD, rise = 720 - 4 * ha - eq, set = 720 + 4 * ha - eq;
    if (rise > late[1]) late = [n, rise]; if (set < early[1]) early = [n, set]; }
  return { latestSunriseDay: late[0], earliestSunsetDay: early[0] }; });
console.log('文中的说法   : 日出最晚在第', claim.latestSunriseDay, '天（1 月初应为 1–10），日落最早在第', claim.earliestSunsetDay, '天（冬至是第 356 天）');
await page.locator('.chip[data-lat="69.7"]').click(); await page.waitForTimeout(300); console.log('特罗姆瑟 冬至 :', await read()); await page.screenshot({ path: path.join(out, 'd2-tromso.png') });
await page.locator('.chip[data-lat="1.3"]').click(); await page.waitForTimeout(300); console.log('新加坡 冬至   :', await read()); await page.screenshot({ path: path.join(out, 'd3-singapore.png') });
await page.locator('.chip[data-lat="-33.9"]').click(); await page.waitForTimeout(300); console.log('悉尼 12/22   :', await read());
await page.locator('.chip[data-lat="39.9"]').click(); await page.locator('#work').focus(); await page.keyboard.press('ArrowRight'); console.log('右键一天     :', (await read()).slice(0, 12));
const box = await page.locator('#cv').boundingBox(); await page.mouse.move(box.x + box.width * 0.47, box.y + box.height / 2); console.log('鼠标到 47%   :', (await read()).slice(0, 44));
await page.locator('#view button[data-v="ring"]').click(); await page.waitForTimeout(400); await page.screenshot({ path: path.join(out, 'd4-ring.png'), fullPage: true });
await page.locator('.chip[data-lat="64.1"]').click(); await page.waitForTimeout(400); await page.locator('#work').screenshot({ path: path.join(out, 'd5-ring-reykjavik.png') });
await page.locator('#lat').evaluate(el => { el.value = '55'; el.dispatchEvent(new Event('input', { bubbles: true })); }); await page.waitForTimeout(200); console.log('滑块 55°     :', await page.locator('#lat-v').innerText(), '| 城市高亮数', await page.locator('.chip[aria-pressed="true"]').count());
const m = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }); await m.goto(url + '#lat=39.9&view=band&day=172'); await m.waitForTimeout(400); await m.screenshot({ path: path.join(out, 'm1.png'), fullPage: true });
console.log('errors:', errors.length, errors.slice(0, 2)); await browser.close();
