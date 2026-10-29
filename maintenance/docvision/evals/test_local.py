"""Local runtime regressions; subprocess/model boundaries are stubbed only."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'docvision' / 'scripts'))
from dv import config, detect, doctor, setup_cmd, util
from dv import cache
from dv.base import Options, RawBlock, RawPage
from dv.providers import mineru_local, paddle_local
from dv.output import write_document


class LocalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='docvision-local-test-')
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name)

    def test_mineru_nested_algorithm_spans_preserve_text_math_and_order(self):
        from dv import read
        from dv.providers.common import raw_from_mineru_zip

        # Shape captured in a real MinerU 4 docvortex code/algorithm block:
        # code.content -> algorithm_body.content -> text/equation_inline spans.
        middle = {'schema': 'docvortex.middle', 'pages': [{'page_idx': 0, 'blocks': [{
            'type': 'code', 'sub_type': 'algorithm', 'bbox': [0.1, 0.1, 0.9, 0.4],
            'content': [{'type': 'algorithm_body', 'content': [
                {'type': 'text', 'content': 'Algorithm 1\nrepeat\n    '},
                {'type': 'equation_inline', 'content': r'\theta, \phi'},
                {'type': 'text', 'content': ' <- update\nreturn '},
                {'type': 'equation_inline', 'content': r'\theta, \phi'},
            ]}],
        }]}]}
        expected = 'Algorithm 1\nrepeat\n    $\\theta, \\phi$ <- update\nreturn $\\theta, \\phi$'
        upstream_md = '<div class="docvortex-algorithm">\n' + expected + '\n</div>'
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('middle_json.json', json.dumps(middle))
            archive.writestr('markdown.md', upstream_md)
        doc = raw_from_mineru_zip(buffer.getvalue(), provider='mineru-local')
        self.assertEqual(doc.markdown, upstream_md)
        self.assertEqual(doc.pages[0].blocks[0].text, expected)
        self.assertEqual(doc.pages[0].blocks[0].markdown, '```\n' + expected + '\n```')
        source = self.tmp / 'fixture.pdf'
        source.write_bytes(b'fixture source; no inference or rendering')
        out = write_document(doc, str(source), Options(), out_root=self.tmp / 'out', info={'pages': 1})
        page = json.loads(read.read(out, page=1, as_json=True))['pages'][0]
        self.assertEqual(page['blocks'][0]['text'], expected)
        self.assertIn('```\n' + expected + '\n```', page['markdown'])
        self.assertNotIn("{'type':", page['markdown'])

    def test_mineru_table_caption_is_kept_before_html_without_correcting_ocr(self):
        from dv import read
        from dv.providers.common import raw_from_mineru_zip

        caption = 'Table 2: Scores on newestest2014.'
        html = '<table><tr><td>Model</td><td>28.4</td></tr></table>'
        middle = {'schema': 'docvortex.middle', 'pages': [{'page_idx': 0, 'blocks': [{
            'type': 'table', 'content': [
                {'type': 'table_caption', 'content': [{'type': 'text', 'content': caption}]},
                {'type': 'table_body', 'content': html, 'image_path': 'images/table.png'},
            ],
        }]}]}
        expected = caption + '\n\n' + html
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('middle_json.json', json.dumps(middle))
            archive.writestr('markdown.md', expected)
            archive.writestr('images/table.png', b'fixture image; no rendering')
        doc = raw_from_mineru_zip(buffer.getvalue(), provider='mineru-local')
        self.assertEqual(doc.pages[0].blocks[0].text, expected)
        self.assertEqual(doc.pages[0].blocks[0].asset, 'images/table.png')
        source = self.tmp / 'fixture.pdf'
        source.write_bytes(b'fixture source; no inference or rendering')
        out = write_document(doc, str(source), Options(), out_root=self.tmp / 'out', info={'pages': 1})
        page = json.loads(read.read(out, page=1, as_json=True))['pages'][0]
        self.assertEqual(page['markdown'], expected)
        self.assertEqual(page['blocks'][0]['text'], expected)
        self.assertEqual(page['markdown'].count(caption), 1)

    def test_auto_short_circuits_when_mineru_is_installed(self):
        engine = config.Engine('mineru', available=True)
        with patch.object(config, 'discover_mineru', return_value=engine), \
             patch.object(config, 'discover_paddle', side_effect=AssertionError('Paddle must not start')):
            self.assertEqual(detect.choose_provider('a.png', Options()), 'mineru-local')

    def test_mineru_discovery_is_reused_but_refresh_bypasses_it(self):
        exe = self.tmp / 'mineru-kit.exe'
        exe.touch()
        cfg = {'engines': {'mineru': {'exe': str(exe)}}}
        calls = []
        def version(*args, **kwargs):
            calls.append(args)
            return '4.0.12', 'ok'
        with patch.object(config, '_exe_version', side_effect=version):
            self.assertTrue(config.discover_mineru(cfg).available)
            self.assertTrue(config.discover_mineru(cfg).available)
            self.assertEqual(len(calls), 1)
            config.discover_mineru(cfg, refresh=True)
            self.assertEqual(len(calls), 2)

    def test_paddle_metadata_upgrade_invalidates_signature_without_importing_runtime(self):
        python = self.tmp / 'python.exe'
        exe = self.tmp / 'Scripts' / 'paddleocr.exe'
        python.touch(); exe.parent.mkdir(); exe.touch()
        packages = self.tmp / 'Lib' / 'site-packages'
        for name, version in [('paddleocr', '3.7.0'), ('paddlex', '3.7.2'), ('paddlepaddle_gpu', '3.2.1')]:
            folder = packages / f'{name}-{version}.dist-info'
            folder.mkdir(parents=True)
            (folder / 'METADATA').write_text(f'Name: {name}\nVersion: {version}\n', encoding='utf-8')
        cfg = {'engines': {'paddleocr': {'python': str(python), 'exe': str(exe)}}}
        info = {'sha256': 'source', 'pages': 1}
        with patch.object(util, 'run', side_effect=AssertionError('normal discovery must not import Paddle')):
            first = config.discover_paddle(cfg)
            self.assertIn('PaddleOCR 3.7.0', first.version or '')
            self.assertIn('PaddleX 3.7.2', first.version)
            before = cache.request_signature(info, Options(), provider='paddleocr-local',
                                             context={'engine_version': first.version})
            metadata = packages / 'paddleocr-3.7.0.dist-info' / 'METADATA'
            metadata.write_text('Name: paddleocr\nVersion: 3.7.1\n', encoding='utf-8')
            modified = metadata.stat().st_mtime_ns + 1_000_000
            os.utime(metadata, ns=(modified, modified))
            upgraded = config.discover_paddle(cfg)
            after = cache.request_signature(info, Options(), provider='paddleocr-local',
                                            context={'engine_version': upgraded.version})
        self.assertIn('PaddleOCR 3.7.1', upgraded.version)
        self.assertNotEqual(before, after)
        self.assertNotEqual(first.extra.get('cache_fingerprint'), upgraded.extra.get('cache_fingerprint'))

    def test_paddle_missing_metadata_does_not_invent_a_cacheable_version(self):
        python = self.tmp / 'python.exe'
        exe = self.tmp / 'paddleocr.exe'
        python.touch(); exe.touch()
        with patch.object(util, 'run', side_effect=AssertionError('no runtime import')):
            result = config.discover_paddle({'engines': {'paddleocr': {'python': str(python), 'exe': str(exe)}}})
        self.assertIsNone(result.version)
        self.assertIsNone(result.extra.get('cache_fingerprint'))

    def test_economy_uses_basic_ocr_and_explicit_mode(self):
        engine = config.Engine('mineru', exe='mineru-kit')
        cmd = mineru_local._command(engine, 'a.png', self.tmp, Options(tier='economy', mode='ocr'),
                                    {'is_image': True, 'needs_ocr': True})
        self.assertEqual(cmd[cmd.index('--tier') + 1], 'basic')
        self.assertEqual(cmd[cmd.index('--ocr-mode') + 1], 'ocr')

    def test_formula_mode_forces_ocr_in_economy(self):
        engine = config.Engine('mineru', exe='mineru-kit')
        cmd = mineru_local._command(engine, 'a.pdf', self.tmp, Options(tier='economy', mode='formula'),
                                    {'is_pdf': True, 'needs_ocr': False})
        self.assertEqual(cmd[cmd.index('--ocr-mode') + 1], 'ocr')

    def test_explicit_ocr_promotes_flash_to_basic(self):
        engine = config.Engine('mineru', exe='mineru-kit')
        cmd = mineru_local._command(engine, 'a.pdf', self.tmp, Options(tier='fast', mode='ocr'),
                                    {'is_pdf': True, 'needs_ocr': False})
        self.assertEqual(cmd[cmd.index('--tier') + 1], 'basic')

    def test_text_only_image_request_has_actionable_error(self):
        engine = config.Engine('mineru', exe='mineru-kit')
        with self.assertRaisesRegex(Exception, 'text'):
            mineru_local._command(engine, 'a.png', self.tmp, Options(mode='text'), {'is_image': True})

    def test_explicit_mineru_device_is_not_silently_ignored(self):
        engine = config.Engine('mineru', exe='mineru-kit')
        with self.assertRaisesRegex(Exception, 'device'):
            mineru_local._command(engine, 'a.pdf', self.tmp, Options(device='cpu'), {'is_pdf': True})

    def test_paddle_upstream_imgs_are_exported_and_chart_text_survives(self):
        from PIL import Image
        source = self.tmp / 'source.png'
        Image.new('RGB', (100, 100), 'white').save(source)
        out = self.tmp / 'out'
        (out / 'imgs').mkdir(parents=True)
        image = out / 'imgs' / 'diagram.jpg'
        Image.new('RGB', (10, 10), 'red').save(image)
        (out / 'sample_res.json').write_text(json.dumps({
            'page_index': 0, 'width': 100, 'height': 100,
            'parsing_res_list': [{'block_label': 'chart', 'block_content': '<table><tr><td>42</td></tr></table>',
                                  'block_bbox': [0, 0, 100, 100]}]}), encoding='utf-8')
        (out / 'sample.md').write_text('![diagram](imgs/diagram.jpg)\n\nRecognized chart: 42', encoding='utf-8')
        engine = config.Engine('paddleocr', exe='paddleocr', available=True, extra={})
        with patch.object(config, 'discover_paddle', return_value=engine), \
             patch.object(paddle_local.util, 'staging_dir', return_value=self.tmp), patch.object(paddle_local.util, 'release_staging'), \
             patch.object(util, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')):
            doc, _ = paddle_local.convert(str(source), Options())
        self.assertIn('imgs/diagram.jpg', doc.assets)
        self.assertIn('42', doc.pages[0].blocks[0].markdown)
        self.assertIn('<table><tr><td>42</td></tr></table>', doc.markdown)
        self.assertTrue(doc.pages[0].blocks[0].asset)
        output = write_document(doc, str(source), Options(), out_root=self.tmp / 'final',
                                info={'pages': 1})
        content = util.read_json(output / 'content.json')
        self.assertNotIn('](imgs/', content['pages'][0]['markdown'])
        self.assertIn('assets/', content['pages'][0]['markdown'])
        for asset in content['assets']:
            self.assertTrue((output / 'assets' / asset).is_file())

    def test_install_commands_ignore_user_site(self):
        candidate = self.tmp / 'candidate'
        seen = []
        def run(cmd, **kwargs):
            seen.append((cmd, kwargs))
            if 'create' in cmd:
                py = util.env_python(candidate)
                py.parent.mkdir(parents=True, exist_ok=True)
                py.touch()
            return subprocess.CompletedProcess(cmd, 0, '', '')
        with patch.object(setup_cmd, '_conda', return_value='conda'), \
             patch.object(util, 'run', side_effect=run):
            setup_cmd._install_env('docvision-test', ['pillow'], manager='conda', prefix=candidate)
        self.assertTrue(all(k.get('env', {}).get('PYTHONNOUSERSITE') == '1' for _, k in seen))
        self.assertTrue(all('-s' in cmd for cmd, _ in seen if 'create' not in cmd))

    def test_core_setup_saves_python_for_entrypoint(self):
        cfg_path = self.tmp / 'config.json'
        with patch.dict(os.environ, {'DOCVISION_CONFIG': str(cfg_path)}), \
             patch.object(setup_cmd, '_conda', return_value='conda'), \
             patch.object(setup_cmd, '_validate_candidate', return_value=[]), \
             patch.object(setup_cmd, '_install_env', return_value=(self.tmp, [])):
            self.assertEqual(setup_cmd.run('core', yes=True), 0)
            self.assertEqual(config.load().get('core', {}).get('python'), str(util.env_python(self.tmp)))

    def test_core_dispatch_selects_configured_python_when_current_dependencies_missing(self):
        cfg_path = self.tmp / 'config.json'
        util.write_json(cfg_path, {'core': {'python': sys.executable}})
        with patch.dict(os.environ, {'DOCVISION_CONFIG': str(cfg_path)}), \
             patch.object(util, 'missing_core_modules', return_value=['PIL']):
            command = util.core_reexec_command(['refine', 'document', '--page', '1'])
        self.assertEqual(command[:2], [sys.executable, '-s'])
        self.assertEqual(command[-4:], ['refine', 'document', '--page', '1'])

    def test_paddle_doctor_reports_extras_and_unknown_model_readiness(self):
        engine = config.Engine('paddleocr', available=True, extra={})
        models = doctor._models(engine)
        self.assertIs(models.get('ready'), None)
        self.assertEqual(models.get('validation'), 'not run')
        py = self.tmp / 'python.exe'
        exe = self.tmp / 'paddleocr.exe'
        py.touch(); exe.touch()
        payload = {'version': '3.7.0', 'gpu': None, 'dependencies': {'ok': False, 'missing': ['beautifulsoup4']}}
        with patch.object(util, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(payload), '')):
            report = config.discover_paddle({'engines': {'paddleocr': {'python': str(py), 'exe': str(exe)}}},
                                             refresh=True, detailed=True)
        self.assertFalse(report.available)
        self.assertIn('beautifulsoup4', report.detail)

    def test_single_frame_image_has_known_page_count(self):
        from PIL import Image
        source = self.tmp / 'image.png'
        Image.new('RGB', (2, 2)).save(source)
        self.assertEqual(detect.inspect_input(str(source), Options())['pages'], 1)

    def test_paddle_without_markdown_uses_cropped_image_in_page_body(self):
        from PIL import Image
        source = self.tmp / 'source.png'
        Image.new('RGB', (20, 20)).save(source)
        out = self.tmp / 'out'
        out.mkdir()
        (out / 'sample_res.json').write_text(json.dumps({
            'page_index': 0, 'width': 20, 'height': 20,
            'parsing_res_list': [{'block_label': 'image', 'block_content': '',
                                  'block_bbox': [0, 0, 20, 20]}]}), encoding='utf-8')
        engine = config.Engine('paddleocr', exe='paddleocr', available=True)
        with patch.object(config, 'discover_paddle', return_value=engine), \
             patch.object(paddle_local.util, 'staging_dir', return_value=self.tmp), patch.object(paddle_local.util, 'release_staging'), \
             patch.object(util, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')):
            doc, _ = paddle_local.convert(str(source), Options())
        self.assertNotIn('![image]()', doc.markdown)
        self.assertIn('page-0001-image-1.png', doc.markdown)

    def test_paddle_footnote_recognition_is_preserved_in_page_markdown(self):
        out = self.tmp / 'out'
        out.mkdir()
        (out / 'sample_res.json').write_text(json.dumps({
            'page_index': 0, 'width': 20, 'height': 20,
            'parsing_res_list': [{'block_label': 'footnote', 'block_content': 'Footnote $q \\cdot k$',
                                  'block_bbox': [0, 10, 20, 20]}]}), encoding='utf-8')
        (out / 'sample.md').write_text('Main body', encoding='utf-8')
        pages = paddle_local._read_pages(out, page_map=None, source=self.tmp / 'source.pdf')
        self.assertIn('Footnote $q \\cdot k$', pages[0].markdown)

    def test_paddle_does_not_export_full_page_debug_layout_images(self):
        (self.tmp / 'imgs').mkdir()
        (self.tmp / 'imgs' / 'figure.jpg').write_bytes(b'original-image')
        (self.tmp / 'paper_0_layout_det_res.png').write_bytes(b'debug-full-page')
        self.assertEqual(paddle_local._export_images(self.tmp), {'imgs/figure.jpg': b'original-image'})

    def test_doctor_does_not_call_unprobed_paddle_key_authenticated(self):
        result = doctor._remote_probe('paddle', 'test-not-a-real-key')
        self.assertIsNone(result['ok'])
        self.assertIn('not tested', result['detail'])

    def test_doctor_checks_configured_core_when_current_python_is_missing_modules(self):
        cfg_path = self.tmp / 'config.json'
        util.write_json(cfg_path, {'core': {'python': sys.executable}})
        engines = {name: config.Engine(name) for name in ('mineru', 'paddleocr', 'vlm')}
        payload = {name: {'ok': True, 'detail': 'installed'} for name in ('pypdfium2', 'PIL', 'pypdf')}
        with patch.dict(os.environ, {'DOCVISION_CONFIG': str(cfg_path)}), \
             patch.object(config, 'engine_status', return_value=engines), \
             patch.object(doctor, '_module', return_value={'ok': False, 'detail': 'not installed'}), \
             patch.object(util, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(payload), '')):
            report = doctor.collect()
        self.assertTrue(all(item['ok'] for item in report['core_python_modules'].values()))
        self.assertNotIn('For page rendering/cropping: docvision setup --profile core --yes', report['next_actions'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
