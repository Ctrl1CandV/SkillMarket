# 第二档：重装绚丽视效指南（3D 物理材质、光线步进与 HDR 后期 / Blender 桥接）

> 当用户要求产品宣传片、MV 或片头达到**“视觉震撼、画面绚丽、流光溢彩、发布会大片感、Blender / C4D 级三维视效”**，或题材本身是旗舰硬件/概念揭晓、高燃电音/流行/后摇 MV、视觉奇观片头时，从轨道 B 第一档升级至本档（**第二档 · 重装绚丽视效档**）。
> 目标不是绑定某一款软件，而是兑现真正的电影级三维光影与视听冲击力，同时守住**不锁死固定画风**的创作自由。

---

## 一、双引擎自适应路线（效果达标优先，不强绑单一工具）

开工先看 `node <kit>/doctor.mjs` 的 `three`、`blender` 与 `gpu` 字段，按本机条件与镜头需求选路：

| 路线 | 适用场景 | 核心武器与优势 |
|---|---|---|
| **路线 A · 内建零安装 3D PBR + HDR 泛光 + SDF 光线步进（默认主力）** | 绝大多数旗舰产品亮相、流光金属/折射水晶特写、千枚三维阵列声画共振 MV、液态金属/虹彩流体奇观 | 直接使用随包内建的 **`kit/stage3d.js`**（Three.js r160 `MeshPhysicalMaterial` 金属/清漆/玻璃透射/薄膜虹彩 + 程序化摄影棚柔光箱 `studioEnv` + 5 级 Karis 防闪烁 HDR 泛光 + `ACESFilmic` 色调映射 + 边缘微色散）与 **`kit/shader.js` `{ sdf: true }`**。**无需安装外部大型软件**，天然兼容 `seek(t)`、`--draft` 秒级快渲、`songmap` 逐帧重音驱动与 2D 锐利排版合成 |
| **路线 B · 原生 Blender 无头渲染桥（本机 `blender.available === true` 时可选）** | 用户提供了 `.blend` / 高精度 CAD 资产，或镜头确需离线路径追踪真实玻璃焦散（Cycles）、次表面散射（SSS）、刚体碰撞与流体解算 | 在 Blender 脚本中导入 **`kit/blender_bridge.py`**（自动兼容 Blender 3.6 / 4.2+ / 5.0 的 EEVEE 与 Cycles、AgX 色彩管理、Principled BSDF 节点改名及 `songmap.json` 拍点采样），经 `blender --background --python ...` 渲出纯净无字三维底片，再交由网页或 `cut.mjs` 合成 2D 标题与歌词字幕 |

> **显卡占用避让闸门**：第二档的 `1920×1080` 多重采样 HDR 泛光、玻璃透射与 Blender 渲染高度依赖物理显卡。若 `doctor.mjs` 报告 `gpu.busy === true`：在线对话必须先告知用户当前显卡正忙，请用户选择**等显卡释放后全开硬件加速出母带**，或先设 `VC_SOFTWARE_GL=1` 跑 `--draft` 预览构图（切勿在未告知时用 CPU 软件渲染硬跑几十分钟的 1080p 重度三维场景）。

---

## 二、为什么画面会“震撼绚丽”：五个光学支点与反廉价屏保铁律

普通代码视频显得平庸，是因为停留在 8-bit 平面色块；而拙劣的三维代码又容易退化成“黑底上转圈的霓虹直角方块（2005 屏保感）”。第二档必须同时立住以下五条工艺：

1. **倒角曲率 + 三档粗糙度反差（严禁直角积木与全身塑料）**：
   - 真实高档工业品与雕塑没有绝对锋利的 90° 死角——高光全靠圆角切面（Bevel）捕捉。主角几何体一律使用 `roundedSlab` 多段平滑倒角、车削/挤压曲面、SDF `smin` 融合体或高精度 `.glb` 模型，**严禁拿裸 `BoxGeometry` / 默认方块圆柱堆砌“简笔积木雪人”**。
   - 同一画面拉开三档粗糙度对比：**高反光金属/折射水晶（`roughness 0.03–0.18`）**抓锐利灯带高光 + **缎面过渡（`0.35–0.50`）**现体积 + **哑光空间地面/无影墙（`0.78–0.92`）**稳住底盘。
