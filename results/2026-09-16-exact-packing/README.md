# Exact-content evidence packing

Opt-in exact packing fixes a small duplicate-displacement case and removes repeated
selected bytes in two passage fixtures. It does not improve the declared required
passage coverage in the repeated-content or documentation cases. Documentation
without exact duplicates returns the same evidence with additional output and
latency costs. These are development measurements, not a retrieval-superiority claim.

## Behavior and method

Compare `--packing-policy original` and `--packing-policy exact-v1` in the same
candidate executable. Original packing is also checked against a historical
executable. Both use unchanged query preparation, authorization, ranking, candidate
limit and released-text budgets. Exact packing retains the first fitting passage,
then omits later byte-equal text only against already selected passages.

Inputs and expected outcomes were frozen before measurement. There are 26 cases:
both segmentation policies for one 33-byte displacement case, two existing
repeated-content queries, and ten existing documentation queries at 8,192 bytes.
The frozen documentation is older than the feature; it is not regenerated from
current documentation. Fixture hashes and required source spans are in
[protocol.json](protocol.json). Its starting revision describes the original
protocol freeze; [manifest.json](manifest.json) records the migrated measurement
bases and exact measured source.

Each case uses one warmup pair and six measured pairs with alternating arm order.
Every query starts from a copy of the same closed historical seed store. A fresh
CLI process includes opening, verification, query, JSON output, close and exit.
Filesystem caches are warm; builds, snapshot copying, historical checks and result
validation are outside query timing. No model, network retrieval or QMD is used.
The host is shared, not a dedicated benchmark machine. No observations were removed
from the completed run and no population percentile is estimated from six samples.

An independent first-fitting exact-byte walk over the large-budget verified
ranking checks selection. Original results match the historical executable's
selected evidence, ranks, packet ID and accounting in all cases. Selected text is
checked against the full normalized representation digest and source byte ranges.
Actual historical stores reopen without rewriting canonical records; mixed v1/v2
trails remain readable by the candidate.

## Evidence retained

Unique selected text is a count of distinct byte strings, not a relevance score.
Useful evidence is the union of selected byte positions within a predeclared
required source passage. This strict source-span measure does not judge semantic
equivalence or answer quality. Copies from different sources are not corroboration.

| Case | Unique selected texts, original → exact | Repeated selected bytes | Required-span bytes retained | Released bytes |
| --- | --- | --- | --- | --- |
| Displacement, either policy | 1 → 2 | 11 → 0 | 0 → 22 of 22 | 22 → 33 |
| Storage classes, fixed-v1 | 2 → 2 | 0 → 0 | 184 → 184 | 5,970 → 5,970 |
| Orchard, fixed-v1 | 2 → 2 | 0 → 0 | 116 → 116 | 5,884 → 5,884 |
| Storage classes, passage-v1 | 4 → 6 | 4,860 → 0 | 184 → 184 | 7,914 → 5,055 |
| Orchard, passage-v1 | 3 → 6 | 5,832 → 0 | 116 → 116 | 7,892 → 5,055 |
| Documentation, both policies | Unchanged in all 20 cases | 0 → 0 | Unchanged in all 20 cases | Unchanged in all 20 cases |

The displacement case changes one budget omission to one duplicate omission and
retains the repair passage. Each repeated passage-v1 case changes four budget
omissions to zero and records seven duplicate omissions. The additional unique
text does not add coverage of either already-complete declared required passage.
Fixed repeated-content cases have two budget omissions in either arm, no duplicate
omissions and no benefit. There are no lifecycle-rejected candidates in this
measurement corpus; lifecycle and authorization checks are separate product tests.

Documentation has six complete required spans out of ten with fixed-v1 and seven
out of ten with passage-v1, unchanged by packing. Partial spans stay partial.
This comparison does not re-evaluate the earlier segmentation experiment or its
semantic-equivalence judgments.

## Costs and negative results

The following descriptive medians pool the indicated fixed set of queries, not a
population of future queries. [summary.json](summary.json) gives each case's six
observations, median, minimum and maximum; [metrics.jsonl](metrics.jsonl) includes
all 312 measured rows and 52 warmup rows.

| Cases | Measured rows per arm | Wall median ms, original → exact | Maximum ms, original → exact | Maximum RSS KiB, original → exact |
| --- | --- | --- | --- | --- |
| Displacement, fixed-v1 | 6 | 58.88 → 47.19 | 63.49 → 68.52 | 15,452 → 15,608 |
| Displacement, passage-v1 | 6 | 56.09 → 48.74 | 68.48 → 62.09 | 15,384 → 15,384 |
| Repeated fixtures, fixed-v1 | 12 | 56.61 → 61.89 | 73.13 → 73.37 | 17,544 → 17,532 |
| Repeated fixtures, passage-v1 | 12 | 69.63 → 78.36 | 207.56 → 89.69 | 19,968 → 18,408 |
| Documentation, fixed-v1 | 60 | 66.49 → 68.97 | 316.54 → 82.20 | 17,616 → 18,172 |
| Documentation, passage-v1 | 60 | 106.23 → 128.37 | 137.47 → 398.27 | 20,540 → 20,784 |

