#!/usr/bin/env python3
"""Disposable negative controls; never measured startup observations."""
import argparse
import copy
import json
import os
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time

import analyze
from common import (ENV, Objects, canonical, decoded_rows, file_identity, loads, physical, read_json,
                    require, save, sha, snapshot, typed)
from run import accounted_storage, argv_for, child


def duplicate_v4_candidates(state):
    """Forge a disposable trail and matching SQL projections, retaining two ordinals."""
    from prepare import encode
    trails = decoded_rows(state, 'source_trails')
    trail = loads(trails[0]['record_json'])
    trail['candidates'][1] = copy.deepcopy(trail['candidates'][0])
    trails[0]['record_json'] = encode(trail)
    candidates = sorted(decoded_rows(state, 'source_trail_candidates'), key=lambda row: row['ordinal'])
    candidates[1] = {**candidates[0], 'ordinal': 1}
    for name, rows in [('source_trails', trails), ('source_trail_candidates', candidates)]:
        table = state['tables'][name]
        names = [column[1] for column in table['columns'] if column[6] != 1]
        table['rows'] = sorted([[typed(row[column]) for column in names] for row in rows], key=canonical)
        table['sha256'] = sha(b''.join(canonical(row)+b'\n' for row in table['rows']))


def replay_mutations(smoke, output, prep):
    """Regenerate semantic mutations without executing the product."""
    from prepare import verify_prepared
    original = analyze.verify(smoke)
    results = []
    for name, field, detector in [('product commit', 'product_commit', 'product source pin'),
                                  ('tree', 'product_tree', 'product source pin'),
                                  ('protocol', 'protocol_sha256', 'protocol pin'),
                                  ('binary', None, 'binary pin')]:
        with tempfile.TemporaryDirectory(dir=output) as temporary:
            root = Path(temporary)
            altered = copy.deepcopy(prep)
            if field is not None:
                altered[field] = '0'*64
            else:
                (root / 'bin').mkdir()
                (root / 'bin/mousa').write_bytes(b'not the pinned executable')
            save(root / 'preparation.json', altered)
            try:
                verify_prepared(root)
            except ValueError as error:
                require(str(error) == detector, 'preflight pin detector')
                results.append({'name': 'preflight wrong '+name, 'observed': str(error), 'native_invocations': 0,
                                'kind': 'unmeasured-control'})
            else:
                raise ValueError('preflight accepted wrong '+name)
    # Reuse raw lossless members. Mutations get new content-addressed members and
    # recomputed capture bytes; no stale digest is the intended detector.
    def mutation(name, change, detector, passes=False):
        with tempfile.TemporaryDirectory(dir=output) as temp:
            root = Path(temp)
            shutil.copy2(smoke / 'schedule.json', root / 'schedule.json')
            (root / 'objects').mkdir()
            for path in (smoke / 'objects').iterdir():
                os.link(path, root / 'objects' / path.name)
            altered = copy.deepcopy(original)
            change(altered, Objects(root))
            for entry in altered['entries']:
                command = entry['command']
                for stream in ('stdin', 'stdout', 'stderr'):
                    from common import sha
                    command[stream+'_sha256'] = sha(bytes.fromhex(command[stream+'_hex']))
                entry['command'] = Objects(root).put(canonical(command))
            save(root / 'capture.json', altered)
            failure = None
            try:
                analyze.verify(root)
            except (ValueError, KeyError) as error:
                failure = str(error)
            require((failure is None) if passes else failure is not None and detector in failure, 'control detector mismatch: ' + name + ': ' + str(failure))
            results.append({'name': name, 'kind': 'unmeasured-control', 'expected_detector': detector, 'observed': failure or 'PASS', 'rehash': 'new objects and capture serialization'})
            save(output / 'mutations.json', results)
    mutation('untouched replay', lambda c, o: None, '', True)
    mutation('missing sample', lambda c, o: c['entries'].pop(), 'smoke coverage')
    mutation('duplicate sample', lambda c, o: c['entries'].append(copy.deepcopy(c['entries'][0])), 'smoke coverage')
    mutation('skipped sample', lambda c, o: c['entries'].__setitem__(1, copy.deepcopy(c['entries'][2])), 'smoke ordinal/order')
    mutation('reordered sample', lambda c, o: c['entries'].reverse(), 'smoke ordinal/order')
    mutation('incomplete suffix', lambda c, o: c['remainder'].pop(), 'explicit NOT RUN')
    mutation('boolean ordinal', lambda c, o: c['entries'][0].__setitem__('ordinal', False), 'smoke ordinal/order')
    def prep_mutation(field, value):
        def change(c, o):
            p = o.json(c['preparation'])
            p[field] = value
            c['preparation'] = o.put(canonical(p))
        return change
    mutation('wrong product commit', prep_mutation('product_commit', '0'*40), 'product/protocol pins')
    mutation('wrong tree', prep_mutation('product_tree', '0'*40), 'product/protocol pins')
    mutation('wrong protocol', lambda c, o: c.__setitem__('protocol_sha256', '0'*64), 'protocol identity')
    def mislabeled(c, o):
        p = o.json(c['preparation'])
        p['fixtures'][0]['E'] = 1
        c['preparation'] = o.put(canonical(p))
    mutation('mislabeled history cardinality', mislabeled, 'fixture label/cardinality')
    def wrong_counts(c, o):
        p = o.json(c['preparation'])
        p['fixtures'][2]['logical'] = p['fixtures'][0]['logical']
        c['preparation'] = o.put(canonical(p))
    mutation('history counts independently recomputed', wrong_counts, 'fixture cardinality: supersession_activations')
    def command_field(field, value, index=0):
        return lambda c, o: c['entries'][index]['command'].__setitem__(field, value)
    mutation('false success', command_field('stdout_hex', b'failed command\n'.hex()), 'canonical declaration output')
    mutation('declaration byte mutation', command_field('stdout_hex', (bytes.fromhex(original['entries'][0]['command']['stdout_hex'])+b' ').hex()), 'canonical declaration output')
    mutation('status JSON type', command_field('stdout_hex', b'{"source":"fixture/startup/00","collection_state":"active","observations":true,"active_items":2,"needs_recovery":false}'.hex(), 1), 'status output/type')
    mutation('status JSON duplicate', command_field('stdout_hex', b'{"source":"fixture/startup/00","source":"fixture/startup/00"}'.hex(), 1), 'duplicate JSON key')
    def key_order(index):
        def change(c, o):
            command = c['entries'][index]['command']
            raw = json.loads(bytes.fromhex(command['stdout_hex']))
            command['stdout_hex'] = json.dumps(dict(reversed(list(raw.items())))).encode().hex()
        return change
    mutation('declaration JSON-equivalent key order', key_order(0), 'canonical declaration output')
    mutation('status harmless key order', key_order(1), '', True)
    def monitor(field, value):
        return lambda c, o: c['entries'][0]['command']['monitor'].__setitem__(field, value)
    mutation('wrong wait mechanism', monitor('mechanism', 'sleep/WNOHANG'), 'wait mechanism')
    mutation('missing wait4', monitor('wait4_calls', 0), 'exact-child wait4')
    mutation('missing deadline records', monitor('deadlines', []), 'missing monitor records')
    mutation('missing storage records', monitor('storage', []), 'missing storage check')
    mutation('wrong poll cadence', lambda c, o: c['entries'][0]['command']['monitor']['polls'][0].__setitem__('requested_ms', 2), 'poll cadence')
    mutation('RSS boolean type', command_field('rss_kib', True), 'RSS type/unit')
    mutation('CPU boolean type', command_field('user_seconds', True), 'CPU type/unit')
    mutation('exit status boolean alias', command_field('exit_code', False), 'exit/signal/deadline types')
    mutation('poll timestamp float', lambda c, o: c['entries'][0]['command']['monitor']['polls'][0].__setitem__(
        'end_ns', float(c['entries'][0]['command']['monitor']['polls'][0]['end_ns'])), 'poll timestamp types')
    mutation('wall metric boundary', command_field('wall_ns', original['entries'][0]['command']['wall_ns']+1), 'wall boundary')
    mutation('read-only main-file mutation', lambda c, o: c['entries'][0]['after_physical']['main'].__setitem__('sha256', '0'*64), 'read-only main-file mutation')
    mutation('status physical-only main-file change', lambda c, o: c['entries'][1]['after_physical']['main'].__setitem__('sha256', '0'*64), '', True)
    def failed_argv(c, o):
        c['failure'] = {'class': 'ValueError', 'message': 'synthetic control claimed failure'}
        c['entries'][-1]['command']['argv'] = ['./bin/mousa', 'wrong-command']
    mutation('failed final argv mutation', failed_argv, 'argv binding')
    def logical(c, o):
        state = o.json(c['entries'][0]['after'])
        state['user_version'] += 1
        c['entries'][0]['after'] = o.put_snapshot(state)
    mutation('logical mutation', logical, 'logical/schema mutation')
    def duplicate_candidates(c, o):
        prepared = o.json(c['preparation'])
        fixture = prepared['fixtures'][1]
        require((fixture['S'], fixture['E'], fixture['T']) == (1, 0, 1), 'v4 control fixture')
        state = o.json(fixture['logical'])
        duplicate_v4_candidates(state)
        fixture['logical'] = o.put_snapshot(state)
        c['preparation'] = o.put(canonical(prepared))
    mutation('v4 duplicate candidate pins with matching projections', duplicate_candidates, 'v4 candidate pins')
    return results


