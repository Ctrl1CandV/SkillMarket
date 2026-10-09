#!/usr/bin/env python3
"""Check evidence freshness/completeness. Does not perform or certify visual judgement."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def page_numbers(items):
    if not isinstance(items, list) or any(not isinstance(p, dict) or type(p.get('page')) is not int for p in items):
        return None
    return [p['page'] for p in items]


def object_record(value, label):
    if not isinstance(value, dict):
        raise ValueError(label + ' must be a JSON object')
    return value


def record_list(value, label):
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(label + ' must be a list of JSON objects')
    return value


def finalize(deck, audit_path, render_path, review_path):
    digest = sha256(deck)
    audit, render, review = [json.loads(Path(p).read_text(encoding='utf-8')) for p in (audit_path, render_path, review_path)]
    failures = []
    for label, evidence in (('audit', audit), ('render', render), ('review', review)):
        object_record(evidence, label)
        if evidence.get('deck_sha256') != digest:
            failures.append(label + ' does not match the current PPTX hash')
    findings = record_list(audit.get('findings', []), 'Audit findings')
    if audit.get('structural_pass') is not True or any(f.get('severity') == 'error' for f in findings):
        failures.append('Structural audit has unresolved errors')
    count = audit.get('slide_count')
    expected = list(range(1, count + 1)) if type(count) is int and count > 0 else []
    render_pages = record_list(render.get('pages', []), 'Rendered pages')
    review_pages = record_list(review.get('pages', []), 'Reviewed pages')
    if not expected or page_numbers(render_pages) != expected:
        failures.append('Rendered page list differs from slide count/order')
    review_numbers = page_numbers(review_pages)
    if not expected or review_numbers is None or sorted(review_numbers) != expected:
        failures.append('Review must cover every slide exactly once')
    audit_pages = record_list(audit.get('pages', []), 'Audited pages')
    if not expected or page_numbers(audit_pages) != expected:
        failures.append('Audit page list differs from slide count/order')
    if any(not isinstance(p.get('animation'), dict)
           or type(p['animation'].get('has_timing')) is not bool
           or type(p['animation'].get('has_transition')) is not bool for p in audit_pages):
        failures.append('Audit animation metadata is missing; rerun the current audit')
    for item in review_pages:
        if item.get('status') != 'pass' or not isinstance(item.get('summary'), str) or not item['summary'].strip():
            failures.append(f'Slide {item.get("page")} has no passing review with a summary')
    content = object_record(review.get('content_review', {}), 'Content review')
    if content.get('status') != 'pass' or not isinstance(content.get('summary'), str) or not content['summary'].strip():
        failures.append('Content review is missing or not passing')
    animated_pages = [p.get('page') for p in audit_pages
                      if isinstance(p.get('animation'), dict)
                      and (p['animation'].get('has_timing') is True or p['animation'].get('has_transition') is True)]
    if animated_pages:
        playback = object_record(review.get('animation_review', {}), 'Animation review')
        covered = playback.get('pages', [])
        if (playback.get('status') != 'pass' or playback.get('method') != 'slideshow'
                or not isinstance(playback.get('player'), str) or not playback['player'].strip()
                or not isinstance(playback.get('summary'), str) or not playback['summary'].strip()
                or not isinstance(covered, list) or any(type(p) is not int for p in covered)
                or any(type(p) is not int for p in animated_pages)
                or sorted(covered) != sorted(animated_pages)):
            failures.append('Animation requires recorded slideshow playback review; static renders or import checks are insufficient')
    base = Path(render_path).resolve().parent
    for item in [object_record(render.get('pdf', {}), 'Rendered PDF')] + render_pages:
        filename = item.get('file')
        if not isinstance(filename, str) or Path(filename).name != filename:
            failures.append('Render manifest contains an invalid artifact filename')
            continue
        path = base / filename
        if not path.is_file() or sha256(path) != item.get('sha256'):
            failures.append('Rendered artifact is missing or changed: ' + filename)
    return {'complete': not failures, 'deck': str(Path(deck).resolve()), 'deck_sha256': digest,
            'slide_count': count, 'failures': failures,
            'animated_pages': animated_pages,
            'audit_warnings': [f for f in findings if f.get('severity') == 'warning'],
            'scope': 'Evidence continuity and recorded review coverage only; not an automatic quality score or independent human approval.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('deck', type=Path)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--render', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = finalize(args.deck, args.audit, args.render, args.review)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['complete'] else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