The faster small-case medians are not evidence of a general speedup. Passage-v1
documentation is slower in every case's median despite identical evidence. V2
requires content/ancestry verification in addition to text-free structural checks;
this experiment does not isolate the cost of each validation step. That overhead
supports keeping exact packing opt-in, not weakening validation.

All outliers remain visible: 398.27 ms for the exact passage documentation
`partial` case; 316.54 ms for original fixed documentation `migration`; and
207.56 ms for original passage storage classes. They do not establish a tail
percentile. No additional run was selected to replace these observations.

Serialized query output grows by 65 bytes in either small case. With unchanged
selection it grows by approximately 58 bytes for policy/count fields, with possible
one-digit timing variation. Repeated passage output shrinks from median
14,618 to 9,921 bytes for storage classes and 14,610 to 9,941 for orchard.
Output includes JSON/provenance, which is outside the released-text budget.

Closed query stores use 413,696 bytes for the small case and 434,176 for fixed
repeated fixtures in either arm. Passage repeated fixtures grow from 442,368 to
446,464 bytes with v2 history. Documentation stores remain 479,232 bytes for fixed
and 516,096–520,192 for passage. Page-granular equality does not mean zero logical
record overhead. Query CPU time is also retained; GNU time's hundredth-second
resolution is coarse at these latencies. Documentation passage pooled median
user+system CPU rises from 0.09 to 0.11 seconds. RSS is a per-process peak, not
simultaneous process-tree memory. Allocations were not measured.

## Failed measurement attempt

The first attempt stopped after 46 CLI calls, including 24 measured calls. Its
Python inspection helper exited a SQLite transaction context without closing the
connection. Retained WAL state contaminated later copied-store history, and the
historical executable rejected a v2 field. Those timings are invalid and excluded
from the completed-run summary, not treated as a product regression.
[aborted-observations.jsonl](aborted-observations.jsonl) preserves every completed
observation from that attempt. The fix closes inspection connections explicitly
and checks that neither source nor destination has WAL/SHM sidecars before copying.
The same frozen inputs and bounded protocol were then rerun in full. There was no
parameter tuning or fixture change based on results.

## Provenance and reproduction

[manifest.json](manifest.json) binds source revisions, source/input/binary hashes,
environment and all files here. [observations.jsonl](observations.jsonl) contains
all 526 completed CLI observations, including non-measured compatibility checks.
It omits repeated full text and absolute temporary paths while retaining selected
segment/provenance/range identities, counts, serialized sizes and resource samples.
Text can be recovered from the frozen fixtures and selected byte ranges. Source
identities use absolute directory roots: another checkout location changes IDs
and may change tie order. Both arms always use the same root within a run.

`fixtures.tar.gz` preserves all ten original fixture files, including trailing
blank lines that affect segmentation. The archive verifier checks each regular
member against the original protocol hash before extraction. Packaging changed
after measurement; input bytes, the executed script and the protocol did not.

The historical binary was built from local snapshot `34381bb`; its 69 runtime/test
Go files match public Mousa base `3c355a17b66a7f1c7505043d223687672858c726` byte-for-byte,
as recorded in [baseline-runtime-manifest.json](baseline-runtime-manifest.json).
The candidate's measurement-time local commit and patch hash are explicit, not
presented as a public commit. Publication mapping is recorded in the manifest.

Build the baseline from the public base above and the candidate from the published
commit mapped in the manifest, in separate Mousa checkouts, using Go 1.27.1 for the
measured toolchain. Both binaries used `CGO_ENABLED=0 go build -o mousa ./cmd/mousa`;
the candidate build explicitly set `GOAMD64=v1`. Measurements set `GOMAXPROCS=6`.
Then, with Python 3.9 or later and GNU time, verify and unpack a scratch copy:

```sh
python3 tools/verify_results.py
cp -R results/2026-09-16-exact-packing /path/to/scratch-run
tar -xzf /path/to/scratch-run/fixtures.tar.gz -C /path/to/scratch-run
python3 /path/to/scratch-run/measure.py \
  --mousa /path/to/candidate/mousa \
  --baseline /path/to/baseline/mousa \
  --output /path/to/new-output-directory
```

The output directory must not exist. The published script was used for the
completed run. Required assertions and subprocess failures return nonzero.
`python3 tools/verify_results.py` checks archived hashes; it does not rerun this
experiment or prove the interpretation of its results.
