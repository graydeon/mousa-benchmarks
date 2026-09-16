"""Matched packing queries and bounded trail histories on closed SQLite snapshots."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tarfile
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def no_sidecars(path):
    for suffix in ('-wal', '-shm', '-journal'):
        if Path(str(path) + suffix).exists():
            raise ValueError(f'contaminated snapshot: {path.name}{suffix}')


def inventory(path):
    no_sidecars(path)
    with closing(sqlite3.connect(path)) as db:
        if db.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
            raise ValueError('invalid SQLite snapshot')
        if db.execute('PRAGMA journal_mode').fetchone() != ('wal',):
            raise ValueError('expected WAL journal mode')
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name")]
        records = {}
        for table in tables:
            columns = {row[1] for row in db.execute(f'PRAGMA table_info("{table}")')}
            if {'id', 'record_json'} <= columns:
                records[table] = dict(db.execute(f'SELECT hex(id),hex(record_json) FROM "{table}" ORDER BY id'))
        counts = {name: db.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0] for name in ('source_trails', 'source_trail_candidates', 'policy_decisions', 'segments', 'representations', 'segment_lexical_rows')}
        versions = dict(db.execute("SELECT json_extract(record_json,'$.schema'),count(*) FROM source_trails GROUP BY 1"))
    no_sidecars(path)
    return {'records': records, 'counts': counts, 'versions': versions, 'bytes': path.stat().st_size, 'sha256': digest(path)}


def copy_seed(seed, target):
    no_sidecars(seed)
    no_sidecars(target)
    if target.exists():
        raise ValueError('target already exists')
    shutil.copyfile(seed, target)
    if digest(seed) != digest(target):
        raise ValueError('snapshot copy mismatch')


def append(path, row):
    with path.open('a') as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--diagnostic', type=Path)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--seeds', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    inputs = Path(__file__).resolve().parent
    protocol = json.loads((inputs / 'protocol.json').read_text())
    fixtures = out / 'fixtures'
    fixtures.mkdir()
    with tarfile.open(inputs / 'fixtures.tar.gz') as archive:
        members = archive.getmembers()
        if {m.name for m in members} != {'fixtures/' + name for name in protocol['manifest']}:
            raise ValueError('fixture archive membership mismatch')
        for member in members:
            if not member.isfile() or member.size > 1048576 or '..' in Path(member.name).parts or Path(member.name).is_absolute():
                raise ValueError('invalid fixture archive member')
            name = member.name.removeprefix('fixtures/')
            path = fixtures / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.extractfile(member).read())
            if digest(path) != protocol['manifest'][name]:
                raise ValueError('fixture hash mismatch')
    binaries = {'baseline': args.baseline.resolve()}
    if args.candidate:
        binaries['candidate'] = args.candidate.resolve()
    if args.diagnostic:
        binaries['diagnostic'] = args.diagnostic.resolve()
    (out / 'provenance.json').write_text(json.dumps({'binaries': {k: digest(v) for k, v in binaries.items()}, 'protocol_sha256': digest(inputs / 'protocol.json'), 'fixture_archive_sha256': digest(inputs / 'fixtures.tar.gz')}, indent=2) + '\n')
    rows_path = out / 'observations.jsonl'
    request_ids = set()

    def call(arm, store, command, label, stdin=None, profile=False):
        cost = out / 'cost.txt'
        env = dict(os.environ)
        if profile:
            env['PACKING_CPU_PROFILE'] = str(out / ('cpu-' + label['corpus'] + '-' + label['history'] + '-' + str(label['size']) + '.pprof'))
        start = time.perf_counter_ns()
        try:
            proc = subprocess.run(['/usr/bin/time', '-f', '%M %U %S', '-o', str(cost), str(binaries[arm]), '-store', str(store), *command], input=stdin, capture_output=True, timeout=protocol['max_cli_seconds'], env=env)
        except subprocess.TimeoutExpired as error:
            append(rows_path, dict(label, arm=arm, valid=False, error='timeout', stdout=(error.stdout or b'').decode(errors='replace'), stderr=(error.stderr or b'').decode(errors='replace')))
            raise
        row = dict(label, arm=arm, wall_ms=(time.perf_counter_ns()-start)/1e6, exit_code=proc.returncode, stdout=proc.stdout.decode(), stderr=proc.stderr.decode(), valid=False)
        append(out / 'attempts.jsonl', row)
        if proc.returncode:
            append(rows_path, row)
            raise ValueError(f'CLI failed: {row}')
        rss, user, system = cost.read_text().split()
        response = json.loads(proc.stdout)
        row.update(response=response, rss_kib=int(rss), user_s=float(user), system_s=float(system), output_bytes=len(proc.stdout), valid=True)
        del row['stdout']
        if arm == 'diagnostic':
            row['diagnostic'] = json.loads(row.pop('stderr'))
        elif row['stderr']:
            raise ValueError('unexpected stderr')
        append(rows_path, row)
        if 'request_id' in response:
            if response['request_id'] in request_ids:
                raise ValueError('reused request identity')
            request_ids.add(response['request_id'])
        no_sidecars(store)
        return response

    questions = protocol['questions']
    corpora = sorted({q['corpus'] for q in questions})
    seed_dir = args.seeds.resolve() if args.seeds else out / 'seeds'
    if not args.seeds:
        seed_dir.mkdir()
        for corpus in corpora:
            seed = seed_dir / f'{corpus}-original-0.sqlite'
            payload = ''.join(json.dumps({'id': str(p.relative_to(fixtures / corpus)), 'text': p.read_text()}) + '\n' for p in sorted((fixtures / corpus).rglob('*')) if p.is_file()).encode()
            call('baseline', seed, ['sync', '--source', 'packing-' + corpus, '--segment-policy', 'passage-v1'], {'stage': 'seed', 'corpus': corpus}, payload)
            initial = inventory(seed)
            if initial['counts']['source_trails'] != 0 or initial['counts']['policy_decisions'] != 0:
                raise ValueError('seed contains query history')
            append(out / 'snapshots.jsonl', dict(corpus=corpus, history='original', size=0, **initial))
            copy_seed(seed, seed_dir / f'{corpus}-mixed-0.sqlite')
            for history in protocol['histories']:
                work = out / 'grow.sqlite'
                copy_seed(seed, work)
                sequence = [q for q in questions if q['corpus'] == corpus]
                maximum = 2 if args.smoke else max(protocol['history_sizes'])
                for index in range(maximum):
                    q = sequence[index % len(sequence)]
                    packing = 'exact-v1' if history == 'mixed' and index % 2 else 'original'
                    call('baseline', work, ['query', '--source', 'packing-' + corpus, '--packing-policy', packing, '--budget-bytes', str(q['budget']), q['query']], {'stage': 'history', 'corpus': corpus, 'history': history, 'index': index, 'packing': packing})
                    if index+1 in protocol['history_sizes'] or args.smoke and index+1 == maximum:
                        snapshot = inventory(work)
                        if snapshot['counts']['source_trails'] != index+1 or snapshot['counts']['policy_decisions'] != index+1:
                            raise ValueError('history count mismatch')
                        append(out / 'snapshots.jsonl', dict(corpus=corpus, history=history, size=index+1, **snapshot))
                        copy_seed(work, seed_dir / f'{corpus}-{history}-{index+1}.sqlite')
                work.unlink()
    oracles = {}
    for q in questions:
        work = out / 'oracle.sqlite'
        seed = seed_dir / f"{q['corpus']}-original-0.sqlite"
        copy_seed(seed, work)
        response = call('baseline', work, ['query', '--source', 'packing-' + q['corpus'], '--budget-bytes', str(q['budget']), q['query']], {'stage': 'oracle', 'corpus': q['corpus'], 'question': q['id']})
        oracles[q['id'], 'original'] = response
        work.unlink()
        copy_seed(seed, work)
        exact = call('baseline', work, ['query', '--source', 'packing-' + q['corpus'], '--packing-policy', 'exact-v1', '--budget-bytes', str(q['budget']), q['query']], {'stage': 'oracle', 'corpus': q['corpus'], 'question': q['id']})
        oracles[q['id'], 'exact-v1'] = exact
        if q['corpus'] == 'documentation':
            if response['evidence'] != exact['evidence'] or response['packet_id'] != exact['packet_id']:
                raise ValueError('duplicate-free selection changed')
        else:
            if len({h['text'] for h in response['evidence']}) != 1 or len({h['text'] for h in exact['evidence']}) != 2:
                raise ValueError('displacement oracle failed')
        for packing, value in [('original', response), ('exact-v1', exact)]:
            for hit in value['evidence']:
                raw = (fixtures / q['corpus'] / hit['item']).read_bytes()
                if hashlib.sha256(raw).hexdigest() != hit['representation_sha256'] or raw[hit['byte_start']:hit['byte_end']] != hit['text'].encode():
                    raise ValueError('normalized source coordinates failed')
        work.unlink()
    sizes = [0, 2] if args.smoke else protocol['history_sizes']
    stable = ['evidence', 'packet_id', 'used_bytes', 'budget_omitted', 'matched_candidates', 'lifecycle_excluded', 'expression', 'duplicate_omitted', 'packing_policy']
    for history in protocol['histories']:
        for size in sizes:
            if history == 'mixed' and size == 0:
                continue
            for qi, q in enumerate(questions):
                seed = seed_dir / f"{q['corpus']}-{history}-{size}.sqlite"
                before = inventory(seed)
                for packing in ('original', 'exact-v1'):
                    modes = [('smoke', 1, list(binaries))] if args.smoke else ([('diagnostic', protocol['diagnostic_repeats'], ['diagnostic'])] if args.diagnostic else [('warmup', protocol['warmups'], list(binaries)), ('measured', protocol['pairs'], list(binaries))])
                    for stage, repeats, arms in modes:
                        for repeat in range(repeats):
                            order = arms if (repeat+qi+size)%2 else list(reversed(arms))
                            for arm in order:
                                work = out / 'query.sqlite'
                                copy_seed(seed, work)
                                label = dict(stage=stage, corpus=q['corpus'], question=q['id'], history=history, size=size, packing=packing, repeat=repeat)
                                response = call(arm, work, ['query', '--source', 'packing-' + q['corpus'], '--packing-policy', packing, '--budget-bytes', str(q['budget']), q['query']], label)
                                oracle = oracles[q['id'], packing]
                                if any(response.get(field) != oracle.get(field) for field in stable):
                                    raise ValueError('stable query output changed')
                                if response['matched_candidates'] != len(response['evidence']) + response['budget_omitted'] + response['lifecycle_excluded'] + response.get('duplicate_omitted', 0):
                                    raise ValueError('packing accounting mismatch')
                                after = inventory(work)
                                if after['counts']['source_trails'] != size+1 or after['counts']['policy_decisions'] != size+1:
                                    raise ValueError('query did not append one decision and trail')
                                if any(after['records'][table].get(key) != value for table, records in before['records'].items() for key, value in records.items()):
                                    raise ValueError('historical canonical record changed')
                                if args.smoke:
                                    call(arm, work, ['trail', '--source', 'packing-' + q['corpus'], response['trail_id']], dict(label, stage='inspection'))
                                work.unlink()
                if qi == next(i for i, value in enumerate(questions) if value['corpus'] == q['corpus']):
                    for arm in binaries:
                        work = out / 'status.sqlite'
                        copy_seed(seed, work)
                        call(arm, work, ['status', '--source', 'packing-' + q['corpus']], dict(stage='reopen', corpus=q['corpus'], history=history, size=size), profile=arm=='diagnostic' and size==100 and history=='mixed')
                        after = inventory(work)
                        if after['records'] != before['records']:
                            raise ValueError('reopen changed canonical history')
                        work.unlink()
    if args.smoke:
        seed = seed_dir / 'small-original-0.sqlite'
        contaminated = out / 'contaminated.sqlite'
        copy_seed(seed, contaminated)
        with closing(sqlite3.connect(contaminated)) as db:
            db.execute('CREATE TABLE contamination(value)')
            db.commit()
            try:
                copy_seed(contaminated, out / 'must-not-exist.sqlite')
            except ValueError as error:
                append(out / 'smoke-checks.jsonl', {'check': 'live WAL snapshot rejected', 'error': str(error), 'pass': True})
            else:
                raise ValueError('live WAL snapshot was accepted')
        no_sidecars(contaminated)
        contaminated.unlink()
    (out / 'PASS.json').write_text(json.dumps({'pass': True, 'fresh_requests': len(request_ids), 'smoke': args.smoke}) + '\n')
    print('PASS', out.name, len(request_ids), 'fresh requests')


if __name__ == '__main__':
    main()
