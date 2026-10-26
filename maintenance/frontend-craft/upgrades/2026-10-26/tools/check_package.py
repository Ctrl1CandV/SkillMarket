#!/usr/bin/env python3
"""Read-only, Python 3.8+ / stdlib checks for this two-skill upgrade package.

Usage:
  python3 check_package.py --package-root /path/to/package
  python3 check_package.py --repo-root /path/to/repo
  python3 check_package.py --package-root /path/to/package --repo-root /path/to/repo
  python3 check_package.py --release

The package may contain runtime/ or the build-time overlay/ directory. A direct
directory containing both skill roots is also accepted. With neither root option,
search this script's ancestors, then the current directory's ancestors.
--repo-root alone checks only that repository, containing frontend-craft/ and
product-design/ directly, or under skills/. Both roots are checked only when
both options are explicitly supplied. Exit 0 means the requested *static* checks passed;
exit 1 means failed checks, and exit 2 means an input/discovery error. Neither
ordinary success nor --release success constitutes visual or behavior approval.
"""

import argparse
from datetime import date, datetime
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PureWindowsPath
import re
import sys
from urllib.parse import unquote, urlsplit


REQUIRED = {
    "frontend-craft": [
        "SKILL.md",
        *["references/" + name + ".md" for name in (
            "content", "layout", "cjk-typography", "scenarios", "visual-style",
            "review", "exemplars", "reference-selection", "style-samples")],
        "references/exemplar-index.json",
        "assets/style-lab/index.html", "assets/style-lab/styles.css",
        "assets/style-lab/lab.js",
    ],
    "product-design": [
        "SKILL.md", "references/product-context.md",
        "references/new-and-redesign.md", "references/examples.md",
    ],
}
THEMES = ("neutral-cobalt", "ink-cyan", "paper-berry")
CATEGORIES = {"reading-verification", "dense-operation", "public-display"}
STATUSES = {"candidate", "documented", "verified_visual"}
PLACEHOLDERS = {
    "", "todo", "tbd", "pending", "placeholder", "n/a", "na", "none", "null",
    "unknown", "xxx", "...", "…", "待填写", "待补充", "待核验", "待采集",
    "待截图", "占位", "未提供", "未核验", "未知",
}
LIMITATIONS = [
    "结构 PASS 或 --release PASS 只表示静态前提满足，不代表本轮总验收通过。",
    "本工具不运行浏览器，不判断审美、内容关系、可访问性、交互或动态连续性。",
    "viewed、来源独立性、许可与观察记录是作者声明，须由独立终审核实，不能以字段自证。",
    "图片仅检查文件存在与格式签名，不解码画面，也不能证明它来自所声明页面或已经被查看。",
    "只检查常见 Markdown 文件链接和 HTML src/href；不执行 JavaScript、不解析 CSS 依赖，不实现完整 YAML/CommonMark。",
]


def meaningful(value):
    if not isinstance(value, str):
        return False
    value = value.strip()
    return (value.casefold() not in PLACEHOLDERS and
            not re.match(r"^(?:todo|tbd|placeholder|待填写|待补充|占位)\s*[:：]", value, re.I))


def text_list(value):
    return isinstance(value, list) and bool(value) and all(meaningful(x) for x in value)


def iso_date(value):
    if not isinstance(value, str):
        return False
    try:
        if len(value) == 10:
            date.fromisoformat(value)
        else:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def source_url(value):
    if not meaningful(value):
        return False
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        return (parsed.scheme in ("https", "http") and bool(host) and
                not parsed.username and not parsed.password and
                host not in {"localhost", "example.com", "example.org", "example.net"} and
                not host.endswith((".invalid", ".example", ".test", ".localhost")) and
                not any(c.isspace() for c in value) and parsed.port != 0)
    except ValueError:
        return False


def within(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError, RuntimeError):
        return False


class Check:
    def __init__(self, label, root):
        self.label, self.root = label, root.resolve()
        self.errors, self.pending = [], []
        self.summary = {"text_files_checked": 0, "local_links_checked": 0, "frontmatter": {}}

    def error(self, code, path, message):
        try:
            path = str(Path(path).relative_to(self.root))
        except ValueError:
            path = str(path)
        self.errors.append({"code": code, "path": path, "message": message})

    def require(self, condition, code, path, message):
        if not condition:
            self.error(code, path, message)
        return bool(condition)

    def read(self, path):
        if not within(path, self.root):
            self.error("unsafe_path", path, "文件解析到检查根目录以外。")
            return None
        if not path.is_file():
            self.error("unreadable_text", path, "缺少可读取的普通文本文件。")
            return None
        try:
            return path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            self.error("unreadable_text", path, str(exc))
            return None

    def result(self):
        return {"label": self.label, "root": str(self.root),
                "static_status": "fail" if self.errors else "pass",
                "errors": self.errors, "pending": self.pending, "summary": self.summary}


