// stage.js — style-agnostic choreography primitives for product demos, UI walkthroughs, and spatial transitions.
// Pure functions of time `t`: works identically in Canvas 2D, SVG, and DOM without CSS transitions or fixed themes.
import { clamp, lerp, ease } from './kit.js';

// Point along a gentle quadratic arc between p0=[x,y] and p1=[x,y].
// `bend` offsets the midpoint perpendicularly by `bend * distance` so pointer/object motion never looks robotic,
// while strictly landing on p0 at k=0 and p1 at k=1 with zero target overshoot.
export function arcPoint(p0, p1, k, { bend = 0.14 } = {}) {
  const u = clamp(k);
  const dx = p1[0] - p0[0], dy = p1[1] - p0[1];
  if (Math.abs(dx) < 1e-6 && Math.abs(dy) < 1e-6) return [p0[0], p0[1]];
  const cx = (p0[0] + p1[0]) * 0.5 - dy * bend;
  const cy = (p0[1] + p1[1]) * 0.5 + dx * bend;
  const om = 1 - u;
  return [
    om * om * p0[0] + 2 * om * u * cx + u * u * p1[0],
    om * om * p0[1] + 2 * om * u * cy + u * u * p1[1],
  ];
}

// Interpolate axis-aligned rectangles { x, y, w, h, r? }.
export function lerpRect(a, b, k) {
  const u = clamp(k);
  return {
    x: lerp(a.x, b.x, u),
    y: lerp(a.y, b.y, u),
    w: lerp(a.w, b.w, u),
    h: lerp(a.h, b.h, u),
    r: a.r !== undefined || b.r !== undefined ? lerp(a.r ?? 0, b.r ?? 0, u) : undefined,
  };
}

// Optional two-phase rect transition: first reshape in place (kMorph 0..1), then travel along an optional arc (kMove 0..1).
export function morphMoveRect(fromRect, toRect, kMorph, kMove, { midW = null, midH = null, bend = 0 } = {}) {
  const km = clamp(kMorph), kf = clamp(kMove);
  const w0 = lerp(fromRect.w, midW ?? toRect.w, km);
  const h0 = lerp(fromRect.h, midH ?? toRect.h, km);
  const startCenter = [fromRect.x + fromRect.w * 0.5, fromRect.y + fromRect.h * 0.5];
  const endCenter = [toRect.x + toRect.w * 0.5, toRect.y + toRect.h * 0.5];
  const [cx, cy] = bend ? arcPoint(startCenter, endCenter, kf, { bend }) : [lerp(startCenter[0], endCenter[0], kf), lerp(startCenter[1], endCenter[1], kf)];
  const w = lerp(w0, toRect.w, kf), h = lerp(h0, toRect.h, kf);
  return { x: cx - w * 0.5, y: cy - h * 0.5, w, h };
}

