import { bass, hat, install, kick, NOTE, piano, pluck, tick, tone, warmPad, wind } from '../../kit/sound.js';
import { PHRASES } from './phrases.js';

const [call, lift, below, reprise] = PHRASES;
const CHORDS = [
  [call.t, 'A2', 'C3 E3 B3'],
  [call.t + 2.5, 'F2', 'A3 C4 E4'],
  [lift.t, 'A2', 'C3 E3 B3'],
  [lift.t + 2.5, 'G2', 'B3 D4 A3'],
  [below.t, 'D2', 'A3 C4 F4'],
  [below.t + 2.5, 'F2', 'A3 C4 G4'],
  [reprise.t, 'A2', 'C3 E3 B3'],
  [reprise.t + 2.5, 'C3', 'G3 D4 E4'],
];

function score(m, events, duration) {
  const { music, master } = m;
  master.gain.setValueAtTime(1, duration - 0.5);
  master.gain.linearRampToValueAtTime(0, duration);
  wind(m, music, 0, duration, { gain: 0.009, center: 340, fadeIn: 0.6, fadeOut: 0.9 });

  CHORDS.forEach(([start, root, notes], index) => {
    const end = CHORDS[index + 1]?.[0] ?? duration;
    const submerged = start >= below.t && start < reprise.t;
    warmPad(m, music, start, end + 0.3, notes.split(' ').map(NOTE), {
      gain: submerged ? 0.032 : 0.044, cutoff: submerged ? 410 : 1100, attack: 0.36, release: 0.65,
    });
    tone(m, music, start, end + 0.1, NOTE(root), {
      gain: submerged ? 0.05 : 0.027, attack: 0.4, release: 0.6,
    });
    if (submerged) return;
    bass(m, music, start + 0.05, NOTE(root), { gain: 0.12, dur: 0.75 });
    bass(m, music, start + 1.52, NOTE(root) * 2, { gain: 0.058, dur: 0.32 });
  });

  for (const { t, note, weight } of events.filter((event) => event.type === 'note')) {
    const submerged = t >= below.t && t < reprise.t;
    const hz = NOTE(note);
    piano(m, music, t, hz, { gain: (submerged ? 0.16 : 0.15) * weight, dur: submerged ? 2.4 : 1.35, bright: submerged ? 0.5 : 0.95 });
    if (!submerged) pluck(m, music, t, hz, { gain: 0.072 * weight, dur: 0.48, bright: 3200 });
    if (t >= reprise.t && t < 18) {
      pluck(m, music, t + 0.31, hz / 2, { gain: 0.034 * weight, dur: 0.57, bright: 1900, pan: -0.45 });
      pluck(m, music, t + 0.47, hz, { gain: 0.016 * weight, dur: 0.58, bright: 3100, pan: 0.53 });
    }
  }

  for (const start of [lift.t, lift.t + 2.5, reprise.t, reprise.t + 2.5]) {
    kick(m, music, start, { gain: 0.28, f1: 58, dur: 0.35 });
    kick(m, music, start + 1.55, { gain: 0.14, f1: 67, dur: 0.25 });
    for (const [offset, pan] of [[0.32, -0.32], [0.95, 0.26], [1.27, -0.1], [2.19, 0.32]]) {
      tick(m, music, start + offset, { gain: 0.045, freq: 3300, pan });
    }
    hat(m, music, start + 1.88, { gain: 0.022, dur: 0.08 });
  }
}

install(score, { reverb: 0.26, irSec: 2.6, irPow: 2.8, seed: 23 });
