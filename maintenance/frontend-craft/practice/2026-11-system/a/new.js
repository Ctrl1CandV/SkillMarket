// 新建报修：值班员一边听电话一边录。右边实时显示这张单、同宿舍有没有没完成的报修、会派给谁。
(function () {
  'use strict';
  const R = window.Repair, F = R.fmt, D = R.data, e = F.esc;
  const $ = (s) => document.querySelector(s);
  $('#now').textContent = `${F.dateLabel(R.NOW)} ${R.NOW.getHours()}:${String(R.NOW.getMinutes()).padStart(2, '0')}`;

  const PHRASES = {
    水暖: ['洗手池下面的水管漏水', '热水器不出热水', '马桶水箱一直流水', '下水堵了，水下不去', '暖气片不热'],
    电: ['整间宿舍没电，隔壁正常', '灯不亮，换过灯泡也不行', '插座没电', '空调开了不制热', '插座有焦味，已经拔了插头'],
    门窗家具: ['门锁打不开，人进不去', '阳台推拉门脱轨了，关不上', '柜门合页掉了', '床板断了一根横档', '窗户关不严'],
    网络: ['墙上的网口没信号', '无线信号很弱，经常断', '校园网登录页打不开'],
  };
  const TIMES = ['全天有人', '下午 4 点以后', '晚上 7 点以后', '来之前先打电话'];

  $('#buildings').innerHTML = D.buildings.map((b) => `<label><input type="radio" name="building" value="${e(b)}">${e(b)}</label>`).join('');
  $('#categories').innerHTML = D.categories.map((c) => `<label><input type="radio" name="category" value="${e(c)}">${e(c)}</label>`).join('');
  $('#times').innerHTML = TIMES.map((t) => `<button class="chip" type="button" data-time="${t}">${t}</button>`).join('');

  const form = $('#form');
  const val = () => {
    const f = new FormData(form);
    return { building: f.get('building') || '', room: (f.get('room') || '').trim(), category: f.get('category') || '', description: (f.get('description') || '').trim(),
      urgent: $('#urgent').checked, reporter: (f.get('reporter') || '').trim(), phone: (f.get('phone') || '').replace(/\D/g, ''), available: (f.get('available') || '').trim() };
  };
  const RULES = {
    building: (v) => Boolean(v.building),
    room: (v) => /^[1-6]\d{2}$/.test(v.room),
    category: (v) => Boolean(v.category),
    description: (v) => v.description.length >= 2,
    reporter: (v) => v.reporter.length >= 2,
    phone: (v) => v.phone.length === 11,
  };
  const touched = new Set();
  function check(name, show) {
    const v = val(), ok = RULES[name](v), box = $('#q-' + name);
    if (show) touched.add(name);
    const bad = !ok && touched.has(name);
    box.classList.toggle('bad', bad);
    box.querySelectorAll('input, textarea').forEach((el) => el.setAttribute('aria-invalid', String(bad)));
    if (name === 'phone' && bad) $('#e-phone').textContent = v.phone.length ? `手机号是 11 位数字，现在是 ${v.phone.length} 位。` : '记一下手机号，师傅上门前要联系。';
    return ok;
  }

  let urgentByHand = false;
  function slip() {
    const v = val();
    $('#phrases').innerHTML = (PHRASES[v.category] || []).map((p) => `<button class="chip" type="button" data-phrase="${e(p)}">${e(p)}</button>`).join('');
    if (!urgentByHand) {
      const hit = R.URGENT_WORDS.test(v.description);
      $('#urgent').checked = hit;
      $('#urgent-why').textContent = hit ? '内容里提到了漏水、断电、焦味或进不去屋，已经帮你勾上；不是的话取消掉。' : '漏水、断电、有焦味、人进不去屋，都算紧急。';
    }
    const urgent = $('#urgent').checked;
    let html = '<div class="slip">';
    html += `<p class="bld">${e(v.building) || '还没选楼栋'}</p><p class="room">${e(v.room) || '—'}</p>`;
    html += `<p>${urgent ? '<span class="tag-hot">急</span>' : ''}${e(v.description) || '<span style="color:var(--ink3)">还没记内容</span>'}</p>`;
    const meta = [v.category, v.reporter, v.available].filter(Boolean).map(e).join(' · ');
    if (meta) html += `<p style="font-size:0.8125rem;color:var(--ink3)">${meta}</p>`;
    html += '</div>';
    const same = v.building && RULES.room(v) ? R.tickets.filter((t) => t.building === v.building && t.room === v.room && R.OPEN.includes(t.status)) : [];
    if (same.length) {
      html += `<div class="dup"><strong>这间宿舍还有 ${same.length} 张没完成的报修</strong>，先问问是不是同一件事。` +
        same.map((t) => `<a href="ticket.html?id=${encodeURIComponent(t.id)}">${F.when(t.created)} · ${e(t.description)}（${t.status}）</a>`).join('') + '</div>';
    }
    if (v.category === '网络') {
      html += '<div class="who"><h2>保存以后</h2><p style="margin-top:0.5rem">网络问题不派师傅，转给信息中心（8800-1234）。</p></div>';
    } else if (v.category) {
      const fake = { category: v.category, description: v.description, building: v.building };
      html += `<div class="who"><h2>能接这张单的师傅</h2><ul>${R.candidates(fake).map((c) => `<li><span>${c.worker.name}${c.aircon ? '（会修空调）' : ''}</span><span class="num">手上 ${c.load} 张</span></li>`).join('')}</ul></div>`;
    }
    $('#slip').innerHTML = html;
  }

  form.addEventListener('input', (ev) => {
    const name = ev.target.name;
    if (name === 'room') ev.target.value = ev.target.value.replace(/\D/g, '');
    if (RULES[name]) check(name, false);
    slip();
  });
  form.addEventListener('change', (ev) => {
    if (ev.target.id === 'urgent') urgentByHand = true;
    if (ev.target.name === 'building' || ev.target.name === 'category') check(ev.target.name, true);
    slip();
  });
  form.addEventListener('focusout', (ev) => {
    const name = ev.target.name;
    if (RULES[name] && ev.target.type !== 'radio') check(name, true);
  });
  form.addEventListener('click', (ev) => {
    const p = ev.target.closest('[data-phrase]'), t = ev.target.closest('[data-time]');
    if (p) { $('#description').value = p.dataset.phrase; check('description', false); slip(); $('#description').focus(); }
    if (t) { $('#available').value = t.dataset.time; slip(); }
  });
  form.addEventListener('submit', (ev) => {
    ev.preventDefault();
    const bad = Object.keys(RULES).filter((name) => !check(name, true));
    if (bad.length) {
      const first = $('#q-' + bad[0]).querySelector('input, textarea');
      first.focus();
      return;
    }
    const v = val();
    v.phone = v.phone.replace(/(\d{3})(\d{4})(\d{4})/, '$1-$2-$3');
    const t = R.actions.create(v);
    location.href = `ticket.html?id=${encodeURIComponent(t.id)}`;
  });
  slip();
  const first = form.querySelector('input[name="building"]');
  if (first) first.focus();
})();
