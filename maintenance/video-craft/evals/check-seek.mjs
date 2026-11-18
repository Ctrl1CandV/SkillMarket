// Compare composited screenshots, including DOM overlays, after out-of-order seeks.
import assert from 'node:assert/strict';
import { readdirSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { launch } from '../../../video-craft/kit/env.mjs';

const examples = fileURLToPath(new URL('../../../video-craft/examples/', import.meta.url));
const names = process.argv.length > 2 ? process.argv.slice(2) :
  readdirSync(examples, { withFileTypes: true }).filter((f) => f.isDirectory()).map((f) => f.name);
const browser = await launch();
try {
  for (const name of names) {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto(pathToFileURL(join(examples, name, 'index.html')).href);
    await page.waitForFunction(() => window.__video);
    const { duration, fps, width, height } = await page.evaluate(() => window.__video);
    await page.setViewportSize({ width, height });
    // Start both passes with the same layout; a viewport resize can re-rasterize gradients.
    await page.reload();
    await page.waitForFunction(() => window.__video);
    await page.evaluate(() => document.fonts.ready.then(() => true));
    const frames = [0, 0.1, 0.25, 0.51, 0.75, 0.91, 1].map((fraction) =>
      Math.round((Math.round(duration * fps) - 1) * fraction));
    async function snapshot(frame) {
      await page.evaluate((t) => window.__seek(t), frame / fps);
      return page.screenshot({ animations: 'disabled' });
    }
    const forward = new Map();
    for (const frame of frames) forward.set(frame, await snapshot(frame));
    for (const frame of frames.reverse()) {
      const before = forward.get(frame), after = await snapshot(frame);
      if (before.equals(after)) continue;
      // The GPU compositor can round antialiased edges one level differently after a repaint.
      const maxDelta = await page.evaluate(async (encoded) => {
        async function pixels(base64) {
          const data = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
          const bitmap = await createImageBitmap(new Blob([data], { type: 'image/png' }));
          const ctx = new OffscreenCanvas(bitmap.width, bitmap.height).getContext('2d');
          ctx.drawImage(bitmap, 0, 0);
          return ctx.getImageData(0, 0, bitmap.width, bitmap.height).data;
        }
        const [a, b] = await Promise.all(encoded.map(pixels));
        let max = 0;
        for (let i = 0; i < a.length; i++) max = Math.max(max, Math.abs(a[i] - b[i]));
        return max;
      }, [before, after].map((png) => png.toString('base64')));
      assert(maxDelta <= 1, `${name} frame ${frame} differs by ${maxDelta} after reverse seek`);
    }
    assert.deepEqual(errors, []);
    await page.close();
    console.log(`${name}: ${forward.size} composited frames match after reverse seeks (RGB tolerance 1/255)`);
  }
} finally {
  await browser.close();
}
