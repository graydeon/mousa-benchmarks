#!/usr/bin/env python3
"""Standalone stdlib MCP historical inspection capture and offline replay.

JSON/schema primitives derive from the accepted query runner at companion
2f419c47be796f6e647997e120fe5a364351e9ce. No product internals are imported.
"""
import argparse
import base64
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import select
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent

def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()


def save(path, value):
    path.write_bytes(encoded(value))


def stream(data):
    return {'bytes': len(data), 'sha256': sha(data), 'base64': base64.b64encode(data).decode(),
            'text': data.decode('utf-8', 'replace')}


def canonical(value):
    """Canonical JSON text for one value: sorted object keys, no whitespace."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def same_json(left, right):
    """JSON equality that keeps types distinct at every depth.

    Python's `==` treats `True` and `1` (and `1` and `1.0`) as equal, so a nested boolean
    rewritten as a number, or an integer rewritten as a float, would compare equal and the
    difference would disappear from an assertion. Comparing canonical encodings keeps
    boolean, number, string, null, array and object distinct at every depth; sorting object
    keys keeps property order irrelevant, the way the JSON definitions compared here are
    defined.
    """
    return canonical(left) == canonical(right)


def strict_json(text):
    """Parse one JSON text, reporting every object that repeats a key at any depth.

    `json.loads` keeps the last of two identical object keys without reporting it, so a
    duplicated tool name or argument would disappear before any comparison. The object hook
    runs for every object the frame contains, so a repeated key inside `params.arguments` is
    reported exactly like one at the frame's top level.
    """
    repeated = []

    def hook(pairs):
        seen = set()
        for name, _ in pairs:
            if name in seen:
                repeated.append(name)
            seen.add(name)
        return dict(pairs)

    try:
        return json.loads(text, object_pairs_hook=hook), repeated
    except ValueError:
        return None, repeated


def sql_name(name):
    return '"' + name.replace('"', '""') + '"'


def sql_value(value):
    if isinstance(value, bytes):
        return ['blob', value.hex()]
    return [type(value).__name__, value]



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
    items and oneOf (exactly one matching branch). Not implemented: formats, $ref/$defs,
    allOf/anyOf/not,
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
    if 'const' in schema and not same_json(value, schema['const']):
        problems.append('%s: expected const %r' % (path, schema['const']))
    if 'enum' in schema and not any(same_json(value, option) for option in schema['enum']):
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
    if branches:
        matched = sum(1 for branch in branches if not schema_violations(branch, value, path))
        if matched != 1:
            problems.append('%s: oneOf requires exactly one matching branch, %d matched'
                            % (path, matched))
    return problems


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


def snapshot(path):
    if not path.exists():
        return None
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.execute('BEGIN')
        schema = list(db.execute('SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name'))
        tables = {}
        for kind, name, _, _ in schema:
            if kind == 'table':
                cursor = db.execute('SELECT * FROM ' + sql_name(name))
                rows = [[sql_value(v) for v in row] for row in cursor]
                tables[name] = {'columns': [c[0] for c in cursor.description],
                                'rows': sorted(rows, key=canonical)}
        return {'schema': schema, 'tables': tables,
                'user_version': db.execute('PRAGMA user_version').fetchone()[0]}


def table_rows(state, name):
    table = state['tables'][name]
    return [dict(zip(table['columns'], [v for _, v in row])) for row in table['rows']]


def stored_trail(state, identifier):
    return next(json.loads(bytes.fromhex(row['record_json']))
                for row in table_rows(state, 'source_trails') if row['id'] == identifier)


def resolve(value, results):
    if isinstance(value, dict):
        if set(value) == {'ref'}:
            step, key = value['ref'].split('.')
            return results[step][key]
        return {key: resolve(item, results) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item, results) for item in value]
    return value


def identity_errors(value, path='$'):
    errors = []
    if isinstance(value, dict):
        for key, child in value.items():
            here = path + '.' + key
            if key in {'id', 'request_id', 'decision_id', 'authorization_decision_id', 'trail_id',
                       'packet_id', 'segment_id', 'content_sha256', 'activation_id', 'declaration_id',
                       'predecessor_representation_id', 'successor_representation_id'}:
                nullable = key in {'activation_id', 'declaration_id'}
                if not (nullable and child is None) and not (
                        isinstance(child, str) and re.fullmatch('[0-9a-f]{64}', child)):
                    errors.append(here)
            errors.extend(identity_errors(child, here))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(identity_errors(child, path + '[' + str(index) + ']'))
    return errors


class Capture:
    def __init__(self, protocol, binary=None, work=None, records=None, forbidden=False):
        self.protocol, self.binary, self.work = protocol, binary, work
        self.replay, self.forbidden = records, forbidden
        self.records, self.assertions, self.results, self.selections = [], [], {}, {}
        self.servers, self.schemas, self.last_state = {}, {}, {}
        self.histories, self.refusals = {}, {}

    def expect(self, name, expected, actual):
        def summary(value):
            data = encoded(value)
            return value if len(data) <= 4096 else {'canonical_bytes': len(data), 'sha256': sha(data)}
        self.assertions.append({'id': name, 'expected': summary(expected), 'observed': summary(actual),
                                'passed': same_json(expected, actual)})

    def produce(self, spec, index):
        path = self.work / (spec['store'] + '.sqlite')
        record = {'schedule': spec, 'before': snapshot(path)}
        kind = spec['kind']
        if kind == 'native':
            argv = [str(self.binary), '-store', str(path), *spec['argv']]
            payload = (ROOT / spec['input']).read_bytes() if 'input' in spec else b''
            argv = [str(ROOT / arg[1:]) if arg.startswith('@') else arg for arg in argv]
            result = subprocess.run(argv, input=payload, capture_output=True, timeout=60)
            record.update(argv=['<binary>', '-store', '<store>', *spec['argv']],
                          stdin=stream(payload), stdout=stream(result.stdout),
                          stderr=stream(result.stderr), exit=result.returncode)
        elif kind == 'damage':
            with sqlite3.connect(path) as db:
                db.execute('PRAGMA foreign_keys=OFF')
                for sql in spec['sql']:
                    db.execute(sql)
            record['sql'] = spec['sql']
        elif kind == 'start':
            errfile = open(self.work / (spec['name'] + '.stderr'), 'wb')
            argv = [str(self.binary), '-store', str(path), 'mcp', '--caller', 'cli',
                    '--source', self.protocol['source'], '--source', 'peer',
                    '--ingest-source', self.protocol['source']]
            process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=errfile)
            self.servers[spec['store']] = (process, LineReader(process.stdout.fileno()), errfile)
            record['argv'] = ['<binary>', '-store', '<store>', *argv[3:]]
        elif kind == 'stop':
            process, _, errfile = self.servers.pop(spec['store'])
            process.stdin.close()
            record['exit'] = process.wait(timeout=20)
            record['stdout'] = stream(process.stdout.read())
            errfile.close()
            record['stderr'] = stream(Path(errfile.name).read_bytes())
        else:
            process, reader, _ = self.servers[spec['store']]
            if kind == 'raw':
                payload = spec['raw'].encode()
            else:
                frame = {'jsonrpc': '2.0', 'method': spec['method']}
                if kind != 'notify':
                    frame['id'] = index
                if 'params' in spec:
                    frame['params'] = spec['params']
                payload = encoded(frame)
            process.stdin.write(payload)
            process.stdin.flush()
            record['request'] = stream(payload)
            notifications = []
            response = b''
            if kind != 'notify':
                while True:
                    line = reader.readline(40)
                    if not line:
                        break
                    parsed = json.loads(line)
                    if 'id' in parsed:
                        response = line + b'\n'
                        break
                    notifications.append(stream(line + b'\n'))
            record['notifications'] = notifications
            record['response'] = stream(response)
            if self.forbidden and spec.get('check') == 'history':
                with sqlite3.connect(path) as db:
                    db.execute("CREATE TABLE forbidden_inspection_write (value TEXT)")
                    db.execute("INSERT INTO forbidden_inspection_write VALUES ('forbidden')")
                self.forbidden = False
        record['after'] = snapshot(path)
        return record

    def audit(self, name, before, after, result, source_id=None):
        identifier = result.get('authorization_decision_id')
        self.expect(name + ':authorization-id', True,
                    isinstance(identifier, str) and re.fullmatch('[0-9a-f]{64}', identifier) is not None)
        decisions = table_rows(after, 'policy_decisions')
        fresh = [row for row in decisions if row['id'] == identifier]
        self.expect(name + ':fresh-decision-count', 1, len(fresh))
        filtered = copy.deepcopy(after)
        for table, column in [('policy_decisions', 'id'), ('policy_decision_inputs', 'decision_id')]:
            projection = filtered['tables'][table]
            idx = projection['columns'].index(column)
            projection['rows'] = [row for row in projection['rows'] if row[idx][1] != identifier]
        self.expect(name + ':only-bound-authorization-write', before, filtered)
        if len(fresh) != 1:
            return
        row = fresh[0]
        decision = json.loads(bytes.fromhex(row['record_json']))
        self.expect(name + ':decision-identity', identifier, decision['id'])
        self.expect(name + ':decision-source', source_id or self.protocol['source_id'], row['source_id'])
        self.expect(name + ':decision-request-source', row['source_id'], decision['request']['source_id'])
        self.expect(name + ':decision-outcome', result['authorization_outcome'], row['outcome'])
        self.expect(name + ':canonical-outcome', row['outcome'], decision['outcome'])
        self.expect(name + ':decision-reasons', result['authorization_reasons'], decision['reason_codes'])
        expected = [{'decision_id': identifier, 'ordinal': i, 'layer': item['layer'],
                     'activation_id': item['policy_activation_id'], 'binding_id': item['policy_binding_id'],
                     'definition_id': item['policy_definition_id'], 'result': item['result']}
                    for i, item in enumerate(decision['policy_inputs'])]
        actual = [r for r in table_rows(after, 'policy_decision_inputs') if r['decision_id'] == identifier]
        self.expect(name + ':necessary-input-children', sorted(expected, key=canonical),
                    sorted(actual, key=canonical))

    def query_writes(self, name, before, after, result):
        trail_id = result['trail_id']
        trail = stored_trail(after, trail_id)
        for key, field in [('id', 'trail_id'), ('decision_id', 'decision_id'),
                           ('request_id', 'request_id'), ('packet_id', 'packet_id')]:
            self.expect(name + ':query-stored-' + key, result[field], trail[key])
        candidates = [row for row in table_rows(after, 'source_trail_candidates')
                      if row['trail_id'] == trail_id]
        expected = [{'trail_id': trail_id, 'ordinal': i, 'segment_id': row['segment_id'],
                     'final_rank': row['final_rank'], 'disposition': row['disposition'],
                     'selected': int(row['selected'])} for i, row in enumerate(trail['candidates'])]
        self.expect(name + ':query-candidate-projection', sorted(expected, key=canonical),
                    sorted(candidates, key=canonical))
        filtered = copy.deepcopy(after)
        for table, column in [('source_trails', 'id'), ('source_trail_candidates', 'trail_id')]:
            projection = filtered['tables'][table]
            idx = projection['columns'].index(column)
            projection['rows'] = [row for row in projection['rows'] if row[idx][1] != trail_id]
        source_id = next(row['id'] for row in table_rows(before, 'sources')
                         if json.loads(bytes.fromhex(row['record_json']))['external_source_id'] == result['source'])
        wrapper = {'authorization_decision_id': result['decision_id'],
                   'authorization_outcome': result['decision_outcome'],
                   'authorization_reasons': result['decision_reasons']}
        self.audit(name, before, filtered, wrapper, source_id)

    def history(self, spec, record, result):
        name = spec['name']
        producing = self.results[spec['producer']]
        trail = stored_trail(record['before'], producing['trail_id'])
        history = result.get('historical', {})
        for target, key in [('id', 'trail_id'), ('request_id', 'request_id'),
                            ('decision_id', 'decision_id'), ('packet_id', 'packet_id')]:
            self.expect(name + ':producing-' + target, producing[key], history.get(target))
            self.expect(name + ':stored-' + target, trail[target], history.get(target))
        opted = spec['params']['arguments'].get('supersession', False)
        member = trail.get('supersession')
        self.expect(name + ':member-presence', opted and member is not None, 'supersession' in history)
        if opted and member is not None:
            self.expect(name + ':recorded-member', member, history.get('supersession'))
        if spec.get('member_shape'):
            for key, expected in spec['member_shape'].items():
                self.expect(name + ':consultation-' + key, expected, member.get(key))
        self.expect(name + ':record-version', spec['version'], trail['schema'])
        self.expect(name + ':history-version', None if spec['version'].endswith('.v1') else spec['version'],
                    history.get('schema'))
        if spec['version'].endswith('.v3'):
            associated = copy.deepcopy(trail['associated'])
            self.expect(name + ':native-association-count', 1, len(associated))
            indexed = {row['segment_id'] for row in table_rows(record['before'], 'segment_lexical_rows')}
            for row in associated:
                row['indexed_now'] = row['segment_id'] in indexed
            self.expect(name + ':association-projection', associated, history.get('associated'))
        indexed = {row['segment_id'] for row in table_rows(record['before'], 'segment_lexical_rows')}
        for i, row in enumerate(history.get('candidates', [])):
            self.expect(name + ':indexed-now-' + str(i), row['segment_id'] in indexed, row['indexed_now'])
        stable = copy.deepcopy(result)
        del stable['authorization_decision_id']
        stable['historical'].pop('supersession', None)
        # Only current index membership may change within one historical record.
        for key in ('candidates', 'associated'):
            for row in stable['historical'].get(key, []):
                row.pop('indexed_now', None)
        if spec['producer'] in self.histories:
            self.expect(name + ':historical-property-and-value-equality',
                        self.histories[spec['producer']], stable)
        else:
            self.histories[spec['producer']] = stable
        cross_run = copy.deepcopy(result)
        for key in ('authorization_decision_id', 'trail_id'):
            del cross_run[key]
        for key in ('id', 'request_id', 'decision_id'):
            del cross_run['historical'][key]
        self.selections[name] = cross_run

    def check(self, spec, record, index):
        name, kind = spec['name'], spec['kind']
        self.expect(name + ':schedule-binding', spec, record['schedule'])
        before, after = record['before'], record['after']
        if spec['store'] in self.last_state:
            self.expect(name + ':state-continuity', self.last_state[spec['store']], before)
        self.last_state[spec['store']] = after
        envelope = None
        if kind in ('rpc', 'notify', 'raw'):
            payload = base64.b64decode(record['request']['base64'])
            if kind == 'raw':
                self.expect(name + ':raw-request-bytes', spec['raw'], payload.decode())
            else:
                frame, repeated = strict_json(payload)
                expected = {'jsonrpc': '2.0', 'method': spec['method']}
                if kind != 'notify':
                    expected['id'] = index
                if 'params' in spec:
                    expected['params'] = spec['params']
                self.expect(name + ':request-no-repeated-keys', [], repeated)
                self.expect(name + ':wire-schedule-binding', expected, frame)
            raw = base64.b64decode(record['response']['base64'])
            if raw:
                reply, duplicates = strict_json(raw)
                self.expect(name + ':reply-no-repeated-keys', [], duplicates)
                self.expect(name + ':reply-protocol', '2.0', reply.get('jsonrpc'))
                expected_id = json.loads(spec['raw'])['id'] if kind == 'raw' else index
                self.expect(name + ':reply-id', expected_id, reply.get('id'))
                if spec.get('check') == 'rpc-error':
                    self.expect(name + ':rpc-error', True, 'error' in reply and 'result' not in reply)
                elif spec.get('method') == 'initialize':
                    self.expect(name + ':negotiated-version', '2025-11-25', reply['result']['protocolVersion'])
                elif spec.get('method') == 'tools/list':
                    tools = {tool['name']: tool for tool in reply['result']['tools']}
                    self.expect(name + ':discovered-definitions', self.protocol['discovery'], tools)
                    self.schemas[spec['store']] = tools
                    baseline = self.protocol['baseline_discovery']
                    for unchanged in ('mousa_query', 'mousa_sync', 'mousa_status'):
                        self.expect(name + ':unchanged-definition-' + unchanged,
                                    baseline[unchanged], tools[unchanged])
                    stripped = copy.deepcopy(tools['mousa_trail'])
                    stripped['inputSchema']['properties'].pop('supersession')
                    stripped['outputSchema']['properties']['result']['properties']['historical']['properties'].pop('supersession')
                    stripped['description'] = baseline['mousa_trail']['description']
                    self.expect(name + ':only-trail-schema-growth', baseline['mousa_trail'], stripped)
                else:
                    response = reply['result']
                    envelope = response['structuredContent']
                    tool = spec.get('tool', spec.get('params', {}).get('name'))
                    self.expect(name + ':closed-output-schema', [],
                                schema_violations(self.schemas[spec['store']][tool]['outputSchema'], envelope))
                    self.expect(name + ':text-envelope', envelope, json.loads(response['content'][0]['text']))
                    error = spec.get('error')
                    self.expect(name + ':is-error', bool(error), response.get('isError', False))
                    self.expect(name + ':error-code', error, envelope.get('error', {}).get('code'))
                    if error:
                        self.expect(name + ':no-partial-history', False, 'result' in envelope)
                        if spec.get('refusal_group') and error == 'not_found':
                            group = spec['refusal_group']
                            if group not in self.refusals:
                                self.refusals[group] = envelope['error']
                            self.expect(name + ':own-foreign-unknown-refusal',
                                        self.refusals[group], envelope['error'])
                    else:
                        result = envelope['result']
                        self.expect(name + ':identity-values', [], identity_errors(result))
                        self.results[name] = result
                        if tool == 'mousa_trail':
                            self.expect(name + ':requested-trail-id',
                                        spec['params']['arguments']['trail_id'], result['trail_id'])
                            self.expect(name + ':requested-source', self.protocol['source'], result['source'])
                            self.audit(name, before, after, result)
                            self.expect(name + ':authorization-outcome', spec.get('outcome', 'allow'),
                                        result['authorization_outcome'])
                            if spec.get('outcome') == 'deny':
                                self.expect(name + ':denial-no-history', False, 'historical' in result)
                                self.expect(name + ':denial-wrapper-properties',
                                            ['authorization_decision_id', 'authorization_outcome',
                                             'authorization_reasons', 'source', 'trail_id'], sorted(result))
                            elif spec.get('check') == 'history':
                                self.history(spec, record, result)
            elif kind != 'notify':
                self.expect(name + ':framing-eof', 'framing-eof', spec.get('check'))
        elif kind == 'native':
            self.expect(name + ':native-argv', ['<binary>', '-store', '<store>', *spec['argv']], record['argv'])
            payload = (ROOT / spec['input']).read_bytes() if 'input' in spec else b''
            self.expect(name + ':native-stdin', stream(payload), record['stdin'])
            self.expect(name + ':native-exit', spec.get('exit', 0), record['exit'])
            if record['exit'] == 0:
                result = json.loads(base64.b64decode(record['stdout']['base64']))
                self.results[name] = result
                if spec['argv'][0] == 'query':
                    self.query_writes(name, before, after, result)
                if spec.get('canonical'):
                    self.expect(name + ':canonical-input-output', json.loads(payload), result)
                if spec.get('verify_trail'):
                    producer = self.results[spec['verify_trail']]
                    trail = stored_trail(before, producer['trail_id'])
                    self.expect(name + ':native-verified-member', trail.get('supersession'),
                                result['historical'].get('supersession'))
                    self.expect(name + ':native-verified-id', trail['id'], result['historical']['id'])
                    self.audit(name, before, after, result)
            else:
                self.expect(name + ':startup-no-payload', 0, record['stdout']['bytes'])
                self.expect(name + ':startup-integrity', True, 'integrity' in record['stderr']['text'])
        elif kind == 'damage':
            self.expect(name + ':damage-sql', spec['sql'], record['sql'])
        elif kind == 'start':
            self.expect(name + ':server-argv',
                        ['<binary>', '-store', '<store>', 'mcp', '--caller', 'cli',
                         '--source', self.protocol['source'], '--source', 'peer',
                         '--ingest-source', self.protocol['source']], record['argv'])
        elif kind == 'stop':
            self.expect(name + ':process-exit', spec.get('exit', 0), record['exit'])
            self.expect(name + ':remaining-stdout', 0, record['stdout']['bytes'])
        inspection = envelope is not None and not spec.get('error') and spec.get('params', {}).get('name') == 'mousa_trail'
        if not inspection and not spec.get('verify_trail'):
            if spec.get('effects') is None:
                self.expect(name + ':unchanged-state', before, after)
            elif before is not None:
                allowed = spec['effects']
                changed = [table for table in sorted(set(before['tables']) | set(after['tables']))
                           if not same_json(before['tables'].get(table), after['tables'].get(table))]
                self.expect(name + ':declared-effects', [], [table for table in changed if table not in allowed])
                self.expect(name + ':schema-unchanged', before['schema'], after['schema'])
                if kind == 'native':
                    mutable = {'source_ingest_state', 'local_items', 'local_recovery_sources',
                               'policy_binding_state', 'supersession_activation_state',
                               'segment_lexical_rows'}
                    for table in changed:
                        if table in mutable or table.startswith('segment_lexical_fts'):
                            continue
                        old = {canonical(row) for row in before['tables'][table]['rows']}
                        new = {canonical(row) for row in after['tables'][table]['rows']}
                        self.expect(name + ':existing-rows-preserved-' + table, [], sorted(old - new))

    def run(self):
        for index, original in enumerate(self.protocol['steps'], 1):
            spec = resolve(original, self.results)
            record = self.replay[index - 1] if self.replay is not None else self.produce(spec, index)
            self.records.append(record)
            self.check(spec, record, index)
        self.expect('complete-schedule', len(self.protocol['steps']), len(self.replay or self.records))
        return {'records': self.records, 'assertions': self.assertions, 'selections': self.selections}


def manifest(data):
    return {'bytes': len(data), 'sha256': sha(data)}


def streams_valid(value):
    if isinstance(value, dict):
        if set(value) == {'bytes', 'sha256', 'base64', 'text'}:
            data = base64.b64decode(value['base64'])
            if not same_json(value, stream(data)):
                raise ValueError('stream-integrity')
        for item in value.values():
            streams_valid(item)
    elif isinstance(value, list):
        for item in value:
            streams_valid(item)


def load_capture(path):
    packed = json.loads(gzip.decompress(path.read_bytes()))
    objects = packed['objects']
    hashes = packed['member_sha256']
    if len(objects) != len(hashes):
        raise ValueError('archive-member-count')
    cache = {}

    def expand(value):
        if not isinstance(value, list):
            return value
        tag, identifier = value
        if tag != '@' or type(identifier) is not int or not 0 <= identifier < len(objects):
            raise ValueError('archive-reference')
        if identifier in cache:
            return cache[identifier]
        node = objects[identifier]
        if sha(encoded(node)) != hashes[identifier]:
            raise ValueError('archive-member-hash')
        kind, content = node
        result = ({key: expand(item) for key, item in content} if kind == 'object'
                  else [expand(item) for item in content])
        cache[identifier] = result
        return result

    observed = expand(packed['root'])
    if set(cache) != set(range(len(objects))):
        raise ValueError('unreferenced-archive-member')
    streams_valid(observed)
    return observed


def replay(path, protocol):
    observed = load_capture(path)
    if observed['protocol_sha256'] != sha((ROOT / 'protocol.json').read_bytes()):
        raise ValueError('protocol-pin')
    expected_files = {name: sha((ROOT / name).read_bytes()) for name in protocol['members']}
    if not same_json(expected_files, protocol['members']):
        raise ValueError('protocol-member-integrity')
    regenerated = Capture(protocol, records=observed['records']).run()
    if not same_json(observed['assertions'], regenerated['assertions']):
        old = {row['id']: row for row in observed['assertions']}
        differences = [row['id'] for row in regenerated['assertions']
                       if not same_json(old.get(row['id']), row)]
        raise ValueError('assertion-binding:' + ','.join(differences))
    failed = [row['id'] for row in regenerated['assertions'] if not row['passed']]
    if failed:
        raise ValueError('assertion-failed:' + ','.join(failed))
    if not same_json(observed['selections'], regenerated['selections']):
        raise ValueError('selection-binding')
    if 'expected_selections' in protocol and not same_json(protocol['expected_selections'], regenerated['selections']):
        raise ValueError('frozen-selection')
    return regenerated


def write_capture(path, observed):
    objects, hashes, indices = [], [], {}

    def intern(value):
        if isinstance(value, dict):
            node = ['object', [[key, intern(item)] for key, item in sorted(value.items())]]
        elif isinstance(value, (list, tuple)):
            node = ['array', [intern(item) for item in value]]
        else:
            return value
        digest = sha(encoded(node))
        if digest not in indices:
            indices[digest] = len(objects)
            objects.append(node)
            hashes.append(digest)
        return ['@', indices[digest]]

    root = intern(observed)
    path.write_bytes(gzip.compress(encoded({'root': root, 'objects': objects,
                                           'member_sha256': hashes}), mtime=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['capture', 'replay'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--work', type=Path)
    parser.add_argument('--forbidden-write', action='store_true')
    args = parser.parse_args()
    protocol = json.loads((ROOT / 'protocol.json').read_bytes())
    try:
        if args.mode == 'capture':
            if args.work.exists():
                raise ValueError('capture requires a fresh work directory')
            args.work.mkdir(parents=True)
            if sha(args.binary.read_bytes()) != json.loads((ROOT / 'build.json').read_bytes())['executable_sha256']:
                raise ValueError('binary-pin')
            session = Capture(protocol, args.binary.resolve(), args.work, forbidden=args.forbidden_write)
            try:
                observed = session.run()
            except Exception as error:
                observed = {'records': session.records, 'assertions': session.assertions,
                            'selections': session.selections, 'capture_error': str(error)}
                raise
            finally:
                for process, _, errfile in session.servers.values():
                    process.stdin.close()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    errfile.close()
                if 'observed' in locals():
                    observed['protocol_sha256'] = sha((ROOT / 'protocol.json').read_bytes())
                    write_capture(args.output, observed)
        result = replay(args.output, protocol)
        print(json.dumps({'status': 'PASS', 'steps': len(result['records']),
                          'assertions': len(result['assertions']), 'selections': len(result['selections'])}))
        return 0
    except (ValueError, KeyError, AssertionError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
