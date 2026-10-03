"""Run with Python 3; checks package structure, links, and archived originals only."""
from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "de-ai-flavor"
ARCHIVE = ROOT / "maintenance/de-ai-flavor/archive/before-generalization-2026-10-03"
EXPECTED = {
    "SKILL.md": "738530b7be9cd791da55fb7c4fba278d6f4a24f1820d99d5c3eb23126d3e27af",
    "references/course-voice.md": "73de6bb579883b38ba4289bbf27b356dff64e655b82f66eec69fccac849cc2ae",
    "references/genres.md": "7158a7c65d78aaa26b81068a8cef8ac710e795acacd9628fce7f4bf91a030ace",
    "references/patterns.md": "06439c567f1f7f7af56f065a7e5ffb66f55628743dda1ea0d79db6fe126d2ef6",
    "references/replacements.md": "562e78de01bc5f3bd18c3f816461991284560d0ff1ddba7f31a5229ab9e8488e",
}
files = sorted(p for p in PACKAGE.rglob("*") if p.is_file())
assert {p.relative_to(PACKAGE).as_posix() for p in files} == {
    "SKILL.md", "references/genres.md", "references/patterns.md"
}
links = 0
for path in files:
    text = path.read_text(encoding="utf-8")
    assert "\ufffd" not in text, path
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        if "://" not in target and not target.startswith("#"):
            resolved = (path.parent / target.split("#")[0]).resolve()
            assert resolved.is_relative_to(PACKAGE.resolve()), target
            assert resolved.is_file(), target
            links += 1
    for obsolete in ("course-voice.md", "replacements.md", "SpecialtyCourses", "优先处理真正的病", "减少模板带来的迂回"):
        assert obsolete not in text, (path, obsolete)
    print(f"UTF-8 OK: {path.relative_to(ROOT).as_posix()} ({len(text.splitlines())} lines)")
entry = (PACKAGE / "SKILL.md").read_text(encoding="utf-8")
assert entry.startswith("---\n")
frontmatter = entry.split("---", 2)[1]
assert "name: de-ai-flavor" in frontmatter
assert re.search(r"^description: .+", frontmatter, re.M)
assert 'version: "2.1.0"' in frontmatter
assert "## 从零生成" in entry and "## 修改已有文本" in entry
for name, expected in EXPECTED.items():
    assert hashlib.sha256((ARCHIVE / name).read_bytes()).hexdigest() == expected, name
print(f"PASS: 3 runtime files, {links} local links, frontmatter fields, 2 writing paths, 5 exact archived originals")
print("Scope: static checks only; not a writing-quality or trigger test.")
