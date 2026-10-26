'use strict';
const $ = (selector) => document.querySelector(selector);
const STORAGE_KEY = 'unfinished-routes-public-exhibition-b-v1';
let data, state, selectedSlot = '', activeWork = 0, returnFocus, returnScroll = 0;
const escapeHTML = (value) => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const artistFor = (work) => data.artists.find(a => a.id === work.artist_id);
const imageURL = (work) => 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(work.image.svg);
const slotFor = (id) => data.visit_slots.find(s => s.id === id);
const dateText = (slot) => new Intl.DateTimeFormat('zh-CN', {timeZone: data.time_zone, month:'long', day:'numeric', weekday:'long'}).format(new Date(slot.start_at));
const timeText = (slot) => [slot.start_at, slot.end_at].map(value => new Intl.DateTimeFormat('zh-CN', {timeZone:data.time_zone,hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(value))).join('—');
const freshState = () => ({version:1,reservations:[]});
function readState() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return freshState();
  const parsed = JSON.parse(raw);
  if (parsed.version !== 1 || !Array.isArray(parsed.reservations)) throw new Error('invalid storage');
  const total = {};
  for (const r of parsed.reservations) {
    const slot=slotFor(r.slotId);
    if (!slot || typeof r.name!=='string' || !r.name.trim() || [...r.name].length>30 || !Number.isInteger(r.partySize) || r.partySize<1 || r.partySize>4 || typeof r.id!=='string' || typeof r.createdAt!=='string') throw new Error('invalid reservation');
    total[r.slotId]=(total[r.slotId]||0)+r.partySize;
    if (total[r.slotId]>slot.remaining) throw new Error('invalid capacity');
  }
  return parsed;
}
function remaining(id) {return slotFor(id).remaining-state.reservations.filter(r=>r.slotId===id).reduce((sum,r)=>sum+r.partySize,0);}
function buildWorks() {
  $('#hero-image').src=imageURL(data.works[0]); $('#hero-image').alt=data.works[0].image.alt;
  $('#hero-open').addEventListener('click',()=>openWork(0));
  $('#curatorial-text').innerHTML=data.exhibition.curatorial_text.map(t=>`<p>${escapeHTML(t)}</p>`).join('');
  $('#opening-hours').textContent=data.exhibition.opening_hours;
  $('#venue').textContent=data.exhibition.venue; $('#address').textContent=data.exhibition.address;
  $('#work-grid').innerHTML=data.works.map((work,index)=>`<article class="work ${work.image.height>work.image.width?'portrait':''}" id="${work.id}"><div class="work-image"><button class="art-button" type="button" data-open-work="${index}" aria-label="放大观看：${escapeHTML(work.title)}"><img src="${imageURL(work)}" alt="${escapeHTML(work.image.alt)}" width="${work.image.width}" height="${work.image.height}" loading="lazy"><span class="image-open" aria-hidden="true">↗</span></button></div><div class="work-heading"><span class="work-number">${String(index+1).padStart(2,'0')}</span><div><h3>${escapeHTML(work.title)}</h3><p class="work-meta">${escapeHTML(artistFor(work).name)} / ${work.year}<br>${escapeHTML(work.medium)} · ${escapeHTML(work.dimensions)}</p><p class="work-description">${escapeHTML(work.description)}</p><button class="work-detail" type="button" data-open-work="${index}" aria-label="查看${escapeHTML(work.title)}的作品及艺术家详情">作品与艺术家 ↗</button></div></div></article>`).join('');
  document.querySelectorAll('[data-open-work]').forEach(button=>button.addEventListener('click',()=>openWork(Number(button.dataset.openWork))));
  $('#artist-grid').innerHTML=data.artists.map(a=>`<article class="artist"><h3>${escapeHTML(a.name)}</h3><p class="english-name">${escapeHTML(a.english_name)}</p><p class="bio">${escapeHTML(a.bio)}</p></article>`).join('');
}
function showWork(index) {
  activeWork=index;
  const work=data.works[index],artist=artistFor(work);
  $('#lightbox-image').src=imageURL(work); $('#lightbox-image').alt=work.image.alt;
  $('#lightbox-title').textContent=work.title;
  $('#lightbox-counter').textContent=`${String(index+1).padStart(2,'0')} / 08`;
  $('#lightbox-series').textContent=`${work.series} / ${work.year}`;
  $('#lightbox-meta').textContent=`${artist.name} · ${work.medium} · ${work.dimensions}`;
  $('#lightbox-description').textContent=work.description;
  $('#lightbox-artist-name').textContent=`${artist.name} / ${artist.english_name}`;
  $('#lightbox-bio').textContent=artist.bio;
  $('#lightbox-provenance').textContent=work.image.provenance;
  $('#previous-work').disabled=index===0; $('#next-work').disabled=index===data.works.length-1;
  $('#lightbox-stage').classList.remove('zoomed');$('#zoom-button').textContent='放大 +';$('#zoom-button').setAttribute('aria-pressed','false');
  $('#lightbox').scrollTop=0;
}
function openWork(index) {
  returnFocus=document.activeElement;returnScroll=window.scrollY;
  showWork(index);$('#lightbox').showModal();document.body.style.overflow='hidden';$('#close-lightbox').focus();
}
function closeWork() {$('#lightbox').close();}
$('#close-lightbox').addEventListener('click',closeWork);
$('#lightbox').addEventListener('close',()=>{document.body.style.overflow='';window.scrollTo({top:returnScroll,behavior:'instant'});returnFocus?.focus({preventScroll:true});});
$('#previous-work').addEventListener('click',()=>{if(activeWork>0)showWork(activeWork-1);});
$('#next-work').addEventListener('click',()=>{if(activeWork<data.works.length-1)showWork(activeWork+1);});
$('#lightbox').addEventListener('keydown',e=>{if(e.key==='ArrowLeft'&&activeWork>0){e.preventDefault();showWork(activeWork-1);}if(e.key==='ArrowRight'&&activeWork<data.works.length-1){e.preventDefault();showWork(activeWork+1);}});
$('#zoom-button').addEventListener('click',()=>{const zoomed=$('#lightbox-stage').classList.toggle('zoomed');$('#zoom-button').setAttribute('aria-pressed',String(zoomed));$('#zoom-button').textContent=zoomed?'适合画面 −':'放大 +';});
function renderSlots() {
  $('#slot-list').innerHTML='<legend class="sr-only">参观场次</legend>'+data.visit_slots.map(slot=>{const count=remaining(slot.id);return `<label class="slot-option"><input type="radio" name="slot" value="${slot.id}" ${selectedSlot===slot.id?'checked':''} ${count===0?'disabled':''} aria-label="${dateText(slot)} ${timeText(slot)}，${count===0?'已满场':`剩余 ${count} 人`}，总名额 ${slot.capacity} 人"><span class="slot-date">${dateText(slot)}<span class="slot-time">${timeText(slot)}</span></span><span class="availability ${count===0?'full':count<=3?'low':''}">${count===0?'已满场':`余 ${count} 人`}</span></label>`;}).join('');
  $('#slot-list').querySelectorAll('input').forEach(input=>input.addEventListener('change',()=>{selectedSlot=input.value;updateSelection();$('#slot-error').textContent='';$('#party-error').textContent='';$('#party-size').removeAttribute('aria-invalid');}));
  updateSelection();
}
function updateSelection() {
  const slot=slotFor(selectedSlot),count=slot?remaining(slot.id):0;
  $('#selection-summary').textContent=slot?`${dateText(slot)} ${timeText(slot)} · ${count===0?'已满场，请重新选择':`余 ${count} 人`}`:'请先从场次列表中选择时间。';
  $('#book-button').disabled=!!slot&&count===0;
  $('#book-button').innerHTML=slot&&count===0?'该场次已满，请选择其他场次':'完成演示预约 <span aria-hidden="true">↗</span>';
}
function renderReservations() {
  $('#reservation-count').textContent=state.reservations.length;
  $('#reservation-list').innerHTML=state.reservations.length?state.reservations.slice().reverse().map(r=>{const slot=slotFor(r.slotId);return `<article class="reservation-item"><div><p>${dateText(slot)} ${timeText(slot)}</p><p class="reservation-code">${escapeHTML(r.id)} · 本地演示</p></div><p>${escapeHTML(r.name)} · ${r.partySize} 人</p></article>`;}).join(''):'<p class="empty-reservation">还没有演示预约。选择一个时间，开始安排这次参观。</p>';
}
function clearErrors(){['slot','name','party','storage'].forEach(id=>$('#'+id+'-error').textContent='');$('#visitor-name').removeAttribute('aria-invalid');$('#party-size').removeAttribute('aria-invalid');}
$('#booking-form').addEventListener('submit',async e=>{
  e.preventDefault();clearErrors();
  const name=$('#visitor-name').value.trim(),size=Number($('#party-size').value),slot=slotFor(selectedSlot);
  let firstInvalid;
  if(!slot){$('#slot-error').textContent='请选择一个可预约的参观场次。';firstInvalid=$('#slot-list input:not(:disabled)');}
  if(!name||[...name].length>30){$('#name-error').textContent=!name?'请填写称呼，不能只输入空格。':'称呼最多 30 个字符，请稍作缩短。';$('#visitor-name').setAttribute('aria-invalid','true');firstInvalid||=$('#visitor-name');}
  if(!Number.isInteger(size)||size<1||size>4){$('#party-error').textContent='人数须为 1—4 之间的整数。';$('#party-size').setAttribute('aria-invalid','true');firstInvalid||=$('#party-size');}
  if(firstInvalid){firstInvalid.focus();return;}
  const commit=()=>{
    let latest;
    try{latest=readState();}catch{ $('#storage-error').textContent='无法读取本地预约，请先恢复演示数据后重试。';return;}
    state=latest;
    const count=remaining(selectedSlot);
    if(size>count){renderSlots();$('#party-error').textContent=count===0?'这个场次已经满场，请选择其他时间。':`这个场次仅剩 ${count} 个名额，请减少人数或换个时间。`;$('#party-size').setAttribute('aria-invalid','true');$('#party-size').focus();return;}
    const createdAt=new Date().toISOString(),id='UR-'+Date.now().toString(36).toUpperCase()+'-'+Math.random().toString(36).slice(2,6).toUpperCase();
    const reservation={id,name,partySize:size,slotId:selectedSlot,createdAt};
    const next={version:1,reservations:[...state.reservations,reservation]};
    try{localStorage.setItem(STORAGE_KEY,JSON.stringify(next));}catch{ $('#storage-error').textContent='浏览器未能保存预约。请允许本地存储后重试，余量尚未扣减。';return;}
    state=next;renderSlots();renderReservations();
    const result=$('#booking-result');result.hidden=false;result.innerHTML=`<h4 class="success-label">✓ 演示预约已保存</h4><p>${escapeHTML(name)} · ${size} 人<br>${dateText(slot)} ${timeText(slot)}</p><p class="result-code">预约编号 ${id}</p><p>${escapeHTML(data.reservation_rules.confirmation_notice)}</p>`;result.focus({preventScroll:true});result.scrollIntoView({behavior:'smooth',block:'nearest'});
  };
  $('#book-button').disabled=true;
  try{if(navigator.locks) await navigator.locks.request(STORAGE_KEY,commit);else commit();}finally{updateSelection();}
});
window.addEventListener('storage',e=>{if(e.key===STORAGE_KEY&&data){try{state=readState();renderSlots();renderReservations();}catch{$('#storage-error').textContent='其他页面的本地数据无法读取，请恢复演示数据。';}}});
$('#reset-button').addEventListener('click',()=>$('#reset-dialog').showModal());
$('#cancel-reset').addEventListener('click',()=>$('#reset-dialog').close());
$('#confirm-reset').addEventListener('click',()=>{
  try{localStorage.removeItem(STORAGE_KEY);}catch{$('#storage-error').textContent='浏览器未能恢复本地数据，请检查存储权限。';$('#reset-dialog').close();return;}
  state=freshState();selectedSlot='';$('#booking-form').reset();clearErrors();$('#booking-result').hidden=true;$('#booking-result').innerHTML='';renderSlots();renderReservations();$('#reset-dialog').close();$('#reset-status').textContent='已恢复原始场次余量，演示预约已清除。';
});
async function init(){
  try{const response=await fetch('data.json');if(!response.ok)throw new Error('data fetch');data=await response.json();buildWorks();try{state=readState();}catch{state=freshState();$('#storage-error').textContent='本地预约数据暂时无法读取。提交前请先使用“恢复演示数据”。';}renderSlots();renderReservations();}
  catch(error){$('#work-grid').innerHTML='<p>未能加载展览资料，请通过本地 HTTP 服务打开此页面并刷新。</p>';$('#book-button').disabled=true;console.error(error);}
}
init();
