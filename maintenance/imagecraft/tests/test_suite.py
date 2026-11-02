import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

MAINTENANCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MAINTENANCE))
from run_suite import load_suite, main, plan


class ExpandedSuite(unittest.TestCase):
    def setUp(self):
        self.source = MAINTENANCE / "suites/expanded-v1.json"
        self.suite = json.loads(self.source.read_text(encoding="utf-8"))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "suite.json"

    def save(self, value):
        self.path.write_text(json.dumps(value), encoding="utf-8")
        return self.path

    def test_24_cases_and_four_edits(self):
        result = plan(load_suite(self.source))
        self.assertEqual((result["total_jobs"], result["text_to_image"], result["reference_edits"]), (24, 20, 4))
        self.assertEqual(len({c["group"] for c in result["cases"]}), 4)

    def test_focused_suite_has_20_bounded_cases(self):
        suite = load_suite(MAINTENANCE / "suites/focused-v1.json")
        result = plan(suite)
        self.assertEqual((result["total_jobs"], result["text_to_image"], result["reference_edits"]), (20, 20, 0))
        groups = {name: sum(c["group"] == name for c in suite["cases"]) for name in {c["group"] for c in suite["cases"]}}
        self.assertEqual(sorted(groups.values()), [6, 6, 8])
        self.assertTrue(all(c["width"] * c["height"] == 1572864 for c in suite["cases"]))

    def test_forward_reference_and_path_ids_rejected(self):
        for bad in ("24-edit-chair-room", "../../private.png"):
            suite = copy.deepcopy(self.suite)
            suite["cases"][0]["references"] = [bad]
            with self.assertRaises(ValueError):
                load_suite(self.save(suite))
        self.suite["cases"][0]["id"] = "../outside"
        with self.assertRaises(ValueError):
            load_suite(self.save(self.suite))

    def test_budget_and_duplicate_ids_rejected(self):
        suite = copy.deepcopy(self.suite)
        suite["cases"] += suite["cases"]
        with self.assertRaises(ValueError):
            load_suite(self.save(suite))
        self.suite["cases"][1]["id"] = self.suite["cases"][0]["id"]
        with self.assertRaises(ValueError):
            load_suite(self.save(self.suite))

    def test_missing_dimensions_fail_before_execution(self):
        del self.suite["cases"][0]["width"]
        with self.assertRaises(ValueError):
            load_suite(self.save(self.suite))

    def test_dry_run_has_no_execution_or_outputs(self):
        destination = Path(self.temp.name) / "not-created"
        with patch("run_suite.execute") as execute, patch("sys.stdout", new=io.StringIO()) as stream:
            code = main(["--suite", str(self.source), "--dry-run", "--output", str(destination)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stream.getvalue())["total_jobs"], 24)
            execute.assert_not_called()
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
