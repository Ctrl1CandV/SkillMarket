// sound.js — offline synthesis of music and sound effects (Web Audio), loudness, limiter, Opus/WebM output.
// Everything is deterministic: noise comes from a seeded generator, events come from the scene timeline.
import { rng } from './kit.js';

export const NOTE = (name) => {
  const m = /^([A-G])(#|b)?(-?\d)$/.exec(name);
  const base = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }[m[1]] + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0);
  const midi = 12 * (+m[3] + 1) + base;
  return 440 * Math.pow(2, (midi - 69) / 12);
};

export function makeMixer(ctx, { reverb = 0.18, seed = 7, irSec = 1.8, irPow = 3.2 } = {}) {
  const r = rng(seed);
  const noise = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
  const nd = noise.getChannelData(0); for (let i = 0; i < nd.length; i++) nd[i] = r() * 2 - 1;
  // a longer buffer for beds (wind, room tone) so the loop is not heard
  const noiseLong = ctx.createBuffer(1, ctx.sampleRate * 9, ctx.sampleRate);
  const nl = noiseLong.getChannelData(0); for (let i = 0; i < nl.length; i++) nl[i] = r() * 2 - 1;
  // impulse response: small room by default, a hall with irSec ≈ 3.5
  const ir = ctx.createBuffer(2, Math.round(ctx.sampleRate * irSec), ctx.sampleRate);
  for (let c = 0; c < 2; c++) { const d = ir.getChannelData(c); for (let i = 0; i < d.length; i++) d[i] = (r() * 2 - 1) * Math.pow(1 - i / d.length, irPow); }
  const master = ctx.createGain(); master.gain.value = 1; master.connect(ctx.destination);
  const conv = ctx.createConvolver(); conv.buffer = ir; const wet = ctx.createGain(); wet.gain.value = reverb; conv.connect(wet); wet.connect(master);
  // each bus: gain (scores may automate it) → mute (used only for stem renders) → master + reverb send
  const bus = (gain = 1, send = 0.5) => { const g = ctx.createGain(); g.gain.value = gain; const mute = ctx.createGain(); g.connect(mute); mute.connect(master); const s = ctx.createGain(); s.gain.value = send; mute.connect(s); s.connect(conv); g.mute = mute; return g; };
  const music = bus(1, 0.6), sfx = bus(1, 0.35), voice = bus(1, 0.08);
  return { ctx, master, music, sfx, voice, vo: {}, noise, noiseLong, rand: r };
}

function env(g, t, { a = 0.005, d = 0.3, peak = 0.2, hold = 0 }) {
  peak = Math.max(peak, 0.0002);
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(peak, t + a);
  if (hold) g.gain.setValueAtTime(peak, t + a + hold);
  g.gain.exponentialRampToValueAtTime(0.0001, t + a + hold + d);
}
const panTo = (m, node, pan) => { if (!pan) return node; const p = m.ctx.createStereoPanner(); p.pan.value = pan; node.connect(p); return p; };
function noiseSrc(m, t, dur) { const s = m.ctx.createBufferSource(); s.buffer = m.noise; s.loop = true; s.start(t, m.rand() * 1.5); s.stop(t + dur + 0.05); return s; }

