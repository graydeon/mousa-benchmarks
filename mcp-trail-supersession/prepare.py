#!/usr/bin/env python3
"""Preparation helper for the MCP query supersession fixture; not an observation tool.

This script is *preparation*, not evidence. It derives the canonical revision,
declaration and activation identities the fixture needs, writes the frozen inputs, and
- with `--verify` - checks every derived identity against the product's own native
store and canonical command output. It is deliberately separate from `run.py`: the
standalone MCP client runner contains no identity codec and observes only the wire
behaviour of the executable it is given. Nothing here is an MCP observation, and the
runner never calls this script.

Usage:
    prepare.py --output <fixture-dir>                # write inputs/ and pins.json
    prepare.py --output <fixture-dir> --verify \
        --binary <mousa> --work <scratch-dir> --receipt <file>
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import struct
import subprocess
import sys

SOURCE_LABEL = 'fixture/mcp-query'
PREDECESSOR = 'predecessor'
DUPLICATE = 'duplicate'
SUCCESSOR = 'successor'
TEXTS = {
    PREDECESSOR: 'oldterm predecessor evidence',
    DUPLICATE: 'oldterm predecessor evidence',
    SUCCESSOR: 'oldterm successor evidence',
}
AUTHOR = 'fixture-author'
BASIS = 'synthetic fixture declaration'
ACTOR_ID = 'fixture-actor'
ACTOR_VERSION = '1'
OCCURRED_AT_USEC = 1700000000000000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tuple_id(*fields):
    fields = [field.encode() if isinstance(field, str) else field for field in fields]
    return sha(b''.join(struct.pack('>Q', len(field)) + field for field in fields))


def item_pins(source_id, item, text):
    """Canonical observation/artifact/representation/segment identities for one item.

    The native revision suffix is the hex encoding of the ASCII lowercase text SHA-256
    hexdigest, matching the product's `%x` formatting of its SHA256 formatter.
    """
    raw = text.encode()
    digest = hashlib.sha256(raw).digest()
    revision_suffix = digest.hex().encode().hex()
    observation = tuple_id('mousa.observation.v1', bytes.fromhex(source_id),
                           'item/' + item + '@' + revision_suffix)
    artifact = tuple_id('mousa.artifact.v1', bytes.fromhex(observation), 'body')
    representation = tuple_id('mousa.representation.v1', struct.pack('>Q', 1), 'artifact',
                              bytes.fromhex(artifact), 'mousa.text.normalize_utf8', '1',
                              hashlib.sha256(b'').digest(), 'text/plain; charset=utf-8', digest)
    segment = tuple_id('mousa.segment.v1', bytes.fromhex(representation),
                       'mousa.selector.text_byte_range.v1', struct.pack('>Q', 0),
                       struct.pack('>Q', len(raw)), digest)
    return {
        'text': text,
        'bytes': len(raw),
        'content_sha256': digest.hex(),
        'observation_id': observation,
        'artifact_id': artifact,
        'representation_id': representation,
        'segment_id': segment,
    }


def declaration_record(source_id, pins):
    fields = {
        'schema': 'mousa.supersession_declaration.v1',
        'source_id': source_id,
        'predecessor_item_id': PREDECESSOR,
        'predecessor_representation_id': pins[PREDECESSOR]['representation_id'],
        'successor_item_id': SUCCESSOR,
        'successor_representation_id': pins[SUCCESSOR]['representation_id'],
        'author': AUTHOR,
        'basis': BASIS,
    }
    identifier = tuple_id('mousa.supersession_declaration.v1', bytes.fromhex(source_id),
                          PREDECESSOR, bytes.fromhex(fields['predecessor_representation_id']),
                          SUCCESSOR, bytes.fromhex(fields['successor_representation_id']),
                          AUTHOR, BASIS)
    return {'schema': fields['schema'], 'id': identifier, **{k: v for k, v in fields.items()
                                                             if k != 'schema'}}


def activation_record(source_id, expected_previous, declaration_id):
    identifier = tuple_id('mousa.supersession_activation.v1', bytes.fromhex(source_id),
                          bytes.fromhex(expected_previous) if expected_previous else b'',
                          bytes.fromhex(declaration_id) if declaration_id else b'')
    return {'schema': 'mousa.supersession_activation.v1', 'id': identifier, 'source_id': source_id,
            'expected_previous_activation_id': expected_previous, 'declaration_id': declaration_id,
            'actor_id': ACTOR_ID, 'actor_version': ACTOR_VERSION,
            'occurred_at_usec': OCCURRED_AT_USEC, 'reason': 'synthetic fixture transition'}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode()


def build():
    source_id = tuple_id('mousa.source.v1', 'mousa-jsonl', SOURCE_LABEL)
    pins = {item: item_pins(source_id, item, text) for item, text in TEXTS.items()}
    declaration = declaration_record(source_id, pins)
    initial = activation_record(source_id, None, declaration['id'])
    deactivation = activation_record(source_id, initial['id'], None)
    items = [{'id': item, 'text': text} for item, text in TEXTS.items()]
    inputs = {
        'items.jsonl': b''.join(encoded(record) for record in items),
        'delete-successor.jsonl': encoded({'id': SUCCESSOR, 'deleted': True}),
        'declaration.json': encoded(declaration),
        'activation-initial.json': encoded(initial),
        'activation-deactivation.json': encoded(deactivation),
    }
    return {'source_label': SOURCE_LABEL, 'source_id': source_id, 'items': pins,
            'declaration': declaration, 'activation_initial': initial,
            'activation_deactivation': deactivation}, inputs


def write_fixture(output, fixture, inputs):
    if output.exists() and any(output.iterdir()):
        raise SystemExit('fixture output is not empty: ' + str(output))
    (output / 'inputs').mkdir(parents=True, exist_ok=True)
    for name, data in inputs.items():
        (output / 'inputs' / name).write_bytes(data)
    (output / 'pins.json').write_bytes(encoded({key: value for key, value in fixture.items()
                                                if key not in ('declaration', 'activation_initial',
                                                               'activation_deactivation')}))


def run(argv, payload=b'', cwd=None):
    result = subprocess.run(argv, input=payload, capture_output=True, cwd=cwd)
    return {'argv': argv, 'exit': result.returncode,
            'stdout': result.stdout.decode('utf-8', 'replace'),
            'stderr': result.stderr.decode('utf-8', 'replace')}


def rows(path, sql, parameters=()):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        return connection.execute(sql, parameters).fetchall()
    finally:
        connection.close()


def verify(fixture, inputs, args):
    """Check every prepared identity against the product's own store and output."""
    work = Path(args.work)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    store = work / 'preparation.sqlite'
    binary = str(Path(args.binary).resolve())
    receipt = {'method': ('Independent Python stdlib tuple derivation; the same pinned binary '
                          'then re-derives every revision identity through native sync, and the '
                          'declaration/activation canonical output is compared byte for byte. '
                          'Preparation evidence only; not an MCP observation.'),
               'source_label': fixture['source_label'], 'commands': []}

    def command(name, argv, payload=b''):
        actual = run([binary, '-store', str(store), *argv], payload, cwd=work)
        # Symbolic paths keep machine-specific locations out of the published receipt.
        record = {'step': name,
                  'argv': ['<binary>', '-store', '<work>/preparation.sqlite', *argv],
                  'exit': actual['exit'], 'stdout': actual['stdout'], 'stderr': actual['stderr']}
        receipt['commands'].append(record)
        if record['exit'] != 0:
            raise SystemExit('preparation command failed: ' + name + '\n' + record['stderr'])
        return record

    command('sync-items', ['sync', '--source', fixture['source_label']], inputs['items.jsonl'])
    source = bytes.fromhex(fixture['source_id'])
    checks = []
    for item, pin in fixture['items'].items():
        external = 'item/' + item + '@' + bytes.fromhex(pin['content_sha256']).hex().encode().hex()
        observation = rows(store, 'SELECT record_json FROM observations WHERE id = ?',
                           (bytes.fromhex(pin['observation_id']),))
        checks.append({'check': 'observation-record:' + item, 'expected': external,
                       'observed': json.loads(observation[0][0])['external_observation_id'] if observation else None})
        artifact = rows(store, 'SELECT id FROM artifacts WHERE id = ? AND observation_id = ?',
                        (bytes.fromhex(pin['artifact_id']), bytes.fromhex(pin['observation_id'])))
        checks.append({'check': 'artifact-row:' + item, 'expected': pin['artifact_id'],
                       'observed': artifact[0][0].hex() if artifact else None})
        representation = rows(store, 'SELECT id FROM representations WHERE id = ?',
                              (bytes.fromhex(pin['representation_id']),))
        checks.append({'check': 'representation-row:' + item, 'expected': pin['representation_id'],
                       'observed': representation[0][0].hex() if representation else None})
        segment = rows(store, 'SELECT id FROM segments WHERE id = ? AND representation_id = ?',
                       (bytes.fromhex(pin['segment_id']), bytes.fromhex(pin['representation_id'])))
        checks.append({'check': 'segment-row:' + item, 'expected': pin['segment_id'],
                       'observed': segment[0][0].hex() if segment else None})
        active = rows(store, 'SELECT representation_id FROM local_items WHERE source_id = ? AND item_id = ?',
                      (source, item))
        checks.append({'check': 'active-item:' + item, 'expected': pin['representation_id'],
                       'observed': active[0][0].hex() if active else None})
    put = command('declaration-put', ['supersession', 'declaration', 'put'], inputs['declaration.json'])
    checks.append({'check': 'declaration:canonical-bytes', 'expected': sha(inputs['declaration.json']),
                   'observed': sha(put['stdout'].encode())})
    put = command('activation-put', ['supersession', 'activation', 'put'], inputs['activation-initial.json'])
    checks.append({'check': 'activation:canonical-bytes', 'expected': sha(inputs['activation-initial.json']),
                   'observed': sha(put['stdout'].encode())})
    get = command('declaration-get', ['supersession', 'declaration', 'get', fixture['declaration']['id']])
    checks.append({'check': 'declaration:readback', 'expected': inputs['declaration.json'].decode(),
                   'observed': get['stdout']})
    state = command('activation-state', ['supersession', 'activation', 'state', fixture['source_id']])
    checks.append({'check': 'activation:projection',
                   'expected': {'source_id': fixture['source_id'],
                                'current_activation_id': fixture['activation_initial']['id'],
                                'active_declaration_id': fixture['declaration']['id']},
                   'observed': json.loads(state['stdout'])})
    damaged = [check for check in checks if check['expected'] != check['observed']]
    receipt['checks'] = checks
    receipt['failed'] = damaged
    receipt['binary_sha256'] = sha(Path(args.binary).resolve().read_bytes())
    Path(args.receipt).write_bytes(encoded(receipt))
    if damaged:
        raise SystemExit('prepared identity check failed: ' + json.dumps(damaged, indent=2))
    print('Verified', len(checks), 'prepared identities against the product store')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--work', type=Path)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    fixture, inputs = build()
    if args.verify:
        if not (args.binary and args.work and args.receipt):
            raise SystemExit('--verify requires --binary, --work and --receipt')
        return verify(fixture, inputs, args)
    write_fixture(args.output, fixture, inputs)
    print('Wrote fixture inputs to', args.output)
    return 0


if __name__ == '__main__':
    sys.exit(main())
