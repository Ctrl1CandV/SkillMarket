import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {findJobs,applyOperation} from './store.mjs';
const data=JSON.parse(await readFile(new URL('./data.json',import.meta.url),'utf8'));
const initial=structuredClone(data.jobs), now='2026-10-26T12:00:00+08:00';
for(const direction of ['asc','desc']) assert.equal(findJobs(initial,{sort:'records_total',direction},data).at(-1).id,'IMP-20261026-009');
assert.equal(findJobs(initial,{query:'reading_index_doi_sources.jsonl'},data)[0].id,'IMP-20261026-008');
assert.equal(findJobs(initial,{status:'failed',owner:'owner-03'},data).length,1);
assert.equal(findJobs(initial,{query:'no-matching-job'},data).length,0);
assert.equal(findJobs([],{query:''},data).length,0);
const mixed=applyOperation(initial,['IMP-20261026-003','IMP-20261026-006','IMP-20261026-011'],'batch_retry',data,null,now);
assert.equal(mixed.results.filter(r=>r.ok).length,2);
for(const id of ['IMP-20261026-003','IMP-20261026-006']){
 const before=initial.find(j=>j.id===id),after=mixed.jobs.find(j=>j.id===id);
 assert.equal(after.status,'queued');assert.equal(after.records_processed,0);assert.equal(after.open_issue_count,0);assert.equal(after.issue_code,null);assert.equal(after.updated_at,now);
 assert.deepEqual(after.activity.slice(0,-1),before.activity);assert.equal(after.activity.at(-1).action,'retried');
 for(const field of data.rules.batch_retry.retain_fields)assert.deepEqual(after[field],before[field]);
}
assert.deepEqual(mixed.jobs.find(j=>j.id.endsWith('011')),initial.find(j=>j.id.endsWith('011')));
const approved=applyOperation(initial,['IMP-20261026-001'],'approve_review',data,null,now).jobs.find(j=>j.id.endsWith('001'));
assert.equal(approved.status,'completed');assert.equal(approved.records_processed,12480);assert.equal(approved.open_issue_count,0);assert.equal(approved.activity.length,3);
const same=applyOperation(initial,['IMP-20261026-001'],'change_priority',data,'high',now);assert.deepEqual(same.jobs,initial);
const changed=applyOperation(initial,['IMP-20261026-001'],'change_priority',data,'low',now).jobs.find(j=>j.id.endsWith('001'));assert.equal(changed.priority,'low');assert.equal(changed.activity.length,3);assert.match(changed.activity.at(-1).message,/高.*低/);
assert.deepEqual(initial,data.jobs);
console.log('PASS: search/filter; empty result/queue; unknown total both directions; mixed retry with preserved fields/history; approval; priority changes/no-op; source immutability.');
