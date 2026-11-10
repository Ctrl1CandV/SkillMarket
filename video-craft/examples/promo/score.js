// score.js — 「两清」 promo music + effects, 120 BPM (beat 0.5 s, bar 2 s), 14 bars.
// Arc: muffled, crowded chaos → drop at 4.0 → groove → one-bar break while the web collapses → groove → stamp on bar 11 → soft end.
import { NOTE, pluck, bass, tick, pop, chime, whoosh, hat, glide, warmPad, riser, kick, clap, snare, crash, impact, install } from '../../kit/sound.js';
import { rng } from '../../kit/kit.js';

const B = 0.5, BAR = 2;
const CH = {
  C: { bass: 'C2', pad: ['C4', 'E4', 'G4', 'B4'], arp: ['C5', 'E5', 'G5', 'B5'] },
  G: { bass: 'G2', pad: ['B3', 'D4', 'G4', 'A4'], arp: ['B4', 'D5', 'G5', 'A5'] },
  Am: { bass: 'A2', pad: ['A3', 'C4', 'E4', 'G4'], arp: ['A4', 'C5', 'E5', 'G5'] },
  F: { bass: 'F2', pad: ['A3', 'C4', 'F4', 'G4'], arp: ['A4', 'C5', 'F5', 'G5'] },
};
// [bar start (s), length (s), chord, section]
const PLAN = [
  [0, 2, 'Am', 'chaos'], [2, 1, 'F', 'chaos'], [3, 1, 'G', 'chaos'],
  [4, 2, 'C', 'full'], [6, 2, 'G', 'full'], [8, 2, 'Am', 'full'], [10, 2, 'F', 'light'], [12, 2, 'C', 'full'],
  [14, 2, 'G', 'break'], [16, 2, 'Am', 'full'], [18, 2, 'F', 'full'], [20, 2, 'C', 'full'], [22, 2, 'G', 'light'],
  [24, 2, 'F', 'end'], [26, 2, 'C', 'end'],
];
const ARP16 = [0, 1, 2, 3, 2, 1, 2, 3, 0, 1, 2, 3, 2, 1, 3, 2];
const BASS16 = [0, 3, 6, 8, 11, 14];

