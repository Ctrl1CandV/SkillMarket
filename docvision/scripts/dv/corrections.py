"""Append-only, scoped human/host corrections; provider results remain candidates."""
from __future__ import annotations

import copy
import hashlib
import json
import time
import uuid
from pathlib import Path

from . import util
from .base import DocVisionError

SCHEMA = 'docvision.correction/1'
STATES = {'candidate', 'accepted', 'unknown'}


def _hash(value) -> str:
    blob = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


def _strings(values, label: str) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple)) or any(not isinstance(v, str) or not v.strip() for v in values):
        raise DocVisionError(f'{label} must contain non-empty strings.')
    return [v.strip() for v in values]


def _identity(author: str, reviewer: str) -> None:
    if author not in {'human', 'host'}:
        raise DocVisionError('Correction author must be human or host; OCR/API output is not a reviewer.')
    if not isinstance(reviewer, str):
        raise DocVisionError('Correction reviewer must be a name or identifier.')


def _box(value) -> list[float] | None:
    if value is None:
        return None
    try:
        result = [float(v) for v in (value.split(',') if isinstance(value, str) else value)]
    except (TypeError, ValueError):
        raise DocVisionError('Correction bbox must contain four normalized numbers.')
    if len(result) != 4 or not all(0 <= v <= 1 for v in result) or result[0] >= result[2] or result[1] >= result[3]:
        raise DocVisionError('Correction bbox must satisfy 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1.')
    return result


def _body(block: dict) -> str:
    return block.get('markdown') or block.get('text') or ''


def _snapshot(content: dict, *, page: int, block_id: str | None, bbox, scope: str) -> tuple[dict, dict]:
    current = next((p for p in content.get('pages') or [] if p.get('page') == page), None)
    if current is None:
        raise DocVisionError(f'Page {page} is not in this document.')
    block = None
    if block_id:
        block = next((b for b in current.get('blocks') or [] if b.get('id') == block_id), None)
        if block is None:
            raise DocVisionError(f'Block {block_id} is not on page {page}.')
    if scope == 'block':
        if block is None:
            raise DocVisionError('A block correction requires a block id.')
        text, payload = _body(block), block
        bbox = block.get('bbox')
    else:
        # A region is an annotation, not an inferred replacement of overlapping blocks.
        # Fingerprint its page context so a new layout cannot reuse the old interpretation.
        payload = current
        selected = current.get('blocks') or []
        if scope == 'region':
            selected = [b for b in selected if b.get('bbox') and
                        max(b['bbox'][0], bbox[0]) < min(b['bbox'][2], bbox[2]) and
                        max(b['bbox'][1], bbox[1]) < min(b['bbox'][3], bbox[3])]
            text = '\n\n'.join(_body(b) for b in selected)
        else:
            text = current.get('markdown') or '\n\n'.join(_body(b) for b in selected)
    target = {'page': page, 'block': block_id, 'bbox': bbox, 'scope': scope}
    fingerprint = {'provider': content.get('provider'), 'model': content.get('model'),
                   'target': target, 'ocr': payload}
    original = {'text': text, 'sha256': _hash(text), 'result_sha256': _hash(fingerprint)}
    return target, original


def _source(meta: dict, content: dict, docdir: Path) -> tuple[str, str, str | None]:
    from .read import _source_path
    source_sha = (meta.get('source') or {}).get('sha256')
    content_sha = (content.get('source') or {}).get('sha256')
    if (not source_sha or not isinstance(source_sha, str) or len(source_sha) != 64 or
            any(c not in '0123456789abcdef' for c in source_sha.lower())):
        return source_sha or '', 'unknown', 'missing_source_fingerprint'
    if content_sha and content_sha != source_sha:
        return source_sha, 'mismatch', 'metadata_source_mismatch'
    source = _source_path(meta, docdir)
    if source:
        if util.sha256_file(source) != source_sha:
            return source_sha, 'mismatch', 'source_changed'
        return source_sha, 'verified_local_file', None
    return source_sha, 'metadata_only', None


