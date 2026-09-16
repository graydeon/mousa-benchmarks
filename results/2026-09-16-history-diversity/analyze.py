"""Verify archived members and recompute comparison gates without rerunning queries."""
import hashlib
import json
from pathlib import Path
import statistics
import tarfile

root = Path(__file__).resolve().parent
expected = json.loads((root / 'archive-members.json').read_text())
found = {}
rows = None
with tarfile.open(root / 'raw-results.tar.xz') as archive:
    for member in archive:
        if (not member.isfile() or member.name not in expected or member.name in found
                or member.size > 64 * 1024 * 1024):
            raise SystemExit('Invalid archive member: ' + member.name)
        data = archive.extractfile(member).read()
        found[member.name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        if member.name == 'comparison/comparison.jsonl':
            rows = [json.loads(line) for line in data.splitlines()]
if found != expected or rows is None:
    raise SystemExit('Archive membership or hashes disagree')
if len(rows) != 360 or len({r['response']['request_id'] for r in rows}) != 360:
    raise SystemExit('Missing observations or reused request identities')
stable_keys = ['evidence', 'packet_id', 'used_bytes', 'budget_bytes', 'budget_omitted',
               'matched_candidates', 'lifecycle_excluded', 'expression', 'duplicate_omitted',
               'packing_policy', 'outcome', 'candidate_limit', 'query_policy',
               'decision_outcome', 'decision_reasons']
summary = []
for fixture in ('small', 'shared', 'diverse'):
    for history in (0, 200):
        for policy in ('original', 'exact-v1'):
            cell = [r for r in rows if (r['fixture'], r['history'], r['policy']) == (fixture, history, policy)]
            stable = [{k: r['response'].get(k) for k in stable_keys} for r in cell]
            if len(cell) != 30 or any(value != stable[0] for value in stable):
                raise SystemExit('Candidate output differs or cell is incomplete')
            arms = {}
            for arm in ('baseline', 'candidate'):
                wall = [r for r in cell if r['arm'] == arm and r['kind'] == 'wall']
                if len(wall) != 12 or {r['repetition'] for r in wall} != set(range(12)):
                    raise SystemExit('Missing or duplicate timing sample')
                allocation = [r['diagnostic']['allocated_bytes'] for r in cell if r['arm'] == arm and r['kind'] == 'allocation']
                if len(allocation) != 1 or any(r['exit'] != 0 for r in cell):
                    raise SystemExit('Invalid comparison cell')
                arms[arm] = {'median_ms': statistics.median(r['wall_ms'] for r in wall),
                             'max_ms': max(r['wall_ms'] for r in wall),
                             'median_rss_kib': statistics.median(r['rss_kib'] for r in wall),
                             'allocated_bytes': allocation[0]}
            b, c = arms['baseline'], arms['candidate']
            ratio = c['median_ms'] / b['median_ms']
            gates = {'latency': ratio <= (0.85 if history == 200 and fixture != 'small' else 1.10),
                     'tail': c['max_ms'] <= b['max_ms'] * 1.25,
                     'rss': c['median_rss_kib'] <= b['median_rss_kib'] + max(2048, b['median_rss_kib'] * .15),
                     'allocation': c['allocated_bytes'] <= b['allocated_bytes'] * 1.10}
            summary.append(dict(fixture=fixture, history=history, policy=policy, arms=arms,
                                latency_percent=(ratio - 1) * 100, gates=gates))
result = {'cells': summary, 'pass': all(all(r['gates'].values()) for r in summary)}
if result != json.loads((root / 'summary.json').read_text()):
    raise SystemExit('Published summary disagrees with all archived observations')
print('Verified', len(found), 'archive members and', len(rows), 'observations; adoption gates:', result['pass'])
