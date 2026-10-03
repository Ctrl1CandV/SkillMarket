// Run with Node >=18. No packages, network, subprocesses, or project writes.
import assert from 'node:assert/strict';
import { readFile, readdir, lstat, realpath } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const workspace = path.resolve(here, '../../..');
const root = path.join(workspace, 'plugins/agent-parliament-plugin');
const names = ['orchestrator', 'project-planner', 'adversary', 'code-developer', 'reviewer', 'untangler', 'memory-keeper'];
const reference = 'skills/orchestrator/references/process.md';
// 2026-10-04 用户决定移除宿主适配清单（.zcode-plugin/plugin.json），本检查只覆盖技能与共享流程文件。
const expectedFiles = [reference, ...names.map(n => `skills/${n}/SKILL.md`)].sort();
const files = [];
async function walk(dir) {
  for (const entry of await readdir(dir)) {
    const full = path.join(dir, entry);
    const info = await lstat(full);
    assert(!info.isSymbolicLink(), `Symlink forbidden: ${full}`);
    if (info.isDirectory()) await walk(full);
    else files.push(path.relative(root, full).split(path.sep).join('/'));
  }
}
await walk(root);
assert.deepEqual(files.sort(), expectedFiles, 'Runtime package must contain only declared minimal files');
const texts = {};
const forbidden = /\b(?:MCP|mcpServers|AgentParliament|peer_review|delegate_research|consensus|validate_approach|test_audit|independent_analysis|advisor_analysis|delegate_chain|delegate_dialogue|verify_implementation|project_dir|context_files)\b|[A-Za-z]:[\\/]|\/Users\/|\/home\/|\b(?:TODO|FIXME|TBD)\b/;
const rootReal = await realpath(root);
for (const rel of files) {
  const full = path.join(root, rel);
  const text = await readFile(full, 'utf8');
  assert(!forbidden.test(text), `External binding, hard path or placeholder: ${rel}`);
  if (!rel.endsWith('.md')) continue;
  texts[rel] = text;
  for (const match of text.matchAll(/\[[^\]]+\]\(([^)]+)\)/g)) {
    const target = path.resolve(path.dirname(full), match[1].split('#')[0]);
    const resolved = await realpath(target);
    const relative = path.relative(rootReal, resolved);
    assert(relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative), `Escaping reference: ${rel}`);
  }
}
for (const name of names) {
  const text = texts[`skills/${name}/SKILL.md`];
  assert(text.startsWith(`---\nname: ${name}\ndescription: `), `Skill discovery frontmatter: ${name}`);
  assert.match(text, /^---\nname: [^\n]+\ndescription: [^\n]+\n---\n/);
  assert(text.includes('共享流程契约'), `Shared contract not loaded: ${name}`);
}
const contract = texts[reference];
for (const phrase of ['AGENTS.md', 'CLAUDE.md', '单代理顺序执行', '不得称为独立评审', '不得自动提交', '未经授权', '另一个专用服务', '不建立空骨架', '轮次上限不是通过条件', '旧证据过期', '需求、范围、破坏性行为、风险接受和权限由用户决定']) {
  assert(contract.includes(phrase), `Missing policy anchor: ${phrase}`);
}
for (const stage of ['澄清', '规划', '质疑', '实现', '审查', '修复', '验证', '交付']) {
  assert(contract.includes(`| ${stage} |`), `Missing stage: ${stage}`);
}
assert(texts['skills/reviewer/SKILL.md'].includes('未经复核不能关闭问题'));
assert(texts['skills/code-developer/SKILL.md'].includes('必须再次交 reviewer'));
assert(texts['skills/memory-keeper/SKILL.md'].includes('不改审查裁决'));
console.log(`PASS structural checks: ${files.length} runtime files, ${names.length} discoverable skills, contained references and policy anchors`);

