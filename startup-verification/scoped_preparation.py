"""Candidate preparation-correctness row; structural validation, not eligibility."""
import json
import math
import re

from common import BUDGET, RESERVE, sha

SCHEMA = 'mousa.startup.preparation_correctness_row.v2'
MAX_ROW_BYTES = 4194304
ROW_FIELDS = frozenset(('schema', 'representation', 'monitor_acceptance', 'phase',
                        'ordinal', 'before', 'after', 'before_physical', 'after_physical', 'command'))
PHYSICAL_FIELDS = frozenset(('main', '-wal', '-shm', '-journal'))
COMMAND_FIELDS = frozenset(('argv', 'cwd', 'environment', 'phase', 'stdin_hex',
                            'stdout_hex', 'stderr_hex', 'stdin_sha256', 'stdout_sha256',
                            'stderr_sha256', 'exit', 'exit_code', 'signal'))


class RowError(ValueError):
    """A deterministic category, field path and detail separated by colons."""


def fail(category, field, detail):
    raise RowError(f'{category}: {field}: {detail}')


def typed(value, expected, field):
    if type(value) is not expected:
        fail('type', field, 'expected ' + expected.__name__)


def text(value, field):
    typed(value, str, field)
    try:
        value.encode('utf-8')
    except UnicodeEncodeError:
        fail('text', field, 'invalid UTF-8 text')


def fields(value, expected, field):
    typed(value, dict, field)
    for key in value:
        text(key, field + '.key')
    if set(value) != expected:
        missing = ','.join(sorted(expected - value.keys()))
        unknown = ','.join(sorted(value.keys() - expected))
        fail('fields', field, f'missing [{missing}]; unknown [{unknown}]')


def literal(value, expected, field):
    text(value, field)
    if value != expected:
        fail('value', field, 'expected ' + expected)


def digest(value, field):
    text(value, field)
    if re.fullmatch('[0-9a-f]{64}', value) is None:
        fail('hex', field, 'expected 64 lowercase hex characters')


def reference(value, field):
    fields(value, {'sha256', 'bytes'}, field)
    digest(value['sha256'], field + '.sha256')
    typed(value['bytes'], int, field + '.bytes')
    if not 0 <= value['bytes'] <= BUDGET - RESERVE:
        fail('value', field + '.bytes', 'outside object size range')


def validate(row):
    """Check structure without mutation; this does not guarantee JSON conversion."""
    fields(row, ROW_FIELDS, '$')
    literal(row['schema'], SCHEMA, 'schema')
    literal(row['representation'], 'derived-preparation-correctness', 'representation')
    literal(row['monitor_acceptance'], 'operator-attested-only', 'monitor_acceptance')
    literal(row['phase'], 'preparation', 'phase')
    typed(row['ordinal'], int, 'ordinal')
    if row['ordinal'] < 0:
        fail('value', 'ordinal', 'expected nonnegative integer')
    for name in ('before', 'after'):
        reference(row[name], name)
        physical = name + '_physical'
        fields(row[physical], PHYSICAL_FIELDS, physical)
        for key in sorted(PHYSICAL_FIELDS):
            if row[physical][key] is not None:
                reference(row[physical][key], physical + '.' + key)
    command = row['command']
    fields(command, COMMAND_FIELDS, 'command')
    typed(command['argv'], list, 'command.argv')
    for index, argument in enumerate(command['argv']):
        text(argument, f'command.argv[{index}]')
    text(command['cwd'], 'command.cwd')
    typed(command['environment'], dict, 'command.environment')
    for key, value in command['environment'].items():
        text(key, 'command.environment.key')
        text(value, 'command.environment.' + key)
    literal(command['phase'], 'preparation', 'command.phase')
    for name in ('stdin', 'stdout', 'stderr'):
        field = 'command.' + name + '_hex'
        encoded = command[name + '_hex']
        text(encoded, field)
        if len(encoded) % 2 or re.fullmatch('[0-9a-f]*', encoded) is None:
            fail('hex', field, 'expected lowercase even-length hex')
        field = 'command.' + name + '_sha256'
        digest(command[name + '_sha256'], field)
        if sha(bytes.fromhex(encoded)) != command[name + '_sha256']:
            fail('digest', field, 'stream SHA-256 mismatch')
    typed(command['exit'], int, 'command.exit')
    for name in ('exit_code', 'signal'):
        if command[name] is not None:
            typed(command[name], int, 'command.' + name)
    status = command['exit']
    if status >= 0:
        valid = command['exit_code'] == status and command['signal'] is None
    else:
        valid = command['exit_code'] is None and command['signal'] == -status
    if not valid:
        fail('exit', 'command', 'inconsistent exit/exit_code/signal')


def encode(row):
    """Emit bounded canonical UTF-8 JSON plus LF; conversion failures are RowError."""
    validate(row)
    # iterencode bounds accumulated output before joining; its JSON options match
    # common.canonical. No identity or normalization rule is added here.
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    chunks = []
    size = 1
    try:
        for chunk in encoder.iterencode(row):
            raw = chunk.encode('utf-8')
            size += len(raw)
            if size > MAX_ROW_BYTES:
                fail('size', '$', 'row exceeds byte ceiling')
            chunks.append(raw)
    except RowError:
        raise
    except ValueError:
        fail('json', '$', 'cannot encode JSON')
    return b''.join(chunks) + b'\n'


def decode(raw):
    """Parse bounded strict JSON and return an independently owned valid row."""
    typed(raw, bytes, '$')
    if len(raw) > MAX_ROW_BYTES:
        fail('size', '$', 'row exceeds byte ceiling')

    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                fail('json', '$', 'duplicate key ' + key)
            result[key] = value
        return result

    def constant(value):
        fail('json', '$', 'nonfinite number ' + value)

    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            fail('json', '$', 'nonfinite number ' + value)
        return number

    try:
        # Explicit UTF-8 matches canonical; json.loads(bytes) also accepts UTF-16/32.
        row = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                         parse_constant=constant, parse_float=finite)
    except RowError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        fail('json', '$', 'invalid JSON')
    validate(row)
    return row
