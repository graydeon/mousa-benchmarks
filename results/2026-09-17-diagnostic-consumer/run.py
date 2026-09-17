from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import shutil
import sqlite3
import subprocess
import sys
import time

out = Path(os.environ['OMP_OUTPUT'])
inp = Path(os.environ['OMP_INPUT']) / 'diagnostic'
seed = inp / 'small-0.sqlite'
expected = '0c697debe9d226ce460c9074c719814108284575a0ea686c0f8b73ba0700083b'
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(seed) == expected

def context():
    result = {}
    for name in ('/proc/loadavg', '/proc/stat', '/proc/pressure/cpu', '/proc/pressure/io', '/proc/pressure/memory', '/sys/fs/cgroup/cpu.stat', '/sys/fs/cgroup/io.stat', '/sys/fs/cgroup/memory.current', '/proc/self/cgroup'):
        try:
            result[name] = Path(name).read_text()
        except OSError as e:
            result[name] = str(e)
    return result

def counts(path):
    # Only inspect closed, checkpointed files; immutable reads must not ignore a WAL.
    assert not any(Path(str(path) + suffix).exists() for suffix in ('-wal', '-shm', '-journal'))
    with closing(sqlite3.connect('file:' + str(path) + '?mode=ro&immutable=1', uri=True)) as db:
        return {name: db.execute('select count(*) from ' + name).fetchone()[0] for name in ('source_trails', 'source_trail_candidates', 'policy_decisions')}

oracle = None
ids = set()
def call(binary, kind, block, arm):
    global oracle
    work = out / 'work.sqlite'
    assert not any(Path(str(work) + suffix).exists() for suffix in ('', '-wal', '-shm', '-journal'))
    shutil.copyfile(seed, work)
    assert sha(work) == expected
    before = counts(work)
    assert all(v == 0 for v in before.values()), before
    command = ['/usr/bin/time', '-f', '%M %U %S', '-o', str(out / 'cost.txt'), str(out / binary), '-store', str(work), 'query', '--source', 'scaling', '--packing-policy', 'original', '--budget-bytes', '8192', 'amber']
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    utc = time.time_ns()
    start = time.perf_counter_ns()
    try:
        p = subprocess.run(command, capture_output=True, timeout=30)
    except subprocess.TimeoutExpired as error:
        with (out / 'attempts.jsonl').open('a') as f:
            f.write(json.dumps(dict(kind=kind, block=block, arm=arm, binary=binary,
                command=command, utc_start_ns=utc, timeout=True,
                stdout=(error.stdout or b'').decode(errors='replace'),
                stderr=(error.stderr or b'').decode(errors='replace'))) + '\n')
        raise
    elapsed = time.perf_counter_ns() - start
    end = time.time_ns()
    after_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    row = dict(kind=kind, block=block, arm=arm, binary=binary, command=command, utc_start_ns=utc, utc_end_ns=end, monotonic_start_ns=start, wall_ms=elapsed/1e6, exit=p.returncode, stdout=p.stdout.decode(), stderr=p.stderr.decode(), before_counts=before)
    row['usage_delta'] = {name: getattr(after_usage, name)-getattr(usage, name) for name in ('ru_utime', 'ru_stime', 'ru_minflt', 'ru_majflt', 'ru_nvcsw', 'ru_nivcsw', 'ru_inblock', 'ru_oublock')}
    row['gnu_time'] = (out / 'cost.txt').read_text()
    with (out / 'attempts.jsonl').open('a') as f:
        f.write(json.dumps(row) + '\n')
    assert p.returncode == 0, row
    response = json.loads(row.pop('stdout'))
    assert response['decision_outcome'] == 'allow' and response['outcome'] == 'evidence'
    assert len(response['evidence']) == 1 and response['matched_candidates'] == 1
    assert response['request_id'] not in ids
    ids.add(response['request_id'])
    stable = {k: v for k, v in response.items() if k not in ('request_id', 'decision_id', 'trail_id', 'evaluated_at_usec', 'latency_micros')}
    if oracle is None:
        oracle = stable
    assert stable == oracle
    row['response'] = response
    row['after_counts'] = counts(work)
    assert all(v == 1 for v in row['after_counts'].values()), row['after_counts']
    if kind == 'stage':
        row['diagnostic'] = json.loads(row.pop('stderr'))
    else:
        assert not row.pop('stderr')
    with (out / 'observations.jsonl').open('a') as f:
        f.write(json.dumps(row) + '\n')
    work.unlink()
    assert not any(Path(str(work) + suffix).exists() for suffix in ('-wal', '-shm', '-journal'))

pairs = {'control': ('old-baseline', 'old-baseline'), 'old': ('old-baseline', 'old-candidate'), 'rebuilt': ('baseline', 'candidate')}
for binary in ('old-baseline', 'old-candidate', 'baseline', 'candidate'):
    call(binary, 'smoke', -1, binary)
print('Smoke PASS: authorization, selected evidence, projected counts and resets', flush=True)
if sys.argv[1:] == ['--smoke-only']:
    (out / 'smoke-context.json').write_text(json.dumps(context(), indent=2) + '\n')
    raise SystemExit(0)
assert sys.argv[1:] in ([], ['--pilot'])
pilot = sys.argv[1:] == ['--pilot']
blocks, stages = (2, 2) if pilot else (24, 8)
for block in range(2):
    for kind, binaries in pairs.items():
        for arm in (range(2) if block == 0 else (1, 0)):
            call(binaries[arm], 'warmup-' + kind, block, arm)
rng = random.Random(20260917)
orders = {}
for kind in pairs:
    orders[kind] = [0, 1] * (blocks // 2)
    rng.shuffle(orders[kind])
schedule = []
for block in range(blocks):
    kinds = list(pairs)
    rng.shuffle(kinds)
    schedule.append([(kind, orders[kind][block]) for kind in kinds])
(out / 'schedule.json').write_text(json.dumps(schedule, indent=2) + '\n')
for block, entries in enumerate(schedule):
    for kind, first in entries:
        record = dict(block=block, kind=kind, before=context())
        for arm in (first, 1-first):
            call(pairs[kind][arm], kind, block, arm)
        record['after'] = context()
        with (out / 'context.jsonl').open('a') as f:
            f.write(json.dumps(record) + '\n')
    print('Completed block', block+1, '/', blocks, flush=True)
for block in range(stages):
    for arm in ((0, 1) if block % 2 == 0 else (1, 0)):
        call(('stage-baseline', 'stage-candidate')[arm], 'stage', block, arm)
    print('Completed stage block', block+1, '/', stages, flush=True)
(out / 'manifest.json').write_text(json.dumps({'fixture_sha256': sha(seed), 'protocol_sha256': sha(inp / 'protocol.json'), 'binaries': {n: sha(out / n) for n in ('old-baseline', 'old-candidate', 'baseline', 'candidate', 'stage-baseline', 'stage-candidate')}}, indent=2) + '\n')
