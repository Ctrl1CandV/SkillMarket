// graphic-parts — every part of kit/graphic.js in turn, 2.4 s each, for checking frames (not shipped with the skill)
import { register, kf, ease, clamp } from '../../../../video-craft/kit/kit.js';
import { layer, finish } from '../../../../video-craft/kit/draw.js';
import { paper, grid, rule, marks, slant, label, headline, glitch, card, scrim, ring, ruler, wave, surface, shapes, wipe, iris, halftone } from '../../../../video-craft/kit/graphic.js';

const W = 1920, H = 1080, SEG = 2.4;
const PAPER = '#ECE7DC', INK = '#16181D', RED = '#E2432E', BLUE = '#2B55E6', CYAN = '#7FD3DC';
const ctx = document.getElementById('cv').getContext('2d');

// a code-drawn "photo" for the card: dusk street of light bars
const PHOTO = layer(800, 500);
{
  const g = PHOTO.getContext('2d'), sky = g.createLinearGradient(0, 0, 0, 500);
  sky.addColorStop(0, '#1d2742'); sky.addColorStop(1, '#c86b4f'); g.fillStyle = sky; g.fillRect(0, 0, 800, 500);
  for (let i = 0; i < 40; i++) { g.fillStyle = `rgba(255,${180 + (i * 7) % 60},120,${0.2 + (i % 5) * 0.12})`; g.fillRect((i * 97) % 800, 260 + (i * 31) % 160, 6 + (i % 4) * 4, 40 + (i % 7) * 12); }
  g.fillStyle = '#0d1018'; g.fillRect(0, 430, 800, 70);
}

const sceneA = (c) => { paper(c, PAPER); headline(c, ['画面 A'], 160, 380, 9, { size: 200, mode: 'cut', color: INK }); };
const sceneB = (c) => { c.fillStyle = INK; c.fillRect(0, 0, W, H); ring(c, 1300, 540, 260, 1, { color: CYAN, width: 3, ticks: 60, tickLen: 14 }); headline(c, ['画面 B'], 160, 380, 9, { size: 200, mode: 'cut', color: PAPER }); };

function seek(t) {
  const i = Math.min(9, Math.floor(t / SEG)), u = t - i * SEG, frame = Math.round(t * 30);
  ctx.clearRect(0, 0, W, H);
  if (i === 0) {
    paper(ctx, PAPER);
    const g = grid(ctx, clamp(u / 1.2), { x: 120, y: 120, w: 1680, h: 840, cols: 12, rows: 6, color: 'rgba(22,24,29,.10)' });
    rule(ctx, g.x[0], 150, 260, clamp((u - 0.2) / 0.5), { color: RED, width: 6 });
    label(ctx, 'LINE MAP / 01', g.x[0], 200, u - 0.3, { size: 22, color: INK });
    headline(ctx, ['图上两站挨着，', { text: '走起来二十分钟。', accent: [3, 7, RED] }], g.x[0], 300, u - 0.5, { size: 120 });
    marks(ctx, g.x[8], g.y[2], 500, 300, clamp((u - 0.8) / 0.5), { color: INK });
  } else if (i === 1) {
    paper(ctx, PAPER);
    headline(ctx, ['破静'], 960, 320, u - 0.2, { size: 300, mode: 'slam', align: 'center' });
    label(ctx, 'BREAK THE SILENCE', 960, 760, u - 0.9, { size: 28, align: 'center', color: INK });
    headline(ctx, ['cut, then leaves'], 160, 160, u, { size: 36, mode: 'cut', color: RED, exit: u - 1.6 });
  } else if (i === 2) {
    ctx.fillStyle = INK; ctx.fillRect(0, 0, W, H);
    headline(ctx, ['ON AXIS'], 960, 220, u - 0.1, { size: 160, mode: 'track', align: 'center', color: PAPER, font: '"Oswald", "Bahnschrift", sans-serif', weight: 700 });
    headline(ctx, ['噪声'], 960, 560, u - 0.6, { size: 220, mode: 'glitch', align: 'center', color: RED });
  } else if (i === 3) {
    paper(ctx, PAPER);
    slant(ctx, kf(u, [[0, W + 200], [0.7, 1380, ease.out]]), 900, { color: BLUE });
    card(ctx, PHOTO, 160, 260, 760, 470, u - 0.2, { shadow: { color: 'rgba(22,24,29,.22)' }, frame: INK, pad: 14, markColor: INK });
    label(ctx, 'FIG. 2  街道 / 夜', 160, 800, u - 0.6, { size: 22, color: INK });
    headline(ctx, ['耳朵先到'], 1000, 300, u - 0.5, { size: 110, color: INK });
  } else if (i === 4) {
    ctx.fillStyle = INK; ctx.fillRect(0, 0, W, H);
    ring(ctx, 1300, 540, 300, clamp(u / 1), { color: 'rgba(237,235,230,.35)', width: 1, ticks: 72, tickLen: 12, rot: u * 0.3 });
    ring(ctx, 1300, 540, 240, clamp((u - 0.2) / 1), { color: RED, width: 6, sweep: Math.PI * 1.2, rot: -u * 0.8 });
    ring(ctx, 1300, 540, 200, clamp((u - 0.3) / 1), { color: CYAN, width: 2, sweep: Math.PI * 0.6, rot: u * 1.4 });
    ruler(ctx, 160, 900, 800, clamp(u / 1.2), { color: 'rgba(237,235,230,.6)' });
    wave(ctx, 160, 700, 800, 160, (x, k) => 0.15 + 0.85 * Math.abs(Math.sin(x * 23 + u * 3) * Math.sin(x * 5.3)), clamp(u / 0.8), { color: 'rgba(237,235,230,.5)', accent: CYAN, head: clamp(u / 2.2) });
    label(ctx, 'SUB  -12.4 dB', 160, 300, u - 0.2, { size: 24, color: PAPER });
    label(ctx, 'MID  -06.1 dB', 160, 340, u - 0.4, { size: 24, color: RED });
  } else if (i === 5 || i === 6) {
    ctx.fillStyle = '#132232'; ctx.fillRect(0, 0, W, H);
    grid(ctx, 1, { x: 80, y: 80, w: 1760, h: 920, cols: 12, rows: 6, color: 'rgba(127,211,220,.08)' });
    surface(ctx, shapes.ribbon({ phase: t * 0.6 }), { x: 1100, y: 540, size: 300, rot: [0.9 + 0.2 * Math.sin(t), t * 0.5, 0.3], edge: RED, burst: i === 6 ? ease.out(clamp(u / 1.6)) : 0, front: '#EDEBE6', back: CYAN });
    label(ctx, i === 6 ? '击穿' : 'SCAN', 160, 200, u - 0.1, { size: 40, color: PAPER });
  } else {
    const k = clamp((u - 0.4) / 1.2);
    sceneA(ctx);
    if (i === 7) wipe(ctx, k, sceneB, { color: RED });
    if (i === 8) iris(ctx, k, sceneB, { x: 1300, y: 540, ring: RED });
    if (i === 9) halftone(ctx, k, sceneB, { color: RED, pitch: 56 });
  }
  finish(ctx, frame, { vignette: 0, grain: 0.04 });
}

register({ duration: SEG * 10, fps: 30, width: W, height: H, seek });
seek(0);
