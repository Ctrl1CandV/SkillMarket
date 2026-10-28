"""Credential loading contracts, using fake values and temporary files only."""
import importlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'docvision' / 'scripts'))
from dv import cli, config, util
from dv.base import DocVisionError
from dv.providers import paddle_cloud


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='docvision-fake-credentials-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Keep the real installation's credential file out of every test.
        patcher = patch.dict(os.environ, {'DOCVISION_CREDENTIALS': str(self.root / 'skill' / '.credentials.env')})
        patcher.start()
        self.addCleanup(patcher.stop)

    def credentials(self):
        self.assertIsNotNone(importlib.util.find_spec('dv.credentials'), 'credential loader is not implemented')
        return importlib.import_module('dv.credentials')

    def write_env(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def test_parser_handles_bom_quotes_comments_and_equals(self):
        result = self.credentials().parse_env('\ufeff# comment\n'
            'export PADDLEAPIKEY = "fake=a#b" # trailing\n'
            "DOCVISION_VLM_API_KEY='fake literal # value'\n"
            'DOCVISION_OPENAI_MODEL = fake-vlm # model\n'
            'OPENAI_BASE_URL=https://example.invalid/v1#fragment\n')
        self.assertEqual(result, {'PADDLEAPIKEY': 'fake=a#b', 'DOCVISION_VLM_API_KEY': 'fake literal # value',
                                  'DOCVISION_OPENAI_MODEL': 'fake-vlm',
                                  'OPENAI_BASE_URL': 'https://example.invalid/v1#fragment'})

    def test_parser_does_not_expand_or_execute_values(self):
        text = 'PADDLEAPIKEY="$(echo FAKE) ${HOME} `fake` %USERPROFILE%"\nDOCVISION_VLM_API_KEY=literal$HOME\n'
        result = self.credentials().parse_env(text)
        self.assertEqual(result['PADDLEAPIKEY'], '$(echo FAKE) ${HOME} `fake` %USERPROFILE%')
        self.assertEqual(result['DOCVISION_VLM_API_KEY'], 'literal$HOME')

    def test_arbitrary_environment_injection_is_filtered(self):
        result = self.credentials().parse_env('PATH=evil\nPYTHONPATH=evil\nDOCVISION_CONFIG=evil\n'
            'DOCVISION_ENV_FILE=evil\nDOCVISION_CORE_ACTIVE=1\nOPENAI_MODEL=fake-model\n')
        self.assertEqual(result, {'OPENAI_MODEL': 'fake-model'})

    def test_explicit_file_wins_over_environment_path_and_default(self):
        explicit = self.write_env('explicit.env', 'PADDLEAPIKEY=explicit-fake')
        fallback = self.write_env('configured.env', 'PADDLEAPIKEY=configured-fake')
        self.write_env('.env', 'PADDLEAPIKEY=default-fake')
        env = {'DOCVISION_ENV_FILE': str(fallback)}
        self.credentials().load_env_file(explicit, environ=env, cwd=self.root)
        self.assertEqual(env['PADDLEAPIKEY'], 'explicit-fake')

    def test_environment_path_is_used_without_recursive_search(self):
        file = self.write_env('nested/credentials.env', 'PADDLEAPIKEY=configured-fake')
        env = {'DOCVISION_ENV_FILE': str(file)}
        self.credentials().load_env_file(environ=env, cwd=self.root)
        self.assertEqual(env['PADDLEAPIKEY'], 'configured-fake')
        child = self.root / 'child'
        child.mkdir()
        self.write_env('.env', 'PADDLEAPIKEY=parent-fake')
        empty = {}
        self.assertIsNone(self.credentials().load_env_file(environ=empty, cwd=child))
        self.assertEqual(empty, {})

    def test_default_order_is_skill_file_then_cwd_dotenv(self):
        # No skill file yet: the working-directory .env is the fallback.
        self.credentials().save_credentials({'PADDLEAPIKEY': 'cwd-fake'}, self.root / '.env')
        env = {}
        self.credentials().load_env_file(environ=env, cwd=self.root)
        self.assertEqual(env['PADDLEAPIKEY'], 'cwd-fake')
        # The canonical skill file wins once it exists.
        skill = self.credentials().save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'skill-fake'})
        env = {}
        self.assertEqual(self.credentials().load_env_file(environ=env, cwd=self.root), skill)
        self.assertEqual(env['PADDLEOCR_ACCESS_TOKEN'], 'skill-fake')

    def test_saved_file_is_restrictive_and_only_holds_recognized_names(self):
        path = self.credentials().save_credentials(
            {'PADDLEOCR_ACCESS_TOKEN': 'fake-token', 'PATH': '/evil', 'DOCVISION_CONFIG': '/evil'})
        self.assertEqual(self.credentials().read_credentials(path), {'PADDLEOCR_ACCESS_TOKEN': 'fake-token'})
        text = path.read_text(encoding='utf-8')
        self.assertNotIn('/evil', text)
        if os.name != 'nt':
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_save_refuses_a_git_work_tree_without_ignore(self):
        if not __import__('shutil').which('git'):
            self.skipTest('git is not installed')
        import subprocess
        repo = self.root / 'repo'
        repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        target = repo / '.credentials.env'
        with self.assertRaises(DocVisionError) as error:
            self.credentials().save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'fake-token'}, target)
        self.assertIn('.gitignore', error.exception.hint or '')
        (repo / '.gitignore').write_text('.credentials.env\n.credentials.env.*\n', encoding='utf-8')
        self.assertTrue(self.credentials().save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'fake-token'}, target).is_file())

    def test_remove_deletes_file_and_reports_count(self):
        self.credentials().save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'fake-token'})
        self.assertEqual(self.credentials().remove_credentials(), 1)
        self.assertEqual(self.credentials().remove_credentials(), 0)
        self.assertFalse(util.credentials_path().exists())

    def test_existing_environment_credentials_win_across_aliases(self):
        file = self.write_env('fake.env', 'DOCVISION_PADDLE_TOKEN=file-fake\nPADDLEAPIKEY=alias-fake\n'
            'DOCVISION_OPENAI_BASE_URL=https://file.invalid\n')
        env = {'PADDLEOCR_ACCESS_TOKEN': 'existing-fake', 'OPENAI_BASE_URL': 'https://existing.invalid'}
        self.credentials().load_env_file(file, environ=env)
        self.assertEqual(env, {'PADDLEOCR_ACCESS_TOKEN': 'existing-fake', 'OPENAI_BASE_URL': 'https://existing.invalid'})

    def test_existing_alias_is_not_replaced_by_official_name_from_file(self):
        file = self.write_env('fake.env', 'PADDLEOCR_ACCESS_TOKEN=file-fake\n')
        env = {'PADDLEAPIKEY': 'existing-alias-fake'}
        self.credentials().load_env_file(file, environ=env)
        self.assertEqual(env, {'PADDLEAPIKEY': 'existing-alias-fake'})

    def test_official_paddle_name_wins_over_legacy_alias_in_same_file(self):
        file = self.write_env('fake.env', 'PADDLEAPIKEY=alias-fake\nPADDLEOCR_ACCESS_TOKEN=official-fake\n')
        with patch.dict(os.environ, {}, clear=True):
            self.credentials().load_env_file(file)
            self.assertEqual(config.remote_keys()['paddle'], 'official-fake')
            self.assertEqual(util.env_value(*paddle_cloud.TOKEN_NAMES), 'official-fake')

    def test_legacy_paddle_alias_works_without_renaming(self):
        with patch.dict(os.environ, {'PADDLEAPIKEY': 'legacy-fake'}, clear=True):
            self.assertEqual(config.remote_keys()['paddle'], 'legacy-fake')
            self.assertEqual(util.env_value(*paddle_cloud.TOKEN_NAMES), 'legacy-fake')

    def test_malformed_file_is_atomic_and_error_omits_secret_contents(self):
        file = self.write_env('fake.env', 'DOCVISION_VLM_API_KEY=first-fake\nPADDLEAPIKEY="FAKE_SECRET_UNCLOSED\n')
        env = {}
        with self.assertRaises(DocVisionError) as error:
            self.credentials().load_env_file(file, environ=env)
        self.assertEqual(env, {})
        self.assertNotIn('FAKE_SECRET_UNCLOSED', str(error.exception))
        self.assertIn('line 2', str(error.exception))

    def test_explicit_missing_file_fails_without_disclosing_contents(self):
        with self.assertRaises(DocVisionError):
            self.credentials().load_env_file(self.root / 'absent.env', environ={})

    def test_global_flag_before_subcommand_loads_fake_file(self):
        file = self.write_env('fake.env', 'PADDLEAPIKEY=cli-fake')
        def doctor(args):
            self.assertEqual(config.remote_keys()['paddle'], 'cli-fake')
            return 0
        with patch.dict(os.environ, {}, clear=True), patch.object(cli, 'cmd_doctor', side_effect=doctor), \
             redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['--env-file', str(file), 'doctor', '--json']), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
