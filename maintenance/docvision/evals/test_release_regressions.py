"""Offline release regressions for source renders and setup command plans."""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'docvision' / 'scripts'))

from dv import read, refine, setup_cmd, util  # noqa: E402
from dv.base import Options, RawBlock, RawDoc, RawPage  # noqa: E402
from dv.output import write_document  # noqa: E402


class RenderReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.png'
        self.image(self.source, 'red')
        self.docdir = self.document()
        isolated_config = patch.dict(os.environ, {'DOCVISION_CONFIG': str(self.root / 'config.json')})
        isolated_config.start()
        self.addCleanup(isolated_config.stop)

    @staticmethod
    def image(path, color):
        Image.new('RGB', (20, 10), color).save(path, format='PNG', compress_level=0)

    def document(self, *, force=False):
        return write_document(
            RawDoc(markdown='Recognized body.', provider='mineru-local', pages=[RawPage(
                page=1, markdown='Recognized body.', blocks=[RawBlock(
                    text='Recognized body.', markdown='Recognized body.', bbox=[0, 0, 1, 1])])]),
            str(self.source), Options(force=force), out_root=self.root / 'out',
            info={'pages': 1, 'sha256': util.sha256_file(self.source)})

    def assert_color(self, path, color):
        with Image.open(path) as image:
            self.assertEqual(image.convert('RGB').getpixel((0, 0)), color)

    def test_force_reconversion_refines_current_source_image(self):
        read.render_page(self.docdir, 1, dpi=300)
        self.image(self.source, 'blue')
        self.assertEqual(self.document(force=True), self.docdir)
        meta, _ = read.load(self.docdir)
        self.assertEqual(meta['source']['sha256'], util.sha256_file(self.source))

        # Packet refinement exercises the actual render consumer without inference.
        with patch.object(refine, 'run_provider', side_effect=AssertionError('no inference')):
            result = refine.run(self.docdir, page=1, provider='packet', dpi=300)
        self.assert_color(result['image_path'], (0, 0, 255))

    def test_read_image_detects_replacement_with_same_size_and_mtime(self):
        previous = Path(read.read(self.docdir, page=1, fmt='image'))
        before = self.source.stat()
        replacement = self.root / 'replacement.png'
        self.image(replacement, 'blue')
        self.assertEqual(replacement.stat().st_size, before.st_size)
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(self.source)
        self.assertEqual(self.source.stat().st_mtime_ns, before.st_mtime_ns)

        current = Path(read.read(self.docdir, page=1, fmt='image'))
        self.assert_color(current, (0, 0, 255))
        self.assert_color(previous, (255, 0, 0))

    def test_unchanged_pdf_reuses_render_and_keeps_dpi_entries(self):
        self.source = self.root / 'source.pdf'
        self.source.write_bytes(b'offline PDF fixture')
        self.docdir = self.document()
        with patch.object(util, 'render_pdf_page', side_effect=lambda source, index, dpi: str(dpi).encode()) as render:
            low = read.render_page(self.docdir, 1, dpi=150)
            high = read.render_page(self.docdir, 1, dpi=300)
            again = read.render_page(self.docdir, 1, dpi=300)
        self.assertEqual(low.read_bytes(), b'150')
        self.assertEqual(high.read_bytes(), b'300')
        self.assertEqual(again, high)
        self.assertEqual(render.call_args_list, [call(self.source, 0, dpi=150), call(self.source, 0, dpi=300)])

    def test_pdf_source_change_invalidates_render_with_stale_metadata(self):
        self.source = self.root / 'source.pdf'
        self.source.write_bytes(b'old PDF fixture')
        self.docdir = self.document()
        with patch.object(util, 'render_pdf_page', side_effect=lambda source, index, dpi: source.read_bytes()):
            previous = read.render_page(self.docdir, 1)
            self.source.write_bytes(b'new PDF fixture')
            current = read.render_page(self.docdir, 1)
        self.assertEqual(current.read_bytes(), b'new PDF fixture')
        self.assertEqual(previous.read_bytes(), b'old PDF fixture')


class SetupReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_install_plan_keeps_extra_package_options_for_both_managers(self):
        for manager in ('uv', 'conda'):
            with self.subTest(manager=manager), \
                 patch.object(setup_cmd, '_uv', return_value='uv'), \
                 patch.object(setup_cmd, '_conda', return_value='conda'), \
                 patch.object(setup_cmd, '_prefix_for', return_value=self.root / 'conda-env'), \
                 patch.object(util, 'app_dir', return_value=self.root), \
                 patch.object(util, 'run', side_effect=AssertionError('dry run must not install')):
                _, commands = setup_cmd._install_env(
                    'docvision-test', ['pillow'], manager=manager, dry_run=True,
                    extra_args=['--extra-index-url', 'https://pypi.org/simple', '--no-deps'])
                self.assertEqual(commands[-1][-4:], [
                    'pillow', '--extra-index-url', 'https://pypi.org/simple', '--no-deps'])
                if manager == 'conda':
                    self.assertNotIn('--index-strategy', commands[-1])

    def test_uv_multiple_indexes_match_pip_candidate_selection(self):
        for extra_args in (['--extra-index-url', 'https://fallback.example/simple'],
                           ['--extra-index-url=https://fallback.example/simple']):
            with self.subTest(extra_args=extra_args), \
                 patch.object(setup_cmd, '_uv', return_value='uv'), \
                 patch.object(util, 'app_dir', return_value=self.root), \
                 patch.object(util, 'run', side_effect=AssertionError('dry run must not install')):
                prefix, commands = setup_cmd._install_env(
                    'docvision-test', ['vendor-package==2.0'], manager='uv', dry_run=True,
                    index='https://vendor.example/simple', extra_args=extra_args)
                self.assertEqual(commands[-1], [
                    'uv', 'pip', 'install', '--python', str(util.env_python(prefix)),
                    '--index-url', 'https://vendor.example/simple',
                    '--index-strategy', 'unsafe-best-match', 'vendor-package==2.0', *extra_args])

    def test_uv_keeps_explicit_multi_index_strategy(self):
        for strategy in (['--index-strategy', 'unsafe-first-match'],
                         ['--index-strategy=first-index']):
            with self.subTest(strategy=strategy), \
                 patch.object(setup_cmd, '_uv', return_value='uv'), \
                 patch.object(util, 'app_dir', return_value=self.root), \
                 patch.object(util, 'run', side_effect=AssertionError('dry run must not install')):
                extra_args = ['--extra-index-url', 'https://fallback.example/simple', *strategy]
                prefix, commands = setup_cmd._install_env(
                    'docvision-test', ['vendor-package==2.0'], manager='uv', dry_run=True,
                    index='https://vendor.example/simple', extra_args=extra_args)
                self.assertEqual(commands[-1], [
                    'uv', 'pip', 'install', '--python', str(util.env_python(prefix)),
                    '--index-url', 'https://vendor.example/simple', 'vendor-package==2.0', *extra_args])

    def test_paddle_gpu_uv_plan_keeps_pypi_fallback(self):
        output = io.StringIO()
        with patch.object(setup_cmd, '_uv', return_value='uv'), \
             patch.object(util, 'app_dir', return_value=self.root), \
             patch.object(util, 'gpu_summary', return_value={'available': True}), \
             patch.object(util, 'run', side_effect=AssertionError('dry run must not install')), \
             patch.object(setup_cmd.config, 'save', side_effect=AssertionError('dry run must not save')), \
             contextlib.redirect_stdout(output):
            self.assertEqual(setup_cmd.run('paddle', manager='uv', device='gpu', dry_run=True), 0)
        install = next(line for line in output.getvalue().splitlines() if 'uv pip install' in line)
        self.assertIn('--index-url https://www.paddlepaddle.org.cn/packages/stable/cu126/', install)
        self.assertIn('paddlepaddle-gpu==3.2.1', install)
        self.assertIn('paddleocr[doc-parser]>=3.7,<3.8', install)
        self.assertIn('--extra-index-url https://pypi.org/simple', install)
        self.assertIn('--index-strategy unsafe-best-match', install)

    def test_uv_core_and_mineru_keep_normal_install_plans(self):
        for profile, packages in (
                ('core', ['pypdfium2>=4,<6', 'pillow>=10,<13', 'pypdf>=5,<7']),
                ('mineru', ['mineru>=4.0,<5'])):
            with self.subTest(profile=profile), \
                 patch.object(setup_cmd, '_uv', return_value='uv'), \
                 patch.object(util, 'app_dir', return_value=self.root), \
                 patch.object(util, 'run', side_effect=AssertionError('dry run must not install')):
                prefix, commands = setup_cmd._install_env(
                    f'docvision-{profile}', packages, manager='uv', dry_run=True,
                    index='https://packages.example/simple')
                self.assertEqual(commands[-1], [
                    'uv', 'pip', 'install', '--python', str(util.env_python(prefix)),
                    '--index-url', 'https://packages.example/simple', *packages])


if __name__ == '__main__':
    unittest.main(verbosity=2)