def _events(docdir: Path) -> list[dict]:
    events = []
    for path in sorted((Path(docdir) / 'corrections').glob('*.json')):
        try:
            event = json.loads(path.read_text(encoding='utf-8'))
            if (not isinstance(event, dict) or event.get('schema') != SCHEMA or
                    event.get('kind') not in {'correction', 'revoke'} or
                    event.get('id') != path.stem or not isinstance(event.get('created_ns'), int)):
                raise ValueError('invalid event envelope')
            if event['kind'] == 'correction' and (event.get('status') not in STATES or
                    not isinstance(event.get('target'), dict) or not isinstance(event.get('original'), dict)):
                raise ValueError('invalid correction')
        except (OSError, ValueError, TypeError) as exc:
            raise DocVisionError(f'Cannot read correction history: {path.name}; inspect it before applying corrections.') from exc
        events.append(event)
    return sorted(events, key=lambda e: (e['created_ns'], e['id']))


def _append(docdir: Path, event: dict) -> dict:
    event = {'schema': SCHEMA, 'id': uuid.uuid4().hex, 'created_at': util.now_iso(),
             'created_ns': time.time_ns(), **event}
    util.write_json(Path(docdir) / 'corrections' / f"{event['id']}.json", event)
    return event


def save(docdir: Path, *, page: int, replacement: str, author: str = 'human',
         status: str = 'candidate', block_id: str | None = None, bbox=None,
         reviewer: str = '', evidence=None, unresolved=None,
         original_text: str | None = None, original_sha256: str | None = None) -> dict:
    """Append a scoped record. Accepted requires explicit reviewer and evidence.

    Optional original_* values are optimistic checks against a caller's old draft.
    An empty replacement may explicitly remove a spurious block; unknown records
    never change reading output. New accepted records supersede the same target.
    """
    from .read import load
    docdir = Path(docdir)
    _identity(author, reviewer)
    if status not in STATES or not isinstance(replacement, str):
        raise DocVisionError('Use candidate, accepted or unknown status and a text replacement.')
    evidence, unresolved = _strings(evidence, 'Evidence'), _strings(unresolved, 'Unresolved items')
    if status == 'accepted' and (not reviewer.strip() or not evidence):
        raise DocVisionError('Accepted corrections require an explicit reviewer and visual/source evidence.')
    meta, content = load(docdir)
    sha, verification, error = _source(meta, content, docdir)
    if error:
        raise DocVisionError(f'Cannot save a correction: {error}; inspect/reconvert the source first.')
    box = _box(bbox)
    scope = 'region' if box is not None else 'block' if block_id else 'page'
    target, original = _snapshot(content, page=page, block_id=block_id, bbox=box, scope=scope)
    if ((original_text is not None and original_text != original['text']) or
            (original_sha256 is not None and original_sha256 != original['sha256'])):
        raise DocVisionError('The original OCR result has changed; read it again before saving a correction.')
    # Validate the existing log rather than silently obscuring corrupt history.
    _events(docdir)
    return _append(docdir, {'kind': 'correction', 'status': status, 'source_sha256': sha,
        'source_verification': verification, 'target': target, 'original': original,
        'replacement': replacement, 'author': author, 'reviewer': reviewer.strip(),
        'evidence': evidence, 'unresolved': unresolved, 'accuracy_verified': False})


def list_records(docdir: Path, *, page: int | None = None, block_id: str | None = None,
                 include_history: bool = True, meta: dict | None = None,
                 content: dict | None = None) -> list[dict]:
    """List saved records with validity/revocation history; False returns applied records only."""
    from .read import load
    docdir = Path(docdir)
    events = _events(docdir)
    if not events:
        return []
    if meta is None or content is None:
        meta, content = load(docdir)
    sha, verification, source_error = _source(meta, content, docdir)
    revocations, latest = {}, {}
    for event in events:
        if event['kind'] == 'revoke':
            revocations.setdefault(event.get('correction_id'), []).append(event)
        elif event['status'] == 'accepted':
            latest[_hash(event['target'])] = event['id']
    results = []
    for event in events:
        if event['kind'] != 'correction':
            continue
        target = event['target']
        if page is not None and target.get('page') != page:
            continue
        if block_id is not None and target.get('block') != block_id:
            continue
        reasons = []
        if source_error:
            reasons.append(source_error)
        if event.get('source_sha256') != sha:
            reasons.append('source_fingerprint_changed')
        try:
            _, current = _snapshot(content, page=target.get('page'), block_id=target.get('block'),
                                   bbox=target.get('bbox'), scope=target.get('scope'))
            if current['result_sha256'] != event['original'].get('result_sha256'):
                reasons.append('original_result_changed')
        except (DocVisionError, TypeError, KeyError, IndexError):
            reasons.append('target_unavailable')
        revoked = revocations.get(event['id'], [])
        superseded = event['status'] == 'accepted' and latest.get(_hash(target)) != event['id']
        effective = event['status'] == 'accepted' and not reasons and not revoked and not superseded
        record = {**event, 'valid': not reasons, 'invalid_reasons': reasons,
                  'source_verification_current': verification, 'effective': effective,
                  'superseded': superseded, 'revocations': revoked}
        if include_history or effective:
            results.append(record)
    return results


