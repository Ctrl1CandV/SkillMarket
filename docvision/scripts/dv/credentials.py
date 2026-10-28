"""Load one explicitly selected credential file without shell evaluation.

Only recognized API credentials, model names and endpoints are accepted. This
module never prints values or writes a credential/configuration file.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
import re
from collections.abc import MutableMapping

from . import util
from .base import DocVisionError


# Group aliases so a preexisting environment value wins even when a file uses
# a higher-priority spelling. Within a file, provider lookup order still applies.
ENV_GROUPS = (
    ('DOCVISION_PADDLE_TOKEN', 'PADDLEOCR_ACCESS_TOKEN', 'PADDLEOCR_API_TOKEN', 'AI_STUDIO_TOKEN', 'PADDLEAPIKEY'),
    ('DOCVISION_VLM_API_KEY',),
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
    """Load one file: argument, DOCVISION_ENV_FILE, the skill folder, or cwd/.env.

    The skill-folder file is the canonical location so a single install keeps
    its credentials in a predictable place instead of scattering `.env` files
    across projects.  Existing environment names and their aliases win over
    file assignments.  Parsing finishes before the environment is changed, so a
    malformed file cannot leave partially loaded credentials.
    """
    env = os.environ if environ is None else environ
    configured = path if path is not None else env.get('DOCVISION_ENV_FILE')
    root = Path.cwd() if cwd is None else Path(cwd)
    if configured is not None:
        selected = Path(configured)
        candidates = [selected if selected.is_absolute() else root / selected]
        required = True
    else:
        candidates = [util.credentials_path(), root / '.env']
        required = False
    chosen = None
    for candidate in candidates:
        if candidate.exists():
            chosen = candidate
            break
    if chosen is None:
        if required:
            raise DocVisionError('Credential file was not found.')
        return None
    try:
        if chosen.stat().st_size > MAX_FILE_BYTES:
            raise DocVisionError('Credential file is too large (maximum 1 MiB).')
        text = chosen.read_text(encoding='utf-8-sig')
    except (OSError, UnicodeError, ValueError):
        raise DocVisionError('Could not read credential file as UTF-8.',
                             hint='Check the selected file path, permissions and encoding.') from None
    parsed = parse_env(text)
    blocked = {name for group in ENV_GROUPS if any(alias in env for alias in group) for name in group}
    for name, value in parsed.items():
        if name not in blocked:
            env.setdefault(name, value)
    return chosen


def read_credentials(path: str | Path | None = None) -> dict[str, str]:
    """Return the parsed names of the canonical file; values are kept private."""
    target = Path(path) if path else util.credentials_path()
    try:
        return parse_env(target.read_text(encoding='utf-8-sig'))
    except (OSError, UnicodeError):
        return {}


def _git_state(target: Path) -> str:
    """'ignored', 'tracked-risk' (inside a repo but not ignored) or 'no-repo'."""
    git = shutil.which('git')
    if not git or not target.parent.is_dir():
        return 'no-repo'
    try:
        proc = subprocess.run([git, 'check-ignore', '-q', '--', target.name],
                              cwd=str(target.parent), capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return 'no-repo'
    if proc.returncode == 0:
        return 'ignored'
    if proc.returncode == 1:
        return 'tracked-risk'
    return 'no-repo'


def save_credentials(values: dict[str, str], path: str | Path | None = None) -> Path:
    """Write recognized names to the fixed file with restrictive permissions.

    Refuses to write a secret into a git work tree that does not ignore it.
    """
    target = Path(path) if path else util.credentials_path()
    values = {name: value for name, value in values.items() if name in ALLOWED_NAMES and value}
    if not values:
        raise DocVisionError('No recognized credential name to save.',
                             hint='Use PADDLEOCR_ACCESS_TOKEN for the PaddleOCR official API.')
    util.ensure_dir(target.parent)
    if _git_state(target) == 'tracked-risk':
        raise DocVisionError(
            'Refusing to write credentials into a git work tree that does not ignore this file.',
            hint=f'Add "{target.name}" to {target.parent / ".gitignore"}, then retry.',
        )
    existing = read_credentials(target)
    existing.update(values)
    body = '# docvision credentials (never commit; values are not printed by the CLI)\n'
    body += ''.join(f'{name}={value}\n' for name, value in sorted(existing.items()))
    temp = target.with_name(target.name + '.tmp')
    try:
        temp.write_text(body, encoding='utf-8')
        os.chmod(temp, 0o600)
        os.replace(temp, target)
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass
    os.chmod(target, 0o600)
    return target


def remove_credentials(path: str | Path | None = None) -> int:
    """Delete stored credentials; returns how many names were removed."""
    target = Path(path) if path else util.credentials_path()
    if not target.exists():
        return 0
    removed = len(read_credentials(target))
    try:
        target.unlink()
    except OSError as exc:
        raise DocVisionError(f'Could not remove the credential file: {exc}') from None
    return removed
