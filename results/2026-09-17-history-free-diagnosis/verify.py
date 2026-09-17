"""Verify diagnostic archive bytes and distinguish smoke from performance records."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

root = Path(__file__).resolve().parent
expected = json.loads((root / 'archive-members.json').read_text())
found = {}
with tarfile.open(root / 'raw-results.tar.xz') as archive:
    for member in archive:
        path = PurePosixPath(member.name)
        if (not member.isfile() or path.is_absolute() or '..' in path.parts
                or member.name not in expected or member.name in found
                or member.size > 1 << 20):
            raise SystemExit('Invalid archive member: ' + member.name)
        data = archive.extractfile(member).read()
        if expected[member.name] != {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}:
            raise SystemExit('Changed archive member: ' + member.name)
        found[member.name] = data
if set(found) != set(expected):
    raise SystemExit('Archive membership mismatch')
for prefix, count in (('failed-study', 1), ('close-only-smoke', 1), ('sidecar-safe-smoke', 4)):
    rows = [json.loads(line) for line in found[prefix + '/observations.jsonl'].splitlines()]
    if len(rows) != count or any(row['kind'] != 'smoke' for row in rows):
        raise SystemExit('Unexpected diagnostic observations: ' + prefix)
    for row in rows:
        response = row['response']
        if (row['exit'] != 0 or response['decision_outcome'] != 'allow'
                or response['outcome'] != 'evidence' or len(response['evidence']) != 1
                or response['matched_candidates'] != 1
                or row['before_counts'] != dict.fromkeys(('source_trails', 'source_trail_candidates', 'policy_decisions'), 0)
                or row['after_counts'] != dict.fromkeys(('source_trails', 'source_trail_candidates', 'policy_decisions'), 1)):
            raise SystemExit('Smoke response/count mismatch: ' + prefix)
for name, code in (('diagnostic-status.log', 1), ('smoke-status.log', 1), ('smoke2-status.log', 0)):
    receipt = json.loads(found['receipts/' + name])
    if receipt['exit_code'] != code:
        raise SystemExit('Worker outcome mismatch: ' + name)
print('Verified', len(found), 'lossless members; six smoke records; zero timed comparison pairs')
