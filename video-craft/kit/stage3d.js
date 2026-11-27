// stage3d.js — Tier-2 3D PBR, procedural HDR studio lightformers, InstancedMesh choreography,
// and multi-pass HDR Mipmap Bloom + ACES Filmic + Chromatic Dispersion post-processing (Three.js r160).
// Pure functions of `t` inside `seek(t)`: works offline over `file://` with zero external HDRI downloads,
// scales automatically with `render.mjs --draft`, and degrades safely under `VC_SOFTWARE_GL=1`.
import * as THREE from './vendor/three/three.module.min.js';
import { GLTFLoader } from './vendor/three/loaders/GLTFLoader.js';

export { THREE, GLTFLoader };

const QUAD_VERT = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = vec4(position.xy, 0.0, 1.0);
}`;

// Pass 0: Karis-weighted 4-tap HDR prefilter + soft-knee threshold (prevents sub-pixel specular firefly strobing).
const PREFILTER_FRAG = /* glsl */ `
precision highp float;
varying vec2 vUv;
uniform sampler2D tInput;
uniform vec2 uTexel;
uniform float uThreshold;
uniform float uKnee;
uniform float uClampMax;

float luma(vec3 c) { return dot(c, vec3(0.2126, 0.7152, 0.0722)); }

vec3 softThreshold(vec3 c) {
  float br = max(max(c.r, c.g), c.b);
  float rq = clamp(br - uThreshold + uKnee, 0.0, 2.0 * uKnee);
  rq = (rq * rq) / (4.0 * uKnee + 1e-5);
  float w = max(rq, br - uThreshold) / max(br, 1e-5);
  return min(c * max(0.0, w), vec3(uClampMax));
}

void main() {
  vec2 o = uTexel * 0.5;
  vec3 c0 = texture2D(tInput, vUv + vec2(-o.x, -o.y)).rgb;
  vec3 c1 = texture2D(tInput, vUv + vec2( o.x, -o.y)).rgb;
  vec3 c2 = texture2D(tInput, vUv + vec2(-o.x,  o.y)).rgb;
  vec3 c3 = texture2D(tInput, vUv + vec2( o.x,  o.y)).rgb;
  float w0 = 1.0 / (1.0 + luma(c0));
  float w1 = 1.0 / (1.0 + luma(c1));
  float w2 = 1.0 / (1.0 + luma(c2));
  float w3 = 1.0 / (1.0 + luma(c3));
  vec3 avg = (c0 * w0 + c1 * w1 + c2 * w2 + c3 * w3) / max(1e-5, w0 + w1 + w2 + w3);
  gl_FragColor = vec4(softThreshold(avg), 1.0);
}`;

// 9-tap tent/box downsample
const DOWNSAMPLE_FRAG = /* glsl */ `
precision highp float;
varying vec2 vUv;
uniform sampler2D tInput;
uniform vec2 uTexel;
void main() {
  vec2 d = uTexel;
  vec3 s = texture2D(tInput, vUv).rgb * 4.0;
  s += texture2D(tInput, vUv + vec2(-d.x, -d.y)).rgb;
  s += texture2D(tInput, vUv + vec2( d.x, -d.y)).rgb;
  s += texture2D(tInput, vUv + vec2(-d.x,  d.y)).rgb;
  s += texture2D(tInput, vUv + vec2( d.x,  d.y)).rgb;
  s += texture2D(tInput, vUv + vec2( 0.0, -d.y)).rgb * 2.0;
  s += texture2D(tInput, vUv + vec2( 0.0,  d.y)).rgb * 2.0;
  s += texture2D(tInput, vUv + vec2(-d.x,  0.0)).rgb * 2.0;
  s += texture2D(tInput, vUv + vec2( d.x,  0.0)).rgb * 2.0;
  gl_FragColor = vec4(s / 16.0, 1.0);
}`;

// 9-tap tent upsample + blend with current pyramid level
const UPSAMPLE_FRAG = /* glsl */ `
precision highp float;
varying vec2 vUv;
uniform sampler2D tLow;
uniform sampler2D tHigh;
uniform vec2 uTexel;
uniform float uRadius;
void main() {
  vec2 d = uTexel * 1.25;
  vec3 b = texture2D(tLow, vUv).rgb * 4.0;
  b += texture2D(tLow, vUv + vec2(-d.x,  0.0)).rgb * 2.0;
  b += texture2D(tLow, vUv + vec2( d.x,  0.0)).rgb * 2.0;
  b += texture2D(tLow, vUv + vec2( 0.0, -d.y)).rgb * 2.0;
  b += texture2D(tLow, vUv + vec2( 0.0,  d.y)).rgb * 2.0;
  b += texture2D(tLow, vUv + vec2(-d.x, -d.y)).rgb;
  b += texture2D(tLow, vUv + vec2( d.x, -d.y)).rgb;
  b += texture2D(tLow, vUv + vec2(-d.x,  d.y)).rgb;
  b += texture2D(tLow, vUv + vec2( d.x,  d.y)).rgb;
  vec3 lowBlur = b / 16.0;
  vec3 hi = texture2D(tHigh, vUv).rgb;
  gl_FragColor = vec4(mix(hi, hi + lowBlur, uRadius), 1.0);
}`;

// Final composite: optional radial chromatic dispersion + linear HDR bloom + ACES Filmic + vignette + deterministic grain + sRGB OETF
const COMPOSITE_FRAG = /* glsl */ `
precision highp float;
varying vec2 vUv;
uniform sampler2D tBase;
uniform sampler2D tBloom;
uniform float uBloom;
uniform float uExposure;
uniform float uDispersion;
uniform float uVignette;
uniform float uGrain;
uniform float uSeed;

