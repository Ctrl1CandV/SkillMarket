#!/usr/bin/env python3
"""Inspect PPTX structure, text, notes, media and geometric risks. Not a visual judge."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import posixpath
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart'}
REL = '{http://schemas.openxmlformats.org/package/2006/relationships}'
EMU = 914400
IDENTITY = (1, 0, 0, 1, 0, 0)
CJK = re.compile('[　-〿㐀-鿿豈-﫿＀-￯]')
EAST_ASIAN = ('zh', 'ja', 'ko')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def multiply(m, n):
    a, b, c, d, e, f = m
    g, h, i, j, k, l = n
    return (a*g+c*h, b*g+d*h, a*i+c*j, b*i+d*j, a*k+c*l+e, b*k+d*l+f)


def point(m, x, y):
    a, b, c, d, e, f = m
    return (a*x+c*y+e, b*x+d*y+f)


def translate(x, y):
    return (1, 0, 0, 1, x, y)


def rotate_flip(xfrm, cx, cy):
    angle = math.radians(float(xfrm.get('rot', 0)) / 60000)
    cosine, sine = math.cos(angle), math.sin(angle)
    fx = -1 if xfrm.get('flipH') in ('1', 'true') else 1
    fy = -1 if xfrm.get('flipV') in ('1', 'true') else 1
    transform = (cosine*fx, sine*fx, -sine*fy, cosine*fy, 0, 0)
    return multiply(multiply(translate(cx, cy), transform), translate(-cx, -cy))


def values(xfrm, name, keys):
    node = xfrm.find('a:' + name, NS)
    if node is None:
        return None
    return tuple(float(node.get(k, 0)) for k in keys)


def geometry(xfrm, parent):
    if xfrm is None:
        return None
    off, ext = values(xfrm, 'off', ('x', 'y')), values(xfrm, 'ext', ('cx', 'cy'))
    if off is None or ext is None:
        return None
    x, y = off
    w, h = ext
    matrix = multiply(parent, rotate_flip(xfrm, x+w/2, y+h/2))
    corners = [point(matrix, xx, yy) for xx, yy in ((x,y),(x+w,y),(x,y+h),(x+w,y+h))]
    return [min(p[0] for p in corners), min(p[1] for p in corners),
            max(p[0] for p in corners), max(p[1] for p in corners)]


def group_matrix(xfrm, parent):
    if xfrm is None:
        return parent
    off, ext = values(xfrm, 'off', ('x','y')), values(xfrm, 'ext', ('cx','cy'))
    child_off = values(xfrm, 'chOff', ('x','y'))
    child_ext = values(xfrm, 'chExt', ('cx','cy'))
    if None in (off, ext, child_off, child_ext) or 0 in child_ext:
        return None
    x, y = off
    w, h = ext
    sx, sy = w/child_ext[0], h/child_ext[1]
    mapped = multiply(translate(x, y), multiply((sx,0,0,sy,0,0), translate(-child_off[0], -child_off[1])))
    rotated = multiply(rotate_flip(xfrm, x+w/2, y+h/2), mapped)
    return multiply(parent, rotated)


def shapes(tree, parent=IDENTITY):
    if tree is None:
        return
    for node in tree:
        kind = node.tag.rsplit('}', 1)[-1]
        if kind == 'grpSp':
            matrix = group_matrix(node.find('p:grpSpPr/a:xfrm', NS), parent)
            if matrix is None:
                yield node, None, 'unmeasured_group'
            else:
                yield from shapes(node, matrix)
        elif kind in ('sp', 'pic', 'graphicFrame', 'cxnSp'):
            xfrm = node.find('p:spPr/a:xfrm', NS)
            if xfrm is None:
                xfrm = node.find('p:xfrm', NS)
            yield node, geometry(xfrm, parent), kind


def relationships(archive, part):
    relpath = posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')
    if relpath not in archive.namelist():
        return {}
    root = ET.fromstring(archive.read(relpath))
    return {r.get('Id'): {
        'target': posixpath.normpath(posixpath.join(posixpath.dirname(part), r.get('Target', ''))).lstrip('/'),
        'type': r.get('Type', ''), 'external': r.get('TargetMode') == 'External'
    } for r in root.findall(REL + 'Relationship')}


def animation_info(slide):
    timing = slide.findall('.//p:timing', NS)
    targets = [node.get('spid') for branch in timing for node in branch.findall('.//p:spTgt', NS)]
    click_effects = [node for branch in timing for node in branch.findall('.//p:cTn', NS)
                     if node.get('nodeType') == 'clickEffect']
    object_ids = []
    for node in slide.iter():
        if node.tag.rsplit('}', 1)[-1] in ('sp', 'pic', 'graphicFrame', 'grpSp', 'cxnSp'):
            identity = node.find('.//p:cNvPr', NS)
            if identity is not None:
                object_ids.append(identity.get('id'))
    time_ids = [[node.get('id') for node in branch.findall('.//p:cTn', NS)] for branch in timing]
    return {'has_timing': bool(timing), 'click_effects': len(click_effects),
            'animated_object_ids': sorted(set(targets)),
            'entrance_effects': len([node for branch in timing for node in branch.findall('.//p:cTn', NS)
                                     if node.get('presetClass') == 'entr']),
            'has_transition': bool(slide.findall('.//p:transition', NS)),
            'invalid_target_ids': sorted(set(targets) - set(object_ids)),
            'duplicate_time_ids': any(len(ids) != len(set(ids)) for ids in time_ids),
            'ambiguous_target_ids': sorted({item for item in targets if object_ids.count(item) > 1})}


def type_scale(slide, canvas_width_in):
    """Characters per explicit run size, scaled to a 13.333 in wide canvas.

    Only run-level sizes are visible here; text that inherits its size from a
    layout or master is counted as unsized and never triggers a warning.
    """
    scale = 13.333 / canvas_width_in if canvas_width_in else 1.0
    by_size, unsized = {}, 0
    for run in slide.findall('.//a:r', NS):
        chars = len(''.join((t.text or '') for t in run.findall('a:t', NS)).strip())
        if not chars:
            continue
        props = run.find('a:rPr', NS)
        size = props.get('sz') if props is not None else None
        if size:
            key = round(int(size) / 100 * scale, 1)
            by_size[key] = by_size.get(key, 0) + chars
        else:
            unsized += chars
    return by_size, unsized


def title_size(page_shapes, canvas_height, scale):
    """Largest explicit run size (4+ characters) in shapes starting in the top quarter: the title band."""
    best = None
    for node, bounds, kind in page_shapes:
        if kind != 'sp' or not bounds or bounds[1] > canvas_height * 0.25:
            continue
        for run in node.findall('.//a:r', NS):
            props = run.find('a:rPr', NS)
            chars = len(''.join(t.text or '' for t in run.findall('a:t', NS)).strip())
            if chars >= 4 and props is not None and props.get('sz'):
                size = round(int(props.get('sz')) / 100 * scale, 1)
                best = size if best is None else max(best, size)
    return best


def default_language(presentation):
    """Deck-wide default run language, if the package declares one."""
    for path in ('p:defaultTextStyle/a:defPPr/a:defRPr', 'p:defaultTextStyle/a:lvl1pPr/a:defRPr'):
        node = presentation.find(path, NS)
        if node is not None and node.get('lang'):
            return node.get('lang')
    return None


def cjk_runs_without_east_asian_language(slide, default_lang):
    """Runs holding Chinese/Japanese/Korean text whose language is not East Asian.

    PowerPoint applies East Asian line breaking only to text tagged with such a
    language; untagged or en-US text may start a line with ，。； or ）.
    """
    count, example = 0, None
    for run in slide.findall('.//a:r', NS):
        if not CJK.search(''.join(t.text or '' for t in run.findall('a:t', NS))):
            continue
        props = run.find('a:rPr', NS)
        lang = (props.get('lang') if props is not None else None) or default_lang
        if not lang or not lang.lower().startswith(EAST_ASIAN):
            count += 1
            example = example or (lang or 'missing')
    return count, example


def audit(path, expected_slides=None, text_warning=900, body_pt=16.0, small_pt=14.0, title_ratio=2.0):
    path = Path(path).resolve()
    findings, pages = [], []
    report = {'deck': str(path), 'deck_sha256': sha256(path), 'pages': pages, 'findings': findings}

    def add(severity, code, message, page=None):
        findings.append({'severity': severity, 'code': code, 'page': page, 'message': message})

    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                add('error', 'duplicate_zip_part', 'Package contains duplicate ZIP member names')
            bad = archive.testzip()
            if bad:
                add('error', 'zip_crc', 'Corrupt ZIP member: ' + bad)
            root = ET.fromstring(archive.read('ppt/presentation.xml'))
            size = root.find('p:sldSz', NS)
            if size is None:
                raise ValueError('Slide canvas dimensions are missing')
            width, height = float(size.get('cx')), float(size.get('cy'))
            if width <= 0 or height <= 0:
                raise ValueError('Invalid slide canvas dimensions')
            report['canvas_inches'] = [round(width/EMU, 4), round(height/EMU, 4)]
            rels = relationships(archive, 'ppt/presentation.xml')
            deck_lang = default_language(root)
            untagged_cjk = {}
            ids = root.findall('p:sldIdLst/p:sldId', NS)
            report['slide_count'] = len(ids)
            if not ids:
                add('error', 'no_slides', 'Presentation has no slides')
            if expected_slides is not None and len(ids) != expected_slides:
                add('error', 'slide_count', f'Expected {expected_slides} slides, found {len(ids)}')
            for number, slide_id in enumerate(ids, 1):
                rid = slide_id.get('{' + NS['r'] + '}id')
                relation = rels.get(rid)
                if not relation or relation['external']:
                    add('error', 'missing_slide_relation', f'Invalid slide relation: {rid}', number)
                    continue
                part = relation['target']
                slide = ET.fromstring(archive.read(part))
                slide_rels = relationships(archive, part)
                page_shapes = list(shapes(slide.find('p:cSld/p:spTree', NS)))
                paragraphs = [''.join(t.text or '' for t in p.findall('.//a:t', NS)) for p in slide.findall('.//a:p', NS)]
                text = '\n'.join(p for p in paragraphs if p)
                image_count = sum(kind == 'pic' for _, _, kind in page_shapes)
                chart_count = len(slide.findall('.//c:chart', NS))
                native_text_shapes = sum(bool(node.findall('.//a:t', NS)) for node, _, _ in page_shapes)
                font_sizes = [int(r.get('sz'))/100 for r in slide.findall('.//a:rPr', NS) if r.get('sz')]
                motion = animation_info(slide)
                by_size, unsized = type_scale(slide, width / EMU)
                sized_chars = sum(by_size.values())
                # Median size by character count: half of the sized text is at or below it.
                main_pt, seen = None, 0
                for key in sorted(by_size):
                    seen += by_size[key]
                    if seen * 2 >= sized_chars:
                        main_pt = key
                        break
                small_chars = sum(v for k, v in by_size.items() if k < small_pt)
                title_pt = title_size(page_shapes, height, 13.333 / (width / EMU))
                untagged, untagged_example = cjk_runs_without_east_asian_language(slide, deck_lang)
                if untagged:
                    untagged_cjk[number] = (untagged, untagged_example)
                if motion['invalid_target_ids'] or motion['ambiguous_target_ids'] or motion['duplicate_time_ids']:
                    add('error', 'invalid_animation_reference', 'Animation has missing/ambiguous shape targets or duplicate timing IDs', number)
                notes_text = ''
                for relation in slide_rels.values():
                    if not relation['external'] and relation['target'] not in archive.namelist():
                        add('error', 'missing_related_part', 'Slide resource missing: ' + relation['target'], number)
                for relation in slide_rels.values():
                    if relation['type'].endswith('/notesSlide') and not relation['external']:
                        notes = ET.fromstring(archive.read(relation['target']))
                        notes_text = '\n'.join(t.text or '' for t in notes.findall('.//a:t', NS))
                pages.append({'page': number, 'part': part, 'text': text, 'text_characters': len(text),
                              'native_text_shapes': native_text_shapes, 'images': image_count,
                              'native_charts': chart_count, 'notes': notes_text,
                              'animation': motion,
                              'explicit_min_font_pt': min(font_sizes) if font_sizes else None,
                              'type_chars_by_pt': {str(k): v for k, v in sorted(by_size.items())},
                              'type_chars_unsized': unsized,
                              'type_median_pt': main_pt,
                              'type_small_chars': small_chars,
                              'title_pt': title_pt,
                              'cjk_runs_without_east_asian_lang': untagged})
                if main_pt is not None and main_pt < body_pt and sized_chars >= 60:
                    add('warning', 'body_type_small',
                        f'Half of the text on this slide is {main_pt:g} pt or smaller (caption size; threshold {body_pt:g} pt '
                        'on a 13.33 in wide canvas). Shorten, split the slide or move explanation to notes instead of shrinking type. '
                        'This is a floor: on dense evidence slides 16-20 pt body text is fine, and hierarchy comes from a larger title, '
                        'not from larger body text', number)
                elif small_chars > max(80, 0.25 * sized_chars):
                    add('warning', 'small_type',
                        f'{small_chars} characters are below {small_pt:g} pt; keep that size for short source lines only', number)
                if main_pt and title_pt and sized_chars >= 60 and title_pt < title_ratio * main_pt:
                    add('warning', 'title_scale_weak',
                        f'Title {title_pt:g} pt is only {title_pt / main_pt:.1f}x the body text ({main_pt:g} pt); below '
                        f'{title_ratio:g}x the hierarchy reads flat in the rendered slide. Enlarge the title (for example '
                        '34-36 pt over 16-18 pt body; shorten a long title) rather than enlarging the body text', number)
                if not page_shapes:
                    add('warning', 'empty_slide', 'No direct slide objects; inspect inherited layout/background', number)
                if len(text) > text_warning:
                    add('warning', 'text_density', 'Dense text; check projection readability or move explanation to notes', number)
                if image_count and len(text.strip()) < 12 and not chart_count:
                    add('warning', 'image_dominant', 'This may be an image-only slide; check the requested editability', number)
                for node, bounds, kind in page_shapes:
                    if kind == 'unmeasured_group':
                        add('warning', 'unmeasured_group', 'Group geometry could not be measured; inspect rendered result', number)
                    if bounds and (bounds[0] < -EMU*0.02 or bounds[1] < -EMU*0.02 or bounds[2] > width+EMU*0.02 or bounds[3] > height+EMU*0.02):
                        add('warning', 'outside_canvas', f'{kind} bounds outside canvas: {[round(v/EMU, 3) for v in bounds]} inches; bleed may be intentional', number)
                for blip in slide.findall('.//a:blip', NS):
                    rid = blip.get('{' + NS['r'] + '}embed')
                    linked = blip.get('{' + NS['r'] + '}link')
                    if rid:
                        relation = slide_rels.get(rid)
                        if not relation or relation['external'] or relation['target'] not in archive.namelist():
                            add('error', 'missing_media', f'Embedded image missing: {rid}', number)
                    if linked:
                        add('warning', 'linked_media', 'Image depends on an external link; embed for offline delivery', number)
            if untagged_cjk:
                runs = sum(n for n, _ in untagged_cjk.values())
                seen = sorted({example for _, example in untagged_cjk.values()})
                add('warning', 'cjk_lang_unset',
                    f'{runs} text runs with Chinese/Japanese/Korean characters on pages {sorted(untagged_cjk)} have no East Asian '
                    f'language (lang: {", ".join(seen)}). PowerPoint then breaks these lines by Western rules and can start a line '
                    'with ，。；：）. Tag the runs lang="zh-CN" (PptxGenJS: text option lang: "zh-CN"; python-pptx: '
                    'run.font._rPr.set("lang", "zh-CN")) and render again')
    except (zipfile.BadZipFile, ET.ParseError, KeyError, ValueError, TypeError) as exc:
        add('error', 'invalid_package', str(exc))
    report['structural_pass'] = not any(f['severity'] == 'error' for f in findings)
    sized = [p for p in pages if p.get('type_median_pt') is not None]
    report['type_summary'] = {
        'reference_canvas_width_in': 13.333, 'body_pt_threshold': body_pt, 'small_pt_threshold': small_pt,
        'title_ratio_threshold': title_ratio,
        'pages_median_pt': {str(p['page']): p['type_median_pt'] for p in sized},
        'pages_below_body_threshold': sorted({f['page'] for f in findings if f['code'] == 'body_type_small'}),
        'note': 'Median run size by character count, scaled to a 13.33 in wide canvas. Inherited sizes and text inside pictures are not measured.'}
    report['limitations'] = 'No OOXML schema validation, slideshow playback test, visual judgement, font fit, factual review or guarantee of full editability.'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('deck', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--expected-slides', type=int)
    parser.add_argument('--text-warning', type=int, default=900)
    parser.add_argument('--body-pt', type=float, default=16.0,
                        help='Warn when half of the text on a slide is set below this size (13.33 in wide canvas)')
    parser.add_argument('--small-pt', type=float, default=14.0,
                        help='Warn when more than a short source line is set below this size')
    parser.add_argument('--title-ratio', type=float, default=2.0,
                        help='Warn when the title band is smaller than this multiple of the median body size')
    args = parser.parse_args()
    try:
        result = audit(args.deck, args.expected_slides, args.text_warning, args.body_pt, args.small_pt, args.title_ratio)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'structural_pass': result['structural_pass'], 'slides': result.get('slide_count'),
                          'errors': sum(f['severity'] == 'error' for f in result['findings']),
                          'warnings': sum(f['severity'] == 'warning' for f in result['findings']),
                          'warning_codes': sorted({f['code'] for f in result['findings'] if f['severity'] == 'warning'}),
                          'pages_below_body_type': result.get('type_summary', {}).get('pages_below_body_threshold', []),
                          'report': str(args.report.resolve())}, ensure_ascii=False))
        return 0 if result['structural_pass'] else 1
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
