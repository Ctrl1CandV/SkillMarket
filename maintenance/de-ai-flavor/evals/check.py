"""Static check for de-ai-flavor 3.1.0: files, links, frontmatter, archive integrity, and negation/hedge density."""
from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "de-ai-flavor"
ARCHIVE_202 = ROOT / "maintenance/de-ai-flavor/archive/before-generalization-2026-10-03"
ARCHIVE_210 = ROOT / "maintenance/de-ai-flavor/archive/2.1.0"
ARCHIVE_300 = ROOT / "maintenance/de-ai-flavor/archive/3.0.0"

EXPECTED_202 = {
    "SKILL.md": "738530b7be9cd791da55fb7c4fba278d6f4a24f1820d99d5c3eb23126d3e27af",
    "references/course-voice.md": "73de6bb579883b38ba4289bbf27b356dff64e655b82f66eec69fccac849cc2ae",
    "references/genres.md": "7158a7c65d78aaa26b81068a8cef8ac710e795acacd9628fce7f4bf91a030ace",
    "references/patterns.md": "06439c567f1f7f7af56f065a7e5ffb66f55628743dda1ea0d79db6fe126d2ef6",
    "references/replacements.md": "562e78de01bc5f3bd18c3f816461991284560d0ff1ddba7f31a5229ab9e8488e",
}

HEDGES = re.compile(r"不能|不必|不要|无须|无需|不等于|不代表|不证明|未必|也可能|可能")

files = sorted(p for p in PACKAGE.rglob("*") if p.is_file())
assert {p.relative_to(PACKAGE).as_posix() for p in files} == {
    "SKILL.md", "references/exemplars.md", "references/genres.md"
}, [p.relative_to(PACKAGE).as_posix() for p in files]

links = 0
total_chars = 0
total_hedges = 0

for path in files:
    text = path.read_text(encoding="utf-8")
    assert "\ufffd" not in text, path
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        if "://" not in target and not target.startswith("#"):
            resolved = (path.parent / target.split("#")[0]).resolve()
            assert resolved.is_relative_to(PACKAGE.resolve()), target
            assert resolved.is_file(), target
            links += 1
    body = re.sub(r"^---\r?\n.*?\r?\n---\r?\n", "", text, flags=re.S)
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    chars = len(re.findall(r"[^\s]", body))
    hedges = len(HEDGES.findall(body))
    total_chars += chars
    total_hedges += hedges
    print(f"UTF-8 OK: {path.relative_to(ROOT).as_posix()} ({len(text.splitlines())} lines, {chars} non-code chars, {hedges} hedges)")

entry = (PACKAGE / "SKILL.md").read_text(encoding="utf-8")
assert entry.startswith("---"), "Missing frontmatter"
frontmatter = entry.split("---", 2)[1]
assert "name: de-ai-flavor" in frontmatter
assert re.search(r"^description: .+", frontmatter, re.M)
assert 'version: "3.1.0"' in frontmatter

entry_body = re.sub(r"^---\r?\n.*?\r?\n---\r?\n", "", entry, flags=re.S)
entry_chars = len(re.findall(r"[^\s]", entry_body))
assert entry_chars <= 3000, f"SKILL.md too long: {entry_chars} chars"

interval = total_chars / total_hedges if total_hedges else float("inf")
assert interval >= 200.0, f"Hedge interval too low: {interval:.1f} chars/hedge"

for name, expected in EXPECTED_202.items():
    assert hashlib.sha256((ARCHIVE_202 / name).read_bytes()).hexdigest() == expected, name

assert {p.relative_to(ARCHIVE_210).as_posix() for p in ARCHIVE_210.rglob("*") if p.is_file()} == {
    "SKILL.md", "references/genres.md", "references/patterns.md"
}
assert {p.relative_to(ARCHIVE_300).as_posix() for p in ARCHIVE_300.rglob("*") if p.is_file()} == {
    "SKILL.md", "references/exemplars.md", "references/genres.md"
}

print(f"PASS: 3 runtime files, {links} local links, SKILL.md={entry_chars} chars, hedge interval={interval:.1f} chars/hedge (>=200), archives intact")
