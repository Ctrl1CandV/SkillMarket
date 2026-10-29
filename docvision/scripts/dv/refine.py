"""Bounded region review: keep the local draft, save a separate attributable result."""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from . import cache, config, focus, portability, read as reading, util
from .base import DocVisionError, Options
from .detect import describe_route
from .output import write_document
from .providers import PROVIDERS, run as run_provider

VISION = {'local-vlm'}
OCR = {'paddleocr-cloud', 'mineru-local', 'paddleocr-local'}


def _error_text(exc: Exception) -> str:
    text = str(exc)
    for key in config.remote_keys().values():
        if key:
            text = text.replace(key, '[redacted]')
    return re.sub(r'(?i)([?&](?:key|api_key|token|access_token)=)[^&\s]+', r'\1[redacted]', text)[:1200]


def _task(block_type: str) -> str:
    return {'formula': 'formula', 'table': 'table', 'image': 'figure', 'chart': 'chart'}.get(block_type, 'transcribe')


def triage(docdir: Path) -> dict:
    """Heuristics indicate review priority; they do not estimate correctness."""
    meta, content = reading.load(docdir)
    candidates = []
    for page in content.get('pages') or []:
        for block in page.get('blocks') or []:
            kind = block.get('type')
            if kind not in {'formula', 'table', 'image', 'chart'}:
                continue
            task = _task(kind)
            merged = kind == 'table' and any(x in (block.get('markdown') or '').lower() for x in ('rowspan', 'colspan'))
            candidates.append({'page': page['page'], 'block': block['id'], 'bbox': block.get('bbox'),
                'task': task, 'priority': 'high' if kind == 'formula' or merged else 'normal',
                'reason': 'merged cells' if merged else f'{kind} needs visual comparison',
                'route': 'vision or host image review' if task in {'figure', 'chart'} else 'independent OCR or host image review'})
    candidates.sort(key=lambda c: (c['priority'] != 'high', c['page'], c['block']))
    qa = util.read_json(Path(docdir) / 'qa.json', {}) or {}
    return {'schema': 'docvision.triage/1', 'accuracy_verified': False, 'candidates': candidates,
            'structural_issues': qa.get('issues') or [],
            'note': 'Candidates are review hints, not detected errors. Also select important inline formulas or unclassified regions manually.'}


def _box(value) -> list[float] | None:
    if value is None:
        return None
    try:
        box = [float(x) for x in value.split(',')] if isinstance(value, str) else [float(x) for x in value]
    except (TypeError, ValueError):
        raise DocVisionError('bbox must contain four normalized numbers.')
    if len(box) != 4 or not all(0 <= n <= 1 for n in box) or box[0] >= box[2] or box[1] >= box[3]:
        raise DocVisionError('bbox must satisfy 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1.')
    return box


def choose_provider(provider: str, task: str, allow_remote: bool) -> str:
    if provider != 'auto':
        if provider not in {'packet'} | VISION | OCR:
            raise DocVisionError(f'Unsupported refinement provider: {provider}')
        if task in {'figure', 'chart'} and provider in OCR:
            raise DocVisionError('Diagram/chart interpretation requires a vision provider or packet. Use --task transcribe for OCR only.')
        if provider != 'packet' and describe_route(provider)['remote']:
            if config.remote_consent() == 'local-only':
                raise DocVisionError('Remote refinement was declined for this installation.',
                                     hint='Run `docvision setup --remote` to re-enable it, or use --provider packet.')
            if config.remote_consent() != 'remote':
                raise DocVisionError('Remote refinement consent has not been recorded for this OS user.',
                                     hint='Confirm upload is acceptable and run `docvision setup --remote`; each call still needs --allow-remote.')
            if not allow_remote:
                raise DocVisionError('Remote refinement requires --allow-remote after upload authorization.')
        return provider
    if task in {'figure', 'chart'}:
        if config.discover_vlm().available:
            return 'local-vlm'
    # A token and upload permission are not evidence that a second OCR pass
    # helps. Select paddleocr-cloud explicitly for an identified uncertainty.
    return 'packet'


