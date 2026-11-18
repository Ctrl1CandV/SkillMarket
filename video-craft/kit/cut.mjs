// Assemble a timed picture edit from stills and rendered or recorded shots.
// node cut.mjs edit.json film.mp4  (see references/editing.md)
import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, extname, join, relative, resolve } from 'node:path';
import { checkAudioStart } from './media.mjs';

function requireNumber(value, label, min, integer = false) {
  if (!Number.isFinite(value) || value < min || (integer && !Number.isInteger(value))) {
    throw new Error(`${label} must be ${integer ? 'an integer' : 'a number'} >= ${min}`);
  }
  return value;
}

function loadEdit(manifest, output) {
  const edit = JSON.parse(readFileSync(manifest, 'utf8').replace(/^\uFEFF/, ''));
  const { width = 1280, height = 720, fps = 24 } = edit;
  for (const [label, size] of Object.entries({ width, height })) {
    requireNumber(size, label, 2, true);
    if (size % 2) throw new Error(`${label} must be even (H.264 4:2:0)`);
  }
  requireNumber(fps, 'fps', 1);
  if (!Array.isArray(edit.shots) || !edit.shots.length) throw new Error('shots must be a nonempty array');

  function mediaPath(name) {
    if (!name || typeof name !== 'string') throw new Error('expected a local media filename');
    const path = resolve(dirname(manifest), name);
    if (!relative(output, path)) throw new Error('output would replace a source file');
    if (!statSync(path).isFile()) throw new Error(`expected a file: ${path}`);
    return path;
  }

  let seconds = 0;
  let totalFrames = 0;
  const shots = edit.shots.map((shot, i) => {
    const label = `shot ${i + 1}`;
    if (Boolean(shot.image) === Boolean(shot.video)) throw new Error(`${label}: supply one image or video`);
    const path = mediaPath(shot.image ?? shot.video);
    const start = requireNumber(shot.in ?? 0, `${label}.in`, 0);
    if (shot.image && start) throw new Error(`${label}: in applies to video`);
    const fit = shot.fit ?? 'contain';
    if (!['contain', 'cover'].includes(fit)) throw new Error(`${label}: fit must be contain or cover`);
    seconds += requireNumber(shot.duration, `${label}.duration`, 0);
    const endFrame = Math.round(seconds * fps);
    const frames = endFrame - totalFrames;
    if (frames < 1) throw new Error(`${label} is shorter than one output frame`);
    totalFrames = endFrame;
    if (shot.sound !== undefined && typeof shot.sound !== 'boolean') throw new Error(`${label}.sound must be true or false`);
    if (shot.sound && (shot.image || edit.audio)) throw new Error(`${label}: sound needs a video and no separate audio master`);
    return { path, image: Boolean(shot.image), start, frames, fit, sound: shot.sound === true };
  });
  const audio = edit.audio == null ? null : {
    path: mediaPath(edit.audio.file),
    start: requireNumber(edit.audio.in ?? 0, 'audio.in', 0),
  };
  return { shots, width, height, fps, audio, totalFrames };
}

function ffmpeg(args, progress = false) {
  return execFileSync(process.env.VC_FFMPEG || 'ffmpeg', ['-nostdin', '-hide_banner', '-loglevel', 'error', ...args], {
    encoding: 'utf8', windowsHide: true, stdio: ['ignore', progress ? 'pipe' : 'ignore', 'inherit'],
  });
}

