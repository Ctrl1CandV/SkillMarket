// 方向 B：三栏调度台。选中一张单，右边直接看、直接处理，不用换页。只做了这一屏。
(function () {
  'use strict';
  const R = window.Repair, F = R.fmt, D = R.data, e = F.esc, A = R.actions;
  const $ = (s) => document.querySelector(s);
  const q = { box: '全部待办', text: '', building: '', category: '', id: null };
  $('#now').textContent = `${F.dateLabel(R.NOW)} ${R.NOW.getHours()}:${String(R.NOW.getMinutes()).padStart(2, '0')}`;
  const fill = (sel, first, list) => { sel.innerHTML = `<option value="">${first}</option>` + list.map((x) => `<option>${e(x)}</option>`).join(''); };
  fill($('#f-building'), '全部楼栋', D.buildings);
  fill($('#f-category'), '全部类别', D.categories);

  const inBox = (t) => (q.box === '全部待办' ? R.OPEN.includes(t.status) : t.status === q.box);
  function match(t) {
    if (!inBox(t)) return false;
    if (q.building && t.building !== q.building) return false;
    if (q.category && t.category !== q.category) return false;
    const s = q.text.trim().toLowerCase();
    if (!s) return true;
    return [t.room, t.building, t.reporter, t.description, t.id, t.phone].some((x) => String(x).toLowerCase().includes(s));
  }
  function pressure(t) {
    const v = R.view(t);
    if (v.late) return { text: `超时 ${F.dur(v.lateBy)}`, hot: true };
    if (t.status === '待派单' && t.urgent) return { text: `还剩 ${F.dur(v.left)}`, hot: true };
    if (R.OPEN.includes(t.status)) return { text: `已 ${F.dur(v.waited)}`, hot: false };
    return { text: F.when(t.created), hot: false };
  }

  function nav() {
    const T = R.tickets, n = (s) => T.filter((t) => t.status === s).length;
    const hotTodo = T.some((t) => t.status === '待派单' && (t.urgent || R.view(t).late));
    const item = (name, count, hot) => `<button type="button" data-box="${name}" aria-current="${q.box === name}">${name === '全部待办' ? '' : `<span class="dot s-${name}"></span>`}${name}<span class="n${hot ? ' hot' : ''}">${count}</span></button>`;
    $('#nav').innerHTML = `<h2>待办</h2>${item('全部待办', T.filter((t) => R.OPEN.includes(t.status)).length)}${item('待派单', n('待派单'), hotTodo)}${item('已派单', n('已派单'))}${item('处理中', n('处理中'))}${item('待确认', n('待确认'))}
      <h2>已结束</h2>${item('已完成', n('已完成'))}${item('已转交', n('已转交'))}${item('已取消', n('已取消'))}`;
  }

  function rows(list) {
    $('#list-title').innerHTML = `<strong>${q.box}</strong>${list.length} 张${R.OPEN.includes(q.box) || q.box === '全部待办' ? '，急的和超时的在前' : '，新的在前'}`;
    $('#rows').innerHTML = list.map((t) => {
      const p = pressure(t), w = R.worker(t.worker);
      return `<li><button class="item" type="button" data-id="${t.id}" aria-current="${t.id === q.id}">
        <span class="l1"><span class="place">${e(t.building)} ${e(t.room)}</span>${t.urgent ? '<span class="badge">急</span>' : ''}<span class="t${p.hot ? ' hot' : ''}">${p.text}</span></span>
        <span class="l2" style="display:block">${e(t.description)}</span>
        <span class="l3">${q.box === '全部待办' ? `<span class="dot s-${t.status}"></span>${t.status} · ` : ''}${t.category}${w ? ' · ' + w.name : ''} · ${e(t.reporter)}</span></button></li>`;
    }).join('') || '<li class="none">这里没有工单。</li>';
  }

  function workerButtons(t, list) {
    return list.map((c, i) => `<button class="b${i === 0 && !t.worker ? ' main' : ''}" type="button" data-act="assign" data-worker="${c.worker.id}">${c.worker.name}<small>手上 ${c.load} 张${c.aircon ? '，会修空调' : ''}${c.nearby ? `，同楼 ${c.nearby} 张` : ''}</small></button>`).join('');
  }
  function doPanel(t) {
    const w = R.worker(t.worker);
    const lesser = '<div class="lesser"><button type="button" data-act="cancel">取消这张工单</button></div>';
    if (t.status === '待派单') {
      if (t.category === '网络') return `<div class="do"><h2>网络问题转给信息中心</h2><div class="rowb"><button class="b main" type="button" data-act="transfer">转交信息中心</button></div>${lesser}</div>`;
      return `<div class="do"><h2>派给谁</h2><div class="rowb">${workerButtons(t, R.candidates(t))}</div>${lesser}</div>`;
    }
    if (t.status === '已派单') return `<div class="do"><h2>等${w.name}上门</h2><div class="rowb"><button class="b main" type="button" data-act="start">${w.name}已经开始处理</button><a class="b" href="tel:${w.phone.replace(/-/g, '')}">打给${w.name}<small>${w.phone}</small></a></div>${lesser}</div>`;
    if (t.status === '处理中') return `<div class="do"><h2>${w.name}修好以后记一下</h2><label for="fixed-note">怎么修的（可以不填）</label><textarea id="fixed-note" autocomplete="off"></textarea><div class="rowb"><button class="b main" type="button" data-act="fixed">记为修好</button><a class="b" href="tel:${w.phone.replace(/-/g, '')}">打给${w.name}<small>${w.phone}</small></a></div>${lesser}</div>`;
    if (t.status === '待确认') return `<div class="do"><h2>${w.name}说修好了，问一下学生</h2><div class="rowb"><button class="b main" type="button" data-act="confirm">学生确认修好了</button><button class="b" type="button" data-act="reopen">没修好，退回给${w.name}</button><a class="b" href="tel:${t.phone.replace(/-/g, '')}">打给${e(t.reporter)}<small>${e(t.phone)}</small></a></div></div>`;
    return '';
  }
  function pane() {
    const t = q.id && R.find(q.id);
    if (!t) { $('#pane').innerHTML = '<p class="none" style="padding-top:6rem">从中间选一张工单。</p>'; return; }
    const p = pressure(t), w = R.worker(t.worker), open = R.OPEN.includes(t.status);
    $('#pane').innerHTML = `<div class="pane-in">
      <div class="p-head"><h1>${e(t.building)} ${e(t.room)}</h1><span class="pill"><span class="dot s-${t.status}"></span>${t.status}</span>${t.urgent ? '<span class="pill hot">紧急</span>' : ''}${p.hot ? `<span class="pill hot">${p.text}</span>` : ''}<span class="id">${e(t.id)}</span></div>
      <p class="p-desc">${e(t.description)}</p>
      ${doPanel(t)}
      <dl class="facts">
        <div><dt>报修人</dt><dd>${e(t.reporter)}　<a href="tel:${t.phone.replace(/-/g, '')}">${e(t.phone)}</a></dd></div>
        <div><dt>方便上门</dt><dd>${e(t.available) || '没有说'}</dd></div>
        <div><dt>类别</dt><dd>${t.category}${w ? ' · ' + w.name : ''}</dd></div>
        <div><dt>照片</dt><dd>${t.photos ? `学生说拍了 ${t.photos} 张` : '没有'}</dd></div>
      </dl>
      <h2 class="sec">处理经过</h2>
      <ol class="tl">${t.events.map((ev) => `<li><span class="w">${e(ev.what)}</span><span class="a">${F.when(ev.at)} · ${e(ev.who)}</span>${ev.note ? `<p class="nt">${e(ev.note)}</p>` : ''}</li>`).join('')}</ol>
      ${open ? '<form class="note-form" id="note-form"><input id="note-text" type="text" autocomplete="off" aria-label="加一条备注" placeholder="加一条备注"><button class="b" type="submit">加备注</button></form>' : ''}
    </div>`;
  }

  function render(keep) {
    const closed = !R.OPEN.includes(q.box) && q.box !== '全部待办';
    const list = R.tickets.filter(match).sort(closed ? (a, b) => b.created.localeCompare(a.created) : R.byPressure);
    if (!keep || !list.some((t) => t.id === q.id)) q.id = list.length ? list[0].id : null;
    nav(); rows(list); pane();
  }
  let timer;
  function toast(text) { $('#toast-text').textContent = text; $('#toast-undo').hidden = !R.canUndo; $('#toast').hidden = false; clearTimeout(timer); timer = setTimeout(() => { $('#toast').hidden = true; }, 8000); }

  $('#nav').addEventListener('click', (ev) => { const b = ev.target.closest('button[data-box]'); if (b) { q.box = b.dataset.box; render(false); } });
  $('#rows').addEventListener('click', (ev) => { const b = ev.target.closest('button[data-id]'); if (b) { q.id = b.dataset.id; render(true); } });
  $('#f-text').addEventListener('input', (ev) => { q.text = ev.target.value; render(true); });
  $('#f-building').addEventListener('change', (ev) => { q.building = ev.target.value; render(true); });
  $('#f-category').addEventListener('change', (ev) => { q.category = ev.target.value; render(true); });
  $('#pane').addEventListener('click', (ev) => {
    const b = ev.target.closest('button[data-act]');
    if (!b) return;
    const act = b.dataset.act, id = q.id, t = R.find(id);
    let msg;
    if (act === 'assign') msg = A.assign(id, b.dataset.worker);
    else if (act === 'transfer') msg = A.transfer(id);
    else if (act === 'start') msg = A.start(id);
    else if (act === 'fixed') msg = A.fixed(id, $('#fixed-note').value.trim());
    else if (act === 'confirm') msg = A.confirm(id);
    else if (act === 'reopen') msg = A.reopen(id, '学生说还没修好');
    else if (act === 'cancel') { $('#cancel-what').textContent = `${t.building} ${t.room}：${t.description}。取消后要再处理只能重新录一张。`; $('#cancel-reason').value = ''; $('#cancel-dialog').showModal(); return; }
    render(true); toast(msg);
  });
  $('#pane').addEventListener('submit', (ev) => { ev.preventDefault(); const s = $('#note-text').value.trim(); if (s) { const m = A.note(q.id, s); render(true); toast(m); } });
  $('#cancel-dialog').addEventListener('close', () => { if ($('#cancel-dialog').returnValue === 'cancel') { const m = A.cancel(q.id, $('#cancel-reason').value.trim() || '没有写原因'); render(true); toast(m); } });
  $('#toast-undo').addEventListener('click', () => { if (R.undo()) { render(true); toast('已撤销'); } });
  $('#reset').addEventListener('click', () => { R.reset(); render(false); toast('已恢复示例'); });
  render(false);
})();
