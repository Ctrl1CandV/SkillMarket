"""Read only the frozen skill packages and matching runtimes; write audit evidence here."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unicodedata
from urllib.parse import unquote, urlsplit


BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
SKILLS = ("frontend-craft", "product-design")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix(): digest(p)
            for name in SKILLS for p in sorted((root / name).rglob("*")) if p.is_file()}


def manifest_check(name):
    manifest = BASE / f"{name}-sha256.json"
    rows = json.loads(manifest.read_text(encoding="utf-8-sig"))
    expected = {(r.get("path") or r["Path"]).replace("\\", "/"):
                (r.get("sha256") or r["SHA256"]).lower() for r in rows}
    actual = inventory(BASE / name)
    changed = [p for p in expected if p in actual and expected[p] != actual[p]]
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    return {"passed": not (changed or missing or extra) and len(expected) == len(rows),
            "manifest_sha256": digest(manifest), "expected_files": len(expected),
            "actual_files": len(actual), "changed": changed, "missing": missing,
            "extra": extra, "duplicate_manifest_paths": len(rows) - len(expected)}


class HTMLLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
        self.inline_scripts = []
        self.in_script = False
        self.script_text = []
        self.script_is_js = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "a" and attrs.get("name"):
            self.ids.add(attrs["name"])
        for attr in ("href", "src", "poster"):
            if attrs.get(attr):
                self.links.append(attrs[attr])
        if tag == "script":
            self.in_script = True
            self.script_text = []
            self.script_is_js = not attrs.get("src") and attrs.get("type", "") in (
                "", "module", "text/javascript", "application/javascript")

    def handle_data(self, data):
        if self.in_script:
            self.script_text.append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            if self.script_is_js and "".join(self.script_text).strip():
                self.inline_scripts.append("".join(self.script_text))
            self.in_script = False


def parsed_html(path):
    parser = HTMLLinks()
    parser.feed(path.read_text(encoding="utf-8-sig"))
    return parser


def markdown_ids(path):
    text = re.sub(r"(?ms)^```.*?^```\s*$", "", path.read_text(encoding="utf-8-sig"))
    result, repeats = set(), Counter()
    for heading in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*#*\s*$", text):
        heading = re.sub(r"<[^>]*>", "", heading).lower()
        heading = "".join(c for c in heading if c in "_- " or not unicodedata.category(c).startswith(("P", "S")))
        slug = re.sub(r"\s", "-", heading)
        count = repeats[slug]
        repeats[slug] += 1
        result.add(slug + (f"-{count}" if count else ""))
    return result


def links_check(root):
    checked, skipped, issues = [], 0, []
    for name in SKILLS:
        skill = root / name
        for path in sorted(skill.rglob("*")):
            if not path.is_file():
                continue
            targets = []
            if path.suffix == ".md":
                text = path.read_text(encoding="utf-8-sig")
                text = re.sub(r"(?ms)^```.*?^```\s*$", "", text)
                targets = [(m.group(1) or m.group(2), path.parent) for m in re.finditer(
                    r"\]\(\s*(?:<([^>]+)>|([^\s)]+))[^)]*\)", text)]
                targets += [(m.group(1), path.parent) for m in re.finditer(
                    r"(?m)^\s*\[[^\]]+\]:\s*<?([^\s>]+)", text)]
            elif path.suffix == ".html":
                targets = [(target, path.parent) for target in parsed_html(path).links]
            elif path.suffix == ".css":
                text = path.read_text(encoding="utf-8-sig")
                targets = [(m.group(1).strip(" \t\r\n\"'"), path.parent)
                           for m in re.finditer(r"url\(([^)]+)\)", text)]
            elif path.name == "exemplar-index.json":
                entries = json.loads(path.read_text(encoding="utf-8-sig"))["entries"]
                targets = [(target, skill) for entry in entries for target in entry["screenshots"]]
            for target, relative_base in targets:
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc:
                    skipped += 1
                    continue
                resolved = (relative_base / unquote(parsed.path)).resolve() if parsed.path else path
                record = {"source": path.relative_to(root).as_posix(), "target": target}
                checked.append(record)
                if not resolved.exists():
                    issues.append({**record, "problem": "missing file"})
                elif parsed.fragment and resolved.suffix in (".html", ".md"):
                    ids = parsed_html(resolved).ids if resolved.suffix == ".html" else markdown_ids(resolved)
                    if unquote(parsed.fragment) not in ids:
                        issues.append({**record, "problem": "missing fragment"})
    return {"passed": not issues, "local_references_checked": len(checked),
            "external_or_data_links_skipped": skipped, "issues": issues, "references": checked}


def run_command(args, stdin=None):
    result = subprocess.run(args, input=stdin, capture_output=True, text=True, encoding="utf-8")
    return {"command": [str(a) for a in args], "passed": result.returncode == 0,
            "exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validator", type=Path,
                        default=Path.home() / ".codex/skills/.system/skill-creator/scripts/quick_validate.py")
    args = parser.parse_args()
    before = {name: manifest_check(name) for name in ("baseline", "candidate")}
    runtime = inventory(REPO)
    candidate = inventory(BASE / "candidate")
    baseline_index = json.loads((BASE / "baseline/frontend-craft/references/exemplar-index.json").read_text(encoding="utf-8-sig"))["entries"]
    candidate_index = json.loads((BASE / "candidate/frontend-craft/references/exemplar-index.json").read_text(encoding="utf-8-sig"))["entries"]
    old_ids = [entry["id"] for entry in baseline_index]
    new_entries = [entry for entry in candidate_index if entry["id"] not in old_ids]
    duplicates = [item for item, count in Counter(entry["id"] for entry in candidate_index).items() if count > 1]
    preserved = candidate_index[:len(baseline_index)] == baseline_index
    index_result = {"passed": len(baseline_index) == 14 and len(candidate_index) == 24 and preserved
                    and len(new_entries) == 10 and not duplicates
                    and all(entry["status"] == "documented" for entry in new_entries),
                    "baseline_count": len(baseline_index), "candidate_count": len(candidate_index),
                    "original_entries_and_order_exactly_equal": preserved, "duplicate_ids": duplicates,
                    "new_entries": [{"id": e["id"], "status": e["status"],
                                     "screenshots": e["screenshots"], "capture": e["capture"]} for e in new_entries]}
    validations = {}
    for label, root in (("candidate", BASE / "candidate"), ("runtime", REPO)):
        for name in SKILLS:
            validations[f"{label}/{name}"] = run_command([sys.executable, "-X", "utf8", str(args.validator), str(root / name)])
    node = shutil.which("node")
    js = []
    if node:
        for label, root in (("candidate", BASE / "candidate"), ("runtime", REPO)):
            for name in SKILLS:
                for path in sorted((root / name).rglob("*.js")):
                    js.append({"scope": label, "file": path.relative_to(root).as_posix(), **run_command([node, "--check", str(path)])})
                for path in sorted((root / name).rglob("*.html")):
                    for number, source in enumerate(parsed_html(path).inline_scripts, 1):
                        js.append({"scope": label, "file": path.relative_to(root).as_posix(), "inline_script": number,
                                   **run_command([node, "--check", "-"], source)})
    else:
        js.append({"passed": False, "problem": "Node.js unavailable"})
    links = links_check(BASE / "candidate")
    after = {name: manifest_check(name) for name in ("baseline", "candidate")}
    result = {"checked_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
              "scope": "baseline and candidate snapshots, frontend-craft/product-design runtime only; no evaluation files, browser or network",
              "snapshot_before": before, "snapshot_after": after,
              "snapshots_and_manifests_unchanged_during_audit": before == after,
              "runtime_equals_candidate": runtime == candidate,
              "runtime_only": sorted(runtime.keys() - candidate.keys()),
              "candidate_only": sorted(candidate.keys() - runtime.keys()),
              "runtime_changed_files": sorted(p for p in runtime.keys() & candidate.keys() if runtime[p] != candidate[p]),
              "quick_validate": validations, "local_links": links, "exemplar_index": index_result, "js_syntax": js}
    result["passed"] = all(item["passed"] for item in after.values()) and before == after and runtime == candidate \
        and all(item["passed"] for item in validations.values()) and links["passed"] \
        and index_result["passed"] and all(item["passed"] for item in js)
    (BASE / "audit-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "snapshot_files": {k: v["actual_files"] for k, v in after.items()},
                      "runtime_equals_candidate": result["runtime_equals_candidate"],
                      "local_references_checked": links["local_references_checked"], "link_issues": links["issues"],
                      "index_passed": index_result["passed"], "js_checks": len(js),
                      "quick_validate": {k: v["passed"] for k, v in validations.items()}}, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
