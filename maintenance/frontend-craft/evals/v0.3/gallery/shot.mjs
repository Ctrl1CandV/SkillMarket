// Usage: node shot.mjs <html-file> <out-dir>
// Writes desktop-top.png, desktop-full.png (1280 wide) and mobile-top.png, mobile-full.png (390 wide),
// then prints page height and the font families actually used for rendering.
import { chromium } from 'playwright-core';
import { pathToFileURL } from 'node:url';
import { readdirSync, mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';

const [, , html, outDir] = process.argv;
if (!html || !outDir) {
  console.error('usage: shot.sh <html-file> <out-dir>');
  process.exit(2);
}
mkdirSync(outDir, { recursive: true });
const cache = join(process.env.HOME, '.cache/ms-playwright');
const shell = readdirSync(cache).find((d) => d.startsWith('chromium_headless_shell-'));
const executablePath = join(cache, shell, 'chrome-linux/headless_shell');

const views = [
  { name: 'desktop', width: 1280, height: 800 },
  { name: 'mobile', width: 390, height: 844 },
];
const browser = await chromium.launch({ executablePath, args: ['--font-render-hinting=none'] });
for (const v of views) {
  const page = await browser.newPage({ viewport: { width: v.width, height: v.height } });
  await page.goto(pathToFileURL(resolve(html)).href);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: join(outDir, `${v.name}-top.png`) });
  await page.screenshot({ path: join(outDir, `${v.name}-full.png`), fullPage: true });
  const info = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    height: document.documentElement.scrollHeight,
  }));
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('DOM.enable');
  await cdp.send('CSS.enable');
  const { root } = await cdp.send('DOM.getDocument', { depth: -1 });
  const fonts = new Map();
  for (const sel of ['h1', 'h2', 'p', 'li', 'button', 'td', 'a']) {
    const { nodeId } = await cdp.send('DOM.querySelector', { nodeId: root.nodeId, selector: sel });
    if (!nodeId) continue;
    const { fonts: pf } = await cdp.send('CSS.getPlatformFontsForNode', { nodeId });
    for (const f of pf) fonts.set(f.familyName, (fonts.get(f.familyName) || 0) + f.glyphCount);
  }
  console.log(`${v.name} ${v.width}px: height=${info.height} scrollWidth=${info.scrollWidth} renderedFonts=${JSON.stringify(Object.fromEntries(fonts))}`);
  await page.close();
}
await browser.close();
console.log(`screenshots in ${resolve(outDir)}`);
