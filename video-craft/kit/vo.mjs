// vo.mjs — measure voice-over clips so the scene can be timed from the real audio.
// usage: node vo.mjs <clip-folder> <out.js>
// Writes `export default { "01-hook": 2.84, ... }` (seconds). Import it in scene.js and build the timeline from it.
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { launch } from './env.mjs';
const [dir, out] = process.argv.slice(2);
const files = readdirSync(dir).filter((f) => /\.(wav|mp3|ogg|opus|webm|m4a|flac)$/i.test(f)).sort();
const b = await launch(), p = await b.newPage();
const durs = {};
for (const f of files) {
  durs[f.replace(/\.[^.]+$/, '')] = await p.evaluate(async (b64) => {
    const bin = atob(b64), u8 = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    const a = await new OfflineAudioContext(2, 48000, 48000).decodeAudioData(u8.buffer);
    return +a.duration.toFixed(3);
  }, readFileSync(join(dir, f)).toString('base64'));
}
writeFileSync(out, `// voice-over clip lengths in seconds, measured by vo.mjs\nexport default ${JSON.stringify(durs, null, 2)};\n`);
console.log(JSON.stringify(durs));
await b.close();
