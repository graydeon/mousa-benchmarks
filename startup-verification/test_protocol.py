#!/usr/bin/env python3
"""Behavioral boundaries; all subprocess observations here are unmeasured controls."""
import json
import os
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

import common
import run


def pad_workspace(root, size):
    """Model existing bytes without allocating them or exceeding per-file limits."""
    chunk = 16*1024*1024
    for index, offset in enumerate(range(0, size, chunk)):
        with (root / f'control-only-budget-padding-{index}').open('wb') as stream:
            stream.truncate(min(chunk, size-offset))


class ProtocolTests(unittest.TestCase):
    def test_synthetic_host_idle_thresholds_exclude_guest_double_counting(self):
        def sample(user, idle, steal=0, guest=0, available=2097152):
            return {'kind': 'synthetic test input', 'counters': {
                'stat': f'cpu {user} 0 0 {idle} 0 0 0 {steal} {guest} 0\n',
                'meminfo': f'MemAvailable: {available} kB\n'}}
        before = sample(0, 0)
        self.assertTrue(run.idle_interval(before, sample(9, 91, guest=9)))
        self.assertFalse(run.idle_interval(before, sample(10, 90)))
        self.assertFalse(run.idle_interval(before, sample(0, 99, steal=1)))
        self.assertFalse(run.idle_interval(before, sample(0, 100, available=2097151)))
        old = {'boottime_offset_interval_ns': [0, 10]}
        self.assertFalse(run.suspension_observed(old, {'boottime_offset_interval_ns': [5, 15]}))
        self.assertTrue(run.suspension_observed(old, {'boottime_offset_interval_ns': [11, 21]}))

    def test_synthetic_inventory_distinguishes_existing_study_from_owned_child(self):
        def process(pid, parent, name):
            return {'pid': pid, 'ppid': parent, 'comm': name, 'cpu_ticks': 0,
                    'start_ticks': pid*100, 'state': 'S'}
        sample = {'kind': 'synthetic test input', 'process_inventory': {
            'owner_pid': 10, 'ancestors': [10, 1], 'inaccessible': [],
            'processes': [process(10, 1, 'python3'), process(11, 10, 'mousa'),
                          process(20, 1, 'mousa'), process(21, 1, 'python3.13')]}}
        self.assertEqual([p['pid'] for p in run.concurrent_processes(sample, sample)], [20, 21])

    def test_strict_json(self):
        for raw in ('{"a":1,"a":2}', '{"a":{"b":1,"b":1}}', 'NaN', '1e999', b'\xff'):
            with self.assertRaises(ValueError):
                common.loads(raw)
        self.assertNotEqual(common.canonical({'n': True}), common.canonical({'n': 1}))
        self.assertEqual(common.canonical(common.loads('{"b":2,"a":1}')),
                         common.canonical({'a': 1, 'b': 2}))

    def test_compressed_monitor_receipt_is_lossless_and_replayable(self):
        import gzip
        value = {'kind': 'synthetic test input', 'stdout_hex': '00ff0a', 'exit': 1,
                 'failure': 'retain this failure', 'monitor': [
                     {'start_ns': 1000000+i*1000000, 'end_ns': 1000500+i*1000000,
                      'requested_ms': 1, 'ready': i == 4999} for i in range(5000)]}
        raw = common.canonical(value)+b'\n'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'receipt.json.gz'
            common.save(path, value)
            self.assertLess(path.stat().st_size, len(raw)//2)
            self.assertEqual(gzip.decompress(path.read_bytes()), raw)
            self.assertEqual(common.read_json(path), value)
            objects = common.Objects(root / 'evidence')
            reference = objects.put_file(path)
            self.assertEqual(objects.json(reference), value)
            archive = root / 'receipts.tar.gz'
            common.pack(root / 'evidence', archive)
            common.unpack(archive, root / 'replay')
            self.assertEqual(common.Objects(root / 'replay').json(reference), value)
            for broken in (b'{"n":1,"n":2}', b'NaN', b'\xff'):
                reference = objects.put(gzip.compress(broken, mtime=0))
                with self.assertRaises(ValueError):
                    objects.json(reference)

    def test_compressed_receipt_decodes_under_control_only_memory_limit(self):
        import hashlib
        payload = {'kind': 'synthetic test input', 'complete': 'receipt-data-'*100000}
        expected = hashlib.sha256(common.canonical(payload)).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'receipt.json.gz'
            common.save(path, payload)
            program = ('import hashlib,resource,sys; sys.path.insert(0,sys.argv[1]); import common; '
                       'resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024)); '
                       'value=common.read_json(sys.argv[2]); print(hashlib.sha256(common.canonical(value)).hexdigest())')
            actual = run.child([sys.executable, '-c', program, str(common.HERE), str(path)], root, {})
        self.assertEqual(actual['exit'], 0, bytes.fromhex(actual['stderr_hex']))
        self.assertEqual(bytes.fromhex(actual['stdout_hex']), expected.encode()+b'\n')

    def test_workspace_inventory_counts_hardlinks_once_and_rejects_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'nested').mkdir()
            first = root / 'original'
            first.write_bytes(bytes(range(256)))
            os.link(first, root / 'nested/shared')
            (root / 'nested/other').write_bytes(b'other')
            self.assertEqual(common.workspace_bytes(root), 261)
            (root / 'nested/cycle').symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'workspace link'):
                common.workspace_bytes(root)

    def test_prefix_validation_does_not_relax_pins_or_complete_coverage(self):
        import prepare
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'bin').mkdir()
            (root / 'bin/mousa').write_bytes(b'synthetic untrusted binary input')
            receipt = {'product_commit': '0'*40, 'product_tree': common.TREE,
                       'protocol_sha256': common.PROTOCOL_SHA, 'fixtures': [],
                       'binary_identity': common.file_identity(root / 'bin/mousa')}
            common.save(root / 'preparation.json', receipt)
            with self.assertRaisesRegex(ValueError, 'product source pin'):
                prepare.verify_prepared(root, allow_prefix=True)
            receipt['product_commit'] = common.PRODUCT
            common.save(root / 'preparation.json', receipt)
            with self.assertRaisesRegex(ValueError, 'fixture coverage'):
                prepare.verify_prepared(root)

    def test_invalid_native_prefix_cutoffs_are_rejected(self):
        import prepare
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'prior'
            (source / 'bin').mkdir(parents=True)
            (source / 'bin/mousa').write_bytes(b'synthetic untrusted prefix binary')
            identity = common.file_identity(source / 'bin/mousa')
            common.save(source / 'preparation.json', {'product_commit': common.PRODUCT,
                        'product_tree': common.TREE, 'protocol_sha256': common.PROTOCOL_SHA,
                        'binary_identity': identity, 'fixtures': []})
            (source / 'invocations').mkdir()
            common.save(source / 'invocations/000000.json.gz', {})
            for cutoff in (-1, 1, True, 0.0):
                with self.subTest(cutoff=cutoff), self.assertRaises(ValueError):
                    prepare.import_prefix(source, root / 'new', common.Objects(root / 'new'), identity, cutoff)

    def test_schedule_independent_order_and_coverage(self):
        import hashlib
        entries = run.schedule()
        self.assertEqual(len(entries), 480)
        self.assertEqual([e['ordinal'] for e in entries], list(range(480)))
        for phase, offset, rounds in [('warmup', 0, 2), ('measured', 80, 10)]:
            for rnd in range(rounds):
                rows = entries[offset + 40*rnd:offset + 40*(rnd+1)]
                self.assertEqual(len({(x['S'], x['E'], x['T'], x['operation']) for x in rows}), 40)
                keys = [f"mousa-startup-v1|{phase}|{rnd}|{x['S']}|{x['E']}|{x['T']}|{x['operation']}".encode() for x in rows]
                self.assertEqual(keys, sorted(keys, key=lambda k: (hashlib.sha256(k).digest(), k)))

    def test_snapshots_preserve_types_duplicates_and_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'store.sqlite'
            with closing(sqlite3.connect(db)) as c, c:
                c.execute('CREATE TABLE values_table(v)')
                c.executemany('INSERT INTO values_table VALUES (?)', [(1,), ('1',), (b'1',), (None,), (1.5,), (1,)])
            before = common.snapshot(db)
            rows = before['tables']['values_table']['rows']
            self.assertEqual(len(rows), 6)
            self.assertEqual({field[0] for row in rows for field in row}, {'integer', 'text', 'blob', 'null', 'real'})
            physical = common.physical(db)
            common.validate_physical(physical)
            physical['-wal'] = {'bytes': False, 'sha256': common.sha(b'')}
            with self.assertRaises(ValueError):
                common.validate_physical(physical)
            with closing(sqlite3.connect(db)) as c, c:
                c.execute('CREATE TABLE forbidden(v)')
                c.execute('INSERT INTO forbidden VALUES (7)')
            self.assertNotEqual(common.canonical(before), common.canonical(common.snapshot(db)))

    def test_pidfd_wakeup_and_exact_child_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run.child([sys.executable, '-c', 'import time; time.sleep(.05); print(time.monotonic_ns())'], Path(tmp), {}, control_poll_ms=1000)
            self.assertEqual(result['exit'], 0)
            self.assertEqual(result['monitor']['wait4_calls'], 1)
            self.assertLess(result['monitor']['polls'][0]['end_ns'] - result['monitor']['polls'][0]['start_ns'], 900_000_000)
            self.assertEqual(result['monitor']['polls'][0]['requested_ms'], 1000)
            marker = int(bytes.fromhex(result['stdout_hex']))
            self.assertLess(result['monitor']['polls'][0]['start_ns'], marker)
            self.assertLessEqual(marker, result['monitor']['polls'][0]['end_ns'])
            self.assertGreaterEqual(result['rss_kib'], 0)

    def test_deadline_reaps_term_ignoring_child(self):
        import analyze
        with tempfile.TemporaryDirectory() as tmp:
            result = run.child([sys.executable, '-c', 'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)'], Path(tmp), {}, control_limits={'command_seconds': .1, 'grace_seconds': .1})
            analyze.check_monitor(result, control=True)
            self.assertEqual(result['censor_reason'], 'timeout')
            self.assertEqual(result['exit'], -9)
            self.assertEqual(result['monitor']['wait4_calls'], 1)
            self.assertTrue(all(p['requested_ms'] <= 1 for p in result['monitor']['polls']))
            with self.assertRaises(ChildProcessError):
                os.waitpid(result['pid'], 0)

    def test_peak_rss_is_per_child_not_wrapper_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            large = run.child([sys.executable, '-c', 'data=bytearray(256*1024*1024); print(data[-1])'],
                              Path(tmp), {})
            small = run.child([sys.executable, '-c', 'print(7)'], Path(tmp), {})
        self.assertEqual(large['exit'], 0)
        self.assertEqual(small['exit'], 0)
        self.assertGreater(large['rss_kib'], 240*1024)
        self.assertLess(large['rss_kib'], 384*1024)
        self.assertLess(small['rss_kib'], large['rss_kib']/2)

    def test_exact_child_cpu_is_seconds_within_its_own_wall_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            actual = run.child([sys.executable, '-c',
                                'import time\nstart=time.process_time()\nwhile time.process_time()-start < .05: pass'],
                               Path(tmp), {})
        self.assertEqual(actual['exit'], 0)
        cpu = actual['user_seconds']+actual['system_seconds']
        self.assertGreaterEqual(cpu, .04)
        self.assertLessEqual(cpu, actual['wall_ns']/1e9+.02)

    def test_missing_pidfd_fails_before_child_creation(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            with patch('os.pidfd_open', side_effect=PermissionError('denied')), patch('os.fork') as fork:
                with self.assertRaises(PermissionError):
                    run.child([sys.executable, '-c', 'pass'], Path(tmp), {})
                fork.assert_not_called()

    def test_monitor_boundary_mutations_reject(self):
        import copy
        import analyze
        with tempfile.TemporaryDirectory() as tmp:
            actual = run.child([sys.executable, '-c', 'pass'], Path(tmp), {}, storage=lambda: 0)
        analyze.check_monitor(actual)
        for mutate in (
            lambda c: c.__setitem__('wall_ns', c['wall_ns']+1),
            lambda c: c.__setitem__('rss_kib', True),
            lambda c: c.__setitem__('exit_code', False),
            lambda c: c['monitor']['polls'][0].__setitem__('end_ns', float(c['monitor']['polls'][0]['end_ns'])),
            lambda c: c['monitor'].__setitem__('wait4_calls', 2),
            lambda c: c['monitor'].__setitem__('storage', []),
            lambda c: c['monitor'].__setitem__('deadlines', []),
            lambda c: c['monitor']['polls'][0].__setitem__('requested_ms', 1000),
            lambda c: c['monitor'].__setitem__('reap_ns', c['end_ns']+1),
            lambda c: c['monitor'].__setitem__('wait4_pid', c['pid']+1),
            lambda c: c['monitor'].__setitem__('wait4_options', 1),
            lambda c: c['monitor']['polls'][-1].__setitem__('events', []),
            lambda c: c.__setitem__('stdout_sha256', '0'*64),
        ):
            altered = copy.deepcopy(actual)
            mutate(altered)
            with self.assertRaises(ValueError):
                analyze.check_monitor(altered)

    def test_recover_complete_actual_states_and_reject_ambiguous_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / 'store.sqlite'
            with closing(sqlite3.connect(db)) as connection, connection:
                connection.execute('CREATE TABLE records(value)')
                connection.executemany('INSERT INTO records VALUES (?)', [(str(i),) for i in range(100)])
                connection.execute('INSERT INTO records VALUES (?)', ('0',))
            first = common.snapshot(db)
            objects = common.Objects(root / 'evidence')
            first_ref = objects.put_snapshot(first)
            with closing(sqlite3.connect(db)) as connection, connection:
                connection.execute('DELETE FROM records WHERE value = ?', ('5',))
                connection.execute('INSERT INTO records VALUES (?)', (b'new bytes',))
            second = common.snapshot(db)
            second_ref = objects.put_snapshot(second)
            self.assertEqual(objects.get(first_ref), common.canonical(first))
            self.assertEqual(objects.get(second_ref), common.canonical(second))
            archive = root / 'states.tar.gz'
            common.pack(root / 'evidence', archive)
            common.unpack(archive, root / 'replay')
            replay = common.Objects(root / 'replay')
            self.assertEqual(replay.json(first_ref), first)
            self.assertEqual(replay.json(second_ref), second)
            (root / 'replay/objects' / first_ref['sha256']).write_bytes(common.canonical(first))
            with self.assertRaisesRegex(ValueError, 'ambiguous object reference'):
                replay.get(first_ref)

    def test_lossless_archive_and_unsafe_member_rejection(self):
        import io
        import tarfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            raw = bytes(range(256)) * 4
            (source / 'raw.bin').write_bytes(raw)
            archive = root / 'capture.tar.gz'
            common.pack(source, archive)
            common.unpack(archive, root / 'replay')
            self.assertEqual((root / 'replay/raw.bin').read_bytes(), raw)
            bad = root / 'bad.tar.gz'
            with tarfile.open(bad, 'w:gz') as tar:
                info = tarfile.TarInfo('../escape')
                info.size = 1
                tar.addfile(info, io.BytesIO(b'x'))
            common.save(str(bad)+'.members.json', [])
            with self.assertRaisesRegex(ValueError, 'unsafe archive path'):
                common.unpack(bad, root / 'bad-replay')

    def test_late_reap_is_censored_when_readiness_precedes_deadline(self):
        import time
        from unittest.mock import patch
        real_wait = os.wait4
        def delayed_wait(pid, options):
            result = real_wait(pid, options)
            time.sleep(.15)  # Control-only parent scheduling delay at the reap boundary.
            return result
        with tempfile.TemporaryDirectory() as tmp, patch('os.wait4', delayed_wait):
            actual = run.child([sys.executable, '-c', 'pass'], Path(tmp), {},
                               control_limits={'command_seconds': .1})
        self.assertEqual(actual['exit'], 0)
        self.assertLess(actual['monitor']['readiness_ns'], actual['command_deadline_ns'])
        self.assertGreater(actual['end_ns'], actual['command_deadline_ns'])
        self.assertEqual(actual['censor_reason'], 'timeout')

    def test_readiness_control_cannot_hide_deadline_censoring(self):
        import analyze
        with tempfile.TemporaryDirectory() as tmp:
            actual = run.child([sys.executable, '-c', 'import time; time.sleep(.05)'],
                               Path(tmp), {}, control_poll_ms=1000)
        self.assertEqual(len(actual['monitor']['polls']), 1)
        poll = actual['monitor']['polls'][0]
        deadline = (poll['start_ns']+poll['end_ns'])//2
        actual['command_deadline_ns'] = deadline
        actual['deadline_overshoot_ns'] = actual['end_ns']-deadline
        for edge in actual['monitor']['deadlines']:
            edge['command_due'] = edge['at_ns'] >= deadline
        with self.assertRaises(ValueError):
            analyze.check_monitor(actual, control=True)

    def test_owned_child_pidfd_denial_is_preflight_failure_and_reaps_probe(self):
        from unittest.mock import patch
        parent = os.getpid()
        real_open, real_fork = os.pidfd_open, os.fork
        children = []
        def fork():
            pid = real_fork()
            if pid:
                children.append(pid)
            return pid
        def denied(pid, flags=0):
            if pid != parent:
                raise PermissionError('control-only owned-child pidfd denial')
            return real_open(pid, flags)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch('os.fork', fork), patch('os.pidfd_open', denied):
                with self.assertRaises(PermissionError):
                    run.preflight_execution(root / 'workspace', common.Objects(root))
            self.assertEqual(len(children), 1)
            with self.assertRaises(ChildProcessError):
                os.waitpid(children[0], 0)
            self.assertEqual(common.read_json(root / 'pidfd-preflight.json')['error_class'], 'PermissionError')

    def test_pack_combined_workspace_budget_before_and_during_compression(self):
        import random
        import gc
        from unittest.mock import patch
        for remaining in (-1, 1024):
            with self.subTest(remaining=remaining), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / 'source'
                source.mkdir()
                raw = random.Random(9).randbytes(65536)
                (source / 'evidence.bin').write_bytes(raw)
                pad_workspace(root, common.BUDGET-common.RESERVE-len(raw)-remaining)
                before = common.workspace_bytes(root)
                archive = root / 'bounded.tar.gz'
                unraisable = []
                with patch('sys.unraisablehook', side_effect=unraisable.append):
                    with self.assertRaises(ValueError):
                        common.pack(source, archive)
                    gc.collect()
                self.assertEqual(unraisable, [])
                self.assertLessEqual(common.workspace_bytes(root), max(before, common.BUDGET-common.RESERVE))
                self.assertEqual((source / 'evidence.bin').read_bytes(), raw)

    def test_unpack_counts_existing_campaign_bytes_before_member_write(self):
        import random
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            (source / 'evidence.bin').write_bytes(random.Random(11).randbytes(65536))
            archive = root / 'capture.tar.gz'
            common.pack(source, archive)
            existing = common.workspace_bytes(root)
            pad_workspace(root, common.BUDGET-common.RESERVE-existing-1024)
            with self.assertRaises(ValueError):
                common.unpack(archive, root / 'replay')
            self.assertFalse((root / 'replay').exists())

    def test_oversized_archive_preserves_every_member_and_refuses_replay(self):
        import random
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            raw = random.Random(7).randbytes(4194304+65536)
            (source / 'evidence.bin').write_bytes(raw)
            archive = root / 'oversized.tar.gz'
            with self.assertRaises(ValueError):
                common.pack(source, archive)
            self.assertGreater(archive.stat().st_size, 4194304)
            self.assertEqual(common.read_json(str(archive)+'.members.json'),
                             [{'name': 'evidence.bin', 'bytes': len(raw), 'sha256': common.sha(raw)}])
            with self.assertRaises(ValueError):
                common.unpack(archive, root / 'replay')
            self.assertFalse((root / 'replay').exists())

    def test_framed_json_retains_complete_prefix_and_reports_raw_failure_offset(self):
        prefix = b'{"sequence":1}\n'
        for tail in (b'{"sequence":2}', b'{"sequence":true,"sequence":2}\n', b'NaN\n'):
            values, failure = common.json_frames(prefix+tail)
            self.assertEqual(values, [{'sequence': 1}])
            self.assertEqual(failure['byte_offset'], len(prefix))
            self.assertIn(failure['class'], ('ValueError', 'JSONDecodeError'))
        self.assertEqual(common.json_frames(prefix), ([{'sequence': 1}], None))

    def test_closed_receipt_survives_atomic_source_replacement_and_rejects_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / 'progress.json'
            common.save(original, {'step': 1})
            raw = original.read_bytes()
            objects = common.Objects(root / 'evidence')
            reference = objects.put_file(original)
            common.save(original, {'step': 2})
            self.assertEqual(objects.get(reference), raw)
            target = root / 'evidence/objects' / reference['sha256']
            target.unlink()
            target.symlink_to(original)
            with self.assertRaises(ValueError):
                objects.get(reference)

    def test_control_limits_cannot_weaken_measured_path(self):
        from unittest.mock import patch
        for options in ({'control_limits': {'command_seconds': .1}}, {'control_poll_ms': 1000}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as tmp:
                with patch('os.fork', side_effect=AssertionError('unexpected spawn')):
                    with self.assertRaises(ValueError):
                        run.child([sys.executable, '-c', 'pass'], Path(tmp), {}, phase='measured', **options)

    def test_readiness_control_retains_host_event_after_reap(self):
        import analyze
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def cancellation():
                output = root / 'stdout.raw'
                if output.exists() and output.stat().st_size:
                    return {'reason': 'host', 'at_ns': int(output.read_bytes()),
                            'detail': 'synthetic test input; real child exit marker'}
                return None
            actual = run.child([sys.executable, '-c', 'import os,time; time.sleep(.05); print(time.monotonic_ns(),flush=True); os._exit(0)'],
                               root, {}, control_poll_ms=1000, cancel_reason=cancellation)
        self.assertEqual(actual['exit'], 0)
        self.assertEqual(actual['censor_reason'], 'host')
        self.assertEqual(actual['monitor']['signals'], [])
        self.assertGreaterEqual(actual['detected_ns'], actual['end_ns'])
        self.assertEqual(actual['wall_ns'], actual['end_ns']-actual['start_ns'])
        analyze.check_monitor(actual, control=True)

    def test_expired_measured_phase_never_spawns(self):
        import time
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp, patch('os.fork') as fork:
            with self.assertRaisesRegex(run.BeforeSpawn, 'phase before spawn'):
                run.child([sys.executable, '-c', 'pass'], Path(tmp), {}, phase='measured',
                          phase_deadline_ns=time.monotonic_ns()-1, storage=lambda: 0)
            fork.assert_not_called()

    def test_archive_member_type_duplicate_size_and_hash_guards(self):
        import io
        import tarfile
        cases = [
            ('link', tarfile.SYMTYPE, 'safe', b'', 'archive member type'),
            ('hardlink', tarfile.LNKTYPE, 'safe', b'', 'archive member type'),
            ('directory', tarfile.DIRTYPE, 'safe', b'', 'archive member type'),
            ('absolute', tarfile.REGTYPE, '/escape', b'x', 'unsafe archive path'),
            ('backslash', tarfile.REGTYPE, r'a\\escape', b'x', 'unsafe archive path'),
            ('duplicate', tarfile.REGTYPE, 'safe', b'x', 'duplicate archive member'),
            ('hash', tarfile.REGTYPE, 'safe', b'x', 'archive member hash'),
        ]
        for name, kind, member, raw, detector in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                archive = root / 'input.tar.gz'
                with tarfile.open(archive, 'w:gz', format=tarfile.USTAR_FORMAT) as tar:
                    for unused in range(2 if name == 'duplicate' else 1):
                        info = tarfile.TarInfo(member)
                        info.type, info.size, info.linkname = kind, len(raw), 'elsewhere'
                        tar.addfile(info, io.BytesIO(raw))
                digest = '0'*64 if name == 'hash' else common.sha(raw)
                common.save(str(archive)+'.members.json', [{'name': member, 'bytes': len(raw), 'sha256': digest}])
                with self.assertRaises(ValueError):
                    common.unpack(archive, root / 'out')
        with tempfile.TemporaryDirectory() as tmp:
            import gzip
            root = Path(tmp)
            archive = root / 'oversized-member.tar.gz'
            info = tarfile.TarInfo('safe')
            info.size = 33554433
            archive.write_bytes(gzip.compress(info.tobuf(format=tarfile.USTAR_FORMAT)+b'\0'*1024))
            common.save(str(archive)+'.members.json', [])
            with self.assertRaises(ValueError):
                common.unpack(archive, root / 'out')


if __name__ == '__main__':
    unittest.main()