2. **真线性 HDR 与克制泛光（只让高光和灯丝发光，禁整屏糊紫雾）**：
   - `stage3d.js` 在线性浮点帧缓冲中运算：常规受光面亮度在 `0.1–0.9`，只有掠射金属边高光与自发光灯丝（`emissiveIntensity: 2.5–8.0`）越过阈值 `bloomThreshold`（保持在 `0.85–1.0`，`bloom: 0.32–0.55`），经多级金字塔溢出柔美光晕后再由 `ACESFilmic` 压回电影胶片曲线，亮处通透不死白、暗部浓郁不发灰。
3. **五种开放的绚丽美学世界（按题材生长，绝不锁死暗黑赛博紫！）**：
   - **日光水晶与高调建筑影棚（High-Key Caustic Studio）**：暖白洞石或冰川浅灰无影空间 + 高折射玻璃/水晶棱镜（`crystal` / `glass` + 轻微边缘色散 `dispersion: 0.35`）+ 明快阳光斜射，适合美妆、声学硬件、现代效率旗舰与明亮空灵 MV；
   - **暗场精密工业微距掠光（ Precision Anodized Macro）**：深炭空间 + 拉丝钛合金/阳极氧化金属圆角机身（`titanium` / `metal`）+ 顶侧长条柔光箱（`studioEnv`）与 `addStudioRig` 动态扫光，55–85mm 窄视角长焦（`fov: 28–36`）贴边掠拍，适合硬核科技与旗舰硬件揭晓；
   - **液态金属与薄膜虹彩流变（Iridescent Liquid SDF）**：用 `shader.js` `{ sdf: true }` 的 `smin` 液态融合与 `thinFilm` 薄膜干涉，随视角与重低音在铜金、洋红、青翠与液态铬之间丝滑流淌，适合电子/流行高潮段落与视觉片头；
   - **千枚实例圣殿与空间穿行（Audio-Reactive Instanced Cathedral）**：用 `instancedField` 排布 300–4000 枚倒角晶柱、金属叶片或轨道光环，随 `songAt` 的 `kick`、`energy` 掀起空间相位波浪，相机从阵列深处穿梭而出；
   - **高饱和多色棱镜与先锋版面交织（Polychrome Kinetic Stage）**：大胆高饱和撞色面光照射雕塑级三维主体，同时与 `graphic.js` 巨幅动态字体、网格裁切前后穿插咬合，适合潮流单品宣传与快节奏说唱/舞曲 MV。
4. **真实电影分镜切点（禁 30 秒懒人旋转展台与全屏跟着鼓点乱跳）**：
   - 绝不把相机架在一个固定距离从头转到尾！按音乐段落或叙事弧排 `SHOTS`：**微距掠光看材质纹理（`radius: 2.6, fov: 28`）→ 硬切反打看结构开合 → 拉开低机位英雄全景（`radius: 6.5, fov: 38`）**。
   - 音画共振要精准克制：`m.kick` 与事件脉冲用来点亮灯丝、扫过光束角或推进波浪相位，**严禁让主角产品本身每一拍原地缩放乱蹦**。
5. **三维绚丽底片 + 二维刀锋级排版叠加**：
   - 三维负责空间、光影与材质奇观；产品卖点大字、规格读数与 MV 双语歌词一律叠在顶层 2D Canvas（`graphic.js`）或 DOM（`#lyric` / `#caps`）上，并在三维构图时主动留出干净的负空间，继续用 `textcheck.mjs` / `boardcheck.mjs` 守住字迹清晰度。

---

## 三、`kit/stage3d.js` 核心用法速查