function assemble(manifest, output) {
  if (extname(output).toLowerCase() !== '.mp4') throw new Error('output must end in .mp4');
  const { shots, width, height, fps, audio, totalFrames } = loadEdit(manifest, output);
  if (audio) checkAudioStart(process.env.VC_FFMPEG || 'ffmpeg', audio.path, audio.start);
  mkdirSync(dirname(output), { recursive: true });
  const scratch = mkdtempSync(join(dirname(output), '.video-craft-cut-'));
  try {
    const list = [];
    const locationAudio = shots.some((shot) => shot.sound);
    const audioFiles = [];
    let elapsedFrames = 0;
    for (const [index, shot] of shots.entries()) {
      const name = `shot-${index}.mp4`;
      const contain = shot.fit === 'contain';
      const scale = `scale=${width}:${height}:force_original_aspect_ratio=${contain ? 'decrease' : 'increase'}:force_divisible_by=2`;
      const framing = contain ? `pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2:black` : `crop=${width}:${height}`;
      const input = shot.image ? ['-loop', '1', '-framerate', String(fps), '-pattern_type', 'none', '-f', 'image2'] : ['-ss', String(shot.start)];
      // Square pixels before fitting so anamorphic footage keeps its displayed aspect.
      const report = ffmpeg([...input, '-i', shot.path, '-map', '0:v:0', '-an',
        '-vf', `fps=${fps}:start_time=0,scale=round(iw*sar):ih,setsar=1,${scale},${framing},setsar=1`,
        '-frames:v', String(shot.frames), '-c:v', 'libx264', '-bf', '0', '-preset', 'veryfast', '-crf', '18',
        '-pix_fmt', 'yuv420p', '-stats_period', '60', '-progress', 'pipe:1', join(scratch, name)], true);
      const written = Number([...report.matchAll(/^frame=(\d+)/gm)].at(-1)?.[1]);
      if (written !== shot.frames) throw new Error(`shot ${index + 1} needs ${shot.frames} frames, decoded ${written}. Check in and duration.`);
      list.push(`file ${name}`, `duration ${(shot.frames / fps).toFixed(9)}`);
      if (locationAudio) {
        const wav = `sound-${index}.wav`;
        const samplesAt = (frame) => Math.round(frame * 48000 / fps);
        const samples = samplesAt(elapsedFrames + shot.frames) - samplesAt(elapsedFrames);
        const source = shot.sound ? ['-ss', String(shot.start), '-i', shot.path]
          : ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo'];
        ffmpeg([...source, '-map', '0:a:0', '-af', `aresample=48000:first_pts=0,apad,atrim=end_sample=${samples}`,
          '-ac', '2', '-c:a', 'pcm_s16le', join(scratch, wav)]);
        audioFiles.push(`file ${wav}`);
      }
      elapsedFrames += shot.frames;
    }
    const playlist = join(scratch, 'shots.ffconcat');
    writeFileSync(playlist, ['ffconcat version 1.0', ...list, ''].join('\n'));
    let audioInput = [];
    if (audio) audioInput = ['-ss', String(audio.start), '-i', audio.path];
    if (locationAudio) {
      const soundList = join(scratch, 'sound.ffconcat');
      writeFileSync(soundList, ['ffconcat version 1.0', ...audioFiles, ''].join('\n'));
      audioInput = ['-f', 'concat', '-safe', '1', '-i', soundList];
    }
    const sound = audioInput.length ? [...audioInput, '-map', '0:v:0', '-map', '1:a:0',
      '-af', 'apad', '-c:a', 'aac', '-b:a', '192k'] : ['-map', '0:v:0', '-an'];
    const assembled = join(scratch, 'edit.mp4');
    ffmpeg(['-f', 'concat', '-safe', '1', '-i', playlist, ...sound, '-c:v', 'copy',
      '-t', String(totalFrames / fps), '-movflags', '+faststart', assembled]);
    renameSync(assembled, output);
    console.log(`${shots.length} shots · ${totalFrames} frames at ${fps} fps · ${width}×${height} → ${output}`);
  } finally {
    // mkdtemp created this private directory next to the requested output.
    rmSync(scratch, { recursive: true, force: true });
  }
}

try {
  const [manifest, output] = process.argv.slice(2);
  if (!manifest || !output) throw new Error('usage: node cut.mjs edit.json out.mp4');
  assemble(resolve(manifest), resolve(output));
} catch (error) {
  console.error('cut:', error.message);
  process.exitCode = 1;
}
