"""Frozen identities, strict serialization and lossless SQLite receipt storage."""
import gzip
import io
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import select
import stat
import sqlite3
import struct
import tarfile
import tempfile

PROTOCOL_SHA = '72fc39d6e8f46466ff39293f6246a44cd0409ba467b405046d2d23026f0169b2'
PRODUCT = 'ff80838c607ab8cde5b89376b9a9f44c1deb13cf'
TREE = '5c18c9d14248c693759f20c93d47d84da98b691f'
ACCEPTED = 'b45f720f9d0164b9dabfd5714a3cda32fa07073d'
HERE = Path(__file__).resolve().parent
ENV = {'GOMAXPROCS': '1', 'HOME': 'home', 'TMPDIR': 'tmp', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'PATH': '/usr/bin:/bin'}
BUDGET = 2147483648
RESERVE = 16777216


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def loads(raw):
    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite JSON: ' + value)
    def finite(value):
        number = float(value)
        require(math.isfinite(number), 'nonfinite JSON number')
        return number
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite)


def json_frames(raw):
    """Decode strict JSONL frames and report the first failure's raw byte offset."""
    values, offset = [], 0
    for line in raw.splitlines(keepends=True):
        try:
            require(line.endswith(b'\n'), 'incomplete JSON frame')
            values.append(loads(line))
        except ValueError as error:
            return values, {'class': type(error).__name__, 'message': str(error), 'byte_offset': offset}
        offset += len(line)
    return values, None


def receipt_json(raw):
    if raw.startswith(b'\x1f\x8b'):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream, io.BytesIO() as expanded:
            while True:
                block = stream.read(65536)
                if not block:
                    break
                require(expanded.tell()+len(block) <= BUDGET-RESERVE, 'expanded receipt workspace budget')
                expanded.write(block)
            raw = expanded.getvalue()
    return loads(raw)


def read_json(path):
    return receipt_json(Path(path).read_bytes())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.'+path.name+'-', delete=False) as stream:
        temporary = stream.name
        raw = canonical(value)+b'\n'
        stream.write(gzip.compress(raw, mtime=0) if path.suffix == '.gz' else raw)
    os.replace(temporary, path)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def protocol(path=None):
    raw = Path(path or HERE / 'protocol.json').read_bytes()
    require(sha(raw) == PROTOCOL_SHA, 'protocol identity mismatch')
    return loads(raw)


def preflight():
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'requires Linux/amd64')
    require(hasattr(os, 'pidfd_open') and hasattr(os, 'wait4') and hasattr(select, 'poll'), 'missing pidfd/poll/wait4')
    fd = os.pidfd_open(os.getpid())
    try:
        poll = select.poll()
        poll.register(fd, select.POLLIN)
        poll.poll(0)
    finally:
        os.close(fd)


def file_identity(path):
    path = Path(path)
    if not path.exists():
        return None
    require(path.is_file() and not path.is_symlink(), 'not a regular file: ' + str(path))
    return {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}


def physical(path):
    return {suffix or 'main': file_identity(str(path) + suffix) for suffix in ('', '-wal', '-shm', '-journal')}


def validate_physical(observation, missing_main=False):
    require(type(observation) is dict and set(observation) == {'main', '-wal', '-shm', '-journal'}, 'physical observation fields')
    require(missing_main or observation['main'] is not None, 'missing main-file observation')
    for identity in observation.values():
        if identity is None:
            continue
        require(type(identity) is dict and set(identity) == {'bytes', 'sha256'}, 'physical identity fields')
        require(type(identity['bytes']) is int and identity['bytes'] >= 0, 'physical byte-count type')
        digest = identity['sha256']
        require(type(digest) is str and len(digest) == 64 and all(c in '0123456789abcdef' for c in digest), 'physical digest')


def quoted(name):
    return '"' + name.replace('"', '""') + '"'


