# /// script
# requires-python = ">=3.12"
# ///
"""Single-paper master records and note saving (grad-radar, phase 1). One authoritative JSON record per paper.

Scope (implementation plan §9.7): this script only saves output the host model has **already produced from evidence**.
It does not call a model, judge paper quality, or read directories the user did not specify. Its mechanical responsibilities
are identity normalization, deduplication, status updates, writing notes, and protecting existing notes.

Commands:
  register        Register or return a paper record (idempotent by identity; never merge by title alone)
  show            Show one paper (paper_id, arXiv ID, or title substring; list candidates for ambiguous matches)
  list            List by status/type (read-only; history and annotations are not master records)
  save-note       Save an AI note and actual source coverage (history snapshot and human-edit protection)
  set-status      Record a reading status explicitly stated by the user (a user action; read requires a quote)
  update-context  Update classification/source metadata/reading depth (preserves user annotations and read time)

Invariants:
- register/save-note **cannot** set reading.status to read/deferred. Only set-status can record a user's explicit statement; a generated note does not mean the user finished reading.
- Restrict all writes to this project's `.grad/`; update via atomic replacement of a temporary file in the same directory so failures do not leave false completion.
- If an existing AI note was changed externally (hash mismatch) or an old note has no recorded hash, refuse full replacement by default (CONFLICT). Offer --merge to append a supplement or --new-path to save a separate draft. AI never reads/writes/overwrites `.user.md` annotation files.
- Be tolerant when reading (accept older records with missing fields) and strict when writing (fully validate new records).

Input contract: pass structured UTF-8 JSON through --input-file. With --json, stdout prints
{"ok": true, "data": ...} or {"ok": false, "error": ..., "detail": ...}.
Error categories: BAD_ARGS / NOT_FOUND / AMBIGUOUS_IDENTITY / CONFLICT / SOURCE_UNAVAILABLE /
WRITE_FAILED。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

IMPORTANCE_VALUES = {"core", "relevant", "peripheral", "unknown"}
DIFFICULTY_VALUES = {"accessible", "needs_background", "challenging", "unknown"}
PAPER_TYPE_VALUES = {"method", "survey", "theory", "system", "evaluation", "other"}
MODE_VALUES = {"quick", "standard", "deep"}
STATUS_VALUES = {"unread", "reading", "read", "deferred"}
# Actual source-capability enum (§5.3); not limited to arxiv_html/mineru.
PARSER_VALUES = {"arxiv_html", "host_pdf", "external_parser", "user_text", "metadata_only"}
BASIS_VALUES = {"metadata", "abstract", "sections", "fulltext", "unavailable"}
VERSION_STATUS_VALUES = {"confirmed", "cache-fallback", "unknown", "legacy"}
USER_STATUS_VALUES = {"reading", "read", "deferred"}  # set-status values; register defaults to unread
ARXIV_NEW_RE = re.compile(r"^\d{4}\.\d{4,5}$")
ARXIV_OLD_RE = re.compile(r"^[a-z][a-z-]*(?:\.[a-z]{2})?/\d{7}$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def die(error: str, detail: str, **extra) -> None:
    print(json.dumps({"ok": False, "error": error, "detail": detail, **extra}, ensure_ascii=False))
    sys.exit(1)


def now_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------- Identity (§9.2) ----------

def normalize_arxiv(raw: str) -> str:
    """Return the arXiv base ID without the arxiv: prefix or version suffix; material version is not identity."""
    s = str(raw).strip().lower().removeprefix("arxiv:")
    s = re.sub(r"v\d+$", "", s)
    if ARXIV_NEW_RE.match(s) or ARXIV_OLD_RE.match(s):
        return s
    die("BAD_ARGS", f"arxiv_id is not a valid arXiv base ID: {raw!r}")
    raise AssertionError


def normalize_doi(raw: str) -> str:
    """Normalize DOI case and remove display-URL prefixes only; **accept verified DOIs only, never guess or invent one**."""
    s = str(raw).strip()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I)
    s = re.sub(r"^doi\s*:", "", s, flags=re.I).strip()
    if not s or " " in s or not re.search(r"10\.\d{4,9}/\S+", s):
        die("BAD_ARGS", f"doi is not a verifiable DOI (must contain a 10.xxxx/ suffix; no guessed completion): {raw!r}")
    return s.lower()


def normalize_file_sha(raw: str) -> str:
    s = str(raw).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", s):
        die("BAD_ARGS", f"file_sha256 must be a 64-character hexadecimal content hash: {raw!r}")
    return s


def derive_paper_id(identifiers: dict) -> str:
    """Stable key: prefer arXiv base ID, then DOI/content hash (truncate hash for filename; store full value in identifiers)."""
    if identifiers.get("arxiv_id"):
        return "arxiv-" + normalize_arxiv(identifiers["arxiv_id"]).replace("/", "_")
    if identifiers.get("doi"):
        return "doi-" + sha256_text(normalize_doi(identifiers["doi"]))[:16]
    if identifiers.get("file_sha256"):
        return "sha-" + normalize_file_sha(identifiers["file_sha256"])[:16]
    die("BAD_ARGS", "identifiers must contain at least one verifiable identity (arxiv_id / doi / file_sha256). "
                    "A title alone cannot create a master record; provide a link, DOI, or file hash. "
                    "Title search and human confirmation are separate.")
    raise AssertionError


# ---------- Path guard (§9.6, rule 8) ----------

def grad_root(repo: Path) -> Path:
    grad = (repo / ".grad").resolve()
    if not grad.is_relative_to(repo.resolve()):
        die("BAD_ARGS", f".grad resolves outside the project: {grad}")
    return grad


def resolve_under_grad(grad: Path, rel_or_abs: str, error_hint: str = "") -> Path:
    """Resolve note.path and similar paths inside .grad/; reject path traversal."""
    p = Path(rel_or_abs)
    full = (grad / p) if not p.is_absolute() else p
    try:
        resolved = full.resolve()
    except OSError as exc:
        die("BAD_ARGS", f"Could not resolve path: {rel_or_abs} ({exc})")
    if not resolved.is_relative_to(grad):
        die("BAD_ARGS", f"Write path must be inside the project .grad/: {rel_or_abs}{('; ' + error_hint) if error_hint else ''}")
    return resolved


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temp.write_text(content, encoding="utf-8", newline="\n")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


# ---------- Record I/O (§9.3: tolerant reads, strict writes) ----------

def papers_dir(grad: Path) -> Path:
    return grad / "radar" / "papers"


def record_path(grad: Path, paper_id: str, *, strict: bool = True) -> Path | None:
    """Map paper_id to a record path; with strict=False, unsafe keys return None for title-search fallback."""
    if not SAFE_ID_RE.match(paper_id) or "/" in paper_id or "\\" in paper_id:
        if not strict:
            return None
        die("BAD_ARGS", f"paper_id is not a filename-safe record key: {paper_id!r}")
    return papers_dir(grad) / f"{paper_id}.json"


def load_record(grad: Path, paper_id: str) -> dict | None:
    f = record_path(grad, paper_id, strict=False)
    if f is None or not f.is_file():
        return None
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die("BAD_RECORD", f"Could not parse {f}: {exc}")
    return data if isinstance(data, dict) else None


def save_record(grad: Path, record: dict) -> None:
    record["updated_at"] = now_local()
    f = record_path(grad, str(record["paper_id"]))
    try:
        atomic_write(f, json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    except OSError as exc:
        die("WRITE_FAILED", f"Failed to write master record (not reporting success): {exc}")


def iter_records(grad: Path) -> list[dict]:
    """Scan papers/ (direct scan of the initially small JSON set; ignore tmp/hidden files)."""
    out = []
    d = papers_dir(grad)
    for f in sorted(d.glob("*.json")) if d.is_dir() else []:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue  # Skip a malformed row in list view; show by ID reports its error.
        if isinstance(data, dict) and data.get("paper_id"):
            out.append(data)
    return out


def validate_enum(value: object, allowed: set[str], field: str, errors: list[str],
                  *, optional: bool = False) -> None:
    if value is None and optional:
        return
    if not isinstance(value, str) or value not in allowed:
        errors.append(f"{field} must be one of {'/'.join(sorted(allowed))}; got {value!r}")


def validate_classification(cls: object, errors: list[str]) -> None:
    if cls is None:
        return
    if not isinstance(cls, dict):
        errors.append("classification must be an object")
        return
    validate_enum(cls.get("importance"), IMPORTANCE_VALUES, "classification.importance", errors)
    validate_enum(cls.get("difficulty"), DIFFICULTY_VALUES, "classification.difficulty", errors)
    validate_enum(cls.get("paper_type"), PAPER_TYPE_VALUES, "classification.paper_type", errors)
    for reason in ("importance_reason", "difficulty_reason", "type_reason"):
        value = cls.get(reason)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            errors.append(f"classification.{reason} must be a non-empty string (include a separate reason for each dimension)")
    if not isinstance(cls.get("provisional"), bool):
        errors.append("classification.provisional must be a boolean (true only for abstract-based assessment)")


def validate_note_fields(note: dict, errors: list[str]) -> None:
    """Strictly validate the note section assembled by save-note (shared write gate)."""
    validate_enum(note.get("basis"), BASIS_VALUES, "note.basis", errors)
    sv = note.get("source_version")
    if sv is not None and (not isinstance(sv, str) or not re.fullmatch(r"v\d+", sv)):
        errors.append("note.source_version must use vN format or be null")
    for field in ("sections", "pages", "figures_viewed", "tables_checked", "limitations"):
        if not isinstance(note.get(field), list):
            errors.append(f"note.{field} must be an array")


# ---------- register ----------

def cmd_register(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    grad = grad_root(repo)
    if not args.input_file:
        die("BAD_ARGS", "register requires --input-file (UTF-8 JSON); avoid building long JSON in the shell")
    try:
        payload = json.loads(Path(args.input_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die("BAD_ARGS", f"Could not read/parse --input-file: {exc}")
    if not isinstance(payload, dict):
        die("BAD_ARGS", "Input root must be a JSON object")

    identifiers = payload.get("identifiers") or {}
    if not isinstance(identifiers, dict):
        die("BAD_ARGS", "identifiers must be an object")
    arxiv_id = normalize_arxiv(identifiers["arxiv_id"]) if identifiers.get("arxiv_id") else None
    doi = normalize_doi(identifiers["doi"]) if identifiers.get("doi") else None
    file_sha = normalize_file_sha(identifiers["file_sha256"]) if identifiers.get("file_sha256") else None
    if not (arxiv_id or doi or file_sha):
        die("AMBIGUOUS_IDENTITY",
            "Missing verifiable identity (provide at least one of arxiv_id / doi / file_sha256). "
            "A title is for search and human confirmation only and cannot create a master record. "
            "Provide a link/DOI/file; retain any confirmed title information in the session.")
    title = str(payload.get("title") or "").strip()
    if not title:
        die("BAD_ARGS", "title cannot be empty (do not fabricate a content note for an identity-only record)")

    paper_id = derive_paper_id({"arxiv_id": arxiv_id, "doi": doi, "file_sha256": file_sha})

    # Deduplicate by identity; same title with different identity yields candidates, never an automatic merge (R03).
    warnings: list[str] = []
    existing = load_record(grad, paper_id)
    if existing is not None:
        warnings.append(f"A master record with this identity already exists: {paper_id} (reused idempotently by both entry points)")
    if existing is None:
        for rec in iter_records(grad):
            ident = rec.get("identifiers") or {}
            match = ((arxiv_id and normalize_arxiv(ident["arxiv_id"]) == arxiv_id) if ident.get("arxiv_id") else False) \
                or ((doi and normalize_doi(ident["doi"]) == doi) if ident.get("doi") else False) \
                or ((file_sha and normalize_file_sha(ident["file_sha256"]) == file_sha) if ident.get("file_sha256") else False)
            if match:
                existing = rec
                warnings.append(f"Identity fields matched existing master record {rec['paper_id']} (both entry points share one paper record)")
                break
            if title and str(rec.get("title", "")).strip().casefold() == title.casefold():
                warnings.append(f"A record with the same title exists: {rec['paper_id']} (title is not an auto-merge key; "
                                "if this is the same paper, use update-context to add a shared identity field)")
        if existing is not None and arxiv_id:
            paper_id = str(existing["paper_id"])  # Use the stable key of the matched record.

    if existing is not None:
        # Idempotent return: preserve progress and classification; only fill missing identity fields and update source references.
        changed = False
        ident = existing.setdefault("identifiers", {})
        for key, value in (("arxiv_id", arxiv_id), ("doi", doi), ("file_sha256", file_sha)):
            if value and not ident.get(key):
                ident[key] = value
                changed = True
        source = payload.get("source")
        if isinstance(source, dict) and source:
            _update_source(existing, source, warnings)
            changed = True
        if changed:
            save_record(grad, existing)
        data = {"paper_id": existing["paper_id"], "created": False, "record": existing,
                "warnings": warnings}
        _emit(data, args.json, f"Master record already exists: {existing['paper_id']} (returned idempotently; reading status preserved)")
        return

    source_errors: list[str] = []
    record: dict = {
        "schema_version": 1,
        "paper_id": paper_id,
        "title": title,
        "identifiers": {"arxiv_id": arxiv_id, "doi": doi, "file_sha256": file_sha},
        "source": _validated_source(payload.get("source"), source_errors),
        "classification": _default_classification(payload.get("classification")),
        "reading": {"mode": None, "status": "unread", "status_updated_at": None,
                    "status_origin": None, "last_read_at": None, "last_read_version": None,
                    "status_user_quote": None},
        "note": {"path": None, "content_sha256": None, "generated_at": None,
                 "source_version": None, "basis": None, "sections": [], "pages": [],
                 "figures_viewed": [], "tables_checked": [], "limitations": []},
        "created_at": now_local(),
        "updated_at": now_local(),
    }
    errors: list[str] = []
    validate_classification(record["classification"], errors)
    if source_errors:
        die("BAD_ARGS", "Source validation failed (not written): " + "; ".join(source_errors))
    if errors:
        die("BAD_ARGS", "Classification validation failed (not written): " + "; ".join(errors))
    # Reuse legacy digest: when an old-path note can be identified by arXiv base ID, point the master note entry to it (§9.1).
    if arxiv_id and record["note"]["path"] is None:
        legacy = grad / "radar" / "digest" / f"{arxiv_id.replace('/', '_')}.md"
        if legacy.is_file():
            record["note"]["path"] = str(legacy.relative_to(grad)).replace("\\", "/")
            warnings.append(f"Found legacy digest: {record['note']['path']}; "
                            "it proves only that a note exists, not full-text coverage or that the user read it")
    save_record(grad, record)
    data = {"paper_id": paper_id, "created": True, "record": record, "warnings": warnings}
    _emit(data, args.json, f"Registered master record: {paper_id}")


def _validated_source(source: object, errors: list[str]) -> dict:
    out = {"url": None, "local_path": None, "version": None, "version_status": "unknown",
           "parser": "metadata_only", "parser_name": None, "fetched_at": None}
    if not isinstance(source, dict):
        return out
    for key in ("url", "local_path", "parser_name", "fetched_at"):
        value = source.get(key)
        if value is not None:
            out[key] = str(value)
    version = source.get("version")
    if version is not None:
        if not isinstance(version, str) or not re.fullmatch(r"v\d+", version.strip()):
            errors.append("source.version must use vN format or be null")
        else:
            out["version"] = version.strip()
    vs = source.get("version_status")
    if vs is not None:
        validate_enum(vs, VERSION_STATUS_VALUES, "source.version_status", errors)
        out["version_status"] = vs
    parser = source.get("parser")
    if parser is not None:
        validate_enum(parser, PARSER_VALUES, "source.parser", errors)
        out["parser"] = parser
    if out["version"] and out["version_status"] == "unknown":
        errors.append("A version was supplied but version_status=unknown; explicit versions must be confirmed")
    return out


def _default_classification(cls: object) -> dict:
    base = {"importance": "unknown", "importance_reason": "Not yet assessed",
            "difficulty": "unknown", "difficulty_reason": "Not yet assessed",
            "paper_type": "other", "type_reason": "Not yet assessed", "provisional": True}
    if isinstance(cls, dict):
        base.update({k: v for k, v in cls.items() if k in base})
    return base


SOURCE_FIELDS = ("url", "local_path", "version", "version_status", "parser", "parser_name", "fetched_at")


def _update_source(record: dict, source: dict, warnings: list[str]) -> None:
    """REV-04: field-level updates—omitted means keep; an explicit value (including null) replaces/clears.

    Defaults are for new records only (register initializes through _validated_source).
    Merge supplied keys into the complete source first, then validate the result.
    """
    if not isinstance(source, dict) or not source:
        die("BAD_ARGS", "source update must be a non-empty object (supply changed fields; omitted fields stay unchanged)")
    unknown = [k for k in source if k not in SOURCE_FIELDS]
    if unknown:
        die("BAD_ARGS", f"Unknown source fields {unknown}; updatable fields: {', '.join(SOURCE_FIELDS)}")
    merged = {**(record.get("source") or {})}
    for key in source:
        merged[key] = source[key]
    errors: list[str] = []
    validated = _validated_source(merged, errors)
    if errors:
        die("BAD_ARGS", "Merged source failed validation (not written): " + "; ".join(errors))
    old_version = (record.get("source") or {}).get("version")
    record["source"] = validated
    if old_version and validated.get("version") and old_version != validated["version"]:
        warnings.append(f"Source version updated: {old_version} → {validated['version']}; "
                        "reading the old version does not mean the new version was read; reading history and note source_version are unchanged")
    elif old_version and not validated.get("version"):
        warnings.append(f"Version {old_version} was cleared as unconfirmed (version_status={validated['version_status']}); "
                        "future notes must not inherit it and should confirm the version from the actual source")


# ---------- Lookup (shared by show/update) ----------

def locate_record(grad: Path, query: str) -> dict:
    """Resolve uniquely by paper_id, arXiv ID (optional version), or title substring; return candidates if ambiguous (§5.1)."""
    s = query.strip()
    if not s:
        die("BAD_ARGS", "Lookup query cannot be empty")
    direct = load_record(grad, s)
    if direct:
        return direct
    lowered = s.strip().lower().removeprefix("arxiv:")
    stripped = re.sub(r"v\d+$", "", lowered)
    if ARXIV_NEW_RE.match(stripped) or ARXIV_OLD_RE.match(stripped):
        rec = load_record(grad, "arxiv-" + stripped.replace("/", "_"))
        if rec:
            return rec
    needle = s.casefold()
    hits = [r for r in iter_records(grad)
            if needle in str(r.get("title", "")).casefold()
            or needle == str(r.get("paper_id", "")).casefold()]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        die("AMBIGUOUS_IDENTITY", "Query matched multiple records; choose from these candidates (no guessing): " +
            "；".join(f"{r['paper_id']}（{str(r.get('title', ''))[:30]}）" for r in hits[:6]),
            candidates=[r["paper_id"] for r in hits[:6]])
        die("NOT_FOUND", f"No paper record matches {query!r}; use the /grad:radar reading entry point or register it directly")
    raise AssertionError


def cmd_show(args: argparse.Namespace) -> None:
    grad = grad_root(Path(args.repo).resolve())
    record = locate_record(grad, args.paper)
    data = {"record": record}
    note_path = (record.get("note") or {}).get("path")
    if note_path:
        full = resolve_under_grad(grad, note_path)
        data["note_exists"] = full.is_file()
        data["note_external_edit"] = (
            full.is_file() and bool((record["note"] or {}).get("content_sha256"))
            and sha256_text(full.read_text(encoding="utf-8", errors="replace")) != record["note"]["content_sha256"])
    user_note = note_path[:-3] + ".user.md" if note_path and note_path.endswith(".md") else None
    if user_note:
        data["user_note_exists"] = resolve_under_grad(grad, user_note).is_file()
        data["user_note_path"] = user_note
    _emit(data, args.json, f"{record['paper_id']}｜{record.get('title')}"
                           f"｜status={record.get('reading', {}).get('status')}"
                           f"｜mode={record.get('reading', {}).get('mode')}")


def cmd_list(args: argparse.Namespace) -> None:
    grad = grad_root(Path(args.repo).resolve())
    records = iter_records(grad)  # papers/*.json are master records; digest/history/user.md are excluded.
    if args.status:
        records = [r for r in records if (r.get("reading") or {}).get("status") == args.status]
    if args.type:
        records = [r for r in records if (r.get("classification") or {}).get("paper_type") == args.type]
    records = records[: args.limit]
    items = [{"paper_id": r["paper_id"], "title": r.get("title"),
              "status": (r.get("reading") or {}).get("status"),
              "mode": (r.get("reading") or {}).get("mode"),
              "paper_type": (r.get("classification") or {}).get("paper_type"),
              "importance": (r.get("classification") or {}).get("importance"),
              "note_path": (r.get("note") or {}).get("path"),
              "last_read_at": (r.get("reading") or {}).get("last_read_at")} for r in records]
    if args.json:
        print(json.dumps({"ok": True, "data": {"count": len(items), "items": items}}, ensure_ascii=False))
        return
    print(f"{len(items)} master records")
    for item in items:
        print(f"  {item['paper_id']:<28} {str(item['title'])[:38]:<40}"
              f" status={item['status']} mode={item['mode']} type={item['paper_type']}")


# ---------- save-note ----------

MERGE_MARKER = "<!-- reading-record:ai-supplement -->"


def cmd_save_note(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    grad = grad_root(repo)
    record = locate_record(grad, args.paper)
    try:
        content = Path(args.note_file).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        die("SOURCE_UNAVAILABLE", f"Note body file is unreadable: {args.note_file}: {exc}")
    if not content.strip():
        die("BAD_ARGS", "Note body is empty; do not save an empty note as a deliverable")

    errors: list[str] = []
    validate_enum(args.mode, MODE_VALUES, "--mode", errors)
    validate_enum(args.basis, BASIS_VALUES, "--basis", errors)
    if errors:
        die("BAD_ARGS", "; ".join(errors))
    if args.source_version and not re.fullmatch(r"v\d+", args.source_version):
        die("BAD_ARGS", f"--source-version must use vN format: {args.source_version!r}")
    # REV-06: unavailable means no readable source, so no depth (including quick) can be delivered;
    # it also cannot overwrite a valid note. Use --record-failure to log retrieval failure in
    # record.note.limitations while preserving the existing note/mode, not as a substitute note.
    if args.basis == "unavailable":
        if not args.record_failure:
            die("BAD_ARGS", "basis=unavailable is not a completed deliverable: no note, including quick, can be saved without a readable source. "
                            "Use --record-failure to log retrieval failure (preserve the existing note and record only the failure/missing materials); "
                            "save again using the actual basis when an abstract/body is available.")
        # Record failure only; never write note body or change reading.mode.
        existing_note = record.get("note") or {}
        reasons = [s.strip() for s in args.record_failure.split(";") if s.strip()]
        merged_lim = list(dict.fromkeys(list(existing_note.get("limitations") or []) + reasons))
        existing_note["limitations"] = merged_lim
        record["note"] = existing_note
        save_record(grad, record)
        _emit({"paper_id": record["paper_id"], "recorded_failure": reasons,
               "note_mode_unchanged": (record.get("reading") or {}).get("mode"),
               "existing_note_preserved": bool(existing_note.get("path"))},
              args.json,
              f"Recorded retrieval failure: {reasons}; existing note and reading depth are unchanged")
        return
    if args.basis == "metadata":
        die("SOURCE_UNAVAILABLE", "Identity/title alone cannot support a content note; register only the source entry. "
                                 "Use basis=abstract after obtaining a reliable abstract.")
    # An abstract alone cannot be saved as a completed standard/deep note (§5.3).
    if args.basis == "abstract" and args.mode in ("standard", "deep"):
        warnings_mode = [f"--basis={args.basis} supports quick delivery only; "
                         "the requested standard/deep note was not completed and mode was downgraded to quick to match available material"]
        args.mode = "quick"
    else:
        warnings_mode = []

    note = record.setdefault("note", {})
    target_rel = args.new_path or note.get("path")
    if target_rel:
        target = resolve_under_grad(grad, target_rel)
    else:
        target = grad / "radar" / "digest" / f"{record['paper_id']}.md"
    if not str(target).endswith(".md"):
        die("BAD_ARGS", "Note must be a .md file")
    if target.name.endswith(".user.md"):
        die("BAD_ARGS", "save-note cannot write .user.md; the user maintains annotation files and AI must not overwrite them")

    # Parse and validate every note field before writing so invalid arguments cannot leave partial output.
    note_fields: dict = {
        # Omitted means the material version for this run is unconfirmed; an old source-record version is not a substitute.
        "source_version": args.source_version or None,
        "basis": args.basis,
        "sections": [s.strip() for s in args.sections.split(",") if s.strip()],
        "pages": _parse_pages(args.pages),
        "figures_viewed": [s.strip() for s in args.figures.split(",") if s.strip()],
        "tables_checked": [s.strip() for s in args.tables.split(",") if s.strip()],
        "limitations": [s.strip() for s in args.limitations.split(",") if s.strip()],
    }
    pre_errors: list[str] = []
    if args.basis == "sections" and not (note_fields["sections"] or note_fields["pages"]):
        pre_errors.append("basis=sections requires actual section or physical-page coverage")
    validate_note_fields({**note, **note_fields}, pre_errors)
    if pre_errors:
        die("BAD_ARGS", "Note field validation failed (nothing written): " + "; ".join(pre_errors))

    warnings: list[str] = list(warnings_mode)
    existing_text = target.read_text(encoding="utf-8", errors="replace") if target.is_file() else None
    stored_sha = note.get("content_sha256")
    has_existing = existing_text is not None and existing_text.strip()
    write_mode = "create"
    final_content = content

    # REV-01: --merge always appends when the target exists, regardless of hash conflicts.
    # If the master note has accepted human content or its hash differs, ordinary saves also protect it.
    protected = bool(note.get("has_human_content"))
    if args.merge:
        if has_existing:
            write_mode = "merge"
        else:
            write_mode = "create"  # Nothing exists to append to; create a new note.
    elif has_existing:
        external_edit = stored_sha is None or sha256_text(existing_text) != stored_sha
        if external_edit:
            # Missing legacy hash or external edits may indicate human changes; refuse replacement by default (§9.6, rule 5).
            if args.force:
                write_mode = "replace"
                warnings.append("The note was externally modified or has no recorded hash; --force replaced it after saving a history snapshot. "
                                "Manually check that overwritten edits are included in the new draft.")
            else:
                die("CONFLICT", f"Master note exists and may have human edits (missing/mismatched hash): {target}; "
                                "human content will not be overwritten. Use --merge to append, --force to snapshot then replace, or --new-path to save separately.")
        elif protected:
            # After a merge (which may include human content), even a hash-matching automatic update appends by default.
            # Replace the full note only with explicit --force.
            if args.force:
                write_mode = "replace"
            else:
                write_mode = "merge"
                warnings.append("The master note previously accepted human content; ordinary saves append to protect it. "
                                "Use --force for a full rewrite (the old draft is snapshotted to history).")
        else:
            write_mode = "replace"  # Pure AI note, matching hash, no protection marker: update and snapshot the old note.
    elif protected and not has_existing:
        write_mode = "create"

    if write_mode == "merge":
        supplement = (f"\n\n{MERGE_MARKER}\n\n---\n\n"
                      f"## Supplementary reading · {datetime.now().astimezone():%Y-%m-%d} (added this time; previous content retained)\n\n{content}")
        final_content = (existing_text or "") + supplement
    elif write_mode == "replace":
        # Save a history snapshot before updating; create history only when content actually changes (§9.6).
        if existing_text is not None and sha256_text(existing_text) != sha256_text(final_content):
            rev = 1
            history_dir = grad / "radar" / "digest" / "history" / str(record["paper_id"])
            while (history_dir / f"rev-{rev:03d}.md").exists():
                rev += 1
            try:
                atomic_write(history_dir / f"rev-{rev:03d}.md", existing_text)
                (history_dir / f"rev-{rev:03d}.reason.txt").write_text(
                    (args.history_reason or "Automatic pre-update snapshot") + f"\nsaved_at={now_local()}\n", encoding="utf-8")
            except OSError as exc:
                die("WRITE_FAILED", f"Failed to write history snapshot; note was not updated: {exc}")

    # Write the new note successfully before updating the master-record pointer (§9.6, rule 6: failed writes are not complete).
    try:
        atomic_write(target, final_content)
    except OSError as exc:
        die("WRITE_FAILED", f"Failed to write note; master record remains unchanged: {exc}")

    note["path"] = str(target.relative_to(grad)).replace("\\", "/")
    note["content_sha256"] = sha256_text(final_content)
    # REV-01: merge accepts human/supplementary content and sets the protection marker for future saves.
    # Full create/replace with AI-only content resets the baseline and clears the marker.
    if write_mode == "merge":
        note["has_human_content"] = True
    else:
        note.pop("has_human_content", None)
    note["generated_at"] = now_local()
    # REV-01: merged-note coverage must include every segment; merge and deduplicate the current range.
    if write_mode == "merge":
        note.update(_merge_note_fields(note, note_fields))
    else:
        note.update(note_fields)
        note["coverage_sources"] = [_coverage_source(note_fields)]
    # mode belongs to reading.mode (§9.3, depth of the current master note); change only the note, not human status/read time.
    record.setdefault("reading", {})["mode"] = args.mode
    save_record(grad, record)
    data = {"paper_id": record["paper_id"], "note_path": note["path"], "mode": args.mode,
            "write_mode": write_mode, "generated_at": note["generated_at"],
            "reading_status_untouched": (record.get("reading") or {}).get("status"),
            "warnings": warnings}
    _emit(data, args.json,
          f"Note saved: {note['path']} (mode={args.mode}, write={write_mode}); "
          f"human reading status remains {(record.get('reading') or {}).get('status')} — generating a note does not mean the paper was read")


def _merge_note_fields(existing: dict, incoming: dict) -> dict:
    """Preserve each segment's version and coverage in merged saves; do not describe only the last segment (REV-01)."""
    merged = dict(incoming)
    sources = existing.get("coverage_sources")
    if not isinstance(sources, list) or not sources:
        sources = [_coverage_source(existing)]
    else:
        sources = list(sources)
    new_source = _coverage_source(incoming)
    if new_source not in sources:
        sources.append(new_source)
    merged["coverage_sources"] = sources
    for key in ("sections", "pages", "figures_viewed", "tables_checked", "limitations"):
        seen = list(dict.fromkeys(list(existing.get(key) or []) + list(incoming.get(key) or [])))
        merged[key] = seen
    # source_version: report differing supplement versions honestly; do not overwrite them with a false single value.
    merged["source_version"] = existing.get("source_version")
    # basis: use the most informative level (fulltext > sections > abstract > metadata; unavailable never upgrades).
    rank = {"unavailable": 0, "metadata": 1, "abstract": 2, "sections": 3, "fulltext": 4}
    ob, nb = existing.get("basis"), incoming.get("basis")
    if ob and nb and rank.get(nb, 0) < rank.get(ob, 0):
        merged["basis"] = ob
    return merged


