# Explicit chronological source scenarios

These independently authored synthetic inputs exercise the optional Mousa
project-history consumer through real native stdio processes. Two named sources
share an item ID but have different content and attribution. Sixteen ordered
steps cover creation, exact replay, successive corrections, omission, tombstone,
repeated deletion, restore, explicit revert, empty active content, normalization,
a committed prefix followed by an invalid item, and explicit repair. Each
consumer command starts a fresh process. Epoch labels are fixture order, not
elapsed time or authenticated timestamps.

`example/alpha.json` and `beta.json` use `mousa-project-history-v2`.
`scenario.json` freezes expected native actions, active-item counts, exact
normalized spans and four mode/budget cases. `manifest.json` binds their original
bytes. Generate the same inputs in a new directory with:

```sh
python3 datasets/chronology/generate.py --out /tmp/chronology-inputs
```

## Run and analyze

Requires Linux, Python 3.9 or later, a matching Mousa checkout with the v2
consumer, and its built native executable. Go and SQLite remain the runtime and
canonical authority. There is no workload-model call, semantic judge, copied
transport, progress database or automatic retry. From this repository, with the
product checkout at `../mousa`:

```sh
python3 datasets/chronology/run.py --mousa ../mousa/mousa --source ../mousa --dataset datasets/chronology/example --store /tmp/chronology.sqlite --out /tmp/chronology-run
python3 datasets/chronology/analyze.py /tmp/chronology-run
python3 datasets/chronology/analyze_test.py --run /tmp/chronology-run
```

The store and output directory must be new. `apply EPOCH` applies only the named
epoch. Omission never deletes an item, restore supplies content and revert
explicitly references old content. Known invalid fixture operations are rejected
by consumer preflight. One separate native-boundary step uses the maintained
consumer's `Client` to send a valid item followed by an invalid item; native
`invalid_item`, `completed_items: 1` and `failed_item: 2` are required. Its native
operation remains FAIL even when the scenario assertion passes. No subprocess
exit is invented for this in-process client call; the native server's actual
exit is retained. Repair is a later explicit invocation, not an inferred replay.

Reports preserve source commit/tree, dirty state, consumed source member hashes,
binary/input/runner/analyzer identities, ordered receipt references, invocations,
consumer exit codes and native process outcomes. `members.json` binds every run
member, including copied frozen inputs and `summary.json`. Decoded JSON receipts
preserve requests and responses, not original wire framing. Missing, modified,
substituted or extra members are invalid evidence. Hashes establish consistency,
not authenticity against complete rewriting.

The runner stops after an unexpected execution failure, retains the committed
prefix and partial capture, and marks the run INCOMPLETE. Unexecuted operations
are not appended as successes. The analyzer distinguishes failed assertions,
missing capture and invalid evidence. `COMPLETE` is execution completion;
`assertion_status: PASS` additionally requires all 84 expected operations and
mechanical lifecycle/evidence checks. Consumer PASS alone is not scenario PASS.

## Comparison units and limits

Four frozen cases run under `original`/`dedup` query policies and
`original`/`exact-v1` packing with identical active content and budgets. Query
tracing adds audit records, not content mutations. Each query is followed by a
fresh-authorized, text-free trail inspection. The analyzer reconciles selected
segment identities and omission counts/reasons with native receipts. Original
trails do not expose an explicit omission reason; the analyzer reports that
absence rather than manufacturing a native field.

Coverage is the number of required complete normalized byte spans contained in
released passages, divided by the frozen required-span count. A zero denominator
is not evidence of answer support. Required/irrelevant passage counts use these
explicit span labels, not semantic judgment. Evidence bytes sum released UTF-8
text; rendered context bytes count the actual consumer context, including
headers and the question. Budgets do not bound the rendered context or an entire
model prompt. Selected source/item/representation identities remain visible.

The near-match question has no required spans yet can release lexical evidence.
The tiny budget can omit the entire required multibyte passage. Preserve both
observations; do not optimize policies against these cases. The mode arms are
repeated observations of four cases, not sixteen independent quality cases.
No timing, model-answer accuracy, context-window safety, authenticated authorship,
desktop acceptance or elapsed-years retention claim follows from this workflow.
Native-host/model-driven acceptance remains NOT RUN.
