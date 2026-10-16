"""Regressions for JSON distinctions required by request binding and schema validation."""
import unittest

import run


class ProtocolTests(unittest.TestCase):
    def test_nested_boolean_is_not_numeric(self):
        for boolean, number in [(True, 1), (False, 0)]:
            self.assertFalse(run.same_json({'arguments': [boolean]}, {'arguments': [number]}))
            self.assertTrue(run.schema_violations({'const': boolean}, number))
            self.assertTrue(run.schema_violations({'enum': [boolean]}, number))

    def test_repeated_nested_generated_keys_are_reported(self):
        _, repeated = run.strict_json('{"params":{"arguments":{"supersession":true,"supersession":true}}}')
        self.assertEqual(repeated, ['supersession'])
        value, repeated = run.strict_json('{"left":{"id":1},"right":{"id":2}}')
        self.assertEqual(repeated, [])
        self.assertEqual(value['right']['id'], 2)

    def test_oneof_requires_exactly_one_branch(self):
        schema = {'oneOf': [{'type': 'integer'}, {'type': 'number'}]}
        self.assertTrue(run.schema_violations(schema, 1))
        self.assertEqual(run.schema_violations(schema, 1.5), [])
        self.assertTrue(run.schema_violations(schema, True))

    def test_closed_nullable_identity(self):
        schema = {'type': 'object', 'additionalProperties': False,
                  'required': ['activation_id'], 'properties': {
                      'activation_id': {'type': ['null', 'string'], 'pattern': '^[0-9a-f]{64}$'}}}
        self.assertEqual(run.schema_violations(schema, {'activation_id': None}), [])
        self.assertEqual(run.schema_violations(schema, {'activation_id': 'a' * 64}), [])
        for value in [{'activation_id': 'A' * 64}, {'activation_id': 0},
                      {'activation_id': None, 'unknown': False}, {}]:
            self.assertTrue(run.schema_violations(schema, value))


if __name__ == '__main__':
    unittest.main()
