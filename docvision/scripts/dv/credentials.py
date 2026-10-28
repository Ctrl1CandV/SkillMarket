"""Load one explicitly selected credential file without shell evaluation.

Only recognized API credentials, model names and endpoints are accepted. This
module never prints values or writes a credential/configuration file.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
from collections.abc import MutableMapping

from .base import DocVisionError


# Group aliases so a preexisting environment value wins even when a file uses
# a higher-priority spelling. Within a file, provider lookup order still applies.
ENV_GROUPS = (
    ('DOCVISION_PADDLE_TOKEN', 'PADDLEOCR_ACCESS_TOKEN', 'PADDLEOCR_API_TOKEN', 'AI_STUDIO_TOKEN', 'PADDLEAPIKEY'),
    ('DOCVISION_MINERU_TOKEN', 'MINERU_TOKEN', 'MINERU_API_KEY'),
    ('DOCVISION_GLM_API_KEY', 'ZHIPU_API_KEY', 'GLM_API_KEY'),
    ('DOCVISION_MISTRAL_API_KEY', 'MISTRAL_API_KEY'),
    ('DOCVISION_GEMINI_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY'),
    ('DOCVISION_OPENAI_API_KEY', 'OPENAI_API_KEY'),
    ('DOCVISION_VLM_API_KEY',),
    ('DOCVISION_GEMINI_MODEL',),
    ('DOCVISION_OPENAI_MODEL', 'OPENAI_MODEL'),
    ('DOCVISION_OPENAI_BASE_URL', 'OPENAI_BASE_URL'),
)
ALLOWED_NAMES = frozenset(name for group in ENV_GROUPS for name in group)
MAX_FILE_BYTES = 1024 * 1024


def _invalid(line: int) -> DocVisionError:
    # Do not include source text, variable values or exception representations.
    return DocVisionError(f'Invalid credential file syntax at line {line}.',
                          hint='Use one NAME=value assignment per line; close quotes on the same line.')


def _value(raw: str, line: int) -> str:
    raw = raw.strip()
    if not raw:
        return ''
    if raw[0] not in {'"', "'"}:
        # Preserve literal hashes in tokens/URL fragments, recognize comments
        # introduced by whitespace (or at the start of an empty value).
        return re.split(r'(?<!\S)#', raw, maxsplit=1)[0].rstrip()
    quote = raw[0]
    result = []
    i = 1
    while i < len(raw):
        char = raw[i]
        if char == quote:
            tail = raw[i + 1:].strip()
            if tail and not tail.startswith('#'):
                raise _invalid(line)
            return ''.join(result)
        if char == '\\' and i + 1 < len(raw) and raw[i + 1] in {quote, '\\'}:
            i += 1
            char = raw[i]
        result.append(char)
        i += 1
    raise _invalid(line)


def parse_env(text: str) -> dict[str, str]:
    """Parse literal single-line values, quotes/comments/BOM; never expand."""
    values = {}
    for number, raw in enumerate(text.lstrip('\ufeff').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].lstrip()
        name, separator, value = line.partition('=')
        name = name.strip()
        if not separator or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
            raise _invalid(number)
        if name in ALLOWED_NAMES:
            parsed = _value(value, number)
            if '\x00' in parsed:
                raise _invalid(number)
            values[name] = parsed
    return values


def load_env_file(path: str | Path | None = None, *,
                  environ: MutableMapping[str, str] | None = None,
                  cwd: Path | None = None) -> Path | None:
    """Load one file: argument, DOCVISION_ENV_FILE, or exactly cwd/.env.

    Existing environment names and their aliases win over file assignments.
    Parsing finishes before the environment is changed, so malformed files do
    not leave partially loaded credentials.
    """
    env = os.environ if environ is None else environ
    configured = path if path is not None else env.get('DOCVISION_ENV_FILE')
    explicit = configured is not None
    root = Path.cwd() if cwd is None else Path(cwd)
    selected = Path(configured) if configured is not None else root / '.env'
    if not selected.is_absolute():
        selected = root / selected
    try:
        if not selected.exists():
            if explicit:
                raise DocVisionError('Credential file was not found.')
            return None
        if selected.stat().st_size > MAX_FILE_BYTES:
            raise DocVisionError('Credential file is too large (maximum 1 MiB).')
        text = selected.read_text(encoding='utf-8-sig')
    except (OSError, UnicodeError, ValueError):
        raise DocVisionError('Could not read credential file as UTF-8.',
                             hint='Check the selected file path, permissions and encoding.') from None
    parsed = parse_env(text)
    blocked = {name for group in ENV_GROUPS if any(alias in env for alias in group) for name in group}
    for name, value in parsed.items():
        if name not in blocked:
            env.setdefault(name, value)
    return selected
