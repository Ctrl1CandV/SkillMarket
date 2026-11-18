// Cut between two named musical events in the bundled, full-length audiovisual preview.
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync, rmdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { cues } from './song.mjs';

const names = {
  '纸开始折起': 'fold', '飞过旧街角': 'launch', '第一次飞呀': 'hook',
  '第二次飞呀': 'secondCall', '手伸入画面': 'land', '落在掌心': 'palm',
};

function excerpt(args) {
  if (args.length !== 3 && args.length !== 4) {
    throw new Error('usage: node excerpt.mjs <startCue> <endCue> [extraSeconds] out.mp4');
  }
  const [startCue, endCue] = args.slice(0, 2).map(name => Object.hasOwn(names, name) ? names[name] : name);
  const extra = args.length === 4 ? Number(args[2]) : 0;
  for (const name of [startCue, endCue]) {
    if (!Object.hasOwn(cues, name)) throw new Error('available cues: ' + Object.entries(names).map(pair => pair.join('/')).join(', '));
  }
  if (cues[endCue] <= cues[startCue]) throw new Error('the end cue must follow the start cue');
  if (!Number.isFinite(extra) || extra < 0) throw new Error('extraSeconds must be nonnegative');

  const source = fileURLToPath(new URL('./preview.mp4', import.meta.url));
  const ffmpeg = process.env.VC_FFMPEG || 'ffmpeg';
  const probe = process.env.VC_FFPROBE || join(dirname(ffmpeg), basename(ffmpeg).replace(/^ffmpeg/i, 'ffprobe'));
  const info = JSON.parse(execFileSync(probe, ['-v', 'error', '-select_streams', 'v:0',
    '-show_entries', 'stream=width,height,avg_frame_rate,duration', '-of', 'json', source], { encoding:'utf8' }));
  const { width, height, avg_frame_rate, duration } = info.streams[0];
  const [num, den] = avg_frame_rate.split('/').map(Number);
  const start = cues[startCue], end = cues[endCue] + extra;
  if (!Number.isFinite(Number(duration)) || end > Number(duration)) {
    throw new Error(`requested end ${end.toFixed(3)}s; preview duration is ${duration}s`);
  }

  const scratch = mkdtempSync(join(tmpdir(), 'sung-mv-'));
  const manifest = join(scratch, 'cut.json');
  try {
    writeFileSync(manifest, JSON.stringify({ width, height, fps:num/den,
      shots:[{ video: source, in: start, duration: end-start, sound: true }] }));
    const cut = fileURLToPath(new URL('../../kit/cut.mjs', import.meta.url));
    execFileSync(process.execPath, [cut, manifest, resolve(args.at(-1))], { stdio:'inherit' });
    console.log(`${startCue} → ${endCue} + ${extra}s: ${start.toFixed(2)}–${end.toFixed(2)} s`);
  } finally {
    rmSync(manifest, { force:true });
    rmdirSync(scratch);
  }
}

try { excerpt(process.argv.slice(2)); }
catch (error) { console.error(error.message); process.exitCode = 1; }
