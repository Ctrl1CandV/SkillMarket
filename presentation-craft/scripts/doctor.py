#!/usr/bin/env python3
"""Read-only dependency probe; does not install packages or contact services."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def find_soffice(explicit=None):
    if explicit:
        p = Path(explicit)
        return str(p.resolve()) if p.is_file() else shutil.which(explicit)
    found = shutil.which('soffice') or shutil.which('libreoffice')
    if found:
        return found
    for key in ('ProgramFiles', 'ProgramFiles(x86)'):
        base = os.environ.get(key)
        if base:
            for name in ('soffice.com', 'soffice.exe'):
                p = Path(base) / 'LibreOffice' / 'program' / name
                if p.is_file():
                    return str(p)
    mac = Path('/Applications/LibreOffice.app/Contents/MacOS/soffice')
    return str(mac) if mac.is_file() else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', help='Node executable; otherwise search PATH')
    parser.add_argument('--soffice', help='LibreOffice executable')
    args = parser.parse_args()
    node = args.node or shutil.which('node')
    modules = {}
    probe_error = None
    if node:
        code = "const o={};for(const m of ['pptxgenjs','@slidev/cli']){try{o[m]=require.resolve(m)}catch{o[m]=null}}process.stdout.write(JSON.stringify(o))"
        try:
            result = subprocess.run([node, '-e', code], capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                modules = json.loads(result.stdout)
            else:
                probe_error = result.stderr.strip()
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            probe_error = str(exc)
    python_modules = {m: importlib.util.find_spec(m) is not None for m in ('pptx', 'PIL', 'pymupdf', 'fitz')}
    soffice = find_soffice(args.soffice)
    poppler = shutil.which('pdftoppm')
    print(json.dumps({
        'python': sys.executable, 'node': node, 'node_modules': modules,
        'python_modules': python_modules, 'soffice': soffice, 'pdftoppm': poppler,
        'native_authoring_available': bool(modules.get('pptxgenjs')),
        'pptx_visual_render_available': bool(soffice and (poppler or python_modules['pymupdf'] or python_modules['fitz'])),
        'probe_error': probe_error,
        'note': 'Available dependencies do not prove content, editability or visual quality.'
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
