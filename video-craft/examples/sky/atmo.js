// atmo.js — physically based sky (single Rayleigh + Mie scattering) rendered with WebGL2 at low resolution.
const VS = `#version 300 es
in vec2 p; void main(){ gl_Position = vec4(p, 0.0, 1.0); }`;
const FS = `#version 300 es
precision highp float;
out vec4 o;
uniform vec2 uRes;
uniform vec3 uSun;
uniform float uPitch, uYaw, uF, uAlt, uExposure, uAspect;
#define PI 3.14159265
#define RP 6371e3
#define RA 6471e3
const vec3 kRlh = vec3(5.5e-6, 13.0e-6, 22.4e-6);
const float kMie = 21e-6;
const float shRlh = 8e3, shMie = 1.2e3, g = 0.758, iSun = 22.0;
const vec3 kOz = vec3(0.650e-6, 1.881e-6, 0.085e-6);
float oz(float h) { return max(0.0, 1.0 - abs(h - 25e3) / 15e3); }
uniform float uSat;

vec2 rsi(vec3 r0, vec3 rd, float sr) {
  float b = 2.0 * dot(rd, r0), c = dot(r0, r0) - sr * sr, d = b * b - 4.0 * c;
  if (d < 0.0) return vec2(1e9, -1e9);
  d = sqrt(d);
  return vec2((-b - d) * 0.5, (-b + d) * 0.5);
}

vec3 sky(vec3 r, vec3 r0, vec3 s, out vec3 trans, out float hitGround) {
  trans = vec3(1.0); hitGround = 0.0;
  vec2 pa = rsi(r0, r, RA);
  if (pa.x > pa.y || pa.y < 0.0) return vec3(0.0);
  float t0 = max(pa.x, 0.0), t1 = pa.y;
  vec2 pg = rsi(r0, r, RP);
  if (pg.x < pg.y && pg.x > 0.0) { t1 = min(t1, pg.x); hitGround = 1.0; }
  const int IS = 20, JS = 8;
  float ds = (t1 - t0) / float(IS), t = t0;
  vec3 sumR = vec3(0.0), sumM = vec3(0.0);
  float odR = 0.0, odM = 0.0, odO = 0.0;
  float mu = dot(r, s), mumu = mu * mu, gg = g * g;
  float pR = 3.0 / (16.0 * PI) * (1.0 + mumu);
  float pM = 3.0 / (8.0 * PI) * ((1.0 - gg) * (mumu + 1.0)) / (pow(1.0 + gg - 2.0 * mu * g, 1.5) * (2.0 + gg));
  for (int i = 0; i < IS; i++) {
    vec3 p = r0 + r * (t + ds * 0.5);
    float h = length(p) - RP;
    float dR = exp(-h / shRlh) * ds, dM = exp(-h / shMie) * ds;
    odR += dR; odM += dM; odO += oz(h) * ds;
    // light from the sun to this sample; blocked by the planet → no light
    vec2 ps = rsi(p, s, RP);
    float shadow = (ps.x < ps.y && ps.x > 0.0) ? 0.0 : 1.0;
    float js = rsi(p, s, RA).y / float(JS), jt = 0.0, jR = 0.0, jM = 0.0, jO = 0.0;
    for (int j = 0; j < JS; j++) {
      vec3 q = p + s * (jt + js * 0.5);
      float hq = length(q) - RP;
      jR += exp(-hq / shRlh) * js; jM += exp(-hq / shMie) * js; jO += oz(hq) * js; jt += js;
    }
    vec3 att = exp(-(kMie * 1.1 * (odM + jM) + kRlh * (odR + jR) + kOz * (odO + jO))) * shadow;
    sumR += dR * att; sumM += dM * att;
    t += ds;
  }
  trans = exp(-(kMie * 1.1 * odM + kRlh * odR + kOz * odO));
  return iSun * (pR * kRlh * sumR + pM * kMie * sumM);
}

void main() {
  vec2 uv = (gl_FragCoord.xy / uRes) * 2.0 - 1.0;
  vec3 d = normalize(vec3(uv.x * uAspect, uv.y, uF));
  float cp = cos(uPitch), sp = sin(uPitch);
  d = vec3(d.x, d.y * cp + d.z * sp, -d.y * sp + d.z * cp);
  float cy = cos(uYaw), sy = sin(uYaw);
  d = vec3(d.x * cy + d.z * sy, d.y, -d.x * sy + d.z * cy);
  vec3 r0 = vec3(0.0, RP + uAlt, 0.0);
  vec3 tr; float gnd;
  vec3 c = sky(d, r0, normalize(uSun), tr, gnd);
  if (gnd > 0.5) {
    vec2 pg = rsi(r0, d, RP);
    vec3 hp = r0 + d * pg.x, n = normalize(hp);
    float lit = max(dot(n, normalize(uSun)), 0.0);
    c += vec3(0.035, 0.05, 0.045) * iSun * 0.08 * lit * tr;
  }
  c = 1.0 - exp(-uExposure * c);
  float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
  c = max(vec3(0.0), mix(vec3(l), c, uSat));
  o = vec4(c, 1.0);
}`;

export function createSky(w, h) {
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  const gl = cv.getContext('webgl2', { preserveDrawingBuffer: true, antialias: false });
  const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
  const pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(pr);
  if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(pr));
  gl.useProgram(pr);
  const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(pr, 'p'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  const U = (n) => gl.getUniformLocation(pr, n);
  const u = { sat: U('uSat'), res: U('uRes'), sun: U('uSun'), pitch: U('uPitch'), yaw: U('uYaw'), f: U('uF'), alt: U('uAlt'), exp: U('uExposure'), aspect: U('uAspect') };
  const px = new Uint8Array(4);
  return {
    canvas: cv,
    // cam: { pitch, yaw, fov (vertical, radians), alt (m) }, sun: { el, az } radians
    render(cam, sun, exposure = 1.0, sat = 1.0) {
      gl.uniform1f(u.sat, sat);
      gl.viewport(0, 0, w, h);
      gl.uniform2f(u.res, w, h);
      gl.uniform3f(u.sun, Math.cos(sun.el) * Math.sin(sun.az), Math.sin(sun.el), Math.cos(sun.el) * Math.cos(sun.az));
      gl.uniform1f(u.pitch, cam.pitch); gl.uniform1f(u.yaw, cam.yaw || 0);
      gl.uniform1f(u.f, 1 / Math.tan(cam.fov / 2)); gl.uniform1f(u.alt, cam.alt); gl.uniform1f(u.exp, exposure);
      gl.uniform1f(u.aspect, w / h);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    },
    sample(x, y) { gl.readPixels(Math.round(x * (w - 1)), Math.round((1 - y) * (h - 1)), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); return [px[0], px[1], px[2]]; },
  };
}

// project a world direction (elevation, azimuth) to screen pixels for the same camera
export function project(cam, el, az, W, H) {
  const dx = Math.cos(el) * Math.sin(az), dy = Math.sin(el), dz = Math.cos(el) * Math.cos(az);
  const cy = Math.cos(-(cam.yaw || 0)), sy = Math.sin(-(cam.yaw || 0));
  let x = dx * cy + dz * sy, y = dy, z = -dx * sy + dz * cy;
  const cp = Math.cos(-cam.pitch), sp = Math.sin(-cam.pitch);
  [y, z] = [y * cp + z * sp, -y * sp + z * cp];
  const f = 1 / Math.tan(cam.fov / 2);
  if (z <= 0.001) return null;
  return [W / 2 + (x / z) * f * (H / 2), H / 2 - (y / z) * f * (H / 2)];
}
