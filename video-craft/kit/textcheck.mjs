// textcheck.mjs — for every visible caption block, measure its box and the smallest font size; flag anything outside the margins.
// usage: node textcheck.mjs <page.html> [--margin 80] [--sel '#caps .cap']
// A caption block is checked once its lines have finished rising (span transform translateY(0%)).
import { resolve } from 'node:path';
import { launch, FFMPEG } from './env.mjs';
const [pg, ...rest] = process.argv.slice(2);
const opt = (k, d) => { const i = rest.indexOf('--' + k); return i >= 0 ? rest[i + 1] : d; };
const margin = +opt('margin', '80'), sel = opt('sel', '#caps .cap');
const b = await launch();
const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
await p.goto('file://' + resolve(pg)); await p.waitForFunction(() => window.__video);
const v = await p.evaluate(() => window.__video); await p.setViewportSize({ width: v.width, height: v.height });
const issues = [];
for (let t = 0; t < v.duration; t += 0.25) {
  await p.evaluate((t) => window.__seek(t), t);
  const r = await p.evaluate(({ W, H, m, sel }) => [...document.querySelectorAll(sel)].filter((e) => e.style.display !== 'none' && [...e.querySelectorAll('.ln span')].every((s) => /translateY\(0(\.0)?%\)/.test(s.style.transform || 'translateY(0%)'))).map((e) => {
    const spans = [...e.querySelectorAll('.ln span')];
    const rs = spans.map((s) => s.getBoundingClientRect());
    const box = { l: Math.min(...rs.map((x) => x.left)), r: Math.max(...rs.map((x) => x.right)), t: Math.min(...rs.map((x) => x.top)), b: Math.max(...rs.map((x) => x.bottom)) };
    const fs = Math.min(...spans.map((s) => parseFloat(getComputedStyle(s).fontSize)));
    const out = box.l < m || box.r > W - m || box.t < m * 0.6 || box.b > H - m * 0.6;
    return { text: e.textContent.slice(0, 16), box, fs, out };
  }), { W: v.width, H: v.height, m: margin, sel });
  for (const x of r) if (x.out || x.fs < v.height / 30) issues.push({ t: +t.toFixed(2), ...x });
}
const uniq = new Map(); for (const i of issues) if (!uniq.has(i.text)) uniq.set(i.text, i);
console.log(uniq.size ? [...uniq.values()].map((i) => `${i.t}s "${i.text}" box=${JSON.stringify(Object.fromEntries(Object.entries(i.box).map(([k, v]) => [k, Math.round(v)])))} font=${i.fs}`).join('\n') : 'no caption outside margins; all fonts ≥ H/30');
await b.close();
