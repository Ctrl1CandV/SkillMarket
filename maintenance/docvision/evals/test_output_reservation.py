"""Offline regressions for atomic output reservation and forced rewrites."""

from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "docvision" / "scripts"))

from dv import output, util, verify  # noqa: E402
from dv.base import DocVisionError, Options, RawDoc  # noqa: E402


class OutputReservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / "out"

    def source(self, parent):
        source = self.root / parent / "same.png"
        source.parent.mkdir(parents=True)
        source.write_bytes(parent.encode("utf-8"))
        return source

    def write(self, source, *, force=False, body=None):
        return output.write_document(
            RawDoc(markdown=body or source.parent.name, provider="test"),
            str(source), Options(force=force), out_root=self.out,
            route={"provider": "test", "privacy": "local"},
            info={"pages": 1, "sha256": util.sha256_file(source)})

    def concurrent_writes(self, sources, *, force=False):
        # Both workers finish directory selection before either writes files.
        # Real reservation must have happened by this boundary.
        barrier = threading.Barrier(len(sources), timeout=10)
        choose = output.document_dir

        def selected(*args, **kwargs):
            directory = choose(*args, **kwargs)
            barrier.wait()
            return directory

        def attempt(source):
            try:
                return self.write(source, force=force)
            except Exception as exc:
                return exc

        with patch.object(output, "document_dir", side_effect=selected), \
                ThreadPoolExecutor(max_workers=len(sources)) as pool:
            return list(pool.map(attempt, sources))

    def assert_sources_preserved(self, sources, directories):
        for directory in directories:
            self.assertIsInstance(directory, Path)
        self.assertEqual(len(set(directories)), len(sources))
        self.assertEqual({util.read_json(path / "content.json")["source"]["path"]
                          for path in directories}, {str(path.resolve()) for path in sources})
        for source, directory in zip(sources, directories):
            markdown = directory / f"{directory.name}.md"
            self.assertIn(source.parent.name, markdown.read_text(encoding="utf-8"))

    def test_two_same_named_sources_reserve_before_writing(self):
        sources = [self.source("first"), self.source("second")]
        directories = self.concurrent_writes(sources)
        self.assert_sources_preserved(sources, directories)

    def test_many_same_slugs_retry_even_when_hash_suffixes_collide(self):
        sources = [self.source(f"source-{number}") for number in range(12)]
        with patch.object(util, "short_hash", return_value="collision"):
            directories = self.concurrent_writes(sources)
        self.assert_sources_preserved(sources, directories)

    def test_nonforced_same_source_concurrently_gets_separate_directories(self):
        source = self.source("first")
        sources = [source] * 8
        self.assert_sources_preserved(sources, self.concurrent_writes(sources))

    def test_force_does_not_reuse_another_sources_directory(self):
        sources = [self.source("first"), self.source("second")]
        directories = [self.write(sources[0]), self.write(sources[1], force=True)]
        self.assert_sources_preserved(sources, directories)

    def test_force_reuses_same_source_in_its_hash_suffixed_directory(self):
        first = self.source("first")
        second = self.source("second")
        first_dir = self.write(first)
        second_dir = self.write(second)
        self.assertEqual(self.write(second, force=True, body="replacement"), second_dir)
        self.assertEqual(util.read_json(first_dir / "content.json")["source"]["path"],
                         str(first.resolve()))

    def test_force_reuses_hash_suffixed_source_through_a_path_alias(self):
        self.write(self.source("first"))
        source = self.source("second")
        alias = source.parent / ".." / source.parent.name / source.name
        directory = self.write(alias)
        self.assertEqual(self.write(source, force=True), directory)

    def test_force_allows_changed_contents_at_the_same_source_path(self):
        source = self.source("first")
        directory = self.write(source)
        source.write_bytes(b"changed source")
        self.assertEqual(self.write(source, force=True, body="replacement"), directory)
        self.assertEqual(util.read_json(directory / "meta.json")["source"]["sha256"],
                         util.sha256_file(source))
        self.assertIn("replacement", (directory / f"{directory.name}.md").read_text(encoding="utf-8"))

    def test_concurrent_force_keeps_different_sources_separate(self):
        sources = [self.source(f"forced-{number}") for number in range(4)]
        with patch.object(util, "short_hash", return_value="collision"):
            directories = self.concurrent_writes(sources, force=True)
        self.assert_sources_preserved(sources, directories)

    def test_concurrent_force_of_same_source_is_explicitly_rejected(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                source = self.source(f"existing-{existing}")
                if existing:
                    self.write(source)
                entered = threading.Event()
                release = threading.Event()
                remap = output.remap_assets

                def pause_first(*args, **kwargs):
                    if not entered.is_set():
                        entered.set()
                        if not release.wait(timeout=10):
                            raise AssertionError("first writer was not released")
                    return remap(*args, **kwargs)

                with patch.object(output, "remap_assets", side_effect=pause_first), \
                        ThreadPoolExecutor(max_workers=2) as pool:
                    first = pool.submit(self.write, source, force=True, body="first writer")
                    try:
                        self.assertTrue(entered.wait(timeout=5))
                        alias = source.parent / ".." / source.parent.name / source.name
                        second = pool.submit(self.write, alias, force=True, body="second writer")
                        with self.assertRaisesRegex(DocVisionError, "in progress"):
                            second.result(timeout=5)
                        self.assertEqual(len(list(self.out.glob(".docvision-force-*.lock"))), 1)
                    finally:
                        release.set()
                    directory = first.result(timeout=5)
                self.assertIn("first writer", (directory / f"{directory.name}.md").read_text(encoding="utf-8"))

    def test_force_rejects_source_still_being_written_without_force(self):
        source = self.source("first")
        entered = threading.Event()
        release = threading.Event()
        check = verify.verify_document

        def pause_first(*args, **kwargs):
            # Metadata exists by verification time, so provenance alone must
            # not authorize another writer to reuse the active directory.
            if not entered.is_set():
                entered.set()
                if not release.wait(timeout=10):
                    raise AssertionError("first writer was not released")
            return check(*args, **kwargs)

        with patch.object(verify, "verify_document", side_effect=pause_first), \
                ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.write, source, body="first writer")
            try:
                self.assertTrue(entered.wait(timeout=5))
                second = pool.submit(self.write, source, force=True, body="second writer")
                with self.assertRaisesRegex(DocVisionError, "in progress"):
                    second.result(timeout=5)
            finally:
                release.set()
            directory = first.result(timeout=5)
        self.assertIn("first writer", (directory / f"{directory.name}.md").read_text(encoding="utf-8"))

    def test_reservation_failure_preserves_existing_directory_and_releases_own_lock(self):
        source = self.source("first")
        foreign = self.out / "same"
        foreign.mkdir(parents=True)
        sentinel = foreign / "sentinel.txt"
        sentinel.write_text("belongs to another writer", encoding="utf-8")
        mkdir = Path.mkdir

        def fail_suffix(path, *args, **kwargs):
            if path.parent == self.out and path.name.startswith("same-"):
                raise PermissionError("reservation denied")
            return mkdir(path, *args, **kwargs)

        with patch.object(Path, "mkdir", new=fail_suffix):
            with self.assertRaisesRegex(PermissionError, "reservation denied"):
                self.write(source, force=True)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "belongs to another writer")
        self.assertFalse(list(self.out.glob(".docvision-force-*.lock")))

    def test_write_failure_releases_own_lock_without_removing_reserved_directory(self):
        source = self.source("first")
        with patch.object(output, "remap_assets", side_effect=RuntimeError("conversion failed")):
            with self.assertRaisesRegex(RuntimeError, "conversion failed"):
                self.write(source, force=True)
        self.assertTrue((self.out / "same").is_dir())
        self.assertFalse(list(self.out.glob(".docvision-force-*.lock")))
        self.assertNotEqual(self.write(source, force=True), self.out / "same")


if __name__ == "__main__":
    unittest.main(verbosity=2)
