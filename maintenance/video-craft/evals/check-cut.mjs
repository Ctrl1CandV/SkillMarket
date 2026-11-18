// End-to-end test of the public edit-list CLI. ffmpeg and ffprobe must be on PATH.
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const cut = fileURLToPath(new URL('../../../video-craft/kit/cut.mjs', import.meta.url));
const dir = mkdtempSync(join(tmpdir(), 'vc cut-'));
const run = (cmd, args) => execFileSync(cmd, args, { cwd: dir, windowsHide: true });
const ff = (args) => run(process.env.VC_FFMPEG || 'ffmpeg', ['-nostdin', '-hide_banner', '-loglevel', 'error', ...args]);
const edit = join(dir, 'edit.json');
const save = (obj) => writeFileSync(edit, JSON.stringify(obj));
const render = () => run(process.execPath, [cut, edit, 'result.mp4']);
const streams = () => JSON.parse(run(process.env.VC_FFPROBE || 'ffprobe', ['-v', 'error', '-show_streams', '-of', 'json', 'result.mp4'])).streams;

try {
  ff(['-f', 'lavfi', '-i', 'color=c=red:s=40x80', '-frames:v', '1', '-update', '1', '板 #1.png']);
  ff(['-f', 'lavfi', '-i', 'color=c=blue:s=80x40:r=24:d=1', '-pix_fmt', 'yuv420p', 'blue.mp4']);
  ff(['-f', 'lavfi', '-i', 'aevalsrc=if(lt(t\\,0.5)\\,0\\,0.5*sin(2*PI*440*t)):s=48000:d=1', 'song.wav']);
  const shots = [
    { image: '板 #1.png', duration: 0.5 },
    { video: 'blue.mp4', in: 0.25, duration: 0.5 },
    { image: '板 #1.png', duration: 0.5, fit: 'cover' },
  ];
  const plan = { width: 64, height: 48, fps: 24, audio: { file: 'song.wav', in: 0.5 }, shots };
  save(plan);
  render();
  const [picture, sound] = streams();
  assert.equal(Number(picture.nb_frames), 36);
  assert.equal(Number(sound.duration), 1.5);
  const pixel = (t, x) => ff(['-ss', String(t), '-i', 'result.mp4', '-vf', `format=rgb24,crop=1:1:${x}:24`, '-frames:v', '1', '-f', 'rawvideo', '-']);
  assert(pixel(0.2, 1)[0] < 12);     // contain pillarbox
  assert(pixel(0.2, 32)[0] > 230);   // still
  assert(pixel(0.5, 32)[2] > 230);   // first frame after cut
  assert(pixel(1.2, 1)[0] > 230);    // cover fills frame
  const level = (t) => {
    const pcm = ff(['-ss', String(t), '-i', 'result.mp4', '-t', '0.1', '-vn', '-ac', '1', '-f', 's16le', '-']);
    let peak = 0;
    for (let i = 0; i < pcm.length; i += 2) peak = Math.max(peak, Math.abs(pcm.readInt16LE(i)));
    return peak;
  };
  assert(level(0.1) > 8000 && level(0.9) < 100);
  ff(['-i', 'blue.mp4', '-i', 'song.wav', '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', 'blue-av.mp4']);
  save({ ...plan, audio: null, shots: [
    shots[0], { video: 'blue-av.mp4', in: 0.5, duration: 0.5, sound: true }, shots[2],
  ] });
  render();
  assert.equal(Number(streams()[1].duration), 1.5);
  assert(level(0.2) < 100 && level(0.7) > 8000 && level(1.3) < 100);
  ff(['-f', 'lavfi', '-i', 'color=red:s=80x40:r=24:d=0.25', '-f', 'lavfi', '-i', 'color=blue:s=80x40:r=24:d=0.75',
    '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[v]', '-map', '[v]', '-c:v', 'libx264', 'change.mp4']);
  ff(['-itsoffset', '0.25', '-i', 'change.mp4', '-i', 'song.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'pcm_s16le', 'offset.mkv']);
  save({ ...plan, audio: null, shots: [{ video: 'offset.mkv', duration: 0.75, sound: true }] });
  render();
  assert(pixel(0.375, 32)[0] > 230 && pixel(0.58, 32)[2] > 230);
  assert(level(0.2) < 100 && level(0.55) > 8000);
  // An impossible cut must keep the previously delivered result intact.
  const previous = readFileSync(join(dir, 'result.mp4'));
  save({ ...plan, shots: [{ video: 'blue.mp4', in: 0.8, duration: 1 }] });
  assert.notEqual(spawnSync(process.execPath, [cut, edit, 'result.mp4'], { cwd: dir }).status, 0);
  assert.deepEqual(readFileSync(join(dir, 'result.mp4')), previous);
  save({ ...plan, audio: { file: 'song.wav', in: 10 } });
  assert.match(spawnSync(process.execPath, [cut, edit, 'result.mp4'], { cwd: dir, encoding: 'utf8' }).stderr, /No audio samples/);
  assert.deepEqual(readFileSync(join(dir, 'result.mp4')), previous);
  assert(!readdirSync(dir).some((file) => file.startsWith('.video-craft-cut-')));
  save({ ...plan, shots: [{ image: '板 #1.png', duration: 0.13 }, { image: '板 #1.png', duration: 0.13 }, { image: '板 #1.png', duration: 0.13 }], audio: null });
  render();
  const silent = streams();
  assert.equal(silent.length, 1);
  assert.equal(Number(silent[0].nb_frames), Math.round(3 * 0.13 * 24));
  save({ ...plan, audio: null, shots: [{ image: '板 #1.png', duration: 1 / 24 }, shots[1]] });
  render();
  const insert = streams()[0];
  assert.equal(Number(insert.nb_frames), 13);
  assert(Math.abs(Number(insert.duration) - 13 / 24) < 0.001);
  assert(pixel(0, 32)[0] > 230 && pixel(1 / 24, 32)[2] > 230);
  console.log('PASS: frame boundaries, fit, master in-point and tail, location audio, silent edit, cumulative rounding, retry after short source');
} finally {
  rmSync(dir, { recursive: true, force: true });
}
