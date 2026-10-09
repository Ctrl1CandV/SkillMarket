#!/usr/bin/env python3
"""Render the actual PPTX via isolated LibreOffice, then rasterize its exported PDF."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from doctor import find_soffice


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(command, timeout):
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {result.stdout}\n{result.stderr}')
    return result


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
        if not soffice:
            raise ValueError('LibreOffice is unavailable; pass --soffice or use another reliable renderer')
        if not poppler and not any(importlib.util.find_spec(m) for m in ('pymupdf', 'fitz')):
            raise ValueError('Install/use pdftoppm or PyMuPDF to rasterize the PDF')
        input_hash = sha256(source)
        out_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.presentation-render-', dir=out_dir.parent) as temporary:
            temp = Path(temporary)
            profile = (temp / 'profile').as_uri()
            result = run([soffice, f'-env:UserInstallation={profile}', '--headless', '--convert-to', 'pdf', '--outdir', str(temp), str(source)], args.timeout)
            generated = temp / (source.stem + '.pdf')
            if not generated.is_file() or generated.stat().st_size == 0:
                raise RuntimeError('LibreOffice produced no PDF: ' + result.stdout + '\n' + result.stderr)
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
        manifest = {
            'deck': str(source), 'deck_sha256': input_hash,
            'renderer': 'LibreOffice PDF export', 'dpi': args.dpi,
            'pdf': {'file': pdf.name, 'sha256': sha256(pdf)},
            'pages': [{'page': i, 'file': path.name, 'sha256': sha256(path)} for i, path in enumerate(files, 1)],
            'montage': contact_sheet,
            'note': 'Rendered files exist; they have not yet been visually reviewed.'
        }
        manifest_path = out_dir / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'pages': len(files), 'manifest': str(manifest_path), 'montage': contact_sheet}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
