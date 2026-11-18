// The teaching logic and voice timing come from lesson.json via build_voice.py.
const lesson = window.LESSON;
const canvas = document.querySelector('canvas');
const ctx = canvas.getContext('2d');
const caption = document.querySelector('.cap');
const W = 1280, H = 720;
const SERIF = '"Noto Serif CJK SC", "Songti SC", "SimSun", serif';
const SANS = '"Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
const LATIN = 'Georgia, "Times New Roman", serif';
const IVORY = '#efe8cf', MINT = '#accabb', AMBER = '#f7ba77';
const TAU = 2 * Math.PI;
const clamp = n => Math.max(0, Math.min(1, n));
const ease = n => { const u = clamp(n); return u * u * (3 - 2 * u); };
const mix = (a, b, t) => a + (b - a) * t;

function text(str, x, y, size, color, options = {}) {
  ctx.fillStyle = color;
  ctx.textAlign = options.align || 'left';
  ctx.textBaseline = 'middle';
  ctx.font = (options.weight || 'normal') + ' ' + size + 'px ' + (options.font || SANS);
  ctx.fillText(str, x, y);
}

function stroke(points, color, width = 1) {
  ctx.beginPath();
  points.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.stroke();
}

function ring(x, y, r, color, width = 1) {
  ctx.beginPath(); ctx.arc(x, y, r, 0, TAU);
  ctx.lineWidth = width; ctx.strokeStyle = color; ctx.stroke();
}

function disk(x, y, r, color) {
  ctx.beginPath(); ctx.arc(x, y, r, 0, TAU);
  ctx.fillStyle = color; ctx.fill();
}

function coinStamp(n) {
  const plate = document.createElement('canvas'); plate.width = plate.height = 192;
  const c = plate.getContext('2d');
  c.translate(96, 94);
  const circle = (r, fill) => { c.fillStyle = fill; c.beginPath(); c.arc(0, 0, r, 0, TAU); c.fill(); };
  c.save(); c.translate(0, 4); circle(87, '#533822'); c.restore();
  const grad = c.createLinearGradient(-70, -80, 70, 80);
  grad.addColorStop(0, '#ffdc9e'); grad.addColorStop(.24, '#d99a61');
  grad.addColorStop(.59, '#e6ac6d'); grad.addColorStop(1, '#b97948');
  circle(87, grad);
  for (const [r, col, width] of [[85, '#ffe0a4', 2.4], [79, '#86512b', 1.9], [74, '#eccc93', 1.2], [69, '#94623b', .7]]) {
    c.beginPath(); c.arc(0, 0, r, 0, TAU); c.strokeStyle = col; c.lineWidth = width; c.stroke();
  }
  // Radial notches and tiny regular dots read as struck metal even at small sizes.
  for (let i = 0; i < 96; i++) {
    const a = i * TAU / 96;
    c.beginPath(); c.moveTo(Math.cos(a) * 80.3, Math.sin(a) * 80.3);
    c.lineTo(Math.cos(a) * 83.4, Math.sin(a) * 83.4); c.strokeStyle = '#976a46'; c.lineWidth = .7; c.stroke();
  }
  c.fillStyle = '#985e38';
  for (let i = 0; i < 290; i++) {
    const a = i * 2.399963, r = Math.sqrt(i / 290) * 72;
    c.globalAlpha = .09 + (i % 3) * .05;
    c.fillRect(Math.cos(a) * r, Math.sin(a) * r, 1.5, .85);
  }
  c.globalAlpha = 1; c.textAlign = 'center'; c.textBaseline = 'middle';
  c.font = 'bold 101px ' + LATIN;
  c.fillStyle = '#f9d297'; c.fillText(n, 1, -3); c.fillStyle = '#5a3423'; c.fillText(n, 0, -5);
  for (const sign of [-1, 1]) {
    c.beginPath();
    c.moveTo(sign * 4, 59); c.quadraticCurveTo(sign * 38, 56, sign * 53, 32);
    c.strokeStyle = '#80532f'; c.lineWidth = 1.7; c.stroke();
    for (let j = 0; j < 7; j++) {
      c.save(); c.translate(sign * (10 + 6 * j), 57 - j * j * .44);
      c.rotate(sign * (-.6 - j * .095)); c.fillStyle = '#8a5a34';
      c.beginPath(); c.ellipse(0, 0, 5, 1.8, 0, 0, TAU); c.fill(); c.restore();
    }
  }
  return plate;
}
const stamps = Array.from({length: 9}, (_, i) => coinStamp(i + 1));

