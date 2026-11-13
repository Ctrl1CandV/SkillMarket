// 校园树叶图鉴：20 种树的资料，以及按叶形参数把叶子画成 SVG 的几个函数。
// 叶子不是照片，是按形态学特征画的示意：叶形、叶缘、叶脉、单叶还是复叶。
(function () {
  const PI = Math.PI;
  // —— 单叶：L 长度，W 半宽，pos 最宽处离叶基的比例，b 两端尖的程度，serr 锯齿深浅，asym 基部偏斜 ——
  function blade(o) {
    const L = o.L || 150, W = o.W || 40, pos = o.pos || 0.45, b = o.b || 1, serr = o.serr || 0, asym = o.asym || 0, N = serr ? 64 : 34;
    const a = Math.log(0.5) / Math.log(pos), half = (t, side) => W * Math.pow(Math.sin(PI * Math.pow(t, a)), b) * (1 + side * asym * (1 - t) * (1 - t));
    const right = [], left = [];
    for (let i = 0; i <= N; i++) { const t = i / N, dent = serr && i % 2 === 0 && i > 0 && i < N ? 1 - serr : 1, lift = serr && i % 2 === 0 ? 0.012 : 0;
      right.push([half(t, 1) * dent, -(t - lift) * L]); left.push([-half(t, -1) * dent, -(t - lift) * L]); }
    const d = 'M' + right.map(p => p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join('L') + 'L' + left.reverse().map(p => p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join('L') + 'Z';
    let veins = `M0 0L0 ${(-L * 0.97).toFixed(1)}`;
    if (o.three) veins += [1, -1].map(s => `M0 ${-L * 0.1}Q${s * W * 0.72} ${-L * 0.4} ${s * W * 0.22} ${-L * 0.84}`).join('');   // 离基三出脉
    else for (let k = 1; k <= (o.veins || 6); k++) { const t = 0.08 + 0.74 * k / ((o.veins || 6) + 1), t2 = Math.min(0.97, t + 0.13); [1, -1].forEach(s => { veins += `M0 ${(-t * L).toFixed(1)}L${(s * half(t2, s) * 0.86).toFixed(1)} ${(-t2 * L).toFixed(1)}`; }); }
    return { d, veins };
  }
  const leafSvg = (o, c) => { const p = blade(o); return `<path d="${p.d}" fill="${c.fill}" stroke="${c.edge}" stroke-width="1.4" stroke-linejoin="round"/><path d="${p.veins}" fill="none" stroke="${c.vein}" stroke-width="${o.veinW || 1.1}" stroke-linecap="round" opacity=".75"/>`; };
  const stem = (c, len) => `<path d="M0 ${len || 24}L0 0" stroke="${c.edge}" stroke-width="2.6" stroke-linecap="round" fill="none"/>`;

  const DRAW = {
    simple: (o, c) => `<g transform="translate(100 ${o.y || 190}) scale(${o.s || 1})">${stem(c, o.stem)}${leafSvg(o, c)}</g>`,
    // 银杏：扇形，顶端中间一个缺口，叶脉从叶柄一路二叉分开
    fan: (o, c) => { const R = 112, span = 0.8, pts = [];
      for (let i = 0; i <= 60; i++) { const th = -span + 2 * span * i / 60, r = R * (1 - 0.035 * Math.cos(th * 9)) * (1 - 0.3 * Math.exp(-Math.pow(th / 0.07, 2))); pts.push([r * Math.sin(th), -r * Math.cos(th)]); }
      let v = ''; for (let i = 0; i <= 16; i++) { const th = -span * 0.94 + 2 * span * 0.94 * i / 16; v += `M0 0L${(R * 0.9 * Math.sin(th)).toFixed(1)} ${(-R * 0.9 * Math.cos(th)).toFixed(1)}`; }
      return `<g transform="translate(100 160)">${stem(c, 44)}<path d="M0 0L${pts.map(p => p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join('L')}Z" fill="${c.fill}" stroke="${c.edge}" stroke-width="1.4" stroke-linejoin="round"/><path d="${v}" stroke="${c.vein}" stroke-width=".8" opacity=".7" fill="none"/></g>`; },
    // 掌状裂：n 个裂片，depth 裂得多深，serr 裂片边缘的锯齿
    palmate: (o, c) => { const n = o.n, R = o.R || 96, spread = o.spread || 2.2, step = spread / (n - 1), pts = [], tips = [];
      const lobe = (th) => { let best = 0; for (let k = 0; k < n; k++) { const th0 = -spread / 2 + k * step, u = Math.abs(th - th0) / (step * (o.fat || 0.62)), len = 1 - (o.short || 0.16) * Math.abs(k - (n - 1) / 2); if (u < 1) best = Math.max(best, len * Math.pow(1 - Math.pow(u, o.p || 1.6), 0.9)); } return best; };
      for (let k = 0; k < n; k++) { const th0 = -spread / 2 + k * step, len = 1 - (o.short || 0.16) * Math.abs(k - (n - 1) / 2); tips.push([R * len * Math.sin(th0) * 0.93, -R * len * Math.cos(th0) * 0.93]); }
      const M = 220; for (let i = 0; i <= M; i++) { const th = -PI * 0.92 + 2 * PI * 0.92 * i / M, body = (1 - o.depth), g = lobe(th), over = Math.abs(th) - spread / 2 - step * 0.35, base = over > 0 ? Math.max(0.28, 0.9 - 0.75 * over) : 1;
        let r = R * (body * base + o.depth * g); if (o.serr && i % 2) r *= 1 - o.serr * (g > 0.05 ? 1 : 0.3); pts.push([r * Math.sin(th), -r * Math.cos(th)]); }
      return `<g transform="translate(100 ${o.y || 132})">${`<path d="M0 62L0 8" stroke="${c.edge}" stroke-width="2.6" stroke-linecap="round" fill="none"/>`}<path d="M${pts.map(p => p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join('L')}Z" transform="translate(0 8)" fill="${c.fill}" stroke="${c.edge}" stroke-width="1.4" stroke-linejoin="round"/><path d="${tips.map(t => `M0 8L${t[0].toFixed(1)} ${(t[1] + 8).toFixed(1)}`).join('')}" stroke="${c.vein}" stroke-width="1.1" opacity=".75" fill="none"/></g>`; },
    // 羽状复叶：一根叶轴，两边成对的小叶；odd 表示顶端还有一片
    pinnate: (o, c) => { const H = o.H || 138, n = o.pairs; let s = `<path d="M0 22L0 ${-H}" stroke="${c.edge}" stroke-width="2.2" stroke-linecap="round" fill="none"/>`;
      for (let i = 0; i < n; i++) { const y = -H * (0.12 + 0.8 * i / (n - (o.odd ? 0 : 1) || 1)), k = 1 - 0.22 * Math.abs(i / (n - 1 || 1) - 0.35);
        [1, -1].forEach(side => { s += `<g transform="translate(0 ${y.toFixed(1)}) rotate(${side * (o.angle || 62)}) scale(${k.toFixed(2)})">${leafSvg(o.leaflet, c)}</g>`; }); }
      if (o.odd) s += `<g transform="translate(0 ${-H})">${leafSvg(o.leaflet, c)}</g>`;
      return `<g transform="translate(100 184)">${s}</g>`; },
    // 二回羽状复叶（合欢）：叶轴两边是羽片，每个羽片上再排满很小的小叶
    bipinnate: (o, c) => { const H = 150; let s = `<path d="M0 24L0 ${-H}" stroke="${c.edge}" stroke-width="2.2" stroke-linecap="round" fill="none"/>`;
      for (let i = 0; i < o.pairs; i++) { const y = -H * (0.14 + 0.82 * i / (o.pairs - 1)), len = 62 - 14 * Math.abs(i / (o.pairs - 1) - 0.4);
        [1, -1].forEach(side => { let f = `<path d="M0 0L0 ${-len}" stroke="${c.edge}" stroke-width="1.2" fill="none"/>`;
          for (let j = 0; j < 13; j++) { const yy = -len * (0.1 + 0.88 * j / 12); f += `<path d="M0 ${yy.toFixed(1)}l6.2 -3.4M0 ${yy.toFixed(1)}l-6.2 -3.4" stroke="${c.fill}" stroke-width="3.4" stroke-linecap="round"/>`; }
          s += `<g transform="translate(0 ${y.toFixed(1)}) rotate(${side * 68})">${f}</g>`; }); }
      return `<g transform="translate(100 176)">${s}</g>`; },
    // 水杉：条形小叶对生，排成一片羽毛
    feather: (o, c) => { const H = 160; let s = `<path d="M0 20L0 ${-H}" stroke="${c.edge}" stroke-width="1.8" stroke-linecap="round" fill="none"/>`;
      for (let i = 0; i < 24; i++) { const t = i / 23, y = -H * (0.06 + 0.92 * t), len = 30 * Math.sin(PI * Math.pow(t, 0.75)) + 5; s += `<path d="M0 ${y.toFixed(1)}l${len.toFixed(1)} ${(-len * 0.34).toFixed(1)}M0 ${y.toFixed(1)}l${(-len).toFixed(1)} ${(-len * 0.34).toFixed(1)}" stroke="${c.fill}" stroke-width="3.6" stroke-linecap="round"/>`; }
      return `<g transform="translate(100 180)">${s}</g>`; },
    // 雪松：针叶一簇一簇长在短枝上
    tufts: (o, c) => { let s = `<path d="M-46 62Q-6 -20 40 -92" stroke="#7A5C3E" stroke-width="5" stroke-linecap="round" fill="none"/>`;
      [[-36, 44, -0.5], [-14, 2, 0.5], [10, -38, -0.3], [34, -80, 0.4]].forEach(([x, y, tilt]) => { for (let i = 0; i < 17; i++) { const th = tilt - 1.5 + 3.0 * i / 16, len = 36 + 6 * Math.sin(i * 2.1); s += `<path d="M${x} ${y}l${(len * Math.sin(th)).toFixed(1)} ${(-len * Math.cos(th)).toFixed(1)}" stroke="${c.fill}" stroke-width="2.2" stroke-linecap="round"/>`; } });
      return `<g transform="translate(100 118)">${s}</g>`; },
  };

  const GREEN = { deep: '#2F6B3F', mid: '#4C8C4A', fresh: '#6FA24A', blue: '#3F7A5E', dark: '#27563A', olive: '#6B8E3A' };
  const AUTUMN = { yellow: '#E0AE1E', gold: '#D99A12', red: '#C2402A', crimson: '#A8261F', orange: '#D9722A', brown: '#A8692E' };
  const shade = (hex, k) => { const n = parseInt(hex.slice(1), 16), f = (v) => Math.max(0, Math.min(255, Math.round(v * k))); return '#' + [n >> 16, (n >> 8) & 255, n & 255].map(v => f(v).toString(16).padStart(2, '0')).join(''); };

  const TREES = [
    { id: 'ginkgo', alias: ['白果树', '公孙树'], name: '银杏', latin: 'Ginkgo biloba', family: '银杏科', type: 'single', margin: 'lobed', habit: 'deciduous', autumn: 'yellow', g: 'fresh', a: 'yellow', draw: ['fan', {}],
      key: '叶子像一把小扇子，顶端中间常有一个缺口。叶脉从叶柄出发一路二叉分开，没有主脉，别的树都不是这样。', similar: '', when: '4 月展叶，11 月叶子变成金黄色。雌树秋天结黄色的“白果”，外种皮有臭味。' },
    { id: 'plane', alias: ['法国梧桐', '法桐', '二球悬铃木'], name: '悬铃木', latin: 'Platanus × acerifolia', family: '悬铃木科', type: 'single', margin: 'lobed', habit: 'deciduous', autumn: 'brown', g: 'mid', a: 'brown', draw: ['palmate', { n: 5, depth: 0.5, serr: 0.07, spread: 2.5, fat: 0.82, p: 1.0, R: 104, short: 0.14 }],
      key: '大叶子，掌状 3 到 5 裂，裂得不深。树皮一块一块剥落，露出灰白色的内皮。球形的果常常两个一串挂在枝上。', similar: '俗称“法国梧桐”，但它不是梧桐。和枫香比：悬铃木叶子更大，树皮斑驳。', when: '4 到 5 月开花，果球挂到冬天。秋天叶子变黄褐色。' },
    { id: 'camphor', alias: ['樟树'], name: '香樟', latin: 'Cinnamomum camphora', family: '樟科', type: 'single', margin: 'entire', habit: 'evergreen', autumn: 'none', g: 'fresh', a: 'red', draw: ['simple', { L: 122, W: 36, pos: 0.42, b: 1.05, three: true, y: 178, stem: 30 }],
      key: '卵状椭圆形，边缘光滑。靠近叶基的地方分出三条主脉，叫“离基三出脉”。揉碎叶子有樟脑的香味。', similar: '', when: '常绿。春天换叶，老叶变红落下，所以四五月地上会有一层红叶。4 到 5 月开黄绿色小花。' },
    { id: 'maple', alias: ['枫树', '槭树'], name: '鸡爪槭', latin: 'Acer palmatum', family: '无患子科', type: 'single', margin: 'lobed', habit: 'deciduous', autumn: 'red', g: 'fresh', a: 'crimson', draw: ['palmate', { n: 7, depth: 0.8, serr: 0.05, spread: 3.5, fat: 0.5, p: 1.0, R: 102, short: 0.09 }],
      key: '掌状深裂，通常 7 个裂片，像张开的手，裂片边缘有细锯齿。叶子在枝上成对生长。果实带一对翅膀。', similar: '和枫香比：鸡爪槭裂片多而深，叶子对生；枫香只有 3 裂，叶子互生。', when: '秋天变红，是最常见的红叶树之一。5 月开花，9 到 10 月翅果成熟。' },
    { id: 'sweetgum', alias: ['枫树', '枫香树'], name: '枫香', latin: 'Liquidambar formosana', family: '蕈树科', type: 'single', margin: 'lobed', habit: 'deciduous', autumn: 'red', g: 'mid', a: 'red', draw: ['palmate', { n: 3, depth: 0.6, serr: 0.05, spread: 2.2, fat: 0.95, p: 1.0, R: 108, short: 0.1 }],
      key: '掌状 3 裂，像一个“山”字，边缘有锯齿。叶子在枝上交错着长（互生）。果实是带刺的小球。', similar: '常被叫成“枫树”，但它不是槭树。看叶子怎么长：枫香互生，槭树对生。', when: '秋天变红或者变黄。3 到 4 月开花，10 月果球成熟。' },
    { id: 'willow', alias: ['柳树'], name: '垂柳', latin: 'Salix babylonica', family: '杨柳科', type: 'single', margin: 'serrate', habit: 'deciduous', autumn: 'yellow', g: 'fresh', a: 'yellow', draw: ['simple', { L: 158, W: 11, pos: 0.36, b: 0.9, serr: 0.1, veins: 9, y: 192, stem: 10 }],
      key: '又细又长的披针形，边缘有很细的锯齿。枝条细软下垂，最好认的其实是整棵树的样子。', similar: '', when: '早春最早发芽的树之一。3 到 4 月开花，4 月飘柳絮。秋天叶子变黄。' },
    { id: 'metaseq', name: '水杉', latin: 'Metasequoia glyptostroboides', family: '柏科', type: 'needle', margin: 'entire', habit: 'deciduous', autumn: 'brown', g: 'fresh', a: 'orange', draw: ['feather', {}],
      key: '条形的小叶两两相对，在小枝上排成一片羽毛。它是少数会落叶的针叶树，秋天连小枝一起掉。', similar: '和落羽杉比：水杉的小叶是对生的，落羽杉是互生的。', when: '秋天变成棕红色，然后落叶。被称为“活化石”，20 世纪 40 年代才在中国被重新发现。' },
    { id: 'cedar', alias: ['喜马拉雅雪松'], name: '雪松', latin: 'Cedrus deodara', family: '松科', type: 'needle', margin: 'entire', habit: 'evergreen', autumn: 'none', g: 'blue', a: 'blue', draw: ['tufts', {}],
      key: '针叶在短枝上一簇一簇地长，每簇二三十根；长枝上的针叶则是散开的。树形像一座塔，大枝平展、枝梢下垂。', similar: '和松树比：松树的针叶是 2、3 或 5 根一束，基部有叶鞘；雪松是很多根簇生。', when: '常绿。10 到 11 月开花，球果第二年成熟。' },
    { id: 'sophora', alias: ['槐树'], name: '国槐', latin: 'Styphnolobium japonicum', family: '豆科', type: 'compound', margin: 'entire', habit: 'deciduous', autumn: 'yellow', g: 'mid', a: 'yellow', draw: ['pinnate', { pairs: 5, odd: true, angle: 70, leaflet: { L: 36, W: 10, pos: 0.42, b: 0.95, veins: 0 } }],
      key: '一根叶轴上有 7 到 15 片卵形小叶，顶端还有一片（奇数羽状复叶）。果实像一串念珠，中间一节一节地缢缩。', similar: '和刺槐（洋槐）比：国槐夏天开黄白色花，枝上没有刺；刺槐春天开白花，枝上有刺。', when: '7 到 8 月开花，是夏天少有的开花乔木。秋天叶子变黄。' },
    { id: 'koel', alias: ['灯笼树'], name: '栾树', latin: 'Koelreuteria paniculata', family: '无患子科', type: 'compound', margin: 'serrate', habit: 'deciduous', autumn: 'yellow', g: 'mid', a: 'gold', draw: ['pinnate', { pairs: 4, odd: true, angle: 66, leaflet: { L: 44, W: 13, pos: 0.38, b: 0.9, serr: 0.24, veins: 0 } }],
      key: '羽状复叶，小叶边缘有粗锯齿或者缺刻。最好认的是果实：像一个个三角形的小灯笼挂满树梢。', similar: '', when: '夏天开一树黄花，秋天“灯笼”由绿变红褐，叶子变黄。一棵树上能同时看到三种颜色。' },
    { id: 'osmanthus', alias: ['木樨'], name: '桂花', latin: 'Osmanthus fragrans', family: '木樨科', type: 'single', margin: 'serrate', habit: 'evergreen', autumn: 'none', g: 'deep', a: 'deep', draw: ['simple', { L: 118, W: 30, pos: 0.48, b: 1.15, serr: 0.05, veins: 8, y: 176, stem: 24 }],
      key: '椭圆形，厚而硬，成对生长。边缘有的光滑，有的上半部分有细锯齿。不开花的时候不显眼，开花时闻香就能找到。', similar: '和女贞比：桂花的叶子更硬，叶脉在叶面上凹下去，摸起来不平。', when: '常绿。9 到 10 月开花，花很小，香气很浓。' },
    { id: 'magnolia-g', alias: ['荷花玉兰'], name: '广玉兰', latin: 'Magnolia grandiflora', family: '木兰科', type: 'single', margin: 'entire', habit: 'evergreen', autumn: 'none', g: 'dark', a: 'dark', draw: ['simple', { L: 156, W: 44, pos: 0.5, b: 1.0, veins: 9, y: 190, stem: 22 }],
      key: '又大又厚的椭圆形叶子，正面深绿发亮，背面有一层锈褐色的短绒毛。翻过来看背面，一眼就能认出来。', similar: '又叫荷花玉兰。和白玉兰比：广玉兰常绿、叶子厚硬，初夏开花；白玉兰落叶，早春先开花后长叶。', when: '常绿。5 到 6 月开花，花像荷花那么大，白色。' },
    { id: 'yulan', alias: ['白玉兰'], name: '玉兰', latin: 'Yulania denudata', family: '木兰科', type: 'single', margin: 'entire', habit: 'deciduous', autumn: 'yellow', g: 'fresh', a: 'yellow', draw: ['simple', { L: 140, W: 50, pos: 0.64, b: 0.86, veins: 8, y: 186, stem: 22 }],
      key: '倒卵形：上半部分最宽，顶端突然收成一个小尖。冬天枝头上有毛茸茸的大花芽。', similar: '', when: '早春 3 月先开花后长叶，满树白花。秋天叶子变黄。' },
    { id: 'cherry', alias: ['樱花', '染井吉野'], name: '东京樱花', latin: 'Prunus × yedoensis', family: '蔷薇科', type: 'single', margin: 'serrate', habit: 'deciduous', autumn: 'red', g: 'mid', a: 'orange', draw: ['simple', { L: 128, W: 36, pos: 0.4, b: 1.2, serr: 0.1, veins: 8, y: 180, stem: 28 }],
      key: '卵状椭圆形，顶端渐渐变尖，边缘有尖锐的锯齿。叶柄靠近叶片的地方有一两个小疙瘩（腺体）。树皮上有横向的皮孔。', similar: '', when: '3 月底到 4 月初开花，花期只有一周左右。秋天叶子变成橙红色。' },
    { id: 'elm', alias: ['白榆', '榆钱树'], name: '榆树', latin: 'Ulmus pumila', family: '榆科', type: 'single', margin: 'serrate', habit: 'deciduous', autumn: 'yellow', g: 'mid', a: 'yellow', draw: ['simple', { L: 104, W: 30, pos: 0.44, b: 1.1, serr: 0.12, asym: 0.5, veins: 10, y: 170, stem: 14 }],
      key: '椭圆状卵形，边缘有锯齿。叶子的基部两边不一样大，是歪的。春天结一串串圆形的“榆钱”。', similar: '', when: '3 到 4 月先开花后长叶，4 到 5 月榆钱成熟。秋天叶子变黄。' },
    { id: 'poplar', alias: ['杨树', '加拿大杨'], name: '加杨', latin: 'Populus × canadensis', family: '杨柳科', type: 'single', margin: 'serrate', habit: 'deciduous', autumn: 'yellow', g: 'mid', a: 'gold', draw: ['simple', { L: 112, W: 50, pos: 0.2, b: 0.62, serr: 0.06, veins: 6, y: 168, stem: 44 }],
      key: '三角形或者三角状卵形，边缘有圆钝的锯齿。叶柄很长，而且是侧扁的，所以一有风叶子就哗哗地翻动。', similar: '', when: '4 月开花，5 月飘杨絮。秋天叶子变黄。' },
    { id: 'tallow', name: '乌桕', latin: 'Triadica sebifera', family: '大戟科', type: 'single', margin: 'entire', habit: 'deciduous', autumn: 'red', g: 'fresh', a: 'crimson', draw: ['simple', { L: 104, W: 44, pos: 0.4, b: 1.7, veins: 6, y: 164, stem: 40 }],
      key: '菱形的叶子，边缘光滑，顶端拉出一个长尖，叶柄细长。冬天落叶后，枝头留着一粒粒白色的种子。', similar: '', when: '秋天叶色很艳，一棵树上有红、紫、黄几种颜色。种子外面有一层白蜡，以前用来做蜡烛。' },
    { id: 'albizia', alias: ['绒花树', '马缨花'], name: '合欢', latin: 'Albizia julibrissin', family: '豆科', type: 'compound', margin: 'entire', habit: 'deciduous', autumn: 'yellow', g: 'fresh', a: 'yellow', draw: ['bipinnate', { pairs: 6 }],
      key: '二回羽状复叶：叶轴两边先分出羽片，每个羽片上再排满很小的镰刀形小叶。到了晚上小叶会两两合拢。', similar: '', when: '6 到 7 月开花，花像一团团粉红色的绒球。秋天叶子变黄。' },
    { id: 'privet', name: '女贞', latin: 'Ligustrum lucidum', family: '木樨科', type: 'single', margin: 'entire', habit: 'evergreen', autumn: 'none', g: 'deep', a: 'deep', draw: ['simple', { L: 120, W: 38, pos: 0.38, b: 1.1, veins: 6, y: 176, stem: 24 }],
      key: '卵形，革质，边缘光滑，表面发亮，成对生长。冬天树上挂着一串串蓝黑色的小果子。', similar: '和桂花比：女贞的叶面平滑，叶脉不明显；桂花的叶脉凹陷。', when: '常绿。6 到 7 月开一大簇白色小花，11 月以后果实变成蓝黑色。' },
    { id: 'soapberry', alias: ['肥皂树'], name: '无患子', latin: 'Sapindus saponaria', family: '无患子科', type: 'compound', margin: 'entire', habit: 'deciduous', autumn: 'yellow', g: 'mid', a: 'gold', draw: ['pinnate', { pairs: 5, odd: false, angle: 58, H: 150, leaflet: { L: 54, W: 11, pos: 0.36, b: 1.0, veins: 0, asym: 0.3 } }],
      key: '羽状复叶，小叶是披针形的，边缘光滑，顶端没有单独的一片（偶数羽状复叶）。', similar: '和国槐比：无患子的小叶更长更尖，顶端成对；国槐的小叶是卵形，顶端多一片。', when: '秋天整棵树变成金黄色。果皮含皂素，以前用来洗衣服，所以又叫“肥皂树”。' },
  ];

  function draw(tree, season) {
    const base = season === 'autumn' && tree.habit === 'deciduous' ? AUTUMN[tree.a] : GREEN[tree.g];
    const c = { fill: base, edge: shade(base, 0.62), vein: shade(base, season === 'autumn' && tree.habit === 'deciduous' ? 0.7 : 1.45) };
    return DRAW[tree.draw[0]](tree.draw[1], c);
  }
  window.Leaves = { TREES, draw };
})();
