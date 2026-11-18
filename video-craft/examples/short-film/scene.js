import { register, seg, ease } from '../../kit/kit.js';
import { wideCoast, turningVessel } from './coast.js';
import { switchRoom, fresnelLens } from './interior.js';
import { W, H, grade } from './paint.js';
import { DURATION, FPS, time, events } from './timeline.js';

const canvas = document.querySelector('#frame');
const g = canvas.getContext('2d', { alpha: false });

function seek(t) {
  g.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);
  g.globalAlpha = 1;
  g.globalCompositeOperation = 'source-over';
  if (t < time.switchShot) wideCoast(g, t, false);
  else if (t < time.lensShot) switchRoom(g, t);
  else if (t < time.seaShot) fresnelLens(g, t);
  else if (t < time.wideShot) turningVessel(g, t);
  else wideCoast(g, t, true);

  grade(g, Math.floor(t * FPS / 2), t < time.seaShot ? 0.69 : 0.53);
  const fade = Math.max(1 - seg(t, 0, 0.62, ease.inOutSoft), seg(t, time.fade, DURATION - time.fade, ease.inOutSoft));
  if (fade > 0) {
    g.fillStyle = `rgba(3,7,11,${fade})`;
    g.fillRect(0, 0, W, H);
  }
}

register({ duration: DURATION, fps: FPS, width: canvas.width, height: canvas.height, seek, meta: { events } });
seek(0);