// ---- instruments ----
export function pluck(m, out, t, f, { dur = 0.7, gain = 0.12, bright = 2600, pan = 0, type = 'triangle' } = {}) {
  const c = m.ctx, o = c.createOscillator(), o2 = c.createOscillator(), lp = c.createBiquadFilter(), g = c.createGain();
  o.type = type; o.frequency.value = f; o2.type = 'sine'; o2.frequency.value = f * 2; const g2 = c.createGain(); g2.gain.value = 0.35;
  lp.type = 'lowpass'; lp.frequency.setValueAtTime(bright, t); lp.frequency.exponentialRampToValueAtTime(Math.max(300, f * 1.5), t + dur * 0.8);
  o.connect(lp); o2.connect(g2); g2.connect(lp); lp.connect(g); panTo(m, g, pan).connect(out);
  env(g, t, { a: 0.004, d: dur, peak: gain });
  o.start(t); o2.start(t); o.stop(t + dur + 0.1); o2.stop(t + dur + 0.1);
}
export function bass(m, out, t, f, { dur = 0.5, gain = 0.2 } = {}) {
  const c = m.ctx, o = c.createOscillator(), o2 = c.createOscillator(), g = c.createGain(), lp = c.createBiquadFilter();
  o.type = 'sine'; o.frequency.value = f; o2.type = 'triangle'; o2.frequency.value = f; const g2 = c.createGain(); g2.gain.value = 0.25;
  lp.type = 'lowpass'; lp.frequency.value = 600;
  o.connect(g); o2.connect(g2); g2.connect(lp); lp.connect(g); g.connect(out);
  env(g, t, { a: 0.012, d: dur, peak: gain, hold: dur * 0.3 });
  o.start(t); o2.start(t); o.stop(t + dur * 1.4 + 0.1); o2.stop(t + dur * 1.4 + 0.1);
}
export function pad(m, out, t, freqs, { dur = 2.4, gain = 0.05, attack = 0.4, cutoff = 1400 } = {}) {
  const c = m.ctx, g = c.createGain(), lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = cutoff; lp.connect(g); g.connect(out);
  g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(gain, t + attack); g.gain.setValueAtTime(gain, t + Math.max(attack, dur - 0.5)); g.gain.linearRampToValueAtTime(0.0001, t + dur + 0.6);
  for (const f of freqs) for (const det of [-6, 6]) { const o = c.createOscillator(); o.type = 'sawtooth'; o.frequency.value = f; o.detune.value = det; o.connect(lp); o.start(t); o.stop(t + dur + 0.7); }
}
export function tick(m, out, t, { freq = 2200, gain = 0.06, dur = 0.035, pan = 0 } = {}) {
  const c = m.ctx, s = noiseSrc(m, t, dur), bp = c.createBiquadFilter(), g = c.createGain();
  bp.type = 'bandpass'; bp.frequency.value = freq; bp.Q.value = 6; s.connect(bp); bp.connect(g); panTo(m, g, pan).connect(out);
  env(g, t, { a: 0.001, d: dur, peak: gain });
  const o = c.createOscillator(), og = c.createGain(); o.frequency.value = freq / 2; o.connect(og); og.connect(out); env(og, t, { a: 0.001, d: dur * 0.8, peak: gain * 0.5 }); o.start(t); o.stop(t + dur + 0.05);
}
export function pop(m, out, t, { f0 = 320, f1 = 980, gain = 0.12, dur = 0.09, pan = 0 } = {}) {
  const c = m.ctx, o = c.createOscillator(), g = c.createGain();
  o.type = 'sine'; o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(f1, t + dur * 0.6);
  o.connect(g); panTo(m, g, pan).connect(out); env(g, t, { a: 0.003, d: dur, peak: gain }); o.start(t); o.stop(t + dur + 0.05);
}
export function chime(m, out, t, f, { gain = 0.08, dur = 1.4, pan = 0 } = {}) {
  const c = m.ctx;
  for (const [mul, gg] of [[1, 1], [2.76, 0.35], [5.4, 0.12]]) {
    const o = c.createOscillator(), g = c.createGain(); o.type = 'sine'; o.frequency.value = f * mul; o.connect(g); panTo(m, g, pan).connect(out);
    env(g, t, { a: 0.003, d: dur / mul ** 0.5, peak: gain * gg }); o.start(t); o.stop(t + dur + 0.1);
  }
}
export function thud(m, out, t, { freq = 95, gain = 0.25, dur = 0.22, pan = 0 } = {}) {
  const c = m.ctx, o = c.createOscillator(), g = c.createGain();
  o.type = 'sine'; o.frequency.setValueAtTime(freq * 2.2, t); o.frequency.exponentialRampToValueAtTime(freq, t + 0.06);
  o.connect(g); panTo(m, g, pan).connect(out); env(g, t, { a: 0.002, d: dur, peak: gain }); o.start(t); o.stop(t + dur + 0.05);
  tick(m, out, t, { freq: 1400, gain: gain * 0.35, dur: 0.02, pan });
}
export function whoosh(m, out, t, { dur = 0.6, f0 = 400, f1 = 2400, gain = 0.12, peakAt = 0.65, pan0 = 0, pan1 = 0 } = {}) {
  const c = m.ctx, s = noiseSrc(m, t, dur), bp = c.createBiquadFilter(), g = c.createGain(), p = c.createStereoPanner();
  bp.type = 'bandpass'; bp.Q.value = 1.4; bp.frequency.setValueAtTime(f0, t); bp.frequency.exponentialRampToValueAtTime(f1, t + dur);
  p.pan.setValueAtTime(pan0, t); p.pan.linearRampToValueAtTime(pan1, t + dur);
  s.connect(bp); bp.connect(g); g.connect(p); p.connect(out);
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(gain, t + dur * peakAt); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
}
export function hat(m, out, t, { gain = 0.03, dur = 0.045 } = {}) {
  const c = m.ctx, s = noiseSrc(m, t, dur), hp = c.createBiquadFilter(), g = c.createGain();
  hp.type = 'highpass'; hp.frequency.value = 7500; s.connect(hp); hp.connect(g); g.connect(out); env(g, t, { a: 0.001, d: dur, peak: gain });
}
export function rewind(m, out, t, dur, { gain = 0.07 } = {}) {
  const c = m.ctx, o = c.createOscillator(), lfo = c.createOscillator(), lg = c.createGain(), bp = c.createBiquadFilter(), g = c.createGain();
  o.type = 'sawtooth'; o.frequency.value = 900; lfo.type = 'square'; lfo.frequency.setValueAtTime(14, t); lfo.frequency.linearRampToValueAtTime(26, t + dur);
  lg.gain.value = 420; lfo.connect(lg); lg.connect(o.frequency);
  bp.type = 'bandpass'; bp.frequency.value = 1500; bp.Q.value = 2; o.connect(bp); bp.connect(g); g.connect(out);
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(gain, t + 0.05); g.gain.setValueAtTime(gain, t + dur - 0.08); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.start(t); lfo.start(t); o.stop(t + dur + 0.05); lfo.stop(t + dur + 0.05);
  whoosh(m, out, t, { dur, f0: 3000, f1: 500, gain: gain * 1.2, peakAt: 0.3 });
}
export function glide(m, out, t, f0, f1, { dur = 1.0, gain = 0.06, type = 'triangle' } = {}) {
  const c = m.ctx, o = c.createOscillator(), g = c.createGain(), lp = c.createBiquadFilter();
  o.type = type; o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(f1, t + dur);
  lp.type = 'lowpass'; lp.frequency.value = 1800; o.connect(lp); lp.connect(g); g.connect(out);
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(gain, t + 0.08); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.start(t); o.stop(t + dur + 0.05);
}


