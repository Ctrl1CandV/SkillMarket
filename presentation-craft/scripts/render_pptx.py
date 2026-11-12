#!/usr/bin/env python3
"""Render the actual PPTX via LibreOffice or Windows PowerPoint, then rasterize its PDF."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from xml.etree import ElementTree as ET
import zipfile

from doctor import find_soffice, powerpoint_com_status

P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
# A line should not start with these; PowerPoint does it when CJK text is not tagged as East Asian.
CLOSING = set('，。、；：！？）」』》】〉,.;:!?)]}%')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(command, timeout):
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {result.stdout}\n{result.stderr}')
    return result


def powerpoint_processes():
    result = run(['tasklist', '/FI', 'IMAGENAME eq POWERPNT.EXE', '/FO', 'CSV', '/NH'], 15)
    return {int(row[1]) for row in csv.reader(result.stdout.splitlines())
            if len(row) > 1 and row[0].upper() == 'POWERPNT.EXE'}


def export_powerpoint(source, target):
    """Open only the requested deck, preserving any existing user PowerPoint session."""
    import pythoncom
    import win32com.client
    before = powerpoint_processes()
    application = presentation = None
    owns_process = False
    pythoncom.CoInitialize()
    try:
        application = win32com.client.DispatchEx('PowerPoint.Application')
        # PowerPoint is a multiuse COM server: DispatchEx may return an
        # existing process. Claim ownership only when none existed before.
        owns_process = not before and len(powerpoint_processes()) == 1 and application.Presentations.Count == 0
        presentation = application.Presentations.Open(str(source), -1, 0, 0)
        # PDF, screen quality, no frame, slides, include hidden slides, all slides.
        presentation.ExportAsFixedFormat(str(target), 2, 1, 0, 1, 1, -1, None, 1)
        return 'Microsoft PowerPoint ' + str(application.Version) + ' COM PDF export'
    except Exception as exc:
        raise RuntimeError('PowerPoint PDF export failed: ' + str(exc)) from exc
    finally:
        cleanup_errors = []
        if presentation is not None:
            try:
                presentation.Close()
            except Exception as exc:
                cleanup_errors.append('close owned presentation: ' + str(exc))
        if application is not None and owns_process:
            try:
                # DispatchEx can reuse a process. Never quit a pre-existing process,
                # or one in which somebody has since opened another presentation.
                if application.Presentations.Count == 0:
                    application.Quit()
            except Exception as exc:
                cleanup_errors.append('quit owned empty instance: ' + str(exc))
        presentation = application = None
        pythoncom.CoUninitialize()
        if cleanup_errors:
            raise RuntimeError('PowerPoint cleanup failed: ' + '; '.join(cleanup_errors))


def rasterize(pdf, out_dir, dpi, pdftoppm, timeout):
    if pdftoppm:
        run([pdftoppm, '-png', '-r', str(dpi), str(pdf), str(out_dir / 'slide')], timeout)
        files = list(out_dir.glob('slide-*.png'))
        return sorted(files, key=lambda p: int(re.search(r'-(\d+)$', p.stem).group(1)))
    module = 'pymupdf' if importlib.util.find_spec('pymupdf') else 'fitz'
    api = __import__(module)
    files = []
    with api.open(pdf) as document:
        for i, page in enumerate(document, 1):
            path = out_dir / f'slide-{i:03d}.png'
            page.get_pixmap(matrix=api.Matrix(dpi / 72, dpi / 72), alpha=False).save(path)
            files.append(path)
    return files


def source_segments(deck):
    """Paragraph texts per slide, in presentation order; a forced line break starts a new segment."""
    pages = []
    with zipfile.ZipFile(deck) as archive:
        root = ET.fromstring(archive.read('ppt/presentation.xml'))
        rels = ET.fromstring(archive.read('ppt/_rels/presentation.xml.rels'))
        targets = {rel.get('Id'): rel.get('Target') for rel in rels}
        for slide_id in root.findall(P + 'sldIdLst/' + P + 'sldId'):
            target = targets[slide_id.get(R + 'id')]
            part = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join('ppt', target))
            segments = []
            for paragraph in ET.fromstring(archive.read(part)).iter(A + 'p'):
                text = ''
                for node in paragraph.iter():
                    if node.tag == A + 't':
                        text += node.text or ''
                    elif node.tag == A + 'br':
                        segments.append(text)
                        text = ''
                segments.append(text)
            pages.append([s for s in segments if s.strip()])
    return pages


def pdf_lines(pdf):
    """Visual lines of the exported PDF as (text, bbox), in extraction order."""
    name = next((m for m in ('pymupdf', 'fitz') if importlib.util.find_spec(m)), None)
    if not name:
        raise ImportError('PyMuPDF is needed to read the exported PDF text layer')
    api = __import__(name)
    pages = []
    with api.open(pdf) as document:
        for page in document:
            pages.append([(''.join(span['text'] for span in line['spans']), line['bbox'])
                          for block in page.get_text('dict')['blocks'] for line in block.get('lines', [])])
    return pages


def squeeze(text):
    kept = [(i, c) for i, c in enumerate(text) if not c.isspace()]
    return ''.join(c for _, c in kept), [i for i, _ in kept]


def text_flags(segments_by_page, lines_by_page):
    """Line breaks in the real render that a reader notices but a glance at the page misses.

    Two consecutive PDF lines count as one wrapped paragraph only when the end of the
    upper line plus the lower line occur together in one source paragraph.
    """
    flags = []
    for page, (segments, lines) in enumerate(zip(segments_by_page, lines_by_page), 1):
        sources = [squeeze(s) for s in segments]
        for (upper, upper_box), (lower, lower_box) in zip(lines, lines[1:]):
            upper_flat, head = squeeze(upper)[0], squeeze(lower)[0]
            tail = upper_flat[-12:]
            if not tail or not head or lower_box[1] < upper_box[1] + 0.5 * (upper_box[3] - upper_box[1]):
                continue
            for flat, index in sources:
                at = flat.find(tail + head)
                if at < 0:
                    continue
                cut = at + len(tail)
                kinds = []
                if head[0] in CLOSING:
                    kinds.append('line_start_punct')
                left, right = flat[cut - 1], flat[cut]
                if left.isascii() and left.isalnum() and right.isascii() and right.isalnum() and index[cut] == index[cut - 1] + 1:
                    kinds.append('split_word')
                # One or two characters left under a much longer line; a narrow two-line label is fine.
                if len(head) <= 2 and len(upper_flat) >= 4 * len(head) and cut + len(head) == len(flat):
                    kinds.append('short_last_line')
                if kinds:
                    flags.append({'page': page, 'kinds': kinds, 'text': tail + ' | ' + head[:12]})
                break
    return flags


def montage(files, target):
    if not importlib.util.find_spec('PIL'):
        return None
    from PIL import Image, ImageDraw
    columns = min(3, len(files))
    tile_width, label_height = 480, 26
    with Image.open(files[0]) as first:
        tile_height = round(tile_width * first.height / first.width)
    rows = (len(files) + columns - 1) // columns
    canvas = Image.new('RGB', (columns * tile_width, rows * (tile_height + label_height)), '#E8ECF0')
    draw = ImageDraw.Draw(canvas)
    for i, path in enumerate(files):
        x = (i % columns) * tile_width
        y = (i // columns) * (tile_height + label_height)
        with Image.open(path) as source:
            tile = source.convert('RGB')
            tile.thumbnail((tile_width, tile_height))
            canvas.paste(tile, (x, y + label_height))
        draw.text((x + 10, y + 7), f'Slide {i + 1}', fill='#243040')
    canvas.save(target)
    return target.name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('deck', type=Path)
    parser.add_argument('--out-dir', type=Path, required=True, help='New or empty directory; never overwrites an existing render')
    parser.add_argument('--renderer', choices=('auto', 'libreoffice', 'powerpoint'), default='auto',
                        help='auto prefers LibreOffice, then registered Windows PowerPoint COM')
    parser.add_argument('--soffice')
    parser.add_argument('--pdftoppm')
    parser.add_argument('--dpi', type=int, default=144)
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    try:
        source = args.deck.resolve()
        if not source.is_file():
            raise ValueError('Input PPTX is missing or is not a file')
        out_dir = args.out_dir.resolve()
        if out_dir.exists() and any(out_dir.iterdir()):
            raise ValueError('Output directory is not empty; choose a new render directory')
        if args.dpi < 72 or args.dpi > 600:
            raise ValueError('DPI must be between 72 and 600')
        soffice = find_soffice(args.soffice)
        poppler = args.pdftoppm or shutil.which('pdftoppm')
        renderer = args.renderer
        if renderer == 'auto':
            renderer = 'libreoffice' if soffice else 'powerpoint'
        if renderer == 'libreoffice' and not soffice:
            raise ValueError('LibreOffice is unavailable; pass --soffice or choose another renderer')
        if renderer == 'powerpoint' and not powerpoint_com_status()['available']:
            raise ValueError('PowerPoint COM is unavailable; Windows, installed PowerPoint and pywin32 are required')
        if not poppler and not any(importlib.util.find_spec(m) for m in ('pymupdf', 'fitz')):
            raise ValueError('Install/use pdftoppm or PyMuPDF to rasterize the PDF')
        input_hash = sha256(source)
        out_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.presentation-render-', dir=out_dir.parent) as temporary:
            temp = Path(temporary)
            generated = temp / (source.stem + '.pdf')
            if renderer == 'libreoffice':
                profile = (temp / 'profile').as_uri()
                result = run([soffice, f'-env:UserInstallation={profile}', '--headless', '--convert-to', 'pdf', '--outdir', str(temp), str(source)], args.timeout)
                renderer_label = 'LibreOffice PDF export'
                detail = result.stdout + '\n' + result.stderr
            else:
                renderer_label = export_powerpoint(source, generated)
                detail = ''
            if not generated.is_file() or generated.stat().st_size == 0:
                raise RuntimeError(renderer + ' produced no PDF: ' + detail)
            if sha256(source) != input_hash:
                raise RuntimeError('Input changed during rendering; create a fresh render')
            pdf = out_dir / 'export.pdf'
            shutil.copy2(generated, pdf)
        files = rasterize(pdf, out_dir, args.dpi, poppler, args.timeout)
        if not files:
            raise RuntimeError('No rendered slide images were produced')
        if sha256(source) != input_hash:
            raise RuntimeError('Input changed during rasterization; create a fresh render')
        contact_sheet = montage(files, out_dir / 'montage.png')
        try:
            text_check = {'checked': True, 'flags': text_flags(source_segments(source), pdf_lines(pdf)),
                          'note': 'Read from the exported PDF text layer: a line that starts with closing punctuation '
                                  '(line_start_punct), a word or number split across lines (split_word), or a paragraph '
                                  'whose last line holds one or two characters (short_last_line). Text in charts and '
                                  'pictures is not checked; this does not replace looking at every page.'}
        except (ImportError, KeyError, ET.ParseError, zipfile.BadZipFile) as exc:
            text_check = {'checked': False, 'reason': str(exc)}
        manifest = {
            'deck': str(source), 'deck_sha256': input_hash,
            'renderer': renderer_label, 'dpi': args.dpi,
            'pdf': {'file': pdf.name, 'sha256': sha256(pdf)},
            'pages': [{'page': i, 'file': path.name, 'sha256': sha256(path)} for i, path in enumerate(files, 1)],
            'montage': contact_sheet,
            'text_check': text_check,
            'note': 'Rendered files exist; they have not yet been visually reviewed.'
        }
        manifest_path = out_dir / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        summary = {'pages': len(files), 'manifest': str(manifest_path), 'montage': contact_sheet}
        if text_check['checked']:
            flags = text_check['flags']
            summary['text_flags'] = len(flags)
            if flags:
                summary['text_flag_pages'] = sorted({f['page'] for f in flags})
                summary['text_flag_hint'] = ('Line breaks to fix (details in manifest text_check): tag Chinese runs '
                                             'lang="zh-CN", widen or reword the box, then render again')
        else:
            summary['text_flags'] = 'not checked: ' + text_check['reason']
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
