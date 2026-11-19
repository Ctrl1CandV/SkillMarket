import { NOTE, bass, chime, glide, install, piano, riser, tick, warmPad, whoosh } from '../../kit/sound.js';

function score(m, events, duration) {
  const { music, sfx, master } = m;
  master.gain.setValueAtTime(1, duration - 0.72);
  master.gain.linearRampToValueAtTime(0, duration);
  warmPad(m, music, 0, 4.6, ['C3', 'G3', 'D4', 'F#4'].map(NOTE), { gain: 0.08, cutoff: 710, attack: 0.27, release: 0.88 });

  for (const { type, t } of events) {
    switch (type) {
      case 'rake':
      case 'secondRake': {
        const answer = type === 'secondRake';
        const line = answer ? ['D6', 'C6', 'G5'] : ['E5', 'G5', 'B5'];
        line.forEach((pitch, i) => piano(m, music, t + i * 0.14, NOTE(pitch), {
          pan: answer ? 0.24 - 0.16 * i : -0.22 + 0.14 * i, gain: 0.15 - i * 0.022, dur: 1.2,
        }));
        tick(m, sfx, t + 0.07, { freq: answer ? 3300 : 3850, dur: 0.075, gain: 0.045 });
        break;
      }
      case 'reveal':
        glide(m, music, t, NOTE('G4'), NOTE('E5'), { dur: 2.5, gain: 0.025, type: 'sine' });
        riser(m, sfx, t + 0.08, 2.7, { f0: 580, f1: 2600, tone0: NOTE('C3'), tone1: NOTE('G3'), gain: 0.047 });
        ['G4', 'A4', 'C5', 'D5', 'E5'].forEach((pitch, i) => piano(m, music, t + 0.2 + i * 0.49, NOTE(pitch), { gain: 0.12 + 0.009 * i, dur: 1.7 }));
        break;
      case 'open':
        warmPad(m, music, t - 0.4, duration, ['C3', 'G3', 'E4', 'A4', 'D5'].map(NOTE), { gain: 0.10, cutoff: 1200, attack: 0.52, release: 1.1 });
        bass(m, music, t, NOTE('C3'), { gain: 0.15, dur: 0.9 });
        chime(m, music, t, NOTE('E5'), { gain: 0.085, dur: 2.2, pan: 0.18 });
        break;
      case 'wingbeat':
        whoosh(m, sfx, t - 0.22,  { f0: 780, f1: 3900, dur: 0.62, gain: 0.10, peakAt: 0.47, pan0: -0.42, pan1: 0.42 });
        ['G5', 'B5', 'E6'].forEach((pitch, i) => piano(m, music, t + i * 0.035, NOTE(pitch), { gain: 0.10, dur: 2.1, pan: (i - 1) * 0.27 }));
        break;
      case 'settle':
        ['A4', 'G4', 'E4', 'C4'].forEach((pitch, i) => piano(m, music, t + i * 0.16, NOTE(pitch), { gain: 0.115 - 0.013 * i, dur: 2.2 }));
        break;
    }
  }
}

install(score, { reverb: 0.28, seed: 60, irSec: 2.8 });
