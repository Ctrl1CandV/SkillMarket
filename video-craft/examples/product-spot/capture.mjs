// Run after changing the product or the example case. Real clicks, screenshots, and exported text
// come from the same local build that the viewer can open after the film.
import { readFileSync, mkdirSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { launch, fileUrl } from '../../kit/env.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const job = JSON.parse(readFileSync(process.argv[2] || join(here, 'spot.json'), 'utf8').replace(/^\uFEFF/, ''));
const frames = join(here, 'material');
mkdirSync(frames, { recursive: true });
const temp = mkdtempSync(join(tmpdir(), 'backtime-download-'));
const browser = await launch();
try {
  const page = await browser.newPage({ viewport: { width: 1180, height: 555 }, deviceScaleFactor: 1.5, acceptDownloads: true });
  await page.goto(fileUrl(join(here, 'product.html')));
  const tasks = page.locator('.task');
  while (await tasks.count()) await tasks.first().getByRole('button').click();
  for (const [name, mins] of job.tasks) {
    await page.locator('#add').click();
    await tasks.last().getByLabel('环节名称').fill(name);
    await tasks.last().getByLabel('环节分钟数').fill(String(mins));
  }
  const snapshot = async name => {
    await page.evaluate(()=>document.activeElement.blur());
    await page.screenshot({ path: join(frames, name + '.png') });
  };
  const texts = () => page.locator('#result tr').allTextContents();
  const locate = async selector => {
    const {x,y,width,height} = await page.locator(selector).boundingBox();
    return { x, y, width, height };
  };
  await page.locator('#show').fill(job.early);
  await page.locator('#rebuild').click();
  const before = await texts();
  await snapshot('before');
  await page.locator('#show').fill(job.late);
  assert.deepEqual(await texts(), before, 'the result must still show the earlier schedule before applying');
  assert.equal(await page.locator('#download').isDisabled(), true);
  await snapshot('edited');
  await page.locator('#rebuild').click();
  const after = await texts();
  assert.notDeepEqual(after, before);
  await snapshot('after');
  const [download] = await Promise.all([page.waitForEvent('download'), page.locator('#download').click()]);
  const downloaded = join(temp, 'actual.txt');
  await download.saveAs(downloaded);
  const exported = readFileSync(downloaded,'utf8').replace(/^\uFEFF/, '');
  const clock = time=> (time < 0 ? Math.ceil(-time/1440) === 1 ? '前日' : '前'+Math.ceil(-time/1440)+'日' : '') +
    [Math.floor(((time%1440+1440)%1440)/60), ((time%60)+60)%60].map(x=>String(x).padStart(2,'0')).join(':');
  const [hour,minute] = job.late.split(':').map(Number);
  let remaining = hour * 60 + minute;
  const reversed = [...job.tasks].reverse().map(([name, length])=>{ remaining -= length; return clock(remaining)+'  '+name+'  '+length+' 分'; });
  assert.deepEqual(exported.trim().split(/\r?\n/), ['倒场 / 执行台本', ...reversed.reverse(), job.late+'  正式开场']);
  const bounds = Object.fromEntries(await Promise.all(['#show','#rebuild','#download','.sheet'].map(async selector=>[selector, await locate(selector)])));
  writeFileSync(join(frames,'proof.js'), 'export const proof = '+JSON.stringify({ job, before, after, exported, filename:download.suggestedFilename(), bounds }, null, 2)+';\n');
  console.log('Verified original, unsubmitted edit, rebuilt rows and downloaded UTF-8 text.\n'+exported);
} finally {
  await browser.close();
  rmSync(temp, { recursive: true, force: true });
}
