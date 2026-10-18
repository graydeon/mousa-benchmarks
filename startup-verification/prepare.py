#!/usr/bin/env python3
"""Build pinned public source and prepare native, closed coherent startup fixtures."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import struct
import subprocess
import sys
import time

from common import (ACCEPTED, BUDGET, ENV, HERE, Objects, PRODUCT, PROTOCOL_SHA,
                    RESERVE, TREE, canonical, decoded_rows, file_identity, loads,
                    physical, preflight, protocol, read_json, require, save, sha, validate_physical,
                    snapshot, workspace_bytes)
from run import accounted_storage, child, preflight_execution, retain_objects, schedule

# The pinned native build's 14 migrations, including FTS shadow column metadata.
SCHEMA_SHA = 'ec7ec8c9bdb210c9dbf96757741b9569ce25078d95dbf2d6003f90a979019fb3'


def tuple_id(*fields):
    raw = [v.encode() if isinstance(v, str) else v for v in fields]
    return sha(b''.join(struct.pack('>Q', len(v)) + v for v in raw))


def encode(record):
    return json.dumps(record, ensure_ascii=False, separators=(',', ':')).encode() + b'\n'


def source_records(index, event_count):
    """Codec adapted from mcp-trail-supersession/prepare.py; native round trips gate it."""
    label = f'fixture/startup/{index:02}'
    source = tuple_id('mousa.source.v1', 'mousa-jsonl', label)
    pins = {}
    for item, text in [('predecessor', 'amber predecessor evidence'), ('successor', 'amber successor evidence')]:
        digest = bytes.fromhex(sha(text.encode()))
        observation = tuple_id('mousa.observation.v1', bytes.fromhex(source), 'item/' + item + '@' + digest.hex().encode().hex())
        artifact = tuple_id('mousa.artifact.v1', bytes.fromhex(observation), 'body')
        representation = tuple_id('mousa.representation.v1', struct.pack('>Q', 1), 'artifact', bytes.fromhex(artifact),
                                  'mousa.text.normalize_utf8', '1', bytes.fromhex(sha(b'')), 'text/plain; charset=utf-8', digest)
        segment = tuple_id('mousa.segment.v1', bytes.fromhex(representation), 'mousa.selector.text_byte_range.v1',
                          struct.pack('>Q', 0), struct.pack('>Q', len(text.encode())), digest)
        pins[item] = {'text': text, 'observation_id': observation, 'artifact_id': artifact, 'representation_id': representation, 'segment_id': segment}
    declaration_id = tuple_id('mousa.supersession_declaration.v1', bytes.fromhex(source), 'predecessor',
                              bytes.fromhex(pins['predecessor']['representation_id']), 'successor',
                              bytes.fromhex(pins['successor']['representation_id']), 'fixture-author', 'synthetic startup fixture')
    declaration = {'schema': 'mousa.supersession_declaration.v1', 'id': declaration_id, 'source_id': source,
                   'predecessor_item_id': 'predecessor', 'predecessor_representation_id': pins['predecessor']['representation_id'],
                   'successor_item_id': 'successor', 'successor_representation_id': pins['successor']['representation_id'],
                   'author': 'fixture-author', 'basis': 'synthetic startup fixture'}
    events, previous = [], None
    for number in range(1, event_count + 1):
        selected = declaration_id if number % 2 else None
        identifier = tuple_id('mousa.supersession_activation.v1', bytes.fromhex(source),
                              bytes.fromhex(previous) if previous else b'', bytes.fromhex(selected) if selected else b'')
        events.append({'schema': 'mousa.supersession_activation.v1', 'id': identifier, 'source_id': source,
                       'expected_previous_activation_id': previous, 'declaration_id': selected, 'actor_id': 'fixture-actor',
                       'actor_version': '1', 'occurred_at_usec': 1700000000000000 + number, 'reason': 'synthetic startup transition'})
        previous = identifier
    return {'label': label, 'source_id': source, 'pins': pins, 'declaration': declaration, 'events': events}


def fixture_gate(state, s, e, t):
    require(type(s) is int and s in (1, 8) and type(e) is int and e in (0, 1, 17, 65, 257)
            and type(t) is int and t in (0, 1), 'fixture dimension types/values')
    expected = {'sources': s, 'observations': 2*s, 'artifacts': 2*s, 'representations': 2*s,
                'segments': 2*s, 'local_items': 2*s, 'supersession_declarations': s,
                'supersession_activations': s*e, 'supersession_activation_state': s if e else 0,
                'source_trails': s*t, 'source_trail_candidates': 2*s*t, 'policy_decisions': s*t,
                'policy_decision_inputs': s*t, 'ingest_receipts': 2*s, 'representation_inputs': 2*s,
                'source_ingest_state': s, 'segment_lexical_rows': 2*s, 'segment_lexical_fts_content': 2*s,
                'source_withdrawals': 0, 'local_recovery_sources': 0, 'ingest_gaps': 0,
                'classifications': 0, 'classification_bases': 0, 'callers': 0, 'purposes': 0,
                'policy_definitions': 1, 'policy_bindings': 1, 'policy_activations': 1, 'policy_binding_state': 1}
    for table, count in expected.items():
        require(state['tables'][table]['count'] == count, 'fixture cardinality: ' + table)
    require(state['tables']['schema_migrations']['count'] == 14, 'current schema migrations')
    require(state['application_id'] == 1297044819 and state['user_version'] == 0, 'current schema header')
    schema = {'schema': state['schema'], 'columns': {name: table['columns'] for name, table in state['tables'].items()}}
    require(sha(canonical(schema)) == SCHEMA_SHA, 'current schema objects/columns')
    declarations = decoded_rows(state, 'supersession_declarations')
    events = decoded_rows(state, 'supersession_activations')
    projections = decoded_rows(state, 'supersession_activation_state')
    expected_records = {}
    for index in range(s):
        records = source_records(index, e)
        expected_records[records['source_id']] = records
        source = bytes.fromhex(records['source_id'])
        source_rows = [row for row in decoded_rows(state, 'sources') if row['id'] == source]
        expected_source = {'schema': 'mousa.source.v1', 'id': records['source_id'], 'namespace': 'mousa-jsonl', 'external_source_id': records['label']}
        require(len(source_rows) == 1 and source_rows[0]['record_json'] == encode(expected_source), 'native source label/identity')
        selected_declarations = [row for row in declarations if row['source_id'] == source]
        declaration = records['declaration']
        require(len(selected_declarations) == 1 and selected_declarations[0]['record_json'] == encode(declaration), 'canonical declaration record bytes')
        for field in ('id', 'source_id', 'predecessor_representation_id', 'successor_representation_id'):
            require(selected_declarations[0][field] == bytes.fromhex(declaration[field]), 'declaration identity projection')
        for field in ('predecessor_item_id', 'successor_item_id'):
            require(selected_declarations[0][field] == declaration[field], 'declaration item projection')
        selected_events = {row['id'].hex(): row for row in events if row['source_id'] == source}
        require(set(selected_events) == {r['id'] for r in records['events']}, 'per-source event count/chain')
        for event in records['events']:
            actual = selected_events[event['id']]
            require(actual['record_json'] == encode(event), 'canonical event record bytes')
            for field in ('id', 'source_id', 'expected_previous_activation_id', 'declaration_id'):
                require(actual[field] == (bytes.fromhex(event[field]) if event[field] is not None else None), 'per-source event projection/chain')
        actual_projection = [row for row in projections if row['source_id'] == source]
        desired_projection = [] if not e else [{'source_id': source, 'current_activation_id': bytes.fromhex(records['events'][-1]['id']),
                                                'active_declaration_id': bytes.fromhex(records['declaration']['id'])}]
        require(actual_projection == desired_projection, 'activation projection')
        for item, pin in records['pins'].items():
            for table, field in [('observations', 'observation_id'), ('artifacts', 'artifact_id'), ('representations', 'representation_id'), ('segments', 'segment_id')]:
                require(any(row['id'].hex() == pin[field] for row in decoded_rows(state, table)), 'native pin: ' + field)
            rows = [row for row in decoded_rows(state, 'local_items') if row['source_id'] == source and row['item_id'] == item]
            require(len(rows) == 1 and rows[0]['representation_id'].hex() == pin['representation_id'] and rows[0]['active'] == 1, 'native item pin')
            observation = next(row for row in decoded_rows(state, 'observations') if row['id'].hex() == pin['observation_id'])
            observation_record = {'schema': 'mousa.observation.v1', 'id': pin['observation_id'], 'source_id': records['source_id'],
                                  'external_observation_id': 'item/'+item+'@'+sha(pin['text'].encode()).encode().hex()}
            require(observation['source_id'] == source and observation['record_json'] == encode(observation_record), 'native revision ancestry')
            artifact = next(row for row in decoded_rows(state, 'artifacts') if row['id'].hex() == pin['artifact_id'])
            require(artifact['observation_id'].hex() == pin['observation_id'], 'artifact ancestry')
            indexed = next(row for row in decoded_rows(state, 'segment_lexical_rows') if row['segment_id'].hex() == pin['segment_id'])
            retained = next(row for row in decoded_rows(state, 'segment_lexical_fts_content') if row['id'] == indexed['rowid'])
            require(retained['c0'] == pin['text'] and retained['c1'].hex() == sha(pin['text'].encode()), 'native retained content')
    decisions = {row['id'].hex(): loads(row['record_json']) for row in decoded_rows(state, 'policy_decisions')}
    seen_sources = []
    for row in decoded_rows(state, 'source_trails'):
        trail = loads(row['record_json'])
        decision = decisions[trail['decision_id']]
        source = decision['request']['source_id']
        seen_sources.append(source)
        require(source in expected_records, 'v4 source identity')
        records = expected_records[source]
        require(trail['schema'] == 'mousa.source_trail.v4' and trail['outcome'] == 'allow', 'v4 allow')
        require(row['id'].hex() == trail['id'] and row['decision_id'].hex() == trail['decision_id'] and row['packet_id'].hex() == trail['packet_id'], 'v4 row projection')
        require(decision['id'] == trail['decision_id'] and decision['request']['id'] == trail['request_id'] and decision['outcome'] == 'allow', 'v4 decision parent')
        selection = trail['supersession']
        require(selection['consulted'] is True, 'v4 consultation')
        require(selection['activation_id'] == (records['events'][-1]['id'] if e else None), 'v4 final tip')
        require(selection['declaration_id'] == (records['declaration']['id'] if e else None), 'v4 declaration')
        candidates = trail['candidates']
        require(len(candidates) == 2, 'v4 candidates')
        require({candidate['segment_id'] for candidate in candidates} ==
                {pin['segment_id'] for pin in records['pins'].values()}, 'v4 candidate pins')
        for candidate in candidates:
            item = next(k for k, pin in records['pins'].items() if pin['segment_id'] == candidate['segment_id'])
            require(candidate['selected'] is (not e or item == 'successor'), 'v4 selection')
            require(candidate['disposition'] == 'accepted' and type(candidate['final_rank']) is int and candidate['final_rank'] > 0, 'v4 accepted candidate')
        actual_candidates = sorted((row for row in decoded_rows(state, 'source_trail_candidates') if row['trail_id'].hex() == trail['id']), key=lambda row: row['ordinal'])
        expected_candidates = [{'trail_id': bytes.fromhex(trail['id']), 'ordinal': ordinal,
                                'segment_id': bytes.fromhex(candidate['segment_id']), 'final_rank': candidate['final_rank'],
                                'disposition': candidate['disposition'], 'selected': int(candidate['selected'])}
                               for ordinal, candidate in enumerate(candidates)]
        require(actual_candidates == expected_candidates, 'v4 candidate projections')
        require(len(selection['dispositions']) == (1 if e else 0), 'v4 dispositions')
        if e:
            disposition = {'selection': 'superseded', 'segment_id': records['pins']['predecessor']['segment_id'],
                           'content_sha256': sha(records['pins']['predecessor']['text'].encode()), 'declaration_id': records['declaration']['id'],
                           **{key: records['declaration'][key] for key in ('predecessor_item_id', 'predecessor_representation_id',
                                                                         'successor_item_id', 'successor_representation_id')}}
            require(canonical(selection['dispositions']) == canonical([disposition]), 'v4 exact suppression disposition')
    require(sorted(seen_sources) == (sorted(source_records(i, e)['source_id'] for i in range(s)) if t else []), 'v4 per-source count')
    return expected


def coherent(source, destination):
    before = snapshot(source)
    incoming = sqlite3.connect(Path(source).resolve().as_uri() + '?mode=ro', uri=True)
    outgoing = sqlite3.connect(destination)
    try:
        incoming.backup(outgoing)
        outgoing.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        require(outgoing.execute('PRAGMA integrity_check').fetchall() == [('ok',)], 'backup integrity')
        require(outgoing.execute('PRAGMA foreign_key_check').fetchall() == [], 'backup foreign keys')
    finally:
        incoming.close()
        outgoing.close()
    require(canonical(snapshot(destination)) == canonical(before), 'coherent backup logical equivalence')
    require(not Path(str(destination) + '-wal').exists() or Path(str(destination) + '-wal').stat().st_size == 0, 'seed WAL not empty')


def git(source, *args):
    return subprocess.check_output(['git', '-C', str(source), *args]).decode().strip()


def verify_prepared(root, *, allow_prefix=False):
    root = Path(root)
    receipt = read_json(root / 'preparation.json')
    require(receipt['product_commit'] == PRODUCT and receipt['product_tree'] == TREE, 'product source pin')
    require(receipt['protocol_sha256'] == PROTOCOL_SHA, 'protocol pin')
    require(file_identity(root / 'bin/mousa') == receipt['binary_identity'], 'binary pin')
    keys = [fixture['key'] for fixture in receipt['fixtures']]
    grid = [f's{s}-e{e}-t{t}' for s in (1, 8) for e in (0, 1, 17, 65, 257) for t in (0, 1)]
    if allow_prefix:
        require(keys == grid[:len(keys)] and len(keys) <= 20, 'fixture prefix coverage')
    else:
        require(len(keys) == 20, 'fixture coverage')
        require(len(set(keys)) == 20 and set(keys) == set(grid), 'fixture key coverage')
    for fixture in receipt['fixtures']:
        require(fixture['key'] == f"s{fixture['S']}-e{fixture['E']}-t{fixture['T']}", 'fixture label')
        validate_physical(fixture['physical'])
        require(fixture['physical']['main'] == fixture['seed_identity'], 'fixture physical identity')
        require(fixture['seed_path'] == 'seeds/'+fixture['key']+'/store.sqlite', 'fixture seed path')
        require(canonical(fixture['declarations']) == canonical([source_records(i, fixture['E'])['declaration'] for i in range(fixture['S'])]), 'prepared declaration identities')
        require(file_identity(root / fixture['seed_path']) == fixture['seed_identity'], 'seed identity')
        state = snapshot(root / fixture['seed_path'])
        require(sha(canonical(state)) == fixture['logical']['sha256'], 'seed logical identity')
        counts = fixture_gate(state, fixture['S'], fixture['E'], fixture['T'])
        require(canonical(fixture['counts']) == canonical(counts), 'prepared cardinality metadata')
    return receipt


def import_prefix(source, output, objects, binary_identity, through=None):
    source = Path(source).resolve()
    require(source.parent == output.resolve().parent and source != output.resolve(), 'prefix campaign accounting')
    prior = verify_prepared(source, allow_prefix=True)
    require(prior['binary_identity'] == binary_identity, 'prefix binary identity')
    paths = sorted((source / 'invocations').glob('*.json.gz'))
    require(paths and [p.name for p in paths] == [f'{i:06}.json.gz' for i in range(len(paths))], 'prefix invocation coverage')
    require(len(paths) <= sum(s*(e+9) for s in (1, 8) for e in (0, 1, 17, 65, 257)), 'prefix too long')
    unused = []
    if through is not None:
        require(type(through) is int and 0 <= through < len(paths), 'prefix cutoff ordinal')
        paths, unused = paths[:through+1], paths[through+1:]
    last = read_json(paths[-1])
    require(last['command']['censor_reason'] is None and 'after' in last, 'prefix must end at an uncensored closed invocation')
    retain_objects(source, objects)
    state = objects.json(last['after'])
    original = source / 'workspace/trial/store.sqlite'
    require(canonical(snapshot(original)) == canonical(state), 'prefix live state differs from last retained state')
    trial = output / 'workspace/trial'
    trial.mkdir()
    coherent(original, trial / 'store.sqlite')
    information = {'preparation': objects.put_file(source / 'preparation.json'),
                   'native_invocations': len(paths), 'logical': last['after'], 'invocations': [],
                   'unreused_invocations': [objects.put_file(path) for path in unused],
                   'derivation': 'uncensored native invocation prefix and coherent closed backup; original source bytes retained'}
    if (source / 'failure.json').exists():
        information['original_failure'] = objects.put_file(source / 'failure.json')
    return prior, paths, information


def reused_output(row, ordinal, argv, payload, expected_exit):
    from analyze import check_monitor
    command = row['command']
    require(type(row['ordinal']) is int and row['ordinal'] == ordinal
            and row['phase'] == command['phase'] == 'preparation', 'reused preparation ordinal/phase')
    require(command['argv'] == ['./bin/mousa', '-store', 'trial/store.sqlite', *argv]
            and command['stdin_hex'] == payload.hex() and canonical(command['environment']) == canonical(ENV)
            and command['cwd'] == '.', 'reused preparation argv/input')
    check_monitor(command, control=True)
    require(all(p['requested_ms'] <= 1 for p in command['monitor']['polls']), 'reused preparation cadence')
    require(command['exit'] == expected_exit and command['censor_reason'] is None
            and 'after' in row, 'reused preparation exit/cancellation')
    require(not command['stderr_hex'] if expected_exit == 0 else bool(command['stderr_hex']), 'reused preparation stderr')
    return bytes.fromhex(command['stdout_hex'])


def execute(args):
    protocol(args.protocol)
    preflight()
    require(git(args.source, 'rev-parse', 'HEAD') == PRODUCT, 'product commit mismatch')
    require(git(args.source, 'rev-parse', 'HEAD^{tree}') == TREE, 'product tree mismatch')
    require(not git(args.source, 'status', '--porcelain=v1'), 'dirty product source')
    objects = Objects(args.output)
    work = args.output / 'workspace'
    (work / 'bin').mkdir(parents=True)
    (work / 'home').mkdir()
    (work / 'tmp').mkdir()
    support = preflight_execution(work, objects, accounted_storage(args.output.parent, work))
    cache_names = ('GOCACHE', 'GOMODCACHE', 'GOPATH')
    cache_paths = subprocess.check_output(['go', 'env', *cache_names]).decode().splitlines()
    build_env = {'PATH': str(Path(shutil.which('go')).parent)+':/usr/bin:/bin',
                 'HOME': str((work / 'home').resolve()),
                 'TMPDIR': str((work / 'tmp').resolve()),
                 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC',
                 'GOWORK': 'off', 'CGO_ENABLED': '0', 'GOOS': 'linux', 'GOARCH': 'amd64', 'GOAMD64': 'v1',
                 'GOTOOLCHAIN': 'local', 'GOPROXY': 'off', 'GOSUMDB': 'off', 'GOTELEMETRY': 'off',
                 **dict(zip(cache_names, cache_paths))}
    go_version = subprocess.check_output(['go', 'version'], env=build_env).decode().strip()
    require(go_version.split()[2] == 'go1.27.1', 'effective Go toolchain mismatch')
    candidate = args.output.resolve() / 'built-mousa'
    build = ['go', 'build', '-trimpath', '-buildvcs=false', '-o', str(candidate), './cmd/mousa']
    modules = subprocess.run(['go', 'mod', 'verify'], cwd=args.source, env=build_env, capture_output=True)
    save(args.output / 'module-verification.json', {'exit': modules.returncode, 'stdout_hex': modules.stdout.hex(), 'stderr_hex': modules.stderr.hex()})
    require(modules.returncode == 0, 'module verification')
    built = subprocess.run(build, cwd=args.source, env=build_env, capture_output=True)
    save(args.output / 'build.json', {'exit': built.returncode, 'argv': build, 'environment': build_env, 'stdout_hex': built.stdout.hex(), 'stderr_hex': built.stderr.hex()})
    require(built.returncode == 0, 'product build')
    require(not git(args.source, 'status', '--porcelain=v1'), 'product source changed during build')
    if args.binary.exists():
        require(file_identity(args.binary) == file_identity(candidate), 'binary does not match pinned build')
    else:
        shutil.copy2(candidate, args.binary)
    (args.output / 'bin').mkdir()
    shutil.copy2(args.binary, args.output / 'bin/mousa')
    shutil.copy2(args.binary, work / 'bin/mousa')
    receipt = {'kind': 'unmeasured-preparation', 'product_commit': PRODUCT, 'product_tree': TREE,
               'pidfd_preflight': support,
               'preparation_start_ns': args.phase_start_ns, 'peak_observed_workspace_bytes': 0,
               'python': sys.version, 'sqlite': sqlite3.sqlite_version,
               'protocol_sha256': PROTOCOL_SHA, 'accepted_protocol_commit': ACCEPTED,
               'binary_identity': file_identity(args.binary), 'fixtures': [],
               'go_version': go_version, 'build_environment': build_env,
               'module_files': {name: objects.put((args.source / name).read_bytes()) for name in ('go.mod', 'go.sum')},
               'module_list': objects.put(subprocess.check_output(['go', 'list', '-m', '-f', '{{.Path}} {{.Version}} {{.Sum}} {{.GoModSum}}', 'all'], cwd=args.source, env=build_env)),
               'binary_buildinfo': objects.put(subprocess.check_output(['go', 'version', '-m', './bin/mousa'], cwd=args.output, env=build_env)),
               'sources': {p.name: objects.put(p.read_bytes()) for p in HERE.glob('*.py')}}
    receipt['not_run'] = [{'ordinal': row['ordinal'], 'status': 'NOT RUN', 'reason': 'unmeasured preparation only'} for row in schedule()]
    save(args.output / 'preparation.json', receipt)
    calls = args.output / 'invocations'
    calls.mkdir()
    prefix_paths, prefix_fixtures, prefix_information = [], {}, None
    if args.reuse_prefix is not None:
        prior, prefix_paths, prefix_information = import_prefix(args.reuse_prefix, args.output, objects, receipt['binary_identity'], args.reuse_through)
        prefix_fixtures = {fixture['key']: fixture for fixture in prior['fixtures']}
        receipt['reused_prefix'] = prefix_information
        save(args.output / 'preparation.json', receipt)
    ordinal = 0
    def invoke(argv, payload=b'', expected_exit=0):
        nonlocal ordinal
        if ordinal < len(prefix_paths):
            path = prefix_paths[ordinal]
            require(path.is_file() and not path.is_symlink(), 'prefix invocation type')
            row = read_json(path)
            output = reused_output(row, ordinal, argv, payload, expected_exit)
            os.link(path, calls / path.name)
            prefix_information['invocations'].append(objects.put_file(path))
            ordinal += 1
            return output
        storage = accounted_storage(args.output.parent, work)
        usage = storage()
        receipt['peak_observed_workspace_bytes'] = max(receipt['peak_observed_workspace_bytes'], usage)
        require(usage < BUDGET - RESERVE, 'preparation storage')
        before_physical = physical(work / 'trial/store.sqlite')
        before = snapshot(work / 'trial/store.sqlite') if (work / 'trial/store.sqlite').exists() else None
        if prefix_paths and ordinal == len(prefix_paths) and continuing_group:
            require(before is not None and sha(canonical(before)) == prefix_information['logical']['sha256'],
                    'prefix continuation state')
        actual = child(['./bin/mousa', '-store', 'trial/store.sqlite', *argv], work, ENV, payload,
                       phase='preparation', control_limits={'command_seconds': None},
                       storage=storage)
        receipt['peak_observed_workspace_bytes'] = max(receipt['peak_observed_workspace_bytes'],
                                                     *(item['bytes'] for item in actual['monitor']['storage']))
        row = {'phase': 'preparation', 'ordinal': ordinal, 'command': actual,
               'before': objects.put_snapshot(before) if before is not None else objects.put(b'null'),
               'before_physical': before_physical}
        save(calls / f'{ordinal:06}.json.gz', row)
        row['after_physical'] = physical(work / 'trial/store.sqlite')
        row['after'] = objects.put_snapshot(snapshot(work / 'trial/store.sqlite'))
        save(calls / f'{ordinal:06}.json.gz', row)
        ordinal += 1
        require(actual['exit'] == expected_exit and not actual['censor_reason'], 'native preparation exit/cancellation')
        require(not actual['stderr_hex'] if expected_exit == 0 else bool(actual['stderr_hex']), 'native preparation stderr')
        return bytes.fromhex(actual['stdout_hex'])
    for s in (1, 8):
        for e in (0, 1, 17, 65, 257):
            trial = work / 'trial'
            continuing_group = ordinal < len(prefix_paths)
            if not continuing_group:
                if trial.exists():
                    shutil.rmtree(trial)
                trial.mkdir()
            for index in range(s):
                records = source_records(index, e)
                payload = b''.join(encode({'id': item, 'text': pin['text']}) for item, pin in records['pins'].items())
                invoke(['sync', '--source', records['label'], '--segment-policy', 'fixed-v1'], payload)
                require(invoke(['supersession', 'declaration', 'put'], encode(records['declaration'])) == encode(records['declaration']), 'native declaration canonical output')
                for event in records['events']:
                    require(invoke(['supersession', 'activation', 'put'], encode(event)) == encode(event), 'native activation canonical output')
            for t in (0, 1):
                if t:
                    for index in range(s):
                        records = source_records(index, e)
                        response = loads(invoke(['query', '--source', records['label'], '--policy', 'original', '--packing-policy', 'original', '--budget-bytes', '8192', '--supersession', 'amber']))
                        require(response['decision_outcome'] == 'allow' and type(response['matched_candidates']) is int and response['matched_candidates'] == 2 and response['supersession_excluded'] == (1 if e else 0), 'native trail output')
                for index in range(s):
                    records = source_records(index, e)
                    require(invoke(['supersession', 'declaration', 'get', records['declaration']['id']]) == encode(records['declaration']), 'native declaration readback')
                    desired_status = {'source': records['label'], 'collection_state': 'active', 'observations': 2, 'active_items': 2, 'needs_recovery': False}
                    require(canonical(loads(invoke(['status', '--source', records['label']]))) == canonical(desired_status), 'native status')
                    output = invoke(['supersession', 'activation', 'state', records['source_id']], expected_exit=0 if e else 1)
                    if e:
                        require(canonical(loads(output)) == canonical({'source_id': records['source_id'], 'current_activation_id': records['events'][-1]['id'], 'active_declaration_id': records['declaration']['id']}), 'native state')
                    else:
                        require(output == b'', 'no-history state payload')
                key = f's{s}-e{e}-t{t}'
                seed = args.output / 'seeds' / key / 'store.sqlite'
                seed.parent.mkdir(parents=True)
                old = prefix_fixtures.get(key)
                origin = args.reuse_prefix / old['seed_path'] if old is not None else trial / 'store.sqlite'
                coherent(origin, seed)
                state = snapshot(seed)
                counts = fixture_gate(state, s, e, t)
                fixture = {'key': key, 'S': s, 'E': e, 'T': t, 'counts': counts,
                           'seed_path': seed.relative_to(args.output).as_posix(), 'seed_identity': file_identity(seed),
                           'physical': physical(seed), 'logical': objects.put_snapshot(state),
                           'declarations': [source_records(i, e)['declaration'] for i in range(s)],
                           'derivation': 'native sync/administration; T1 extends coherent T0 state with native queries'}
                if old is not None:
                    fixture['derivation'] = {'kind': 'coherent native fixture reuse',
                                             'preparation': prefix_information['preparation'],
                                             'source_fixture': key, 'source_seed_identity': old['seed_identity']}
                receipt['fixtures'].append(fixture)
                save(args.output / 'preparation.json', receipt)
                print('prepared', key, 'native receipts', ordinal, 'reused', min(ordinal, len(prefix_paths)), flush=True)
    verify_prepared(args.output)
    receipt['preparation_end_ns'] = time.monotonic_ns()
    receipt['new_native_invocations'] = ordinal-len(prefix_paths)
    receipt['peak_observed_workspace_bytes'] = max(receipt['peak_observed_workspace_bytes'], workspace_bytes(args.output.parent))
    save(args.output / 'preparation.json', receipt)
    print('PASS: 20 native fixtures; preparation only')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, default=HERE / 'protocol.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reuse-prefix', type=Path, help='reuse an uncensored closed native preparation prefix in the same campaign')
    parser.add_argument('--reuse-through', type=int, help='inclusive last successful native ordinal; retain any later failure separately')
    args = parser.parse_args()
    require(args.reuse_prefix is not None or args.reuse_through is None, 'reuse cutoff requires prefix')
    args.phase_start_ns = time.monotonic_ns()
    import signal
    from run import operator_interrupt
    signal.signal(signal.SIGTERM, operator_interrupt)
    require(not args.output.exists(), 'preparation output exists')
    args.output.mkdir(parents=True)
    not_run = [{'ordinal': row['ordinal'], 'status': 'NOT RUN', 'reason': 'preparation only; collection NOT RUN'}
               for row in schedule()]
    save(args.output / 'not-run.json', not_run)
    try:
        objects = Objects(args.output)
        save(args.output / 'preflight.json', {
            'kind': 'unmeasured preparation', 'expected_product': PRODUCT, 'expected_tree': TREE,
            'protocol_input': objects.put(args.protocol.read_bytes()),
            'binary_input': file_identity(args.binary) if args.binary.exists() else None,
            'sources': {p.name: objects.put(p.read_bytes()) for p in HERE.glob('*.py')}})
        execute(args)
    except BaseException as error:
        save(args.output / 'failure.json', {'kind': 'unmeasured preparation failure',
                                          'error_class': type(error).__name__, 'message': str(error),
                                          'collection': 'NOT RUN', 'not_run': not_run})
        raise


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
