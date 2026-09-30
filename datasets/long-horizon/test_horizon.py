"""Regressions for distant memory labels and stale/corrupt evidence rejection."""

import json
from pathlib import Path
import tempfile
import unittest

from generate import generate, label, record
from run import grade


class HorizonTests(unittest.TestCase):
    def test_chronology_preserves_early_memory_and_replaces_current_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory) / "corpus"
            generate(dataset, documents=257, epochs=17)
            state = {}
            introduced = set()
            with (dataset / "events.jsonl").open() as events:
                for line in events:
                    event = json.loads(line)
                    for row in event["items"]:
                        if row.get("deleted"):
                            state.pop(row["id"])
                        else:
                            introduced.add(row["id"])
                            state[row["id"]] = row
            self.assertEqual(len(introduced), 257)
            self.assertEqual(len(state), 256)
            self.assertEqual(state["memory-000000000"], record(20260930, 0)[0])
            self.assertEqual(state["memory-000000009"], record(20260930, 9, 2)[0])
            self.assertNotIn("memory-000000001", state)
            plan = json.loads((dataset / "tasks.json").read_text())
            earliest = next(case for case in plan["cases"] if case["id"] == "retention-0")
            self.assertEqual(earliest["intervening_documents"], 256)
            for case in plan["cases"]:
                for expected in case["expected"]:
                    self.assertEqual(expected, label(state[expected["item"]]))

    def test_stale_revision_does_not_pass_current_memory_label(self):
        current, _ = record(20260930, 9, 2)
        old, _ = record(20260930, 9)
        evidence = dict(label(old), text=old["text"])
        self.assertIn("wrong_provenance", grade([label(current)], {"evidence": [evidence]}))

    def test_withdrawn_evidence_is_not_an_empty_answer(self):
        old, _ = record(20260930, 1)
        self.assertIn("wrong_selected_items", grade([], {"evidence": [dict(label(old), text=old["text"])]}))

    def test_matching_metadata_cannot_hide_corrupt_released_text(self):
        row, _ = record(20260930, 0)
        evidence = dict(label(row), text="changed bytes")
        self.assertIn("corrupt_released_bytes", grade([label(row)], {"evidence": [evidence]}))


if __name__ == "__main__":
    unittest.main()
