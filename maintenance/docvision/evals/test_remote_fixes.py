"""Offline local-transport, effective configuration and credential-rotation checks."""
from __future__ import annotations

import http.client
import io
import json
import os
import sys
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'docvision' / 'scripts'))
from dv import config, credentials, refine, util
from dv.base import DocVisionError, Options
from dv.providers import openai_compat


class Response:
    def __init__(self, status=200, headers=None, content=None):
        self.status = self.code = status
        self.reason = self.msg = 'fixture'
        self.headers = Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value
        self.body = io.BytesIO(content if content is not None else json.dumps({
            'choices': [{'finish_reason': 'stop', 'message': {'content': 'Recognized fixture.'}}]
        }).encode())

    def info(self):
        return self.headers

    def read(self, *args):
        return self.body.read(*args)

    def close(self):
        self.body.close()

    @property
    def closed(self):
        return self.body.closed

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class LocalTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='docvision-local-transport-')
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'fixture.png'
        Image.new('RGB', (20, 10), 'white').save(self.source)
        self.calls = []
        self.response = Response()
        case = self

        class Connection(http.client.HTTPConnection):
            def request(self, method, url, body=None, headers=None, **kwargs):
                case.calls.append({'host': self.host, 'url': url, 'method': method,
                                   'body': body, 'headers': headers or {}})

            def getresponse(self):
                return case.response

            def close(self):
                pass

        for patcher in (
            patch.dict(os.environ, {
                'http_proxy': 'http://outside-proxy.invalid:8080',
                'https_proxy': 'http://outside-proxy.invalid:8080',
                'DOCVISION_VLM_API_KEY': 'fake-local-key',
            }, clear=True),
            patch.object(config, 'load', return_value=config.DEFAULT_CONFIG),
            patch.object(http.client, 'HTTPConnection', Connection),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def convert(self):
        return openai_compat.convert(str(self.source), Options(allow_remote=False, extra={
            'base_url': 'http://127.0.0.1:11434/v1', 'model': 'fixture-model'
        }))

    def test_local_inference_ignores_environment_proxy_without_remote_consent(self):
        doc, meta = self.convert()
        self.assertEqual(doc.pages[0].markdown, 'Recognized fixture.')
        self.assertTrue(meta['local'])
        self.assertEqual(len(self.calls), 1)
        call = self.calls[0]
        self.assertEqual(call['host'], '127.0.0.1')
        self.assertEqual(call['url'], '/v1/chat/completions')
        self.assertIn(b'image_url', call['body'])
        self.assertEqual(call['headers']['Authorization'], 'Bearer fake-local-key')

    def test_redirects_never_forward_images_or_credentials(self):
        for status in (301, 302, 303, 307, 308):
            for target in ('https://outside.invalid/collect', 'http://127.0.0.1:1234/other'):
                with self.subTest(status=status, target=target):
                    self.calls.clear()
                    self.response = Response(status, {'Location': target})
                    with self.assertRaisesRegex(DocVisionError, 'redirects are refused'):
                        self.convert()
                    self.assertEqual(len(self.calls), 1)
                    self.assertEqual(self.calls[0]['host'], '127.0.0.1')
                    self.assertTrue(self.response.body.closed)

    def test_invalid_scheme_or_remote_endpoint_fails_before_any_transport(self):
        for url in ('ftp://127.0.0.1/v1', 'file://localhost/v1',
                    'http://outside.invalid/v1', 'http://127.0.0.1:bad/v1',
                    'http://user:secret@127.0.0.1/v1'):
            with self.subTest(url=url), self.assertRaises(DocVisionError):
                util.post_local_json(url, {'private': 'fixture'})
        self.assertEqual(self.calls, [])

    def test_http_errors_remain_actionable(self):
        self.response = Response(401, content=b'{"error":{"message":"fixture unauthorized"}}')
        with self.assertRaisesRegex(DocVisionError, 'fixture unauthorized'):
            self.convert()
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(self.response.body.closed)


class EffectiveVlmTests(unittest.TestCase):
    def setUp(self):
        for patcher in (
            patch.dict(os.environ, {}, clear=True),
            patch.object(config, 'load', return_value=config.DEFAULT_CONFIG),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_environment_only_configuration_drives_discovery_and_auto_route(self):
        with patch.dict(os.environ, {'DOCVISION_OPENAI_BASE_URL': 'http://127.0.0.1:1234/v1',
                                     'DOCVISION_OPENAI_MODEL': 'env-model'}):
            engine = config.discover_vlm()
            self.assertTrue(engine.available)
            self.assertEqual(engine.extra['model'], 'env-model')
            self.assertEqual(engine.extra['base_url'], 'http://127.0.0.1:1234/v1')
            self.assertEqual(refine.choose_provider('auto', 'figure', False), 'local-vlm')

    def test_environment_only_configuration_reaches_adapter_payload(self):
        with patch.dict(os.environ, {'DOCVISION_OPENAI_BASE_URL': 'http://localhost:5678/v1',
                                     'DOCVISION_OPENAI_MODEL': 'env-model'}), \
             patch.object(openai_compat, 'inspect_input', return_value={'pages': 1}), \
             patch.object(openai_compat, '_page_images', return_value=[(1, b'fixture', 'image/png')]), \
             patch.object(util, 'post_local_json', return_value=(200, json.dumps({
                 'choices': [{'finish_reason': 'stop', 'message': {'content': 'result'}}]
             }).encode())) as post:
            doc, _ = openai_compat.convert('fixture.png', Options())
        self.assertEqual(post.call_args.args[0], 'http://localhost:5678/v1/chat/completions')
        self.assertEqual(post.call_args.args[1]['model'], 'env-model')
        self.assertEqual(doc.model, 'env-model')

    def test_precedence_extra_then_dedicated_env_then_alias_then_config(self):
        cfg = {'engines': {'vlm': {'base_url': 'http://localhost:1/v1', 'model': 'config'}}}
        self.assertEqual(config.effective_vlm_config(cfg=cfg)['model'], 'config')
        with patch.dict(os.environ, {'OPENAI_MODEL': 'alias', 'OPENAI_BASE_URL': 'http://localhost:2/v1'}):
            self.assertEqual(config.effective_vlm_config(cfg=cfg)['model'], 'alias')
            self.assertEqual(config.effective_vlm_config(cfg=cfg)['base_url'], 'http://localhost:2/v1')
            with patch.dict(os.environ, {'DOCVISION_OPENAI_MODEL': 'dedicated',
                                         'DOCVISION_OPENAI_BASE_URL': 'http://localhost:3/v1'}):
                self.assertEqual(config.effective_vlm_config(cfg=cfg)['model'], 'dedicated')
                self.assertEqual(config.effective_vlm_config(cfg=cfg)['base_url'], 'http://localhost:3/v1')
                selected = config.effective_vlm_config({'model': 'explicit',
                                                       'base_url': 'http://localhost:4/v1'}, cfg)
                self.assertEqual(selected['model'], 'explicit')
                self.assertEqual(selected['base_url'], 'http://localhost:4/v1')

    def test_remote_environment_url_is_not_discovered_as_a_local_service(self):
        with patch.dict(os.environ, {'DOCVISION_OPENAI_BASE_URL': 'https://outside.invalid/v1',
                                     'DOCVISION_OPENAI_MODEL': 'fixture'}):
            self.assertFalse(config.discover_vlm().available)
            self.assertEqual(refine.choose_provider('auto', 'figure', False), 'packet')

    def test_effective_settings_never_include_key_values(self):
        with patch.dict(os.environ, {'DOCVISION_VLM_API_KEY': 'fake-private-value'}):
            self.assertNotIn('fake-private-value', json.dumps(config.effective_vlm_config()))


class CredentialRotationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='docvision-rotation-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # These fake files remain safe even when the test temp directory is in a repo.
        (self.root / '.gitignore').write_text('*\n', encoding='utf-8')

    def test_default_paddle_name_replaces_previous_higher_priority_alias(self):
        target = self.root / 'credentials.env'
        credentials.save_credentials({'DOCVISION_PADDLE_TOKEN': 'old-fixture',
                                      'DOCVISION_VLM_API_KEY': 'local-fixture'}, target)
        credentials.save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'new-fixture'}, target)
        env = {}
        credentials.load_env_file(target, environ=env)
        self.assertNotIn('DOCVISION_PADDLE_TOKEN', env)
        self.assertEqual(env['DOCVISION_VLM_API_KEY'], 'local-fixture')
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(config.remote_keys()['paddle'], 'new-fixture')

    def test_rotation_via_another_alias_replaces_previous_default(self):
        target = self.root / 'credentials.env'
        credentials.save_credentials({'PADDLEOCR_ACCESS_TOKEN': 'old-fixture'}, target)
        credentials.save_credentials({'AI_STUDIO_TOKEN': 'new-fixture'}, target)
        env = {}
        credentials.load_env_file(target, environ=env)
        self.assertEqual(env, {'AI_STUDIO_TOKEN': 'new-fixture'})


if __name__ == '__main__':
    unittest.main()
