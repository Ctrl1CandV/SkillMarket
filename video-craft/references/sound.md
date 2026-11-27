# 声音与配乐合成

## 一、声音与画面讲同一件事（先定听觉性格，禁套单一循环）

动笔写 `score.js` 前，先根据片子的体裁、节奏与温度决定声音扮演什么角色——**不要一做产品片或科普片就条件反射铺一套“120 BPM C–G–Am–F 四和弦循环”**：

- **把规律直接变成声音**：[sky 的配乐](../examples/sky/score.js) 让红到紫六个波长对应由低到高六个音高——白光是六音齐响，三棱镜拆光时六音依次弹出，日落散射掉蓝光时高音逐个隐去只剩低音红光。
- **用配器收放帮观众分辨段落**：[promo 的配乐](../examples/promo/score.js) 开头用 520 Hz 低通把鼓闷在底下衬托群聊嘈杂，画面豁然变亮那一拍打开滤波器进全鼓，揭晓核心算法时停鼓一拍只留和声，最后印章砸在重拍上。
- **让声音先于画面引导注意力（J-cut / 留白）**：转场前 0.2 秒先听见下一场的环境声或 `riser` 吸气；人物摘下耳机或关键结论落定前一拍果断抽空伴奏，安静本身比堆满音符更有力量。

---

## 二、四种开放的声音与配乐方向（`kit/sound.js`）

`sound.js` 内置带早期反射与高频空气吸收阻尼的自然房间/大厅混响（消除了传统白噪卷积的金属嘶声），并支持可选磁带柔饱和 `warmth`。做新片时按气质自由选择或混搭：

| 声音方向 | 适合的场景 | 织体与 `kit/sound.js` 组合思路 |
|---|---|---|
| **1 · 触感拟音留白型（无和弦循环）** | 软件实操教程、极简桌面工具、硬核推演、冷峻科技短片 | **不写背景鼓组与和弦循环**；人声唱主角，只在指针落点、面板滑出、读数跳变和结论定格处点缀确定性微音效（`uiClick`、`swipe`、`tick`、`glass`），极淡 `wind` 室内空气底噪托底，干净高级 |
| **2 · 温暖电钢与律动型（82–104 BPM）** | 日常效率产品、生活方式硬件、温暖人文科普、午后叙事 | `epiano`（FM 电钢琴，可开轻微 `tremolo: 4.5`）弹七/九和弦，`subBass` 走松弛根音，轻柔 `hat` 与反拍小音量 `snare`，混音台开 `{ warmth: 0.14, reverb: 0.2 }`，松弛不吵耳 |
| **3 · 现代合成器侧链脉冲型（108–128 BPM）** | 快节奏发布会短片、多步状态流转、动态版面片头 | `kick` + `clap` 立住骨架，`subBass` 或切分 `bass` 铺底，`warmPad` 经 `sidechain(m.music, beatTimes, { depth: -7 })` 随底鼓呼吸让位，`pluck` 或 `glass` 在高频点亮关键视觉节点 |
| **4 · 木质室内与电影氛围型（慢拍或自由拍）** | 电影感叙事短片、自然跨尺度科普、情绪留白片尾 | `piano` 稀疏单音与双音，`tone` 或 `warmPad` 缓慢推开和声色彩，`wind` 随室内外切镜改变滤波中心频率，混响设 `{ reverb: 0.26, irSec: 3.2, irDamp: 0.8 }` 营造深远空间 |

### 写和声不发闷浑浊的三条铁律

1. **低音区（`< C3` / 130 Hz 以下）只放单音根音**：用单声道 `subBass` 或 `bass`，绝不在低音区叠三度、五度双音，同时笔记本/手机外放靠 `subBass` 自带的温和低通泛音就能听清根音走向。
2. **中音和弦（`A3–C5`）拉开声部间距**：`warmPad`、`epiano`、`piano` 排和弦时优先用开离排列或加九音/挂留音（如 `['C4', 'E4', 'G4', 'D5']` 或 `['D4', 'F4', 'A4', 'C5']`），避免四五个锯齿波挤在同一八度里糊成一团。
3. **给配音让出中频（1–3 kHz）**：有人声口播时，除了用 `duck(m.music, 说话区间, { depth: -9 })` 压低伴奏总电平，尽量减少与人声同频段的密集 `pluck` 连奏；`sidechain(m.music, beats)` 走独立内部节点 `bus.sc`，可与 `duck(m.music, ...)` 安全叠加而互不覆盖。

---

## 三、一张事件表驱动声画同步

场景页导出 `meta.events`（或讲题/轻演示的 `meta.sfx`），配乐页读取同一份时间线发声，改画面时机无需手改两处秒数：

