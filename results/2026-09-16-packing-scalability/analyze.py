"""Summarize every valid sample without trimming or selective reruns."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def percentile90(values):
    return sorted(values)[math.ceil(0.9 * len(values)) - 1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--comparison', type=Path, required=True)
    parser.add_argument('--baseline-allocations', type=Path, required=True)
    parser.add_argument('--candidate-allocations', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    all_rows = rows(args.comparison)
    groups = defaultdict(lambda: defaultdict(list))
    fields = ('corpus', 'question', 'history', 'size', 'packing')
    for row in all_rows:
        if row['stage'] == 'measured':
            if not row['valid']:
                raise ValueError('invalid measured attempt')
            groups[tuple(row[field] for field in fields)][row['arm']].append(row)
    cells = []
    for key, arms in sorted(groups.items()):
        if set(arms) != {'baseline', 'candidate'} or any(len(value) != 12 for value in arms.values()):
            raise ValueError('incomplete matched cell')
        baseline, candidate = arms['baseline'], arms['candidate']
        stats = {}
        for arm, values in arms.items():
            stats[arm] = {'wall_median_ms': statistics.median(r['wall_ms'] for r in values), 'wall_p90_ms': percentile90([r['wall_ms'] for r in values]), 'rss_median_kib': statistics.median(r['rss_kib'] for r in values), 'wall_samples_ms': [r['wall_ms'] for r in values]}
        b, c = stats['baseline'], stats['candidate']
        paired = {r['repeat']: r for r in baseline}
        wins = sum(r['wall_ms'] < paired[r['repeat']]['wall_ms'] for r in candidate)
        gates = {'median': c['wall_median_ms']-b['wall_median_ms'] <= max(b['wall_median_ms']*0.1, 2), 'p90': c['wall_p90_ms']-b['wall_p90_ms'] <= max(b['wall_p90_ms']*0.2, 5), 'rss': c['rss_median_kib']-b['rss_median_kib'] <= max(b['rss_median_kib']*0.1, 2048)}
        cells.append(dict(zip(fields, key), stats=stats, paired_wins=wins, improvement_percent=100*(1-c['wall_median_ms']/b['wall_median_ms']), gates=gates))
    primary = []
    for history, size in [('original', 0), ('mixed', 100)]:
        matched = [c for c in cells if c['corpus']=='documentation' and c['packing']=='exact-v1' and c['history']==history and c['size']==size]
        medians = {arm: statistics.median(v for c in matched for v in c['stats'][arm]['wall_samples_ms']) for arm in ('baseline','candidate')}
        improvement = 100*(1-medians['candidate']/medians['baseline'])
        primary.append({'history':history,'size':size,'wall_medians_ms':medians,'improvement_percent':improvement,'pass':len(matched)==3 and improvement>=15 and all(c['paired_wins']>=10 for c in matched)})
    allocations = defaultdict(dict)
    for arm, path in [('baseline',args.baseline_allocations),('candidate',args.candidate_allocations)]:
        grouped = defaultdict(list)
        for row in rows(path):
            if row['stage']=='diagnostic':
                grouped[tuple(row[field] for field in fields)].append(row['diagnostic'])
        for key, values in grouped.items():
            if len(values)!=3 or any(value['stages'] for value in values):
                raise ValueError('not three allocation-only measurements')
            allocations[key][arm] = {field:statistics.median(v[field] for v in values) for field in ('allocated_bytes','allocations','gc_cycles')}
    allocation_cells=[]
    for key, values in sorted(allocations.items()):
        allocation_cells.append(dict(zip(fields,key),stats=values,pass_gate=values['candidate']['allocated_bytes']<=values['baseline']['allocated_bytes']*1.1))
    result={'p90_method':'nearest rank, sample not population percentile','cells':cells,'primary':primary,'allocations':allocation_cells,'adopt':all(p['pass'] for p in primary) and all(all(c['gates'].values()) for c in cells) and all(c['pass_gate'] for c in allocation_cells),'samples':len([r for r in all_rows if r['stage']=='measured'])}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'adopt':result['adopt'],'primary':primary,'failed_guardrails':[c for c in cells if not all(c['gates'].values())],'allocation_failures':[c for c in allocation_cells if not c['pass_gate']]},indent=2))


if __name__ == '__main__':
    main()