def _selector(provider: str, extra: dict) -> dict:
    # Hash configuration so URLs with credentials and arbitrary extra options are not persisted.
    blob = json.dumps(cache.provider_context(provider, extra=extra), sort_keys=True,
                      ensure_ascii=True, default=str)
    return {'configuration_sha256': hashlib.sha256(blob.encode()).hexdigest()}


def _latest_attempt(root: Path, identifier: str) -> tuple[int, Path]:
    """Include unfinished directories: an older success must not hide a new submission."""
    latest = (1, root / identifier)
    for directory in root.glob(f'{identifier}-*'):
        suffix = directory.name[len(identifier) + 1:]
        if directory.is_dir() and suffix.isdigit() and int(suffix) > latest[0]:
            latest = (int(suffix), directory)
    return latest


def _context(page: dict, block: dict | None, box: list | None) -> tuple[str, list[str]]:
    body = page.get('markdown') or '\n\n'.join(b.get('markdown') or b.get('text') or '' for b in page.get('blocks') or [])
    blocks = page.get('blocks') or []
    if block is None and box is None:
        return f'Original PDF page: {page["page"]}\nWhole-page OCR draft (possibly erroneous):\n{body[:6000]}', ['whole-page']
    selected = {i for i, b in enumerate(blocks) if b is block}
    if block is None and box:
        for i, b in enumerate(blocks):
            bb = b.get('bbox')
            if bb and max(bb[0], box[0]) < min(bb[2], box[2]) and max(bb[1], box[1]) < min(bb[3], box[3]):
                selected.add(i)
    indices = set(selected)
    for i in selected:
        indices.update(n for n in (i - 1, i + 1) if 0 <= n < len(blocks))
    scope = [blocks[i].get('id') or f'block-{i}' for i in sorted(indices)]
    chunks = []
    for i in sorted(indices):
        b = blocks[i]
        text = b.get('markdown') or b.get('text') or ''
        if b.get('type') in {'image', 'chart'} and b.get('text') and b['text'] not in text:
            text += '\nCaption/recognized figure text: ' + b['text']
        chunks.append(f"[{b.get('id', i)}] " + text[:(3500 if i in selected else 1000)])
    return f'Original PDF page: {page["page"]}\nSelected/neighboring OCR blocks (possibly erroneous):\n' + '\n\n'.join(chunks)[:8000], scope