// This is a hand-authored executable protocol model, NOT the host's skill engine.
// Fixtures describe hypothetical actions; verify-pass below does NOT execute a build.
function simulate(events, {mode = 'self', independentRequired = false} = {}) {
  let state = 'start';
  let reviewed = false;
  let verified = false;
  let rounds = 0;
  const allowed = (states, event) => assert(states.includes(state), `Rejected ${event} from ${state}`);
  for (const event of events) {
    if (event === 'clarify') { allowed(['start'], event); state = 'clarified'; }
    else if (event === 'clarify-needs-user') { allowed(['start'], event); state = 'awaiting-user'; }
    else if (event === 'user-decides') { allowed(['awaiting-user'], event); state = 'clarified'; }
    else if (event === 'plan') { allowed(['clarified'], event); state = 'planned'; }
    else if (event === 'challenge-fail') { allowed(['planned'], event); state = 'needs-plan'; }
    else if (event === 'replan') { allowed(['needs-plan'], event); reviewed = verified = false; state = 'planned'; }
    else if (event === 'challenge-pass') { allowed(['planned'], event); state = 'ready'; }
    else if (event === 'implement') { allowed(['ready'], event); reviewed = verified = false; state = 'implemented'; }
    else if (event === 'review-fail-structural' || event === 'review-fail-local') {
      allowed(['implemented'], event); reviewed = verified = false;
      rounds++;
      state = rounds >= 3 ? 'blocked-budget' : event.endsWith('structural') ? 'needs-plan' : 'needs-fix';
    }
    else if (event === 'fix') { allowed(['needs-fix'], event); reviewed = verified = false; state = 'implemented'; }
    else if (event === 'review-pass') {
      allowed(['implemented'], event);
      assert(!independentRequired || mode === 'independent', 'Independent review missing');
      reviewed = true; state = 'reviewed';
    }
    else if (event === 'verify-pass') { allowed(['reviewed'], event); assert(reviewed); verified = true; state = 'verified'; }
    else if (event === 'verify-missing') { allowed(['reviewed'], event); state = 'awaiting-verification'; }
    else if (event === 'verify-fail') { allowed(['reviewed'], event); verified = false; state = 'needs-fix'; }
    else if (event === 'deliver') { allowed(['verified'], event); assert(reviewed && verified); state = 'delivered'; }
    else throw new Error(`Unknown event: ${event}`);
  }
  return state;
}
const suite = JSON.parse(await readFile(path.join(here, 'cases.json'), 'utf8'));
assert.equal(suite.kind, 'synthetic-protocol-cases-not-live-agent-runs');
assert.equal(suite.cases.length, 3);
for (const c of suite.cases) {
  assert(c.prompt && c.manualRubric.length >= 4 && c.forbiddenClaims.length >= 3);
  assert.equal(simulate(c.events, c), c.expected, c.id);
  console.log(`PASS synthetic case: ${c.id} -> ${c.expected}`);
}
const prefix = ['clarify', 'plan', 'challenge-pass', 'implement'];
const rejected = [
  ['pending-user', ['clarify-needs-user', 'plan']],
  ['unaccepted-plan', [...prefix, 'review-fail-structural', 'implement']],
  ['skip-rereview', [...prefix, 'review-fail-local', 'fix', 'verify-pass', 'deliver']],
  ['missing-verification', [...prefix, 'review-pass', 'verify-missing', 'deliver']],
  ['failed-verification', [...prefix, 'review-pass', 'verify-fail', 'deliver']],
  ['budget-is-not-pass', [...prefix, 'review-fail-local', 'fix', 'review-fail-local', 'fix', 'review-fail-local', 'review-pass']],
  ['fake-independent-review', [...prefix, 'review-pass'], {mode: 'self', independentRequired: true}]
];
for (const [id, events, options] of rejected) {
  assert.throws(() => simulate(events, options), undefined, id);
  console.log(`PASS rejected unsafe trace: ${id}`);
}
console.log('LIMIT: static assertions and synthetic protocol simulations only; no live agent, host installation, product build or runtime behavior verified.');