def local_path(check, owner, raw, boundary=None, screenshot=False):
    """Return an existing local target; skip ordinary URL/fragment links."""
    boundary = boundary or check.root
    if not isinstance(raw, str) or not raw.strip():
        check.error("empty_path", owner, "本地路径不能为空。")
        return None
    raw = html.unescape(raw.strip())
    if "\\" in raw or PureWindowsPath(raw).drive or any(ord(c) < 32 for c in raw):
        check.error("unsafe_path", owner, "路径含反斜杠、盘符或控制字符：" + repr(raw))
        return None
    try:
        parsed = urlsplit(raw)
    except ValueError:
        check.error("invalid_link", owner, "无法解析路径：" + repr(raw))
        return None
    if parsed.scheme or parsed.netloc:
        if screenshot or parsed.scheme == "file":
            check.error("unsafe_path", owner, "此处必须使用包内相对路径：" + raw)
        return None
    decoded = unquote(parsed.path)
    if not decoded and not screenshot:
        return None  # Fragment/query-only links, including JS-driven HTML anchors.
    if (not decoded or "\\" in decoded or Path(decoded).is_absolute() or
            PureWindowsPath(decoded).drive or any(ord(c) < 32 for c in decoded) or
            (screenshot and (parsed.query or parsed.fragment or ".." in Path(decoded).parts))):
        check.error("unsafe_path", owner, "不是可移植的包内相对路径：" + raw)
        return None
    target = (boundary if screenshot else owner.parent) / decoded
    if not within(target, boundary):
        check.error("unsafe_path", owner, "路径越过允许的根目录：" + raw)
        return None
    check.summary["local_links_checked"] += 1
    if not target.exists():
        check.error("missing_link_target", owner, "目标不存在：" + raw)
        return None
    return target


def frontmatter(check, skill):
    path = check.root / skill / "SKILL.md"
    text = check.read(path)
    if text is None:
        return
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        check.error("frontmatter", path, "需要以 --- 开始并闭合的 YAML frontmatter。")
        return
    block = lines[1:lines.index("---", 1)]
    fields, versions, in_metadata = {}, [], False
    for line in block:
        top = re.match(r"^([A-Za-z_][\w-]*):\s*(.*?)\s*$", line)
        if top:
            key, value = top.groups()
            if key in fields:
                check.error("frontmatter_duplicate", path, "重复字段：" + key)
            fields[key] = value
            in_metadata = key == "metadata"
            if key == "version":
                versions.append(value)
        elif in_metadata:
            match = re.match(r"^\s+version:\s*(.*?)\s*$", line)
            if match:
                versions.append(match.group(1))

    def scalar(value):
        if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
            return value[1:-1]
        return value.split(" #", 1)[0].strip()

    name = scalar(fields.get("name", ""))
    check.require(name == skill, "frontmatter_name", path, "name 应等于目录名 " + skill)
    description = scalar(fields.get("description", ""))
    if description in {"|", ">", "|-", ">-", "|+", ">+"}:
        match = re.search(r"^description:\s*[|>][+-]?\s*\n((?:[ \t]+[^\n]*\n?)+)", "\n".join(block), re.M)
        description = match.group(1).strip() if match else ""
    check.require(meaningful(description), "frontmatter_description", path, "description 缺失或为空占位。")
    version = scalar(versions[0]) if len(versions) == 1 else ""
    check.require(bool(re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", version)),
                  "frontmatter_version", path, "需要唯一的 version 或 metadata.version，使用三段版本号及可选预发布后缀。")
    check.summary["frontmatter"][skill] = {"name": name, "version": version}


def without_markdown_code(text):
    kept, fence = [], None
    for line in text.splitlines():
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= fence[1] and not match.group(2).strip():
                fence = None
            continue
        if match:
            fence = (match.group(1)[0], len(match.group(1)))
        else:
            kept.append(line)
    return re.sub(r"(`+).*?\1", "", "\n".join(kept), flags=re.S)


def markdown_destinations(text):
    # Read a destination, allowing escaped or balanced parentheses and <...>.
    def destination(tail):
        tail = tail.lstrip()
        if tail.startswith("<"):
            end = tail.find(">", 1)
            return tail[1:end] if end >= 0 else ""
        chars, depth, escaped = [], 0, False
        for char in tail:
            if escaped:
                chars.append(char)
                escaped = False
            elif char == "\\":
                escaped = True
            elif depth == 0 and (char == ")" or char.isspace()):
                break
            else:
                depth += 1 if char == "(" else -1 if char == ")" else 0
                chars.append(char)
        return "".join(chars)

    text = without_markdown_code(text)
    for match in re.finditer(r"(?<!\\)\]\(\s*", text):
        yield destination(text[match.end():])
    for match in re.finditer(r"^ {0,3}\[(?!\^)[^\]\n]+\]:\s*(.+)$", text, re.M):
        yield destination(match.group(1))


class LocalHTMLLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in {"src", "href"} and value is not None)


