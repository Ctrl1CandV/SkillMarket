'use strict';
const ORIGINAL=window.TRANSLATE_DATA;
const NOW=ORIGINAL.now, TODAY=NOW.slice(0,10), ME=ORIGINAL.me;
const STORE='yitong-workspace-v1';
let state,storageOK=true;
try{state=JSON.parse(localStorage.getItem(STORE)||'null')}catch(e){storageOK=false}
if(!state||state.version!==1)state={version:1,chapters:structuredClone(ORIGINAL.chapters),proposals:structuredClone(ORIGINAL.term_proposals).map((p,i)=>({...p,id:'P'+i})),drafts:{},votes:{},activity:[]};
state.chapters.forEach(c=>{
 c.review_comments.forEach(r=>{if(r.resolved===undefined)r.resolved=c.status==='已完成'});
 if(c.status==='翻译中'&&c.due&&c.due<TODAY){
  c.released={translator:c.translator,due:c.due,claimed_at:c.claimed_at,date:TODAY};
  state.activity.unshift({text:`${c.title} 的认领已超期释放`,date:TODAY});
  c.status='未认领';c.translator=null;c.reviewer=null;c.claimed_at=null;c.due=null;
 }
});
const PARTS=[...new Set(state.chapters.map(c=>c.part))];
const LABELS={overview:'章节总览',tasks:'我的任务',glossary:'术语表',chapter:'章节详情'};
const cls={'未认领':'unclaimed','翻译中':'translating','待审校':'review','审校中':'reviewing','已完成':'complete'};
let page='overview',chapterId=null,filter='全部',part='',query='',termQuery='',termFilter='全部术语',taskFilter='进行中',collapsed=new Set();
const $=(s)=>document.querySelector(s);
const esc=(s)=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const num=n=>n.toLocaleString('en-US');
const date=s=>s?s.slice(0,10).replaceAll('-','.'):'—';
const statusPill=c=>`<span class="pill ${cls[c.status]}">${c.status}</span>`;
const person=n=>n?`<span class="person"><span class="avatar" style="background:${['#edf0e3','#edece0','#e8eee7','#f0ebe3'][n.charCodeAt(0)%4]}">${esc(n.slice(-2,-1))}</span>${esc(n)}</span>`:'<span class="dash">—</span>';
const pending=c=>c.review_comments.filter(r=>!r.resolved).length;
const owned=c=>c.translator===ME||c.reviewer===ME;
const activeMine=()=>state.chapters.filter(c=>owned(c)&&c.status!=='已完成');
const find=id=>state.chapters.find(c=>c.id===id);
function persist(){try{localStorage.setItem(STORE,JSON.stringify(state));storageOK=true}catch(e){storageOK=false;toast('本地存储不可用，请勿关闭页面；可导出备份。')}updateChrome()}
function activity(text){state.activity.unshift({text,date:TODAY});state.activity=state.activity.slice(0,50)}
function toast(message){$('#toast').textContent=message;$('#toast').classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').classList.remove('show'),3400)}
function updateChrome(){
 $('#task-count').textContent=activeMine().length;
 $('#breadcrumb').textContent=LABELS[page];
 document.title=`${page==='chapter'?find(chapterId)?.title:LABELS[page]} · 译同`;
 document.querySelectorAll('#main-nav a').forEach(a=>{const active=a.dataset.page===page||(page==='chapter'&&a.dataset.page==='overview');a.classList.toggle('active',active);if(active)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')});
 $('#part-nav').innerHTML=PARTS.map((p,i)=>`<a class="part-link ${part===p&&page==='overview'?'selected':''}" href="#overview" data-action="part" data-part="${esc(p)}">${esc(p)}<b>${state.chapters.filter(c=>c.part===p).length.toString().padStart(2,'0')}</b></a>`).join('');
 const saved=$('.header-right>span:last-child');if(saved)saved.textContent=storageOK?'本地已保存':'未能保存';
}
function heading(kicker,title,subtitle,button=''){return `<div class="page-heading"><div><div class="eyebrow">${kicker}</div><h1>${title}</h1><p class="subtitle">${subtitle}</p></div>${button}</div>`}
function tabs(items,current,action){return `<div class="tabs">${items.map(([name,count])=>`<button class="tab ${current===name?'active':''}" data-action="${action}" data-value="${name}">${name}${count!==undefined?`<span>${count}</span>`:''}</button>`).join('')}</div>`}
function countStatus(s){return state.chapters.filter(c=>c.status===s).length}
function overview(){
 const complete=countStatus('已完成'),n=state.chapters.length,percent=Math.round(complete/n*100),outdated=state.chapters.filter(c=>c.outdated).length;
 const stats=[['未认领',countStatus('未认领'),'等待下一位热心的你','＋','未认领'],['翻译中',countStatus('翻译中'),'字里行间，正在发生','↗','翻译中'],['待审校',countStatus('待审校')+countStatus('审校中'),`其中 ${countStatus('审校中')} 章正在审校`,'☷','待审校'],['已完成',complete,`${outdated} 章原文更新，待同步`,'✓','已完成']];
 return heading('THE TRANSLATION WORKSPACE','让好文档，不止于英文。','和 26 位志愿者一起，把 Framework v4 带给更多开发者。',`<button class="btn" data-action="guide"><span>♧</span> 协作指南 <span>↗</span></button>`)+
 `<section class="hero"><div class="hero-copy"><div class="eyebrow">FRAMEWORK v4 · 简体中文翻译计划</div><h2>一章一节，译路同行。</h2><p>不必一口气走很远，每一小段都算数。</p><div class="hero-bottom"><div class="avatars">${['宋','谢','汪','贾'].map((n,i)=>`<span class="avatar" style="background:${['#b8c5a0','#c4c6a3','#aaba9d','#c7ccb4'][i]}">${n}</span>`).join('')}</div><span>26 位志愿者参与</span><span class="hero-line"></span><span>9 个部分 · 54 个章节</span></div></div><div class="hero-progress"><div class="overline">我们的翻译进度</div><div class="progress-number">${percent}<span>%</span><small>${complete} / ${n} 章已完成</small></div><div class="progress-track"><span style="width:${percent}%"></span></div><div class="progress-caption"><span>每一份贡献，都在推动进度</span><span>继续加油 ↗</span></div></div></section>`+
 `<section class="stats">${stats.map((s,i)=>`<button class="stat-card" data-action="filter" data-value="${s[4]}"><div class="stat-top">${s[0]}<span class="stat-icon">${s[3]}</span></div><div class="stat-number">${s[1]}<small>章</small></div><div class="stat-foot ${i===3?'accent':''}">${s[2]} ${i===0?'↗':''}</div></button>`).join('')}</section>`+
 `<section id="chapters"><div class="section-heading"><h2>章节目录<small>把下一章，交给你。</small></h2><span class="hint"><span style="color:#b39154">↻</span> 原文有更新的章节需要同步译文</span></div><div class="filters">${tabs([['全部',54],['未认领',countStatus('未认领')],['翻译中',countStatus('翻译中')],['待审校',countStatus('待审校')+countStatus('审校中')],['已完成',complete],['待同步',outdated]],filter,'filter')}<div class="filter-controls"><label class="search"><span>⌕</span><input id="chapter-search" aria-label="搜索章节或译者" placeholder="搜索章节、译者…" value="${esc(query)}"></label><select class="select" id="part-select" aria-label="选择文档部分"><option value="">所有部分</option>${PARTS.map(p=>`<option ${part===p?'selected':''}>${p}</option>`).join('')}</select></div></div><div id="chapter-results">${chapterResults()}</div></section>`+
 `<div class="overview-note"><span>ⓘ</span><span>认领后请在 21 天内提交审校，逾期未提交的章节会自动释放。${state.chapters.filter(c=>c.released).length} 个超期认领已释放，详情保留原认领记录。<button class="clear-filter" data-action="guide">了解协作规则 ↗</button><br>所有操作仅保存在当前浏览器，不会同步给其他志愿者。</span></div>`;
}
function filteredChapters(){return state.chapters.filter(c=>(!part||c.part===part)&&(!query||`${c.title} ${c.translator||''} ${c.reviewer||''}`.toLowerCase().includes(query.toLowerCase()))&&(filter==='全部'||(filter==='待同步'?c.outdated:filter==='待审校'?['待审校','审校中'].includes(c.status):c.status===filter)))}
function chapterResults(){
 const filtered=filteredChapters();if(!filtered.length)return `<div class="empty"><strong>没有找到匹配的章节</strong><p>试试其他关键词，或清除筛选条件。</p><button class="btn light" data-action="reset-filters" style="margin-top:15px">清除筛选</button></div>`;
 return PARTS.filter(p=>filtered.some(c=>c.part===p)).map((p)=>{
 const all=state.chapters.filter(c=>c.part===p),chapters=filtered.filter(c=>c.part===p),done=all.filter(c=>c.status==='已完成').length;
 return `<section class="chapter-group"><button class="group-header" data-action="collapse" data-part="${p}" aria-expanded="${!collapsed.has(p)}"><span class="chevron">${collapsed.has(p)?'›':'⌄'}</span><span class="group-number">${(PARTS.indexOf(p)+1).toString().padStart(2,'0')}</span><strong>${p}</strong><small>${all.length} 个章节</small><span class="group-progress"><span class="mini-track"><i style="width:${done/all.length*100}%"></i></span>${done} / ${all.length} 已完成</span></button>${collapsed.has(p)?'':`<table class="chapter-table"><thead><tr><th>章节名称</th><th>英文词数</th><th>状态</th><th>译者</th><th>截止日期</th><th>操作</th></tr></thead><tbody>${chapters.map(c=>`<tr><td><div class="chapter-title"><span class="doc-icon">▤</span><a href="#chapter/${c.id}">${c.title}</a>${c.outdated?'<span class="outdated" title="原文已更新，译文待同步" aria-label="原文已更新，译文待同步">↻ 待同步</span>':''}</div></td><td class="words">${num(c.words)}</td><td>${statusPill(c)}</td><td>${person(c.translator)}</td><td>${c.due?`<span class="${c.due<='2026-11-22'?'due-warn':''}">${date(c.due)}</span>`:'<span class="dash">—</span>'}</td><td>${c.status==='未认领'?`<button class="row-link" data-action="claim" data-id="${c.id}">认领 <span>＋</span></button>`:`<a class="row-link" href="#chapter/${c.id}">查看 <span>↗</span></a>`}</td></tr>`).join('')}</tbody></table>`}</section>`;
 }).join('');
}
const SAMPLE_ZH=['组件是一段拥有自身逻辑和外观的 UI。','组件可以小到一个按钮，也可以大到整个页面。','你可以将组件嵌套在其他组件中。','当状态改变时，框架会重新渲染组件。','在水合过程中，客户端会为服务器发送的 HTML 附加事件处理函数。','props 是只读的快照：每次渲染都会收到一个新版本的 props。'];
function chapter(){
 const c=find(chapterId);if(!c)return `<div class="empty"><strong>找不到这一章</strong><a class="text-link" href="#overview">返回章节总览</a></div>`;
 const edit=c.translator===ME&&c.status!=='已完成';
 const draft=state.drafts[c.id]||SAMPLE_ZH;
 let action='';
 if(c.status==='未认领')action=`<button class="btn primary" data-action="claim" data-id="${c.id}">＋ 认领本章</button>`;
 else if(c.translator===ME&&c.status==='翻译中')action=`<button class="btn primary" data-action="submit" data-id="${c.id}">提交审校 ↗</button>`;
 else if(c.status==='待审校'&&c.translator!==ME&&!c.reviewer)action=`<button class="btn primary" data-action="take-review" data-id="${c.id}">开始审校 ↗</button>`;
 else if(c.reviewer===ME&&['待审校','审校中'].includes(c.status))action=`<button class="btn primary" data-action="finish-review" data-id="${c.id}">完成审校 ✓</button>`;
 else if(c.translator===ME&&c.status==='待审校')action=`<button class="btn" data-action="withdraw" data-id="${c.id}">撤回修改</button>`;
 return `<a href="#overview" class="back-link">← 返回章节总览</a>`+heading(`${c.part.toUpperCase()} / ${c.id}`,c.title,`<span class="detail-meta">${statusPill(c)}<span>${num(c.words)} 英文词</span><span>原文更新于 ${date(c.source_updated)}</span>${c.outdated?'<span class="outdated">↻ 译文待同步</span>':''}</span>`,action)+
 (c.outdated?`<div class="notice">↻ 英文原文已于 ${date(c.source_updated)} 更新，当前译文需要同步。${c.translator===ME?`<button class="clear-filter" data-action="sync" data-id="${c.id}">已核对并同步译文 →</button>`:'请由本章译者核对更新。'}</div>`:'')+
 `<div class="detail-layout"><div>${c.handoff?`<div class="notice info"><strong>译文交接说明</strong><br>${esc(c.handoff).replaceAll('\n','<br>')}</div>`:''}<section class="panel"><div class="panel-heading"><h2>双语对照 <span class="sample-tag">示例片段</span></h2><span class="draft-status">${edit?'修改自动保存在本机':'只读预览'}</span></div><div class="notice info" style="margin:15px 16px;font-size:10px">ⓘ 数据只提供了 6 段通用示例，以下并非 ${c.title} 的完整正文。中文为演示译文，可用于体验对照与草稿编辑；提交审校仅记录协作状态。</div><div class="compare-head"><span>ENGLISH · 原文示例</span><span>简体中文 · ${edit?'我的示例草稿':'译文示例'}</span></div>${ORIGINAL.sample_paragraphs.map((s,i)=>`<div class="paragraph-pair"><div class="source-text"><span class="para-num">SAMPLE ${String(i+1).padStart(2,'0')}</span>${esc(s)}</div><div class="translation"><span class="para-num">示例 ${String(i+1).padStart(2,'0')}</span>${edit?`<textarea data-draft="${c.id}" data-index="${i}" aria-label="第 ${i+1} 段示例译文">${esc(draft[i])}</textarea>`:`<p>${esc(draft[i])}</p>`}</div></div>`).join('')}</section>
 <section class="panel" id="comments"><div class="panel-heading"><h2>审校意见 <small>${pending(c)} 条待处理 / 共 ${c.review_comments.length} 条</small></h2><span class="muted" style="font-size:9px">段落号来自完整章节</span></div>${c.review_comments.length?c.review_comments.map((r,i)=>`<article class="comment ${r.resolved?'resolved':''}"><div class="comment-top">${person(r.by)}<span class="comment-ref">完整原文 · 第 ${r.para} 段</span></div><p>${esc(r.text)}</p>${r.reply?`<div class="reply">贾浩宇：${esc(r.reply)}</div>`:''}<div class="comment-foot"><span class="${r.resolved?'resolved-label':'muted'}" style="font-size:10px">${r.resolved?'✓ 已处理':'○ 待处理'}</span>${owned(c)?`<button class="row-link" data-action="${r.resolved?'reopen-comment':'resolve-comment'}" data-id="${c.id}" data-index="${i}">${r.resolved?'重新打开':'回复并处理 →'}</button>`:''}</div></article>`).join(''):`<div class="empty" style="border:0;border-radius:0;padding:30px"><p>还没有审校意见。准确、具体的反馈能让译文更好。</p></div>`}<form class="comment-form" id="comment-form" data-id="${c.id}"><textarea name="comment" placeholder="写下具体的审校意见，或补充翻译说明…" aria-label="审校意见" required maxlength="1200"></textarea><div class="form-bottom"><label>完整原文章节段落 <input name="para" type="number" value="1" min="1" max="999" required aria-label="意见对应段落号"></label><button class="btn primary" type="submit">发表意见</button></div></form></section></div>
 <aside class="detail-aside"><section class="panel"><div class="panel-heading"><h2>章节信息</h2><span class="sample-tag">${c.id}</span></div><div class="panel-body"><dl class="metadata"><dt>译者</dt><dd>${person(c.translator)}</dd><dt>审校者</dt><dd>${person(c.reviewer)}</dd><dt>认领时间</dt><dd>${date(c.claimed_at)}${c.claimed_at?' '+c.claimed_at.slice(11,16):''}</dd><dt>提交截止日</dt><dd class="${c.due&&c.due<='2026-11-22'?'due-warn':''}">${date(c.due)}</dd><dt>英文词数</dt><dd>${num(c.words)}</dd><dt>待处理意见</dt><dd>${pending(c)} 条</dd></dl><p class="aside-note">认领后 21 天内提交审校。待审校、审校中的章节不会因翻译期限而释放。</p></div>${c.released?`<div class="release-record">↺ ${esc(c.released.translator)} 的原认领已于 ${date(c.released.date)} 释放。<br>原截止日期：${date(c.released.due)}</div>`:''}</section><section class="panel"><div class="panel-heading"><h2>翻译小约定</h2></div><div class="panel-body"><p class="aside-note" style="margin-top:0">章节标题、术语和代码保留英文原样。正文中的术语译法以术语表为准。<br><br>有不确定的词？先查查大家的共识。</p><a href="#glossary" class="btn light" style="width:100%;margin-top:16px">查看术语表 ↗</a></div></section></aside></div>`;
}
function tasks(){
 const mine=state.chapters.filter(owned),active=activeMine(),comments=active.reduce((a,c)=>a+pending(c),0),review=active.filter(c=>c.reviewer===ME),released=state.chapters.filter(c=>c.released?.translator===ME);
 const list=mine.filter(c=>taskFilter==='已完成'?c.status==='已完成':taskFilter==='待我审校'?c.reviewer===ME&&c.status!=='已完成':taskFilter==='待处理意见'?c.status!=='已完成'&&pending(c)>0:c.status!=='已完成');
 return heading('MY CONTRIBUTIONS','晚上好，浩宇。',`有 ${active.length} 章正在等你接力。慢慢来，也在向前。`,`<a class="btn" href="#overview">寻找下一章 ↗</a>`)+
 `<section class="stats">${[['我的翻译',active.filter(c=>c.translator===ME).length,'进行中的翻译任务','✎','进行中'],['待我审校',review.length,'帮助另一位译者更进一步','☷','待我审校'],['待处理意见',comments,'及时回复，让协作更顺畅','◌','待处理意见'],['已完成',mine.filter(c=>c.status==='已完成').length,'感谢每一份认真','✓','已完成']].map(s=>`<button class="stat-card" data-action="task-filter" data-value="${s[4]}"><div class="stat-top">${s[0]}<span class="stat-icon">${s[3]}</span></div><div class="stat-number">${s[1]}<small>${s[0]==='待处理意见'?'条':'章'}</small></div><div class="stat-foot">${s[2]}</div></button>`).join('')}</section>`+
 (released.length?`<div class="notice">↺ ${released.map(c=>`<a class="text-link" href="#chapter/${c.id}">${c.title}</a>`).join('、')} 的旧认领已超期释放，暂不计入当前任务。你可以在详情重新认领。</div>`:'')+
 `<div class="task-layout"><section><div class="section-heading"><h2>我的任务清单</h2></div><div style="margin-bottom:16px">${tabs([['进行中',active.length],['待我审校',review.length],['待处理意见',active.filter(c=>pending(c)>0).length],['已完成',mine.filter(c=>c.status==='已完成').length]],taskFilter,'task-filter')}</div>${list.length?list.map(c=>`<article class="task-card"><div class="task-part">${c.part} <span style="padding:0 6px">/</span> ${c.translator===ME?'我是译者':'我是审校者'}</div><div class="task-card-top"><h3><a href="#chapter/${c.id}">${c.title}</a></h3>${statusPill(c)}</div><p>${num(c.words)} 英文词 <span style="padding:0 7px">·</span> ${c.due?'截止 '+date(c.due):c.status==='已完成'?'已完成协作':'审校阶段，无翻译截止日'}${c.outdated?' <span class="outdated">↻ 原文待同步</span>':''}</p><div class="task-card-bottom"><span>${pending(c)?`◌ ${pending(c)} 条审校意见待处理`:'✓ 暂无待处理意见'}</span><a href="#chapter/${c.id}${pending(c)?'/comments':''}">${c.translator===ME?'继续翻译':'进入审校'} →</a></div></article>`).join(''):`<div class="empty"><strong>这一栏暂时没有任务</strong><p>去章节总览，找一章感兴趣的内容吧。</p></div>`}</section><aside class="task-aside"><div class="task-summary"><div class="eyebrow">A LITTLE REMINDER</div><h3>按自己的节奏，认真一点。</h3><p>认领不是竞速，而是一份 21 天的约定。记得留一点时间，检查术语和代码注释。</p></div><section class="panel"><div class="panel-heading"><h2>最近动态</h2><small>本机记录</small></div><div class="panel-body">${state.activity.slice(0,5).map(a=>`<div class="activity">${esc(a.text)}<small>${date(a.date)}</small></div>`).join('')||'<p class="aside-note">认领和审校后的动态会显示在这里。</p>'}</div></section></aside></div>`;
}
function glossary(){
 return heading('SHARED VOCABULARY','同一个词，同一种默契。','统一术语，让 54 个章节读起来像出自同一个人。',`<button class="btn primary" data-action="propose"><span class="plus">＋</span> 提议新术语</button>`)+
 `<div class="glossary-intro"><span>Aa</span><span><strong>先查术语，再动笔。</strong> 标注「不译」的术语保持英文原样；代码、章节标题也不翻译。新提议需达成共识后再采用。</span></div><div class="glossary-layout"><section><div class="section-heading"><h2>共享术语表 <small>50 个共识用词</small></h2></div><div class="filters">${tabs([['全部术语',50],['保留英文',ORIGINAL.glossary.filter(t=>t.zh.includes('不译')).length]],termFilter,'term-filter')}<label class="search"><span>⌕</span><input id="term-search" aria-label="搜索英文或中文术语" value="${esc(termQuery)}" placeholder="搜索英文、译法或备注…"></label></div><div class="panel" id="term-results">${termResults()}</div></section><aside class="glossary-aside"><section class="panel"><div class="panel-heading"><h2>待讨论提议 <small>${state.proposals.length}</small></h2><span class="sample-tag">一起决定</span></div><div class="proposal-list">${state.proposals.map(p=>`<article class="term-proposal"><h3>${esc(p.en)}</h3><div class="proposal-zh">建议译为「${esc(p.zh)}」</div>${p.note?`<p>${esc(p.note)}</p>`:''}<div class="proposal-bottom"><span>${esc(p.by)} 提议</span><button class="vote-btn ${state.votes[p.id]?'voted':''}" data-action="vote" data-id="${p.id}" aria-label="${state.votes[p.id]?'撤回':'支持'} ${esc(p.en)}" aria-pressed="${!!state.votes[p.id]}">△ ${p.votes+(state.votes[p.id]?1:0)}</button></div></article>`).join('')}</div></section><p class="aside-note">每人每条提议可投 1 票，再次点击可撤回。票数只代表支持，不会自动成为正式术语。本地投票不会联网同步。</p></aside></div>`;
}
function termResults(){const list=ORIGINAL.glossary.filter(t=>(termFilter!=='保留英文'||t.zh.includes('不译'))&&`${t.en} ${t.zh} ${t.note}`.toLowerCase().includes(termQuery.toLowerCase()));return list.length?`<table class="glossary-table"><thead><tr><th>英文术语</th><th>统一译法</th><th>使用约定</th></tr></thead><tbody>${list.map(t=>`<tr><td>${esc(t.en)}</td><td>${esc(t.zh)}</td><td>${esc(t.note)||'—'}</td></tr>`).join('')}</tbody></table>`:'<div class="empty" style="border:0"><strong>还没有这个术语</strong><p>换一个关键词，或提议新的译法。</p><button class="btn light" data-action="propose" style="margin-top:12px">提议新术语</button></div>'}
function render(){updateChrome();$('#app').innerHTML=page==='overview'?overview():page==='tasks'?tasks():page==='glossary'?glossary():chapter();if(page==='chapter')$('.page-heading')?.classList.add('detail-heading');if(page==='glossary')$('.page-heading')?.classList.add('glossary-heading')}
function route(){const [p,id,anchor]=location.hash.slice(1).split('/');page=['overview','tasks','glossary','chapter'].includes(p)?p:'overview';chapterId=id;$('#sidebar').classList.remove('open');render();if(anchor==='comments')setTimeout(()=>$('#comments')?.scrollIntoView({behavior:'smooth'}),30);else window.scrollTo(0,0)}
window.addEventListener('hashchange',route);
function modal(title,body){const d=$('#modal');d.innerHTML=`<div class="modal-head"><h2>${title}</h2><button class="icon-btn" data-action="close-modal" aria-label="关闭弹窗">✕</button></div><div class="modal-body">${body}</div>`;if(!d.open)d.showModal()}
function closeModal(){$('#modal').close()}
function confirmModal(title,body,confirm,action,id){modal(title,`${body}<div class="modal-actions"><button class="btn" data-action="close-modal">再想想</button><button class="btn primary" data-action="${action}" data-id="${id}">${confirm}</button></div>`)}
function claim(id){const c=find(id);if(!c||c.status!=='未认领'){toast('该章节已被认领，请选择其他章节');return}confirmModal('认领这一章',`<div class="eyebrow">${c.part.toUpperCase()}</div><h2 style="font-family:Arial;margin-bottom:12px">${c.title}</h2><p>这一章有 <strong>${num(c.words)}</strong> 个英文词。认领后由你负责翻译，请在 <strong>2026.12.10</strong> 前提交审校（21 天）。<br>未按时提交将自动释放，保留原认领记录。</p><div class="notice info" style="margin-bottom:0">当前以项目时间 2026.11.19 21:00 计算期限。</div>`,'确认认领','confirm-claim',id)}
function guide(){modal('一起协作的几个约定',`<p><strong>01 · 从一章开始</strong><br>在章节总览中找到未认领章节，认领后有 21 天时间提交。未提供活动记录，因此本地以“到期仍处于翻译中”为超期条件，自动释放并保留记录。</p><p><strong>02 · 翻译，然后一起打磨</strong><br>章节标题、代码和英文术语保持原样；正文术语译法遵循术语表。提交后由其他审校者审阅，译者回复意见，审校者确认后完成。</p><p><strong>03 · 这是一份离线协作原型</strong><br>数据提供 54 章协作信息，只有 6 段通用示例正文，双语对照明确标记为示例。不会假装已加载整本文档。</p><p><strong>04 · 你的操作留在本机</strong><br>所有操作保存于此浏览器，不会同步给其他人。可导出本机状态用于备份。演示时钟固定为 2026.11.19 21:00。</p><div class="modal-actions"><button class="btn" data-action="export">导出本机数据</button><button class="btn primary" data-action="close-modal">知道了</button></div>`)}
document.addEventListener('click',e=>{
 if(e.target.closest('#main-nav a'))$('#sidebar').classList.remove('open');
 const el=e.target.closest('[data-action]');if(!el)return;
 const a=el.dataset.action,id=el.dataset.id,c=find(id),index=Number(el.dataset.index);
 if(a==='menu'){$('#sidebar').classList.toggle('open');return}
 if(a==='close-modal'){closeModal();return}
 if(a==='guide'||a==='storage-info'){guide();return}
 if(a==='filter'){filter=el.dataset.value;render();return}
 if(a==='part'){e.preventDefault();part=el.dataset.part;filter='全部';query='';if(page!=='overview')location.hash='overview';else render();return}
 if(a==='reset-filters'){filter='全部';part='';query='';render();return}
 if(a==='collapse'){const p=el.dataset.part;collapsed.has(p)?collapsed.delete(p):collapsed.add(p);$('#chapter-results').innerHTML=chapterResults();return}
 if(a==='task-filter'){taskFilter=el.dataset.value;render();return}
 if(a==='term-filter'){termFilter=el.dataset.value;render();return}
 if(a==='claim'){claim(id);return}
 if(a==='confirm-claim'){
  if(!c||c.status!=='未认领')return;
  c.status='翻译中';c.translator=ME;c.claimed_at=NOW;c.due='2026-12-10';activity(`认领了 ${c.title}`);persist();closeModal();if(location.hash===`#chapter/${id}`)render();else location.hash=`chapter/${id}`;toast('认领成功，请于 12 月 10 日前提交审校');return;
 }
 if(a==='submit'){
  if(c.translator!==ME||c.status!=='翻译中')return;
  modal('提交本章审校',`<h3 style="font-family:Arial;margin-bottom:12px">${c.title}</h3><p>提交后，本章将进入待审校，翻译截止日将不再适用。</p><div class="notice">这里仅保存协作状态与示例草稿，不包含完整章节编辑器。请确认完整译文已在项目使用的文档中准备好。</div><form id="submit-form" data-id="${id}"><label class="check"><input type="checkbox" required>我已检查完整译文、术语和代码注释</label><label>译文位置或交接说明（可选）<textarea name="handoff" placeholder="例如：完整译文保存在本地文件…" maxlength="600">${esc(c.handoff||'')}</textarea></label><div class="modal-actions"><button class="btn" type="button" data-action="close-modal">取消</button><button class="btn primary" type="submit">确认提交审校</button></div></form>`);return;
 }
 if(a==='take-review'){
  if(c.translator===ME)return;
  confirmModal('开始审校',`<p>你将负责 <strong>${c.title}</strong> 的审校。请核对术语、遗漏与语序，并留下可操作的修改意见。</p>`,'确认开始','confirm-review',id);return;
 }
 if(a==='confirm-review'){if(c.status!=='待审校'||c.reviewer||c.translator===ME)return;c.reviewer=ME;c.status='审校中';activity(`开始审校 ${c.title}`);persist();closeModal();render();toast('已加入你的审校任务');return}
 if(a==='finish-review'){
  if(pending(c)){toast(`还有 ${pending(c)} 条意见待处理，请先解决再完成审校`);$('#comments')?.scrollIntoView({behavior:'smooth'});return}
  confirmModal('确认完成审校',`<p>确认 <strong>${c.title}</strong> 的完整译文已检查，所有审校意见均已处理？</p>`,'审校通过','confirm-finish',id);return;
 }
 if(a==='confirm-finish'){if(c.reviewer!==ME||pending(c))return;c.status='已完成';c.due=null;activity(`完成了 ${c.title} 的审校`);persist();closeModal();render();toast('审校完成，感谢你的认真');return}
 if(a==='withdraw'){confirmModal('撤回修改',`<p>撤回 <strong>${c.title}</strong> 后将恢复翻译中，获得从当前项目时间起的 21 天修改期。所有意见会保留。</p>`,'确认撤回','confirm-withdraw',id);return}
 if(a==='confirm-withdraw'){if(c.translator!==ME||c.status!=='待审校')return;c.status='翻译中';c.due='2026-12-10';activity(`撤回修改 ${c.title}`);persist();closeModal();render();toast('已恢复翻译中，截止日期为 12 月 10 日');return}
 if(a==='resolve-comment'){
  const r=c.review_comments[index];if(!r)return;
  modal('回复并处理审校意见',`<p style="padding:12px;background:#f0f4e9;border-radius:5px">${esc(r.by)} · 第 ${r.para} 段<br>${esc(r.text)}</p><form id="resolve-form" data-id="${id}" data-index="${index}"><label>修改说明<textarea name="reply" required placeholder="说明你如何修改了译文，或解释保留原译法的原因…" maxlength="1000"></textarea></label><div class="modal-actions"><button class="btn" type="button" data-action="close-modal">取消</button><button class="btn primary" type="submit">保存并标记已处理</button></div></form>`);return;
 }
 if(a==='reopen-comment'){if(!owned(c))return;c.review_comments[index].resolved=false;persist();render();toast('已重新打开该意见');return}
 if(a==='sync'){confirmModal('确认已同步原文更新',`<p>请先对照 ${date(c.source_updated)} 的英文更新核对完整译文。这里没有原文差异数据，需要你在完整文档中检查。</p>`,'已核对并同步','confirm-sync',id);return}
 if(a==='confirm-sync'){if(c.translator!==ME)return;c.outdated=false;activity(`同步了 ${c.title} 的原文更新`);persist();closeModal();render();toast('已清除待同步标记');return}
 if(a==='propose'){
  modal('让一个新术语有共识',`<p>先确认共享术语表里没有相同用词。提议会进入讨论，不会直接覆盖正式译法。</p><form id="proposal-form"><label>英文术语<input name="en" required maxlength="80" placeholder="例如：progressive enhancement"></label><label>建议译法<input name="zh" required maxlength="80" placeholder="保留英文时可注明“不译”"></label><label>提议理由（可选）<textarea name="note" maxlength="500" placeholder="为什么这一种译法更合适？"></textarea></label><p id="proposal-error" class="error-text" role="alert"></p><div class="modal-actions"><button class="btn" type="button" data-action="close-modal">取消</button><button class="btn primary" type="submit">发布提议</button></div></form>`);return;
 }
 if(a==='vote'){state.votes[id]=!state.votes[id];persist();render();toast(state.votes[id]?'已支持这条提议':'已撤回支持');return}
 if(a==='export'){const blob=new Blob([JSON.stringify({...state,exported_at:NOW},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='译同-本机备份-2026-11-19.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('已导出本机数据备份');return}
});
document.addEventListener('input',e=>{
 const el=e.target;
 if(el.id==='chapter-search'){query=el.value;$('#chapter-results').innerHTML=chapterResults()}
 if(el.id==='term-search'){termQuery=el.value;$('#term-results').innerHTML=termResults()}
 if(el.dataset.draft){const id=el.dataset.draft;if(!state.drafts[id])state.drafts[id]=[...SAMPLE_ZH];state.drafts[id][Number(el.dataset.index)]=el.value;persist();$('.draft-status').textContent=storageOK?'草稿已自动保存':'草稿未能保存'}
});
document.addEventListener('change',e=>{if(e.target.id==='part-select'){part=e.target.value;render()}});
document.addEventListener('submit',e=>{
 const form=e.target;if(!['comment-form','resolve-form','proposal-form','submit-form'].includes(form.id))return;e.preventDefault();
 const fd=new FormData(form),c=find(form.dataset.id);
 if(form.id==='comment-form'){
  const text=fd.get('comment').trim();if(!text){toast('请填写意见内容');return}c.review_comments.push({by:ME,para:Number(fd.get('para')),text,resolved:false});activity(`在 ${c.title} 留下了审校意见`);persist();render();$('#comments').scrollIntoView({block:'start'});toast('意见已发表');
 }
 if(form.id==='resolve-form'){
  const reply=fd.get('reply').trim();if(!reply){toast('请补充处理说明');return}if(!owned(c))return;const r=c.review_comments[Number(form.dataset.index)];r.resolved=true;r.reply=reply;activity(`处理了 ${c.title} 的一条审校意见`);persist();closeModal();render();$('#comments').scrollIntoView({block:'start'});toast('回复已保存，意见已处理');
 }
 if(form.id==='proposal-form'){
  const en=fd.get('en').trim(),zh=fd.get('zh').trim(),note=fd.get('note').trim();
  if(!en||!zh){$('#proposal-error').textContent='英文术语与建议译法不能为空。';return}
  if([...ORIGINAL.glossary,...state.proposals].some(t=>t.en.toLowerCase()===en.toLowerCase())){$('#proposal-error').textContent='这个术语已在术语表或提议中，请先搜索现有用词。';return}
  state.proposals.unshift({en,zh,note,by:ME,votes:0,id:'P'+Date.now()});activity(`提议了新术语 ${en}`);persist();closeModal();render();toast('提议已发布，等待大家的支持');
 }
 if(form.id==='submit-form'){
  if(c.translator!==ME||c.status!=='翻译中')return;c.status='待审校';c.due=null;c.handoff=fd.get('handoff').trim();activity(`提交了 ${c.title}，等待审校`);persist();closeModal();render();toast('已提交审校，感谢你的贡献');
 }
});
$('#modal').addEventListener('click',e=>{if(e.target===$('#modal')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)closeModal()}});
document.addEventListener('click',e=>{if(window.innerWidth<=700&&$('#sidebar').classList.contains('open')&&!e.target.closest('.sidebar')&&!e.target.closest('[data-action="menu"]'))$('#sidebar').classList.remove('open')});
persist();route();
