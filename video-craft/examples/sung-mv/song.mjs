// Timing is in quarter notes. Both the drawing and the audio arrangement use this file.
export const BPM = 100;
export const beat = 60 / BPM;
export const beats = 38;
export const duration = beat * beats;
export const title = '纸鸟';
export const lines = [
  { start: 4, end: 11.45, text: '把心折成鸟', notes: [
    ['把', 4, .82, 62], ['心', 5, .84, 66], ['折', 6, .91, 69],
    ['成', 7, .90, 66], ['鸟', 8, 2.95, 64],
  ] },
  { start: 12, end: 19.48, text: '飞过旧街角', notes: [
    ['飞', 12, .86, 64], ['过', 13, .80, 66], ['旧', 14, .88, 69],
    ['街', 15, .87, 71], ['角', 16, 3.05, 69],
  ] },
  { start: 20, end: 27.65, text: '飞呀，飞呀', notes: [
    ['飞', 20, .86, 69], ['呀', 21, 2.15, 74],
    ['飞', 24, .86, 69], ['呀', 25, 2.25, 71],
  ] },
  { start: 28, end: 35.80, text: '飞进你掌心', notes: [
    ['飞', 28, .82, 69], ['进', 29, .86, 66], ['你', 30, .86, 64],
    ['掌', 31, .90, 61], ['心', 32, 3.32, 62],
  ] },
];
export const cues = { fold: 6 * beat, launch: 12 * beat, hook: 20 * beat, secondCall: 24 * beat, land: 28 * beat, palm: 32 * beat };
export const chords = [
  [50,57,62,66], [47,54,59,62], [43,50,55,59], [45,52,57,61],
  [50,57,62,66], [43,50,55,59], [45,52,57,61], [43,50,55,59],
  [50,57,62,66], [50,57,62,66],
];
