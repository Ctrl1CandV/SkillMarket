"""Small installation journal; roll back configuration without deleting runtimes."""
from __future__ import annotations

import copy
import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import config, util
from .base import DocVisionError


def new_id() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]


def root() -> Path:
    return util.config_path().parent / 'setup-history'


def value(data: dict, field: str):
    item = data
    for key in field.split('.'):
        if not isinstance(item, dict):
            return None
        item = item.get(key)
    return copy.deepcopy(item)


def assign(data: dict, field: str, setting) -> None:
    parts = field.split('.')
    item = data
    for key in parts[:-1]:
        item = item.setdefault(key, {})
    item[parts[-1]] = copy.deepcopy(setting)


def versions(data: dict) -> dict:
    """Read installed metadata without importing models or running old code."""
    result = {}
    for field in ('core', 'engines.mineru', 'engines.paddleocr'):
        section = value(data, field) or {}
        python = section.get('python')
        if not python:
            continue
        parent = Path(python).parent
        prefix = parent.parent if parent.name.lower() in {'scripts', 'bin'} else parent
        sites = [prefix / 'Lib/site-packages', *(prefix / 'lib').glob('python*/site-packages')]
        packages = {}
        for site in sites:
            for path in site.glob('*.dist-info/METADATA'):
                try:
                    with path.open(encoding='utf-8', errors='replace') as stream:
                        header = stream.read(65536).split('\n\n', 1)[0]
                    name = re.search(r'(?m)^Name:\s*(.+)$', header)
                    release = re.search(r'(?m)^Version:\s*(.+)$', header)
                    if name and release:
                        packages[name.group(1).strip()] = release.group(1).strip()
                except OSError:
                    continue
        result[field] = {'python': python, 'packages': packages,
                         'metadata_available': bool(packages)}
    return result


def begin(identifier: str, before: dict, fields: list[str], *, profile: str,
          prefixes: dict, kind: str = 'install') -> tuple[Path, dict]:
    directory = root() / identifier
    directory.mkdir(parents=True, exist_ok=False)
    record = {'schema': 'docvision.setup/1', 'id': identifier, 'kind': kind,
              'config_path': str(util.config_path()),
              'created_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'),
              'profile': profile, 'state': 'installing', 'fields': fields,
              'before': before, 'versions_before': versions(before), 'prefixes': prefixes}
    util.write_json(directory / 'snapshot.json', record)
    return directory, record


def update(directory: Path, record: dict, **changes) -> None:
    record.update(changes)
    util.write_json(directory / 'snapshot.json', record)


@contextmanager
def _switch_lock():
    path = util.config_path().with_name(util.config_path().name + '.setup.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = path.open('x', encoding='utf-8')
    except FileExistsError as exc:
        raise DocVisionError('Another installation is switching this configuration; retry after it finishes.') from exc
    try:
        with handle:
            yield
    finally:
        path.unlink()


def activate(before: dict, candidate: dict, fields: list[str]) -> None:
    with _switch_lock():
        current = config.load()
        if any(value(current, field) != value(before, field) for field in fields):
            raise DocVisionError('Runtime configuration changed during installation; the candidate was not activated.')
        for field in fields:
            assign(current, field, value(candidate, field))
        config.save(current)  # write_json uses atomic replacement


def entries() -> list[dict]:
    result = []
    for path in sorted(root().glob('*/snapshot.json'), reverse=True):
        item = util.read_json(path, {})
        if (isinstance(item, dict) and item.get('schema') == 'docvision.setup/1'
                and item.get('config_path') == str(util.config_path())):
            result.append({key: item.get(key) for key in
                           ('id', 'kind', 'profile', 'state', 'created_at', 'prefixes', 'error')})
    return sorted(result, key=lambda item: item.get('created_at') or '', reverse=True)


def read(identifier: str) -> tuple[Path, dict]:
    if not re.fullmatch(r'\d{8}T\d{6}Z-[0-9a-f]{8}', identifier):
        raise DocVisionError('Invalid setup snapshot ID; choose an ID from setup history.')
    directory = root() / identifier
    record = util.read_json(directory / 'snapshot.json', {})
    if (not isinstance(record, dict) or record.get('schema') != 'docvision.setup/1'
            or record.get('config_path') != str(util.config_path())
            or not isinstance(record.get('before'), dict)):
        raise DocVisionError('Setup snapshot was not found for this configuration.')
    allowed = {'core', 'models_dir', 'engines.mineru', 'engines.paddleocr'}
    if (not isinstance(record.get('fields'), list) or not record['fields']
            or any(not isinstance(field, str) or field not in allowed for field in record['fields'])):
        raise DocVisionError('Setup snapshot contains unsupported configuration fields.')
    return directory, record


def restore(identifier: str) -> str:
    _, selected = read(identifier)
    fields = selected['fields']
    # An absent/removed previous runtime cannot be made usable by configuration.
    for field in fields:
        section = value(selected['before'], field)
        if isinstance(section, dict):
            for key in ('python', 'exe'):
                path = section.get(key)
                if path and not Path(path).is_file():
                    raise DocVisionError(f'Previous runtime is missing: {path}. Nothing was changed.')
            path = section.get('model_home')
            if not path and not selected['before'].get('models_dir'):
                path = section.get('mineru_home')
            if path and not config._stored_path(path).is_dir():
                raise DocVisionError(f'Previous model directory is missing: {path}. Nothing was changed.')
    with _switch_lock():
        current = config.load()
        checkpoint = new_id()
        directory, record = begin(checkpoint, current, fields, profile=selected['profile'],
                                  prefixes={}, kind='rollback')
        restored = copy.deepcopy(current)
        for field in fields:
            assign(restored, field, value(selected['before'], field))
        update(directory, record, state='validated', restored_snapshot=identifier)
        try:
            config.save(restored)
        except OSError as exc:
            try:
                update(directory, record, state='failed', error=str(exc))
            except OSError:
                pass  # Keep the original config-write failure and its pre-rollback snapshot.
            raise
        try:
            update(directory, record, state='activated')
        except OSError as exc:
            print(f'Configuration restored; journal update failed: {exc}. Snapshot: {directory}')
    return checkpoint
