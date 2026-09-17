import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
from unittest.mock import patch

from analyze import analyze

root = Path(os.environ['OMP_OUTPUT'])
inp = Path(os.environ['OMP_INPUT']) / 'diagnostic'
for mode in ('exit', 'timeout', 'wal'):
    target = root / ('failure-' + mode)
    target.mkdir()
    shutil.copyfile('/bin/false', target / 'old-baseline')
    (target / 'old-baseline').chmod(0o755)
    if mode == 'wal':
        (target / 'work.sqlite-wal').write_bytes(b'live-sidecar')
    os.environ['OMP_OUTPUT'] = str(target)
    try:
        if mode == 'timeout':
            with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(['injected'], 30, output=b'partial')):
                runpy.run_path(str(inp / 'run.py'))
        else:
            runpy.run_path(str(inp / 'run.py'))
    except (AssertionError, subprocess.TimeoutExpired):
        pass
    else:
        raise AssertionError('failure did not stop: ' + mode)
    assert not (target / 'observations.jsonl').exists()
    if mode != 'wal':
        attempts = [json.loads(s) for s in (target / 'attempts.jsonl').read_text().splitlines()]
        assert len(attempts) == 1
        assert attempts[0].get('timeout') if mode == 'timeout' else attempts[0]['exit'] != 0
        assert (target / 'work.sqlite').exists()
    else:
        assert (target / 'work.sqlite-wal').read_bytes() == b'live-sidecar'
os.environ['OMP_OUTPUT'] = str(root)
broken = root / 'failure-analysis'
broken.mkdir()
for name in ('observations.jsonl', 'attempts.jsonl'):
    shutil.copyfile(root / name, broken / name)
with (broken / 'observations.jsonl').open('a') as stream:
    stream.write('{')
try:
    analyze(broken, True)
except json.JSONDecodeError:
    pass
else:
    raise AssertionError('truncated observations accepted')
print('Failure paths PASS: exit, timeout receipt, WAL refusal, truncated analysis')
