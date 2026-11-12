"""Real-paper findings from 2026-11-12: hidden text in the fast tier, GBK pipes, engine crash causes."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
ENTRY = ROOT / 'docvision' / 'scripts' / 'docvision.py'
sys.path.insert(0, str(ROOT / 'docvision' / 'scripts'))

from dv import config, read, util  # noqa: E402
from dv.base import Options, RawBlock, RawDoc, RawPage  # noqa: E402
from dv.output import write_document  # noqa: E402
from dv.providers import text_local  # noqa: E402


def figure_pdf(path: Path, *, clipped: bool) -> None:
    """One page whose figure (a form XObject) holds a line of text; `clipped` crops that text away,
    as LaTeX does when a figure is a trimmed page of another PDF."""
    hidden = ' '.join(['draftword'] * 12)
    clip = '300 300 1 1 re W n ' if clipped else ''
    page = f'BT /F1 14 Tf 72 720 Td (Visible page text) Tj ET q {clip}/Fm Do Q'.encode()
    form = f'BT /F1 14 Tf 72 400 Td ({hidden}) Tj ET'.encode()
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
        b'/Resources << /Font << /F1 4 0 R >> /XObject << /Fm 6 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length %d >>\nstream\n' % len(page) + page + b'\nendstream',
        b'<< /Type /XObject /Subtype /Form /BBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> '
        b'/Length %d >>\nstream\n' % len(form) + form + b'\nendstream',
    ]
    out, offsets = bytearray(b'%PDF-1.4\n'), []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b'%d 0 obj\n' % number + body + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objects) + 1)
    out += b''.join(b'%010d 00000 n \n' % offset for offset in offsets)
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objects) + 1, xref)
    path.write_bytes(bytes(out))


class TextLayerVisibilityTests(unittest.TestCase):
    def setUp(self):
        try:
            import pypdfium2  # noqa: F401
            import pypdf  # noqa: F401
        except ImportError:
            self.skipTest('core PDF dependencies are not installed in this interpreter')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_text_cropped_out_of_a_figure_is_reported(self):
        pdf = self.root / 'paper.pdf'
        figure_pdf(pdf, clipped=True)
        [(page, invisible, total)] = text_local.invisible_text_pages(str(pdf), [0])
        self.assertEqual(page, 1)
        self.assertGreaterEqual(invisible, 100)
        self.assertGreater(total, invisible)

    def test_visible_figure_text_is_not_reported(self):
        pdf = self.root / 'paper.pdf'
        figure_pdf(pdf, clipped=False)
        self.assertEqual(text_local.invisible_text_pages(str(pdf), [0]), [])

    def test_convert_warns_and_read_repeats_the_warning_on_that_page(self):
        pdf = self.root / 'paper.pdf'
        figure_pdf(pdf, clipped=True)
        raw, _ = text_local.convert(str(pdf), Options(tier='fast'))
        self.assertTrue(any('not visible on the rendered page' in w for w in raw.warnings))
        docdir = write_document(raw, str(pdf), Options(tier='fast'), out_root=self.root / 'out',
                                info={'pages': 1, 'sha256': util.sha256_file(pdf)})
        self.assertIn('Text-layer warning', read.read(docdir, page=1))
        self.assertIn('Pages [1]', read.read(docdir))

    def test_gbk_pipe_prints_symbols_from_papers(self):
        body = 'phase φ, ϕ and the ﬁ ligature'
        source = self.root / 'paper.png'
        source.write_bytes(b'not read by this test')
        docdir = write_document(RawDoc(markdown=body, provider='text-local', pages=[RawPage(
            page=1, markdown=body, blocks=[RawBlock(type='text', text=body, markdown=body)])]),
            str(source), Options(), out_root=self.root / 'out',
            info={'pages': 1, 'sha256': util.sha256_file(source)})
        env = dict(os.environ, PYTHONIOENCODING='gbk', DOCVISION_CONFIG=str(self.root / 'config.json'))
        proc = subprocess.run([sys.executable, str(ENTRY), 'read', str(docdir), '--page', '1'],
                              capture_output=True, env=env, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode('utf-8', 'replace'))
        self.assertIn('ϕ and the ﬁ ligature', proc.stdout.decode('utf-8'))


class EngineCrashCauseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.exe = Path(self.temp.name) / 'mineru-kit.exe'
        self.exe.touch()
        crash = ('Traceback (most recent call last):\n  File "mineru/__init__.py", line 11\n'
                 "ModuleNotFoundError: No module named 'pydantic'\n")
        mock = patch.object(util, 'run', return_value=subprocess.CompletedProcess([], 1, '', crash))
        mock.start()
        self.addCleanup(mock.stop)

    def test_crash_reports_the_last_traceback_line_not_the_first(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('PYTHONNOUSERSITE', None)
            version, detail = config._exe_version(str(self.exe), args=['--help'])
        self.assertIsNone(version)
        self.assertEqual(detail, "exit 1: ModuleNotFoundError: No module named 'pydantic'")

    def test_missing_module_under_nousersite_points_at_user_site_packages(self):
        with patch.dict(os.environ, {'PYTHONNOUSERSITE': '1'}):
            _, detail = config._exe_version(str(self.exe), args=['--help'])
        self.assertIn('PYTHONNOUSERSITE is set', detail)


if __name__ == '__main__':
    unittest.main(verbosity=2)
