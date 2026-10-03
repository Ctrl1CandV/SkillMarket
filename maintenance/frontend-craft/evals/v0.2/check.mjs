// frontend-craft v0.2 应用小样检查：静态 + mock-DOM 模拟 + 对比度计算。
// 不渲染浏览器、不截图、不证明视觉或无障碍达标；见输出中的 notTested。
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(dir, '../../../..'); // 仓库根目录，两份小样所在
const PAGES = ['evening-radio.html', 'field-notes.html'];
let checks = 0;
function ok(test, msg) {
  if (!test) throw new Error('检查失败: ' + (msg || '(无描述)'));
  checks++;
}

// ---------- 最小 mock DOM（仅覆盖两页脚本用到的 API） ----------
class Element {
  constructor(tag) {
    this.tagName = String(tag || 'div').toLowerCase();
    this.children = [];
    this.attrs = {};
    this.handlers = {};
    this.textContent = '';
    this.hidden = false;
    this.disabled = false;
    this.open = false;
    this.value = '';
    this._cls = new Set();
  }
  get className() { return [...this._cls].join(' '); }
  set className(v) { this._cls = new Set(String(v).split(/\s+/).filter(Boolean)); }
  get classList() {
    const s = this._cls;
    return {
      add: (...a) => a.forEach(x => s.add(x)),
      remove: (...a) => a.forEach(x => s.delete(x)),
      toggle: (f, force) => {
        const has = s.has(f);
        const want = force === undefined ? !has : !!force;
        if (want) s.add(f); else s.delete(f);
        return want;
      },
      contains: c => s.has(c)
    };
  }
  append(...items) {
    for (const it of items) {
      this.children.push(it);
      this.textContent += typeof it === 'string' ? it : it.textContent;
    }
  }
  replaceChildren(...items) {
    this.children = items;
    this.textContent = items.map(i => (typeof i === 'string' ? i : i.textContent)).join('');
  }
  setAttribute(k, v) {
    this.attrs[k] = String(v);
    if (k === 'class') this._cls = new Set(String(v).split(/\s+/).filter(Boolean));
  }
  getAttribute(k) { return this.attrs[k] ?? null; }
  removeAttribute(k) { delete this.attrs[k]; }
  addEventListener(k, f) { this.handlers[k] = f; }
  focus() { this.focused = true; }
  async fire(k) {
    return this.handlers[k]?.({ currentTarget: this, target: this, preventDefault() {}, stopPropagation() {} });
  }
}