// Deterministic pointer choreography across chronological waypoints:
//   waypoints = [{ t, x, y, click?: boolean, travel?: seconds, settle?: seconds, dwell?: seconds, bend?: number }, ...]
// Arrives smoothly with zero overshoot, holds steady across clicks, and pins click ripples to the clicked target.
export function cursorAt(t, waypoints, { pressDur = 0.18, rippleDur = 0.46, bend = 0.12, moveEase = ease.inOutSoft } = {}) {
  if (!Array.isArray(waypoints) || !waypoints.length) {
    return { x: 0, y: 0, vx: 0, vy: 0, press: 0, clicking: false, ripple: null, visible: false };
  }
  const wps = waypoints;
  let x = wps[0].x, y = wps[0].y, vx = 0, vy = 0;

  if (t > wps[0].t) {
    x = wps[wps.length - 1].x;
    y = wps[wps.length - 1].y;
    for (let i = 1; i < wps.length; i++) {
      const prev = wps[i - 1], cur = wps[i];
      if (t <= cur.t) {
        const holdAfterPrev = prev.dwell ?? (prev.click ? Math.min(0.22, pressDur * 1.1) : 0);
        const settleBeforeCur = cur.settle ?? (cur.click ? 0.06 : 0);
        const tArrive = Math.max(prev.t + 1e-4, cur.t - settleBeforeCur);
        const span = Math.max(1e-4, tArrive - (prev.t + holdAfterPrev));
        const travel = Math.min(span, cur.travel ?? Math.min(0.65, Math.max(0.18, span * 0.8)));
        const tStart = Math.max(prev.t + holdAfterPrev, tArrive - travel);
        if (t <= tStart) {
          x = prev.x; y = prev.y;
        } else if (t >= tArrive) {
          x = cur.x; y = cur.y;
        } else {
          const raw = clamp((t - tStart) / Math.max(1e-4, tArrive - tStart));
          const u = (moveEase || ease.inOutSoft)(raw);
          const u2 = (moveEase || ease.inOutSoft)(clamp(raw + 0.01));
          const b = cur.bend ?? bend;
          [x, y] = arcPoint([prev.x, prev.y], [cur.x, cur.y], u, { bend: b });
          const [x2, y2] = arcPoint([prev.x, prev.y], [cur.x, cur.y], u2, { bend: b });
          const dt = 0.01 * Math.max(1e-4, tArrive - tStart);
          vx = (x2 - x) / dt; vy = (y2 - y) / dt;
        }
        break;
      }
    }
  }

  let press = 0, clicking = false, ripple = null;
  for (const wp of wps) {
    if (!wp.click) continue;
    if (t >= wp.t && t < wp.t + pressDur) {
      clicking = true;
      press = Math.max(press, Math.sin(Math.PI * clamp((t - wp.t) / pressDur)));
    }
    if (t >= wp.t && t < wp.t + rippleDur) {
      ripple = { active: true, x: wp.x, y: wp.y, p: clamp((t - wp.t) / rippleDur) };
    }
  }

  return { x, y, vx, vy, press, clicking, ripple, visible: true };
}

// Optional Canvas 2D cursor + pinned click-ripple renderer. Caller controls palette and cursor style ('arrow' | 'dot' | 'ring').
export function drawCursor(ctx, state, {
  kind = 'arrow', size = 28, fill = '#ffffff', stroke = '#141820', accent = '#3b82f6', rippleRadius = 34,
} = {}) {
  if (!state || state.visible === false) return;
  if (state.ripple?.active) {
    const { x, y, p } = state.ripple;
    ctx.save();
    ctx.globalAlpha = (1 - p) * 0.75;
    ctx.strokeStyle = accent;
    ctx.lineWidth = Math.max(1.5, 3.2 * (1 - p * 0.5));
    ctx.beginPath();
    ctx.arc(x, y, rippleRadius * (0.22 + 0.78 * ease.out(p)), 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }
  ctx.save();
  ctx.translate(state.x, state.y);
  const sc = 1 - 0.12 * (state.press || 0);
  ctx.scale(sc, sc);
  ctx.shadowColor = 'rgba(0,0,0,0.26)';
  ctx.shadowBlur = size * 0.35;
  ctx.shadowOffsetY = size * 0.12;
  if (kind === 'dot' || kind === 'ring') {
    const r = size * 0.42;
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, Math.PI * 2);
    if (kind === 'dot') {
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.lineWidth = Math.max(2, size * 0.09);
      ctx.strokeStyle = stroke;
      ctx.stroke();
    } else {
      ctx.lineWidth = Math.max(2.5, size * 0.12);
      ctx.strokeStyle = fill;
      ctx.stroke();
    }
  } else {
    const s = size / 28;
    const pts = [[0, 0], [0, 25 * s], [6.8 * s, 19.2 * s], [12.2 * s, 29.5 * s], [16.8 * s, 27.2 * s], [11.4 * s, 17 * s], [20 * s, 17 * s]];
    ctx.beginPath();
    pts.forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py)));
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.lineJoin = 'round';
    ctx.lineWidth = Math.max(1.8, 2.2 * s);
    ctx.strokeStyle = stroke;
    ctx.stroke();
  }
  ctx.restore();
}

