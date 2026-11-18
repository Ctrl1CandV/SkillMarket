'use strict';
const DATA = window.CLUB_DATA;
const NOW = DATA.now;
const KEY = 'tongpin-campus-v1';
const $ = (s, root = document) => root.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function initialState() {
  const s = {activities: structuredClone(DATA.activities), mine: structuredClone(DATA.my_signups), rosters: structuredClone(DATA.rosters), queues: {}};
  for (const a of s.activities) {
    const m = s.mine.find(m => m.activity === a.id && m.status.startsWith('候补'));
    const n = Math.max(a.waitlist, m ? Number(m.status.match(/\d+/)[0]) : 0);
    s.queues[a.id] = Array.from({length:n}, (_,i) => ({unknown:true,name:'候补同学（原始资料未提供）',student_id:`unknown-${a.id}-${i}`,at:NOW,checked_in:false}));
    if(m) s.queues[a.id][Number(m.status.match(/\d+/)[0])-1] = {...DATA.me,at:m.at,note:'',checked_in:false};
    a.waitlist = n;
  }
  return s;
}
let state;
let storageOK = true;
try { state = JSON.parse(localStorage.getItem(KEY)) || initialState(); } catch { state = initialState(); storageOK = false; }
function save() {
  try {localStorage.setItem(KEY, JSON.stringify(state));} catch {storageOK = false; toast('浏览器未能保存，请允许本地存储后再操作。');}
}
const activity = id => state.activities.find(a => a.id === id);
const mine = id => state.mine.find(m => m.activity === id && m.status !== '已取消');
const isClosed = a => a.deadline <= NOW;
const isEnded = a => a.end <= NOW;
const isStarted = a => a.start <= NOW;
function status(a) {
  if(isEnded(a)) return ['已结束','closed'];
  if(isClosed(a)) return ['报名截止','closed'];
  if(a.signed >= a.capacity) return ['已满 · 可候补','wait'];
  const left = a.capacity - a.signed;
  if(left <= Math.max(5, a.capacity * .15)) return [`仅剩 ${left} 席`,'warning'];
  return ['报名中',''];
}
function badge(a) { const [s,c] = status(a); return `<span class="status ${c}">${s}</span>`; }
function md(s){const d=new Date(s);return `${d.getMonth()+1}月${d.getDate()}日`;}
function weekday(s){return '周'+'日一二三四五六'[new Date(s).getDay()];}
function time(s){return s.slice(11,16);}
function dateTime(s){return `${md(s)} ${weekday(s)} ${time(s)}`;}
function range(a){return `${md(a.start)} ${weekday(a.start)} ${time(a.start)}–${a.start.slice(0,10)===a.end.slice(0,10)?'':md(a.end)+' '}${time(a.end)}`;}
function fee(a){return a.fee ? `¥${a.fee} / 人`:'免费参加';}
let toastTimer;
function toast(text){const el=$('#toast');el.textContent=text;el.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('show'),3200);}
function confirmAction(title,text,action,label='确认',danger=false){const modal=$('#modal');modal.innerHTML=`<h2>${esc(title)}</h2><p>${esc(text)}</p><div class="modal-actions"><button class="btn secondary" id="dismiss">再想想</button><button class="btn ${danger?'danger':''}" id="confirm">${esc(label)}</button></div>`;$('#dismiss').onclick=()=>modal.close();$('#confirm').onclick=()=>{modal.close();action();};modal.showModal();}
const icons={clock:'◷',pin:'⌖'};
function art(a,hero=false){
  let type = a.club;
  let bg='#e6ebdc', ink='#56704a', content='';
  if(type==='天文社') {
    bg='#dce5dc'; ink='#405b4b';
    content=`<circle cx="283" cy="48" r="32" fill="#f1f2cf"/><circle cx="296" cy="36" r="28" fill="${bg}"/><g stroke="${ink}" stroke-width="1" opacity=".3"><circle cx="175" cy="85" r="61" fill="none"/><ellipse cx="175" cy="85" rx="97" ry="29" fill="none" transform="rotate(-28 175 85)"/></g><g fill="${ink}" opacity=".65"><path d="M65 35v10m-5-5h10M300 110v12m-6-6h12M245 20v8m-4-4h8" stroke="${ink}"/><circle cx="114" cy="28" r="2"/><circle cx="335" cy="66" r="2"/><circle cx="51" cy="106" r="1.5"/></g><g stroke="${ink}" stroke-linecap="round"><path d="m173 94-18 65m18-65 35 65m-35-65 2 68" stroke-width="4"/><path d="m144 87 76-37" stroke-width="25"/><path d="m143 87 75-36" stroke="#8b9b7c" stroke-width="17"/><path d="m212 45 8 15m-78 18 8 16" stroke-width="6"/></g><path d="M0 157Q80 135 150 158T360 149V180H0" fill="#b5c3ab"/>`;
  } else if(type==='机器人社') {
    bg='#e9e7d9';ink='#697458';
    content=`<g stroke="#b6bd9f" stroke-width="1" fill="none"><path d="M28 46h70v29h40M248 26v37h62v37h30M25 126h55v-27h30M255 147v-30h65"/><circle cx="28" cy="46" r="4"/><circle cx="340" cy="100" r="4"/><circle cx="320" cy="117" r="4"/></g><g transform="translate(126 21) rotate(-8 55 65)"><rect x="6" y="39" width="105" height="77" rx="17" fill="#788568"/><rect x="17" y="48" width="83" height="47" rx="9" fill="#d9dfc7"/><circle cx="38" cy="69" r="8" fill="#415842"/><circle cx="78" cy="69" r="8" fill="#415842"/><path d="M48 84h20" stroke="#415842" stroke-width="3"/><path d="M57 39V24" stroke="#788568" stroke-width="4"/><circle cx="57" cy="20" r="7" fill="#b9a376"/><rect x="-6" y="62" width="12" height="29" rx="5" fill="#a4ae91"/><rect x="111" y="62" width="12" height="29" rx="5" fill="#a4ae91"/><rect x="24" y="116" width="18" height="15" rx="4" fill="#8e997a"/><rect x="76" y="116" width="18" height="15" rx="4" fill="#8e997a"/></g><path d="m281 45 9-15 9 15-9 15z" fill="#c2b082"/>`;
  } else if(type==='徒步社'){
    bg='#e4e9d6';ink='#6b8050';
    content=`<circle cx="268" cy="43" r="25" fill="#d3bc83"/><path d="m30 156 104-111 69 88 45-70 112 98H0" fill="#b6c2a0"/><path d="m108 71 26-26 28 36-23-9-12 9z" fill="#eff1e4"/><path d="m124 170 91-93 90 93" fill="#879e72"/><path d="m192 101 23-24 19 24-21-8z" fill="#e4ead7"/><path d="M0 145Q75 120 148 158T360 142V180H0" fill="#6f8859"/><path d="M153 180q75-28 32-37t23-35" fill="none" stroke="#d5d8ae" stroke-width="9"/><g stroke="#4f6c45" stroke-width="4"><path d="M48 100v55m-18-9 18-35 18 35zM321 94v57m-17-12 17-35 17 35z" fill="#4f6c45"/></g>`;
  } else if(type==='摄影社') {
    bg='#e7e5d9';ink='#6d7860';
    content=`<circle cx="292" cy="40" r="26" fill="#d6c397"/><g fill="#c0c5a7"><path d="M10 152 61 67l44 85zM284 160l48-89 48 89z"/><path d="M49 163 100 86l48 77z"/></g><g transform="translate(116 31) rotate(-8 66 54)"><path d="M38 18 46 4h42l10 14" fill="#7e896d"/><rect y="18" width="140" height="95" rx="13" fill="#68775c"/><path d="M0 42h140v14H0" fill="#8b967d"/><circle cx="74" cy="66" r="39" fill="#bec6aa"/><circle cx="74" cy="66" r="29" fill="#415743"/><circle cx="74" cy="66" r="21" fill="#6c8270"/><circle cx="65" cy="57" r="8" fill="#abbcac"/><rect x="13" y="28" width="21" height="10" rx="3" fill="#d6dbbf"/><circle cx="121" cy="32" r="4" fill="#d9c28c"/></g><path d="M35 35v16m-8-8h16" stroke="#a6ac90" stroke-width="2"/>`;
  } else if(type==='读书会'||type==='辩论队') {
    bg='#e9e4d6';ink='#8d7b58';
    content=`<circle cx="280" cy="46" r="34" fill="#dfd1ac"/><g transform="translate(100 38) rotate(-7 80 50)"><path d="M75 15Q42-3 0 5v100q43-8 75 10 34-20 81-10V5Q114-4 75 15" fill="#9c9e7b"/><path d="M75 8Q42-9 5 0v96q43-8 70 10 34-20 76-10V0Q114-9 75 8" fill="#f8f3df"/><path d="M75 8v98" stroke="#b9b490"/><g stroke="#c3bda0" stroke-width="2"><path d="m17 24 45 4m-45 10 45 4m-45 10 45 4m-45 10 45 4m25-42 50-4m-50 18 50-4m-50 18 50-4m-50 18 50-4"/></g><path d="M112 0v38l10-7 10 5V-1" fill="#b68e5d"/></g><path d="M43 135q-20-37 4-63 20 38-4 63m0 0q30-26 44-17-13 24-44 17" fill="#b1b59a"/>`;
  } else if(type==='吉他社'||type==='街舞社') {
    bg='#e9ded2';ink='#96765b';
    content=`<circle cx="276" cy="53" r="33" fill="#e0c8a7"/><g transform="translate(141 11) rotate(28 30 75)"><path d="M25 71C-28 46-35 114 0 120c-22 41 48 65 65 22 31-2 45-55 7-57-7-4-14-13-17-23" fill="#af8c65"/><path d="M28 71V7h23v75" fill="#6e6c51"/><rect x="24" y="0" width="31" height="28" rx="5" fill="#59634d"/><circle cx="28" cy="104" r="17" fill="#62634a"/><path d="M24 134h28" stroke="#62634a" stroke-width="6"/><path d="M36 20v116m7-116v116" stroke="#d4c39d"/></g><g fill="#aa9471"><path d="M74 51v32c-17-4-20 14-8 14 8 0 13-5 13-13V57l20-6v25c-17-4-19 14-7 14 8 0 12-5 12-13V40zM279 117v24c-15-4-17 11-6 11 7 0 10-4 10-10v-30l15 4v-7z"/></g>`;
  } else if(type==='烘焙社') {
    bg='#eee3d3';ink='#ab8b62';
    content=`<ellipse cx="180" cy="147" rx="86" ry="13" fill="#d1c5aa"/><path d="m113 79 14 61q54 20 109-1l13-60" fill="#b19b71"/><path d="m139 89 6 47m21-45 2 50m22-50-1 50m24-50-6 46m23-49-7 45" stroke="#d5c7a4" stroke-width="4"/><path d="M112 82c-29-17-6-43 14-38-7-28 39-43 54-17 18-24 60-4 49 18 28-4 46 31 19 40-45 12-92 11-136-3" fill="#faf0d8"/><circle cx="179" cy="20" r="10" fill="#b47b58"/><path d="M180 10q6-15 17-13" stroke="#7d8e5e" fill="none" stroke-width="3"/><g fill="#c6ac81"><circle cx="65" cy="51" r="4"/><circle cx="293" cy="107" r="4"/><path d="M278 38v15m-7-8h14M62 111v15m-7-8h14" stroke="#bda57a" stroke-width="2"/></g>`;
  } else if(type==='电影社') {
    bg='#dfe5df';ink='#687e6b';
    content=`<circle cx="284" cy="45" r="30" fill="#c4cdb8"/><g transform="translate(112 31) rotate(-7 70 60)"><rect x="0" y="34" width="145" height="88" rx="7" fill="#6b7c66"/><path d="M0 34h145v22H0" fill="#dbe1c7"/><path d="m5 34 17 22m13-22 17 22m13-22 17 22m13-22 17 22m13-22 17 22" stroke="#6b7c66" stroke-width="14"/><g transform="rotate(-13 0 34)"><rect y="11" width="145" height="23" rx="3" fill="#dbe1c7"/><path d="m10 11 18 23m13-23 18 23m13-23 18 23m13-23 18 23" stroke="#6b7c66" stroke-width="14"/></g><path d="m60 72 32 16-32 16z" fill="#ccd6b9"/></g>`;
  } else if(type==='围棋社') {
    bg='#e6e5d7';ink='#7b8064';
    content=`<g transform="translate(104 17) rotate(-8 80 70)"><rect width="157" height="144" rx="6" fill="#ccb98d"/><g stroke="#a38f68" stroke-width="1"><path d="M17 10v124m21-124v124m21-124v124m21-124v124m21-124v124m21-124v124m21-124v124M10 15h138M10 36h138M10 57h138M10 78h138M10 99h138M10 120h138"/></g><g fill="#4b5947"><circle cx="59" cy="57" r="10"/><circle cx="80" cy="78" r="10"/><circle cx="38" cy="78" r="10"/></g><g fill="#f4f1db"><circle cx="80" cy="57" r="10"/><circle cx="101" cy="78" r="10"/><circle cx="59" cy="99" r="10"/></g></g>`;
  } else {
    bg='#e2e9da';ink='#70815b';content=`<circle cx="180" cy="85" r="61" fill="#c1cfaa"/><path d="m122 85 36 36 77-75" stroke="#718b5c" stroke-width="20" fill="none" stroke-linecap="round" stroke-linejoin="round"/><circle cx="65" cy="47" r="14" fill="#c7d3b6"/><circle cx="302" cy="128" r="23" fill="#d4c99e"/>`;
  }
  return `<svg viewBox="0 0 360 180" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><rect width="360" height="180" fill="${bg}"/>${content}<g fill="${ink}" opacity=".16"><circle cx="20" cy="20" r="1"/><circle cx="341" cy="158" r="1"/><path d="M17 160h20m-10-10v20M330 25h15m-7-7v15" stroke="${ink}" stroke-width=".8"/></g></svg>`;
}
function heroArt(){return `<svg class="hero-art" viewBox="0 0 330 280" aria-hidden="true"><circle cx="194" cy="140" r="105" fill="#d8e1c8"/><circle cx="194" cy="140" r="125" fill="none" stroke="#d2dcc1" stroke-dasharray="3 7"/><path d="M260 260q-3-62 27-112 34 57-2 109m-12-27q-35-26-42-5 8 29 42 25" fill="#84986c"/><path d="M270 259V191" stroke="#5b7853" stroke-width="2"/><path d="M54 250q-19-36-3-66 31 34 16 61m-2-12q27-23 39-6-9 25-34 18" fill="#acbb8e"/><g transform="translate(92 60) rotate(-11 85 90)"><rect x="6" y="8" width="170" height="193" rx="10" fill="#a2b38b" opacity=".3"/><rect width="170" height="193" rx="10" fill="#fffdf2"/><path d="M0 10Q0 0 10 0h150q10 0 10 10v36H0" fill="#607c54"/><g stroke="#344f35" stroke-width="7" stroke-linecap="round"><path d="M40-9v24M130-9v24"/></g><g fill="#dce3cc"><rect x="21" y="64" width="29" height="27" rx="5"/><rect x="70" y="64" width="29" height="27" rx="5"/><rect x="119" y="64" width="29" height="27" rx="5"/><rect x="21" y="107" width="29" height="27" rx="5"/><rect x="119" y="107" width="29" height="27" rx="5"/><rect x="21" y="150" width="29" height="27" rx="5"/><rect x="70" y="150" width="29" height="27" rx="5"/></g><rect x="66" y="102" width="37" height="36" rx="6" fill="#d2ad63"/><path d="m74 120 7 7 14-15" stroke="#fff9df" stroke-width="4" fill="none" stroke-linecap="round"/></g><g transform="translate(218 178) rotate(12)"><rect width="79" height="54" rx="9" fill="#264f3f"/><path d="m29 17 9-8 11 8" fill="#92aa7b"/><circle cx="40" cy="29" r="15" fill="#9fb389"/><circle cx="40" cy="29" r="10" fill="#41694f"/><circle cx="36" cy="25" r="4" fill="#abc196"/><rect x="9" y="11" width="13" height="7" rx="2" fill="#bed0a2"/></g><path d="M264 51v20m-10-10h20M65 108v14m-7-7h14" stroke="#7d9665" stroke-width="2"/><circle cx="296" cy="122" r="5" fill="#ba9e60"/><path d="m75 38 8-6 8 6-8 6z" fill="#acbd8c"/></svg>`;}
let filters={kind:'全部',club:'全部社团',period:'two',status:'all',search:'',sort:'open'};
function activityCard(a){
 const m=mine(a.id),left=a.capacity-a.signed;
 return `<a class="activity-card" href="#detail/${a.id}" aria-label="查看${esc(a.title)}详情"><div class="card-image">${art(a)}<span class="club-pill">${esc(a.club)}</span><span class="image-index">CAMPUS / ${a.id.slice(1)}</span></div><div class="card-body"><div class="card-topline"><span class="kind-text">${esc(a.kind)}</span>${m?`<span class="own-tag">${m.status.startsWith('候补')?esc(m.status):'已报名'}</span>`:badge(a)}</div><h3>${esc(a.title)}</h3><div class="meta"><span class="icon">◷</span>${range(a)}</div><div class="meta"><span class="icon">⌖</span>${esc(a.place)}</div><div class="occupancy"><div class="track ${left<=5?'hot':''}"><span style="width:${Math.min(100,a.signed/a.capacity*100)}%"></span></div><span>${a.signed} / ${a.capacity} 人${a.waitlist?' · 候补 '+a.waitlist:''}</span></div><div class="card-footer"><span class="fee ${a.fee?'paid':''}">${fee(a)}</span><span class="card-action">${isClosed(a)?'查看详情':left<=0?'加入候补':'查看活动'} <span>↗</span></span></div></div></a>`;
}
function nextSignup(){return state.mine.filter(m=>m.status==='已报名'&&activity(m.activity).start>NOW).sort((a,b)=>activity(a.activity).start.localeCompare(activity(b.activity).start))[0];}
function renderActivities(){
 const next=nextSignup(),a=next?activity(next.activity):null;
 $('#app').innerHTML=`<section class="hero"><div class="hero-main"><div class="eyebrow">MEET YOUR PEOPLE. FIND YOUR PASSION.</div><h1>把热爱，<br><span>排进日程。</span></h1><p>课表之外，还有一群和你同频的人。</p><div class="hero-bottom"><span><b>12</b> 个有趣社团</span><span><b>14</b> 天校园灵感</span><span>一起，去试试看 ↗</span></div>${heroArt()}</div><aside class="next-card"><div class="next-label">◷ &nbsp; 我的下一站 <span>UP NEXT</span></div><div class="next-date">${a?dateTime(a.start):'发现新的可能'}</div><h3>${a?esc(a.title):'下一场相遇，等你出发'}</h3><div class="next-place">${a?'⌖ '+esc(a.place):'去挑一场感兴趣的活动吧'}</div><a class="next-link" href="${a?'#detail/'+a.id:'#mine'}"><span>查看我的报名</span><span>→</span></a></aside></section><section><div class="section-heading"><div><h2>发现活动</h2><span class="subtitle">给平常的一天，添一点不一样</span></div><span class="date-range">▦ &nbsp; 11.18 — 12.01 · 近两周</span></div><div class="filters"><div class="filter-line"><span class="filter-label">活动类型</span><div class="kind-tabs">${['全部',...new Set(DATA.activities.map(a=>a.kind))].map(k=>`<button data-kind="${k}" class="${filters.kind===k?'selected':''}">${k}</button>`).join('')}</div></div><div class="filter-bottom"><select id="club-filter" class="field-select" aria-label="按社团筛选"><option>全部社团</option>${DATA.clubs.map(c=>`<option ${filters.club===c.name?'selected':''}>${c.name}</option>`).join('')}</select><select id="period-filter" class="field-select" aria-label="按日期筛选"><option value="two">近两周</option><option value="week">未来七天</option><option value="weekend">本周末</option><option value="all">全部日期（含往期）</option></select><select id="status-filter" class="field-select" aria-label="按报名状态筛选"><option value="all">全部状态</option><option value="open">有剩余名额</option><option value="wait">可排候补</option><option value="closed">报名已截止</option></select><div class="search-wrap"><span>⌕</span><input id="activity-search" placeholder="搜索活动、社团或关键词" aria-label="搜索活动" value="${esc(filters.search)}"></div></div></div><div class="results-bar"><span id="result-count"></span><select class="sort-select" id="sort" aria-label="活动排序"><option value="open">可报名优先 ↓</option><option value="time">按开始时间 ↑</option><option value="deadline">按截止时间 ↑</option></select></div><div class="cards" id="cards"></div><div class="results-foot">— 课表之外的精彩，不止一种 —</div></section>`;
 $('#period-filter').value=filters.period;$('#status-filter').value=filters.status;$('#sort').value=filters.sort;
 document.querySelectorAll('[data-kind]').forEach(b=>b.onclick=()=>{filters.kind=b.dataset.kind;document.querySelectorAll('[data-kind]').forEach(n=>n.classList.toggle('selected',n===b));updateCards();});
 for(const [id,key] of [['club-filter','club'],['period-filter','period'],['status-filter','status'],['sort','sort']]) $('#'+id).onchange=e=>{filters[key]=e.target.value;updateCards();};
 $('#activity-search').oninput=e=>{filters.search=e.target.value;updateCards();};
 updateCards();
}
function updateCards(){
 const f=filters;
 let arr=state.activities.filter(a=>{
  const date=a.start.slice(0,10);
  if(f.period==='two'&&(date<'2026-11-18'||date>'2026-12-01'))return false;
  if(f.period==='week'&&(date<'2026-11-18'||date>'2026-11-24'))return false;
  if(f.period==='weekend'&&(date<'2026-11-21'||date>'2026-11-22'))return false;
  if(f.kind!=='全部'&&a.kind!==f.kind)return false;
  if(f.club!=='全部社团'&&a.club!==f.club)return false;
  if(f.status==='open'&&(isClosed(a)||a.signed>=a.capacity))return false;
  if(f.status==='wait'&&(isClosed(a)||a.signed<a.capacity))return false;
  if(f.status==='closed'&&!isClosed(a))return false;
  return (a.title+a.club+a.note+a.kind).toLowerCase().includes(f.search.trim().toLowerCase());
 });
 arr.sort((a,b)=>f.sort==='deadline'?a.deadline.localeCompare(b.deadline):(f.sort==='open'?(Number(isClosed(a))-Number(isClosed(b))):0)||a.start.localeCompare(b.start));
 $('#result-count').innerHTML=`共 <b>${arr.length}</b> 场活动 <span> · ${f.period==='all'?'包含往期活动':'找到属于你的那一场'}</span>`;
 $('#cards').innerHTML=arr.length?arr.map(activityCard).join(''):`<div class="empty"><h3>暂时没有匹配的活动</h3><p>换个关键词，或看看其他社团吧。</p><br><button class="btn secondary" id="clear-filters">清除筛选</button></div>`;
 if($('#clear-filters'))$('#clear-filters').onclick=()=>{filters={kind:'全部',club:'全部社团',period:'two',status:'all',search:'',sort:'open'};renderActivities();};
}
function renderDetail(id){
 const a=activity(id);if(!a){$('#app').innerHTML='<div class="empty"><h3>没有找到这场活动</h3><a href="#activities">返回活动列表 →</a></div>';return;}
 const m=mine(id),closed=isClosed(a),left=a.capacity-a.signed,wait=left<=0;
 $('#app').innerHTML=`<a class="back" href="#activities">← 返回发现活动</a><div class="detail-layout"><article class="detail-main"><div class="detail-art">${art(a)}<span class="club-pill">${esc(a.club)} · ${esc(a.kind)}</span></div><div class="detail-content"><div class="detail-club">${esc(a.club)} 发起 ${badge(a)}</div><h1>${esc(a.title)}</h1><dl class="detail-grid"><div><dt>◷ 活动时间</dt><dd>${dateTime(a.start)}<br>至 ${dateTime(a.end)}</dd></div><div><dt>⌖ 活动地点</dt><dd>${esc(a.place)}</dd></div><div><dt>▦ 报名截止</dt><dd>${dateTime(a.deadline)}</dd></div><div><dt>◎ 活动费用</dt><dd>${fee(a)}${a.fee?'<br><small>现场向社团支付，平台不收款</small>':''}</dd></div></dl><section class="info-block"><h3>出发前，请看这里</h3><p>${esc(a.note||'暂无额外注意事项，按时到场即可。期待与你见面！')}</p></section><section class="info-block"><h3>联系社团</h3><p>${esc(a.contact)}</p></section><section class="info-block note-box">报名成功后可在「我的报名」中查看。名额已满时可排候补；有人取消后，按候补顺序自动递补。活动开始前可取消，费用事宜请联系社团。</section></div></article><aside class="signup-panel"><h2>${m?'我的参与状态':closed?'活动报名已关闭':wait?'加入候补队列':'留一个位置，给热爱'}</h2><div class="signup-fee">${a.fee?'¥'+a.fee:'免费'} <small>${a.fee?'/ 人 · 现场支付':'无需支付费用'}</small></div>${a.fee?`<p class="signup-hint">费用说明：${esc(a.note||'社团未提供具体费用明细，请报名前联系负责人确认。')}</p>`:''}<div class="capacity-line"><span>已报名 ${a.signed} / ${a.capacity} 人</span><b>${left>0?'剩余 '+left+' 席':'名额已满'}</b></div><div class="track ${left<=5?'hot':''}"><span style="width:${Math.min(100,a.signed/a.capacity*100)}%"></span></div><p class="signup-hint" style="margin-top:9px">${a.waitlist?'当前候补 '+a.waitlist+' 人 · 按顺序递补':'候补按加入顺序自动递补'}</p>${m?`<div class="success-box"><b>${esc(m.status)}</b><p>${m.status.startsWith('候补')?'递补结果会显示在「我的报名」中。':'位置已经留好，期待与你见面。'}</p></div><a class="btn" href="#mine">查看我的报名 →</a>${!isStarted(a)?'<button class="btn secondary" id="cancel-detail">取消'+(m.status.startsWith('候补')?'候补':'报名')+'</button>':'<p class="detail-done">活动已开始，不能在线取消</p>'}`:closed?`<div class="success-box"><b>${isEnded(a)?'活动已结束':'报名已截止'}</b><p>截止后不再接受报名或候补。</p></div><a class="btn secondary" href="#activities">看看其他活动 →</a>`:`<form id="signup-form"><label for="name">姓名 <span class="required">*</span></label><input id="name" name="name" required maxlength="20" autocomplete="name" value="${esc(DATA.me.name)}"><label for="student">学号 <span class="required">*</span></label><input id="student" name="student" required pattern="[0-9]{6,16}" inputmode="numeric" maxlength="16" title="请输入 6–16 位数字学号" value="${esc(DATA.me.student_id)}"><label for="phone">手机号 <span class="required">*</span></label><input id="phone" name="phone" required type="tel" pattern="1[3-9][0-9 -]{9,13}" title="请输入有效的 11 位手机号，可含空格或短横线" value="${esc(DATA.me.phone)}"><label for="note">给社团留句话 <span style="color:#9ba48d">（选填）</span></label><textarea id="note" name="note" maxlength="150" placeholder="想说的话、需要的帮助……"></textarea><label class="agreement"><input type="checkbox" required name="agree"><span>我已阅读活动时间、注意事项${a.fee?'，知晓需现场支付 ¥'+a.fee:''}${wait?'，并理解候补不代表报名成功':''}。</span></label><button class="btn" type="submit">${wait?'加入候补 · 预计第 '+(a.waitlist+1)+' 位':'确认报名'} →</button><p class="detail-done">仅用于本次活动联络，不公开个人信息</p></form>`}</aside></div>`;
 if(!m&&!closed){const jump=document.createElement('button');jump.className='mobile-signup-jump';jump.innerHTML=`<span>${fee(a)}</span><b>${wait?'前往候补':'前往报名'} ↓</b>`;jump.onclick=()=>$('.signup-panel').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});$('#app').appendChild(jump);const observer=new IntersectionObserver(entries=>{if(!jump.isConnected){observer.disconnect();return;}jump.classList.toggle('out-of-view',entries[0].isIntersecting);},{threshold:0.05});observer.observe($('.signup-panel'));}
 if($('#signup-form'))$('#signup-form').onsubmit=e=>{e.preventDefault();const form=new FormData(e.target);const phone=String(form.get('phone')).replace(/[ -]/g,'');if(!/^1[3-9]\d{9}$/.test(phone)){toast('请填写有效的 11 位手机号');return;}if(!String(form.get('name')).trim()){toast('请填写姓名');return;}const person={name:String(form.get('name')).trim(),student_id:String(form.get('student')),phone:String(form.get('phone')),note:String(form.get('note')).trim(),at:NOW,checked_in:false};signUp(a,person);};
 if($('#cancel-detail'))$('#cancel-detail').onclick=()=>cancelMine(id);
}
function signUp(a,person){
 if(mine(a.id)||isClosed(a)){toast('报名状态已变化，请重新查看');renderDetail(a.id);return;}
 // The demo has a fixed signed-in student. The form is contact information, not an account switch.
 const existing=state.rosters[a.id]?.some(r=>r.student_id===person.student_id)||state.queues[a.id].some(r=>r.student_id===person.student_id);
 if(existing){toast('这个学号已在报名或候补名单中，请勿重复提交');return;}
 const waiting=a.signed>=a.capacity;
 const record={activity:a.id,status:'已报名',at:NOW,person};
 if(waiting){state.queues[a.id].push({...person,owner:true});a.waitlist=state.queues[a.id].length;record.status=`候补第 ${a.waitlist} 位`;}else{a.signed++;if(state.rosters[a.id])state.rosters[a.id].push({...person,owner:true});}
 state.mine=state.mine.filter(m=>m.activity!==a.id);state.mine.push(record);save();refreshHeader();renderDetail(a.id);toast(waiting?'已加入候补，可在我的报名中查看顺序':'报名成功！期待与你见面');
}
function syncQueue(a){a.waitlist=state.queues[a.id].length;const m=mine(a.id);if(m?.status.startsWith('候补')){const pos=state.queues[a.id].findIndex(r=>r.owner||r.student_id===DATA.me.student_id);if(pos>=0)m.status=`候补第 ${pos+1} 位`;}}
function promote(a){
 if(a.start<=NOW)return;
 while(a.signed<a.capacity&&state.queues[a.id].length){const p=state.queues[a.id].shift();a.signed++;if(state.rosters[a.id])state.rosters[a.id].push(p);if(p.owner||p.student_id===DATA.me.student_id){const m=mine(a.id);if(m){m.status='已报名';m.promoted=true;}}}
 syncQueue(a);
}
function cancelMine(id){
 const a=activity(id),m=mine(id);if(!m||isStarted(a))return;
 const waiting=m.status.startsWith('候补');
 confirmAction(waiting?'确定退出候补吗？':'确定取消报名吗？',`「${a.title}」${waiting?'退出后将失去当前候补顺序。':'取消后名额将释放给候补同学，重新报名需按当前名额情况处理。'}${a.fee?' 已支付的费用请联系社团协商退还。':''}`,()=>{
  m.status='已取消';m.cancelled_at=NOW;
  if(waiting){state.queues[id]=state.queues[id].filter(r=>!r.owner&&r.student_id!==DATA.me.student_id&&r.student_id!==m.person?.student_id);syncQueue(a);}else{a.signed=Math.max(0,a.signed-1);if(state.rosters[id])state.rosters[id]=state.rosters[id].filter(r=>!r.owner&&r.student_id!==(m.person?.student_id||DATA.me.student_id));promote(a);}
  save();render();toast(waiting?'已退出候补队列':'已取消报名，名额已释放');
 },waiting?'确认退出':'确认取消',true);
}
let mineTab='upcoming';
function renderMine(){
 const active=state.mine.filter(m=>m.status!=='已取消'),future=active.filter(m=>!isStarted(activity(m.activity))),waiting=active.filter(m=>m.status.startsWith('候补'));
 $('#app').innerHTML=`<div class="page-head"><div><div class="page-kicker">MY CAMPUS JOURNEY</div><h1>我的报名</h1><p>林雨桐，你的每一次出发，都在这里。</p></div><a class="btn secondary" href="#activities">发现新活动 ↗</a></div><div class="stats"><div class="stat"><strong>${future.filter(m=>m.status==='已报名').length}</strong>场活动待出发</div><div class="stat"><strong>${waiting.length}</strong>场活动候补中</div><div class="stat"><strong>${active.filter(m=>isEnded(activity(m.activity))).length}</strong>场活动已结束</div></div><div class="list-tabs">${[['upcoming','待参加'],['waiting','候补中'],['past','已结束'],['all','全部记录']].map(([v,t])=>`<button class="${mineTab===v?'selected':''}" data-mine-tab="${v}">${t}</button>`).join('')}</div><div class="signup-list" id="signup-list"></div>`;
 document.querySelectorAll('[data-mine-tab]').forEach(b=>b.onclick=()=>{mineTab=b.dataset.mineTab;renderMine();});
 let arr=state.mine.filter(m=>mineTab==='all'||(m.status!=='已取消'&&(mineTab==='waiting'?m.status.startsWith('候补'):mineTab==='past'?isEnded(activity(m.activity)):!isEnded(activity(m.activity))&&!m.status.startsWith('候补'))));
 arr.sort((x,y)=>activity(x.activity).start.localeCompare(activity(y.activity).start));
 $('#signup-list').innerHTML=arr.length?arr.map(m=>{const a=activity(m.activity),cancelled=m.status==='已取消';return `<article class="signup-item ${cancelled?'cancelled':''}"><a class="signup-thumb" href="#detail/${a.id}" aria-label="${esc(a.title)}详情">${art(a)}</a><div class="signup-info"><div class="detail-club">${esc(a.club)} <span class="own-tag">${cancelled?'已取消':m.status.startsWith('候补')?esc(m.status):isEnded(a)?'已结束':isStarted(a)?'进行中':'已报名'}${m.promoted?' · 候补已递补':''}</span></div><a href="#detail/${a.id}"><h3>${esc(a.title)}</h3></a><div class="meta">◷ &nbsp; ${range(a)}</div><div class="meta">⌖ &nbsp; ${esc(a.place)} &nbsp; · &nbsp; ${fee(a)}</div></div><div class="signup-actions"><small>${m.status.startsWith('候补')?'名额释放后自动递补':cancelled?'名额已释放':isEnded(a)?'感谢你的参与':'记得提前安排好时间'}</small><a class="btn secondary small" href="#detail/${a.id}">查看详情 ↗</a>${!cancelled&&!isStarted(a)?`<button class="text-button" data-cancel="${a.id}">${m.status.startsWith('候补')?'退出候补':'取消报名'}</button>`:''}</div></article>`;}).join(''):`<div class="empty"><h3>${mineTab==='waiting'?'目前没有候补中的活动':'这里还没有活动'}</h3><p>去发现一些新鲜事，下一次相遇就在路上。</p><br><a href="#activities" class="btn secondary">去发现活动 →</a></div>`;
 document.querySelectorAll('[data-cancel]').forEach(b=>b.onclick=()=>cancelMine(b.dataset.cancel));
}
let adminId='A01',rosterSearch='',rosterMode='all';
function renderAdmin(){
 const acts=state.activities.filter(a=>a.club===DATA.manager_of);const a=activity(adminId)||acts[0];adminId=a.id;
 const rows=state.rosters[a.id]||[],checked=rows.filter(r=>r.checked_in).length;
 $('#app').innerHTML=`<div class="page-head"><div><div class="page-kicker">CLUB WORKSPACE / PHOTOGRAPHY</div><h1>摄影社工作台</h1><p>把琐事留在这里，把时间留给热爱。</p></div><span class="date-range">● &nbsp; 摄影社负责人</span></div><div class="admin-notice">演示时钟：2026 年 11 月 18 日 周三 20:30 · 当前开放摄影社管理权限。报名和签到数据仅保存在此浏览器。</div><div class="admin-layout"><aside class="admin-sidebar"><h3>社团活动 <span style="color:#a3ab99"> / 04</span></h3>${acts.map(e=>`<button class="admin-event ${e.id===a.id?'selected':''}" data-event="${e.id}"><small>${md(e.start)} · ${isEnded(e)?'已结束':isStarted(e)?'进行中':'未开始'}</small><b>${esc(e.title)}</b><small>${e.signed} 人报名 · ${e.waitlist} 人候补</small></button>`).join('')}</aside><section class="roster-panel"><div class="roster-head"><div><h2>${esc(a.title)}</h2><p>◷ ${range(a)} &nbsp; ⌖ ${esc(a.place)}</p></div><button class="btn secondary small" id="export">↓ 导出名单</button></div><div class="roster-stats"><span><b>${a.signed}</b>已报名</span><span><b>${checked}</b>已签到</span><span><b>${rows.length-checked}</b>未签到</span><span><b>${a.waitlist}</b>候补</span></div><div class="roster-controls"><div class="search-wrap"><span>⌕</span><input id="roster-search" placeholder="搜索姓名、学号或手机号" aria-label="搜索报名名单" value="${esc(rosterSearch)}"></div><select id="roster-mode" class="field-select" aria-label="名单状态筛选"><option value="all">全部报名</option><option value="unchecked">未签到</option><option value="checked">已签到</option><option value="wait">候补名单</option></select></div><div class="table-scroll" id="roster-table"></div><div class="roster-foot">${isStarted(a)?'现场核对姓名 / 学号后签到；点「已签到」可撤销误操作。':'活动尚未开始，签到将在活动开始后开放。'} · 导出包含全部报名与候补，不受筛选影响。</div></section></div>`;
 document.querySelectorAll('[data-event]').forEach(b=>b.onclick=()=>{adminId=b.dataset.event;rosterSearch='';rosterMode='all';renderAdmin();});
 $('#roster-mode').value=rosterMode;$('#roster-mode').onchange=e=>{rosterMode=e.target.value;renderRoster();};$('#roster-search').oninput=e=>{rosterSearch=e.target.value;renderRoster();};$('#export').onclick=()=>exportRoster(a);
 renderRoster();
}
function renderRoster(){
 const a=activity(adminId),wait=rosterMode==='wait',base=wait?state.queues[a.id]:state.rosters[a.id]||[];
 let rows=base.map((r,i)=>({...r,index:i})).filter(r=>(wait||rosterMode==='all'||(rosterMode==='checked'?r.checked_in:!r.checked_in))&&(r.name+r.student_id+(r.phone||'')).includes(rosterSearch.trim()));
 $('#roster-table').innerHTML=`<table><thead><tr><th>${wait?'顺序':'序号'}</th><th>姓名 / 学号</th><th>手机号</th><th>报名时间</th><th>备注</th><th>${wait?'候补状态':'签到状态'}</th><th>操作</th></tr></thead><tbody>${rows.length?rows.map(r=>`<tr><td>${String(r.index+1).padStart(2,'0')}</td><td>${esc(r.unknown?'候补同学':r.name)}<small>${r.unknown?'原始资料未提供':esc(r.student_id)}</small></td><td>${esc(r.phone||'—')}</td><td>${r.unknown?'—':md(r.at)+' '+time(r.at)}</td><td class="table-note" title="${esc(r.note||'')}">${esc(r.note||'—')}</td><td>${wait?`<span class="status wait">第 ${r.index+1} 位</span>`:`<button class="btn ${r.checked_in?'secondary':''} small" data-check="${r.index}" ${!isStarted(a)?'disabled':''}>${r.checked_in?'✓ 已签到':'签到'}</button>`}</td><td>${!isStarted(a)?`<button class="text-button" data-remove="${r.index}">${wait?'移出候补':'取消报名'}</button>`:'<span style="color:#a7af9c">—</span>'}</td></tr>`).join(''):'<tr><td colspan="7" style="text-align:center;padding:42px;color:#949f89">没有匹配的同学</td></tr>'}</tbody></table>`;
 document.querySelectorAll('[data-check]').forEach(b=>b.onclick=()=>{const r=state.rosters[a.id][Number(b.dataset.check)];if(!isStarted(a))return;const apply=()=>{r.checked_in=!r.checked_in;save();renderAdmin();toast(r.checked_in?'签到成功 · '+r.name:'已撤销签到 · '+r.name);};if(r.checked_in)confirmAction('撤销这位同学的签到？',r.name+' 的状态将改为未签到，之后可以重新签到。',apply,'撤销签到');else apply();});
 document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{const i=Number(b.dataset.remove),r=base[i];confirmAction(wait?'移出候补名单？':'取消这位同学的报名？',`${r.unknown?'该候补同学':r.name}将从名单移出。${wait?'后续候补顺序自动前移。':'有候补时，首位候补将自动递补。'}请先与同学确认。`,()=>{
  const m=mine(a.id);if(m&&(r.owner||r.student_id===(m.person?.student_id||DATA.me.student_id)))m.status='已取消';
  if(wait){state.queues[a.id].splice(i,1);syncQueue(a);}else{state.rosters[a.id].splice(i,1);a.signed--;promote(a);}
  save();refreshHeader();renderAdmin();toast(wait?'已移出候补，顺序已更新':'已取消报名，候补已按顺序递补');
 },'确认移出',true);});
}
function exportRoster(a){
 const header=['活动','姓名','学号','手机号','报名时间','备注','报名状态','签到状态'];
 const values=[header,...(state.rosters[a.id]||[]).map(r=>[a.title,r.name,r.unknown?'未提供':r.student_id,r.phone||'',r.unknown?'':r.at,r.note||'','已报名',r.checked_in?'已签到':'未签到']),...state.queues[a.id].map((r,i)=>[a.title,r.name,r.unknown?'未提供':r.student_id,r.phone||'',r.unknown?'':r.at,r.note||'',`候补第 ${i+1} 位`,'—'])];
 const cell=v=>'"'+String(v??'').replace(/^[=+@\-\t\r]/,"'$&").replace(/"/g,'""')+'"';
 const blob=new Blob(['\ufeff'+values.map(row=>row.map(cell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8;'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=`摄影社_${a.title}_报名名单.csv`;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);toast('完整名单已导出为 CSV，可用 Excel 打开');
}
function refreshHeader(){const count=state.mine.filter(m=>m.status!=='已取消'&&!isEnded(activity(m.activity))).length;$('#my-count').textContent=count;}
function render(){
 const hash=location.hash.slice(1)||'activities',page=hash.split('/')[0];
 document.querySelectorAll('[data-nav]').forEach(el=>{const on=el.dataset.nav===(page==='detail'?'activities':page);el.classList.toggle('active',on);if(on)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});refreshHeader();
 if(page==='detail')renderDetail(hash.split('/')[1]);else if(page==='mine')renderMine();else if(page==='admin')renderAdmin();else renderActivities();
 document.title=(page==='detail'?(activity(hash.split('/')[1])?.title||'活动详情'):page==='mine'?'我的报名':page==='admin'?'摄影社工作台':'发现活动')+' · 同频';
}
window.addEventListener('hashchange',()=>{render();window.scrollTo(0,0);});
$('#modal').addEventListener('click',e=>{if(e.target===$('#modal')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
$('#reset-demo').onclick=()=>confirmAction('恢复初始演示数据？','这会清除本浏览器中新增的报名、取消和签到记录，恢复题目提供的初始数据。已下载的名单不会被删除。',()=>{state=initialState();save();render();toast('已恢复初始演示数据');},'确认恢复',true);
render();if(!storageOK)setTimeout(()=>toast('本地存储不可用，关闭页面后改动可能丢失'),300);
