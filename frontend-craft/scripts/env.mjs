// env.mjs — find a browser for the page checks. Nothing is installed from here.
//   FC_NODE_MODULES  a folder whose node_modules contains playwright-core (or playwright); default: current folder, then this folder
//   FC_CHROME        a Chrome / Chromium executable; default: Playwright's own browser, then the Chrome or Edge installed on the machine
import { createRequire } from 'node:module';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import fs from 'node:fs';

const here = dirname(fileURLToPath(import.meta.url));
function load(name) {
  for (const base of [process.env.FC_NODE_MODULES, process.cwd(), here].filter(Boolean)) {
    const root = resolve(base);
    for (const dir of [root, dirname(root)]) { try { return createRequire(join(dir, 'noop.js'))(name); } catch { /* try the next place */ } }
  }
  return null;
}
const pw = load('playwright-core') || load('playwright');
if (!pw) {
  console.error('frontend-craft scripts: playwright-core not found. Ask before installing anything. Either run `npm i -D playwright-core` in the project, '
    + 'or set FC_NODE_MODULES to a folder that already has it. Without it, review the page by opening it in a browser and taking screenshots by hand.');
  process.exit(2);
}

export async function launch() {
  const tries = process.env.FC_CHROME ? [{ executablePath: process.env.FC_CHROME }] : [{}, { channel: 'chrome' }, { channel: 'msedge' }];
  let last;
  for (const how of tries) { try { return await pw.chromium.launch({ headless: true, ...how }); } catch (err) { last = err; } }
  console.error('frontend-craft scripts: no browser could be started. Set FC_CHROME to a Chrome or Chromium executable. (' + String(last && last.message).split('\n')[0] + ')');
  process.exit(2);
}

// A local file path, or a URL, as something page.goto() accepts.
export function target(input, query = '') {
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(input)) return input + query;
  const file = resolve(input);
  if (!fs.existsSync(file)) { console.error('not found: ' + file); process.exit(2); }
  return pathToFileURL(file).href + query;
}

// Open one page at one size. Phones (narrower than 700 px) get touch and a mobile viewport.
export async function open(browser, input, { width = 1440, height = 900, query = '' } = {}) {
  const mobile = width < 700;
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1, isMobile: mobile, hasTouch: mobile });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e.message).slice(0, 200)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  await page.goto(target(input, query), { waitUntil: 'load' });
  await page.waitForTimeout(400);
  return { page, context, errors, mobile };
}
