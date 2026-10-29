"""Durable, credential-free receipts for asynchronous cloud submissions.

The journal records intent before POST. A receipt without a job ID is deliberately
ambiguous and must never be interpreted as permission to submit again.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from contextlib import contextmanager
from pathlib import Path

from . import cache, util
from .base import DocVisionError, Options

SCHEMA = 'docvision.cloud-job/1'
TERMINAL = {'completed', 'remote_failed'}


def jobs_dir() -> Path:
    return util.config_path().parent / 'cloud-jobs'


def _path(task_id: str) -> Path:
    if not isinstance(task_id, str) or not re.fullmatch(r'[0-9a-f]{32}', task_id):
        raise DocVisionError('Invalid cloud task ID; use `docvision jobs list`.')
    return jobs_dir() / task_id / 'receipt.json'


def _write(path: Path, value: dict) -> None:
    """Flush before replace: a POST must not outrun its local intent record."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.receipt-' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load(task_id: str) -> dict:
    record = util.read_json(_path(task_id), None)
    if not isinstance(record, dict) or record.get('schema') != SCHEMA or record.get('task_id') != task_id:
        raise DocVisionError('Cloud task receipt is missing or invalid; no request was sent.')
    return record


def update(task_id: str, **changes) -> dict:
    record = load(task_id)
    record.update(changes, updated_at=util.now_iso())
    _write(_path(task_id), record)
    return record


def list_jobs() -> list[dict]:
    """Only safe summaries; never return an upstream response or signed URL."""
    rows = []
    for path in sorted(jobs_dir().glob('*/receipt.json')):
        record = util.read_json(path, None)
        if not isinstance(record, dict) or record.get('schema') != SCHEMA:
            continue
        rows.append({key: record.get(key) for key in (
            'task_id', 'job_id', 'state', 'created_at', 'updated_at', 'source',
            'model', 'expected_pages', 'output_dir', 'refinement_record', 'last_error_kind')})
    return sorted(rows, key=lambda row: row.get('created_at') or '', reverse=True)


@contextmanager
def _request_lock(key: str):
    root = jobs_dir()
    root.mkdir(parents=True, exist_ok=True)
    path = root / ('.intent-' + key + '.lock')
    try:
        handle = path.open('x', encoding='utf-8')
    except FileExistsError as exc:
        raise DocVisionError('A matching cloud submission is being registered.',
                             hint='Inspect jobs list first. A stale intent lock can be removed only after confirming its writer stopped.') from exc
    try:
        with handle:
            yield
    finally:
        path.unlink(missing_ok=True)


def create(source: str, info: dict, endpoint: str, payload: dict, expected: list[int],
           opts: Options, *, output_root: Path) -> dict:
    is_url = util.is_url(source)
    identity = ({'kind': 'url', 'url_sha256': util.sha256_bytes(source.encode())} if is_url else
                {'kind': 'file', 'path': str(Path(source).resolve()), 'sha256': info['sha256']})
    fingerprint = {key: value for key, value in identity.items() if key != 'path'}
    request_key = util.sha256_bytes(json.dumps([fingerprint, endpoint, payload], sort_keys=True).encode())
    explicit_attempt = opts.extra.get('cloud_new_attempt') is True or opts.extra.get('cloud_new_attempt') == 'true'
    with _request_lock(request_key):
        previous = []
        for path in jobs_dir().glob('*/receipt.json'):
            old = util.read_json(path, {}) or {}
            if old.get('request_key') == request_key and old.get('state') not in TERMINAL:
                previous.append(old['task_id'])
        if previous and not explicit_attempt:
            raise DocVisionError('A matching cloud submission is unfinished; no new POST was sent.',
                                 hint='Use `docvision jobs list` and resume task ' + previous[-1] +
                                 '. If submission is unknown, inspect the service account first; an explicit cloud_new_attempt=true may incur a second charge.')
        task_id = uuid.uuid4().hex
        now = util.now_iso()
        record = {'schema': SCHEMA, 'task_id': task_id, 'job_id': None,
                  'state': 'submission_unknown', 'created_at': now, 'updated_at': now,
                  'source': identity, 'endpoint': endpoint, 'model': payload['model'],
                  'request': payload, 'request_key': request_key, 'expected_pages': expected,
                  'options': {key: getattr(opts, key) for key in (
                      'tier', 'mode', 'pages', 'lang', 'device', 'keep_raw', 'images', 'max_mb')},
                  'extra': {key: opts.extra[key] for key in ('model', 'refine_task', 'refine_is_region')
                            if key in opts.extra},
                  'cache_request': cache.request_signature(info, opts, provider='paddleocr-cloud',
                      context=cache.provider_context('paddleocr-cloud', extra=opts.extra)),
                  'output_root': str(output_root.resolve()), 'supersedes_task_ids': previous,
                  'refinement_record': str(Path(opts.extra['_cloud_refinement_record']).resolve())
                  if opts.extra.get('_cloud_refinement_record') else None}
        _write(_path(task_id), record)
    # This in-memory value lets refine retain the association even in its error path.
    opts.extra['_cloud_task_id'] = task_id
    if record['refinement_record']:
        link_refinement(record)
    return record


def refinement(record: dict, override: str | Path | None = None) -> tuple[Path, Path, dict] | None:
    value = override or record.get('refinement_record')
    if not value:
        return None
    path = Path(value).resolve()
    saved = util.read_json(path, None)
    if not isinstance(saved, dict) or saved.get('schema') != 'docvision.refinement/1':
        raise DocVisionError('Linked refinement record is missing or invalid; no request was sent.')
    docdir = path.parent.parent.parent
    try:
        from .portability import resolve_refinement
    except ImportError:
        pass
    else:
        saved = resolve_refinement(docdir, saved, path)
    if saved.get('cloud_task_id') not in (None, record['task_id']):
        raise DocVisionError('Refinement belongs to a different cloud task.')
    if saved.get('input_sha256') != record['source'].get('sha256'):
        raise DocVisionError('Refinement input SHA256 does not match the cloud task.')
    return docdir, path, saved


def save_refinement(docdir: Path, path: Path, record: dict) -> None:
    try:
        from .portability import save_refinement as save
    except ImportError:
        util.write_json(path, record)
    else:
        save(docdir, path, record)


def link_refinement(record: dict) -> None:
    linked = refinement(record)
    if linked:
        docdir, path, saved = linked
        saved['cloud_task_id'] = record['task_id']
        save_refinement(docdir, path, saved)


def mark_output(task_id: str, output_dir: Path) -> dict:
    """Called after the common writer completes; never performs network I/O."""
    qa = util.read_json(Path(output_dir) / 'qa.json', {}) or {}
    return update(task_id, state='completed' if qa.get('status') in {'pass', 'warn'} else 'output_failed',
                  output_dir=str(Path(output_dir).resolve()))
