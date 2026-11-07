"""Check failure attribution and retained artifact/provenance boundaries."""
import copy
import unittest

import run
import analyze


class FailureBoundaryTest(unittest.TestCase):
    def attempt(self, stderr="", exit_code=1):
        return {"exit": exit_code, "stderr": run.base.wire.stream(stderr.encode())}

    def test_preparation_failure_does_not_claim_query_attempt(self):
        native = run.artifact_fields(None, None, b'{"segmentation":')
        boundary = run.arm_boundary(native, self.attempt("beir: ingest failed"), ["q1", "q2"])
        self.assertEqual(boundary["status"], "PREPARATION_FAILED")
        self.assertIsNone(boundary["failed_query_id"])
        self.assertEqual(native["artifact_errors"], {"manifest": "malformed"})

    def test_timeout_requires_identifying_native_diagnostic(self):
        native = run.artifact_fields(b'{"QueryID":"q1"}\n', None, None)
        timeout = run.arm_boundary(native, self.attempt("beir: query q2 exceeded its request deadline: context deadline exceeded\n"), ["q1", "q2", "q3"])
        self.assertEqual((timeout["status"], timeout["failed_query_id"], timeout["failed_query_status"]), ("QUERY_FAILED", "q2", "TIMEOUT"))
        unknown = run.arm_boundary(native, self.attempt("process killed"), ["q1", "q2", "q3"])
        self.assertEqual(unknown["status"], "INTERRUPTED")
        self.assertIsNone(unknown["failed_query_id"])

    def test_truncated_report_preserves_completed_journal(self):
        journal = b'{"QueryID":"q1"}\n{"QueryID":"q2"}\n'
        native = run.artifact_fields(journal, b'{"queries":', b'{}')
        self.assertEqual([r["QueryID"] for r in native["journal"]], ["q1", "q2"])
        self.assertEqual(analyze.validate_stream(native["report_raw"]), b'{"queries":')
        self.assertEqual(native["artifact_errors"], {"report": "malformed"})
        self.assertEqual(run.arm_boundary(native, self.attempt(exit_code=0), ["q1", "q2"])["status"], "ARTIFACT_FAILED")

    def test_partial_journal_retains_prefix_and_raw_tail(self):
        native = run.artifact_fields(b'{"QueryID":"q1"}\n{"Query', None, None)
        self.assertEqual(native["journal"], [{"QueryID": "q1"}])
        self.assertEqual(analyze.validate_stream(native["journal_tail"]), b'{"Query')
        self.assertIsNone(run.arm_boundary(native, self.attempt(), ["q1", "q2"])["failed_query_id"])

    def test_stream_extra_fields_and_stale_text_rejected(self):
        original = run.base.wire.stream(b"original stderr")
        for mutation in ({"extra": True}, {"text": "forged timeout"}):
            value = dict(original, **mutation)
            with self.assertRaises(ValueError):
                analyze.validate_stream(value)

    def test_publication_and_resource_schema(self):
        capture = {"publication": {"public_head": "1" * 40, "public_tree": "2" * 40,
                                  "binary_identity": {"sha256": "3" * 64, "bytes": 100}},
                   "collection_wall_seconds": 1,
                   "attempts": [{"wall_seconds": 1, "user_seconds": 0, "system_seconds": None,
                                 "peak_rss_kib": 100, "exit": 0, "experiment_timeout": False,
                                 "argv": ["beir"], "stdout": run.base.wire.stream(b""),
                                 "stderr": run.base.wire.stream(b"")}]}
        analyze.validate_provenance(capture)
        for field, value in (("wall_seconds", -1), ("user_seconds", float("nan")), ("peak_rss_kib", True)):
            changed = copy.deepcopy(capture)
            changed["attempts"][0][field] = value
            with self.assertRaises(ValueError):
                analyze.validate_provenance(changed)
        del capture["publication"]
        with self.assertRaises(ValueError):
            analyze.validate_provenance(capture)


if __name__ == "__main__":
    unittest.main()
