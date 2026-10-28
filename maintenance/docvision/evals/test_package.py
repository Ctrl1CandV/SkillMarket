"""Package metadata checks for the distributed skill and runtime."""

from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "docvision" / "scripts"))

from dv import __version__  # noqa: E402


class PackageTests(unittest.TestCase):
    def test_runtime_version_matches_skill_metadata(self):
        frontmatter = (ROOT / "docvision" / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
        version = re.search(r"(?m)^  version:\s*(.+?)\s*$", frontmatter)
        self.assertIsNotNone(version, "SKILL.md must declare metadata.version")
        self.assertEqual(__version__, version.group(1).strip("\"'"))


if __name__ == "__main__":
    unittest.main()
