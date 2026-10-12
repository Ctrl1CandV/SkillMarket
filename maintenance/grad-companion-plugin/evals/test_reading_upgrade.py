"""维护验收：仅使用独立临时目录内的合成记录，不读取个人记录。"""
import copy
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

WORKSPACE = Path(__file__).resolve().parents[3]
PLUGIN = Path(os.environ.get('GRAD_PLUGIN_ROOT', WORKSPACE / 'plugins/grad-companion-plugin')).resolve()
SCRIPTS = PLUGIN / 'skills/grad-radar/scripts'
TMP = Path(os.environ.get('GRAD_EVAL_TEMP', tempfile.gettempdir())).resolve()
TMP.mkdir(parents=True, exist_ok=True)
# GRAD_EVAL_TEMP can select an explicitly permitted temporary root.
spec = importlib.util.spec_from_file_location('survey_check', SCRIPTS / 'survey_check.py')
survey = importlib.util.module_from_spec(spec)
spec.loader.exec_module(survey)
config_spec = importlib.util.spec_from_file_location('radar_config', SCRIPTS / 'radar_config.py')
radar_config = importlib.util.module_from_spec(config_spec)
config_spec.loader.exec_module(radar_config)
fetch_spec = importlib.util.spec_from_file_location('arxiv_fetch', SCRIPTS / 'arxiv_fetch.py')
fetch = importlib.util.module_from_spec(fetch_spec)
fetch_spec.loader.exec_module(fetch)


