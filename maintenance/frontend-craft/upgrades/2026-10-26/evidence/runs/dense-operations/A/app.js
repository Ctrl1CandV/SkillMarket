import {findJobs, applyOperation} from './store.mjs';
const $ = selector => document.querySelector(selector);
const key = 'xuliu-dense-operations-A-v1';
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = value => value === null ? '待统计' : value.toLocaleString('zh-CN');
const date = (value, full = false) => new Date(value).toLocaleString('zh-CN', {timeZone:'Asia/Shanghai', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', ...(full ? {year:'numeric', second:'2-digit'} : {})}).replaceAll('/','.');
const shortTime = value => new Date(value).toLocaleTimeString('zh-CN', {timeZone:'Asia/Shanghai', hour:'2-digit', minute:'2-digit'});
let data, jobs = [], selected = new Set(), detailId = null, toastTimer, pendingIds = [];
let filters = {query:'', status:'', owner:'', sort:'submitted_at', direction:'desc'};
const ownerName = id => data.owners.find(owner => owner.id === id)?.name || '本地演示系统';
const badge = job => `<span class="status ${job.status}">${escape(data.status_labels[job.status])}</span>`;
const priority = job => `<span class="priority ${job.priority}">${escape(data.priority_labels[job.priority])}</span>`;
const visible = () => findJobs(jobs, filters, data);

function notify(message) {
  $('#toast').textContent = message; $('#toast').hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').hidden = true, 4200);
}
function save() {
  try { localStorage.setItem(key, JSON.stringify({version:data.dataset_version, jobs})); $('#save-status').textContent = '变更已保存在此浏览器'; }
  catch { $('#error').hidden = false; $('#error').textContent = '浏览器未允许本地存储：本次操作仍然生效，但刷新后可能丢失。'; }
}
function render() {
  const active = document.activeElement;
  const focusSelector = active?.matches('.row-check') ? `.row-check[data-id="${active.dataset.id}"]` : active?.matches('[data-status]') ? `[data-status="${active.dataset.status}"]` : null;
  const rows = visible();
  $('#total-count').textContent = jobs.length;
  const tabs = [['','全部作业'],...Object.entries(data.status_labels)];
  $('#status-tabs').innerHTML = tabs.map(([status,label]) => `<button type="button" class="tab ${filters.status === status ? 'active' : ''}" aria-pressed="${filters.status === status}" data-status="${status}">${label}<span class="tab-count">${status ? jobs.filter(j => j.status === status).length : jobs.length}</span></button>`).join('');
  const filtered = filters.query || filters.owner || filters.status;
  $('#result-count').textContent = `显示 ${rows.length} / ${jobs.length} 项作业${filtered ? ' · 已应用筛选' : ' · 全部队列'}`;
  $('#clear-filters').hidden = !filtered;
  $('#footer-count').textContent = rows.length ? `当前结果 ${rows.length} 项 · 全部记录已显示` : '当前结果 0 项';
  $('#direction').textContent = filters.sort === 'submitted_at' ? (filters.direction === 'desc' ? '↓ 最新优先' : '↑ 最早优先') : filters.sort === 'priority' ? (filters.direction === 'asc' ? '↑ 高优先级在前' : '↓ 低优先级在前') : (filters.direction === 'desc' ? '↓ 从多到少' : '↑ 从少到多');
  $('#direction').setAttribute('aria-label', `切换排序方向，当前${$('#direction').textContent.slice(2)}`);
  $('#jobs').innerHTML = rows.map(job => {
    const percent = job.records_total ? Math.min(100, job.records_processed / job.records_total * 100) : null;
    return `<tr data-id="${job.id}" class="${selected.has(job.id) ? 'selected' : ''}">
      <td><input type="checkbox" class="row-check" aria-label="选择 ${job.id}" data-id="${job.id}" ${selected.has(job.id) ? 'checked' : ''}></td>
      <td><button class="job-title" data-open="${job.id}">${escape(job.name)}</button><div class="source-file">${escape(job.source_file)}</div><div class="job-meta">${job.id}</div></td>
      <td>${badge(job)}${job.open_issue_count ? `<div class="issue-count">${job.open_issue_count} 项${job.status === 'running' ? '警告' : '待检查'}</div>` : ''}</td>
      <td><div class="owner-name"><span class="owner-dot" aria-hidden="true">${escape(ownerName(job.owner_id).slice(0,1))}</span>${escape(ownerName(job.owner_id))}</div></td>
      <td class="number-cell"><b>${number(job.records_processed)}</b> <small>/ ${number(job.records_total)}</small>${percent !== null ? `<div class="progress ${job.status}" aria-hidden="true"><i style="width:${percent}%"></i></div>` : '<div class="hint" style="margin:4px 0 0;font-size:10px">总数尚未统计</div>'}</td>
      <td>${priority(job)}</td><td class="time-cell">${shortTime(job.submitted_at)}<br><small>10月26日</small></td>
      <td><button class="open-detail" aria-label="查看 ${job.id} 完整详情" data-open="${job.id}">›</button></td></tr>`;
  }).join('');
  $('#table-wrap').hidden = !rows.length;
  $('#empty').hidden = !!rows.length;
  if (!rows.length) $('#empty').innerHTML = jobs.length ? '<div class="empty-icon" aria-hidden="true">⌕</div><h3>没有匹配的作业</h3><p>试试其他关键词，或清除状态与负责人筛选。</p><button class="button" data-clear>清除全部筛选</button>' : '<div class="empty-icon" aria-hidden="true">▤</div><h3>队列中还没有作业</h3><p>当前本地队列为空。恢复演示队列可继续体验。</p><button class="button" data-reset>恢复演示队列</button>';
  $('#select-all').checked = rows.length > 0 && rows.every(j => selected.has(j.id));
  $('#select-all').indeterminate = rows.some(j => selected.has(j.id)) && !$('#select-all').checked;
  $('#select-all').disabled = !rows.length;
  const hidden = [...selected].filter(id => !rows.some(j => j.id === id)).length;
  $('#selection-bar').hidden = !selected.size;
  $('#selection-bar').innerHTML = `<span class="selection-summary"><strong>已选 ${selected.size} 项</strong> · 当前结果中 ${selected.size-hidden} 项${hidden ? ` · <span class="hidden-count">筛选外 ${hidden} 项仍保留选择</span>` : ''}</span><button class="text-button" data-scope>查看选择范围</button><button class="text-button" data-deselect>取消选择</button><button class="button primary" data-retry>批量重试</button>`;
  if (focusSelector) $(focusSelector)?.focus({preventScroll:true});
}

function showDetail(id, open = true) {
  detailId = id;
  const job = jobs.find(j => j.id === id); if (!job) return;
  const canPriority = data.rules.change_priority.allowed_statuses.includes(job.status);
  const canRetry = data.rules.batch_retry.allowed_statuses.includes(job.status);
  const canApprove = data.rules.approve_review.allowed_statuses.includes(job.status);
  const labels = {submitted:'提交作业',status_changed:'队列快照',retried:'重新加入队列',review_approved:'复核确认',priority_changed:'优先级调整'};
  $('#detail-content').innerHTML = `<div class="detail-header"><span>作业详情</span><button class="close-button" data-close-detail aria-label="关闭详情">×</button></div><div class="detail-body">
    <div class="detail-id">${job.id}</div><h2 id="detail-title">${escape(job.name)}</h2><div class="detail-badges">${badge(job)}${priority(job)}</div>
    <section class="detail-section"><h3>${job.open_issue_count ? `问题与处理说明 · ${job.open_issue_count} 项${job.status === 'running' ? '非阻断警告' : '待检查'}` : '处理说明'}</h3><div class="issue-block">${job.issue_code ? `<code>${escape(job.issue_code)}</code>` : ''}<p>${escape(job.summary)}</p></div></section>
    <section class="detail-section"><h3>作业属性</h3><dl class="attributes"><dt>源文件</dt><dd class="file">${escape(job.source_file)}</dd><dt>所属项目</dt><dd>${escape(job.project)}</dd><dt>负责人</dt><dd>${escape(ownerName(job.owner_id))} <span class="hint">(${job.owner_id})</span></dd><dt>记录总数</dt><dd>${number(job.records_total)}${job.records_total === null ? '（尚未统计）' : ' 条'}</dd><dt>已处理</dt><dd>${number(job.records_processed)} 条${job.records_total !== null ? ` / ${job.records_total ? (job.records_processed/job.records_total*100).toFixed(1) : '0'}%` : ' · 总数未知，不计算比例'}</dd><dt>待检查问题</dt><dd>${job.open_issue_count} 项</dd><dt>问题代码</dt><dd>${escape(job.issue_code || '无')}</dd><dt>提交时间</dt><dd>${date(job.submitted_at,true)}</dd><dt>最近更新</dt><dd>${date(job.updated_at,true)}</dd></dl></section>
    <section class="detail-section"><h3>处理作业</h3><div class="action-row">${canApprove ? '<button class="button primary" data-approve>确认复核完成</button>' : ''}${canRetry ? '<button class="button primary" data-retry-one>重试此作业</button>' : ''}${canPriority ? `<select id="detail-priority" aria-label="作业优先级">${Object.entries(data.priority_labels).map(([value,label]) => `<option value="${value}" ${value===job.priority?'selected':''}>${label}优先级</option>`).join('')}</select><button class="button" data-priority>保存优先级</button>` : ''}</div><p class="hint">${canApprove ? '确认后将标记为完成并清除待检查问题，原始说明保留在活动中。' : canRetry ? '重试将重置处理进度与问题标记，重新进入本地待处理队列。' : canPriority ? '待处理作业可调整优先级，不能重复加入重试队列。' : `当前${data.status_labels[job.status]}状态只可查看，不允许重试或调整优先级。`}</p></section>
    <section class="detail-section"><h3>活动记录 <span class="hint">${job.activity.length} 条 · 最新在前</span></h3><ol class="activity-list">${[...job.activity].reverse().map(event => `<li><span class="activity-label">${labels[event.action] || escape(event.action)}</span><div class="activity-meta"><span>${escape(ownerName(event.actor_id))}</span><time datetime="${event.at}">${date(event.at,true)}</time></div><p>${escape(event.message)}</p></li>`).join('')}</ol></section></div>`;
  if (open && !$('#detail').open) { $('#detail').showModal(); $('#detail').scrollTop = 0; }
  if (!open) $('[data-close-detail]').focus({preventScroll:true});
}
function openModal(title, body, footer) {
  $('#operation-content').innerHTML = `<div class="modal-heading"><h2 id="operation-title">${title}</h2><button class="close-button" data-close-operation aria-label="关闭对话框">×</button></div><div class="modal-body">${body}</div><div class="modal-footer">${footer}</div>`;
  if (!$('#operation').open) $('#operation').showModal();
  else $('[data-close-operation]').focus({preventScroll:true});
}
function scopeItem(job, content, tag, skip = false) {
  return `<li><div class="scope-detail"><span class="scope-id">${job.id}</span><strong>${escape(job.name)}</strong><p>${escape(content)}</p></div><span class="scope-tag ${skip?'skip':''}">${tag}</span></li>`;
}
function showScope(retry = false, ids = [...selected]) {
  pendingIds = [...ids];
  const items = ids.map(id => jobs.find(j => j.id === id)).filter(Boolean);
  const allowed = items.filter(job => data.rules.batch_retry.allowed_statuses.includes(job.status)).length;
  openModal(retry ? '检查重试范围' : `已选择 ${items.length} 项作业`, `<p>${retry ? `本次选择 ${items.length} 项，其中 ${allowed} 项可重试。重试后进度和问题标记归零，原始活动保留；其他项保持原状态。` : '以下编号为当前选择的完整范围，包含筛选后暂时隐藏的作业。'}</p><ul class="scope-list">${items.map(job => {
    const can = data.rules.batch_retry.allowed_statuses.includes(job.status);
    return scopeItem(job, retry ? (can ? `${data.status_labels[job.status]} → 待处理` : `当前为${data.status_labels[job.status]}，仅失败或已取消作业允许重试。`) : `${data.status_labels[job.status]} · ${ownerName(job.owner_id)}`, retry ? (can ? '可重试' : '将跳过') : (visible().some(j=>j.id===job.id)?'当前可见':'筛选外'), retry && !can);
  }).join('')}</ul>`, `<button class="button" data-close-operation>${retry ? '返回检查' : '关闭'}</button>${retry ? `<button class="button primary" data-execute-retry ${!allowed?'disabled':''}>重试 ${allowed} 项${items.length > allowed ? `，跳过 ${items.length-allowed} 项` : ''}</button>` : ''}`);
}
function mutate(ids, action, value) {
  const outcome = applyOperation(jobs, ids, action, data, value); jobs = outcome.jobs;
  if (outcome.results.some(r=>r.ok)) save();
  render(); if (detailId && $('#detail').open) showDetail(detailId, false);
  return outcome.results;
}
function clearFilters() { filters.query='';filters.owner='';filters.status='';$('#search').value='';$('#owner').value='';render(); }
function resetPrompt() {
  openModal('恢复最初演示队列', '<p>恢复 data.json 中的 12 条作业与初始活动记录，并清除本浏览器中的演示操作、当前筛选及选择。</p>', '<button class="button" data-close-operation>取消</button><button class="button primary" data-confirm-reset>恢复 12 条初始作业</button>');
}

async function init() {
  try {
    const response = await fetch('./data.json'); if (!response.ok) throw new Error('数据文件读取失败');
    data = await response.json(); jobs = structuredClone(data.jobs);
    try {
      const saved = JSON.parse(localStorage.getItem(key));
      if (saved) {
        if (saved.version !== data.dataset_version || !Array.isArray(saved.jobs) || saved.jobs.some(j=>!j.id || !Array.isArray(j.activity) || !data.status_labels[j.status])) throw new Error('invalid');
        jobs = saved.jobs; $('#save-status').textContent = '已恢复此浏览器的本地状态';
      }
    } catch { $('#error').hidden = false; $('#error').textContent='本地存档不可用，已载入初始演示队列。可使用“恢复演示队列”重建存档。'; }
    $('#owner').innerHTML += data.owners.map(owner=>`<option value="${owner.id}">${escape(owner.name)}</option>`).join('');
    render();
  } catch {
    $('#result-count').textContent='读取失败';$('#table-wrap').hidden=true;$('#error').hidden=false;
    $('#error').innerHTML='无法读取同目录的 data.json。请通过本地 HTTP 服务打开页面后刷新。<button class="text-button" data-reload>重新读取</button>';
  }
}
$('#search').addEventListener('input',event=>{filters.query=event.target.value;render()});
$('#owner').addEventListener('change',event=>{filters.owner=event.target.value;render()});
$('#sort').addEventListener('change',event=>{filters.sort=event.target.value;filters.direction=filters.sort==='priority'?'asc':'desc';render()});
$('#direction').addEventListener('click',()=>{filters.direction=filters.direction==='asc'?'desc':'asc';render()});
$('#clear-filters').addEventListener('click',clearFilters);
$('#reset').addEventListener('click',resetPrompt);
$('#select-all').addEventListener('change',event=>{visible().forEach(job=>event.target.checked?selected.add(job.id):selected.delete(job.id));render()});
document.addEventListener('change',event=>{if(event.target.matches('.row-check')){event.target.checked?selected.add(event.target.dataset.id):selected.delete(event.target.dataset.id);render()}});
document.addEventListener('click',event=>{
  const button=event.target.closest('button');if(!button)return;
  if (button.hasAttribute('data-status')) {filters.status=button.dataset.status;render()}
  if (button.dataset.open) showDetail(button.dataset.open);
  if (button.hasAttribute('data-close-detail')) $('#detail').close();
  if (button.hasAttribute('data-close-operation')) $('#operation').close();
  if (button.hasAttribute('data-clear')) clearFilters();
  if (button.hasAttribute('data-reset')) resetPrompt();
  if (button.hasAttribute('data-deselect')) {selected.clear();render()}
  if (button.hasAttribute('data-scope')) showScope();
  if (button.hasAttribute('data-retry')) showScope(true);
  if (button.hasAttribute('data-retry-one')) showScope(true,[detailId]);
  if (button.hasAttribute('data-priority')) {const result=mutate([detailId],'change_priority',$('#detail-priority').value);notify(result[0].message)}
  if (button.hasAttribute('data-approve')) {const result=mutate([detailId],'approve_review');notify(result[0].message)}
  if (button.hasAttribute('data-execute-retry')) {
    const results=mutate(pendingIds,'batch_retry'), success=results.filter(r=>r.ok).length;
    openModal('重试结果',`<p><strong>${success} 项已加入本地待处理队列</strong>，${results.length-success} 项未执行。队列不会自动推进，完整操作记录可在详情中查看。</p><ul class="scope-list">${results.map(r=>scopeItem(jobs.find(j=>j.id===r.id),r.message,r.ok?'已重试':'未执行',!r.ok)).join('')}</ul>`,'<button class="button primary" data-close-operation>返回队列</button>');
  }
  if (button.hasAttribute('data-confirm-reset')) {jobs=structuredClone(data.jobs);selected.clear();detailId=null;if($('#detail').open)$('#detail').close();$('#operation').close();$('#error').hidden=true;filters={query:'',status:'',owner:'',sort:'submitted_at',direction:'desc'};$('#search').value='';$('#owner').value='';$('#sort').value='submitted_at';save();render();notify('已恢复 12 条初始作业与全部原始活动。')}
  if (button.hasAttribute('data-reload')) location.reload();
});
document.addEventListener('keydown',event=>{if(event.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)&&!$('#detail').open&&!$('#operation').open){event.preventDefault();$('#search').focus()}});
for(const dialog of [$('#detail'),$('#operation')]) dialog.addEventListener('click',event=>{if(event.target===dialog){const rect=dialog.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)dialog.close()}});
init();
