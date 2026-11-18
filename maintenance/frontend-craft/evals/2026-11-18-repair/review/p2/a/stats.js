// 近两周：给后勤主管看的数据。只摆数，不替他下结论。
(function () {
  'use strict';
  const R = window.Repair, F = R.fmt, D = R.data, e = F.esc;
  const $ = (s) => document.querySelector(s);
  $('#now').textContent = `${F.dateLabel(R.NOW)} ${R.NOW.getHours()}:${String(R.NOW.getMinutes()).padStart(2, '0')}`;
  const T = R.tickets, V = new Map(T.map((t) => [t.id, R.view(t)]));
  const median = (a) => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const durOr = (m) => (m === null ? '—' : F.dur(m));
  const href = (t) => `ticket.html?id=${encodeURIComponent(t.id)}`;

  // 14 天
  const days = [];
  for (let i = 13; i >= 0; i--) { const d = new Date(R.NOW); d.setDate(d.getDate() - i); d.setHours(0, 0, 0, 0); days.push(d); }
  const key = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const perDay = days.map((d) => { const list = T.filter((t) => t.created.startsWith(key(d))); return { d, n: list.length, urgent: list.filter((t) => t.urgent).length }; });
  const maxDay = Math.max(...perDay.map((x) => x.n), 1);

  const open = T.filter((t) => R.OPEN.includes(t.status));
  const late = open.filter((t) => V.get(t.id).late);
  const fixedList = T.filter((t) => V.get(t.id).fixMinutes !== null);
  const assignMinutes = T.map((t) => { const a = t.events.find((x) => x.what === '派单'); return a ? F.minutesBetween(t.created, a.at) : null; }).filter((x) => x !== null);

  const figures = `<dl class="figures">
    <div><dt>报修</dt><dd>${T.length}<small>张</small></dd><p class="sub">其中紧急 ${T.filter((t) => t.urgent).length} 张</p></div>
    <div><dt>现在没完成</dt><dd>${open.length}<small>张</small></dd><p class="sub">${late.length ? `<span class="hot-text">超时 ${late.length} 张</span>` : '没有超时的'}</p></div>
    <div><dt>报修到派单，中位</dt><dd>${durOr(median(assignMinutes)).replace(/ (.+)$/, '<small>$1</small>')}</dd><p class="sub">${assignMinutes.length} 张派过的单</p></div>
    <div><dt>报修到修好，中位</dt><dd>${durOr(median(fixedList.map((t) => V.get(t.id).fixMinutes))).replace(/ (.+)$/, '<small>$1</small>')}</dd><p class="sub">${fixedList.length} 张修好的单</p></div>
  </dl>`;

  const bars = `<section class="panel"><h2>每天的报修量</h2><p class="cap">${F.dateLabel(days[0])} 到 ${F.dateLabel(days[13])}，今天算到 15:20</p>
    <div class="days" role="img" aria-label="近 14 天每天的报修量：${perDay.map((x) => `${x.d.getDate()} 日 ${x.n} 张`).join('，')}">
      ${perDay.map((x, i) => `<div class="bar${[0, 6].includes(x.d.getDay()) ? ' weekend' : ''}${i === 13 ? ' today' : ''}" style="height:${(x.n / maxDay) * 100}%"><span>${x.n}</span>${x.urgent ? `<i class="hotpart" style="height:${(x.urgent / x.n) * 100}%"></i>` : ''}</div>`).join('')}
    </div>
    <div class="days-x" aria-hidden="true">${perDay.map((x) => `<span>${x.d.getDate()}<b>${'日一二三四五六'[x.d.getDay()]}</b></span>`).join('')}</div>
    <p class="chart-legend"><span><i style="background:var(--hot)"></i>其中紧急的</span><span><i style="background:var(--line2)"></i>周末</span><span><i style="background:repeating-linear-gradient(135deg,var(--ink) 0 3px,#5b636b 3px 6px)"></i>今天，还没过完</span></p></section>`;

  // 报修到修好：每张单一个点，横轴是对数刻度
  const LO = Math.log(20), HI = Math.log(7 * 1440);
  const pos = (m) => Math.min(100, Math.max(0, ((Math.log(Math.max(m, 20)) - LO) / (HI - LO)) * 100));
  const lanes = [['全部', fixedList]].concat(['水暖', '电', '门窗家具'].map((c) => [c, fixedList.filter((t) => t.category === c)]));
  const strips = `<section class="panel"><h2>从报修到修好用了多久</h2><p class="cap">每个点是一张修好的单，竖线是中位数。超过 48 小时的标红。网络问题转给信息中心，不在这里。</p>
    ${lanes.map(([name, list]) => { const ms = list.map((t) => V.get(t.id).fixMinutes), md = median(ms);
      return `<div class="strip"><span>${name}</span><div class="lane" role="img" aria-label="${name}：${list.length} 张，中位 ${durOr(md)}">${ms.map((m) => `<i class="dot${m > 2880 ? ' over' : ''}" style="left:${pos(m).toFixed(1)}%"></i>`).join('')}${md === null ? '' : `<i class="med" style="left:${pos(md).toFixed(1)}%"></i>`}</div><span class="val">${durOr(md)}<small>${list.length} 张</small></span></div>`; }).join('')}
    <div class="axis" aria-hidden="true"><span></span><div class="ticks">${[[60, '1 小时'], [240, '4 小时'], [1440, '1 天'], [2880, '2 天'], [7200, '5 天']].map(([m, l]) => `<span style="left:${pos(m).toFixed(1)}%">${l}</span>`).join('')}</div><span></span></div></section>`;

  // 楼栋 × 类别
  const cell = (b, c) => T.filter((t) => t.building === b && t.category === c).length;
  const maxCell = Math.max(...D.buildings.flatMap((b) => D.categories.map((c) => cell(b, c))), 1);
  const matrix = `<section class="panel"><h2>各楼栋、各类别的报修</h2><p class="cap">格子分三档深浅，越深张数越多</p>
    <table class="matrix"><thead><tr><th scope="col">楼栋</th>${D.categories.map((c) => `<th scope="col">${c}</th>`).join('')}<th scope="col">合计</th></tr></thead>
    <tbody>${D.buildings.map((b) => `<tr><td>${e(b)}</td>${D.categories.map((c) => { const n = cell(b, c), r = n / maxCell, v = !n ? 0 : r <= 0.34 ? 9 : r <= 0.67 ? 26 : 80; return `<td class="cell${v > 50 ? ' dark' : ''}${n ? '' : ' zero'}" style="--v:${v}">${n}</td>`; }).join('')}<td class="total">${T.filter((t) => t.building === b).length}</td></tr>`).join('')}</tbody>
    <tfoot><tr><td>合计</td>${D.categories.map((c) => `<td>${T.filter((t) => t.category === c).length}</td>`).join('')}<td>${T.length}</td></tr></tfoot></table></section>`;

  const crew = `<section class="panel"><h2>各位师傅</h2><p class="cap">近两周接的单</p>
    <table class="plain"><thead><tr><th scope="col">师傅</th><th scope="col">接单</th><th scope="col">修好</th><th scope="col">手上</th><th scope="col">修好用时，中位</th></tr></thead>
    <tbody>${D.workers.map((w) => { const mine = T.filter((t) => t.worker === w.id), fx = mine.filter((t) => V.get(t.id).fixMinutes !== null);
      return `<tr><td>${w.name}　<span style="color:var(--ink3);font-size:0.8125rem">${w.trade}</span></td><td>${mine.length}</td><td>${fx.length}</td><td>${R.inHand(w.id).length}</td><td>${durOr(median(fx.map((t) => V.get(t.id).fixMinutes)))}</td></tr>`; }).join('')}</tbody></table></section>`;

  const backlogRows = open.sort(R.byPressure).sort((a, b) => V.get(b.id).late - V.get(a.id).late).map((t) => { const v = V.get(t.id), w = R.worker(t.worker);
    return `<tr><td><a href="${href(t)}"><span class="num" style="font-weight:500">${e(t.building)} ${e(t.room)}</span>　${e(t.description)}</a></td><td style="font-family:var(--font)">${t.status}</td><td style="font-family:var(--font)">${w ? w.name : '—'}</td><td>${F.dur(v.waited)}</td><td>${v.late ? `<span class="hot-text">超时 ${F.dur(v.lateBy)}</span>` : '—'}</td></tr>`; }).join('');
  const backlog = `<section class="panel"><h2>现在没完成的 ${open.length} 张</h2><p class="cap">超时的排在前面</p>
    <table class="plain"><thead><tr><th scope="col">工单</th><th scope="col">状态</th><th scope="col">师傅</th><th scope="col">报修后已</th><th scope="col">超时</th></tr></thead><tbody>${backlogRows}</tbody></table></section>`;

  $('#view').innerHTML = `<div class="stats-head"><h1>近两周</h1><p>${F.dateLabel(days[0])} 到 ${F.dateLabel(days[13])} 15:20</p></div>
    ${figures}<div class="cols">${bars}${strips}</div><div class="cols">${matrix}${crew}</div>${backlog}`;
})();