// ---- cinematic / ambient instruments ----
// soft piano: additive partials with slight inharmonicity, upper partials decay faster
export function piano(m, out, t, f, { gain = 0.07, dur = 3.2, pan = 0, bright = 1 } = {}) {
  const c = m.ctx, g = c.createGain(); panTo(m, g, pan).connect(out);
  const amps = [1, 0.42, 0.2, 0.11, 0.06, 0.035];
  for (let n = 1; n <= amps.length; n++) {
    const fn = f * n * Math.sqrt(1 + 0.00035 * n * n); if (fn > 14000) break;
    const o = c.createOscillator(), og = c.createGain(); o.type = 'sine'; o.frequency.value = fn;
    const a = gain * amps[n - 1] * Math.pow(bright, n - 1), d = (dur / (1 + (n - 1) * 0.9)) * (f > 900 ? 0.7 : 1);
    og.gain.setValueAtTime(0.0001, t); og.gain.exponentialRampToValueAtTime(a, t + 0.005);
    og.gain.exponentialRampToValueAtTime(a * 0.35, t + 0.18); og.gain.exponentialRampToValueAtTime(0.0001, t + d);
    o.connect(og); og.connect(g); o.start(t); o.stop(t + d + 0.05);
  }
  const s = noiseSrc(m, t, 0.03), lp = c.createBiquadFilter(), hg = c.createGain();
  lp.type = 'lowpass'; lp.frequency.value = Math.min(4000, f * 4); s.connect(lp); lp.connect(hg); hg.connect(g);
  env(hg, t, { a: 0.001, d: 0.03, peak: gain * 0.25 });
}
// a held tone (sine + detuned twin); returns its gain so callers can automate it
export function tone(m, out, t0, t1, f, { gain = 0.03, attack = 0.3, release = 0.6, pan = 0, pan1 = null, type = 'sine', detune = 5 } = {}) {
  const c = m.ctx, g = c.createGain(), p = c.createStereoPanner();
  p.pan.setValueAtTime(pan, t0); if (pan1 !== null) p.pan.linearRampToValueAtTime(pan1, t1);
  g.connect(p); p.connect(out);
  g.gain.setValueAtTime(0, t0); g.gain.linearRampToValueAtTime(gain, t0 + attack);
  g.gain.setValueAtTime(gain, Math.max(t0 + attack, t1 - release)); g.gain.linearRampToValueAtTime(0, t1);
  for (const det of [0, detune]) { const o = c.createOscillator(); o.type = type; o.frequency.value = f; o.detune.value = det; const og = c.createGain(); og.gain.value = det ? 0.5 : 1; o.connect(og); og.connect(g); o.start(t0); o.stop(t1 + 0.05); }
  return g;
}
// warm pad: detuned saw + triangle through a slowly breathing low-pass, spread left/right
export function warmPad(m, out, t0, t1, freqs, { gain = 0.03, attack = 1.2, release = 1.4, cutoff = 1000, breathe = 0.12 } = {}) {
  const c = m.ctx, g = c.createGain(), lp = c.createBiquadFilter();
  lp.type = 'lowpass'; lp.frequency.value = cutoff; lp.Q.value = 0.5;
  const lfo = c.createOscillator(), lg = c.createGain(); lfo.frequency.value = breathe; lg.gain.value = cutoff * 0.25; lfo.connect(lg); lg.connect(lp.frequency); lfo.start(t0); lfo.stop(t1 + 0.1);
  lp.connect(g); g.connect(out);
  g.gain.setValueAtTime(0, t0); g.gain.linearRampToValueAtTime(gain, t0 + attack);
  g.gain.setValueAtTime(gain, Math.max(t0 + attack, t1 - release)); g.gain.linearRampToValueAtTime(0, t1);
  freqs.forEach((f, i) => {
    for (const [det, pan, type, a] of [[-7, -0.45, 'sawtooth', 0.5], [7, 0.45, 'sawtooth', 0.5], [0, 0, 'triangle', 0.9]]) {
      const o = c.createOscillator(), og = c.createGain(), p = c.createStereoPanner();
      o.type = type; o.frequency.value = f; o.detune.value = det + (i % 2 ? 2 : -2); og.gain.value = a / Math.sqrt(freqs.length);
      p.pan.value = pan; o.connect(og); og.connect(p); p.connect(lp); o.start(t0); o.stop(t1 + 0.05);
    }
  });
}
// wind / air bed: two band-passed noise layers whose colour and level drift slowly
export function wind(m, out, t0, t1, { gain = 0.05, fadeIn = 1.5, fadeOut = 1.5, center = 650 } = {}) {
  const c = m.ctx;
  for (const [pan, rate] of [[-0.6, 0.071], [0.6, 0.053]]) {
    const s = c.createBufferSource(); s.buffer = m.noiseLong; s.loop = true; s.start(t0, m.rand() * 8); s.stop(t1 + 0.05);
    const bp = c.createBiquadFilter(); bp.type = 'bandpass'; bp.Q.value = 0.8; bp.frequency.value = center;
    const lfo = c.createOscillator(), lg = c.createGain(); lfo.frequency.value = rate; lg.gain.value = center * 0.45; lfo.connect(lg); lg.connect(bp.frequency);
    const am = c.createGain(); am.gain.value = 0.65; const lfo2 = c.createOscillator(), lg2 = c.createGain(); lfo2.frequency.value = rate * 1.63; lg2.gain.value = 0.35; lfo2.connect(lg2); lg2.connect(am.gain);
    const g = c.createGain(); g.gain.setValueAtTime(0, t0); g.gain.linearRampToValueAtTime(gain, t0 + fadeIn); g.gain.setValueAtTime(gain, Math.max(t0 + fadeIn, t1 - fadeOut)); g.gain.linearRampToValueAtTime(0, t1);
    const p = c.createStereoPanner(); p.pan.value = pan;
    s.connect(bp); bp.connect(am); am.connect(g); g.connect(p); p.connect(out);
    for (const o of [lfo, lfo2]) { o.start(t0); o.stop(t1 + 0.1); }
  }
}
// riser: noise sweep + rising sine, builds to a peak at t + dur
export function riser(m, out, t, dur, { gain = 0.08, f0 = 300, f1 = 5000, tone0 = 110, tone1 = 440 } = {}) {
  const c = m.ctx, s = c.createBufferSource(); s.buffer = m.noiseLong; s.start(t, m.rand() * 4); s.stop(t + dur + 0.3);
  const bp = c.createBiquadFilter(), g = c.createGain(); bp.type = 'bandpass'; bp.Q.value = 1.1;
  bp.frequency.setValueAtTime(f0, t); bp.frequency.exponentialRampToValueAtTime(f1, t + dur);
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(gain, t + dur); g.gain.exponentialRampToValueAtTime(0.0001, t + dur + 0.25);
  s.connect(bp); bp.connect(g); g.connect(out);
  const o = c.createOscillator(), og = c.createGain(); o.type = 'sine'; o.frequency.setValueAtTime(tone0, t); o.frequency.exponentialRampToValueAtTime(tone1, t + dur);
  og.gain.setValueAtTime(0.0001, t); og.gain.exponentialRampToValueAtTime(gain * 0.4, t + dur); og.gain.exponentialRampToValueAtTime(0.0001, t + dur + 0.2);
  o.connect(og); og.connect(out); o.start(t); o.stop(t + dur + 0.3);
}


