// score.js — sound for "天空为什么是蓝的". Sound follows the physics:
// every colour has a pitch (red lowest, violet highest); white light is all six pitches at once;
// a beam that loses its blue loses its high notes; blue scattering rings, red is 1/5.9 as loud.
import { NOTE, chime, pop, whoosh, glide, piano, tone, warmPad, wind, riser, install } from '../../kit/sound.js';
import { rng } from '../../kit/kit.js';

const PRISM = [ // 700, 610, 575, 530, 450, 410 nm
  { nm: 700, note: 'D4', pan: -0.6 }, { nm: 610, note: 'F#4', pan: -0.36 }, { nm: 575, note: 'A4', pan: -0.12 },
  { nm: 530, note: 'B4', pan: 0.12 }, { nm: 450, note: 'F#5', pan: 0.36 }, { nm: 410, note: 'A5', pan: 0.6 },
].map((p) => ({ ...p, f: NOTE(p.note) }));
const BLUE_SET = ['F#5', 'A5', 'B5', 'D6', 'E6', 'F#6'].map(NOTE);
const HIGH_SET = ['F#6', 'A6', 'B6', 'D7', 'E7'].map(NOTE);
const RAY_SET = ['A4', 'B4', 'D5', 'E5', 'F#5', 'A5', 'B5', 'D6', 'E6', 'F#6', 'A6', 'B6', 'D7', 'E7'].map(NOTE);

// [t0, t1, bass, pad notes, cutoff]
const CHORDS = [
  [0.0, 5.9, 'D2', ['D3', 'A3', 'E4', 'F#4'], 1000],
  [5.4, 11.6, 'G2', ['B3', 'D4', 'F#4', 'A4'], 1100],
  [11.0, 16.8, 'E2', ['G3', 'B3', 'D4', 'F#4'], 800],
  [16.3, 20.6, 'B1', ['D4', 'F#4', 'A4', 'C#5'], 850],
  [20.1, 24.5, 'G2', ['B3', 'D4', 'F#4', 'A4'], 850],
  [24.0, 27.4, 'E2', ['G3', 'B3', 'D4', 'F#4'], 900],
  [27.0, 30.5, 'A2', ['A3', 'D4', 'E4', 'G4'], 900],
  [30.0, 34.4, 'G2', ['B3', 'D4', 'F#4', 'A4'], 1100],
  [34.0, 36.8, 'D2', ['D4', 'F#4', 'A4', 'E5'], 1400],
  [36.2, 38.9, 'B1', ['D4', 'F#4', 'A4', 'C#5'], 1100],
  [38.5, 41.2, 'G2', ['B3', 'D4', 'E4', 'A4'], 1000],
  [40.6, 43.6, 'E2', ['G3', 'B3', 'D4', 'F#4'], 1200],
  [49.6, 54.2, 'G2', ['B3', 'D4', 'F#4', 'A4'], 1000],
  [53.8, 55.6, 'A2', ['A3', 'C#4', 'E4', 'G4'], 1000],
  [55.2, 59.2, 'D2', ['D3', 'A3', 'E4', 'F#4', 'C#5'], 1200],
];
// [t, note, velocity]; the opening phrase (A D E F#) is answered at the end
const MELODY = [
  [0.6, 'A4', 0.8], [1.44, 'D5', 0.9], [2.28, 'E5', 0.85], [3.12, 'F#5', 1.0], [4.8, 'E5', 0.6],
  [5.6, 'B4', 0.7], [6.44, 'D5', 0.75], [7.28, 'A5', 0.8],
  [12.4, 'G4', 0.6], [13.24, 'B4', 0.6], [14.08, 'F#5', 0.7], [15.6, 'E5', 0.5],
  [20.2, 'D5', 0.55], [21.04, 'F#5', 0.6], [21.88, 'A5', 0.55], [23.0, 'B4', 0.45],
  [30.9, 'B4', 0.6], [31.74, 'D5', 0.65],
  [34.0, 'D4', 0.7], [34.0, 'F#4', 0.6], [34.02, 'A4', 0.7], [34.04, 'D5', 0.9], [34.84, 'E5', 0.6], [35.68, 'F#5', 0.7],
  [36.6, 'F#5', 0.8], [37.44, 'E5', 0.7], [38.28, 'D5', 0.7], [39.12, 'B4', 0.65], [39.96, 'A4', 0.55],
  [52.6, 'A4', 0.7], [53.44, 'D5', 0.8], [54.28, 'E5', 0.8],
  [55.2, 'A3', 0.6], [55.2, 'D4', 0.7], [55.22, 'F#5', 1.0], [55.55, 'A5', 0.7], [55.9, 'D6', 0.6],
];

