"""Reject altered, omitted, incomplete or reordered native scenario evidence."""

import argparse
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from analyze import analyze, sha


class EvidenceTests(unittest.TestCase):
    capture_root = None

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "run"
        shutil.copytree(self.capture_root, self.root)

    def rehash(self, name):
        path = self.root / "members.json"
        manifest = json.loads(path.read_text())
        data = (self.root / name).read_bytes()
        manifest["files"][name] = {"bytes": len(data), "sha256": sha(data)}
        path.write_text(json.dumps(manifest))

    def test_omitted_or_substituted_member_is_invalid(self):
        manifest = json.loads((self.root / "members.json").read_text())
        name = next(n for n in manifest["files"] if n.endswith(".jsonl"))
        path = self.root / name
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            analyze(self.root)
        path.unlink()
        with self.assertRaisesRegex(ValueError, "membership mismatch"):
            analyze(self.root)

    def test_missing_response_is_incomplete_not_assertion_pass(self):
        run = json.loads((self.root / "summary.json").read_text())
        name = run["operations"][0]["receipt"]
        path = self.root / name
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows = [row for row in rows if not (row["direction"] == "response" and row["message"].get("id") == 4)]
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        self.rehash(name)
        result = analyze(self.root)
        self.assertEqual(result["assertion_status"], "INCOMPLETE")
        self.assertEqual(result["missing_evidence"][0]["operation"], 0)

    def test_reordered_epochs_do_not_satisfy_frozen_protocol(self):
        path = self.root / "summary.json"
        run = json.loads(path.read_text())
        run["operations"][0], run["operations"][3] = run["operations"][3], run["operations"][0]
        path.write_text(json.dumps(run))
        self.rehash("summary.json")
        result = analyze(self.root)
        self.assertNotEqual(result["assertion_status"], "PASS")
        self.assertEqual([r["operation"] for r in result["failures"][:2]], [0, 3])

    def test_success_report_cannot_substitute_native_result(self):
        run = json.loads((self.root / "summary.json").read_text())
        name = run["operations"][0]["stdout"]
        path = self.root / name
        report = json.loads(path.read_text())
        report["result"]["added"] = ["fabricated"]
        path.write_text(json.dumps(report))
        self.rehash(name)
        result = analyze(self.root)
        self.assertEqual(result["assertion_status"], "FAIL")
        self.assertEqual(result["failures"][0]["operation"], 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    EvidenceTests.capture_root = args.run.resolve(strict=True)
    unittest.main(argv=["analyze_test", *remaining])
