// doctor.mjs — what this machine can do: browser, WebGL, encoders, voices, ffmpeg. Read-only.
// usage: node doctor.mjs
import { spawnSync } from 'node:child_process';

import { launch, FFMPEG } from './env.mjs';
const out = { node: process.version };
try {
  const b = await launch(), p = await b.newPage();
  await p.goto(import.meta.url);   // WebCodecs needs a secure context; file:// counts
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
// Python side: songmap.py / shotlist.py need NumPy; narrate.py prefers local VoxCPM; --lyrics and --takes use faster-whisper
const PY = process.env.VC_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const probe = `import importlib.util as u, json, os, shutil, sys
sys.path.insert(0, sys.argv[1])
r = {"python": sys.version.split()[0]}
for m in ["numpy", "PIL", "voxcpm", "faster_whisper", "edge_tts"]: r[m] = u.find_spec(m) is not None
if not r["edge_tts"] and shutil.which("edge-tts"): r["edge_tts"] = "cli"
try:
    import torch; r["cuda"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else False
except Exception: r["cuda"] = None
try:
    import gpu; r["gpu"] = gpu.probe_gpu()
except Exception as e: r["gpu"] = {"available": False, "state": "probe_error", "detail": str(e)}
import glob
r["broken_scripts"] = []
for f in sorted(glob.glob(os.path.join(sys.argv[1], "*.py"))):
    try: compile(open(f, encoding="utf-8").read(), f, "exec")
    except SyntaxError as e: r["broken_scripts"].append(os.path.basename(f) + ":" + str(e.lineno))
print(json.dumps(r))`;
const KIT = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const py = spawnSync(PY, ['-c', probe, decodeURIComponent(KIT)], { encoding: 'utf8' });
out.python = py.status === 0 ? JSON.parse(py.stdout.trim().split(/\r?\n/).pop()) : false;
if (out.python?.gpu) { out.gpu = out.python.gpu; delete out.python.gpu; }
console.log(JSON.stringify(out, null, 2));
const tips = [];
if (out.browserError) tips.push('Browser did not start: install one with `npx playwright install chromium`, or point VC_CHROME at chrome-headless-shell.');
if (out.ffmpeg === false) tips.push('No ffmpeg: frames can still be reviewed, but videos cannot be encoded. Set VC_FFMPEG or install ffmpeg.');
else if (!out.ffmpeg.h264) tips.push('ffmpeg has no libx264: deliver WebM (VP9 + Opus); convert to MP4 elsewhere.');
if (out.gpu?.state === 'present_but_inaccessible') {
  tips.push('GPU tools are present, but device query failed (likely sandbox isolation). Ask the user to check `nvidia-smi` in a normal terminal; do not report this as "no GPU".');
} else if (out.gpu?.available && !out.gpu.voxcpm15_safe) {
  tips.push(`GPU resource guard: ${out.gpu.guard_note}. In interactive mode, inform the user and ask before running local GPU models (offer --engine edge + CPU word-alignment, --draft preview, or waiting).`);
}
if (!out.python) tips.push(`No Python (${PY}): songmap.py, shotlist.py and narrate.py need Python 3.9+ with NumPy. Set VC_PYTHON.`);
else {
  if (!out.python.numpy) tips.push('Python has no NumPy: pip install numpy (songmap.py, shotlist.py).');
  if (!out.python.voxcpm) tips.push(out.python.edge_tts
    ? 'No VoxCPM: narrate.py will fall back to Edge online voices (flatter, supports word-level sync). For local neural narration: pip install voxcpm (see references/voice.md).'
    : 'No narration engine: pip install voxcpm (local, natural) or edge-tts (online), or record the lines.');
  else if (!out.python.cuda) tips.push('VoxCPM is installed but PyTorch has no CUDA: narration works on CPU, several times slower than real time.');
  if (out.python.broken_scripts?.length) tips.push(`Kit scripts that do not compile: ${out.python.broken_scripts.join(', ')}. Fix them before use.`);
  if (!out.python.faster_whisper) tips.push('No faster-whisper: songmap.py --lyrics and VoxCPM word-timestamp checks are unavailable (Edge TTS still exports word boundaries natively).');
}
if (tips.length) console.log('\n' + tips.join('\n'));