def files_and_links(check):
    for skill, required in REQUIRED.items():
        if not within(check.root / skill, check.root):
            check.error("unsafe_path", check.root / skill, "技能根目录解析到检查根目录以外。")
            continue
        for relative in required:
            path = check.root / skill / relative
            check.require(within(path, check.root) and path.is_file(), "required_file", path,
                          "必需文件缺失、不是普通文件或越过检查根目录。")
        if (check.root / skill / "SKILL.md").is_file():
            frontmatter(check, skill)
        for directory, dirs, files in os.walk(str(check.root / skill), followlinks=False):
            for name in dirs + files:
                path = Path(directory) / name
                if path.is_symlink() and (not within(path, check.root) or not path.exists()):
                    check.error("unsafe_symlink", path, "符号链接损坏或指向检查根目录以外。")
            for name in files:
                path = Path(directory) / name
                if path.suffix.lower() not in {".md", ".html"}:
                    continue
                text = check.read(path)
                if text is None:
                    continue
                check.summary["text_files_checked"] += 1
                if path.suffix.lower() == ".md":
                    links = markdown_destinations(text)
                else:
                    parser = LocalHTMLLinks()
                    parser.feed(text)  # Script bodies are data, not HTML tags.
                    links = parser.links
                for link in links:
                    local_path(check, path, link)
    for filename in ("index.html", "styles.css", "lab.js"):
        path = check.root / "frontend-craft/assets/style-lab" / filename
        if path.is_file():
            text = check.read(path)
            if text is not None:
                for theme in THEMES:
                    check.require(theme in text, "theme_missing", path, "缺少主题 ID：" + theme)


def image_signature(path):
    try:
        with path.open("rb") as stream:
            header = stream.read(32)
        size = path.stat().st_size
        suffix = path.suffix.lower()
        if suffix == ".png":
            return (size >= 33 and header.startswith(b"\x89PNG\r\n\x1a\n") and
                    header[12:16] == b"IHDR" and int.from_bytes(header[16:20], "big") > 0 and
                    int.from_bytes(header[20:24], "big") > 0)
        if suffix in {".jpg", ".jpeg"}:
            return size > 4 and header.startswith(b"\xff\xd8\xff")
        if suffix == ".webp":
            return (size > 20 and header[:4] == b"RIFF" and header[8:12] == b"WEBP" and
                    header[12:16] in {b"VP8 ", b"VP8L", b"VP8X"})
    except OSError:
        pass
    return False


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("重复 JSON 字段：" + key)
        result[key] = value
    return result


def reject_json_constant(value):
    raise ValueError("非法 JSON 常量：" + value)