def _coverage_source(fields: dict) -> dict:
    """Preserve each coverage segment's actual version; keep legacy flat coverage for older consumers."""
    return {"source_version": fields.get("source_version"), "basis": fields.get("basis"),
            **{key: list(fields.get(key) or []) for key in
               ("sections", "pages", "figures_viewed", "tables_checked", "limitations")}}


def _parse_pages(text: str) -> list[int]:
    pages: list[int] = []
    for part in (p.strip() for p in (text or "").split(",")):
        if not part:
            continue
        if not part.isdigit() or int(part) < 1:
            die("BAD_ARGS", f"pages must be comma-separated physical page integers >= 1: {part!r}")
        pages.append(int(part))
    return pages


# ---------- set-status / update-context ----------

def cmd_set_status(args: argparse.Namespace) -> None:
    grad = grad_root(Path(args.repo).resolve())
    record = locate_record(grad, args.paper)
    quote = (args.user_quote or "").strip()
    if not quote:
        die("BAD_ARGS", "set-status requires --user-quote (the user's explicit statement or paraphrase of reading status); "
                        "AI-generated notes and model suggestions cannot set human reading status")
    # REV-02: last_read_version records the version actually read, not the current source version.
    # Priority: explicit --read-version > version in the lookup (e.g. --paper 2609.90003v1) > null (never guess).
    read_version = None
    if args.read_version:
        if not re.fullmatch(r"v\d+", args.read_version):
            die("BAD_ARGS", f"--read-version must use vN format: {args.read_version!r}")
        read_version = args.read_version
    else:
        qm = re.search(r"(v\d+)$", args.paper.strip())
        if qm:
            read_version = qm.group(1)
    reading = record.setdefault("reading", {})
    reading["status"] = args.status
    reading["status_updated_at"] = now_local()
    reading["status_origin"] = "user"
    reading["status_user_quote"] = quote
    if args.status == "read":
        # Record the version actually read (null without evidence; never substitute the latest source version).
        # When resuming read → reading, preserve the previous completion time/version (§8.4).
        reading["last_read_at"] = now_local()
        if read_version:
            reading["last_read_version"] = read_version
    save_record(grad, record)
    _emit({"paper_id": record["paper_id"], "status": args.status,
           "last_read_at": reading.get("last_read_at"),
           "last_read_version": reading.get("last_read_version"),
           "note_generated_at": (record.get("note") or {}).get("generated_at")},
          args.json, f"Reading status recorded (user): {args.status}"
                     + (f" | completed version {reading.get('last_read_version')}" if args.status == "read" else ""))


