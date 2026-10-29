"""Digital-paper fast reading and task-aware local region recognition."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'docvision' / 'scripts'))
from dv import cli, config, detect, refine, util
from dv.base import DocVisionError, Options
from dv.providers import PROVIDERS, paddle_local, text_local


class ReadingRouteTests(unittest.TestCase):
    def test_fast_pdf_does_not_discover_or_start_ocr(self):
        with patch.object(config, 'discover_mineru', side_effect=AssertionError('no OCR discovery')), \
             patch.object(config, 'discover_paddle', side_effect=AssertionError('no OCR discovery')):
            for mode in ('auto', 'text'):
                self.assertEqual(detect.choose_provider('paper.PDF', Options(tier='fast', mode=mode)),
                                 'text-local')
        self.assertEqual(PROVIDERS['text-local']['layer'], 'local')
        self.assertEqual(detect.describe_route('text-local')['privacy'], 'local')

    def test_explicit_provider_and_ocr_tasks_keep_their_routes(self):
        self.assertEqual(detect.choose_provider('paper.pdf', Options(tier='fast', provider='paddleocr-local')),
                         'paddleocr-local')
        engine = config.Engine('mineru', available=True)
        with patch.object(config, 'discover_mineru', return_value=engine):
            for source, opts in [('paper.pdf', Options(tier='fast', mode='ocr')),
                                 ('paper.pdf', Options(tier='standard')),
                                 ('scan.png', Options(tier='fast')),
                                 ('https://example.test/paper.pdf', Options(tier='fast'))]:
                self.assertEqual(detect.choose_provider(source, opts), 'mineru-local')

    def test_region_specialization_requires_verified_paddle_runtime(self):
        opts = Options(extra={'refine_task': 'formula', 'refine_is_region': True})
        for version in ('', '2.9.1', '3.6.0'):
            engine = config.Engine('paddleocr', exe='paddleocr',
                                   extra={'package_versions': {'paddleocr': version}})
            with self.assertRaisesRegex(DocVisionError, '3.7'):
                paddle_local._command(engine, Path('crop.png'), Path('out'), opts, 'cpu')

    def test_known_formula_and_table_regions_skip_layout_detection(self):
        engine = config.Engine('paddleocr', exe='paddleocr',
                               extra={'package_versions': {'paddleocr': '3.7.0'}})
        for task in ('formula', 'table'):
            opts = Options(mode='ocr', extra={'refine_task': task, 'refine_is_region': True})
            command = paddle_local._command(engine, Path('crop.png'), Path('out'), opts, 'gpu:0')
            self.assertEqual(command[command.index('--prompt_label') + 1], task)
            self.assertEqual(command[command.index('--use_layout_detection') + 1], 'False')
            self.assertEqual(command[command.index('--format_block_content') + 1], 'True')

    def test_full_page_and_transcription_keep_layout_analysis(self):
        engine = config.Engine('paddleocr', exe='paddleocr')
        for extra in ({}, {'refine_task': 'formula', 'refine_is_region': False},
                      {'refine_task': 'transcribe', 'refine_is_region': True}):
            command = paddle_local._command(engine, Path('page.png'), Path('out'), Options(extra=extra), 'cpu')
            self.assertNotIn('--prompt_label', command)
            self.assertNotIn('--use_layout_detection', command)


@unittest.skipUnless(importlib.util.find_spec('pypdf'), 'core pypdf dependency is needed')
class TextReadingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='docvision-text-reading-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def pdf(self, texts):
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
        writer = PdfWriter()
        for text in texts:
            page = writer.add_blank_page(width=612, height=792)
            if text:
                font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                         NameObject('/Subtype'): NameObject('/Type1'),
                                         NameObject('/BaseFont'): NameObject('/Helvetica')})
                page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({
                    NameObject('/F1'): font})})
                stream = DecodedStreamObject()
                stream.set_data(f'BT /F1 12 Tf 30 760 Td ({text}) Tj ET'.encode('ascii'))
                page[NameObject('/Contents')] = writer._add_object(stream)
        source = self.root / 'paper.pdf'
        with source.open('wb') as output:
            writer.write(output)
        return source

    def test_real_text_extraction_retains_physical_pages_without_invented_boxes(self):
        source = self.pdf(['First page.', 'Second-page evidence.', '', 'Fourth-page conclusion.'])
        raw, meta = text_local.convert(str(source), Options(tier='fast', pages='2,4'))
        self.assertEqual([p.page for p in raw.pages], [2, 4])
        self.assertIn('Second-page evidence.', raw.markdown)
        self.assertIn('Fourth-page conclusion.', raw.markdown)
        self.assertNotIn('First page.', raw.markdown)
        self.assertTrue(all(block.bbox is None for page in raw.pages for block in page.blocks))
        self.assertEqual(meta['source_pages'], 4)

    def test_empty_text_selection_fails_with_manual_visual_reading_hint(self):
        source = self.pdf(['Readable body.', ''])
        with self.assertRaisesRegex(DocVisionError, 'No embedded text') as raised:
            text_local.convert(str(source), Options(tier='fast', pages='2'))
        self.assertIn('docvision pages', raised.exception.hint)
        self.assertIn('OCR', raised.exception.hint)

    def test_mixed_text_and_blank_pages_are_not_silently_dropped(self):
        source = self.pdf(['Readable body.', ''])
        raw, _ = text_local.convert(str(source), Options(tier='fast'))
        self.assertEqual([p.page for p in raw.pages], [1, 2])
        self.assertEqual(raw.pages[1].markdown, '')
        self.assertTrue(any('Pages [2]' in warning for warning in raw.warnings))
        with patch.object(config, 'load', return_value=config.DEFAULT_CONFIG):
            result = cli._convert_one(str(source), Options(tier='fast'), self.root / 'output')
        self.assertEqual(result['state'], 'done')
        self.assertEqual(result['qa'], 'warn')

    def test_all_empty_pdf_cannot_be_reported_as_successful(self):
        source = self.pdf(['', ''])
        result = cli._convert_one(str(source), Options(tier='fast'), self.root / 'output')
        self.assertEqual(result['state'], 'failed')
        self.assertIsNone(result['output_dir'])
        self.assertIn('No embedded text', result['error'])

    def test_empty_page_range_and_non_text_tasks_are_rejected(self):
        source = self.pdf(['A paper.'])
        with self.assertRaisesRegex(DocVisionError, 'no PDF pages'):
            text_local.convert(str(source), Options(pages='10'))
        with self.assertRaisesRegex(DocVisionError, 'cannot perform OCR'):
            text_local.convert(str(source), Options(mode='formula'))
        with self.assertRaisesRegex(DocVisionError, 'local PDF'):
            text_local.convert('https://example.test/paper.pdf', Options())

    def test_dry_run_reports_selection_without_claiming_a_document(self):
        source = self.pdf(['A paper.', 'Next page.'])
        raw, meta = text_local.convert(str(source), Options(pages='2', dry_run=True))
        self.assertIsNone(raw)
        self.assertEqual(meta['pages'], [2])

    @unittest.skipUnless(importlib.util.find_spec('pypdfium2') and importlib.util.find_spec('PIL'),
                         'core renderer is needed for a real packet')
    def test_core_only_fast_output_can_create_a_real_page_packet(self):
        source = self.pdf(['A digital paper ready for visual review.'])
        with patch.object(config, 'load', return_value=config.DEFAULT_CONFIG), \
             patch.object(config, 'discover_mineru', side_effect=AssertionError('no OCR engine needed')), \
             patch.object(config, 'discover_paddle', side_effect=AssertionError('no OCR engine needed')):
            result = cli._convert_one(str(source), Options(tier='fast'), self.root / 'output')
            self.assertEqual(result['state'], 'done', result)
            record = refine.run(Path(result['output_dir']), page=1, provider='packet')
        self.assertEqual(record['state'], 'review_required')
        self.assertTrue(Path(record['image_path']).is_file())
        self.assertTrue(Path(record['context_path']).is_file())


if __name__ == '__main__':
    unittest.main(verbosity=2)