function coin(n, x, y, radius, selected = false) {
  if (selected) {
    ring(x, y, radius + 8, '#f0c98e', 2);
    ring(x, y, radius + 13, 'rgba(255,203,141,.32)');
  }
  ctx.drawImage(stamps[n - 1], x - radius * 1.1, y - radius * 1.08, radius * 2.2, radius * 2.2);
}

// One cached lithographic ground; grain remains still during viewing and seeking.
const ground = document.createElement('canvas');
ground.width = W; ground.height = H;
{
  const c = ground.getContext('2d');
  const paint = c.createRadialGradient(510, 315, 30, 570, 345, 830);
  paint.addColorStop(0, '#20483d'); paint.addColorStop(.66, '#163a34'); paint.addColorStop(1, '#0f2827');
  c.fillStyle = paint; c.fillRect(0, 0, W, H);
  let seed = 117;
  const next = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 35000; i++) {
    c.fillStyle = i % 3 ? 'rgba(255,242,193,.034)' : 'rgba(0,16,13,.15)';
    c.fillRect(next() * W, next() * H, .6 + next() * 1.9, .7);
  }
  c.strokeStyle = 'rgba(180,203,174,.065)'; c.lineWidth = 1;
  for (let x = 73; x < W - 50; x += 28) {
    c.beginPath(); c.moveTo(x, 536); c.lineTo(x - 17, 552); c.stroke();
  }
}

function header(title, label) {
  text('数学观察室', 65, 44, 19, AMBER);
  stroke([[183, 44], [225, 44]], '#b29f73', 1.4);
  text('天平上的推理', 242, 44, 18, MINT);
  text(title, 60, 113, 55, IVORY, {font: SERIF, weight: 'bold'});
  text(label, 1212, 110, 24, AMBER, {align: 'right'});
  stroke([[63, 162], [1217, 162]], '#80978a');
}

function footer(focus) {
  stroke([[63, 598], [1217, 598]], '#647f71');
  if (focus) text(focus, 640, 563, 25, MINT, {align: 'center'});
}

function overhead(id, elapsed) {
  header('九枚硬币，只称两次', '条件 · 只有一枚偏轻');
  const sorting = id === 'split' ? ease(elapsed / 1.1) : 0;
  const r = 47;
  for (let g = 0; g < 3; g++) {
    const cx = 270 + g * 370;
    if (sorting > 0) {
      ctx.save(); ctx.globalAlpha = sorting;
      ring(cx, 357, 116, '#92ad92', 1.4);
      text(['第一堆','第二堆','第三堆'][g], cx, 510, 25, IVORY, {align:'center'}); ctx.restore();
    }
    for (let j = 0; j < 3; j++) {
      const n = 3 * g + j + 1;
      const fx = cx + [-49, 47, 0][j], fy = [331, 325, 407][j];
      const x = mix(212 + (n - 1) * 106 + (j % 2) * 8, fx, sorting);
      const y = mix(352 + Math.sin(n * 1.8) * 42, fy, sorting);
      coin(n, x, y, mix(r + 2, r, sorting));
    }
  }
  footer(id === 'split' ? '三枚　｜　三枚　｜　三枚' : '已知　八枚等重，一枚较轻');
}