vec3 acesFilmic(vec3 x) {
  const float a = 2.51;
  const float b = 0.03;
  const float c = 2.43;
  const float d = 0.59;
  const float e = 0.14;
  return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}

vec3 linearToSrgb(vec3 c) {
  vec3 lo = c * 12.92;
  vec3 hi = 1.055 * pow(max(c, vec3(0.0)), vec3(1.0 / 2.4)) - 0.055;
  return mix(lo, hi, step(vec3(0.0031308), c));
}

float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}

void main() {
  vec2 centered = vUv - 0.5;
  float r2 = dot(centered, centered);
  vec3 base;
  if (uDispersion > 1e-4) {
    vec2 shift = centered * r2 * uDispersion * 0.035;
    base.r = texture2D(tBase, clamp(vUv + shift, 0.001, 0.999)).r;
    base.g = texture2D(tBase, vUv).g;
    base.b = texture2D(tBase, clamp(vUv - shift, 0.001, 0.999)).b;
  } else {
    base = texture2D(tBase, vUv).rgb;
  }
  vec3 bloom = texture2D(tBloom, vUv).rgb;
  vec3 hdr = max(vec3(0.0), (base + bloom * uBloom) * uExposure);
  vec3 mapped = acesFilmic(hdr);
  if (uVignette > 1e-4) {
    float vig = clamp(1.0 - uVignette * smoothstep(0.12, 0.68, r2), 0.0, 1.0);
    mapped *= vig;
  }
  vec3 srgb = linearToSrgb(mapped);
  if (uGrain > 1e-4) {
    float n = hash12(gl_FragCoord.xy + vec2(uSeed * 97.0, uSeed * 61.0)) - 0.5;
    srgb = clamp(srgb + n * uGrain, 0.0, 1.0);
  }
  gl_FragColor = vec4(srgb, 1.0);
}`;

function makePostPass(frag, uniforms) {
  return new THREE.ShaderMaterial({
    vertexShader: QUAD_VERT,
    fragmentShader: frag,
    uniforms,
    depthTest: false,
    depthWrite: false,
    toneMapped: false,
  });
}

// Create a complete 3D PBR + HDR Bloom + ACES Filmic stage.
// Renders into `stage.canvas` (mount in DOM or draw into 2D canvas via `ctx.drawImage(stage.canvas, 0, 0, W, H)`).
export function createStage3D(width = 1920, height = 1080, {
  canvas = null,
  fov = 38,
  near = 0.1,
  far = 220,
  bg = '#090b10',
  scale = undefined,
  exposure = 1.0,
  bloom = 0.42,
  bloomThreshold = 0.92,
  bloomKnee = 0.35,
  bloomRadius = 0.68,
  bloomClamp = 9.0,
  dispersion = 0.0,
  vignette = 0.2,
  grain = 0.02,
} = {}) {
  const dprCap = typeof window !== 'undefined' && window.devicePixelRatio ? Math.min(1, window.devicePixelRatio) : 1;
  const renderScale = Math.max(0.2, Math.min(2, scale ?? dprCap));
  const rw = Math.max(2, Math.round(width * renderScale));
  const rh = Math.max(2, Math.round(height * renderScale));

  const domCanvas = canvas || document.createElement('canvas');
  domCanvas.width = rw;
  domCanvas.height = rh;

  const renderer = new THREE.WebGLRenderer({
    canvas: domCanvas,
    antialias: false,
    alpha: false,
    powerPreference: 'high-performance',
    preserveDrawingBuffer: true,
  });
  renderer.setPixelRatio(1);
  renderer.setSize(rw, rh, false);
  // Keep internal scene rendering strictly linear HDR; tone mapping + sRGB happen once in COMPOSITE_FRAG.
  renderer.toneMapping = THREE.NoToneMapping;
  renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const gl = renderer.getContext();
  const dbg = gl.getExtension('WEBGL_debug_renderer_info');
  const glRendererName = String(gl.getParameter(dbg ? dbg.UNMASKED_RENDERER_WEBGL : gl.RENDERER) || '');
  const isSoftwareGL = /SwiftShader|llvmpipe|Software/i.test(glRendererName);
  const hasFloatBuffer = !!gl.getExtension('EXT_color_buffer_float');
  const rtType = hasFloatBuffer ? THREE.HalfFloatType : THREE.UnsignedByteType;
  const msaaSamples = !isSoftwareGL && hasFloatBuffer ? Math.min(4, renderer.capabilities.maxSamples || 0) : 0;

  const scene = new THREE.Scene();
  if (bg !== null) scene.background = new THREE.Color(bg);
  const camera = new THREE.PerspectiveCamera(fov, width / height, near, far);
  camera.position.set(0, 0.8, 6.2);

  const rtOpts = { type: rtType, format: THREE.RGBAFormat, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, depthBuffer: false };
  const hdrTarget = new THREE.WebGLRenderTarget(rw, rh, { ...rtOpts, depthBuffer: true, samples: msaaSamples });

  const levels = 5;
  const downTargets = [];
  const upTargets = [];
  let mw = rw, mh = rh;
  for (let i = 0; i < levels; i++) {
    mw = Math.max(2, mw >> 1);
    mh = Math.max(2, mh >> 1);
    downTargets.push(new THREE.WebGLRenderTarget(mw, mh, rtOpts));
    if (i < levels - 1) upTargets.push(new THREE.WebGLRenderTarget(mw, mh, rtOpts));
  }

  const postScene = new THREE.Scene();
  const postCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), null);
  quad.frustumCulled = false;
  postScene.add(quad);

  const prefilterMat = makePostPass(PREFILTER_FRAG, {
    tInput: { value: null },
    uTexel: { value: new THREE.Vector2(1 / rw, 1 / rh) },
    uThreshold: { value: bloomThreshold },
    uKnee: { value: bloomKnee },
    uClampMax: { value: bloomClamp },
  });
  const downMat = makePostPass(DOWNSAMPLE_FRAG, {
    tInput: { value: null },
    uTexel: { value: new THREE.Vector2(1, 1) },
  });
  const upMat = makePostPass(UPSAMPLE_FRAG, {
    tLow: { value: null },
    tHigh: { value: null },
    uTexel: { value: new THREE.Vector2(1, 1) },
    uRadius: { value: bloomRadius },
  });
  const compMat = makePostPass(COMPOSITE_FRAG, {
    tBase: { value: hdrTarget.texture },
    tBloom: { value: upTargets[0].texture },
    uBloom: { value: bloom },
    uExposure: { value: exposure },
    uDispersion: { value: dispersion },
    uVignette: { value: vignette },
    uGrain: { value: grain },
    uSeed: { value: 0 },
  });

  const post = { exposure, bloom, bloomThreshold, bloomKnee, bloomRadius, bloomClamp, dispersion, vignette, grain };
  let envRT = null;

  function render(t = 0, overrides = null) {
    if (overrides) Object.assign(post, overrides);
    renderer.setRenderTarget(hdrTarget);
    renderer.clear();
    renderer.render(scene, camera);

    if (post.bloom > 1e-4) {
      // 0: Karis prefilter into downTargets[0]
      quad.material = prefilterMat;
      prefilterMat.uniforms.tInput.value = hdrTarget.texture;
      prefilterMat.uniforms.uThreshold.value = post.bloomThreshold;
      prefilterMat.uniforms.uKnee.value = post.bloomKnee;
      prefilterMat.uniforms.uClampMax.value = post.bloomClamp;
      renderer.setRenderTarget(downTargets[0]);
      renderer.render(postScene, postCam);

      // 1..levels-1: progressive downsample
      quad.material = downMat;
      for (let i = 1; i < levels; i++) {
        const prev = downTargets[i - 1];
        downMat.uniforms.tInput.value = prev.texture;
        downMat.uniforms.uTexel.value.set(1 / prev.width, 1 / prev.height);
        renderer.setRenderTarget(downTargets[i]);
        renderer.render(postScene, postCam);
      }

      // Upsample & accumulate from smallest mip back to upTargets[0]
      quad.material = upMat;
      upMat.uniforms.uRadius.value = post.bloomRadius;
      let low = downTargets[levels - 1];
      for (let i = levels - 2; i >= 0; i--) {
        const high = downTargets[i];
        upMat.uniforms.tLow.value = low.texture;
        upMat.uniforms.tHigh.value = high.texture;
        upMat.uniforms.uTexel.value.set(1 / low.width, 1 / low.height);
        renderer.setRenderTarget(upTargets[i]);
        renderer.render(postScene, postCam);
        low = upTargets[i];
      }
      compMat.uniforms.tBloom.value = upTargets[0].texture;
    }

    quad.material = compMat;
    compMat.uniforms.tBase.value = hdrTarget.texture;
    compMat.uniforms.uBloom.value = post.bloom;
    compMat.uniforms.uExposure.value = post.exposure;
    compMat.uniforms.uDispersion.value = post.dispersion;
    compMat.uniforms.uVignette.value = post.vignette;
    compMat.uniforms.uGrain.value = post.grain;
    compMat.uniforms.uSeed.value = Math.round(t * 60) % 8192;
    renderer.setRenderTarget(null);
    renderer.render(postScene, postCam);
    return domCanvas;
  }

  return {
    canvas: domCanvas,
    renderer,
    scene,
    camera,
    post,
    isSoftwareGL,
    renderScale,
    render,
    _setEnvRT(rt) { if (envRT && envRT !== rt) envRT.dispose(); envRT = rt; },
  };
}

// Bake a procedural HDR studio lightformer environment ONCE at setup via `PMREMGenerator.fromScene`.
// Do NOT call inside `seek(t)`: pair with `orbitCamera` or `addStudioRig` moving lights to sweep speculars!
// `panels`: array of `{ kind?: 'rect'|'ring', pos: [x,y,z], target?: [x,y,z], size?: [w,h] | r, color?: '#ffffff', intensity?: 6 }`.
export function studioEnv(stage, panels = null, { domeTop = '#101522', domeBottom = '#05060a', domeIntensity = 0.6 } = {}) {
  const defaultPanels = [
    { kind: 'rect', pos: [0, 8, 2], size: [12, 3.2], color: '#ffffff', intensity: 6.5 },
    { kind: 'rect', pos: [-7, 2.5, 4], size: [2.2, 9], color: '#dbeafe', intensity: 5.0 },
    { kind: 'rect', pos: [7, 2.0, -3], size: [2.6, 8], color: '#fde68a', intensity: 4.5 },
    { kind: 'ring', pos: [0, -1, -8], size: 4.2, color: '#ffffff', intensity: 3.2 },
  ];
  const list = panels || defaultPanels;
  const envScene = new THREE.Scene();

  // Smooth gradient sky dome
  const domeGeo = new THREE.SphereGeometry(32, 32, 16);
  const cTop = new THREE.Color(domeTop).multiplyScalar(domeIntensity);
  const cBot = new THREE.Color(domeBottom).multiplyScalar(domeIntensity);
  const posAttr = domeGeo.attributes.position;
  const colors = new Float32Array(posAttr.count * 3);
  const tmp = new THREE.Color();
  for (let i = 0; i < posAttr.count; i++) {
    const k = THREE.MathUtils.clamp(posAttr.getY(i) / 32 * 0.5 + 0.5, 0, 1);
    tmp.copy(cBot).lerp(cTop, k);
    colors[i * 3] = tmp.r; colors[i * 3 + 1] = tmp.g; colors[i * 3 + 2] = tmp.b;
  }
  domeGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  envScene.add(new THREE.Mesh(domeGeo, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, toneMapped: false })));

  for (const p of list) {
    const col = new THREE.Color(p.color ?? '#ffffff').multiplyScalar(p.intensity ?? 5);
    const mat = new THREE.MeshBasicMaterial({ color: col, side: THREE.DoubleSide, toneMapped: false });
    let geo;
    if (p.kind === 'ring') {
      const r = typeof p.size === 'number' ? p.size : 3.5;
      geo = new THREE.RingGeometry(r * 0.78, r, 64);
    } else {
      const [w, h] = Array.isArray(p.size) ? p.size : [p.size ?? 6, (p.size ?? 6) * 0.35];
      geo = new THREE.PlaneGeometry(w, h);
    }
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(...(p.pos || [0, 6, 0]));
    mesh.lookAt(...(p.target || [0, 0, 0]));
    envScene.add(mesh);
  }

  const pmrem = new THREE.PMREMGenerator(stage.renderer);
  const rt = pmrem.fromScene(envScene, 0.035);
  pmrem.dispose();
  stage._setEnvRT(rt);
  stage.scene.environment = rt.texture;
  return rt.texture;
}

// Add real-time analytical key/rim/fill lights with a pure-function `sweep(t)` method so grazing highlights glide across bevels.
export function addStudioRig(stage, {
  keyColor = '#fff7ed', keyIntensity = 3.2,
  rimColor = '#93c5fd', rimIntensity = 4.0,
  fillColor = '#e2e8f0', fillIntensity = 1.1,
  radius = 8.5,
} = {}) {
  const group = new THREE.Group();
  const key = new THREE.DirectionalLight(keyColor, keyIntensity);
  key.position.set(radius * 0.65, radius * 0.8, radius * 0.6);
  const rim = new THREE.DirectionalLight(rimColor, rimIntensity);
  rim.position.set(-radius * 0.75, radius * 0.45, -radius * 0.8);
  const fill = new THREE.DirectionalLight(fillColor, fillIntensity);
  fill.position.set(-radius * 0.5, -radius * 0.25, radius * 0.75);
  group.add(key, rim, fill);
  stage.scene.add(group);
  return {
    group, key, rim, fill,
    sweep(angleRad = 0, lift = 0) {
      group.rotation.y = angleRad;
      group.position.y = lift;
    },
  };
}

// Style-agnostic physical material builder with open presets ('metal', 'titanium', 'glass', 'crystal', 'iridescent', 'ceramic', 'matte', 'emissive').
const PBR_PRESETS = {
  metal: { color: '#d4d8e0', metalness: 0.96, roughness: 0.14, clearcoat: 0.35, clearcoatRoughness: 0.12, envMapIntensity: 1.4 },
  titanium: { color: '#2a2e37', metalness: 0.92, roughness: 0.22, clearcoat: 0.6, clearcoatRoughness: 0.15, envMapIntensity: 1.5 },
  glass: { color: '#ffffff', metalness: 0.0, roughness: 0.05, transmission: 0.96, ior: 1.52, thickness: 0.9, clearcoat: 1.0, clearcoatRoughness: 0.04, envMapIntensity: 1.6 },
  crystal: { color: '#f8fafc', metalness: 0.0, roughness: 0.03, transmission: 0.98, ior: 1.75, thickness: 1.8, iridescence: 0.65, iridescenceIOR: 1.4, envMapIntensity: 1.8 },
  iridescent: { color: '#181824', metalness: 0.85, roughness: 0.16, iridescence: 1.0, iridescenceIOR: 1.38, iridescenceThicknessRange: [160, 620], clearcoat: 1.0, clearcoatRoughness: 0.08, envMapIntensity: 1.6 },
  ceramic: { color: '#f5f3ef', metalness: 0.04, roughness: 0.18, clearcoat: 1.0, clearcoatRoughness: 0.06, envMapIntensity: 1.2 },
  matte: { color: '#1e222b', metalness: 0.05, roughness: 0.84, envMapIntensity: 0.7 },
};

export function pbrMaterial(presetOrOpts = 'metal', overrides = {}) {
  const base = typeof presetOrOpts === 'string' ? (PBR_PRESETS[presetOrOpts] || PBR_PRESETS.metal) : presetOrOpts;
  const cfg = { ...base, ...(typeof presetOrOpts === 'string' ? overrides : {}) };
  if (presetOrOpts === 'emissive' || cfg.emissiveIntensity > 0) {
    const col = cfg.emissive ?? cfg.color ?? '#ffffff';
    return new THREE.MeshStandardMaterial({
      color: cfg.baseColor ?? '#050508',
      emissive: new THREE.Color(col),
      emissiveIntensity: cfg.emissiveIntensity ?? 3.2,
      roughness: cfg.roughness ?? 0.25,
      metalness: cfg.metalness ?? 0.1,
    });
  }
  return new THREE.MeshPhysicalMaterial(cfg);
}

// Smoothly bevelled 3D slab/chassis/monolith (never use sharp 90-degree BoxGeometry for hero objects!).
export function roundedSlab(w = 2.4, h = 3.8, d = 0.22, { radius = 0.22, bevel = 0.04, segments = 8 } = {}) {
  const r = Math.max(0.001, Math.min(radius, (w - 2 * bevel) * 0.48, (h - 2 * bevel) * 0.48));
  const iw = Math.max(0.01, w - 2 * bevel), ih = Math.max(0.01, h - 2 * bevel);
  const x0 = -iw * 0.5, y0 = -ih * 0.5;
  const shape = new THREE.Shape();
  shape.moveTo(x0 + r, y0);
  shape.lineTo(x0 + iw - r, y0);
  shape.quadraticCurveTo(x0 + iw, y0, x0 + iw, y0 + r);
  shape.lineTo(x0 + iw, y0 + ih - r);
  shape.quadraticCurveTo(x0 + iw, y0 + ih, x0 + iw - r, y0 + ih);
  shape.lineTo(x0 + r, y0 + ih);
  shape.quadraticCurveTo(x0, y0 + ih, x0, y0 + ih - r);
  shape.lineTo(x0, y0 + r);
  shape.quadraticCurveTo(x0, y0, x0 + r, y0);

  const depthBody = Math.max(0.002, d - 2 * bevel);
  const geo = new THREE.ExtrudeGeometry(shape, {
    depth: depthBody,
    bevelEnabled: bevel > 0,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: Math.max(2, segments),
    curveSegments: Math.max(6, segments * 2),
  });
  geo.center();
  geo.computeVertexNormals();
  return geo;
}

// High-count InstancedMesh controller for audio-reactive 3D fields, monolith cathedrals, or particle rings.
// Call `field.update(t, extra)` inside `seek(t)`.
export function instancedField(geometry, material, count, updateOne) {
  const mesh = new THREE.InstancedMesh(geometry, material, count);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  const dummy = new THREE.Object3D();
  const col = new THREE.Color();
  function update(t, extra = null) {
    let usedColor = false;
    for (let i = 0; i < count; i++) {
      dummy.position.set(0, 0, 0);
      dummy.rotation.set(0, 0, 0);
      dummy.scale.set(1, 1, 1);
      const hasCol = updateOne(i, dummy, col, t, extra);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
      if (hasCol) {
        mesh.setColorAt(i, col);
        usedColor = true;
      }
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (usedColor && mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }
  return { mesh, update };
}

// Pure spherical + Dutch-roll + dynamic FOV 3D camera rig.
export function orbitCamera(camera, {
  target = [0, 0, 0],
  radius = 6.0,
  azimuth = 0,
  elevation = 0.18,
  roll = 0,
  fov = null,
} = {}) {
  const [tx, ty, tz] = target;
  const el = THREE.MathUtils.clamp(elevation, -Math.PI * 0.48, Math.PI * 0.48);
  const cosE = Math.cos(el);
  camera.position.set(
    tx + radius * cosE * Math.sin(azimuth),
    ty + radius * Math.sin(el),
    tz + radius * cosE * Math.cos(azimuth),
  );
  camera.up.set(Math.sin(roll), Math.cos(roll), 0);
  camera.lookAt(tx, ty, tz);
  if (fov !== null && Math.abs(camera.fov - fov) > 1e-3) {
    camera.fov = fov;
    camera.updateProjectionMatrix();
  }
}
