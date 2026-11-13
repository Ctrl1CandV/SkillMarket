// Regression test for frontend-craft/scripts/pagecheck.mjs: known-bad page must be caught, known traps must stay quiet.
// Usage: node test_pagecheck.mjs   (needs FC_NODE_MODULES / FC_CHROME like the script itself)
import { execFileSync } from 'node:child_process'; import fs from 'node:fs'; import path from 'node:path'; import os from 'node:os'; import assert from 'node:assert/strict'; import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url)), root = path.resolve(here, '../../..'), script = path.join(root, 'frontend-craft/scripts/pagecheck.mjs');
const out = fs.mkdtempSync(path.join(os.tmpdir(), 'pagecheck-test-'));
const run = (file, extra = []) => { const text = execFileSync(process.execPath, [script, file, '--out', out, '--sizes', '1280x800,390x844', ...extra], { encoding: 'utf8' });
  return { text, views: JSON.parse(fs.readFileSync(path.join(out, path.basename(file, '.html') + '-check.json'), 'utf8')).views }; };
let n = 0; const ok = (cond, msg) => { assert.ok(cond, msg); n++; };

const bad = run(path.join(here, 'pagecheck/bad.html')), [d, m] = bad.views;
ok(d.script_errors.some(e => e.includes('故意的脚本错误')), 'script error reported');
ok(d.scroll_x && d.sticking_out.some(c => c.width >= 1900), 'sideways scroll and its cause');
ok(d.overlapping.some(o => (o.a + o.b).includes('早上') && (o.a + o.b).includes('中午')), 'overlapping text');
ok(d.small_text.some(s => s.svg && s.size < 6), 'tiny text inside a scaled SVG');
ok(d.line_start_punctuation.some(s => s.text.includes('⏎ 。')), 'full stop at the start of a line');
ok(d.one_char_per_line.some(s => s.text.startsWith('被挤成')), 'one character per line');
ok(d.low_contrast.some(s => s.text.includes('灰字')), 'low contrast');
ok(d.clipped.some(s => s.text.includes('裁掉')), 'clipped text');
ok(m.small_taps.some(t => t.w === 24 && t.h === 24), 'small touch target on the phone size');
ok(d.small_taps_count === 0, 'touch targets are only checked on phone widths');
ok(d.broken_values.some(b => b.where === 'text' && b.value.includes('NaN 件')), 'NaN in visible text');
ok(d.broken_values.some(b => b.where === 'style' && b.value.includes('NaN%')) && d.broken_values.some(b => b.where === 'title'), 'NaN / undefined in a style and a tooltip');
ok(/finding\(s\)/.test(bad.text) && /Open them/.test(bad.text), 'summary tells the reader to open the screenshots');

const good = run(path.join(here, 'pagecheck/good.html'));
for (const v of good.views) for (const key of ['overlapping', 'small_text', 'line_start_punctuation', 'one_char_per_line', 'low_contrast', 'clipped', 'small_taps', 'script_errors', 'broken_values'])
  ok(v[key].length === 0, `${v.viewport}: ${key} should be empty, got ${JSON.stringify(v[key])}`);
ok(good.views.every(v => !v.scroll_x), 'no sideways scroll'); ok(/Nothing measurable found/.test(good.text), 'clean summary');
for (const f of fs.readdirSync(out)) if (f.endsWith('-first.png')) ok(fs.statSync(path.join(out, f)).size > 2000, 'screenshot written');

// every starter that ships with the skill must be free of the hard errors
const starters = path.join(root, 'frontend-craft/assets/starters');
if (fs.existsSync(starters)) for (const dir of fs.readdirSync(starters)) { const p = path.join(starters, dir, 'index.html'); if (!fs.existsSync(p)) continue;
  for (const v of run(p).views) { ok(v.script_errors.length === 0, `${dir} ${v.viewport}: script errors ${v.script_errors}`); ok(!v.scroll_x, `${dir} ${v.viewport}: scrolls sideways`);
    ok(v.overlapping.length === 0, `${dir} ${v.viewport}: overlapping ${JSON.stringify(v.overlapping)}`); ok(v.one_char_per_line.length === 0, `${dir} ${v.viewport}: squeezed`); ok(v.low_contrast_count === 0, `${dir} ${v.viewport}: low contrast ${JSON.stringify(v.low_contrast)}`);
    ok(v.broken_values_count === 0, `${dir} ${v.viewport}: broken values ${JSON.stringify(v.broken_values)}`); } }
fs.rmSync(out, { recursive: true, force: true });
console.log(`pagecheck: ${n} checks passed`);
