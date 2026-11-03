"""Hand-computed metric fixtures and source-bound, rehashed observation controls."""
import argparse
import copy
from pathlib import Path
import tempfile
import unittest

import prepare
import sanity


class MetricChecks(unittest.TestCase):
    def test_binary_discount_and_reciprocal_rank(self):
        # Gold a,b; first relevant is rank2; gains at ranks2 and3.
        score = sanity.metrics(["x", "a", "b"], {"a", "b"})
        self.assertAlmostEqual(score["binary_ndcg_at_10"], 0.6934264036172708)
        self.assertEqual(score["mrr_at_10"], 0.5)
        self.assertEqual(score["recall_at_10"], 1)
        self.assertEqual(score["recall_at_100"], 1)

    def test_unique_documents_before_cutoffs(self):
        score = sanity.metrics(["x"] * 12 + ["a"], {"a", "b"})
        self.assertEqual(score["recall_at_10"], 0.5)
        self.assertEqual(score["recall_at_100"], 0.5)
        self.assertEqual(score["mrr_at_10"], 0.5)
        self.assertAlmostEqual(score["binary_ndcg_at_10"], 0.38685280723454163)

    def test_cutoffs_and_legitimate_empty(self):
        score = sanity.metrics([f"x{i}" for i in range(10)] + ["a"], {"a"})
        self.assertEqual(score, {"recall_at_10": 0, "recall_at_100": 1,
                                 "binary_ndcg_at_10": 0, "mrr_at_10": 0})
        self.assertEqual(sanity.metrics([], {"a"}), {key: 0 for key in score})
        with self.assertRaisesRegex(ValueError, "unscorable-empty-gold"):
            sanity.metrics([], set())

    def test_rendering_keeps_title_and_entire_body(self):
        self.assertEqual(prepare.render(b"\xef\xbb\xbfTitle\r\n\rBody\n"), b"Title\n\nBody")
        self.assertEqual(prepare.render(b"\x1cbody\x1c"), b"\x1cbody\x1c")
        with self.assertRaises(UnicodeDecodeError):
            prepare.render(b"\xff")


def controls(capture, sanity_directory):
    original = prepare.wire.load_capture(capture)
    stable = sanity.stable_rows(sanity_directory)
    receipts = []
    # Re-encode every mutated archive, including all node/member hashes, then load it
    # successfully before the semantic check. A stale outer hash cannot be the detector.
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        for name, detector in (("changed-enrollment-equal-count", "enrollment-identity"),
                               ("wrong-physical-mapping", "logical-physical-mapping"),
                               ("changed-ranking", "ranking-binding"),
                               ("changed-packed-evidence", "packed-binding")):
            if name.startswith("changed-enrollment"):
                mutated = copy.deepcopy(original)
                mutated["stable"]["enrolled"][0]["question"]["question_id"] = "qst_not_enrolled"
                validate = lambda value: prepare.verify(value, original)
            elif name == "wrong-physical-mapping":
                mutated = copy.deepcopy(original)
                mapping = mutated["stable"]["outcomes"][0]["mapping"]
                mapping[next(iter(mapping))] = [mutated["stable"]["corpus"][-1]["item_id"]]
                validate = lambda value: prepare.verify(value, original)
            else:
                mutated = copy.deepcopy(stable)
                key = "original-traced-1024.json.jsonl"
                if name == "changed-ranking":
                    mutated[key][0]["RankedDocIDs"].reverse()
                else:
                    mutated[key][0]["SelectedDocIDs"] = ["d-a"]
                validate = lambda value: sanity.compare_rows(value, stable)
            path = directory / (name + ".json.gz")
            prepare.wire.write_capture(path, mutated)
            loaded = prepare.wire.load_capture(path)
            try:
                validate(loaded)
            except ValueError as error:
                prepare.check(str(error) == detector, "wrong-control-detector")
                receipts.append({"control": name, "detector": str(error), "rehashed_archive": prepare.manifest(path.read_bytes()),
                                 "archive_integrity_passed": True, "semantic_rejection": True,
                                 "scope": "synthetic sanity only" if "ranking" in name or "packed" in name else "enterprise preparation"})
            else:
                raise ValueError("control-not-rejected: " + name)
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--sanity", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MetricChecks))
    prepare.check(result.wasSuccessful(), "metric-fixtures")
    receipts = controls(args.capture, args.sanity)
    args.out.write_bytes(prepare.encoded({"metric_fixture_tests": result.testsRun, "controls": receipts}))
    print("PASS: four rehashed controls rejected by intended semantic detectors; ranking/packing controls are synthetic, not enterprise scores")


if __name__ == "__main__":
    main()