```js
// scene.js
register({ duration: 24, fps: 30, width: 1920, height: 1080, seek, meta: {
  events: [{ t: 1.25, type: 'click' }, { t: 3.8, type: 'drawer', pan0: -0.2, pan1: 0.2 }, { t: 8.0, type: 'done' }],
} });

// score.js
import { install, epiano, subBass, sidechain, uiClick, swipe, glass, NOTE } from '<kit>/sound.js';
function score(m, events, duration) {
  for (const e of events) {
    if (e.type === 'click') uiClick(m, m.sfx, e.t, { freq: 1900, gain: 0.07 });
    else if (e.type === 'drawer') swipe(m, m.sfx, e.t, { dur: 0.22, pan0: e.pan0, pan1: e.pan1 });
    else if (e.type === 'done') glass(m, m.sfx, e.t, NOTE('E6'), { gain: 0.055, dur: 1.5 });
  }
}
install(score, { reverb: 0.18, irSec: 1.8, irDamp: 0.75, warmth: 0.12 });
```

若无需编写整页配乐（如实操教程、讲题或旁白主导的产品短片），直接运行 `node <kit>/audio.mjs index.html - out/audio.webm --vo vo/ [--srt out/captions.srt]`，即可将 `meta.cues` 干声与 `meta.sfx`（支持 `uiClick`/`click`、`swipe`、`glass`、`epiano`、`tick`、`pop`、`pluck`、`chime`、`thud`、`whoosh`、`glide`）合成至 `-16 LUFS`。

---

## 四、音效与乐器速查

| 画面动作或音乐职责 | 推荐函数（`kit/sound.js`） | 听感特点 |
|---|---|---|
| 真实鼠标/按键/触控点击 | `uiClick(m, out, t, { freq, gain, crisp, pan })` | 确定性物理微瞬态，干脆不卡通 |
| 抽屉展开、卡片滑入、轻切镜 | `swipe(m, out, t, { dur, f0, f1, gain, pan0, pan1 })` | 柔和空气摩擦声，比 `whoosh` 更轻巧现代 |
| 状态完成、微光点亮、清透提示 | `glass(m, out, t, freq, { dur, gain, pan })` / `chime` | 非谐波玻璃/钟琴泛音，通透不刺耳 |
| 温暖键盘和弦与动机 | `epiano`（FM 电钢，支持 `tremolo`）/ `piano`（柔音钢琴） | 适合人文、现代产品与叙事铺底 |
| 小扬声器也能听清的低音 | `subBass`（单声道带温和泛音）/ `bass` | 下潜稳且笔记本外放不丢根音 |
| 气泡弹出、轻量节点浮现 | `pop` / `tick` / `pluck` | 适合多节点依次上行点亮 |
| 大跨度穿屏、升空蓄力、盖章落地 | `whoosh` / `riser` / `impact` / `thud` | 留给全片关键转折，克制使用 |
| 随节拍呼吸压低铺底 | `sidechain(bus, beatTimes, { depth, attack, release })` | 独立作用于 `bus.sc`，不与 `duck()` 冲突 |
| 人声期间压低音乐 | `duck(bus, [[t0, t1], ...], { depth: -9 })` | 平滑让出人声清晰度 |

---

## 五、配音、混音检查与响度规范

1. **配音工作流**：选音色、口语流畅度门禁与显卡繁忙回退做法详见 **[人声生成与声音卡](voice.md)**。镜头时间按 `vo.mjs` / `words.js` 实测语音长度排，绝不拉伸人声凑画面。
2. **可视化与试听核查**：
   - 跑 `node <kit>/mixcheck.mjs index.html score.html out/mix.png [--vo vo/]` 看音乐、音效、人声与总混音瞬时响度曲线：关键音效是否在事件线上清楚探出音乐之上？台词段音乐是否已让位？有无长段死平或大面积削顶限幅？
   - 外部音轨或最终 MP4 可跑 `node <kit>/audiocheck.mjs final.mp4 index.html out/check.png` 核对频谱与包络。未亲耳试听时，在交付说明里如实写明核对了哪些响度与频谱指标。
3. **响度与总线纪律**：
   - `audio.mjs` 默认归一到 **−16 LUFS**，采样峰值限幅在 **−1.5 dBFS**（原声 MV 用 `mux_original.py` 保留母带原样，不二次归一）。
   - 分轨静音由工具内部 `bus.mute` 完成；自动化音量请操作 `m.music.gain`、`duck(m.music, ...)` 或自建子总线，不要手动改动 `bus.mute`。
