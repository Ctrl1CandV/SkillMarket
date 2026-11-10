#!/usr/bin/env python3
"""Check a video storyboard, build a voice-over driven timeline, and draft subtitles.

  storyboard.py check    STORYBOARD [--json] [--rate N]
  storyboard.py timeline STORYBOARD --out timeline.json [--audio-dir DIR] [--lead S] [--tail S] [--end-hold S]
  storyboard.py srt      STORYBOARD --timeline timeline.json --out subtitles.srt [--max-chars N] [--keep-punct]

Standard library only. Audio durations come from ffprobe when it is on PATH;
plain .wav files are also measured without it. Nothing is rendered or uploaded.
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
import wave

CJK = re.compile('[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]')
LATIN_WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")
NUMBER = re.compile(r'\d+(?:[.,]\d+)*')
EN_WORD = re.compile(r"[A-Za-z0-9]+(?:['’.\-][A-Za-z0-9]+)*")
AUDIO_EXTS = ('.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg', '.opus')
SAFE_ID = re.compile(r'^[A-Za-z0-9._-]+$')
SOFT_TRANSITIONS = {'crossfade', 'fade', 'dissolve', 'cross-dissolve'}

DEFAULTS = {
    'zh': {'rate': 4.0, 'read': 7.0, 'onscreen_max': 24, 'item_max': 12, 'sub_chars': 16, 'sub_cps': 9.0},
    'en': {'rate': 2.5, 'read': 3.0, 'onscreen_max': 16, 'item_max': 7, 'sub_chars': 42, 'sub_cps': 17.0},
}


# ---------------------------------------------------------------- helpers

def load_json(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        sys.exit('无法解析 JSON：%s（第 %d 行第 %d 列）：%s' % (path, exc.lineno, exc.colno, exc.msg))
    except OSError as exc:
        sys.exit('无法读取 %s：%s' % (path, exc))


def detect_language(sb):
    lang = sb.get('language')
    if lang:
        return 'zh' if str(lang).lower().startswith(('zh', 'cn', 'ja', 'ko')) else 'en'
    text = ''.join(str(s.get('vo') or '') + ''.join(onscreen_items(s)) for s in sb.get('shots', []))
    return 'zh' if CJK.search(text) else 'en'


def onscreen_items(shot):
    value = shot.get('onscreen') or []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value if v]


def spoken_units(text, lang):
    """Rough count of spoken units: characters for zh, words for en."""
    text = text or ''
    if lang == 'zh':
        cjk = len(CJK.findall(text))
        latin = sum(max(1.0, len(w) / 3.0) for w in LATIN_WORD.findall(text))
        digits = sum(len(re.sub(r'\D', '', n)) for n in NUMBER.findall(text))
        return cjk + latin + digits
    return float(len(EN_WORD.findall(text)))


def reading_units(text, lang):
    """Units a viewer reads: CJK characters plus one per Latin word or number (zh); words (en)."""
    text = text or ''
    if lang == 'zh':
        return float(len(CJK.findall(text)) + len(LATIN_WORD.findall(text)) + len(NUMBER.findall(text)))
    return float(len(EN_WORD.findall(text)))


def display_width(text):
    """Line width in full-width character cells (ASCII counts as half)."""
    return sum(0.5 if ord(ch) < 0x2E80 else 1.0 for ch in text)


def line_width(text, lang):
    """Subtitle line width: full-width cells for zh, characters for en."""
    return display_width(text) if lang == 'zh' else float(len(text))


def normalized(text):
    return re.sub(r'[\s\W_]+', '', text or '').lower()


def fmt_s(value):
    return '%.2f' % value


def get_format(sb):
    fmt = sb.get('format') or {}
    return (int(fmt.get('width') or 1920), int(fmt.get('height') or 1080), float(fmt.get('fps') or 30))


def num(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def media_duration(path):
    """Duration in seconds via ffprobe, or the wave module for .wav files."""
    path = str(path)
    probe = shutil.which('ffprobe')
    if probe:
        try:
            out = subprocess.run([probe, '-v', 'error', '-show_entries', 'format=duration',
                                  '-of', 'default=noprint_wrappers=1:nokey=1', path],
                                 capture_output=True, text=True, timeout=60)
            value = float(out.stdout.strip().splitlines()[0])
            if value > 0:
                return value
        except (ValueError, IndexError, subprocess.SubprocessError, OSError):
            pass
    if path.lower().endswith('.wav'):
        try:
            with wave.open(path, 'rb') as wav:
                return wav.getnframes() / float(wav.getframerate())
        except (wave.Error, EOFError, OSError):
            return None
    return None


def find_vo_file(shot, base_dir, audio_dir):
    explicit = shot.get('vo_file')
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = base_dir / p
        return p if p.is_file() else None
    if audio_dir and shot.get('id'):
        for ext in AUDIO_EXTS:
            p = Path(audio_dir) / (str(shot['id']) + ext)
            if p.is_file():
                return p
    return None


def rel_posix(path, start):
    try:
        return Path(os.path.relpath(str(path), str(start))).as_posix()
    except ValueError:  # different drive on Windows
        return Path(path).resolve().as_posix()


# ---------------------------------------------------------------- check

def check(sb, rate=None):
    issues = []

    def add(level, shot, code, msg):
        issues.append({'level': level, 'shot': shot, 'code': code, 'msg': msg})

    lang = detect_language(sb)
    d = DEFAULTS[lang]
    rate = rate or d['rate']
    shots = sb.get('shots')
    if not isinstance(shots, list) or not shots:
        add('error', None, 'no-shots', '没有 shots 数组，或数组为空。')
        return {'language': lang, 'shots': [], 'issues': issues, 'total': 0.0}

    fmt = sb.get('format') or {}
    if not fmt.get('width') or not fmt.get('height') or not fmt.get('fps'):
        add('warn', None, 'format', 'format 缺少 width/height/fps，按 1920×1080、30 fps 计算。')
    width, height, fps = get_format(sb)
    vertical = height > width

    seen = set()
    rows = []
    t = 0.0
    for i, shot in enumerate(shots):
        sid = str(shot.get('id') or '#%d' % (i + 1))
        if not shot.get('id'):
            add('error', sid, 'id', '镜头缺少 id。')
        elif sid in seen:
            add('error', sid, 'id', 'id 重复。')
        elif not SAFE_ID.match(sid):
            add('warn', sid, 'id', 'id 含空格或非 ASCII 字符；它会用作文件名，建议改成 s03-exchange 这类英文短名。')
        seen.add(sid)

        missing = [k for k in ('purpose', 'hero', 'layout') if not shot.get(k)]
        if missing:
            add('warn', sid, 'fields', '缺少 %s：先想清楚这一镜的作用、主体和构图。' % '、'.join(missing))

        vo = str(shot.get('vo') or '')
        est_vo = spoken_units(vo, lang) / rate if vo else 0.0
        duration = num(shot.get('duration'))
        if duration is None and not vo:
            add('error', sid, 'duration', '没有 duration，也没有旁白可以推算时长。')
        if duration is not None and duration <= 0:
            add('error', sid, 'duration', 'duration 必须大于 0。')
            duration = None
        planned = duration if duration is not None else (est_vo + 0.55 if vo else 0.0)

        if vo and duration is not None:
            need = est_vo + 0.55
            if need > duration + 0.05:
                add('warn', sid, 'vo-fit',
                    '旁白按 %.1f 字/秒约需 %.1f s（含前后留白），镜头计划 %.1f s。配音实测后时间线会自动延长；'
                    '要保持时长就删减旁白。' % (rate, need, duration) if lang == 'zh' else
                    'Narration needs about %.1f s at %.1f words/s; the shot is planned at %.1f s.' % (need, rate, duration))
            elif duration >= 6 and est_vo < 0.35 * duration:
                add('info', sid, 'vo-sparse', '旁白只占约 %d%% 的时长，确认这段时间画面有内容在推进（写 beats）。'
                    % round(100 * est_vo / duration))

        items = onscreen_items(shot)
        screen_units = sum(reading_units(x, lang) for x in items)
        if screen_units > d['onscreen_max']:
            add('warn', sid, 'onscreen-amount', '屏幕文字约 %d 字，超过 %d：完整句子交给字幕，屏幕只留关键词和数字。'
                % (screen_units, d['onscreen_max']))
        for item in items:
            if reading_units(item, lang) > d['item_max']:
                add('info', sid, 'onscreen-item', '“%s”超过 %d 字，考虑缩成关键词。' % (item, d['item_max']))
            if vo and reading_units(item, lang) >= 8 and normalized(item) and normalized(item) in normalized(vo):
                add('info', sid, 'redundant', '“%s”与旁白整句重复；字幕已经承担全文，屏幕文字只放要点。' % item)
        if items and not vo and planned:
            need_read = screen_units / d['read'] + 0.5
            if need_read > planned + 0.05:
                add('warn', sid, 'read-time', '屏幕文字约需 %.1f s 读完，镜头只有 %.1f s。' % (need_read, planned))

        role = str(shot.get('role') or '')
        if planned and planned < 0.8 and role not in ('beat', 'flash'):
            add('warn', sid, 'too-short', '镜头不到 0.8 s，除非是节拍镜头（role: beat），观众来不及看清。')
        long_limit = 6.0 if vertical else 10.0
        if planned and planned > long_limit and not shot.get('beats'):
            add('warn', sid, 'long-static', '镜头 %.1f s 但没有写 beats；每 2–4 s 要有一个可见变化。' % planned)
        for key in ('beats', 'sfx'):
            for b in shot.get(key) or []:
                at = num(b.get('at')) if isinstance(b, dict) else None
                if at is None:
                    add('warn', sid, key, '%s 条目缺少数值 at。' % key)
                elif planned and at > planned:
                    add('warn', sid, key, '%s 的 at=%.2f 超出镜头时长 %.2f。' % (key, at, planned))

        rows.append({'id': sid, 'start': t, 'end': t + planned, 'duration': planned,
                     'vo_units': spoken_units(vo, lang), 'vo_est': est_vo,
                     'screen_units': screen_units, 'layout': shot.get('layout'),
                     'shot_size': shot.get('shot_size'), 'transition': shot.get('transition'),
                     'carry_out': bool(shot.get('carry_out'))})
        t += planned

    # variety of layouts
    run = 1
    for i in range(1, len(rows) + 1):
        same = i < len(rows) and rows[i]['layout'] and rows[i]['layout'] == rows[i - 1]['layout']
        if same:
            run += 1
            continue
        if run >= 3:
            ids = [r['id'] for r in rows[i - run:i]]
            add('warn', ids[0], 'layout-repeat', '连续 %d 个镜头都是 %s 构图（%s），像在翻页；换景别或构图。'
                % (run, rows[i - 1]['layout'], '、'.join(ids)))
        run = 1
    sizes = [r['shot_size'] for r in rows if r['shot_size']]
    if len(rows) >= 4 and sizes and len(set(sizes)) == 1 and len(sizes) == len(rows):
        add('info', None, 'shot-size', '所有镜头都是 %s 景别；全景、中景、特写交替更有层次。' % sizes[0])

    # transitions
    declared = sb.get('transitions') or []
    used = [r['transition'] for r in rows[:-1] if r['transition']]
    if declared:
        for name in sorted(set(used) - set(declared)):
            add('warn', None, 'transition', '转场 %s 不在顶层 transitions 词汇里。' % name)
    if len(set(used)) > 3:
        add('warn', None, 'transition', '用了 %d 种转场（%s）；全片 2–3 种并反复使用更统一。'
            % (len(set(used)), '、'.join(sorted(set(used)))))
    soft = [u for u in used if str(u).lower() in SOFT_TRANSITIONS]
    if used and len(soft) > max(1, len(rows) // 3):
        add('info', None, 'transition', '交叉淡化用了 %d 次；它适合时间流逝和情绪段落，普通切点用运动中硬切或共享元素。'
            % len(soft))

    no_carry = [r['id'] for r in rows[:-1] if not r['carry_out']]
    if no_carry:
        add('info', None, 'carry', '%d 个切点没有写 carry_out（%s）：写清什么跨过切点、朝哪个方向。'
            % (len(no_carry), '、'.join(no_carry)))

    if rows and rows[-1]['duration'] and rows[-1]['duration'] < 1.5:
        add('warn', rows[-1]['id'], 'end-hold', '结尾镜头不到 1.5 s，观众来不及读完收尾画面。')
    if vertical and rows and rows[0]['duration'] > 4:
        add('info', rows[0]['id'], 'hook', '竖屏开头镜头超过 4 s，确认前 2 s 已经给出钩子。')

    total = t
    target = num(sb.get('target_duration'))
    if target and abs(total - target) / target > 0.15:
        add('warn', None, 'total', '计划总时长 %.1f s，与目标 %.1f s 相差超过 15%%。' % (total, target))

    return {'language': lang, 'rate': rate, 'format': {'width': width, 'height': height, 'fps': fps},
            'total': total, 'shots': rows, 'issues': issues}


def print_check(sb, result):
    rows = result['shots']
    fmt = result.get('format', {})
    print('%s  %sx%s @ %s fps  语言 %s' % (sb.get('title') or '(未命名)', fmt.get('width'), fmt.get('height'),
                                         fmt.get('fps'), result['language']))
    if rows:
        avg = result['total'] / len(rows)
        print('总时长 %.1f s，%d 个镜头，平均每镜 %.1f s\n' % (result['total'], len(rows), avg))
        print('%-20s %13s %6s %6s %8s %6s  %s' % ('镜头', '起止(s)', '时长', '旁白', '旁白约需', '屏幕字', '构图'))
        for r in rows:
            print('%-20s %6s-%6s %6s %6d %8s %6d  %s' % (
                r['id'][:20], fmt_s(r['start']), fmt_s(r['end']), fmt_s(r['duration']),
                round(r['vo_units']), fmt_s(r['vo_est']) if r['vo_units'] else '-', round(r['screen_units']),
                r['layout'] or '-'))
    labels = {'error': '错误', 'warn': '注意', 'info': '提示'}
    for level in ('error', 'warn', 'info'):
        items = [x for x in result['issues'] if x['level'] == level]
        if items:
            print('\n[%s] %d 项' % (labels[level], len(items)))
            for x in items:
                print('  - %s%s' % ('%s：' % x['shot'] if x['shot'] else '', x['msg']))
    if not result['issues']:
        print('\n没有发现可计算的问题。画面、衔接和节奏仍要在样帧和草稿上看。')


# ---------------------------------------------------------------- timeline

def build_timeline(sb, sb_path, out_path, audio_dir=None, lead=0.2, tail=0.35, end_hold=1.5, rate=None):
    lang = detect_language(sb)
    rate = rate or DEFAULTS[lang]['rate']
    width, height, fps = get_format(sb)
    base_dir = Path(sb_path).resolve().parent
    out_dir = Path(out_path).resolve().parent
    shots = sb.get('shots') or []
    if not shots:
        sys.exit('分镜里没有镜头。')
    warnings = []
    t = 0.0
    out_shots = []
    for i, shot in enumerate(shots):
        sid = str(shot.get('id') or 'shot%02d' % (i + 1))
        is_last = i == len(shots) - 1
        vo_text = str(shot.get('vo') or '')
        vo_path = find_vo_file(shot, base_dir, audio_dir)
        vo_dur = media_duration(vo_path) if vo_path else None
        estimated = False
        if vo_path and vo_dur is None:
            warnings.append('%s：无法读取 %s 的时长（需要 ffprobe 或 .wav）。' % (sid, vo_path))
        if vo_text and vo_dur is None:
            vo_dur = spoken_units(vo_text, lang) / rate
            estimated = True
            if audio_dir or shot.get('vo_file'):
                warnings.append('%s：没有找到配音文件，按语速估算 %.2f s。' % (sid, vo_dur))
        shot_lead = num(shot.get('vo_lead'))
        shot_lead = lead if shot_lead is None else shot_lead
        shot_tail = num(shot.get('vo_tail'))
        shot_tail = (max(tail, end_hold) if is_last else tail) if shot_tail is None else shot_tail
        planned = num(shot.get('duration')) or 0.0
        need = shot_lead + vo_dur + shot_tail if vo_dur else 0.0
        if is_last and not vo_dur:
            need = max(need, end_hold if planned == 0 else 0.0)
        duration = max(planned, need)
        if duration <= 0:
            sys.exit('%s：没有时长，也没有配音。' % sid)
        if vo_dur and planned and need > planned + 1e-6:
            warnings.append('%s：配音需要 %.2f s，计划 %.2f s，已延长。' % (sid, need, planned))
        start, end = t, t + duration
        f0, f1 = int(round(start * fps)), int(round(end * fps))
        item = {
            'id': sid, 'index': i, 'start': round(start, 4), 'end': round(end, 4),
            'duration': round(end - start, 4), 'from': f0, 'durationInFrames': f1 - f0,
            'role': shot.get('role'), 'layout': shot.get('layout'), 'transition': shot.get('transition'),
            'carry_out': shot.get('carry_out'),
        }
        if vo_dur:
            vs = start + shot_lead
            item['vo'] = {'text': vo_text, 'start': round(vs, 4), 'duration': round(vo_dur, 4),
                          'start_frame': int(round(vs * fps)), 'estimated': estimated,
                          'file': rel_posix(vo_path, out_dir) if vo_path and not estimated else None}
        for key in ('beats', 'sfx'):
            entries = []
            for b in shot.get(key) or []:
                at = num(b.get('at')) if isinstance(b, dict) else None
                if at is None:
                    continue
                e = dict(b)
                e['at'] = round(start + at, 4)
                e['frame'] = int(round((start + at) * fps))
                entries.append(e)
            if entries:
                item[key] = entries
        out_shots.append(item)
        t = end
    total_frames = int(round(t * fps))
    timeline = {
        'version': 1, 'source': rel_posix(Path(sb_path).resolve(), out_dir), 'title': sb.get('title'),
        'language': lang, 'fps': fps, 'width': width, 'height': height,
        'duration': round(t, 4), 'duration_frames': total_frames,
        'cuts': [s['end'] for s in out_shots[:-1]], 'shots': out_shots,
    }
    return timeline, warnings


# ---------------------------------------------------------------- subtitles

CLAUSE_SPLIT_ZH = re.compile(r'(?<=[，。！？；：、…!?;:,])')
CLAUSE_SPLIT_EN = re.compile(r'(?<=[.!?;:,])\s+')
TRAILING = '，。、；：,.;:'
INTERNAL = re.compile(r'[，、；：,;:]')


def split_long(text, max_width, lang='zh'):
    """Split a clause wider than max_width into balanced pieces without breaking Latin words."""
    tokens = re.findall(r'[A-Za-z0-9]+(?:[.\'’-][A-Za-z0-9]+)*\s*|\S\s*|\s+', text)
    total = line_width(text, lang)
    parts = max(2, int(math.ceil(total / max_width)))
    limit = min(max_width, total / parts * 1.15)
    pieces, cur = [], ''
    for tok in tokens:
        if cur and line_width((cur + tok).rstrip(), lang) > limit:
            pieces.append(cur)
            cur = tok.lstrip()
        else:
            cur += tok
    if cur:
        pieces.append(cur)
    return [p.strip() for p in pieces if p.strip()]


def split_cues(text, max_width, lang):
    """Return [(cue_text, forced)] where forced marks a break placed without punctuation."""
    text = re.sub(r'\s+', ' ', text or '').strip()
    if not text:
        return []
    if lang == 'zh':
        clauses = [c.strip() for c in CLAUSE_SPLIT_ZH.split(text) if c.strip()]
    else:
        clauses = [c.strip() for c in CLAUSE_SPLIT_EN.split(text) if c.strip()]
    cues, cur, cur_forced = [], '', False
    joiner = '' if lang == 'zh' else ' '
    for clause in clauses:
        long_clause = line_width(clause, lang) > max_width
        pieces = split_long(clause, max_width, lang) if long_clause else [clause]
        for k, piece in enumerate(pieces):
            forced = long_clause and k < len(pieces) - 1
            candidate = (cur + joiner + piece) if cur else piece
            if cur and line_width(candidate, lang) > max_width:
                cues.append((cur, cur_forced))
                cur, cur_forced = piece, forced
            else:
                cur, cur_forced = candidate, forced
            if lang == 'zh' and cur and cur[-1] in '。！？!?…':
                cues.append((cur, False))
                cur, cur_forced = '', False
    if cur:
        cues.append((cur, cur_forced))
    return cues


def clean_cue(text, lang):
    text = text.strip().rstrip(TRAILING).strip()
    if lang == 'zh':
        text = INTERNAL.sub(' ', text)
        text = re.sub(r'\s{2,}', ' ', text).strip()
    return text


def srt_time(seconds):
    ms = int(round(max(0.0, seconds) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return '%02d:%02d:%02d,%03d' % (h, m, s, ms)


def build_subtitles(timeline, max_chars=None, keep_punct=False):
    lang = timeline.get('language') or 'zh'
    d = DEFAULTS.get(lang, DEFAULTS['zh'])
    default_chars = d['sub_chars']
    if lang == 'zh' and (timeline.get('height') or 0) > (timeline.get('width') or 0):
        default_chars = 14  # vertical frames fit fewer characters at a phone-legible size
    max_width = float(max_chars or default_chars)
    fps = float(timeline.get('fps') or 30)
    gap = 2.0 / fps
    cues, warnings = [], []
    shots = timeline.get('shots') or []
    for idx, shot in enumerate(shots):
        vo = shot.get('vo')
        if not vo or not vo.get('text'):
            continue
        if vo.get('estimated'):
            warnings.append('%s：配音时长是估算值，字幕时间只能作草稿。' % shot['id'])
        split = split_cues(vo['text'], max_width, lang)
        parts = [p for p, _ in split]
        weights = [max(1.0, spoken_units(p, lang)) for p in parts]
        span_start, span = float(vo['start']), float(vo['duration'])
        shot_end = float(shot['end'])
        acc = 0.0
        total_w = sum(weights)
        for j, (part, w) in enumerate(zip(parts, weights)):
            forced = split[j][1]
            start = span_start + span * acc / total_w
            acc += w
            end = span_start + span * acc / total_w
            last_in_shot = j == len(parts) - 1
            if not last_in_shot:
                end -= gap
            else:
                end = min(max(end, start + 0.83), shot_end - gap)
            text = part if keep_punct else clean_cue(part, lang)
            if not text:
                continue
            dur = end - start
            width = line_width(text, lang)
            cue = {'index': len(cues) + 1, 'shot': shot['id'], 'start': round(start, 3),
                   'end': round(end, 3), 'text': text}
            cues.append(cue)
            if forced:
                warnings.append('#%d（%s）在没有标点的位置断行：“%s”，检查是否拆开了词语，必要时改写旁白。'
                                % (cue['index'], shot['id'], text))
            if width > max_width + 0.01:
                warnings.append('#%d（%s）%.1f 字宽，超过每行 %d。' % (cue['index'], shot['id'], width, max_width))
            if dur < 0.83:
                warnings.append('#%d（%s）只显示 %.2f s，少于 0.83 s；与相邻字幕合并或放慢配音。'
                                % (cue['index'], shot['id'], dur))
            if dur > 7.0:
                warnings.append('#%d（%s）显示 %.1f s，超过 7 s。' % (cue['index'], shot['id'], dur))
            cps = (width if lang == 'zh' else len(text)) / max(dur, 0.01)
            if cps > d['sub_cps']:
                warnings.append('#%d（%s）阅读速度 %.1f 字/秒，超过 %.0f。' % (cue['index'], shot['id'], cps, d['sub_cps']))
    return cues, warnings


def write_srt(cues, path):
    lines = []
    for cue in cues:
        lines += [str(cue['index']), '%s --> %s' % (srt_time(cue['start']), srt_time(cue['end'])), cue['text'], '']
    Path(path).write_text('\n'.join(lines), encoding='utf-8')


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('check', help='检查分镜的时长、语速、文字量、构图变化和衔接')
    p.add_argument('storyboard')
    p.add_argument('--json', action='store_true', help='输出机器可读的 JSON')
    p.add_argument('--rate', type=float, help='旁白语速：中文字/秒（默认 4.0）或英文词/秒（默认 2.5）')

    p = sub.add_parser('timeline', help='按配音实测时长生成 timeline.json')
    p.add_argument('storyboard')
    p.add_argument('--out', required=True)
    p.add_argument('--audio-dir', help='按镜头 id 命名的配音目录，如 video/audio/vo')
    p.add_argument('--lead', type=float, default=0.2, help='镜头开始到配音开始的秒数（默认 0.2）')
    p.add_argument('--tail', type=float, default=0.35, help='配音结束到切点的留白（默认 0.35）')
    p.add_argument('--end-hold', type=float, default=1.5, help='最后一镜配音后的停留（默认 1.5）')
    p.add_argument('--rate', type=float, help='没有配音文件时估算用的语速')

    p = sub.add_parser('srt', help='从时间线里的配音生成 SRT 和同名 JSON 字幕')
    p.add_argument('storyboard', nargs='?', help='可省略；字幕取自 --timeline，时间线缺语言信息时用分镜判断')
    p.add_argument('--timeline', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--max-chars', type=float, help='每行最大字宽（中文横屏默认 16、竖屏 14，英文默认 42 个字符）')
    p.add_argument('--keep-punct', action='store_true', help='保留原标点（默认去掉行末逗号句号，句中逗号改为空格）')

    args = parser.parse_args()

    if args.cmd == 'check':
        sb = load_json(args.storyboard)
        result = check(sb, args.rate)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_check(sb, result)
        sys.exit(1 if any(x['level'] == 'error' for x in result['issues']) else 0)

    if args.cmd == 'timeline':
        sb = load_json(args.storyboard)
        timeline, warnings = build_timeline(sb, args.storyboard, args.out, args.audio_dir,
                                            args.lead, args.tail, args.end_hold, args.rate)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        measured = sum(1 for s in timeline['shots'] if s.get('vo') and not s['vo']['estimated'])
        estimated = sum(1 for s in timeline['shots'] if s.get('vo') and s['vo']['estimated'])
        print('已写入 %s：%d 个镜头，总时长 %.2f s（%d 帧 @ %s fps）；配音实测 %d 段，估算 %d 段。' % (
            args.out, len(timeline['shots']), timeline['duration'], timeline['duration_frames'],
            ('%g' % timeline['fps']), measured, estimated))
        for w in warnings:
            print('  - ' + w)
        return

    if args.cmd == 'srt':
        timeline = load_json(args.timeline)
        if not timeline.get('language') and args.storyboard:
            timeline['language'] = detect_language(load_json(args.storyboard))
        cues, warnings = build_subtitles(timeline, args.max_chars, args.keep_punct)
        if not cues:
            sys.exit('时间线里没有带文字的配音，无法生成字幕。')
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        write_srt(cues, out)
        out.with_suffix('.json').write_text(json.dumps({'cues': cues}, ensure_ascii=False, indent=2) + '\n',
                                            encoding='utf-8')
        print('已写入 %s 和 %s：%d 条字幕。' % (out, out.with_suffix('.json'), len(cues)))
        for w in warnings:
            print('  - ' + w)


if __name__ == '__main__':
    main()
