import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "imagecraft/scripts"))
from ic import common
from ic.common import Error, external_path


class OutputBoundary(unittest.TestCase):
    def test_project_workspace_allowed_when_skill_is_installed_inside_project(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp).resolve()
            (project / ".git").mkdir()
            skill = project / ".claude/skills/imagecraft"
            skill.mkdir(parents=True)
            original = common.SKILL
            common.SKILL = skill
            try:
                job = project / ".imagecraft/jobs/hero"
                self.assertEqual(external_path(job), job)
                with self.assertRaises(Error):
                    external_path(skill / "jobs/hero")
                with self.assertRaises(Error):
                    external_path(skill)
            finally:
                common.SKILL = original

    def test_relative_paths_rejected(self):
        with self.assertRaises(Error):
            external_path(os.path.join("relative", "job"))


if __name__ == "__main__":
    unittest.main()
