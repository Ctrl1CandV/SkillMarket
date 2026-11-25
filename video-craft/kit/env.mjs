// env.mjs — find the tools the kit needs. Override with environment variables when the defaults do not fit:
//   VC_NODE_MODULES  a folder whose node_modules contains playwright-core (or playwright); default: current folder, then the kit folder
//   VC_CHROME        a Chromium / chrome-headless-shell executable; default: the browser Playwright installed
//   VC_FFMPEG        ffmpeg executable; default: ffmpeg on PATH
import { existsSync, readdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const defaultLocal = process.env.LOCALAPPDATA ? join(process.env.LOCALAPPDATA, 'video-craft-kit') : null;
function load(name) {
  for (const base of [process.env.VC_NODE_MODULES, process.cwd(), here, defaultLocal].filter(Boolean)) {
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
function findBrowser() {
  if (process.env.VC_CHROME) return process.env.VC_CHROME;
  try {
    const def = chromium.executablePath();
    if (def && existsSync(def)) return undefined;
  } catch { /* fallback below */ }
  const candidates = [];
  if (process.env.LOCALAPPDATA) {
    const mspw = join(process.env.LOCALAPPDATA, 'ms-playwright');
    if (existsSync(mspw)) {
      for (const d of readdirSync(mspw).sort().reverse()) {
        candidates.push(
          join(mspw, d, 'chrome-headless-shell-win64', 'chrome-headless-shell.exe'),
          join(mspw, d, 'chrome-win64', 'chrome.exe'),
        );
      }
    }
  }
  candidates.push(
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  );
  return candidates.find((p) => existsSync(p));
}

export const launch = (extra = []) => {
  const lowGpu = process.env.VC_SOFTWARE_GL === '1';
  const gpuArgs = lowGpu ? ['--use-angle=swiftshader', '--disable-gpu-compositing'] : [];
  return chromium.launch({
    executablePath: findBrowser(),
    args: ['--allow-file-access-from-files', '--autoplay-policy=no-user-gesture-required', '--font-render-hinting=none', '--disable-lcd-text', ...gpuArgs, ...extra],
  });
};
export const fileUrl = (p) => pathToFileURL(resolve(p)).href;
