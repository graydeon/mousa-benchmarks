#!/usr/bin/env python3
"""Replay retained raw states/streams; unmeasured inputs never produce performance summaries."""
import argparse
import csv
from pathlib import Path
import statistics
import sys

from common import (Objects, PRODUCT, PROTOCOL_SHA, TREE, canonical, json_frames, loads,
                    read_json, require, save, sha, validate_physical, validate_snapshot)


def check_monitor(command, control=False):
    monitor = command['monitor']
    require(monitor['mechanism'] == 'pidfd/select.poll/wait4', 'wait mechanism')
    require(type(monitor['wait4_calls']) is int and monitor['wait4_calls'] == 1, 'exact-child wait4 count')
    require(all(type(monitor[field]) is int for field in ('pidfd_target_pid', 'wait4_pid', 'readiness_ns', 'reap_ns')),
            'monitor identity/timestamp types')
    require(type(command['pid']) is int and command['pid'] > 0 and monitor['pidfd_target_pid'] == command['pid']
            and monitor['wait4_pid'] == command['pid'] and type(monitor['wait4_options']) is int
            and monitor['wait4_options'] == 0, 'exact-child wait target/options')
    require(type(monitor['pidfd']) is int and monitor['pidfd'] >= 0, 'pidfd descriptor')
    start, end = command['start_ns'], command['end_ns']
    require(type(start) is int and type(end) is int and end >= start, 'monotonic endpoints')
    require(all(command[field] is None or type(command[field]) is int for field in
                ('exit_code', 'signal', 'command_deadline_ns', 'phase_deadline_ns', 'termination_delay_ns', 'deadline_overshoot_ns')),
            'exit/signal/deadline types')
    require(type(command['termination_grace_ns']) is int and command['termination_grace_ns'] >= 0, 'termination grace type')
    require(type(command['wall_ns']) is int and command['wall_ns'] == end-start, 'wall boundary')
    require(monitor['reap_ns'] == end and monitor['readiness_ns'] <= end, 'reap boundary')
    require(command['command_deadline_ns'] == start + 10_000_000_000 or control, 'command deadline')
    require(type(command['exit']) is int, 'exit type')
    require(command['exit_code'] == (command['exit'] if command['exit'] >= 0 else None)
            and command['signal'] == (-command['exit'] if command['exit'] < 0 else None), 'exit/signal consistency')
    for stream in ('stdin', 'stdout', 'stderr'):
        raw = bytes.fromhex(command[stream+'_hex'])
        require(raw.hex() == command[stream+'_hex'] and sha(raw) == command[stream+'_sha256'], 'stream identity')
    require(control or command['termination_grace_ns'] == 1_000_000_000, 'termination grace')
    require(type(command['rss_kib']) is int and command['rss_kib'] >= 0, 'RSS type/unit')
    for field in ('user_seconds', 'system_seconds'):
        require(type(command[field]) in (int, float) and command[field] >= 0, 'CPU type/unit')
    polls = monitor['polls']
    require(bool(polls) and len(monitor['deadlines']) == 2*len(polls), 'missing monitor records')
    previous = start
    for index, poll in enumerate(polls):
        require(type(poll['requested_ms']) is int and 0 <= poll['requested_ms'] <= (1000 if control else 1), 'poll cadence')
        require(all(type(poll[field]) is int for field in ('start_ns', 'end_ns', 'overshoot_ns')), 'poll timestamp types')
        require(previous <= poll['start_ns'] <= poll['end_ns'] <= end, 'poll time order')
        before, after = monitor['deadlines'][2*index:2*index+2]
        require(before['edge'] == 'before' and after['edge'] == 'after' and previous <= before['at_ns'] <= poll['start_ns'] and after['at_ns'] == poll['end_ns'], 'deadline check boundaries')
        for edge in (before, after):
            require(type(edge['at_ns']) is int, 'deadline timestamp type')
            deadline = command['command_deadline_ns']
            require(type(edge['command_due']) is bool and edge['command_due'] is (deadline is not None and edge['at_ns'] >= deadline), 'command deadline check')
            phase = command['phase_deadline_ns']
            require(type(edge['phase_due']) is bool and edge['phase_due'] is (phase is not None and edge['at_ns'] >= phase), 'phase deadline check')
        require(not (before['command_due'] or before['phase_due']) or poll['requested_ms'] == 0, 'due poll timeout')
        require(type(poll['ready']) is bool and (not poll['ready'] or index == len(polls)-1), 'ready reap priority')
        require(poll['ready'] is bool(poll['events']) and all(
            len(event) == 2 and type(event[0]) is int and event[0] == monitor['pidfd']
            and type(event[1]) is int and event[1] & 1 for event in poll['events']), 'pidfd event binding')
        require(poll['overshoot_ns'] == max(0, poll['end_ns']-poll['start_ns']-poll['requested_ms']*1_000_000), 'poll overshoot')
        previous = poll['end_ns']
    require(polls[-1]['ready'] is True and monitor['readiness_ns'] == polls[-1]['end_ns'], 'pidfd readiness')
    require(monitor['storage'] or control, 'missing storage check')
    for check in monitor['storage']:
        require(type(check['at_ns']) is int, 'storage timestamp type')
        require(type(check['bytes']) is int and check['bytes'] >= 0 and check['at_ns'] <= end, 'storage record')
    checks = monitor['storage']
    if checks:
        require(checks[0]['at_ns'] <= start, 'pre-spawn storage check')
        index, due = 1, start+100_000_000
        for poll_index, poll in enumerate(polls):
            if not poll['ready'] and poll['end_ns'] >= due:
                require(index < len(checks), 'missing due storage check')
                check = checks[index]
                require(type(check['due_ns']) is int and type(check['delay_ns']) is int, 'storage deadline/delay types')
                following = polls[poll_index+1]['start_ns'] if poll_index+1 < len(polls) else end
                require(check['due_ns'] == due and poll['end_ns'] <= check['at_ns'] <= following
                        and check['delay_ns'] == check['at_ns']-due, 'storage cadence/delay')
                due, index = check['at_ns']+100_000_000, index+1
        require(index == len(checks), 'unscheduled storage check')
    for index, sent in enumerate(monitor['signals']):
        require(type(sent['signal']) is int and type(sent['at_ns']) is int, 'signal record types')
        require(sent['signal'] in (15, 9) and start <= sent['at_ns'] <= end, 'termination signal record')
        require(sent['signal'] == (15 if index == 0 else 9) and index < 2, 'TERM/KILL order')
        if index:
            require(sent['at_ns']-monitor['signals'][0]['at_ns'] >= command['termination_grace_ns'], 'TERM/KILL grace')
    require(command['termination_delay_ns'] == (None if not monitor['signals'] else end-monitor['signals'][0]['at_ns']), 'termination delay')
    deadline = command['command_deadline_ns']
    require(command['deadline_overshoot_ns'] == (None if deadline is None else max(0, end-deadline)), 'deadline overshoot')
    reason, event, detected = command['censor_reason'], command['censor_event_ns'], command['detected_ns']
    require(reason in (None, 'timeout', 'phase', 'storage', 'interruption', 'host'), 'censor classification')
    expired = [(value, label) for value, label in
               ((command['command_deadline_ns'], 'timeout'), (command['phase_deadline_ns'], 'phase'))
               if value is not None and end >= value]
    if expired:
        first, label = min(expired)
        require(reason is not None and type(event) is int and event <= first, 'missing deadline censor')
        if event == first:
            require(reason == label, 'earliest deadline classification')
    if reason is None:
        require(event is None and detected is None and not monitor['signals'], 'uncensored termination')
    else:
        require(type(event) is int and type(detected) is int and event <= end and detected >= event, 'censor timestamps')
        if reason in ('timeout', 'phase'):
            require(event == command['command_deadline_ns' if reason == 'timeout' else 'phase_deadline_ns'], 'censor deadline')
        elif reason == 'storage':
            require(any(check['bytes'] >= 2147483648-16777216 and check['at_ns'] == event for check in checks), 'storage censor evidence')
        elif reason == 'interruption':
            require(event in monitor['interruptions'], 'interruption censor evidence')
        else:
            require(monitor['host_event']['reason'] == 'host' and monitor['host_event']['at_ns'] == event, 'host censor evidence')
    if command['phase'] != 'preparation':
        require(command['detection_delay_ns'] == (None if detected is None else detected-event), 'detection delay')
    require(not command['descendants'], 'unexpected descendants')


