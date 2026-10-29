"""Cloud recovery behavior with offline responses; never submit real documents."""
from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'docvision' / 'scripts'))
from dv import cloud_jobs, util
from dv.base import DocVisionError, Options
from dv.providers import paddle_cloud

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
ENDPOINT = 'https://paddleocr.aistudio-app.com/api/v2/ocr/jobs'
SIGNED_URL = 'https://fixture.invalid/result.jsonl?signature=never-log-this'


def result_bytes(indices=(0,)):
    return json.dumps({'result': {'layoutParsingResults': [
        {'markdown': {'text': f'# Source page {index + 1}'},
         'prunedResult': {'page_index': index, 'parsing_res_list': [
             {'block_label': 'text', 'block_content': f'Page {index + 1}'}]}}
        for index in indices]}}).encode()


class CloudJobRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cloud-recovery-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'input.png'
        self.source.write_bytes(PNG)
        self.env = patch.dict(os.environ, {'DOCVISION_CONFIG': str(self.root / 'config.json'),
                                           'DOCVISION_PADDLE_TOKEN': 'fixture-secret-token'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.cfg = {'remote': {'paddle_base': ENDPOINT, 'consent': 'remote'}}
        self.config = patch.object(paddle_cloud.config, 'load', side_effect=lambda: self.cfg)
        self.config.start()
        self.addCleanup(self.config.stop)
        self.download = patch.object(paddle_cloud.util, 'download', return_value=result_bytes())
        self.mock_download = self.download.start()
        self.addCleanup(self.download.stop)
        self.calls = []
        self.fail_poll = True
        self.fail_submit = False
        self.api = patch.object(paddle_cloud, '_api', side_effect=self.request)
        self.mock_api = self.api.start()
        self.addCleanup(self.api.stop)

    def options(self, **kwargs):
        return Options(provider='paddleocr-cloud', allow_remote=True, output=self.root / 'out',
                       keep_raw=True, timeout=5, **kwargs)

    def request(self, url, token, deadline, **kwargs):
        post = kwargs.get('body') is not None or kwargs.get('payload') is not None
        self.calls.append('POST' if post else 'GET')
        receipts = cloud_jobs.list_jobs()
        if post:
            self.assertTrue(any(row['state'] == 'submission_unknown' and row['job_id'] is None for row in receipts))
            if self.fail_submit:
                raise TimeoutError('request may have reached service')
            return {'jobId': 'job-fixture'}
        self.assertTrue(any(row['job_id'] == 'job-fixture' for row in receipts))
        if self.fail_poll:
            raise TimeoutError('poll connection lost')
        return {'state': 'done', 'resultUrl': {'jsonUrl': SIGNED_URL}}

    def submit_interrupted(self, **kwargs):
        opts = self.options(**kwargs)
        with self.assertRaises(DocVisionError):
            paddle_cloud.convert(str(self.source), opts)
        return opts.extra['_cloud_task_id']

    def test_job_id_survives_disconnect_and_recovery_writes_complete_output_without_post(self):
        task_id = self.submit_interrupted(pages='1', mode='ocr')
        self.assertEqual(cloud_jobs.load(task_id)['state'], 'submitted')
        self.assertEqual(cloud_jobs.load(task_id)['job_id'], 'job-fixture')
        self.fail_poll = False
        recovered = paddle_cloud.resume_job(task_id, allow_remote=True)
        self.assertEqual(recovered['state'], 'done')
        out = Path(recovered['output_dir'])
        for name in ('content.json', 'meta.json', 'qa.json', out.name + '.md', 'raw/paddle-result.jsonl'):
            self.assertTrue((out / name).is_file(), name)
        self.assertEqual(self.calls.count('POST'), 1)
        before = list(self.calls)
        again = paddle_cloud.resume_job(task_id, allow_remote=True)
        self.assertEqual(again['output_dir'], recovered['output_dir'])
        self.assertEqual(self.calls, before)
        self.assertEqual(cloud_jobs.load(task_id)['state'], 'completed')

    def test_unknown_submission_blocks_recovery_and_repeated_post_until_explicit_new_attempt(self):
        self.fail_submit = True
        task_id = self.submit_interrupted()
        receipt = cloud_jobs.load(task_id)
        self.assertEqual(receipt['state'], 'submission_unknown')
        self.assertIsNone(receipt['job_id'])
        with self.assertRaisesRegex(DocVisionError, 'unknown'):
            paddle_cloud.resume_job(task_id, allow_remote=True)
        with self.assertRaisesRegex(DocVisionError, 'unfinished'):
            paddle_cloud.convert(str(self.source), self.options(force=True))
        self.assertEqual(self.calls, ['POST'])
        self.fail_submit = self.fail_poll = False
        _, meta = paddle_cloud.convert(str(self.source), self.options(extra={'cloud_new_attempt': 'true'}))
        self.assertNotEqual(meta['cloud_task_id'], task_id)
        self.assertEqual(cloud_jobs.load(meta['cloud_task_id'])['supersedes_task_ids'], [task_id])
        self.assertEqual(self.calls.count('POST'), 2)
        self.assertEqual(cloud_jobs.load(task_id)['state'], 'submission_unknown')

    def test_parsed_but_unwritten_result_blocks_new_post_and_can_be_recovered(self):
        self.fail_poll = False
        _, meta = paddle_cloud.convert(str(self.source), self.options())
        task_id = meta['cloud_task_id']
        self.assertEqual(cloud_jobs.load(task_id)['state'], 'parsed')
        with self.assertRaisesRegex(DocVisionError, 'unfinished'):
            paddle_cloud.convert(str(self.source), self.options())
        self.assertEqual(self.calls.count('POST'), 1)
        self.assertEqual(paddle_cloud.resume_job(task_id, allow_remote=True)['state'], 'done')
        self.assertEqual(self.calls.count('POST'), 1)

    def test_missing_job_id_is_retained_as_unknown(self):
        self.mock_api.side_effect = lambda *args, **kwargs: {}
        task_id = self.submit_interrupted()
        self.assertEqual(cloud_jobs.load(task_id)['state'], 'submission_unknown')
        with self.assertRaisesRegex(DocVisionError, 'unknown'):
            paddle_cloud.resume_job(task_id, allow_remote=True)
        self.assertEqual(self.mock_api.call_count, 1)

    def test_keyboard_interrupt_preserves_durable_job(self):
        def request(*args, **kwargs):
            if kwargs.get('body'):
                return {'jobId': 'job-fixture'}
            raise KeyboardInterrupt()
        self.mock_api.side_effect = request
        opts = self.options()
        with self.assertRaises(KeyboardInterrupt):
            paddle_cloud.convert(str(self.source), opts)
        record = cloud_jobs.load(opts.extra['_cloud_task_id'])
        self.assertEqual(record['job_id'], 'job-fixture')
        self.assertEqual(record['last_error_kind'], 'KeyboardInterrupt')
        self.mock_api.side_effect = self.request
        self.fail_poll = False
        self.assertEqual(paddle_cloud.resume_job(record['task_id'], allow_remote=True)['state'], 'done')
        self.assertEqual(self.calls, ['GET'])

    def test_download_failure_retains_job_and_does_not_log_token_or_signed_url(self):
        self.fail_poll = False
        self.mock_download.side_effect = DocVisionError('HTTP failure ' + SIGNED_URL + ' fixture-secret-token')
        opts = self.options()
        with self.assertRaises(DocVisionError) as caught:
            paddle_cloud.convert(str(self.source), opts)
        receipt = cloud_jobs.load(opts.extra['_cloud_task_id'])
        self.assertEqual(receipt['state'], 'remote_done')
        for content in (str(caught.exception), caught.exception.hint, json.dumps(receipt), json.dumps(cloud_jobs.list_jobs())):
            self.assertNotIn('never-log-this', content)
            self.assertNotIn('fixture-secret-token', content)
        self.mock_download.side_effect = None
        result = paddle_cloud.resume_job(receipt['task_id'], allow_remote=True)
        self.assertEqual(result['state'], 'done')
        self.assertEqual(self.calls.count('POST'), 1)

    def test_source_mismatch_stops_before_network_and_same_bytes_can_be_rebound(self):
        task_id = self.submit_interrupted()
        moved = self.root / 'moved.png'
        moved.write_bytes(PNG)
        self.source.write_bytes(b'changed')
        before = list(self.calls)
        with self.assertRaisesRegex(DocVisionError, 'SHA256'):
            paddle_cloud.resume_job(task_id, allow_remote=True)
        self.assertEqual(self.calls, before)
        self.source.unlink()
        self.fail_poll = False
        result = paddle_cloud.resume_job(task_id, allow_remote=True, source=str(moved))
        meta = util.read_json(Path(result['output_dir']) / 'meta.json', {})
        self.assertEqual(meta['source']['sha256'], util.sha256_bytes(PNG))
        self.assertEqual(self.calls.count('POST'), 1)
        self.assertEqual(cloud_jobs.load(task_id)['source']['path'], str(moved.resolve()))
        before = list(self.calls)
        repeated = paddle_cloud.resume_job(task_id, allow_remote=True)
        self.assertEqual(repeated['output_dir'], result['output_dir'])
        self.assertEqual(self.calls, before)

    def test_consent_and_endpoint_checks_are_before_any_recovery_request(self):
        task_id = self.submit_interrupted()
        before = list(self.calls)
        with self.assertRaisesRegex(DocVisionError, 'allow-remote'):
            paddle_cloud.resume_job(task_id)
        self.cfg['remote']['consent'] = 'local-only'
        with self.assertRaisesRegex(DocVisionError, 'consent'):
            paddle_cloud.resume_job(task_id, allow_remote=True)
        self.cfg['remote']['consent'] = 'remote'
        self.cfg['remote']['paddle_base'] = 'https://different.invalid/jobs'
        with self.assertRaisesRegex(DocVisionError, 'endpoint'):
            paddle_cloud.resume_job(task_id, allow_remote=True)
        self.assertEqual(self.calls, before)

    def test_page_mapping_and_original_options_survive_recovery(self):
        self.source = self.root / 'four-pages.pdf'
        self.source.write_bytes(b'offline PDF fixture; parser inspection is mocked')
        info = {'is_pdf': True, 'is_image': False, 'pages': 4, 'bytes': self.source.stat().st_size,
                'sha256': util.sha256_file(self.source), 'source': str(self.source)}
        self.mock_download.return_value = result_bytes((0, 1))
        with patch.object(paddle_cloud, 'inspect_input', return_value=info):
            task_id = self.submit_interrupted(pages='2,4', images=False, mode='chart')
            self.fail_poll = False
            result = paddle_cloud.resume_job(task_id, allow_remote=True)
        content = util.read_json(Path(result['output_dir']) / 'content.json', {})
        self.assertEqual([p['page'] for p in content['pages']], [2, 4])
        receipt = cloud_jobs.load(task_id)
        self.assertEqual(receipt['request']['pageRanges'], '2,4')
        self.assertTrue(receipt['request']['optionalPayload']['useChartRecognition'])
        self.assertTrue((Path(result['output_dir']) / 'raw/paddle-result.jsonl').is_file())
        meta = util.read_json(Path(result['output_dir']) / 'meta.json', {})
        self.assertEqual(meta['raw_meta']['cache_request'], receipt['cache_request'])

    def test_refinement_is_linked_before_post_and_recovered_record_becomes_recognized(self):
        original = self.root / 'original.png'
        original.write_bytes(PNG)
        docdir = self.root / 'document'
        directory = docdir / 'refinements' / 'region-1'
        directory.mkdir(parents=True)
        self.source = directory / 'input.png'
        self.source.write_bytes(PNG)
        record_path = directory / 'record.json'
        util.write_json(docdir / 'meta.json', {'source': {'path': '../original.png',
                                                        'sha256': util.sha256_file(original)}})
        util.write_json(record_path, {'schema': 'docvision.refinement/1', 'id': 'region-1', 'state': 'submitted',
                                    'source': {'path': str(original), 'sha256': util.sha256_file(original)},
                                    'input_sha256': util.sha256_file(self.source), 'image_path': str(self.source)})
        request = self.request
        def check_link(*args, **kwargs):
            if kwargs.get('body'):
                self.assertTrue(util.read_json(record_path, {})['cloud_task_id'])
            return request(*args, **kwargs)
        self.mock_api.side_effect = check_link
        task_id = self.submit_interrupted(extra={'_cloud_refinement_record': str(record_path),
                                                'refine_task': 'formula', 'refine_is_region': True})
        record = util.read_json(record_path, {})
        record.update(state='failed', error='poll lost')
        util.write_json(record_path, record)
        self.fail_poll = False
        result = paddle_cloud.resume_job(task_id, allow_remote=True)
        updated = util.read_json(record_path, {})
        self.assertEqual(updated['state'], 'recognized')
        self.assertEqual(updated['cloud_task_id'], task_id)
        self.assertNotIn('error', updated)
        self.assertTrue(Path(result['markdown_path']).is_file())
        self.assertEqual(self.calls.count('POST'), 1)
        recovered_meta = util.read_json(Path(result['output_dir']) / 'meta.json', {})
        self.assertFalse(Path(recovered_meta['source']['path']).is_absolute())

        # Rename the output folder (its Markdown filename does not change),
        # relink the original and move the document. Explicit --record locates
        # its portable refinement; an intact success needs no further GET.
        renamed_output = Path(result['output_dir']).with_name('renamed-result')
        Path(result['output_dir']).rename(renamed_output)
        from dv.portability import resolve_refinement, save_refinement
        portable = resolve_refinement(docdir, updated, record_path)
        portable['markdown_path'] = str(renamed_output / Path(result['markdown_path']).name)
        save_refinement(docdir, record_path, portable)
        moved_original = original.with_name('relinked-original.png')
        original.rename(moved_original)
        util.write_json(docdir / 'meta.json', {'source': {'path': '../relinked-original.png',
                                                        'sha256': util.sha256_file(moved_original)}})
        moved_docdir = docdir.with_name('moved-document')
        docdir.rename(moved_docdir)
        moved_record = moved_docdir / record_path.relative_to(docdir)
        before = list(self.calls)
        again = paddle_cloud.resume_job(task_id, allow_remote=True, refinement_record=moved_record)
        self.assertEqual(self.calls, before)
        self.assertEqual(Path(again['output_dir']).name, 'renamed-result')
        self.assertTrue(Path(again['markdown_path']).is_file())
        self.assertEqual(Path(again['markdown_path']).name, Path(result['markdown_path']).name)

    def test_changed_refinement_original_prevents_recovery(self):
        original = self.root / 'original.png'
        original.write_bytes(PNG)
        directory = self.root / 'doc' / 'refinements' / 'region'
        directory.mkdir(parents=True)
        record_path = directory / 'record.json'
        util.write_json(record_path, {'schema': 'docvision.refinement/1', 'source': {'path': str(original),
                                      'sha256': util.sha256_file(original)}, 'input_sha256': util.sha256_file(self.source)})
        task_id = self.submit_interrupted(extra={'_cloud_refinement_record': str(record_path)})
        original.write_bytes(b'changed')
        before = list(self.calls)
        with self.assertRaisesRegex(DocVisionError, 'original source'):
            paddle_cloud.resume_job(task_id, allow_remote=True)
        self.assertEqual(self.calls, before)

    def test_url_receipt_does_not_store_signed_source_and_recovery_is_explicitly_unsupported(self):
        source = 'https://fixture.invalid/source.pdf?signature=private-source-link'
        opts = self.options(pages='1')
        with self.assertRaises(DocVisionError):
            paddle_cloud.convert(source, opts)
        task_id = opts.extra['_cloud_task_id']
        self.assertNotIn('private-source-link', json.dumps(cloud_jobs.load(task_id)))
        before = list(self.calls)
        with self.assertRaisesRegex(DocVisionError, 'URL-source'):
            paddle_cloud.resume_job(task_id, allow_remote=True)
        self.assertEqual(self.calls, before)

    def test_intent_persistence_failure_prevents_submission(self):
        with patch.object(cloud_jobs, '_write', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):
                paddle_cloud.convert(str(self.source), self.options())
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