function load(name) {
  const html = fs.readFileSync(path.join(ROOT, name), 'utf8');

  // 基本文档头
  ok(html.startsWith('<!doctype html>'), name + ': doctype 在首行');
  ok(html.includes('<html lang="zh-CN">'), name + ': lang');
  ok(html.includes('charset="utf-8"'), name + ': charset');
  ok(html.includes('name="viewport"'), name + ': viewport');
  ok(/<title>[^<]{8,}<\/title>/.test(html), name + ': title 非空');
  ok(!/(?:\s(?:src|href))\s*=\s*["'](?:https?:)?\/\//i.test(html), name + ': 无外链 src/href');
  ok(!html.includes('url(') && !/@import/.test(html), name + ': 无外部字体/资源引用');
  ok(!/<audio/i.test(html), name + ': 无音频元素（无声演示）');
  ok((html.match(/<h1[\s>]/g) || []).length === 1, name + ': 恰好一个 h1');
  ok(/class="skip" href="#/.test(html), name + ': 跳转链接');
  ok(/<main[\s>]/.test(html) && /<footer[\s>]/.test(html), name + ': main/footer 地标');
  ok((html.match(/虚构/g) || []).length >= 2, name + ': 虚构声明（页头+页脚）');
  ok(html.includes(':focus-visible'), name + ': 键盘焦点样式');
  ok(html.includes('prefers-reduced-motion:reduce') && html.includes('prefers-reduced-motion:no-preference'), name + ': 减少动效设置');
  ok(/@media \(max-width:\s*\d+px\)/.test(html), name + ': 窄屏断点存在');
  ok(html.includes('overflow-wrap'), name + ': 长内容换行保护');
  ok(html.includes('tabular-nums'), name + ': 数字等宽');
  ok(html.includes('role="status"'), name + ': 状态播报区');

  // 互链
  const other = name === 'evening-radio.html' ? 'field-notes.html' : 'evening-radio.html';
  ok(html.includes('href="' + other + '"'), name + ': 页脚互链 ' + other);
  ok(fs.existsSync(path.join(ROOT, other)), name + ': 互链目标文件存在');

  // id 唯一 + 锚点可达
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
  ok(new Set(ids).size === ids.length, name + ': id 无重复');
  for (const m of html.matchAll(/href="#([^"]+)"/g)) ok(ids.includes(m[1]), name + ': 锚点 #' + m[1] + ' 可达');

  // 标签配平（剥离 script/style 后做栈检查）
  const stripped = html
    .replace(/<script>[\s\S]*?<\/script>/g, '<script></script>')
    .replace(/<style>[\s\S]*?<\/style>/g, '<style></style>');
  const VOID = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);
  const tagRe = /<\/([a-zA-Z][a-zA-Z0-9-]*)\s*>|<([a-zA-Z][a-zA-Z0-9-]*)((?:"[^"]*"|'[^']*'|[^"'>])*)>/g;
  const stack = [];
  let m;
  while ((m = tagRe.exec(stripped))) {
    if (m[1]) {
      const top = stack.pop();
      ok(top === m[1].toLowerCase(), name + ': </' + m[1] + '> 与开启标签 <' + top + '> 配对');
    } else {
      const tag = m[2].toLowerCase();
      const selfClose = /\/\s*$/.test(m[3]);
      if (!selfClose && !VOID.has(tag)) stack.push(tag);
    }
  }
  ok(stack.length === 0, name + ': 无未闭合标签 ' + stack.join(','));

  // 装饰 SVG 隐藏 / 语义图版
  const hiddenSvg = (html.match(/<svg[^>]*aria-hidden="true"/g) || []).length;
  const roleImg = (html.match(/<svg[^>]*role="img"/g) || []).length;
  if (name === 'evening-radio.html') {
    ok(hiddenSvg >= 2, name + ': 波形与唱片 SVG 标记为装饰');
    ok((html.match(/aria-pressed=/g) || []).length >= 6, name + ': 筛选与播放为按压态控件');
    ok(/id="play"[^>]*disabled/.test(html), name + ': 播放按钮初始禁用（未选定）');
  } else {
    ok(roleImg === 1 && html.includes('id="plate-title"'), name + ': 植物图版为带标题的语义图像');
    ok((html.match(/<details[\s>]/g) || []).length === 9, name + ': 台账 8 条 + 目录 1 个 details');
  }

  // 构造 mock 元素并运行页面脚本
  const elements = Object.fromEntries(ids.map(id => [id, new Element('div')]));
  const document = {
    getElementById: id => {
      if (!(id in elements)) throw new Error(name + ': getElementById 未命中 ' + id);
      return elements[id];
    },
    createElement: tag => new Element(tag)
  };
  const context = vm.createContext({ document });
  for (const m of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) {
    new vm.Script(m[1]); // 语法检查
    vm.runInContext(m[1], context);
  }
  return { html, elements, hash: crypto.createHash('sha256').update(html).digest('hex') };
}

function walk(e, out = []) {
  for (const c of e.children) { out.push(c); walk(c, out); }
  return out;
}

// ---------- 对比度计算（WCAG 相对亮度） ----------
function lum(hex) {
  const c = hex.replace('#', '');
  const chan = [0, 2, 4].map(i => parseInt(c.slice(i, i + 2), 16) / 255)
    .map(v => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
  return 0.2126 * chan[0] + 0.7152 * chan[1] + 0.0722 * chan[2];
}
function ratio(a, b) {
  const [l1, l2] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}
// [用途, 前景, 背景, 最低比率]
const CONTRAST = {
  'evening-radio.html': [
    ['正文 on 墨蓝底', '#E8EEFB', '#0B1630', 4.5],
    ['次级文本 on 墨蓝底', '#AEBBE0', '#0B1630', 4.5],
    ['元数据 on 墨蓝底', '#8B9CC9', '#0B1630', 4.5],
    ['酸橙强调文本 on 墨蓝底', '#CDF25A', '#0B1630', 4.5],
    ['珊瑚播出标记 on 墨蓝底', '#FF8A70', '#0B1630', 4.5],
    ['播放台正文 on 面板', '#E8EEFB', '#15264A', 4.5],
    ['播放台元数据 on 面板', '#8B9CC9', '#15264A', 4.5],
    ['深底文本 on 酸橙（选中/播放态）', '#0B1630', '#CDF25A', 4.5]
  ],
  'field-notes.html': [
    ['正文 on 纸白', '#2B2A24', '#F6F1E6', 4.5],
    ['次级文本 on 纸白', '#6B6555', '#F6F1E6', 4.5],
    ['森林绿标题/链接 on 纸白', '#2E5339', '#F6F1E6', 4.5],
    ['赭色文本 on 纸白', '#9A5A20', '#F6F1E6', 4.5],
    ['正文 on 台账底', '#2B2A24', '#EFE7D3', 4.5],
    ['森林绿 on 台账底', '#2E5339', '#EFE7D3', 4.5],
    ['页脚文本 on 森林深底', '#E9E4D4', '#1F3A28', 4.5],
    ['页脚链接 on 森林深底', '#D9A441', '#1F3A28', 4.5]
  ]
};
let contrastPairs = 0;
for (const [page, pairs] of Object.entries(CONTRAST)) {
  const html = fs.readFileSync(path.join(ROOT, page), 'utf8');
  for (const [use, fg, bg, min] of pairs) {
    const r = ratio(fg, bg);
    ok(r >= min, page + ' 对比度 ' + use + ' ' + fg + '/' + bg + ' = ' + r.toFixed(2) + ' < ' + min);
    ok(html.includes(fg) && html.includes(bg), page + ' 对比度对色值确实声明在页面里: ' + use);
    contrastPairs++;
  }
}

// ---------- 运行页面并做交互模拟 ----------
async function runRadio() {
  const R = load('evening-radio.html');
  const E = R.elements;
  const rows = () => walk(E.list).filter(e => e.attrs.class === 'track');
  const picks = () => walk(E.list).filter(e => e.attrs.class === 't-pick');
  const blocks = () => walk(E.list).filter(e => e.tagName === 'section');

  ok(rows().length === 9, '电台: 初始渲染 9 段曲目');
  ok(blocks().length === 3, '电台: 三个时段块');
  ok(E.play.disabled === true, '电台: 未选定时播放禁用');
  ok(picks().every(b => b.attrs['aria-label']?.startsWith('选定《')), '电台: 选定按钮有曲名标签');

  await E['chip-rain'].fire('click');
  ok(rows().length === 3, '电台: 筛选雨夜剩 3 段');
  ok(E.count.textContent.includes('雨夜') && E.count.textContent.includes('3 / 9'), '电台: 计数播报筛选结果');
  ok(E['chip-rain'].attrs['aria-pressed'] === 'true' && E['chip-all'].attrs['aria-pressed'] === 'false', '电台: 按压态互斥');

  await E['chip-all'].fire('click');
  ok(rows().length === 9, '电台: 回到全部 9 段');

  await picks()[3].fire('click'); // 深流第一段《屋檐滴水练习》
  ok(E.play.disabled === false, '电台: 选定后播放可用');
  ok(E['now-title'].textContent.includes('屋檐滴水练习'), '电台: 播放台显示当前选定');
  ok(rows().some(r => r.attrs['aria-current'] === 'true'), '电台: 当前行有 aria-current');
  ok(E.status.textContent.includes('没有音频'), '电台: 选定即声明无声演示');

  await E.play.fire('click');
  ok(E.play.textContent === '暂停' && E.play.attrs['aria-pressed'] === 'true', '电台: 播放态切换');
  ok(E.status.textContent.includes('无声演示进行中'), '电台: 播放态明示无声');

  await E.play.fire('click');
  ok(E.play.textContent === '播放' && E.status.textContent.includes('演示已暂停'), '电台: 暂停态与保留提示');

  await E['chip-voice'].fire('click');
  ok(rows().length === 1, '电台: 远处人声仅 1 段');
  ok(E['now-title'].textContent.includes('屋檐滴水练习') && E.play.disabled === false, '电台: 被筛掉的选定仍保留、播放可用');

  await E['chip-all'].fire('click');
  const currentRows = rows().filter(r => r.attrs['aria-current'] === 'true');
  ok(currentRows.length === 1 && currentRows[0].textContent.includes('屋檐滴水练习'), '电台: 筛选往返后选定高亮保留');

  await picks()[0].fire('click'); // 切换选定到晚潮第一段
  const afterSwitch = rows().filter(r => r.attrs['aria-current'] === 'true');
  ok(afterSwitch.length === 1 && afterSwitch[0].textContent.includes('环线夜车'), '电台: 切换选定后旧行清理、新行唯一高亮');
  ok(E['now-title'].textContent.includes('环线夜车'), '电台: 播放台随切换更新');
  return R;
}

async function runField() {
  const F = load('field-notes.html');
  const FEl = F.elements;
  const IDS = ['rec-1', 'rec-2', 'rec-3', 'rec-4', 'rec-5', 'rec-6', 'rec-7', 'rec-8'];
  ok(IDS.every(id => FEl[id].open === false), '植物志: 初始台账全部收起');
  await FEl['expand-all'].fire('click');
  ok(IDS.every(id => FEl[id].open === true), '植物志: 全部展开生效');
  ok(FEl['log-status'].textContent.includes('8'), '植物志: 展开状态有播报');
  await FEl['collapse-all'].fire('click');
  ok(IDS.every(id => FEl[id].open === false), '植物志: 全部收起生效');
  ok(FEl['log-status'].textContent.includes('收起'), '植物志: 收起状态有播报');
  return F;
}

const radio = await runRadio();
const field = await runField();

console.log(JSON.stringify({
  kind: 'static-and-mock-DOM-only',
  checks,
  contrastPairs,
  status: 'passed',
  hashes: {
    'evening-radio.html': radio.hash,
    'field-notes.html': field.hash
  },
  notTested: [
    'browser rendering', 'screenshots', 'visual quality',
    'responsive geometry (390/1280 real layout)',
    'real keyboard traversal', 'screen reader', 'zoom 200%',
    'performance', 'SVG visual appearance'
  ]
}, null, 2));
