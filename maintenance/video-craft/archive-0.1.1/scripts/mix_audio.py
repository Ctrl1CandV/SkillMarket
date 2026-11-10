#!/usr/bin/env python3
"""Mix voice-over, music and sound effects under a rendered video, normalize loudness, and mux.

  mix_audio.py --video draft.mp4 --out final.mp4 [--timeline timeline.json] [--vo FILE[@SECONDS] ...]
               [--music FILE] [--music-under 10] [--no-duck] [--sfx-dir DIR] [--sfx SECONDS:FILE[:GAIN] ...]
               [--keep-video-audio] [--target-lufs -14] [--true-peak -1] [--reencode auto|always|never]

- Voice-over clips are placed at `vo.start` from timeline.json (made by storyboard.py) and leveled to the
  same loudness, so segments made at different times sound consistent.
- Music is looped to the video length, set `--music-under` LU below the voice, faded, and ducked under
  speech with a sidechain compressor.
- Sound effects come from timeline `sfx` entries (`name` looked up in --sfx-dir) or --sfx; `gain` is the
  effect's peak in dB relative to a typical voice peak (default -14).
- The final mix gets two-pass EBU R128 normalization (default -14 LUFS, -1 dBTP), then is muxed with
  the video: copied when it is already H.264/yuv420p, otherwise re-encoded for upload.

Needs ffmpeg and ffprobe. Standard library only.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

FFMPEG = 'ffmpeg'
FFPROBE = 'ffprobe'
AUDIO_EXTS = ('.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg', '.opus')
VO_REF = -16.0       # LUFS each voice clip is leveled to before mixing
VOICE_PEAK = -3.0    # dBFS a leveled voice typically peaks at; sfx gain is relative to this


def run(cmd, check=True):
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if check and proc.returncode != 0:
        tail = '\n'.join(proc.stderr.strip().splitlines()[-15:])
        sys.exit('ffmpeg 失败（%d）：\n%s' % (proc.returncode, tail))
    return proc


def resolve_tools(args):
    global FFMPEG, FFPROBE
    FFMPEG = args.ffmpeg or os.environ.get('VIDEO_CRAFT_FFMPEG') or shutil.which('ffmpeg')
    FFPROBE = args.ffprobe or os.environ.get('VIDEO_CRAFT_FFPROBE') or shutil.which('ffprobe')
    if not FFMPEG or not FFPROBE:
        sys.exit('需要 ffmpeg 和 ffprobe。运行 doctor.py 查看安装建议，或用 --ffmpeg/--ffprobe 指定路径。')


def probe(path):
    out = run([FFPROBE, '-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', str(path)]).stdout
    data = json.loads(out or '{}')
    streams = data.get('streams') or []
    v = next((s for s in streams if s.get('codec_type') == 'video'), None)
    a = next((s for s in streams if s.get('codec_type') == 'audio'), None)
    fps = 0.0
    if v and v.get('r_frame_rate') and '/' in v['r_frame_rate']:
        n, d = v['r_frame_rate'].split('/')
        fps = float(n) / float(d) if float(d) else 0.0
    return {'duration': float((data.get('format') or {}).get('duration') or 0), 'video': v, 'audio': a, 'fps': fps}


def loudness(path):
    """Integrated loudness (LUFS) and true peak (dBFS) via ebur128; None when unmeasurable."""
    log = run([FFMPEG, '-hide_banner', '-nostats', '-i', str(path), '-map', '0:a:0',
               '-af', 'ebur128=peak=true', '-f', 'null', '-'], check=False).stderr
    summary = log[log.rfind('Summary:'):] if 'Summary:' in log else ''
    m_i = re.search(r'I:\s+([-\d.]+) LUFS', summary)
    m_tp = re.search(r'Peak:\s+([-\d.]+) dBFS', summary)
    i = float(m_i.group(1)) if m_i else None
    if i is not None and i <= -69.0:
        i = None
    return i, (float(m_tp.group(1)) if m_tp else None)


def peak_db(path):
    log = run([FFMPEG, '-hide_banner', '-nostats', '-i', str(path), '-map', '0:a:0',
               '-af', 'volumedetect', '-f', 'null', '-'], check=False).stderr
    m = re.search(r'max_volume:\s*([-\d.]+) dB', log)
    return float(m.group(1)) if m else None


def amix_has_normalize():
    out = run([FFMPEG, '-hide_banner', '-h', 'filter=amix'], check=False).stdout
    return 'normalize' in out


def find_by_name(directory, name):
    if not directory or not name:
        return None
    p = Path(directory) / name
    if p.suffix and p.is_file():
        return p
    for ext in AUDIO_EXTS:
        q = Path(directory) / (str(name) + ext)
        if q.is_file():
            return q
    return None


def collect(args, video_info):
    """Return a list of sources: dict(kind, path, start, gain_db)."""
    sources = []
    tl_dir = Path(args.timeline).resolve().parent if args.timeline else None
    timeline = None
    if args.timeline:
        with open(args.timeline, encoding='utf-8') as fh:
            timeline = json.load(fh)
        for shot in timeline.get('shots') or []:
            vo = shot.get('vo') or {}
            if vo.get('file') and not vo.get('estimated'):
                p = Path(vo['file'])
                p = p if p.is_absolute() else tl_dir / p
                if not p.is_file():
                    sys.exit('找不到配音文件：%s（镜头 %s）' % (p, shot.get('id')))
                sources.append({'kind': 'vo', 'path': p, 'start': float(vo['start']), 'label': shot.get('id')})
            elif vo.get('estimated') and vo.get('text'):
                print('  - %s：时间线里的配音是估算值，没有文件可混入。' % shot.get('id'))
            for fx in shot.get('sfx') or []:
                p = find_by_name(args.sfx_dir, fx.get('name')) or find_by_name(args.sfx_dir, fx.get('file'))
                if not p:
                    print('  - %s：没有在 %s 找到音效 %s，已跳过。' % (shot.get('id'), args.sfx_dir or '(未指定 --sfx-dir)',
                                                       fx.get('name') or fx.get('file')))
                    continue
                sources.append({'kind': 'sfx', 'path': p, 'start': float(fx['at']),
                                'gain_db': float(fx.get('gain', -14.0)), 'label': fx.get('name')})
    for item in args.vo or []:
        path, _, start = item.partition('@')
        sources.append({'kind': 'vo', 'path': Path(path), 'start': float(start or 0), 'label': Path(path).stem})
    for item in args.sfx or []:
        parts = item.split(':')
        if len(parts) < 2:
            sys.exit('--sfx 格式应为 秒:文件[:增益]，收到 %s' % item)
        gain = -14.0
        if len(parts) >= 3:
            try:
                gain = float(parts[-1])
                parts = parts[:-1]
            except ValueError:
                pass
        sources.append({'kind': 'sfx', 'path': Path(':'.join(parts[1:])), 'start': float(parts[0]),
                        'gain_db': gain, 'label': Path(parts[1]).stem})
    if args.music:
        sources.append({'kind': 'music', 'path': Path(args.music), 'start': float(args.music_start),
                        'label': Path(args.music).stem})
    if args.keep_video_audio and video_info['audio']:
        sources.append({'kind': 'orig', 'path': Path(args.video), 'start': 0.0, 'label': 'video'})
    for s in sources:
        if not s['path'].is_file():
            sys.exit('找不到音频文件：%s' % s['path'])
    return sources


def plan_gains(sources, args):
    """Measure inputs and decide per-source gain in dB."""
    has_vo = any(s['kind'] == 'vo' for s in sources)
    report = []
    for s in sources:
        if s['kind'] in ('vo', 'orig'):
            i, _ = loudness(s['path'])
            ref = VO_REF + (args.video_audio_gain if s['kind'] == 'orig' else 0.0)
            s['gain_db'] = round(ref - i, 2) if i is not None else 0.0
            report.append('%s %s：%s LUFS → 增益 %+.1f dB' % ('配音' if s['kind'] == 'vo' else '原声', s['label'],
                                                         '%.1f' % i if i is not None else '无法测量', s['gain_db']))
        elif s['kind'] == 'music':
            i, _ = loudness(s['path'])
            under = args.music_under if has_vo else 0.0
            s['gain_db'] = round((VO_REF - under) - i, 2) if i is not None else -18.0
            report.append('音乐 %s：%s LUFS → 增益 %+.1f dB（比人声低 %.0f LU%s）' % (
                s['label'], '%.1f' % i if i is not None else '无法测量', s['gain_db'], under,
                '，说话时再自动压低' if has_vo and not args.no_duck else ''))
        elif s['kind'] == 'sfx':
            pk = peak_db(s['path'])
            target = VOICE_PEAK + s['gain_db']
            s['gain_db'] = round(target - pk, 2) if pk is not None else s['gain_db']
            report.append('音效 %s @%.2fs：峰值 %s dB → 增益 %+.1f dB' % (
                s['label'], s['start'], '%.1f' % pk if pk is not None else '?', s['gain_db']))
    return report


def build_graph(sources, duration, args, normalize_opt):
    """Return (input_args, filter_lines, final_label)."""
    inputs, lines = [], []
    labels = {'vo': [], 'sfx': [], 'music': [], 'orig': []}
    idx = 1
    for n, s in enumerate(sources):
        if s['kind'] == 'music':
            inputs += ['-stream_loop', '-1', '-i', str(s['path'])]
        elif s['kind'] == 'orig':
            inputs += ['-i', str(s['path'])]
        else:
            inputs += ['-i', str(s['path'])]
        delay = int(round(max(0.0, s['start']) * 1000))
        chain = ['aresample=48000', 'aformat=sample_fmts=fltp:channel_layouts=stereo',
                 'volume=%.2fdB' % s.get('gain_db', 0.0)]
        if s['kind'] == 'music':
            length = max(0.1, duration - s['start'])
            fade_out = min(args.music_fade_out, length / 3.0)
            chain += ['atrim=0:%.3f' % length, 'asetpts=PTS-STARTPTS',
                      'afade=t=in:st=0:d=%.3f' % min(args.music_fade_in, length / 3.0),
                      'afade=t=out:st=%.3f:d=%.3f' % (length - fade_out, fade_out)]
        if delay:
            chain.append('adelay=%d|%d' % (delay, delay))
        label = 'a%d' % n
        lines.append('[%d:a:0]%s[%s]' % (idx, ','.join(chain), label))
        labels[s['kind']].append(label)
        idx += 1

    def mix(names, out):
        if len(names) == 1:
            lines.append('[%s]anull[%s]' % (names[0], out))
        elif normalize_opt:
            lines.append('%samix=inputs=%d:duration=longest:normalize=0[%s]' % (
                ''.join('[%s]' % x for x in names), len(names), out))
        else:  # older ffmpeg divides by the input count; undo that
            lines.append('%samix=inputs=%d:duration=longest,volume=%d[%s]' % (
                ''.join('[%s]' % x for x in names), len(names), len(names), out))

    finals = []
    if labels['vo']:
        mix(labels['vo'], 'vobus')
    if labels['music']:
        mix(labels['music'], 'musicbus')
        if labels['vo'] and not args.no_duck:
            lines.append('[vobus]asplit=2[vomain][vosc]')
            lines.append('[musicbus][vosc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[musicd]')
            finals += ['vomain', 'musicd']
        else:
            finals += (['vobus'] if labels['vo'] else []) + ['musicbus']
    elif labels['vo']:
        finals.append('vobus')
    finals += labels['sfx'] + labels['orig']
    mix(finals, 'mixraw')
    lines.append('[mixraw]apad,atrim=0:%.3f,asetpts=PTS-STARTPTS[mix]' % duration)
    return inputs, lines, 'mix'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--video', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--timeline', help='storyboard.py 生成的 timeline.json')
    parser.add_argument('--vo', action='append', help='整段配音文件，可写 文件@起始秒；可重复')
    parser.add_argument('--music')
    parser.add_argument('--music-start', type=float, default=0.0)
    parser.add_argument('--music-under', type=float, default=10.0, help='音乐比人声低多少 LU（默认 10）')
    parser.add_argument('--music-fade-in', type=float, default=1.0)
    parser.add_argument('--music-fade-out', type=float, default=2.0)
    parser.add_argument('--no-duck', action='store_true', help='说话时不自动压低音乐')
    parser.add_argument('--sfx-dir', help='音效目录，按时间线 sfx 的 name 查找')
    parser.add_argument('--sfx', action='append', help='秒:文件[:增益]，可重复')
    parser.add_argument('--keep-video-audio', action='store_true', help='保留视频原有音轨并参与混音')
    parser.add_argument('--video-audio-gain', type=float, default=0.0)
    parser.add_argument('--target-lufs', type=float, default=-14.0)
    parser.add_argument('--true-peak', type=float, default=-1.0)
    parser.add_argument('--no-normalize', action='store_true')
    parser.add_argument('--reencode', choices=['auto', 'always', 'never'], default='auto')
    parser.add_argument('--crf', type=int, default=18)
    parser.add_argument('--preset', default='slow')
    parser.add_argument('--audio-bitrate', default='192k')
    parser.add_argument('--ffmpeg')
    parser.add_argument('--ffprobe')
    args = parser.parse_args()
    resolve_tools(args)

    video = Path(args.video)
    if not video.is_file():
        sys.exit('找不到视频：%s' % video)
    vinfo = probe(video)
    if not vinfo['video']:
        sys.exit('%s 里没有视频流。' % video)
    duration = vinfo['duration']
    sources = collect(args, vinfo)
    if not sources:
        sys.exit('没有任何音频输入：给出 --timeline（含配音文件）、--vo、--music、--sfx 或 --keep-video-audio。')

    print('测量输入响度……')
    for line in plan_gains(sources, args):
        print('  ' + line)
    late = [s for s in sources if s['start'] >= duration]
    for s in late:
        print('  - %s 从 %.2f s 开始，超出视频长度 %.2f s，将被截掉。' % (s['label'], s['start'], duration))

    inputs, lines, final = build_graph(sources, duration, args, amix_has_normalize())
    base_cmd = [FFMPEG, '-hide_banner', '-nostats', '-i', str(video)] + inputs

    post = ''
    if not args.no_normalize:
        lra = 11.0
        graph = ';'.join(lines + ['[%s]loudnorm=I=%.1f:TP=%.1f:LRA=%.1f:print_format=json[o]' % (
            final, args.target_lufs, args.true_peak, lra)])
        log = run(base_cmd + ['-filter_complex', graph, '-map', '[o]', '-f', 'null', '-']).stderr
        blocks = re.findall(r'\{[^{}]*"input_i"[^{}]*\}', log)
        if not blocks:
            sys.exit('无法读取响度测量结果。')
        m = json.loads(blocks[-1])
        if float(m['input_i']) <= -69:
            sys.exit('混音几乎是静音，检查输入文件和时间。')
        lra = max(11.0, min(20.0, math.ceil(float(m['input_lra'])) + 1))
        post = (',loudnorm=I=%.1f:TP=%.1f:LRA=%.1f:measured_I=%s:measured_TP=%s:measured_LRA=%s:'
                'measured_thresh=%s:offset=%s:linear=true:print_format=summary' % (
                    args.target_lufs, args.true_peak, lra, m['input_i'], m['input_tp'], m['input_lra'],
                    m['input_thresh'], m['target_offset']))
    graph = ';'.join(lines + ['[%s]anull%s,aresample=48000[o]' % (final, post)])

    v = vinfo['video']
    copy_ok = (v.get('codec_name') == 'h264' and v.get('pix_fmt') == 'yuv420p'
               and str(args.out).lower().endswith(('.mp4', '.mov', '.m4v')))
    reencode = args.reencode == 'always' or (args.reencode == 'auto' and not copy_ok)
    if args.reencode == 'never' and not copy_ok:
        print('  - 视频不是 H.264/yuv420p，按 --reencode never 直接复制，部分平台可能无法播放。')
    vargs = ['-c:v', 'copy']
    if reencode:
        fps = vinfo['fps'] or 30.0
        vargs = ['-c:v', 'libx264', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-crf', str(args.crf),
                 '-preset', args.preset, '-r', '%g' % fps, '-g', str(int(round(fps * 2))),
                 '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709']
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.resolve() == video.resolve():
        sys.exit('输出不能覆盖输入视频。')
    cmd = base_cmd + ['-filter_complex', graph, '-map', '0:v:0', '-map', '[o]'] + vargs + [
        '-c:a', 'aac', '-b:a', args.audio_bitrate, '-ar', '48000', '-t', '%.3f' % duration,
        '-movflags', '+faststart', '-y', str(out)]
    print('合成%s……' % ('并重新编码视频' if reencode else '（视频流直接复制）'))
    run(cmd)
    i, tp = loudness(out)
    print('已写入 %s：%.2f s，响度 %s LUFS，真峰值 %s dBTP。' % (
        out, probe(out)['duration'], '%.1f' % i if i is not None else '?', '%.1f' % tp if tp is not None else '?'))


if __name__ == '__main__':
    main()
