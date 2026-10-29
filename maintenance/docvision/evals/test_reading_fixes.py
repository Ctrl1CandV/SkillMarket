"""Evidence must match the current draft, including explicit refinement retries."""

from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'docvision' / 'scripts'))

from dv import config, read, refine, util  # noqa: E402
from dv.base import DocVisionError, Options, RawBlock, RawDoc, RawPage  # noqa: E402
from dv.output import write_document  # noqa: E402


class ReadingEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.png'
        Image.new('RGB', (200, 100), 'red').save(self.source)
        self.docdir = self.document()
        for mock in (patch.object(config, 'load', return_value={}),
                     patch.object(config, 'remote_consent', return_value='remote'),
                     patch.object(config, 'remote_keys', return_value={'paddle': 'fake-test-key'})):
            mock.start()
            self.addCleanup(mock.stop)

    def document(self, body='Original formula', *, force=False):
        return write_document(
            RawDoc(markdown=body, provider='mineru-local', pages=[RawPage(
                page=1, markdown=body, blocks=[RawBlock(type='formula', text=body,
                    markdown=body, bbox=[.1, .1, .9, .9])])]),
            str(self.source), Options(force=force), out_root=self.root / 'out',
            info={'pages': 1, 'sha256': util.sha256_file(self.source)})

    def packet(self, **kwargs):
        return refine.run(self.docdir, page=1, block_id='p1-b0', provider='packet', **kwargs)

    def cloud(self, **kwargs):
        return refine.run(self.docdir, page=1, block_id='p1-b0',
                          provider='paddleocr-cloud', allow_remote=True, **kwargs)

    @staticmethod
    def recognized(provider, source, opts):
        return RawDoc(markdown='Corrected formula', provider=provider, model='offline-test'), {}

    def test_changed_source_rejects_read_image_and_block_crop(self):
        read.render_page(self.docdir, 1)
        Image.new('RGB', (200, 100), 'blue').save(self.source)
        for operation in (lambda: read.read(self.docdir, page=1, fmt='image'),
                          lambda: read.crop(self.docdir, page=1, block_id='p1-b0')):
            with self.subTest(operation=operation), self.assertRaisesRegex(DocVisionError, 'changed'):
                operation()

    def test_reconverted_source_excludes_old_refinement_but_keeps_history(self):
        old = self.packet()
        Image.new('RGB', (200, 100), 'blue').save(self.source)
        self.assertEqual(refine.list_results(self.docdir), [])
        self.document(force=True)
        current = self.packet()
        results = refine.list_results(self.docdir)
        self.assertEqual([r['record_path'] for r in results], [current['record_path']])
        self.assertTrue(Path(old['record_path']).is_file())

    def test_new_ocr_draft_excludes_context_from_previous_conversion(self):
        old = self.packet()
        self.document('Corrected OCR formula', force=True)
        self.assertEqual(refine.list_results(self.docdir, page=1), [])
        current = self.packet()
        results = refine.list_results(self.docdir, block_id='p1-b0')
        self.assertEqual([r['id'] for r in results], [current['id']])
        self.assertTrue(Path(old['record_path']).is_file())

    def test_block_move_excludes_previous_coordinates_even_when_text_matches(self):
        self.packet()
        content = util.read_json(self.docdir / 'content.json')
        content['pages'][0]['blocks'][0]['bbox'] = [.2, .2, .8, .8]
        util.write_json(self.docdir / 'content.json', content)
        self.assertEqual(refine.list_results(self.docdir), [])

    def test_current_manual_bbox_override_is_still_listed(self):
        result = self.packet(bbox='.2,.2,.8,.8')
        self.assertEqual([r['id'] for r in refine.list_results(self.docdir)], [result['id']])

    def test_neighbor_context_change_excludes_old_record(self):
        content = util.read_json(self.docdir / 'content.json')
        content['pages'][0]['blocks'].append({'id': 'p1-b1', 'type': 'text', 'markdown': 'Old caption'})
        util.write_json(self.docdir / 'content.json', content)
        self.packet()
        content['pages'][0]['blocks'][1]['markdown'] = 'Corrected caption'
        util.write_json(self.docdir / 'content.json', content)
        self.assertEqual(refine.list_results(self.docdir), [])

    def test_force_success_supersedes_failed_attempt_for_cache(self):
        with patch.object(refine, 'run_provider', side_effect=DocVisionError('temporary error')):
            first = self.cloud()
        with patch.object(refine, 'run_provider', side_effect=self.recognized) as provider:
            retry = self.cloud(force=True)
            cached = self.cloud()
        self.assertEqual(first['state'], 'failed')
        self.assertEqual(retry['state'], 'recognized')
        self.assertEqual(cached['record_path'], retry['record_path'])
        self.assertTrue(cached['cached'])
        self.assertEqual(provider.call_count, 1)
        self.assertTrue(Path(first['record_path']).is_file())

    def test_force_failure_does_not_fall_back_to_older_success_or_resubmit(self):
        with patch.object(refine, 'run_provider', side_effect=self.recognized):
            self.cloud()
        with patch.object(refine, 'run_provider', side_effect=DocVisionError('quota exhausted')) as provider:
            retry = self.cloud(force=True)
            cached = self.cloud()
        self.assertEqual(cached['state'], 'failed')
        self.assertEqual(cached['record_path'], retry['record_path'])
        self.assertEqual(provider.call_count, 1)

    def test_interrupted_force_submission_is_not_hidden_by_cached_success(self):
        with patch.object(refine, 'run_provider', side_effect=self.recognized):
            self.cloud()
        with patch.object(refine, 'run_provider', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.cloud(force=True)
        with patch.object(refine, 'run_provider') as provider:
            cached = self.cloud()
        self.assertEqual(cached['state'], 'submitted')
        self.assertTrue(Path(cached['record_path']).parent.name.endswith('-2'))
        provider.assert_not_called()

    def test_running_force_submission_is_visible_until_new_result_completes(self):
        with patch.object(refine, 'run_provider', side_effect=self.recognized):
            self.cloud()
        entered, finish = threading.Event(), threading.Event()

        def recognize(provider, source, opts):
            entered.set()
            if not finish.wait(timeout=5):
                raise AssertionError('test did not release the provider')
            return self.recognized(provider, source, opts)

        with patch.object(refine, 'run_provider', side_effect=recognize) as provider:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self.cloud, force=True)
                try:
                    self.assertTrue(entered.wait(timeout=5))
                    pending = self.cloud()
                    self.assertEqual(pending['state'], 'submitted')
                    self.assertTrue(Path(pending['record_path']).parent.name.endswith('-2'))
                finally:
                    finish.set()
                completed = future.result(timeout=5)
            cached = self.cloud()
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(cached['state'], 'recognized')
        self.assertEqual(cached['record_path'], completed['record_path'])

    def test_new_attempt_directory_without_record_blocks_old_cache(self):
        first = self.packet()
        (self.docdir / 'refinements' / f"{first['id']}-2").mkdir()
        with self.assertRaisesRegex(DocVisionError, 'in progress'):
            self.packet()

    def test_attempt_number_order_is_numeric_after_tenth_retry(self):
        first = self.packet()
        for _ in range(9):
            latest = self.packet(force=True)
        cached = self.packet()
        self.assertTrue(Path(latest['record_path']).parent.name.endswith('-10'))
        self.assertEqual(cached['record_path'], latest['record_path'])
        self.assertTrue(Path(first['record_path']).is_file())

    def test_missing_latest_output_requires_explicit_retry(self):
        with patch.object(refine, 'run_provider', side_effect=self.recognized):
            self.cloud()
            latest = self.cloud(force=True)
        Path(latest['markdown_path']).unlink()
        with patch.object(refine, 'run_provider') as provider:
            with self.assertRaisesRegex(DocVisionError, 'files are missing'):
                self.cloud()
        provider.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
