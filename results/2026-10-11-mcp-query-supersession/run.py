#!/usr/bin/env python3
"""Independent stdio MCP query-supersession capture; Python 3.9+, standard library only.

This runner speaks newline-delimited JSON-RPC 2.0 to an explicitly supplied Mousa
executable, the transport the published stdio MCP interface uses. It builds no product
code, imports no product internals, contains no product identity codec and uses no SDK
test utility: the executable is the observation engine, the frozen protocol and fixture
inputs are prepared separately (see prepare.py), and the runner only compares what it
observed with what the protocol and a passing pilot fixed.

Modes:
    discovery  capture one executable's tools/list definitions (baseline provenance)
    pilot      run the schedule without frozen expectations; only a passing pilot freezes
    freeze     verify a passing pilot and write its observed selections as expectations
    capture    run the schedule against frozen expectations; exit 1 on a false assertion
    verify     re-check an extracted capture: membership, wire integrity, provenance and
               regenerated assertions
    negative-controls  mutate copies of a capture; every copy must be rejected
    forbidden-write    the same schedule with one injected write inside a read bracket
    manifest   rewrite one archive directory's member manifest
    package    assemble the published result directory from the capture directories

Exit status: 0 on success, 1 when an assertion is false, 2 for a rejected precondition,
a verification failure or a damaged archive.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import select
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parent
PROTOCOL_SCHEMA = 'mousa.mcp_query_supersession.v1'
EXPECTATIONS_SCHEMA = 'mousa.mcp_query_supersession_expectations.v1'
OBSERVED_SCHEMA = 'mousa.mcp_query_supersession_observed.v1'
MANIFEST_SCHEMA = 'mousa.run_manifest.v1'
BASELINE_SCHEMA = 'mousa.mcp_discovery_capture.v1'
AUDIT_PREFIXES = ('policy_evaluation', 'policy_decision', 'source_trail')
TOOLS = ('mousa_sync', 'mousa_status', 'mousa_query', 'mousa_trail')
CALL_TIMEOUT = 40.0
PROTOCOL_VERSION = '2025-11-25'
CLIENT_NAME = 'mousa-mcp-supersession-capture'
CALLER = 'cli'

# Documented comparison exclusions: query identities and timing are fresh per call, and a
# trail inspection's recorded identities are validated against this run's own query.
VOLATILE_QUERY = ('request_id', 'decision_id', 'trail_id', 'evaluated_at_usec', 'latency_micros')
VOLATILE_TRAIL = ('authorization_decision_id', 'trail_id')
RECORDED_TRAIL_IDENTITIES = ('id', 'request_id', 'decision_id')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()


def save(path, value):
    path.write_bytes(encoded(value))


def stream(data):
    return {'bytes': len(data), 'sha256': sha(data), 'base64': base64.b64encode(data).decode(),
            'text': data.decode('utf-8', 'replace')}


def load_protocol(root=ROOT):
    protocol = json.loads((root / 'protocol.json').read_bytes())
    if protocol['schema'] != PROTOCOL_SCHEMA:
        raise ValueError('unknown protocol')
    inputs = root / 'inputs'
    if not inputs.is_dir() or sorted(p.name for p in inputs.iterdir()) != sorted(protocol['inputs']):
        raise ValueError('fixture membership differs')
    frozen = {}
    for name, digest in protocol['inputs'].items():
        data = (inputs / name).read_bytes()
        if sha(data) != digest:
            raise ValueError('damaged frozen input: ' + name)
        frozen[name] = data
    if protocol['baseline_discovery']['tools']['mousa_query']['name'] != 'mousa_query':
        raise ValueError('baseline discovery is not a tool list')
    for key, expected in (('protocol_version', PROTOCOL_VERSION), ('client_name', CLIENT_NAME),
                          ('caller', CALLER)):
        if protocol[key] != expected:
            raise ValueError('protocol disagrees with the runner on ' + key)
    return protocol, frozen


def sql_name(name):
    return '"' + name.replace('"', '""') + '"'


def sql_value(value):
    if isinstance(value, bytes):
        return ['blob', value.hex()]
    return [type(value).__name__, value]


def fingerprint(path):
    """Complete committed logical tables in one read snapshot, including WAL-visible rows."""
    if path is None or not Path(path).exists():
        return None
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        connection.execute('BEGIN')
        schema = list(connection.execute(
            'SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name'))
        tables = {}
        for kind, name, _, _ in schema:
            if kind != 'table':
                continue
            rows = [encoded([sql_value(value) for value in row])
                    for row in connection.execute('SELECT * FROM ' + sql_name(name))]
            rows.sort()
            tables[name] = {'rows': len(rows), 'sha256': sha(b''.join(rows))}
        return {'schema_sha256': sha(encoded(schema)),
                'user_version': connection.execute('PRAGMA user_version').fetchone()[0],
                'tables': tables}
    finally:
        connection.close()


def immutable(fp):
    if fp is None:
        return None
    return {**fp, 'tables': {name: rows for name, rows in fp['tables'].items()
                             if not name.startswith(AUDIT_PREFIXES)}}


def stable_query(result):
    return {key: value for key, value in result.items() if key not in VOLATILE_QUERY}


def stable_trail(result):
    stable = {key: value for key, value in result.items() if key not in VOLATILE_TRAIL}
    historical = stable.get('historical')
    if isinstance(historical, dict):
        stable['historical'] = {key: value for key, value in historical.items()
                                if key not in RECORDED_TRAIL_IDENTITIES}
    return stable


def json_delta(before, after, path=''):
    """Structural delta between two JSON values as added, removed and changed paths."""
    added, removed, changed = [], [], []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            child = path + '.' + key
            if key not in before:
                added.append(child)
            elif key not in after:
                removed.append(child)
            else:
                a, r, c = json_delta(before[key], after[key], child)
                added += a
                removed += r
                changed += c
    elif isinstance(before, list) and isinstance(after, list):
        for index in range(max(len(before), len(after))):
            child = '%s[%d]' % (path, index)
            if index >= len(before):
                added.append(child)
            elif index >= len(after):
                removed.append(child)
            else:
                a, r, c = json_delta(before[index], after[index], child)
                added += a
                removed += r
                changed += c
    elif before != after:
        changed.append(path)
    return added, removed, changed


def keys_used(value, found=None):
    """Every object key appearing anywhere in a JSON value."""
    found = set() if found is None else found
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(key)
            keys_used(item, found)
    elif isinstance(value, list):
        for item in value:
            keys_used(item, found)
    return found


def type_matches(expected, value):
    for name in (expected if isinstance(expected, list) else [expected]):
        if name == 'null' and value is None:
            return True
        if name == 'boolean' and isinstance(value, bool):
            return True
        if name == 'integer' and isinstance(value, int) and not isinstance(value, bool):
            return True
        if name == 'number' and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if name == 'string' and isinstance(value, str):
            return True
        if name == 'array' and isinstance(value, list):
            return True
        if name == 'object' and isinstance(value, dict):
            return True
    return False


def schema_violations(schema, value, path='$'):
    """Bounded JSON Schema subset checker.

    Supported: type, const, enum, pattern, minLength/maxLength, minimum/maximum,
    minItems/maxItems, properties, required, additionalProperties (false or schema),
    items and oneOf. Not implemented: formats, $ref/$defs, allOf/anyOf/not,
    unevaluatedProperties, patternProperties, dependencies, exclusive bounds and
    $schema-driven dialect selection. Every schema Mousa discovers over stdio is
    inline and needs only the supported subset; this is not a general JSON Schema
    implementation.
    """
    problems = []
    if not isinstance(schema, dict):
        return problems
    if 'type' in schema and not type_matches(schema['type'], value):
        return ['%s: expected type %s, observed %s' % (path, schema['type'], type(value).__name__)]
    if 'const' in schema and value != schema['const']:
        problems.append('%s: expected const %r' % (path, schema['const']))
    if 'enum' in schema and value not in schema['enum']:
        problems.append('%s: value is not in the declared enum' % path)
    if isinstance(value, str):
        if 'pattern' in schema and not re.search(schema['pattern'], value):
            problems.append('%s: does not match the declared pattern' % path)
        if 'minLength' in schema and len(value) < schema['minLength']:
            problems.append('%s: shorter than minLength' % path)
        if 'maxLength' in schema and len(value) > schema['maxLength']:
            problems.append('%s: longer than maxLength' % path)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 'minimum' in schema and value < schema['minimum']:
            problems.append('%s: below minimum' % path)
        if 'maximum' in schema and value > schema['maximum']:
            problems.append('%s: above maximum' % path)
    if isinstance(value, list):
        if 'minItems' in schema and len(value) < schema['minItems']:
            problems.append('%s: fewer than minItems' % path)
        if 'maxItems' in schema and len(value) > schema['maxItems']:
            problems.append('%s: more than maxItems' % path)
        if isinstance(schema.get('items'), dict):
            for index, item in enumerate(value):
                problems += schema_violations(schema['items'], item, '%s[%d]' % (path, index))
    if isinstance(value, dict):
        properties = schema.get('properties', {})
        for name in schema.get('required', []):
            if name not in value:
                problems.append('%s: missing required property %s' % (path, name))
        additional = schema.get('additionalProperties', True)
        for name, item in value.items():
            child = '%s.%s' % (path, name)
            if name in properties:
                problems += schema_violations(properties[name], item, child)
            elif additional is False:
                problems.append('%s: undeclared property' % child)
            elif isinstance(additional, dict):
                problems += schema_violations(additional, item, child)
    branches = schema.get('oneOf', [])
    if branches and not any(not schema_violations(branch, value, path) for branch in branches):
        problems.append('%s: no oneOf branch matches' % path)
    return problems


def validate_pin(pin):
    for key in ('public_head', 'public_tree', 'executable_sha256', 'toolchain',
                'build_command', 'build_environment', 'build_receipt'):
        if not pin.get(key):
            raise ValueError('missing published product/build pin field: ' + key)
    receipt = pin['build_receipt']
    if receipt['exit'] != 0:
        raise ValueError('supplied build did not succeed')
    if receipt['argv'] != pin['build_command']:
        raise ValueError('build command differs from receipt')
    for key in ('stdin', 'stdout', 'stderr'):
        if stream(base64.b64decode(receipt[key]['base64'], validate=True)) != receipt[key]:
            raise ValueError('damaged supplied build stream: ' + key)


class LineReader:
    """Newline-delimited reader over a pipe with a per-message deadline."""

    def __init__(self, fd):
        self.fd = fd
        self.buffer = b''

    def readline(self, timeout):
        deadline = time.monotonic() + timeout
        while b'\n' not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('no MCP message within %.1fs' % timeout)
            ready, _, _ = select.select([self.fd], [], [], remaining)
            if not ready:
                raise TimeoutError('no MCP message within %.1fs' % timeout)
            chunk = os.read(self.fd, 65536)
            if not chunk:
                if not self.buffer:
                    return b''
                line, self.buffer = self.buffer, b''
                return line
            self.buffer += chunk
        line, _, self.buffer = self.buffer.partition(b'\n')
        return line


class Server:
    """One stdio MCP server process driving one store."""

    def __init__(self, binary, store, label, caller, stderr_path):
        self.binary, self.store = Path(binary), Path(store)
        self.argv = [str(self.binary), '-store', str(self.store), 'mcp', '--caller', caller,
                     '--source', label]
        self.stderr_path = Path(stderr_path)
        self.stderr_file = open(self.stderr_path, 'wb')
        self.process = subprocess.Popen(self.argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.stderr_file)
        self.reader = LineReader(self.process.stdout.fileno())
        self.next_id = 0

    def request(self, method=None, params=None, raw=None, timeout=CALL_TIMEOUT):
        if raw is None:
            self.next_id += 1
            message = {'jsonrpc': '2.0', 'id': self.next_id, 'method': method}
            if params is not None:
                message['params'] = params
            payload = json.dumps(message, ensure_ascii=False, separators=(',', ':')).encode()
        else:
            payload = raw
        self.process.stdin.write(payload + b'\n')
        self.process.stdin.flush()
        response = self.reader.readline(timeout)
        return payload + b'\n', (response + b'\n') if response else b''

    def notify(self, method):
        payload = json.dumps({'jsonrpc': '2.0', 'method': method}, separators=(',', ':')).encode() + b'\n'
        self.process.stdin.write(payload)
        self.process.stdin.flush()
        return payload

    def stop(self):
        try:
            self.process.stdin.close()
        except OSError:
            pass
        try:
            code = self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.kill()
            code = None
        self.stderr_file.close()
        return code, self.stderr_path.read_bytes()


class Session:
    """Records one schedule and regenerates its assertions from the records."""

    def __init__(self, protocol, frozen, binary=None, work=None, replay=None, forbidden=False):
        self.p, self.f = protocol, frozen
        self.binary, self.work = binary, work
        self.replay = replay
        self.forbidden = forbidden
        self.steps, self.assertions, self.selections = [], [], {}
        self.sessions = []
        self.index = 0
        self.frame_id = 100
        self.server = None
        self.current_store = None
        self.request_ids = {}
        self.discovery = {}
        self.results = {}
        self.errors = {}

    # -- assertions ---------------------------------------------------------------
    def expect(self, ident, expected, observed):
        record = {'id': ident, 'expected': expected, 'observed': observed,
                  'passed': type(expected) is type(observed) and expected == observed}
        self.assertions.append(record)
        return record

    def yes(self, ident, condition):
        return self.expect(ident, True, bool(condition))

    def contains(self, ident, needle, haystack):
        return self.yes(ident, needle in haystack)

    # -- recording ----------------------------------------------------------------
    def step(self, kind, name, key, produce):
        """Return the recorded step: replayed when verifying, otherwise produced."""
        if self.replay is not None:
            if self.index >= len(self.replay):
                raise ValueError('omitted step: ' + name)
            record = self.replay[self.index]
            self.index += 1
            if (record['kind'], record['name'], record['match']) != (kind, name, key):
                raise ValueError('changed step: ' + name)
            self.steps.append(record)
            return record
        record = produce()
        self.steps.append(record)
        return record

    def bracket(self, name, record):
        """A read-only protocol step: unchanged tables, or the store opening itself."""
        if record['fingerprint_before'] is None:
            self.yes(name + ':store-opened-during-startup',
                     record['fingerprint_after'] is not None)
        else:
            self.expect(name + ':unchanged-all-tables', record['fingerprint_before'],
                        record['fingerprint_after'])

    def fingerprint_of(self, store):
        if self.replay is not None:
            return None
        return fingerprint(self.work / (store + '.sqlite'))

    # -- preparation, damage and process steps ------------------------------------
    def native(self, name, argv, payload=b'', store='main', expected_exit=0, mode='prepare'):
        key = {'argv': argv, 'stdin': stream(payload)}

        def produce():
            path = self.work / (store + '.sqlite')
            before = fingerprint(path)
            result = subprocess.run([str(self.binary), '-store', str(path), *argv],
                                    input=payload, capture_output=True, cwd=self.work)
            after = fingerprint(path)
            return {'kind': 'native', 'name': name, 'store': store, 'mode': mode, 'match': key,
                    'argv': ['<binary>', '-store', '<work>/' + store + '.sqlite', *argv],
                    'stdin': stream(payload), 'exit': result.returncode,
                    'stdout': stream(result.stdout), 'stderr': stream(result.stderr),
                    'fingerprint_before': before, 'fingerprint_after': after}

        record = self.step('native', name, key, produce)
        self.expect(name + ':exit', expected_exit, record['exit'])
        if mode in ('read', 'reject'):
            self.expect(name + ':unchanged-all-tables', record['fingerprint_before'],
                        record['fingerprint_after'])
        elif mode == 'write':
            self.yes(name + ':store-changed',
                     record['fingerprint_before'] != record['fingerprint_after'])
        return record

    def damage(self, name, statements, store):
        key = {'sql': list(statements), 'store': store}

        def produce():
            path = self.work / (store + '.sqlite')
            before = fingerprint(path)
            connection = sqlite3.connect(path)
            for statement in statements:
                connection.execute(statement)
            connection.commit()
            connection.close()
            return {'kind': 'damage', 'name': name, 'store': store, 'mode': 'damage', 'match': key,
                    'sql': list(statements), 'fingerprint_before': before,
                    'fingerprint_after': fingerprint(path)}

        record = self.step('damage', name, key, produce)
        self.yes(name + ':store-changed',
                 record['fingerprint_before'] != record['fingerprint_after'])
        return record

    def start(self, session, store, prepared=True):
        caller, label = self.p['caller'], self.p['source_label']
        key = {'store': store, 'caller': caller, 'label': label}

        def produce():
            stderr_path = self.work / ('%s-%d-stderr.log' % (store, len(self.sessions)))
            before = fingerprint(self.work / (store + '.sqlite'))
            self.server = Server(self.binary, self.work / (store + '.sqlite'), label, caller,
                                 stderr_path)
            return {'kind': 'start', 'name': session + ':start', 'store': store, 'mode': 'start',
                    'match': key,
                    'argv': ['<binary>', '-store', '<work>/' + store + '.sqlite', 'mcp',
                             '--caller', caller, '--source', label],
                    'stderr_path': stderr_path.name,
                    'fingerprint_before': before, 'fingerprint_after': None}

        record = self.step('start', session + ':start', key, produce)
        self.expect(session + ':store-' + ('prepared' if prepared else 'absent') + '-before-start',
                    prepared, record['fingerprint_before'] is not None)
        self.current_store = store
        self.request_ids[session] = []
        self.sessions.append({'session': session, 'store': store, 'start': record})
        return record

    def protocol_call(self, session, name, method, params=None, raw=None, mode='protocol'):
        key = {'method': method, 'params': params, 'raw': raw.decode() if raw else None}

        def produce():
            before = self.fingerprint_of(self.current_store)
            payload, response = self.server.request(method, params, raw)
            after = self.fingerprint_of(self.current_store)
            return {'kind': 'protocol', 'name': name, 'store': self.current_store, 'mode': mode,
                    'match': key, 'request': stream(payload), 'response': stream(response),
                    'fingerprint_before': before, 'fingerprint_after': after}

        record = self.step('protocol', name, key, produce)
        self.bracket(name, record)
        return record

    def notify(self, session, name, method):
        key = {'method': method}

        def produce():
            before = self.fingerprint_of(self.current_store)
            payload = self.server.notify(method)
            after = self.fingerprint_of(self.current_store)
            return {'kind': 'notify', 'name': name, 'store': self.current_store, 'mode': 'notify',
                    'match': key, 'request': stream(payload), 'response': stream(b''),
                    'fingerprint_before': before, 'fingerprint_after': after}

        record = self.step('notify', name, key, produce)
        self.bracket(name, record)
        return record

    def call(self, session, name, tool, arguments=None, raw=None, mode='query', store=None):
        store = store or self.current_store
        key = {'tool': tool, 'arguments': arguments, 'raw': raw.decode() if raw else None}

        def produce():
            before = self.fingerprint_of(store)
            params = {'name': tool, 'arguments': arguments} if raw is None else None
            payload, response = self.server.request('tools/call', params, raw)
            after = self.fingerprint_of(store)
            record = {'kind': 'call', 'name': name, 'store': store, 'tool': tool, 'mode': mode,
                      'match': key, 'request': stream(payload), 'response': stream(response),
                      'fingerprint_before': before, 'fingerprint_after': after}
            if self.forbidden and mode == 'read':
                connection = sqlite3.connect(self.work / (store + '.sqlite'))
                connection.execute('CREATE TABLE forbidden_control(value TEXT)')
                connection.commit()
                connection.close()
                record['fingerprint_after'] = self.fingerprint_of(store)
                record['negative_control_sql'] = ['CREATE TABLE forbidden_control(value TEXT)',
                                                  'DROP TABLE forbidden_control']
                self.forbidden = False
                connection = sqlite3.connect(self.work / (store + '.sqlite'))
                connection.execute('DROP TABLE forbidden_control')
                connection.commit()
                connection.close()
            return record

        record = self.step('call', name, key, produce)
        return self.check_call(session, record, mode)

    def stop(self, session, expected_exit=0, stderr_text=''):
        key = {'session': session}

        def produce():
            code, stderr = self.server.stop()
            self.server = None
            return {'kind': 'stop', 'name': session + ':stop', 'mode': 'stop', 'match': key,
                    'store': self.current_store, 'exit': code, 'stderr': stream(stderr)}

        record = self.step('stop', session + ':stop', key, produce)
        self.sessions[-1]['stop'] = record
        self.expect(session + ':shutdown-exit', expected_exit, record['exit'])
        if stderr_text:
            self.contains(session + ':shutdown-stderr', stderr_text, record['stderr']['text'])
        else:
            self.expect(session + ':stderr-empty-on-shutdown', '', record['stderr']['text'])
        return record

    # -- response assertions ------------------------------------------------------
    def check_call(self, session, record, mode):
        name = record['name']
        parsed = None
        if record['response']['bytes']:
            try:
                parsed = json.loads(record['response']['text'])
            except ValueError:
                parsed = None
        self.yes(name + ':json-response', isinstance(parsed, dict))
        if mode in ('read', 'reject'):
            self.expect(name + ':unchanged-all-tables', record['fingerprint_before'],
                        record['fingerprint_after'])
        elif mode in ('query', 'inspection'):
            self.expect(name + ':unchanged-administration-canonical-index',
                        immutable(record['fingerprint_before']),
                        immutable(record['fingerprint_after']))
            self.yes(name + ':audit-written',
                     record['fingerprint_before'] != record['fingerprint_after'])
        if not isinstance(parsed, dict):
            return None
        self.expect(name + ':jsonrpc', '2.0', parsed.get('jsonrpc'))
        requested = json.loads(record['request']['text'])
        self.expect(name + ':response-id-matches-request', requested.get('id'), parsed.get('id'))
        result = parsed.get('result')
        self.yes(name + ':result-present', isinstance(result, dict))
        if not isinstance(result, dict):
            return None
        envelope = result.get('structuredContent')
        self.yes(name + ':structured-content', isinstance(envelope, dict))
        if not isinstance(envelope, dict):
            return None
        self.expect(name + ':error-flag', 'error' in envelope, result.get('isError') is True)
        self.expect(name + ':content-text', True,
                    isinstance(result.get('content'), list) and len(result['content']) == 1
                    and isinstance(result['content'][0].get('text'), str))
        self.expect(name + ':envelope-keys',
                    sorted([*self.p['envelope_keys'], 'result' if 'result' in envelope else 'error']),
                    sorted(envelope))
        self.yes(name + ':envelope-payload-exclusive', ('result' in envelope) != ('error' in envelope))
        self.expect(name + ':schema-version', self.p['result_version'], envelope.get('schema'))
        self.expect(name + ':operation', record['tool'], envelope.get('operation'))
        try:
            self.expect(name + ':text-content-equals-structured', envelope,
                        json.loads(result['content'][0]['text']))
        except (ValueError, KeyError):
            self.yes(name + ':text-content-equals-structured', False)
        schema = self.discovery.get(record['tool'])
        if schema is not None:
            self.expect(name + ':closed-schema', [], schema_violations(schema, envelope))
        return envelope

    # -- discovery ----------------------------------------------------------------
    def check_discovery(self, session, record):
        by_name = {tool['name']: tool
                   for tool in json.loads(record['response']['text'])['result']['tools']}
        self.expect(session + ':discovered-tools', sorted(TOOLS), sorted(by_name))
        self.discovery = {name: tool['outputSchema'] for name, tool in by_name.items()}
        baseline = self.p['baseline_discovery']['tools']
        for name in ('mousa_sync', 'mousa_status', 'mousa_trail'):
            self.expect(session + ':baseline-definition-unchanged:' + name, baseline[name],
                        by_name[name])
        for name in TOOLS:
            self.expect(session + ':declared-result-keys:' + name,
                        sorted(self.p['declared_result_keys'][name]),
                        sorted(by_name[name]['outputSchema']['properties']['result']['properties']))
            self.expect(session + ':result-required:' + name,
                        sorted(self.p['result_required'][name]),
                        sorted(by_name[name]['outputSchema']['properties']['result'].get('required', [])))
            self.expect(session + ':error-required:' + name, sorted(self.p['error_required']),
                        sorted(by_name[name]['outputSchema']['properties']['error']['required']))
            self.expect(session + ':output-closed:' + name, False,
                        by_name[name]['outputSchema'].get('additionalProperties'))
        query = by_name['mousa_query']
        added, removed, changed = json_delta(baseline['mousa_query'], query)
        self.expect(session + ':query-definition-delta',
                    self.p['baseline_discovery']['query_definition_delta'],
                    {'added': added, 'removed': removed, 'changed': changed})
        supersession = query['inputSchema']['properties'].get('supersession', {})
        self.expect(session + ':query-input-property', 'boolean', supersession.get('type'))
        self.yes(session + ':query-input-property-described',
                 isinstance(supersession.get('description'), str) and len(supersession['description']) > 0)
        self.expect(session + ':query-input-closed', False, query['inputSchema'].get('additionalProperties'))
        for name in ('mousa_sync', 'mousa_status', 'mousa_trail'):
            self.yes(session + ':baseline-tool-has-no-supersession-input:' + name,
                     'supersession' not in by_name[name]['inputSchema'].get('properties', {}))
        self.expect(session + ':trail-output-has-no-supersession',
                    False, 'supersession' in json.dumps(by_name['mousa_trail']['outputSchema']))
        return by_name

    def check_initialize(self, session, record):
        result = json.loads(record['response']['text'])['result']
        self.expect(session + ':protocol-version', self.p['protocol_version'],
                    result.get('protocolVersion'))
        self.expect(session + ':server-info', {'name': 'mousa', 'version': '1'},
                    result.get('serverInfo'))
        self.expect(session + ':capabilities', {'tools': {}}, result.get('capabilities'))
        self.yes(session + ':instructions-nonempty',
                 isinstance(result.get('instructions'), str) and len(result['instructions']) > 0)
        return result

    # -- tool-result checks -------------------------------------------------------
    def check_query(self, session, name, envelope, expect):
        result = envelope.get('result')
        self.yes(name + ':result-payload', isinstance(result, dict))
        if not isinstance(result, dict):
            self.selections[name] = {'query': None}
            return None
        self.expect(name + ':result-keys', sorted(expect['keys']), sorted(result))
        self.expect(name + ':query', expect['query'], result.get('query'))
        self.expect(name + ':query-policy', self.p['query_policy'], result.get('query_policy'))
        self.expect(name + ':source', self.p['source_label'], result.get('source'))
        self.expect(name + ':budget-bytes', expect['budget'], result.get('budget_bytes'))
        self.expect(name + ':outcome', expect['outcome'], result.get('outcome'))
        self.expect(name + ':count-present', expect['opted'], 'supersession_excluded' in result)
        if expect['opted']:
            self.expect(name + ':count', expect.get('suppressed', 0),
                        result.get('supersession_excluded'))
        self.expect(name + ':packing-present', expect['packing'] is not None,
                    'packing_policy' in result)
        if expect['packing'] is not None:
            self.expect(name + ':packing-policy', expect['packing'], result.get('packing_policy'))
        self.expect(name + ':duplicate-count-present', expect.get('duplicate_present', False),
                    'duplicate_omitted' in result)
        if expect.get('duplicate_present'):
            self.expect(name + ':duplicate-count', expect['duplicate_omitted'],
                        result.get('duplicate_omitted'))
        self.expect(name + ':budget-omitted', expect['budget_omitted'], result.get('budget_omitted'))
        self.expect(name + ':matched-candidates', expect['matched'], result.get('matched_candidates'))
        self.expect(name + ':lifecycle-excluded', 0, result.get('lifecycle_excluded'))
        self.expect(name + ':candidate-limit', self.p['candidate_limit'], result.get('candidate_limit'))
        self.expect(name + ':decision-outcome', expect['decision'], result.get('decision_outcome'))
        self.expect(name + ':decision-reasons', expect['reasons'], result.get('decision_reasons'))
        evidence = result.get('evidence') or []
        self.expect(name + ':evidence-items', sorted(expect['items']),
                    sorted(hit.get('item') for hit in evidence))
        self.expect(name + ':used-bytes', sum(len(hit['text'].encode()) for hit in evidence),
                    result.get('used_bytes'))
        for hit in evidence:
            pin = self.p['items'].get(hit.get('item'))
            if pin is None:
                self.yes(name + ':known-evidence-item-' + str(hit.get('item')), False)
                continue
            self.expect(name + ':evidence-keys-' + hit['item'], sorted(self.p['evidence_keys']),
                        sorted(hit))
            self.expect(name + ':text-' + hit['item'], pin['text'], hit.get('text'))
            self.expect(name + ':digest-' + hit['item'], pin['content_sha256'],
                        hit.get('content_sha256'))
            self.expect(name + ':segment-' + hit['item'], pin['segment_id'], hit.get('segment_id'))
            self.expect(name + ':representation-' + hit['item'], pin['representation_id'],
                        hit.get('representation_id'))
            self.expect(name + ':representation-digest-' + hit['item'], pin['content_sha256'],
                        hit.get('representation_sha256'))
            self.expect(name + ':byte-start-' + hit['item'], 0, hit.get('byte_start'))
            self.expect(name + ':byte-end-' + hit['item'], pin['bytes'], hit.get('byte_end'))
            self.expect(name + ':byte-length-' + hit['item'], pin['bytes'], hit.get('byte_length'))
            self.expect(name + ':segment-policy-' + hit['item'], self.p['segment_policy'],
                        hit.get('segment_policy'))
        for key in ('request_id', 'decision_id', 'trail_id', 'packet_id'):
            self.expect(name + ':identity-' + key, True,
                        isinstance(result.get(key), str) and len(result[key]) == 64
                        and all(character in '0123456789abcdef' for character in result[key]))
        if expect.get('withheld') is not None:
            withheld = self.p['items'][expect['withheld']]['segment_id']
            self.yes(name + ':withheld-not-released',
                     withheld not in {hit.get('segment_id') for hit in evidence})
        self.expect(name + ':fresh-request-id', True,
                    result['request_id'] not in self.request_ids[session])
        self.request_ids[session].append(result['request_id'])
        self.results[name] = result
        self.selections[name] = {'query': stable_query(result)}
        return result

    def check_trail(self, session, name, envelope, expect):
        result = envelope.get('result')
        self.yes(name + ':result-payload', isinstance(result, dict))
        if not isinstance(result, dict):
            self.selections[name] = {'trail': None}
            return None
        self.expect(name + ':result-keys',
                    sorted(self.p['result_keys']['mousa_trail']) if expect['historical']
                    else sorted(self.p['trail_denied_result_keys']), sorted(result))
        self.expect(name + ':source', self.p['source_label'], result.get('source'))
        self.expect(name + ':trail-id', expect['trail_id'], result.get('trail_id'))
        self.expect(name + ':authorization-outcome', expect['authorization'],
                    result.get('authorization_outcome'))
        self.expect(name + ':authorization-reasons', expect['reasons'],
                    result.get('authorization_reasons'))
        self.expect(name + ':no-supersession-anywhere', False,
                    'supersession' in json.dumps(envelope))
        for item, pin in self.p['items'].items():
            self.expect(name + ':no-evidence-text-' + item, False,
                        pin['text'] in json.dumps(envelope))
        self.expect(name + ':no-text-property', False, 'text' in keys_used(result))
        historical = result.get('historical')
        if not expect['historical']:
            self.expect(name + ':no-historical', None, historical)
            self.selections[name] = {'trail': stable_trail(result)}
            return result
        self.yes(name + ':historical-present', isinstance(historical, dict))
        self.expect(name + ':historical-keys', sorted(self.p['trail_historical_keys']),
                    sorted(historical))
        self.expect(name + ':historical-schema', self.p['trail_schema'], historical.get('schema'))
        self.expect(name + ':historical-id', expect['trail_id'], historical.get('id'))
        for key in ('request_id', 'decision_id', 'packet_id', 'budget_bytes', 'used_bytes'):
            self.expect(name + ':historical-' + key, expect['query'].get(key), historical.get(key))
        self.expect(name + ':historical-packing', expect['query'].get('packing_policy'),
                    historical.get('packing_policy'))
        self.expect(name + ':historical-expression', expect['query'].get('expression'),
                    historical.get('expression'))
        self.expect(name + ':historical-decision', expect['query'].get('decision_outcome'),
                    historical.get('decision_outcome'))
        self.expect(name + ':historical-reasons', expect['query'].get('decision_reasons'),
                    historical.get('decision_reasons'))
        candidates = historical.get('candidates') or []
        self.expect(name + ':candidate-ranks', list(range(1, len(candidates) + 1)),
                    [row.get('rank') for row in candidates])
        self.expect(name + ':candidate-keys', sorted(self.p['trail_candidate_keys']),
                    sorted(candidates[0]) if candidates else [])
        for row in candidates:
            pin = next((pin for pin in self.p['items'].values()
                        if pin['segment_id'] == row.get('segment_id')), None)
            self.yes(name + ':candidate-known-' + str(row.get('segment_id')), pin is not None)
            if pin is not None:
                self.expect(name + ':candidate-digest-' + row['segment_id'], pin['content_sha256'],
                            row.get('content_sha256'))
                self.expect(name + ':candidate-size-' + row['segment_id'], pin['bytes'],
                            row.get('text_bytes'))
        selected = {row['segment_id']: row for row in candidates}
        for hit in expect['query'].get('evidence', []):
            row = selected.get(hit['segment_id'], {})
            self.expect(name + ':evidence-rank-' + hit['item'], hit.get('rank'), row.get('rank'))
            self.expect(name + ':evidence-selected-' + hit['item'], True, row.get('selected') is True)
        self.expect(name + ':selected-segments',
                    sorted(hit['segment_id'] for hit in expect['query'].get('evidence', [])),
                    sorted(row['segment_id'] for row in candidates if row.get('selected')))
        self.expect(name + ':matched-candidates',
                    expect['query'].get('matched_candidates'),
                    len(candidates) + expect['query'].get('lifecycle_excluded', 0))
        self.selections[name] = {'trail': stable_trail(result)}
        return result

    def check_error(self, session, name, envelope, expect):
        error = envelope.get('error')
        self.yes(name + ':error-payload', isinstance(error, dict))
        if not isinstance(error, dict):
            self.selections[name] = {'error': None}
            return None
        self.expect(name + ':error-keys', sorted(self.p['error_required']), sorted(error))
        self.expect(name + ':error-code', expect['code'], error.get('code'))
        self.expect(name + ':completed-items', 0, error.get('completed_items'))
        self.expect(name + ':envelope-source', expect['source'], envelope.get('source'))
        self.yes(name + ':no-result-payload', 'result' not in envelope)
        if expect.get('message_contains'):
            self.contains(name + ':error-message', expect['message_contains'],
                          error.get('message', ''))
        self.errors[name] = {'code': error.get('code'), 'source': envelope.get('source'),
                             'message': error.get('message')}
        self.selections[name] = {'error': self.errors[name]}
        return error

    # -- scenario helpers ---------------------------------------------------------
    def prepare_store(self, store, steps):
        last = None
        for index, (name, argv, payload, kind) in enumerate(steps):
            last = self.native(name, argv, payload, store=store, mode='write')
            if index == 0:
                self.expect(store + ':absent-before-preparation', None,
                            last['fingerprint_before'])
            if kind == 'put':
                self.expect(name + ':canonical-bytes', payload.decode(),
                            last['stdout']['text'])
            elif kind == 'sync':
                report = json.loads(last['stdout']['text'])
                self.expect(name + ':sync-source', self.p['source_label'], report.get('source'))
                self.expect(name + ':sync-total-items', len(payload.splitlines()),
                            report.get('total_items'))
        self.expect(store + ':store-created', True, last['fingerprint_after'] is not None)

    def open_session(self, session, store, discovery=True, prepared=True):
        start = self.start(session, store, prepared=prepared)
        initialize = self.protocol_call(session, session + ':initialize', 'initialize', {
            'protocolVersion': self.p['protocol_version'], 'capabilities': {},
            'clientInfo': {'name': self.p['client_name'], 'version': '1'}})
        self.check_initialize(session, initialize)
        self.notify(session, session + ':initialized', 'notifications/initialized')
        # Startup fingerprints are sampled after the server created or migrated the store
        # and installed its deployment policy, so every per-call bracket stays clean.
        key = {'session': session}

        def produce():
            return {'kind': 'startup', 'name': session + ':startup', 'store': store,
                    'mode': 'startup', 'match': key,
                    'fingerprint_before': start['fingerprint_before'],
                    'fingerprint_after': self.fingerprint_of(store)}

        startup = self.step('startup', session + ':startup', key, produce)
        self.expect(session + ':store-exists-after-startup', True,
                    startup['fingerprint_after'] is not None)
        if prepared:
            # The deployment policy a prepared store already carries is an exact retry, so
            # starting the server changes no committed logical state of its own.
            self.expect(session + ':startup-changes-nothing', startup['fingerprint_before'],
                        startup['fingerprint_after'])
        else:
            # Opening an absent store path creates and migrates it before any call.
            self.yes(session + ':absent-store-created-at-startup',
                     startup['fingerprint_before'] is None
                     and startup['fingerprint_after'] is not None)
        self.sessions[-1]['startup'] = startup
        if discovery:
            listed = self.protocol_call(session, session + ':tools-list', 'tools/list', {})
            self.check_discovery(session, listed)
        return start

    # -- scenarios ----------------------------------------------------------------
    def scenario_fresh_store(self):
        label = self.p['source_label']
        self.open_session('fresh-store', 'fresh-store', prepared=False)
        self.frame_id += 1
        frame = ('{"jsonrpc":"2.0","id":%d,"method":"tools/call","params":{"name":"mousa_query",'
                 '"arguments":%s}}' % (self.frame_id,
                                       self.p['boundary_arguments']['null'].replace('%(source)s',
                                                                                    label))).encode()
        envelope = self.call('fresh-store', 'fresh-store:boundary-null', 'mousa_query', raw=frame,
                             mode='reject')
        self.check_error('fresh-store', 'fresh-store:boundary-null', envelope,
                         {'code': 'invalid_arguments', 'source': ''})
        self.stop('fresh-store')

    def scenario_no_history(self):
        label = self.p['source_label']
        self.prepare_store('no-history', [
            ('no-history:sync-items', ['sync', '--source', label], self.f['items.jsonl'], 'sync')])
        self.open_session('no-history', 'no-history')
        base = {'source': label, 'query': 'oldterm', 'policy': 'original', 'budget_bytes': 4096}
        expected = {'query': 'oldterm', 'budget': 4096, 'outcome': 'evidence', 'opted': False,
                    'packing': None, 'budget_omitted': 0, 'matched': 3, 'decision': 'allow',
                    'reasons': ['allow'], 'items': ['predecessor', 'duplicate', 'successor'],
                    'withheld': None, 'keys': self.p['result_keys']['query_default']}
        omitted = self.call('no-history', 'no-history:query-omitted', 'mousa_query', base, mode='query')
        self.check_query('no-history', 'no-history:query-omitted', omitted, expected)
        explicit = self.call('no-history', 'no-history:query-false', 'mousa_query',
                             {**base, 'supersession': False}, mode='query')
        self.check_query('no-history', 'no-history:query-false', explicit, expected)
        self.expect('no-history:omitted-equals-false', self.selections['no-history:query-omitted'],
                    self.selections['no-history:query-false'])
        opted = self.call('no-history', 'no-history:query-opted', 'mousa_query',
                          {**base, 'supersession': True}, mode='query')
        self.check_query('no-history', 'no-history:query-opted', opted, {
            **expected, 'opted': True, 'packing': 'original',
            'keys': self.p['result_keys']['query_opted']})
        self.expect('no-history:count-zero', 0, opted['result']['supersession_excluded'])
        self.expect('no-history:opted-packet-equals-default',
                    self.results['no-history:query-omitted']['packet_id'],
                    opted['result']['packet_id'])
        self.expect('no-history:opted-selection-equals-default',
                    {key: value for key, value
                     in self.selections['no-history:query-omitted']['query'].items()
                     if key not in ('packing_policy', 'supersession_excluded')},
                    {key: value for key, value
                     in self.selections['no-history:query-opted']['query'].items()
                     if key not in ('packing_policy', 'supersession_excluded')})
        self.yes('no-history:opted-records-its-own-trail',
                 self.results['no-history:query-omitted']['trail_id']
                 != opted['result']['trail_id'])
        status = self.call('no-history', 'no-history:status', 'mousa_status', {'source': label},
                           mode='read')
        self.expect('no-history:status-result-keys', sorted(self.p['result_keys']['mousa_status']),
                    sorted(status['result']))
        self.expect('no-history:status-source', label, status['result'].get('source'))
        for name, arguments in self.p['boundary_arguments'].items():
            self.frame_id += 1
            frame = ('{"jsonrpc":"2.0","id":%d,"method":"tools/call","params":{"name":"mousa_query",'
                     '"arguments":%s}}' % (self.frame_id,
                                           arguments.replace('%(source)s', label))).encode()
            envelope = self.call('no-history', 'no-history:boundary-' + name, 'mousa_query',
                                 raw=frame, mode='reject')
            self.check_error('no-history', 'no-history:boundary-' + name, envelope,
                             {'code': 'invalid_arguments', 'source': ''})
        control = self.call('no-history', 'no-history:sync-control', 'mousa_sync',
                            {'source': label, 'items': [{'id': 'probe', 'text': 'probe'}]},
                            mode='reject')
        self.check_error('no-history', 'no-history:sync-control', control,
                         {'code': 'ingestion_not_permitted', 'source': label})
        for name, tool, arguments in (
                ('no-history:sync-supersession', 'mousa_sync',
                 {'source': label, 'items': [{'id': 'probe', 'text': 'probe'}], 'supersession': True}),
                ('no-history:status-supersession', 'mousa_status',
                 {'source': label, 'supersession': True})):
            envelope = self.call('no-history', name, tool, arguments, mode='reject')
            self.check_error('no-history', name, envelope, {'code': 'invalid_arguments', 'source': ''})
        trail_id = self.results['no-history:query-opted']['trail_id']
        trail = self.call('no-history', 'no-history:trail-filtered', 'mousa_trail',
                          {'source': label, 'trail_id': trail_id}, mode='inspection')
        self.check_trail('no-history', 'no-history:trail-filtered', trail,
                         {'trail_id': trail_id, 'authorization': 'allow', 'reasons': ['allow'],
                          'historical': True, 'query': self.results['no-history:query-opted']})
        rejected = self.call('no-history', 'no-history:trail-supersession', 'mousa_trail',
                             {'source': label, 'trail_id': trail_id, 'supersession': True},
                             mode='reject')
        self.check_error('no-history', 'no-history:trail-supersession', rejected,
                         {'code': 'invalid_arguments', 'source': ''})
        self.stop('no-history')

    def scenario_active(self, packing, session, store, expected):
        label = self.p['source_label']
        packing_arguments = {'packing_policy': packing} if packing else {}
        self.prepare_store(store, [
            (store + ':sync-items', ['sync', '--source', label], self.f['items.jsonl'], 'sync'),
            (store + ':declaration-put', ['supersession', 'declaration', 'put'],
             self.f['declaration.json'], 'put'),
            (store + ':activation-put', ['supersession', 'activation', 'put'],
             self.f['activation-initial.json'], 'put')])
        self.open_session(session, store)
        base = {'source': label, 'query': 'oldterm', 'policy': 'original', 'budget_bytes': 4096}
        omitted = self.call(session, session + ':query-omitted', 'mousa_query',
                            {**base, **packing_arguments}, mode='query')
        self.check_query(session, session + ':query-omitted', omitted, expected['omitted'])
        explicit = self.call(session, session + ':query-false', 'mousa_query',
                             {**base, **packing_arguments, 'supersession': False}, mode='query')
        self.check_query(session, session + ':query-false', explicit, expected['omitted'])
        self.expect(session + ':omitted-equals-false', self.selections[session + ':query-omitted'],
                    self.selections[session + ':query-false'])
        opted = self.call(session, session + ':query-opted', 'mousa_query',
                          {**base, **packing_arguments, 'supersession': True}, mode='query')
        self.check_query(session, session + ':query-opted', opted, expected['opted'])
        self.expect(session + ':opted-count-one', 1, opted['result']['supersession_excluded'])
        self.yes(session + ':opted-withholds-the-pinned-predecessor',
                 self.p['items']['predecessor']['segment_id']
                 not in {hit['segment_id'] for hit in opted['result']['evidence']})
        self.yes(session + ':default-packet-differs-from-opted',
                 self.results[session + ':query-omitted']['packet_id']
                 != opted['result']['packet_id'])
        budget_default = self.call(session, session + ':budget-default', 'mousa_query',
                                   {**base, **packing_arguments, 'query': 'predecessor',
                                    'budget_bytes': 28}, mode='query')
        self.check_query(session, session + ':budget-default', budget_default, expected['budget_default'])
        budget_opted = self.call(session, session + ':budget-opted', 'mousa_query',
                                 {**base, **packing_arguments, 'query': 'predecessor',
                                  'budget_bytes': 28, 'supersession': True}, mode='query')
        self.check_query(session, session + ':budget-opted', budget_opted, expected['budget_opted'])
        self.expect(session + ':withheld-consumes-no-budget', True,
                    budget_opted['result']['used_bytes'] == self.p['items']['duplicate']['bytes']
                    and budget_opted['result']['supersession_excluded'] == 1)
        if packing == 'exact-v1':
            self.expect(session + ':withheld-seeds-no-duplicate', 0,
                        budget_opted['result']['duplicate_omitted'])
            self.yes(session + ':byte-equal-survivor-released',
                     [hit['item'] for hit in budget_opted['result']['evidence']] == ['duplicate'])
        trail_id = self.results[session + ':query-opted']['trail_id']
        trail = self.call(session, session + ':trail-filtered', 'mousa_trail',
                          {'source': label, 'trail_id': trail_id}, mode='inspection')
        self.check_trail(session, session + ':trail-filtered', trail,
                         {'trail_id': trail_id, 'authorization': 'allow', 'reasons': ['allow'],
                          'historical': True, 'query': self.results[session + ':query-opted']})
        self.stop(session)
        self.open_session(session + '-restart', store, discovery=False)
        repeated = self.call(session + '-restart', session + '-restart:query-opted', 'mousa_query',
                             {**base, **packing_arguments, 'supersession': True}, mode='query')
        self.check_query(session + '-restart', session + '-restart:query-opted', repeated,
                         expected['opted'])
        self.expect(session + ':restart-stable-selection', self.selections[session + ':query-opted'],
                    self.selections[session + '-restart:query-opted'])
        self.yes(session + ':restart-fresh-trail',
                 self.results[session + ':query-opted']['trail_id']
                 != self.results[session + '-restart:query-opted']['trail_id'])
        self.yes(session + ':restart-fresh-decision',
                 self.results[session + ':query-opted']['decision_id']
                 != self.results[session + '-restart:query-opted']['decision_id'])
        self.stop(session + '-restart')

    def scenario_deactivated(self):
        label = self.p['source_label']
        self.prepare_store('deactivated', [
            ('deactivated:sync-items', ['sync', '--source', label], self.f['items.jsonl'], 'sync'),
            ('deactivated:declaration-put', ['supersession', 'declaration', 'put'],
             self.f['declaration.json'], 'put'),
            ('deactivated:activation-put', ['supersession', 'activation', 'put'],
             self.f['activation-initial.json'], 'put'),
            ('deactivated:deactivation-put', ['supersession', 'activation', 'put'],
             self.f['activation-deactivation.json'], 'put')])
        self.open_session('deactivated', 'deactivated')
        base = {'source': label, 'query': 'oldterm', 'policy': 'original', 'budget_bytes': 4096}
        expected = {'query': 'oldterm', 'budget': 4096, 'outcome': 'evidence', 'opted': False,
                    'packing': None, 'budget_omitted': 0, 'matched': 3, 'decision': 'allow',
                    'reasons': ['allow'], 'items': ['predecessor', 'duplicate', 'successor'],
                    'withheld': None, 'keys': self.p['result_keys']['query_default']}
        omitted = self.call('deactivated', 'deactivated:query-omitted', 'mousa_query', base,
                            mode='query')
        self.check_query('deactivated', 'deactivated:query-omitted', omitted, expected)
        opted = self.call('deactivated', 'deactivated:query-opted', 'mousa_query',
                          {**base, 'supersession': True}, mode='query')
        self.check_query('deactivated', 'deactivated:query-opted', opted,
                         {**expected, 'opted': True, 'packing': 'original',
                          'keys': self.p['result_keys']['query_opted']})
        self.expect('deactivated:count-zero', 0, opted['result']['supersession_excluded'])
        self.expect('deactivated:packet-equals-default',
                    self.results['deactivated:query-omitted']['packet_id'],
                    opted['result']['packet_id'])
        trail_id = self.results['deactivated:query-opted']['trail_id']
        trail = self.call('deactivated', 'deactivated:trail-filtered', 'mousa_trail',
                          {'source': label, 'trail_id': trail_id}, mode='inspection')
        self.check_trail('deactivated', 'deactivated:trail-filtered', trail,
                         {'trail_id': trail_id, 'authorization': 'allow', 'reasons': ['allow'],
                          'historical': True, 'query': self.results['deactivated:query-opted']})
        self.stop('deactivated')

    def scenario_successor_withdrawn(self):
        label = self.p['source_label']
        self.prepare_store('successor-withdrawn', [
            ('successor-withdrawn:sync-items', ['sync', '--source', label], self.f['items.jsonl'],
             'sync'),
            ('successor-withdrawn:declaration-put', ['supersession', 'declaration', 'put'],
             self.f['declaration.json'], 'put'),
            ('successor-withdrawn:activation-put', ['supersession', 'activation', 'put'],
             self.f['activation-initial.json'], 'put'),
            ('successor-withdrawn:delete-successor', ['sync', '--source', label],
             self.f['delete-successor.jsonl'], 'sync')])
        self.open_session('successor-withdrawn', 'successor-withdrawn')
        opted = self.call('successor-withdrawn', 'successor-withdrawn:query-opted', 'mousa_query',
                          {'source': label, 'query': 'oldterm', 'policy': 'original',
                           'budget_bytes': 4096, 'supersession': True}, mode='query')
        self.check_query('successor-withdrawn', 'successor-withdrawn:query-opted', opted, {
            'query': 'oldterm', 'budget': 4096, 'outcome': 'evidence', 'opted': True,
            'packing': 'original', 'budget_omitted': 0, 'matched': 2, 'decision': 'allow',
            'reasons': ['allow'], 'items': ['duplicate'], 'withheld': 'predecessor',
            'suppressed': 1, 'keys': self.p['result_keys']['query_opted']})
        self.expect('successor-withdrawn:no-replacement-evidence', ['duplicate'],
                    [hit['item'] for hit in opted['result']['evidence']])
        self.stop('successor-withdrawn')

    def scenario_denied(self):
        label = self.p['source_label']
        self.prepare_store('denied', [
            ('denied:sync-items', ['sync', '--source', label], self.f['items.jsonl'], 'sync'),
            ('denied:declaration-put', ['supersession', 'declaration', 'put'],
             self.f['declaration.json'], 'put'),
            ('denied:activation-put', ['supersession', 'activation', 'put'],
             self.f['activation-initial.json'], 'put'),
            ('denied:access-deny', ['access', '--source', label, 'deny'], b'', 'admin')])
        self.open_session('denied', 'denied')
        opted = self.call('denied', 'denied:query-opted', 'mousa_query',
                          {'source': label, 'query': 'oldterm', 'policy': 'original',
                           'budget_bytes': 4096, 'supersession': True}, mode='query')
        self.check_query('denied', 'denied:query-opted', opted, {
            'query': 'oldterm', 'budget': 4096, 'outcome': 'policy_excluded', 'opted': True,
            'packing': 'original', 'budget_omitted': 0, 'matched': 0, 'decision': 'deny',
            'reasons': ['policy_deny'], 'items': [], 'withheld': None, 'suppressed': 0,
            'keys': self.p['result_keys']['query_opted']})
        self.expect('denied:count-zero', 0, opted['result']['supersession_excluded'])
        self.expect('denied:used-bytes-zero', 0, opted['result']['used_bytes'])
        self.expect('denied:no-administrative-identity', False,
                    'activation' in json.dumps(opted['result'])
                    or 'declaration' in json.dumps(opted['result']))
        trail_id = self.results['denied:query-opted']['trail_id']
        trail = self.call('denied', 'denied:trail-denied', 'mousa_trail',
                          {'source': label, 'trail_id': trail_id}, mode='inspection')
        self.check_trail('denied', 'denied:trail-denied', trail,
                         {'trail_id': trail_id, 'authorization': 'deny',
                          'reasons': ['policy_deny'], 'historical': False})
        self.stop('denied')

    def scenario_damaged(self):
        label = self.p['source_label']
        self.prepare_store('damaged-events', [
            ('damaged-events:sync-items', ['sync', '--source', label], self.f['items.jsonl'],
             'sync'),
            ('damaged-events:declaration-put', ['supersession', 'declaration', 'put'],
             self.f['declaration.json'], 'put'),
            ('damaged-events:activation-put', ['supersession', 'activation', 'put'],
             self.f['activation-initial.json'], 'put')])
        self.open_session('damaged-events', 'damaged-events')
        base = {'source': label, 'query': 'oldterm', 'policy': 'original', 'budget_bytes': 4096}
        before = self.call('damaged-events', 'damaged-events:query-opted', 'mousa_query',
                           {**base, 'supersession': True}, mode='query')
        self.check_query('damaged-events', 'damaged-events:query-opted', before, {
            'query': 'oldterm', 'budget': 4096, 'outcome': 'evidence', 'opted': True,
            'packing': 'original', 'budget_omitted': 0, 'matched': 3, 'decision': 'allow',
            'reasons': ['allow'], 'items': ['duplicate', 'successor'],
            'withheld': 'predecessor', 'suppressed': 1,
            'keys': self.p['result_keys']['query_opted']})
        self.damage('damaged-events:damage-activation-events',
                    ['DELETE FROM supersession_activations'], 'damaged-events')
        damaged = self.call('damaged-events', 'damaged-events:query-opted-after-damage',
                            'mousa_query', {**base, 'supersession': True}, mode='reject')
        self.check_error('damaged-events', 'damaged-events:query-opted-after-damage', damaged,
                         {'code': 'integrity', 'source': label,
                          'message_contains': 'current activation event is missing'})
        default = self.call('damaged-events', 'damaged-events:query-default-after-damage',
                            'mousa_query', base, mode='query')
        self.check_query('damaged-events', 'damaged-events:query-default-after-damage', default, {
            'query': 'oldterm', 'budget': 4096, 'outcome': 'evidence', 'opted': False,
            'packing': None, 'budget_omitted': 0, 'matched': 3, 'decision': 'allow',
            'reasons': ['allow'], 'items': ['predecessor', 'duplicate', 'successor'],
            'withheld': None, 'keys': self.p['result_keys']['query_default']})
        self.stop('damaged-events')

    def scenario_malformed(self):
        label = self.p['source_label']
        self.prepare_store('malformed', [
            ('malformed:sync-items', ['sync', '--source', label], self.f['items.jsonl'], 'sync')])
        self.open_session('malformed', 'malformed')
        frame = ('{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"mousa_query",'
                 '"arguments":{"source":"%s"}}} trailing' % label).encode()
        record = self.protocol_call('malformed', 'malformed:invalid-frame', None, raw=frame,
                                    mode='reject')
        self.expect('malformed:no-response', '', record['response']['text'])
        self.stop('malformed', expected_exit=1,
                  stderr_text='invalid trailing data at the end of stream')

    def run(self):
        self.scenario_fresh_store()
        self.scenario_no_history()
        self.scenario_active(None, 'active-original', 'active-original', {
            'omitted': {'query': 'oldterm', 'budget': 4096, 'outcome': 'evidence', 'opted': False,
                        'packing': None, 'budget_omitted': 0, 'matched': 3, 'decision': 'allow',
                        'reasons': ['allow'],
                        'items': ['predecessor', 'duplicate', 'successor'], 'withheld': None,
                        'keys': self.p['result_keys']['query_default']},
            'opted': {'query': 'oldterm', 'budget': 4096, 'outcome': 'evidence', 'opted': True,
                      'packing': 'original', 'budget_omitted': 0, 'matched': 3,
                      'decision': 'allow', 'reasons': ['allow'],
                      'items': ['duplicate', 'successor'], 'withheld': 'predecessor',
                      'suppressed': 1, 'keys': self.p['result_keys']['query_opted']},
            'budget_default': {'query': 'predecessor', 'budget': 28, 'outcome': 'evidence',
                               'opted': False, 'packing': None, 'budget_omitted': 1,
                               'matched': 2, 'decision': 'allow', 'reasons': ['allow'],
                               'items': ['predecessor'], 'withheld': None,
                               'keys': self.p['result_keys']['query_default']},
            'budget_opted': {'query': 'predecessor', 'budget': 28, 'outcome': 'evidence',
                             'opted': True, 'packing': 'original', 'budget_omitted': 0,
                             'matched': 2, 'decision': 'allow', 'reasons': ['allow'],
                             'items': ['duplicate'], 'withheld': 'predecessor',
                             'suppressed': 1, 'keys': self.p['result_keys']['query_opted']}})
        self.scenario_active('exact-v1', 'active-exact-v1', 'active-exact-v1', {
            'omitted': {'query': 'oldterm', 'budget': 4096, 'outcome': 'evidence', 'opted': False,
                        'packing': 'exact-v1', 'duplicate_present': True, 'duplicate_omitted': 1,
                        'budget_omitted': 0, 'matched': 3, 'decision': 'allow',
                        'reasons': ['allow'], 'items': ['predecessor', 'successor'],
                        'withheld': None, 'keys': self.p['result_keys']['query_exact_v1']},
            'opted': {'query': 'oldterm', 'budget': 4096, 'outcome': 'evidence', 'opted': True,
                      'packing': 'exact-v1', 'duplicate_present': True, 'duplicate_omitted': 0,
                      'budget_omitted': 0, 'matched': 3, 'decision': 'allow',
                      'reasons': ['allow'], 'items': ['duplicate', 'successor'],
                      'withheld': 'predecessor', 'suppressed': 1,
                      'keys': self.p['result_keys']['query_opted_exact_v1']},
            'budget_default': {'query': 'predecessor', 'budget': 28, 'outcome': 'evidence',
                               'opted': False, 'packing': 'exact-v1', 'duplicate_present': True,
                               'duplicate_omitted': 1, 'budget_omitted': 0, 'matched': 2,
                               'decision': 'allow', 'reasons': ['allow'],
                               'items': ['predecessor'], 'withheld': None,
                               'keys': self.p['result_keys']['query_exact_v1']},
            'budget_opted': {'query': 'predecessor', 'budget': 28, 'outcome': 'evidence',
                             'opted': True, 'packing': 'exact-v1', 'duplicate_present': True,
                             'duplicate_omitted': 0, 'budget_omitted': 0, 'matched': 2,
                             'decision': 'allow', 'reasons': ['allow'], 'items': ['duplicate'],
                             'withheld': 'predecessor', 'suppressed': 1,
                             'keys': self.p['result_keys']['query_opted_exact_v1']}})
        self.scenario_deactivated()
        self.scenario_successor_withdrawn()
        self.scenario_denied()
        self.scenario_damaged()
        self.scenario_malformed()
        if self.replay is not None and self.index != len(self.replay):
            raise ValueError('unexpected extra step')
        if len({record['id'] for record in self.assertions}) != len(self.assertions):
            raise ValueError('duplicate assertion IDs')
        return self


def make_manifest(directory):
    files = {}
    for path in sorted(directory.rglob('*')):
        if path.is_file() and path.name != 'manifest.json':
            data = path.read_bytes()
            files[str(path.relative_to(directory))] = {'bytes': len(data), 'sha256': sha(data)}
    save(directory / 'manifest.json', {'schema': MANIFEST_SCHEMA, 'files': files})


def verify(directory, require_pass=True):
    manifest = json.loads((directory / 'manifest.json').read_bytes())['files']
    actual = {str(path.relative_to(directory)) for path in directory.rglob('*')
              if path.is_file() and path != directory / 'manifest.json'}
    if set(manifest) != actual:
        raise ValueError('archive membership differs')
    observed = json.loads((directory / 'observed.json').read_bytes())
    if observed['schema'] != OBSERVED_SCHEMA:
        raise ValueError('unknown observation schema')
    required = {'run.py', 'protocol.json', 'observed.json', 'assertions.json', 'product-pin.json'}
    if observed.get('expectations_sha256') is not None:
        required.add('expectations.json')
    missing = required - actual
    if missing:
        raise ValueError('missing required archive member: ' + ', '.join(sorted(missing)))
    for name, entry in manifest.items():
        data = (directory / name).read_bytes()
        if entry != {'bytes': len(data), 'sha256': sha(data)}:
            raise ValueError('archive digest differs: ' + name)
    for name in ('run.py', 'protocol.json'):
        if (directory / name).read_bytes() != (ROOT / name).read_bytes():
            raise ValueError('capture does not match this committed runner/protocol: ' + name)
    protocol, frozen = load_protocol(directory)
    if (observed['runner_sha256'] != sha((ROOT / 'run.py').read_bytes())
            or observed['protocol_sha256'] != sha((ROOT / 'protocol.json').read_bytes())):
        raise ValueError('observation provenance hashes differ')
    pin = json.loads((directory / 'product-pin.json').read_bytes())
    validate_pin(pin)
    if pin != observed['product_pin']:
        raise ValueError('pin receipt differs')
    provenance = observed['provenance_commands']
    expected_argv = [['git', '-C', root, *command] for root in ('<product>', '<companion>')
                     for command in (['rev-parse', 'HEAD'], ['rev-parse', 'HEAD^{tree}'],
                                     ['status', '--porcelain'])]
    if [command['argv'] for command in provenance] != expected_argv or any(
            command['exit'] != 0 for command in provenance):
        raise ValueError('omitted or changed provenance command')
    expected_stdout = [pin['public_head'], pin['public_tree'], '',
                       observed['companion_execution']['head'],
                       observed['companion_execution']['tree'], '']
    if [command['stdout']['text'].strip() for command in provenance] != expected_stdout:
        raise ValueError('source/companion execution pin differs')
    for record in observed['steps'] + observed['provenance_commands']:
        for key in ('stdin', 'stdout', 'stderr', 'request', 'response'):
            if key in record:
                if stream(base64.b64decode(record[key]['base64'], validate=True)) != record[key]:
                    raise ValueError('damaged wire stream in ' + record['name'])
    regenerated = Session(protocol, frozen, replay=observed['steps']).run()
    expected_path = directory / 'expectations.json'
    if observed.get('expectations_sha256') is not None:
        expected = json.loads(expected_path.read_bytes())
        if (sha(encoded(expected)) != observed['expectations_sha256']
                or expected['product_pin'] != pin
                or expected['protocol_sha256'] != observed['protocol_sha256']):
            raise ValueError('wrong frozen expectations')
        regenerated.expect('frozen-pilot-selections', expected['selections'],
                           regenerated.selections)
    elif expected_path.exists():
        raise ValueError('unexpected frozen expectations')
    assertions = json.loads((directory / 'assertions.json').read_bytes())
    if assertions != regenerated.assertions:
        raise ValueError('omitted or tampered assertion: '
                         + ', '.join(assertion_differences(assertions, regenerated.assertions)))
    if observed['selections'] != regenerated.selections:
        raise ValueError('omitted or tampered selection')
    if require_pass:
        failed = [record['id'] for record in assertions if not record['passed']]
        if failed:
            raise ValueError('false assertion: ' + ', '.join(failed))
    return observed, regenerated


def assertion_differences(recorded, regenerated):
    """Name the exact assertions a mutated archive trips."""
    before = {record['id']: record for record in recorded}
    after = {record['id']: record for record in regenerated}
    differences = []
    for ident in sorted(set(before) | set(after)):
        if ident not in before:
            differences.append('unrecorded:' + ident)
        elif ident not in after:
            differences.append('omitted:' + ident)
        elif before[ident] != after[ident]:
            differences.append('changed:' + ident)
    return differences


def provenance_command(argv):
    result = subprocess.run(argv, capture_output=True)
    return {'argv': argv, 'stdin': stream(b''), 'exit': result.returncode,
            'stdout': stream(result.stdout), 'stderr': stream(result.stderr)}


def capture(args, expectations):
    protocol, frozen = load_protocol()
    pin = json.loads(args.pin.read_bytes())
    validate_pin(pin)
    binary = args.binary.resolve()
    if sha(binary.read_bytes()) != pin['executable_sha256']:
        raise ValueError('executable differs from the published build receipt')
    commands = [provenance_command(['git', '-C', str(args.source), *command]) for command in
                (['rev-parse', 'HEAD'], ['rev-parse', 'HEAD^{tree}'], ['status', '--porcelain'])]
    if any(command['exit'] != 0 for command in commands) or [
            command['stdout']['text'].strip() for command in commands] != [
            pin['public_head'], pin['public_tree'], '']:
        raise ValueError('source checkout is not clean at the published product pin')
    companion_commands = [provenance_command(['git', '-C', str(ROOT.parent), *command])
                          for command in (['rev-parse', 'HEAD'], ['rev-parse', 'HEAD^{tree}'],
                                          ['status', '--porcelain'])]
    if any(command['exit'] != 0 for command in companion_commands) or \
            companion_commands[-1]['stdout']['text'].strip():
        raise ValueError('companion execution tree must be committed and clean')
    companion = {'head': companion_commands[0]['stdout']['text'].strip(),
                 'tree': companion_commands[1]['stdout']['text'].strip()}
    for command in commands:
        command['argv'][2] = '<product>'
    for command in companion_commands:
        command['argv'][2] = '<companion>'
    commands.extend(companion_commands)
    if args.output.exists():
        raise ValueError('output already exists')
    args.output.mkdir(parents=True)
    for name in ('run.py', 'protocol.json'):
        shutil.copyfile(ROOT / name, args.output / name)
    shutil.copytree(ROOT / 'inputs', args.output / 'inputs')
    save(args.output / 'product-pin.json', pin)
    with tempfile.TemporaryDirectory(prefix='mousa-mcp-capture-') as temporary:
        work = Path(temporary)
        session = Session(protocol, frozen, binary, work, forbidden=args.forbidden_write)
        try:
            session.run()
        except (ValueError, KeyError, TypeError, OSError, sqlite3.Error, TimeoutError) as error:
            session.expect('runner-completed-schedule', 'complete',
                           type(error).__name__ + ': ' + str(error))
    if expectations is not None:
        save(args.output / 'expectations.json', expectations)
        session.expect('frozen-pilot-selections', expectations['selections'], session.selections)
    observed = {'schema': OBSERVED_SCHEMA,
                'captured_at_utc': datetime.now(timezone.utc).isoformat(),
                'runner_sha256': sha((ROOT / 'run.py').read_bytes()),
                'protocol_sha256': sha((ROOT / 'protocol.json').read_bytes()),
                'product_pin': pin, 'provenance_commands': commands, 'steps': session.steps,
                'sessions': [{'session': entry['session'], 'store': entry['store'],
                              'start_argv': entry['start']['argv'],
                              'start_fingerprint_before': entry['start']['fingerprint_before'],
                              'startup_fingerprint_after': entry['startup']['fingerprint_after'],
                              'exit': entry.get('stop', {}).get('exit'),
                              'stderr': entry.get('stop', {}).get('stderr')}
                             for entry in session.sessions],
                'companion_execution': companion, 'selections': session.selections,
                'python_version': sys.version, 'sqlite_version': sqlite3.sqlite_version,
                'expectations_sha256': sha(encoded(expectations)) if expectations else None}
    save(args.output / 'observed.json', observed)
    save(args.output / 'assertions.json', session.assertions)
    make_manifest(args.output)
    return 0 if all(record['passed'] for record in session.assertions) else 1


def discovery(args):
    """Capture one executable's tool definitions. Baseline provenance, not an observation.

    This mode reads no protocol: a baseline binary answers with the pre-query tool
    definitions, and the protocol is authored afterwards from that comparison.
    """
    items = (ROOT / 'inputs' / 'items.jsonl').read_bytes()
    with tempfile.TemporaryDirectory(prefix='mousa-mcp-discovery-') as temporary:
        work = Path(temporary)
        store = work / 'discovery.sqlite'
        sync = subprocess.run([str(args.binary), '-store', str(store), 'sync', '--source',
                               args.label], input=items, capture_output=True)
        server = Server(args.binary, store, args.label, CALLER, work / 'stderr.log')
        initialize_request, initialize_response = server.request('initialize', {
            'protocolVersion': args.protocol_version, 'capabilities': {},
            'clientInfo': {'name': CLIENT_NAME, 'version': '1'}})
        initialized = server.notify('notifications/initialized')
        list_request, list_response = server.request('tools/list', {})
        exit_code, stderr = server.stop()
    receipt = {'schema': BASELINE_SCHEMA,
               'captured_at_utc': datetime.now(timezone.utc).isoformat(),
               'executable_sha256': sha(Path(args.binary).read_bytes()),
               'label': args.label, 'protocol_version': args.protocol_version,
               'client_name': CLIENT_NAME,
               'argv': ['<binary>', '-store', '<work>/discovery.sqlite', 'mcp', '--caller',
                        CALLER, '--source', args.label],
               'sync': {'argv': ['<binary>', '-store', '<work>/discovery.sqlite', 'sync',
                                 '--source', args.label],
                        'stdin': stream(items), 'exit': sync.returncode,
                        'stdout': stream(sync.stdout), 'stderr': stream(sync.stderr)},
               'exit': exit_code, 'stderr': stream(stderr),
               'initialize_request': stream(initialize_request),
               'initialize_response': stream(initialize_response),
               'initialized_notification': stream(initialized),
               'tools_list_request': stream(list_request), 'tools_list_response': stream(list_response),
               'tools': json.loads(list_response)['result']['tools']}
    save(args.output, receipt)
    print('Captured', len(receipt['tools']), 'tool definitions from', args.binary)
    return 0


def negative_controls(args):
    verify(args.capture)
    if args.output.exists():
        raise ValueError('negative-control output exists')
    args.output.mkdir(parents=True)
    results = []
    protocol, frozen = load_protocol()
    false_session = Session(protocol, frozen)
    false_session.yes('negative-actual-false', False)
    actual_false = false_session.assertions[0]
    results.append({'control': 'actual-false-condition', 'assertion': actual_false,
                    'reason': 'the assertion API recorded observed False with passed False',
                    'rejected': actual_false['observed'] is False
                    and actual_false['passed'] is False})
    kinds = ('damaged-input', 'wrong-count-expectation', 'wrong-default-property-set',
             'false-assertion', 'omitted-assertion', 'undeclared-response-field',
             'forbidden-write-fingerprint', 'fabricated-success-after-damage', 'failed-build',
             'damaged-build-stream')
    for kind in kinds:
        directory = args.output / kind
        shutil.copytree(args.capture, directory)
        observation_path = directory / 'observed.json'
        observations = json.loads(observation_path.read_bytes())
        if kind == 'damaged-input':
            path = directory / 'inputs' / 'items.jsonl'
            path.write_bytes(path.read_bytes() + b'\n')
        elif kind in ('wrong-count-expectation', 'wrong-default-property-set', 'false-assertion',
                      'omitted-assertion'):
            path = directory / 'assertions.json'
            assertions = json.loads(path.read_bytes())
            if kind == 'wrong-count-expectation':
                record = next(record for record in assertions
                              if record['id'].endswith(':count') and record['expected'] == 1)
                record['expected'] = 999
            elif kind == 'wrong-default-property-set':
                record = next(record for record in assertions if record['id'].endswith(':result-keys')
                              and record['expected'] == sorted(protocol['result_keys']['query_default']))
                record['expected'] = record['expected'][:-1]
            elif kind == 'false-assertion':
                record = next(record for record in assertions
                              if record['expected'] is True and record['observed'] is True)
                record['observed'] = False
                record['passed'] = True
            else:
                assertions.pop()
            save(path, assertions)
        elif kind == 'undeclared-response-field':
            step = next(step for step in observations['steps'] if step['kind'] == 'call'
                        and step['mode'] == 'query'
                        and b'"evidence"' in base64.b64decode(step['response']['base64']))
            line = json.loads(base64.b64decode(step['response']['base64']).decode())
            line['result']['structuredContent']['result']['undeclared_probe'] = 1
            line['result']['content'][0]['text'] = json.dumps(
                line['result']['structuredContent'], separators=(',', ':'))
            step['response'] = stream(json.dumps(line, separators=(',', ':')).encode() + b'\n')
            save(observation_path, observations)
        elif kind == 'forbidden-write-fingerprint':
            step = next(step for step in observations['steps'] if step['mode'] == 'read')
            step['fingerprint_after']['tables']['forbidden_control'] = {
                'rows': 1, 'sha256': sha(b'forbidden')}
            save(observation_path, observations)
        elif kind == 'fabricated-success-after-damage':
            steps = observations['steps']
            failed = next(step for step in steps
                          if step['name'].endswith('query-opted-after-damage'))
            success = next(step for step in steps if step['name'].endswith(':query-opted')
                           and b'"error"' not in base64.b64decode(step['response']['base64']))
            failed['response'] = success['response']
            save(observation_path, observations)
        else:
            pin_path = directory / 'product-pin.json'
            pin = json.loads(pin_path.read_bytes())
            if kind == 'failed-build':
                pin['build_receipt']['exit'] = 1
            else:
                pin['build_receipt']['stdout']['sha256'] = 'f' * 64
            save(pin_path, pin)
            observations['product_pin'] = pin
            save(observation_path, observations)
        # Recompute the manifest so verification must detect the semantic fault rather than
        # relying only on a stale file checksum.
        make_manifest(directory)
        try:
            verify(directory)
        except (ValueError, KeyError, TypeError, IndexError, OSError,
                sqlite3.Error) as error:
            results.append({'control': kind, 'rejected': True,
                            'reason': type(error).__name__ + ': ' + str(error)})
        else:
            results.append({'control': kind, 'rejected': False})
    save(args.output / 'negative-controls.json', results)
    if not all(row['rejected'] for row in results):
        raise ValueError('negative control was accepted')
    return 0


def deep_selections(directory):
    return json.loads((directory / 'observed.json').read_bytes())['selections']


def archive(directory, archive_path):
    """Archive one directory under its archive stem, so extraction is positional."""
    inner = archive_path.name[:-len('.tar.gz')]
    with tarfile.open(archive_path, 'w:gz') as archive:
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                archive.add(path, arcname=inner + '/' + str(path.relative_to(directory)),
                            recursive=False)
    members = {}
    with tarfile.open(archive_path) as archive:
        for member in archive:
            inner = PurePosixPath(member.name)
            if not member.isfile() or inner.is_absolute() or '..' in inner.parts:
                raise ValueError('invalid archive member: ' + member.name)
            data = archive.extractfile(member).read()
            members[member.name] = {'bytes': len(data), 'sha256': sha(data)}
    return members


def package(args):
    if args.output.exists():
        raise ValueError('package output exists')
    args.output.mkdir(parents=True)
    members = {}
    collections = {}
    for name, directory in (('pilot', args.pilot), ('capture', args.capture),
                            ('fresh-reproduction', args.fresh),
                            ('forbidden-write', args.forbidden)):
        archive_path = args.output / (name + '.tar.gz')
        members[archive_path.name] = archive(directory, archive_path)
        observed = json.loads((directory / 'observed.json').read_bytes())
        assertions = json.loads((directory / 'assertions.json').read_bytes())
        collections[name] = {
            'captured_at_utc': observed['captured_at_utc'],
            'companion_execution': observed['companion_execution'],
            'runner_sha256': observed['runner_sha256'],
            'protocol_sha256': observed['protocol_sha256'],
            'expectations_sha256': observed['expectations_sha256'],
            'assertions': len(assertions),
            'failed_assertions': [record['id'] for record in assertions if not record['passed']],
            'sessions': [(entry['session'], entry['exit']) for entry in observed['sessions']]}
    for directory in sorted(path for path in args.negatives.iterdir() if path.is_dir()):
        archive_path = args.output / ('negative-' + directory.name + '.tar.gz')
        members[archive_path.name] = archive(directory, archive_path)
    shutil.copyfile(args.negatives / 'negative-controls.json',
                    args.output / 'negative-controls.json')
    shutil.copyfile(args.commands, args.output / 'commands.json')
    for name in ('run.py', 'protocol.json'):
        shutil.copyfile(ROOT / name, args.output / name)
    for name, source in (('expectations.json', args.expectations),
                         ('product-pin.json', args.pin),
                         ('preparation-verification.json', args.preparation),
                         ('baseline-discovery.json', args.baseline)):
        shutil.copyfile(source, args.output / name)
    save(args.output / 'archive-members.json',
         {'schema': 'mousa.archive_members.v1', 'archives': members})
    capture_selections = deep_selections(args.capture)
    fresh_selections = deep_selections(args.fresh)
    save(args.output / 'summary.json', {'schema': 'mousa.mcp_query_supersession_summary.v1',
                                        'collections': collections,
                                        'capture_and_reproduction_share_stable_selections':
                                            capture_selections == fresh_selections,
                                        'stable_selection_cases': len(capture_selections)})
    make_manifest(args.output)
    print('Packaged', len(members), 'archives into', args.output)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    for mode in ('pilot', 'capture', 'forbidden-write'):
        sub = modes.add_parser(mode)
        sub.add_argument('--binary', type=Path, required=True)
        sub.add_argument('--source', type=Path, required=True)
        sub.add_argument('--pin', type=Path, required=True)
        sub.add_argument('--output', type=Path, required=True)
        sub.add_argument('--expectations', type=Path, required=mode == 'capture')
        sub.set_defaults(forbidden_write=mode == 'forbidden-write')
    sub = modes.add_parser('verify')
    sub.add_argument('directory', type=Path)
    sub = modes.add_parser('manifest')
    sub.add_argument('directory', type=Path)
    sub = modes.add_parser('freeze')
    sub.add_argument('pilot', type=Path)
    sub.add_argument('--output', type=Path, required=True)
    sub = modes.add_parser('negative-controls')
    sub.add_argument('capture', type=Path)
    sub.add_argument('--output', type=Path, required=True)
    sub = modes.add_parser('discovery')
    sub.add_argument('--binary', type=Path, required=True)
    sub.add_argument('--label', required=True)
    sub.add_argument('--protocol-version', default=PROTOCOL_VERSION)
    sub.add_argument('--output', type=Path, required=True)
    sub = modes.add_parser('package')
    sub.add_argument('--output', type=Path, required=True)
    sub.add_argument('--pilot', type=Path, required=True)
    sub.add_argument('--capture', type=Path, required=True)
    sub.add_argument('--fresh', type=Path, required=True)
    sub.add_argument('--forbidden', type=Path, required=True)
    sub.add_argument('--negatives', type=Path, required=True)
    sub.add_argument('--expectations', type=Path, required=True)
    sub.add_argument('--pin', type=Path, required=True)
    sub.add_argument('--preparation', type=Path, required=True)
    sub.add_argument('--baseline', type=Path, required=True)
    sub.add_argument('--commands', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.mode in ('pilot', 'capture', 'forbidden-write'):
            expectations = json.loads(args.expectations.read_bytes()) if args.expectations else None
            if expectations is not None and (
                    expectations['protocol_sha256'] != sha((ROOT / 'protocol.json').read_bytes())):
                raise ValueError('frozen pilot expectations do not match this protocol')
            return capture(args, expectations)
        if args.mode == 'verify':
            verify(args.directory)
            print('Verified complete MCP assertions, wire bytes and archive members')
        elif args.mode == 'manifest':
            make_manifest(args.directory)
        elif args.mode == 'freeze':
            observed, session = verify(args.pilot)
            if args.output.exists():
                raise ValueError('expectation output already exists')
            save(args.output, {'schema': EXPECTATIONS_SCHEMA,
                               'product_pin': observed['product_pin'],
                               'protocol_sha256': observed['protocol_sha256'],
                               'pilot_observed_sha256': sha((args.pilot / 'observed.json').read_bytes()),
                               'selections': session.selections})
        elif args.mode == 'negative-controls':
            return negative_controls(args)
        elif args.mode == 'discovery':
            return discovery(args)
        else:
            return package(args)
        return 0
    except (ValueError, KeyError, OSError, sqlite3.Error, TimeoutError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
