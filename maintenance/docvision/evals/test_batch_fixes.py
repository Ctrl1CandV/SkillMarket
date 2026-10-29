"""Batch reuse and command contracts; no OCR runtime or external services."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'docvision' / 'scripts'))
from dv import cache, cli, config, doctor, util
from dv.base import DocVisionError, Options, RawDoc, RawPage


class BatchFixTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / 'paper.png'
        self.source.write_bytes(b'local fake provider input')
        self.out = self.root / 'out'
        self.env = patch.dict(os.environ, {'DOCVISION_CONFIG': str(self.root / 'config.json')})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.engine = config.Engine(name='mineru', available=True, exe='fixture-engine',
                                    python='fixture-python', version='4.0.12',
                                    extra={'mineru_home': str(self.root / 'models')})
        engine = patch.object(config, 'discover_mineru', return_value=self.engine)
        engine.start()
        self.addCleanup(engine.stop)

    def recognize(self, provider, source, opts):
        return RawDoc('recognized text', [RawPage(1, markdown='recognized text')],
                      provider=provider), {}

    def test_local_resume_survives_consent_output_and_other_engine_changes(self):
        opts = Options(provider='mineru-local', resume=True)
        with patch.object(cli, 'run_provider', side_effect=self.recognize) as inference:
            first = cli._convert_one(str(self.source), opts, self.out)
            cfg = config.load()
            cfg['remote']['consent'] = 'remote'
            cfg['remote']['paddle_base'] = 'https://changed.example/jobs'
            cfg['output']['default_dir'] = 'different-project'
            cfg['engines']['vlm']['model'] = 'unrelated'
            config.save(cfg)
            second = cli._convert_one(str(self.source), opts, self.out)
        self.assertEqual(first['state'], 'done')
        self.assertEqual(second['state'], 'skipped')
        self.assertEqual(inference.call_count, 1)
        self.assertEqual(first['output_dir'], second['output_dir'])

    def test_model_home_and_runtime_changes_invalidate_cache(self):
        first = cache.provider_context('mineru-local')
        self.engine.extra['mineru_home'] = str(self.root / 'other-models')
        self.assertNotEqual(first, cache.provider_context('mineru-local'))
        self.engine.extra['mineru_home'] = str(self.root / 'models')
        self.engine.version = '4.0.13'
        self.assertNotEqual(first, cache.provider_context('mineru-local'))

    def test_force_is_not_silently_skipped_by_resume(self):
        opts = Options(provider='mineru-local', resume=True)
        with patch.object(cli, 'run_provider', side_effect=self.recognize) as inference:
            a = cli._convert_one(str(self.source), opts, self.out)
            opts.force = True
            b = cli._convert_one(str(self.source), opts, self.out)
        self.assertEqual(inference.call_count, 2)
        self.assertEqual(b['state'], 'done')
        self.assertEqual(a['output_dir'], b['output_dir'])

    def test_fast_does_not_extract_whole_pdf_just_to_decide_ocr(self):
        source = self.root / 'paper.pdf'
        source.write_bytes(b'PDF inspected without extraction for this routing test')
        with patch.object(util, 'pdf_page_count', return_value=20), \
             patch.object(util, 'pdf_text_stats', side_effect=AssertionError('unnecessary full extraction')):
            info = cli.detect.inspect_input(str(source), Options(tier='fast'))
        self.assertEqual(info['pages'], 20)

    def test_index_skips_unrelated_metadata_and_revalidates_candidates(self):
        opts = Options(provider='mineru-local', resume=True)
        with patch.object(cli, 'run_provider', side_effect=self.recognize):
            result = cli._convert_one(str(self.source), opts, self.out)
        for i in range(30):
            util.write_json(self.out / f'unrelated-{i}' / 'meta.json',
                            {'source': {'sha256': f'other-{i}'}})
        index = cache.ResumeIndex(self.out)
        info = cli.detect.inspect_input(str(self.source), opts)
        context = cache.provider_context('mineru-local')
        with patch.object(util, 'read_json', wraps=util.read_json) as reads:
            for _ in range(3):
                hit = cache.find_existing(self.out, info, opts, provider='mineru-local',
                                          context=context, index=index)
                self.assertEqual(hit.resolve(), Path(result['output_dir']).resolve())
        self.assertFalse(any('unrelated-' in str(call.args[0]) for call in reads.call_args_list))
        # An index is not permission to reuse a candidate changed by another writer.
        util.write_json(hit / 'qa.json', {'status': 'fail'})
        self.assertIsNone(cache.find_existing(self.out, info, opts, provider='mineru-local',
                                              context=context, index=index))

    def test_in_progress_document_is_not_reused(self):
        opts = Options(provider='mineru-local', resume=True)
        with patch.object(cli, 'run_provider', side_effect=self.recognize):
            result = cli._convert_one(str(self.source), opts, self.out)
        docdir = Path(result['output_dir'])
        (docdir / '.docvision-write.lock').touch()
        info = cli.detect.inspect_input(str(self.source), opts)
        self.assertIsNone(cache.find_existing(self.out, info, opts, provider='mineru-local',
                                              context=cache.provider_context('mineru-local')))

    def test_identical_copy_keeps_its_own_source_provenance(self):
        opts = Options(provider='mineru-local', resume=True)
        with patch.object(cli, 'run_provider', side_effect=self.recognize):
            cli._convert_one(str(self.source), opts, self.out)
        copied = self.root / 'copy.png'
        copied.write_bytes(self.source.read_bytes())
        info = cli.detect.inspect_input(str(copied), opts)
        self.assertIsNone(cache.find_existing(self.out, info, opts, provider='mineru-local',
                                              context=cache.provider_context('mineru-local')))

    def test_dry_run_consent_does_not_write_configuration(self):
        config.set_consent('local-only')
        before = util.config_path().read_bytes()
        args = cli.build_parser().parse_args(['setup', '--remote', '--dry-run'])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.cmd_setup(args), 0)
        self.assertEqual(util.config_path().read_bytes(), before)
        self.assertEqual(config.remote_consent(), 'local-only')

    def test_core_only_doctor_reports_text_reading_without_claiming_ocr(self):
        engines = {name: config.Engine(name) for name in ('mineru', 'paddleocr', 'vlm')}
        with patch.object(config, 'engine_status', return_value=engines), \
             patch.object(config, 'remote_keys', return_value={}), \
             patch.object(doctor, '_module', return_value={'ok': True, 'detail': 'installed'}), \
             patch.object(util, 'gpu_summary', return_value={'available': False}), \
             patch.object(util, 'credentials_path', return_value=self.root / 'absent'):
            report = doctor.collect()
        self.assertTrue(report['healthy'])
        self.assertTrue(report['text_local_available'])
        self.assertFalse(report['local_available'])
        self.assertIn('--tier fast', report['next_actions'][0])

    def test_batch_reports_inference_and_reuse_separately(self):
        args = cli.build_parser().parse_args(['convert', str(self.source), '--provider', 'mineru-local',
                                             '--output', str(self.out), '--resume', '--json'])
        with patch.object(cli, 'run_provider', side_effect=self.recognize):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.cmd_convert(args), 0)
            first = json.loads(output.getvalue())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.cmd_convert(args), 0)
            second = json.loads(output.getvalue())
        self.assertEqual(first['pages_processed'], 1)
        self.assertEqual(second['pages_processed'], 0)
        self.assertEqual(second['skipped'], 1)
        self.assertIn('provider', first['results'][0]['timings_seconds'])
        self.assertNotIn('provider', second['results'][0]['timings_seconds'])
        self.assertGreaterEqual(first['elapsed_seconds'], first['results'][0]['elapsed'])

    def test_parallel_cloud_failures_retain_each_files_own_receipt(self):
        second = self.root / 'second.png'
        second.write_bytes(self.source.read_bytes())
        options = Options(provider='paddleocr-cloud', allow_remote=True)
        barrier = threading.Barrier(2)
        def interrupted(provider, source, opts):
            opts.extra['_cloud_task_id'] = Path(source).stem
            barrier.wait(timeout=5)
            raise DocVisionError('fixture poll interrupted after durable submission')
        with patch.object(config, 'remote_consent', return_value='remote'), \
             patch.object(cli, 'run_provider', side_effect=interrupted), ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda source: cli._convert_one(str(source), options, self.out),
                                    [self.source, second]))
        self.assertEqual([r['cloud_task_id'] for r in results], ['paper', 'second'])
        self.assertNotIn('_cloud_task_id', options.extra)

    def test_cloud_receipt_and_retry_intent_do_not_invalidate_completed_cache_signature(self):
        info = {'sha256': 'source-hash', 'pages': 1}
        options = Options(provider='paddleocr-cloud', extra={'model': 'fixture-model'})
        before = cache.request_signature(info, options)
        context = cache.provider_context(options.provider, options.extra)
        options.extra.update(_cloud_task_id='receipt', _cloud_refinement_record='local-path', cloud_new_attempt=True)
        self.assertEqual(cache.request_signature(info, options), before)
        self.assertEqual(cache.provider_context(options.provider, options.extra), context)


if __name__ == '__main__':
    unittest.main()
