"""Synthetic structural controls; no execution or public eligibility claims."""
import copy
import hashlib
import json
import unittest
import sys
from unittest.mock import patch

import common
import scoped_preparation as codec


# Literal canonical JSON, independent of the encoder under test.
GOLDEN = (
    '{"after":{"bytes":4,"sha256":"74234e98afe7498fb5daf1f36ac2d78acc339464f950703b8c019892f982b90b"},'
    '"after_physical":{"-journal":null,"-shm":null,"-wal":null,"main":null},'
    '"before":{"bytes":4,"sha256":"74234e98afe7498fb5daf1f36ac2d78acc339464f950703b8c019892f982b90b"},'
    '"before_physical":{"-journal":null,"-shm":null,"-wal":null,"main":null},'
    '"command":{"argv":[],"cwd":".","environment":{},"exit":0,"exit_code":0,"phase":"preparation","signal":null,'
    '"stderr_hex":"","stderr_sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",'
    '"stdin_hex":"","stdin_sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",'
    '"stdout_hex":"","stdout_sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},'
    '"monitor_acceptance":"operator-attested-only","ordinal":0,"phase":"preparation",'
    '"representation":"derived-preparation-correctness","schema":"mousa.startup.preparation_correctness_row.v2"}\n'
).encode('utf-8')


def row():
    return json.loads(GOLDEN)


def assign(value, path, replacement):
    keys = path.split('.')
    for key in keys[:-1]:
        value = value[key]
    value[keys[-1]] = replacement


