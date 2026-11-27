// shader.js — run a full-screen GLSL fragment shader as a layer you draw into a 2D canvas.
// Use it for what per-pixel maths does best: nebulae, aurora, liquid light, caustics, smoke, glow fields.
//
//   import { shader } from '<kit>/shader.js';
//   const neb = shader(1920, 1080, `
//     void main() {
//       vec2 p = (gl_FragCoord.xy - 0.5 * res) / res.y;
//       o = vec4(0.5 + 0.5 * cos(t + p.xyx + vec3(0, 2, 4)), 1.0);
//     }`, { scale: 0.5 });
//   function seek(t) { neb.draw(t, { glow: 0.5 + 0.5 * Math.sin(t) }); ctx.drawImage(neb.canvas, 0, 0, 1920, 1080); … }
//
// The fragment source gets `uniform float t; uniform vec2 res; out vec4 o;` plus one `uniform float` (or vecN)
// per key you pass to draw(); those three names are taken. `hash(vec2)`, `noise(vec2)` and `fbm(vec2)` are
// predefined. A key you pass only on some frames: list it in `uniforms: ['glow']` so it is always declared;
// frames that leave it out get 0. Everything stays a pure function of t and the keys, so frames can be
// rendered in any order. scale < 1 renders smaller and lets drawImage upscale (soft subjects such as nebulae
// lose nothing at 0.5 and render 4x faster on software GL).
const HEADER = `#version 300 es
precision highp float;
uniform float t;
uniform vec2 res;
out vec4 o;
float hash(vec2 p) { vec3 q = fract(p.xyx * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p), u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int k = 0; k < 6; k++) { s += a * noise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s; }
`;
const SDF_LIB = `
mat2 rot2(float a) { float c = cos(a), s = sin(a); return mat2(c, -s, s, c); }
float smin(float a, float b, float k) {
  float h = max(k - abs(a - b), 0.0) / max(k, 1e-5);
  return min(a, b) - h * h * k * 0.25;
}
float sdSphere(vec3 p, float r) { return length(p) - r; }
float sdRoundBox(vec3 p, vec3 b, float r) {
  vec3 q = abs(p) - b;
  return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0) - r;
}
float sdTorus(vec3 p, vec2 t) { vec2 q = vec2(length(p.xz) - t.x, p.y); return length(q) - t.y; }
float sdCapsule(vec3 p, vec3 a, vec3 b, float r) {
  vec3 pa = p - a, ba = b - a;
  float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-5), 0.0, 1.0);
  return length(pa - ba * h) - r;
}
vec3 opRep(vec3 p, vec3 s) { return mod(p + 0.5 * s, s) - 0.5 * s; }
vec3 thinFilm(float cosTheta, float phase) {
  return 0.5 + 0.5 * cos(6.28318 * (cosTheta + phase) + vec3(0.0, 2.094, 4.188));
}
vec3 aces(vec3 x) {
  return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0);
}
vec3 toSrgb(vec3 c) { return pow(max(c, vec3(0.0)), vec3(1.0 / 2.2)); }
`;

const VERT = `#version 300 es
void main() { vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2); gl_Position = vec4(p * 2.0 - 1.0, 0, 1); }`;

const RESERVED = new Set(['t', 'res', 'o']);

export function shader(width, height, frag, { scale = 1, uniforms = [], sdf = false } = {}) {
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(width * scale));
  canvas.height = Math.max(1, Math.round(height * scale));
  const gl = canvas.getContext('webgl2', { preserveDrawingBuffer: true, premultipliedAlpha: false });
  if (!gl) throw new Error('shader(): WebGL2 is not available in this browser (run doctor.mjs)');
  const compile = (type, src) => {
    const s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error('shader(): ' + gl.getShaderInfoLog(s));
    return s;
  };
  const programs = new Map();                      // one per set of uniform names and sizes, built once
  const build = (sizes) => {
    const head = HEADER + (sdf ? SDF_LIB : '') + [...sizes].map(([k, n]) => `uniform ${n === 1 ? 'float' : 'vec' + n} ${k};\n`).join('');
    let prog = programs.get(head);
    if (prog) return prog;
    prog = gl.createProgram();
    const vs = compile(gl.VERTEX_SHADER, VERT), fs = compile(gl.FRAGMENT_SHADER, head + frag);
    gl.attachShader(prog, vs); gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    gl.deleteShader(vs); gl.deleteShader(fs);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error('shader(): ' + gl.getProgramInfoLog(prog));
    programs.set(head, prog);
    return prog;
  };
  function draw(time, extra = {}) {
    const sizes = new Map(uniforms.map((k) => [k, 1]));
    for (const [k, v] of Object.entries(extra)) {
      if (RESERVED.has(k)) throw new Error(`shader(): "${k}" is predefined; give this uniform another name`);
      sizes.set(k, Array.isArray(v) ? v.length : 1);
    }
    const prog = build(sizes);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.useProgram(prog);
    gl.uniform1f(gl.getUniformLocation(prog, 't'), time);
    gl.uniform2f(gl.getUniformLocation(prog, 'res'), canvas.width, canvas.height);
    for (const [k, n] of sizes) {                  // every declared key, every frame: none keeps last frame's value
      const at = gl.getUniformLocation(prog, k), v = extra[k] ?? (n === 1 ? 0 : new Array(n).fill(0));
      if (n === 1) gl.uniform1f(at, v);
      else gl[`uniform${n}fv`](at, v);
    }
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    return canvas;
  }
  return { canvas, draw };
}
