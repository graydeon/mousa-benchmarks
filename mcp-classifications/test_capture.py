"""Pure replay checks; public captures are separate executable evidence."""
import copy
import unittest
import capture


class StrictClassificationTests(unittest.TestCase):
    def setUp(self):
        self.draft = dict(schema="mousa.classification_input.v1", subject=dict(kind="segment", id="a" * 64), taxonomy="example.review", taxonomy_version="1", label="synthetic", asserter_id="example.caller", asserter_version="1", asserted_at_usec=1, confidence_ppm=0, basis=[dict(kind="representation", id="b" * 64), dict(kind="source", id="c" * 64)])

    def test_explicit_zero_roundtrip(self):
        record = capture.canonical(self.draft)
        decoded = capture.strict_loads(capture.wire.canonical(record))
        self.assertEqual(capture.accepted(decoded, self.draft), record)
        self.assertIs(type(decoded["confidence_ppm"]), int)

    def test_missing_and_coerced_confidence(self):
        for value in (None, False, True, "0", 0.0):
            with self.subTest(value=value):
                record = capture.canonical(self.draft)
                record["confidence_ppm"] = value
                with self.assertRaisesRegex(ValueError, "confidence-integer"):
                    capture.accepted(record, self.draft)
        record = capture.canonical(self.draft)
        del record["confidence_ppm"]
        with self.assertRaisesRegex(ValueError, "confidence-integer"):
            capture.accepted(record, self.draft)

    def test_strict_json(self):
        for text in ('{"confidence_ppm":0,"confidence_ppm":1}', '{"a":{"x":1,"x":2}}', '{"x":NaN}', '{} {}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                capture.strict_loads(text)

    def test_all_asserted_facts_bind_identity(self):
        original = capture.canonical(self.draft)
        for field, value in (("taxonomy", "other"), ("taxonomy_version", "2"), ("label", "other"), ("asserter_id", "other"), ("asserter_version", "2"), ("asserted_at_usec", 2), ("confidence_ppm", 1)):
            changed = dict(self.draft, **{field: value})
            self.assertNotEqual(capture.canonical(changed)["id"], original["id"])
        changed = copy.deepcopy(self.draft)
        changed["basis"].reverse()
        self.assertNotEqual(capture.canonical(changed)["id"], original["id"])

    def test_native_identity_golden(self):
        draft = dict(schema="mousa.classification_input.v1",
                     subject=dict(kind="segment", id="a454fa6d452787a2ec079bb3f453a9842a9a7d36da099123676093247e423492"),
                     taxonomy="example.sensitivity", taxonomy_version="2026-08-24",
                     label="restricted", asserter_id="example.classifier", asserter_version="1.0.0",
                     asserted_at_usec=1724544000123456, confidence_ppm=875000,
                     basis=[dict(kind="source", id="f111237310ae4db59c528c5e0e53581384059910adab736913c6e29f0ef91d41"),
                            dict(kind="observation", id="8ad5e465541e71ad6246c21fdd9da960736394e1ac4688e034471910784ea12a")])
        self.assertEqual(capture.canonical(draft)["id"], "e2219c6503abb262adf8526af12cc96bd9cd62e99e2ba6be89628695bf3c7b66")



if __name__ == "__main__":
    unittest.main()
