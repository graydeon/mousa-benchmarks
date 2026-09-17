import hashlib
import json
from pathlib import Path
import random
import statistics
import sys


def analyze(root, pilot=False):
    blocks, stages = (2, 2) if pilot else (24, 8)
    rows = [json.loads(line) for line in (root / 'observations.jsonl').read_text().splitlines()]
    attempts = [json.loads(line) for line in (root / 'attempts.jsonl').read_text().splitlines()]
    assert len(rows) == len(attempts) == 4 + 12 + blocks * 6 + stages * 2
    assert all(r['exit'] == 0 and not r.get('timeout') for r in attempts)
    manifest = json.loads((root / 'manifest.json').read_text())
    for name, digest in manifest['binaries'].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
    assert len(manifest['binaries']) == 6
    assert not any((root / ('work.sqlite' + suffix)).exists() for suffix in ('', '-wal', '-shm', '-journal'))
    assert len({r['response']['request_id'] for r in rows}) == len(rows)
    for r in rows:
        assert all(v == 0 for v in r['before_counts'].values())
        assert all(v == 1 for v in r['after_counts'].values())
        response = r['response']
        assert response['decision_outcome'] == 'allow' and response['outcome'] == 'evidence'
        assert response['matched_candidates'] == len(response['evidence']) == 1
        assert r['wall_ms'] > 0
    schedule = json.loads((root / 'schedule.json').read_text())
    contexts = [json.loads(line) for line in (root / 'context.jsonl').read_text().splitlines()]
    assert len(schedule) == blocks and len(contexts) == blocks * 3
    for kind in ('control', 'old', 'rebuilt'):
        assert sum(dict(entry)[kind] for entry in schedule) == blocks // 2
        for block, entry in enumerate(schedule):
            pair = [r for r in rows if r['kind'] == kind and r['block'] == block]
            first = dict(entry)[kind]
            assert [r['arm'] for r in pair] == [first, 1-first]
            assert len([c for c in contexts if c['kind'] == kind and c['block'] == block]) == 1
    def summary(a, b):
        differences = [y-x for x, y in zip(a, b)]
        ratios = [y/x for x, y in zip(a, b)]
        rng = random.Random(20260917)
        boot = [[], []]
        for _ in range(10000):
            indices = rng.choices(range(len(a)), k=len(a))
            boot[0].append(statistics.median([differences[i] for i in indices]))
            boot[1].append(statistics.median([ratios[i] for i in indices]))
        return dict(baseline_median=statistics.median(a), candidate_median=statistics.median(b),
                    median_difference=statistics.median(differences), median_ratio=statistics.median(ratios),
                    difference_interval=[sorted(boot[0])[249], sorted(boot[0])[9749]],
                    ratio_interval=[sorted(boot[1])[249], sorted(boot[1])[9749]],
                    baseline_max=max(a), candidate_max=max(b), candidate_slower=sum(d > 0 for d in differences))
    result = {'status': 'PILOT ONLY' if pilot else 'diagnostic; not acceptance', 'invocations': len(rows), 'pairs': {}}
    for kind in ('control', 'old', 'rebuilt'):
        pairs = [[next(r for r in rows if r['kind'] == kind and r['block'] == block and r['arm'] == arm)
                  for arm in (0, 1)] for block in range(blocks)]
        result['pairs'][kind] = {}
        for metric in ('wall_ms', 'cpu_ms'):
            def value(row):
                return row['wall_ms'] if metric == 'wall_ms' else 1000 * (row['usage_delta']['ru_utime'] + row['usage_delta']['ru_stime'])
            result['pairs'][kind][metric] = summary([value(p[0]) for p in pairs], [value(p[1]) for p in pairs])
    stage_rows = [r for r in rows if r['kind'] == 'stage']
    assert len(stage_rows) == stages * 2
    keys = set(stage_rows[0]['diagnostic']['stages'])
    assert keys and any(k.endswith('getSourceTrail') for k in keys)
    assert all(set(r['diagnostic']['stages']) == keys for r in stage_rows)
    result['stages'] = {}
    for key in sorted(keys):
        arms = [[next(r for r in stage_rows if r['block'] == block and r['arm'] == arm)['diagnostic']['stages'][key]
                 for block in range(stages)] for arm in (0, 1)]
        assert all(m['Calls'] > 0 and 0 <= m['ExclusiveNS'] <= m['InclusiveNS'] for arm in arms for m in arm)
        result['stages'][key] = {metric: summary([m[metric] for m in arms[0]], [m[metric] for m in arms[1]])
                                for metric in ('InclusiveNS', 'ExclusiveNS') if all(m[metric] > 0 for arm in arms for m in arm)}
    return result


if __name__ == '__main__':
    print(json.dumps(analyze(Path(sys.argv[1]), '--pilot' in sys.argv[2:]), indent=2))