// ---- drums (for beat-driven pieces) ----
export function kick(m, out, t, { gain = 0.5, f0 = 150, f1 = 46, dur = 0.42 } = {}) {
  const c = m.ctx, o = c.createOscillator(), g = c.createGain();
  o.type = 'sine'; o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(f1, t + 0.09);
  o.connect(g); g.connect(out); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(gain, t + 0.003); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.start(t); o.stop(t + dur + 0.05);
  const s = noiseSrc(m, t, 0.012), hp = c.createBiquadFilter(), cg = c.createGain(); hp.type = 'highpass'; hp.frequency.value = 2500;
  s.connect(hp); hp.connect(cg); cg.connect(out); env(cg, t, { a: 0.001, d: 0.012, peak: gain * 0.25 });
}
export function clap(m, out, t, { gain = 0.16, pan = 0 } = {}) {
  const c = m.ctx, bp = c.createBiquadFilter(), g = c.createGain(); bp.type = 'bandpass'; bp.frequency.value = 1500; bp.Q.value = 0.9;
  bp.connect(g); panTo(m, g, pan).connect(out);
  g.gain.setValueAtTime(0.0001, t);
  for (const k of [0, 0.011, 0.022]) { g.gain.setValueAtTime(gain, t + k); g.gain.exponentialRampToValueAtTime(gain * 0.25, t + k + 0.009); }
  g.gain.setValueAtTime(gain * 0.8, t + 0.033); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.2);
  const s = noiseSrc(m, t, 0.22); s.connect(bp);
}
export function snare(m, out, t, { gain = 0.12, dur = 0.14 } = {}) {
  const c = m.ctx, s = noiseSrc(m, t, dur), bp = c.createBiquadFilter(), g = c.createGain(); bp.type = 'bandpass'; bp.frequency.value = 2000; bp.Q.value = 0.7;
  s.connect(bp); bp.connect(g); g.connect(out); env(g, t, { a: 0.001, d: dur, peak: gain });
  const o = c.createOscillator(), og = c.createGain(); o.frequency.setValueAtTime(240, t); o.frequency.exponentialRampToValueAtTime(170, t + 0.05); o.connect(og); og.connect(out); env(og, t, { a: 0.001, d: 0.08, peak: gain * 0.6 }); o.start(t); o.stop(t + 0.12);
}
export function crash(m, out, t, { gain = 0.08, dur = 2.2 } = {}) {
  const c = m.ctx, s = c.createBufferSource(); s.buffer = m.noiseLong; s.start(t, m.rand() * 4); s.stop(t + dur + 0.1);
  const hp = c.createBiquadFilter(), g = c.createGain(); hp.type = 'highpass'; hp.frequency.value = 4200;
  s.connect(hp); hp.connect(g); g.connect(out); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(gain, t + 0.004); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
}
// a heavy landing: kick + sub tail + short low noise slap
export function impact(m, out, t, { gain = 0.5 } = {}) {
  kick(m, out, t, { gain, f0: 120, f1: 38, dur: 1.1 });
  const c = m.ctx, s = noiseSrc(m, t, 0.25), lp = c.createBiquadFilter(), g = c.createGain(); lp.type = 'lowpass'; lp.frequency.value = 900;
  s.connect(lp); lp.connect(g); g.connect(out); env(g, t, { a: 0.002, d: 0.25, peak: gain * 0.35 });
}

