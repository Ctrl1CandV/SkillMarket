#!/usr/bin/env python3
"""Make review material for a rendered video and run automatic checks.

  video_qa.py probe  VIDEO [--json]
  video_qa.py detect VIDEO [--timeline T] [--out DIR] [--target-lufs -14]
  video_qa.py sheet  VIDEO --out DIR [--timeline T | --every S | --times a,b] [--guides vertical|title-safe]
  video_qa.py strips VIDEO --out DIR (--timeline T | --cuts a,b) [--no-entries]
  video_qa.py frames VIDEO --out DIR --times a,b [--guides ...]
  video_qa.py all    VIDEO --out DIR [--timeline T | --every S] [--guides ...]

Needs ffmpeg and ffprobe (on PATH, or --ffmpeg / --ffprobe). Standard library only.
The checks measure what can be computed; they do not judge whether a frame looks good.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile

FFMPEG = 'ffmpeg'
FFPROBE = 'ffprobe'
_FILTERS = None


# ---------------------------------------------------------------- tools

def resolve_tools(args):
    global FFMPEG, FFPROBE
    ff = getattr(args, 'ffmpeg', None) or os.environ.get('VIDEO_CRAFT_FFMPEG') or shutil.which('ffmpeg')
    fp = getattr(args, 'ffprobe', None) or os.environ.get('VIDEO_CRAFT_FFPROBE') or shutil.which('ffprobe')
    if not ff or not fp:
        sys.exit('需要 ffmpeg 和 ffprobe。运行 doctor.py 查看安装建议，或用 --ffmpeg/--ffprobe 指定路径。')
    FFMPEG, FFPROBE = ff, fp


def run(cmd, cwd=None, check=True, timeout=None):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8',
                          errors='replace', timeout=timeout)
    if check and proc.returncode != 0:
        tail = '\n'.join(proc.stderr.strip().splitlines()[-12:])
        raise RuntimeError('命令失败（%d）：%s\n%s' % (proc.returncode, ' '.join(cmd[:6]) + ' …', tail))
    return proc


def available_filters():
    global _FILTERS
    if _FILTERS is None:
        out = run([FFMPEG, '-hide_banner', '-filters'], check=False).stdout
        _FILTERS = set()
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 3 and re.match(r'^[TSC.|AVN]+$', parts[0]):
                _FILTERS.add(parts[1])
    return _FILTERS


def ratio(text):
    try:
        if '/' in text:
            a, b = text.split('/', 1)
            return float(a) / float(b) if float(b) else 0.0
        return float(text)
    except (ValueError, TypeError):
        return 0.0


def fnum(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_times(text):
    if not text:
        return []
    return [float(x) for x in re.split(r'[,\s]+', text.strip()) if x]


def filter_quote(value):
    """Quote a path for use as a filter option value."""
    value = str(value).replace('\\', '/')
    return "'" + value.replace("'", r"'\''").replace(':', r'\:') + "'"


def find_label_font():
    candidates = []
    fc = shutil.which('fc-match')
    if fc:
        try:
            out = run([fc, '-f', '%{file}', 'DejaVu Sans:style=Bold'], check=False, timeout=10).stdout.strip()
            if out:
                candidates.append(out)
            out = run([fc, '-f', '%{file}', 'sans-serif'], check=False, timeout=10).stdout.strip()
            if out:
                candidates.append(out)
        except (OSError, subprocess.SubprocessError):
            pass
    candidates += [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
        '/Library/Fonts/Arial.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
        'C:/Windows/Fonts/arial.ttf',
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    return None


# ---------------------------------------------------------------- probe

def mp4_top_boxes(path, limit=64):
    order = []
    try:
        size_total = os.path.getsize(path)
        with open(path, 'rb') as fh:
            pos = 0
            while pos < size_total and len(order) < limit:
                fh.seek(pos)
                hdr = fh.read(8)
                if len(hdr) < 8:
                    break
                size, kind = struct.unpack('>I4s', hdr)
                if size == 1:
                    size = struct.unpack('>Q', fh.read(8))[0]
                elif size == 0:
                    size = size_total - pos
                if size < 8:
                    break
                order.append(kind.decode('latin-1'))
                pos += size
    except OSError:
        return []
    return order


def probe(video):
    data = json.loads(run([FFPROBE, '-v', 'error', '-print_format', 'json', '-show_format',
                           '-show_streams', str(video)]).stdout or '{}')
    streams = data.get('streams') or []
    fmt = data.get('format') or {}
    v = next((s for s in streams if s.get('codec_type') == 'video' and not s.get('disposition', {}).get('attached_pic')), None)
    a = next((s for s in streams if s.get('codec_type') == 'audio'), None)
    info = {'file': str(video), 'container': fmt.get('format_name'), 'duration': fnum(fmt.get('duration'), 0.0),
            'bitrate_kbps': round(fnum(fmt.get('bit_rate'), 0.0) / 1000) if fmt.get('bit_rate') else None,
            'size_mb': round(fnum(fmt.get('size'), 0.0) / 1048576, 2)}
    checks = []

    def add(level, code, msg):
        checks.append({'level': level, 'code': code, 'msg': msg})

    if not v:
        add('error', 'no-video', '文件里没有视频流。')
        info['checks'] = checks
        return info
    r_fps, avg_fps = ratio(v.get('r_frame_rate', '0')), ratio(v.get('avg_frame_rate', '0'))
    info['video'] = {
        'codec': v.get('codec_name'), 'profile': v.get('profile'), 'width': v.get('width'),
        'height': v.get('height'), 'pix_fmt': v.get('pix_fmt'), 'fps': round(r_fps, 3),
        'avg_fps': round(avg_fps, 3), 'duration': fnum(v.get('duration'), info['duration']),
        'frames': int(v['nb_frames']) if str(v.get('nb_frames', '')).isdigit() else None,
        'color_space': v.get('color_space'), 'color_primaries': v.get('color_primaries'),
        'color_transfer': v.get('color_transfer'), 'sar': v.get('sample_aspect_ratio'),
    }
    vi = info['video']
    if vi['codec'] != 'h264':
        add('info', 'codec', '视频编码是 %s；上传各平台兼容性最好的是 H.264。' % vi['codec'])
    if vi['codec'] in ('h264', 'hevc') and vi['pix_fmt'] != 'yuv420p':
        add('warn', 'pix-fmt', '像素格式 %s；部分播放器和平台只支持 yuv420p。' % vi['pix_fmt'])
    if (vi['width'] or 0) % 2 or (vi['height'] or 0) % 2:
        add('error', 'odd-size', '宽或高是奇数（%sx%s），H.264 yuv420p 需要偶数。' % (vi['width'], vi['height']))
    if r_fps and avg_fps and abs(r_fps - avg_fps) > 0.05 * r_fps:
        add('warn', 'vfr', '可能是可变帧率（标称 %.3f，平均 %.3f）；用恒定帧率重新编码。' % (r_fps, avg_fps))
    if vi['sar'] not in (None, '1:1', '0:1'):
        add('warn', 'sar', '像素宽高比 %s 不是 1:1，平台上可能被拉伸。' % vi['sar'])
    if not (vi['color_primaries'] or vi['color_space']):
        add('info', 'color-tags', '没有色彩标签；建议标为 BT.709，避免不同播放器颜色偏移。')
    if a:
        info['audio'] = {'codec': a.get('codec_name'), 'sample_rate': int(fnum(a.get('sample_rate'), 0)),
                         'channels': a.get('channels'), 'duration': fnum(a.get('duration'), info['duration'])}
        if info['audio']['sample_rate'] not in (44100, 48000):
            add('info', 'sample-rate', '音频采样率 %s Hz；常用 48000。' % info['audio']['sample_rate'])
        diff = abs((info['audio']['duration'] or 0) - (vi['duration'] or 0))
        if diff > 0.1:
            add('warn', 'av-length', '音频与视频时长相差 %.2f s。' % diff)
    else:
        add('info', 'no-audio', '没有音频流。需要配音或音乐时用 mix_audio.py 合成。')
    boxes = mp4_top_boxes(video) if str(info['container'] or '').startswith('mov') else []
    if boxes:
        info['mp4_boxes'] = boxes[:12]
        if 'moov' in boxes and 'mdat' in boxes and boxes.index('moov') > boxes.index('mdat'):
            add('warn', 'faststart', 'moov 在文件末尾，网页上要下载完才能播放；编码时加 -movflags +faststart。')
    info['checks'] = checks
    return info


# ---------------------------------------------------------------- timeline helpers

def load_timeline(path):
    if not path:
        return None
    with open(path, encoding='utf-8') as fh:
        data = json.load(fh)
    shots = data.get('shots') or []
    t = 0.0
    out = []
    for i, s in enumerate(shots):
        start = fnum(s.get('start'))
        end = fnum(s.get('end'))
        fps = fnum(data.get('fps'))
        if fps and s.get('from') is not None and s.get('durationInFrames') is not None:
            start = int(s['from']) / fps  # exact frame boundaries from storyboard.py timeline
            end = (int(s['from']) + int(s['durationInFrames'])) / fps
        if start is None or end is None:  # a storyboard: accumulate durations
            dur = fnum(s.get('duration'), 0.0)
            start, end = t, t + dur
        t = end
        out.append({'id': str(s.get('id') or 'shot%02d' % (i + 1)), 'start': start, 'end': end,
                    'role': s.get('role'), 'transition': s.get('transition')})
    fmt = data.get('format') or {}
    return {'shots': out, 'cuts': [s['end'] for s in out[:-1]],
            'fps': fnum(data.get('fps') or fmt.get('fps')), 'width': data.get('width') or fmt.get('width'),
            'height': data.get('height') or fmt.get('height'),
            'duration': fnum(data.get('duration'), out[-1]['end'] if out else None)}


def shot_at(timeline, t):
    if not timeline:
        return None
    for s in timeline['shots']:
        if s['start'] <= t < s['end']:
            return s
    return timeline['shots'][-1] if timeline['shots'] else None


# ---------------------------------------------------------------- detect

def parse_metadata_file(path, key):
    values = []
    if not Path(path).is_file():
        return values
    cur_t = None
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            m = re.search(r'pts_time:([-\d.e+]+)', line)
            if m:
                cur_t = float(m.group(1))
                continue
            if line.startswith(key + '=') and cur_t is not None:
                values.append((cur_t, float(line.split('=', 1)[1])))
    return values


def find_flashes(yavg, fps):
    """Short luminance spikes or dips that return to the previous level within a few frames."""
    if len(yavg) < 3:
        return []
    scale = 4.0 if max(v for _, v in yavg) > 260 else 1.0
    ys = [v / scale for _, v in yavg]
    ts = [t for t, _ in yavg]
    flashes, i = [], 1
    while i < len(ys) - 1:
        jump = ys[i] - ys[i - 1]
        if abs(jump) >= 45:
            for k in range(1, 5):
                j = i + k
                if j >= len(ys):
                    break
                if abs(ys[j] - ys[i - 1]) < 15 and abs(ys[j] - ys[i]) > 30:
                    flashes.append({'time': round(ts[i], 3), 'frames': k, 'from': round(ys[i - 1], 1),
                                    'peak': round(ys[i], 1), 'kind': 'bright' if jump > 0 else 'dark'})
                    i = j
                    break
        i += 1
    return flashes


def detect(video, info, timeline=None, workdir=None, target_lufs=-14.0, true_peak=-1.0):
    filters = available_filters()
    fps = (info.get('video') or {}).get('fps') or 30.0
    duration = info.get('duration') or 0.0
    result = {'black': [], 'freeze': [], 'flashes': [], 'scene_changes': [], 'silence': [],
              'loudness': None, 'checks': []}

    def add(level, code, msg, time=None):
        item = {'level': level, 'code': code, 'msg': msg}
        if time is not None:
            item['time'] = round(time, 3)
            s = shot_at(timeline, time)
            if s:
                item['shot'] = s['id']
        result['checks'].append(item)

    tmp = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix='vqa-'))
    tmp.mkdir(parents=True, exist_ok=True)
    chain = []
    if 'blackdetect' in filters:
        chain.append('blackdetect=d=0.03:pix_th=0.06:pic_th=0.98')
    if 'freezedetect' in filters:
        chain.append('freezedetect=n=-60dB:d=1.0')
    if 'signalstats' in filters and 'metadata' in filters:
        chain.append('signalstats,metadata=mode=print:key=lavfi.signalstats.YAVG:file=yavg.txt')
    if 'select' in filters and 'metadata' in filters:
        chain.append("select='gt(scene,0.30)',metadata=mode=print:key=lavfi.scene_score:file=scene.txt")
    if chain:
        proc = run([FFMPEG, '-hide_banner', '-nostats', '-i', str(Path(video).resolve()), '-map', '0:v:0',
                    '-vf', ','.join(chain), '-f', 'null', '-'], cwd=str(tmp), check=False)
        log = proc.stderr
        for m in re.finditer(r'black_start:([\d.]+)\s+black_end:([\d.]+)\s+black_duration:([\d.]+)', log):
            result['black'].append({'start': float(m.group(1)), 'end': float(m.group(2)),
                                    'duration': float(m.group(3))})
        starts = [float(x) for x in re.findall(r'freeze_start: ([\d.]+)', log)]
        durs = [float(x) for x in re.findall(r'freeze_duration: ([\d.]+)', log)]
        ends = [float(x) for x in re.findall(r'freeze_end: ([\d.]+)', log)]
        for k, st in enumerate(starts):
            if k < len(durs):
                result['freeze'].append({'start': st, 'duration': durs[k], 'end': ends[k] if k < len(ends) else st + durs[k]})
            else:  # freeze running until the end of the file
                result['freeze'].append({'start': st, 'duration': round(duration - st, 3), 'end': duration})
        result['flashes'] = find_flashes(parse_metadata_file(tmp / 'yavg.txt', 'lavfi.signalstats.YAVG'), fps)
        result['scene_changes'] = [{'time': round(t, 3), 'score': round(s, 3)}
                                   for t, s in parse_metadata_file(tmp / 'scene.txt', 'lavfi.scene_score')]

    if info.get('audio'):
        achain = []
        if 'silencedetect' in filters:
            achain.append('silencedetect=n=-50dB:d=0.6')
        if 'ebur128' in filters:
            achain.append('ebur128=peak=true')
        if achain:
            proc = run([FFMPEG, '-hide_banner', '-nostats', '-i', str(video), '-map', '0:a:0',
                        '-af', ','.join(achain), '-f', 'null', '-'], check=False)
            log = proc.stderr
            s_starts = [float(x) for x in re.findall(r'silence_start: ([-\d.]+)', log)]
            s_ends = re.findall(r'silence_end: ([\d.]+) \| silence_duration: ([\d.]+)', log)
            for k, st in enumerate(s_starts):
                if k < len(s_ends):
                    result['silence'].append({'start': max(0.0, st), 'end': float(s_ends[k][0]),
                                              'duration': float(s_ends[k][1])})
                else:
                    result['silence'].append({'start': max(0.0, st), 'end': duration,
                                              'duration': round(duration - max(0.0, st), 3)})
            summary = log[log.rfind('Summary:'):] if 'Summary:' in log else ''
            m_i = re.search(r'I:\s+([-\d.]+) LUFS', summary)
            m_lra = re.search(r'LRA:\s+([-\d.]+) LU', summary)
            m_tp = re.search(r'Peak:\s+([-\d.inf]+) dBFS', summary)
            if m_i:
                result['loudness'] = {'integrated': float(m_i.group(1)),
                                      'lra': float(m_lra.group(1)) if m_lra else None,
                                      'true_peak': float(m_tp.group(1)) if m_tp and 'inf' not in m_tp.group(1) else None}

    # ---- interpret
    frame = 1.0 / fps
    for b in result['black']:
        if b['start'] < frame and b['duration'] <= 0.5:
            continue
        if b['end'] >= duration - frame and b['duration'] <= 1.0:
            continue
        add('warn', 'black', '近乎全黑的画面 %.2f s（%.2f–%.2f s）：98%% 以上像素接近黑色。'
            '深色背景上内容很少时也会触发，确认是有意的。'
            % (b['duration'], b['start'], b['end']), b['start'])
    for f in result['flashes']:
        add('error', 'flash', '疑似闪帧：%d 帧亮度从 %.0f 跳到 %.0f 又回落（%s）。常见原因是透明度转场露出白底或空帧。'
            % (f['frames'], f['from'], f['peak'], '变亮' if f['kind'] == 'bright' else '变暗'), f['time'])
    last_shot = timeline['shots'][-1] if timeline and timeline['shots'] else None
    for fz in result['freeze']:
        s = shot_at(timeline, fz['start'] + 0.01)
        in_outro = bool(s and (s is last_shot or s.get('role') in ('outro', 'hold')))
        at_end = fz['end'] >= duration - 2 * frame
        if fz['duration'] >= 2.0 and not (in_outro or at_end):
            add('warn', 'freeze', '画面完全静止 %.1f s（%.2f–%.2f s）。确认这一段有内容在推进，或缩短。'
                % (fz['duration'], fz['start'], fz['end']), fz['start'])
        elif fz['duration'] >= 1.0 and not (in_outro or at_end):
            add('info', 'freeze', '静止 %.1f s（%.2f s 起）。' % (fz['duration'], fz['start']), fz['start'])
    for si in result['silence']:
        if si['duration'] >= 1.5 and si['start'] > 0.3 and si['end'] < duration - 0.3:
            add('info', 'silence', '静音 %.1f s（%.2f–%.2f s）。' % (si['duration'], si['start'], si['end']), si['start'])
    if info.get('audio') and result['silence'] and len(result['silence']) == 1 \
            and result['silence'][0]['duration'] >= duration - 0.5:
        add('warn', 'all-silent', '音轨几乎全程静音。')
    loud = result['loudness']
    if loud:
        if target_lufs is not None and abs(loud['integrated'] - target_lufs) > 2.0:
            add('warn', 'loudness', '积分响度 %.1f LUFS，目标约 %.0f LUFS。用 mix_audio.py 统一。'
                % (loud['integrated'], target_lufs))
        if loud['true_peak'] is not None and loud['true_peak'] > true_peak + 0.1:
            add('warn', 'true-peak', '真峰值 %.1f dBTP，高于 %.1f。' % (loud['true_peak'], true_peak))

    if timeline:
        vi = info.get('video') or {}
        if timeline.get('width') and timeline.get('height') and \
                (int(timeline['width']), int(timeline['height'])) != (vi.get('width'), vi.get('height')):
            add('error', 'size', '成片 %sx%s 与时间线 %sx%s 不一致。'
                % (vi.get('width'), vi.get('height'), timeline['width'], timeline['height']))
        if timeline.get('fps') and vi.get('fps') and abs(timeline['fps'] - vi['fps']) > 0.01:
            add('warn', 'fps', '成片 %.3f fps 与时间线 %.3f fps 不一致。' % (vi['fps'], timeline['fps']))
        if timeline.get('duration') and abs(timeline['duration'] - duration) > 2.5 * frame:
            add('warn', 'duration', '成片 %.2f s，时间线 %.2f s；配音与画面可能已经错位。'
                % (duration, timeline['duration']))
        tol = max(2.5 * frame, 0.09)
        changes = [c['time'] for c in result['scene_changes']]
        matched = []
        for cut in timeline['cuts']:
            near = [c for c in changes if abs(c - cut) <= tol]
            matched.append({'cut': cut, 'detected': min(near, key=lambda c: abs(c - cut)) if near else None})
        result['cut_match'] = matched
        unmatched = [m['cut'] for m in matched if m['detected'] is None]
        if unmatched and changes:
            add('info', 'cut-soft', '%d 个计划切点没有检测到明显画面变化（%s）：共享元素或连续运动的切点属正常，'
                '否则检查镜头是否按时间线切换。' % (len(unmatched), '、'.join('%.2f' % c for c in unmatched[:8])))
        extra = [c for c in result['scene_changes']
                 if c['score'] >= 0.45 and all(abs(c['time'] - cut) > 0.25 for cut in timeline['cuts'])]
        for c in extra[:10]:
            add('info', 'jump', '计划外的画面突变（变化度 %.2f）：检查是否是有意的镜头内揭示。' % c['score'], c['time'])
    return result


# ---------------------------------------------------------------- frames, sheets, strips

def guide_filter(kind, width, height):
    if kind == 'vertical':
        return ('drawbox=x=0:y=0:w=iw:h=ih*160/1920:color=red@0.28:t=fill,'
                'drawbox=x=0:y=ih-ih*450/1920:w=iw:h=ih*450/1920:color=red@0.28:t=fill,'
                'drawbox=x=iw-iw*160/1080:y=0:w=iw*160/1080:h=ih:color=red@0.28:t=fill,'
                'drawbox=x=0:y=0:w=iw*64/1080:h=ih:color=red@0.18:t=fill')
    if kind == 'title-safe':
        t = max(2, int(round(min(width, height) / 180)))
        return 'drawbox=x=iw*0.05:y=ih*0.05:w=iw*0.9:h=ih*0.9:color=yellow@0.7:t=%d' % t
    return None


def frame_seek_time(t, fps, duration):
    """Seek point that lands on the frame containing time t, clamped inside the file."""
    if fps:
        k = int(round(t * fps))
        last = max(0, int(math.floor(duration * fps)) - 1)
        k = max(0, min(k, last))
        return max(0.0, (k - 0.25) / fps), k / fps
    t = max(0.0, min(t, duration - 0.05))
    return t, t


def extract_frame(video, t, out_path, fps, duration, width=None, guides=None, label=None, font=None, vsize=None):
    seek, actual = frame_seek_time(t, fps, duration)
    vf = []
    g = guide_filter(guides, *(vsize or (1920, 1080))) if guides else None
    if g:
        vf.append(g)
    if width:
        vf.append('scale=%d:-2:flags=lanczos' % width)
    label_file = None
    if label and font and 'drawtext' in available_filters():
        label_file = Path(out_path).with_suffix('.label.txt')
        label_file.write_text(label, encoding='utf-8')
        size = max(12, int((width or 960) / 22))
        vf.append("drawtext=fontfile=%s:textfile=%s:expansion=none:x=8:y=8:fontsize=%d:fontcolor=white:"
                  "box=1:boxcolor=black@0.65:boxborderw=6" % (filter_quote(font), filter_quote(label_file.name), size))
    cmd = [FFMPEG, '-hide_banner', '-v', 'error', '-ss', '%.4f' % seek, '-i', str(Path(video).resolve()),
           '-frames:v', '1']
    if vf:
        cmd += ['-vf', ','.join(vf)]
    cmd += ['-y', Path(out_path).name]
    run(cmd, cwd=str(Path(out_path).parent))
    if label_file:
        label_file.unlink()
    if not Path(out_path).is_file():
        raise RuntimeError('没有在 %.3f s 取到画面。' % t)
    return actual


def tile_images(cells, out_pattern, cols, rows_per_page, cell_size):
    """Lay out same-sized PNG cells into one or more JPEG pages with ffmpeg's tile filter."""
    out_pattern = Path(out_pattern)
    if not cells:
        return []
    work = out_pattern.parent / ('.tile-' + out_pattern.stem.replace('%02d', 'x'))
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    per_page = cols * rows_per_page
    n = len(cells)
    pages = max(1, int(math.ceil(n / float(per_page))))
    rows_last = int(math.ceil((n - (pages - 1) * per_page) / float(cols)))
    w, h = cell_size
    blank = work / 'blank.png'
    run([FFMPEG, '-hide_banner', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=0x1e1e1e:s=%dx%d' % (w, h),
         '-frames:v', '1', '-y', str(blank)])
    outputs = []
    for p in range(pages):
        page_cells = cells[p * per_page:(p + 1) * per_page]
        rows = rows_per_page if p < pages - 1 else rows_last
        total = cols * rows
        for k in range(total):
            src = page_cells[k] if k < len(page_cells) else blank
            shutil.copyfile(str(src), str(work / ('c%04d.png' % k)))
        name = str(out_pattern).replace('%02d', '%02d' % (p + 1)) if '%02d' in str(out_pattern) else str(out_pattern)
        run([FFMPEG, '-hide_banner', '-v', 'error', '-framerate', '1', '-i', str(work / 'c%04d.png'),
             '-vf', 'tile=%dx%d:margin=10:padding=10:color=0x101010' % (cols, rows),
             '-frames:v', '1', '-q:v', '3', '-y', name])
        outputs.append(name)
        for f in work.glob('c*.png'):
            f.unlink()
    shutil.rmtree(work)
    return outputs


