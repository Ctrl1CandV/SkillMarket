"""Portable behavior checks. Synthetic package/artifact fixtures are not visual reviews."""
import copy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import warnings
from xml.etree import ElementTree as ET
import zipfile

sys.dont_write_bytecode = True
# In dev: maintenance/presentation-craft/evals/check.py -> repository root.
SCRIPTS = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else Path(__file__).resolve().parents[3] / 'presentation-craft' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from animate_pptx import animate, inventory
from audit_pptx import audit, NS, sha256
from finalize import finalize


def package_parts():
    p, a, r = NS['p'], NS['a'], NS['r']
    slide = f'''<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="{p}" xmlns:a="{a}" xmlns:r="{r}" xmlns:q="urn:fixture" q:keep="yes">
<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name="root"/></p:nvGrpSpPr>
<p:sp><p:nvSpPr><p:cNvPr id="2" name="first"/></p:nvSpPr><p:spPr><a:xfrm><a:off x="914400" y="914400"/><a:ext cx="1828800" cy="914400"/></a:xfrm></p:spPr><p:txBody><a:p><a:r><a:t>First evidence</a:t></a:r></a:p></p:txBody></p:sp>
<p:pic><p:nvPicPr><p:cNvPr id="3" name="image"/></p:nvPicPr><p:blipFill><a:blip r:embed="image"/></p:blipFill><p:spPr><a:xfrm><a:off x="914400" y="2743200"/><a:ext cx="1828800" cy="914400"/></a:xfrm></p:spPr></p:pic>
<p:sp><p:nvSpPr><p:cNvPr id="4" name="second"/></p:nvSpPr><p:spPr/><p:txBody><a:p><a:r><a:t>Next explanation</a:t></a:r></a:p></p:txBody></p:sp>
</p:spTree></p:cSld><p:extLst><p:ext uri="urn:fixture"><q:payload>preserve me</q:payload></p:ext></p:extLst></p:sld>'''.encode()
    rel_ns = 'http://schemas.openxmlformats.org/package/2006/relationships'
    return {
        'ppt/presentation.xml': f'<p:presentation xmlns:p="{p}" xmlns:r="{r}"><p:sldIdLst><p:sldId id="256" r:id="b"/><p:sldId id="257" r:id="a"/></p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/></p:presentation>'.encode(),
        'ppt/_rels/presentation.xml.rels': f'<Relationships xmlns="{rel_ns}"><Relationship Id="b" Target="slides/slide2.xml"/><Relationship Id="a" Target="slides/slide1.xml"/></Relationships>'.encode(),
        'ppt/slides/slide1.xml': slide,
        'ppt/slides/slide2.xml': slide,
        'ppt/slides/_rels/slide2.xml.rels': f'<Relationships xmlns="{rel_ns}"><Relationship Id="image" Target="../media/image.png"/><Relationship Id="notes" Type="{r}/notesSlide" Target="../notesSlides/notes1.xml"/></Relationships>'.encode(),
        'ppt/slides/_rels/slide1.xml.rels': f'<Relationships xmlns="{rel_ns}"><Relationship Id="image" Target="../media/image.png"/></Relationships>'.encode(),
        'ppt/media/image.png': b'synthetic image bytes; not a renderable PNG',
        'ppt/notesSlides/notes1.xml': f'<p:notes xmlns:p="{p}" xmlns:a="{a}"><a:t>notes-sentinel</a:t></p:notes>'.encode(),
        'ppt/charts/chart1.xml': b'untargeted chart sentinel'
    }


class BehaviorChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='presentation-craft-check-', dir=Path.cwd())
        self.work = Path(self.temp.name)
        self.deck = self.work / 'fixture.pptx'
        self.parts = package_parts()
        self.write_package(self.deck)
        self.plan = {'slides': [{'page': 1, 'steps': [[2, 3], [4]], 'effect': 'fade', 'duration_ms': 300}]}

    def tearDown(self):
        self.temp.cleanup()

    def write_package(self, target, parts=None):
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_STORED) as package:
            for name, data in (parts or self.parts).items():
                package.writestr(name, data)

    def evidence(self, deck=None):
        deck = deck or self.deck
        report = audit(deck, expected_slides=2)
        self.assertTrue(report['structural_pass'], report['findings'])
        digest = sha256(deck)
        render = {'deck_sha256': digest, 'pdf': {'file': 'export.pdf'}, 'pages': [{'page': i, 'file': f'slide-{i}.png'} for i in (1, 2)]}
        for item in [render['pdf']] + render['pages']:
            path = self.work / item['file']
            path.write_bytes(b'synthetic artifact bytes for continuity tests only')
            item['sha256'] = sha256(path)
        review = {'deck_sha256': digest, 'content_review': {'status': 'pass', 'summary': 'Synthetic test record; no real content reviewed'}, 'pages': [{'page': i, 'status': 'pass', 'summary': 'Synthetic test record; no slide viewed'} for i in (1, 2)]}
        paths = [self.work / (name + '.json') for name in ('audit', 'render', 'review')]
        return deck, paths, [report, render, review]

    def finish(self, evidence):
        deck, paths, records = evidence
        for path, record in zip(paths, records):
            path.write_text(json.dumps(record), encoding='utf-8')
        return finalize(deck, *paths)

    def test_reveal_uses_presentation_order_and_preserves_other_bytes(self):
        original_hash = sha256(self.deck)
        output = self.work / 'moving.pptx'
        animate(self.deck, output, self.plan)
        self.assertEqual(sha256(self.deck), original_hash)
        with zipfile.ZipFile(output) as package:
            changed = [name for name, data in self.parts.items() if package.read(name) != data]
            self.assertEqual(changed, ['ppt/slides/slide2.xml'])
            xml = package.read(changed[0])
            root = ET.fromstring(xml)
            self.assertEqual(xml[:xml.index(b'<p:timing')], self.parts[changed[0]][:self.parts[changed[0]].index(b'<p:extLst>')])
            self.assertTrue(xml.endswith(self.parts[changed[0]][self.parts[changed[0]].index(b'<p:extLst>'):]))
            self.assertLess(list(root).index(root.find('p:timing', NS)), list(root).index(root.find('p:extLst', NS)))
        result = audit(output)
        self.assertTrue(result['structural_pass'])
        self.assertEqual([p['animation']['click_effects'] for p in result['pages']], [2, 0])
        self.assertEqual(result['pages'][0]['animation']['entrance_effects'], 3)
        self.assertEqual([p['part'] for p in result['pages']], ['ppt/slides/slide2.xml', 'ppt/slides/slide1.xml'])
        self.assertEqual([o['id'] for o in inventory(output)['slides'][0]['objects']], [2, 3, 4])

    def test_bad_plans_never_create_output(self):
        variants = [None, {'slides': []}, {'slides': [{'page': True, 'steps': [[2]]}]}, {'slides': [{'page': 3, 'steps': [[2]]}]}, {'slides': [{'page': 1, 'steps': [[999]]}]}, {'slides': [{'page': 1, 'steps': [[2], [2]]}]}, {'slides': [{'page': 1, 'steps': [[True]]}]}, {'slides': [{'page': 1, 'steps': [[2]], 'effect': 'fly'}]}, {'slides': [{'page': 1, 'steps': [[2]], 'duration_ms': 0}]}]
        for i, plan in enumerate(variants):
            with self.subTest(plan=plan):
                output = self.work / f'invalid-{i}.pptx'
                with self.assertRaises(ValueError):
                    animate(self.deck, output, plan)
                self.assertFalse(output.exists())

    def test_existing_file_or_timing_is_preserved(self):
        existing = self.work / 'existing.pptx'
        existing.write_bytes(b'preserve user file')
        for output in (existing, self.deck):
            with self.assertRaises(ValueError):
                animate(self.deck, output, self.plan)
        self.assertEqual(existing.read_bytes(), b'preserve user file')
        moving = self.work / 'moving.pptx'
        animate(self.deck, moving, self.plan)
        with self.assertRaises(ValueError):
            animate(moving, self.work / 'again.pptx', self.plan)
        self.assertFalse((self.work / 'again.pptx').exists())

    def test_duplicate_shape_ids_are_rejected(self):
        parts = dict(self.parts)
        parts['ppt/slides/slide2.xml'] = parts['ppt/slides/slide2.xml'].replace(b'id="4"', b'id="2"')
        self.write_package(self.deck, parts)
        with self.assertRaisesRegex(ValueError, 'duplicate object IDs'):
            animate(self.deck, self.work / 'moving.pptx', self.plan)
        self.assertFalse((self.work / 'moving.pptx').exists())

    def test_duplicate_zip_parts_are_rejected(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.deck, 'a') as package:
                package.writestr('ppt/media/image.png', b'duplicate')
        self.assertFalse(audit(self.deck)['structural_pass'])
        with self.assertRaisesRegex(ValueError, 'duplicate ZIP'):
            animate(self.deck, self.work / 'moving.pptx', self.plan)
        self.assertFalse((self.work / 'moving.pptx').exists())

    def test_crc_damage_in_untargeted_part_is_rejected_before_writing(self):
        raw = bytearray(self.deck.read_bytes())
        with zipfile.ZipFile(self.deck) as package:
            info = package.getinfo('ppt/notesSlides/notes1.xml')
            name_size, extra_size = struct.unpack_from('<HH', raw, info.header_offset + 26)
            payload = info.header_offset + 30 + name_size + extra_size
            raw[payload + 5] ^= 1
        self.deck.write_bytes(raw)
        self.assertFalse(audit(self.deck)['structural_pass'])
        with self.assertRaisesRegex(ValueError, 'corrupt ZIP'):
            animate(self.deck, self.work / 'moving.pptx', self.plan)
        self.assertFalse((self.work / 'moving.pptx').exists())

    def test_evidence_continuity_accepts_current_and_rejects_changed_input(self):
        evidence = self.evidence()
        self.assertTrue(self.finish(evidence)['complete'])
        self.deck.write_bytes(self.deck.read_bytes() + b'changed after review')
        self.assertFalse(self.finish(evidence)['complete'])

    def test_legacy_or_null_animation_metadata_cannot_skip_playback_gate(self):
        for value in ('missing', None):
            evidence = self.evidence()
            if value == 'missing':
                del evidence[2][0]['pages'][0]['animation']
            else:
                evidence[2][0]['pages'][0]['animation'] = value
            result = self.finish(evidence)
            self.assertFalse(result['complete'])
            self.assertTrue(any('animation metadata' in f for f in result['failures']))

    def test_boolean_page_missing_duplicate_and_failed_reviews_are_rejected(self):
        original = self.evidence()
        for mode in ('boolean', 'missing', 'duplicate', 'failed'):
            evidence = copy.deepcopy(original)
            pages = evidence[2][2]['pages']
            if mode == 'boolean':
                pages[0]['page'] = True
            elif mode == 'missing':
                pages.pop()
            elif mode == 'duplicate':
                pages.append(copy.deepcopy(pages[0]))
            else:
                pages[0]['status'] = 'needs_fix'
            self.assertFalse(self.finish(evidence)['complete'], mode)

    def test_malformed_records_fail_with_clear_errors(self):
        for record, key, value in ((0, None, []), (0, 'findings', [None]), (1, 'pages', {}), (2, 'pages', [None]), (2, 'content_review', None)):
            evidence = self.evidence()
            if key is None:
                evidence[2][record] = value
            else:
                evidence[2][record][key] = value
            with self.assertRaisesRegex(ValueError, 'must be'):
                self.finish(evidence)

    def test_changed_missing_or_escaping_render_artifact_is_rejected(self):
        for mode in ('changed', 'missing', 'escape'):
            evidence = self.evidence()
            if mode == 'changed':
                (self.work / 'slide-1.png').write_bytes(b'changed')
            elif mode == 'missing':
                (self.work / 'slide-1.png').unlink()
            else:
                evidence[2][1]['pages'][0]['file'] = '../slide-1.png'
            self.assertFalse(self.finish(evidence)['complete'], mode)

    def test_animation_needs_slideshow_record_with_integer_page_coverage(self):
        moving = self.work / 'moving.pptx'
        animate(self.deck, moving, self.plan)
        evidence = self.evidence(moving)
        self.assertFalse(self.finish(evidence)['complete'])
        playback = {'status': 'pass', 'method': 'player_import', 'player': 'synthetic fixture', 'pages': [1], 'summary': 'Synthetic coverage test only; no real slideshow played'}
        evidence[2][2]['animation_review'] = playback
        self.assertFalse(self.finish(evidence)['complete'])
        playback['method'] = 'slideshow'
        playback['pages'] = [True]
        self.assertFalse(self.finish(evidence)['complete'])
        playback['pages'] = [1]
        self.assertTrue(self.finish(evidence)['complete'])

    def test_renderer_refuses_nonempty_directory_without_touching_it(self):
        output = self.work / 'render'
        output.mkdir()
        marker = output / 'user.txt'
        marker.write_text('preserve me', encoding='utf-8')
        result = subprocess.run([sys.executable, str(SCRIPTS / 'render_pptx.py'), str(self.deck), '--out-dir', str(output)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not empty', result.stderr)
        self.assertEqual(marker.read_text(encoding='utf-8'), 'preserve me')


if __name__ == '__main__':
    unittest.main(verbosity=2)
