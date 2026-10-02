"""Regressions for rejecting unsupported or malformed benchmark answers."""

import copy
import json
from pathlib import Path
import unittest

from run_codex import evaluate


class GradingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {row["id"]: row for row in map(json.loads, (Path(__file__).parent / "example/tasks.jsonl").read_text().splitlines())}

    def answer_and_event(self, case):
        evidence = dict(case["expected"]["evidence"][0], segment_id="actual-segment")
        answer = dict(case["expected"], evidence=[evidence], packet_id="actual-packet", trail_id="actual-trail")
        result = {"evidence": [dict(evidence)], "packet_id": "actual-packet", "trail_id": "actual-trail"}
        event = {"type": "item.completed", "item": {"type": "mcp_tool_call", "tool": "mousa_query", "result": {"structuredContent": {"operation": "mousa_query", "source": "fleet", "result": result}}}}
        return answer, event

    def test_malformed_answer_and_evidence_are_failures(self):
        case = self.cases["production-window"]
        reasons, _ = evaluate(case, [], [])
        self.assertIn("invalid_answer_object", reasons)
        for evidence in (None, {"item": "service-00000000-prod"}, ["not a reference"]):
            with self.subTest(evidence=evidence):
                answer = dict(case["expected"], evidence=evidence)
                reasons, _ = evaluate(case, [], answer)
                self.assertIn("invalid_evidence_array", reasons)

    def test_missing_segment_cannot_pass_with_correct_fact_and_digest(self):
        case = self.cases["production-window"]
        answer, event = self.answer_and_event(case)
        del answer["evidence"][0]["segment_id"]
        reasons, _ = evaluate(case, [event], answer)
        self.assertIn("invalid_evidence_reference", reasons)

    def test_invented_segment_is_not_released_evidence(self):
        case = self.cases["production-window"]
        answer, event = self.answer_and_event(case)
        answer["evidence"][0]["segment_id"] = "invented-segment"
        reasons, _ = evaluate(case, [event], answer)
        self.assertIn("evidence_not_released_by_tool", reasons)

    def test_structured_evidence_overrides_unparseable_rendered_text(self):
        case = self.cases["production-window"]
        answer, event = self.answer_and_event(case)
        payload = event["item"]["result"]["structuredContent"]
        event["item"]["result"] = {"content": [{"type": "text", "text": "{\"schema\":"}], "details": {"structuredContent": payload}}
        reasons, _ = evaluate(case, [event], answer)
        self.assertEqual(reasons, [])

    def test_trail_must_match_the_query_packet(self):
        case = self.cases["historical-trail"]
        answer, query = self.answer_and_event(case)
        trail = copy.deepcopy(query)
        trail["item"]["tool"] = "mousa_trail"
        trail["item"]["result"]["structuredContent"] = {"operation": "mousa_trail", "result": {"trail_id": "different-trail", "historical": {"packet_id": "different-packet"}}}
        answer.update(trail_id="different-trail", packet_id="different-packet")
        reasons, _ = evaluate(case, [query, trail], answer)
        self.assertIn("trail_not_bound_to_query", reasons)
        self.assertNotIn("unverified_historical_trail", reasons)


if __name__ == "__main__":
    unittest.main()
