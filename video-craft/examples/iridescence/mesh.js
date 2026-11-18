import { rng } from '../../kit/kit.js';

const TAU = 2 * Math.PI;
const upper = [[0, 0.09], [0.61, 1.36], [1.77, 2.55], [3.12, 3.04], [3.92, 2.89], [3.96, 2.40], [3.7, 1.71], [3.23, 1.01], [2.36, 0.53], [1.38, 0.28]];
const lower = [[0, -0.06], [1.24, 0.22], [2.44, 0.19], [3.16, -0.37], [3.35, -0.94], [3.09, -1.63], [2.48, -2.18], [1.72, -2.38], [1.13, -1.98], [0.62, -1.19]];

function closedCurve(points) {
  const polygon = [];
  const count = points.length;
  for (let i = 0; i < count; i++) {
    const p = [points[(i + count - 1) % count], points[i], points[(i + 1) % count], points[(i + 2) % count]];
    for (let j = 0; j < 8; j++) {
      const s = j / 8;
      polygon.push([0, 1].map((axis) => {
        const [a, b, c, d] = p.map((v) => v[axis]);
        return 0.5 * (2 * b + (c - a) * s + (2 * a - 5 * b + 4 * c - d) * s * s + (3 * b - a - 3 * c + d) * s * s * s);
      }));
    }
  }
  return polygon;
}

function contains(polygon, x, y) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [a, b] = polygon[i], [c, d] = polygon[j];
    if ((b > y) !== (d > y) && x < (c - a) * (y - b) / (d - b) + a) inside = !inside;
  }
  return inside;
}

function membrane(x, y, lowerWing) {
  return 0.18 * Math.sin(x * 0.69 + y * 0.52) + y * y * 0.012 - (lowerWing ? 0.085 : 0);
}

function wing(data, back, points, side, lowerWing, random) {
  const outline = closedCurve(points);
  const height = (x, y) => membrane(x, y, lowerWing);
  const face = (x, y, z, kind, tint, u, v, nx, ny) => [side * x, y, z, side * nx, ny, 1, side, kind, tint, u, v];
  const center = face(1.9, lowerWing ? -0.94 : 1.34, height(1.9, lowerWing ? -0.94 : 1.34), 0, 0.45, 0, 0, 0, 0);
  const border = outline.map(([x, y]) => face(x, y, height(x, y), 0, 0.45, 0, 0, 0, 0));
  for (let i = 0; i < border.length; i++) {
    const triangle = [...center, ...border[i], ...border[(i + 1) % border.length]];
    data.push(...triangle);
    back.push(...triangle);
  }

  const terrace = [];
  let row = 0;
  const step = 0.136;
  for (let y = lowerWing ? -2.47 : 0.03; y < (lowerWing ? 0.31 : 3.13); y += step, row++) {
    for (let x = 0.09 + (row % 2) * step / 2; x < 4.08; x += step) {
      const px = x + (random() - 0.5) * 0.038;
      const py = y + (random() - 0.5) * 0.036;
      if (contains(outline, px, py)) terrace.push([px, py]);
    }
  }
  for (const [x, y] of terrace) {
    const r = Math.hypot(x - 0.1, y * 0.93);
    const angle = Math.atan2(y, x) + (random() - 0.5) * 0.28;
    const along = [Math.cos(angle), Math.sin(angle)];
    const across = [-along[1], along[0]];
    const len = 0.12 + random() * 0.049 + Math.min(r, 4) * 0.008;
    const half = 0.065 + random() * 0.021;
    const z = height(x, y) + 0.011 * x;
    const tint = r * 0.22 + Math.sin(y * 2.7 + x * 1.7) * 0.075 + random() * 0.25 + (lowerWing ? 0.19 : 0);
    const rim = [
      [-0.35, -1], [0.35, -1], [0.91, -0.55], [1, 0.24], [0.64, 0.79], [0.16, 1],
      [-0.38, 0.95], [-0.83, 0.61], [-1, 0.0], [-0.85, -0.57],
    ].map(([u, v]) => face(
      x + across[0] * half * u + along[0] * len * v,
      y + across[1] * half * u + along[1] * len * v,
      z + v * 0.012, 1, tint, u, v,
      (u * across[0] * 0.57 + v * along[0] * 0.32) - 0.17 * Math.cos(x * 0.69 + y * 0.52),
      u * across[1] * 0.57 + v * along[1] * 0.32 - 0.06 * y,
    ));
    const peak = face(x, y, z + 0.06 + 0.035 * random(), 1, tint, 0, 0, -0.14 * Math.cos(x), -0.04 * y);
    for (let i = 0; i < rim.length; i++) data.push(...peak, ...rim[i], ...rim[(i + 1) % rim.length]);
  }
}

function shell(data, x, y, z, rx, ry, rz, kind, tint, slices = 24) {
  const rings = 16;
  function vertex(v, h) {
    const phi = -Math.PI / 2 + Math.PI * v / rings;
    const a = TAU * h / slices;
    const dx = Math.cos(phi) * Math.cos(a), dy = Math.sin(phi), dz = Math.cos(phi) * Math.sin(a);
    return [x + rx * dx, y + ry * dy, z + rz * dz, dx, dy, dz, 0, kind, tint, h / slices, v / rings];
  }
  for (let v = 0; v < rings; v++) {
    for (let h = 0; h < slices; h++) {
      const a = vertex(v, h), b = vertex(v, h + 1), c = vertex(v + 1, h + 1), d = vertex(v + 1, h);
      data.push(...a, ...b, ...c, ...a, ...c, ...d);
    }
  }
}

function antenna(data, side) {
  const count = 31;
  const vertex = (i, a) => {
    const t = i / count;
    const x = side * (0.08 + t * 0.24 + t ** 2 * 0.65);
    const y = 0.6 + t * 1.34;
    const z = 0.17 + t * 0.31;
    const r = 0.038 - t * 0.02;
    const u = Math.cos(TAU * a / 7), v = Math.sin(TAU * a / 7);
    return [x + r * u, y, z + r * v, u, 0, v, 0, 2, 0.6, a / 7, t];
  };
  for (let i = 0; i < count; i++) {
    for (let a = 0; a < 7; a++) {
      const u = vertex(i, a), v = vertex(i, a + 1), w = vertex(i + 1, a + 1), x = vertex(i + 1, a);
      data.push(...u, ...v, ...w, ...u, ...w, ...x);
    }
  }
  shell(data, side * 0.97, 1.94, 0.48, 0.052, 0.076, 0.05, 2, 0.8, 10);
}

export function butterfly() {
  const random = rng(66);
  const data = [];
  const shadow = [];
  for (const side of [-1, 1]) {
    wing(data, shadow, lower, side, true, random);
    wing(data, shadow, upper, side, false, random);
    antenna(data, side);
  }
  shell(data, 0, 0.47, 0.15, 0.2, 0.26, 0.24, 2, 0.51);
  shell(data, 0, 0.09, 0.16, 0.27, 0.55, 0.26, 2, 0.25);
  shell(data, 0, -0.7, 0.13, 0.19, 0.74, 0.17, 2, 0.43);
  for (let i = 0; i < 5; i++) {
    const narrow = 1 - i * 0.11;
    shell(data, 0, -0.48 - i * 0.17, 0.14, narrow * 0.204, 0.052, narrow * 0.18, 2, 0.67);
  }
  for (const side of [-1, 1]) shell(data, side * 0.125, 0.56, 0.3, 0.076, 0.085, 0.08, 3, 0.32, 12);
  return { sculpture: new Float32Array(data), shadow: new Float32Array(shadow) };
}
