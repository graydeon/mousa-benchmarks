#!/usr/bin/env python3
"""Compare frozen selections and denial wrappers without hiding unknown fields."""
import argparse
import json
from pathlib import Path
import sys

import run


def denied_wrappers(observed):
    wrappers = []
    for record in observed['records']:
        spec = record['schedule']
        if spec.get('outcome') != 'deny' or spec.get('params', {}).get('name') != 'mousa_trail':
            continue
        result = json.loads(record['response']['text'])['result']['structuredContent']['result']
        # These are the fresh audit identity and the explicitly requested identity, not payload.
        wrappers.append({key: value for key, value in result.items()
                         if key not in ('authorization_decision_id', 'trail_id')})
    return wrappers


def compare(left, right):
    if not run.same_json(left['selections'], right['selections']):
        raise ValueError('cross-capture-historical-selection')
    a, b = denied_wrappers(left), denied_wrappers(right)
    if not a or not b or not all(run.same_json(a[0], wrapper) for wrapper in a + b):
        raise ValueError('denial-existence-nondisclosure')
    return {'selections_equal': True, 'selections': len(left['selections']),
            'denied_wrappers_per_capture': [len(a), len(b)], 'denial_wrappers_equal': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('left', type=Path)
    parser.add_argument('right', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(compare(run.load_capture(args.left), run.load_capture(args.right))))
        return 0
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
