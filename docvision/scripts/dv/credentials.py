"""Load one explicitly selected credential file without shell evaluation.

Only recognized API credentials, model names and endpoints are accepted.
Automatically discovered files belong to one machine and OS user; explicitly
selected legacy env files remain usable without shell evaluation.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
import re
import hashlib
import socket
import stat
import tempfile
import secrets
import warnings
import time
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
OWNER_PREFIX = '# docvision-owner-v1: '


def _win32():
    """Load the built-in Windows security APIs; no external ACL tool required."""
    import ctypes
    from ctypes import wintypes as w
    adv = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.LocalFree.argtypes = [w.HLOCAL]
    kernel.LocalFree.restype = w.HLOCAL
    adv.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)]
    adv.GetTokenInformation.argtypes = [w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD, ctypes.POINTER(w.DWORD)]
    adv.ConvertSidToStringSidW.argtypes = [w.LPVOID, ctypes.POINTER(w.LPWSTR)]
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [w.LPCWSTR, w.DWORD, ctypes.POINTER(w.LPVOID), w.LPVOID]
    adv.GetSecurityInfo.argtypes = [w.HANDLE, ctypes.c_int, w.DWORD, ctypes.POINTER(w.LPVOID), w.LPVOID,
                                   ctypes.POINTER(w.LPVOID), w.LPVOID, ctypes.POINTER(w.LPVOID)]
    adv.GetSecurityInfo.restype = w.DWORD
    adv.GetAclInformation.argtypes = [w.LPVOID, w.LPVOID, w.DWORD, ctypes.c_int]
    adv.GetAce.argtypes = [w.LPVOID, w.DWORD, ctypes.POINTER(w.LPVOID)]
    adv.GetSecurityDescriptorControl.argtypes = [w.LPVOID, ctypes.POINTER(w.WORD), ctypes.POINTER(w.DWORD)]
    return ctypes, w, adv, kernel


def _sid_text(pointer, api) -> str:
    ctypes, w, adv, kernel = api
    value = w.LPWSTR()
    if not adv.ConvertSidToStringSidW(pointer, ctypes.byref(value)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return value.value
    finally:
        kernel.LocalFree(ctypes.cast(value, w.HLOCAL))


def _windows_sid() -> str:
    api = _win32()
    ctypes, w, adv, kernel = api
    token = w.HANDLE()
    if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        size = w.DWORD()
        adv.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not adv.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        pointer = ctypes.cast(buffer, ctypes.POINTER(w.LPVOID))[0]
        return _sid_text(pointer, api)
    finally:
        kernel.CloseHandle(token)


def _identity() -> str:
    principal = _windows_sid() if os.name == 'nt' else str(os.getuid())
    identity = f'{socket.gethostname()}\0{principal}'
    return hashlib.sha256(identity.encode('utf-8')).hexdigest()


def _private_windows(fd: int) -> None:
    """Verify a protected DACL containing only this process user's SID."""
    import msvcrt
    api = _win32()
    ctypes, w, adv, kernel = api
    handle = w.HANDLE(msvcrt.get_osfhandle(fd))
    sid = _windows_sid()
    descriptor, owner, dacl = w.LPVOID(), w.LPVOID(), w.LPVOID()
    error = adv.GetSecurityInfo(handle, 1, 0x00000005, ctypes.byref(owner), None,
                                ctypes.byref(dacl), None, ctypes.byref(descriptor))
    if error:
        raise ctypes.WinError(error)
    try:
        control, revision = w.WORD(), w.DWORD()
        if not adv.GetSecurityDescriptorControl(descriptor, ctypes.byref(control), ctypes.byref(revision)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not dacl or not control.value & 0x1000 or _sid_text(owner, api) != sid:
            raise OSError('Credential file does not have a private owner and protected DACL.')
        class AclSize(ctypes.Structure):
            _fields_ = [('count', w.DWORD), ('used', w.DWORD), ('free', w.DWORD)]
        info = AclSize()
        if not adv.GetAclInformation(dacl, ctypes.byref(info), ctypes.sizeof(info), 2):
            raise ctypes.WinError(ctypes.get_last_error())
        if info.count != 1:
            raise OSError('Credential file must grant access only to its current OS user.')
        ace = w.LPVOID()
        if not adv.GetAce(dacl, 0, ctypes.byref(ace)):
            raise ctypes.WinError(ctypes.get_last_error())
        ace_type = ctypes.c_ubyte.from_address(ace.value).value
        access = w.DWORD.from_address(ace.value + 4).value
        if ace_type != 0 or _sid_text(w.LPVOID(ace.value + 8), api) != sid or access & 0x1f01ff != 0x1f01ff:
            raise OSError('Credential file has an unexpected access rule.')
    finally:
        kernel.LocalFree(descriptor)


def _private(fd: int) -> None:
    if os.name == 'nt':
        _private_windows(fd)
    else:
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise OSError('Credential file must belong to this OS user and have mode 0600.')


def _owned(fd: int) -> None:
    if os.name != 'nt':
        if os.fstat(fd).st_uid != os.getuid():
            raise OSError('Credential file belongs to another OS user.')
        return
    import msvcrt
    api = _win32()
    ctypes, w, adv, kernel = api
    owner, descriptor = w.LPVOID(), w.LPVOID()
    error = adv.GetSecurityInfo(w.HANDLE(msvcrt.get_osfhandle(fd)), 1, 1, ctypes.byref(owner),
                                None, None, None, ctypes.byref(descriptor))
    if error:
        raise ctypes.WinError(error)
    try:
        if _sid_text(owner, api) != _windows_sid():
            raise OSError('Credential file belongs to another OS user.')
    finally:
        kernel.LocalFree(descriptor)


def _new_private_file(target: Path) -> tuple[int, Path]:
    if os.name != 'nt':
        fd, name = tempfile.mkstemp(prefix=f'{target.name}.', suffix='.part', dir=str(target.parent))
        os.fchmod(fd, 0o600)
        return fd, Path(name)
    # Create with a private DACL before any secret bytes are written. CRT open
    # handles lack WRITE_DAC, so use CreateFile rather than chmod-after-write.
    import msvcrt
    ctypes, w, adv, kernel = _win32()
    class SecurityAttributes(ctypes.Structure):
        _fields_ = [('length', w.DWORD), ('descriptor', w.LPVOID), ('inherit', w.BOOL)]
    descriptor = w.LPVOID()
    if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            f'D:P(A;;FA;;;{_windows_sid()})', 1, ctypes.byref(descriptor), None):
        raise ctypes.WinError(ctypes.get_last_error())
    kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, ctypes.POINTER(SecurityAttributes),
                                   w.DWORD, w.DWORD, w.HANDLE]
    kernel.CreateFileW.restype = w.HANDLE
    try:
        attributes = SecurityAttributes(ctypes.sizeof(SecurityAttributes), descriptor, False)
        for _ in range(10):
            path = target.with_name(f'{target.name}.{secrets.token_hex(16)}.part')
            handle = kernel.CreateFileW(str(path), 0xc0060000, 0, ctypes.byref(attributes), 1, 0x80, None)
            if handle != w.HANDLE(-1).value:
                try:
                    return msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY), path
                except BaseException:
                    kernel.CloseHandle(handle)
                    path.unlink(missing_ok=True)
                    raise
            error = ctypes.get_last_error()
            if error not in {80, 183}:
                raise ctypes.WinError(error)
        raise OSError('Could not create a unique credential staging file.')
    finally:
        kernel.LocalFree(descriptor)