// ---- voice-over ----
// play a decoded clip (m.vo[name]) at time t; returns its end time
export function voice(m, t, name, { gain = 1, pan = 0 } = {}) {
  const buf = m.vo[name]; if (!buf) { console.warn('voice clip missing: ' + name); return t; }
  const s = m.ctx.createBufferSource(), g = m.ctx.createGain(); s.buffer = buf; g.gain.value = gain;
  s.connect(g); panTo(m, g, pan).connect(m.voice); s.start(t); return t + buf.duration;
}
// lower a bus during [a, b] regions (e.g. music under the voice): depth in dB, ramps in seconds
export function duck(bus, regions, { depth = -9, attack = 0.12, release = 0.35, base = null } = {}) {
  const g0 = base ?? bus.gain.value, low = g0 * Math.pow(10, depth / 20);
  for (const [a, b] of regions) { bus.gain.setValueAtTime(g0, Math.max(0, a - attack)); bus.gain.linearRampToValueAtTime(low, a); bus.gain.setValueAtTime(low, b); bus.gain.linearRampToValueAtTime(g0, b + release); }
}
async function decodeVo(map) {
  const out = {}, ctx = new OfflineAudioContext(2, 48000, 48000);
  for (const [k, b64] of Object.entries(map || {})) {
    const bin = atob(b64), u8 = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    out[k] = await ctx.decodeAudioData(u8.buffer);
  }
  return out;
}

