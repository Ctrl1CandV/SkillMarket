"""Small, dependency-free helpers shared by the CLI and providers."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable

from .base import DocVisionError

IS_WINDOWS = os.name == "nt"
HOME = Path.home()
SUPPORTED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".jp2"}
SUPPORTED_DOC_EXT = {".pdf"}
SUPPORTED_NATIVE_EXT = {
    ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".rtf",
    ".odt", ".ods", ".odp", ".epub", ".ofd", ".html", ".htm",
    ".mhtml", ".mht", ".csv", ".tsv",
}
SUPPORTED_EXT = SUPPORTED_IMAGE_EXT | SUPPORTED_DOC_EXT | SUPPORTED_NATIVE_EXT


def app_dir() -> Path:
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        return Path(base or (HOME / "AppData" / "Local")) / "docvision"
    base = os.environ.get("XDG_DATA_HOME")
    return Path(base or (HOME / ".local" / "share")) / "docvision"


def config_dir() -> Path:
    if IS_WINDOWS:
        base = os.environ.get("APPDATA")
        return Path(base or (HOME / "AppData" / "Roaming")) / "docvision"
    base = os.environ.get("XDG_CONFIG_HOME")
    return Path(base or (HOME / ".config")) / "docvision"


def cache_dir() -> Path:
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA")
        return Path(base or (HOME / "AppData" / "Local")) / "docvision" / "cache"
    base = os.environ.get("XDG_CACHE_HOME")
    return Path(base or (HOME / ".cache")) / "docvision"


def config_path() -> Path:
    return Path(os.environ.get("DOCVISION_CONFIG") or (config_dir() / "config.json"))


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def which(name: str) -> str | None:
    return shutil.which(name)


def env_value(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def is_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def suffix_of(value: str) -> str:
    if is_url(value):
        return Path(urllib.parse.urlsplit(value).path).suffix.lower()
    return Path(value).suffix.lower()


def is_supported(value: str) -> bool:
    return is_url(value) or suffix_of(value) in SUPPORTED_EXT


def safe_slug(value: str, limit: int = 80) -> str:
    """A readable filename that still works on Windows and POSIX.

    Unicode is kept (Chinese filenames are common here), but path separators,
    control characters and Windows-reserved characters are replaced.
    """
    name = Path(value).stem if not is_url(value) else Path(urllib.parse.urlsplit(value).path).stem
    name = unicodedata.normalize("NFKC", name or "document")
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip(" ._")
    name = name or "document"
    if len(name) > limit:
        name = name[:limit].rstrip(" ._")
    return name


def short_hash(value: str | bytes, n: int = 8) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8", errors="replace")
    return hashlib.sha1(value).hexdigest()[:n]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def data_id_for(value: str) -> str:
    """MinerU only accepts ASCII letters, digits, `_-.` in data_id."""
    return "docvision-" + short_hash(value, 16)


def human_bytes(n: int | float | None) -> str:
    if n is None:
        return "unknown"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def run(cmd: list[str], *, timeout: int = 900, cwd: Path | None = None,
        env: dict[str, str] | None = None, check: bool = False) -> subprocess.CompletedProcess:
    """Run a subprocess with UTF-8 output, even on a Chinese Windows console."""
    merged = os.environ.copy()
    merged.setdefault("PYTHONUTF8", "1")
    merged.setdefault("PYTHONIOENCODING", "utf-8")
    if env:
        merged.update(env)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=merged,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DocVisionError(f"Executable not found: {cmd[0]}", hint="Run `docvision doctor` or `docvision setup`.") from exc
    except subprocess.TimeoutExpired as exc:
        raise DocVisionError(f"Command timed out after {timeout}s: {cmd[0]}",
                             hint="Reduce --pages, use a faster tier, or raise --timeout.") from exc
    if check and proc.returncode != 0:
        tail = tail_text(proc)
        raise DocVisionError(f"{Path(cmd[0]).name} failed (exit {proc.returncode}).\n{tail}")
    return proc


def tail_text(proc: subprocess.CompletedProcess | None, limit: int = 2500) -> str:
    if proc is None:
        return ""
    text = (proc.stderr or "") + "\n" + (proc.stdout or "")
    text = text.strip()
    return text[-limit:]


def atomic_write(path: Path, data: bytes | str) -> None:
    ensure_dir(path.parent)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data.encode("utf-8") if isinstance(data, str) else data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def write_json(path: Path, value) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def download(url: str, *, timeout: int = 120, headers: dict[str, str] | None = None,
             max_bytes: int | None = None) -> bytes:
    req = urllib.request.Request(url, headers=headers or {})
    req.add_header("User-Agent", "docvision/0.1")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if max_bytes is not None and total > max_bytes:
                    raise DocVisionError(f"Download exceeds {human_bytes(max_bytes)}: {url}")
                chunks.append(chunk)
            return b"".join(chunks)
    except urllib.error.HTTPError as exc:
        body = exc.read(800).decode("utf-8", errors="replace")
        raise DocVisionError(f"HTTP {exc.code} while downloading {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise DocVisionError(f"Network error while downloading {url}: {exc.reason}") from exc


def post_json(url: str, payload, *, timeout: int = 120,
              headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "docvision/0.1")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        raise DocVisionError(f"Network error while calling {url}: {exc.reason}") from exc


def get_json(url: str, *, timeout: int = 60,
             headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "docvision/0.1")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        raise DocVisionError(f"Network error while calling {url}: {exc.reason}") from exc


def put_file_unsigned(url: str, path: Path, *, timeout: int = 300) -> int:
    """PUT a file without urllib's automatic Content-Type.

    Signed OSS URLs for MinerU include the headers in the signature; urllib
    adds ``application/x-www-form-urlencoded`` when it sees a body, which breaks
    the signature.  http.client lets us send only Content-Length.
    """
    import http.client

    split = urllib.parse.urlsplit(url)
    conn_cls = http.client.HTTPSConnection if split.scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(split.hostname, split.port, timeout=timeout)
    target = split.path + (("?" + split.query) if split.query else "")
    size = path.stat().st_size
    try:
        conn.putrequest("PUT", target)
        conn.putheader("Content-Length", str(size))
        conn.endheaders()
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                conn.send(chunk)
        resp = conn.getresponse()
        body = resp.read(800)
        if resp.status >= 300:
            raise DocVisionError(f"Upload failed: HTTP {resp.status} {body.decode('utf-8', 'replace')}")
        return resp.status
    finally:
        conn.close()


def mime_for(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def data_uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def b64decode(value: str) -> bytes:
    if "," in value and value.lstrip().startswith("data:"):
        value = value.split(",", 1)[1]
    return base64.b64decode(value)


def clamp_bbox(value) -> list[float] | None:
    try:
        if not value or len(value) < 4:
            return None
        x0, y0, x1, y1 = (float(value[i]) for i in range(4))
        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0
        return [max(0.0, min(1.0, x0)), max(0.0, min(1.0, y0)),
                max(0.0, min(1.0, x1)), max(0.0, min(1.0, y1))]
    except (TypeError, ValueError):
        return None


def normalize_bbox_pixels(bbox, width, height) -> list[float] | None:
    """Convert pixel coordinates to normalised coordinates (do not clamp first)."""
    if not bbox or len(bbox) < 4 or not width or not height:
        return None
    try:
        x0, y0, x1, y1 = (float(bbox[i]) for i in range(4))
        w, h = float(width), float(height)
    except (TypeError, ValueError):
        return None
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    return clamp_bbox([x0 / w, y0 / h, x1 / w, y1 / h])


def parse_pages(spec: str | None, total: int | None = None) -> list[int] | None:
    """Parse 1-based page ranges into 0-based indices.

    Supports MinerU/Paddle-style ``1-5,8`` and reverse-from-end ``r3-r1``.
    Returns None for "all" / omitted.
    """
    if not spec or spec.strip().lower() == "all":
        return None
    result: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if re.fullmatch(r"r\d+", part):
            if total is None:
                raise DocVisionError("Reverse page ranges need a page count.")
            idx = total - int(part[1:])
            result.append(idx)
        elif re.fullmatch(r"\d+", part):
            result.append(int(part) - 1)
        elif re.fullmatch(r"\d+-\d+", part):
            a, b = (int(x) for x in part.split("-"))
            step = 1 if b >= a else -1
            result.extend(range(a - 1, b, step))
        elif re.fullmatch(r"r\d+-r\d+", part):
            if total is None:
                raise DocVisionError("Reverse page ranges need a page count.")
            a, b = (total - int(x[1:]) for x in part.split("-"))
            step = 1 if b >= a else -1
            result.extend(range(a, b + step, step))
        else:
            raise DocVisionError(f"Unsupported page range: {part!r}",
                                 hint="Use examples like 1-5,8 or r3-r1; comma lists are supported.")
    if not result:
        return None
    if total is not None:
        result = [i for i in result if 0 <= i < total]
    return sorted(set(result))


def page_label(spec: str | None) -> str:
    return "all" if not spec else spec


def split_pdf_pages(source: Path, spec: str | None, out_dir: Path) -> tuple[Path, list[int]]:
    """Split a PDF by page range using pypdf if available."""
    total = pdf_page_count(source)
    indices = parse_pages(spec, total)
    if indices is None:
        return source, list(range(total or 0))
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise DocVisionError("Page selection for this backend needs pypdf.",
                             hint="Run `docvision setup --profile core`, or omit --pages.") from exc
    reader = PdfReader(str(source))
    writer = PdfWriter()
    for idx in indices:
        writer.add_page(reader.pages[idx])
    dest = out_dir / f"{source.stem}-pages-{short_hash(spec, 6)}.pdf"
    with dest.open("wb") as fh:
        writer.write(fh)
    return dest, indices


def pdf_page_count(path: Path) -> int | None:
    try:
        import pypdfium2 as pdfium  # type: ignore
        doc = pdfium.PdfDocument(str(path))
        try:
            return len(doc)
        finally:
            doc.close()
    except Exception:
        pass
    try:
        import fitz  # type: ignore
        with fitz.open(str(path)) as doc:
            return doc.page_count
    except Exception:
        return None


def pdf_text_stats(path: Path) -> dict:
    """Return rough text/image statistics used only for routing hints."""
    try:
        import fitz  # type: ignore
    except Exception:
        return {}
    try:
        with fitz.open(str(path)) as doc:
            chars = 0
            images = 0
            for page in doc:
                chars += len((page.get_text("text") or "").strip())
                images += len(page.get_images(full=True))
            pages = max(1, doc.page_count)
            return {"pages": doc.page_count, "chars": chars,
                    "chars_per_page": round(chars / pages, 1), "images": images}
    except Exception:
        return {}


def render_pdf_page(path: Path, index: int, *, dpi: int = 150) -> bytes:
    try:
        import pypdfium2 as pdfium  # type: ignore
        doc = pdfium.PdfDocument(str(path))
        try:
            page = doc[index]
            bitmap = page.render(scale=dpi / 72.0)
            pil = bitmap.to_pil()
            from io import BytesIO
            buf = BytesIO()
            pil.save(buf, format="PNG")
            return buf.getvalue()
        finally:
            doc.close()
    except ImportError:
        pass
    try:
        import fitz  # type: ignore
        with fitz.open(str(path)) as doc:
            pix = doc[index].get_pixmap(dpi=dpi)
            return pix.tobytes("png")
    except ImportError as exc:
        raise DocVisionError("Rendering PDF pages needs pypdfium2 or PyMuPDF.",
                             hint="Run `docvision setup --profile core`.") from exc
    except Exception as exc:
        raise DocVisionError(f"Could not render page {index + 1}: {exc}") from exc


def image_dimensions(data: bytes) -> tuple[int, int] | None:
    try:
        from PIL import Image  # type: ignore
        from io import BytesIO
        with Image.open(BytesIO(data)) as img:
            return img.width, img.height
    except Exception:
        pass
    # Minimal PNG/JPEG header fallback
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h = int.from_bytes(data[i + 5:i + 7], "big")
                w = int.from_bytes(data[i + 7:i + 9], "big")
                return w, h
            if marker in (0xD8, 0xD9):
                i += 2
                continue
            seg = int.from_bytes(data[i + 2:i + 4], "big")
            i += 2 + seg
    return None


def crop_image(data: bytes, bbox: list[float] | None, out: Path) -> Path | None:
    if not bbox:
        return None
    try:
        from PIL import Image  # type: ignore
        from io import BytesIO
        with Image.open(BytesIO(data)) as img:
            w, h = img.size
            box = (int(bbox[0] * w), int(bbox[1] * h), int(bbox[2] * w), int(bbox[3] * h))
            box = (max(0, box[0]), max(0, box[1]), min(w, box[2]), min(h, box[3]))
            if box[2] <= box[0] or box[3] <= box[1]:
                return None
            ensure_dir(out.parent)
            img.crop(box).save(out)
            return out
    except Exception:
        return None


def make_contact_sheet(images: list[Path], out: Path, *, cols: int = 4,
                       thumb_width: int = 380) -> Path | None:
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None
    if not images:
        return None
    thumbs = []
    for path in images:
        try:
            with Image.open(path) as img:
                img = img.convert("RGB")
                ratio = thumb_width / max(1, img.width)
                thumbs.append(img.resize((thumb_width, max(1, int(img.height * ratio)))))
        except Exception:
            continue
    if not thumbs:
        return None
    rows = (len(thumbs) + cols - 1) // cols
    cell_h = max(t.height for t in thumbs) + 24
    sheet = Image.new("RGB", (cols * thumb_width, rows * cell_h), "white")
    for i, thumb in enumerate(thumbs):
        x = (i % cols) * thumb_width
        y = (i // cols) * cell_h + 20
        sheet.paste(thumb, (x, y))
    ensure_dir(out.parent)
    sheet.save(out)
    return out


def expand_inputs(items: Iterable[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for item in items:
        if is_url(item):
            if item not in seen:
                seen.add(item)
                expanded.append(item)
            continue
        path = Path(item).expanduser()
        if path.is_dir():
            for child in sorted(path.iterdir()):
                if child.is_file() and is_supported(child.name):
                    key = str(child.resolve())
                    if key not in seen:
                        seen.add(key)
                        expanded.append(str(child))
        else:
            key = str(path.resolve()) if path.exists() else str(path)
            if key not in seen:
                seen.add(key)
                expanded.append(str(path))
    return expanded


def parse_kv_list(value: str | None) -> dict[str, str]:
    result: dict[str, str] = {}
    if not value:
        return result
    for pair in value.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def platform_summary() -> dict:
    import platform
    return {
        "os": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "executable": sys.executable,
    }


def total_ram_gb() -> float | None:
    try:
        if IS_WINDOWS:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return round(stat.ullTotalPhys / (1024 ** 3), 1)
        if hasattr(os, "sysconf"):
            return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024 ** 3), 1)
    except Exception:
        return None
    return None


def gpu_summary() -> dict:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {"available": False, "detail": "nvidia-smi not found"}
    try:
        proc = run([exe, "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader"], timeout=15)
        lines = [x.strip() for x in (proc.stdout or "").splitlines() if x.strip()]
        if proc.returncode != 0 or not lines:
            return {"available": False, "detail": tail_text(proc, 400)}
        gpus = []
        for line in lines:
            parts = [x.strip() for x in line.split(",")]
            gpus.append({"name": parts[0] if parts else "GPU",
                         "vram": parts[1] if len(parts) > 1 else "unknown",
                         "driver": parts[2] if len(parts) > 2 else "unknown"})
        return {"available": True, "gpus": gpus}
    except Exception as exc:
        return {"available": False, "detail": str(exc)}


def conda_envs() -> dict[str, Path]:
    """Return conda env name -> prefix, without assuming conda is on PATH."""
    result: dict[str, Path] = {}
    conda = shutil.which("conda")
    if conda:
        try:
            proc = run([conda, "env", "list", "--json"], timeout=30)
            data = json.loads(proc.stdout or "{}")
            for env in data.get("envs", []):
                p = Path(env)
                result[p.name] = p
        except Exception:
            pass
    for base in (Path.home() / ".conda" / "envs", Path.home() / "miniconda3" / "envs",
                 Path.home() / "anaconda3" / "envs", Path("C:/ProgramData/miniconda3/envs"),
                 Path("C:/ProgramData/anaconda3/envs")):
        if base.is_dir():
            for child in base.iterdir():
                if child.is_dir():
                    result.setdefault(child.name, child)
    return result


def env_bin(prefix: Path) -> Path:
    return prefix / ("Scripts" if IS_WINDOWS else "bin")


def env_python(prefix: Path) -> Path:
    """Python path for either a conda prefix or a venv prefix."""
    if IS_WINDOWS:
        candidates = [prefix / "python.exe", prefix / "Scripts" / "python.exe"]
    else:
        candidates = [prefix / "bin" / "python", prefix / "python"]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def resolve_env_exe(name: str, env_name: str | None = None) -> str | None:
    candidates: list[Path] = []
    if env_name:
        prefix = conda_envs().get(env_name)
        if prefix:
            candidates.append(env_bin(prefix) / (name + (".exe" if IS_WINDOWS else "")))
    found = shutil.which(name)
    if found:
        return found
    for prefix in conda_envs().values():
        for exe in (name, name + ".exe"):
            p = env_bin(prefix) / exe
            if p.is_file():
                candidates.append(p)
    for p in candidates:
        if p.is_file():
            return str(p)
    return None


def redact(text: str, secrets: Iterable[str | None]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def error_hint_for_http(status: int, body: str) -> str:
    lowered = (body or "").lower()
    if status in (401, 403) or "auth" in lowered or "token" in lowered:
        return "Check the API key/token and whether it has expired."
    if status == 429 or "rate" in lowered or "quota" in lowered:
        return "Rate limit or quota reached; retry later or switch provider."
    if status == 413 or "too large" in lowered or "size" in lowered:
        return "File is too large for this provider; split pages or use a local engine."
    if status >= 500:
        return "Provider-side error; retry, or use another provider."
    return "Inspect the provider response above; no upload is retried automatically."