def exemplar_index(check, release):
    path = check.root / "frontend-craft/references/exemplar-index.json"
    text = check.read(path)
    if text is None:
        return
    try:
        data = json.loads(text, object_pairs_hook=no_duplicate_keys,
                          parse_constant=reject_json_constant)
    except (ValueError, RecursionError) as exc:
        check.error("invalid_index_json", path, str(exc))
        return
    if not check.require(isinstance(data, dict) and type(data.get("schema_version")) is int and data["schema_version"] == 1,
                         "index_schema", path, "索引必须是 schema_version 为 1 的对象。"):
        return
    check.require(iso_date(data.get("updated_at")), "index_date", path, "updated_at 应为 ISO 日期或时间。")
    check.require(meaningful(data.get("basis")), "index_basis", path, "basis 必须描述本索引的实际依据。")
    entries = data.get("entries")
    if not check.require(isinstance(entries, list) and bool(entries), "index_entries", path, "entries 必须是非空数组。"):
        return
    counts = {status: 0 for status in sorted(STATUSES)}
    seen, eligible, covered, origins = set(), [], set(), {}
    for number, entry in enumerate(entries):
        before = len(check.errors)
        if not check.require(isinstance(entry, dict), "entry_schema", path, "条目 %d 必须为对象。" % number):
            continue
        entry_id = entry.get("id")
        label = str(entry_id) if isinstance(entry_id, str) else "entries[%d]" % number

        def need(condition, field, message):
            return check.require(condition, "entry_" + field, path, label + ": " + message)

        if need(isinstance(entry_id, str) and bool(re.fullmatch(r"[a-z0-9][a-z0-9-]*", entry_id)), "id", "id 应为小写短标识。"):
            need(entry_id not in seen, "id", "id 不能重复。")
            seen.add(entry_id)
        status = entry.get("status")
        if need(isinstance(status, str) and status in STATUSES, "status", "status 必须是 candidate、documented 或 verified_visual。"):
            counts[status] += 1
        for field in ("tasks", "content_shapes"):
            need(text_list(entry.get(field)), field, field + " 必须是非空字符串数组，原有任务词汇可保留。")
        for field in ("notes", "evidence_kind"):
            need(meaningful(entry.get(field)), field, field + " 必须有实际内容。")
        need(source_url(entry.get("source_url")), "source_url", "source_url 必须是非占位的 HTTP(S) 来源。")
        screenshots = entry.get("screenshots")
        if need(isinstance(screenshots, list), "screenshots", "screenshots 必须是数组；待核验条目可以为空。"):
            for screenshot in screenshots:
                target = local_path(check, path, screenshot, check.root / "frontend-craft", screenshot=True)
                if target is not None:
                    need(target.is_file() and image_signature(target), "screenshot_file",
                         "截图必须是具有有效格式签名的非空 PNG/JPEG/WebP 文件：" + str(screenshot))
        categories = entry.get("release_categories", [])
        categories_valid = (isinstance(categories, list) and
                            all(isinstance(x, str) and x in CATEGORIES for x in categories))
        need(categories_valid, "release_categories", "release_categories 只能含 reading-verification、dense-operation、public-display。")
        for field in ("capture", "license", "review"):
            need(field in entry and (entry[field] is None or isinstance(entry[field], dict)), field,
                 field + " 必须为对象或 null。")
        if status != "verified_visual":
            check.pending.append({"code": "visual_reference_pending", "entry_id": label, "status": status,
                                  "message": "未纳入完整本地画面覆盖；继续按已记录依据使用。"})
            continue
        need(bool(screenshots) and isinstance(screenshots, list), "screenshots", "verified_visual 至少需要一张本地截图。")
        need(categories_valid and bool(categories), "release_categories", "verified_visual 必须明确至少一类 release_categories。")
        origin = entry.get("source_origin")
        need(meaningful(origin) and bool(re.fullmatch(r"[a-z0-9][a-z0-9._-]*", origin or "")), "source_origin",
             "source_origin 必须是发布主体的小写短标识，同一主体不同子域使用同一标识。")
        evidence_kind = str(entry.get("evidence_kind", "")).casefold().replace("-", "_")
        need(evidence_kind not in {"generated_image", "original_sample", "mockup", "synthetic", "placeholder"},
             "evidence_kind", "生成图、原创样张或重画稿不能声称是已核验外部页面。")
        capture = entry.get("capture") if isinstance(entry.get("capture"), dict) else {}
        need(iso_date(capture.get("captured_at")), "capture", "capture.captured_at 需要 ISO 日期或时间。")
        viewport = capture.get("viewport") if isinstance(capture.get("viewport"), dict) else {}
        need(all(type(viewport.get(k)) is int and viewport[k] > 0 for k in ("width", "height")),
             "capture", "capture.viewport.width/height 需要正整数。")
        for field in ("page_state", "method"):
            need(meaningful(capture.get(field)), "capture", "capture." + field + " 需要实际记录。")
        license_info = entry.get("license") if isinstance(entry.get("license"), dict) else {}
        need(license_info.get("redistribution") == "allowed" and meaningful(license_info.get("basis")),
             "license", "本地可再分发画面需要 license.redistribution='allowed' 和具体 basis；未知许可保留链接并用 documented。")
        if "source_url" in license_info:
            need(source_url(license_info["source_url"]), "license", "若提供 license.source_url，必须是有效依据 URL。")
        review = entry.get("review") if isinstance(entry.get("review"), dict) else {}
        need(review.get("viewed") is True, "review", "review.viewed 必须为 true；仅生成截图不等于看过。")
        need(iso_date(review.get("reviewed_at")), "review", "review.reviewed_at 需要 ISO 日期或时间。")
        for field in ("relationships", "transfer_limits"):
            need(text_list(review.get(field)), "review", "review." + field + " 需要非空观察数组。")
        if len(check.errors) == before:
            eligible.append(entry_id)
            covered.update(categories)
            origins.setdefault(origin, []).append(entry["source_url"])
    missing = sorted(CATEGORIES - covered)
    ready = not missing and len(origins) >= 2 and not check.errors
    check.summary["exemplars"] = {"total": len(entries), **counts}
    check.summary["release_prerequisites"] = {
        "static_gate": "met" if ready else "not_met", "eligible_entries": eligible,
        "required_categories": sorted(CATEGORIES), "covered_categories": sorted(covered),
        "missing_categories": missing, "declared_source_origins": origins,
        "minimum_independent_source_origins": 2, "independence_verified_by_script": False,
        "human_visual_and_behavior_review_required": True,
    }
    if release:
        check.require(not missing, "release_coverage", path, "缺少完整外部画面覆盖：" + ", ".join(missing))
        check.require(len(origins) >= 2, "release_sources", path, "完整外部画面需至少 2 个声明的独立发布主体；现有 %d 个。" % len(origins))


