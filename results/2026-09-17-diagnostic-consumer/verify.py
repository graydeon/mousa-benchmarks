"""Verify retained raw bytes, observation counts and paired result summaries."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import statistics
import tarfile

root = Path(__file__).resolve().parent
expected = json.loads((root / 'archive-members.json').read_text())
found = {}
with tarfile.open(root / 'raw-results.tar.xz') as archive:
    for member in archive:
        path = PurePosixPath(member.name)
        if (not member.isfile() or path.is_absolute() or '..' in path.parts
                or member.name not in expected or member.name in found
                or member.size > 4 << 20):
            raise SystemExit('Invalid archive member: ' + member.name)
        data = archive.extractfile(member).read()
        if expected[member.name] != {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}:
            raise SystemExit('Changed archive member: ' + member.name)
        found[member.name] = data
assert set(found) == set(expected)
assert hashlib.sha256(found['inputs/small-0.sqlite']).hexdigest() == '0c697debe9d226ce460c9074c719814108284575a0ea686c0f8b73ba0700083b'
for prefix, blocks, stages, count in (('pilot', 2, 2, 32), ('timed', 24, 8, 176)):
    rows = [json.loads(line) for line in found[prefix + '/observations.jsonl'].splitlines()]
    attempts = [json.loads(line) for line in found[prefix + '/attempts.jsonl'].splitlines()]
    summary = json.loads(found[prefix + '/analysis.json'])
    assert len(rows) == len(attempts) == summary['invocations'] == count
    assert len({r['response']['request_id'] for r in rows}) == count
    assert all(r['exit'] == 0 and not r.get('timeout') for r in attempts)
    for row in rows:
        assert all(v == 0 for v in row['before_counts'].values())
        assert all(v == 1 for v in row['after_counts'].values())
        response = row['response']
        assert response['decision_outcome'] == 'allow' and response['outcome'] == 'evidence'
        assert len(response['evidence']) == response['matched_candidates'] == 1
    for kind in ('control', 'old', 'rebuilt'):
        pairs = [[next(r for r in rows if r['kind'] == kind and r['block'] == block and r['arm'] == arm)
                  for arm in (0, 1)] for block in range(blocks)]
        for metric in ('wall_ms', 'cpu_ms'):
            def value(row):
                return row['wall_ms'] if metric == 'wall_ms' else 1000 * (row['usage_delta']['ru_utime'] + row['usage_delta']['ru_stime'])
            a, b = ([value(pair[arm]) for pair in pairs] for arm in (0, 1))
            actual = summary['pairs'][kind][metric]
            assert actual['baseline_median'] == statistics.median(a)
            assert actual['candidate_median'] == statistics.median(b)
            assert actual['median_difference'] == statistics.median([y-x for x, y in zip(a, b)])
            assert actual['median_ratio'] == statistics.median([y/x for x, y in zip(a, b)])
    assert len([r for r in rows if r['kind'] == 'stage']) == stages * 2
    receipt = json.loads(found['receipts/' + prefix + '-status.log'])
    assert receipt['exit_code'] == 0
    assert receipt['finished_at'] - receipt['started_at'] < 1200
manifest = json.loads(found['timed/manifest.json'])
assert manifest['protocol_sha256'] == hashlib.sha256((root / 'protocol.json').read_bytes()).hexdigest()
consumer = json.loads(found['consumer/results.json'])
assert hashlib.sha256(found['consumer/measured-docs.py']).hexdigest() == consumer['inputs']['docs.py']
questions = json.loads(found['consumer/questions.json'])
assert consumer['result'] == 'PASS' and len(consumer['rows']) == 27
for row in consumer['rows']:
    assert row['exit'] == 0
    if row['stage'] != 'ask':
        continue
    packet = row['packet']
    evidence = packet['response']['evidence'] or []
    assert sum(len(hit['text'].encode()) for hit in evidence) == packet['response']['used_bytes'] <= questions['budget_bytes']
    assert packet['answer'] is None and packet['support'] == 'not_assessed'
assert json.loads(found['receipts/consumer-status.log'])['exit_code'] == 0
print('Verified', len(found), 'lossless members; separate 32-row pilot, 176-row diagnostic and 25-query consumer study')
