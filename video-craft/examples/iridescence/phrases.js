export const DURATION = 10;
export const CUES = {
  rake: 0.32,
  secondRake: 1.78,
  reveal: 2.75,
  open: 5.55,
  wingbeat: 6.72,
  settle: 8.06,
};
export const EVENTS = Object.entries(CUES).map(([type, t]) => ({ type, t }));