// Compute logarithmic scale, center translation, and tilt flattening so zooming through `screenRect`
// clears all 4 viewport edges AND rounded screen corners (`borderRadius`) at k=1 with zero bezel leak.
// `screenRect` = { x, y, w, h } in unscaled stage coordinates; `origin` = transform origin (defaults to viewport center).
export function throughScreen(k, screenRect, viewport = { w: 1920, h: 1080 }, {
  borderRadius = 0, pose0 = {}, origin = null, safety = 1.04,
} = {}) {
  const u = clamp(k);
  const vw = viewport.w ?? 1920, vh = viewport.h ?? 1080;
  const ox = origin?.x ?? vw * 0.5, oy = origin?.y ?? vh * 0.5;
  const r = Math.max(0, Math.min(borderRadius, screenRect.w * 0.45, screenRect.h * 0.45));
  const cornerInset = r * (1 - Math.SQRT1_2);
  const clearW = Math.max(1, screenRect.w - 2 * cornerInset);
  const clearH = Math.max(1, screenRect.h - 2 * cornerInset);

  const s0 = Math.max(1e-3, pose0.scale ?? 1);
  const sEnd = Math.max(vw / clearW, vh / clearH) * safety;
  const scale = u <= 0 ? s0 : Math.exp(lerp(Math.log(s0), Math.log(sEnd), u));

  // Flatten 3D tilt before k reaches 0.82 so tilted edges never clip near full-bleed handoff.
  const tiltKeep = 1 - clamp(u / 0.82);
  const rx = (pose0.rx ?? 0) * tiltKeep || 0;
  const ry = (pose0.ry ?? 0) * tiltKeep || 0;
  const rz = (pose0.rz ?? 0) * tiltKeep || 0;

  const x0 = pose0.x ?? 0, y0 = pose0.y ?? 0;
  const startFocusX = ox + (vw * 0.5 - ox - x0) / s0;
  const startFocusY = oy + (vh * 0.5 - oy - y0) / s0;
  const cx = screenRect.x + screenRect.w * 0.5;
  const cy = screenRect.y + screenRect.h * 0.5;
  const panU = ease.inOut(clamp(u * 1.18));
  const focusX = lerp(startFocusX, cx, panU);
  const focusY = lerp(startFocusY, cy, panU);

  const tx = (vw * 0.5 - ox) - (focusX - ox) * scale;
  const ty = (vh * 0.5 - oy) - (focusY - oy) * scale;

  return { tx, ty, scale, sEnd, rx, ry, rz, ox, oy, cleared: u >= 0.999 };
}

// CSS transform string matching `throughScreen` state (pair with `el.style.transformOrigin = `${st.ox}px ${st.oy}px``).
export function cssStageTransform(state, { perspective = 2200 } = {}) {
  const { tx = 0, ty = 0, scale = 1, rx = 0, ry = 0, rz = 0 } = state;
  const has3d = Math.abs(rx) > 1e-3 || Math.abs(ry) > 1e-3;
  const rot = has3d
    ? `perspective(${perspective}px) rotateY(${ry.toFixed(3)}deg) rotateX(${rx.toFixed(3)}deg) rotateZ(${rz.toFixed(3)}deg)`
    : (Math.abs(rz) > 1e-3 ? `rotate(${rz.toFixed(3)}deg)` : '');
  return `translate3d(${tx.toFixed(2)}px, ${ty.toFixed(2)}px, 0) ${rot} scale(${scale.toFixed(4)})`.replace(/\s+/g, ' ').trim();
}

// Apply 2D `throughScreen` state to a Canvas 2D context around `(state.ox, state.oy)`.
export function applyStageCamera(ctx, state, fn) {
  const { tx = 0, ty = 0, scale = 1, rz = 0, ox = ctx.canvas.width * 0.5, oy = ctx.canvas.height * 0.5 } = state;
  ctx.save();
  ctx.translate(ox + tx, oy + ty);
  if (rz) ctx.rotate((rz * Math.PI) / 180);
  ctx.scale(scale, scale);
  ctx.translate(-ox, -oy);
  fn(ctx);
  ctx.restore();
}

// Deterministic counter string formatter (pair with tabular-nums or monospace font to avoid width jitter).
export function rollNumber(v0, v1, k, { decimals = 0, prefix = '', suffix = '', locale = 'en-US', padStart = 0 } = {}) {
  const val = lerp(v0, v1, clamp(k));
  const factor = 10 ** decimals;
  const rounded = Math.round(val * factor) / factor;
  const body = locale
    ? rounded.toLocaleString(locale, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
    : rounded.toFixed(decimals);
  return `${prefix}${padStart > 0 ? body.padStart(padStart, '0') : body}${suffix}`;
}