def cmd_update_context(args: argparse.Namespace) -> None:
    grad = grad_root(Path(args.repo).resolve())
    record = locate_record(grad, args.paper)
    warnings: list[str] = []
    changed = False
    if args.classification_json:
        try:
            cls = json.loads(Path(args.classification_json).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            die("BAD_ARGS", f"Could not read/parse --classification-json: {exc}")
        merged = {**(record.get("classification") or {}), **cls}
        errors: list[str] = []
        validate_classification(merged, errors)
        if errors:
            die("BAD_ARGS", "Classification validation failed (not written): " + "; ".join(errors))
        old_type = (record.get("classification") or {}).get("paper_type")
        record["classification"] = merged
        if args.type_reason:
            merged["type_reason"] = args.type_reason + " (classification-change explanation)"
        if old_type and merged.get("paper_type") and old_type != merged["paper_type"]:
            warnings.append(f"Primary type changed from {old_type} to {merged['paper_type']}; "
                            "classification changes require a reason (--type-reason or a reason field)")
        changed = True
    if args.source_json:
        try:
            source = json.loads(Path(args.source_json).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            die("BAD_ARGS", f"Could not read/parse --source-json: {exc}")
        _update_source(record, source, warnings)
        changed = True
    if args.difficulty_point:
        cls = record.setdefault("classification", {})
        cls["difficulty_reason"] = f"{cls.get('difficulty_reason', '')} | Difficulty point: {args.difficulty_point}".strip(" |")
        changed = True
    if args.reading_mode:
        mode_errors: list[str] = []
        validate_enum(args.reading_mode, MODE_VALUES, "--reading-mode", mode_errors)
        note = record.get("note") or {}
        basis = note.get("basis")
        if not note.get("path") or basis not in {"abstract", "sections", "fulltext"}:
            mode_errors.append("The saved note has no readable basis; context cannot set its delivered depth")
        if args.reading_mode in {"standard", "deep"} and basis not in {"sections", "fulltext"}:
            mode_errors.append("standard/deep require body-text evidence; context cannot bypass an abstract-only downgrade")
        depth_rank = {"quick": 0, "standard": 1, "deep": 2}
        old_mode = (record.get("reading") or {}).get("mode")
        if depth_rank.get(args.reading_mode, -1) > depth_rank.get(old_mode, -1):
            mode_errors.append("Upgrading delivered depth requires saving the corresponding explanation with save-note; context updates cannot replace content")
        if mode_errors:
            die("BAD_ARGS", "；".join(mode_errors))
        record.setdefault("reading", {})["mode"] = args.reading_mode
        changed = True
    if changed:
        # This operation changes classification/source/depth only; preserve user annotations and last_read_at (§9.7).
        save_record(grad, record)
    _emit({"paper_id": record["paper_id"], "record": record, "warnings": warnings,
           "changed": changed}, args.json,
          f"Updated reading context for {record['paper_id']} (status and read time unchanged)")


def _emit(data: dict, as_json: bool, summary: str) -> None:
    if as_json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
    else:
        print(summary)


def main() -> None:
    ap = argparse.ArgumentParser(description="Single-paper master records: identity, status, and note saving (store, do not judge)")
    sub = ap.add_subparsers(dest="command", required=True)

    def common(cmd: argparse.ArgumentParser, paper: bool = True) -> None:
        cmd.add_argument("--repo", default=".", help="Project root (contains .grad/)")
        if paper:
            cmd.add_argument("--paper", required=True, help="paper_id / arXiv ID (optional version) / title substring")
        cmd.add_argument("--json", action="store_true")

    p = sub.add_parser("register", help="Register or return a master record (idempotent by identity)")
    p.add_argument("--repo", default=".")
    p.add_argument("--input-file", required=True, help="UTF-8 JSON：identifiers/title/source/classification")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("show", help="Show one record (read-only)"); common(p)
    p = sub.add_parser("list", help="List master records by status/type")
    p.add_argument("--repo", default=".")
    p.add_argument("--status", choices=sorted(STATUS_VALUES), default=None)
    p.add_argument("--type", choices=sorted(PAPER_TYPE_VALUES), default=None)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("save-note", help="Save an AI master note and the source coverage actually retrieved")
    common(p)
    p.add_argument("--note-file", required=True, help="UTF-8 file containing the note body already written by the model")
    p.add_argument("--mode", required=True, choices=sorted(MODE_VALUES))
    p.add_argument("--basis", required=True, choices=sorted(BASIS_VALUES),
                   help="Actual evidence basis: metadata/abstract/sections/fulltext/unavailable")
    p.add_argument("--source-version", default="", help="Material version confirmed for this note (vN); omitted means unknown, not inherited")
    p.add_argument("--sections", default="", help="Sections read, comma-separated (S1,S3.SS2...)")
    p.add_argument("--pages", default="", help="Physical PDF pages, starting at 1, comma-separated")
    p.add_argument("--figures", default="", help="Figure IDs checked; empty means none confirmed, not full coverage")
    p.add_argument("--tables", default="", help="Table IDs checked")
    p.add_argument("--limitations", default="", help="Uncovered/limited-parsing notes, comma-separated")
    p.add_argument("--merge", action="store_true", help="Append a supplement instead of replacing on note conflict")
    p.add_argument("--force", action="store_true", help="Confirm full replacement (snapshot the old note to history first)")
    p.add_argument("--new-path", default="", help="Save as a separate draft path relative to .grad/")
    p.add_argument("--history-reason", default="", help="Snapshot reason (mode and time are recorded automatically by default)")
    p.add_argument("--record-failure", default="",
                   help="For basis=unavailable: record retrieval failure and missing materials (semicolon-separated); writes no note and changes no depth")

    p = sub.add_parser("set-status", help="Record the user's explicit reading status (the only command that can set read)")
    common(p)
    p.add_argument("--status", required=True, choices=sorted(USER_STATUS_VALUES))
    p.add_argument("--user-quote", required=True, help="User quote/paraphrase; status must reflect a user action")
    p.add_argument("--read-version", default="",
                   help="Version actually read when status=read (vN); otherwise use an explicit version in the lookup or null; never substitute the latest source version")

    p = sub.add_parser("update-context", help="Update classification/source metadata/depth; preserve annotations and read time")
    common(p)
    p.add_argument("--classification-json", default="", help="UTF-8 JSON file with classification fields and reasons")
    p.add_argument("--type-reason", default="", help="Reason for primary type change (required for reclassification)")
    p.add_argument("--source-json", default="", help="UTF-8 JSON file with source/version metadata updates")
    p.add_argument("--difficulty-point", default="", help="Specific difficulty reported by the user (appended to difficulty_reason)")
    p.add_argument("--reading-mode", choices=sorted(MODE_VALUES), default=None)

    args = ap.parse_args()
    {
        "register": cmd_register,
        "show": cmd_show,
        "list": cmd_list,
        "save-note": cmd_save_note,
        "set-status": cmd_set_status,
        "update-context": cmd_update_context,
    }[args.command](args)


if __name__ == "__main__":
    main()
