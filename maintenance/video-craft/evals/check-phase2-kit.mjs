// Zero-GPU verification suite for video-craft 1.2.0 (Track B engines, QA tools, and doc links).
// Runs pure Node math checks, CPU OfflineAudioContext synthesis, Software-GL single-frame determinism,
// textcheck #lyric auto-detection, shotlist.py vocal-onset & returning-section flags, and Markdown link checks.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { arcPoint, cursorAt, morphMoveRect, rollNumber, throughScreen, cssStageTransform } from '../../../video-craft/kit/stage.js';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '../../..');
const skillRoot = join(repoRoot, 'video-craft');
const kitRoot = join(skillRoot, 'kit');

// ---- 1. stage.js pure geometry & bezel-clearance invariants ----
{
  const [x0, y0] = arcPoint([100, 200], [500, 400], 0, { bend: 0.2 });
  const [x1, y1] = arcPoint([100, 200], [500, 400], 1, { bend: 0.2 });
  const [xm, ym] = arcPoint([100, 200], [500, 200], 0.5, { bend: 0.2 });
  assert.equal(x0, 100); assert.equal(y0, 200);
  assert.equal(x1, 500); assert.equal(y1, 400);
  assert.equal(xm, 300); assert(Math.abs(ym - 240) < 1e-6, `Expected curved midpoint y=240, got ${ym}`);

  // Zero overshoot on a tiny 20x20 button + pinned click ripple after cursor moves away
  const wps = [
    { t: 0, x: 1200, y: 700 },
    { t: 1.0, x: 400, y: 300, click: true, travel: 0.6 },
    { t: 1.6, x: 900, y: 600, travel: 0.35 },
  ];
  for (let t = 0; t <= 1.0; t += 0.02) {
    const c = cursorAt(t, wps);
    assert(c.x >= 400 - 1e-6 && c.x <= 1200 + 1e-6, `Cursor x overshot at t=${t}: ${c.x}`);
  }
  const atClick = cursorAt(1.08, wps);
  assert(atClick.clicking && atClick.press > 0.5);
  assert.equal(atClick.ripple.x, 400); assert.equal(atClick.ripple.y, 300);
  const afterMove = cursorAt(1.38, wps);
  assert(afterMove.x > 450, 'Cursor should have started moving toward next waypoint');
  assert.equal(afterMove.ripple.x, 400, 'Click ripple must stay pinned to clicked target x');
  assert.equal(afterMove.ripple.y, 300, 'Click ripple must stay pinned to clicked target y');

  // Rounded-corner bezel clearance at k=1
  const screenRect = { x: 1080, y: 180, w: 380, h: 740 };
  const radius = 48;
  const st0 = throughScreen(0, screenRect, { w: 1920, h: 1080 }, { borderRadius: radius, pose0: { x: 120, y: -30, scale: 1, rx: 5, ry: -16, rz: 2 } });
  assert(Math.abs(st0.tx - 120) < 1e-6 && Math.abs(st0.ty - -30) < 1e-6);
  const stMid = throughScreen(0.85, screenRect, { w: 1920, h: 1080 }, { borderRadius: radius, pose0: { rx: 5, ry: -16, rz: 2 } });
  assert.equal(stMid.rx, 0); assert.equal(stMid.ry, 0); assert.equal(stMid.rz, 0);
  const st1 = throughScreen(1, screenRect, { w: 1920, h: 1080 }, { borderRadius: radius, pose0: { x: 120, y: -30, rx: 5, ry: -16, rz: 2 } });
  assert(st1.cleared);
  assert.match(cssStageTransform(st1), /^translate3d\(/);
  for (const [vx, vy] of [[0, 0], [1920, 0], [0, 1080], [1920, 1080]]) {
    // Inverse map viewport corner back to unscaled stage coordinates
    const sx = st1.ox + (vx - st1.ox - st1.tx) / st1.scale;
    const sy = st1.oy + (vy - st1.oy - st1.ty) / st1.scale;
    assert(sx > screenRect.x && sx < screenRect.x + screenRect.w, `Leaked horizontal bezel: sx=${sx}`);
    assert(sy > screenRect.y && sy < screenRect.y + screenRect.h, `Leaked vertical bezel: sy=${sy}`);
    // Check rounded corner arc clearance
    const cx = sx < screenRect.x + radius ? screenRect.x + radius : (sx > screenRect.x + screenRect.w - radius ? screenRect.x + screenRect.w - radius : sx);
    const cy = sy < screenRect.y + radius ? screenRect.y + radius : (sy > screenRect.y + screenRect.h - radius ? screenRect.y + screenRect.h - radius : sy);
    const dist = Math.hypot(sx - cx, sy - cy);
    assert(dist < radius - 0.5, `Leaked rounded corner bezel: dist=${dist} >= r=${radius}`);
  }

  const mm = morphMoveRect({ x: 100, y: 100, w: 200, h: 60 }, { x: 800, y: 400, w: 300, h: 80 }, 1, 0, { midW: 260, midH: 70 });
  assert.equal(mm.w, 260); assert.equal(mm.h, 70);
  assert.equal(rollNumber(0, 1250, 0.5, { prefix: '¥' }), '¥625');
  console.log('PASS [1/6]: stage.js geometry, zero-overshoot cursor, pinned ripple & rounded bezel clearance');
}

// ---- 2. Markdown relative link Integrity across video-craft/ ----
{
  const mdFiles = [join(skillRoot, 'SKILL.md'), ...readdirSync(join(skillRoot, 'references')).filter((f) => f.endsWith('.md')).map((f) => join(skillRoot, 'references', f))];
  const linkRe = /\[[^\]]+\]\((?!https?:\/\/|mailto:|file:\/\/)([^)]+)\)/g;
  const broken = [];
  for (const file of mdFiles) {
    const raw = readFileSync(file, 'utf8');
    // Strip fenced code blocks before scanning prose links
    const prose = raw.replace(/```[\s\S]*?```/g, '');
    for (const m of prose.matchAll(linkRe)) {
      const target = m[1].trim();
      const [relPath] = target.split('#');
      if (!relPath) continue;
      const abs = resolve(dirname(file), relPath);
      if (!existsSync(abs)) broken.push(`${file} -> ${target}`);
    }
  }
  assert.deepEqual(broken, [], `Broken Markdown links:\n${broken.join('\n')}`);
  console.log(`PASS [2/6]: ${mdFiles.length} Markdown files verified with 0 broken relative links`);
}

