import { createRequire } from 'node:module'; import path from 'node:path';
const require = createRequire(path.join(process.env.FC_NODE_MODULES, 'x.js')); const { chromium } = require('playwright-core');
for (const args of [[], ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'], ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']]) {
  const b = await chromium.launch({ executablePath: process.env.FC_CHROME, headless: true, args }); const p = await b.newPage();
  console.log(JSON.stringify(args), '->', await p.evaluate(() => { const c = document.createElement('canvas').getContext('webgl'); if (!c) return 'no webgl'; const d = c.getExtension('WEBGL_debug_renderer_info'); return d ? c.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'webgl, renderer hidden'; })); await b.close(); }