def check_support(reference, objects):
    from common import ENV
    report = objects.json(reference)
    require(report['kind'] == 'unmeasured owned-child API preflight; not product performance'
            and type(report['product_invocations']) is int and report['product_invocations'] == 0
            and 'error_class' not in report, 'owned-child preflight receipt')
    command = objects.json(report['command'])
    check_monitor(command, control=True)
    require(command['phase'] == 'control' and len(command['argv']) == 3 and command['argv'][1:] == ['-c', 'pass']
            and command['cwd'] == '.' and canonical(command['environment']) == canonical(ENV), 'owned-child probe binding')
    require(command['exit'] == 0 and command['censor_reason'] is None
            and all(command[field+'_hex'] == '' for field in ('stdin', 'stdout', 'stderr')), 'owned-child probe failure')
    require(all(poll['requested_ms'] <= 1 for poll in command['monitor']['polls']), 'owned-child probe cadence')


def failure_kind(entry):
    command = entry['command']
    if command['descendants'] or 'after' not in entry:
        return 'infrastructure'
    if command['censor_reason']:
        return command['censor_reason']
    error = bytes.fromhex(command['stderr_hex'])
    if command['exit'] != 0 and (b'foreign SQLite application ID' in error or b'incompatible_schema' in error):
        return 'startup-schema'
    return 'correctness'


def _check_entry_binding(entry, fixture, objects):
    from prepare import fixture_gate, source_records
    from run import argv_for
    from common import ENV
    require(entry['fixture'] == fixture['key'], 'fixture binding')
    require(entry['seed_identity'] == fixture['seed_identity'], 'seed binding')
    command = entry['command']
    if set(command) == {'sha256', 'bytes'}:
        command = objects.json(command)
    require(command['phase'] == entry['phase'], 'invocation phase binding')
    expected = source_records(0, fixture['E'])['declaration']
    require(command['argv'] == argv_for(entry['operation'], expected['id']), 'argv binding')
    require(canonical(command['environment']) == canonical(ENV) and command['cwd'] == '.', 'execution environment')
    require(command['stdin_hex'] == '', 'stdin binding')
    check_monitor(command)
    validate_physical(entry['before_physical'])
    before = objects.json(entry['before'])
    validate_snapshot(before)
    fixture_gate(before, fixture['S'], fixture['E'], fixture['T'])
    require(entry['before']['sha256'] == fixture['logical']['sha256'], 'fixture initial logical state')
    require(entry['before_physical']['main'] == fixture['seed_identity'], 'initial main-file identity')
    return command, expected, before


def _check_failed_entry(entry, fixture, objects):
    _check_entry_binding(entry, fixture, objects)
    if 'after' in entry:
        validate_snapshot(objects.json(entry['after']))
    if 'after_physical' in entry:
        validate_physical(entry['after_physical'])


def check_invariance(operation, before, after, before_physical, after_physical):
    require(canonical(before) == canonical(after), 'logical/schema mutation')
    if operation == 'declaration-get':
        require(before_physical['main'] == after_physical['main'], 'read-only main-file mutation')


def check_entry(entry, fixture, objects):
    from prepare import encode
    command, expected, before = _check_entry_binding(entry, fixture, objects)
    require('after' in entry and 'after_physical' in entry, 'post-state unavailable; failed attempt retained')
    validate_physical(entry['after_physical'])
    after = objects.json(entry['after'])
    validate_snapshot(after)
    check_invariance(entry['operation'], before, after, entry['before_physical'], entry['after_physical'])
    require(command['exit'] == 0 and not command['stderr_hex'] and not command['censor_reason'], 'raw command failure/censor')
    output = bytes.fromhex(command['stdout_hex'])
    if entry['operation'] == 'declaration-get':
        require(output == encode(expected), 'canonical declaration output')
    else:
        wanted = {'source': 'fixture/startup/00', 'collection_state': 'active', 'observations': 2, 'active_items': 2, 'needs_recovery': False}
        require(canonical(loads(output)) == canonical(wanted), 'status output/type')


