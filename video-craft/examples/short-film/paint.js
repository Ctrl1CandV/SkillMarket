import { clamp, rng } from '../../kit/kit.js';

export const W = 1280;
export const H = 576;

export function polygon(g, points, fill, stroke, width = 1) {
  g.beginPath();
  g.moveTo(...points[0]);
  for (const p of points.slice(1)) g.lineTo(...p);
  g.closePath();
  if (fill) { g.fillStyle = fill; g.fill(); }
  if (stroke) { g.strokeStyle = stroke; g.lineWidth = width; g.stroke(); }
}

export function line(g, points, color, width = 1) {
  g.beginPath();
  g.moveTo(...points[0]);
  for (const p of points.slice(1)) g.lineTo(...p);
  g.strokeStyle = color;
  g.lineWidth = width;
  g.stroke();
}

export function linear(g, x0, y0, x1, y1, stops) {
  const gradient = g.createLinearGradient(x0, y0, x1, y1);
  for (const [at, color] of stops) gradient.addColorStop(at, color);
  return gradient;
}

export function radial(g, x, y, radius, stops) {
  const gradient = g.createRadialGradient(x, y, 0, x, y, radius);
  for (const [at, color] of stops) gradient.addColorStop(at, color);
  return gradient;
}

export function light(g, x, y, rx, ry, stops) {
  g.save();
  g.translate(x, y);
  g.scale(rx, ry);
  g.fillStyle = radial(g, 0, 0, 1, stops);
  g.fillRect(-1, -1, 2, 2);
  g.restore();
}

function noiseOctave(random, size) {
  const stride = size + 1;
  const grid = Float32Array.from({ length: stride * stride }, () => random());
  const smooth = (x) => x * x * (3 - 2 * x);
  return (u, v) => {
    const x = u * size, y = v * size;
    const col = Math.floor(x), row = Math.floor(y), i = row * stride + col;
    const s = smooth(x - col), t = smooth(y - row);
    const a = grid[i] * (1 - s) + grid[i + 1] * s;
    const b = grid[i + stride] * (1 - s) + grid[i + stride + 1] * s;
    return a * (1 - t) + b * t;
  };
}

export function texture(seed, width, height, colorAt) {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const g = canvas.getContext('2d');
  const bitmap = g.createImageData(width, height);
  const random = rng(seed);
  const octaves = [4, 9, 18, 35, 72].map((size) => noiseOctave(random, size));
  for (let y = 0, i = 0; y < height; y++) {
    for (let x = 0; x < width; x++, i += 4) {
      const u = x / width, v = y / height;
      const fog = octaves.reduce((sum, sample, n) => sum + sample(u, v) * 0.52 ** n, 0) * 0.5;
      const [red, green, blue, alpha] = colorAt(u, v, fog, random());
      bitmap.data[i] = red;
      bitmap.data[i + 1] = green;
      bitmap.data[i + 2] = blue;
      bitmap.data[i + 3] = alpha;
    }
  }
  g.putImageData(bitmap, 0, 0);
  return canvas;
}

const rain = (() => {
  const random = rng(626);
  return Array.from({ length: 470 }, () => [random() * 1380, random() * 660, random(), random()]);
})();

export function rainfall(g, t, amount = 1, warm = 0) {
  for (let layer = 0; layer < 3; layer++) {
    g.strokeStyle = warm ? `rgba(230,199,158,${amount * (0.08 + layer * 0.025)})` : `rgba(160,193,212,${amount * (0.08 + layer * 0.025)})`;
    g.lineWidth = 0.45 + layer * 0.38;
    g.beginPath();
    for (let i = layer; i < rain.length; i += 3) {
      const [x, y, size, speed] = rain[i];
      const px = ((x + t * (110 + speed * 95)) % 1380) - 50;
      const py = ((y + t * (330 + speed * 240)) % 660) - 60;
      const len = (5 + size * 12) * (layer + 1) / 1.8;
      g.moveTo(px, py);
      g.lineTo(px - len * 0.4, py - len);
    }
    g.stroke();
  }
}

const filmGrain = [1, 2, 3, 4].map((seed) => texture(seed, 360, 164, (_, __, ___, grain) => {
  const color = 255 * (grain > 0.5);
  return [color, color, color, 12 * Math.abs(grain - 0.5)];
}));

export function grade(g, frame, vignette = 0.55) {
  light(g, W * 0.5, H * 0.46, W * 0.71, H * 0.89, [[0.39, '#0000'], [1, `rgba(0,4,12,${clamp(vignette)})`]]);
  g.drawImage(filmGrain[frame % filmGrain.length], 0, 0, W, H);
}
