#!/usr/bin/env python3
"""Add native click-to-reveal steps to PPTX, preserving all unmodified package parts."""
import argparse
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
from xml.parsers import expat
import zipfile

from audit_pptx import NS, relationships

P = NS['p']


def tag(name):
    return '{' + P + '}' + name


def slide_parts(package):
    root = ET.fromstring(package.read('ppt/presentation.xml'))
    rels = relationships(package, 'ppt/presentation.xml')
    result = []
    for slide in root.findall('p:sldIdLst/p:sldId', NS):
        relation = rels[slide.get('{' + NS['r'] + '}id')]
        if relation['external']:
            raise ValueError('External slide references are unsupported')
        result.append(relation['target'])
    if not result or len(set(result)) != len(result):
        raise ValueError('Presentation must contain distinct slide parts')
    return result


def objects(root):
    result = []
    tree = root.find('p:cSld/p:spTree', NS)
    if tree is None:
        return result
    for node in tree:
        kind = node.tag.rsplit('}', 1)[-1]
        if kind not in ('sp', 'pic', 'graphicFrame', 'grpSp', 'cxnSp'):
            continue
        identity = node.find('.//p:cNvPr', NS)
        if identity is not None:
            result.append({'id': int(identity.get('id')), 'name': identity.get('name', ''),
                           'kind': kind, 'text': ' '.join(t.text or '' for t in node.findall('.//a:t', NS))[:200]})
    return result


def inventory(source):
    with zipfile.ZipFile(source) as package:
        return {'slides': [{'page': page, 'objects': objects(ET.fromstring(package.read(part)))}
                           for page, part in enumerate(slide_parts(package), 1)]}


def timing(steps, effect, duration):
    ET.register_namespace('p', P)
    result = ET.Element(tag('timing'))
    next_id = 0

    def child(parent, name, **attrs):
        return ET.SubElement(parent, tag(name), {k: str(v) for k, v in attrs.items()})

    def node(parent, **attrs):
        nonlocal next_id
        next_id += 1
        return child(parent, 'cTn', id=next_id, **attrs)

    def start(parent, delay):
        child(child(parent, 'stCondLst'), 'cond', delay=delay)

    root = node(child(child(result, 'tnLst'), 'par'), dur='indefinite', restart='never', nodeType='tmRoot')
    sequence = child(child(root, 'childTnLst'), 'seq', concurrent=1, nextAc='seek')
    main = node(sequence, dur='indefinite', nodeType='mainSeq')
    main_children = child(main, 'childTnLst')
    for step in steps:
        waiting = node(child(main_children, 'par'), fill='hold')
        start(waiting, 'indefinite')
        active = node(child(child(waiting, 'childTnLst'), 'par'), fill='hold')
        start(active, 0)
        effects = child(active, 'childTnLst')
        for index, shape_id in enumerate(step):
            leaf = node(child(effects, 'par'), presetID=1 if effect == 'appear' else 10,
                        presetClass='entr', presetSubtype=0, fill='hold', grpId=0,
                        nodeType='clickEffect' if index == 0 else 'withEffect')
            start(leaf, 0)
            behaviors = child(leaf, 'childTnLst')
            setting = child(behaviors, 'set')
            behavior = child(setting, 'cBhvr')
            start(node(behavior, dur=1, fill='hold'), 0)
            child(child(behavior, 'tgtEl'), 'spTgt', spid=shape_id)
            child(child(behavior, 'attrNameLst'), 'attrName').text = 'style.visibility'
            child(child(setting, 'to'), 'strVal', val='visible')
            if effect == 'fade':
                fade = child(behaviors, 'animEffect', transition='in', filter='fade')
                behavior = child(fade, 'cBhvr')
                node(behavior, dur=duration)
                child(child(behavior, 'tgtEl'), 'spTgt', spid=shape_id)
    for name, event in [('prevCondLst', 'onPrev'), ('nextCondLst', 'onNext')]:
        condition = child(child(sequence, name), 'cond', evt=event, delay=0)
        child(child(condition, 'tgtEl'), 'sldTgt')
    builds = child(result, 'bldLst')
    for step in steps:
        for shape_id in step:
            child(builds, 'bldP', spid=shape_id, grpId=0)
    return ET.tostring(result, encoding='utf-8')