def skill_roots(directory, package=True):
    directory = Path(directory).expanduser().resolve()
    candidates = [directory / "runtime", directory / "overlay"] if package else [directory / "skills"]
    candidates.append(directory)
    matches = [p for p in candidates if all((p / skill).is_dir() for skill in REQUIRED)]
    if len(matches) > 1:
        raise ValueError("存在多个可用技能根，请显式指定实际根目录：" + ", ".join(str(p) for p in matches))
    return matches[0] if matches else None


def discover_package(argument):
    if argument:
        found = skill_roots(argument)
        if found:
            return found
        raise ValueError("--package-root 下未找到同时包含两技能的 runtime/、overlay/ 或直接技能根。")
    for base in (Path(__file__).resolve().parent, Path.cwd().resolve()):
        for directory in (base, *base.parents):
            found = skill_roots(directory)
            if not found:
                found = skill_roots(directory, package=False)
            if found:
                return found
    raise ValueError("无法自动找到包，请传入 --package-root PATH。")


class JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"static_status": "fail", "exit_code": 2,
                          "errors": [{"code": "arguments", "message": message}],
                          "limitations": LIMITATIONS}, ensure_ascii=False, indent=2))
        raise SystemExit(2)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = JSONArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--package-root", help="包目录，或直接包含两技能的 runtime/overlay 目录")
    parser.add_argument("--repo-root", help="实际仓库根目录（技能直接位于其下，或位于 skills/ 下）")
    parser.add_argument("--release", action="store_true", help="额外要求三类外部画面覆盖与至少两个声明的独立发布主体；不是总验收")
    args = parser.parse_args()
    try:
        targets = []
        if args.package_root or not args.repo_root:
            targets.append(("package", discover_package(args.package_root)))
        if args.repo_root:
            repo = skill_roots(args.repo_root, package=False)
            if repo is None:
                raise ValueError("--repo-root 下未找到 frontend-craft/ 与 product-design/，也未在 skills/ 下找到。")
            targets.append(("repository", repo))
    except (ValueError, OSError, RuntimeError) as exc:
        parser.error(str(exc))
    results = []
    for label, root in targets:
        check = Check(label, root)
        files_and_links(check)
        exemplar_index(check, args.release)
        results.append(check.result())
    code = 1 if any(result["errors"] for result in results) else 0
    print(json.dumps({"checker": "skillmarket-package-static", "schema_version": 1,
                      "mode": "release_prerequisites" if args.release else "structure",
                      "static_status": "fail" if code else "pass", "exit_code": code,
                      "targets": results, "limitations": LIMITATIONS}, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
