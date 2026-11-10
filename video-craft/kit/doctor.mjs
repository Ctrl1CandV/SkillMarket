// doctor.mjs — what this machine can do: browser, WebGL, encoders, voices, ffmpeg. Read-only.
// usage: node doctor.mjs
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { launch, FFMPEG } from './env.mjs';
const out = { node: process.version };
try {
  const b = await launch(), p = await b.newPage();
  await p.goto('file://' + fileURLToPath(import.meta.url));   // WebCodecs needs a secure context; file:// counts
  out.browser = b.version();
  Object.assign(out, await p.evaluate(async () => {
    const r = {};
    const gl = document.createElement('canvas').getContext('webgl2'), dbg = gl && gl.getExtension('WEBGL_debug_renderer_info');
    r.webgl2 = gl ? gl.getParameter(dbg ? dbg.UNMASKED_RENDERER_WEBGL : gl.RENDERER) : false;
    const v = async (codec) => { try { return (await VideoEncoder.isConfigSupported({ codec, width: 1920, height: 1080, bitrate: 8e6, framerate: 30 })).supported; } catch { return false; } };
    const a = async (codec) => { try { return (await AudioEncoder.isConfigSupported({ codec, sampleRate: 48000, numberOfChannels: 2, bitrate: 160000 })).supported; } catch { return false; } };
    r.webcodecs = { vp9: await v('vp09.00.40.08'), av1: await v('av01.0.08M.08'), h264: await v('avc1.640028'), opus: await a('opus'), aac: await a('mp4a.40.2') };
    r.speechVoices = (window.speechSynthesis?.getVoices() || []).length;
    return r;
  }));
  await b.close();
} catch (e) { out.browserError = String(e.message || e).split('\n')[0]; }
const ff = spawnSync(FFMPEG, ['-hide_banner', '-encoders'], { encoding: 'utf8' });
if (ff.status === 0) { const has = (n) => new RegExp('\\s' + n + '\\s').test(ff.stdout); out.ffmpeg = { path: FFMPEG, vp9: has('libvpx-vp9'), h264: has('libx264'), aac: has('aac'), opus: has('libopus') }; }
else out.ffmpeg = false;
console.log(JSON.stringify(out, null, 2));
const tips = [];
if (out.browserError) tips.push('Browser did not start: install one with `npx playwright install chromium`, or point VC_CHROME at chrome-headless-shell.');
if (out.ffmpeg === false) tips.push('No ffmpeg: frames can still be reviewed, but videos cannot be encoded. Set VC_FFMPEG or install ffmpeg.');
else if (!out.ffmpeg.h264) tips.push('ffmpeg has no libx264: deliver WebM (VP9 + Opus); convert to MP4 elsewhere.');
if (out.speechVoices === 0) tips.push('No speech voices in the browser: voice-over must come from a TTS service or recorded clips.');
if (tips.length) console.log('\n' + tips.join('\n'));
