// 工单列表：默认是“派工板”（等你派单 / 等学生确认 / 师傅手上），切到“全部”是一张查找用的表。
(function () {
  'use strict';
  const R = window.Repair, F = R.fmt, D = R.data, e = F.esc;
  const $ = (s) => document.querySelector(s);
  const q = { view: 'todo', text: '', building: '', category: '', status: '' };
  try { Object.assign(q, JSON.parse(sessionStorage.getItem('repair-a-list') || '{}')); } catch (err) { /* 用默认值 */ }

  $('#now').textContent = `${F.dateLabel(R.NOW)} ${R.NOW.getHours()}:${String(R.NOW.getMinutes()).padStart(2, '0')}`;
  const fill = (sel, first, list) => { sel.innerHTML = `<option value="">${first}</option>` + list.map((x) => `<option>${e(x)}</option>`).join(''); };
  fill($('#f-building'), '全部楼栋', D.buildings);
  fill($('#f-category'), '全部类别', D.categories);
  fill($('#f-status'), '全部状态', D.statuses);

  function match(t) {
    if (q.building && t.building !== q.building) return false;
    if (q.category && t.category !== q.category) return false;
    if (q.view === 'all' && q.status && t.status !== q.status) return false;
    const s = q.text.trim().toLowerCase();
    if (!s) return true;
    const w = R.worker(t.worker);
    return [t.room, t.building, t.building.replace(/\s/g, '') + t.room, t.reporter, t.description, t.id, t.phone, w ? w.name : ''].some((x) => String(x).toLowerCase().includes(s));
  }
  const href = (t) => `ticket.html?id=${encodeURIComponent(t.id)}`;
  const where = (t) => `<span class="where"><span class="bld">${e(t.building)}</span><span class="room">${e(t.room)}</span></span>`;
  const hot = (t) => (t.urgent ? '<span class="tag-hot">急</span>' : '');

  function rowTodo(t) {
    const v = R.view(t);
    let sub = `${F.when(t.created)} 报修`, cls = '';
    if (v.late) { sub = `超时 ${F.dur(v.lateBy)}`; cls = ' hot'; }
    else if (t.urgent) { sub = `还剩 ${F.dur(v.left)}`; cls = ' hot'; }
    const meta = [t.category, t.reporter, t.available].filter(Boolean).map(e).join(' · ');
    let buttons;
    if (t.category === '网络') {
      buttons = `<button class="btn" type="button" data-act="transfer" data-id="${t.id}">转交信息中心</button>`;
    } else {
      buttons = R.candidates(t).map((c) => `<button class="btn" type="button" data-act="assign" data-id="${t.id}" data-worker="${c.worker.id}" aria-label="派给${c.worker.name}，他手上有 ${c.load} 张单">${c.worker.name}<i>${c.load} 张</i></button>`).join('');
    }
    return `<li class="row"><a class="open" href="${href(t)}">${where(t)}<span class="what"><span class="desc">${hot(t)}${e(t.description)}</span><span class="meta" style="display:block">${meta}</span></span></a>
      <span class="clock"><span class="t">${F.dur(v.waited)}</span><span class="sub${cls}">${sub}</span></span>
      <span class="assign">${buttons}</span></li>`;
  }
  function rowConfirm(t) {
    const v = R.view(t), w = R.worker(t.worker);
    return `<li class="row"><a class="open" href="${href(t)}">${where(t)}<span class="what"><span class="desc">${e(t.description)}</span><span class="meta" style="display:block">${e(w.name)} ${F.when(v.since)} 修好 · ${e(t.reporter)} ${e(t.phone)}</span></span></a>
      <span class="clock"><span class="t">${F.dur(F.minutesBetween(v.since, R.NOW))}</span><span class="sub">还没确认</span></span>
      <span class="assign"><button class="btn" type="button" data-act="confirm" data-id="${t.id}">学生已确认</button></span></li>`;
  }
  function crew(w, list) {
    const jobs = list.filter((t) => t.worker === w.id).sort(R.byPressure).map((t) => {
      const v = R.view(t);
      const st = v.late ? `<span class="hot-text">超时 ${F.dur(v.lateBy)}</span>` : `${t.status} · ${F.dur(F.minutesBetween(v.since, R.NOW))}`;
      return `<a class="job${v.late ? ' late' : ''}" href="${href(t)}"><span class="at"><span>${e(t.building)}</span> ${e(t.room)}</span><span class="st">${st}</span><span class="d">${t.urgent ? '<span class="tag-hot ghost">急</span>' : ''}${e(t.description)}</span></a>`;
    }).join('');
    return `<div class="crew"><div class="crew-head"><h3>${w.name}</h3><span class="trade">${w.trade}${w.note ? '，' + w.note : ''}</span><a class="tel" href="tel:${w.phone.replace(/-/g, '')}">${w.phone}</a></div>${jobs || '<p class="free">手上没有活</p>'}</div>`;
  }

  function board(list) {
    const todo = list.filter((t) => t.status === '待派单').sort(R.byPressure);
    const conf = list.filter((t) => t.status === '待确认').sort((a, b) => R.view(a).since.localeCompare(R.view(b).since));
    const hand = list.filter((t) => t.status === '已派单' || t.status === '处理中');
    const filtered = q.text || q.building || q.category;
    return `<div class="board">
      <div>
        <section class="group" aria-labelledby="g1"><div class="group-head"><h2 id="g1">等你派单</h2><span class="count">${todo.length}</span><span class="hint">点名字直接派单，后面是他手上的单数</span></div>
          ${todo.length ? `<ol>${todo.map(rowTodo).join('')}</ol>` : `<p class="empty">${filtered ? '按现在的条件，没有要派的单。' : '都派出去了。'}</p>`}</section>
        <section class="group" aria-labelledby="g2"><div class="group-head"><h2 id="g2">等学生确认</h2><span class="count">${conf.length}</span></div>
          ${conf.length ? `<ol>${conf.map(rowConfirm).join('')}</ol>` : '<p class="empty">没有等确认的单。</p>'}</section>
      </div>
      <section class="group" aria-labelledby="g3"><div class="group-head"><h2 id="g3">师傅手上</h2><span class="count">${hand.length}</span></div>
        ${D.workers.map((w) => crew(w, hand)).join('')}</section>
    </div>`;
  }

  function table(list) {
    const rows = [...list].sort((a, b) => b.created.localeCompare(a.created)).map((t) => {
      const v = R.view(t), w = R.worker(t.worker), open = R.OPEN.includes(t.status);
      let d = '—';
      if (open) d = v.late ? `<span class="hot-text">超时 ${F.dur(v.lateBy)}</span>` : `已 ${F.dur(v.waited)}`;
      else if (v.fixMinutes !== null) d = F.dur(v.fixMinutes);
      return `<tr class="${open ? '' : 'closed'}"><td class="c-time">${F.when(t.created)}</td><td class="c-where"><span>${e(t.building)}</span> ${e(t.room)}</td>
        <td class="c-what"><a href="${href(t)}">${hot(t)}${e(t.description)}</a></td><td class="c-cat">${t.category}</td>
        <td class="c-st">${t.status}</td><td class="c-who">${w ? w.name : (t.status === '已转交' ? '信息中心' : '—')}</td><td class="c-dur">${d}</td></tr>`;
    }).join('');
    return `<div class="all-head group-head" style="border:0"><h2>全部工单</h2><span class="count">${list.length}</span><span class="hint">近两周，新的在前</span></div>
      <table class="table"><thead><tr><th>报修时间</th><th>地点</th><th>内容</th><th>类别</th><th>状态</th><th>处理人</th><th>报修到修好</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="7" class="empty" style="text-align:left">没有符合条件的工单。</td></tr>'}</tbody></table>`;
  }

  function render() {
    try { sessionStorage.setItem('repair-a-list', JSON.stringify(q)); } catch (err) { /* 忽略 */ }
    const all = R.tickets;
    $('#n-todo').textContent = all.filter((t) => R.OPEN.includes(t.status)).length;
    $('#n-all').textContent = all.length;
    document.querySelectorAll('.switch button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.view === q.view)));
    $('#f-status').hidden = q.view !== 'all';
    $('#f-status').value = q.status; $('#f-building').value = q.building; $('#f-category').value = q.category;
    if ($('#f-text').value !== q.text) $('#f-text').value = q.text;
    const list = all.filter(match);
    $('#view').innerHTML = q.view === 'all' ? table(list) : board(list);
  }

  let toastTimer;
  function toast(text) {
    $('#toast-text').textContent = text;
    $('#toast-undo').hidden = !R.canUndo;
    $('#toast').hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 8000);
  }

  document.querySelector('.switch').addEventListener('click', (ev) => { const b = ev.target.closest('button'); if (b) { q.view = b.dataset.view; render(); } });
  $('#f-text').addEventListener('input', (ev) => { q.text = ev.target.value; render(); });
  $('#f-building').addEventListener('change', (ev) => { q.building = ev.target.value; render(); });
  $('#f-category').addEventListener('change', (ev) => { q.category = ev.target.value; render(); });
  $('#f-status').addEventListener('change', (ev) => { q.status = ev.target.value; render(); });
  $('#view').addEventListener('click', (ev) => {
    const b = ev.target.closest('button[data-act]');
    if (!b) return;
    const row = b.closest('.row'), next = row && (row.nextElementSibling || row.previousElementSibling);
    const nextId = next && next.querySelector('button[data-id]') ? next.querySelector('button[data-id]').dataset.id : null;
    const A = R.actions, id = b.dataset.id;
    const msg = b.dataset.act === 'assign' ? A.assign(id, b.dataset.worker) : b.dataset.act === 'transfer' ? A.transfer(id) : A.confirm(id);
    render();
    toast(msg);
    const focus = nextId && document.querySelector(`button[data-id="${nextId}"]`);
    (focus || $('#toast-undo')).focus();
  });
  $('#toast-undo').addEventListener('click', () => { if (R.undo()) { render(); toast('已撤销'); } });
  $('#reset').addEventListener('click', () => { R.reset(); render(); toast('已恢复成最初的示例'); });
  document.addEventListener('keydown', (ev) => {
    if (ev.key.toLowerCase() === 'n' && !ev.ctrlKey && !ev.metaKey && !ev.altKey && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) location.href = 'new.html';
    if (ev.key === '/' && document.activeElement !== $('#f-text')) { ev.preventDefault(); $('#f-text').focus(); }
  });
  render();
})();