def run(docdir: Path, *, page: int, block_id: str | None = None, bbox=None,
        task: str = 'auto', provider: str = 'auto', allow_remote: bool = False,
        dpi: int = 300, extra: dict | None = None, question: str = '', timeout: int = 900,
        dry_run: bool = False, force: bool = False) -> dict:
    started = time.monotonic()
    docdir = Path(docdir)
    meta, content = reading.load(docdir)
    current = next((p for p in content.get('pages') or [] if p.get('page') == page), None)
    if not current:
        raise DocVisionError(f'Page {page} is not in this document.')
    block = None
    if block_id:
        block = next((b for b in current.get('blocks') or [] if b.get('id') == block_id), None)
        if block is None:
            raise DocVisionError(f'Block {block_id} is not on page {page}.')
        if not bbox and not block.get('bbox'):
            raise DocVisionError('Selected block has no bbox; use --bbox or omit --block to review the page.')
    box = _box(bbox if bbox is not None else block.get('bbox') if block else None)
    task = _task(block.get('type', 'text')) if task == 'auto' and block else 'transcribe' if task == 'auto' else task
    if task not in focus.TASKS:
        raise DocVisionError(f'Unknown refinement task: {task}')
    if not 72 <= dpi <= 600:
        raise DocVisionError('Refinement DPI must be between 72 and 600.')
    provider = choose_provider(provider, task, allow_remote)
    context, context_scope = _context(current, block, box)
    extra = dict(extra or {})
    if provider == 'paddleocr-local' and not config.discover_paddle().version and not force:
        raise DocVisionError('Cannot identify the isolated Paddle runtime version for safe reuse. Run doctor/setup, or explicitly use --force for a new local attempt.')
    original = reading._source_path(meta, docdir)
    if not original:
        raise DocVisionError('Refinement needs the original local PDF/image for an attributable crop.')
    actual_sha = util.sha256_file(original)
    if meta.get('source', {}).get('sha256') and meta['source']['sha256'] != actual_sha:
        raise DocVisionError('The original file has changed; reconvert it before reusing page/block coordinates.')
    signature = {'source_sha256': actual_sha, 'page': page, 'block': block_id, 'bbox': box,
                 'selected_block_bbox': block.get('bbox') if block else None,
                 'task': task, 'provider': provider, 'dpi': dpi, 'prompt_version': focus.PROMPT_VERSION,
                 'context_sha256': hashlib.sha256(context.encode()).hexdigest(),
                 'question_sha256': hashlib.sha256(question.encode()).hexdigest(), **_selector(provider, extra)}
    identifier = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[:20]
    directory = docdir / 'refinements' / identifier
    record_path = directory / 'record.json'
    source = {'path': str(original.resolve()), 'sha256': actual_sha, 'page': page, 'block': block_id, 'bbox': box}
    record = {'schema': 'docvision.refinement/1', 'id': identifier, 'state': 'planned',
              'source': source, 'provider': provider, 'task': task, 'dpi': dpi,
              'accuracy_verified': False, 'cached': False, 'signature': signature,
              'context_scope': context_scope, 'context_chars': len(context),
              'quota': 'account-dependent; no automatic retries or paid fallback',
              'record_path': str(record_path.resolve())}
    if dry_run:
        return record
    attempt, directory = _latest_attempt(directory.parent, identifier)
    record_path = directory / 'record.json'
    cached = util.read_json(record_path, {}) or {}
    if cached:
        cached = portability.resolve_refinement(docdir, cached, record_path)
    if cached and not force and cached.get('state') in {'recognized', 'review_required', 'failed', 'submitted'}:
        # Missing local inputs/results invalidate the cache. A previous failure is never silently retried.
        needed = [cached.get('image_path'), cached.get('context_path')]
        if cached.get('state') == 'recognized':
            needed.append(cached.get('markdown_path'))
        if all(p and Path(p).is_file() for p in needed):
            return {**cached, 'cached': True}
        raise DocVisionError('A refinement attempt already exists but its files are missing. Inspect it and use --force for an explicit new attempt.')
    util.ensure_dir(directory.parent)
    while True:
        try:
            # Atomic ownership across threads and processes, before rendering or submission.
            directory.mkdir()
            break
        except FileExistsError:
            if not force:
                raise DocVisionError('This refinement attempt already exists or is in progress; inspect record.json. Use --force only for an explicit new attempt.')
            attempt += 1
            directory = docdir / 'refinements' / f'{identifier}-{attempt}'
    record_path = directory / 'record.json'
    record['record_path'] = str(record_path.resolve())
    portability.save_refinement(docdir, record_path, record)
    image_path = directory / 'input.png'
    if box:
        reading.crop(docdir, page=page, bbox=','.join(str(n) for n in box), out=image_path, dpi=dpi)
    else:
        page_image = reading.render_page(docdir, page, meta=meta, content=content, dpi=dpi)
        # Normalize image bytes; standalone JPEG must not masquerade as image/png.
        from PIL import Image
        with Image.open(page_image) as im:
            im.convert('RGB').save(image_path, format='PNG')
    context_path = directory / 'context.md'
    util.atomic_write(context_path, '# Region review\n\n' + focus.prompt(task, context, question)
                      + '\n\nOpen input.png with an actual image viewing tool before answering. '
                        'A generated packet alone is not a completed visual review.\n')
    record.update({'image_path': str(image_path.resolve()), 'context_path': str(context_path.resolve()),
                   'input_sha256': util.sha256_file(image_path), 'created_at': util.now_iso()})
    if provider == 'packet':
        record['state'] = 'review_required'
    else:
        # Write an in-progress record before submission. An interrupted request is never auto-resubmitted.
        record['state'] = 'submitted'
        portability.save_refinement(docdir, record_path, record)
        opts = Options(provider=provider, mode='ocr', tier='quality', allow_remote=allow_remote,
                       timeout=timeout, keep_raw=True, staging=directory / 'work', output=directory / 'result',
                       extra={**extra, 'refine_task': task, 'refine_is_region': box is not None,
                              'refine_context': context, 'question': question,
                              **({'_cloud_refinement_record': str(record_path.resolve()),
                                  'cloud_new_attempt': force} if provider == 'paddleocr-cloud' else {})})
        try:
            raw, raw_meta = run_provider(provider, str(image_path), opts)
            if raw is None or not raw.markdown.strip():
                raise DocVisionError('Refinement returned no content.')
            output = write_document(raw, str(image_path), opts, out_root=directory / 'result',
                                    info={'pages': 1, 'sha256': record['input_sha256']},
                                    raw_meta=raw_meta, route=describe_route(provider))
            if (raw_meta or {}).get('cloud_task_id'):
                from . import cloud_jobs
                cloud_jobs.mark_output(raw_meta['cloud_task_id'], output)
            qa = util.read_json(output / 'qa.json', {}) or {}
            record.update({'state': 'recognized' if qa.get('status') != 'fail' else 'failed',
                           'model': raw.model, 'markdown_path': str((output / f'{output.name}.md').resolve()),
                           'qa': qa.get('status'), 'warnings': raw.warnings})
            if qa.get('status') == 'fail':
                record['error'] = 'Refinement failed structural checks; inspect the result before using it.'
        except Exception as exc:
            # Keep the local packet for review; never switch provider or repeat submission.
            record.update({'state': 'failed', 'error': _error_text(exc)})
        finally:
            if opts.extra.get('_cloud_task_id'):
                record['cloud_task_id'] = opts.extra['_cloud_task_id']
    record['elapsed_seconds'] = round(time.monotonic() - started, 3)
    portability.save_refinement(docdir, record_path, record)
    return record


