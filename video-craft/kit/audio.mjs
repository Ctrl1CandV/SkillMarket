// audio.mjs — render the soundtrack for a scene: events come from the scene page, synthesis runs in the score page.
// usage: node audio.mjs <scene.html> <score.html> <out.webm> [--wav out.wav] [--target -16] [--vo voice-clip-folder] [--stems]
import { writeFileSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { resolve } from 'node:path';
import { launch, FFMPEG } from './env.mjs';
const [scene, score, out, ...rest] = process.argv.slice(2);
const opt = (k, d) => { const i = rest.indexOf('--' + k); return i >= 0 ? rest[i + 1] : d; };
const voDir = opt('vo');
const vo = voDir ? Object.fromEntries(readdirSync(voDir).filter((f) => /\.(wav|mp3|ogg|opus|webm|m4a|flac)$/i.test(f)).map((f) => [f.replace(/\.[^.]+$/, ''), readFileSync(join(voDir, f)).toString('base64')])) : {};
const b = await launch();
const p1 = await b.newPage();
p1.on('pageerror', (e) => console.error('[scene]', e.message));
await p1.goto('file://' + resolve(scene));
await p1.waitForFunction(() => window.__video);
const { duration, meta } = await p1.evaluate(() => window.__video);
const p2 = await b.newPage();
p2.on('pageerror', (e) => console.error('[score]', e.message));
p2.on('console', (m) => console.error('[score]', m.text()));
await p2.goto('file://' + resolve(score));
await p2.waitForFunction(() => window.__renderAudio);
if (rest.includes('--stems')) { console.log('stems', JSON.stringify(await p2.evaluate(([ev, d, vo]) => window.__stems(ev, d, { vo }), [meta.events || [], duration, vo]))); }
const t0 = Date.now();
const r = await p2.evaluate(([ev, d, o]) => window.__renderAudio(ev, d, o), [meta.events || [], duration, { wav: !!opt('wav'), target: +opt('target', '-16'), vo }]);
writeFileSync(out, Buffer.from(r.webm, 'base64'));
if (r.wav) writeFileSync(opt('wav'), Buffer.from(r.wav, 'base64'));
console.log(JSON.stringify({ out, events: (meta.events || []).length, rawLufs: +r.raw.lufs.toFixed(1), rawPeak: +r.raw.peak.toFixed(1), gainDb: +(20 * Math.log10(r.gain)).toFixed(1), lufs: +r.lufs.toFixed(1), peak: +r.peak.toFixed(1), secs: (Date.now() - t0) / 1000 }));
await b.close();
