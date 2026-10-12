"""Verify Git safety semantics in owned temporary repositories, without network.

Run with Python 3.9+ and Git. Set SKILL_EVAL_TEMP to an existing writable
directory if the system temp directory is unavailable. This is maintenance
tooling, not a skill dependency.
"""

import io
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest


class GitSemantics(unittest.TestCase):
    def setUp(self):
        self.temp_parent = Path(os.environ.get("SKILL_EVAL_TEMP", tempfile.gettempdir())).resolve()
        self.root = Path(tempfile.mkdtemp(prefix="git-governance-eval-", dir=self.temp_parent)).resolve()
        self.addCleanup(self.cleanup_fixture)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.hooks = self.root / "empty-hooks"
        self.hooks.mkdir()
        self.env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("GIT_")
        }
        self.env.update({
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C",
        })
        self.git("init", "--initial-branch=main")

    def cleanup_fixture(self):
        root = self.root.resolve()
        if root.parent != self.temp_parent or not root.name.startswith("git-governance-eval-"):
            raise RuntimeError("Refusing to remove a path outside the owned fixture")

        def remove_readonly(function, path, exc_info):
            resolved = Path(path).resolve()
            if root not in resolved.parents and resolved != root:
                raise RuntimeError("Cleanup target escaped fixture")
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            function(path)

        shutil.rmtree(root, onerror=remove_readonly)

    def git(self, *args, cwd=None, expected=0):
        result = subprocess.run([
            "git", "-c", "user.name=Git Governance Fixture",
            "-c", "user.email=fixture@example.invalid",
            "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false",
            "-c", f"core.hooksPath={self.hooks}", *args,
        ], cwd=cwd or self.repo, env=self.env, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, expected, result.stderr.decode("utf-8", "replace"))
        return result.stdout

    def write(self, path, text):
        file = self.repo / path
        file.parent.mkdir(parents=True, exist_ok=True)
        with file.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)

    def seed(self, files=None):
        files = files or {"src.txt": "base\n"}
        for path, text in files.items():
            self.write(path, text)
        self.git("add", "--", *files)
        self.git("commit", "-m", "test: create fixture")

    def test_ignore_does_not_untrack_and_cached_removal_keeps_local(self):
        self.seed({".env": "FAKE_FIXTURE_VALUE=1\n"})
        self.write(".gitignore", ".env\n")
        self.assertEqual(self.git("ls-files", "--", ".env"), b".env\n")
        self.git("check-ignore", "-v", "--", ".env", expected=1)
        self.assertIn(b".env", self.git("check-ignore", "-v", "--no-index", "--", ".env"))
        self.git("rm", "--cached", "--", ".env")
        self.assertTrue((self.repo / ".env").exists())
        self.assertEqual(self.git("ls-files", "--", ".env"), b"")
        self.assertIn(b"FAKE_FIXTURE_VALUE", self.git("show", "HEAD:.env"))

    def test_unstage_preserves_work_and_other_staged_changes(self):
        self.seed({"src.txt": "base\n", "user.txt": "base\n"})
        self.write("src.txt", "task change\n")
        self.write("user.txt", "user change\n")
        self.git("add", "--", "src.txt", "user.txt")
        self.git("restore", "--staged", "--", "src.txt")
        self.assertEqual((self.repo / "src.txt").read_text(), "task change\n")
        self.assertEqual(self.git("diff", "--cached", "--name-only"), b"user.txt\n")

    def test_unborn_index_can_remove_staged_path_without_deleting_file(self):
        self.write("local.txt", "unsaved local fixture\n")
        self.git("add", "--", "local.txt")
        self.git("rm", "--cached", "--", "local.txt")
        self.assertTrue((self.repo / "local.txt").exists())
        self.assertEqual(self.git("ls-files"), b"")

    def test_clean_preview_and_scoped_cleanup_preserve_local_files(self):
        self.seed({"src.txt": "base\n", ".gitignore": ".env\n"})
        self.write(".env", "FAKE_LOCAL_VALUE=1\n")
        self.write("notes.txt", "user notes\n")
        self.write("disposable/output.txt", "rebuildable\n")
        preview = self.git("clean", "-nd", "--", "disposable/")
        self.assertIn(b"disposable/", preview)
        self.assertNotIn(b"notes.txt", preview)
        self.assertNotIn(b".env", preview)
        self.assertTrue((self.repo / "disposable/output.txt").exists())
        self.assertIn(b".env", self.git("clean", "-ndX"))
        self.assertIn(b"notes.txt", self.git("clean", "-ndx"))
        self.git("clean", "-fd", "--", "disposable/")
        self.assertFalse((self.repo / "disposable").exists())
        self.assertTrue((self.repo / ".env").exists())
        self.assertTrue((self.repo / "notes.txt").exists())

    def test_ignore_exception_requires_visible_parent(self):
        self.seed()
        self.write("data/fixtures/sample.csv", "x,y\n1,2\n")
        self.write("data/private.csv", "fake fixture data\n")
        self.write(".gitignore", "/data/\n!/data/fixtures/\n")
        self.git("check-ignore", "-q", "--", "data/fixtures/sample.csv")
        self.write(".gitignore", "/data/*\n!/data/fixtures/\n")
        self.git("check-ignore", "-q", "--", "data/fixtures/sample.csv", expected=1)
        self.git("check-ignore", "-q", "--", "data/private.csv")

    def test_archive_exclusion_does_not_remove_tracked_files(self):
        self.seed({
            "src.txt": "runtime\n", "maintenance/report.md": "evaluation\n",
            ".gitattributes": "maintenance/ export-ignore\n",
        })
        with tarfile.open(fileobj=io.BytesIO(self.git("archive", "--format=tar", "HEAD"))) as archive:
            names = archive.getnames()
        self.assertIn("src.txt", names)
        self.assertFalse(any(name.startswith("maintenance") for name in names))
        self.assertIn(b"maintenance/report.md", self.git("ls-tree", "-r", "--name-only", "HEAD"))

    def test_full_merge_imports_branch_only_directory(self):
        self.seed()
        self.git("switch", "-c", "dev")
        self.write("maintenance/report.md", "branch-only fixture\n")
        self.git("add", "--", "maintenance/report.md")
        self.git("commit", "-m", "docs: add development report")
        self.git("switch", "main")
        self.assertFalse((self.repo / "maintenance").exists())
        self.git("merge", "--no-ff", "dev", "-m", "test: integrate branch")
        self.assertTrue((self.repo / "maintenance/report.md").exists())

    def test_worktree_does_not_copy_dirty_or_untracked_files(self):
        self.seed()
        self.write("src.txt", "uncommitted change\n")
        self.write("needed.txt", "untracked dependency\n")
        other = self.root / "other-worktree"
        self.git("worktree", "add", "-b", "topic", str(other), "HEAD")
        self.assertEqual((other / "src.txt").read_text(), "base\n")
        self.assertFalse((other / "needed.txt").exists())
        self.assertEqual((self.repo / "src.txt").read_text(), "uncommitted change\n")
        self.assertTrue((self.repo / "needed.txt").exists())

    def test_deleted_file_still_travels_in_exported_history(self):
        self.seed({"obsolete.txt": "FAKE_HISTORY_CONTENT\n"})
        initial = self.git("rev-parse", "HEAD").decode().strip()
        self.git("rm", "--", "obsolete.txt")
        self.git("commit", "-m", "chore: remove obsolete file")
        bundle = self.root / "history.bundle"
        self.git("bundle", "create", str(bundle), "main")
        remote = self.root / "imported.git"
        self.git("clone", "--bare", str(bundle), str(remote))
        self.assertEqual(self.git("show", f"{initial}:obsolete.txt", cwd=remote), b"FAKE_HISTORY_CONTENT\n")
        self.assertNotIn(b"obsolete.txt", self.git("ls-tree", "--name-only", "main", cwd=remote))


if __name__ == "__main__":
    unittest.main(verbosity=2)