```js
import { register, kf, ease, clamp } from '<kit>/kit.js';
import { headline, label } from '<kit>/graphic.js';
import {
  THREE, createStage3D, studioEnv, addStudioRig,
  pbrMaterial, roundedSlab, instancedField, orbitCamera,
} from '<kit>/stage3d.js';

const W = 1920, H = 1080;
const ctx = document.getElementById('cv').getContext('2d');

// 1. 初始化线性 HDR + 多级泛光 + ACES 色调映射三维舞台（--draft 下自动半分辨率提速）
const stage = createStage3D(W, H, {
  fov: 34, bg: '#07090e', exposure: 1.08,
  bloom: 0.45, bloomThreshold: 0.9, dispersion: 0.22, vignette: 0.24, grain: 0.02,
});

// 2. 一次性烘焙程序化摄影棚柔光箱 IBL（严禁放进 seek(t) 每帧重复烘焙！）
studioEnv(stage, [
  { kind: 'rect', pos: [0, 8, 3], size: [14, 3.0], color: '#ffffff', intensity: 7.5 },
  { kind: 'rect', pos: [-8, 2, 4], size: [2.0, 10], color: '#bae6fd', intensity: 5.5 },
  { kind: 'rect', pos: [8, 3, -4], size: [2.4, 9], color: '#fde68a', intensity: 5.0 },
  { kind: 'ring', pos: [0, 0, -9], size: 4.8, color: '#f472b6', intensity: 4.0 },
]);
const lights = addStudioRig(stage, { keyIntensity: 3.4, rimColor: '#60a5fa', rimIntensity: 4.5 });

// 3. 搭建多段圆角金属机身 + 折射水晶环 + 哑光底座（三档粗糙度对比）
const hero = new THREE.Mesh(roundedSlab(2.4, 3.6, 0.22, { radius: 0.24, bevel: 0.045, segments: 10 }), pbrMaterial('iridescent'));
const ring = new THREE.Mesh(new THREE.TorusGeometry(2.35, 0.06, 32, 128), pbrMaterial('crystal'));
const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), pbrMaterial('matte', { color: '#0b0e16', roughness: 0.86 }));
floor.rotation.x = -Math.PI / 2; floor.position.y = -2.2;
stage.scene.add(hero, ring, floor);

// 4. 可选：数百枚环绕实例随时间/重音流动
const shardGeo = roundedSlab(0.12, 0.42, 0.06, { radius: 0.03, bevel: 0.01, segments: 3 });
const shards = instancedField(shardGeo, pbrMaterial('metal', { roughness: 0.16 }), 180, (i, obj, col, t, pulse) => {
  const ang = (i / 180) * Math.PI * 2 + t * 0.18;
  const r = 3.4 + 0.35 * Math.sin(i * 0.7 + t * 1.4) + 0.18 * pulse;
  obj.position.set(Math.cos(ang) * r, Math.sin(i * 1.3 + t) * 0.9, Math.sin(ang) * r);
  obj.rotation.set(t * 0.4 + i, -ang, 0.3);
});
stage.scene.add(shards.mesh);

// 5. 纯函数 seek(t)：分镜切机位 + 扫光 + 2D 锐利文字合成
function seek(t) {
  const macro = t < 4.0;
  orbitCamera(stage.camera, macro
    ? { target: [0.6, 0.8, 0], radius: kf(t, [[0, 2.5], [4, 3.1]]), azimuth: -0.45 + t * 0.12, elevation: 0.22, fov: 28 }
    : { target: [-0.8, 0.1, 0], radius: kf(t, [[4, 6.8], [10, 5.8, ease.outSoft]]), azimuth: 0.35 - (t - 4) * 0.08, elevation: 0.14, fov: 36 });
  lights.sweep(t * 0.35);
  hero.rotation.y = Math.sin(t * 0.4) * 0.22;
  ring.rotation.x = 1.1 + t * 0.25;
  shards.update(t, Math.exp(-((t % 1.0) * 5)));

  stage.render(t);
  ctx.drawImage(stage.canvas, 0, 0, W, H);
  if (!macro) {
    label(ctx, 'FLAGSHIP ACOUSTICS / 01', 140, 380, t - 4.1, { size: 22, color: '#93c5fd' });
    headline(ctx, ['每一道切面，', '都在捕捉声音。'], 140, 430, t - 4.25, { size: 96, color: '#f8fafc', mode: 'rise' });
  }
}
register({ duration: 10, fps: 30, width: W, height: H, seek });
seek(0);
```

---

## 四、`kit/shader.js` `{ sdf: true }` 光线步进奇观速查