function score(m, events, duration) {
  const c = m.ctx, MU = m.music, r = rng(5);
  MU.gain.value = 0.55;                                   // music sits under the interface sounds
  const S = c.createGain(); S.gain.value = 2.2; S.connect(m.sfx);
  m.master.gain.setValueAtTime(0, 0); m.master.gain.linearRampToValueAtTime(1, 0.05);
  m.master.gain.setValueAtTime(1, duration - 1.3); m.master.gain.linearRampToValueAtTime(0, duration);

  // buses: drums go through a low-pass that opens at the drop; pads are side-chained to the kick
  const drumLP = c.createBiquadFilter(); drumLP.type = 'lowpass'; drumLP.frequency.setValueAtTime(520, 0);
  drumLP.frequency.setValueAtTime(520, 3.0); drumLP.frequency.exponentialRampToValueAtTime(7000, 3.98); drumLP.frequency.setValueAtTime(20000, 4.0);
  const drums = c.createGain(); drums.gain.value = 1; drums.connect(drumLP); drumLP.connect(MU);
  const padBus = c.createGain(); padBus.gain.value = 1; padBus.connect(MU);
  const duck = (t) => { padBus.gain.setValueAtTime(0.35, t); padBus.gain.linearRampToValueAtTime(1, t + 0.24); };

  for (const [t0, len, name, sec] of PLAN) {
    const ch = CH[name], t1 = t0 + len;
    warmPad(m, padBus, t0, t1 + 0.25, ch.pad.map(NOTE), { gain: sec === 'end' ? 0.03 : 0.024, attack: sec === 'chaos' && t0 === 0 ? 0.05 : 0.08, release: 0.3, cutoff: sec === 'chaos' ? 900 : 1600, breathe: 0.2 });
    const steps = Math.round(len / (B / 4));
    for (let k = 0; k < steps; k++) {
      const t = t0 + k * B / 4, beat = k % 4 === 0, n = k % 16;
      // drums
      if (sec === 'chaos') { if (beat) kick(m, drums, t, { gain: 0.32 }); hat(m, drums, t, { gain: k % 2 ? 0.012 : 0.02 }); if (t >= 3.0) snare(m, drums, t, { gain: 0.03 + 0.09 * (t - 3.0) }); }
      if (sec === 'full' || sec === 'light') {
        if (beat) { kick(m, drums, t, { gain: 0.42 }); duck(t); }
        if (sec === 'full' && beat && Math.round(t / B) % 2 === 1) clap(m, drums, t, { gain: 0.12 });
        if (k % 4 === 2) hat(m, drums, t, { gain: 0.03 }); else if (k % 2) hat(m, drums, t, { gain: 0.012 });
      }
      // bass
      if (sec !== 'end' && sec !== 'break' && BASS16.includes(n)) bass(m, MU, t, NOTE(ch.bass) * (n === 8 ? 2 : 1), { dur: 0.16, gain: sec === 'chaos' ? 0.08 : 0.11 });
      // arpeggio (louder once the product arrives)
      if (sec === 'full' || sec === 'light') pluck(m, MU, t, NOTE(ch.arp[ARP16[n]]), { dur: 0.22, gain: k % 4 === 0 ? 0.03 : 0.02, bright: 3600, pan: k % 2 ? 0.3 : -0.3 });
      if (sec === 'end' && k % 4 === 0 && k < steps - 2) pluck(m, MU, t, NOTE(ch.arp[(k / 4) % 4]), { dur: 0.9, gain: 0.04, bright: 2600, pan: (k / 4) % 2 ? 0.25 : -0.25 });
    }
    if (sec === 'break') bass(m, MU, t0, NOTE(ch.bass), { dur: 1.4, gain: 0.07 });
    if (sec === 'end') bass(m, MU, t0, NOTE(ch.bass), { dur: 1.6, gain: 0.07 });
  }
  riser(m, MU, 3.0, 1.0, { gain: 0.06, f0: 400, f1: 6000, tone0: 220, tone1: 880 });
  riser(m, MU, 15.0, 1.0, { gain: 0.045, f0: 400, f1: 5000, tone0: 196, tone1: 784 });
  for (const t of [4.0, 16.0]) crash(m, MU, t, { gain: 0.06, dur: 2.4 });

  // ---- effects, from the scene's events ----
  const MSGN = ['A4', 'B4', 'C5', 'D5', 'E5', 'F5', 'G5', 'A5', 'B5', 'C6'].map(NOTE);
  const BOLD = ['D5', 'G5', 'A5', 'C6'].map(NOTE), CHECK = ['C5', 'E5', 'G5', 'C6'].map(NOTE);
  let mi = 0;
  for (const e of events) {
    const t = e.t;
    switch (e.type) {
      case 'msg': pop(m, S, t, { f0: 600, f1: MSGN[Math.min(9, mi)] * 2, gain: 0.14, dur: 0.08, pan: mi % 2 ? 0.35 : 0.1 }); tick(m, S, t, { freq: 3200, gain: 0.04 }); mi++; break;
      case 'reveal': impact(m, S, t, { gain: 0.14 }); whoosh(m, S, t, { dur: 0.55, f0: 600, f1: 3000, gain: 0.05, peakAt: 0.3 }); break;
      case 'morph': whoosh(m, S, t, { dur: 0.35, f0: 2000, f1: 900, gain: 0.025 }); break;
      case 'land': pluck(m, S, t, NOTE(['G5', 'A5', 'C6', 'D6', 'E6'][e.k]), { dur: 0.25, gain: 0.06, bright: 5000, type: 'sine' }); tick(m, S, t, { freq: 2400, gain: 0.04 }); break;
      case 'count': for (let k = 0; k < 12; k++) tick(m, S, t + k * (e.dur / 12), { freq: 2600 + k * 90, gain: 0.035 }); chime(m, S, t + e.dur, NOTE('G6'), { gain: 0.025, dur: 0.8 }); break;
      case 'tap': tick(m, S, t, { freq: 1600, gain: 0.14, dur: 0.03 }); pop(m, S, t, { f0: 900, f1: 500, gain: 0.08, dur: 0.06 }); break;
      case 'push': riser(m, S, t, e.dur, { gain: 0.05, f0: 300, f1: 4000, tone0: 330, tone1: 990 }); break;
      case 'node': pop(m, S, t, { f0: 300, f1: 700 + e.i * 80, gain: 0.04, pan: [0, 0.4, 0.3, -0.3, -0.4][e.i] }); break;
      case 'naive': tick(m, S, t, { freq: 2000 + (e.k % 5) * 260, gain: 0.08, pan: ((e.k * 7) % 9) / 9 - 0.45 }); whoosh(m, S, t, { dur: 0.3, f0: 1500, f1: 3500, gain: 0.008 }); break;
      case 'clear': whoosh(m, S, t, { dur: 0.6, f0: 3500, f1: 400, gain: 0.04, peakAt: 0.25 }); break;
      case 'net': pop(m, S, t, { f0: 500, f1: 900, gain: 0.05, pan: [0, 0.4, 0.3, -0.3, -0.4][e.i] }); break;
      case 'bold': pluck(m, S, t, BOLD[e.k], { dur: 0.6, gain: 0.07, bright: 4200 }); bass(m, S, t, BOLD[e.k] / 8, { dur: 0.3, gain: 0.1 }); whoosh(m, S, t, { dur: 0.42, f0: 800, f1: 2400, gain: 0.02 }); break;
      case 'four': chime(m, S, t, NOTE('E6'), { gain: 0.05, dur: 1.4 }); pop(m, S, t, { f0: 500, f1: 1200, gain: 0.04 }); break;
      case 'note': pop(m, S, t, { f0: 600, f1: 1000, gain: 0.02 }); break;
      case 'pull': whoosh(m, S, t, { dur: e.dur, f0: 3200, f1: 400, gain: 0.05, peakAt: 0.3 }); break;
      case 'check': pluck(m, S, t, CHECK[e.k], { dur: 0.5, gain: 0.08, bright: 5000 }); chime(m, S, t, CHECK[e.k] * 2, { gain: 0.03, dur: 0.8 }); break;
      case 'stamp': impact(m, S, t, { gain: 0.16 }); crash(m, S, t, { gain: 0.03, dur: 1.8 }); break;
      case 'logo': whoosh(m, S, t, { dur: e.dur, f0: 500, f1: 2400, gain: 0.035 }); break;
      case 'tag': chime(m, S, t, NOTE('G5'), { gain: 0.03, dur: 2.2 }); chime(m, S, t + 0.12, NOTE('C6'), { gain: 0.025, dur: 2.2 }); break;
    }
  }
}
install(score, { reverb: 0.16, irSec: 1.6, irPow: 3.0 });