def typed(value):
    if value is None:
        return ['null', None]
    if type(value) is int:
        return ['integer', str(value)]
    if type(value) is float:
        return ['real', struct.pack('>d', value).hex()]
    if type(value) is str:
        return ['text', value.encode().hex()]
    if type(value) is bytes:
        return ['blob', value.hex()]
    raise ValueError('unsupported SQLite value')


def snapshot(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('BEGIN')
        schema = connection.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT GLOB 'sqlite_*' ORDER BY type,name").fetchall()
        tables = {}
        for kind, name, _, _ in schema:
            if kind != 'table':
                continue
            rows = [[typed(v) for v in row] for row in connection.execute('SELECT * FROM ' + quoted(name))]
            rows.sort(key=canonical)
            tables[name] = {'columns': [list(r) for r in connection.execute('PRAGMA table_xinfo(' + quoted(name) + ')')], 'rows': rows,
                            'count': len(rows), 'sha256': sha(b''.join(canonical(row) + b'\n' for row in rows))}
        return {'schema': [list(row) for row in schema], 'application_id': connection.execute('PRAGMA application_id').fetchone()[0],
                'user_version': connection.execute('PRAGMA user_version').fetchone()[0], 'tables': tables}
    finally:
        connection.close()


def decoded_rows(state, table):
    info = state['tables'][table]
    names = [c[1] for c in info['columns'] if c[6] != 1]
    def value(field):
        kind, raw = field
        if kind == 'null':
            return None
        if kind == 'integer':
            return int(raw)
        if kind == 'real':
            return struct.unpack('>d', bytes.fromhex(raw))[0]
        if kind == 'text':
            return bytes.fromhex(raw).decode()
        if kind == 'blob':
            return bytes.fromhex(raw)
        raise ValueError('invalid SQLite type')
    return [dict(zip(names, map(value, row))) for row in info['rows']]


def validate_snapshot(state):
    require(type(state) is dict and set(state) == {'schema', 'tables', 'application_id', 'user_version'}, 'snapshot envelope')
    require(type(state['schema']) is list and type(state['tables']) is dict, 'snapshot schema/tables')
    require(type(state['application_id']) is int and type(state['user_version']) is int, 'snapshot header types')
    for row in state['schema']:
        require(type(row) is list and len(row) == 4 and row[0] in ('table', 'index', 'view', 'trigger')
                and type(row[1]) is str and type(row[2]) is str and (row[3] is None or type(row[3]) is str), 'snapshot schema row')
    require(state['schema'] == sorted(state['schema'], key=lambda row: (row[0], row[1])), 'snapshot schema order')
    require({row[1] for row in state['schema'] if row[0] == 'table'} == set(state['tables']), 'snapshot table coverage')
    for table in state['tables'].values():
        require(set(table) == {'columns', 'rows', 'count', 'sha256'}, 'snapshot table envelope')
        require(type(table['columns']) is list and type(table['rows']) is list, 'snapshot table types')
        for index, column in enumerate(table['columns']):
            require(type(column) is list and len(column) == 7, 'snapshot column metadata')
            require(type(column[0]) is int and column[0] == index and type(column[1]) is str and type(column[2]) is str, 'snapshot column identity')
            require(type(column[3]) is int and column[3] in (0, 1) and (column[4] is None or type(column[4]) is str)
                    and type(column[5]) is int and column[5] >= 0 and type(column[6]) is int and column[6] in (0, 1, 2, 3), 'snapshot column attributes')
        visible = sum(column[6] != 1 for column in table['columns'])
        require(type(table['count']) is int and table['count'] == len(table['rows']), 'snapshot cardinality')
        require(table['rows'] == sorted(table['rows'], key=canonical), 'snapshot row order')
        for row in table['rows']:
            require(type(row) is list and len(row) == visible, 'snapshot row width')
            for field in row:
                require(type(field) is list and len(field) == 2, 'typed field shape')
                kind, value = field
                if kind == 'null':
                    require(value is None, 'typed null')
                elif kind == 'integer':
                    require(type(value) is str and str(int(value)) == value, 'typed integer')
                else:
                    require(kind in ('text', 'blob', 'real') and type(value) is str and bytes.fromhex(value).hex() == value, 'typed value')
                    if kind == 'real':
                        require(len(value) == 16, 'typed real')
                    if kind == 'text':
                        bytes.fromhex(value).decode('utf-8')
        require(table['sha256'] == sha(b''.join(canonical(row) + b'\n' for row in table['rows'])), 'snapshot row digest')


class Objects:
    def __init__(self, root):
        self.root = Path(root)

    def put(self, raw):
        require(not (self.root / 'objects').is_symlink(), 'object directory link')
        digest = sha(raw)
        path = self.root / 'objects' / digest
        descriptor = Path(str(path)+'.ref')
        require(not path.is_symlink() and not descriptor.is_symlink(), 'object link')
        if descriptor.exists():
            ref = {'sha256': digest, 'bytes': len(raw)}
            require(self.get(ref) == raw, 'object collision')
            return ref
        if path.exists():
            require(path.is_file(), 'object file type')
            require(path.read_bytes() == raw, 'object collision')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        return {'sha256': digest, 'bytes': len(raw)}

    def put_file(self, path):
        """Retain a closed, immutable regular file without duplicating its storage."""
        identity = file_identity(path)
        require(identity is not None, 'missing closed receipt file')
        target = self.root / 'objects' / identity['sha256']
        require(not target.parent.is_symlink() and not target.is_symlink(), 'object link')
        require(not Path(str(target)+'.ref').is_symlink(), 'object link')
        if Path(str(target)+'.ref').exists():
            self.get(identity)
        elif target.exists():
            require(file_identity(target) == identity, 'object collision')
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.link(path, target)
        return identity

    def put_snapshot(self, state):
        """Store a lossless row trie; unchanged native history shares leaf bytes."""
        raw = canonical(state)
        ref = {'sha256': sha(raw), 'bytes': len(raw)}
        path = self.root / 'objects' / ref['sha256']
        if path.exists() or Path(str(path)+'.ref').exists():
            require(self.get(ref) == raw, 'snapshot collision')
            return ref

        def tree(rows, depth=0):
            if len(rows) <= 16 or depth == 64:
                return self.put(canonical({'rows': [row for _, row in rows]}))
            buckets = {}
            for digest, row in rows:
                buckets.setdefault(digest[depth], []).append((digest, row))
            return self.put(canonical({'children': {key: tree(group, depth+1) for key, group in buckets.items()}}))

        header = {key: value for key, value in state.items() if key != 'tables'}
        tables = {}
        for name, table in state['tables'].items():
            metadata = {key: value for key, value in table.items() if key != 'rows'}
            rows = [(sha(canonical(row)), row) for row in table['rows']]
            tables[name] = self.put(canonical({'metadata': self.put(canonical(metadata)), 'rows': tree(rows)}))
        recipe = self.put(canonical({'header': self.put(canonical(header)), 'tables': tables}))
        save(str(path)+'.ref', {'bytes': len(raw), 'snapshot': recipe})
        require(self.get(ref) == raw, 'lossless snapshot reconstruction')
        return ref

    def get(self, ref):
        return self._get(ref, set())

    def _get(self, ref, active):
        require(type(ref) is dict and set(ref) == {'sha256', 'bytes'}, 'object reference fields')
        require(not (self.root / 'objects').is_symlink(), 'object directory link')
        digest = ref['sha256']
        require(type(digest) is str and len(digest) == 64 and all(c in '0123456789abcdef' for c in digest), 'object reference')
        require(type(ref['bytes']) is int and 0 <= ref['bytes'] <= BUDGET-RESERVE, 'object size')
        require(digest not in active, 'cyclic object reference')
        active.add(digest)
        path = self.root / 'objects' / digest
        descriptor = Path(str(path)+'.ref')
        require(not path.is_symlink() and not descriptor.is_symlink(), 'object link')
        require(not (path.exists() and descriptor.exists()), 'ambiguous object reference')
        try:
            if descriptor.exists():
                require(descriptor.is_file(), 'object descriptor type')
                specification = read_json(descriptor)
                require(set(specification) == {'bytes', 'snapshot'} and type(specification['bytes']) is int
                        and specification['bytes'] == ref['bytes'], 'snapshot descriptor size')
                def read(ref):
                    return loads(self._get(ref, active))
                def rows(ref, depth=0):
                    nonlocal expanded_bytes
                    require(depth <= 64, 'snapshot trie depth')
                    node = read(ref)
                    if set(node) == {'rows'}:
                        require(type(node['rows']) is list, 'snapshot trie rows')
                        expanded_bytes += sum(len(canonical(row))+1 for row in node['rows'])
                        require(expanded_bytes <= ref_size, 'snapshot expansion size')
                        return node['rows']
                    require(set(node) == {'children'} and all(key in '0123456789abcdef' and len(key) == 1 for key in node['children']), 'snapshot trie node')
                    result = []
                    for child in node['children'].values():
                        result.extend(rows(child, depth+1))
                    return result
                expanded_bytes, ref_size = 0, ref['bytes']
                recipe = read(specification['snapshot'])
                state = read(recipe['header'])
                state['tables'] = {}
                for name, table_ref in recipe['tables'].items():
                    table = read(table_ref)
                    metadata = read(table['metadata'])
                    metadata['rows'] = sorted(rows(table['rows']), key=canonical)
                    state['tables'][name] = metadata
                raw = canonical(state)
            else:
                require(path.is_file(), 'object file type')
                require(path.stat().st_size == ref['bytes'], 'object file size')
                raw = path.read_bytes()
            require(ref['bytes'] == len(raw) and sha(raw) == digest, 'object identity')
            return raw
        finally:
            active.remove(digest)

    def json(self, ref):
        return receipt_json(self.get(ref))


def workspace_bytes(root):
    total = 0
    seen = set()
    pending = [os.fspath(root)]
    while pending:
        try:
            entries = os.scandir(pending.pop())
        except FileNotFoundError:
            continue
        with entries:
            for entry in entries:
                try:
                    info = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    # SQLite sidecar removal and atomic saves retire names.
                    continue
                require(not stat.S_ISLNK(info.st_mode), 'workspace link')
                if stat.S_ISDIR(info.st_mode):
                    pending.append(entry.path)
                else:
                    identity = (info.st_dev, info.st_ino)
                    if identity not in seen:
                        seen.add(identity)
                        total += info.st_size
    return total


def safe_member(name):
    require(type(name) is str and '\0' not in name and ':' not in name, 'unsafe archive path')
    path = PurePosixPath(name)
    require(name and not path.is_absolute() and '\\' not in name and all(p not in ('', '.', '..') for p in name.split('/')), 'unsafe archive path')


class BudgetFile:
    """Bound compressed writes without consuming the failure-receipt reserve."""
    def __init__(self, stream, remaining):
        self.stream, self.remaining = stream, remaining

    def write(self, raw):
        require(len(raw) <= self.remaining, 'packaging workspace budget; raw evidence retained')
        written = self.stream.write(raw)
        self.remaining -= written
        return written

    def __getattr__(self, name):
        return getattr(self.stream, name)


def pack(root, output, budget_root=None):
    root, output = Path(root), Path(output)
    require(root.is_dir() and not root.is_symlink(), 'archive source directory type')
    require(not output.exists() and not output.is_symlink(), 'archive already exists/link')
    require(root.resolve() not in output.resolve().parents, 'archive output must be outside evidence directory')
    budget_root = Path(budget_root or root.parent).resolve()
    require(budget_root in output.resolve().parents, 'archive outside campaign budget root')
    require(budget_root.is_dir() and budget_root in root.resolve().parents, 'archive input outside campaign budget root')
    available = BUDGET-RESERVE-workspace_bytes(budget_root)
    require(available > 0, 'packaging workspace budget before archive')
    manifest_path = Path(str(output)+'.members.json')
    require(not manifest_path.exists() and not manifest_path.is_symlink(), 'archive manifest already exists')
    manifest = []
    files = sorted(p for p in root.rglob('*') if p.is_file())
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'archive link')
        require(path.is_dir() or path.is_file(), 'archive source type')
    for path in files:
        name = path.relative_to(root).as_posix()
        safe_member(name)
        identity = file_identity(path)
        require(identity['bytes'] <= 33554432, 'archive member exceeds 32 MiB')
        manifest.append({'name': name, **identity})
    manifest_bytes = len(canonical(manifest))+1
    require(manifest_bytes <= 6291456, 'manifest public blob exceeds 6 MiB; raw evidence retained')
    require(manifest_bytes <= available, 'packaging workspace budget before manifest')
    save(manifest_path, manifest)
    with output.open('xb') as stream, tarfile.open(fileobj=BudgetFile(stream, available-manifest_bytes),
                                                 mode='w|gz', format=tarfile.USTAR_FORMAT) as archive:
        for entry in manifest:
            info = tarfile.TarInfo(entry['name'])
            info.size = entry['bytes']
            with (root / entry['name']).open('rb') as member_stream:
                archive.addfile(info, member_stream)
    require(output.stat().st_size <= 4194304, 'compressed archive exceeds 4 MiB; archive and manifest preserved locally')
    return manifest