需要做液态铬水银融合、全屏折射水晶隧道、声波干涉场等逐像素三维奇观时，开启 `{ sdf: true }` 即可直接调用内建的 `rot2`、`smin`、`sdSphere`、`sdRoundBox`、`sdTorus`、`sdCapsule`、`opRep`、`thinFilm`、`aces` 与 `toSrgb`（自己的变量不要与这些函数重名）：

```js
import { shader } from '<kit>/shader.js';
const liquid = shader(1920, 1080, `
float map(vec3 p) {
  p.xz *= rot2(t * 0.25);
  float core = sdSphere(p, 1.05 + 0.22 * kick);
  vec3 q = p - vec3(sin(t * 1.1) * 1.35, cos(t * 0.9) * 0.85, sin(t * 0.7) * 0.9);
  float orb = sdRoundBox(q, vec3(0.42), 0.16);
  return smin(core, orb, 0.55 + 0.25 * energy);
}
vec3 calcNormal(vec3 p) {
  vec2 e = vec2(0.0015, 0.0);
  return normalize(vec3(map(p+e.xyy)-map(p-e.xyy), map(p+e.yxy)-map(p-e.yxy), map(p+e.yyx)-map(p-e.yyx)));
}
void main() {
  vec2 uv = (gl_FragCoord.xy - 0.5 * res) / res.y;
  vec3 ro = vec3(0.0, 0.0, 4.2), rd = normalize(vec3(uv, -1.35));
  float d = 0.0;
  for (int i = 0; i < 84; i++) { float h = map(ro + rd * d); if (abs(h) < 0.001 || d > 20.0) break; d += h; }
  vec3 col = mix(vec3(0.02, 0.025, 0.05), vec3(0.08, 0.06, 0.14), uv.y + 0.5);
  if (d < 20.0) {
    vec3 p = ro + rd * d, n = calcNormal(p), v = -rd;
    vec3 l = normalize(vec3(1.4, 2.2, 1.8)), h = normalize(l + v);
    float fres = pow(1.0 - max(dot(n, v), 0.0), 3.0);
    vec3 irid = thinFilm(dot(n, v), 0.35 + 0.4 * energy + 0.1 * t);
    float spec = pow(max(dot(n, h), 0.0), 96.0);
    col = mix(vec3(0.08, 0.1, 0.14), irid, 0.55 + 0.4 * fres) * (0.25 + 0.85 * max(dot(n, l), 0.0)) + spec * (1.8 + 2.0 * kick) * irid;
  }
  o = vec4(toSrgb(aces(col)), 1.0);
}`, { scale: 0.75, sdf: true, uniforms: ['kick', 'energy'] });
```

---

## 五、何时及如何桥接原生 Blender（`kit/blender_bridge.py`）

当 `doctor.mjs` 显示 `blender.available === true`，且用户明确提供了 `.blend` / `.glb` 工业模型或要求离线 Cycles 焦散/刚体模拟时：

1. 在项目构建脚本中将 `<kit>` 加入 `sys.path`，`import blender_bridge as bb`：
   - `scene = bb.reset_scene(1920, 1080, fps=30, frame_start=1, frame_end=N)`
   - `bb.pick_engine(scene, prefer="EEVEE" | "CYCLES", samples=64)`（自动适配 Blender 3.6 / 4.2+ / 5.0）
   - `bb.setup_color_and_bloom(scene, prefer_view="AgX", bloom=True)`
   - `bb.build_cyclorama(...)` + `bb.add_area_lights(...)` + `bb.make_pbr_material(...)`
   - 若为 MV，调 `bb.sample_songmap_frames("out/song/songmap.json", fps=30)` 把精确到帧的 `kick` 与 `energy` 写入灯光能量或几何阵列关键帧。
2. 无头渲染为帧序列或无损视频片段后，**不要在 Blender 里硬做中文说明排字**：把渲好的三维底片通过 `<video>` / 图片序列接入 `index.html` 叠加 2D 锐利文字与 `lyrics.mjs`，或交给 [`cut.mjs`](editing.md) + `mux_original.py` 封装成片，最后照常跑 `shotlist.py` 与解码抽帧验收。
