"""Offline first-install regressions; only subprocess boundaries are mocked."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'docvision' / 'scripts'))
from dv import config, doctor, setup_cmd, util


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='docvision-onboarding-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cfg = self.root / 'settings' / 'config.json'
        self.env = patch.dict(os.environ, {
            'DOCVISION_CONFIG': str(self.cfg), 'DOCVISION_MODELS': '',
            'MINERU_HOME': '', 'PADDLE_PDX_CACHE_HOME': '',
            'LOCALAPPDATA': str(self.root / 'local'), 'APPDATA': str(self.root / 'roaming'),
            'XDG_DATA_HOME': str(self.root / 'data'), 'XDG_CONFIG_HOME': str(self.root / 'config'),
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.home = patch.object(Path, 'home', return_value=self.root)
        self.home.start()
        self.addCleanup(self.home.stop)
        self.no_process = patch.object(util, 'run', side_effect=AssertionError('unexpected subprocess'))
        self.no_process.start()
        self.addCleanup(self.no_process.stop)
        self.gpu = patch.object(util, 'gpu_summary', return_value={'available': False})
        self.gpu.start()
        self.addCleanup(self.gpu.stop)
        # These tests isolate dependency/install failures; transactional
        # single-page validation is exercised in test_setup_transactions.py.
        self.validation = patch.object(setup_cmd, '_validate_candidate', return_value=[{'state': 'done', 'pages': 1}])
        self.validation.start()
        self.addCleanup(self.validation.stop)
        self.sample = self.root / 'sample.pdf'
        self.sample.write_bytes(b'%PDF mocked OCR sample')

    def invoke(self, profile='core', **kwargs):
        if profile != 'core' and not kwargs.get('dry_run'):
            kwargs.setdefault('sample', str(self.sample))
        with patch.object(setup_cmd, '_uv', return_value='uv'), contextlib.redirect_stdout(io.StringIO()):
            return setup_cmd.run(profile, manager='uv', **kwargs)

    def runtime(self):
        prefix = self.root / 'runtime'
        python = util.env_python(prefix)
        python.parent.mkdir(parents=True, exist_ok=True)
        python.touch()
        util.env_bin(prefix).mkdir(parents=True, exist_ok=True)
        (util.env_bin(prefix) / ('mineru-kit.exe' if util.IS_WINDOWS else 'mineru-kit')).touch()
        return prefix

    def test_dry_run_with_models_override_does_not_change_configuration(self):
        config.save({'models_dir': str(self.root / 'original')})
        before = self.cfg.read_bytes()
        with patch.object(setup_cmd, '_install_env', return_value=(self.root / 'runtime', [])):
            self.assertEqual(self.invoke(dry_run=True, models_dir='planned-models'), 0)
        self.assertEqual(self.cfg.read_bytes(), before)

    def test_setup_persists_absolute_models_path_before_changing_projects(self):
        project = self.root / 'project'
        project.mkdir()
        previous = Path.cwd()
        self.addCleanup(os.chdir, previous)
        os.chdir(project)
        with patch.object(setup_cmd, '_install_env', return_value=(self.root / 'runtime', [])):
            self.assertEqual(self.invoke(yes=True, models_dir='weights'), 0)
        saved = config.load()['models_dir']
        os.chdir(self.root)
        self.assertEqual(saved, str(project / 'weights'))
        self.assertEqual(config.model_home('mineru'), project / 'weights' / 'mineru')

    def test_legacy_relative_config_is_anchored_to_config_directory(self):
        config.save({'models_dir': 'weights'})
        self.assertEqual(config.model_home('mineru'), self.cfg.parent / 'weights' / 'mineru')

    def test_global_root_overrides_stale_engine_home_and_doctor_agrees(self):
        config.save({'models_dir': str(self.root / 'new'), 'engines': {
            'mineru': {'mineru_home': str(self.root / 'old')}}})
        with patch.object(util, 'resolve_env_exe', return_value=None):
            engine = config.discover_mineru(refresh=True)
        self.assertEqual(engine.extra['mineru_home'], str(self.root / 'new' / 'mineru'))
        self.assertEqual(doctor._models(engine)['dir'], str(self.root / 'new' / 'mineru' / 'models'))

    def test_environment_root_changes_invalidate_discovery_cache(self):
        config._DISCOVERY.clear()
        for folder in ('one', 'two'):
            with patch.dict(os.environ, {'DOCVISION_MODELS': str(self.root / folder)}), \
                 patch.object(util, 'resolve_env_exe', return_value=None):
                engine = config.discover_mineru()
            self.assertEqual(engine.extra['mineru_home'], str(self.root / folder / 'mineru'))

    def test_paddle_cache_environment_changes_invalidate_discovery_cache(self):
        config._DISCOVERY.clear()
        for folder in ('paddle-one', 'paddle-two'):
            with patch.dict(os.environ, {'PADDLE_PDX_CACHE_HOME': str(self.root / folder)}), \
                 patch.object(util, 'resolve_env_exe', return_value=None):
                engine = config.discover_paddle()
            self.assertEqual(engine.extra['paddlex_home'], str(self.root / folder))

    def test_discovered_paddle_has_no_automatic_gpu_default_without_runtime_evidence(self):
        with patch.object(util, 'resolve_env_exe', return_value=None):
            engine = config.discover_paddle(refresh=True)
        self.assertEqual(engine.extra['device'], 'cpu')

    def test_relative_environment_storage_paths_are_rejected(self):
        for variable, reader in (('DOCVISION_MODELS', util.models_dir),
                                 ('LOCALAPPDATA', util.app_dir), ('APPDATA', util.config_dir)):
            with self.subTest(variable=variable), patch.object(util, 'IS_WINDOWS', True), \
                 patch.dict(os.environ, {variable: 'relative-storage'}):
                with self.assertRaisesRegex(Exception, 'absolute'):
                    reader()

    def test_conda_new_install_uses_private_prefix_ignoring_unknown_named_env(self):
        shared = self.root / 'shared' / 'docvision-mineru'
        with patch.object(setup_cmd, '_conda', return_value='conda'), \
             patch.object(util, 'conda_envs', return_value={'docvision-mineru': shared}):
            prefix, commands = setup_cmd._install_env('docvision-mineru', ['mineru'], manager='conda', dry_run=True)
        self.assertEqual(prefix.parent, util.app_dir() / 'envs')
        self.assertTrue(prefix.name.startswith('docvision-mineru-'))
        self.assertEqual(commands[0][1:5], ['create', '-y', '-p', str(prefix)])
        self.assertNotIn(str(shared), ' '.join(' '.join(cmd) for cmd in commands))

    def test_conda_update_creates_new_prefix_instead_of_upgrading_configured_runtime(self):
        prefix = self.runtime()
        config.save({'engines': {'mineru': {'python': str(util.env_python(prefix))}}})
        with patch.object(setup_cmd, '_conda', return_value='conda'):
            installed, commands = setup_cmd._install_env('docvision-mineru', ['mineru'], manager='conda', dry_run=True)
        self.assertNotEqual(installed, prefix)
        self.assertTrue(any('create' in cmd for cmd in commands))
        self.assertNotIn(str(util.env_python(prefix)), ' '.join(' '.join(cmd) for cmd in commands))

    def test_uv_update_creates_new_prefix_instead_of_upgrading_configured_runtime(self):
        prefix = self.runtime()
        python = str(util.env_python(prefix))
        config.save({'core': {'python': python}})
        with patch.object(setup_cmd, '_uv', return_value='uv'):
            installed, commands = setup_cmd._install_env('docvision-core', ['pypdf'], manager='uv', dry_run=True)
        self.assertNotEqual(installed, prefix)
        self.assertTrue(any('venv' in cmd for cmd in commands))
        self.assertNotIn(python, ' '.join(' '.join(cmd) for cmd in commands))

    def test_failed_models_download_leaves_configuration_unchanged(self):
        prefix = self.runtime()
        config.save({'models_dir': str(self.root / 'original')})
        before = self.cfg.read_bytes()
        def process(command, **kwargs):
            code = 1 if 'download' in command else 0
            return subprocess.CompletedProcess(command, code, 'help', 'offline download failure')
        with patch.object(setup_cmd, '_install_env', return_value=(prefix, [])), \
             patch.object(util, 'run', side_effect=process), self.assertRaises(SystemExit) as raised:
            self.invoke('mineru', yes=True, models_dir=str(self.root / 'new'))
        self.assertNotEqual(raised.exception.code, 0)
        self.assertEqual(self.cfg.read_bytes(), before)

    def test_failed_paddle_dependency_check_does_not_save_engine(self):
        prefix = self.runtime()
        payload = {'dependencies': {'ok': False, 'missing': ['missing-extra']}}
        with patch.object(setup_cmd, '_install_env', return_value=(prefix, [])), \
             patch.object(util, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(payload), '')), \
             self.assertRaises(SystemExit):
            self.invoke('paddle', yes=True)
        self.assertFalse(self.cfg.exists())

    def test_doctor_low_ram_and_apple_plan_does_not_recommend_cuda(self):
        engines = {name: config.Engine(name) for name in ('mineru', 'paddleocr', 'vlm')}
        with patch.object(config, 'engine_status', return_value=engines), \
             patch.object(config, 'remote_keys', return_value={'paddle': None}), \
             patch.object(doctor, '_module', return_value={'ok': False}), \
             patch.object(util, 'platform_summary', return_value={'os': 'Darwin', 'machine': 'arm64'}), \
             patch.object(util, 'total_ram_gb', return_value=2), \
             patch.object(util, 'gpu_summary', return_value={'available': True}), \
             patch.object(util, 'credentials_path', return_value=self.root / 'absent'):
            report = doctor.collect()
        plan = report.get('hardware_plan') or {}
        self.assertEqual(plan.get('paddle_device'), 'cpu')
        self.assertEqual(plan.get('local_feasibility'), 'caution')
        self.assertTrue(plan.get('notes'))

    def test_under_16_gb_and_under_8_gb_vram_recommend_smaller_models(self):
        platform = {'os': 'Windows', 'machine': 'AMD64'}
        for ram, vram in ((12, '16384 MiB'), (32, '4096 MiB'), (32, '8170 MiB')):
            with self.subTest(ram=ram, vram=vram):
                plan = doctor.hardware_plan(platform, ram, {'available': True, 'gpus': [{'vram': vram}]})
                self.assertEqual(plan['local_feasibility'], 'caution')
                self.assertEqual(plan.get('recommended_tier'), 'economy')

    def test_no_confirmed_accelerator_starts_with_economy_even_with_enough_ram(self):
        plan = doctor.hardware_plan({'os': 'Linux', 'machine': 'x86_64'}, 32,
                                    {'available': False})
        self.assertEqual(plan['recommended_tier'], 'economy')
        self.assertEqual(plan['paddle_device'], 'cpu')
        self.assertEqual(plan['local_feasibility'], 'unverified')

    def test_disk_status_probes_existing_parent_of_both_storage_roots(self):
        environment = self.root / 'env-disk'
        models = self.root / 'model-disk'
        environment.mkdir(); models.mkdir()
        def disk_usage(path):
            self.assertTrue(Path(path).exists())
            free = 9 if Path(path) == environment else 30
            return type('Usage', (), {'free': free * 1024 ** 3})()
        with patch.object(util, 'app_dir', return_value=environment / 'docvision'), \
             patch.object(doctor.shutil, 'disk_usage', side_effect=disk_usage):
            status = doctor.storage_status(models / 'weights')
        self.assertEqual(status['environment']['free_gb'], 9)
        self.assertEqual(status['models']['free_gb'], 30)
        plan = doctor.hardware_plan({'os': 'Linux', 'machine': 'x86_64'}, 32,
                                    {'available': False}, status)
        self.assertEqual(plan['local_feasibility'], 'caution')
        self.assertEqual(plan['recommended_tier'], 'economy')

    def test_failed_model_verification_does_not_save_engine(self):
        prefix = self.runtime()
        def process(command, **kwargs):
            return subprocess.CompletedProcess(command, 1 if 'verify' in command else 0, '', 'bad model')
        with patch.object(setup_cmd, '_install_env', return_value=(prefix, [])), \
             patch.object(util, 'run', side_effect=process), self.assertRaises(SystemExit):
            self.invoke('mineru', yes=True)
        self.assertFalse(self.cfg.exists())

    def test_successful_setup_pins_an_isolated_home_for_safe_rollback(self):
        prefix = self.runtime()
        homes = []
        def process(command, **kwargs):
            homes.append(kwargs.get('env', {}).get('MINERU_HOME'))
            return subprocess.CompletedProcess(command, 0, 'help', '')
        with patch.object(setup_cmd, '_install_env', return_value=(prefix, [])), \
             patch.object(util, 'run', side_effect=process):
            self.assertEqual(self.invoke('mineru', yes=True, models_dir=str(self.root / 'weights')), 0)
        saved_home = config.load()['engines']['mineru']['model_home']
        self.assertEqual(set(homes), {saved_home})
        self.assertTrue(Path(saved_home).is_relative_to(self.root / 'weights' / 'installations'))
        self.assertIsNone(config.load()['engines']['mineru']['mineru_home'])

    def test_invalid_paddle_report_fails_cleanly_without_saving(self):
        prefix = self.runtime()
        with patch.object(setup_cmd, '_install_env', return_value=(prefix, [])), \
             patch.object(util, 'run', return_value=subprocess.CompletedProcess([], 0, '[]', '')), \
             self.assertRaises(SystemExit):
            self.invoke('paddle', yes=True)
        self.assertFalse(self.cfg.exists())

    def test_doctor_does_not_treat_unconsented_key_as_usable_route(self):
        engines = {name: config.Engine(name) for name in ('mineru', 'paddleocr', 'vlm')}
        with patch.object(config, 'engine_status', return_value=engines), \
             patch.object(config, 'remote_keys', return_value={'paddle': 'offline-fake-key'}), \
             patch.object(doctor, '_module', return_value={'ok': False}), \
             patch.object(util, 'credentials_path', return_value=self.root / 'absent'):
            report = doctor.collect()
        self.assertTrue(report['remote_available'])
        self.assertIs(report.get('remote_policy_allowed'), False)
        self.assertFalse(report['remote_usable'])
        self.assertFalse(report['healthy'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
