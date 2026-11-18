import { ease, kf, register, seg } from '../../kit/kit.js';
import { butterfly } from './mesh.js';
import { CUES, DURATION, EVENTS } from './phrases.js';

const W = 1600;
const H = 900;
const FPS = 30;
const gl = document.getElementById('film').getContext('webgl2', { alpha: false, antialias: true, preserveDrawingBuffer: true });
if (!gl) throw new Error('显色需要 WebGL2');

const header = '#version 300 es\nprecision highp float;\n';
const stageVertex = header + `
out vec2 screenUV;
void main() {
  vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
  screenUV = p;
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}`;
const stageFragment = header + `
in vec2 screenUV;
out vec4 color;
void main() {
  vec2 p = (screenUV - vec2(.49,.55)) * vec2(1.6,1.0);
  float spot = exp(-2.55 * dot(p,p));
  float copper = exp(-3.7 * length(p - vec2(.53,-.25)));
  float grain = fract(sin(dot(gl_FragCoord.xy,vec2(12.31,78.24))) * 34824.51) - .5;
  vec3 paper = mix(vec3(.65,.74,.72),vec3(1.0,.94,.79),spot)
       + copper * vec3(.14,.02,-.025) + grain * .025;
  color = vec4(paper,1.0);
}`;

const sculptureVertex = header + `
layout(location=0) in vec3 point;
layout(location=1) in vec3 facing;
layout(location=2) in float wing;
layout(location=3) in float material;
layout(location=4) in float thickness;
layout(location=5) in vec2 uv;
uniform vec3 eye;
uniform vec3 aim;
uniform vec3 lamp;
uniform vec2 folds;
uniform vec2 tilt;
uniform float lift;
uniform float shadowPass;
out vec3 world;
out vec3 normal;
out vec2 scaleUV;
out float type;
out float film;
vec3 rotY(vec3 p, float a) {
  float s = sin(a), c = cos(a);
  return vec3(p.x*c + p.z*s,p.y,-p.x*s + p.z*c);
}
vec3 rotZ(vec3 p, float a) {
  float s = sin(a), c = cos(a);
  return vec3(p.x*c - p.y*s,p.x*s + p.y*c,p.z);
}
void main() {
  float a = -wing * (wing > 0.0 ? folds.x : folds.y);
  world = rotZ(rotY(rotY(point,a),tilt.x),tilt.y) + vec3(0.0,lift,0.0);
  normal = rotZ(rotY(rotY(facing,a),tilt.x),tilt.y);
  if (shadowPass > 0.5) {
    world = lamp + (world-lamp) * ((-1.92-lamp.z)/(world.z-lamp.z));
  }
  vec3 direction = normalize(aim-eye);
  vec3 right = normalize(cross(direction,vec3(0,1,0)));
  vec3 up = cross(right,direction);
  vec3 offset = world-eye;
  float z = dot(offset,direction);
  gl_Position = vec4(dot(offset,right)*3.21/1.77777778,dot(offset,up)*3.21,1.004*z-.16,z);
  type = material; film = thickness; scaleUV = uv;
}`;

const sculptureFragment = header + `
in vec3 world;
in vec3 normal;
in vec2 scaleUV;
in float type;
in float film;
uniform vec3 eye;
uniform vec3 lamp;
uniform float shadowPass;
uniform float glint;
out vec4 color;
void main() {
  if (shadowPass > .5) {
    color = vec4(.22,.18,.26,.014);
    return;
  }
  vec3 n = normalize(normal);
  vec3 v = normalize(eye-world);
  vec3 l = normalize(lamp-world);
  vec3 h = normalize(l+v);
  n *= dot(n,v) > 0.0 ? 1.0 : -1.0;
  float diff = max(dot(n,l),0.0);
  float shine = max(dot(n,h),0.0);
  float fresnel = pow(1.0-max(dot(n,v),0.0),2.5);
  float rim = max(abs(scaleUV.x),abs(scaleUV.y));
  float fine = cos(86.0 * scaleUV.x + 10.0 * scaleUV.y) * .028;
  float lateral = world.x-lamp.x;
  float attention = .40 + .60 * exp(-.34 * lateral * lateral);
  vec3 result;
  if (type > 0.5 && type < 1.5) {
    float interference = film * .95 + shine * .91 + fresnel * .45;
    vec3 rose = vec3(.54,.085,.30);
    vec3 brass = vec3(.79,.39,.14);
    vec3 teal = vec3(.025,.53,.66);
    vec3 violet = vec3(.18,.095,.45);
    vec3 first = mix(rose,brass,smoothstep(.08,.83,.5+.5*cos(6.283*interference)));
    vec3 second = mix(teal,violet,smoothstep(.15,.80,.5+.5*cos(6.283*(interference+.18))));
    vec3 pigment = mix(first,second,smoothstep(.19,.82,.5+.5*cos(6.283*(interference+.36))));
    vec3 specular = attention * glint * (pow(shine,24.0)*vec3(1.0,.81,.47)*.43 + pow(shine,115.0)*vec3(.88,.91,1.0));
    float edge = smoothstep(.74,1.0,rim);
    result = pigment * (.43 + diff*.69 + fresnel*.19) * (1.0-edge*.44) + specular + fine;
    result += smoothstep(.93,1.0,rim) * vec3(.31,.16,.035) * (.35+diff*.65);
  } else if (type > 1.5) {
    vec3 alloy = type > 2.5 ? vec3(.061,.036,.082) : mix(vec3(.14,.086,.12),vec3(.49,.24,.095),film);
    result = alloy*(.55+diff*.86) + pow(shine,39.0)*vec3(.99,.75,.45)*.68 + fresnel*.13;
  } else {
    result = vec3(.19,.096,.105) * (.75+.40*diff) + pow(shine,24.0)*vec3(.4,.2,.06);
  }
  color = vec4(result,1.0);
}`;

