export const DURATION = 22;
export const FPS = 24;

export const time = {
  horn: 1.62,
  switchShot: 4.5,
  glove: 5.6,
  pull: 6.65,
  contact: 7.65,
  lensShot: 8.25,
  ignition: 8.62,
  seaShot: 11.7,
  beam: 12.13,
  turn: 13.15,
  wideShot: 17,
  fade: 20.77,
};

export const events = [
  { t: time.horn, type: 'foghorn' },
  { t: time.switchShot, type: 'interior' },
  { t: time.glove, type: 'grip' },
  { t: time.pull, type: 'lever' },
  { t: time.contact, type: 'contact' },
  { t: time.lensShot, type: 'lens' },
  { t: time.ignition, type: 'ignition' },
  { t: time.seaShot, type: 'back to sea' },
  { t: time.beam, type: 'beam' },
  { t: time.turn, type: 'rudder' },
  { t: time.wideShot, type: 'release' },
];
