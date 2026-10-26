export function findJobs(jobs, {query = '', status = '', owner = '', sort = 'submitted_at', direction = 'desc'}, data) {
  const q = query.trim().toLocaleLowerCase();
  const result = jobs.filter(job => (!q || data.rules.search_fields.some(field => String(job[field]).toLocaleLowerCase().includes(q))) && (!status || job.status === status) && (!owner || job.owner_id === owner));
  return result.sort((a, b) => {
    if (sort === 'records_total') {
      if (a.records_total === null) return b.records_total === null ? a.id.localeCompare(b.id) : 1;
      if (b.records_total === null) return -1;
    }
    let diff = sort === 'priority' ? data.priority_order.indexOf(a.priority) - data.priority_order.indexOf(b.priority) : sort === 'records_total' ? a.records_total - b.records_total : new Date(a.submitted_at) - new Date(b.submitted_at);
    return (direction === 'desc' ? -diff : diff) || a.id.localeCompare(b.id);
  });
}

export function applyOperation(jobs, ids, action, data, value, now = new Date().toISOString()) {
  const rule = data.rules[action];
  const results = [];
  const wanted = new Set(ids);
  const nextJobs = jobs.map(job => {
    if (!wanted.has(job.id)) return job;
    if (!rule.allowed_statuses.includes(job.status)) {
      results.push({id: job.id, ok: false, message: `当前为${data.status_labels[job.status]}，不允许${action === 'batch_retry' ? '重试' : action === 'approve_review' ? '复核确认' : '修改优先级'}。`});
      return job;
    }
    if (action === 'change_priority' && (!rule.allowed_values.includes(value) || job.priority === value)) {
      results.push({id: job.id, ok: false, message: job.priority === value ? '优先级未变化，未新增活动记录。' : '优先级无效。'});
      return job;
    }
    const next = structuredClone(job);
    let message = rule.activity_message;
    if (action === 'change_priority') {
      message = `本地用户将优先级从「${data.priority_labels[job.priority]}」调整为「${data.priority_labels[value]}」。`;
      next.priority = value;
    } else {
      Object.assign(next, rule.set_fields);
      next.status = rule.new_status;
      message = `本地用户操作：${message}`;
    }
    next.updated_at = now;
    next.activity.push({id: `${next.id}-local-${now}-${next.activity.length}`, at: now, actor_id: null, action: rule.activity_action, message});
    results.push({id: next.id, ok: true, message: action === 'batch_retry' ? '已重新加入本地待处理队列，处理进度已重置。' : action === 'approve_review' ? '已确认复核并标记为完成。' : '优先级已更新。'});
    return next;
  });
  return {jobs: nextJobs, results};
}
