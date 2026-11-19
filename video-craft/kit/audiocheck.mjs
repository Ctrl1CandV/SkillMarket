// audiocheck.mjs — decode an audio/video file in the browser and draw its envelope + spectrogram with scene events on top.
// usage: node audiocheck.mjs <media> <scene.html> <out.png> [--from 0] [--to 42] [--scene-offset 8]

import { readFileSync } from 'node:fs';
import { launch, fileUrl } from './env.mjs';
const [media, scene, out, ...rest] = process.argv.slice(2);
const opt = (k, d) => { const i = rest.indexOf('--' + k); return i >= 0 ? rest[i + 1] : d; };
const b = await launch();
const p1 = await b.newPage();
await p1.goto(fileUrl(scene));
await p1.waitForFunction(() => window.__video);
const { meta } = await p1.evaluate(() => window.__video);
const p = await b.newPage({ viewport: { width: 1800, height: 640 } });
p.on('console', (m) => console.log('[page]', m.text()));
// Decoding the delivered soundtrack needs no score page (e.g. an existing song).
const stats = await p.evaluate(async ([b64, events, from, end, offset]) => {
  const bin = atob(b64), u8 = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  const buf = u8.buffer;
  const ac = new OfflineAudioContext(2, 48000, 48000);
  const a = await ac.decodeAudioData(buf);
  const to = Math.min(end ?? a.duration, a.duration);
  if (!(from >= 0 && from < to) || !Number.isFinite(offset)) throw new Error('Invalid media-local time range or scene offset');
  const sr = a.sampleRate, L = a.getChannelData(0), R = a.numberOfChannels > 1 ? a.getChannelData(1) : L;
  const W = 1760, H = 600, cv = document.createElement('canvas'); cv.width = W + 40; cv.height = H + 40; document.body.appendChild(cv);
  const g = cv.getContext('2d'); g.fillStyle = '#111'; g.fillRect(0, 0, cv.width, cv.height);
  const x0 = 20, tx = (t) => x0 + ((t - from) / (to - from)) * W;
  // spectrogram (naive DFT on 1024-sample frames, 48 log bins)
  const N = 1024, bins = 48, cols = W / 2, top = 20, sh = 300;
  for (let c = 0; c < cols; c++) {
    const t = from + (c / cols) * (to - from), s0 = Math.floor(t * sr);
    if (s0 + N >= L.length) break;
    for (let k = 0; k < bins; k++) {
      const f = 40 * Math.pow(16000 / 40, k / (bins - 1)), w = (2 * Math.PI * f) / sr;
      let re = 0, im = 0;
      for (let n = 0; n < N; n += 2) { const v = (L[s0 + n] + R[s0 + n]) * 0.5 * (0.5 - 0.5 * Math.cos((2 * Math.PI * n) / N)); re += v * Math.cos(w * n); im -= v * Math.sin(w * n); }
      const db = 20 * Math.log10(Math.hypot(re, im) / (N / 4) + 1e-9);
      const v = Math.max(0, Math.min(1, (db + 80) / 70));
      g.fillStyle = `hsl(${260 - v * 220},80%,${v * 60}%)`; g.fillRect(x0 + c * 2, top + sh - ((k + 1) / bins) * sh, 2, sh / bins + 1);
    }
  }
  // envelope (RMS per 20 ms, dBFS)
  const ey = top + sh + 20, eh = 200;
  g.strokeStyle = '#555'; g.beginPath(); for (const db of [0, -12, -24, -36, -48]) { const y = ey + (-db / 48) * eh; g.moveTo(x0, y); g.lineTo(x0 + W, y); } g.stroke();
  g.fillStyle = '#9fd'; const hop = Math.round(0.02 * sr); let peak = 0;
  for (let s = Math.floor(from * sr); s < Math.min(L.length, to * sr); s += hop) {
    let acc = 0; for (let i = s; i < s + hop && i < L.length; i++) { acc += L[i] * L[i] + R[i] * R[i]; peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i])); }
    const db = 10 * Math.log10(acc / (2 * hop) + 1e-12), h = Math.max(0, (1 + db / 48)) * eh;
    g.fillRect(tx(s / sr), ey + eh - h, Math.max(1, (hop / sr) / (to - from) * W), h);
  }
  // events and seconds
  const colors = {};
  let hue = 0;
  for (const e of events) { const t = e.t - offset; if (t < from || t > to) continue; colors[e.type] ??= `hsl(${(hue += 47) % 360},90%,65%)`; g.strokeStyle = colors[e.type]; g.globalAlpha = 0.8; g.beginPath(); g.moveTo(tx(t), top); g.lineTo(tx(t), ey + eh); g.stroke(); }
  g.globalAlpha = 1; g.fillStyle = '#ddd'; g.font = '12px monospace';
  for (let s = Math.ceil(from); s <= to; s++) g.fillText(String(s), tx(s) - 4, H + 34);
  let lx = x0; for (const [k, c] of Object.entries(colors)) { g.fillStyle = c; g.fillText(k, lx, 14); lx += g.measureText(k).width + 14; }
  return { decodedSeconds: a.duration, channels: a.numberOfChannels, peakDb: 20 * Math.log10(peak), sceneOffset: offset, plottedEvents: events.filter((e) => e.t - offset >= from && e.t - offset <= to).length };
}, [readFileSync(media).toString('base64'), meta.events || [], +opt('from', '0'), opt('to') === undefined ? null : +opt('to'), +opt('scene-offset', '0')]);
await p.locator('canvas').screenshot({ path: out });
console.log(JSON.stringify(stats));
await b.close();