class RegularMember(tarfile.TarInfo):
    def _proc_member(self, archive):
        # Reject extension headers before tarfile reads attacker-sized payloads.
        require(self.type in (tarfile.REGTYPE, tarfile.AREGTYPE) and not self.issparse(), 'archive member type')
        require(0 <= self.size <= 33554432, 'archive member size')
        return super()._proc_member(archive)


def unpack(archive_path, output):
    archive_path, output = Path(archive_path), Path(output)
    require(archive_path.is_file() and not archive_path.is_symlink(), 'archive input type')
    manifest_path = Path(str(archive_path)+'.members.json')
    require(manifest_path.is_file() and not manifest_path.is_symlink() and manifest_path.stat().st_size <= 6291456, 'manifest type/public blob limit')
    require(archive_path.stat().st_size <= 4194304, 'compressed archive exceeds 4 MiB')
    expected = read_json(str(archive_path) + '.members.json')
    require(len({e['name'] for e in expected}) == len(expected), 'duplicate manifest member')
    for entry in expected:
        safe_member(entry['name'])
        require(type(entry['bytes']) is int and 0 <= entry['bytes'] <= 33554432, 'manifest member size')
        require(type(entry['sha256']) is str and len(entry['sha256']) == 64 and all(c in '0123456789abcdef' for c in entry['sha256']), 'manifest digest')
    expected_by_name = {entry['name']: entry for entry in expected}
    require(not output.exists() and not output.is_symlink(), 'replay output already exists/link')
    budget_root = output.parent.resolve()
    require(budget_root.is_dir(), 'replay campaign parent missing')
    fixed = workspace_bytes(budget_root)
    if budget_root not in archive_path.resolve().parents:
        fixed += archive_path.stat().st_size+manifest_path.stat().st_size
    seen, total = set(), 0
    with tarfile.open(archive_path, 'r:gz', tarinfo=RegularMember) as archive:
        for member in archive:
            safe_member(member.name)
            require(member.isfile() and not member.issparse() and member.name not in seen, 'archive member type/duplicate')
            require(0 <= member.size <= 33554432, 'archive member size')
            total += member.size
            require(fixed+total <= BUDGET-RESERVE, 'archive combined workspace budget')
            raw = archive.extractfile(member).read(member.size + 1)
            identity = {'name': member.name, 'bytes': len(raw), 'sha256': sha(raw)}
            require(identity == expected_by_name.get(member.name), 'archive member identity')
            seen.add(member.name)
            path = output / member.name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    require(seen == {e['name'] for e in expected}, 'archive membership')
