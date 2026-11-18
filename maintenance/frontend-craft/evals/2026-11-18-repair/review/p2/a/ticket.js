// 工单详情：左边是这张单的内容和经过，右边只放“下一步该做什么”。
(function () {
  'use strict';
  const R = window.Repair, F = R.fmt, D = R.data, e = F.esc, A = R.actions;
  const $ = (s) => document.querySelector(s);
  const id = new URLSearchParams(location.search).get('id');
  $('#now').textContent = `${F.dateLabel(R.NOW)} ${R.NOW.getHours()}:${String(R.NOW.getMinutes()).padStart(2, '0')}`;

  function pickList(t, list) {
    return `<div class="pick">${list.map((c) => {
      const why = [];
      if (c.aircon) why.push('会修空调');
      if (c.nearby) why.push(`手上有 ${c.nearby} 张也在${t.building}`);
      if (!c.load) why.push('手上没有活');
      const cur = t.worker === c.worker.id;
      return `<button type="button" data-act="assign" data-worker="${c.worker.id}" class="${cur ? 'current' : ''}" ${cur ? 'disabled' : ''}>
        <span class="n">${c.worker.name}${cur ? '（现在是他）' : ''}</span><span class="load">手上 ${c.load} 张</span>
        <span class="why">${c.worker.trade}${why.length ? ' · ' + why.join(' · ') : ''}</span></button>`;
    }).join('')}</div>`;
  }
  const others = (t) => D.workers.filter((w) => w.trade !== R.TRADE[t.category]).map((w) => ({ worker: w, load: R.inHand(w.id).length, aircon: false, nearby: 0 }));

  function nextPanel(t, v) {
    const w = R.worker(t.worker);
    const more = '<div class="more"><button class="linkbtn" type="button" data-act="cancel">取消这张工单</button></div>';
    if (t.status === '待派单') {
      if (t.category === '网络') {
        return `<h2>下一步</h2><p class="lead">网络问题不派师傅，转给信息中心</p>
          <div class="stack"><button class="btn primary big" type="button" data-act="transfer">转交信息中心</button></div>
          <details><summary>还是要派给师傅</summary>${pickList(t, others(t))}</details>${more}`;
      }
      const lead = '<p class="lead">派给谁？</p>';
      return `<h2>下一步</h2>${lead}${pickList(t, R.candidates(t))}
        <details><summary>其他工种的师傅</summary>${pickList(t, others(t))}</details>${more}`;
    }
    if (t.status === '已派单') {
      return `<h2>下一步</h2><p class="lead">等${w.name}上门。他到了以后记一下</p>
        <div class="stack"><button class="btn primary big" type="button" data-act="start">${w.name}已经开始处理</button>
        <a class="btn quiet" href="tel:${w.phone.replace(/-/g, '')}">打给${w.name} <span class="num">${w.phone}</span></a></div>
        <details><summary>改派给别人</summary>${pickList(t, R.candidates(t).concat(others(t)))}</details>${more}`;
    }
    if (t.status === '处理中') {
      return `<h2>下一步</h2><p class="lead">${w.name}修好以后记一下</p>
        <form id="fixed-form"><label for="fixed-note">怎么修的（师傅说的，可以不填）</label>
        <textarea id="fixed-note" rows="2" autocomplete="off"></textarea>
        <div class="stack" style="margin-top:0.5rem"><button class="btn primary big" type="submit">记为修好</button>
        <a class="btn quiet" href="tel:${w.phone.replace(/-/g, '')}">打给${w.name} <span class="num">${w.phone}</span></a></div></form>
        <details><summary>改派给别人</summary>${pickList(t, R.candidates(t).concat(others(t)))}</details>${more}`;
    }
    if (t.status === '待确认') {
      return `<h2>下一步</h2><p class="lead">${w.name}说修好了，问一下学生</p>
        <div class="stack"><a class="btn quiet" href="tel:${t.phone.replace(/-/g, '')}">打给${e(t.reporter)} <span class="num">${e(t.phone)}</span></a>
        <button class="btn primary big" type="button" data-act="confirm">学生确认修好了</button>
        <button class="btn" type="button" data-act="reopen">学生说没修好，退回给${w.name}</button></div>`;
    }
    const closed = { 已完成: '这张单已经完成', 已取消: '这张单已经取消', 已转交: '已转给信息中心，电话 8800-1234' }[t.status];
    return `<h2>状态</h2><p class="lead" style="margin-bottom:0">${closed}</p>${v.fixMinutes !== null ? `<p style="color:var(--ink2);margin-top:0.25rem">从报修到修好用了 ${F.dur(v.fixMinutes)}</p>` : ''}`;
  }

  function render() {
    const t = R.find(id);
    if (!t) {
      $('#view').innerHTML = '<p class="empty">没有找到这张工单。可能是恢复示例数据时被清掉了。</p>';
      return;
    }
    document.title = `${t.building} ${t.room} · 报修处理台`;
    const v = R.view(t), w = R.worker(t.worker);
    let pressure = '';
    if (v.late) pressure = `<span class="hot-text">超时 ${F.dur(v.lateBy)}</span>`;
    else if (t.status === '待派单' && t.urgent) pressure = `<span class="hot-text">紧急单，还剩 ${F.dur(v.left)}</span>`;
    const open = R.OPEN.includes(t.status);
    const timeline = t.events.map((ev) => `<li><span class="at">${F.when(ev.at)}</span><span class="what">${e(ev.what)}</span><span class="note">${e(ev.note) || ''}<span class="who">${e(ev.who)}</span></span></li>`).join('');
    $('#view').innerHTML = `<div class="detail">
      <article>
        <header class="d-head">
          <h1><span class="bld">${e(t.building)}</span><span class="room">${e(t.room)}</span>${t.urgent ? '<span class="tag-hot" style="font-size:0.875rem;align-self:center">紧急</span>' : ''}</h1>
          <p class="state"><strong>${t.status}</strong>${w ? `<span>${w.name}</span>` : ''}${open ? `<span>报修后已 ${F.dur(v.waited)}</span>` : ''}${pressure}<span class="id">${e(t.id)}</span></p>
        </header>
        <p class="d-desc">${e(t.description)}</p>
        <dl class="facts">
          <dt>类别</dt><dd>${t.category}</dd>
          <dt>报修人</dt><dd>${e(t.reporter)}　<a class="tel" href="tel:${t.phone.replace(/-/g, '')}">${e(t.phone)}</a></dd>
          <dt>方便上门</dt><dd>${e(t.available) || '没有说'}</dd>
          <dt>照片</dt><dd>${t.photos ? `学生说拍了 ${t.photos} 张，需要时让他发给师傅` : '没有'}</dd>
        </dl>
        <h2 class="sec-title">处理经过</h2>
        <ol class="timeline">${timeline}</ol>
        ${open ? `<form class="note-form" id="note-form"><label class="sr" for="note-text">加一条备注</label><input class="field-inline" id="note-text" type="text" autocomplete="off" placeholder="加一条备注，比如：学生来电话催"><button class="btn" type="submit">加备注</button></form>` : ''}
      </article>
      <aside class="next" aria-label="下一步">${nextPanel(t, v)}</aside>
    </div>`;
  }

  let toastTimer;
  function toast(text) {
    $('#toast-text').textContent = text;
    $('#toast-undo').hidden = !R.canUndo;
    $('#toast').hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 8000);
  }
  function done(msg) { render(); toast(msg); const h = document.querySelector('.next .btn.primary, .next .pick button:not([disabled])'); if (h) h.focus(); }

  $('#view').addEventListener('click', (ev) => {
    const b = ev.target.closest('button[data-act]');
    if (!b) return;
    const act = b.dataset.act, t = R.find(id);
    if (act === 'assign') done(A.assign(id, b.dataset.worker));
    else if (act === 'transfer') done(A.transfer(id));
    else if (act === 'start') done(A.start(id));
    else if (act === 'confirm') done(A.confirm(id));
    else if (act === 'reopen') done(A.reopen(id, '学生说还没修好'));
    else if (act === 'cancel') {
      $('#cancel-what').textContent = `${t.building} ${t.room}：${t.description}。取消后这张单就结束了，要再处理只能重新录一张。`;
      $('#cancel-reason').value = '';
      $('#cancel-dialog').showModal();
    }
  });
  $('#view').addEventListener('submit', (ev) => {
    ev.preventDefault();
    if (ev.target.id === 'fixed-form') done(A.fixed(id, $('#fixed-note').value.trim()));
    if (ev.target.id === 'note-form') { const s = $('#note-text').value.trim(); if (s) done(A.note(id, s)); }
  });
  $('#cancel-dialog').addEventListener('close', () => {
    if ($('#cancel-dialog').returnValue === 'cancel') done(A.cancel(id, $('#cancel-reason').value.trim() || '没有写原因'));
  });
  $('#toast-undo').addEventListener('click', () => { if (R.undo()) { render(); toast('已撤销'); } });
  document.addEventListener('keydown', (ev) => {
    if (ev.key.toLowerCase() === 'n' && !ev.ctrlKey && !ev.metaKey && !ev.altKey && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) && !$('#cancel-dialog').open) location.href = 'new.html';
  });
  render();
})();
