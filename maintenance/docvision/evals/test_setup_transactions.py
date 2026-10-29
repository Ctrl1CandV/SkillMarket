"""Offline install transactions: subprocess boundaries mocked; no downloads."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'docvision' / 'scripts'))
from dv import config, setup_cmd, setup_history, util
from dv.base import DocVisionError


class SetupTransactionsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='docvision-setup-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.cfg = self.root / 'settings' / 'config.json'
        self.sample = self.root / 'sample.pdf'
        self.sample.write_bytes(b'%PDF offline fixture; subprocess is mocked')
        env = patch.dict(os.environ, {'DOCVISION_CONFIG': str(self.cfg), 'DOCVISION_MODELS': '',
                                     'MINERU_HOME': '', 'PADDLE_PDX_CACHE_HOME': ''})
        env.start(); self.addCleanup(env.stop)
        for obj, name, value in ((util, 'app_dir', self.root / 'app'),
                                  (util, 'gpu_summary', {'available': False}),
                                  (setup_cmd, '_uv', 'uv')):
            mock = patch.object(obj, name, return_value=value)
            mock.start(); self.addCleanup(mock.stop)
        self.old = self.root / 'old-env'
        self._make_runtime(self.old)
        metadata = self.old / 'Lib/site-packages/mineru-4.0.11.dist-info/METADATA'
        metadata.parent.mkdir(parents=True)
        metadata.write_text('Name: mineru\nVersion: 4.0.11\n\n', encoding='utf-8')
        self.models = self.root / 'old-models'
        self.models.mkdir()
        (self.models / 'weights').write_bytes(b'old weights')
        config.save({'core': {'python': str(util.env_python(self.old))},
                     'models_dir': str(self.root / 'models'),
                     'engines': {'mineru': {'python': str(util.env_python(self.old)),
                                           'model_home': str(self.models)}},
                     'remote': {'consent': 'remote'}, 'output': {'default_dir': 'my-results'}})
        self.before = self.cfg.read_bytes()
        self.calls = []

    def _make_runtime(self, prefix):
        python = util.env_python(prefix)
        python.parent.mkdir(parents=True, exist_ok=True)
        python.touch()
        util.env_bin(prefix).mkdir(parents=True, exist_ok=True)
        (util.env_bin(prefix) / ('mineru-kit.exe' if util.IS_WINDOWS else 'mineru-kit')).touch()

    def process(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if command[0] == 'uv' and command[1] == 'venv':
            self._make_runtime(Path(command[-1]))
        if command[0] == 'uv' and command[1] == 'pip':
            # Snapshot exists, and active defaults remain unchanged during install.
            self.assertEqual(self.cfg.read_bytes(), self.before)
            records = setup_cmd.history()
            self.assertEqual(records[0]['state'], 'installing')
            _, record = setup_history.read(records[0]['id'])
            self.assertEqual(record['versions_before']['engines.mineru']['packages']['mineru'], '4.0.11')
            self.assertNotIn(str(util.env_python(self.old)), command)
        if '-c' in command and command[command.index('-c') + 1] == config.PADDLE_CHECK:
            return subprocess.CompletedProcess(command, 0, json.dumps({'dependencies': {'ok': True}}), '')
        if 'download' in command:
            Path(kwargs['env']['MINERU_HOME']).mkdir(parents=True, exist_ok=True)
        if 'convert' in command:
            candidate = util.read_json(Path(kwargs['env']['DOCVISION_CONFIG']))
            self.assertEqual(self.cfg.read_bytes(), self.before)
            self.assertEqual(kwargs['env']['DOCVISION_MODELS'], '')
            self.assertNotEqual(candidate['engines']['mineru']['model_home'], str(self.models))
            self.assertIn('--pages', command)
            self.assertEqual(command[command.index('--pages') + 1], '2')
            self.assertEqual(command[command.index('--mode') + 1], 'ocr')
            payload = {'results': [{'state': 'done', 'pages': 1, 'qa': 'pass',
                                    'provider': 'mineru-local'}]}
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), '')
        if '-c' in command and command[command.index('-c') + 1] == setup_cmd._CORE_SMOKE:
            return subprocess.CompletedProcess(command, 0, json.dumps({'state': 'done', 'pages': 1}), '')
        return subprocess.CompletedProcess(command, 0, 'help', '')

    def invoke(self, profile='mineru', **kwargs):
        defaults = {'manager': 'uv', 'yes': True, 'sample': str(self.sample), 'sample_page': 2}
        defaults.update(kwargs)
        with contextlib.redirect_stdout(io.StringIO()):
            return setup_cmd.run(profile, **defaults)

    def test_success_switches_only_after_validation_and_rollback_preserves_files(self):
        with patch.object(util, 'run', side_effect=self.process):
            self.assertEqual(self.invoke(), 0)
        saved = config.load()
        new_python = Path(saved['engines']['mineru']['python'])
        self.assertNotEqual(new_python, util.env_python(self.old))
        self.assertTrue(new_python.is_file())
        self.assertIn('installations', saved['engines']['mineru']['model_home'])
        self.assertEqual(saved['core']['python'], str(util.env_python(self.old)))
        self.assertEqual(saved['remote']['consent'], 'remote')
        selected = setup_cmd.history()[0]['id']
        self.assertEqual(setup_cmd.history()[0]['state'], 'activated')
        self.assertEqual((self.models / 'weights').read_bytes(), b'old weights')
        # Preserve a later independent preference change across rollback.
        saved['remote']['consent'] = 'local-only'
        config.save(saved)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup_cmd.rollback(selected, yes=True), 0)
        restored = config.load()
        self.assertEqual(restored['engines']['mineru']['python'], str(util.env_python(self.old)))
        self.assertEqual(restored['engines']['mineru']['model_home'], str(self.models))
        self.assertEqual(restored['remote']['consent'], 'local-only')
        self.assertTrue(new_python.is_file())
        rollback_record = next(item for item in setup_cmd.history() if item['kind'] == 'rollback')
        with contextlib.redirect_stdout(io.StringIO()):
            setup_cmd.rollback(rollback_record['id'], yes=True)
        self.assertEqual(config.load()['engines']['mineru']['python'], str(new_python))

    def test_install_failure_keeps_previous_config_and_journals_failure(self):
        def fail(command, **kwargs):
            result = self.process(command, **kwargs)
            if command[:3] == ['uv', 'pip', 'install']:
                return subprocess.CompletedProcess(command, 1, '', 'disk full')
            return result
        with patch.object(util, 'run', side_effect=fail), self.assertRaisesRegex(SystemExit, 'disk full'):
            self.invoke()
        self.assertEqual(self.cfg.read_bytes(), self.before)
        self.assertEqual(setup_cmd.history()[0]['state'], 'failed')
        self.assertFalse(any('convert' in command for command, _ in self.calls))

    def test_failed_or_empty_page_never_activates_candidate(self):
        for result in ({'state': 'failed', 'pages': 1, 'qa': 'fail'},
                       {'state': 'done', 'pages': 0, 'qa': 'pass'},
                       {'state': 'done', 'pages': 1, 'qa': 'warn'}):
            def invalid(command, **kwargs):
                outcome = self.process(command, **kwargs)
                if 'convert' in command:
                    return subprocess.CompletedProcess(command, 0, json.dumps({'results': [result]}), '')
                return outcome
            with self.subTest(result=result), patch.object(util, 'run', side_effect=invalid), \
                 self.assertRaisesRegex(DocVisionError, 'verified page'):
                self.invoke()
            self.assertEqual(self.cfg.read_bytes(), self.before)

    def test_dry_run_never_writes_even_with_missing_sample(self):
        initial = {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        with patch.object(util, 'run', side_effect=AssertionError('dry run subprocess')):
            self.assertEqual(self.invoke(dry_run=True, sample=None), 0)
        after = {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        self.assertEqual(initial, after)
        self.assertFalse(setup_history.root().exists())
        self.assertFalse((self.root / 'app').exists())

    def test_ocr_requires_sample_before_snapshot_or_install(self):
        with patch.object(util, 'run', side_effect=AssertionError('no install')), self.assertRaisesRegex(SystemExit, '--sample'):
            self.invoke(sample=None)
        self.assertFalse(setup_history.root().exists())
        self.assertEqual(self.cfg.read_bytes(), self.before)

    def test_core_uses_generated_text_validation_without_user_sample(self):
        with patch.object(util, 'run', side_effect=self.process):
            self.assertEqual(self.invoke('core', sample=None), 0)
        self.assertNotEqual(config.load()['core']['python'], str(util.env_python(self.old)))
        self.assertTrue(any(setup_cmd._CORE_SMOKE in command for command, _ in self.calls))

    def test_activation_preserves_concurrent_consent_but_rejects_runtime_changes(self):
        before = config.load()
        candidate = copy.deepcopy(before)
        candidate['core']['python'] = 'new-python'
        current = copy.deepcopy(before)
        current['remote']['consent'] = 'local-only'
        config.save(current)
        setup_history.activate(before, candidate, ['core'])
        self.assertEqual(config.load()['remote']['consent'], 'local-only')
        with self.assertRaisesRegex(DocVisionError, 'changed during installation'):
            setup_history.activate(before, candidate, ['core'])

    def test_rollback_dry_run_no_mutation_and_missing_old_runtime_rejected(self):
        with patch.object(util, 'run', side_effect=self.process):
            self.invoke()
        selected = setup_cmd.history()[0]['id']
        before = self.cfg.read_bytes()
        histories = setup_cmd.history()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup_cmd.rollback(selected, dry_run=True), 0)
            self.assertEqual(setup_cmd.rollback(selected), 2)
        self.assertEqual(self.cfg.read_bytes(), before)
        self.assertEqual(setup_cmd.history(), histories)
        util.env_python(self.old).unlink()
        with self.assertRaisesRegex(DocVisionError, 'missing'), contextlib.redirect_stdout(io.StringIO()):
            setup_cmd.rollback(selected, yes=True)
        self.assertEqual(self.cfg.read_bytes(), before)

    def test_install_helper_refuses_existing_prefix(self):
        with patch.object(util, 'run', side_effect=AssertionError('must not mutate')):
            for manager in ('uv', 'conda'):
                with self.subTest(manager=manager), self.assertRaisesRegex(SystemExit, 'already exists'):
                    setup_cmd._install_env('docvision-test', ['pillow'], manager=manager, prefix=self.old)

    def test_atomic_config_write_failure_keeps_old_default(self):
        real_save = config.save
        def fail(data):
            if data['engines']['mineru']['python'] != str(util.env_python(self.old)):
                raise OSError('config disk full')
            return real_save(data)
        with patch.object(util, 'run', side_effect=self.process), patch.object(config, 'save', side_effect=fail), \
             self.assertRaisesRegex(OSError, 'disk full'):
            self.invoke()
        self.assertEqual(self.cfg.read_bytes(), self.before)
        self.assertEqual(setup_cmd.history()[0]['state'], 'failed')

    def test_rollback_refuses_missing_model_directory(self):
        with patch.object(util, 'run', side_effect=self.process):
            self.invoke()
        selected = setup_cmd.history()[0]['id']
        before = self.cfg.read_bytes()
        (self.models / 'weights').unlink()
        self.models.rmdir()
        with self.assertRaisesRegex(DocVisionError, 'model directory is missing'), contextlib.redirect_stdout(io.StringIO()):
            setup_cmd.rollback(selected, yes=True)
        self.assertEqual(self.cfg.read_bytes(), before)

    def test_new_global_root_preserves_other_installed_engine_models(self):
        data = config.load()
        data['engines']['paddleocr']['python'] = str(util.env_python(self.old))
        config.save(data)
        self.before = self.cfg.read_bytes()
        previous_home = config.model_home('paddlex')
        with patch.object(util, 'run', side_effect=self.process):
            self.invoke(models_dir=str(self.root / 'new-model-root'))
        self.assertEqual(config.model_home('paddlex'), previous_home)
        self.assertEqual(config.load()['models_dir'], str(self.root / 'new-model-root'))
        selected = setup_cmd.history()[0]['id']
        _, record = setup_history.read(selected)
        self.assertIn('engines.paddleocr', record['fields'])
        with contextlib.redirect_stdout(io.StringIO()):
            setup_cmd.rollback(selected, yes=True)
        self.assertEqual(config.model_home('paddlex'), previous_home)
        self.assertIsNone(config.load()['engines']['paddleocr'].get('model_home'))

    def test_rollback_journal_error_reports_that_config_was_restored(self):
        with patch.object(util, 'run', side_effect=self.process):
            self.invoke()
        selected = setup_cmd.history()[0]['id']
        real_update = setup_history.update
        def update(directory, record, **changes):
            if record['kind'] == 'rollback' and changes.get('state') == 'activated':
                raise OSError('journal disk full')
            return real_update(directory, record, **changes)
        output = io.StringIO()
        with patch.object(setup_history, 'update', side_effect=update), contextlib.redirect_stdout(output):
            self.assertEqual(setup_cmd.rollback(selected, yes=True), 0)
        self.assertEqual(config.load()['engines']['mineru']['python'], str(util.env_python(self.old)))
        self.assertIn('Configuration restored; journal update failed', output.getvalue())

    def test_transient_model_override_does_not_become_other_engine_pin(self):
        data = config.load()
        data['engines']['paddleocr']['python'] = str(util.env_python(self.old))
        config.save(data)
        self.before = self.cfg.read_bytes()
        previous_home = config.model_home('paddlex', use_environment=False)
        with patch.dict(os.environ, {'DOCVISION_MODELS': str(self.root / 'temporary-override')}), \
             patch.object(util, 'run', side_effect=self.process):
            self.invoke(models_dir=str(self.root / 'new-model-root'))
        self.assertEqual(config.model_home('paddlex'), previous_home)
        self.assertNotIn('temporary-override', config.load()['engines']['paddleocr']['model_home'])

    def test_transient_model_override_does_not_become_new_install_root(self):
        data = config.load()
        data['models_dir'] = None
        config.save(data)
        self.before = self.cfg.read_bytes()
        with patch.dict(os.environ, {'DOCVISION_MODELS': str(self.root / 'temporary-override')}), \
             patch.object(util, 'run', side_effect=self.process):
            self.invoke()
        active = Path(config.load()['engines']['mineru']['model_home'])
        self.assertTrue(active.is_relative_to(self.root / 'app/models/installations'))
        self.assertNotIn('temporary-override', str(active))

    def test_core_smoke_really_extracts_and_renders_its_generated_page(self):
        data = config.load()
        data['core']['python'] = sys.executable
        directory = self.root / 'core-smoke'
        reports = setup_cmd._validate_candidate(data, ['core'], directory,
                                               sample=None, sample_page=1, timeout=60)
        self.assertEqual(reports[0]['pages'], 1)
        self.assertEqual(reports[0]['provider'], 'text-local')
        self.assertTrue((directory / 'core-sample.pdf').is_file())
        self.assertEqual(self.cfg.read_bytes(), self.before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
