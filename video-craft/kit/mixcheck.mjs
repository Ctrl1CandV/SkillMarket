// mixcheck.mjs — plot momentary loudness of the music stem, the effects stem and the mix, with scene events.
// Reading it: effects should rise clearly above the music at their events; the mix should have no holes or walls.
// usage: node mixcheck.mjs <scene.html> <score.html> <out.png> [--from 0] [--to dur] [--vo voice-clip-folder]
import { resolve, join } from 'node:path';
import { readFileSync, readdirSync } from 'node:fs';
import { launch, FFMPEG } from './env.mjs';
const [scene, score, out, ...rest] = process.argv.slice(2);
const opt = (k, d) => { const i = rest.indexOf('--' + k); return i >= 0 ? rest[i + 1] : d; };
const voDir = opt('vo');
const vo = voDir ? Object.fromEntries(readdirSync(voDir).filter((f) => /\.(wav|mp3|ogg|opus|webm|m4a|flac)$/i.test(f)).map((f) => [f.replace(/\.[^.]+$/, ''), readFileSync(join(voDir, f)).toString('base64')])) : {};
const b = await launch();
const p1 = await b.newPage(); await p1.goto('file://' + resolve(scene)); await p1.waitForFunction(() => window.__video);
const { duration, meta } = await p1.evaluate(() => window.__video);
const p2 = await b.newPage({ viewport: { width: 1840, height: 560 } });
p2.on('pageerror', (e) => console.error('[score]', e.message));
await p2.goto('file://' + resolve(score)); await p2.waitForFunction(() => window.__mixcheck);
const curves = await p2.evaluate(([ev, d, vo]) => window.__mixcheck(ev, d, { vo }), [meta.events || [], duration, vo]);
const from = +opt('from', '0'), to = +opt('to', String(duration));
await p2.evaluate(([c, events, from, to]) => {
  const W = 1800, H = 520, cv = document.createElement('canvas'); cv.width = W + 40; cv.height = H + 40; document.body.style.margin = 0; document.body.appendChild(cv);
  const g = cv.getContext('2d'); g.fillStyle = '#111'; g.fillRect(0, 0, cv.width, cv.height);
  const x0 = 30, tx = (t) => x0 + ((t - from) / (to - from)) * W, ly = (l) => 20 + ((-10 - l) / 50) * H;
  g.font = '12px monospace'; g.strokeStyle = '#333'; g.fillStyle = '#888';
  for (let l = -10; l >= -60; l -= 10) { g.beginPath(); g.moveTo(x0, ly(l)); g.lineTo(x0 + W, ly(l)); g.stroke(); g.fillText(String(l), 2, ly(l) + 4); }
  for (let s = Math.ceil(from); s <= to; s++) { g.fillText(String(s), tx(s) - 4, H + 36); }
  let k = 0;
  for (const e of events) { if (e.t < from || e.t > to) continue; g.strokeStyle = 'rgba(255,255,255,0.18)'; g.beginPath(); g.moveTo(tx(e.t), 20); g.lineTo(tx(e.t), 20 + H); g.stroke(); g.save(); g.translate(tx(e.t) + 3, 30 + (k++ % 6) * 12); g.fillStyle = 'rgba(255,255,255,0.55)'; g.fillText(e.type, 0, 0); g.restore(); }
  for (const [name, col] of [['music', '#6fa8ff'], ['sfx', '#ffb35c'], ['voice', '#7be08a'], ['mix', '#e8e8e8']]) {
    if (!c[name]) continue;
    g.strokeStyle = col; g.lineWidth = name === 'mix' ? 1.2 : 2; g.beginPath();
    c[name].forEach((l, i) => { const t = i * 0.1 + 0.2; if (t < from || t > to) return; const y = ly(Math.max(-60, l)); i ? g.lineTo(tx(t), y) : g.moveTo(tx(t), y); }); g.stroke();
  }
  g.fillStyle = '#6fa8ff'; g.fillText('music', x0 + 10, H + 16); g.fillStyle = '#ffb35c'; g.fillText('sfx', x0 + 70, H + 16); g.fillStyle = '#7be08a'; if (c.voice) g.fillText('voice', x0 + 110, H + 16); g.fillStyle = '#e8e8e8'; g.fillText('mix (raw, before normalising)', x0 + 170, H + 16);
}, [curves, meta.events || [], from, to]);
await p2.locator('canvas').screenshot({ path: out });
console.log('mixcheck →', out);
await b.close();