def check_host(capture, objects):
    from run import concurrent_processes, idle_interval, new_throttling, suspension_observed
    host = capture['host']
    idle = host['idle_samples']
    require(type(host['idle_passed']) is bool and len(idle) <= 61, 'idle receipt shape')
    if not host['idle_passed']:
        require(not capture['entries'] and capture['stop_reason'] in ('host', 'interruption', 'infrastructure'), 'failed idle collection')
        return
    require(len(idle) == 61, 'idle coverage')
    for index, sample in enumerate(idle):
        require(not concurrent_processes(sample), 'idle concurrent workload')
        memory = dict(line.split(':', 1) for line in sample['counters']['meminfo'].splitlines())
        require(int(memory['MemAvailable'].split()[0])*1024 >= 2147483648, 'idle memory')
        if index:
            previous = idle[index-1]
            require(sample['at_ns']-previous['at_ns'] >= 1_000_000_000 and idle_interval(previous, sample)
                    and not suspension_observed(previous, sample), 'idle interval')
    if 'sampler' not in host:
        require(not any(e['phase'] == 'measured' for e in capture['entries']), 'missing host sampler')
        return
    sampler = host['sampler']
    raw = objects.get(sampler['raw'])
    samples, frame_error = json_frames(raw)
    require(canonical(frame_error) == canonical(sampler['frame_error']), 'sampler frame error binding')
    require(frame_error is None or (sampler['failure'] is not None and capture['stop_reason'] is not None), 'sampler frame falsely successful')
    require(canonical(samples) == canonical(host['samples']) == canonical(sampler['samples']), 'raw host sampling binding')
    require(samples or capture['stop_reason'] == 'host', 'empty host sampler')
    previous = None
    for index, sample in enumerate(samples):
        require(type(sample.get('sequence')) is int and sample['sequence'] == index, 'host sequence coverage')
        require(type(sample.get('terminal')) is bool and (not sample['terminal'] or index == len(samples)-1),
                'host terminal sample')
        require(sample['kind'] == 'host sampling' and sample['requested_interval_ns'] == 1_000_000_000, 'host cadence')
        require(sample['sampling_start_ns'] <= sample['at_ns'] <= sample['sampling_end_ns']
                and sample['sampling_overhead_ns'] == sample['sampling_end_ns']-sample['sampling_start_ns'], 'host overhead')
        require(sample['contention'] is (False if previous is None else not idle_interval(previous, sample)), 'host contention flag')
        require(sample['new_throttling'] == ([] if previous is None else new_throttling(previous, sample)), 'host throttling flag')
        require(sample['concurrent_workload'] == concurrent_processes(sample, previous), 'host workload flag')
        require(sample['suspension'] is (False if previous is None else suspension_observed(previous, sample)), 'host suspension flag')
        inventory = sample['process_inventory']
        require(sample['collector_stopped'] is any(p['pid'] == inventory['owner_pid'] and p['state'] in ('T', 't') for p in inventory['processes']), 'collector suspension flag')
        require(sample['window_start_ns'] == (sample['at_ns'] if previous is None else previous['at_ns']), 'host window binding')
        if previous:
            require(sample['at_ns'] > previous['at_ns'], 'host sample order')
        must_stop = sample['suspension'] or sample['collector_stopped'] or sample['concurrent_workload'] or (previous and sample['at_ns']-previous['at_ns'] > 2_000_000_000)
        require(not must_stop or capture['stop_reason'] is not None, 'host failure falsely successful')
        previous = sample
    require((sampler['failure'] is None and sampler['exit'] == 0) or capture['stop_reason'] is not None, 'sampler failure falsely successful')
    fields = ('start_ns', 'shutdown_ns', 'end_ns')
    require(all(type(sampler.get(field)) is int for field in fields), 'sampler lifetime provenance')
    start, shutdown, end = (sampler[field] for field in fields)
    phase_start, phase_end = capture['measured_phase_start_ns'], capture['measured_phase_end_ns']
    require(phase_start <= start <= shutdown <= end <= phase_end, 'sampler phase lifetime')
    require(all(start <= s['sampling_start_ns'] <= s['sampling_end_ns'] <= end for s in samples),
            'sampler sample lifetime')
    measured = [e['command'] for e in capture['entries'] if e['phase'] == 'measured']
    require(all(start <= c['start_ns'] <= c['end_ns'] <= shutdown for c in measured), 'command sampler lifetime')
    complete = (bool(samples) and samples[0]['sampling_start_ns']-phase_start <= 2_000_000_000
                and samples[-1]['terminal'] and samples[-1]['sampling_start_ns'] >= shutdown
                and phase_end-samples[-1]['sampling_end_ns'] <= 2_000_000_000
                and all(b['at_ns']-a['at_ns'] <= 2_000_000_000 for a, b in zip(samples, samples[1:])))
    if not complete:
        require(capture['stop_reason'] is not None
                and sampler['failure'] is not None, 'incomplete host coverage falsely successful')


