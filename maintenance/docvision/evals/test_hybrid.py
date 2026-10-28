"""Behavioral tests for region refinement; no external inference or credentials."""
import json
import sys
import tempfile
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'docvision' / 'scripts'))
from dv import refine
from dv.base import DocVisionError, Options, RawBlock, RawDoc, RawPage
from dv.output import write_document


class HybridTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.png'
        Image.new('RGB', (200, 100), 'white').save(self.source)
        self.docdir = write_document(
            RawDoc(markdown='$x^2$', provider='mineru-local', pages=[RawPage(
                page=1, markdown='$x^2$', blocks=[RawBlock(type='formula', text='x^2',
                markdown='$x^2$', bbox=[.25, .25, .75, .75])])]),
            str(self.source), Options(), out_root=self.root / 'out', info={'pages': 1})

    def tearDown(self):
        self.tmp.cleanup()

    def test_triage_is_review_priority_not_accuracy(self):
        report = refine.triage(self.docdir)
        self.assertEqual(report['candidates'][0]['task'], 'formula')
        self.assertEqual(report['candidates'][0]['block'], 'p1-b0')
        self.assertFalse(report['accuracy_verified'])

    def test_packet_crops_exact_region_without_network(self):
        from PIL import Image
        with patch.object(refine, 'run_provider', side_effect=AssertionError('network')):
            result = refine.run(self.docdir, page=1, block_id='p1-b0', provider='packet')
        self.assertEqual(result['state'], 'review_required')
        with Image.open(result['image_path']) as im:
            self.assertEqual(im.size, (100, 50))
        self.assertEqual(result['source']['page'], 1)
        self.assertEqual(result['source']['bbox'], [.25, .25, .75, .75])
        self.assertTrue(Path(result['context_path']).is_file())

    def test_remote_requires_authorization_before_request(self):
        with patch.object(refine, 'run_provider') as call:
            with self.assertRaises(DocVisionError):
                refine.run(self.docdir, page=1, provider='paddleocr-cloud')
        call.assert_not_called()

    def test_remote_only_receives_region_and_keeps_base(self):
        base = (self.docdir / f'{self.docdir.name}.md').read_bytes()
        def recognize(provider, source, opts):
            from PIL import Image
            with Image.open(source) as im:
                self.assertEqual(im.size, (100, 50))
            self.assertIsNone(opts.pages)
            self.assertEqual(opts.extra['refine_task'], 'formula')
            return RawDoc(markdown='$$x^2$$', provider=provider, model='test'), {}
        with patch.object(refine, 'run_provider', side_effect=recognize):
            result = refine.run(self.docdir, page=1, block_id='p1-b0', provider='paddleocr-cloud',
                                allow_remote=True, extra={'model': 'test'})
        self.assertEqual(result['state'], 'recognized')
        self.assertFalse(result['accuracy_verified'])
        self.assertEqual((self.docdir / f'{self.docdir.name}.md').read_bytes(), base)
        self.assertIn('x^2', Path(result['markdown_path']).read_text('utf-8'))

    def test_cache_changes_with_model_task_and_context(self):
        def recognize(provider, source, opts):
            return RawDoc(markdown='result', provider=provider, model=opts.extra.get('model')), {}
        with patch.object(refine, 'run_provider', side_effect=recognize) as call:
            kw = dict(page=1, provider='paddleocr-cloud', allow_remote=True)
            a = refine.run(self.docdir, **kw, extra={'model': 'one'})
            b = refine.run(self.docdir, **kw, extra={'model': 'one'})
            c = refine.run(self.docdir, **kw, extra={'model': 'two'})
            d = refine.run(self.docdir, **kw, task='table', extra={'model': 'two'})
        self.assertTrue(b['cached'])
        self.assertEqual(call.call_count, 3)
        self.assertNotEqual(a['id'], c['id'])
        self.assertNotEqual(c['id'], d['id'])

    def test_failure_is_recorded_without_retry_or_provider_fallback(self):
        with patch.object(refine, 'run_provider', side_effect=DocVisionError('quota exhausted')) as call:
            result = refine.run(self.docdir, page=1, provider='paddleocr-cloud', allow_remote=True)
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(call.call_count, 1)
        self.assertTrue(Path(result['image_path']).is_file())
        self.assertIn('quota exhausted', result['error'])

    def test_figure_auto_without_vision_credentials_produces_packet(self):
        with patch.object(refine.config, 'remote_keys', return_value={}), \
             patch.object(refine.config, 'discover_vlm', return_value=type('E', (), {'available': False})()):
            result = refine.run(self.docdir, page=1, task='figure', allow_remote=True)
        self.assertEqual(result['provider'], 'packet')
        self.assertEqual(result['state'], 'review_required')

    def test_ocr_provider_does_not_claim_figure_understanding(self):
        with self.assertRaises(DocVisionError):
            refine.run(self.docdir, page=1, task='figure', provider='paddleocr-cloud', allow_remote=True)

    def test_invalid_bbox_and_wrong_page_are_rejected(self):
        for bbox in ('0,0,0,1', '-1,0,1,1', '0,0,2,1'):
            with self.subTest(bbox=bbox), self.assertRaises(DocVisionError):
                refine.run(self.docdir, page=1, bbox=bbox, provider='packet')
        with self.assertRaises(DocVisionError):
            refine.run(self.docdir, page=2, provider='packet')

    def test_source_change_rejected_before_using_old_coordinates(self):
        from PIL import Image
        # Source fingerprint is optional in old outputs, so first add it.
        meta_file = self.docdir / 'meta.json'
        meta = json.loads(meta_file.read_text('utf-8'))
        from dv import util
        meta['source']['sha256'] = util.sha256_file(self.source)
        meta_file.write_text(json.dumps(meta), encoding='utf-8')
        Image.new('RGB', (400, 100), 'black').save(self.source)
        with self.assertRaises(DocVisionError):
            refine.run(self.docdir, page=1, provider='packet')

    def test_error_record_does_not_expose_configured_token(self):
        with patch.object(refine.config, 'remote_keys', return_value={'gemini': 'SECRET_FAKE_KEY'}), \
             patch.object(refine, 'run_provider', side_effect=DocVisionError('bad URL ?key=SECRET_FAKE_KEY')):
            result = refine.run(self.docdir, page=1, provider='paddleocr-cloud', allow_remote=True)
        self.assertNotIn('SECRET_FAKE_KEY', Path(result['record_path']).read_text('utf-8'))

    def test_submitted_attempt_is_never_automatically_resubmitted(self):
        with patch.object(refine, 'run_provider', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                refine.run(self.docdir, page=1, provider='paddleocr-cloud', allow_remote=True)
        with patch.object(refine, 'run_provider') as call:
            result = refine.run(self.docdir, page=1, provider='paddleocr-cloud', allow_remote=True)
        self.assertEqual(result['state'], 'submitted')
        call.assert_not_called()

    def test_vision_adapter_rejects_truncated_responses(self):
        from dv.providers import openai_compat
        from dv import util
        opts = Options(extra={'model': 'test', 'refine_task': 'figure',
                              'base_url': 'http://127.0.0.1:11434/v1'})
        with patch.object(util, 'post_json', return_value=(200, json.dumps({
                'choices': [{'finish_reason': 'length', 'message': {'content': 'partial'}}]}).encode())),              patch.object(util, 'env_value', return_value=None):
            with self.assertRaises(DocVisionError):
                openai_compat.convert(str(self.source), opts)

    def test_local_vlm_cannot_use_a_remote_endpoint(self):
        from dv.providers import openai_compat
        with self.assertRaises(DocVisionError):
            openai_compat.convert(str(self.source), Options(extra={
                'model': 'test', 'base_url': 'https://external.example/v1'}))

    def test_endpoint_change_invalidates_refinement_cache(self):
        import os
        def recognize(provider, source, opts):
            return RawDoc(markdown='result', provider=provider), {}
        with patch.object(refine, 'run_provider', side_effect=recognize) as call:
            with patch.dict(os.environ, {'DOCVISION_OPENAI_BASE_URL': 'https://a.example/v1'}):
                a = refine.run(self.docdir, page=1, provider='local-vlm')
            with patch.dict(os.environ, {'DOCVISION_OPENAI_BASE_URL': 'https://b.example/v1'}):
                b = refine.run(self.docdir, page=1, provider='local-vlm')
        self.assertNotEqual(a['id'], b['id'])
        self.assertEqual(call.call_count, 2)

    def test_local_only_consent_refuses_remote_even_with_flag(self):
        with patch.object(refine.config, 'remote_consent', return_value='local-only'),              patch.object(refine, 'run_provider') as call:
            with self.assertRaises(DocVisionError) as error:
                refine.run(self.docdir, page=1, provider='paddleocr-cloud', allow_remote=True)
        self.assertIn('declined', str(error.exception))
        call.assert_not_called()

    def test_auto_route_skips_remote_when_consent_is_local_only(self):
        with patch.object(refine.config, 'remote_consent', return_value='local-only'),              patch.object(refine.config, 'remote_keys', return_value={'paddle': 'FAKE'}):
            self.assertEqual(refine.choose_provider('auto', 'formula', allow_remote=True), 'packet')

    def test_cloud_provider_config_endpoint_changes_invalidate_cache(self):
        def recognize(provider, source, opts):
            return RawDoc(markdown='result', provider=provider), {}
        provider = 'paddleocr-cloud'
        with patch.object(refine, 'run_provider', side_effect=recognize) as call:
            with patch.object(refine.config, 'load', return_value={'remote': {'paddle_base': 'https://a.example/v1'}}):
                first = refine.run(self.docdir, page=1, provider=provider, allow_remote=True)
            with patch.object(refine.config, 'load', return_value={'remote': {'paddle_base': 'https://b.example/v1'}}):
                second = refine.run(self.docdir, page=1, provider=provider, allow_remote=True)
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(call.call_count, 2)

    def test_block_context_excludes_distant_page_text(self):
        p = self.docdir / 'content.json'
        data = json.loads(p.read_text('utf-8'))
        data['pages'][0]['markdown'] = '$x^2$\nNEAR_CAPTION\nUNRELATED_PRIVATE_TEXT'
        data['pages'][0]['blocks'].extend([
            {'id': 'p1-b1', 'type': 'text', 'markdown': 'NEAR_CAPTION'},
            {'id': 'p1-b2', 'type': 'text', 'markdown': 'UNRELATED_PRIVATE_TEXT'}])
        p.write_text(json.dumps(data), encoding='utf-8')
        result = refine.run(self.docdir, page=1, block_id='p1-b0', provider='packet')
        context = Path(result['context_path']).read_text('utf-8')
        self.assertIn('NEAR_CAPTION', context)
        self.assertNotIn('UNRELATED_PRIVATE_TEXT', context)
        self.assertEqual(result['context_scope'], ['p1-b0', 'p1-b1'])

    def test_concurrent_identical_requests_submit_once(self):
        original_read = refine.util.read_json
        barrier = threading.Barrier(2)
        def read_json(path, default=None):
            result = original_read(path, default)
            if Path(path).name == 'record.json':
                barrier.wait(timeout=4)
            return result
        def recognize(provider, source, opts):
            return RawDoc(markdown='result', provider=provider), {}
        def job():
            try:
                return refine.run(self.docdir, page=1, provider='paddleocr-cloud', allow_remote=True)
            except DocVisionError as exc:
                return {'state': 'busy', 'error': str(exc)}
        with patch.object(refine.util, 'read_json', side_effect=read_json), \
             patch.object(refine.reading, 'render_page', return_value=self.source), \
             patch.object(refine, 'run_provider', side_effect=recognize) as call:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: job(), range(2)))
        self.assertEqual(call.call_count, 1)
        self.assertEqual(sum(r['state'] == 'recognized' for r in results), 1)

    def test_figure_context_preserves_caption_stored_in_block_text(self):
        p = self.docdir / 'content.json'
        data = json.loads(p.read_text('utf-8'))
        data['pages'][0]['blocks'][0].update(type='image', text='Figure 1: precise scientific caption',
                                          markdown='![figure](assets/figure.png)')
        p.write_text(json.dumps(data), encoding='utf-8')
        result = refine.run(self.docdir, page=1, block_id='p1-b0', provider='packet')
        self.assertIn('precise scientific caption', Path(result['context_path']).read_text('utf-8'))


if __name__ == '__main__':
    unittest.main()