function pan(x, jointY, coins, elapsed, load, highlight, opacity) {
  const shelf = jointY + 137;
  stroke([[x, jointY], [x - 113, shelf], [x + 113, shelf], [x, jointY]], '#bcc5a8', 1.9);
  stroke([[x, jointY], [x, shelf - 31]], 'rgba(183,198,169,.42)', 1);
  ctx.fillStyle = '#9c7654'; ctx.beginPath(); ctx.moveTo(x - 120, shelf);
  ctx.quadraticCurveTo(x, shelf + 73, x + 120, shelf); ctx.closePath(); ctx.fill();
  ctx.beginPath(); ctx.moveTo(x - 120, shelf); ctx.quadraticCurveTo(x, shelf + 32, x + 120, shelf);
  ctx.lineWidth = 2.7; ctx.strokeStyle = '#e8c08a'; ctx.stroke();
  for (let j = -8; j <= 8; j++) {
    const u = j / 9, sy = shelf + (1-u*u)*19;
    stroke([[x+u*103,sy],[x+u*102+3,sy+7*(1-u*u)]], '#bb9770');
  }
  const r = coins.length === 1 ? 45 : 31;
  coins.forEach((n, i) => {
    const u = load ? ease((elapsed - i * .12) / .75) : 1;
    if (!u) return;
    ctx.save(); ctx.globalAlpha = u * opacity;
    coin(n, x + (i - (coins.length - 1) / 2) * 65, shelf - r * .9 - (1-u) * 65, r, n === highlight);
    ctx.restore();
  });
}

function balance(left, right, off, tilt, elapsed, load, focus, highlight = 0, tray = '盘外') {
  const px = 466, py = 295;
  const x1 = 215, x2 = 717, y1 = py - tilt, y2 = py + tilt;
  stroke([[83, py], [851, py]], 'rgba(200,217,188,.24)', 1);
  for (let x = 87; x < 850; x += 18) stroke([[x, py - 2], [x,py + 2]], 'rgba(200,217,188,.24)');
  // Pillar, embossed base and the pointer behind the moving beam.
  ctx.beginPath(); ctx.moveTo(px-9,py-12); ctx.lineTo(px-18,510); ctx.lineTo(px+18,510); ctx.lineTo(px+9,py-12);
  ctx.closePath(); ctx.fillStyle = '#779684'; ctx.fill();
  for (let j = -7; j <= 7; j += 4) stroke([[px+j,py+14],[px+j*1.6,502]], '#506f60', 1);
  ctx.fillStyle='#769082'; ctx.fillRect(px-42,506,84,6); ctx.fillRect(px-63,512,126,9);
  stroke([[px - 76,525],[px + 76,525]],'#dacf9d', 2);
  ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(px,py-12); ctx.lineTo(x2,y2);
  ctx.lineTo(px,py+9); ctx.closePath(); ctx.fillStyle='#aa8f63'; ctx.fill();
  stroke([[x1,y1],[px,py-12],[x2,y2]], '#edcd8f', 3);
  disk(px, py, 12, '#bd9b64'); ring(px,py,8,'#5f694f',2);
  disk(x1,y1,4,'#e5d1a0'); disk(x2,y2,4,'#e5d1a0');
  const opacity = side => focus === null || focus === side ? 1 : mix(1,.38,ease(elapsed/.7));
  pan(x1,y1,left,elapsed,load,highlight,opacity(0)); pan(x2,y2,right,elapsed,load,highlight,opacity(1));
  stroke([[884,200],[884,524]], '#789384');
  text(tray, 1048, tray === '盘外' ? 251 : 229, 29, IVORY, {align:'center',font:SERIF,weight:'bold'});
  const r = off.length === 1 ? 45 : 32;
  ctx.save(); ctx.globalAlpha=opacity(2);
  off.forEach((n,i) => {
    if (off.length === 9) coin(n,1048+(i%3-1)*64,294+Math.floor(i/3)*63,29);
    else coin(n,1048+(i-(off.length-1)/2)*69,382,r,n===highlight);
  });
  ctx.restore();
  const shelfY = off.length === 9 ? 465 : 438;
  stroke([[930,shelfY],[1165,shelfY]], '#8a9b82', 1.5);
  if (focus !== null) {
    const fx = [x1, x2, 1048][focus], fy = focus === 0 ? y1 + 204 : focus === 1 ? y2 + 204 : 480;
    text(highlight ? '轻币' : '继续查这边', fx, fy, 23, AMBER, {align:'center'});
  }
}

