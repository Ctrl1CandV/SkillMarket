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
    import { install, voice, chime } from ${JSON.stringify(soundUrl)};
    install((m, events, dur) => {
      const cues = ${JSON.stringify(meta?.cues || [])};
      const chimes = ${JSON.stringify(meta?.chimes || [])};
      for (const c of cues) if (c && c.id != null && Number.isFinite(c.t0)) voice(m, c.t0, c.id);
      for (const ch of chimes) if (ch && Number.isFinite(ch.t)) chime(m, m.sfx, ch.t, ch.freq || 660, { gain: ch.gain ?? 0.035, dur: ch.dur ?? 0.9 });
    }, { reverb: 0.04, irSec: 0.9 });
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
