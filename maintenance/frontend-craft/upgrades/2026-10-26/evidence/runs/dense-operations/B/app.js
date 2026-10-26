'use strict';
(() => {
  const data = window.QUEUE_DATA;
  const KEY = 'import-desk:dense-operations:B:v1';
  const $ = s => document.querySelector(s);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clone = v => JSON.parse(JSON.stringify(v));
  let jobs = clone(data.jobs);
  let selected = new Set();
  let filters = { query: '', status: '', owner: '', sort: 'submitted_at-desc' };
  let currentDetail = null;
  let pendingIds = [];
  let toastTimer;
  const ownerName = id => data.owners.find(o => o.id === id)?.name || '本地演示系统';
  const num = value => value == null ? '尚未统计' : value.toLocaleString('zh-CN');
  const date = (value, short = false) => new Intl.DateTimeFormat('zh-CN', {timeZone:data.time_zone, ...(short ? {} : {year:'numeric',month:'2-digit',day:'2-digit'}), hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(value));
  const can = (job, rule) => data.rules[rule].allowed_statuses.includes(job.status);
  const badge = job => `<span class="badge ${job.status}">${escape(data.status_labels[job.status])}</span>`;
  const priority = job => `<span class="priority ${job.priority}">${escape(data.priority_labels[job.priority])}</span>`;
  const issue = job => job.open_issue_count ? `<div class="issue-count ${job.status === 'failed' ? '' : 'warning'}">${num(job.open_issue_count)} ${job.status === 'running' ? '条警告' : '项待处理问题'}</div>` : '';
  const percent = job => job.records_total == null || job.records_total === 0 ? null : Math.min(100, 100 * job.records_processed / job.records_total);
  const progress = job => percent(job) == null ? '' : `<div class="progress-track ${job.status}" aria-hidden="true"><span style="width:${percent(job)}%"></span></div>`;
  const isFiltered = () => Boolean(filters.query || filters.status || filters.owner);
  function storageWarning(message) { $('#storage-warning').hidden = false; $('#storage-warning').textContent = message; }
  try {
    const stored = JSON.parse(localStorage.getItem(KEY) || 'null');
    if (stored && stored.version === data.dataset_version && Array.isArray(stored.jobs)) {
      const originalIds = new Set(data.jobs.map(j => j.id));
      const valid = stored.jobs.length <= data.jobs.length && new Set(stored.jobs.map(j => j.id)).size === stored.jobs.length && stored.jobs.every(j => originalIds.has(j.id) && data.status_labels[j.status] && data.priority_labels[j.priority] && Array.isArray(j.activity) && Number.isFinite(j.records_processed) && (j.records_total === null || Number.isFinite(j.records_total)));
      if (valid) jobs = stored.jobs;
      else storageWarning('保存的演示状态无法读取，已载入初始队列。可使用“恢复演示队列”清除旧状态。');
    }
  } catch { storageWarning('浏览器未能读取保存状态，当前显示初始队列。'); }
  function persist() {
    try { localStorage.setItem(KEY, JSON.stringify({version:data.dataset_version,jobs})); $('#storage-warning').hidden = true; }
    catch { storageWarning('本次更改已在当前页面生效，但浏览器未能保存。刷新后可能丢失，请检查浏览器存储设置。'); }
  }
  function visibleJobs() {
    const query = filters.query.trim().toLocaleLowerCase();
    const [field, direction] = filters.sort.split('-');
    return jobs.filter(job => (!query || data.rules.search_fields.some(key => String(job[key]).toLocaleLowerCase().includes(query))) && (!filters.status || job.status === filters.status) && (!filters.owner || job.owner_id === filters.owner)).sort((a,b) => {
      if (field === 'records_total') {
        if (a.records_total === null && b.records_total === null) return a.id.localeCompare(b.id);
        if (a.records_total === null) return 1;
        if (b.records_total === null) return -1;
      }
      const av = field === 'priority' ? data.priority_order.indexOf(a.priority) : field === 'submitted_at' ? Date.parse(a.submitted_at) : a.records_total;
      const bv = field === 'priority' ? data.priority_order.indexOf(b.priority) : field === 'submitted_at' ? Date.parse(b.submitted_at) : b.records_total;
      return (direction === 'asc' ? av-bv : bv-av) || a.id.localeCompare(b.id);
    });
  }
  function renderTabs() {
    const tabs = [['','全部作业'],['failed','失败'],['needs_review','待复核'],['queued','待处理'],['running','进行中'],['completed','完成'],['cancelled','已取消']];
    $('#status-tabs').innerHTML = tabs.map(([status,label]) => `<button class="status-tab ${filters.status === status ? 'active' : ''}" data-status="${status}" aria-pressed="${filters.status === status}">${status === 'failed' || status === 'needs_review' ? '<span class="tab-dot" aria-hidden="true"></span>' : ''}${label}<span class="tab-number">${status ? jobs.filter(j => j.status === status).length : jobs.length}</span></button>`).join('');
  }
  function desktopRow(job) {
    return `<tr class="${selected.has(job.id) ? 'selected' : ''}"><td><input type="checkbox" data-select="${job.id}" aria-label="选择 ${job.id} ${escape(job.name)}" ${selected.has(job.id) ? 'checked' : ''}></td><td><span class="job-id">${job.id}</span><button class="job-name" data-open="${job.id}">${escape(job.name)}</button><div class="job-file">${escape(job.source_file)}</div></td><td>${badge(job)}${issue(job)}</td><td><div class="record-total ${job.records_total === null ? 'unknown' : ''}">${num(job.records_total)}</div><div class="record-sub">已处理 ${num(job.records_processed)}${percent(job) === null ? '' : ` · ${percent(job).toFixed(1)}%`}</div>${progress(job)}</td><td><span class="owner-name"><span class="owner-avatar" aria-hidden="true">${escape(ownerName(job.owner_id).slice(0,1))}</span>${escape(ownerName(job.owner_id))}</span></td><td>${priority(job)}</td><td class="date-cell">${date(job.submitted_at,true)}<br><small>10 月 26 日</small></td><td><button class="arrow-button" data-open="${job.id}" aria-label="查看 ${job.id} 详情">›</button></td></tr>`;
  }
  function mobileRow(job) {
    return `<article class="mobile-job ${selected.has(job.id) ? 'selected' : ''}"><div class="mobile-job-head"><input type="checkbox" data-select="${job.id}" aria-label="选择 ${job.id} ${escape(job.name)}" ${selected.has(job.id) ? 'checked' : ''}><span class="job-id">${job.id}</span>${badge(job)}</div><button class="job-name" data-open="${job.id}">${escape(job.name)}</button><div class="job-file">${escape(job.source_file)}</div><div class="mobile-job-meta"><span class="owner-name">${escape(ownerName(job.owner_id))}</span>${issue(job)}${priority(job)}</div><div class="mobile-progress"><span><strong>${num(job.records_total)}</strong>${job.records_total === null ? '' : ' 条'}</span>${progress(job)}<span>已处理 ${num(job.records_processed)}</span></div><div class="mobile-job-time"><span>10 月 26 日 ${date(job.submitted_at,true)} 提交</span><button class="text-button" data-open="${job.id}">查看详情 ↗</button></div></article>`;
  }
  function render() {
    const visible = visibleJobs();
    renderTabs();
    $('#result-count').innerHTML = `显示 <strong>${visible.length}</strong> / ${jobs.length} 条作业${filters.status ? ` · ${escape(data.status_labels[filters.status])}` : ''}`;
    $('#clear-filters').hidden = !isFiltered();
    $('#footer-count').textContent = visible.length ? `当前结果 ${visible.length} 条` : '当前结果 0 条';
    if (!jobs.length) $('#queue-content').innerHTML = `<div class="empty-state"><div class="empty-icon" aria-hidden="true">▤</div><h2>队列中还没有作业</h2><p>恢复初始演示队列，可以继续处理 12 条示例作业。</p><button class="button primary" data-action="reset">恢复演示队列</button></div>`;
    else if (!visible.length) $('#queue-content').innerHTML = `<div class="empty-state"><div class="empty-icon" aria-hidden="true">⌕</div><h2>没有符合条件的作业</h2><p>换一个编号、名称或筛选条件，继续查找。</p><button class="button primary" data-action="clear-filters">清除筛选</button></div>`;
    else $('#queue-content').innerHTML = `<table class="job-table"><colgroup><col class="check"><col class="job"><col class="status"><col class="records"><col class="owner"><col class="priority-col"><col class="date"><col class="arrow"></colgroup><thead><tr><th><input type="checkbox" id="select-all" aria-label="选择当前结果中的全部 ${visible.length} 条作业"></th><th>作业 / 源文件</th><th>当前状态</th><th>记录总数 / 进度</th><th>负责人</th><th>优先级</th><th>提交时间</th><th><span aria-hidden="true"></span></th></tr></thead><tbody>${visible.map(desktopRow).join('')}</tbody></table><div class="mobile-jobs">${visible.map(mobileRow).join('')}</div>`;
    const chosen = visible.filter(j => selected.has(j.id)).length;
    for (const checkbox of [$('#select-all'),$('#mobile-select-all')].filter(Boolean)) { checkbox.checked = visible.length > 0 && chosen === visible.length; checkbox.indeterminate = chosen > 0 && chosen < visible.length; checkbox.disabled = !visible.length; }
    const hidden = selected.size - chosen;
    $('#selection-bar').hidden = !selected.size;
    document.body.classList.toggle('selection-active', selected.size > 0);
    $('#selection-count').textContent = `已选择 ${selected.size} 条作业`;
    $('#hidden-count').textContent = hidden ? `其中 ${hidden} 条不在当前结果中` : '全部位于当前结果中';
  }
  function toast(message) {
    clearTimeout(toastTimer); $('#toast').textContent = message; $('#toast').hidden = false;
    toastTimer = setTimeout(() => $('#toast').hidden = true, 4000);
  }
  function clearFilters() { filters.query='';filters.status='';filters.owner='';$('#search').value='';$('#owner-filter').value='';render(); }
  function appendActivity(job, action, message, at) { job.updated_at = at; job.activity.push({id:`${job.id}-local-${Date.now()}-${Math.random().toString(36).slice(2,7)}`,at,actor_id:null,action,message}); }
  function applyRule(job, ruleKey) {
    const rule=data.rules[ruleKey];
    if (!can(job,ruleKey)) return false;
    Object.assign(job,clone(rule.set_fields),{status:rule.new_status});
    appendActivity(job,rule.activity_action,rule.activity_message,new Date().toISOString());
    return true;
  }
  function showAction(title, description, body, footer) {
    $('#action-content').innerHTML = `<div class="action-head"><h2 id="action-title">${title}</h2><button class="close-button" data-action="close-action" aria-label="关闭对话框">×</button>${description ? `<p>${description}</p>` : ''}</div><div class="action-body">${body}</div><div class="action-footer">${footer}</div>`;
    if (!$('#action-dialog').open) $('#action-dialog').showModal();
    $('#action-dialog .close-button').focus();
  }
  function detail(jobId) {
    const job=jobs.find(j=>j.id===jobId); if(!job) return;
    currentDetail=jobId;
    $('#detail-content').innerHTML=`<div class="detail-top"><span class="dialog-eyebrow">${job.id}</span><button class="close-button" data-action="close-detail" aria-label="关闭作业详情">×</button><h2 id="detail-title">${escape(job.name)}</h2><div class="detail-status-line">${badge(job)}${priority(job)}<span class="owner-name">${escape(ownerName(job.owner_id))}</span></div></div><div class="detail-body"><h3 class="section-title">${job.open_issue_count ? '问题与处理说明' : '作业说明'}</h3><div class="summary-box ${job.status}"><p>${escape(job.summary)}</p>${job.issue_code ? `<div class="issue-code">${escape(job.issue_code)}</div>` : ''}</div><div class="detail-stats"><div><span>记录总数</span><strong class="${job.records_total === null ? 'unknown' : ''}">${num(job.records_total)}</strong></div><div><span>已处理</span><strong>${num(job.records_processed)}</strong></div><div><span>${job.status==='running'?'非阻断警告':'未处理问题'}</span><strong>${num(job.open_issue_count)}</strong></div></div><h3 class="section-title">作业属性</h3><dl class="detail-properties"><dt>所属项目</dt><dd>${escape(job.project)}</dd><dt>源文件</dt><dd class="mono">${escape(job.source_file)}</dd><dt>负责人</dt><dd>${escape(ownerName(job.owner_id))} <span class="mono">(${job.owner_id})</span></dd><dt>提交时间</dt><dd>${date(job.submitted_at)}（北京时间）</dd><dt>更新时间</dt><dd>${date(job.updated_at)}（北京时间）</dd><dt>处理比例</dt><dd>${percent(job)===null?'总数尚未统计，暂不计算比例':`${percent(job).toFixed(1)}%`}</dd><dt>问题代码</dt><dd class="mono">${job.issue_code ? escape(job.issue_code) : '无'}</dd></dl><div class="detail-actions"><div class="priority-control"><label for="detail-priority">优先级</label><select id="detail-priority" ${can(job,'change_priority')?'':'disabled'}>${data.rules.change_priority.allowed_values.map(value=>`<option value="${value}" ${job.priority===value?'selected':''}>${data.priority_labels[value]}</option>`).join('')}</select><button class="button" data-action="save-priority" ${can(job,'change_priority')?'':'disabled'}>保存</button></div>${!can(job,'change_priority')?`<p class="permission-note">${data.status_labels[job.status]}作业不可调整优先级。</p>`:''}${can(job,'approve_review')?`<div class="review-action"><p>核对上方问题说明后，<br>可将此作业确认为完成。</p><button class="button primary" data-action="approve-preview">确认复核</button></div>`:can(job,'batch_retry')?`<div class="review-action"><p>重新排队会清除当前处理进度。</p><button class="button primary" data-action="retry-one">重试此作业</button></div>`:''}</div><h3 class="section-title">活动记录 <span style="font-weight:400;color:var(--muted)">/ ${job.activity.length}</span></h3><ol class="timeline">${[...job.activity].reverse().map(event=>`<li><div class="event-meta"><span>${escape(ownerName(event.actor_id))}</span><time datetime="${escape(event.at)}">${date(event.at)}</time></div><p class="event-message">${escape(event.message)}</p><span class="event-action">${escape(event.action)}</span></li>`).join('')}</ol></div>`;
    if (!$('#detail-dialog').open) { $('#detail-dialog').showModal(); $('#detail-dialog').scrollTop=0; }
  }
  function scopeRow(job, mode='preview', result) {
    const eligible=can(job,'batch_retry');
    return `<div class="scope-row"><div class="scope-main"><code>${job.id}</code><strong>${escape(job.name)}</strong>${mode==='selection'?`<span class="scope-reason">${data.status_labels[job.status]} · ${visibleJobs().some(j=>j.id===job.id)?'在当前结果中':'不在当前结果中'}</span>`:mode==='result'?`<div class="scope-reason ${result.success?'success':''}">${escape(result.message)}</div>`:`<div class="scope-reason ${eligible?'success':''}">${eligible?`${data.status_labels[job.status]} → 待处理；已处理数量归零`:`状态为${data.status_labels[job.status]}；仅失败或已取消作业可重试`}</div>`}</div>${mode==='selection'?`<button class="scope-remove" data-remove="${job.id}" aria-label="取消选择 ${job.id}">移除</button>`:`<span class="scope-tag ${mode==='result'?!result.success?'skip':'':!eligible?'skip':''}">${mode==='result'?result.success?'已重试':'未执行':eligible?'可重试':'跳过'}</span>`}</div>`;
  }
  function inspectSelection() {
    const items=jobs.filter(j=>selected.has(j.id));
    showAction(`已选择 ${items.length} 条作业`,'所列编号即批量操作范围；切换筛选不会自动增加选择。',items.length?items.map(j=>scopeRow(j,'selection')).join(''):'<p>已清空选择。</p>','<button class="button primary" data-action="close-action">返回队列</button>');
  }
  function previewRetry(ids) {
    pendingIds=[...ids];
    const items=pendingIds.map(id=>jobs.find(j=>j.id===id)).filter(Boolean);
    const eligible=items.filter(j=>can(j,'batch_retry')).length;
    showAction('确认批量重试','仅重新加入本地演示队列，不会启动真实服务器作业。',`<div class="scope-summary"><strong>${eligible} 条可重试</strong> · ${items.length-eligible} 条将跳过</div>${items.map(j=>scopeRow(j)).join('')}`,`<button class="button" data-action="close-action">返回</button><button class="button primary" data-action="execute-retry" ${eligible?'':'disabled'}>重试 ${eligible} 条作业</button>`);
  }
  function executeRetry() {
    const results=[];
    for(const id of pendingIds){const job=jobs.find(j=>j.id===id);if(!job)continue;const oldStatus=data.status_labels[job.status];const success=applyRule(job,'batch_retry');results.push({job,success,message:success?'已加入待处理队列；处理进度和当前问题已清零。':`未执行：状态为${oldStatus}，仅失败或已取消作业可重试。`});}
    persist();render();if(currentDetail && $('#detail-dialog').open)detail(currentDetail);
    const count=results.filter(r=>r.success).length;
    showAction('重试结果','操作结果已更新，可返回队列查看属性及活动记录。',`<div class="scope-summary"><strong>${count} 条已重试</strong> · ${results.length-count} 条未执行</div>${results.map(r=>scopeRow(r.job,'result',r)).join('')}`,'<button class="button primary" data-action="close-action">完成</button>');
  }
  function resetPreview() {
    showAction('恢复最初的演示队列？','将恢复 data.json 中的 12 条作业与初始活动记录。',`<div class="summary-box"><p>本地重试、复核确认和优先级调整记录将被清除，已选作业与筛选条件也会清空。</p></div>`,'<button class="button" data-action="close-action">保留当前状态</button><button class="button primary" data-action="reset-confirm">恢复演示队列</button>');
  }
  $('#owner-filter').innerHTML='<option value="">全部负责人</option>'+data.owners.map(owner=>`<option value="${owner.id}">${escape(owner.name)}</option>`).join('');
  $('#search').addEventListener('input',event=>{filters.query=event.target.value;render()});
  $('#owner-filter').addEventListener('change',event=>{filters.owner=event.target.value;render()});
  $('#sort').addEventListener('change',event=>{filters.sort=event.target.value;render()});
  $('#status-tabs').addEventListener('click',event=>{const button=event.target.closest('[data-status]');if(button){filters.status=button.dataset.status;render()}});
  $('#clear-filters').addEventListener('click',clearFilters);
  $('#reset-button').addEventListener('click',resetPreview);
  $('#clear-selection').addEventListener('click',()=>{selected.clear();render()});
  $('#inspect-selection').addEventListener('click',inspectSelection);
  $('#retry-selected').addEventListener('click',()=>previewRetry(selected));
  document.addEventListener('change',event=>{
    if(event.target.matches('[data-select]')){const id=event.target.dataset.select;if(event.target.checked)selected.add(id);else selected.delete(id);render();}
    if(event.target.id==='select-all'||event.target.id==='mobile-select-all'){for(const job of visibleJobs()){if(event.target.checked)selected.add(job.id);else selected.delete(job.id)}render();}
  });
  document.addEventListener('click',event=>{
    const open=event.target.closest('[data-open]');if(open){detail(open.dataset.open);return}
    const remove=event.target.closest('[data-remove]');if(remove){selected.delete(remove.dataset.remove);render();inspectSelection();return}
    const button=event.target.closest('[data-action]');if(!button)return;
    const action=button.dataset.action;
    if(action==='close-action')$('#action-dialog').close();
    if(action==='close-detail')$('#detail-dialog').close();
    if(action==='clear-filters')clearFilters();
    if(action==='reset')resetPreview();
    if(action==='execute-retry')executeRetry();
    if(action==='retry-one')previewRetry([currentDetail]);
    if(action==='save-priority'){
      const job=jobs.find(j=>j.id===currentDetail),value=$('#detail-priority').value;
      if(!job||!can(job,'change_priority')||!data.rules.change_priority.allowed_values.includes(value))return;
      if(job.priority===value){toast('优先级未变化，无需保存。');return}
      const previous=job.priority;job.priority=value;
      appendActivity(job,data.rules.change_priority.activity_action,`本地用户将优先级从“${data.priority_labels[previous]}”调整为“${data.priority_labels[value]}”。`,new Date().toISOString());
      persist();render();detail(job.id);toast('优先级已保存。');
    }
    if(action==='approve-preview'){
      const job=jobs.find(j=>j.id===currentDetail);if(!job||!can(job,'approve_review'))return;
      showAction('确认复核完成？',`${job.id} · ${escape(job.name)}`,`<div class="summary-box needs_review"><p>${escape(job.summary)}</p></div><p>确认后标记为完成，并清除当前 ${num(job.open_issue_count)} 项问题。原始说明保留在活动记录中。</p>`,'<button class="button" data-action="close-action">继续核对</button><button class="button primary" data-action="approve-confirm">确认并标记完成</button>');
    }
    if(action==='approve-confirm'){
      const job=jobs.find(j=>j.id===currentDetail);if(!job||!applyRule(job,'approve_review'))return;
      persist();render();$('#action-dialog').close();detail(job.id);toast('复核已确认，作业标记为完成。');
    }
    if(action==='reset-confirm'){
      jobs=clone(data.jobs);selected.clear();filters={query:'',status:'',owner:'',sort:'submitted_at-desc'};
      $('#search').value='';$('#owner-filter').value='';$('#sort').value=filters.sort;currentDetail=null;pendingIds=[];
      persist();render();$('#action-dialog').close();$('#detail-dialog').close();toast('已恢复最初的 12 条演示作业。');
    }
  });
  for(const dialog of document.querySelectorAll('dialog'))dialog.addEventListener('click',event=>{if(event.target===dialog){const bounds=dialog.getBoundingClientRect();if(event.clientX<bounds.left||event.clientX>bounds.right||event.clientY<bounds.top||event.clientY>bounds.bottom)dialog.close()}});
  render();
})();
