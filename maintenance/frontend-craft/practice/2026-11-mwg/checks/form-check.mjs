// 练习页 2 的表单核对：错误出现的时机、aria 同步、错误汇总与焦点、成功提交、自动填充属性、提示在输入框上方、触控尺寸、字号单位、文字间距、强制颜色。
//   node form-check.mjs <page.html> <out-dir>
import { mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const { launch, open } = await import(pathToFileURL(resolve(fileURLToPath(new URL('.', import.meta.url)), '../../../../../frontend-craft/scripts/env.mjs')).href);
const [input, out] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const results = [];
const check = (name, ok, detail = '') => results.push({ name, ok: !!ok, detail });
const browser = await launch();
const { page, errors } = await open(browser, input, { width: 390, height: 844 });
const errShown = (id) => page.evaluate((id) => getComputedStyle(document.getElementById(id)).display !== 'none', id);
const attr = (id, a) => page.evaluate(([id, a]) => document.getElementById(id).getAttribute(a), [id, a]);

check('打开时没有显示任何错误', !(await page.evaluate(() => [...document.querySelectorAll('.error-msg')].some((e) => getComputedStyle(e).display !== 'none'))));
check('打开时 aria-invalid 都是 false', await page.evaluate(() => [...document.querySelectorAll('input')].every((i) => i.getAttribute('aria-invalid') === 'false')));

await page.focus('#child'); await page.keyboard.press('Tab');
check('空字段只经过、不输入：不报错（记录行为）', !(await errShown('child-error')), (await errShown('child-error')) ? '经过就报错' : '经过不报错');

await page.fill('#tel', '1234'); await page.keyboard.press('Tab');
check('手机号写错离开后显示错误', await errShown('tel-error'));
check('写错后 aria-invalid=true', (await attr('tel', 'aria-invalid')) === 'true');
check('写错后 aria-describedby 带上错误', (await attr('tel', 'aria-describedby') || '').includes('tel-error'), await attr('tel', 'aria-describedby'));
await page.fill('#tel', '13812345678');
check('改对后错误消失、aria-invalid=false', !(await errShown('tel-error')) && (await attr('tel', 'aria-invalid')) === 'false');

await page.click('#submit');
check('提交不全时出现错误汇总并获得焦点', await page.evaluate(() => !document.getElementById('errors').hidden && document.activeElement.id === 'errors'));
const n = await page.locator('#err-list li').count();
check('汇总列出了每一处', n >= 4, `${n} 处`);
await page.locator('#err-list a').first().click();
check('点汇总里的链接跳到对应字段', await page.evaluate(() => document.activeElement.tagName === 'INPUT'), await page.evaluate(() => document.activeElement.name));
check('提交后没碰过的空字段也标成错误', (await attr('child', 'aria-invalid')) === 'true' && (await errShown('child-error')));
await page.screenshot({ path: join(out, 'errors.png'), fullPage: true });

check('家长姓名和手机号带自动填充', (await attr('parent', 'autocomplete')) === 'name' && (await attr('tel', 'autocomplete'))?.startsWith('tel'));
check('格式提示在输入框上方', await page.evaluate(() => ['birth', 'tel', 'tel2'].every((id) => {
  const i = document.getElementById(id); const h = document.getElementById(id + '-hint');
  return h.getBoundingClientRect().bottom <= i.getBoundingClientRect().top + 1;
})));
const small = await page.evaluate(() => [...document.querySelectorAll('input:not([type=radio]):not([type=checkbox]), label.session, label.choice, label.agree, button')]
  .filter((el) => el.getBoundingClientRect().height && el.getBoundingClientRect().height < 47.5).map((el) => (el.id || el.textContent.trim().slice(0, 8)) + ' ' + Math.round(el.getBoundingClientRect().height)));
check('触控区域都不小于 48px（Google 表单指南）', !small.length, small.join('；'));

// 填对并提交
await page.check('input[name=session][value=s1]');
await page.fill('#child', '林小禾');
await page.fill('#birth', '2016-05-12');
await page.check('input[name=level][value="1"]');
await page.fill('#parent', '林晓');
await page.check('#agree');
await page.click('#submit');
check('提交后按钮立刻停用，防止重复提交', await page.evaluate(() => document.getElementById('submit').disabled));
await page.waitForTimeout(800);
check('提交成功显示确认信息（role=status）', await page.evaluate(() => !document.getElementById('done').hidden && document.getElementById('done').getAttribute('role') === 'status'));
await page.screenshot({ path: join(out, 'done.png') });

const px = await page.evaluate(() => { const r = []; for (const s of document.styleSheets) for (const x of s.cssRules) if (x.style && /px$/.test(x.style.fontSize)) r.push(x.selectorText); return r; });
check('字号不用 px', !px.length, px.join('；'));
await page.close();

// 文字间距与强制颜色
const p2 = await (await browser.newContext({ viewport: { width: 390, height: 844 } })).newPage();
await p2.goto(pathToFileURL(resolve(input)).href);
await p2.addStyleTag({ content: '* { line-height: 1.5 !important; letter-spacing: .12em !important; word-spacing: .16em !important; } p { margin-block-end: 2em !important; }' });
const clipped = await p2.evaluate(() => [...document.querySelectorAll('label, .hint, .when, .left, button, legend')].filter((el) => {
  const cs = getComputedStyle(el); return (cs.overflow !== 'visible') && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1);
}).map((el) => el.textContent.trim().slice(0, 12)));
check('文字间距放大后无裁切', !clipped.length, clipped.join('；'));
const p3 = await (await browser.newContext({ forcedColors: 'active', viewport: { width: 390, height: 844 } })).newPage();
await p3.goto(pathToFileURL(resolve(input)).href);
await p3.check('input[name=session][value=s3]');
const ol = await p3.evaluate(() => getComputedStyle(document.querySelector('.session:has(input:checked)')).outlineStyle);
check('强制颜色下选中的班次有轮廓', ol !== 'none', ol);
await p3.screenshot({ path: join(out, 'forced-colors.png') });

check('页面脚本无错误', !errors.length, errors.join('；'));
await browser.close();
for (const r of results) console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.name}${r.detail ? '  — ' + r.detail : ''}`);
console.log(`${results.filter((r) => r.ok).length}/${results.length}`);
