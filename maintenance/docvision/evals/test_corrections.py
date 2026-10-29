"""Human review is attributable, local to its scope, and never silently reused on new OCR."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'docvision' / 'scripts'))

from dv import corrections, read, util  # noqa: E402
from dv.base import DocVisionError, Options, RawBlock, RawDoc, RawPage  # noqa: E402
from dv.output import write_document  # noqa: E402


class CorrectionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'paper.png'
        Image.new('RGB', (120, 100), 'white').save(self.source)
        body = '$d_x$\n\nA neighboring paragraph.'
        self.docdir = write_document(RawDoc(provider='offline-test', model='fixture-1', markdown=body,
            pages=[RawPage(page=1, markdown=body, blocks=[
                RawBlock(type='formula', text='$d_x$', markdown='$d_x$', bbox=[.1, .1, .5, .3]),
                RawBlock(type='text', text='A neighboring paragraph.', markdown='A neighboring paragraph.', bbox=[.1, .4, .9, .8])])]),
            str(self.source), Options(), out_root=self.root / 'out',
            info={'pages': 1, 'sha256': util.sha256_file(self.source)})

    def accepted(self, **kwargs):
        return corrections.save(self.docdir, **{'page': 1, 'block_id': 'p1-b0', 'replacement': '$d_k$',
            'status': 'accepted', 'author': 'host', 'reviewer': 'visual-review-agent',
            'evidence': ['Opened source image at page 1 and checked the subscript.'], **kwargs})

    def mutate(self, edit):
        content = util.read_json(self.docdir / 'content.json')
        edit(content)
        util.write_json(self.docdir / 'content.json', content)

    def test_candidate_and_unknown_are_recorded_but_never_applied(self):
        for status in ('candidate', 'unknown'):
            corrections.save(self.docdir, page=1, block_id='p1-b0', replacement='Not accepted',
                             status=status, author='host', unresolved=['Subscript is unclear.'])
        result = json.loads(read.read(self.docdir, block_id='p1-b0', as_json=True))
        self.assertEqual(result['block']['markdown'], '$d_x$')
        self.assertNotIn('correction', result['block'])
        self.assertEqual(corrections.list_records(self.docdir, include_history=False), [])
        self.assertEqual({r['status'] for r in corrections.list_records(self.docdir)}, {'candidate', 'unknown'})

    def test_acceptance_requires_reviewer_evidence_and_human_or_host_author(self):
        for change in ({'reviewer': ''}, {'evidence': []}, {'author': 'paddleocr-cloud'}):
            with self.subTest(change=change), self.assertRaises(DocVisionError):
                self.accepted(**change)
        self.assertFalse((self.docdir / 'corrections').exists())

    def test_accepted_block_shows_revision_with_original_and_audit_provenance(self):
        before_content = (self.docdir / 'content.json').read_bytes()
        before_md = (self.docdir / 'paper.md').read_bytes()
        saved = self.accepted(unresolved=['The neighboring formula has not been reviewed.'])
        result = json.loads(read.read(self.docdir, block_id='p1-b0', as_json=True))
        block = result['block']
        self.assertEqual(block['markdown'], '$d_k$')
        self.assertEqual(block['original_ocr']['markdown'], '$d_x$')
        self.assertEqual(block['correction']['id'], saved['id'])
        self.assertEqual(saved['source_sha256'], util.sha256_file(self.source))
        self.assertEqual(saved['original']['text'], '$d_x$')
        self.assertEqual(len(saved['original']['sha256']), 64)
        self.assertFalse(block['accuracy_verified'])
        self.assertIn('neighboring formula', read.read(self.docdir, block_id='p1-b0'))
        self.assertEqual(json.loads(read.read(self.docdir, block_id='p1-b0', as_json=True, original=True))['block']['markdown'], '$d_x$')
        self.assertEqual((self.docdir / 'content.json').read_bytes(), before_content)
        self.assertEqual((self.docdir / 'paper.md').read_bytes(), before_md)

    def test_partial_bbox_is_annotation_and_never_replaces_whole_block_or_page(self):
        self.accepted(bbox='.1,.1,.2,.2', replacement='Only this small symbol is k.')
        result = json.loads(read.read(self.docdir, block_id='p1-b0', as_json=True))
        self.assertEqual(result['block']['markdown'], '$d_x$')
        self.assertNotIn('correction', result['block'])
        self.assertEqual(result['block']['correction_annotations'][0]['target']['scope'], 'region')
        page = json.loads(read.read(self.docdir, page=1, as_json=True))['pages'][0]
        self.assertIn('region annotation; no whole-block replacement', page['markdown'])
        self.assertIn('$d_x$', page['original_ocr_markdown'])
        self.assertIn('A neighboring paragraph.', page['markdown'])
        self.assertFalse(page['accuracy_verified'])

    def test_source_bytes_changed_does_not_apply_old_correction_and_cannot_save(self):
        self.accepted()
        Image.new('RGB', (120, 100), 'black').save(self.source)
        record = corrections.list_records(self.docdir)[0]
        self.assertFalse(record['effective'])
        self.assertIn('source_changed', record['invalid_reasons'])
        self.assertIn('$d_x$', read.read(self.docdir, block_id='p1-b0'))
        self.assertNotIn('$d_k$', read.read(self.docdir, block_id='p1-b0'))
        with self.assertRaisesRegex(DocVisionError, 'source_changed'):
            self.accepted()

    def test_new_ocr_text_or_layout_invalidates_the_original_result_fingerprint(self):
        self.accepted()
        self.mutate(lambda c: c['pages'][0]['blocks'][0].update(markdown='$d_y$', text='$d_y$'))
        record = corrections.list_records(self.docdir)[0]
        self.assertIn('original_result_changed', record['invalid_reasons'])
        self.assertFalse(record['effective'])
        self.assertIn('$d_y$', read.read(self.docdir, block_id='p1-b0'))
        self.accepted(replacement='$d_z$')
        self.mutate(lambda c: c['pages'][0]['blocks'][0].update(bbox=[.2, .1, .6, .3]))
        self.assertEqual(corrections.list_records(self.docdir, include_history=False), [])

    def test_caller_old_original_is_rejected_without_writing(self):
        for kwargs in ({'original_text': '$d_y$'}, {'original_sha256': '0' * 64}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(DocVisionError, 'original OCR result has changed'):
                self.accepted(**kwargs)
        self.assertFalse((self.docdir / 'corrections').exists())

    def test_revoke_latest_does_not_resurrect_superseded_record(self):
        first = self.accepted(replacement='$d_a$')
        second = self.accepted(replacement='$d_b$')
        self.assertEqual([r['id'] for r in corrections.list_records(self.docdir, include_history=False)], [second['id']])
        event = corrections.revoke(self.docdir, second['id'], reviewer='human-reader', reason='Needs another image check.')
        records = corrections.list_records(self.docdir)
        self.assertEqual(len(records), 2)
        self.assertTrue(records[0]['superseded'])
        self.assertEqual(records[1]['revocations'][0]['id'], event['id'])
        self.assertEqual(corrections.list_records(self.docdir, include_history=False), [])
        self.assertIn('$d_x$', read.read(self.docdir, block_id='p1-b0'))
        self.assertEqual(len(list((self.docdir / 'corrections').glob('*.json'))), 3)
        self.assertTrue((self.docdir / 'corrections' / f"{first['id']}.json").is_file())

    def test_later_candidate_does_not_implicitly_replace_an_accepted_revision(self):
        accepted = self.accepted()
        corrections.save(self.docdir, page=1, block_id='p1-b0', replacement='API candidate', author='host')
        self.assertEqual([r['id'] for r in corrections.list_records(self.docdir, include_history=False)], [accepted['id']])
        self.assertIn('$d_k$', read.read(self.docdir, block_id='p1-b0'))

    def test_region_only_without_a_block_is_visible_as_a_page_annotation(self):
        self.accepted(block_id=None, bbox=[.11, .11, .2, .2])
        page = json.loads(read.read(self.docdir, page=1, as_json=True))['pages'][0]
        self.assertEqual(page['blocks'][0]['markdown'], '$d_x$')
        self.assertEqual(page['corrections'][0]['target']['scope'], 'region')
        self.assertIn('Accepted revision:\n$d_k$', page['markdown'])
        block = json.loads(read.read(self.docdir, block_id='p1-b0', as_json=True))['block']
        self.assertEqual(block['markdown'], '$d_x$')
        self.assertEqual(block['correction_annotations'][0]['target']['scope'], 'region')

    def test_relative_source_survives_moving_document_and_correction_history(self):
        source_copy = self.docdir / 'source.png'
        shutil.copyfile(self.source, source_copy)
        for name in ('meta.json', 'content.json'):
            data = util.read_json(self.docdir / name)
            data['source']['path'] = 'source.png'
            util.write_json(self.docdir / name, data)
        self.accepted()
        moved = self.root / 'moved-paper'
        shutil.copytree(self.docdir, moved)
        self.assertEqual(read._source_path(util.read_json(moved / 'meta.json'), moved), moved / 'source.png')
        self.assertEqual(corrections.list_records(moved, include_history=False)[0]['source_verification_current'], 'verified_local_file')
        self.assertIn('$d_k$', read.read(moved, block_id='p1-b0'))
        self.assertTrue(read.render_page(moved, 1).is_file())

    def test_long_original_page_does_not_hide_the_accepted_revision(self):
        self.mutate(lambda c: c['pages'][0].update(markdown='Long original paragraph. ' * 2000))
        self.accepted()
        result = read.read(self.docdir, page=1, max_chars=1200)
        self.assertIn('Accepted revision:\n$d_k$', result)
        self.assertIn('truncated', result)

    def test_corrupt_history_cannot_silently_fall_back_to_older_acceptance(self):
        self.accepted()
        (self.docdir / 'corrections' / 'incomplete.json').write_text('{', encoding='utf-8')
        with self.assertRaisesRegex(DocVisionError, 'Cannot read correction history'):
            read.read(self.docdir, block_id='p1-b0')
        self.assertIn('$d_x$', read.read(self.docdir, block_id='p1-b0', original=True))


if __name__ == '__main__':
    unittest.main(verbosity=2)
