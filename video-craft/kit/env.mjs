// env.mjs — find the tools the kit needs. Override with environment variables when the defaults do not fit:
//   VC_NODE_MODULES  a folder whose node_modules contains playwright-core (or playwright); default: current folder, then the kit folder
//   VC_CHROME        a Chromium / chrome-headless-shell executable; default: the browser Playwright installed
//   VC_FFMPEG        ffmpeg executable; default: ffmpeg on PATH
import { createRequire } from 'node:module';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
function load(name) {
  for (const base of [process.env.VC_NODE_MODULES, process.cwd(), here].filter(Boolean)) {
    try { return createRequire(join(resolve(base), 'noop.js'))(name); } catch { /* try the next place */ }
  }
  return null;
}
const pw = load('playwright-core') || load('playwright');
if (!pw) {
  console.error('video-craft kit: playwright-core not found. Run `npm i -D playwright-core` in your project (and `npx playwright install chromium` if no browser is installed), or set VC_NODE_MODULES.');
  process.exit(2);
}
export const chromium = pw.chromium;
export const FFMPEG = process.env.VC_FFMPEG || 'ffmpeg';
export const launch = (extra = []) => chromium.launch({
  executablePath: process.env.VC_CHROME || undefined,
  args: ['--allow-file-access-from-files', '--autoplay-policy=no-user-gesture-required', '--font-render-hinting=none', '--disable-lcd-text', ...extra],
});
export const fileUrl = (p) => 'file://' + resolve(p);
