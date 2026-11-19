// The song for the last-light example, composed only to have a recording to cut to.
// The MV (../scene.js) never imports this file: it reads ../map/songmap.js, made by songmap.py from song.m4a,
// exactly as it would for a song you were handed. Rebuild the recording from examples/last-light:
//   node ../../kit/audio.mjs song/score.html song/score.html out/song.webm --wav out/song.wav
//   ffmpeg -i out/song.wav -c:a aac -b:a 192k song.m4a
import { register } from '../../../kit/kit.js';
import { bass, clap, crash, hat, install, kick, NOTE, piano, pluck, riser, tone, warmPad, wind } from '../../../kit/sound.js';

const BPM = 96, BEAT = 60 / BPM, BAR = 4 * BEAT;
const LEAD = 0.2 + 2 * BEAT;                 // a little air, then a two-beat piano pickup before bar 0
const at = (bar, beat = 1) => LEAD + bar * BAR + (beat - 1) * BEAT;
const BARS = 20, DURATION = at(BARS) + 3.2;

// sections in bars: intro 0-1, verse 2-5, chorus 6-9, bridge 10-13, last chorus 14-17, outro 18-19
const CHORDS = ['Am', 'F', 'Am', 'F', 'C', 'G', 'F', 'G', 'Am', 'C', 'Dm', 'Am', 'Dm', 'E', 'F', 'G', 'C', 'C', 'F', 'C'];
const VOICING = {
  Am: ['A2', 'C4 E4 A4'], F: ['F2', 'C4 F4 A4'], C: ['C3', 'E4 G4 C5'], G: ['G2', 'D4 G4 B4'],
  Dm: ['D3', 'D4 F4 A4'], E: ['E2', 'E4 G#4 B4'],
};
const part = (bar) => (bar < 2 ? 'intro' : bar < 6 ? 'verse' : bar < 10 ? 'chorus' : bar < 14 ? 'bridge' : bar < 18 ? 'last' : 'outro');

// melody: [bar, beat, note, beats]
const MELODY = [
  [-1, 3, 'E4', 1], [-1, 4, 'G4', 1],
  [0, 1, 'A4', 1], [0, 2, 'C5', 1], [0, 3, 'E5', 2], [1, 1, 'D5', 1], [1, 2, 'C5', 1], [1, 3, 'A4', 2],
  [2, 1, 'E4', 1.5], [2, 2.5, 'A4', 0.5], [2, 3, 'C5', 1], [2, 4, 'B4', 1],
  [3, 1, 'A4', 2], [3, 3, 'F4', 1], [3, 4, 'A4', 1],
  [4, 1, 'G4', 1.5], [4, 2.5, 'E4', 0.5], [4, 3, 'G4', 1], [4, 4, 'C5', 1],
  [5, 1, 'B4', 2], [5, 3, 'D5', 1], [5, 4, 'B4', 1],
  [6, 1, 'C5', 1], [6, 2, 'F5', 1], [6, 3, 'E5', 1], [6, 4, 'C5', 1],
  [7, 1, 'D5', 1], [7, 2, 'G5', 1.5], [7, 3.5, 'F5', 0.5], [7, 4, 'E5', 1],
  [8, 1, 'E5', 2], [8, 3, 'C5', 1], [8, 4, 'A4', 1],
  [9, 1, 'G4', 1], [9, 2, 'C5', 1], [9, 3, 'E5', 2],
  [10, 1, 'F5', 3], [10, 4, 'E5', 1], [11, 1, 'C5', 4],
  [12, 1, 'D5', 2], [12, 3, 'F5', 2], [13, 1, 'G#4', 2], [13, 3, 'B4', 2],
  [14, 1, 'C5', 1], [14, 2, 'F5', 1], [14, 3, 'E5', 1], [14, 4, 'C5', 1],
  [15, 1, 'D5', 1], [15, 2, 'G5', 1.5], [15, 3.5, 'F5', 0.5], [15, 4, 'E5', 1],
  [16, 1, 'E5', 2], [16, 3, 'G5', 1], [16, 4, 'E5', 1], [17, 1, 'C5', 4],
  [18, 1, 'A4', 2], [18, 3, 'C5', 2], [19, 1, 'E4', 1], [19, 2, 'G4', 1], [19, 3, 'C5', 2],
];

