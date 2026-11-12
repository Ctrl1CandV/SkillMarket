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


def powerpoint_com_status():
    """Inspect Python support and COM registration without starting PowerPoint."""
    status = {'available': False, 'python_support': False, 'registered': False,
              'probe': 'read-only registry and Python module lookup'}
    if sys.platform != 'win32':
        return status
    status['python_support'] = importlib.util.find_spec('win32com') is not None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r'PowerPoint.Application\CLSID') as key:
            clsid = winreg.QueryValueEx(key, '')[0]
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'CLSID\\' + clsid + r'\LocalServer32') as key:
            server = winreg.QueryValueEx(key, '')[0]
        status['registered'] = bool(server)
    except OSError:
        pass
    status['available'] = status['python_support'] and status['registered']
    return status


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
    powerpoint = powerpoint_com_status()
    authoring_engines = (['pptxgenjs'] if modules.get('pptxgenjs') else []) + (['python-pptx'] if python_modules['pptx'] else [])
    renderers = (['libreoffice'] if soffice else []) + (['powerpoint'] if powerpoint['available'] else [])
    render_ready = bool(renderers and (poppler or python_modules['pymupdf'] or python_modules['fitz']))
    advice = None
    if not render_ready:
        advice = ('No PPTX renderer here. Make at most one ordinary install attempt that the host permits '
                  '(system package manager or the official installer). If that is not possible, stop there: '
                  'do not unpack system packages, build a private runtime (proot, fakechroot, AppImage hunting) '
                  'or probe system directories. Build the deck, run audit_pptx.py, tell the user that exported '
                  'rendering was not verified and which program they need to install.')
    print(json.dumps({
        'python': sys.executable, 'node': node, 'node_modules': modules,
        'python_modules': python_modules, 'soffice': soffice, 'pdftoppm': poppler,
        'native_authoring_available': bool(authoring_engines),
        'native_authoring_engines': authoring_engines,
        'powerpoint_com': powerpoint,
        'pptx_visual_renderers': renderers,
        'pptx_visual_render_available': render_ready,
        'no_renderer_advice': advice,
        'probe_error': probe_error,
        'note': 'Available dependencies/COM registration do not prove successful export, content, editability or visual quality.'
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
