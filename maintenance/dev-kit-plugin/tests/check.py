"""Structural self-check for plugins/dev-kit-plugin.

Run:  python -I maintenance/dev-kit-plugin/tests/check.py
Checks frontmatter, name/folder match, relative links, skill names mentioned in
backticks, licence files for vendored skills, and that the five linked skills
point at dev-kickoff. It does not prove the skills work.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KIT = ROOT / "plugins" / "dev-kit-plugin" / "skills"
EXPECTED = {"dev-kickoff", "dev-acceptance", "tdd", "codebase-design", "diagnose", "code-reviewer"}
VENDORED = {"tdd", "codebase-design", "code-reviewer"}
LINKED = ["product-design", "frontend-craft", "imagecraft", "presentation-craft", "video-craft"]

errors = []
checks = 0


def ok(cond, msg):
    global checks
    checks += 1
    if not cond:
        errors.append(msg)


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else None


def all_skill_names():
    names = set()
    for p in ROOT.glob("*/SKILL.md"):
        names.add(p.parent.name)
    for p in ROOT.glob("plugins/*/skills/*/SKILL.md"):
        names.add(p.parent.name)
    return names


known = all_skill_names()
found = {p.name for p in KIT.iterdir() if p.is_dir()}
ok(found == EXPECTED, f"skill folders {sorted(found)} != {sorted(EXPECTED)}")

for name in sorted(found):
    skill = KIT / name / "SKILL.md"
    ok(skill.exists(), f"{name}: SKILL.md missing")
    if not skill.exists():
        continue
    text = skill.read_text(encoding="utf-8")
    fm = frontmatter(text)
    ok(fm is not None, f"{name}: no frontmatter")
    if fm is None:
        continue
    ok(re.search(rf"^name: {re.escape(name)}$", fm, re.M) is not None, f"{name}: name field does not match folder")
    desc = re.search(r"^description: (.+)$", fm, re.M)
    ok(desc is not None and len(desc.group(1)) <= 1024, f"{name}: description missing or over 1024 chars")
    ok(re.search(r'^\s+version: "\d+\.\d+\.\d+"$', fm, re.M) is not None, f"{name}: metadata.version missing")
    if name in VENDORED:
        ok((KIT / name / "LICENSE").exists(), f"{name}: vendored skill without LICENSE")
        ok("upstream:" in fm, f"{name}: vendored skill without upstream note")

    # relative links in every markdown file of the skill
    for md in (KIT / name).rglob("*.md"):
        body = md.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", body):
            if re.match(r"^[a-z]+:", target):
                continue
            ok((md.parent / target).exists(), f"{md.relative_to(ROOT)}: broken link {target}")
        # hyphenated names in backticks are skill names; each must exist in the repo
        for ref in re.findall(r"`([a-z]+(?:-[a-z]+)+)`", body):
            ok(ref in known, f"{md.relative_to(ROOT)}: mentions unknown skill `{ref}`")

# the Matt files keep their text apart from the listed edits
tdd = (KIT / "tdd" / "SKILL.md").read_text(encoding="utf-8")
ok("Call the Skill tool" not in tdd and "call the Skill tool" not in tdd, "tdd: still names the Claude Code Skill tool")
ok("see the `dev-acceptance` skill" in tdd, "tdd: review stage not pointed at dev-acceptance")
dit = (KIT / "codebase-design" / "DESIGN-IT-TWICE.md").read_text(encoding="utf-8")
ok("## Scale it to the decision" in dit, "codebase-design: design-an-interface merge missing")

# the kickoff covers the six agreed aspects, including aesthetics
kick = (KIT / "dev-kickoff" / "SKILL.md").read_text(encoding="utf-8")
for word in ["使用者与任务", "倾向", "功能与架构", "内容与展示", "审美", "完成标准与验证档位"]:
    ok(f"**{word}**" in kick, f"dev-kickoff: aspect {word} missing")
ok("AskUserQuestion" in kick and "request_user_input" in kick and "全部按推荐" in kick, "dev-kickoff: question channels incomplete")

acc = (KIT / "dev-acceptance" / "SKILL.md").read_text(encoding="utf-8")
ok("references/reviewer.md" in acc, "dev-acceptance: reviewer branch missing")
ok("spawn_agent" in acc and "review-request.md" in acc, "dev-acceptance: reviewer fallbacks missing")
ok("推送、开 PR、合并，等用户开口" in acc, "dev-acceptance: push rule missing")

for s in LINKED:
    t = (ROOT / s / "SKILL.md").read_text(encoding="utf-8")
    ok("dev-kickoff" in t and "docs/briefs/" in t, f"{s}: no pointer to the kickoff brief")

if errors:
    print("\n".join("FAIL " + e for e in errors))
    print(f"{len(errors)} failed of {checks}")
    sys.exit(1)
print(f"OK {checks} checks")
