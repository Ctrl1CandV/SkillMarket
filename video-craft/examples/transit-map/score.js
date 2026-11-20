// score.js — transit-map: 120 BPM (beat 0.5 s, bar 2 s), 9 bars.
// Arc: light pulse under the opening question → the groove arrives with the street map at 4.0 → drums drop out while
// the lines straighten (a riser carries it) → back in for one bar → soft ending under the rule.
import { NOTE, pluck, bass, tick, pop, chime, whoosh, hat, warmPad, riser, kick, clap, impact, install } from '../../kit/sound.js';

const B = 0.5;
const CH = { Am: { bass: 'A2', pad: ['A3', 'C4', 'E4'], arp: ['A4', 'C5', 'E5', 'G5'] }, F: { bass: 'F2', pad: ['A3', 'C4', 'F4'], arp: ['A4', 'C5', 'F5', 'A5'] },
  C: { bass: 'C2', pad: ['G3', 'C4', 'E4'], arp: ['G4', 'C5', 'E5', 'G5'] }, G: { bass: 'G2', pad: ['B3', 'D4', 'G4'], arp: ['B4', 'D5', 'G5', 'B5'] } };
// [bar start, chord, section]
const PLAN = [[0, 'Am', 'intro'], [2, 'F', 'intro'], [4, 'Am', 'groove'], [6, 'F', 'groove'], [8, 'C', 'groove'],
  [10, 'G', 'break'], [12, 'Am', 'groove'], [14, 'F', 'end'], [16, 'C', 'end']];

function score(m, events, duration) {
  const c = m.ctx, MU = m.music, S = c.createGain();
  MU.gain.value = 0.6; S.gain.value = 2.0; S.connect(m.sfx);
  m.master.gain.setValueAtTime(1, duration - 1.2); m.master.gain.linearRampToValueAtTime(0, duration);
  for (const [t0, name, sec] of PLAN) {
    const ch = CH[name];
    warmPad(m, MU, t0, t0 + 2.2, ch.pad.map(NOTE), { gain: sec === 'break' ? 0.03 : 0.022, attack: 0.3, release: 0.6, cutoff: sec === 'intro' ? 900 : 1500 });
    for (let k = 0; k < 16; k++) {
      const t = t0 + k * B / 4, beat = k % 4 === 0;
      if (sec === 'groove') {
        if (beat) kick(m, MU, t, { gain: 0.4 });
        if (beat && k % 8 === 4) clap(m, MU, t, { gain: 0.1 });
        if (k % 2 === 1) hat(m, MU, t, { gain: k % 4 === 2 ? 0.03 : 0.014 });
        if ([0, 3, 6, 10].includes(k)) bass(m, MU, t, NOTE(ch.bass), { dur: 0.18, gain: 0.12 });
      }
      if (sec === 'intro' && k % 2 === 0) hat(m, MU, t, { gain: 0.012 });
      if (sec !== 'end' && k % 2 === 0) pluck(m, MU, t, NOTE(ch.arp[(k / 2) % 4]), { dur: 0.25, gain: sec === 'intro' ? 0.022 : 0.028, bright: 3200, pan: k % 4 ? 0.25 : -0.25 });
      if (sec === 'end' && beat) pluck(m, MU, t, NOTE(ch.arp[(k / 4) % 4]), { dur: 1.0, gain: 0.035, bright: 2400 });
    }
    if (sec === 'break' || sec === 'end') bass(m, MU, t0, NOTE(ch.bass), { dur: 1.6, gain: 0.08 });
  }
  for (const e of events) {
    const t = e.t;
    switch (e.type) {
      case 'rise': whoosh(m, S, t, { dur: 0.5, f0: 900, f1: 2600, gain: 0.025 }); break;
      case 'tick': tick(m, S, t, { freq: 2600, gain: 0.05 }); tick(m, S, t + 0.06, { freq: 3100, gain: 0.04 }); break;
      case 'wipe': whoosh(m, S, t, { dur: 0.6, f0: 500, f1: 3000, gain: 0.06, peakAt: 0.55, pan0: -0.6, pan1: 0.6 }); impact(m, S, t + 0.35, { gain: 0.12 }); break;
      case 'line': pop(m, S, t, { f0: 400, f1: 700 + e.i * 160, gain: 0.05, pan: [-0.3, 0, 0.3][e.i] }); break;
      case 'mark': pluck(m, S, t, NOTE('E6'), { dur: 0.3, gain: 0.04, bright: 5000, type: 'sine' }); pluck(m, S, t + 0.15, NOTE('A6'), { dur: 0.3, gain: 0.04, bright: 5000, type: 'sine' }); break;
      case 'measure': for (let k = 0; k < 8; k++) tick(m, S, t + k * (e.dur / 8), { freq: 2000 + k * 120, gain: 0.03 }); break;
      case 'walk': for (let k = 0; k * 0.25 < e.dur; k++) tick(m, S, t + k * 0.25, { freq: 900 + (k % 2) * 140, gain: 0.05, dur: 0.03, pan: k % 2 ? 0.2 : -0.2 }); break;
      case 'arrive': pluck(m, S, t, NOTE('A5'), { dur: 0.6, gain: 0.06, bright: 4000 }); pluck(m, S, t + 0.1, NOTE('E6'), { dur: 0.6, gain: 0.05, bright: 4000 }); break;
      case 'morph': riser(m, S, t, e.dur, { gain: 0.05, f0: 300, f1: 4200, tone0: 220, tone1: 660 }); break;
      case 'step': pluck(m, S, t, NOTE(['C6', 'E6'][e.k]), { dur: 0.5, gain: 0.06, bright: 4500 }); bass(m, S, t, NOTE(['C3', 'E3'][e.k]), { dur: 0.3, gain: 0.08 }); break;
      case 'iris': whoosh(m, S, t, { dur: e.dur, f0: 2800, f1: 600, gain: 0.05, peakAt: 0.4 }); break;
      case 'land': chime(m, S, t, NOTE('A5'), { gain: 0.03, dur: 1.6 }); break;
      case 'end': chime(m, S, t, NOTE('E6'), { gain: 0.025, dur: 2.2 }); chime(m, S, t + 0.12, NOTE('A6'), { gain: 0.02, dur: 2.2 }); break;
    }
  }
}
install(score, { reverb: 0.14, irSec: 1.4, irPow: 3.0 });