// ---- 3. CPU OfflineAudioContext + Software-GL Canvas/DOM checks ----
const tmp = mkdtempSync(join(tmpdir(), 'vc-phase2-'));
const env = { ...process.env, VC_SOFTWARE_GL: '1', PYTHONNOUSERSITE: '1' };
try {
  // Build a tiny test scene & score exercising all new sound.js, draw.js, stage.js & #lyric features
  const kitUrl = kitRoot.replace(/\\/g, '/');
  const sceneHtml = join(tmp, 'scene.html');
  const scoreHtml = join(tmp, 'score.html');
  const outWebm = join(tmp, 'audio.webm');
  const promoScene = join(skillRoot, 'examples', 'promo', 'index.html');
  const promoScore = join(skillRoot, 'examples', 'promo', 'score.html');
  const promoWebm = join(tmp, 'promo.webm');

  writeFileSync(sceneHtml, `<!doctype html><meta charset="utf-8">
<style>
  body { margin: 0; background: #f4f1ea; overflow: hidden; font-family: sans-serif; }
  #stage { position: relative; width: 1080px; height: 1920px; }
  #lyric { position: absolute; left: 8%; right: 8%; bottom: 15%; text-align: center; color: #1c2026; }
  #lyric-en { font-size: 48px; }
  #lyric-zh { font-size: 38px; }
</style>
<div id="stage"><canvas id="cv" width="1080" height="1920"></canvas><div id="lyric"><div id="lyric-en"></div><div id="lyric-zh"></div></div></div>
<script type="module">
  import { register } from 'file:///${kitUrl}/kit.js';
  import { glow, lightBeam, bokeh, withHandheld, finish } from 'file:///${kitUrl}/draw.js';
  import { cursorAt, drawCursor } from 'file:///${kitUrl}/stage.js';
  const cv = document.getElementById('cv'), ctx = cv.getContext('2d');
  const en = document.getElementById('lyric-en'), zh = document.getElementById('lyric-zh');
  const wps = [{ t: 0, x: 800, y: 1200 }, { t: 1.2, x: 540, y: 960, click: true }];
  function seek(t) {
    ctx.fillStyle = '#f4f1ea'; ctx.fillRect(0, 0, 1080, 1920);
    const cam = withHandheld({ x: 0, y: 0, z: 1 }, t, { amp: 5, seed: 3 });
    lightBeam(ctx, 120, 0, 680, 1400, 140, 520, '#ffd89b', 0.22, { blend: 'source-over' });
    bokeh(ctx, 9, 28, cam, t, { color: [255, 200, 140], alpha: 0.16, blend: 'source-over' });
    glow(ctx, 540, 960, 120, '#ff8844', 0.15);
    drawCursor(ctx, cursorAt(t, wps), { kind: 'arrow', accent: '#e04f3e' });
    if (t >= 0.4 && t < 3.0) { en.textContent = 'Three PM sunlight on the wall'; zh.textContent = '下午三点白墙上的窗影'; document.getElementById('lyric').style.opacity = '1'; }
    else { en.textContent = ''; zh.textContent = ''; document.getElementById('lyric').style.opacity = '0'; }
    finish(ctx, Math.round(t * 30), { vignette: 0.08, grain: 0.03 });
  }
  register({ duration: 3.5, fps: 30, width: 1080, height: 1920, seek, meta: {
    events: [{ t: 0.3, type: 'click' }, { t: 1.2, type: 'click' }, { t: 1.8, type: 'swipe' }, { t: 2.4, type: 'done' }],
    sfx: [{ t: 0.5, kind: 'uiClick' }, { t: 1.4, kind: 'swipe' }, { t: 2.2, kind: 'glass', note: 'E6' }],
  } });
  seek(0);
</script>`, 'utf8');

  writeFileSync(scoreHtml, `<!doctype html><script type="module">
  import { install, NOTE, epiano, subBass, warmPad, glass, uiClick, swipe, kick, duck, sidechain } from 'file:///${kitUrl}/sound.js';
  install((m, events, dur) => {
    m.music.gain.value = 0.7;
    warmPad(m, m.music, 0, dur, ['C4', 'E4', 'G4', 'D5'].map(NOTE), { gain: 0.03 });
    for (const bt of [0, 0.5, 1.0, 1.5, 2.0, 2.12, 2.5, 3.0]) kick(m, m.music, bt, { gain: 0.32 });
    sidechain(m.music, [0, 0.5, 1.0, 1.5, 2.0, 2.12, 2.5, 3.0], { depth: -8 });
    duck(m.music, [[0.8, 1.8]], { depth: -9 });
    epiano(m, m.music, 0.2, NOTE('C4'), { dur: 1.4, gain: 0.08, tremolo: 4.5 });
    subBass(m, m.music, 0.2, NOTE('C2'), { dur: 0.8, gain: 0.18 });
    for (const e of events) {
      if (e.type === 'click') uiClick(m, m.sfx, e.t, { freq: 1900, gain: 0.08 });
      else if (e.type === 'swipe') swipe(m, m.sfx, e.t, { dur: 0.22, pan0: -0.3, pan1: 0.3 });
      else if (e.type === 'done') glass(m, m.sfx, e.t, NOTE('G5'), { dur: 1.1, gain: 0.06 });
    }
  }, { reverb: 0.2, irSec: 1.8, irDamp: 0.75, preDelay: 0.014, warmth: 0.14 });
</script>`, 'utf8');

  // 3a. Synthesize score.html + stems (verifies damped IR, warmth shaper, sidechain+duck coexistence, new instruments)
  const a1 = spawnSync(process.execPath, [join(kitRoot, 'audio.mjs'), sceneHtml, scoreHtml, outWebm, '--stems'], { encoding: 'utf8', env, windowsHide: true });
  assert.equal(a1.status, 0, a1.stderr);
  const lines1 = a1.stdout.trim().split(/\r?\n/);
  const stems1 = JSON.parse(lines1[0].replace(/^stems\s+/, ''));
  const mix1 = JSON.parse(lines1[1]);
  assert(Number.isFinite(stems1.music.lufs) && Number.isFinite(stems1.sfx.lufs));
  assert(Math.abs(mix1.lufs - -16) <= 0.4, `Expected ~ -16 LUFS, got ${mix1.lufs}`);
  assert(mix1.peak <= -1.4, `Expected peak <= -1.4 dBFS, got ${mix1.peak}`);

  // 3b. Synthesize '-' mode (verifies audio.mjs inline uiClick/swipe/glass wiring) + existing promo regression
  const aDash = spawnSync(process.execPath, [join(kitRoot, 'audio.mjs'), sceneHtml, '-', join(tmp, 'dash.webm')], { encoding: 'utf8', env, windowsHide: true });
  assert.equal(aDash.status, 0, aDash.stderr);
  const aPromo = spawnSync(process.execPath, [join(kitRoot, 'audio.mjs'), promoScene, promoScore, promoWebm], { encoding: 'utf8', env, windowsHide: true });
  assert.equal(aPromo.status, 0, aPromo.stderr);
  const promoRes = JSON.parse(aPromo.stdout.trim().split(/\r?\n/).pop());
  assert(promoRes.lufs >= -17.0 && promoRes.lufs <= -15.5 && promoRes.peak <= -1.4, `Unexpected promo audio stats: ${JSON.stringify(promoRes)}`);
  console.log(`PASS [3/6]: sound.js & audio.mjs CPU synthesis verified (new instruments LUFS=${mix1.lufs}/peak=${mix1.peak}, promo LUFS=${promoRes.lufs}/peak=${promoRes.peak})`);

  // 4. textcheck.mjs vertical 9:16 #lyric auto-detection + Software-GL out-of-order seek determinism
  const tc = spawnSync(process.execPath, [join(kitRoot, 'textcheck.mjs'), sceneHtml], { encoding: 'utf8', env, windowsHide: true });
  assert.equal(tc.status, 0, tc.stderr);
  assert.match(tc.stdout, /no caption outside margins; all fonts ≥ 36px/);

  const seekProbe = `
    import { launch, fileUrl } from ${JSON.stringify('file:///' + kitUrl + '/env.mjs')};
    const b = await launch();
    const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
    await p.goto(fileUrl(${JSON.stringify(sceneHtml)}));
    await p.waitForFunction(() => window.__video);
    await p.evaluate(() => window.__seek(1.25));
    const b1 = await p.screenshot();
    await p.evaluate(() => window.__seek(0.2));
    await p.evaluate(() => window.__seek(2.7));
    await p.evaluate(() => window.__seek(1.25));
    const b2 = await p.screenshot();
    await b.close();
    if (!b1.equals(b2)) { console.error('Out-of-order seek mismatch'); process.exit(1); }
  `;
  const sp = spawnSync(process.execPath, ['--input-type=module', '-e', seekProbe], { encoding: 'utf8', env, windowsHide: true });
  assert.equal(sp.status, 0, sp.stderr);
  console.log('PASS [4/6]: textcheck.mjs 9:16 #lyric auto-check & Software-GL out-of-order seek determinism verified');

  // 4b. Tier-2 stage3d.js (Three.js PBR + studioEnv + HDR Bloom + ACES + dispersion) & shader.js { sdf: true } under Software-GL
  const tier2Html = join(tmp, 'tier2.html');
  writeFileSync(tier2Html, `<!doctype html><meta charset="utf-8"><body style="margin:0;background:#000">
<canvas id="out" width="320" height="180"></canvas>
<script type="module">
  import { register } from 'file:///${kitUrl}/kit.js';
  import { shader } from 'file:///${kitUrl}/shader.js';
  import { THREE, createStage3D, studioEnv, addStudioRig, pbrMaterial, roundedSlab, instancedField, orbitCamera } from 'file:///${kitUrl}/stage3d.js';
  const cv = document.getElementById('out'), ctx = cv.getContext('2d');
  const bg = shader(320, 180, \`
    void main() {
      vec2 uv = (gl_FragCoord.xy - 0.5 * res) / res.y;
      vec3 p = vec3(uv * 2.0, 0.0);
      p.xy *= rot2(t * 0.3);
      float d = smin(sdSphere(p, 0.55), sdRoundBox(p - vec3(0.35, 0.0, 0.0), vec3(0.25), 0.08), 0.35);
      vec3 col = d < 0.0 ? thinFilm(abs(d), t * 0.2) * (1.2 + pulse) : vec3(0.03, 0.04, 0.08);
      o = vec4(toSrgb(aces(col)), 1.0);
    }\`, { scale: 0.5, sdf: true, uniforms: ['pulse'] });
  const st = createStage3D(320, 180, { fov: 35, bloom: 0.48, bloomThreshold: 0.85, dispersion: 0.25 });
  studioEnv(st);
  const rig = addStudioRig(st);
  const hero = new THREE.Mesh(roundedSlab(1.8, 2.6, 0.2, { radius: 0.2, bevel: 0.04, segments: 6 }), pbrMaterial('iridescent'));
  const crystal = new THREE.Mesh(new THREE.TorusGeometry(1.5, 0.08, 16, 48), pbrMaterial('crystal'));
  const glowBar = new THREE.Mesh(roundedSlab(2.2, 0.08, 0.08, { radius: 0.02, bevel: 0.01, segments: 3 }), pbrMaterial('emissive', { color: '#60a5fa', emissiveIntensity: 4.5 }));
  glowBar.position.set(0, -1.6, 0.4);
  const field = instancedField(roundedSlab(0.12, 0.3, 0.06, { radius: 0.02, bevel: 0.01, segments: 2 }), pbrMaterial('metal'), 24, (i, obj, col, t) => {
    const a = (i / 24) * Math.PI * 2 + t * 0.5;
    obj.position.set(Math.cos(a) * 2.4, Math.sin(i + t) * 0.4, Math.sin(a) * 2.4);
    obj.rotation.y = -a;
  });
  st.scene.add(hero, crystal, glowBar, field.mesh);
  function seek(t) {
    orbitCamera(st.camera, { target: [0, 0, 0], radius: 5.2, azimuth: t * 0.4, elevation: 0.2, fov: 35 });
    rig.sweep(t * 0.5);
    hero.rotation.y = t * 0.3;
    crystal.rotation.x = 0.8 + t * 0.4;
    field.update(t);
    bg.draw(t, { pulse: 0.5 });
    st.render(t);
    ctx.drawImage(st.canvas, 0, 0, 320, 180);
    ctx.globalAlpha = 0.25; ctx.drawImage(bg.canvas, 0, 0, 320, 180); ctx.globalAlpha = 1;
  }
  register({ duration: 2, fps: 30, width: 320, height: 180, seek });
  seek(0);
</script></body>`, 'utf8');

  const tier2Probe = `
    import { launch, fileUrl } from ${JSON.stringify('file:///' + kitUrl + '/env.mjs')};
    const b = await launch();
    const p = await b.newPage({ viewport: { width: 320, height: 180 } });
    const errs = [];
    p.on('pageerror', (e) => errs.push(e.message));
    await p.goto(fileUrl(${JSON.stringify(tier2Html)}));
    await p.waitForFunction(() => window.__video);
    await p.evaluate(() => window.__seek(0.9));
    const s1 = await p.screenshot();
    const nonBlack = await p.evaluate(() => {
      const d = document.getElementById('out').getContext('2d').getImageData(0, 0, 320, 180).data;
      let bright = 0;
      for (let i = 0; i < d.length; i += 4) if (d[i] + d[i+1] + d[i+2] > 60) bright++;
      return bright;
    });
    await p.evaluate(() => window.__seek(0.1));
    await p.evaluate(() => window.__seek(0.9));
    const s2 = await p.screenshot();
    await b.close();
    if (errs.length) { console.error('Page errors:', errs); process.exit(1); }
    if (nonBlack < 500) { console.error('Tier-2 3D render looks blank/black:', nonBlack); process.exit(1); }
    if (!s1.equals(s2)) { console.error('Tier-2 3D seek non-deterministic'); process.exit(1); }
  `;
  const t2 = spawnSync(process.execPath, ['--input-type=module', '-e', tier2Probe], { encoding: 'utf8', env, windowsHide: true });
  assert.equal(t2.status, 0, t2.stderr);
  console.log('PASS [5/6]: Tier-2 stage3d.js (PBR + studioEnv + HDR Bloom + ACES) & shader.js { sdf: true } verified');

  // 5. shotlist.py vocal-onset recognition & returning-section identical-visual warning (CPU ffmpeg synthetic clip)
  const pyExe = process.env.VC_PYTHON || 'C:\\Users\\11487\\.conda\\envs\\skillmarket\\python.exe';
  const ffmpegExe = process.env.VC_FFMPEG || 'ffmpeg';
  const testMp4 = join(tmp, 'mv_test.mp4');
  const songJson = join(tmp, 'songmap.json');
  // 6s video: 0..2s dark gray (luma ~0.2) -> hard cut at 2.14s (off-beat from 2.0s, on vocal onset 2.15s!) to bright (0.75) -> hard cut at 4.0s back to identical 0.2 gray
  const ff = spawnSync(ffmpegExe, [
    '-y', '-v', 'error',
    '-f', 'lavfi', '-i', 'color=c=#333333:s=320x180:r=30:d=2.133',
    '-f', 'lavfi', '-i', 'color=c=#bfbfbf:s=320x180:r=30:d=1.867',
    '-f', 'lavfi', '-i', 'color=c=#333333:s=320x180:r=30:d=2.0',
    '-filter_complex', '[0:v][1:v][2:v]concat=n=3:v=1:a=0',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', testMp4,
  ], { encoding: 'utf8', env, windowsHide: true });
  assert.equal(ff.status, 0, ff.stderr);

  writeFileSync(songJson, JSON.stringify({
    beats: [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5],
    downbeats: [0, 2.0, 4.0],
    sections: [
      { t0: 0.0, t1: 2.1, bar: 0, bars: 1, label: 'A', db: -12, character: 'mid' },
      { t0: 2.1, t1: 4.0, bar: 1, bars: 1, label: 'B', db: -8, character: 'peak' },
      { t0: 4.0, t1: 6.0, bar: 2, bars: 1, label: 'A', db: -12, character: 'mid' },
    ],
    lyrics: { lines: [{ t0: 2.15, t1: 3.6, text: 'Vocal entrance right after beat', words: [{ t0: 2.15, t1: 2.5, w: 'Vocal' }] }] },
  }), 'utf8');

  const sl = spawnSync(pyExe, [join(kitRoot, 'shotlist.py'), testMp4, '--song', songJson], { encoding: 'utf8', env, windowsHide: true });
  assert.equal(sl.status, 0, sl.stderr);
  assert.match(sl.stdout, /1 on vocal phrase onsets/, `Expected vocal phrase onset recognition:\n${sl.stdout}`);
  assert.doesNotMatch(sl.stdout, /more than 120 ms off both/, `Vocal cut should not be flagged off-beat:\n${sl.stdout}`);
  assert.match(sl.stdout, /same music as #1.*looks visually almost identical/, `Expected returning section warning:\n${sl.stdout}`);

  // Also test blender_bridge.py sample_songmap_frames helper on both synthetic and real last-light songmap.json
  const realSongMap = join(skillRoot, 'examples', 'last-light', 'map', 'songmap.json');
  const bbProbe = `import sys; sys.path.insert(0, ${JSON.stringify(kitRoot)}); import blender_bridge as bb; r1 = bb.sample_songmap_frames(${JSON.stringify(songJson)}, fps=30, duration=1.0); r2 = bb.sample_songmap_frames(${JSON.stringify(realSongMap)}, fps=30, duration=2.0); assert len(r1) == 30 and len(r2) == 60 and max(x['energy'] for x in r2) > 0`;
  const bb = spawnSync(pyExe, ['-c', bbProbe], { encoding: 'utf8', env, windowsHide: true });
  assert.equal(bb.status, 0, bb.stderr);
  console.log('PASS [6/6]: shotlist.py vocal-onset/returning-section & blender_bridge.py songmap sampling verified');
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
