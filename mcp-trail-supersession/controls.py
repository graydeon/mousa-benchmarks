#!/usr/bin/env python3
"""Regenerate rehashed semantic controls without storing a full copy per mutation."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys

import run


def record_named(observed, name):
    return next(row for row in observed['records'] if row['schedule']['name'] == name)


def change_reply(row, change):
    reply = json.loads(row['response']['text'])
    envelope = reply['result']['structuredContent']
    change(envelope['result'])
    reply['result']['content'][0]['text'] = run.canonical(envelope)
    row['response'] = run.stream(run.encoded(reply))


def change_request(row, value, metadata=False):
    frame = json.loads(row['request']['text'])
    frame['params']['arguments']['supersession'] = value
    row['request'] = run.stream(run.encoded(frame))
    if metadata:
        row['schedule']['params']['arguments']['supersession'] = value


def controls(capture, output):
    original = run.load_capture(capture)
    active = 'active-original-inspect-true'
    legacy = 'association-original-inspect-true'
    denied = 'denied-active-original-true'
    cases = [
        ('contradictory-wire-input', active + ':wire-schedule-binding'),
        ('true-to-one', active + ':wire-schedule-binding'),
        ('false-to-zero', 'active-original-inspect-false:wire-schedule-binding'),
        ('coherent-metadata-and-wire', active + ':schedule-binding'),
        ('repeated-generated-key', active + ':request-no-repeated-keys'),
        ('repeated-top-level-key', active + ':request-no-repeated-keys'),
        ('mutated-historical-member', active + ':recorded-member'),
        ('fabricated-v3-member', legacy + ':member-presence'),
        ('mutated-producing-request', active + ':producing-request_id'),
        ('mutated-producing-trail', active + ':producing-id'),
        ('mutated-producing-packet', active + ':producing-packet_id'),
        ('mutated-v3-association', legacy + ':association-projection'),
        ('undeclared-history-field', active + ':closed-output-schema'),
        ('incorrect-v3-member-expectation', legacy + ':member-presence'),
        ('false-denial-write-expectation', denied + ':fresh-decision-count'),
        ('recorded-false-assertion', active + ':recorded-member'),
        ('altered-intentional-raw-frame', 'invalid-duplicate:raw-request-bytes'),
        ('ordinary-roundtrip', None),
        ('ordinary-key-order', None),
    ]
    receipts = []
    output.mkdir(parents=True, exist_ok=False)
    for name, detector in cases:
        # JSON round-trip removes archive deduplication aliases before one targeted mutation.
        observed = json.loads(run.encoded(original))
        target = record_named(observed, active)
        if name == 'contradictory-wire-input':
            change_request(target, False)
        elif name == 'true-to-one':
            change_request(target, 1)
        elif name == 'false-to-zero':
            change_request(record_named(observed, 'active-original-inspect-false'), 0)
        elif name == 'coherent-metadata-and-wire':
            change_request(target, 1, metadata=True)
        elif name == 'repeated-generated-key':
            text = target['request']['text'].replace('"supersession":true',
                                                     '"supersession":true,"supersession":true')
            target['request'] = run.stream(text.encode())
        elif name == 'repeated-top-level-key':
            text = target['request']['text'].replace('"jsonrpc":"2.0"',
                                                     '"jsonrpc":"2.0","jsonrpc":"2.0"')
            target['request'] = run.stream(text.encode())
        elif name == 'mutated-historical-member':
            change_reply(target, lambda result: result['historical']['supersession'].__setitem__('consulted', False))
        elif name == 'fabricated-v3-member':
            member = json.loads(target['response']['text'])['result']['structuredContent']['result']['historical']['supersession']
            change_reply(record_named(observed, legacy),
                         lambda result: result['historical'].__setitem__('supersession', copy.deepcopy(member)))
        elif name.startswith('mutated-producing-'):
            field = {'request': 'request_id', 'trail': 'id', 'packet': 'packet_id'}[name.rsplit('-', 1)[1]]
            change_reply(target, lambda result: result['historical'].__setitem__(field, 'b' * 64))
        elif name == 'mutated-v3-association':
            change_reply(record_named(observed, legacy),
                         lambda result: result['historical']['associated'][0].__setitem__('basis', 'fabricated'))
        elif name == 'undeclared-history-field':
            change_reply(target, lambda result: result['historical'].__setitem__('undeclared', True))
        elif name in ('incorrect-v3-member-expectation', 'false-denial-write-expectation', 'recorded-false-assertion'):
            assertion = next(row for row in observed['assertions'] if row['id'] == detector)
            if name == 'recorded-false-assertion':
                assertion['passed'] = False
            else:
                assertion['expected'] = True if name == 'incorrect-v3-member-expectation' else 0
                assertion['passed'] = True
        elif name == 'altered-intentional-raw-frame':
            row = record_named(observed, 'invalid-duplicate')
            row['request'] = run.stream(row['request']['text'].replace('"supersession":false', '"supersession":true').encode())
        elif name == 'ordinary-key-order':
            frame = json.loads(target['request']['text'])
            target['request'] = run.stream((json.dumps(dict(reversed(list(frame.items())))) + '\n').encode())
        path = output / (name + '.json.gz')
        run.write_capture(path, observed)
        command = [sys.executable, str(run.ROOT / 'run.py'), 'replay', '--output', str(path)]
        result = subprocess.run(command, capture_output=True, text=True)
        reason = result.stderr.strip()
        named = reason.partition(':')[2].split(',')
        passed = (result.returncode == 0 if detector is None
                  else result.returncode == 1 and detector in named)
        receipts.append({'name': name, 'expected_detector': detector, 'exit': result.returncode,
                         'stdout': result.stdout, 'stderr': result.stderr,
                         'sha256': run.sha(path.read_bytes()), 'bytes': path.stat().st_size,
                         'passed': passed})
        run.save(output / 'receipts.json', receipts)
        print(name, result.returncode, 'PASS' if passed else 'FAIL', flush=True)
    return 0 if all(row['passed'] for row in receipts) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    return controls(args.capture, args.output)


if __name__ == '__main__':
    sys.exit(main())