def check_preparation(root):
    """Deep public replay includes native preparation streams and retained states."""
    from common import ENV
    from prepare import encode, source_records
    objects = Objects(root)
    capture = read_json(Path(root) / 'capture.json')
    prep = objects.json(capture['preparation'])
    if 'pidfd_preflight' in prep:
        check_support(prep['pidfd_preflight'], objects)
    for reference in [*prep['sources'].values(), *prep['module_files'].values(),
                      prep['module_list'], prep['binary_buildinfo']]:
        objects.get(reference)
    require(prep['go_version'] == 'go version go1.27.1 linux/amd64', 'preparation toolchain')
    build = objects.json(capture['build_receipts']['build.json'])
    modules = objects.json(capture['build_receipts']['module-verification.json'])
    require(build['exit'] == 0 and modules['exit'] == 0, 'build/module verification failure')
    require(build['argv'][:5] == ['go', 'build', '-trimpath', '-buildvcs=false', '-o']
            and len(build['argv']) == 7 and build['argv'][-1] == './cmd/mousa', 'build command')
    require(canonical(build['environment']) == canonical(prep['build_environment']), 'build environment binding')
    target = {'GOWORK': 'off', 'CGO_ENABLED': '0', 'GOOS': 'linux', 'GOARCH': 'amd64', 'GOAMD64': 'v1'}
    require(all(build['environment'].get(k) == v for k, v in target.items()), 'build target')
    def expected_calls():
        for s in (1, 8):
            for e in (0, 1, 17, 65, 257):
                for index in range(s):
                    records = source_records(index, e)
                    payload = b''.join(encode({'id': item, 'text': pin['text']}) for item, pin in records['pins'].items())
                    sync = {'source': records['label'], 'input': 'jsonl', 'segment_policy': 'fixed-v1',
                            'added': ['predecessor', 'successor'], 'total_items': 2}
                    yield ['sync', '--source', records['label'], '--segment-policy', 'fixed-v1'], payload, sync, 0, index == 0
                    yield ['supersession', 'declaration', 'put'], encode(records['declaration']), encode(records['declaration']), 0, False
                    for event in records['events']:
                        yield ['supersession', 'activation', 'put'], encode(event), encode(event), 0, False
                for t in (0, 1):
                    if t:
                        for index in range(s):
                            records = source_records(index, e)
                            wanted = {'decision_outcome': 'allow', 'matched_candidates': 2, 'supersession_excluded': 1 if e else 0}
                            yield ['query', '--source', records['label'], '--policy', 'original', '--packing-policy', 'original', '--budget-bytes', '8192', '--supersession', 'amber'], b'', wanted, 0, False
                    for index in range(s):
                        records = source_records(index, e)
                        yield ['supersession', 'declaration', 'get', records['declaration']['id']], b'', encode(records['declaration']), 0, False
                        status = {'source': records['label'], 'collection_state': 'active', 'observations': 2, 'active_items': 2, 'needs_recovery': False}
                        yield ['status', '--source', records['label']], b'', status, 0, False
                        state = b'' if not e else {'source_id': records['source_id'], 'current_activation_id': records['events'][-1]['id'], 'active_declaration_id': records['declaration']['id']}
                        yield ['supersession', 'activation', 'state', records['source_id']], b'', state, 0 if e else 1, False
    expected = list(expected_calls())
    require(len(capture['preparation_invocations']) == len(expected), 'preparation invocation coverage')
    if 'reused_prefix' in prep:
        reuse = prep['reused_prefix']
        count = reuse['native_invocations']
        require(type(count) is int and 0 < count <= len(expected), 'reused prefix count')
        require(canonical(reuse['invocations']) == canonical(capture['preparation_invocations'][:count]),
                'reused prefix raw receipt binding')
        prior = objects.json(reuse['preparation'])
        require(prior['product_commit'] == PRODUCT and prior['product_tree'] == TREE
                and prior['protocol_sha256'] == PROTOCOL_SHA and prior['binary_identity'] == prep['binary_identity'],
                'reused prefix pins')
        for reference in prior['sources'].values():
            objects.get(reference)
        for index, reference in enumerate(reuse.get('unreused_invocations', []), count):
            failure = objects.json(reference)
            require(type(failure['ordinal']) is int and failure['ordinal'] == index
                    and failure['phase'] == failure['command']['phase'] == 'preparation', 'unreused prefix receipt order')
            check_monitor(failure['command'], control=True)
            for field in ('before', 'after'):
                if field in failure:
                    state = objects.json(failure[field])
                    if state is not None:
                        validate_snapshot(state)
        if 'original_failure' in reuse:
            objects.json(reuse['original_failure'])
        require(reuse['logical'] == objects.json(reuse['invocations'][-1])['after'], 'reused continuation state binding')
        require(type(prep['new_native_invocations']) is int
                and prep['new_native_invocations'] == len(expected)-count, 'new preparation count')
        originals = {fixture['key']: fixture for fixture in prior['fixtures']}
        for fixture in prep['fixtures']:
            if type(fixture['derivation']) is dict:
                derivation = fixture['derivation']
                old = originals[fixture['key']]
                require(derivation['kind'] == 'coherent native fixture reuse'
                        and derivation['preparation'] == reuse['preparation']
                        and derivation['source_fixture'] == fixture['key']
                        and derivation['source_seed_identity'] == old['seed_identity']
                        and fixture['logical'] == old['logical'], 'reused fixture derivation')
    previous, seen = None, set()
    for ordinal, (reference, wanted) in enumerate(zip(capture['preparation_invocations'], expected)):
        row = objects.json(reference)
        argv, stdin, stdout, exit_code, reset = wanted
        command = row['command']
        require(type(row['ordinal']) is int and row['ordinal'] == ordinal and row['phase'] == command['phase'] == 'preparation', 'preparation ordinal/phase')
        check_monitor(command, control=True)
        require(all(p['requested_ms'] <= 1 for p in command['monitor']['polls']), 'preparation poll cadence')
        require(command['argv'] == ['./bin/mousa', '-store', 'trial/store.sqlite', *argv]
                and command['stdin_hex'] == stdin.hex() and canonical(command['environment']) == canonical(ENV)
                and command['cwd'] == '.', 'preparation argv/input')
        validate_physical(row['before_physical'], missing_main=reset)
        validate_physical(row['after_physical'])
        require(command['exit'] == exit_code and command['censor_reason'] is None, 'preparation raw failure')
        output, error = bytes.fromhex(command['stdout_hex']), bytes.fromhex(command['stderr_hex'])
        require(not error if exit_code == 0 else b'not_found' in error, 'preparation stderr')
        if isinstance(stdout, bytes):
            require(output == stdout, 'preparation canonical output')
        else:
            value = loads(output)
            selected = {key: value[key] for key in stdout}
            require(canonical(selected) == canonical(stdout), 'preparation typed output')
            if argv[0] not in ('sync', 'query'):
                require(set(value) == set(stdout), 'preparation output fields')
        require(objects.json(row['before']) is None if reset else row['before'] == previous, 'native preparation continuity')
        for field in ('before', 'after'):
            reference = row[field]
            if reference['sha256'] not in seen:
                state = objects.json(reference)
                if state is not None:
                    validate_snapshot(state)
                seen.add(reference['sha256'])
        previous = row['after']


