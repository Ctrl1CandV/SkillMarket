// audio.mjs — render the soundtrack for a scene: events come from the scene page, synthesis runs in the score page.
// Pass '-' as <score.html> for clean narration-led tracks (course/problem-solving): places meta.cues [{id, t0, t1, text}]
// onto the voice bus with optional subtle cue chimes in meta.chimes [{t, freq, gain}], and exports soft subtitles with --srt.
// usage:
//   node audio.mjs <scene.html> <score.html|-> <out.webm> [--wav out.wav] [--srt out.srt] [--target -16] [--vo voice-clip-folder] [--stems]
import { mkdirSync, writeFileSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { launch, fileUrl } from './env.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const [scene, score, out, ...rest] = process.argv.slice(2);
const opt = (k, d) => { const i = rest.indexOf('--' + k); return i >= 0 ? rest[i + 1] : d; };
const voDir = opt('vo');
const vo = voDir ? Object.fromEntries(readdirSync(voDir).filter((f) => /\.(wav|mp3|ogg|opus|webm|m4a|flac)$/i.test(f)).map((f) => [f.replace(/\.[^.]+$/, ''), readFileSync(join(voDir, f)).toString('base64')])) : {};

function fmtSrtTime(sec) {
  const ms = Math.max(0, Math.round(sec * 1000));
  const h = Math.floor(ms / 3600000), m = Math.floor((ms % 3600000) / 60000), s = Math.floor((ms % 60000) / 1000), f = ms % 1000;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(f).padStart(3, '0')}`;
}

const b = await launch();
const p1 = await b.newPage();
p1.on('pageerror', (e) => console.error('[scene]', e.message));
await p1.goto(fileUrl(scene));
await p1.waitForFunction(() => window.__video);
const { duration, meta } = await p1.evaluate(() => window.__video);

const srtOut = opt('srt');
if (srtOut && Array.isArray(meta?.cues) && meta.cues.length) {
  const blocks = meta.cues
    .filter((c) => c && c.text && Number.isFinite(c.t0) && Number.isFinite(c.t1) && c.t1 > c.t0)
    .map((c, idx) => `${idx + 1}\n${fmtSrtTime(c.t0)} --> ${fmtSrtTime(c.t1)}\n${String(c.text).trim()}\n`);
  mkdirSync(dirname(resolve(srtOut)), { recursive: true });
  writeFileSync(srtOut, blocks.join('\n'), 'utf8');
}

const p2 = await b.newPage();
p2.on('pageerror', (e) => console.error('[score]', e.message));
p2.on('console', (m) => console.error('[score]', m.text()));

if (score === '-') {
  const soundUrl = fileUrl(join(here, 'sound.js'));
  await p2.goto(fileUrl(scene));
  await p2.setContent(`<script type="module">
    import { install, voice, NOTE, chime, tick, pop, pluck, thud, whoosh, glide } from ${JSON.stringify(soundUrl)};
    const freqOf = (x, fallback = 660) => typeof x === 'string' ? NOTE(x) : (Number.isFinite(x) ? x : fallback);
    install((m, events, dur) => {
      const cues = ${JSON.stringify(meta?.cues || [])};
      const chimes = ${JSON.stringify(meta?.chimes || [])};
      const sfxList = [...(${JSON.stringify(meta?.sfx || [])}), ...(${JSON.stringify(meta?.events || [])})];
      for (const c of cues) if (c && c.id != null && Number.isFinite(c.t0)) voice(m, c.t0, c.id);
      for (const ch of chimes) if (ch && Number.isFinite(ch.t)) chime(m, m.sfx, ch.t, freqOf(ch.note ?? ch.freq, 660), { gain: ch.gain ?? 0.035, dur: ch.dur ?? 0.9, pan: ch.pan ?? 0 });
      for (const e of sfxList) {
        if (!e || !Number.isFinite(e.t) || e.t < 0 || e.t >= dur) continue;
        const k = e.kind || e.type;
        if (k === 'tick') tick(m, m.sfx, e.t, { freq: e.freq ?? 2100, gain: e.gain ?? 0.024, dur: e.dur ?? 0.032, pan: e.pan ?? 0 });
        else if (k === 'pop') pop(m, m.sfx, e.t, { f0: e.f0 ?? 340, f1: e.f1 ?? 920, gain: e.gain ?? 0.045, dur: e.dur ?? 0.08, pan: e.pan ?? 0 });
        else if (k === 'pluck') pluck(m, m.sfx, e.t, freqOf(e.note ?? e.freq, 659.25), { gain: e.gain ?? 0.045, dur: e.dur ?? 0.55, pan: e.pan ?? 0 });
        else if (k === 'chime') chime(m, m.sfx, e.t, freqOf(e.note ?? e.freq, 783.99), { gain: e.gain ?? 0.038, dur: e.dur ?? 1.1, pan: e.pan ?? 0 });
        else if (k === 'thud') thud(m, m.sfx, e.t, { freq: e.freq ?? 92, gain: e.gain ?? 0.14, dur: e.dur ?? 0.24, pan: e.pan ?? 0 });
        else if (k === 'whoosh') whoosh(m, m.sfx, e.t, { dur: e.dur ?? 0.62, f0: e.f0 ?? 360, f1: e.f1 ?? 1600, gain: e.gain ?? 0.042, pan0: e.pan0 ?? 0, pan1: e.pan1 ?? 0 });
        else if (k === 'glide') glide(m, m.sfx, e.t, e.f0 ?? 280, e.f1 ?? 85, { dur: e.dur ?? 0.65, gain: e.gain ?? 0.042 });
      }
    }, { reverb: 0.06, irSec: 1.0 });
  </script>`);
} else {
  await p2.goto(fileUrl(score));
}
await p2.waitForFunction(() => window.__renderAudio);
if (rest.includes('--stems')) { console.log('stems', JSON.stringify(await p2.evaluate(([ev, d, vo]) => window.__stems(ev, d, { vo }), [meta.events || [], duration, vo]))); }
const t0 = Date.now();
const r = await p2.evaluate(([ev, d, o]) => window.__renderAudio(ev, d, o), [meta.events || [], duration, { wav: !!opt('wav'), target: +opt('target', '-16'), vo }]);
mkdirSync(dirname(resolve(out)), { recursive: true });
writeFileSync(out, Buffer.from(r.webm, 'base64'));
if (r.wav) {
  mkdirSync(dirname(resolve(opt('wav'))), { recursive: true });
  writeFileSync(opt('wav'), Buffer.from(r.wav, 'base64'));
}
console.log(JSON.stringify({ out, srt: srtOut || undefined, events: (meta.events || []).length, cues: (meta.cues || []).length, rawLufs: +r.raw.lufs.toFixed(1), rawPeak: +r.raw.peak.toFixed(1), gainDb: +(20 * Math.log10(r.gain)).toFixed(1), lufs: +r.lufs.toFixed(1), peak: +r.peak.toFixed(1), secs: +((Date.now() - t0) / 1000).toFixed(2) }));
await b.close();
