"""Recheck the retained package into a NEW directory; never overwrite old evidence."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import json
import subprocess
import sys
import argparse
from zipfile import ZipFile

REPO = Path(__file__).resolve().parents[5]
UPGRADE = Path(__file__).resolve().parents[1]
ARCHIVE = UPGRADE / 'delivery/original-package.zip'
ORIGINAL_PREFIX = 'SkillMarket-upgrade/dev-only/maintenance/frontend-craft/upgrades/2026-10-26/'
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', required=True, type=Path,
                    help='New output directory; an existing directory is refused to preserve prior evidence.')
args = parser.parse_args()
REPORTS = args.output_dir.resolve()
REPORTS.mkdir(parents=True, exist_ok=False)

with ZipFile(ARCHIVE) as archive:
    original_files = {name.removeprefix(ORIGINAL_PREFIX): archive.read(name)
                      for name in archive.namelist() if name.startswith(ORIGINAL_PREFIX)}

def original_digest(name):
    return hashlib.sha256(original_files[name]).hexdigest()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def command_record(command):
    run = subprocess.run(command, cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace')
    record = dict(command=command, executed_at=NOW, process_exit_code=run.returncode, stdout=run.stdout, stderr=run.stderr)
    try:
        record['result'] = json.loads(run.stdout)
    except json.JSONDecodeError:
        pass
    return record

static_exits = []
for name, extra in [('static-check.json', []), ('resource-check.json', ['--release'])]:
    record = command_record([sys.executable, '-X', 'utf8', str(UPGRADE / 'tools/check_package.py'), '--repo-root', str(REPO), *extra])
    (REPORTS / name).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    static_exits.append(record['process_exit_code'])

frozen = json.loads((UPGRADE / 'evidence/candidate-snapshot-hashes.json').read_text(encoding='utf-8'))['files']
runtime = [{'path': p, 'expected': h, 'actual': digest(REPO / p), 'match': digest(REPO / p) == h} for p, h in frozen.items()]
final_files = {p.relative_to(REPO).as_posix(): digest(p) for folder in ['frontend-craft', 'product-design'] for p in (REPO / folder).rglob('*') if p.is_file()}
post_freeze_diff = {
    'added': sorted(set(final_files) - set(frozen)),
    'removed': sorted(set(frozen) - set(final_files)),
    'changed': [p for p in frozen if p in final_files and frozen[p] != final_files[p]],
    'meaning': 'Runs used the frozen snapshot. Additional resource evidence is not retroactively attributed to their construction; see post-freeze-resource-supplement.md.'
}
(REPORTS / 'runtime-hashes.json').write_text(json.dumps({'recorded_at': NOW, 'files': final_files}, ensure_ascii=False, indent=2), encoding='utf-8')
(REPORTS / 'post-freeze-diff.json').write_text(json.dumps(post_freeze_diff, ensure_ascii=False, indent=2), encoding='utf-8')
criteria = []
for name in ['PLAN.md', 'REQUIREMENTS.md', 'ACCEPTANCE.md', 'prompts/01-complete-and-evaluate.md', 'prompts/02-final-review.md', 'tools/check_package.py']:
    criteria.append({'path': name, 'original_sha256': original_digest(name), 'current_sha256': digest(UPGRADE / name), 'match': original_digest(name) == digest(UPGRADE / name)})
inputs = []
for scene in ['reading-evidence', 'dense-operations', 'public-exhibition']:
    for name in ['brief.md', 'data.json']:
        for label in ['A', 'B']:
            a, b = UPGRADE / 'evals' / scene / name, UPGRADE / 'evidence/runs' / scene / label / name
            inputs.append({'scene': scene, 'label': label, 'file': name, 'match': digest(a) == digest(b) == original_digest(f'evals/{scene}/{name}')})
diff = command_record(['git', '-c', 'core.safecrlf=false', 'diff', '--check'])
result = dict(executed_at=NOW, runtime_frozen_files=runtime, final_runtime_file_count=len(final_files), post_freeze_diff=post_freeze_diff, original_criteria_unchanged=criteria, paired_original_inputs=inputs, git_diff_check=diff,
              obsolete_adapter_absent=not (REPO / 'write-with-judgment/agents/openai.yaml').exists(),
              scope='Integrity and static checks only; no visual, behavioral or license verdict.')
(REPORTS / 'final-integrity.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'frozen_files_unchanged': all(x['match'] for x in runtime), 'added_runtime_files': len(post_freeze_diff['added']), 'criteria_unchanged': all(x['match'] for x in criteria), 'inputs_match': all(x['match'] for x in inputs), 'diff_check_exit': diff['process_exit_code']}))
sys.exit(0 if all(code == 0 for code in static_exits) and all(x['match'] for x in criteria)
         and all(x['match'] for x in inputs) and diff['process_exit_code'] == 0 else 1)