class ScopedPreparationTests(unittest.TestCase):
    def reject(self, value, category, field):
        for operation in (codec.validate, codec.encode):
            with self.subTest(operation=operation.__name__):
                with self.assertRaises(codec.RowError) as caught:
                    operation(value)
                self.assertTrue(str(caught.exception).startswith(f'{category}: {field}:'), str(caught.exception))
        # JSON-representable invalid values must also fail through decode.
        try:
            raw = json.dumps(value, ensure_ascii=False).encode()
        except (UnicodeError, TypeError):
            return
        with self.assertRaises(codec.RowError) as caught:
            codec.decode(raw)
        self.assertTrue(str(caught.exception).startswith(f'{category}: {field}:'), str(caught.exception))

    def test_canonical_golden_and_no_store_reference(self):
        value = row()
        self.assertIsNone(codec.validate(value))
        self.assertEqual(codec.encode(value), GOLDEN)
        self.assertEqual(common.sha(GOLDEN), 'fa75badd24cae523892a147981a7caf51e5093c657a99de6c7e5f6d3e968b2d8')
        self.assertEqual(codec.encode(codec.decode(GOLDEN)), GOLDEN)
        self.assertEqual(value['before'], {'sha256': common.sha(b'null'), 'bytes': 4})
        self.assertEqual(codec.decode(b' \n' + GOLDEN + b'\t'), value)

    def test_exited_signalled_streams_text_and_ownership(self):
        value = row()
        command = value['command']
        command.update(argv=['./bin/mousa', 'private-marker/\u00e9/e\u0301'],
                       cwd='/private/operator', environment={'PRIVATE_MARKER': 'secret-looking\x00text'})
        for name, raw in [('stdin', b'\x00\xff\r\n '), ('stdout', b' {"a":1}\n\n'), ('stderr', b'\x80error\r\n')]:
            command[name + '_hex'] = raw.hex()
            command[name + '_sha256'] = hashlib.sha256(raw).hexdigest()
        value['after_physical']['main'] = {'bytes': 0, 'sha256': common.sha(b'')}
        snapshot = copy.deepcopy(value)
        encoded = codec.encode(value)
        decoded = codec.decode(encoded)
        self.assertEqual(decoded, snapshot)
        for name in ('stdin', 'stdout', 'stderr'):
            self.assertEqual(bytes.fromhex(decoded['command'][name + '_hex']), bytes.fromhex(command[name + '_hex']))
        self.assertEqual(codec.encode(decoded), encoded)
        self.assertEqual(value, snapshot)
        decoded['command']['argv'].append('changed')
        decoded['before']['bytes'] = 9
        self.assertEqual(value, snapshot)
        self.assertEqual(codec.decode(encoded), snapshot)
        for exit_value in (7, -15):
            command.update(exit=exit_value, exit_code=exit_value if exit_value >= 0 else None,
                           signal=-exit_value if exit_value < 0 else None)
            self.assertEqual(codec.decode(codec.encode(value)), value)

    def test_closed_fields_at_every_structured_level(self):
        for path in ('', 'command', 'before', 'after', 'before_physical', 'after_physical', 'before_physical.main'):
            base = row()
            base['before_physical']['main'] = copy.deepcopy(base['before'])
            target = base
            for key in path.split('.') if path else []:
                target = target[key]
            for key in list(target):
                value = copy.deepcopy(base)
                nested = value
                for part in path.split('.') if path else []:
                    nested = nested[part]
                del nested[key]
                self.reject(value, 'fields', path or '$')
            for claim in ('monitor', 'start_ns', 'provenance', 'public_eligible'):
                value = copy.deepcopy(base)
                nested = value
                for part in path.split('.') if path else []:
                    nested = nested[part]
                nested[claim] = True
                self.reject(value, 'fields', path or '$')

    def test_explicit_types(self):
        cases = {
            'schema': [None, 2, True], 'representation': [None, []],
            'monitor_acceptance': [False, {}], 'phase': [None, 1],
            'ordinal': [True, 1.0, '0', None],
            'before': [None, [], 'ref'], 'after': [None, []],
            'before_physical': [None, []], 'after_physical': [None, []],
            'before_physical.main': [0, False, []], 'command': [None, []],
            'command.argv': [None, {}, 'cmd', ('cmd',)], 'command.cwd': [None, 1, False],
            'command.environment': [None, [], 'env'], 'command.phase': [None, 0],
            'command.exit': [False, 0.0, None, '0'],
            'command.exit_code': [False, 0.0, '0'], 'command.signal': [True, 1.0, '1'],
            'before.bytes': [True, 4.0, '4', None], 'before.sha256': [None, 1, False],
        }
        for name in ('stdin', 'stdout', 'stderr'):
            cases['command.' + name + '_hex'] = [None, 0, []]
            cases['command.' + name + '_sha256'] = [None, 0, []]
        for path, replacements in cases.items():
            for replacement in replacements:
                with self.subTest(path=path, replacement=replacement):
                    value = row()
                    assign(value, path, replacement)
                    # Tuples serialize as lists, so test only Python entry points.
                    if type(replacement) is tuple:
                        for operation in (codec.validate, codec.encode):
                            with self.assertRaisesRegex(codec.RowError, 'type: command.argv:'):
                                operation(value)
                    else:
                        self.reject(value, 'type', path)
        value = row()
        value['command']['argv'] = [1]
        self.reject(value, 'type', 'command.argv[0]')
        for environment, field in [({1: 'x'}, 'command.environment.key'), ({'X': 1}, 'command.environment.X')]:
            value = row()
            value['command']['environment'] = environment
            if 1 in environment:
                with self.assertRaisesRegex(codec.RowError, 'type: command.environment.key:'):
                    codec.validate(value)
            else:
                self.reject(value, 'type', field)

    def test_literals_reference_and_integer_boundaries(self):
        for path in ('schema', 'representation', 'monitor_acceptance', 'phase', 'command.phase'):
            value = row()
            assign(value, path, 'unknown')
            self.reject(value, 'value', path)
        for path, invalid in [('ordinal', -1), ('before.bytes', -1), ('before.bytes', common.BUDGET-common.RESERVE+1)]:
            value = row()
            assign(value, path, invalid)
            self.reject(value, 'value', path)
        for size in (0, common.BUDGET-common.RESERVE):
            value = row()
            value['before']['bytes'] = size
            codec.validate(value)
        for digest in ('a'*63, 'a'*65, 'A'*64, 'z'*64, ''):
            value = row()
            value['before']['sha256'] = digest
            self.reject(value, 'hex', 'before.sha256')

    def test_stream_hex_and_digests(self):
        for name in ('stdin', 'stdout', 'stderr'):
            for invalid in ('0', 'AA', '00 00', 'gg', '\n', 'éé'):
                value = row()
                value['command'][name + '_hex'] = invalid
                self.reject(value, 'hex', 'command.' + name + '_hex')
            for invalid in ('a'*63, 'A'*64, 'g'*64):
                value = row()
                value['command'][name + '_sha256'] = invalid
                self.reject(value, 'hex', 'command.' + name + '_sha256')
            value = row()
            value['command'][name + '_hex'] = '00'
            self.reject(value, 'digest', 'command.' + name + '_sha256')

    def test_exit_consistency(self):
        for exit_value, code, signal in [(0, None, None), (0, 1, None), (0, 0, 1),
                                         (-9, 9, 9), (-9, None, None), (-9, None, -9), (-9, None, 8)]:
            value = row()
            value['command'].update(exit=exit_value, exit_code=code, signal=signal)
            self.reject(value, 'exit', 'command')

    def test_integer_conversion_errors(self):
        limit = getattr(sys, 'get_int_max_str_digits', lambda: 0)()
        if not limit:
            self.skipTest('interpreter has no integer conversion ceiling')
        huge = 10 ** limit
        for case in ('ordinal', 'exited', 'signalled'):
            with self.subTest(case=case):
                value = row()
                raw = GOLDEN
                digits = b'1' + b'0' * limit
                if case == 'ordinal':
                    value['ordinal'] = huge
                    raw = raw.replace(b'"ordinal":0', b'"ordinal":' + digits)
                elif case == 'exited':
                    value['command'].update(exit=huge, exit_code=huge)
                    raw = raw.replace(b'"exit":0', b'"exit":' + digits)
                    raw = raw.replace(b'"exit_code":0', b'"exit_code":' + digits)
                else:
                    value['command'].update(exit=-huge, exit_code=None, signal=huge)
                    raw = raw.replace(b'"exit":0', b'"exit":-' + digits)
                    raw = raw.replace(b'"exit_code":0', b'"exit_code":null')
                    raw = raw.replace(b'"signal":null', b'"signal":' + digits)
                self.assertIsNone(codec.validate(value))
                with self.assertRaises(codec.RowError) as caught:
                    codec.encode(value)
                self.assertEqual(str(caught.exception), 'json: $: cannot encode JSON')
                with self.assertRaises(codec.RowError) as caught:
                    codec.decode(raw)
                self.assertEqual(str(caught.exception), 'json: $: invalid JSON')

    def test_strict_json_and_text(self):
        for raw in (b'[]', b'null', b'1', b'"text"', b'true'):
            with self.assertRaisesRegex(codec.RowError, r'type: \$:'):
                codec.decode(raw)
        for raw in (GOLDEN+b'{}', b'{', b'\xff', b'\xef\xbb\xbf'+GOLDEN,
                    b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e9999}'):
            with self.assertRaisesRegex(codec.RowError, r'json: \$:'):
                codec.decode(raw)
        for raw in (b'{"schema":1,"schema":2}', b'{"x":{"a":1,"a":2}}',
                    b'{"x":[{"a":1,"a":2}]}', b'{"a":1,"\\u0061":2}'):
            with self.assertRaisesRegex(codec.RowError, r'json: \$: duplicate key '):
                codec.decode(raw)
        for raw in ('{}', bytearray(GOLDEN), None):
            with self.assertRaisesRegex(codec.RowError, r'type: \$:'):
                codec.decode(raw)
        value = row()
        value['command']['cwd'] = '\ud800'
        self.reject(value, 'text', 'command.cwd')
        with self.assertRaisesRegex(codec.RowError, 'text: command.cwd:'):
            codec.decode(GOLDEN.replace(b'"cwd":"."', b'"cwd":"\\ud800"'))

    def test_size_ceiling_before_parse_and_encode_boundary(self):
        self.assertLessEqual(codec.MAX_ROW_BYTES, 4194304)
        with patch('scoped_preparation.json.loads', side_effect=AssertionError('must not parse')):
            with self.assertRaisesRegex(codec.RowError, r'size: \$:'):
                codec.decode(b' ' * (codec.MAX_ROW_BYTES + 1))
        value = row()
        value['command']['cwd'] = 'x' * (codec.MAX_ROW_BYTES - len(GOLDEN) + 1)
        encoded = codec.encode(value)
        self.assertEqual(len(encoded), codec.MAX_ROW_BYTES)
        self.assertEqual(codec.decode(encoded), value)
        value['command']['cwd'] += 'x'
        with self.assertRaisesRegex(codec.RowError, r'size: \$:'):
            codec.encode(value)
        with self.assertRaisesRegex(codec.RowError, r'size: \$:'):
            codec.decode(GOLDEN + b' ' * (codec.MAX_ROW_BYTES - len(GOLDEN) + 1))


if __name__ == '__main__':
    unittest.main()
