#!/usr/bin/env python3
"""Direct-child startup execution. Smoke/control observations are not performance data."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import select
import shutil
import signal
import sqlite3
import sys
import time

from common import (BUDGET, ENV, HERE, Objects, RESERVE, canonical, file_identity, json_frames, loads,
                    physical, preflight, protocol, read_json, require, save, sha,
                    snapshot, workspace_bytes)


def utc():
    return datetime.now(timezone.utc).isoformat()


def schedule(prep=None):
    entries = []
    for phase, rounds in [('warmup', 2), ('measured', 10)]:
        for rnd in range(rounds):
            cells = []
            for s in (1, 8):
                for e in (0, 1, 17, 65, 257):
                    for t in (0, 1):
                        for operation in ('declaration-get', 'status'):
                            key = f'mousa-startup-v1|{phase}|{rnd}|{s}|{e}|{t}|{operation}'
                            cells.append((sha(key.encode()), key, s, e, t, operation))
            for digest, key, s, e, t, operation in sorted(cells):
                entries.append({'ordinal': len(entries), 'phase': phase, 'round': rnd, 'S': s, 'E': e, 'T': t,
                                'fixture': f's{s}-e{e}-t{t}', 'operation': operation, 'order_key': key, 'order_sha256': digest})
    if prep is not None:
        from prepare import encode, source_records
        fixtures = {f['key']: f for f in prep['fixtures']}
        for row in entries:
            fixture = fixtures[row['fixture']]
            declaration = source_records(0, row['E'])['declaration']
            expected = encode(declaration) if row['operation'] == 'declaration-get' else canonical({
                'source': 'fixture/startup/00', 'collection_state': 'active', 'observations': 2,
                'active_items': 2, 'needs_recovery': False})
            row.update({'argv': argv_for(row['operation'], declaration['id']), 'stdin_sha256': sha(b''),
                        'seed_identity': fixture['seed_identity'], 'expected_output_sha256': sha(expected)})
    return entries


class BeforeSpawn(ValueError):
    def __init__(self, reason, at_ns, storage_bytes=None):
        self.reason = reason
        self.observation = {'at_ns': at_ns, 'storage_bytes': storage_bytes}
        super().__init__(reason+' before spawn')


def child(argv, cwd, env, payload=b'', phase_deadline_ns=None, storage=None,
          control_poll_ms=None, control_limits=None, phase='control', cancel_reason=None):
    """Own one fork/exec child, its pidfd, output descriptors and exactly one reap."""
    preflight()
    require(phase in ('control', 'preparation', 'smoke', 'warmup', 'measured'), 'invocation phase')
    require(control_limits is None or phase in ('control', 'preparation'), 'injected limits outside controls/preparation')
    require(control_poll_ms is None or phase == 'control', 'long readiness wait outside named control')
    limits = {'command_seconds': 10, 'grace_seconds': 1}
    if control_limits is not None:
        limits.update(control_limits)
    requested = 1 if control_poll_ms is None else control_poll_ms
    cwd = Path(cwd)
    cwd.mkdir(parents=True, exist_ok=True)
    paths = [cwd / name for name in ('stdin.raw', 'stdout.raw', 'stderr.raw')]
    paths[0].write_bytes(payload)
    monitor = {'mechanism': 'pidfd/select.poll/wait4', 'wait4_calls': 0, 'polls': [], 'deadlines': [], 'storage': [], 'signals': []}
    started_utc = utc()
    if storage is not None:
        used = storage()
        monitor['storage'].append({'at_ns': time.monotonic_ns(), 'bytes': used})
        if used >= BUDGET-RESERVE:
            raise BeforeSpawn('storage', time.monotonic_ns(), used)
    fds = []
    try:
        for path, flags in zip(paths, (os.O_RDONLY, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, os.O_CREAT | os.O_TRUNC | os.O_WRONLY)):
            fds.append(os.open(path, flags, 0o600))
    except BaseException:
        for descriptor in fds:
            os.close(descriptor)
        raise
    interrupted = []
    def on_interrupt(signum, frame):
        interrupted.append(time.monotonic_ns())
    old_interrupt = signal.signal(signal.SIGINT, on_interrupt)
    old_terminate = signal.signal(signal.SIGTERM, on_interrupt)
    try:
        checked = time.monotonic_ns()
        if phase == 'measured' and phase_deadline_ns is not None and checked >= phase_deadline_ns:
            raise BeforeSpawn('phase', checked)
        cancellation = None if cancel_reason is None else cancel_reason()
        if cancellation is not None:
            raise BeforeSpawn(cancellation['reason'], cancellation['at_ns'])
        if interrupted:
            raise BeforeSpawn('interruption', interrupted[0])
        start = time.monotonic_ns()
        pid = os.fork()
    except BaseException:
        for descriptor in fds:
            os.close(descriptor)
        signal.signal(signal.SIGINT, old_interrupt)
        signal.signal(signal.SIGTERM, old_terminate)
        raise
    if pid == 0:
        try:
            os.setsid()
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            os.chdir(cwd)
            for target, fd in enumerate(fds):
                os.dup2(fd, target)
            for fd in fds:
                if fd > 2:
                    os.close(fd)
            os.execve(argv[0], argv, env)
        except BaseException as error:
            os.write(2, ('exec failure: ' + str(error)).encode())
            os._exit(127)
    for fd in fds:
        os.close(fd)
    deadline = None if limits['command_seconds'] is None else start + int(limits['command_seconds'] * 1e9)
    deadlines = sorted((value, label) for value, label in ((deadline, 'timeout'), (phase_deadline_ns, 'phase')) if value is not None)
    first_deadline = deadlines[0] if deadlines else None
    reason, detected, term_at, killed = None, None, None, False
    censor_event = None
    monitor['interruptions'] = interrupted
    def note_event(label, event_ns, detected_ns):
        nonlocal reason, detected, censor_event
        if censor_event is None or event_ns < censor_event:
            reason, detected, censor_event = label, detected_ns, event_ns
    reaped = False
    fd = None
    def terminate(sig):
        at = time.monotonic_ns()
        try:
            os.killpg(pid, sig)
        except ProcessLookupError:
            # setsid may not have run yet; the exact child still belongs to us.
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        monitor['signals'].append({'signal': int(sig), 'at_ns': at})
        return at
    try:
        fd = os.pidfd_open(pid)
        monitor['pidfd_target_pid'] = pid
        monitor['pidfd'] = fd
        poll = select.poll()
        poll.register(fd, select.POLLIN)
        next_storage = start + 100_000_000
        while True:
            before = time.monotonic_ns()
            due = (deadline is not None and before >= deadline) or (phase_deadline_ns is not None and before >= phase_deadline_ns)
            if first_deadline is not None and before >= first_deadline[0]:
                note_event(first_deadline[1], first_deadline[0], before)
            monitor['deadlines'].append({'edge': 'before', 'at_ns': before, 'command_due': deadline is not None and before >= deadline,
                                         'phase_due': phase_deadline_ns is not None and before >= phase_deadline_ns})
            timeout = 0 if due else requested
            poll_start = time.monotonic_ns()
            ready = poll.poll(timeout)
            poll_end = time.monotonic_ns()
            if interrupted:
                note_event('interruption', interrupted[0], interrupted[0])
            if first_deadline is not None and poll_end >= first_deadline[0]:
                note_event(first_deadline[1], first_deadline[0], poll_end)
            require(all(event_fd == fd and mask & select.POLLIN for event_fd, mask in ready), 'pidfd readiness event')
            monitor['polls'].append({'start_ns': poll_start, 'end_ns': poll_end, 'requested_ms': timeout,
                                     'ready': bool(ready), 'events': [list(event) for event in ready],
                                     'overshoot_ns': max(0, poll_end-poll_start-timeout*1_000_000)})
            monitor['deadlines'].append({'edge': 'after', 'at_ns': poll_end, 'command_due': deadline is not None and poll_end >= deadline,
                                         'phase_due': phase_deadline_ns is not None and poll_end >= phase_deadline_ns})
            if ready:
                monitor['readiness_ns'] = poll_end
                waited_pid, status, usage = os.wait4(pid, 0)
                end = time.monotonic_ns()
                monitor['wait4_calls'] += 1
                monitor['reap_ns'] = end
                monitor['wait4_pid'] = waited_pid
                monitor['wait4_options'] = 0
                reaped = True
                if first_deadline is not None and end >= first_deadline[0]:
                    note_event(first_deadline[1], first_deadline[0], end)
                if interrupted and interrupted[0] <= end:
                    note_event('interruption', interrupted[0], interrupted[0])
                cancellation = None if cancel_reason is None else cancel_reason()
                if cancellation is not None:
                    monitor['host_event'] = cancellation
                    if cancellation['at_ns'] <= end:
                        note_event(cancellation['reason'], cancellation['at_ns'], time.monotonic_ns())
                    else:
                        monitor['post_reap_cancel'] = cancellation['reason']
                break
            if cancel_reason is not None:
                cancellation = cancel_reason()
                if cancellation is not None:
                    monitor['host_event'] = cancellation
                    note_event(cancellation['reason'], cancellation['at_ns'], time.monotonic_ns())
            if storage is not None and poll_end >= next_storage:
                used = storage()
                at = time.monotonic_ns()
                monitor['storage'].append({'at_ns': at, 'due_ns': next_storage, 'delay_ns': max(0, at-next_storage), 'bytes': used})
                next_storage = at + 100_000_000
                if used >= BUDGET - RESERVE:
                    note_event('storage', at, at)
            if reason is not None and term_at is None:
                term_at = terminate(signal.SIGTERM)
            if term_at is not None and not killed and time.monotonic_ns() >= term_at + int(limits['grace_seconds'] * 1e9):
                terminate(signal.SIGKILL)
                killed = True
        # A direct executable should leave no process-group members behind.
        descendants = []
        for entry in Path('/proc').iterdir():
            if entry.name.isdigit():
                try:
                    if os.getpgid(int(entry.name)) == pid:
                        descendants.append(int(entry.name))
                except ProcessLookupError:
                    pass
        if descendants:
            terminate(signal.SIGKILL)
            monitor['invalid_reason'] = 'unexpected-descendants'
        streams = {name: path.read_bytes() for name, path in zip(('stdin', 'stdout', 'stderr'), paths)}
        exit_status = os.waitstatus_to_exitcode(status)
        return {'argv': argv, 'cwd': '.', 'environment': env, 'phase': phase,
                'pid': pid, 'start_utc': started_utc, 'end_utc': utc(), 'start_ns': start, 'end_ns': end, 'wall_ns': end-start,
                'command_deadline_ns': deadline, 'phase_deadline_ns': phase_deadline_ns,
                'exit': exit_status, 'exit_code': exit_status if exit_status >= 0 else None,
                'signal': -exit_status if exit_status < 0 else None, 'user_seconds': usage.ru_utime,
                'system_seconds': usage.ru_stime, 'rss_kib': usage.ru_maxrss, 'monitor': monitor,
                'censor_reason': reason, 'censor_event_ns': censor_event, 'detected_ns': detected,
                'detection_delay_ns': None if detected is None else detected-censor_event,
                'termination_grace_ns': int(limits['grace_seconds']*1e9),
                'termination_delay_ns': None if term_at is None else end-term_at,
                'deadline_overshoot_ns': None if deadline is None else max(0, end-deadline), 'descendants': descendants,
                **{name+'_hex': raw.hex() for name, raw in streams.items()},
                **{name+'_sha256': sha(raw) for name, raw in streams.items()}}
    finally:
        if not reaped:
            terminate(signal.SIGKILL)
            os.wait4(pid, 0)
        if fd is not None:
            os.close(fd)
        signal.signal(signal.SIGINT, old_interrupt)
        signal.signal(signal.SIGTERM, old_terminate)


def argv_for(operation, declaration):
    prefix = ['./bin/mousa', '-store', 'trial/store.sqlite']
    if operation == 'declaration-get':
        return prefix + ['supersession', 'declaration', 'get', declaration]
    return prefix + ['status', '--source', 'fixture/startup/00']


def process_inventory(owner):
    processes, missing = [], []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / 'stat').read_text()
            tail = raw.rsplit(')', 1)[1].split()
            processes.append({'pid': int(entry.name), 'ppid': int(tail[1]), 'comm': raw.split('(', 1)[1].rsplit(')', 1)[0],
                              'cpu_ticks': int(tail[11])+int(tail[12]), 'start_ticks': int(tail[19]), 'state': tail[0]})
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError:
            missing.append(int(entry.name))
    parents = {p['pid']: p['ppid'] for p in processes}
    ancestors, current = [], owner
    while current and current not in ancestors:
        ancestors.append(current)
        current = parents.get(current, 0)
    return {'owner_pid': owner, 'ancestors': ancestors, 'processes': processes, 'inaccessible': missing}


def concurrent_processes(current, previous=None):
    inventory = current['process_inventory']
    allowed = set(inventory['ancestors'])
    known = {'go', 'compile', 'link', 'gcc', 'cc1', 'rustc', 'cargo', 'python', 'python3',
             'pytest', 'node', 'bun', 'ollama', 'llama-server', 'vllm'}
    earlier = None if previous is None else {(p['pid'], p['start_ticks']) for p in previous['process_inventory']['processes']}
    return [p for p in inventory['processes']
            if p['pid'] not in allowed and p['ppid'] != inventory['owner_pid'] and p['ppid'] != 2
            and (p['comm'] in known or p['comm'].startswith(('mousa', 'python', 'pytest', 'llama', 'vllm'))
                 or (earlier is not None and (p['pid'], p['start_ticks']) not in earlier))]


def host_sample(owner=None):
    started = time.monotonic_ns()
    boot_before = time.monotonic_ns()
    boot = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    boot_after = time.monotonic_ns()
    counters = {}
    for name in ('stat', 'loadavg', 'meminfo', 'pressure/cpu', 'pressure/io'):
        path = Path('/proc') / name
        counters[name] = path.read_text() if path.exists() else None
    membership = Path('/proc/self/cgroup').read_text()
    mountinfo = Path('/proc/self/mountinfo').read_text()
    cgroups = {}
    for line in mountinfo.splitlines():
        left, right = line.split(' - ', 1)
        if right.split()[0] != 'cgroup2':
            continue
        fields = left.split()
        mount_root, mount_point = Path(fields[3]), Path(fields[4])
        relative = next((entry.split(':', 2)[2] for entry in membership.splitlines() if entry.startswith('0::')), None)
        if relative is None:
            continue
        try:
            require('..' not in Path(relative).parts, 'escaped cgroup namespace')
            path = mount_point / Path(relative).relative_to(mount_root)
        except ValueError:
            cgroups['unresolved'] = {'membership': relative, 'mount_root': str(mount_root)}
            continue
        while path == mount_point or mount_point in path.parents:
            values = {}
            for name in ('cpu.stat', 'cpu.pressure', 'io.pressure', 'memory.max', 'memory.high', 'cpu.max', 'io.max'):
                file = path / name
                values[name] = file.read_text() if file.exists() else None
            cgroups[str(path.relative_to(mount_point))] = values
            if path == mount_point:
                break
            path = path.parent
    sample = {'at_ns': time.monotonic_ns(), 'utc': utc(), 'counters': counters, 'cgroup_membership': membership,
              'cgroups': cgroups, 'process_inventory': process_inventory(owner or os.getpid())}
    sample['sampling_start_ns'] = started
    sample['sampling_end_ns'] = time.monotonic_ns()
    sample['sampling_overhead_ns'] = sample['sampling_end_ns']-started
    sample['boottime_offset_interval_ns'] = [boot-boot_after, boot-boot_before]
    return sample


def idle_interval(before, after):
    a = list(map(int, before['counters']['stat'].splitlines()[0].split()[1:9]))
    b = list(map(int, after['counters']['stat'].splitlines()[0].split()[1:9]))
    delta = [y-x for x, y in zip(a, b)]
    total = sum(delta)
    memory = dict(line.split(':', 1) for line in after['counters']['meminfo'].splitlines())
    return total > 0 and all(value >= 0 for value in delta) and (total-delta[3]-delta[4])/total < .10 and delta[7]/total < .01 and int(memory['MemAvailable'].split()[0])*1024 >= 2147483648


def suspension_observed(before, after):
    low, high = after['boottime_offset_interval_ns']
    old_low, old_high = before['boottime_offset_interval_ns']
    return low > old_high or high < old_low


def new_throttling(before, after):
    flags = []
    for level, counters in after['cgroups'].items():
        old = before['cgroups'].get(level, {}).get('cpu.stat')
        new = counters.get('cpu.stat')
        if old is None or new is None:
            continue
        a = dict(line.split() for line in old.splitlines())
        b = dict(line.split() for line in new.splitlines())
        if any(int(b.get(key, 0)) > int(a.get(key, 0)) for key in ('nr_throttled', 'throttled_usec')):
            flags.append(level)
    return flags


def start_sampler(work, control_interval_seconds=None):
    """A separate process avoids forking the native child from a threaded parent."""
    work = Path(work)
    interval = 1 if control_interval_seconds is None else control_interval_seconds
    output, failure = work / 'host.jsonl', work / 'host-stop.json'
    require(not output.exists() and not failure.exists(), 'sampler paths already exist')
    started = time.monotonic_ns()
    wake_read, wake_write = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
    owner = os.getpid()
    try:
        pid = os.fork()
    except BaseException:
        os.close(wake_read)
        os.close(wake_write)
        raise
    if pid == 0:
        stopping = []
        def stop(signum, frame):
            stopping.append(True)
            try:
                os.write(wake_write, b'x')
            except BlockingIOError:
                pass
        try:
            os.setsid()
            signal.signal(signal.SIGTERM, stop)
            signal.signal(signal.SIGINT, stop)
            wake = select.poll()
            wake.register(wake_read, select.POLLIN)
            previous = None
            next_sample = time.monotonic_ns()
            with output.open('xb', buffering=0) as stream:
                sequence = 0
                while True:
                    terminal = bool(stopping)
                    sample = host_sample(owner)
                    sample['kind'] = 'host sampling' if control_interval_seconds is None else 'synthetic test input'
                    sample['sequence'] = sequence
                    sample['terminal'] = terminal
                    sample['requested_interval_ns'] = int(interval*1e9)
                    sample['contention'] = False if previous is None else not idle_interval(previous, sample)
                    sample['new_throttling'] = [] if previous is None else new_throttling(previous, sample)
                    sample['concurrent_workload'] = concurrent_processes(sample, previous)
                    sample['window_start_ns'] = sample['at_ns'] if previous is None else previous['at_ns']
                    sample['suspension'] = False if previous is None else suspension_observed(previous, sample)
                    sample['collector_stopped'] = any(p['pid'] == owner and p['state'] in ('T', 't') for p in sample['process_inventory']['processes'])
                    raw = canonical(sample)+b'\n'
                    while raw:
                        written = stream.write(raw)
                        raw = raw[written:]
                    sequence += 1
                    if control_interval_seconds is None:
                        reason = None
                        if previous is not None and sample['at_ns']-previous['at_ns'] > 2_000_000_000:
                            reason = 'suspension or sampler delay'
                        if sample['suspension'] or sample['collector_stopped']:
                            reason = 'collector or system suspension'
                        if sample['concurrent_workload']:
                            reason = 'concurrent workload'
                        if reason:
                            save(failure, {'reason': reason, 'at_ns': time.monotonic_ns()})
                            break
                    if sample['terminal']:
                        break
                    previous = sample
                    next_sample += int(interval*1e9)
                    wake.poll(max(0, (next_sample-time.monotonic_ns()+999999)//1000000))
            os._exit(0)
        except BaseException as error:
            try:
                save(failure, {'reason': 'sampler failure: '+str(error), 'at_ns': time.monotonic_ns()})
            finally:
                os._exit(1)
    os.close(wake_read)
    os.close(wake_write)
    fd = None
    try:
        fd = os.pidfd_open(pid)
        poll = select.poll()
        poll.register(fd, select.POLLIN)
    except BaseException:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        deadline = time.monotonic_ns()+1_000_000_000
        reaped = False
        while time.monotonic_ns() < deadline:
            if os.wait4(pid, os.WNOHANG)[0] == pid:
                reaped = True
                break
            time.sleep(.001)
        if fd is not None:
            os.close(fd)
        save(failure, {'reason': 'sampler readiness setup failed', 'at_ns': time.monotonic_ns(),
                       'pid': pid, 'reaped': reaped})
        raise
    return {'pid': pid, 'pidfd': fd, 'poll': poll, 'output': output, 'failure': failure, 'start_ns': started}


def sampler_failed(sampler):
    return sampler['failure'].exists() or bool(sampler['poll'].poll(0))


def sampler_cancel_event(sampler):
    if sampler is None:
        return None
    if sampler['failure'].exists():
        failure = read_json(sampler['failure'])
        return {'reason': 'host', 'at_ns': failure['at_ns'], 'detail': failure['reason']}
    if sampler['poll'].poll(0):
        return {'reason': 'host', 'at_ns': time.monotonic_ns(), 'detail': 'sampler exited'}
    return None


def finish_sampler(sampler, objects):
    signals = []
    polls = []
    def ready(milliseconds):
        started = time.monotonic_ns()
        events = sampler['poll'].poll(milliseconds)
        polls.append({'start_ns': started, 'end_ns': time.monotonic_ns(),
                      'requested_ms': milliseconds, 'events': events})
        return bool(events)
    def terminate(sig):
        at = time.monotonic_ns()
        try:
            os.kill(sampler['pid'], sig)
            sent = True
        except ProcessLookupError:
            sent = False
        signals.append({'signal': signal.Signals(sig).name, 'at_ns': at, 'sent': sent})
    interruptions = []
    def interrupted(signum, frame):
        interruptions.append({'signal': signum, 'at_ns': time.monotonic_ns()})
    old_handlers = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGINT, signal.SIGTERM)}
    already_exited = False
    shutdown = time.monotonic_ns()
    forced = False
    status = usage = None
    cleanup_failure = None
    try:
        already_exited = ready(0)
        if not already_exited:
            terminate(signal.SIGTERM)
            grace = signals[-1]['at_ns']+1_000_000_000
            while not ready(max(0, min(100, (grace-time.monotonic_ns()+999999)//1000000))):
                if time.monotonic_ns() >= grace:
                    forced = True
                    terminate(signal.SIGKILL)
                    break
            # A killed process can still await kernel I/O. Never enter blocking
            # wait4 without readiness; retain a local failure if the kernel stalls.
            if forced and not ready(1000):
                cleanup_failure = {'reason': 'sampler SIGKILL readiness deadline; child not yet reapable',
                                   'at_ns': time.monotonic_ns()}
        if cleanup_failure is None:
            pid, status, usage = os.wait4(sampler['pid'], 0)
            require(pid == sampler['pid'], 'sampler exact-child reap')
        end = time.monotonic_ns()
    finally:
        sampler['poll'].unregister(sampler['pidfd'])
        os.close(sampler['pidfd'])
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
    raw = sampler['output'].read_bytes() if sampler['output'].exists() else b''
    failure = read_json(sampler['failure']) if sampler['failure'].exists() else None
    failure = failure or cleanup_failure
    if interruptions:
        failure = failure or {'reason': 'sampler cleanup interrupted', 'at_ns': interruptions[0]['at_ns']}
    if forced or already_exited:
        failure = failure or {'reason': 'sampler forced termination' if forced else 'sampler exited before shutdown',
                              'at_ns': shutdown}
    report = {'pid': sampler['pid'], 'start_ns': sampler['start_ns'], 'end_ns': end,
              'shutdown_ns': shutdown, 'signals': signals, 'polls': polls, 'wait4_calls': int(status is not None),
              'interruptions': interruptions, 'reaped': status is not None,
              'exit': None if status is None else os.waitstatus_to_exitcode(status),
              'user_seconds': None if usage is None else usage.ru_utime,
              'system_seconds': None if usage is None else usage.ru_stime,
              'rss_kib': None if usage is None else usage.ru_maxrss, 'raw': objects.put(raw), 'failure': failure}
    report['samples'], report['frame_error'] = json_frames(raw)
    if report['frame_error'] is not None:
        report['failure'] = failure or {'reason': 'invalid sampler frame', 'at_ns': time.monotonic_ns()}
    save(objects.root / 'sampler-reap.json', report)
    return report


def observe_seeds(prepared, prep, objects):
    observations = {}
    for fixture in prep['fixtures']:
        path = Path(prepared) / fixture['seed_path']
        observations[fixture['key']] = {'identity': file_identity(path), 'physical': physical(path),
                                         'logical': objects.put_snapshot(snapshot(path))}
    return observations


def accounted_storage(root, live):
    fixed = workspace_bytes(root)-workspace_bytes(live)
    require(fixed >= 0, 'workspace accounting')
    return lambda: fixed+workspace_bytes(live)


def preflight_execution(work, objects, storage=None):
    """Probe owned-child pidfd/reaping before invoking any product command."""
    path = objects.root / 'pidfd-preflight.json'
    report = {'kind': 'unmeasured owned-child API preflight; not product performance', 'product_invocations': 0}
    try:
        actual = child([sys.executable, '-c', 'pass'], work, ENV, storage=storage)
        report['command'] = objects.put(canonical(actual))
        require(actual['exit'] == 0 and not actual['stdout_hex'] and not actual['stderr_hex']
                and actual['censor_reason'] is None, 'owned-child API preflight failed')
    except BaseException as error:
        report.update({'error_class': type(error).__name__, 'message': str(error)})
        save(path, report)
        raise
    save(path, report)
    return objects.put_file(path)


def retain_objects(prepared, destination):
    """Share immutable content-addressed members without rebuilding native states."""
    source = Path(prepared) / 'objects'
    require(not source.is_symlink() and source.is_dir(), 'preparation object directory')
    target = destination.root / 'objects'
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.iterdir()):
        require(not path.is_symlink() and path.is_file(), 'preparation object type')
        digest = path.name[:-4] if path.name.endswith('.ref') else path.name
        require(len(digest) == 64 and all(c in '0123456789abcdef' for c in digest), 'preparation object name')
        require(path.stat().st_size <= 33554432, 'preparation member exceeds 32 MiB')
        raw = path.read_bytes()
        if path.name.endswith('.ref'):
            descriptor = loads(raw)
            require(set(descriptor) == {'bytes', 'snapshot'} and type(descriptor['bytes']) is int, 'snapshot descriptor')
        else:
            require(sha(raw) == digest, 'preparation object identity')
        copied = target / path.name
        if copied.exists():
            require(file_identity(copied) == file_identity(path), 'object import collision')
        else:
            os.link(path, copied)


def capture(args, prep):
    """One non-resumable capture; this entry point is not invoked by smoke."""
    root = workspace_root(args.prepared, args.output)
    require(args.output.resolve().parent == root, 'capture must be a direct campaign directory')
    import subprocess
    import platform
    from prepare import git
    require(not git(HERE, 'status', '--porcelain=v1'), 'dirty runner source')
    public_head = git(HERE, 'rev-parse', 'HEAD')
    remote = subprocess.check_output(['git', 'ls-remote', 'https://github.com/graydeon/mousa-benchmarks.git', 'refs/heads/*']).decode()
    require(any(line.split()[0] == public_head for line in remote.splitlines()), 'runner must be a reviewed clean public revision')
    args.output.mkdir(parents=True)
    objects = Objects(args.output)
    retain_objects(args.prepared, objects)
    work = args.output / 'workspace'
    (work / 'bin').mkdir(parents=True)
    (work / 'home').mkdir()
    (work / 'tmp').mkdir()
    shutil.copy2(args.prepared / 'bin/mousa', work / 'bin/mousa')
    support = preflight_execution(work, objects, accounted_storage(root, work))
    frozen = schedule(prep)
    save(args.output / 'schedule.json', frozen)
    filesystem = os.statvfs(work)
    governors = {}
    for path in Path('/sys/devices/system/cpu').glob('cpu[0-9]*/cpufreq/scaling_governor'):
        try:
            value = path.read_text().strip()
        except OSError:
            value = None
        governors[str(path.relative_to('/sys/devices/system/cpu'))] = value
    receipt = {'kind': 'measured', 'data_class': 'measured', 'protocol_sha256': sha((HERE / 'protocol.json').read_bytes()),
               'pidfd_preflight': support,
               'runner_commit': public_head, 'runner_tree': git(HERE, 'rev-parse', 'HEAD^{tree}'),
               'preparation': objects.put(canonical(prep)), 'sources': {p.name: objects.put(p.read_bytes()) for p in HERE.glob('*.py')},
               'preparation_invocations': [objects.put_file(path) for path in sorted((args.prepared / 'invocations').glob('*.json.gz'))],
               'build_receipts': {name: objects.put_file(args.prepared / name) for name in ('build.json', 'module-verification.json')},
               'schedule_sha256': sha(canonical(frozen)+b'\n'), 'entries': [], 'stop_reason': None,
               'host': {'platform': platform.platform(), 'cpuinfo': Path('/proc/cpuinfo').read_text(),
                        'python': sys.version, 'sqlite': sqlite3.sqlite_version, 'cpu_count': os.cpu_count(),
                        'filesystem': {name: getattr(filesystem, name) for name in
                                       ('f_bsize', 'f_frsize', 'f_blocks', 'f_bfree', 'f_bavail', 'f_files', 'f_ffree', 'f_favail', 'f_flag', 'f_namemax')},
                        'governors': governors or None,
                        'mounts': Path('/proc/mounts').read_text(), 'idle_samples': [], 'samples': [], 'idle_passed': False}}
    def persist(final=False):
        receipt['remainder'] = [{'ordinal': row['ordinal'], 'status': 'NOT RUN', 'reason': receipt['stop_reason'] or 'pending'} for row in frozen[len(receipt['entries']):]]
        if final:
            receipt['seed_after'] = observe_seeds(args.prepared, prep, objects)
        save(args.output / 'capture.json', receipt)
    persist()
    try:
        for index in range(61):
            sample = host_sample()
            receipt['host']['idle_samples'].append(sample)
            persist()
            memory = dict(line.split(':', 1) for line in sample['counters']['meminfo'].splitlines())
            previous = receipt['host']['idle_samples'][-2] if index else None
            if (concurrent_processes(sample) or int(memory['MemAvailable'].split()[0])*1024 < 2147483648
                    or (previous is not None and (not idle_interval(previous, sample) or suspension_observed(previous, sample)))):
                receipt['stop_reason'] = 'host'
                persist(final=True)
                raise ValueError('idle prerequisite failed; no collection started')
            if index != 60:
                time.sleep(1)
    except KeyboardInterrupt:
        receipt['stop_reason'] = 'interruption'
        persist(final=True)
        raise ValueError('interrupted idle prerequisite; no collection started')
    except BaseException as error:
        receipt['stop_reason'] = receipt['stop_reason'] or 'infrastructure'
        receipt['failure'] = str(error)
        persist(final=True)
        raise
    receipt['host']['idle_passed'] = True
    receipt['host']['sampler_source'] = receipt['sources']['run.py']
    sampler = None
    phase_deadline = None
    fixtures = {f['key']: f for f in prep['fixtures']}
    receipt['warmup_start_ns'] = time.monotonic_ns()
    receipt['phase_storage'] = []
    def storage_observation(phase, stage):
        usage = workspace_bytes(root)
        receipt['phase_storage'].append({'phase': phase, 'stage': stage, 'bytes': usage, 'at_ns': time.monotonic_ns()})
        return usage
    try:
        storage_observation('warmup', 'start')
        for row in frozen:
            if row['phase'] == 'measured' and phase_deadline is None:
                phase_deadline = time.monotonic_ns()+1800_000_000_000
                receipt['measured_phase_start_ns'] = phase_deadline-1800_000_000_000
                receipt['measured_phase_deadline_ns'] = phase_deadline
                sampler = start_sampler(work)
                receipt['warmup_end_ns'] = receipt['measured_phase_start_ns']
                storage_observation('warmup', 'end')
                storage_observation('measured', 'start')
            if sampler is not None and sampler_failed(sampler):
                receipt['stop_reason'] = 'host'
                break
            if phase_deadline is not None and time.monotonic_ns() >= phase_deadline:
                receipt['stop_reason'] = 'phase'
                break
            old_trial_bytes = workspace_bytes(work / 'trial') if (work / 'trial').exists() else 0
            usage = storage_observation(row['phase'], 'before-copy')
            if usage-old_trial_bytes+fixtures[row['fixture']]['seed_identity']['bytes'] >= BUDGET-RESERVE:
                receipt['stop_reason'] = 'storage'
                break
            fixture = fixtures[row['fixture']]
            trial = work / 'trial'
            if trial.exists():
                shutil.rmtree(trial)
            trial.mkdir()
            shutil.copy2(args.prepared / fixture['seed_path'], trial / 'store.sqlite')
            db = trial / 'store.sqlite'
            require(file_identity(db) == fixture['seed_identity'], 'trial seed identity')
            before_physical, before = physical(db), snapshot(db)
            command = child(argv_for(row['operation'], fixture['declarations'][0]['id']), work, ENV,
                            phase_deadline_ns=phase_deadline, phase=row['phase'],
                            cancel_reason=lambda: sampler_cancel_event(sampler),
                            storage=accounted_storage(root, work))
            entry = {**row, 'seed_identity': fixture['seed_identity'], 'command': objects.put(canonical(command)),
                     'before_physical': before_physical, 'before': objects.put_snapshot(before)}
            receipt['entries'].append(entry)
            persist()
            entry['after_physical'] = physical(db)
            entry['after'] = objects.put_snapshot(snapshot(db))
            persist()
            from analyze import check_entry, failure_kind
            try:
                check_entry(entry, fixture, objects)
            except ValueError as error:
                receipt['stop_reason'] = failure_kind({**entry, 'command': command})
                receipt['failure'] = str(error)
                break
            if command['monitor']['interruptions'] and command['monitor']['interruptions'][0] > command['end_ns']:
                receipt['stop_reason'] = 'interruption'
                break
            if command['monitor'].get('post_reap_cancel'):
                receipt['stop_reason'] = command['monitor']['post_reap_cancel']
                break
    except BeforeSpawn as error:
        receipt['stop_reason'] = error.reason
        receipt['stop_before_spawn'] = error.observation
    except KeyboardInterrupt:
        receipt['stop_reason'] = 'interruption'
    except BaseException as error:
        receipt['stop_reason'] = 'infrastructure'
        receipt['failure'] = str(error)
        raise
    finally:
        if sampler is not None:
            receipt['host']['sampler'] = finish_sampler(sampler, objects)
            receipt['host']['samples'] = receipt['host']['sampler']['samples']
            if receipt['host']['sampler']['failure'] is not None or receipt['host']['sampler']['exit'] != 0:
                receipt['stop_reason'] = receipt['stop_reason'] or 'host'
        receipt['seed_after'] = observe_seeds(args.prepared, prep, objects)
        completed_phase = 'warmup' if phase_deadline is None else 'measured'
        storage_observation(completed_phase, 'end')
        if phase_deadline is None:
            receipt['warmup_end_ns'] = time.monotonic_ns()
        receipt['measured_phase_end_ns'] = time.monotonic_ns() if phase_deadline is not None else None
        if phase_deadline is not None and receipt['measured_phase_end_ns'] >= phase_deadline and receipt['stop_reason'] is None:
            receipt['stop_reason'] = 'phase'
        persist()
    require(receipt['stop_reason'] is None, 'partial capture: '+str(receipt['stop_reason']))


def operator_interrupt(signum, frame):
    raise KeyboardInterrupt


def workspace_root(prepared, output):
    prepared, output = Path(prepared).resolve(), Path(output).resolve()
    require(prepared.parent in output.parents and prepared not in output.parents and output != prepared,
            'use separate phase directories under the preparation campaign parent')
    return prepared.parent


def smoke(args, prep):
    root = workspace_root(args.prepared, args.output)
    require(not args.output.exists(), 'output exists')
    args.output.mkdir(parents=True)
    objects = Objects(args.output)
    retain_objects(args.prepared, objects)
    work = args.output / 'workspace'
    (work / 'bin').mkdir(parents=True)
    (work / 'home').mkdir()
    (work / 'tmp').mkdir()
    shutil.copy2(args.prepared / 'bin/mousa', work / 'bin/mousa')
    support = preflight_execution(work, objects, accounted_storage(root, work))
    frozen = schedule(prep)
    save(args.output / 'schedule.json', frozen)
    receipt = {'kind': 'unmeasured-smoke', 'collection': 'NOT RUN', 'protocol_sha256': sha((HERE / 'protocol.json').read_bytes()),
               'pidfd_preflight': support,
               'preparation': objects.put(canonical(prep)), 'sources': {p.name: objects.put(p.read_bytes()) for p in HERE.glob('*.py')},
               'preparation_invocations': [objects.put_file(path) for path in sorted((args.prepared / 'invocations').glob('*.json.gz'))],
               'build_receipts': {name: objects.put_file(args.prepared / name) for name in ('build.json', 'module-verification.json')},
               'schedule_sha256': sha(canonical(frozen) + b'\n'), 'entries': [],
               'remainder': [{'ordinal': e['ordinal'], 'status': 'NOT RUN', 'reason': 'unmeasured smoke only'} for e in frozen]}
    plan = [(fixture, operation) for fixture in prep['fixtures'] for operation in ('declaration-get', 'status')]
    def persist():
        receipt['smoke_remainder'] = [{'ordinal': ordinal, 'fixture': fixture['key'], 'operation': operation,
                                       'status': 'NOT RUN'} for ordinal, (fixture, operation) in enumerate(plan)
                                      if ordinal >= len(receipt['entries'])]
        save(args.output / 'capture.json', receipt)
    persist()
    try:
        for fixture, operation in plan:
            trial = work / 'trial'
            if trial.exists():
                shutil.rmtree(trial)
            require(workspace_bytes(root)+fixture['seed_identity']['bytes'] < BUDGET-RESERVE, 'smoke copy storage')
            trial.mkdir()
            seed = args.prepared / fixture['seed_path']
            shutil.copy2(seed, trial / 'store.sqlite')
            db = trial / 'store.sqlite'
            require(file_identity(db) == fixture['seed_identity'], 'trial seed bytes')
            before_physical, before = physical(db), snapshot(db)
            command = child(argv_for(operation, fixture['declarations'][0]['id']), work, ENV,
                            phase='smoke', storage=accounted_storage(root, work))
            entry = {'ordinal': len(receipt['entries']), 'phase': 'smoke', 'fixture': fixture['key'], 'operation': operation,
                     'seed_identity': fixture['seed_identity'], 'before': objects.put_snapshot(before),
                     'before_physical': before_physical, 'command': objects.put(canonical(command))}
            receipt['entries'].append(entry)
            persist()
            entry['after_physical'] = physical(db)
            entry['after'] = objects.put_snapshot(snapshot(db))
            persist()
            from analyze import check_entry
            check_entry(entry, fixture, objects)
            if command['monitor']['interruptions']:
                raise KeyboardInterrupt
    except BaseException as error:
        receipt['failure'] = {'class': type(error).__name__, 'message': str(error)}
        raise
    finally:
        receipt['seed_after'] = observe_seeds(args.prepared, prep, objects)
        persist()
    from analyze import verify
    verify(args.output)
    print('PASS: 40 unmeasured native smoke operations; measured collection NOT RUN')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['smoke', 'capture'])
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, operator_interrupt)
    protocol()
    preflight()
    from prepare import verify_prepared
    prep = verify_prepared(args.prepared)
    require(not args.output.exists(), 'output exists')
    if args.mode == 'capture':
        capture(args, prep)
    else:
        smoke(args, prep)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