function outcomeTilt(branch) {
  return [34, -34, 0][branch];
}

function weighing(id, elapsed, holdProgress) {
  const practice = ['reset','group','ask','think','solve'].includes(id);
  const narrowed = ['second','found','ask','think','solve'].includes(id);
  const model = practice ? lesson.practice : lesson.example;
  const outcome = narrowed ? model.position : model.group;
  const isKnown = ['weigh','reason','found','reset','group','ask','think','solve'].includes(id);
  const show = id === 'weigh' || id === 'found' || id === 'reset' || id === 'ask' ? ease(elapsed / .8) : 1;
  const tilt = isKnown ? outcomeTilt(outcome) * show : 0;
  const answer = (id === 'found' || id === 'solve') && elapsed > .85;
  const groupFocus = (id === 'reason' || id === 'group') ? outcome : null;
  const title = practice ? (id === 'solve' ? '验证你的选择' : '换你来称') : (narrowed ? '再称两枚，留下第三枚' : '先称两堆，留下一堆');
  const label = (practice ? '练习' : '示范') + (narrowed ? '　／　第二称' : '　／　第一称');
  header(title, label);
  balance(narrowed ? [model.coins[0]] : [1,2,3],
          narrowed ? [model.coins[1]] : [4,5,6],
          narrowed ? [model.coins[2]] : [7,8,9],
          tilt, elapsed, id === 'load' || id === 'second', answer ? outcome : groupFocus, answer ? model.answer : 0);
  const outcomes = ['左盘升高', '右盘升高', '两盘齐平'];
  if (id === 'think') {
    footer('选一枚轻币');
    ctx.fillStyle='#547868'; ctx.fillRect(526,579,228,3);
    ctx.fillStyle=AMBER; ctx.fillRect(526,579,228 * clamp(holdProgress),3);
  } else if (answer) {
    footer('轻币　' + model.answer + ' 号');
  } else if (id === 'ask') {
    footer(outcomes[outcome] + '　·　哪一枚轻？');
  } else if (isKnown && show >= 1) {
    footer(outcomes[outcome]);
  } else footer(narrowed ? '一枚对一枚' : '三枚对三枚');
}

function summary() {
  header('把九个可能，缩成一个', '两次称量');
  const positions = [235, 642, 1044];
  const labels = ['起点','第一称后','第二称后'];
  const counts = [9,3,1];
  for (let g = 0; g < 3; g++) {
    const x = positions[g];
    text(labels[g],x,255,26,MINT,{align:'center'});
    text(String(counts[g]),x,365,117,IVORY,{align:'center',font:LATIN});
    const list = g === 0 ? [1,2,3,4,5,6,7,8,9] : g === 1 ? lesson.practice.coins : [lesson.practice.answer];
    list.forEach((n,i) => coin(n,x+(i-(list.length-1)/2)*28,475,19));
    if (g < 2) {
      const ax = x + 205;
      stroke([[ax-44,367],[ax+22,367],[ax+13,359]], '#bbba8c',2);
      stroke([[ax+22,367],[ax+13,375]], '#bbba8c',2);
    }
  }
  footer('每次只保留仍有可能的那一组');
}

window.__video = {width: W, height: H, fps: lesson.fps, duration: lesson.duration, events: []};
window.__seek = function seek(time) {
  const cue = lesson.cues.find(c => time < c.end) || lesson.cues.at(-1);
  ctx.drawImage(ground,0,0);
  const t = Math.max(0,time-cue.start);
  if (cue.id === 'limit') {
    header('能在两称内找到它吗？','条件 · 没有砝码');
    balance([],[],[1,2,3,4,5,6,7,8,9],0,t,false,null,0,'待称');
    footer('只有一架等臂天平');
  } else if (['intro','split'].includes(cue.id)) overhead(cue.id,t);
  else if (cue.id === 'rule') summary();
  else weighing(cue.id,t,t/(cue.end-cue.start));
  caption.textContent = cue.text;
  caption.style.visibility = cue.text ? 'visible' : 'hidden';
};
window.__seek(0);