function shader(kind, text) {
  const compiled = gl.createShader(kind);
  gl.shaderSource(compiled, text);
  gl.compileShader(compiled);
  if (!gl.getShaderParameter(compiled, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(compiled));
  return compiled;
}

function program(vertex, fragment) {
  const linked = gl.createProgram();
  gl.attachShader(linked, shader(gl.VERTEX_SHADER, vertex));
  gl.attachShader(linked, shader(gl.FRAGMENT_SHADER, fragment));
  gl.linkProgram(linked);
  if (!gl.getProgramParameter(linked, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(linked));
  return linked;
}

function buffer(data) {
  const va = gl.createVertexArray();
  gl.bindVertexArray(va);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
  let offset = 0;
  [3, 3, 1, 1, 1, 2].forEach((size, index) => {
    gl.enableVertexAttribArray(index);
    gl.vertexAttribPointer(index, size, gl.FLOAT, false, 44, offset * 4);
    offset += size;
  });
  return { va, count: data.length / 11 };
}

const stageProgram = program(stageVertex, stageFragment);
const surfaceProgram = program(sculptureVertex, sculptureFragment);
const { sculpture, shadow } = butterfly();
const body = buffer(sculpture);
const shadowBody = buffer(shadow);
const location = Object.fromEntries(
  ['eye', 'aim', 'lamp', 'folds', 'tilt', 'lift', 'shadowPass', 'glint'].map((name) => [name, gl.getUniformLocation(surfaceProgram, name)]),
);
const shadowSamples = Array.from({ length: 19 }, (_, index) => {
  const angle = index * 2.399963;
  const radius = Math.sqrt(index / 18) * 0.62;
  return [radius * Math.cos(angle), radius * Math.sin(angle)];
});

function draw(geometry) {
  gl.bindVertexArray(geometry.va);
  gl.drawArrays(gl.TRIANGLES, 0, geometry.count);
}

function seek(t) {
  const { rake, secondRake, reveal, open, wingbeat, settle } = CUES;
  const eyeX = kf(t, [[0, 2.6], [reveal, 1.9], [open, 0.00, ease.outSoft], [settle, -0.62], [DURATION, -0.37]]);
  const eyeY = kf(t, [[0, 2.12], [reveal, 1.46], [open, 0.42], [DURATION, 0.47]]);
  const eyeZ = kf(t, [[0, 3.64], [reveal, 4.00], [open, 11.13, ease.outSoft], [DURATION, 11.38]]);
  const aimX = kf(t, [[0, 2.12], [reveal, 1.59], [open, 0.0, ease.outSoft], [DURATION, 0.0]]);
  const aimY = kf(t, [[0, 1.68], [reveal, 1.20], [open, 0.36, ease.outSoft], [DURATION, 0.44]]);
  const foldTrack = [[0, 0.69], [reveal, 0.62], [open, 0.07], [wingbeat - 0.24, 0.12], [wingbeat, 0.66, ease.in], [wingbeat + 0.33, 0.035, ease.out], [settle, 0.09], [DURATION, 0.07]];
  const tilt = kf(t, [[0, -.08], [open, -.05], [wingbeat, .19], [settle, .015], [DURATION, .04]]);
  const lift = kf(t, [[0, 0], [wingbeat-.25, 0], [wingbeat+.54, .32, ease.out], [settle, .16], [DURATION, .16]]);
  const lightX = kf(t, [[0, -1.9], [rake, -.54], [secondRake, 3.52], [reveal, 4.15], [open, 1.8], [wingbeat, -.71], [settle, -2.16], [DURATION, -2.65]]);
  const lightY = kf(t, [[0, 3.4], [reveal, 1.42], [open, 2.8], [settle, 3.64], [DURATION, 3.5]]);
  const glint = 0.78 + .31 * seg(t, rake, 1.35) + .38 * seg(t, wingbeat-.1, .23) * (1.0-seg(t, wingbeat+.24,.75));

  gl.viewport(0, 0, W, H);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  gl.disable(gl.DEPTH_TEST);
  gl.useProgram(stageProgram);
  gl.bindVertexArray(null);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
  gl.useProgram(surfaceProgram);
  gl.uniform3f(location.eye, eyeX, eyeY, eyeZ);
  gl.uniform3f(location.aim, aimX, aimY, 0);
  gl.uniform2f(location.folds, kf(t, foldTrack), kf(t - 0.057, foldTrack) + 0.055);
  gl.uniform2f(location.tilt, tilt, -.128 + lift*.46);
  gl.uniform1f(location.lift, lift);
  gl.uniform1f(location.glint, glint);
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  gl.uniform1f(location.shadowPass, 1);
  for (const [x, y] of shadowSamples) {
    gl.uniform3f(location.lamp, lightX + x, lightY + y, 5.6);
    draw(shadowBody);
  }
  gl.disable(gl.BLEND);
  gl.enable(gl.DEPTH_TEST);
  gl.uniform1f(location.shadowPass, 0);
  gl.uniform3f(location.lamp, lightX, lightY, 5.6);
  draw(body);
}

register({ width: W, height: H, fps: FPS, duration: DURATION, seek, meta: { events: EVENTS } });
seek(0);
