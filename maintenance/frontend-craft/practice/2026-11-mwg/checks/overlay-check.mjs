// 练习页 1 的交互核对：行内菜单的锚点位置、撤销对话框的焦点与 Esc、提示条时机、键盘、强制颜色、字号单位、文字间距。
//   node overlay-check.mjs <page.html> <out-dir>
// 需要 FC_NODE_MODULES、FC_CHROME（见 frontend-craft/scripts/env.mjs）。
import { mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const envUrl = pathToFileURL(resolve(fileURLToPath(new URL('.', import.meta.url)), '../../../../../frontend-craft/scripts/env.mjs')).href;
const { launch, open } = await import(envUrl);
const [input, out] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const results = [];
const check = (name, ok, detail = '') => results.push({ name, ok: !!ok, detail });

const browser = await launch();
const { page, errors } = await open(browser, input, { width: 1440, height: 900 });

// 1. 行内菜单贴着按钮
const more = page.locator('button.more').first();
await more.click();
const panel = page.locator('.panel:popover-open');
const [mb, pb] = [await more.boundingBox(), await panel.boundingBox()];
check('菜单打开', pb);
check('菜单贴着按钮（垂直间距 ≤ 16px，水平有重叠）', pb && Math.abs(pb.y - (mb.y + mb.height)) <= 16 && pb.x < mb.x + mb.width && pb.x + pb.width > mb.x,
  pb && `按钮 ${Math.round(mb.x)},${Math.round(mb.y)} 菜单 ${Math.round(pb.x)},${Math.round(pb.y)}`);
await page.keyboard.press('Escape');
check('Esc 关菜单', !(await page.locator('.panel:popover-open').count()));

// 2. 撤销对话框：默认焦点、Esc、焦点回到哪里
await more.click();
await page.locator('.panel:popover-open [data-cancel]').click();
check('对话框以模态打开', await page.evaluate(() => document.querySelector('#cancel-dialog').matches(':modal')));
check('默认焦点在“保留工单”', (await page.evaluate(() => document.activeElement?.textContent)) === '保留工单');
await page.keyboard.press('Escape');
check('Esc 关对话框', !(await page.evaluate(() => document.querySelector('#cancel-dialog').open)));
const back = await page.evaluate(() => { const a = document.activeElement; return a === document.body ? 'body' : (a.getAttribute('aria-label') || a.textContent).trim(); });
check('关闭后焦点回到可见的控件（不是 body）', back !== 'body', `焦点在：${back}`);

// 3. 确认撤销：提示条在对话框关闭后才出现
const before = await page.locator('.row').count();
await more.click();
await page.locator('.panel:popover-open [data-cancel]').click();
await page.fill('#cancel-reason', '业主已自行修好');
check('对话框打开时没有提示条', !(await page.locator('.toast:popover-open').count()));
await page.click('#cancel-dialog [value="cancel-ticket"]');
await page.waitForTimeout(100);
check('撤销后工单少一张', (await page.locator('.row').count()) === before - 1);
check('撤销后出现提示条', await page.locator('.toast:popover-open').count());
await page.screenshot({ path: join(out, 'after-cancel.png') });

// 4. 键盘派单：Tab 到“派单”，空格选师傅，回车提交
await page.locator('.row button.btn:has-text("派单")').first().focus();
await page.keyboard.press('Enter');
await page.locator('#assign button[type=submit]').focus();
await page.keyboard.press('Enter');
await page.waitForTimeout(100);
check('键盘可派单（出现派单提示）', await page.locator('.toast:popover-open', { hasText: '已派给' }).count());

// 5. 字号单位与带文字元素的固定高度
const units = await page.evaluate(() => {
  const px = []; const fixed = [];
  for (const sheet of document.styleSheets) for (const r of sheet.cssRules) {
    const s = r.style; if (!s) continue;
    if (/px$/.test(s.fontSize)) px.push(r.selectorText);
    if (/^\d/.test(s.height) || /^\d/.test(s.blockSize)) fixed.push(r.selectorText + ' ' + (s.height || s.blockSize));
  }
  return { px, fixed };
});
check('字号不用 px', !units.px.length, units.px.join('；'));
check('没有写死高度的规则（逐条看是否带文字）', !units.fixed.length, units.fixed.join('；'));

// 6. WCAG 1.4.12 文字间距：放大后没有被裁掉的文字
await page.addStyleTag({ content: '* { line-height: 1.5 !important; letter-spacing: .12em !important; word-spacing: .16em !important; } p { margin-block-end: 2em !important; }' });
const clipped = await page.evaluate(() => [...document.querySelectorAll('button, .tag, .what, .sub, .room, label, dt, dd')].filter((el) => {
  const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
  return r.width && (cs.overflow !== 'visible' || cs.overflowX !== 'visible') && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1);
}).map((el) => el.textContent.trim().slice(0, 20)));
check('文字间距放大后无裁切', !clipped.length, clipped.join('；'));
await page.screenshot({ path: join(out, 'text-spacing.png') });
await page.close();

// 7. 强制颜色：选中行与“紧急”还能分辨
const fc = await browser.newContext({ forcedColors: 'active', viewport: { width: 1440, height: 900 } });
const p2 = await fc.newPage();
await p2.goto(input.startsWith('http') ? input : pathToFileURL(resolve(input)).href);
const fcInfo = await p2.evaluate(() => {
  const row = document.querySelector('.row[aria-current="true"]'); const tag = document.querySelector('.tag.urgent');
  const cs = (el) => getComputedStyle(el);
  return { rowOutline: cs(row).outlineStyle + ' ' + cs(row).outlineWidth, tagBorder: cs(tag).borderStyle + ' ' + cs(tag).borderWidth };
});
check('强制颜色下选中行有轮廓', !fcInfo.rowOutline.startsWith('none'), fcInfo.rowOutline);
check('强制颜色下“紧急”有边框', !fcInfo.tagBorder.startsWith('none'), fcInfo.tagBorder);
await p2.screenshot({ path: join(out, 'forced-colors.png') });

check('页面脚本无错误', !errors.length, errors.join('；'));
await browser.close();
for (const r of results) console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.name}${r.detail ? '  — ' + r.detail : ''}`);
console.log(`${results.filter((r) => r.ok).length}/${results.length}`);
