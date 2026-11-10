#!/usr/bin/env python3
"""Read-only probe of the tools a code-made video needs. Installs nothing and contacts no service.

  doctor.py [--project DIR] [--json]

Reports ffmpeg/ffprobe and the filters the other scripts use, Node and the video engines a project
already depends on, a headless browser, Chinese fonts, LaTeX for Manim, and optional Python modules.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

QA_FILTERS = ['scale', 'tile', 'drawbox', 'drawtext', 'blackdetect', 'freezedetect', 'signalstats', 'metadata',
              'select']
MIX_FILTERS = ['ebur128', 'loudnorm', 'sidechaincompress', 'amix', 'adelay', 'silencedetect', 'volumedetect',
               'afade', 'apad']
ENGINE_FILTERS = ['subtitles', 'xfade', 'zoompan']
ENCODERS = ['libx264', 'aac']
NPM_ENGINES = ['remotion', '@remotion/cli', 'hyperframes', '@hyperframes/core', 'gsap', '@motion-canvas/core',
               'playwright', 'playwright-core', 'puppeteer', 'puppeteer-core']
PY_MODULES = ['manim', 'moviepy', 'PIL', 'numpy', 'edge_tts', 'whisper', 'faster_whisper']
CJK_FONT_HINTS = re.compile(r'(Noto ?(Sans|Serif) ?(CJK|SC|TC)|Source ?Han|思源|WenQuanYi|wqy|文泉|PingFang|'
                            r'Hiragino ?Sans ?GB|Microsoft ?YaHei|msyh|微软雅黑|SimHei|黑体|SimSun|宋体|LXGW|霞鹜|'
                            r'Smiley ?Sans|得意黑|HarmonyOS ?Sans ?SC|MiSans|Alibaba ?PuHuiTi|阿里巴巴普惠体|'
                            r'Droid ?Sans ?Fallback)', re.I)


def run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except (OSError, subprocess.SubprocessError) as exc:
        return -1, '', str(exc)


def version_line(path, flag='-version'):
    code, out, err = run([path, flag])
    text = (out or err).strip().splitlines()
    return text[0].strip() if text else None


def ffmpeg_info():
    ff = os.environ.get('VIDEO_CRAFT_FFMPEG') or shutil.which('ffmpeg')
    fp = os.environ.get('VIDEO_CRAFT_FFPROBE') or shutil.which('ffprobe')
    info = {'ffmpeg': ff, 'ffprobe': fp, 'version': None, 'missing_filters': {}, 'missing_encoders': []}
    if not ff:
        return info
    info['version'] = version_line(ff)
    _, out, _ = run([ff, '-hide_banner', '-filters'])
    have = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and re.match(r'^[TSC.|AVN]+$', parts[0]):
            have.add(parts[1])
    for group, names in (('qa', QA_FILTERS), ('mix', MIX_FILTERS), ('engine', ENGINE_FILTERS)):
        miss = [n for n in names if n not in have]
        if miss:
            info['missing_filters'][group] = miss
    _, out, _ = run([ff, '-hide_banner', '-encoders'])
    info['missing_encoders'] = [e for e in ENCODERS if not re.search(r'\s%s\s' % re.escape(e), out)]
    _, out, _ = run([ff, '-hide_banner', '-h', 'filter=amix'])
    info['amix_normalize'] = 'normalize' in out
    return info


def node_info():
    node = shutil.which('node')
    info = {'node': node, 'version': None, 'npm': shutil.which('npm'), 'npx': shutil.which('npx')}
    if node:
        v = version_line(node, '--version')
        info['version'] = v
        m = re.match(r'v?(\d+)', v or '')
        info['major'] = int(m.group(1)) if m else None
    return info


def browsers(project=None):
    found = []
    for name in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome', 'msedge',
                 'microsoft-edge'):
        p = shutil.which(name)
        if p:
            found.append(p)
    fixed = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
             '/Applications/Chromium.app/Contents/MacOS/Chromium']
    for env in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
        base = os.environ.get(env)
        if base:
            fixed.append(os.path.join(base, 'Google', 'Chrome', 'Application', 'chrome.exe'))
            fixed.append(os.path.join(base, 'Microsoft', 'Edge', 'Application', 'msedge.exe'))
    found += [p for p in fixed if os.path.isfile(p)]
    caches = [Path.home() / '.cache' / 'ms-playwright', Path.home() / 'Library' / 'Caches' / 'ms-playwright']
    if os.environ.get('LOCALAPPDATA'):
        caches.append(Path(os.environ['LOCALAPPDATA']) / 'ms-playwright')
    for c in caches:
        if c.is_dir():
            found += [str(d) for d in sorted(c.glob('chromium*')) if d.is_dir()]
    if project:
        shell = Path(project) / 'node_modules' / '.remotion'
        if shell.is_dir():
            found.append(str(shell) + '（Remotion 自带的无头浏览器）')
    return found


def cjk_fonts(project=None):
    families = set()
    fc = shutil.which('fc-list')
    if fc:
        _, out, _ = run([fc, ':lang=zh', 'family'])
        for line in out.splitlines():
            for fam in line.split(','):
                fam = fam.strip()
                if fam:
                    families.add(fam)
    else:
        dirs = [Path('/System/Library/Fonts'), Path('/Library/Fonts'), Path.home() / 'Library' / 'Fonts']
        if os.environ.get('WINDIR'):
            dirs.append(Path(os.environ['WINDIR']) / 'Fonts')
        for d in dirs:
            if d.is_dir():
                for f in d.iterdir():
                    if re.search(r'(msyh|simhei|simsun|PingFang|STHeiti|Hiragino Sans GB|NotoSans.*(SC|CJK)|'
                                 r'SourceHan)', f.name, re.I):
                        families.add(f.stem)
    project_fonts = []
    if project and Path(project).is_dir():
        for p in Path(project).rglob('*'):
            if 'node_modules' in p.parts or '.git' in p.parts:
                continue
            if p.suffix.lower() in ('.ttf', '.otf', '.ttc', '.woff', '.woff2') and CJK_FONT_HINTS.search(
                    p.stem.replace('-', ' ').replace('_', ' ')):
                project_fonts.append(str(p))
            if len(project_fonts) >= 20:
                break
    return sorted(families), project_fonts


def project_info(project):
    if not project:
        return None
    root = Path(project)
    info = {'path': str(root.resolve()), 'npm': {}, 'python': [], 'hints': []}
    pkg = root / 'package.json'
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding='utf-8'))
            deps = {}
            for key in ('dependencies', 'devDependencies'):
                deps.update(data.get(key) or {})
            info['npm'] = {k: v for k, v in deps.items() if k in NPM_ENGINES or k.startswith('@remotion/')}
        except (OSError, ValueError):
            info['hints'].append('package.json 无法解析')
    for name in ('requirements.txt', 'pyproject.toml', 'environment.yml'):
        p = root / name
        if p.is_file():
            text = p.read_text(encoding='utf-8', errors='replace').lower()
            for mod in ('manim', 'moviepy', 'manim-voiceover'):
                if mod in text:
                    info['python'].append('%s（%s）' % (mod, name))
    for name in ('remotion.config.ts', 'remotion.config.js'):
        if (root / name).is_file():
            info['hints'].append('发现 %s：Remotion 工程' % name)
    if (root / 'hyperframes.json').is_file():
        info['hints'].append('发现 hyperframes.json：HyperFrames 工程')
    return info


def tex_info():
    return {name: shutil.which(name) for name in ('latex', 'xelatex', 'dvisvgm')}


def py_modules():
    return {m: importlib.util.find_spec(m) is not None for m in PY_MODULES}


def install_hint():
    system = platform.system()
    if system == 'Windows':
        return 'winget install Gyan.FFmpeg（或 conda install -c conda-forge ffmpeg）'
    if system == 'Darwin':
        return 'brew install ffmpeg（或 conda install -c conda-forge ffmpeg）'
    return 'sudo apt install ffmpeg（Debian/Ubuntu），或在 conda 环境中 conda install -c conda-forge ffmpeg'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--project', help='视频工程目录，用来识别已用的引擎和工程内字体')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    ff = ffmpeg_info()
    node = node_info()
    fams, proj_fonts = cjk_fonts(args.project)
    report = {
        'python': sys.version.split()[0], 'platform': platform.platform(),
        'ffmpeg': ff, 'node': node, 'browsers': browsers(args.project),
        'cjk_fonts': {'system': fams, 'project': proj_fonts},
        'latex': tex_info(), 'python_modules': py_modules(), 'project': project_info(args.project),
    }
    advice = []
    if not ff['ffmpeg'] or not ff['ffprobe']:
        advice.append('缺 ffmpeg/ffprobe：审查、混音和多数引擎的编码都需要它。征得用户同意后安装：' + install_hint())
    else:
        if ff['missing_encoders']:
            advice.append('ffmpeg 缺编码器 %s：成片编码需要 libx264 和 aac，换用完整版 ffmpeg。' % '、'.join(ff['missing_encoders']))
        if ff['missing_filters'].get('qa'):
            advice.append('ffmpeg 缺审查用滤镜 %s；video_qa.py 会跳过对应检测（缺 drawtext 时帧图没有标签）。'
                          % '、'.join(ff['missing_filters']['qa']))
        if ff['missing_filters'].get('mix'):
            advice.append('ffmpeg 缺混音用滤镜 %s；mix_audio.py 可能失败。' % '、'.join(ff['missing_filters']['mix']))
        if 'subtitles' in ff['missing_filters'].get('engine', []):
            advice.append('ffmpeg 没有 libass（subtitles 滤镜）：不能用 ffmpeg 烧录 SRT 字幕，改在引擎里渲染字幕。')
    if not fams and not proj_fonts:
        advice.append('没有找到中文字体：中文会显示成豆腐块。把思源黑体（Noto Sans SC）等字体文件放进工程并显式加载，'
                      '或请用户安装到系统。')
    proj = report['project'] or {}
    npm = proj.get('npm') or {}
    if node['node'] is None and (npm or not proj.get('python')):
        advice.append('没有 Node.js：Remotion 和 HyperFrames 都需要它（HyperFrames 要求 Node 22+）。')
    elif node.get('major') and node['major'] < 22 and any(k.startswith('hyperframes') or k.startswith('@hyperframes')
                                                          for k in npm):
        advice.append('HyperFrames 要求 Node 22+，当前 %s。' % node['version'])
    if npm and not report['browsers'] and any(k.startswith(('remotion', '@remotion', 'hyperframes', 'playwright',
                                                            'puppeteer')) for k in npm):
        advice.append('没有找到无头浏览器；Remotion 渲染时会自动下载，其他方案按其文档安装（需联网）。')
    if (report['python_modules'].get('manim') or proj.get('python')) and not report['latex']['latex']:
        advice.append('Manim 可用但没有 LaTeX：MathTex/Tex 公式会失败，纯 Text 不受影响。')
    report['advice'] = advice

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    def yn(v):
        return v if v else '未找到'

    print('Python %s  |  %s' % (report['python'], report['platform']))
    print('ffmpeg   %s' % (ff['version'] or '未找到'))
    print('ffprobe  %s' % yn(ff['ffprobe']))
    print('Node     %s%s' % (node['version'] or '未找到', '' if not node['npx'] else '（npx 可用）'))
    print('浏览器   %s' % ('；'.join(report['browsers'][:4]) if report['browsers'] else '未找到'))
    print('中文字体 系统 %d 个%s；工程内 %d 个' % (len(fams), '（%s 等）' % '、'.join(fams[:3]) if fams else '',
                                          len(proj_fonts)))
    print('LaTeX    %s' % ('可用' if report['latex']['latex'] else '未找到'))
    mods = [m for m, ok in report['python_modules'].items() if ok]
    print('Python 模块 %s' % ('、'.join(mods) if mods else '无相关模块'))
    if report['project']:
        p = report['project']
        print('工程     %s' % p['path'])
        if p['npm']:
            print('  npm 依赖：%s' % '，'.join('%s %s' % kv for kv in sorted(p['npm'].items())))
        for x in p['python'] + p['hints']:
            print('  ' + x)
        if not (p['npm'] or p['python'] or p['hints']):
            print('  没有识别到视频引擎')
    if advice:
        print('\n建议：')
        for a in advice:
            print('- ' + a)
    else:
        print('\n基础工具齐全。')


if __name__ == '__main__':
    main()
