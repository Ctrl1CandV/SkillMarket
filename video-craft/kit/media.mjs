import { execFileSync } from 'node:child_process';

// FFmpeg can exit successfully even when -ss on the audio input skips past EOF.
// Check for decoded samples rather than amplitude so an intentional silent opening is valid.
export function checkAudioStart(ffmpeg, file, seconds) {
  const sample = execFileSync(ffmpeg, ['-nostdin', '-hide_banner', '-loglevel', 'error',
    '-ss', String(seconds), '-i', file, '-map', '0:a:0', '-frames:a', '1',
    '-ac', '1', '-ar', '8000', '-f', 's16le', 'pipe:1'], { windowsHide: true });
  if (!sample.length) throw new Error(`No audio samples at ${seconds}s in ${file}. Check the recording and its source in-point.`);
}
