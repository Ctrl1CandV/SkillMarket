// montage.mjs — put several images side by side at a reduced size (for reviewing full frames cheaply)
// usage: node montage.mjs out.jpg width img1 img2 ...
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';
import { launch, FFMPEG } from './env.mjs';
const [out, w, ...imgs] = process.argv.slice(2);
const b = await launch();
const p = await b.newPage({ viewport: { width: 400, height: 400 } });
const tags = imgs.map((f) => `<figure><img src="data:image/${f.endsWith('png') ? 'png' : 'jpeg'};base64,${readFileSync(f).toString('base64')}"><figcaption>${basename(f)}</figcaption></figure>`).join('');
await p.setContent(`<style>body{margin:0;padding:8px;background:#222;display:flex;gap:8px;align-items:flex-start;width:max-content}figure{margin:0;color:#ccc;font:13px monospace}img{width:${w}px;display:block}</style>${tags}`);
await p.waitForFunction(() => [...document.images].every((i) => i.complete));
const box = await p.evaluate(() => [document.body.scrollWidth, document.body.scrollHeight]);
await p.setViewportSize({ width: box[0], height: box[1] });
await p.screenshot({ path: out, type: 'jpeg', quality: 85 });
await b.close();
