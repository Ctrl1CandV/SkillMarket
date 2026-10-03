# /// script
# requires-python = ">=3.12"
# ///
"""单篇阅读主记录与笔记保存（grad-radar·阶段 1）。每篇论文一条权威 JSON 记录。

职责边界（实施方案 §9.7）：本脚本只保存宿主模型**已依据证据完成**的输出——
它不调用模型、不判断论文质量、不读取用户未指定的目录。身份规范化、去重、
状态更新、笔记落盘与保护是它的机械职责。

操作：
  register        登记/返回论文主记录（同身份幂等；不根据标题擅自合并）
  show            读一篇（支持 paper_id／arXiv id／标题子串，多义时报候选不猜）
  list            按状态/类型列出（只读，无写入副作用；history 与批注不算主条目）
  save-note       保存 AI 主笔记 + 实际来源范围（历史快照、人工改动保护）
  set-status      记录用户明确表达的阅读状态（必须是用户动作，read 需原话引用）
  update-context  更新分类/来源资料/阅读深度（不改用户批注与已读时间）

铁律：
- register / save-note **无权**把 reading.status 设为 read/deferred——人的状态只能经
  set-status 由用户明确表达写入；生成笔记 ≠ 用户读完。
- 所有写入路径限制在本项目 `.grad/` 内；更新走同目录临时文件原子替换，失败不留假完成。
- 已有 AI 笔记被外部改动（哈希不符）或旧笔记无哈希记录时，默认拒绝整体替换
  （CONFLICT），提供 --merge（追加补充段）/ --new-path（独立草稿）出口；`.user.md`
  批注文件 AI 永不读写覆盖。
- 读取宽容（缺字段的旧记录照读），写入严格（新记录完整校验）。

输入契约：结构化输入经 --input-file 传 UTF-8 JSON。输出契约：--json 时
stdout 打印 {"ok": true, "data": ...} 或 {"ok": false, "error": ..., "detail": ...}。
错误类别：BAD_ARGS / NOT_FOUND / AMBIGUOUS_IDENTITY / CONFLICT / SOURCE_UNAVAILABLE /
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
# 实际来源能力枚举（§5.3）——不再是「只能 arxiv_html／mineru」
PARSER_VALUES = {"arxiv_html", "host_pdf", "external_parser", "user_text", "metadata_only"}
BASIS_VALUES = {"metadata", "abstract", "sections", "fulltext", "unavailable"}
VERSION_STATUS_VALUES = {"confirmed", "cache-fallback", "unknown", "legacy"}
USER_STATUS_VALUES = {"reading", "read", "deferred"}  # set-status 可设（unread 由 register 默认）
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


# ---------- 身份（§9.2） ----------

def normalize_arxiv(raw: str) -> str:
    """arXiv 基础 ID：去 arxiv: 前缀与版本号（版本是材料版本，不进身份）。"""
    s = str(raw).strip().lower().removeprefix("arxiv:")
    s = re.sub(r"v\d+$", "", s)
    if ARXIV_NEW_RE.match(s) or ARXIV_OLD_RE.match(s):
        return s
    die("BAD_ARGS", f"arxiv_id 不是合法 arXiv 基础 ID：{raw!r}")
    raise AssertionError


def normalize_doi(raw: str) -> str:
    """DOI：只规范大小写与去掉展示 URL 前缀；**仅接受实际核实的 DOI，不猜不造**。"""
    s = str(raw).strip()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I)
    s = re.sub(r"^doi\s*:", "", s, flags=re.I).strip()
    if not s or " " in s or not re.search(r"10\.\d{4,9}/\S+", s):
        die("BAD_ARGS", f"doi 不是可核实的 DOI（需含 10.xxxx/ 后缀，不做猜测补全）：{raw!r}")
    return s.lower()


def normalize_file_sha(raw: str) -> str:
    s = str(raw).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", s):
        die("BAD_ARGS", f"file_sha256 必须是 64 位十六进制内容哈希：{raw!r}")
    return s


def derive_paper_id(identifiers: dict) -> str:
    """稳定主键：arxiv 优先（基础 ID），其次 DOI/内容哈希（截断哈希做文件名，全值存 identifiers）。"""
    if identifiers.get("arxiv_id"):
        return "arxiv-" + normalize_arxiv(identifiers["arxiv_id"]).replace("/", "_")
    if identifiers.get("doi"):
        return "doi-" + sha256_text(normalize_doi(identifiers["doi"]))[:16]
    if identifiers.get("file_sha256"):
        return "sha-" + normalize_file_sha(identifiers["file_sha256"])[:16]
    die("BAD_ARGS", "identifiers 至少要有一个可核实身份（arxiv_id / doi / file_sha256）；"
                    "仅凭标题不能建立主记录——请补链接、DOI 或文件哈希（标题检索与人工确认另走）")
    raise AssertionError


# ---------- 路径护栏（§9.6 第 8 条） ----------

def grad_root(repo: Path) -> Path:
    grad = (repo / ".grad").resolve()
    if not grad.is_relative_to(repo.resolve()):
        die("BAD_ARGS", f".grad 解析越出项目：{grad}")
    return grad


def resolve_under_grad(grad: Path, rel_or_abs: str, error_hint: str = "") -> Path:
    """把 note.path 之类解析到 .grad/ 内；逃逸即 BAD_ARGS。"""
    p = Path(rel_or_abs)
    full = (grad / p) if not p.is_absolute() else p
    try:
        resolved = full.resolve()
    except OSError as exc:
        die("BAD_ARGS", f"路径无法解析：{rel_or_abs}（{exc}）")
    if not resolved.is_relative_to(grad):
        die("BAD_ARGS", f"写入路径必须位于项目 .grad/ 内：{rel_or_abs}{('；' + error_hint) if error_hint else ''}")
    return resolved


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temp.write_text(content, encoding="utf-8", newline="\n")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


# ---------- 记录读写（§9.3：读宽容、写严格） ----------

def papers_dir(grad: Path) -> Path:
    return grad / "radar" / "papers"


def record_path(grad: Path, paper_id: str, *, strict: bool = True) -> Path | None:
    """paper_id → 记录文件路径。读路径（strict=False）对非安全键返回 None 走标题检索。"""
    if not SAFE_ID_RE.match(paper_id) or "/" in paper_id or "\\" in paper_id:
        if not strict:
            return None
        die("BAD_ARGS", f"paper_id 不是文件名安全的记录键：{paper_id!r}")
    return papers_dir(grad) / f"{paper_id}.json"


def load_record(grad: Path, paper_id: str) -> dict | None:
    f = record_path(grad, paper_id, strict=False)
    if f is None or not f.is_file():
        return None
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die("BAD_RECORD", f"{f} 不可解析：{exc}")
    return data if isinstance(data, dict) else None


def save_record(grad: Path, record: dict) -> None:
    record["updated_at"] = now_local()
    f = record_path(grad, str(record["paper_id"]))
    try:
        atomic_write(f, json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    except OSError as exc:
        die("WRITE_FAILED", f"主记录写入失败（不返回成功）：{exc}")


def iter_records(grad: Path) -> list[dict]:
    """扫描 papers/（首期小量 JSON 直扫；忽略 tmp/隐藏文件）。"""
    out = []
    d = papers_dir(grad)
    for f in sorted(d.glob("*.json")) if d.is_dir() else []:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue  # 坏记录跳过列表（单条损坏不拖垮台账视图），show 按 id 读时会报错
        if isinstance(data, dict) and data.get("paper_id"):
            out.append(data)
    return out


def validate_enum(value: object, allowed: set[str], field: str, errors: list[str],
                  *, optional: bool = False) -> None:
    if value is None and optional:
        return
    if not isinstance(value, str) or value not in allowed:
        errors.append(f"{field} 必须是 {'/'.join(sorted(allowed))} 之一，收到 {value!r}")


def validate_classification(cls: object, errors: list[str]) -> None:
    if cls is None:
        return
    if not isinstance(cls, dict):
        errors.append("classification 必须是对象")
        return
    validate_enum(cls.get("importance"), IMPORTANCE_VALUES, "classification.importance", errors)
    validate_enum(cls.get("difficulty"), DIFFICULTY_VALUES, "classification.difficulty", errors)
    validate_enum(cls.get("paper_type"), PAPER_TYPE_VALUES, "classification.paper_type", errors)
    for reason in ("importance_reason", "difficulty_reason", "type_reason"):
        value = cls.get(reason)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            errors.append(f"classification.{reason} 必须是非空字符串（每维度附一句独立理由）")
    if not isinstance(cls.get("provisional"), bool):
        errors.append("classification.provisional 必须是布尔（仅摘要判读时为 true）")


def validate_note_fields(note: dict, errors: list[str]) -> None:
    """save-note 组装的 note 段严格校验（写侧统一门槛）。"""
    validate_enum(note.get("basis"), BASIS_VALUES, "note.basis", errors)
    sv = note.get("source_version")
    if sv is not None and (not isinstance(sv, str) or not re.fullmatch(r"v\d+", sv)):
        errors.append("note.source_version 必须是 vN 形式或 null")
    for field in ("sections", "pages", "figures_viewed", "tables_checked", "limitations"):
        if not isinstance(note.get(field), list):
            errors.append(f"note.{field} 必须是数组")


# ---------- register ----------

def cmd_register(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    grad = grad_root(repo)
    if not args.input_file:
        die("BAD_ARGS", "register 需要 --input-file（UTF-8 JSON），避免在 shell 里拼接长 JSON")
    try:
        payload = json.loads(Path(args.input_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die("BAD_ARGS", f"--input-file 读取/解析失败：{exc}")
    if not isinstance(payload, dict):
        die("BAD_ARGS", "输入根节点必须是 JSON 对象")

    identifiers = payload.get("identifiers") or {}
    if not isinstance(identifiers, dict):
        die("BAD_ARGS", "identifiers 必须是对象")
    arxiv_id = normalize_arxiv(identifiers["arxiv_id"]) if identifiers.get("arxiv_id") else None
    doi = normalize_doi(identifiers["doi"]) if identifiers.get("doi") else None
    file_sha = normalize_file_sha(identifiers["file_sha256"]) if identifiers.get("file_sha256") else None
    if not (arxiv_id or doi or file_sha):
        die("AMBIGUOUS_IDENTITY",
            "缺少可核实身份（arxiv_id / doi / file_sha256 至少其一）；标题只用于检索与人工确认，"
            "不足以建立主条目。请补链接/DOI/文件，已确定的标题信息在会话中保留")
    title = str(payload.get("title") or "").strip()
    if not title:
        die("BAD_ARGS", "title 不能为空（仅身份字段无标题的记录不得伪造内容笔记）")

    paper_id = derive_paper_id({"arxiv_id": arxiv_id, "doi": doi, "file_sha256": file_sha})

    # 去重：按身份匹配既有记录；同标题不同身份只给候选提示，不自动合并（R03）
    warnings: list[str] = []
    existing = load_record(grad, paper_id)
    if existing is not None:
        warnings.append(f"同身份主记录已存在：{paper_id}（幂等复用，双入口共享一条主条目）")
    if existing is None:
        for rec in iter_records(grad):
            ident = rec.get("identifiers") or {}
            match = ((arxiv_id and normalize_arxiv(ident["arxiv_id"]) == arxiv_id) if ident.get("arxiv_id") else False) \
                or ((doi and normalize_doi(ident["doi"]) == doi) if ident.get("doi") else False) \
                or ((file_sha and normalize_file_sha(ident["file_sha256"]) == file_sha) if ident.get("file_sha256") else False)
            if match:
                existing = rec
                warnings.append(f"按身份字段命中既有主记录 {rec['paper_id']}（两个入口同篇论文，复用同一主条目）")
                break
            if title and str(rec.get("title", "")).strip().casefold() == title.casefold():
                warnings.append(f"存在同名记录 {rec['paper_id']}（标题不作为自动合并依据；"
                                "确认同一论文时通过 update-context 补充共同身份字段）")
        if existing is not None and arxiv_id:
            paper_id = str(existing["paper_id"])  # 命中既有条目：以它的稳定主键为准

    if existing is not None:
        # 幂等返回：不覆盖旧进度、不清空分类；只补缺的身份字段并更新 source 资料引用
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
        _emit(data, args.json, f"已有主记录 {existing['paper_id']}（幂等返回，旧阅读状态保持）")
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
        die("BAD_ARGS", "source 校验失败（未写入）：" + "；".join(source_errors))
    if errors:
        die("BAD_ARGS", "classification 校验失败（未写入）：" + "；".join(errors))
    # legacy digest 复用：旧路径笔记能按 arXiv 基础 ID 确认身份时，主笔记入口指过去（§9.1）
    if arxiv_id and record["note"]["path"] is None:
        legacy = grad / "radar" / "digest" / f"{arxiv_id.replace('/', '_')}.md"
        if legacy.is_file():
            record["note"]["path"] = str(legacy.relative_to(grad)).replace("\\", "/")
            warnings.append(f"发现旧 digest（legacy）：{record['note']['path']}；"
                            "只证明有一份笔记，不证明全文读取范围、不证明用户已读")
    save_record(grad, record)
    data = {"paper_id": paper_id, "created": True, "record": record, "warnings": warnings}
    _emit(data, args.json, f"已登记主记录 {paper_id}")


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
            errors.append("source.version 必须是 vN 形式或 null")
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
        errors.append("给了版本号但 version_status=unknown——两者矛盾：显式版本应为 confirmed")
    return out


def _default_classification(cls: object) -> dict:
    base = {"importance": "unknown", "importance_reason": "尚未判断",
            "difficulty": "unknown", "difficulty_reason": "尚未判断",
            "paper_type": "other", "type_reason": "尚未判断", "provisional": True}
    if isinstance(cls, dict):
        base.update({k: v for k, v in cls.items() if k in base})
    return base


SOURCE_FIELDS = ("url", "local_path", "version", "version_status", "parser", "parser_name", "fetched_at")


def _update_source(record: dict, source: dict, warnings: list[str]) -> None:
    """REV-04：字段级更新语义——省略 = 保留旧值，显式给值（含 null）= 覆盖/清空。

    默认值只用于新建记录（register 走 _validated_source 初始化的那条路）；
    这里先按键合并出完整 source，再对完整结果做校验与一致性检查。
    """
    if not isinstance(source, dict) or not source:
        die("BAD_ARGS", "source 更新必须是非空对象（要改哪个字段给哪个，未给的保持原样）")
    unknown = [k for k in source if k not in SOURCE_FIELDS]
    if unknown:
        die("BAD_ARGS", f"未知 source 字段 {unknown}；可更新字段：{'、'.join(SOURCE_FIELDS)}")
    merged = {**(record.get("source") or {})}
    for key in source:
        merged[key] = source[key]
    errors: list[str] = []
    validated = _validated_source(merged, errors)
    if errors:
        die("BAD_ARGS", "source 合并后校验失败（未写入）：" + "；".join(errors))
    old_version = (record.get("source") or {}).get("version")
    record["source"] = validated
    if old_version and validated.get("version") and old_version != validated["version"]:
        warnings.append(f"资料版本更新：{old_version} → {validated['version']}；"
                        "用户读过旧版不等于读过新版，阅读历史与笔记 source_version 保持不动")
    elif old_version and not validated.get("version"):
        warnings.append(f"版本已从 {old_version} 清为未确认（version_status={validated['version_status']}）："
                        "后续笔记不得再继承旧版本号，按新来源实际情况重新确认")


# ---------- 定位（show/update 共用） ----------

def locate_record(grad: Path, query: str) -> dict:
    """按 paper_id / arXiv id(可带版本) / 标题子串唯一定位；多义报候选（§5.1）。"""
    s = query.strip()
    if not s:
        die("BAD_ARGS", "定位查询不能为空")
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
        die("AMBIGUOUS_IDENTITY", "查询命中多条记录，列出候选让用户确认，不猜：" +
            "；".join(f"{r['paper_id']}（{str(r.get('title', ''))[:30]}）" for r in hits[:6]),
            candidates=[r["paper_id"] for r in hits[:6]])
    die("NOT_FOUND", f"没有匹配 {query!r} 的论文记录；先用 /grad:radar 阅读入口或直接 register 登记")
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
    records = iter_records(grad)  # papers/*.json 即全部主条目；digest/history/user.md 天然不在内
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
    print(f"{len(items)} 条主记录")
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
        die("SOURCE_UNAVAILABLE", f"笔记正文文件不可读：{args.note_file}：{exc}")
    if not content.strip():
        die("BAD_ARGS", "笔记正文为空；不保存空笔记冒充产出")

    errors: list[str] = []
    validate_enum(args.mode, MODE_VALUES, "--mode", errors)
    validate_enum(args.basis, BASIS_VALUES, "--basis", errors)
    if errors:
        die("BAD_ARGS", "；".join(errors))
    if args.source_version and not re.fullmatch(r"v\d+", args.source_version):
        die("BAD_ARGS", f"--source-version 必须是 vN：{args.source_version!r}")
    # REV-06：unavailable 没有任何可读来源，不构成任何一档完成交付（含 quick 卡片），
    # 也不能覆盖既有有效笔记。获取失败用 --record-failure 单独落一条失败记录（写进
    # record.note.limitations + 保留原笔记/mode 不动），而不是伪装成笔记。
    if args.basis == "unavailable":
        if not args.record_failure:
            die("BAD_ARGS", "basis=unavailable 不是完成交付：没有可读来源时不能保存任何档笔记（含 quick）。"
                            "记录获取失败请改用 --record-failure（保留原笔记不动，只登记失败与待补材料）；"
                            "有可用摘要/正文再按实际 basis 重新保存")
        # 只登记失败信息，绝不写笔记正文、绝不改 reading.mode
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
              f"已登记获取失败：{reasons}；原笔记与阅读深度保持不变")
        return
    # 只有摘要时不能保存成 standard/deep 冒充完成（§5.3）
    if args.basis in ("metadata", "abstract") and args.mode in ("standard", "deep"):
        warnings_mode = [f"--basis={args.basis} 只支持 quick 交付；"
                         "standard/deep 请求实际未完成，mode 已按实际材料降级为 quick（如实说明原因）"]
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
        die("BAD_ARGS", "笔记必须是 .md 文件")
    if target.name.endswith(".user.md"):
        die("BAD_ARGS", "save-note 不能写 .user.md——用户批注文件由用户维护，AI 不覆盖")

    # 先把所有 note 字段解析并校验（任何坏参数都在落盘前挡下，不留半成品）
    note_fields: dict = {
        "source_version": args.source_version or (record.get("source") or {}).get("version"),
        "basis": args.basis,
        "sections": [s.strip() for s in args.sections.split(",") if s.strip()],
        "pages": _parse_pages(args.pages),
        "figures_viewed": [s.strip() for s in args.figures.split(",") if s.strip()],
        "tables_checked": [s.strip() for s in args.tables.split(",") if s.strip()],
        "limitations": [s.strip() for s in args.limitations.split(",") if s.strip()],
    }
    pre_errors: list[str] = []
    validate_note_fields({**note, **note_fields}, pre_errors)
    if pre_errors:
        die("BAD_ARGS", "note 字段校验失败（未写入任何东西）：" + "；".join(pre_errors))

    warnings: list[str] = list(warnings_mode)
    existing_text = target.read_text(encoding="utf-8", errors="replace") if target.is_file() else None
    stored_sha = note.get("content_sha256")
    has_existing = existing_text is not None and existing_text.strip()
    write_mode = "create"
    final_content = content

    # REV-01：--merge 只要目标存在就始终追加，语义不受哈希冲突与否影响；
    # 一旦主笔记接纳过人工内容（保护标记）或哈希不符，普通保存也必须保守保护。
    protected = bool(note.get("has_human_content"))
    if args.merge:
        if has_existing:
            write_mode = "merge"
        else:
            write_mode = "create"  # 无既有内容可追加，等同新建
    elif has_existing:
        external_edit = stored_sha is None or sha256_text(existing_text) != stored_sha
        if external_edit:
            # 无哈希（legacy）或被外部编辑：可能有人工改动，默认拒绝整体替换（§9.6 第 5 条）
            if args.force:
                write_mode = "replace"
                warnings.append("笔记被外部修改/无哈希记录，--force 整体替换已把原稿快照进 history；"
                                "请人工回查被覆盖的改动是否已并入新稿")
            else:
                die("CONFLICT", f"主笔记已存在且可能被人工编辑（无哈希或哈希不符）：{target}；"
                                "不覆盖人工内容。--merge 追加补充段 / --force 快照后替换 / --new-path 另存")
        elif protected:
            # 之前 merge 过（含人工内容），即便本次哈希相等的自动更新也保守：默认追加而非覆盖，
            # 除非显式 --force 才整体替换（用户确实要求重写）。
            if args.force:
                write_mode = "replace"
            else:
                write_mode = "merge"
                warnings.append("主笔记此前接纳过人工内容，普通保存改为追加保护旧内容；"
                                "确需整体重写用 --force（旧稿快照进 history）")
        else:
            write_mode = "replace"  # 纯 AI 笔记、哈希一致、无保护标记：正常更新，旧稿快照进 history
    elif protected and not has_existing:
        write_mode = "create"

    if write_mode == "merge":
        supplement = (f"\n\n{MERGE_MARKER}\n\n---\n\n"
                      f"## 补充阅读 · {datetime.now().astimezone():%Y-%m-%d}（本次新增，原有内容保留）\n\n{content}")
        final_content = (existing_text or "") + supplement
    elif write_mode == "replace":
        # 更新前保存历史快照（历史只在内容确实变化时创建，§9.6）
        if existing_text is not None and sha256_text(existing_text) != sha256_text(final_content):
            rev = 1
            history_dir = grad / "radar" / "digest" / "history" / str(record["paper_id"])
            while (history_dir / f"rev-{rev:03d}.md").exists():
                rev += 1
            try:
                atomic_write(history_dir / f"rev-{rev:03d}.md", existing_text)
                (history_dir / f"rev-{rev:03d}.reason.txt").write_text(
                    (args.history_reason or "更新前自动快照") + f"\nsaved_at={now_local()}\n", encoding="utf-8")
            except OSError as exc:
                die("WRITE_FAILED", f"历史快照写入失败，笔记未更新：{exc}")

    # 先确保新笔记落盘成功，再更新主记录指向（§9.6 第 6 条：失败不得登记完成）
    try:
        atomic_write(target, final_content)
    except OSError as exc:
        die("WRITE_FAILED", f"笔记写入失败，主记录保持原状：{exc}")

    note["path"] = str(target.relative_to(grad)).replace("\\", "/")
    note["content_sha256"] = sha256_text(final_content)
    # REV-01：merge 引入补充段即视为接纳过人工/补充内容，置保护标记，后续普通保存继续保守；
    # 纯 AI 内容整体写入（create/replace）则基线重新干净，解除标记。
    if write_mode == "merge":
        note["has_human_content"] = True
    else:
        note.pop("has_human_content", None)
    note["generated_at"] = now_local()
    # REV-01：合并笔记的覆盖范围不能只描述最后一段；追加时把本次范围并入既有条目去重
    if write_mode == "merge":
        note.update(_merge_note_fields(note, note_fields))
    else:
        note.update(note_fields)
    # mode 归属 reading.mode（§9.3：当前主笔记采用的阅读深度）；只动笔记，不碰人的 status/last_read_at
    record.setdefault("reading", {})["mode"] = args.mode
    save_record(grad, record)
    data = {"paper_id": record["paper_id"], "note_path": note["path"], "mode": args.mode,
            "write_mode": write_mode, "generated_at": note["generated_at"],
            "reading_status_untouched": (record.get("reading") or {}).get("status"),
            "warnings": warnings}
    _emit(data, args.json,
          f"笔记已保存：{note['path']}（mode={args.mode}，写入方式={write_mode}）；"
          f"人的阅读状态保持 {(record.get('reading') or {}).get('status')}——生成笔记不等于读完")


def _merge_note_fields(existing: dict, incoming: dict) -> dict:
    """合并保存时保留各补充段的版本/范围，不假装只描述最后一段（REV-01）。"""
    merged = dict(incoming)
    for key in ("sections", "pages", "figures_viewed", "tables_checked", "limitations"):
        seen = list(dict.fromkeys(list(existing.get(key) or []) + list(incoming.get(key) or [])))
        merged[key] = seen
    # source_version：不同补充段版本不一致时如实标注，不覆盖成单值假象
    old_v = existing.get("source_version")
    new_v = incoming.get("source_version")
    if old_v and new_v and old_v != new_v:
        merged["source_version"] = old_v  # 保留主笔记基线版本，差异体现在覆盖说明
    # basis：取信息量更高的一档（fulltext>sections>abstract>metadata；unavailable 不提升）
    rank = {"unavailable": 0, "metadata": 1, "abstract": 2, "sections": 3, "fulltext": 4}
    ob, nb = existing.get("basis"), incoming.get("basis")
    if ob and nb and rank.get(nb, 0) < rank.get(ob, 0):
        merged["basis"] = ob
    return merged


def _parse_pages(text: str) -> list[int]:
    pages: list[int] = []
    for part in (p.strip() for p in (text or "").split(",")):
        if not part:
            continue
        if not part.isdigit() or int(part) < 1:
            die("BAD_ARGS", f"pages 必须是逗号分隔的 ≥1 物理页码整数：{part!r}")
        pages.append(int(part))
    return pages


# ---------- set-status / update-context ----------

def cmd_set_status(args: argparse.Namespace) -> None:
    grad = grad_root(Path(args.repo).resolve())
    record = locate_record(grad, args.paper)
    quote = (args.user_quote or "").strip()
    if not quote:
        die("BAD_ARGS", "set-status 必须附 --user-quote（用户明确表达阅读状态的原话/转述）；"
                        "AI 生成笔记、模型建议都不能写成人的阅读状态")
    # REV-02：last_read_version 记「实际读完的版本」，不能盲取当前资料版本。
    # 优先级：显式 --read-version > 定位查询里带的版本（如 --paper 2609.90003v1）> null（不猜）。
    read_version = None
    if args.read_version:
        if not re.fullmatch(r"v\d+", args.read_version):
            die("BAD_ARGS", f"--read-version 必须是 vN：{args.read_version!r}")
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
        # 完成阅读按实际读的版本记录（没有依据时留 null，不拿最新资料版本冒充）；
        # 重读 read→reading 保留上次完成时间与版本（§8.4）
        reading["last_read_at"] = now_local()
        if read_version:
            reading["last_read_version"] = read_version
    save_record(grad, record)
    _emit({"paper_id": record["paper_id"], "status": args.status,
           "last_read_at": reading.get("last_read_at"),
           "last_read_version": reading.get("last_read_version"),
           "note_generated_at": (record.get("note") or {}).get("generated_at")},
          args.json, f"阅读状态已记录（user）：{args.status}"
                     + (f"｜读完版本 {reading.get('last_read_version')}" if args.status == "read" else ""))


def cmd_update_context(args: argparse.Namespace) -> None:
    grad = grad_root(Path(args.repo).resolve())
    record = locate_record(grad, args.paper)
    warnings: list[str] = []
    changed = False
    if args.classification_json:
        try:
            cls = json.loads(Path(args.classification_json).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            die("BAD_ARGS", f"--classification-json 读取/解析失败：{exc}")
        merged = {**(record.get("classification") or {}), **cls}
        errors: list[str] = []
        validate_classification(merged, errors)
        if errors:
            die("BAD_ARGS", "classification 校验失败（未写入）：" + "；".join(errors))
        old_type = (record.get("classification") or {}).get("paper_type")
        record["classification"] = merged
        if args.type_reason:
            merged["type_reason"] = args.type_reason + "（分类变更说明）"
        if old_type and merged.get("paper_type") and old_type != merged["paper_type"]:
            warnings.append(f"主类型变更 {old_type} → {merged['paper_type']}；"
                            "分类变更必须说明原因（--type-reason 或写在 reason 里）")
        changed = True
    if args.source_json:
        try:
            source = json.loads(Path(args.source_json).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            die("BAD_ARGS", f"--source-json 读取/解析失败：{exc}")
        _update_source(record, source, warnings)
        changed = True
    if args.difficulty_point:
        cls = record.setdefault("classification", {})
        cls["difficulty_reason"] = f"{cls.get('difficulty_reason', '')}｜卡点：{args.difficulty_point}".strip("｜")
        changed = True
    if args.reading_mode:
        validate_enum(args.reading_mode, MODE_VALUES, "--reading-mode", [])
        record.setdefault("reading", {})["mode"] = args.reading_mode
        changed = True
    if changed:
        # 本操作只动分类/来源/深度：用户批注文件与 last_read_at 不碰（§9.7）
        save_record(grad, record)
    _emit({"paper_id": record["paper_id"], "record": record, "warnings": warnings,
           "changed": changed}, args.json,
          f"已更新 {record['paper_id']} 的阅读上下文（状态与已读时间未动）")


def _emit(data: dict, as_json: bool, summary: str) -> None:
    if as_json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
    else:
        print(summary)


def main() -> None:
    ap = argparse.ArgumentParser(description="单篇阅读主记录：身份、状态与笔记保存（只存不判）")
    sub = ap.add_subparsers(dest="command", required=True)

    def common(cmd: argparse.ArgumentParser, paper: bool = True) -> None:
        cmd.add_argument("--repo", default=".", help="项目根（.grad/ 所在）")
        if paper:
            cmd.add_argument("--paper", required=True, help="paper_id / arXiv id（可带版本）/ 标题子串")
        cmd.add_argument("--json", action="store_true")

    p = sub.add_parser("register", help="登记/返回主记录（同身份幂等）")
    p.add_argument("--repo", default=".")
    p.add_argument("--input-file", required=True, help="UTF-8 JSON：identifiers/title/source/classification")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("show", help="读取一篇记录（无写入副作用）"); common(p)
    p = sub.add_parser("list", help="按状态/类型列出主记录")
    p.add_argument("--repo", default=".")
    p.add_argument("--status", choices=sorted(STATUS_VALUES), default=None)
    p.add_argument("--type", choices=sorted(PAPER_TYPE_VALUES), default=None)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("save-note", help="保存 AI 主笔记与已获取来源范围")
    common(p)
    p.add_argument("--note-file", required=True, help="模型已写好的笔记正文文件（UTF-8）")
    p.add_argument("--mode", required=True, choices=sorted(MODE_VALUES))
    p.add_argument("--basis", required=True, choices=sorted(BASIS_VALUES),
                   help="实际依据材料：metadata/abstract/sections/fulltext/unavailable")
    p.add_argument("--source-version", default="", help="本笔记实际基于的材料版本（vN）")
    p.add_argument("--sections", default="", help="已读章节，逗号分隔（S1,S3.SS2…）")
    p.add_argument("--pages", default="", help="PDF 物理页码（从 1 开始），逗号分隔")
    p.add_argument("--figures", default="", help="已核对图标识；空=没有确认，不补成全覆盖")
    p.add_argument("--tables", default="", help="已核对表标识")
    p.add_argument("--limitations", default="", help="未覆盖/解析受限说明，逗号分隔")
    p.add_argument("--merge", action="store_true", help="与既有笔记冲突时追加补充段而非替换")
    p.add_argument("--force", action="store_true", help="确认整体替换（旧稿先快照进 history）")
    p.add_argument("--new-path", default="", help="另存为独立草稿路径（相对 .grad/）")
    p.add_argument("--history-reason", default="", help="快照原因（默认自动记录模式与时间）")
    p.add_argument("--record-failure", default="",
                   help="basis=unavailable 专用：登记获取失败原因与待补材料（分号分隔），不写笔记不改深度")

    p = sub.add_parser("set-status", help="记录用户明确表达的阅读状态（唯一能写 read 的入口）")
    common(p)
    p.add_argument("--status", required=True, choices=sorted(USER_STATUS_VALUES))
    p.add_argument("--user-quote", required=True, help="用户原话/转述——状态必须是用户动作")
    p.add_argument("--read-version", default="",
                   help="status=read 时实际读完的版本（vN）；不给则用定位查询里的显式版本，都没有记 null，不拿最新资料版本冒充")

    p = sub.add_parser("update-context", help="更新分类/来源资料/深度；不动批注与已读时间")
    common(p)
    p.add_argument("--classification-json", default="", help="UTF-8 JSON 文件：分类字段（含理由）")
    p.add_argument("--type-reason", default="", help="主类型变更的原因（分类变更必须说明）")
    p.add_argument("--source-json", default="", help="UTF-8 JSON 文件：来源/版本资料更新")
    p.add_argument("--difficulty-point", default="", help="用户反馈的具体卡点（附加到 difficulty_reason）")
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
