// render.mjs — drive a seekable page in headless Chromium.
// usage:
//   node render.mjs <page.html> stills <outdir> <t1> <t2> ...         full-res PNG per time
//   node render.mjs <page.html> sheet <out.jpg> [--every 1] [--cols 8] [--w 220] [--from a] [--to b] [--times a,b,c]
//   node render.mjs <page.html> strip <out.jpg> --at t1,t2 [--offsets -10,-4,-1,0,1,4,10] [--w 200]
//   node render.mjs <page.html> video <out.webm|out.mp4> [--from a] [--to b] [--crf n] [--audio track.webm] [--mux out-av.webm]
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';

import { launch, FFMPEG } from './env.mjs';

const argv = process.argv.slice(2);
const [pagePath, mode, target, ...rest] = argv;
const opt = (k, d) => { const i = rest.indexOf('--' + k); return i >= 0 ? rest[i + 1] : d; };
const positional = rest.filter((x, i) => !x.startsWith('--') && !(i > 0 && rest[i - 1].startsWith('--')));

const browser = await launch();

async function openPage() {
  const page = await browser.newPage({ viewport: { width: 400, height: 400 } });
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.error('[page]', m.text()); });
  page.on('pageerror', (e) => console.error('[pageerror]', e.message));
  await page.goto('file://' + resolve(pagePath));
  await page.waitForFunction(() => window.__video, null, { timeout: 60000 });
  const v = await page.evaluate(() => window.__video);
  await page.setViewportSize({ width: v.width, height: v.height });
  return { page, v };
}

async function shot(page, t, type = 'jpeg', quality = 90) {
  await page.evaluate((t) => window.__seek(t), t);
  return page.screenshot({ type, quality: type === 'jpeg' ? quality : undefined, animations: 'disabled' });
}

async function sheet(images, labels, out, { cols = 8, w = 220, aspect = 1, title = '' } = {}) {
  const h = Math.round(w * aspect);
  const p = await browser.newPage({ viewport: { width: cols * (w + 8) + 16, height: 400 } });
  const cells = images.map((b, i) => `<figure><img src="data:image/jpeg;base64,${b.toString('base64')}"><figcaption>${labels[i]}</figcaption></figure>`).join('');
  await p.setContent(`<style>body{margin:0;padding:8px;background:#111;font:12px/1.2 monospace;color:#ccc}
  h1{font:600 14px sans-serif;color:#eee;margin:0 0 6px}
  .g{display:grid;grid-template-columns:repeat(${cols},${w}px);gap:8px}
  figure{margin:0} img{width:${w}px;height:${h}px;display:block;object-fit:cover;border:1px solid #333}
  figcaption{padding-top:2px}</style><h1>${title}</h1><div class="g">${cells}</div>`);
  await p.waitForFunction(() => [...document.images].every((i) => i.complete));
  const H = await p.evaluate(() => document.body.scrollHeight);
  await p.setViewportSize({ width: cols * (w + 8) + 16, height: H });
  await p.screenshot({ path: out, type: 'jpeg', quality: 82, fullPage: true });
  await p.close();
}

const fmt = (t) => t.toFixed(2);
const { page, v } = await openPage();
const aspect = v.height / v.width;

if (mode === 'stills') {
  mkdirSync(target, { recursive: true });
  for (const s of positional) {
    const t = parseFloat(s);
    await page.evaluate((t) => window.__seek(t), t);
    await page.screenshot({ path: `${target}/t${fmt(t).padStart(6, '0')}.png`, type: 'png' });
  }
  console.log('stills', positional.length, '→', target);
} else if (mode === 'sheet') {
  const every = parseFloat(opt('every', '1'));
  const from = parseFloat(opt('from', '0')), to = parseFloat(opt('to', String(v.duration - 1 / v.fps)));
  const times = opt('times') ? opt('times').split(',').map(Number) : [];
  if (!times.length) for (let t = from; t <= to + 1e-6; t += every) times.push(+t.toFixed(4));
  const imgs = [];
  for (const t of times) imgs.push(await shot(page, t, 'jpeg', 80));
  mkdirSync(dirname(resolve(target)), { recursive: true });
  await sheet(imgs, times.map((t) => 't=' + fmt(t)), target, { cols: +opt('cols', aspect > 1 ? 8 : 5), w: +opt('w', aspect > 1 ? 200 : 340), aspect, title: opt('title', pagePath) });
  console.log('sheet', times.length, '→', target);
} else if (mode === 'strip') {
  const at = opt('at').split(',').map(Number);
  const offs = opt('offsets', '-10,-4,-1,0,1,4,10').split(',').map(Number);
  const imgs = [], labels = [];
  for (const a of at) for (const o of offs) {
    const t = Math.max(0, a + o / v.fps);
    imgs.push(await shot(page, t, 'jpeg', 80)); labels.push(`${fmt(a)} ${o >= 0 ? '+' : ''}${o}f`);
  }
  await sheet(imgs, labels, target, { cols: offs.length, w: +opt('w', aspect > 1 ? 220 : 150), aspect, title: 'cut strips' });
  console.log('strip', imgs.length, '→', target);
} else if (mode === 'video') {
  const from = parseFloat(opt('from', '0')), to = parseFloat(opt('to', String(v.duration)));
  const n = Math.round((to - from) * v.fps);
  mkdirSync(dirname(resolve(target)), { recursive: true });
  // .webm → VP9 (works with minimal ffmpeg builds); .mp4 → H.264 (needs libx264)
  const codec = target.endsWith('.mp4')
    ? ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', opt('crf', '18'), '-preset', 'medium', '-movflags', '+faststart']
    : ['-c:v', 'libvpx-vp9', '-pix_fmt', 'yuv420p', '-b:v', '0', '-crf', opt('crf', '30'), '-row-mt', '1', '-deadline', 'good', '-cpu-used', '4', '-g', '60'];
  const ff = spawn(FFMPEG, ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(v.fps), '-i', 'pipe:0', ...codec, target], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((r, j) => ff.on('close', (c) => (c === 0 ? r() : j(new Error('ffmpeg ' + c)))));
  const t0 = Date.now();
  for (let i = 0; i < n; i++) {
    const buf = await shot(page, from + i / v.fps, 'jpeg', 94);
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (i % 150 === 0) process.stderr.write(`frame ${i}/${n} ${((Date.now() - t0) / 1000).toFixed(0)}s\n`);
  }
  ff.stdin.end();
  await done;
  console.log('video', n, 'frames →', target, ((Date.now() - t0) / 1000).toFixed(0) + 's');
  if (opt('audio')) {
    const muxed = opt('mux', target.replace(/\.(webm|mp4)$/, '-av.$1'));
    const acodec = muxed.endsWith('.mp4') ? ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k'] : ['-c', 'copy'];
    await new Promise((r, j) => spawn(FFMPEG, ['-y', '-loglevel', 'error', '-i', target, '-i', opt('audio'), '-map', '0:v', '-map', '1:a', ...acodec, '-shortest', muxed], { stdio: 'inherit' }).on('close', (c) => (c === 0 ? r() : j(new Error('mux ' + c)))));
    console.log('muxed →', muxed);
  }
}
await browser.close();