// ---- render, measure, limit ----
export async function render(duration, build, sampleRate = 48000, stem = null, mixOpts = {}, vo = {}) {
  const ctx = new OfflineAudioContext(2, Math.ceil(duration * sampleRate), sampleRate);
  const m = makeMixer(ctx, mixOpts);
  m.vo = vo;
  if (stem) for (const k of ['music', 'sfx', 'voice']) if (k !== stem) m[k].mute.gain.value = 0;
  build(m);
  return ctx.startRendering();
}

function biquad(x, b, a) {
  const y = new Float32Array(x.length); let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  for (let i = 0; i < x.length; i++) { const v = b[0] * x[i] + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2; x2 = x1; x1 = x[i]; y2 = y1; y1 = v; y[i] = v; }
  return y;
}
// ITU-R BS.1770 integrated loudness (48 kHz coefficients)
export function lufs(buf) {
  const sr = buf.sampleRate, chans = [];
  for (let c = 0; c < buf.numberOfChannels; c++) {
    let x = buf.getChannelData(c);
    x = biquad(x, [1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585]);
    x = biquad(x, [1, -2, 1], [1, -1.99004745483398, 0.99007225036621]);
    chans.push(x);
  }
  const blk = Math.round(0.4 * sr), step = Math.round(0.1 * sr), zs = [];
  for (let s = 0; s + blk <= chans[0].length; s += step) {
    let z = 0; for (const x of chans) { let acc = 0; for (let i = s; i < s + blk; i++) acc += x[i] * x[i]; z += acc / blk; }
    zs.push(z);
  }
  const L = (z) => -0.691 + 10 * Math.log10(z);
  const abs = zs.filter((z) => L(z) > -70); if (!abs.length) return -Infinity;
  const rel = L(abs.reduce((a, b) => a + b, 0) / abs.length) - 10;
  const g = abs.filter((z) => L(z) > rel);
  return L(g.reduce((a, b) => a + b, 0) / g.length);
}
// momentary loudness (400 ms K-weighted window) every `hop` seconds
export function momentary(buf, hop = 0.1) {
  const sr = buf.sampleRate, chans = [];
  for (let c = 0; c < buf.numberOfChannels; c++) {
    let x = buf.getChannelData(c);
    x = biquad(x, [1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585]);
    x = biquad(x, [1, -2, 1], [1, -1.99004745483398, 0.99007225036621]);
    chans.push(x);
  }
  const blk = Math.round(0.4 * sr), st = Math.round(hop * sr), out = [];
  for (let s = 0; s + blk <= chans[0].length; s += st) {
    let z = 0; for (const x of chans) { let acc = 0; for (let i = s; i < s + blk; i += 2) acc += x[i] * x[i]; z += acc / (blk / 2); }
    out.push(+(-0.691 + 10 * Math.log10(z + 1e-12)).toFixed(1));
  }
  return out;
}
export function peakDb(buf) { let p = 0; for (let c = 0; c < buf.numberOfChannels; c++) for (const v of buf.getChannelData(c)) p = Math.max(p, Math.abs(v)); return 20 * Math.log10(p); }