def _reject_links(path: Path) -> None:
    for item in (path.absolute(), *path.absolute().parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise DocVisionError('Credential paths must not contain symlinks or reparse points.')


def _read_file(path: Path, *, require_binding: bool, purpose: str = 'load') -> dict[str, str]:
    _reject_links(path)
    try:
        before = path.lstat()
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0))
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino):
                raise OSError('Credential path changed while opening it.')
            if require_binding or purpose != 'load':
                _owned(stream.fileno())
            raw = stream.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES:
                raise DocVisionError('Credential file is too large (maximum 1 MiB).')
            text = raw.decode('utf-8-sig')
            owners = [line[len(OWNER_PREFIX):].strip() for line in text.splitlines() if line.startswith(OWNER_PREFIX)]
            if owners:
                if len(owners) != 1 or owners[0] != _identity():
                    raise DocVisionError('Credential file belongs to another machine or OS user.',
                                         hint='Use your own private skill installation or an explicit process API key.')
                if purpose != 'remove':
                    try:
                        _private(stream.fileno())
                    except OSError:
                        if purpose == 'replace':
                            return {}
                        raise
            elif purpose == 'replace':
                # Re-entering a key migrates it; never silently preserve unbound secrets.
                return {}
            parsed = parse_env(text)
            if parsed and not owners and require_binding:
                raise DocVisionError('Unbound credential file cannot be loaded automatically.',
                                     hint='Re-enter your own key with `docvision credentials set --prompt` (or --stdin).')
            return parsed
    except DocVisionError:
        raise
    except (OSError, UnicodeError, ValueError):
        raise DocVisionError('Could not safely read the credential file.',
                             hint='Use a private regular file; re-enter your key with `docvision credentials set --prompt`.') from None


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

    Automatic files must be private and bound to this machine/OS user. An
    explicitly selected unbound env file is accepted for development/import.
    Existing process API keys are usable independently of an installed file.
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
        if candidate.exists() or candidate.is_symlink():
            chosen = candidate
            break
    if chosen is None:
        if required:
            raise DocVisionError('Credential file was not found.')
        return None
    try:
        parsed = _read_file(chosen, require_binding=configured is None)
    except DocVisionError:
        if required:
            raise
        warnings.warn('Ignored an automatic credential file that is unbound, foreign, or unsafe. '
                      'Re-enter your own key with `docvision credentials set --prompt`; no fallback file was loaded.',
                      RuntimeWarning, stacklevel=2)
        return None
    if not parsed:
        return None
    blocked = {name for group in ENV_GROUPS if any(alias in env for alias in group) for name in group}
    for name, value in parsed.items():
        if name not in blocked:
            env.setdefault(name, value)
    return chosen


