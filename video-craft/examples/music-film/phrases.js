export const DURATION = 20;

// Each landmark names a sound the editor could find by ear.
export const PHRASES = [
  { t: 0, end: 5, id: 'call', cue: '拨弦奏出四音动机' },
  { t: 5, end: 10, id: 'lift', cue: '高八度回应，加入低鼓' },
  { t: 10, end: 15, id: 'below', cue: '鼓停，三颗低音拉开间距' },
  { t: 15, end: DURATION, id: 'return', cue: '动机回来，最后落到 C' },
];

// [time, note, weight, optional gesture]. Pickup and answer leave audible gaps.
export const MELODY = [
  [0.12, 'A4', 0.88], [0.60, 'C5', 0.77], [1.02, 'E5', 1], [1.65, 'D5', 0.83],
  [2.62, 'C5', 0.88], [3.22, 'G4', 0.68], [3.58, 'A4', 0.84], [4.37, 'E4', 0.63],
  [5.10, 'A4', 0.92], [5.61, 'C5', 0.85, 'dip'], [6.02, 'E5', 1, 'pull'], [6.65, 'D5', 0.84],
  [7.53, 'G5', 0.81, 'lift'], [8.15, 'E5', 0.88], [8.55, 'D5', 0.79], [9.28, 'C5', 0.82],
  [10.14, 'D4', 0.86], [11.45, 'F4', 0.79], [12.91, 'E4', 0.84], [14.12, 'G4', 0.64],
  [15.11, 'A4', 0.92], [15.60, 'C5', 0.83], [16.02, 'E5', 1], [16.65, 'D5', 0.82],
  [17.39, 'G5', 0.81], [17.98, 'E5', 0.79], [18.60, 'C5', 1, 'wake'],
];

export const EVENTS = [
  ...PHRASES.map(({ t, id, cue }) => ({ t, type: 'phrase', id, cue })),
  ...MELODY.map(([t, note, weight, gesture]) => ({ t, type: 'note', note, weight, gesture })),
].sort((a, b) => a.t - b.t);
