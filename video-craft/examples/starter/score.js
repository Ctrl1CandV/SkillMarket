// starter/score.js — music bed, voice-over clips at their lines, music ducked under the voice, one effect.
import { NOTE, warmPad, piano, chime, voice, duck, install } from '../../kit/sound.js';

function score(m, events, duration) {
  m.master.gain.setValueAtTime(0, 0); m.master.gain.linearRampToValueAtTime(1, 0.1);
  m.master.gain.setValueAtTime(1, duration - 1.2); m.master.gain.linearRampToValueAtTime(0, duration);
  const chords = [['D3', 'A3', 'E4', 'F#4'], ['B2', 'F#3', 'D4', 'A4'], ['G3', 'B3', 'D4', 'F#4'], ['A3', 'D4', 'E4', 'A4']];
  for (let i = 0, t = 0; t < duration; i++, t += 3.2) warmPad(m, m.music, t, Math.min(duration, t + 3.6), chords[i % 4].map(NOTE), { gain: 0.09, attack: 0.8, release: 0.8 });
  const spoken = [];
  for (const e of events) {
    if (e.type === 'line') { const end = voice(m, e.t, e.id); if (end > e.t) spoken.push([e.t, end]); else piano(m, m.music, e.t, NOTE('A4'), { gain: 0.05 }); }
    if (e.type === 'count') chime(m, m.sfx, e.t, NOTE('E6'), { gain: 0.06, dur: 1.6 });
  }
  duck(m.music, spoken, { depth: -9 });   // music steps back while someone speaks
}
install(score, { reverb: 0.2, irSec: 2.4, irPow: 3 });