export function normalize(buf, target = -16, ceilingDb = -1.5) {
  const gain = Math.pow(10, (target - lufs(buf)) / 20), ceil = Math.pow(10, ceilingDb / 20), sr = buf.sampleRate, n = buf.length;
  const ch = [...Array(buf.numberOfChannels)].map((_, c) => buf.getChannelData(c));
  const need = new Float32Array(n);
  for (let i = 0; i < n; i++) { let p = 0; for (const x of ch) p = Math.max(p, Math.abs(x[i] * gain)); need[i] = p > ceil ? ceil / p : 1; }
  const look = Math.round(0.005 * sr), rel = 1 - Math.exp(-1 / (0.08 * sr));
  const g = new Float32Array(n); let cur = 1;
  for (let i = 0; i < n; i++) { let m = 1; for (let k = i; k < Math.min(n, i + look); k += 8) m = Math.min(m, need[k]); m = Math.min(m, need[Math.min(n - 1, i + look - 1)]); cur = m < cur ? m : cur + (m - cur) * rel; g[i] = cur; }
  for (const x of ch) for (let i = 0; i < n; i++) x[i] = x[i] * gain * g[i];
  return { gain, lufs: lufs(buf), peak: peakDb(buf) };
}

// ---- Opus in WebM ----
function ebml() {
  const parts = [];
  const id = (n) => { const b = []; while (n > 0) { b.unshift(n & 255); n = Math.floor(n / 256); } return b; };
  const size = (n) => { const b = [0x01]; for (let i = 6; i >= 0; i--) b.push(Math.floor(n / 2 ** (8 * i)) & 255); return b; };
  const el = (i, payload) => { const p = payload instanceof Uint8Array ? payload : new Uint8Array(payload); const h = [...id(i), ...size(p.length)]; const out = new Uint8Array(h.length + p.length); out.set(h); out.set(p, h.length); return out; };
  const uint = (i, v) => { const b = []; do { b.unshift(v & 255); v = Math.floor(v / 256); } while (v > 0); return el(i, b); };
  const flt = (i, v) => { const d = new DataView(new ArrayBuffer(8)); d.setFloat64(0, v); return el(i, new Uint8Array(d.buffer)); };
  const str = (i, s) => el(i, [...new TextEncoder().encode(s)]);
  const cat = (...a) => { const n = a.reduce((s, x) => s + x.length, 0), o = new Uint8Array(n); let k = 0; for (const x of a) { o.set(x, k); k += x.length; } return o; };
  return { el, uint, flt, str, cat };
}

export async function encodeWebmOpus(buf, bitrate = 160000) {
  const chunks = []; let desc = null;
  const enc = new AudioEncoder({ output: (c, meta) => { const d = new Uint8Array(c.byteLength); c.copyTo(d); chunks.push({ ts: c.timestamp, data: d }); if (meta?.decoderConfig?.description) desc = new Uint8Array(meta.decoderConfig.description); }, error: (e) => { throw e; } });
  enc.configure({ codec: 'opus', sampleRate: buf.sampleRate, numberOfChannels: buf.numberOfChannels, bitrate });
  const N = 4800, chans = buf.numberOfChannels;
  for (let s = 0; s < buf.length; s += N) {
    const n = Math.min(N, buf.length - s), data = new Float32Array(n * chans);
    for (let c = 0; c < chans; c++) data.set(buf.getChannelData(c).subarray(s, s + n), c * n);
    enc.encode(new AudioData({ format: 'f32-planar', sampleRate: buf.sampleRate, numberOfFrames: n, numberOfChannels: chans, timestamp: Math.round((s / buf.sampleRate) * 1e6), data }));
  }
  await enc.flush(); enc.close();
  if (!desc || String.fromCharCode(...desc.slice(0, 8)) !== 'OpusHead') {
    const d = new DataView(new ArrayBuffer(19)); [...'OpusHead'].forEach((ch, i) => d.setUint8(i, ch.charCodeAt(0)));
    d.setUint8(8, 1); d.setUint8(9, chans); d.setUint16(10, 312, true); d.setUint32(12, buf.sampleRate, true); d.setInt16(16, 0, true); d.setUint8(18, 0);
    desc = new Uint8Array(d.buffer);
  }
  const preskip = desc[10] | (desc[11] << 8);
  const E = ebml();
  const header = E.el(0x1a45dfa3, E.cat(E.uint(0x4286, 1), E.uint(0x42f7, 1), E.uint(0x42f2, 4), E.uint(0x42f3, 8), E.str(0x4282, 'webm'), E.uint(0x4287, 4), E.uint(0x4285, 2)));
  const info = E.el(0x1549a966, E.cat(E.uint(0x2ad7b1, 1000000), E.str(0x4d80, 'video-craft'), E.str(0x5741, 'video-craft'), E.flt(0x4489, buf.duration * 1000)));
  const track = E.el(0xae, E.cat(E.uint(0xd7, 1), E.uint(0x73c5, 1), E.uint(0x83, 2), E.str(0x86, 'A_OPUS'), E.el(0x63a2, desc),
    E.uint(0x56aa, Math.round((preskip / 48000) * 1e9)), E.uint(0x56bb, 80000000), E.el(0xe1, E.cat(E.flt(0xb5, buf.sampleRate), E.uint(0x9f, chans)))));
  const tracks = E.el(0x1654ae6b, track);
  const clusters = []; let i = 0;
  while (i < chunks.length) {
    const base = Math.round(chunks[i].ts / 1000), blocks = [E.uint(0xe7, base)];
    while (i < chunks.length && Math.round(chunks[i].ts / 1000) - base < 5000) {
      const rel = Math.round(chunks[i].ts / 1000) - base, b = new Uint8Array(4 + chunks[i].data.length);
      b[0] = 0x81; b[1] = (rel >> 8) & 255; b[2] = rel & 255; b[3] = 0x80; b.set(chunks[i].data, 4);
      blocks.push(E.el(0xa3, b)); i++;
    }
    clusters.push(E.el(0x1f43b675, E.cat(...blocks)));
  }
  const segment = E.el(0x18538067, E.cat(info, tracks, ...clusters));
  return E.cat(header, segment);
}

