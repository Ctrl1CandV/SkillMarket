// 练习页 3 的主题与表格核对：跟随系统深浅色、手动覆盖与记住选择、两种配色下的对比度、高对比度偏好、强制颜色、窄屏表格、字号单位。
//   node theme-check.mjs <page.html> <out-dir>
import { mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const { launch } = await import(pathToFileURL(resolve(fileURLToPath(new URL('.', import.meta.url)), '../../../../../frontend-craft/scripts/env.mjs')).href);
const [input, out] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const url = pathToFileURL(resolve(input)).href;
const results = [];
const check = (name, ok, detail = '') => results.push({ name, ok: !!ok, detail });
const browser = await launch();

// 对比度：在页面里把计算后的颜色转成 sRGB 再算
const contrastJs = () => {
  const toRgb = (c) => { const x = document.createElement('canvas').getContext('2d'); x.fillStyle = c; x.fillRect(0, 0, 1, 1); return [...x.getImageData(0, 0, 1, 1).data].slice(0, 3); };
  const lum = ([r, g, b]) => [r, g, b].map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }).reduce((a, v, i) => a + v * [0.2126, 0.7152, 0.0722][i], 0);
  const ratio = (a, b) => { const [x, y] = [lum(toRgb(a)), lum(toRgb(b))].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
  const cs = (sel, prop) => getComputedStyle(document.querySelector(sel))[prop];
  const surface = cs('.hero', 'backgroundColor');
  return {
    scheme: getComputedStyle(document.documentElement).colorScheme,
    body: cs('body', 'backgroundColor'),
    ink: ratio(cs('.amount .num', 'color'), surface),
    ink2: ratio(cs('.amount .label', 'color'), surface),
    up: ratio(cs('.why .up', 'color'), surface),
    brandBar: ratio(cs('.bar span', 'backgroundColor'), cs('.bar', 'backgroundColor')),
  };
};
const fmt = (o) => `正文 ${o.ink.toFixed(1)}，次要文字 ${o.ink2.toFixed(1)}，涨幅红 ${o.up.toFixed(1)}，进度条对底色 ${o.brandBar.toFixed(1)}`;

for (const scheme of ['light', 'dark']) {
  const ctx = await browser.newContext({ colorScheme: scheme, viewport: { width: 1024, height: 900 } });
  const page = await ctx.newPage();
  const errors = []; page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(url);
  const c = await page.evaluate(contrastJs);
  check(`系统为${scheme === 'dark' ? '深色' : '浅色'}时页面跟随`, (scheme === 'dark') === /^(rgb\((1|2|3)\d,)/.test(c.body), c.body);
  check(`${scheme}：文字对比度达标（正文、次要 ≥ 4.5，涨幅红 ≥ 4.5，进度条 ≥ 3）`, c.ink >= 4.5 && c.ink2 >= 4.5 && c.up >= 4.5 && c.brandBar >= 3, fmt(c));
  await page.screenshot({ path: join(out, `${scheme}-1024.png`), fullPage: true });
  if (scheme === 'dark') {
    await page.click('text=浅色');
    check('系统深色时可以手动切成浅色', (await page.evaluate(() => getComputedStyle(document.documentElement).colorScheme)) === 'light');
    await page.reload();
    check('刷新后记住手动选择', (await page.evaluate(() => getComputedStyle(document.documentElement).colorScheme)) === 'light'
      && (await page.isChecked('input[value="light"]')));
    await page.click('text=跟随系统');
    await page.reload();
    check('改回跟随系统后不再覆盖', (await page.evaluate(() => getComputedStyle(document.documentElement).colorScheme)).includes('dark')
      && (await page.evaluate(() => localStorage.getItem('bill-scheme'))) === null);
  }
  check(`${scheme}：页面脚本无错误`, !errors.length, errors.join('；'));
  await ctx.close();
}

// 窄屏表格变成逐月卡片，宽屏是表格
for (const [w, want] of [[1024, 'table'], [390, 'block']]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
  const page = await ctx.newPage(); await page.goto(url);
  const d = await page.evaluate(() => ({ table: getComputedStyle(document.querySelector('table')).display, thead: getComputedStyle(document.querySelector('thead')).display, label: getComputedStyle(document.querySelector('td'), '::before').content, scroll: document.documentElement.scrollWidth > innerWidth }));
  check(`${w}px：表格形态为 ${want}`, d.table === want && (want === 'block' ? d.thead === 'none' && d.label.includes('用电') : true), JSON.stringify(d));
  check(`${w}px：页面不横向滚动`, !d.scroll);
  if (w === 390) await page.screenshot({ path: join(out, 'light-390.png'), fullPage: true });
  await ctx.close();
}

// 高对比度偏好与强制颜色
{
  const ctx = await browser.newContext({ contrast: 'more', viewport: { width: 1024, height: 900 } });
  const page = await ctx.newPage(); await page.goto(url);
  const c = await page.evaluate(contrastJs);
  check("偏好高对比度时次要文字更深，进度条仍清楚", c.ink2 >= 7 && c.brandBar >= 3, fmt(c));
  await ctx.close();
}
{
  const ctx = await browser.newContext({ forcedColors: 'active', viewport: { width: 1024, height: 900 } });
  const page = await ctx.newPage(); await page.goto(url);
  const b = await page.evaluate(() => getComputedStyle(document.querySelector('.bar')).borderTopStyle);
  check('强制颜色下进度条有边框', b !== 'none', b);
  await page.screenshot({ path: join(out, 'forced-colors.png') });
  const px = await page.evaluate(() => { const r = []; for (const s of document.styleSheets) for (const x of s.cssRules) if (x.style && /px$/.test(x.style.fontSize)) r.push(x.selectorText); return r; });
  check('字号不用 px', !px.length, px.join('；'));
  await ctx.close();
}
await browser.close();
for (const r of results) console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.name}${r.detail ? '  — ' + r.detail : ''}`);
console.log(`${results.filter((r) => r.ok).length}/${results.length}`);
