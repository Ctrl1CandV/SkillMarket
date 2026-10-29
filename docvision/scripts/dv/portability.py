"""Portable document references and explicit, hash-checked source relinking."""
from __future__ import annotations

import copy
import os
import uuid
from pathlib import Path

from . import util
from .base import DocVisionError

REF_PATHS = ('record_path', 'image_path', 'context_path', 'markdown_path')


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _old_root(record: dict) -> Path | None:
    path = Path(record.get('record_path') or '')
    if path.is_absolute() and len(path.parents) >= 3 and path.parent.parent.name == 'refinements':
        return path.parent.parent.parent
    return None


def resolve_refinement(docdir: Path, record: dict, record_path: Path | None = None) -> dict:
    """Return usable paths without trusting stale absolute locations after a move."""
    result = copy.deepcopy(record)
    root = Path(docdir).resolve()
    old_root = _old_root(record)
    for key in REF_PATHS:
        value = record.get(key)
        if not value:
            continue
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        elif old_root and _inside(path, old_root):
            path = root / path.resolve().relative_to(old_root.resolve())
        if not _inside(path, root):
            raise DocVisionError(f'Refinement {key} escapes its document directory.')
        result[key] = str(path.resolve())
    if record_path is not None:
        if not _inside(record_path, root):
            raise DocVisionError('Refinement record is outside its document directory.')
        result['record_path'] = str(record_path.resolve())
    result['path_base'] = 'document'
    return result


def save_refinement(docdir: Path, record_path: Path, record: dict) -> None:
    root = Path(docdir).resolve()
    portable = resolve_refinement(root, record, record_path)
    for key in REF_PATHS:
        if portable.get(key):
            portable[key] = Path(portable[key]).relative_to(root).as_posix()
    # The source is provenance; internal input files also become portable.
    source = portable.get('source') or {}
    path = source.get('path')
    if path and not util.is_url(path) and Path(path).is_absolute() and _inside(Path(path), root):
        source['path'] = Path(path).resolve().relative_to(root).as_posix()
        source['path_base'] = 'document'
    util.write_json(record_path, portable)


def relink(docdir: Path, *, source: str | None = None, dry_run: bool = False) -> dict:
    """Relink only the supplied file; migrate known internal paths, never scan disks."""
    from .output import _exclusive_write_lock
    root = Path(docdir).resolve()
    meta = util.read_json(root / 'meta.json', {}) or {}
    content = util.read_json(root / 'content.json', {}) or {}
    if not meta or not content:
        raise DocVisionError('Relink expects a converted document directory.')
    expected = (meta.get('source') or {}).get('sha256')
    replacement = None
    if source is not None:
        candidate = Path(source).expanduser().resolve()
        if not candidate.is_file() or not expected:
            raise DocVisionError('Relink requires an existing source file and the saved source SHA-256.')
        if util.sha256_file(candidate) != expected:
            raise DocVisionError('Source SHA-256 does not match; reconvert changed content instead of relinking.')
        if (content.get('source') or {}).get('sha256') != expected:
            raise DocVisionError('Source identities in meta.json and content.json disagree.')
        try:
            replacement = Path(os.path.relpath(candidate, root)).as_posix()
        except ValueError:  # Different Windows volumes cannot share a relative path.
            replacement = str(candidate)

    updates = {}
    roots = []
    for path in sorted((root / 'refinements').glob('*/record.json')):
        saved = util.read_json(path, {}) or {}
        old = _old_root(saved)
        if old:
            roots.append(old)
        normalized = resolve_refinement(root, saved, path)
        for key in REF_PATHS:
            if normalized.get(key):
                normalized[key] = Path(normalized[key]).relative_to(root).as_posix()
        if normalized != saved:
            updates[path] = normalized

    # A refinement's result has its own meta/content source pointing to input.png.
    # Migrate these known subdocuments using recorded roots, without following links.
    for path in sorted((root / 'refinements').glob('*/result/*/meta.json')):
        for item in (path, path.with_name('content.json')):
            data = util.read_json(item, {}) or {}
            src = data.get('source') or {}
            value = src.get('path')
            if not value or util.is_url(value) or not Path(value).is_absolute():
                continue
            mapped = None
            for old in [root] + roots:
                if _inside(Path(value), old):
                    mapped = root / Path(value).resolve().relative_to(old.resolve())
                    break
            if mapped is not None:
                src['path'] = Path(os.path.relpath(mapped, item.parent)).as_posix()
                src['path_base'] = 'document'
                updates[item] = data

    if replacement is not None:
        for path, data in ((root / 'meta.json', meta), (root / 'content.json', content)):
            data = copy.deepcopy(data)
            data['source']['path'] = replacement
            data['source']['path_base'] = 'document' if not Path(replacement).is_absolute() else 'absolute'
            updates[path] = data
    result = {'source_sha256': expected, 'source': replacement or meta.get('source', {}).get('path'),
              'files_updated': len(updates), 'dry_run': dry_run, 'document': str(root)}
    if dry_run or not updates:
        return result
    # All references are prepared first. Keep a recoverable journal and restore on error.
    with _exclusive_write_lock(root / '.docvision-write.lock', 'A document writer is active.'):
        before = {p.relative_to(root).as_posix(): util.read_json(p) for p in updates}
        event = {'schema': 'docvision.relink/1', 'created_at': util.now_iso(), 'state': 'prepared',
                 'source_sha256': expected, 'before': before, 'new_source': replacement}
        journal = util.ensure_dir(root / 'relinks') / (uuid.uuid4().hex + '.json')
        util.write_json(journal, event)
        try:
            for path, value in updates.items():
                util.write_json(path, value)
        except Exception:
            for relative, value in before.items():
                util.write_json(root / relative, value)
            event['state'] = 'rolled_back'
            util.write_json(journal, event)
            raise
        event['state'] = 'complete'
        util.write_json(journal, event)
        result['journal'] = str(journal)
    return result
