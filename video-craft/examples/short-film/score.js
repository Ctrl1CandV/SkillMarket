import { install, NOTE, piano, thud, tick, tone, warmPad, wind } from '../../kit/sound.js';

function wash(m, t, duration, { gain, frequency, pan = 0, attack = 0.2 }) {
  const g = m.ctx;
  const source = g.createBufferSource();
  const filter = g.createBiquadFilter();
  const envelope = g.createGain();
  const stereo = g.createStereoPanner();
  source.buffer = m.noiseLong;
  source.loop = true;
  filter.type = 'bandpass';
  filter.Q.value = 0.75;
  filter.frequency.setValueAtTime(frequency, t);
  filter.frequency.exponentialRampToValueAtTime(frequency * 0.45, t + duration);
  envelope.gain.setValueAtTime(0.0001, t);
  envelope.gain.exponentialRampToValueAtTime(gain, t + attack);
  envelope.gain.exponentialRampToValueAtTime(0.0001, t + duration);
  stereo.pan.value = pan;
  source.connect(filter).connect(envelope).connect(stereo).connect(m.sfx);
  source.start(t, m.rand() * 7);
  source.stop(t + duration + 0.02);
}

function foghorn(m, t) {
  const end = t + 2.13;
  tone(m, m.sfx, t, end, 94, { gain: 0.106, attack: 0.36, release: 0.78, pan: 0.44, type: 'triangle', detune: 6 });
  tone(m, m.sfx, t + 0.025, end, 187, { gain: 0.035, attack: 0.44, release: 0.88, pan: 0.51, detune: 2 });
  tone(m, m.sfx, t + 0.061, end, 280, { gain: 0.019, attack: 0.52, release: 0.94, pan: 0.45 });
  wash(m, t, 1.94, { gain: 0.022, frequency: 770, pan: 0.5, attack: 0.48 });
}

function score(m, events, duration) {
  const at = Object.fromEntries(events.map((event) => [event.type, event.t]));
  const exterior = m.sfx.gain;
  const fade = m.master.gain;
  fade.setValueAtTime(0, 0);
  fade.linearRampToValueAtTime(1, 0.36);
  fade.setValueAtTime(1, duration - 1.0);
  fade.linearRampToValueAtTime(0, duration);

  wind(m, m.sfx, 0, at.interior + 0.25, { gain: 0.17, fadeIn: 0.35, fadeOut: 0.22, center: 446 });
  wind(m, m.sfx, at.interior - 0.08, at['back to sea'] + 0.13, { gain: 0.039, fadeIn: 0.13, fadeOut: 0.3, center: 264 });
  wind(m, m.sfx, at['back to sea'] - 0.14, duration, { gain: 0.13, fadeIn: 0.23, fadeOut: 2.6, center: 394 });
  exterior.setValueAtTime(1, 0);
  exterior.setValueAtTime(1, at.release);
  exterior.linearRampToValueAtTime(0.74, at.release + 2.1);

  for (const [t, gain, pan, frequency] of [[0.15, 0.078, -0.62, 1460], [3.12, 0.115, -0.55, 1420], [11.94, 0.108, -0.6, 1990], [13.8, 0.115, 0.25, 1600], [15.43, 0.069, 0.45, 1240], [17.27, 0.066, -0.52, 1080], [19.63, 0.048, -0.47, 1240]]) {
    wash(m, t, 1.32, { gain, frequency, pan, attack: 0.32 });
  }
  foghorn(m, at.foghorn);
  wash(m, at.grip - 0.31, 0.73, { gain: 0.048, frequency: 1900, pan: -0.18, attack: 0.39 });
  wash(m, at.lever + 0.11, 0.71, { gain: 0.052, frequency: 1060, pan: -0.04 });
  tick(m, m.sfx, at.lever, { gain: 0.036, freq: 1080, dur: 0.095, pan: -0.19 });
  thud(m, m.sfx, at.contact, { gain: 0.16, freq: 158, dur: 0.11, pan: 0.11 });
  tick(m, m.sfx, at.contact + 0.012, { gain: 0.09, freq: 4300, dur: 0.082, pan: 0.13 });
  wash(m, at.contact + 0.02, 0.23, { gain: 0.046, frequency: 5860, pan: 0.13, attack: 0.005 });
  tone(m, m.sfx, at.ignition, at['back to sea'] + 0.22, 121, { gain: 0.069, attack: 0.12, release: 0.64, type: 'triangle' });
  tone(m, m.sfx, at.ignition + 0.035, at['back to sea'] + 0.19, 239, { gain: 0.022, attack: 0.13, release: 0.8, pan: 0.32 });
  wash(m, at.beam - 0.08, 1.37, { gain: 0.078, frequency: 957, pan: -0.21, attack: 0.53 });
  tone(m, m.sfx, at.rudder, at.release + 0.29, 67, { gain: 0.057, attack: 0.75, release: 0.86, pan: 0.4 });

  warmPad(m, m.music, at.ignition + 0.28, at.release + 0.35, ['D3', 'A3', 'C4', 'E4'].map(NOTE), { gain: 0.062, attack: 2.2, release: 2.0, cutoff: 560 });
  warmPad(m, m.music, at.release - 0.3, duration, ['D3', 'A3', 'F#4', 'E5'].map(NOTE), { gain: 0.075, attack: 1.9, release: 2.2, cutoff: 740 });
  piano(m, m.music, at.release + 0.19, NOTE('A4'), { dur: 3.15, gain: 0.048, bright: 0.71, pan: -0.24 });
  piano(m, m.music, at.release + 1.13, NOTE('D5'), { dur: 3.2, gain: 0.052, bright: 0.76, pan: 0.19 });
}

install(score, { reverb: 0.18, irSec: 2.35, irPow: 2.7 });