def run(script, *args):
    return subprocess.run([sys.executable, '-B', str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding='utf-8',
                          env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'}, timeout=30)


class ReadingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='grad-reading-eval-', dir=TMP)
        self.repo = Path(self.temp.name).resolve()
        assert self.repo.is_relative_to(TMP.resolve())
        self.addCleanup(self.temp.cleanup)
        payload = self.repo / 'input.json'
        payload.write_text(json.dumps({'identifiers': {'arxiv_id': '2404.13501'}, 'title': 'Synthetic fixture',
                                     'source': {'version': 'v1', 'version_status': 'confirmed'}}), encoding='utf-8')
        out = run('reading_record.py', 'register', '--repo', self.repo, '--input-file', payload, '--json')
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.record_path = self.repo / '.grad/radar/papers/arxiv-2404.13501.json'
        self.content = self.repo / 'note.md'
        self.content.write_text('合成笔记，不是实际论文内容。', encoding='utf-8')

    def record(self):
        return json.loads(self.record_path.read_text(encoding='utf-8'))

    def save(self, basis='sections', mode='standard', *extra):
        return run('reading_record.py', 'save-note', '--repo', self.repo, '--paper', '2404.13501',
                   '--note-file', self.content, '--basis', basis, '--mode', mode, '--sections', 'S1', '--json', *extra)

    def note_path(self):
        return self.repo / '.grad' / self.record()['note']['path']

    def test_metadata_no_write(self):
        before = self.record_path.read_bytes()
        self.assertNotEqual(self.save('metadata').returncode, 0)
        self.assertEqual(before, self.record_path.read_bytes())
        self.assertIsNone(self.record()['note']['path'])

    def test_abstract_downgrade(self):
        self.assertEqual(self.save('abstract', 'deep').returncode, 0)
        self.assertEqual(self.record()['reading']['mode'], 'quick')

    def test_empty_and_comma_ranges_no_write(self):
        for value in ('', ', ,'):
            with self.subTest(value=value):
                before = self.record_path.read_bytes()
                out = self.save('sections', 'standard', '--sections', value)
                self.assertNotEqual(out.returncode, 0)
                self.assertEqual(before, self.record_path.read_bytes())

    def test_context_cannot_upgrade(self):
        for basis in ('abstract', 'sections'):
            self.assertEqual(self.save(basis, 'quick').returncode, 0)
            before = self.record_path.read_bytes()
            out = run('reading_record.py', 'update-context', '--repo', self.repo, '--paper', '2404.13501',
                      '--reading-mode', 'deep', '--json')
            self.assertNotEqual(out.returncode, 0)
            self.assertEqual(before, self.record_path.read_bytes())

    def test_omitted_version_not_inherited(self):
        self.assertEqual(self.save().returncode, 0)
        rec = self.record()
        self.assertEqual(rec['source']['version'], 'v1')
        self.assertIsNone(rec['note']['source_version'])
        self.assertIsNone(rec['note']['coverage_sources'][0]['source_version'])

    def test_merge_version_combinations(self):
        for first, second in (('v1', None), (None, 'v2'), ('v1', 'v2')):
            with self.subTest(first=first, second=second):
                opts = ['--new-path', f'radar/digest/combo-{first}-{second}.md']
                if first:
                    opts += ['--source-version', first]
                self.assertEqual(self.save('sections', 'standard', *opts).returncode, 0)
                opts = ['--merge', '--sections', 'S2']
                if second:
                    opts += ['--source-version', second]
                self.assertEqual(self.save('sections', 'standard', *opts).returncode, 0)
                note = self.record()['note']
                self.assertEqual(note['source_version'], first)
                self.assertEqual([s['source_version'] for s in note['coverage_sources']], [first, second])
                self.assertEqual(note['sections'], ['S1', 'S2'])

    def test_legacy_backfill(self):
        self.assertEqual(self.save('sections', 'standard', '--source-version', 'v1').returncode, 0)
        rec = self.record()
        rec['note'].pop('coverage_sources')
        self.record_path.write_text(json.dumps(rec), encoding='utf-8')
        self.assertEqual(self.save('sections', 'deep', '--source-version', 'v2', '--sections', 'S2', '--merge').returncode, 0)
        self.assertEqual([s['source_version'] for s in self.record()['note']['coverage_sources']], ['v1', 'v2'])

    def test_human_content_protected(self):
        self.assertEqual(self.save().returncode, 0)
        path = self.note_path()
        path.write_text(path.read_text(encoding='utf-8') + '\n人工批注', encoding='utf-8')
        before = path.read_bytes()
        self.assertNotEqual(self.save().returncode, 0)
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(self.save('sections', 'standard', '--merge').returncode, 0)
        self.assertIn('人工批注', path.read_text(encoding='utf-8'))
        self.assertEqual(self.save().returncode, 0)
        self.assertIn('人工批注', path.read_text(encoding='utf-8'))

    def test_unavailable_preserves_note(self):
        self.assertEqual(self.save().returncode, 0)
        before = self.note_path().read_bytes()
        self.assertNotEqual(self.save('unavailable').returncode, 0)
        self.assertEqual(self.save('unavailable', 'deep', '--record-failure', '测试获取失败').returncode, 0)
        self.assertEqual(before, self.note_path().read_bytes())
        self.assertEqual(self.record()['reading']['mode'], 'standard')

    def test_user_read_version_untouched(self):
        out = run('reading_record.py', 'set-status', '--repo', self.repo, '--paper', '2404.13501',
                  '--status', 'read', '--user-quote', '合成测试用户表示读完v1', '--read-version', 'v1', '--json')
        self.assertEqual(out.returncode, 0, out.stdout)
        before = self.record()['reading']
        self.assertEqual(self.save('sections', 'deep', '--source-version', 'v2').returncode, 0)
        after = self.record()['reading']
        for key in ('status', 'status_origin', 'status_updated_at', 'last_read_at', 'last_read_version', 'status_user_quote'):
            self.assertEqual(before[key], after[key])


class SurveyTests(unittest.TestCase):
    def setUp(self):
        self.outline = {'source_id': 'arxiv:2404.13501', 'version': 'v1', 'version_status': 'confirmed', 'sections': [
            {'id': 'abstract', 'kind': 'abstract'}, {'id': 'S1', 'kind': 'numbered'},
            {'id': 'S2', 'kind': 'numbered'}, {'id': 'bib', 'kind': 'bibliography'}]}
        self.coverage = {'source_id': 'arxiv:2404.13501', 'version': 'v1', 'sections': [
            {'id': sid, 'processed': True, 'checked': True, 'disposition': 'taught', 'guide_heading': sid}
            for sid in ('abstract', 'S1', 'S2')] + [
            {'id': 'bib', 'processed': False, 'checked': False, 'disposition': 'reference-only', 'reason': '保留索引'}],
            'assets': [{'id': 'F1', 'kind': 'figure', 'required': True, 'checked': True, 'basis': 'visual'}]}

    def check(self):
        return survey.check_coverage(self.outline, self.coverage)

    def test_ready_and_wrapped_outline(self):
        self.assertTrue(self.check()['coverage_ready'])
        self.assertTrue(survey.check_coverage({'ok': True, 'data': self.outline}, self.coverage)['coverage_ready'])
        self.assertIn('不证明', self.check()['verification_scope'])

    def test_middle_section_gap(self):
        self.coverage['sections'].pop(1)
        result = self.check()
        self.assertFalse(result['coverage_ready'])
        self.assertIn('未登记章节：S1', result['gaps'])

    def test_unknown_version(self):
        self.outline['version_status'] = 'unknown'
        self.assertFalse(self.check()['coverage_ready'])
        self.outline['version_status'] = 'cache-fallback'
        self.assertTrue(self.check()['coverage_ready'])
        self.outline['version'] = None
        self.assertFalse(self.check()['coverage_ready'])

    def test_version_mismatch(self):
        self.coverage['version'] = 'v2'
        self.assertFalse(self.check()['coverage_ready'])

    def test_same_version_different_paper_is_not_ready(self):
        self.coverage['source_id'] = 'arxiv:2210.03629'
        self.assertFalse(self.check()['coverage_ready'])
        self.assertIn('制作清单与原文身份不一致', self.check()['gaps'])

    def test_missing_identity_is_legacy_not_ready(self):
        self.coverage.pop('source_id')
        self.assertFalse(self.check()['coverage_ready'])
        self.assertIn('制作清单缺少 source_id', self.check()['gaps'])

    def test_arxiv_parser_id_is_accepted(self):
        self.outline.pop('source_id')
        self.outline['id'] = '2404.13501'
        self.assertTrue(self.check()['coverage_ready'])

    def test_fixed_journal_pdf_and_fingerprint_mismatch(self):
        for item in (self.outline, self.coverage):
            item.update(source_id='doi:10.0000/synthetic-fixture', version='published', source_sha256='a' * 64)
        self.assertTrue(self.check()['coverage_ready'])
        self.coverage['source_sha256'] = 'b' * 64
        self.assertFalse(self.check()['coverage_ready'])
        self.outline.pop('source_sha256')
        self.assertFalse(self.check()['coverage_ready'])

    def test_doi_identity_normalization(self):
        for item in (self.outline, self.coverage):
            item.update(source_id='doi:10.0000/SYNTHETIC', version='published', source_sha256='a' * 64)
        self.coverage['source_id'] = 'https://doi.org/10.0000/synthetic'
        self.assertTrue(self.check()['coverage_ready'])

    def test_guide_mapping_missing_and_fenced_heading(self):
        guide = '# abstract\n## S1\n## S2\n'
        self.assertTrue(survey.check_coverage(self.outline, self.coverage, guide)['coverage_ready'])
        self.assertFalse(survey.check_coverage(self.outline, self.coverage, '# abstract\n## S1')['coverage_ready'])
        guide = '# abstract\n## S1\n```markdown\n## S2\n```\n'
        self.assertFalse(survey.check_coverage(self.outline, self.coverage, guide)['coverage_ready'])

    def test_unchecked_optional_asset_needs_reason(self):
        self.coverage['assets'][0].update(required=False, checked=False, basis='caption-only')
        self.assertFalse(self.check()['coverage_ready'])
        self.coverage['assets'][0]['reason'] = '非关键背景示意，正文提供必要定义'
        self.assertTrue(self.check()['coverage_ready'])

    def test_unknown_section(self):
        self.coverage['sections'][1]['id'] = 'S99'
        with self.assertRaises(survey.InvalidManifest):
            self.check()

    def test_duplicate_and_invalid_outline(self):
        self.outline['sections'].append(copy.deepcopy(self.outline['sections'][0]))
        with self.assertRaises(survey.InvalidManifest):
            self.check()
        for value in ({'sections': []}, {'ok': False, 'data': self.outline}, {'sections': [{'id': 'S1', 'kind': 'made-up'}]}):
            with self.assertRaises(survey.InvalidManifest):
                survey.check_coverage(value, self.coverage)

    def test_non_string_enum_inputs_fail_cleanly(self):
        cases = [('outline-kind', {}), ('disposition', []), ('asset-kind', {}), ('basis', [])]
        for field, value in cases:
            with self.subTest(field=field):
                outline, coverage = copy.deepcopy(self.outline), copy.deepcopy(self.coverage)
                if field == 'outline-kind':
                    outline['sections'][0]['kind'] = value
                elif field == 'disposition':
                    coverage['sections'][0][field] = value
                else:
                    coverage['assets'][0]['kind' if field == 'asset-kind' else field] = value
                with self.assertRaises(survey.InvalidManifest):
                    survey.check_coverage(outline, coverage)
        self.outline['version_status'] = {}
        self.assertFalse(self.check()['coverage_ready'])

    def test_boolean_and_checked_guard(self):
        self.coverage['sections'][0]['processed'] = 'true'
        with self.assertRaises(survey.InvalidManifest):
            self.check()
        self.coverage['sections'][0]['processed'] = False
        with self.assertRaises(survey.InvalidManifest):
            self.check()

    def test_necessary_and_optional_appendix(self):
        self.outline['sections'].append({'id': 'A1', 'kind': 'appendix'})
        item = {'id': 'A1', 'processed': False, 'checked': False, 'disposition': 'reference-only', 'reason': '附加资源'}
        self.coverage['sections'].append(item)
        self.assertFalse(self.check()['coverage_ready'])
        item['required'] = False
        self.assertTrue(self.check()['coverage_ready'])

    def test_asset_basis_and_gap(self):
        asset = self.coverage['assets'][0]
        asset['basis'] = 'caption-only'
        with self.assertRaises(survey.InvalidManifest):
            self.check()
        asset['checked'] = False
        self.assertFalse(self.check()['coverage_ready'])
        asset['required'] = False
        asset['reason'] = '非关键背景图，正文提供所需上下文'
        self.assertTrue(self.check()['coverage_ready'])
        asset.update(kind='table', required=True, checked=True, basis='text')
        self.assertTrue(self.check()['coverage_ready'])

    def test_cli_readonly_exit_codes(self):
        with tempfile.TemporaryDirectory(prefix='grad-reading-eval-', dir=TMP) as folder:
            root = Path(folder).resolve()
            assert root.is_relative_to(TMP.resolve())
            outline, coverage = root / 'outline.json', root / 'coverage.json'
            outline.write_text(json.dumps(self.outline), encoding='utf-8')
            self.coverage['sections'].pop(1)
            coverage.write_text(json.dumps(self.coverage), encoding='utf-8')
            before = [p.read_bytes() for p in (outline, coverage)]
            args = ['--outline-file', outline, '--coverage-file', coverage, '--json']
            self.assertEqual(run('survey_check.py', *args).returncode, 0)
            self.assertEqual(run('survey_check.py', *args, '--require-ready').returncode, 2)
            self.assertEqual(before, [p.read_bytes() for p in (outline, coverage)])
            self.assertEqual(sorted(p.name for p in root.iterdir()), ['coverage.json', 'outline.json'])


class DailyContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='grad-reading-eval-', dir=TMP)
        self.repo = Path(self.temp.name).resolve()
        assert self.repo.is_relative_to(TMP.resolve())
        self.addCleanup(self.temp.cleanup)
        self.config = self.repo / '.grad/config.json'

    def init(self):
        out = run('radar_config.py', 'init', '--config', self.config, '--json')
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        return json.loads(self.config.read_text(encoding='utf-8'))

    def legacy_config(self):
        data = self.init()
        data.update(keywords=[['llm', 'agent']], categories=['cs.AI'],
                    thesis_rules={'synthetic_fixture': True})
        self.config.write_text(json.dumps(data), encoding='utf-8')
        return data

    def fetch_offline(self, *args):
        # 假响应仅替代网络；真实 main 仍解析参数、构建查询和处理结果。
        stdout = io.StringIO()
        with patch.object(sys, 'argv', ['arxiv_fetch.py', *map(str, args), '--no-dedup', '--json']), \
             patch.object(fetch, 'fetch_all', return_value=([], 0, 'synthetic://offline')) as network, \
             redirect_stdout(stdout):
            fetch.main()
        self.assertEqual(network.call_count, 1)
        return json.loads(stdout.getvalue())['data']

    def test_initial_config_has_no_research_preferences(self):
        data = self.init()
        self.assertEqual(data['keywords'], [])
        self.assertEqual(data['categories'], [])
        self.assertIsNone(data['reading_profile']['direction'])
        self.assertEqual(radar_config.validate_config(data), [])

    def test_unset_scope_fails_before_network_or_seen_write(self):
        self.init()
        before = self.config.read_bytes()
        stdout = io.StringIO()
        with patch.object(sys, 'argv', ['arxiv_fetch.py', '--config', str(self.config), '--json']), \
             patch.object(fetch, 'fetch_all') as network, \
             patch.object(fetch, 'load_seen_ids') as seen_read, \
             patch.object(fetch, 'append_seen') as seen_write, redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as stopped:
                fetch.main()
        self.assertEqual(stopped.exception.code, 1)
        self.assertEqual(json.loads(stdout.getvalue())['error'], 'BAD_ARGS')
        network.assert_not_called()
        seen_read.assert_not_called()
        seen_write.assert_not_called()
        self.assertEqual(self.config.read_bytes(), before)

    def test_current_cli_does_not_inherit_project_preferences(self):
        self.legacy_config()
        before = self.config.read_bytes()
        previous_directory = Path.cwd()
        try:
            os.chdir(self.repo)
            data = self.fetch_offline('--keywords', 'quantum,measurement', '--categories', 'quant-ph')
        finally:
            os.chdir(previous_directory)
        self.assertEqual(data['effective_params']['keyword_groups'], [['quantum', 'measurement']])
        self.assertEqual(data['effective_params']['categories'], ['quant-ph'])
        self.assertNotIn('llm', data['query'])
        self.assertNotIn('cs.AI', data['query'])
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(sorted(str(p.relative_to(self.repo)) for p in self.repo.rglob('*') if p.is_file()),
                         [str(Path('.grad/config.json'))])

    def test_explicit_cli_overrides_named_config_without_saving(self):
        self.legacy_config()
        before = self.config.read_bytes()
        data = self.fetch_offline('--config', self.config, '--keywords', 'graph,coloring',
                                  '--categories', '', '--days', '2')
        self.assertEqual(data['effective_params']['keyword_groups'], [['graph', 'coloring']])
        self.assertEqual(data['effective_params']['categories'], [])
        self.assertEqual(data['effective_params']['days'], 2)
        self.assertNotIn('llm', data['query'])
        self.assertNotIn('cs.AI', data['query'])
        self.assertEqual(self.config.read_bytes(), before)

    def test_legacy_configuration_remains_valid_and_read_only(self):
        data = self.legacy_config()
        before = self.config.read_bytes()
        result = radar_config.load_and_validate(self.config)
        self.assertTrue(result['ok'])
        self.assertEqual(result['data']['radar']['keywords'], data['keywords'])
        self.assertEqual(result['data']['radar']['categories'], data['categories'])
        self.assertEqual(self.config.read_bytes(), before)

    def test_empty_scope_does_not_allow_invalid_groups(self):
        data = self.init()
        for invalid in ([[]], [['']], [[False]], 'llm'):
            with self.subTest(invalid=invalid):
                candidate = {**data, 'keywords': invalid}
                self.assertTrue(radar_config.validate_config(candidate))
        self.assertTrue(radar_config.validate_config({**data, 'categories': [False]}))

    def test_remembered_reading_background_does_not_fill_query(self):
        self.init()
        out = run('radar_config.py', 'profile', '--config', self.config,
                  '--known-background', 'linear algebra', '--available-minutes', '20', '--json')
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        data = json.loads(self.config.read_text(encoding='utf-8'))
        self.assertEqual(data['reading_profile']['known_background'], ['linear algebra'])
        self.assertEqual(data['keywords'], [])
        self.assertEqual(data['categories'], [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