def default_layout(info):
    vi = info.get('video') or {}
    vertical = (vi.get('height') or 0) > (vi.get('width') or 1)
    return {'vertical': vertical, 'cols': 6 if vertical else 4, 'rows': 3 if vertical else 5,
            'cell': 270 if vertical else 480, 'strip_cell': 200 if vertical else 280}


def cell_dims(info, cell_w):
    vi = info.get('video') or {}
    w, h = vi.get('width') or 16, vi.get('height') or 9
    ch = int(round(cell_w * h / float(w)))
    return cell_w, ch + (ch % 2)


def sheet(video, info, out_dir, times_labels, cols=None, cell=None, guides=None, name='sheet'):
    lay = default_layout(info)
    cols = cols or lay['cols']
    cell = cell or lay['cell']
    out_dir = Path(out_dir)
    cells_dir = out_dir / ('.cells-' + name)
    if cells_dir.exists():
        shutil.rmtree(cells_dir)
    cells_dir.mkdir(parents=True)
    vi = info.get('video') or {}
    fps, duration = vi.get('fps') or 30.0, info.get('duration') or 0.0
    font = find_label_font()
    index = []
    cells = []
    for k, (t, label) in enumerate(times_labels):
        p = cells_dir / ('f%04d.png' % k)
        actual = extract_frame(video, t, p, fps, duration, width=cell, guides=guides,
                               label='%s  %.2fs' % (label, t) if label else '%.2fs' % t, font=font,
                               vsize=(vi.get('width'), vi.get('height')))
        cells.append(p)
        index.append({'cell': k + 1, 'time': round(actual, 3), 'label': label})
    rows = default_layout(info)['rows']
    pages = tile_images(cells, out_dir / (name + '-%02d.jpg'), cols, rows, cell_dims(info, cell))
    shutil.rmtree(cells_dir)
    (out_dir / (name + '-index.json')).write_text(json.dumps({'pages': [Path(p).name for p in pages],
                                                             'columns': cols, 'cells': index},
                                                            ensure_ascii=False, indent=2), encoding='utf-8')
    return pages, index