def synthetic_analysis(smoke, output):
    """Invent outcomes and metrics explicitly; retain only native logical states."""
    import csv
    from prepare import encode, source_records
    from run import schedule
    source = Objects(smoke)
    baseline = analyze.verify(smoke)
    prep = source.json(baseline['preparation'])
    fixtures = {fixture['key']: fixture for fixture in prep['fixtures']}
    frozen = schedule(prep)
    operations = {(e['fixture'], e['operation']): e for e in baseline['entries']}
    results = []
    for partial in (False, True):
        root = output / ('synthetic-partial' if partial else 'synthetic-complete')
        objects = Objects(root)
        for fixture in prep['fixtures']:
            require(objects.put_snapshot(source.json(fixture['logical'])) == fixture['logical'], 'synthetic retained native state')
        sources = {name: objects.put(source.get(ref)) for name, ref in baseline['sources'].items()}
        capture = {'kind': 'synthetic-test-input', 'data_class': 'synthetic test input',
                   'synthetic_inputs': 'All command outcomes and metrics invented from frozen expectations; not native observations',
                   'protocol_sha256': baseline['protocol_sha256'], 'preparation': objects.put(canonical(prep)),
                   'sources': sources, 'schedule_sha256': baseline['schedule_sha256'], 'entries': [],
                   'seed_after': baseline['seed_after'], 'stop_reason': 'timeout' if partial else None,
                   'host': {'kind': 'synthetic test input; no host sampling performed'},
                   'measured_phase_start_ns': 1_000_008_000_000_000,
                   'measured_phase_deadline_ns': 1_001_808_000_000_000}
        for row in frozen[:83 if partial else 480]:
            entry = copy.deepcopy(operations[row['fixture'], row['operation']])
            entry.update(row)
            command = entry['command']
            start = 1_000_000_000_000_000 + row['ordinal']*100_000_000
            wall = 1_000_000 + row['ordinal'] % 3
            censored = partial and row['ordinal'] == 82
            if censored:
                wall = 10_000_000_002
            end, pid = start+wall, 10000+row['ordinal']
            deadline = start+10_000_000_000
            phase_deadline = None if row['phase'] == 'warmup' else capture['measured_phase_deadline_ns']
            command.update({'phase': row['phase'], 'pid': pid, 'start_ns': start, 'end_ns': end, 'wall_ns': wall,
                            'start_utc': '2000-01-01T00:00:00+00:00', 'end_utc': '2000-01-01T00:00:00+00:00',
                            'user_seconds': .000001, 'system_seconds': .000002, 'rss_kib': 1024,
                            'command_deadline_ns': deadline, 'phase_deadline_ns': phase_deadline,
                            'termination_grace_ns': 1_000_000_000, 'termination_delay_ns': None,
                            'censor_reason': 'timeout' if censored else None,
                            'censor_event_ns': deadline if censored else None,
                            'detected_ns': end-1 if censored else None,
                            'detection_delay_ns': 1 if censored else None,
                            'deadline_overshoot_ns': max(0, end-deadline)})
            fixture = fixtures[row['fixture']]
            stdout = (encode(source_records(0, fixture['E'])['declaration']) if row['operation'] == 'declaration-get'
                      else canonical({'source': 'fixture/startup/00', 'collection_state': 'active',
                                      'observations': 2, 'active_items': 2, 'needs_recovery': False}))
            command.update({'exit': 0, 'exit_code': 0, 'signal': None,
                            'stdout_hex': stdout.hex(), 'stderr_hex': '', 'stdin_hex': ''})
            for stream in ('stdin', 'stdout', 'stderr'):
                command[stream+'_sha256'] = sha(bytes.fromhex(command[stream+'_hex']))
            command['monitor'] = {
                'mechanism': 'pidfd/select.poll/wait4', 'wait4_calls': 1, 'wait4_pid': pid,
                'wait4_options': 0, 'pidfd_target_pid': pid, 'pidfd': 3,
                'readiness_ns': end-1, 'reap_ns': end, 'signals': [], 'interruptions': [],
                'polls': [{'start_ns': start, 'end_ns': end-1, 'requested_ms': 1, 'ready': True,
                           'events': [[3, 1]], 'overshoot_ns': max(0, wall-1-1_000_000)}],
                'storage': [{'at_ns': start, 'bytes': 1024}],
                'deadlines': [{'edge': 'before', 'at_ns': start, 'command_due': False, 'phase_due': False},
                              {'edge': 'after', 'at_ns': end-1, 'command_due': censored, 'phase_due': False}]}
            entry['command'] = objects.put(canonical(command))
            capture['entries'].append(entry)
        capture['measured_phase_end_ns'] = end+1
        capture['remainder'] = [{'ordinal': row['ordinal'], 'status': 'NOT RUN', 'reason': capture['stop_reason']}
                                for row in frozen[len(capture['entries']):]]
        save(root / 'capture.json', capture)
        save(root / 'schedule.json', frozen)
        if partial:
            forged = copy.deepcopy(capture['entries'][-1])
            command = objects.json(forged['command'])
            for field in ('censor_reason', 'censor_event_ns', 'detected_ns', 'detection_delay_ns'):
                command[field] = None
            forged['command'] = objects.put(canonical(command))
            forgery = {'data_class': 'synthetic test input', 'entry': forged}
        else:
            forged = copy.deepcopy(capture)
            forged['measured_phase_end_ns'] = forged['measured_phase_deadline_ns']+1
            forgery = {'data_class': 'synthetic test input', 'capture': forged}
        save(root / 'forgery.json', forgery)
        analyze.summarize(root, root / 'report')
        with (root / 'report/summary.csv').open() as stream:
            summaries = list(csv.DictReader(stream))
        require(len(summaries) == 40 and all(r['data_class'] == 'synthetic test input' for r in summaries), 'synthetic report labels/coverage')
        require(sum(int(r['n']) for r in summaries) == (2 if partial else 400), 'synthetic successful sample totals')
        require(sum(int(r['censored']) for r in summaries) == int(partial), 'synthetic censor total')
        require(sum(int(r['NOT RUN']) for r in summaries) == (397 if partial else 0), 'synthetic incomplete suffix total')
        results.append({'name': root.name, 'kind': 'synthetic test input', 'analysis': 'PASS'})
    save(output / 'synthetic-analysis.json', results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--smoke', type=Path)
    args = parser.parse_args()
    import signal
    from run import operator_interrupt
    signal.signal(signal.SIGTERM, operator_interrupt)
    from prepare import verify_prepared
    prep = verify_prepared(args.prepared)
    require(not args.output.exists(), 'controls output exists')
    args.output.mkdir(parents=True)
    baseline = args.output / 'baseline'
    if args.smoke is None:
        from run import smoke as native_smoke
        from argparse import Namespace
        native_smoke(Namespace(prepared=args.prepared, output=baseline), prep)
        smoke = baseline
    else:
        smoke = args.smoke
    original = analyze.verify(smoke)
    require(canonical(Objects(smoke).json(original['preparation'])) == canonical(prep), 'smoke preparation binding')
    results = replay_mutations(smoke, args.output, prep)
    if smoke != baseline:
        baseline.mkdir()
        shutil.copy2(smoke / 'capture.json', baseline / 'capture.json')
        shutil.copy2(smoke / 'schedule.json', baseline / 'schedule.json')
        shutil.copytree(smoke / 'objects', baseline / 'objects', copy_function=os.link)
    fixture = prep['fixtures'][0]
    real = args.output / 'real-controls'
    (real / 'bin').mkdir(parents=True)
    (real / 'home').mkdir()
    (real / 'tmp').mkdir()
    shutil.copy2(Path(sys.executable).resolve(), real / 'bin/control-python')
    (real / 'trial').mkdir()
    shutil.copy2(args.prepared / 'bin/mousa', real / 'bin/mousa-real')
    objects = Objects(args.output)
    native_receipts = []
    save(args.output / 'control-fixture.json', fixture)
    def retain_native(row):
        native_receipts.append(row)
        save(args.output / 'native-controls.json', native_receipts)
        save(args.output / 'controls.json', results)
    def reset():
        shutil.rmtree(real / 'trial')
        (real / 'trial').mkdir()
        shutil.copy2(args.prepared / fixture['seed_path'], real / 'trial/store.sqlite')
    wrapper = real / 'bin/mousa'
    wrapper.write_text('''#!./bin/control-python
import sqlite3
import subprocess
import sys

result = subprocess.run(["./bin/mousa-real", *sys.argv[1:]], capture_output=True)
if result.returncode == 0:
    connection = sqlite3.connect("trial/store.sqlite")
    try:
        connection.execute("CREATE TABLE forbidden_control(v)")
        connection.execute("INSERT INTO forbidden_control VALUES (7)")
        connection.commit()
    finally:
        connection.close()
sys.stdout.buffer.write(result.stdout)
sys.stderr.buffer.write(result.stderr)
sys.exit(result.returncode)
''')
    wrapper.chmod(0o755)
    reset()
    db = real / 'trial/store.sqlite'
    before_physical, before = physical(db), snapshot(db)
    actual = child(argv_for('declaration-get', fixture['declarations'][0]['id']), real, ENV,
                   storage=accounted_storage(args.prepared.parent, real))
    after_physical, after = physical(db), snapshot(db)
    entry = {'ordinal': 0, 'phase': 'control', 'fixture': fixture['key'], 'operation': 'declaration-get', 'seed_identity': fixture['seed_identity'],
             'before': objects.put_snapshot(before), 'after': objects.put_snapshot(after), 'before_physical': before_physical, 'after_physical': after_physical, 'command': actual}
    entry['control_wrapper'] = objects.put(wrapper.read_bytes())
    entry['native_binary_identity'] = file_identity(real / 'bin/mousa-real')
    entry['control_python_identity'] = file_identity(real / 'bin/control-python')
    save(args.output / 'forbidden-write.json', entry)
    try:
        analyze.check_entry(entry, fixture, objects)
    except ValueError as error:
        require(str(error) == 'logical/schema mutation', 'forbidden write detector: '+str(error))
        results.append({'name': 'real wrapper extra-table-and-row write', 'observed': str(error), 'kind': 'unmeasured-control'})
    else:
        raise ValueError('real forbidden write accepted')
    wrapper.unlink()
    shutil.copy2(args.prepared / 'bin/mousa', wrapper)
    reset()
    before_physical, before = physical(db), snapshot(db)
    actual = child(argv_for('declaration-get', fixture['declarations'][0]['id']), real, ENV,
                   storage=accounted_storage(args.prepared.parent, real))
    raw = bytearray(db.read_bytes())
    counter = (int.from_bytes(raw[24:28], 'big')+1) % (2**32)
    raw[24:28] = raw[92:96] = counter.to_bytes(4, 'big')
    db.write_bytes(raw)
    after_physical, after = physical(db), snapshot(db)
    require(canonical(before) == canonical(after), 'physical-only control changed logical state')
    entry = {'ordinal': 0, 'phase': 'control', 'fixture': fixture['key'], 'operation': 'declaration-get',
             'seed_identity': fixture['seed_identity'], 'command': actual,
             'before': objects.put_snapshot(before), 'after': objects.put_snapshot(after),
             'before_physical': before_physical, 'after_physical': after_physical,
             'control_injection': 'After native exit, increment main header counters at offsets24 and92; no logical change'}
    save(args.output / 'main-file-write.json', entry)
    try:
        analyze.check_entry(entry, fixture, objects)
    except ValueError as error:
        require(str(error) == 'read-only main-file mutation', 'physical-only detector: '+str(error))
        results.append({'name': 'real main-file-only mutation', 'observed': str(error), 'kind': 'unmeasured-control'})
    else:
        raise ValueError('main-file mutation accepted')
    reset()
    with closing(sqlite3.connect(db)) as connection, connection:
        require(connection.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal', 'reader control WAL setup')
        connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    before_physical, before = physical(db), snapshot(db)
    reader = sqlite3.connect(db.resolve().as_uri()+'?mode=ro', uri=True)
    denial = None
    try:
        reader.execute('PRAGMA query_only=ON')
        reader.execute('BEGIN')
        source_count = reader.execute('SELECT count(*) FROM sources').fetchone()[0]
        during = physical(db)
        try:
            reader.execute('CREATE TABLE denied_reader_control(value)')
        except sqlite3.OperationalError as error:
            denial = {'class': type(error).__name__, 'message': str(error),
                      'sqlite_errorcode': getattr(error, 'sqlite_errorcode', None)}
    finally:
        reader.close()
    after_physical, after = physical(db), snapshot(db)
    save(args.output / 'reader-sidecars.json', {
        'kind': 'unmeasured-control; synthetic disposable WAL fixture',
        'setup': ['PRAGMA journal_mode=WAL', 'PRAGMA wal_checkpoint(TRUNCATE)'],
        'connection': 'mode=ro; PRAGMA query_only=ON; no immutable mode',
        'source_count': source_count, 'denied_write': denial,
        'before': objects.put_snapshot(before), 'after': objects.put_snapshot(after),
        'before_physical': before_physical, 'during_physical': during, 'after_physical': after_physical})
    require(denial is not None and source_count == 1 and canonical(before) == canonical(after), 'read-only SQLite control')
    require(before_physical['main'] == during['main'] == after_physical['main'], 'reader main invariant')
    require(during['-wal'] is not None and during['-shm'] is not None, 'reader sidecars observed')
    for operation in ('declaration-get', 'status'):
        reset()
        with closing(sqlite3.connect(db)) as connection, connection:
            connection.execute('PRAGMA application_id=7')
        damaged = snapshot(db)
        before_physical = physical(db)
        actual = child(argv_for(operation, fixture['declarations'][0]['id']), real, ENV,
                       storage=accounted_storage(args.prepared.parent, real))
        after = snapshot(db)
        failed = {'ordinal': 0, 'phase': 'control', 'fixture': fixture['key'], 'operation': operation,
                  'seed_identity': fixture['seed_identity'], 'command': actual,
                  'before': objects.put_snapshot(damaged), 'after': objects.put_snapshot(after),
                  'before_physical': before_physical, 'after_physical': physical(db)}
        retain_native({'kind': 'startup-schema control', **failed})
        require(actual['exit'] != 0 and actual['stdout_hex'] == '' and actual['stderr_hex'] and canonical(after) == canonical(damaged), 'startup schema refusal/repair')
        forged = copy.deepcopy(failed)
        forged['command'].update({'exit': 0, 'exit_code': 0, 'signal': None, 'passed': True})
        save(args.output / ('forged-success-'+operation+'.json'), forged)
        try:
            analyze.check_entry(forged, fixture, objects)
        except ValueError as error:
            require(str(error) == 'current schema header', 'rewritten failure detector: '+str(error))
            results.append({'name': 'failure exit rewritten to success '+operation, 'observed': str(error), 'kind': 'unmeasured-control'})
        else:
            raise ValueError('rewritten failure accepted')
    for name, limits in [('deadline', {'command_seconds': .1, 'grace_seconds': .1}), ('phase', {'command_seconds': 10, 'grace_seconds': .1})]:
        phase = time.monotonic_ns()+100_000_000 if name == 'phase' else None
        actual = child([sys.executable, '-c', 'import time; time.sleep(60)'], real, ENV, control_limits=limits, phase_deadline_ns=phase)
        retain_native({'kind': name+' control', 'command': actual})
        require(actual['censor_reason'] == ('timeout' if name == 'deadline' else 'phase') and actual['exit'] != 0, name+' cancellation')
        analyze.check_monitor(actual, control=True)
    usage_calls = 0
    def growing_workspace():
        nonlocal usage_calls
        usage_calls += 1
        return 0 if usage_calls == 1 else 2147483648
    actual = child([sys.executable, '-c', 'import time; time.sleep(60)'], real, ENV,
                   storage=growing_workspace, control_limits={'grace_seconds': .1})
    retain_native({'kind': 'injected storage control', 'command': actual})
    require(actual['censor_reason'] == 'storage' and actual['exit'] != 0, 'storage cancellation')
    analyze.check_monitor(actual, control=True)
    actual = child([sys.executable, '-c', 'import os,signal,time; time.sleep(.05); os.kill(os.getppid(),signal.SIGINT); time.sleep(60)'],
                   real, ENV, control_limits={'grace_seconds': .1})
    retain_native({'kind': 'parent interruption control', 'command': actual})
    require(actual['censor_reason'] == 'interruption' and actual['exit'] != 0, 'interruption cancellation')
    analyze.check_monitor(actual, control=True)
    actual = child([sys.executable, '-c', 'import time; time.sleep(.05); print(time.monotonic_ns())'], real, ENV, control_poll_ms=1000)
    retain_native({'kind': '1000ms readiness control; mechanism only, not product performance', 'command': actual})
    poll = actual['monitor']['polls'][0]
    exit_marker = int(bytes.fromhex(actual['stdout_hex']))
    require(actual['exit'] == 0 and poll['start_ns'] < exit_marker <= poll['end_ns']
            and poll['end_ns']-poll['start_ns'] < 900_000_000, 'pidfd readiness wakeup')
    analyze.check_monitor(actual, control=True)
    synthetic_analysis(smoke, args.output)
    save(args.output / 'controls.json', results)
    analyze.verify_controls(args.output)
    print('PASS:', len(results), 'replay/write controls;', len(native_receipts), 'native/child controls; measured collection NOT RUN')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