def read_credentials(path: str | Path | None = None) -> dict[str, str]:
    """Return the parsed names of the canonical file; values are kept private."""
    target = Path(path) if path else util.credentials_path()
    _reject_links(target)
    if not target.exists():
        return {}
    return _read_file(target, require_binding=True)


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
    if any('\n' in value or '\r' in value or '\x00' in value for value in values.values()):
        raise DocVisionError('Credentials must be single-line values.')
    _reject_links(target)
    util.ensure_dir(target.parent)
    _reject_links(target)
    if _git_state(target) == 'tracked-risk':
        raise DocVisionError(
            'Refusing to write credentials into a git work tree that does not ignore this file.',
            hint=f'Add "{target.name}" to {target.parent / ".gitignore"}, then retry.',
        )
    existing = _read_file(target, require_binding=True, purpose='replace') if target.exists() else {}
    # Re-entering a credential replaces its entire alias group. Otherwise a
    # stale higher-priority spelling can keep shadowing the newly saved value.
    for group in ENV_GROUPS:
        if any(name in values for name in group):
            for name in group:
                existing.pop(name, None)
    existing.update(values)
    body = '# docvision credentials (never commit; values are not printed by the CLI)\n'
    body += OWNER_PREFIX + _identity() + '\n'
    # Always quote values so a literal whitespace/hash/quote round-trips.
    for name, value in sorted(existing.items()):
        quoted = value.replace('\\', '\\\\').replace('"', '\\"')
        body += f'{name}="{quoted}"\n'
    temp = None
    try:
        fd, temp = _new_private_file(target)
        with os.fdopen(fd, 'wb') as stream:
            _private(stream.fileno())
            if _git_state(temp) == 'tracked-risk':
                raise DocVisionError('Credential staging files must also be ignored by git.',
                                     hint=f'Add "{target.name}.*" to the credential directory .gitignore.')
            stream.write(body.encode('utf-8'))
            stream.flush()
            os.fsync(stream.fileno())
        for attempt in range(6):
            _reject_links(target)
            try:
                os.replace(temp, target)
                break
            except OSError as exc:
                # Windows briefly denies replacement when another process is
                # examining/replacing the destination. Each writer has its own
                # private staging file, so a bounded retry cannot mix secrets.
                if os.name != 'nt' or getattr(exc, 'winerror', None) not in {5, 32, 33} or attempt == 5:
                    raise
                time.sleep(0.01 * 2 ** attempt)
    except (OSError, ValueError):
        raise DocVisionError('Could not privately save the credential file.',
                             hint='Use your own writable skill installation with private file permissions.') from None
    finally:
        if temp is not None and temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass
    return target


def remove_credentials(path: str | Path | None = None) -> int:
    """Delete stored credentials; returns how many names were removed."""
    target = Path(path) if path else util.credentials_path()
    _reject_links(target)
    if not target.exists():
        return 0
    # Explicit removal may delete an old unbound file, but never another user's
    # bound file. Values are neither printed nor loaded into the process.
    removed = len(_read_file(target, require_binding=False, purpose='remove'))
    try:
        target.unlink()
    except OSError as exc:
        raise DocVisionError(f'Could not remove the credential file: {exc}') from None
    return removed
