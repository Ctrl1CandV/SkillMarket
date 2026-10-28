"""Consent and credential isolation; temporary files and fake keys only."""
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'docvision' / 'scripts'))
from dv import cli, config, credentials, detect, refine, util
from dv.base import DocVisionError, Options
from dv.config import Engine
from dv import providers


class CredentialBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='docvision-fake-boundaries-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / 'skill' / '.credentials.env'
        self.environment = patch.dict(os.environ, {
            'PATH': os.environ.get('PATH', ''),
            'DOCVISION_CREDENTIALS': str(self.target),
            'DOCVISION_CONFIG': str(self.root / 'user' / 'config.json'),
        }, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.cwd = patch.object(Path, 'cwd', return_value=self.root)
        self.cwd.start()
        self.addCleanup(self.cwd.stop)

    def invoke(self, argv, token='FAKE_BOUNDARY_TOKEN\n'):
        output = io.StringIO()
        with patch.object(sys, 'stdin', io.StringIO(token)), redirect_stdout(output), redirect_stderr(output):
            try:
                code = cli.main(argv)
            except SystemExit as exc:
                code = exc.code
        return code, output.getvalue()

    def test_local_only_key_update_replaces_previous_remote_consent(self):
        config.set_consent('remote')
        code, _ = self.invoke(['credentials', 'set', '--stdin', '--local-only'])
        self.assertEqual(code, 0)
        self.assertEqual(config.remote_consent(), 'local-only')
        with self.assertRaises(DocVisionError):
            cli._guard_remote('paddleocr-cloud', True)

    def test_unset_requires_install_consent_before_each_remote_entrypoint(self):
        with self.assertRaises(DocVisionError) as raised:
            cli._guard_remote('paddleocr-cloud', True)
        self.assertIn('setup --remote', raised.exception.hint or '')
        with self.assertRaises(DocVisionError):
            refine.choose_provider('paddleocr-cloud', 'formula', True)
        with patch.object(config, 'remote_keys', return_value={'paddle': 'FAKE'}):
            self.assertEqual(refine.choose_provider('auto', 'formula', True), 'packet')
        with patch.object(config, 'discover_mineru', return_value=Engine('mineru')), \
             patch.object(config, 'discover_paddle', return_value=Engine('paddleocr')), \
             patch.object(config, 'discover_vlm', return_value=Engine('vlm')), \
             patch.object(detect, 'remote_keys', return_value={'paddle': 'FAKE'}):
            with self.assertRaises(DocVisionError):
                detect.choose_provider('fake.png', Options(allow_remote=True))

    def test_registry_requires_consent_and_per_call_authorization(self):
        with patch.object(providers.paddle_cloud, 'convert', return_value='fake-result'):
            with self.assertRaises(DocVisionError):
                providers.run('paddleocr-cloud', 'fake.png', Options(allow_remote=True))
            config.set_consent('remote')
            with self.assertRaises(DocVisionError):
                providers.run('paddleocr-cloud', 'fake.png', Options(allow_remote=False))
            self.assertEqual(providers.run('paddleocr-cloud', 'fake.png', Options(allow_remote=True)), 'fake-result')

    def test_providers_does_not_report_unconsented_key_as_ready(self):
        os.environ['PADDLEAPIKEY'] = 'FAKE_PROCESS_TOKEN'
        engines = {name: Engine(name) for name in ('mineru', 'paddleocr', 'vlm')}
        with patch.object(config, 'engine_status', return_value=engines):
            code, output = self.invoke(['providers', '--json'])
        self.assertEqual(code, 0)
        remote = next(row for row in json.loads(output)['providers'] if row['name'] == 'paddleocr-cloud')
        self.assertFalse(remote['ready'])

    def test_prompt_reads_secret_without_exposing_it(self):
        with patch('getpass.getpass', return_value='FAKE_PROMPT_TOKEN'):
            code, output = self.invoke(['credentials', 'set', '--prompt', '--local-only'])
        self.assertEqual(code, 0)
        self.assertNotIn('FAKE_PROMPT_TOKEN', output)
        self.assertEqual(credentials.read_credentials()['PADDLEOCR_ACCESS_TOKEN'], 'FAKE_PROMPT_TOKEN')

    def test_automatic_legacy_file_requires_explicit_reentry(self):
        self.target.parent.mkdir()
        self.target.write_text('PADDLEOCR_ACCESS_TOKEN=FAKE_OLD_TOKEN\n', encoding='utf-8')
        environment = {}
        with self.assertWarns(RuntimeWarning):
            self.assertIsNone(credentials.load_env_file(environ=environment, cwd=self.root))
        self.assertEqual(environment, {})
        with self.assertRaises(DocVisionError):
            credentials.read_credentials()
        code, _ = self.invoke(['credentials', 'set', '--stdin', '--local-only'])
        self.assertEqual(code, 0)
        environment = {}
        credentials.load_env_file(environ=environment, cwd=self.root)
        self.assertEqual(environment['PADDLEOCR_ACCESS_TOKEN'], 'FAKE_BOUNDARY_TOKEN')

    def test_other_machine_user_cannot_load_saved_skill_key(self):
        credentials.save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'FAKE_OWNER_A'})
        with patch.object(credentials, '_identity', return_value='other-machine-user', create=True):
            with self.assertWarns(RuntimeWarning):
                self.assertIsNone(credentials.load_env_file(environ={}, cwd=self.root))
            with self.assertRaises(DocVisionError):
                credentials.load_env_file(self.target, environ={}, cwd=self.root)
            with self.assertRaises(DocVisionError):
                credentials.save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'FAKE_OWNER_B'})
        self.assertEqual(credentials.read_credentials()['PADDLEOCR_ACCESS_TOKEN'], 'FAKE_OWNER_A')

    def test_process_key_works_when_automatic_file_belongs_to_other_user(self):
        credentials.save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'FAKE_OWNER_A'})
        environment = {'PADDLEAPIKEY': 'FAKE_OWN_PROCESS_KEY'}
        with patch.object(credentials, '_identity', return_value='other-machine-user', create=True):
            with self.assertWarns(RuntimeWarning):
                self.assertIsNone(credentials.load_env_file(environ=environment, cwd=self.root))
        self.assertEqual(environment, {'PADDLEAPIKEY': 'FAKE_OWN_PROCESS_KEY'})

    def test_process_vlm_key_does_not_hide_saved_paddle_key(self):
        credentials.save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'FAKE_SAVED_PADDLE'})
        environment = {'DOCVISION_VLM_API_KEY': 'FAKE_PROCESS_VLM'}
        self.assertEqual(credentials.load_env_file(environ=environment, cwd=self.root), self.target)
        self.assertEqual(environment['PADDLEOCR_ACCESS_TOKEN'], 'FAKE_SAVED_PADDLE')
        self.assertEqual(environment['DOCVISION_VLM_API_KEY'], 'FAKE_PROCESS_VLM')

    def test_unrelated_project_dotenv_does_not_block_local_cli(self):
        (self.root / '.env').write_text('OTHER_TOOL_TOKEN=FAKE_OTHER_TOOL_KEY\n', encoding='utf-8')
        with patch.object(cli, 'cmd_convert', return_value=0):
            code, output = self.invoke(['convert', 'local.png', '--provider', 'mineru-local'])
        self.assertEqual(code, 0)
        self.assertNotIn('FAKE_OTHER_TOOL_KEY', output)

    def test_unsafe_automatic_file_does_not_fall_back_to_project_key(self):
        self.target.parent.mkdir()
        self.target.write_text('PADDLEOCR_ACCESS_TOKEN=FAKE_UNBOUND_SKILL\n', encoding='utf-8')
        (self.root / '.env').write_text('PADDLEOCR_ACCESS_TOKEN=FAKE_PROJECT_KEY\n', encoding='utf-8')
        environment = {}
        with self.assertWarns(RuntimeWarning):
            self.assertIsNone(credentials.load_env_file(environ=environment, cwd=self.root))
        self.assertEqual(environment, {})

    def test_fixed_tmp_file_is_never_followed_or_overwritten(self):
        self.target.parent.mkdir()
        fixed = self.target.with_name(self.target.name + '.tmp')
        fixed.write_text('unrelated-file', encoding='utf-8')
        credentials.save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'FAKE_NEW_KEY'})
        self.assertTrue(fixed.is_file(), 'saving credentials removed an unrelated fixed temp file')
        self.assertEqual(fixed.read_text(encoding='utf-8'), 'unrelated-file')
        self.assertEqual(credentials.read_credentials()['PADDLEOCR_ACCESS_TOKEN'], 'FAKE_NEW_KEY')

    def test_parallel_saves_use_independent_private_staging_files(self):
        barrier = threading.Barrier(2)
        replace = os.replace
        call_lock = threading.Lock()
        calls = []
        def simultaneous_replace(source, target):
            with call_lock:
                calls.append(source)
                initial = len(calls) <= 2
            if initial:
                barrier.wait(timeout=5)
            return replace(source, target)
        with patch.object(credentials.os, 'replace', side_effect=simultaneous_replace), ThreadPoolExecutor(2) as executor:
            saves = [executor.submit(credentials.save_credentials, {'PADDLEOCR_ACCESS_TOKEN': key})
                     for key in ('FAKE_PARALLEL_A', 'FAKE_PARALLEL_B')]
            self.assertEqual([future.result(timeout=10) for future in saves], [self.target, self.target])
        self.assertIn(credentials.read_credentials()['PADDLEOCR_ACCESS_TOKEN'], {'FAKE_PARALLEL_A', 'FAKE_PARALLEL_B'})
        self.assertEqual(list(self.target.parent.glob('*.part')), [])

    def test_symlink_target_is_refused_before_loading_or_saving(self):
        self.target.parent.mkdir()
        actual = self.root / 'actual.env'
        actual.write_text('PADDLEOCR_ACCESS_TOKEN=FAKE_SYMLINK_KEY\n', encoding='utf-8')
        try:
            self.target.symlink_to(actual)
        except OSError:
            self.skipTest('creating symlinks is unavailable for this OS user')
        with self.assertRaises(DocVisionError):
            credentials.load_env_file(self.target, environ={}, cwd=self.root)
        with self.assertRaises(DocVisionError):
            credentials.save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'FAKE_REPLACEMENT'})
        self.assertEqual(actual.read_text(encoding='utf-8'), 'PADDLEOCR_ACCESS_TOKEN=FAKE_SYMLINK_KEY\n')

    @unittest.skipUnless(os.name == 'nt', 'Windows ACL contract')
    def test_saved_file_does_not_inherit_shared_folder_read_access(self):
        self.target.parent.mkdir()
        subprocess.run(['icacls', str(self.target.parent), '/grant', '*S-1-5-32-545:(OI)(CI)(RX)'],
                       check=True, capture_output=True)
        credentials.save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'FAKE_PRIVATE_KEY'})
        exported = self.root / 'acl.txt'
        subprocess.run(['icacls', str(self.target), '/save', str(exported)],
                       check=True, capture_output=True)
        acl = exported.read_text(encoding='utf-16-le')
        self.assertNotIn(';;;BU)', acl)
        self.assertNotIn(';;;WD)', acl)
        self.assertIn('D:P', acl)

    @unittest.skipUnless(os.name == 'nt', 'Windows junction contract')
    def test_parent_junction_is_refused_for_load_and_save(self):
        actual = self.root / 'actual-skill'
        actual.mkdir()
        source = actual / '.credentials.env'
        source.write_text('PADDLEOCR_ACCESS_TOKEN=FAKE_JUNCTION_KEY\n', encoding='utf-8')
        junction = self.root / 'linked-skill'
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(actual)],
                       check=True, capture_output=True)
        self.addCleanup(lambda: os.rmdir(junction) if junction.exists() else None)
        with self.assertRaises(DocVisionError):
            credentials.load_env_file(junction / '.credentials.env', environ={}, cwd=self.root)
        with self.assertRaises(DocVisionError):
            credentials.save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'FAKE_REPLACEMENT'}, junction / '.credentials.env')
        with patch.dict(os.environ, {'DOCVISION_CREDENTIALS': str(junction / '.credentials.env')}):
            with self.assertRaises(DocVisionError):
                credentials.save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'FAKE_OVERRIDE_REPLACEMENT'})
            with self.assertRaises(DocVisionError):
                credentials.read_credentials()
        self.assertEqual(source.read_text(encoding='utf-8'), 'PADDLEOCR_ACCESS_TOKEN=FAKE_JUNCTION_KEY\n')


if __name__ == '__main__':
    unittest.main(verbosity=2)
