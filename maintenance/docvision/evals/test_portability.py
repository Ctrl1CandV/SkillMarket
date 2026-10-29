"""A moved paper keeps its evidence; relinking cannot disguise changed bytes."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'docvision' / 'scripts'))
from dv import cache, config, corrections, portability, read, refine, util
from dv.base import DocVisionError, Options, RawBlock, RawDoc, RawPage
from dv.output import write_document


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'paper.png'
        Image.new('RGB', (80, 60), 'white').save(self.source)
        self.opts = Options(provider='mineru-local')
        self.info = {'source': str(self.source), 'pages': 1, 'sha256': util.sha256_file(self.source)}
        self.raw = RawDoc(markdown='Original formula', provider='mineru-local', pages=[RawPage(page=1,
            markdown='Original formula', blocks=[RawBlock(type='formula', text='Original formula',
                markdown='Original formula', bbox=[.1, .1, .8, .8])])])
        self.doc = write_document(self.raw, str(self.source), self.opts, out_root=self.root / 'out',
            info=self.info, raw_meta={'cache_request': cache.request_signature(self.info, self.opts)})
        mock = patch.object(config, 'load', return_value={})
        mock.start()
        self.addCleanup(mock.stop)

    def packet(self):
        return refine.run(self.doc, page=1, block_id='p1-b0', provider='packet')

    def test_new_record_is_relative_and_reused_after_document_rename(self):
        original = self.packet()
        on_disk = util.read_json(Path(original['record_path']))
        self.assertEqual(on_disk['path_base'], 'document')
        self.assertFalse(Path(on_disk['image_path']).is_absolute())
        moved = self.root / 'renamed-document'
        self.doc.rename(moved)
        self.doc = moved
        result = self.packet()
        self.assertTrue(result['cached'])
        self.assertTrue(Path(result['image_path']).is_file())
        self.assertTrue(Path(result['image_path']).is_relative_to(moved))
        self.assertEqual(read.read(moved, page=1).count('Original formula'), 1)

    def test_move_source_and_document_relink_then_crop_and_resume(self):
        self.packet()
        moved = self.root / 'library'
        moved.mkdir()
        new_source = moved / 'renamed-paper.png'
        self.source.rename(new_source)
        new_doc = moved / 'reading-output'
        self.doc.rename(new_doc)
        result = portability.relink(new_doc, source=str(new_source))
        self.assertEqual(result['source_sha256'], self.info['sha256'])
        self.assertEqual(util.read_json(new_doc / 'meta.json')['source']['path'], '../renamed-paper.png')
        self.assertTrue(read.render_page(new_doc, 1).is_file())
        self.assertTrue(read.crop(new_doc, page=1, block_id='p1-b0').is_file())
        self.assertEqual(len(refine.list_results(new_doc)), 1)
        info = {**self.info, 'source': str(new_source)}
        self.assertEqual(cache.find_existing(moved, info, self.opts), new_doc)
        # Move the whole library again; relative source follows with no second relink.
        newer = self.root / 'library-again'
        moved.rename(newer)
        self.assertTrue(read.render_page(newer / 'reading-output', 1).is_file())

    def test_wrong_source_rejected_without_metadata_mutation(self):
        before = (self.doc / 'meta.json').read_bytes()
        other = self.root / 'other.png'
        Image.new('RGB', (80, 60), 'black').save(other)
        with self.assertRaisesRegex(DocVisionError, 'SHA-256'):
            portability.relink(self.doc, source=str(other))
        self.assertEqual((self.doc / 'meta.json').read_bytes(), before)
        self.assertFalse((self.doc / 'relinks').exists())

    def test_legacy_paths_migrate_to_moved_tree_even_if_old_tree_still_exists(self):
        result = self.packet()
        # Emulate 0.4.1 absolute-path records, then copy the output directory.
        util.write_json(Path(result['record_path']), result)
        copied = self.root / 'copy'
        shutil.copytree(self.doc, copied)
        portability.relink(copied)
        found = refine.list_results(copied)[0]
        self.assertTrue(Path(found['image_path']).is_relative_to(copied))
        self.assertFalse(Path(util.read_json(Path(found['record_path']))['image_path']).is_absolute())

    def recognized(self):
        result = RawDoc(markdown='Recognized crop', provider='mineru-local', pages=[RawPage(
            page=1, markdown='Recognized crop', blocks=[RawBlock(type='formula',
                markdown='Recognized crop', text='Recognized crop', bbox=[0, 0, 1, 1])])])
        with patch.object(refine, 'run_provider', return_value=(result, {})):
            record = refine.run(self.doc, page=1, block_id='p1-b0', provider='mineru-local')
        self.assertEqual(record['state'], 'recognized')
        return record

    def test_new_recognized_crop_source_survives_move_and_relink(self):
        record = self.recognized()
        self.assertFalse(Path(util.read_json(Path(record['record_path']))['record_path']).is_absolute())
        result_relative = Path(record['markdown_path']).parent.relative_to(self.doc)
        moved = self.root / 'moved-recognized'
        self.doc.rename(moved)
        portability.relink(moved)
        crop_doc = moved / result_relative
        self.assertTrue(read.render_page(crop_doc, 1).is_file())
        self.assertTrue(read._source_path(util.read_json(crop_doc / 'meta.json'), crop_doc).is_relative_to(moved))

    def test_legacy_recognized_crop_rebinds_to_copy_not_existing_original(self):
        record = self.recognized()
        util.write_json(Path(record['record_path']), record)
        result_relative = Path(record['markdown_path']).parent.relative_to(self.doc)
        copied = self.root / 'copied-recognized'
        shutil.copytree(self.doc, copied)
        portability.relink(copied)
        crop_doc = copied / result_relative
        source = read._source_path(util.read_json(crop_doc / 'meta.json'), crop_doc)
        self.assertIsNotNone(source)
        self.assertTrue(source.resolve().is_relative_to(copied))
        self.assertTrue(read.render_page(crop_doc, 1).is_file())

    def test_accepted_correction_survives_source_relink_and_library_move(self):
        correction = corrections.save(self.doc, page=1, block_id='p1-b0', replacement='Reviewed formula',
            status='accepted', author='human', reviewer='reader', evidence=['Viewed paper.png formula.'])
        original_history = (self.doc / 'corrections' / f"{correction['id']}.json").read_bytes()
        library = self.root / 'library-with-corrections'
        library.mkdir()
        new_source = library / 'renamed.png'
        self.source.rename(new_source)
        new_doc = library / 'document'
        self.doc.rename(new_doc)
        portability.relink(new_doc, source=str(new_source))
        moved = self.root / 'moved-library-with-corrections'
        library.rename(moved)
        new_doc = moved / 'document'
        self.assertEqual(corrections.list_records(new_doc, include_history=False)[0]['id'], correction['id'])
        self.assertEqual((new_doc / 'corrections' / f"{correction['id']}.json").read_bytes(), original_history)
        self.assertIn('Reviewed formula', read.read(new_doc, block_id='p1-b0'))
        self.assertIn('Original formula', read.read(new_doc, block_id='p1-b0', original=True))

    def test_dry_run_writes_nothing(self):
        self.packet()
        before = {p.relative_to(self.doc): p.read_bytes() for p in self.doc.rglob('*') if p.is_file()}
        portability.relink(self.doc, source=str(self.source), dry_run=True)
        self.assertEqual(before, {p.relative_to(self.doc): p.read_bytes() for p in self.doc.rglob('*') if p.is_file()})

    def test_internal_reference_escape_is_rejected(self):
        with self.assertRaisesRegex(DocVisionError, 'escapes'):
            portability.resolve_refinement(self.doc, {'image_path': '../outside.png'})

    def test_permission_and_token_do_not_automatically_select_cloud(self):
        with patch.object(config, 'remote_consent', return_value='remote'), \
             patch.object(config, 'remote_keys', return_value={'paddle': 'fake-key'}):
            for task in ('formula', 'table', 'transcribe'):
                self.assertEqual(refine.choose_provider('auto', task, True), 'packet')
            self.assertEqual(refine.choose_provider('paddleocr-cloud', 'formula', True), 'paddleocr-cloud')


if __name__ == '__main__':
    unittest.main()