function score(m, _events, duration) {
  const { music, master } = m;
  master.gain.setValueAtTime(1, duration - 1.2);
  master.gain.linearRampToValueAtTime(0, duration);
  wind(m, music, 0, duration, { gain: 0.008, center: 420, fadeIn: 1.5, fadeOut: 2 });

  CHORDS.forEach((name, bar) => {
    const [root, notes] = VOICING[name], p = part(bar), t0 = at(bar), t1 = at(bar + 1);
    const big = p === 'chorus' || p === 'last';
    warmPad(m, music, t0, t1 + 0.4, notes.split(' ').map(NOTE), {
      gain: p === 'bridge' ? 0.03 : big ? 0.05 : 0.038, cutoff: big ? 1500 : 800, attack: 0.5, release: 0.9,
    });
    if (p === 'intro' || p === 'outro') { tone(m, music, t0, t1 + 0.5, NOTE(root), { gain: 0.03, attack: 0.6, release: 1 }); return; }
    bass(m, music, t0 + 0.01, NOTE(root), { gain: big ? 0.16 : 0.12, dur: big ? 0.9 : 1.6 });
    if (big) bass(m, music, at(bar, 3), NOTE(root), { gain: 0.11, dur: 0.6 });
    if (big) bass(m, music, at(bar, 4.5), NOTE(root) * 2, { gain: 0.05, dur: 0.25 });
  });

  for (const [bar, beat, note, beats] of MELODY) {
    const t = at(bar, beat), p = part(Math.max(0, bar)), hz = NOTE(note);
    const big = p === 'chorus' || p === 'last';
    piano(m, music, t, hz, { gain: big ? 0.15 : 0.13, dur: Math.max(1.2, beats * BEAT * 1.6), bright: big ? 1 : 0.75 });
    if (big) pluck(m, music, t, hz * 2, { gain: 0.03, dur: 0.4, bright: 3400, pan: 0.25 });
    if (p === 'last') pluck(m, music, t + BEAT / 2, hz, { gain: 0.025, dur: 0.5, bright: 2400, pan: -0.35 });
  }

  // drums: verse soft on one; choruses full; bridge none, a riser into the last chorus
  for (let bar = 2; bar < 18; bar++) {
    const p = part(bar);
    if (p === 'bridge') continue;
    if (p === 'verse') {
      kick(m, music, at(bar), { gain: 0.26, dur: 0.35 });
      for (const b of [1.5, 2.5, 3.5, 4.5]) hat(m, music, at(bar, b), { gain: 0.012 });
      continue;
    }
    kick(m, music, at(bar), { gain: 0.42 });
    kick(m, music, at(bar, 3), { gain: 0.34 });
    if (bar % 2) kick(m, music, at(bar, 3.5), { gain: 0.2, dur: 0.25 });
    clap(m, music, at(bar, 2), { gain: 0.12 });
    clap(m, music, at(bar, 4), { gain: 0.13 });
    for (let k = 0; k < 8; k++) hat(m, music, at(bar, 1 + k / 2), { gain: k % 2 ? 0.022 : 0.012 });
  }
  crash(m, music, at(6), { gain: 0.07 });
  riser(m, music, at(13), BAR, { gain: 0.05 });
  crash(m, music, at(14), { gain: 0.09 });
  crash(m, music, at(18), { gain: 0.04, dur: 3 });
}

install(score, { reverb: 0.24, irSec: 2.4, irPow: 2.8, seed: 31 });
// lets audio.mjs use this page as its own "scene" for the length
register({ duration: DURATION, fps: 30, width: 16, height: 16, seek: () => {} });
