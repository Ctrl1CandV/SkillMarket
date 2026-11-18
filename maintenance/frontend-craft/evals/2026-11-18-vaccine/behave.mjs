// 对照计划第 3 项：实际操作两组页面，按同样的步骤记录结果。
//   node behave.mjs <A|B|C|A2> <page.html> <out-dir>   （C 是 0.6.2 基线，A2 是修订后的 0.7.0）
// 两组的元素名不同，步骤相同；每组的选择器写在下面，是优化者读了各自页面后填的。
import { mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const { launch, open } = await import(pathToFileURL(resolve(fileURLToPath(new URL('.', import.meta.url)), '../../../../frontend-craft/scripts/env.mjs')).href);
const [arm, input, out] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const S = {
  A: { toMine: '#tab-mine', cancel: '[data-cancel]', dialog: '#dlg-cancel', toForm: async (p) => { await p.click('#tab-book'); await p.locator('[data-time]:not([disabled])').first().click(); await p.click('#bar1-next'); }, submit: '#bar2-next', phone: '#f-phone', pick: (p) => p.locator('[data-time]:not([disabled])').first().check({ force: true }), picked: '.slot:has(input:checked)' },
  B: { toMine: null, cancel: '[data-act="cancel"]', dialog: '#dlg-cancel', toForm: async () => {}, submit: '#submit-booking', phone: '#phone', pick: (p) => p.locator('.slots button.slot:not([aria-disabled="true"])').first().click(), picked: '.slots [aria-pressed="true"]' },
  C: { toMine: '.tabs [data-hot="mine"]', cancel: '[data-act="cancel"]', dialog: '#dlg', toForm: async (p) => { await p.locator('[data-time]:not([disabled])').first().click(); await p.click('#cta-btn'); }, submit: '#book-form button[type=submit]', phone: '#f-phone', pick: (p) => p.locator('[data-time]:not([disabled])').first().click(), picked: '[data-time][aria-pressed="true"]' },
  A2: { toMine: '#tab-mine', cancel: '[data-act="cancel"]', dialog: '#cancel-dialog', toForm: async (p) => { await p.locator('input[name="day"]:not([disabled])').first().check({ force: true }); await p.locator('input[name="slot"]:not([disabled])').first().check({ force: true }); await p.click('#next-btn'); }, submit: '#next-btn', phone: '#phone', pick: async (p) => { await p.locator('input[name="day"]:not([disabled])').first().check({ force: true }); await p.locator('input[name="slot"]:not([disabled])').first().check({ force: true }); }, picked: '.slot input:checked + .slot-in' },
}[arm];
const rows = [];
const rec = (k, v) => rows.push([k, v]);
const browser = await launch();
const { page, errors } = await open(browser, input, { width: 1440, height: 900 });
const focusDesc = () => page.evaluate(() => { const a = document.activeElement; if (!a || a === document.body) return 'body（页面开头）'; return (a.tagName + ' ' + (a.getAttribute('aria-label') || a.textContent || a.value || '').trim().slice(0, 20)); });

// 1. 取消确认对话框
if (S.toMine) await page.click(S.toMine);
await page.locator(S.cancel).first().click();
rec('取消对话框以模态打开', await page.evaluate((d) => document.querySelector(d).matches(':modal'), S.dialog));
rec('打开时的焦点', await focusDesc());
await page.keyboard.press('Escape');
rec('Esc 后对话框关闭', !(await page.evaluate((d) => document.querySelector(d).open, S.dialog)));
rec('关闭后的焦点', await focusDesc());

// 2. 空表单提交
await page.reload(); await page.waitForTimeout(300);
await S.toForm(page);
await page.click(S.submit);
await page.waitForTimeout(200);
rec('空提交后的焦点', await focusDesc());
rec('空提交后 aria-invalid=true 的字段数', await page.evaluate(() => document.querySelectorAll('[aria-invalid="true"]').length));
rec('空提交后看得见的错误提示数', await page.evaluate(() => [...document.querySelectorAll('[id*="err"], [id^="e-"], .error, .err')].filter((e) => !e.hidden && getComputedStyle(e).display !== 'none' && e.textContent.trim()).length));
await page.screenshot({ path: join(out, 'empty-submit.png') });

// 3. 手机号写错后离开
await page.reload(); await page.waitForTimeout(300);
await S.toForm(page);
await page.fill(S.phone, '123');
await page.keyboard.press('Tab');
await page.waitForTimeout(150);
rec('手机号写错离开后 aria-invalid', await page.getAttribute(S.phone, 'aria-invalid'));
rec('手机号写错离开后的 aria-describedby', await page.getAttribute(S.phone, 'aria-describedby'));
rec('手机号旁出现错误文字', await page.evaluate((sel) => { const i = document.querySelector(sel); const ids = (i.getAttribute('aria-describedby') || '').split(/\s+/); return ids.map((id) => document.getElementById(id)).filter((e) => e && !e.hidden && getComputedStyle(e).display !== 'none' && /[0-9位号码]/.test(e.textContent)).map((e) => e.textContent.trim().slice(0, 24)).join(' | ') || '无'; }, S.phone));
const hintPos = await page.evaluate((sel) => { const i = document.querySelector(sel); const ids = (i.getAttribute('aria-describedby') || '').split(/\s+/); const r = i.getBoundingClientRect(); return ids.map((id) => document.getElementById(id)).filter((e) => e && e.getBoundingClientRect().height).map((e) => (e.getBoundingClientRect().bottom <= r.top + 1 ? '上方' : '下方') + ':' + e.textContent.trim().slice(0, 12)).join(' | '); }, S.phone);
rec('手机号说明与错误的位置', hintPos || '无');
await page.close();

// 4. 系统深色
for (const scheme of ['dark']) {
  const ctx = await browser.newContext({ colorScheme: scheme, viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const p = await ctx.newPage(); await p.goto(pathToFileURL(resolve(input)).href); await p.waitForTimeout(300);
  rec('系统深色时 body 背景', await p.evaluate(() => getComputedStyle(document.body).backgroundColor));
  await p.screenshot({ path: join(out, 'dark-390.png'), fullPage: true });
  await ctx.close();
}
// 5. 强制颜色：选中一个时段后截图，看还分不分得清
{
  const ctx = await browser.newContext({ forcedColors: 'active', viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage(); await p.goto(pathToFileURL(resolve(input)).href); await p.waitForTimeout(300);
  await S.pick(p);   // 第一个还有名额的时段（第一次写的脚本点到了已满的时段，没选中，已改）
  rec('强制颜色下选中时段的轮廓', await p.evaluate((sel) => { const el = document.querySelector(sel); if (!el) return '没找到选中项'; const s = getComputedStyle(el); return s.outlineStyle + ' ' + s.outlineWidth; }, S.picked));
  await p.screenshot({ path: join(out, 'forced-picked.png') });
  await ctx.close();
}
rec('页面脚本错误', errors.length ? errors.join('；') : '无');
await browser.close();
for (const [k, v] of rows) console.log(`${k}：${v}`);