function shimmer(m, out, t0, t1, set, { rate = 4, gain = 0.012, seed = 1 } = {}) {
  const r = rng(seed);
  for (let t = t0; t < t1; t += (0.5 + r()) / rate) {
    const fade = Math.min(1, (t - t0) / 0.8, (t1 - t) / 0.8);
    chime(m, out, t, set[Math.floor(r() * set.length)], { gain: gain * fade * (0.6 + 0.4 * r()), dur: 1.1, pan: (r() - 0.5) * 1.4 });
  }
}

function score(m, events, duration) {
  const c = m.ctx, MU = m.music, S = m.sfx;
  // master: no click at the start, fade with the end card
  m.master.gain.setValueAtTime(0, 0); m.master.gain.linearRampToValueAtTime(1, 0.12);
  m.master.gain.setValueAtTime(1, duration - 1.4); m.master.gain.linearRampToValueAtTime(0, duration);

  // ---- music ----
  // the music bed steps back (about 4 dB) wherever an effect carries the explanation
  MU.gain.value = 0.8;
  for (const [a, b] of [[16.1, 18.2], [24.2, 30.3], [31.9, 33.4], [40.5, 43.5], [44.9, 46.8], [49.5, 52.3]]) {
    MU.gain.setValueAtTime(0.8, a); MU.gain.linearRampToValueAtTime(0.5, a + 0.3); MU.gain.setValueAtTime(0.5, b - 0.4); MU.gain.linearRampToValueAtTime(0.8, b);
  }
  for (const [t0, t1, b, notes, cutoff] of CHORDS) {
    warmPad(m, MU, t0, t1, notes.map(NOTE), { gain: 0.028, attack: t0 === 0 ? 1.0 : 0.9, release: 0.9, cutoff });
    tone(m, MU, t0, t1, NOTE(b), { gain: 0.035, attack: 0.8, release: 0.9 });
  }
  // space: open fifth drone, nearly silent
  tone(m, MU, 43.2, 50.2, NOTE('D2'), { gain: 0.02, attack: 1.2, release: 1.4 });
  tone(m, MU, 43.2, 50.2, NOTE('A2'), { gain: 0.012, attack: 1.6, release: 1.4 });
  warmPad(m, MU, 43.6, 50.0, ['A4', 'E5'].map(NOTE), { gain: 0.012, attack: 2.0, release: 1.6, cutoff: 1800 });
  const hr = rng(3);
  for (const [t, n, v] of MELODY) piano(m, MU, t + (hr() - 0.5) * 0.02, NOTE(n), { gain: 0.075 * v, dur: 3.4, pan: (NOTE(n) > 500 ? 0.15 : -0.15) });

  // ---- sound effects ----
  wind(m, S, 0, 12.6, { gain: 0.065, fadeIn: 0.4, fadeOut: 1.8, center: 620 });
  wind(m, S, 11.2, 30.8, { gain: 0.03, fadeIn: 1.4, fadeOut: 1.0, center: 240 });   // room tone inside the air
  wind(m, S, 30.2, 42.8, { gain: 0.05, fadeIn: 1.0, fadeOut: 2.2, center: 620 });
  wind(m, S, 50.8, 59, { gain: 0.045, fadeIn: 1.8, fadeOut: 1.2, center: 520 });

  let ray = 0;
  for (const e of events) {
    const t = e.t;
    switch (e.type) {
      case 'beam': {
        // white light = all six pitches together; they split, then thin out to red and blue
        for (const p of PRISM) {
          const keep = p.nm === 700 || p.nm === 450, g = tone(m, S, t, keep ? 24.7 : 16.2, p.f, { gain: 0.016, attack: e.dur, release: keep ? 0.7 : 0.8, pan: 0, pan1: null });
          g.gain.setValueAtTime(0.016, 10.4); g.gain.linearRampToValueAtTime(0.006, 12.4);
          if (keep) { g.gain.setValueAtTime(0.006, 15.4); g.gain.linearRampToValueAtTime(0.008, 16.4); }
        }
        whoosh(m, S, t, { dur: e.dur, f0: 1200, f1: 6000, gain: 0.02, peakAt: 0.8 });
        break;
      }
      case 'split': PRISM.forEach((p, i) => chime(m, S, t + 0.05 + i * 0.13, p.f * 2, { gain: 0.06, dur: 1.8, pan: p.pan })); break;
      case 'zoomin': whoosh(m, S, t, { dur: e.dur, f0: 280, f1: 2600, gain: 0.07, peakAt: 0.8 }); break;
      case 'labels': pop(m, S, t + 0.1, { f0: 500, f1: 900, gain: 0.025, pan: -0.2 }); pop(m, S, t + 0.25, { f0: 520, f1: 980, gain: 0.025, pan: 0.2 }); break;
      case 'separate': whoosh(m, S, t, { dur: 0.9, f0: 600, f1: 1800, gain: 0.02 }); break;
      case 'ring':
        if (e.color === 'blue') chime(m, S, t, BLUE_SET[Math.floor((e.pan + 1) * 2.99)], { gain: 0.07, dur: 1.6, pan: e.pan });
        else chime(m, S, t, NOTE('D4'), { gain: 0.07 / 5.9, dur: 1.6, pan: e.pan });
        break;
      case 'panels': whoosh(m, S, t, { dur: 0.7, f0: 1800, f1: 500, gain: 0.025, peakAt: 0.4 }); break;
      case 'pring': {
        const fade = Math.min(1, (30.6 - t) / 1.0);
        chime(m, S, t, NOTE('F#5'), { gain: 0.08 * fade, dur: 1.2, pan: -0.55 });
        chime(m, S, t, NOTE('D4'), { gain: (0.08 / 5.9) * fade, dur: 1.2, pan: 0.55 });
        break;
      }
      case 'meter': glide(m, S, t, NOTE('D4'), NOTE('F#5'), { dur: e.dur, gain: 0.025, type: 'sine' }); pop(m, S, t + e.dur, { f0: 500, f1: 1100, gain: 0.035 }); break;
      case 'pullout': whoosh(m, S, t, { dur: e.dur, f0: 2600, f1: 300, gain: 0.07, peakAt: 0.35 }); break;
      case 'sparks': shimmer(m, S, t, 36.2, HIGH_SET, { rate: 6, gain: 0.009, seed: 11 }); break;
      case 'ray': chime(m, S, t, RAY_SET[ray++ % RAY_SET.length], { gain: 0.06, dur: 1.4, pan: e.pan * 0.5 + 0.2 }); break;
      case 'resolve': tone(m, S, t, 36.4, NOTE('D2'), { gain: 0.03, attack: 0.3, release: 1.6 }); break;
      case 'timelapse': glide(m, S, t, NOTE('A4'), NOTE('D4'), { dur: e.dur, gain: 0.014, type: 'sine' }); break;
      case 'rise': riser(m, S, t, e.dur, { gain: 0.1, f0: 250, f1: 4200, tone0: 110, tone1: 440 }); break;
      case 'space': whoosh(m, S, t + 0.4, { dur: 1.5, f0: 700, f1: 200, gain: 0.015, peakAt: 0.3 }); break;
      case 'noonbeam': for (const p of PRISM) tone(m, S, t, 47.2, p.f, { gain: 0.007, attack: 0.25, release: 1.2 }); break;
      case 'sunsetbeam': {
        // the beam loses violet, blue, green, yellow, orange in turn; red keeps going
        const lose = [null, 46.35, 46.25, 46.15, 46.05, 45.95];
        PRISM.forEach((p, i) => {
          const end = lose[i] ? lose[i] + 0.25 : 50.2;
          tone(m, S, t, end, p.f, { gain: i === 0 ? 0.016 : 0.011, attack: 0.5, release: lose[i] ? 0.25 : 1.2 });
        });
        shimmer(m, S, 46.0, 49.6, BLUE_SET, { rate: 5, gain: 0.011, seed: 23 });
        break;
      }
      case 'marks': pop(m, S, t, { f0: 420, f1: 820, gain: 0.03, pan: -0.3 }); pop(m, S, t + 0.18, { f0: 380, f1: 700, gain: 0.03, pan: 0.2 }); break;
      case 'dive': whoosh(m, S, t, { dur: e.dur, f0: 3200, f1: 250, gain: 0.14, peakAt: 0.6 }); break;
      case 'land': tone(m, S, t - 0.2, 54.8, NOTE('D2'), { gain: 0.03, attack: 0.5, release: 1.4 }); break;
      case 'end': chime(m, S, t + 0.02, NOTE('D6'), { gain: 0.025, dur: 3.0 }); break;
    }
  }
}
install(score, { reverb: 0.32, irSec: 3.4, irPow: 2.6 });