def check_phase(capture):
    fields = ('measured_phase_start_ns', 'measured_phase_deadline_ns', 'measured_phase_end_ns')
    measured = [e for e in capture['entries'] if e['phase'] == 'measured']
    started = measured or any(capture.get(field) is not None for field in fields) or 'sampler' in capture.get('host', {})
    if not started:
        return
    require(all(type(capture.get(field)) is int for field in fields), 'measured phase provenance')
    start, deadline, end = (capture[field] for field in fields)
    require(0 <= start <= end and deadline == start+1800_000_000_000, 'measured phase cap/endpoints')
    require(end < deadline or capture['stop_reason'] is not None, 'phase cap falsely successful')
    for entry in capture['entries']:
        command = entry['command']
        if entry['phase'] == 'measured':
            require(type(command['start_ns']) is int and type(command['end_ns']) is int
                    and start <= command['start_ns'] <= command['end_ns'] <= end
                    and type(command['phase_deadline_ns']) is int
                    and command['phase_deadline_ns'] == deadline, 'measured command phase binding')
            monitor = command['monitor']
            timestamps = [s['at_ns'] for s in monitor['storage']] + monitor['interruptions']
            timestamps += [s['at_ns'] for s in monitor['signals']]
            timestamps += [d['at_ns'] for d in monitor['deadlines']]
            timestamps += [p[field] for p in monitor['polls'] for field in ('start_ns', 'end_ns')]
            timestamps += [monitor['readiness_ns'], monitor['reap_ns']]
            require(all(type(t) is int and start <= t <= end for t in timestamps), 'monitor phase binding')
        else:
            require(command['end_ns'] <= start, 'warmup phase overlap')


def verify(root):
    from prepare import fixture_gate
    from run import schedule
    root = Path(root)
    objects = Objects(root)
    capture = read_json(root / 'capture.json')
    require(capture['protocol_sha256'] == PROTOCOL_SHA, 'protocol identity')
    prep = objects.json(capture['preparation'])
    require(prep['product_commit'] == PRODUCT and prep['product_tree'] == TREE and prep['protocol_sha256'] == PROTOCOL_SHA, 'product/protocol pins')
    fixtures = {f['key']: f for f in prep['fixtures']}
    expected_keys = {f's{s}-e{e}-t{t}' for s in (1, 8) for e in (0, 1, 17, 65, 257) for t in (0, 1)}
    require(set(fixtures) == expected_keys and len(prep['fixtures']) == 20, 'fixture coverage')
    for key, fixture in fixtures.items():
        require(key == f"s{fixture['S']}-e{fixture['E']}-t{fixture['T']}", 'fixture label/cardinality')
        validate_physical(fixture['physical'])
        require(fixture['physical']['main'] == fixture['seed_identity'], 'fixture physical identity')
        state = objects.json(fixture['logical'])
        validate_snapshot(state)
        counts = fixture_gate(state, fixture['S'], fixture['E'], fixture['T'])
        require(canonical(fixture['counts']) == canonical(counts), 'prepared cardinality metadata')
    frozen = schedule(prep)
    require(canonical(read_json(root / 'schedule.json')) == canonical(frozen), 'frozen schedule/order')
    require(capture['schedule_sha256'] == sha(canonical(frozen) + b'\n'), 'schedule hash')
    for ref in capture['sources'].values():
        objects.get(ref)
    if capture['kind'] != 'synthetic-test-input':
        check_support(capture['pidfd_preflight'], objects)
    entries = capture['entries']
    for entry in entries:
        require(set(entry['command']) == {'sha256', 'bytes'}, 'raw command reference')
        entry['command'] = objects.json(entry['command'])
    if capture['kind'] == 'unmeasured-smoke':
        require(capture['collection'] == 'NOT RUN', 'smoke classification')
        expected = [(f['key'], op) for f in prep['fixtures'] for op in ('declaration-get', 'status')]
        suffix = [{'ordinal': ordinal, 'fixture': key, 'operation': op, 'status': 'NOT RUN'}
                  for ordinal, (key, op) in enumerate(expected) if ordinal >= len(entries)]
        require(0 < len(entries) <= 40 and canonical(capture['smoke_remainder']) == canonical(suffix), 'smoke coverage')
        failed = False
        for ordinal, (entry, (key, op)) in enumerate(zip(entries, expected)):
            require(type(entry['ordinal']) is int and entry['ordinal'] == ordinal and entry['phase'] == 'smoke' and entry['fixture'] == key and entry['operation'] == op, 'smoke ordinal/order')
            try:
                check_entry(entry, fixtures[key], objects)
            except ValueError:
                if ordinal != len(entries)-1 or 'failure' not in capture:
                    raise
                _check_failed_entry(entry, fixtures[key], objects)
                failed = True
        require(failed is ('failure' in capture) and (failed or len(entries) == 40), 'smoke outcome classification')
        require(canonical(capture['remainder']) == canonical([{'ordinal': e['ordinal'], 'status': 'NOT RUN', 'reason': 'unmeasured smoke only'} for e in frozen]), 'explicit NOT RUN schedule')
    else:
        require(capture['kind'] in ('measured', 'synthetic-test-input'), 'capture kind')
        synthetic = capture['kind'] == 'synthetic-test-input'
        require(not synthetic or capture['data_class'] == 'synthetic test input', 'synthetic input label')
        require(synthetic or capture['data_class'] == 'measured', 'measured data label')
        require(capture['stop_reason'] is None or (type(capture['stop_reason']) is str and capture['stop_reason'] in
                ('timeout', 'phase', 'storage', 'interruption', 'host', 'correctness', 'startup-schema', 'infrastructure')), 'stop reason type/class')
        require(len(entries) == 480 or capture['stop_reason'] is not None, 'incomplete capture falsely successful')
        require(len(entries) <= 480, 'too many entries')
        check_phase(capture)
        failed = False
        for ordinal, entry in enumerate(entries):
            scheduled = frozen[ordinal]
            require(not failed, 'attempt continued after failure')
            require(entry['command']['phase_deadline_ns'] == (None if entry['phase'] == 'warmup' else capture['measured_phase_deadline_ns']), 'phase deadline binding')
            for field in scheduled:
                require(canonical(entry[field]) == canonical(scheduled[field]), 'schedule entry binding: ' + field)
            try:
                check_entry(entry, fixtures[entry['fixture']], objects)
            except ValueError:
                _check_failed_entry(entry, fixtures[entry['fixture']], objects)
                failed = True
                require(capture['stop_reason'] == failure_kind(entry), 'failed entry classification')
        require(canonical(capture['remainder']) == canonical([{'ordinal': e['ordinal'], 'status': 'NOT RUN', 'reason': capture['stop_reason']} for e in frozen[len(entries):]]), 'explicit incomplete suffix')
        require(failed is bool(capture['stop_reason']) or (not failed and capture['stop_reason'] in ('phase', 'storage', 'interruption', 'host', 'infrastructure')), 'false success/stop classification')
        if synthetic:
            require(capture['host'] == {'kind': 'synthetic test input; no host sampling performed'}, 'synthetic host label')
        else:
            check_host(capture, objects)
    require(set(capture['seed_after']) == set(fixtures), 'seed-after coverage')
    for key, fixture in fixtures.items():
        observed = capture['seed_after'][key]
        validate_physical(observed['physical'])
        require(observed['physical']['main'] == observed['identity'], 'seed physical identity')
        require(observed['identity'] == fixture['seed_identity'], 'seed main mutation')
        require(observed['logical']['sha256'] == fixture['logical']['sha256'], 'seed logical mutation')
        state = objects.json(observed['logical'])
        validate_snapshot(state)
        fixture_gate(state, fixture['S'], fixture['E'], fixture['T'])
    return capture