def sheet_times(info, timeline=None, every=None, times=None):
    duration = info.get('duration') or 0.0
    if times:
        return [(t, None) for t in times]
    if timeline and not every:
        out = []
        for s in timeline['shots']:
            dur = s['end'] - s['start']
            out.append((s['start'] + dur * 0.5, s['id'] + ' mid'))
            if dur > 1.2:
                out.append((s['end'] - 0.45, s['id'] + ' end'))
        return out
    step = every or max(1.0, round(duration / 24.0, 1))
    n = int(duration // step) + 1
    return [(min(i * step + step / 2.0, max(0.0, duration - 0.05)), None) for i in range(n) if i * step < duration]


def strips(video, info, out_dir, cuts, shots=None, entries=True, cell=None):
    lay = default_layout(info)
    cell = cell or lay['strip_cell']
    vi = info.get('video') or {}
    fps, duration = vi.get('fps') or 30.0, info.get('duration') or 0.0
    scale = fps / 30.0
    font = find_label_font()
    made = {'cuts': [], 'entries': []}
    out_dir = Path(out_dir)
    cut_offsets = [-10, -4, -1, 0, 1, 4, 10]
    for i, cut in enumerate(cuts):
        before = shots[i]['id'] if shots and i < len(shots) else 'a'
        after = shots[i + 1]['id'] if shots and i + 1 < len(shots) else 'b'
        work = out_dir / 'cuts' / ('.cut%02d' % (i + 1))
        work.mkdir(parents=True, exist_ok=True)
        cells = []
        for k, off in enumerate(cut_offsets):
            frames = int(round(off * scale))
            t = cut + frames / fps
            label = 'CUT' if frames == 0 else '%+df' % frames
            p = work / ('c%02d.png' % k)
            extract_frame(video, t, p, fps, duration, width=cell, label=label, font=font)
            cells.append(p)
        name = out_dir / 'cuts' / ('cut-%02d-%s-%s.jpg' % (i + 1, safe(before), safe(after)))
        tile_images(cells, name, len(cells), 1, cell_dims(info, cell))
        shutil.rmtree(work)
        made['cuts'].append({'file': str(name.relative_to(out_dir)), 'time': cut, 'from': before, 'to': after})
    if entries and shots:
        entry_offsets = [0.0, 0.1, 0.2, 0.33, 0.5, 0.8, 1.2]
        for i, s in enumerate(shots):
            dur = s['end'] - s['start']
            offs = [o for o in entry_offsets if o < dur - 0.05] or [0.0]
            work = out_dir / 'entries' / ('.e%02d' % (i + 1))
            work.mkdir(parents=True, exist_ok=True)
            cells = []
            for k, off in enumerate(offs):
                p = work / ('c%02d.png' % k)
                extract_frame(video, s['start'] + off, p, fps, duration, width=cell, label='+%.2fs' % off, font=font)
                cells.append(p)
            name = out_dir / 'entries' / ('entry-%02d-%s.jpg' % (i + 1, safe(s['id'])))
            tile_images(cells, name, len(cells), 1, cell_dims(info, cell))
            shutil.rmtree(work)
            made['entries'].append({'file': str(name.relative_to(out_dir)), 'shot': s['id'], 'time': s['start']})
    return made


def safe(text):
    return re.sub(r'[^A-Za-z0-9._-]+', '_', str(text))[:40] or 'x'


# ---------------------------------------------------------------- report

LEVEL_ZH = {'error': '阻断', 'warn': '注意', 'info': '提示'}


def write_report(out_dir, info, det, sheets, strip_info, timeline):
    out_dir = Path(out_dir)
    checks = list(info.get('checks') or []) + list((det or {}).get('checks') or [])
    report = {'probe': info, 'detect': det, 'sheets': sheets, 'strips': strip_info, 'checks': checks}
    (out_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    vi = info.get('video') or {}
    au = info.get('audio') or {}
    loud = (det or {}).get('loudness') or {}
    lines = ['# 视频检查报告', '', '文件：`%s`' % info.get('file'), '',
             '| 项目 | 值 |', '|---|---|',
             '| 时长 | %.2f s |' % (info.get('duration') or 0),
             '| 画面 | %sx%s，%s fps，%s，%s |' % (vi.get('width'), vi.get('height'), vi.get('fps'), vi.get('codec'),
                                            vi.get('pix_fmt')),
             '| 音频 | %s |' % ('%s，%s Hz，%s 声道' % (au.get('codec'), au.get('sample_rate'), au.get('channels'))
                               if au else '无'),
             '| 响度 | %s |' % ('%.1f LUFS，真峰值 %s dBTP，LRA %s LU' % (
                 loud['integrated'], loud.get('true_peak'), loud.get('lra')) if loud else '未测'),
             '| 码率 / 大小 | %s kbps / %s MB |' % (info.get('bitrate_kbps'), info.get('size_mb')), '']
    if checks:
        lines += ['## 自动检测', '']
        for level in ('error', 'warn', 'info'):
            for c in [x for x in checks if x['level'] == level]:
                where = ''
                if 'time' in c:
                    where = ' @%.2fs' % c['time'] + ('（%s）' % c['shot'] if c.get('shot') else '')
                lines.append('- **%s**%s：%s' % (LEVEL_ZH[level], where, c['msg']))
        lines.append('')
    else:
        lines += ['## 自动检测', '', '没有发现可计算的问题。', '']
    lines += ['## 需要实际查看的图', '']
    for p in sheets or []:
        lines.append('- 联系表 `%s`：构图、主次、风格一致、文字大小与安全区' % Path(p).name)
    if strip_info:
        if strip_info.get('cuts'):
            lines.append('- 切点帧条 `cuts/`（%d 张）：切点在运动中、方向一致、无空帧白闪' % len(strip_info['cuts']))
        if strip_info.get('entries'):
            lines.append('- 入场帧条 `entries/`（%d 张）：入场顺序、错峰、缓出' % len(strip_info['entries']))
    lines += ['', '检测通过不代表画面好看；逐张看图，把发现写进 qa/review.md。', '']
    (out_dir / 'report.md').write_text('\n'.join(lines), encoding='utf-8')
    return report


def print_checks(checks):
    if not checks:
        print('没有发现可计算的问题。')
        return
    for level in ('error', 'warn', 'info'):
        for c in [x for x in checks if x['level'] == level]:
            where = (' @%.2fs' % c['time'] + (' %s' % c['shot'] if c.get('shot') else '')) if 'time' in c else ''
            print('[%s]%s %s' % (LEVEL_ZH[level], where, c['msg']))


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--ffmpeg')
    parser.add_argument('--ffprobe')
    sub = parser.add_subparsers(dest='cmd', required=True)

    def common(p, out_required=True):
        p.add_argument('video')
        p.add_argument('--out', required=out_required, help='输出目录')
        p.add_argument('--timeline', help='timeline.json（或分镜 storyboard.json）')
        return p

    p = sub.add_parser('probe', help='编码、帧率、时长、faststart 检查')
    p.add_argument('video')
    p.add_argument('--json', action='store_true')
    p = common(sub.add_parser('detect', help='黑帧、闪帧、静止、静音、响度、切点比对'), out_required=False)
    p.add_argument('--target-lufs', type=float, default=-14.0)
    p.add_argument('--true-peak', type=float, default=-1.0)
    p = common(sub.add_parser('sheet', help='联系表'))
    p.add_argument('--every', type=float, help='每隔几秒取一帧')
    p.add_argument('--times', help='逗号分隔的时间点')
    p.add_argument('--cols', type=int)
    p.add_argument('--cell', type=int, help='每格宽度（像素）')
    p.add_argument('--guides', choices=['vertical', 'title-safe'])
    p = common(sub.add_parser('strips', help='切点与入场帧条'))
    p.add_argument('--cuts', help='逗号分隔的切点时间（没有时间线时）')
    p.add_argument('--no-entries', action='store_true')
    p.add_argument('--cell', type=int)
    p = common(sub.add_parser('frames', help='原尺寸单帧'))
    p.add_argument('--times', required=True)
    p.add_argument('--guides', choices=['vertical', 'title-safe'])
    p = common(sub.add_parser('all', help='probe + detect + sheet + strips + 报告'))
    p.add_argument('--every', type=float)
    p.add_argument('--guides', choices=['vertical', 'title-safe'])
    p.add_argument('--target-lufs', type=float, default=-14.0)
    p.add_argument('--true-peak', type=float, default=-1.0)
    p.add_argument('--no-entries', action='store_true')

    args = parser.parse_args()
    resolve_tools(args)
    video = Path(args.video)
    if not video.is_file():
        sys.exit('找不到视频：%s' % video)
    info = probe(video)
    if args.cmd == 'probe':
        if args.json:
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            vi = info.get('video') or {}
            print('%s：%.2f s，%sx%s，%s fps，%s %s，音频 %s' % (
                video.name, info['duration'], vi.get('width'), vi.get('height'), vi.get('fps'), vi.get('codec'),
                vi.get('pix_fmt'), (info.get('audio') or {}).get('codec') or '无'))
            print_checks(info['checks'])
        return

    timeline = load_timeline(args.timeline) if getattr(args, 'timeline', None) else None
    out = Path(args.out) if getattr(args, 'out', None) else None
    if out:
        out.mkdir(parents=True, exist_ok=True)

    try:
        if args.cmd == 'detect':
            work = Path(tempfile.mkdtemp(prefix='vqa-'))
            det = detect(video, info, timeline, work, args.target_lufs, args.true_peak)
            shutil.rmtree(work, ignore_errors=True)
            if out:
                (out / 'detect.json').write_text(json.dumps(det, ensure_ascii=False, indent=2), encoding='utf-8')
            if det.get('loudness'):
                ld = det['loudness']
                print('响度 %.1f LUFS，真峰值 %s dBTP，LRA %s LU' % (ld['integrated'], ld['true_peak'], ld['lra']))
            print('检测到 %d 处画面突变、%d 段静止、%d 段黑场、%d 处疑似闪帧、%d 段静音。' % (
                len(det['scene_changes']), len(det['freeze']), len(det['black']), len(det['flashes']),
                len(det['silence'])))
            print_checks(det['checks'])
        elif args.cmd == 'sheet':
            pts = sheet_times(info, timeline, args.every, parse_times(args.times))
            pages, _ = sheet(video, info, out, pts, args.cols, args.cell, args.guides)
            print('联系表：' + '、'.join(str(Path(p)) for p in pages))
        elif args.cmd == 'strips':
            cuts = parse_times(args.cuts) if args.cuts else (timeline['cuts'] if timeline else [])
            if not cuts and not timeline:
                sys.exit('需要 --timeline 或 --cuts。')
            made = strips(video, info, out, cuts, timeline['shots'] if timeline else None,
                          not args.no_entries, args.cell)
            print('切点帧条 %d 张（%s），入场帧条 %d 张（%s）。' % (
                len(made['cuts']), out / 'cuts', len(made['entries']), out / 'entries'))
        elif args.cmd == 'frames':
            vi = info.get('video') or {}
            for t in parse_times(args.times):
                p = out / ('frame-%08.3f.png' % t)
                extract_frame(video, t, p, vi.get('fps') or 30.0, info['duration'], guides=args.guides,
                              vsize=(vi.get('width'), vi.get('height')))
                print(p)
        elif args.cmd == 'all':
            work = out / '.detect'
            det = detect(video, info, timeline, work, args.target_lufs, args.true_peak)
            shutil.rmtree(work, ignore_errors=True)
            pts = sheet_times(info, timeline, args.every)
            pages, _ = sheet(video, info, out, pts, guides=args.guides)
            made = None
            if timeline and len(timeline['shots']) > 0:
                made = strips(video, info, out, timeline['cuts'], timeline['shots'], not args.no_entries)
            write_report(out, info, det, [str(Path(p).name) for p in pages], made, timeline)
            print('报告：%s' % (out / 'report.md'))
            print('联系表：%s' % '、'.join(Path(p).name for p in pages))
            if made:
                print('切点帧条 %d 张，入场帧条 %d 张。' % (len(made['cuts']), len(made['entries'])))
            print_checks(list(info['checks']) + list(det['checks']))
    except RuntimeError as exc:
        sys.exit(str(exc))


if __name__ == '__main__':
    main()