def list_results(docdir: Path, *, page: int | None = None, block_id: str | None = None) -> list[dict]:
    paths = sorted((Path(docdir) / 'refinements').glob('*/record.json'))
    if not paths:
        return []
    meta, content = reading.load(Path(docdir))
    source_sha = (meta.get('source') or {}).get('sha256')
    original = reading._source_path(meta, docdir)
    if original:
        actual_sha = util.sha256_file(original)
        if source_sha and source_sha != actual_sha:
            return []
        source_sha = actual_sha
    results = []
    for path in paths:
        record = util.read_json(path, {}) or {}
        source = record.get('source') or {}
        if not source_sha or source.get('sha256') != source_sha:
            continue
        if page is not None and source.get('page') != page:
            continue
        if block_id is not None and source.get('block') != block_id:
            continue
        current = next((p for p in content.get('pages') or [] if p.get('page') == source.get('page')), None)
        if not current:
            continue
        block = None
        signature = record.get('signature') or {}
        if source.get('block'):
            block = next((b for b in current.get('blocks') or [] if b.get('id') == source['block']), None)
            # Legacy records do not distinguish a manually overridden box.
            recorded_box = signature.get('selected_block_bbox', source.get('bbox'))
            if not block or block.get('bbox') != recorded_box:
                continue
        context, _ = _context(current, block, source.get('bbox'))
        if signature.get('context_sha256') != hashlib.sha256(context.encode()).hexdigest():
            continue
        results.append(portability.resolve_refinement(docdir, record, path))
    return results
