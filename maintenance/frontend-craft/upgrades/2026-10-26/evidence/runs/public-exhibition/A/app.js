(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const KEY = 'unfinished-routes-exhibition-A-v1';
  let data, reservations = [], currentWork = 0, viewerOrigin, savedScroll = 0, submitting = false;
  const escape = (text) => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const artist = id => data.artists.find(a => a.id === id);
  const remaining = slot => Math.max(0, slot.remaining - reservations.filter(r => r.slot_id === slot.id).reduce((sum, r) => sum + r.party_size, 0));
  const date = slot => {
    const d = new Date(slot.start_at), end = new Date(slot.end_at);
    const parts = new Intl.DateTimeFormat('zh-CN', {timeZone:data.time_zone,month:'numeric',day:'numeric'}).formatToParts(d);
    return { day: `${parts.find(p=>p.type==='month').value}月${parts.find(p=>p.type==='day').value}日`, week: new Intl.DateTimeFormat('zh-CN',{timeZone:data.time_zone,weekday:'short'}).format(d), time: [d,end].map(v => new Intl.DateTimeFormat('zh-CN',{timeZone:data.time_zone,hour:'2-digit',minute:'2-digit',hour12:false}).format(v)).join('—') };
  };
  function readReservations() {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) throw new Error('invalid storage');
    const used = new Map();
    const valid = parsed.every(r => {
      const slot = data.visit_slots.find(s => s.id === r.slot_id);
      if (!slot || typeof r.visitor_name !== 'string' || !r.visitor_name.trim() || [...r.visitor_name].length > 30 || !Number.isInteger(r.party_size) || r.party_size < 1 || r.party_size > 4 || typeof r.id !== 'string' || !Number.isFinite(Date.parse(r.created_at))) return false;
      used.set(slot.id, (used.get(slot.id) || 0) + r.party_size);
      return used.get(slot.id) <= slot.remaining;
    });
    if (!valid) throw new Error('invalid storage');
    return parsed;
  }
  function showStorageError() { $('#storage-alert').textContent = '无法读取或保存本地演示数据。请允许浏览器本地存储，或使用“恢复演示数据”重试。'; }
  function renderWorks() {
    $('#curatorial').innerHTML = data.exhibition.curatorial_text.map(p => `<p>${escape(p)}</p>`).join('');
    $('#work-grid').innerHTML = data.works.map((w,i) => `<article class="work-card" id="${w.id}"><button class="art-button" data-work="${i}" aria-label="放大作品：${escape(w.title)}"><img src="images/${w.id}.svg" width="${w.image.width}" height="${w.image.height}" alt="${escape(w.image.alt)}" loading="lazy"><span class="image-action">放大 ↗</span></button><div class="work-caption"><span class="work-number">${String(i+1).padStart(2,'0')}</span><div class="work-info"><h3>${escape(w.title)}</h3><p class="meta">${escape(artist(w.artist_id).name)} · ${w.year}<br>${escape(w.medium)} / ${escape(w.dimensions)}</p><p class="description">${escape(w.description)}</p></div></div></article>`).join('');
    $('#artist-grid').innerHTML = data.artists.map(a => `<article><h3>${escape(a.name)}</h3><small>${escape(a.english_name)}</small><p>${escape(a.bio)}</p></article>`).join('');
    document.querySelectorAll('[data-work]').forEach(button => button.addEventListener('click', () => openWork(Number(button.dataset.work),button)));
  }
  function updateViewer() {
    const w = data.works[currentWork];
    $('#viewer-count').textContent = `作品 ${String(currentWork+1).padStart(2,'0')} / ${String(data.works.length).padStart(2,'0')}`;
    $('#viewer-img').src = `images/${w.id}.svg`;
    $('#viewer-img').alt = w.image.alt;
    $('#viewer-title').textContent = w.title;
    $('#viewer-series').textContent = `系列 / ${w.series}`;
    $('#viewer-meta').textContent = `${artist(w.artist_id).name} · ${w.year} · ${w.medium} · ${w.dimensions}`;
    $('#viewer-text').textContent = w.description;
    $('#viewer-prev').disabled = currentWork === 0;
    $('#viewer-next').disabled = currentWork === data.works.length - 1;
    $('#viewer').scrollTop = 0;
  }
  function openWork(index, origin) {
    currentWork=index;viewerOrigin=origin;savedScroll=window.scrollY;
    updateViewer();document.body.classList.add('modal-open');$('#viewer').showModal();$('#viewer-close').focus();
  }
  function moveWork(delta) {
    const next = currentWork + delta;
    if (next < 0 || next >= data.works.length) return;
    currentWork=next;updateViewer();
  }
  function renderSlots() {
    const selected = document.querySelector('input[name="slot_id"]:checked')?.value;
    $('#slots').innerHTML = data.visit_slots.map(s => {
      const d=date(s), left=remaining(s);
      return `<label class="slot"><input type="radio" name="slot_id" value="${s.id}" ${selected === s.id ? 'checked' : ''} ${left === 0 ? 'disabled' : ''} aria-describedby="slot-error"><span class="slot-main"><span class="slot-date">${d.day}<small>${d.week}</small></span><span class="slot-time">${d.time}</span></span><span class="slot-left">${left ? `余 <b>${left}</b> 位` : '已满场'}</span></label>`;
    }).join('');
    $('#slots').querySelectorAll('input').forEach(input => input.addEventListener('change', () => {$('#slot-error').textContent='';$('#party-error').textContent='';}));
  }
  function renderHistory() {
    $('#history').hidden = reservations.length === 0;
    $('#history-count').textContent = `（${reservations.length}）`;
    $('#history-list').innerHTML = [...reservations].reverse().map(r => {
      const d=date(data.visit_slots.find(s=>s.id===r.slot_id));
      return `<div class="history-item">${escape(r.visitor_name)} · ${r.party_size} 人 · ${d.day} ${d.time}<span>${escape(r.id)} · 本地演示预约</span></div>`;
    }).join('');
  }
  function showConfirmation(r) {
    const d=date(data.visit_slots.find(s=>s.id===r.slot_id));
    const time=new Intl.DateTimeFormat('zh-CN',{timeZone:data.time_zone,month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(r.created_at));
    $('#confirmation').innerHTML=`<span class="receipt-id">${escape(r.id)}</span><h3>演示预约已保存 ✓</h3><p>${escape(r.visitor_name)}，已为你记下这次来访。</p><p>2026 年 ${d.day}（${d.week}） ${d.time}</p><p>${r.party_size} 人 · 河岸艺术空间（虚构场地）</p><p class="receipt-notice">${escape(data.reservation_rules.confirmation_notice)}<br>保存时间：${time}（北京时间）</p>`;
    $('#confirmation').hidden=false;
  }
  function clearErrors() { ['slot','name','party'].forEach(id => $(`#${id}-error`).textContent='');['#visitor-name','#party-size'].forEach(id=>$(id).removeAttribute('aria-invalid')); }
  async function submitBooking(event) {
    event.preventDefault();if(submitting)return;submitting=true;
    const submit=$('.submit');submit.disabled=true;clearErrors();
    const process = () => {
      try { reservations=readReservations(); } catch {showStorageError();return;}
      const name=$('#visitor-name').value.trim();const input=$('#party-size').value;const count=Number(input);
      const slotId=document.querySelector('input[name="slot_id"]:checked')?.value;
      const slot=data.visit_slots.find(s=>s.id===slotId);let firstInvalid=null;
      if(!slot){$('#slot-error').textContent='请先选择一个有余量的参观场次。';firstInvalid=$('#slots input:not(:disabled)');}
      if(!name || [...name].length>30){$('#name-error').textContent='请输入 1—30 字的称呼。';$('#visitor-name').setAttribute('aria-invalid','true');firstInvalid ||= $('#visitor-name');}
      if(!input || !Number.isInteger(count) || count<1 || count>4){$('#party-error').textContent='人数须为 1—4 的整数，包含你本人。';$('#party-size').setAttribute('aria-invalid','true');firstInvalid ||= $('#party-size');}
      else if(slot && count>remaining(slot)){$('#party-error').textContent=remaining(slot)===0?'这个场次已经满了，请选择其他场次。':`这个场次仅余 ${remaining(slot)} 位，请减少人数或选择其他场次。`;firstInvalid ||= $('#party-size');}
      if(firstInvalid){renderSlots();if(firstInvalid.isConnected) firstInvalid.focus();else $('#slots input:not(:disabled)')?.focus();return;}
      const r={id:`UR-${crypto.randomUUID().slice(0,8).toUpperCase()}`,visitor_name:name,party_size:count,slot_id:slot.id,created_at:new Date().toISOString()};
      const next=[...reservations,r];
      try {localStorage.setItem(KEY,JSON.stringify(next));}catch{showStorageError();return;}
      reservations=next;$('#storage-alert').textContent='';$('#visitor-name').value=name;renderSlots();renderHistory();showConfirmation(r);$('#confirmation').focus();
    };
    try { if(navigator.locks) await navigator.locks.request(KEY,process);else process(); } finally {submitting=false;submit.disabled=false;}
  }
  async function resetDemo() {
    const reset=()=>{try{localStorage.removeItem(KEY);reservations=[];$('#booking-form').reset();clearErrors();renderSlots();renderHistory();$('#confirmation').hidden=true;$('#storage-alert').textContent='已恢复原始场次余量，演示预约已清除。';$('#reset-dialog').close();}catch{showStorageError();$('#reset-dialog').close();}};
    if(navigator.locks) await navigator.locks.request(KEY,reset);else reset();
  }
  async function init() {
    try {const response=await fetch('data.json');if(!response.ok)throw new Error('data loading');data=await response.json();renderWorks();}
    catch{$('#curatorial').innerHTML='<p>展览资料暂时无法加载。请通过本地 HTTP 服务打开此页面，并刷新重试。</p>';$('.submit').disabled=true;return;}
    try {reservations=readReservations();}catch{showStorageError();}
    renderSlots();renderHistory();if(reservations.length)showConfirmation(reservations.at(-1));
    $('#booking-form').addEventListener('submit',submitBooking);
    $('#viewer-close').addEventListener('click',()=>$('#viewer').close());
    $('#viewer').addEventListener('close',()=>{document.body.classList.remove('modal-open');window.scrollTo({top:savedScroll,behavior:'instant'});viewerOrigin?.focus({preventScroll:true});});
    $('#viewer-prev').addEventListener('click',()=>moveWork(-1));$('#viewer-next').addEventListener('click',()=>moveWork(1));
    $('#viewer').addEventListener('keydown',e=>{if(e.key==='ArrowLeft'){e.preventDefault();moveWork(-1);}if(e.key==='ArrowRight'){e.preventDefault();moveWork(1);}});
    $('#reset-open').addEventListener('click',()=>$('#reset-dialog').showModal());$('#reset-cancel').addEventListener('click',()=>$('#reset-dialog').close());$('#reset-confirm').addEventListener('click',resetDemo);
    window.addEventListener('storage',e=>{if(e.key===KEY){try{reservations=readReservations();renderSlots();renderHistory();if(reservations.length)showConfirmation(reservations.at(-1));else $('#confirmation').hidden=true;}catch{showStorageError();}}});
  }
  init();
})();
