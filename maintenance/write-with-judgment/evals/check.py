"""Static check for write-with-judgment 1.2.0: files, links, frontmatter, archive integrity, and negation/hedge density."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "write-with-judgment"
ARCHIVE_010 = ROOT / "maintenance/write-with-judgment/archive/0.1.0"
ARCHIVE_021 = ROOT / "maintenance/write-with-judgment/archive/0.2.1"
ARCHIVE_100 = ROOT / "maintenance/write-with-judgment/archive/1.0.0"
ARCHIVE_110 = ROOT / "maintenance/write-with-judgment/archive/1.1.0"

HEDGES = re.compile(r"不能|不必|不要|无须|无需|不等于|不代表|不证明|未必|也可能|可能")

files = sorted(p for p in PACKAGE.rglob("*") if p.is_file())
assert {p.relative_to(PACKAGE).as_posix() for p in files} == {
    "SKILL.md", "references/exemplars.md", "references/revision-and-diagnosis.md"
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
assert "name: write-with-judgment" in frontmatter
assert re.search(r"^description: .+", frontmatter, re.M)
assert 'version: "1.2.0"' in frontmatter

entry_body = re.sub(r"^---\r?\n.*?\r?\n---\r?\n", "", entry, flags=re.S)
entry_chars = len(re.findall(r"[^\s]", entry_body))
assert entry_chars <= 3000, f"SKILL.md too long: {entry_chars} chars"

interval = total_chars / total_hedges if total_hedges else float("inf")
assert interval >= 200.0, f"Hedge interval too low: {interval:.1f} chars/hedge"

assert (ARCHIVE_010 / "SKILL.md").is_file()
assert {p.relative_to(ARCHIVE_021).as_posix() for p in ARCHIVE_021.rglob("*") if p.is_file()} == {
    "SKILL.md", "references/choices.md", "references/emotion-and-voice.md", "references/revision.md"
}
assert {p.relative_to(ARCHIVE_100).as_posix() for p in ARCHIVE_100.rglob("*") if p.is_file()} == {
    "SKILL.md", "references/exemplars.md", "references/revision-and-diagnosis.md"
}
assert {p.relative_to(ARCHIVE_110).as_posix() for p in ARCHIVE_110.rglob("*") if p.is_file()} == {
    "SKILL.md", "references/exemplars.md", "references/revision-and-diagnosis.md"
}

print(f"PASS: 3 runtime files, {links} local links, SKILL.md={entry_chars} chars, hedge interval={interval:.1f} chars/hedge (>=200), archives intact")