def summarize(root, output):
    capture = verify(root)
    require(capture['kind'] in ('measured', 'synthetic-test-input'), 'unmeasured smoke/control input: no performance summaries')
    data_class = capture.get('data_class', 'measured')
    require(data_class in ('measured', 'synthetic test input'), 'analysis data class')
    output = Path(output)
    require(not output.exists(), 'report exists')
    output.mkdir(parents=True)
    objects = Objects(root)
    prep = objects.json(capture['preparation'])
    fixtures = {f['key']: f for f in prep['fixtures']}

    def csv_file(name, fields, rows):
        with (output / name).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    observations = []
    for entry in capture['entries']:
        command = entry['command']
        fixture = fixtures[entry['fixture']]
        failure = ''
        try:
            check_entry(entry, fixture, objects)
        except ValueError as error:
            failure = str(error)
        reason = command['censor_reason']
        threshold = ''
        if reason == 'timeout':
            threshold = 10_000_000_000
        elif reason == 'phase':
            threshold = max(0, command['phase_deadline_ns']-command['start_ns'])
        elif reason:
            threshold = max(0, command['censor_event_ns']-command['start_ns'])
        flags = [sample['at_ns'] for sample in capture['host'].get('samples', [])
                 if (sample.get('contention') or sample.get('new_throttling'))
                 and sample['window_start_ns'] <= command['end_ns'] and sample['at_ns'] >= command['start_ns']]
        observations.append({
            'data_class': data_class, **{k: entry[k] for k in ('ordinal', 'phase', 'fixture', 'operation', 'round')},
            **{k: fixture[k] for k in ('S', 'E', 'T')},
            **{k: command[k] for k in ('start_ns', 'end_ns', 'wall_ns', 'user_seconds', 'system_seconds', 'rss_kib', 'exit', 'censor_reason')},
            'success': not failure, 'failure': failure, 'censor_threshold_ns': threshold,
            'contention_flags': canonical(flags).decode()})
    fields = ['data_class', 'ordinal', 'phase', 'fixture', 'S', 'E', 'T', 'operation', 'round',
              'start_ns', 'end_ns', 'wall_ns', 'user_seconds', 'system_seconds', 'rss_kib',
              'exit', 'success', 'failure', 'censor_reason', 'censor_threshold_ns', 'contention_flags']
    rows = [r for r in observations if r['phase'] == 'measured']
    csv_file('samples.csv', fields, rows)
    coverage, summaries = [], []
    for fixture in fixtures:
        for operation in ('declaration-get', 'status'):
            for phase, expected in [('warmup', 2), ('measured', 10)]:
                samples = [r for r in observations if r['fixture'] == fixture and r['operation'] == operation and r['phase'] == phase]
                successes = [r for r in samples if r['success']]
                cover = {'data_class': data_class, 'fixture': fixture, 'operation': operation, 'phase': phase,
                         'expected': expected, 'attempted': len(samples), 'success': len(successes),
                         'censored': sum(bool(r['censor_reason']) for r in samples),
                         'failure': sum(not r['success'] and not r['censor_reason'] for r in samples),
                         'NOT RUN': expected-len(samples)}
                coverage.append(cover)
                if phase == 'warmup':
                    continue
                summary = {**cover, 'n': len(successes), 'complete': len(successes) == expected}
                for metric in ('wall_ns', 'user_seconds', 'system_seconds', 'rss_kib'):
                    values = [r[metric] for r in successes]
                    for name, fn in [('min', min), ('median', statistics.median), ('max', max)]:
                        summary[metric+'_'+name] = fn(values) if values else ''
                summaries.append(summary)
    csv_file('coverage.csv', list(coverage[0]), coverage)
    csv_file('summary.csv', list(summaries[0]), summaries)
    fixture_rows = []
    for fixture in fixtures.values():
        state = objects.json(fixture['logical'])
        attempted = [entry for entry in capture['entries'] if entry['fixture'] == fixture['key']]
        row = {'data_class': data_class, 'fixture': fixture['key'],
               'snapshot_sha256': fixture['seed_identity']['sha256'], 'logical_sha256': fixture['logical']['sha256']}
        for table in ('sources', 'local_items', 'representations', 'supersession_declarations',
                      'supersession_activations', 'supersession_activation_state',
                      'source_trails', 'source_trail_candidates', 'policy_decisions'):
            row[table] = state['tables'][table]['count']
        for sidecar, identity in fixture['physical'].items():
            row[sidecar+'_bytes'] = identity['bytes'] if identity is not None else 'absent'
        for name, differs in [
            ('main_changed', lambda e: e['before_physical']['main'] != e.get('after_physical', {}).get('main')),
            ('logical_changed', lambda e: e['before'] != e.get('after')),
            ('sidecar_changed', lambda e: any(e['before_physical'][k] != e.get('after_physical', {}).get(k) for k in ('-wal', '-shm', '-journal'))),
        ]:
            row[name+'_ordinals'] = canonical([e['ordinal'] for e in attempted if differs(e)]).decode()
        fixture_rows.append(row)
    csv_file('fixtures.csv', list(fixture_rows[0]), fixture_rows)
    for filename, metrics in [('observations.svg', ['wall_ns']), ('resources.svg', ['user_seconds', 'system_seconds', 'rss_kib'])]:
        panels = [(s, t, op, metric) for metric in metrics for s in (1, 8) for t in (0, 1) for op in ('declaration-get', 'status')]
        height = 35+210*((len(panels)+2)//3)
        name = filename[:-4]
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {height}" role="img" aria-labelledby="{name}-title {name}-description">',
               f'<title id="{name}-title">{data_class}: individual command observations</title>',
               f'<desc id="{name}-description">Facets separate source counts, trail states, operations and units. Crosses mark censored commands; resources retain actual values through reap. Non-censored correctness failures are excluded; see coverage.csv.</desc>',
               f'<text x="10" y="18" fill="currentColor" font-size="13">{data_class}; crosses denote censoring; resources through reap</text>']
        for panel, (s, t, operation, metric) in enumerate(panels):
            x0, y0 = (panel % 3)*320, 30+(panel//3)*210
            svg.append(f'<text x="{x0+5}" y="{y0+15}" fill="currentColor" font-size="12">S={s} T={t} {operation} {metric}</text>')
            samples = [r for r in rows if r['S'] == s and r['T'] == t and r['operation'] == operation
                       and (r['success'] or r['censor_reason'])]
            def ordinate(sample):
                if metric == 'wall_ns' and sample['censor_reason']:
                    return sample['censor_threshold_ns']
                return sample[metric]
            maximum = max([ordinate(r) for r in samples] or [1]) or 1
            svg.append(f'<text x="{x0+5}" y="{y0+32}" fill="currentColor" font-size="10">0 to {maximum:g}; events per source</text>')
            svg.append(f'<path d="M{x0+25} {y0+40}V{y0+175}H{x0+305}" stroke="currentColor" fill="none"/>')
            for event in (0, 1, 17, 65, 257):
                x = x0+30+event/257*270
                # 0 and 1 share a tick label rather than overlapping text.
                if event != 1:
                    label = '0/1' if event == 0 else str(event)
                    svg.append(f'<text x="{x}" y="{y0+190}" fill="currentColor" font-size="10">{label}</text>')
            for sample in samples:
                x, y = x0+30+sample['E']/257*270, y0+170-ordinate(sample)/maximum*125
                if sample['censor_reason']:
                    svg.append(f'<path d="M{x-3} {y-3}l6 6m-6 0l6 -6" stroke="currentColor"/>')
                else:
                    svg.append(f'<circle cx="{x}" cy="{y}" r="2" fill="currentColor"/>')
        svg.append('</svg>')
        (output / filename).write_text('\n'.join(svg)+'\n', encoding='utf-8')


def verify_controls(root):
    import tempfile
    import copy
    import os
    import shutil
    from controls import replay_mutations
    root = Path(root)
    baseline = verify(root / 'baseline')
    prep = Objects(root / 'baseline').json(baseline['preparation'])
    fixture = read_json(root / 'control-fixture.json')
    require(canonical(fixture) == canonical(prep['fixtures'][0]), 'control fixture binding')
    objects = Objects(root)
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        results = replay_mutations(root / 'baseline', Path(temporary), prep)
    require(canonical(results) == canonical(read_json(root / 'mutations.json')), 'mutation replay conclusions')
    for filename, name, detector in [
        ('forbidden-write.json', 'real wrapper extra-table-and-row write', 'logical/schema mutation'),
        ('main-file-write.json', 'real main-file-only mutation', 'read-only main-file mutation'),
    ]:
        entry = read_json(root / filename)
        before, after = objects.json(entry['before']), objects.json(entry['after'])
        validate_snapshot(before)
        validate_snapshot(after)
        if filename == 'forbidden-write.json':
            objects.get(entry['control_wrapper'])
            require(entry['native_binary_identity'] == prep['binary_identity'], 'wrapper product binary identity')
            require('forbidden_control' not in before['tables'] and after['tables']['forbidden_control']['rows'] == [[['integer', '7']]], 'actual forbidden table/row')
        else:
            require(canonical(before) == canonical(after), 'main-only control logical state')
        try:
            check_entry(entry, fixture, objects)
        except ValueError as error:
            require(str(error) == detector, 'native control detector')
        else:
            raise ValueError('native control falsely accepted')
        results.append({'name': name, 'observed': detector, 'kind': 'unmeasured-control'})
    reader = read_json(root / 'reader-sidecars.json')
    before, after = objects.json(reader['before']), objects.json(reader['after'])
    for field in ('before_physical', 'during_physical', 'after_physical'):
        validate_physical(reader[field])
    validate_snapshot(before)
    validate_snapshot(after)
    require(canonical(before) == canonical(after) and reader['source_count'] == 1, 'reader logical invariant')
    require(reader['before_physical']['main'] == reader['during_physical']['main'] == reader['after_physical']['main'], 'reader main invariant')
    require(reader['during_physical']['-wal'] is not None and reader['during_physical']['-shm'] is not None, 'reader sidecar observation')
    denial = reader['denied_write']
    require(denial['class'] == 'OperationalError' and 'readonly' in denial['message'].lower()
            and (denial['sqlite_errorcode'] is None or type(denial['sqlite_errorcode']) is int and denial['sqlite_errorcode'] == 8),
            'reader forbidden-write refusal')
    native = read_json(root / 'native-controls.json')
    require(len(native) == 7, 'native control coverage')
    schema_operations = []
    other = []
    for record in native:
        command, kind = record['command'], record['kind']
        check_monitor(command, control=True)
        if kind == 'startup-schema control':
            operation = record['operation']
            schema_operations.append(operation)
            before, after = objects.json(record['before']), objects.json(record['after'])
            require(before['application_id'] == 7 and canonical(before) == canonical(after), 'schema refusal repair/state')
            require(command['exit'] > 0 and command['stdout_hex'] == '' and b'foreign SQLite application ID' in bytes.fromhex(command['stderr_hex']), 'native startup-schema refusal')
            forged = read_json(root / ('forged-success-'+operation+'.json'))
            require(forged['command']['exit'] == 0 and forged['command']['passed'] is True, 'forged success injection')
            require(forged['command']['stdout_hex'] == command['stdout_hex'] and forged['command']['stderr_hex'] == command['stderr_hex'], 'forged raw failure streams')
            try:
                check_entry(forged, fixture, objects)
            except ValueError as error:
                require(str(error) == 'current schema header', 'forged success detector')
            else:
                raise ValueError('forged success accepted')
            results.append({'name': 'failure exit rewritten to success '+operation, 'observed': 'current schema header', 'kind': 'unmeasured-control'})
        elif kind.startswith('1000ms readiness'):
            other.append('readiness')
            poll = command['monitor']['polls'][0]
            require(command['exit'] == 0 and poll['requested_ms'] == 1000 and poll['end_ns']-poll['start_ns'] < 900_000_000, 'control readiness wakeup')
            marker = int(bytes.fromhex(command['stdout_hex']))
            require(poll['start_ns'] < marker <= poll['end_ns'], 'readiness spans actual child exit marker')
        else:
            reason = {'deadline control': 'timeout', 'phase control': 'phase',
                      'injected storage control': 'storage', 'parent interruption control': 'interruption'}[kind]
            other.append(reason)
            require(command['censor_reason'] == reason and command['exit'] != 0, 'cancellation classification')
            require(all(p['requested_ms'] <= 1 for p in command['monitor']['polls']), 'non-readiness control cadence')
            require(command['monitor']['signals'] and command['monitor']['signals'][0]['signal'] == 15, 'cancellation TERM/reap')
    require(sorted(schema_operations) == ['declaration-get', 'status'], 'startup-schema operation coverage')
    require(set(other) == {'readiness', 'timeout', 'phase', 'storage', 'interruption'}, 'cancellation/readiness coverage')
    require(canonical(results) == canonical(read_json(root / 'controls.json')), 'control conclusions')
    for name, successful, censored, missing in [('synthetic-complete', 400, 0, 0), ('synthetic-partial', 2, 1, 397)]:
        synthetic = verify(root / name)
        require(synthetic['kind'] == 'synthetic-test-input', 'synthetic replay label')
        with (root / name / 'report/summary.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        require(len(rows) == 40 and all(row['data_class'] == 'synthetic test input' for row in rows), 'synthetic report labels')
        require(sum(int(row['n']) for row in rows) == successful
                and sum(int(row['censored']) for row in rows) == censored
                and sum(int(row['NOT RUN']) for row in rows) == missing, 'synthetic report coverage')
        for row in rows:
            samples = [entry for entry in synthetic['entries'] if entry['phase'] == 'measured'
                       and entry['fixture'] == row['fixture'] and entry['operation'] == row['operation']
                       and entry['command']['censor_reason'] is None]
            require(int(row['n']) == len(samples), 'synthetic cell sample count')
            for metric in ('wall_ns', 'user_seconds', 'system_seconds', 'rss_kib'):
                values = [entry['command'][metric] for entry in samples]
                for statistic, function in [('min', min), ('median', statistics.median), ('max', max)]:
                    actual = row[metric+'_'+statistic]
                    require(float(actual) == function(values) if values else actual == '', 'synthetic descriptive statistic')
        forgery = read_json(root / name / 'forgery.json')
        require(forgery['data_class'] == 'synthetic test input', 'synthetic forgery label')
        if censored:
            forged = forgery['entry']
            original = synthetic['entries'][-1]
            require(canonical({k: v for k, v in forged.items() if k != 'command'}) ==
                    canonical({k: v for k, v in original.items() if k != 'command'}), 'censor forgery raw state binding')
            case_objects = Objects(root / name)
            expected = copy.deepcopy(original['command'])
            for field in ('censor_reason', 'censor_event_ns', 'detected_ns', 'detection_delay_ns'):
                expected[field] = None
            require(canonical(case_objects.json(forged['command'])) == canonical(expected), 'censor flags-only injection')
            try:
                check_entry(forged, next(f for f in prep['fixtures'] if f['key'] == forged['fixture']), case_objects)
            except ValueError as error:
                require(str(error) == 'missing deadline censor', 'independent censor detector')
            else:
                raise ValueError('deadline censor removal accepted')
        else:
            expected = read_json(root / name / 'capture.json')
            expected['measured_phase_end_ns'] = expected['measured_phase_deadline_ns']+1
            require(canonical(forgery['capture']) == canonical(expected), 'phase-end-only injection')
            with tempfile.TemporaryDirectory(dir=root) as temporary:
                target = Path(temporary)
                shutil.copytree(root / name / 'objects', target / 'objects', copy_function=os.link)
                shutil.copy2(root / name / 'schedule.json', target / 'schedule.json')
                save(target / 'capture.json', forgery['capture'])
                try:
                    verify(target)
                except ValueError as error:
                    require(str(error) == 'phase cap falsely successful', 'independent phase-cap detector')
                else:
                    raise ValueError('phase-cap false success accepted')
    return {'kind': 'unmeasured-controls', 'entries': native}


def verify_evidence(root):
    root = Path(root)
    if (root / 'capture.json').exists():
        result = verify(root)
        if result['kind'] != 'synthetic-test-input':
            check_preparation(root)
    else:
        result = verify_controls(root)
        check_preparation(root / 'baseline')
    return result


def pack_evidence(root, output):
    # Complete raw provenance currently has no approved public-safe representation.
    # Refuse before creating an archive rather than silently rewriting execution.
    raise ValueError('public export blocked: complete raw provenance requires a reviewed public-safe representation')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['verify', 'summarize', 'pack', 'unpack'])
    parser.add_argument('capture', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.mode != 'verify' and args.output is None:
        parser.error('--output is required for '+args.mode)
    if args.mode == 'verify':
        result = verify_evidence(args.capture)
        outcome = '; native attempt FAILED as retained' if result['kind'] == 'unmeasured-smoke' and 'failure' in result else ''
        print('PASS replay:', result['kind'], len(result['entries']), 'raw entries'+outcome+'; measured collection', 'NOT RUN' if result['kind'] != 'measured' else 'partial/complete per coverage')
    elif args.mode == 'summarize':
        summarize(args.capture, args.output)
    elif args.mode == 'pack':
        pack_evidence(args.capture, args.output)
    else:
        from common import unpack
        unpack(args.capture, args.output)
        verify_evidence(args.output)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
