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
            "GEMINI_API_KEY='fake literal # value'\n"
            'DOCVISION_GEMINI_MODEL = fake-flash # model\n'
            'OPENAI_BASE_URL=https://example.invalid/v1#fragment\n')
        self.assertEqual(result, {'PADDLEAPIKEY': 'fake=a#b', 'GEMINI_API_KEY': 'fake literal # value',
                                  'DOCVISION_GEMINI_MODEL': 'fake-flash',
                                  'OPENAI_BASE_URL': 'https://example.invalid/v1#fragment'})

    def test_parser_does_not_expand_or_execute_values(self):
        text = 'PADDLEAPIKEY="$(echo FAKE) ${HOME} `fake` %USERPROFILE%"\nGEMINI_API_KEY=literal$HOME\n'
        result = self.credentials().parse_env(text)
        self.assertEqual(result['PADDLEAPIKEY'], '$(echo FAKE) ${HOME} `fake` %USERPROFILE%')
        self.assertEqual(result['GEMINI_API_KEY'], 'literal$HOME')

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

    def test_default_is_only_cwd_dotenv(self):
        self.write_env('.env', 'PADDLEAPIKEY=cwd-fake')
        env = {}
        self.credentials().load_env_file(environ=env, cwd=self.root)
        self.assertEqual(env['PADDLEAPIKEY'], 'cwd-fake')

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
        file = self.write_env('fake.env', 'GEMINI_API_KEY=first-fake\nPADDLEAPIKEY="FAKE_SECRET_UNCLOSED\n')
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
