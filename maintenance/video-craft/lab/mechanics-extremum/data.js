// data.js — Single source of truth for the mechanics extremum lesson.
// Every vector length, angle, curve point, and numerical readout in scene.js comes from these exact formulas.

export const MU = 0.75;                                // coefficient of kinetic friction μ = 3/4 (classic 3-4-5 triangle)
export const PHI_RAD = Math.atan(MU);                  // friction angle φ = arctan(3/4) ≈ 0.6435 rad
export const PHI_DEG = (PHI_RAD * 180) / Math.PI;      // ≈ 36.87° (37° in standard physics problems)
export const HYPOT_FACTOR = Math.hypot(1, MU);         // √(1 + μ²) = 1.25 = 5/4

// Pull force normalized by weight mg: F(α) / mg = μ / (cos α + μ sin α)
export function pullRatio(alphaDeg) {
  const a = (alphaDeg * Math.PI) / 180;
  return MU / (Math.cos(a) + MU * Math.sin(a));
}

// Normal force normalized by weight mg: F_N(α) / mg = 1 - (F/mg) sin α
export function normalRatio(alphaDeg) {
  const a = (alphaDeg * Math.PI) / 180;
  const f = pullRatio(alphaDeg);
  return Math.max(0, 1 - f * Math.sin(a));
}

// Kinetic friction normalized by weight mg: f(α) / mg = μ * (F_N / mg)
export function frictionRatio(alphaDeg) {
  return MU * normalRatio(alphaDeg);
}

// Downward push force normalized by weight mg: F_push(θ) / mg = μ / (cos θ - μ sin θ), self-locks when cos θ <= μ sin θ
export function pushRatio(thetaDeg) {
  const a = (thetaDeg * Math.PI) / 180;
  const denom = Math.cos(a) - MU * Math.sin(a);
  return denom <= 1e-4 ? Infinity : MU / denom;
}

export const F_HORIZ = pullRatio(0);                   // 0.75 (3/4 mg)
export const F_MIN = MU / HYPOT_FACTOR;                // 0.60 (3/5 mg)
export const SAVING_PCT = Math.round((1 - F_MIN / F_HORIZ) * 100); // 20%
export const LOCK_DEG = 90 - PHI_DEG;                  // ≈ 53.13° (53° critical self-locking push angle)