def insert_timing(raw, fragment):
    """Inject into the original UTF-8 XML without rewriting namespace declarations."""
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        raise ValueError('UTF-16 slide XML is unsupported; use a UTF-8 authoring route')
    parser = expat.ParserCreate(namespace_separator='}')
    depth, insertion = 0, None

    def begin(name, attrs):
        nonlocal depth, insertion
        if depth == 1 and name == P + '}extLst':
            insertion = parser.CurrentByteIndex
        depth += 1

    def end(name):
        nonlocal depth, insertion
        if depth == 1 and name == P + '}sld' and insertion is None:
            insertion = parser.CurrentByteIndex
        depth -= 1

    parser.StartElementHandler, parser.EndElementHandler = begin, end
    parser.Parse(raw, True)
    if insertion is None:
        raise ValueError('Cannot find the slide insertion point')
    changed = raw[:insertion] + fragment + raw[insertion:]
    ET.fromstring(changed)
    return changed


def animate(source, output, plan):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or output.exists():
        raise ValueError('Output must be a new file, different from the source')
    if not isinstance(plan, dict):
        raise ValueError('Plan must be a JSON object')
    slides = plan.get('slides')
    if not isinstance(slides, list) or not slides:
        raise ValueError('Plan must contain a nonempty slides list')
    changed, summary = {}, []
    with zipfile.ZipFile(source) as package:
        names = package.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Input contains duplicate ZIP parts')
        bad = package.testzip()
        if bad:
            raise ValueError('Input contains a corrupt ZIP part: ' + bad)
        parts, seen = slide_parts(package), set()
        for entry in slides:
            if not isinstance(entry, dict):
                raise ValueError('Each planned slide must be a JSON object')
            page, steps = entry.get('page'), entry.get('steps')
            if type(page) is not int or not 1 <= page <= len(parts) or page in seen:
                raise ValueError('Plan page must exist and be unique')
            seen.add(page)
            if not isinstance(steps, list) or not steps or any(not isinstance(s, list) or not s for s in steps):
                raise ValueError('Each slide must contain nonempty click-step lists')
            targets = [item for step in steps for item in step]
            if any(type(item) is not int for item in targets) or len(targets) != len(set(targets)):
                raise ValueError('Object IDs must be integers and appear in only one step')
            effect, duration = entry.get('effect', 'appear'), entry.get('duration_ms', 300)
            if effect not in ('appear', 'fade') or type(duration) is not int or not 50 <= duration <= 2000:
                raise ValueError('Use appear/fade and duration_ms between 50 and 2000')
            part = parts[page - 1]
            raw = package.read(part)
            root = ET.fromstring(raw)
            if root.findall('.//p:timing', NS):
                raise ValueError(f'Slide {page} already has animation timing; preserve or edit it in its authoring tool')
            found = objects(root)
            allowed = {item['id'] for item in found}
            if len(allowed) != len(found):
                raise ValueError(f'Slide {page} has duplicate object IDs; fix in the source before adding animation')
            if not set(targets) <= allowed:
                raise ValueError(f'Slide {page} has unknown or non-top-level target IDs: {set(targets) - allowed}')
            changed[part] = insert_timing(raw, timing(steps, effect, duration))
            summary.append({'page': page, 'click_steps': len(steps), 'animated_objects': len(targets), 'effect': effect})
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, 'x') as result:
            for item in package.infolist():
                result.writestr(item, changed.get(item.filename, package.read(item.filename)))
    return {'output': str(output), 'slides': summary, 'note': 'Native animation written; validate in the intended slideshow player.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('deck', type=Path)
    parser.add_argument('--list', action='store_true', help='List top-level IDs, names and text for an explicit reveal plan')
    parser.add_argument('--plan', type=Path)
    parser.add_argument('-o', '--output', type=Path)
    args = parser.parse_args()
    try:
        if args.list:
            result = inventory(args.deck)
        else:
            if not args.plan or not args.output:
                parser.error('--plan and --output are required unless --list is used')
            result = animate(args.deck, args.output, json.loads(args.plan.read_text(encoding='utf-8')))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError, zipfile.BadZipFile, expat.ExpatError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
