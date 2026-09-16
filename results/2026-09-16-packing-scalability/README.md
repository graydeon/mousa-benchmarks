# Exact packing and accumulated trail history

This study separates current-query packing costs from the cost of reopening a
store containing earlier policy decisions and Source Trails. It uses three
unchanged passage-documentation questions (`install`, `budget`, and `trail`)
and the 33-byte duplicate-displacement case from the preceding
[exact-packing study](../2026-09-16-exact-packing). It is not a retrieval-quality
comparison or evidence for changing the default packing policy.

## Protocol

`protocol.json` was frozen before candidate implementation. Its SHA-256 is
`52dd143378ffb9a5a1528f56a87670e2d12fe836ae1977071d5b10a9cbdbfb0a`.
The product baseline is
`d1c01b1a76afcda6e644cb68ce18bd29dd3d6b64`; the benchmark repository baseline is
`f1bd9d7d9c8358f9bbaff6844eeb35459787d957`.

The measured candidate's 109 source-manifest files match published product
commit [`462c5d1`](https://github.com/graydeon/mousa/commit/462c5d14f38f268aff932e21d5d4e03eb267a269),
merged in [PR #27](https://github.com/graydeon/mousa/pull/27).
`provenance.json` records this later publication separately from the uncommitted
state at measurement time. Research documentation was added after measurement.

The corpus bytes, passage segmentation, query strings, 100-candidate limit,
original query-term policy, and byte budgets stay fixed. Documentation queries
return 48 candidates; displacement returns three. No fixture was regenerated
from newer documentation. The archive retains all ten original fixture files;
this study uses the documentation and small-displacement corpora only.

History sizes are 0, 10, and 100 trails. Original-only histories contain v1
trails. Mixed histories alternate original and exact packing, yielding 5 v1 plus
5 v2 trails at size 10 and 50 of each at size 100. Each history query has a fresh
request identity and appends one decision and one trail. Documentation histories
cycle through the three questions; displacement histories repeat `amber`.

Seeds use the supported JSONL sync interface with fixed external source names,
not directory-root identities. This avoids scratch-directory paths in canonical
records. These are newly created stores, not copies of the preceding study's
stores. Original and mixed histories have the same corpus, query sequence and
trail count, but different request IDs, evaluation times, canonical trail
schemas and database page layouts. Each baseline/candidate pair copies the
*same* closed history snapshot. The two size-zero history labels are byte-equal;
only one is measured.

Each of the 40 question/history/packing cells has one warmup pair and 12 measured
pairs. Baseline/candidate order alternates. Packing modes are separate blocks;
mode-to-mode wall comparisons are descriptive, not independently randomized
mode effects. The candidate comparison uses uninstrumented executables.
Diagnostic runs use three repetitions per cell and separate binaries.

Adoption requires at least a 15% pooled median wall-time reduction for exact
packing on documentation at both size zero and mixed-history size 100, with at
least 10 of 12 paired wins for every documentation question in those cells.
Every cell must also meet these ceilings:

- Median regression no greater than the larger of 10% or 2 ms.
- Sample p90 regression no greater than the larger of 20% or 5 ms.
- Median peak RSS increase no greater than the larger of 10% or 2,048 KiB.
- Median allocation-byte increase no greater than 10%.
- Unchanged stable evidence, packet identity, accounting and source coordinates;
  passing integrity and product correctness checks.

The p90 calculation is the nearest-rank order statistic, not an estimate of a
population tail. Every observation is retained; no outlier is trimmed. History
sizes do not exceed 100. CLI calls have a 90-second deadline and each experiment
job has a 3,600-second deadline.

## Snapshot and measurement checks

Before the longer run, the harness exercised creation, queries in both modes,
close, copy, reopen and trail inspection. A live WAL snapshot was deliberately
rejected. Python inspection uses `contextlib.closing`; a transaction context
alone does not close a SQLite connection. Every copy requires absent WAL, SHM
and rollback-journal sidecars and matching file hashes. Inspection checks
`quick_check`, WAL mode, table counts and ID-keyed canonical records. Reopening
must not change those records; a query must preserve their existing bytes while
adding exactly one decision and one trail. The external byte inventory covers
tables with both `id` and `record_json`, including trails and policy decisions.
It excludes observation-keyed ingest receipts. Store opening still runs the
product's canonical receipt checks; this inventory is not an independent proof
of every store invariant.

The harness records elapsed wall time, GNU `time` CPU time and peak RSS, output
bytes, response data, fresh request identities and snapshot inventories. Copying
and external validation are outside the timed CLI interval. The interval
includes process launch, store opening, the operation, JSON output and process
exit. Filesystem caches are not flushed.

Diagnostic binaries record call counts and inclusive and exclusive elapsed time
for opening, version verification, historical trail verification, canonical
trail reads, exact-content verification, ancestry walks, segment reads, policy
evaluation, retrieval, packing, persistence, response assembly and serialization.
These scopes nest. **Do not add their inclusive times or cumulative CPU-profile
percentages.** Exclusive stage times exclude instrumented child scopes, not
uninstrumented functions. Diagnostic wall time is excluded from adoption.

Allocation-only binaries add a `runtime.MemStats` reading at entry to `main` and
another after the command. Their `TotalAlloc` and `Mallocs` deltas cover command
execution, not package initialization. They have no stage timers. Allocation
bytes measure cumulative Go allocation, not live heap size or peak RSS. Peak RSS
comes from the uninstrumented comparisons. CPU-profile tables describe a
separate instrumented mixed-history reopen.

## Baseline diagnosis

The diagnostic documentation pooled medians were:

| History | Original query wall, ms | Exact query wall, ms | Historical verification, original/exact query, ms |
| --- | ---: | ---: | ---: |
| 0 trails | 102.85 | 127.49 | 0.11 / 0.11 |
| 10 original trails | 235.97 | 244.06 | 105.97 / 108.65 |
| 100 original trails | 1,328.00 | 1,343.43 | 1,084.35 / 1,110.48 |
| 10 mixed trails | 475.06 | 469.60 | 329.89 / 333.64 |
| 100 mixed trails | 3,637.22 | 3,711.55 | 3,379.16 / 3,443.06 |

Current-query work remained approximately 43–74 ms across those groups. Every
writable open runs both the existing read-only preflight and writable
verification. At mixed-history size 100, those passes together performed 4,800
historical ancestry walks. The current original query added 48 walks; the exact
query added 96. The documentation candidates derive from only two
representations.

For the exact `install` query at size zero, median trail read-back was 18.53 ms.
It included 16.75 ms in exact-content verification, which included 11.57 ms in
48 ancestry walks. Current retrieval separately spent 16.50 ms on another 48
walks. Constructing and packing the trail took 0.27 ms. Repeated ancestry work,
not the byte-equality packing loop, is a measured contributor to the overhead.
This does not attribute every millisecond of the previous study's increase.

The mixed-history CPU profile attributed 95.74% cumulative sampled CPU to
opening, 91.93% to historical trail verification, and 50.67% to ancestry walks.
Those percentages overlap. SQL preparation, canonical decoding, segment reads
and other verification remain real costs; the profile does not justify skipping
checks or reusing validity across operations.

## Adopted change and uninstrumented comparison

The candidate reuses canonical ancestry by representation within one retrieval
or one exact-trail read. Standalone trail reads and each historical trail scan
hold a read transaction, so reuse is confined to one snapshot. The reuse maps
are local to a retrieval or trail, not a store-wide or history-wide cache.
Both opening verification passes remain. Every trail, candidate projection,
segment, digest, available byte string and lifecycle decision is still checked.
Historical v1 bytes, v2 decoding, packet identity and packing defaults are unchanged.

The frozen adoption criteria passed on 960 measured invocations, plus 80
warmups. Exact documentation improved by 24.18% at size zero and 55.27% at
mixed-history size 100. Size-zero paired wins were 11/12 for `budget` and 12/12
for the other two questions; all three size-100 mixed cases won 12/12 pairs.
All 40 cells passed the latency, RSS and allocation guardrails.

| History | Packing | Baseline median, ms | Candidate median, ms |
| --- | --- | ---: | ---: |
| 0 trails | original | 100.88 | 90.94 |
| 0 trails | exact | 125.50 | 95.15 |
| 10 original trails | original | 238.35 | 210.04 |
| 10 original trails | exact | 256.55 | 215.86 |
| 100 original trails | original | 1,370.42 | 1,110.23 |
| 100 original trails | exact | 1,420.95 | 1,099.24 |
| 10 mixed trails | original | 468.57 | 266.73 |
| 10 mixed trails | exact | 488.81 | 268.56 |
| 100 mixed trails | original | 3,739.90 | 1,648.98 |
| 100 mixed trails | exact | 3,719.80 | 1,663.85 |

These are pooled documentation medians. The duplicate-benefit seed control was
slower: original packing went from 49.34 to 54.27 ms (+9.9944%), narrowly inside
the predeclared 10% ceiling; exact packing went from 53.90 to 55.87 ms (+3.65%).
That margin does not establish reliable small-case non-regression on a shared
host. No rerun was used to improve it. At 100 mixed trails, the same small case
improved from 460.74 to 380.60 ms for original packing and 472.31 to 387.52 ms
for exact packing. The repair passage remained selected only by exact packing.

Candidate diagnostics reduced current documentation ancestry walks from 48 to
2 for original packing and from 96 to 4 for exact packing. At 100 mixed trails,
historical walks fell from 4,800 to 200; all 200 historical trail reads across
the two opening passes remained. Candidate historical verification for exact
documentation queries had a pooled diagnostic median of 1,490.62 ms, compared
with 3,443.06 ms before. History cost is still substantial and grows with trail
count. Transaction-scoped reads also change statement-level transaction work;
this comparison does not isolate that effect from ancestry reuse.

For the exact `install` query, allocation-only median bytes during `main` fell
from 7,980,608 to 5,707,232 at size zero, and from 336,463,928 to 223,070,880
with 100 mixed trails. The latter allocation count fell from 4,547,670 to
2,957,069. Original-only history has much less allocation benefit: the same
size-100 query used 165,271,232 versus 164,996,104 bytes, while its allocation
count increased from 2,083,903 to 2,093,472.

Pooled exact-documentation peak-RSS medians were 18,610 versus 18,204 KiB at
size zero and 22,736 versus 22,894 KiB at 100 mixed trails. The largest
per-cell median RSS increase was 1,276 KiB. Lower cumulative allocation does
not imply proportionally lower resident memory.

Focused shared-representation regressions passed for ancestry, later-segment
and later-text damage, repair/reopen, and a concurrent writer with a pinned read
snapshot. Full Go tests, race tests, vet, module tidiness and verification, and
the required two-test CLI client acceptance suite passed. Stable query outputs,
packet IDs, accounting, coordinates and inventoried historical bytes matched
throughout the comparison.

Two unsuccessful attempts are retained separately. The first smoke stopped
after seed creation because its inventory assumed every `record_json` table
had an `id` column; ingest receipts use `observation_id`. The first candidate
test run stopped before measurements because the damage fixture violated a SQL
CHECK instead of reaching canonical verification. The fixture was corrected to
use an oversized but SQL-valid end coordinate. Neither failure supplied a
candidate timing sample. No timed comparison was repeated.

## Evidence index

- `protocol.json`, `fixtures.tar.gz`: frozen design and byte-identical inputs.
- `summary.json`: all 40 cells, sample values, primary criteria and guardrails.
- `baseline-diagnostic-summary.json`, `candidate-diagnostic-summary.json`:
  stage counts and inclusive/exclusive timing summaries.
- `raw-results.tar.xz`: individual calls, diagnostics, allocation probes,
  snapshot inventories, warmups and unsuccessful-attempt records.
- `provenance.json`, the two source manifests, and `manifest.json`:
  revisions, source/input/binary hashes, environment and file checksums.
- `cpu-top.txt`, `cpu-cumulative.txt`: baseline mixed-history CPU-profile tables.
- `measure.py`, `instrument.py`, `analyze.py`: reproduction and analysis tools.

## Limits

This is a small repeated corpus on a shared host, with warm filesystem caches.
It does not measure changing corpora, sustained concurrent writers, larger
histories, population latency tails or general retrieval quality. A snapshot
used for a whole historical scan can retain WAL pages until that scan finishes.
The correctness check exercises a concurrent writer, but does not measure
sustained WAL growth or contention.

The earlier negative exact-packing results remain unchanged. Text-free history
still cannot recover or re-prove retired bytes. Original packing remains the
default; exact packing remains opt-in.

## Reproduction

Use Linux, Go with the product's module dependencies available, Python 3.9 or
later with `sqlite3`, and GNU `time` at `/usr/bin/time`. The measurements use
Go 1.27.1, Python 3.13.5, `CGO_ENABLED=0`, `GOAMD64=v1` and `GOMAXPROCS=6`.
The managed VM has six vCPUs, a 5.5-core job quota and an 8 GiB job memory limit,
on a shared Ryzen 7 2700X host with an EPYC-compatible virtual CPU and NVMe
storage. These are not dedicated-host or cold-filesystem measurements.

Keep baseline and candidate source in separate disposable checkouts. Check the
source files against the supplied source manifests before building. Do not add
diagnostic instrumentation to a product checkout intended for publication.
Build the uninstrumented executables first:

```sh
export CGO_ENABLED=0 GOAMD64=v1 GOMAXPROCS=6
(cd baseline-source && go build -o ../baseline ./cmd/mousa)
(cd candidate-source && go build -o ../candidate ./cmd/mousa)
```

In another disposable baseline copy, run `instrument.py SOURCE_DIRECTORY`, then
`gofmt` and build `baseline-diagnostic`. The default instrumentation adds stage
timers and optional CPU profiling. Run the smoke before the longer diagnosis:

```sh
python3 measure.py --baseline ./baseline --diagnostic ./baseline-diagnostic --output smoke --smoke
python3 measure.py --baseline ./baseline --diagnostic ./baseline-diagnostic --output baseline-diagnosis
python3 measure.py --baseline ./baseline --candidate ./candidate --seeds baseline-diagnosis/seeds --output comparison
```

Output directories must not already exist. The diagnosis creates and retains
the closed history seeds. The comparison reuses those exact files; it does not
regenerate their histories. A rerun naturally creates new request IDs and
evaluation times, so regenerated store hashes will differ.

For allocation measurements, apply `instrument.py SOURCE_DIRECTORY allocations`
to separate clean baseline and candidate copies, format and build each one.
Pass each resulting binary as `--diagnostic`, retaining the uninstrumented
baseline in `--baseline` and the same `--seeds` directory. This runs three
allocation probes per cell. Use distinct `allocations-base` and
`allocations-candidate` output directories. Do not use these binaries for the
wall-time adoption comparison.

Run the default stage instrumentation separately on a clean candidate copy to
inspect changed counts and costs. `PACKING_CPU_PROFILE` names an optional CPU
profile file; the harness uses it for the size-100 mixed-history status operation.
Finally, compute the frozen comparison:

```sh
python3 analyze.py --comparison comparison/observations.jsonl --baseline-allocations allocations-base/observations.jsonl --candidate-allocations allocations-candidate/observations.jsonl --output summary.json
```

Inspect `adopt`, every guardrail result, and the retained samples. A successful
analysis process does not imply that the adoption criteria passed.