def revoke(docdir: Path, identifier: str, *, author: str = 'human', reviewer: str = '', reason: str) -> dict:
    """Append a revocation; older superseded corrections do not become active again."""
    _identity(author, reviewer)
    if not reviewer.strip() or not isinstance(reason, str) or not reason.strip():
        raise DocVisionError('Revocation requires a reviewer and reason.')
    events = _events(Path(docdir))
    if not any(e['id'] == identifier and e['kind'] == 'correction' for e in events):
        raise DocVisionError(f'Correction not found: {identifier}')
    return _append(Path(docdir), {'kind': 'revoke', 'correction_id': identifier,
        'author': author, 'reviewer': reviewer.strip(), 'reason': reason.strip()})


def _note(record: dict) -> str:
    target = record['target']
    scope = f"page {target['page']}"
    if target.get('block'):
        scope += f" / block {target['block']}"
    if target['scope'] == 'region':
        scope += f" / bbox {target['bbox']} (region annotation; no whole-block replacement)"
    unresolved = '\nUnresolved: ' + '; '.join(record['unresolved']) if record['unresolved'] else ''
    return (f"### Accepted local correction {record['id']}\nScope: {scope}; reviewer: {record['reviewer']}. "
            'Only this scope was reviewed; document accuracy remains unverified.\n'
            f"Evidence: {'; '.join(record['evidence'])}{unresolved}\n\n"
            f"Accepted revision:\n{record['replacement']}\n\n"
            f"Original OCR for this scope:\n{record['original']['text']}")


def project(docdir: Path, meta: dict, content: dict) -> tuple[dict, list[dict]]:
    """Create a read-only view. Region/page notes never rewrite inferred text spans."""
    records = list_records(docdir, meta=meta, content=content)
    effective = [r for r in records if r['effective']]
    if not effective:
        return content, records
    result = copy.deepcopy(content)
    for page in result.get('pages') or []:
        selected = [r for r in effective if r['target']['page'] == page.get('page')]
        if not selected:
            continue
        original = page.get('markdown') or '\n\n'.join(_body(b) for b in page.get('blocks') or [])
        page['original_ocr_markdown'] = original
        page['corrections'] = selected
        page['accuracy_verified'] = False
        # Keep provider layout intact. Scoped accepted amendments explicitly take
        # precedence, while an arbitrary bbox is never expanded to a whole block.
        page['markdown'] = ('[Accepted local corrections take precedence only within their stated scopes. Original OCR layout is preserved below.]\n\n'
                            + '\n\n'.join(_note(r) for r in selected) + '\n\n### Original OCR layout\n\n' + original)
        for block in page.get('blocks') or []:
            matched = [r for r in selected if r['target'].get('block') == block.get('id') and r['target']['scope'] == 'block']
            if matched:
                correction = matched[-1]
                block['original_ocr'] = {'markdown': block.get('markdown'), 'text': block.get('text')}
                block['markdown'] = block['text'] = correction['replacement']
                block['correction'] = correction
                block['accuracy_verified'] = False
            def overlaps(record):
                target = record['target']
                if target.get('block'):
                    return target['block'] == block.get('id')
                bb, rb = block.get('bbox'), target.get('bbox')
                return bool(bb and rb and max(bb[0], rb[0]) < min(bb[2], rb[2]) and
                            max(bb[1], rb[1]) < min(bb[3], rb[3]))

            annotations = [r for r in selected if r['target']['scope'] == 'region' and overlaps(r)]
            if annotations:
                block['correction_annotations'] = annotations
    return result, records
