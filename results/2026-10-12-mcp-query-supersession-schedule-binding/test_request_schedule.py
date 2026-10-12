"""Regressions for type-preserving comparison with the frozen request schedule."""
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('capture_runner', Path(__file__).with_name('run.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RequestScheduleTest(unittest.TestCase):
    def replay(self, planned, recorded):
        key = {'tool': 'mousa_query', 'arguments': planned, 'raw': None}
        match = {'tool': 'mousa_query', 'arguments': recorded, 'raw': None}
        frame = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                 'params': {'name': 'mousa_query', 'arguments': recorded}}
        record = {'kind': 'call', 'name': 'probe', 'match': match,
                  'request': runner.stream((json.dumps(frame) + '\n').encode())}
        session = runner.Session({}, {}, replay=[record])
        session.step('call', 'probe', key, lambda: self.fail('replay produced a new step'))
        self.assertTrue(all(row['passed'] for row in session.assertions))

    def test_schedule_rejects_nested_type_substitutions(self):
        for planned, recorded in [(True, 1), (False, 0), (4096, 4096.0)]:
            with self.subTest(planned=planned, recorded=recorded):
                with self.assertRaisesRegex(ValueError, '^changed step: probe$'):
                    self.replay({'option': planned}, {'option': recorded})

    def test_matching_schedule_accepts_object_key_reordering(self):
        self.replay({'supersession': True, 'budget_bytes': 4096},
                    {'budget_bytes': 4096, 'supersession': True})


if __name__ == '__main__':
    unittest.main()
