// data.js — Single source of truth for the stem-lesson example.
export const MU = 0.75;                                // μ = 3/4
export const PHI_RAD = Math.atan(MU);                  // φ = arctan(3/4) ≈ 0.643501 rad
export const PHI_DEG = (PHI_RAD * 180) / Math.PI;      // ≈ 36.8699°
export const HYPOT_FACTOR = Math.hypot(1, MU);         // 5/4 = 1.25

export function pullRatio(alphaDeg) {
  const a = (alphaDeg * Math.PI) / 180;
  return MU / (Math.cos(a) + MU * Math.sin(a));
}

export function normalRatio(alphaDeg) {
  const a = (alphaDeg * Math.PI) / 180;
  return Math.max(0, 1 - pullRatio(alphaDeg) * Math.sin(a));
}

export function frictionRatio(alphaDeg) {
  return MU * normalRatio(alphaDeg);
}

export const F_HORIZ = pullRatio(0);                   // 0.75
export const F_MIN = MU / HYPOT_FACTOR;                // 0.60
export const SAVING_PCT = Math.round((1 - F_MIN / F_HORIZ) * 100); // 20%