export function toWav(buf) {
  const n = buf.length, ch = buf.numberOfChannels, d = new DataView(new ArrayBuffer(44 + n * ch * 2));
  const w = (o, s) => [...s].forEach((c, i) => d.setUint8(o + i, c.charCodeAt(0)));
  w(0, 'RIFF'); d.setUint32(4, 36 + n * ch * 2, true); w(8, 'WAVE'); w(12, 'fmt '); d.setUint32(16, 16, true); d.setUint16(20, 1, true); d.setUint16(22, ch, true);
  d.setUint32(24, buf.sampleRate, true); d.setUint32(28, buf.sampleRate * ch * 2, true); d.setUint16(32, ch * 2, true); d.setUint16(34, 16, true); w(36, 'data'); d.setUint32(40, n * ch * 2, true);
  const cs = [...Array(ch)].map((_, c) => buf.getChannelData(c));
  for (let i = 0, o = 44; i < n; i++) for (let c = 0; c < ch; c++, o += 2) d.setInt16(o, Math.max(-1, Math.min(1, cs[c][i])) * 32767, true);
  return new Uint8Array(d.buffer);
}

const b64 = (u8) => { let s = ''; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode(...u8.subarray(i, i + 0x8000)); return btoa(s); };

// entry used by kit/audio.mjs
// score(m, events, duration): m has buses m.music / m.sfx / m.voice and decoded voice clips in m.vo
export function install(score, mixOpts = {}) {
  const stems = (vo) => ['music', 'sfx', ...(Object.keys(vo).length ? ['voice'] : [])];
  window.__stems = async (events, duration, opts = {}) => {
    const vo = await decodeVo(opts.vo), out = {};
    for (const stem of stems(vo)) { const b = await render(duration, (m) => score(m, events, duration), 48000, stem, mixOpts, vo); out[stem] = { lufs: lufs(b), peak: peakDb(b) }; }
    return out;
  };
  window.__mixcheck = async (events, duration, opts = {}) => {
    const vo = await decodeVo(opts.vo), out = {};
    for (const stem of [...stems(vo), null]) { const b = await render(duration, (m) => score(m, events, duration), 48000, stem, mixOpts, vo); out[stem || 'mix'] = momentary(b); }
    return out;
  };
  window.__renderAudio = async (events, duration, opts = {}) => {
    const vo = await decodeVo(opts.vo);
    const buf = await render(duration, (m) => score(m, events, duration), 48000, null, mixOpts, vo);
    const raw = { lufs: lufs(buf), peak: peakDb(buf) };
    const st = normalize(buf, opts.target ?? -16, opts.ceiling ?? -1.5);
    const webm = await encodeWebmOpus(buf);
    return { raw, ...st, webm: b64(webm), wav: opts.wav ? b64(toWav(buf)) : null };
  };
}
