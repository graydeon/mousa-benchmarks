# Historical verification with diverse representations

## Result: candidate not adopted

Reusing verified canonical segments and representation/source membership within one
historical-scan snapshot substantially reduced query cost at 200 recorded trails.
It failed the predeclared small-case latency and tail guards, so the runtime change
was removed. The supported implementation remains the baseline. This report does
not supersede or replace the earlier packing-scalability study.

The comparison contains 288 measured CLI invocations, 24 labeled warmups,
24 separate stage-instrumented invocations and 24 separate allocation probes.
All observations, including outliers and an invalid diagnostic fixture attempt,
are preserved. No failed cell was rerun or omitted.

## Inputs and scope

Baseline: Mousa `e68be171b6dce5f4ee410aece1a655aa2009b78b`.
Companion repository before this study: `404fcc43feabb72bcd3db28c6e9d1a97c759ae60`.
The uncommitted candidate is exactly that baseline plus the patch in `candidate.patch.xz`;
`candidate-source-manifest.json` records all 117 submitted source-file hashes.
The patch includes the measured regression tests. A later test-only refinement
alternates rereads of both returned trails to strengthen the aliasing check;
it was not part of the measured binary. No candidate runtime code was adopted.

Three deterministic synthetic fixtures separate representation count from segment
count: small has one segment in one representation; shared has 32 segments in one
representation; diverse has 32 segments in 32 representations. Each fixed-v1 segment
is exactly 4096 UTF-8 bytes: `amber`, a unique decimal index, then ASCII spaces.
No segments are byte-equal. This is not a natural-document relevance evaluation.

Each fixture has closed SQLite snapshots at zero and 200 recorded trails. Histories
alternate original/v1 and exact-v1/v2 trails with 100 candidates as the retrieval
limit and an 8192-byte budget. The actual candidate counts are one or 32. A warm
supported `EvaluateAndTraceLexical` caller creates history outside measurements,
using the same authorization identity as the CLI. All histories contain allowed
candidates. Snapshot hashes and original JSONL bytes are archived. Every measured
invocation gets a byte-verified copy of the same seed; query history does not grow
between paired samples.

The managed worker used Go 1.27.1 on Linux/amd64, CGO_ENABLED=0, GOAMD64=v1 and
GOMAXPROCS=6. It had six virtual CPUs, an 8 GiB job memory limit and a 5.5-core job
quota, on a shared Ryzen 7 2700X desktop host. It was not dedicated benchmark
hardware. Environment and job receipts are archived. No GPU, model or network
service participates in retrieval or measurement.

## Cost model and candidate

Code inspection shows that each writable open performs two independent verification
passes. Canonical-record and lexical checks grow with stored records and segments.
Historical verification decodes every trail, verifies its ordered projections and
parent decision, and checks each referenced canonical segment. V2 also verifies
candidate digests, ranges, available indexed text, duplicate relationships and
ancestry. Existing ancestry reuse is per representation within one trail, not across
trails. Therefore its work sums distinct representations over all v2 trails; the
current query's candidate limit does not bound historical work.

A bounded baseline diagnostic at 200 trails measured about 2.0 seconds in historical
verification for shared and 3.7 seconds for diverse. In the diverse/exact probe,
canonical segment reads took 1172.33 ms and ancestry walks 1680.99 ms. These are
inclusive instrumented stage timings, not adoption measurements. The CPU profile
attributes 72.60% of sampled CPU cumulatively to historical verification,
23.59% to canonical segment reads and 31.76% to ancestry walks.

The candidate retained verified segment value structs and representation/source
membership pairs only inside one historical-scan read transaction. Each map held
at most 4096 entries; additional entries were verified without reuse. It retained
no text or mutable returned trails. Every trail still decoded its canonical bytes,
checked projections and parent agreement, and checked its own candidate digest,
size, available bytes and duplicate relationships. Both opening passes remained;
no state crossed operations or passes. Original packing remained the default.
No dependency, schema, public configuration, authorization or packet change was
proposed.

## Frozen comparison

`protocol.json` was frozen before observing candidate measurements. Each of the
12 fixture/history/packing cells has 12 paired uninstrumented calls, alternating
which binary runs first, after one labeled warmup per arm. Both binaries were built
and run in the same worker job with identical seeds and configuration.

Acceptance required at least 15% median wall-time improvement for both policies in
shared/diverse at 200 trails; no more than 10% median regression in every other
cell; no more than 25% regression in each cell's maximum observed latency; median
RSS no more than baseline plus the larger of 15% or 2048 KiB; and allocation bytes
no more than 10% above baseline. All stable evidence, packet IDs, ranks, scores,
text, coordinates, digests, accounting and policy outputs had to match. Request
identities had to remain fresh. All 48 numerical gates are recomputable from the
archive. Forty-five passed; three failed.

| Fixture | Trails | Packing | Baseline median ms | Candidate median ms | Change | Failed gates |
|---|---:|---|---:|---:|---:|---|
| small | 0 | original | 43.56 | 53.21 | +22.18% | latency |
| small | 0 | exact-v1 | 45.98 | 54.22 | +17.93% | latency |
| small | 200 | original | 507.10 | 434.65 | -14.29% | none |
| small | 200 | exact-v1 | 551.49 | 440.48 | -20.13% | none |
| shared | 0 | original | 73.01 | 74.93 | +2.63% | tail |
| shared | 0 | exact-v1 | 82.16 | 83.68 | +1.85% | none |
| shared | 200 | original | 2342.14 | 1210.65 | -48.31% | none |
| shared | 200 | exact-v1 | 2348.98 | 1210.82 | -48.45% | none |
| diverse | 0 | original | 156.80 | 165.77 | +5.73% | none |
| diverse | 0 | exact-v1 | 183.05 | 182.99 | -0.03% | none |
| diverse | 200 | original | 3988.31 | 1342.62 | -66.34% | none |
| diverse | 200 | exact-v1 | 4002.88 | 1296.84 | -67.60% | none |

The shared/history0/original maximum rose from 82.54 to 130.29 ms (+57.85%), failing
the tail guard even though its median passed. Both smallest history-free medians
failed their 10% ceilings. Their cause is unresolved. Shared-host contention or
sampling variation is not established as an explanation and does not excuse the
failures. The candidate was rejected without a favorable replacement run.

## Separate stage and resource observations

For diverse/history200/exact, the uninstrumented median fell from 4002.88 to
1296.84 ms. Separate instrumented opening time fell from 4095.55 to 1213.62 ms;
queryItems time was 42.53 versus 39.68 ms. These separate probes are not additive
components of the uninstrumented median. Opening is not the same as total process
startup, and neither is a persistent-store query benchmark.

Across both opening passes, all 400 historical trail reads remained. Historical
canonical segment reads fell from 19200 to 64, and ancestry walks from 6400 to 64.
This supports the repeated-work hypothesis for the exercised diverse history.
It does not overcome the failed adoption guards.

In separate allocation-only probes for that same cell, main-entry-to-main-exit
allocation bytes fell from 510458328 to 200260984. Median process peak RSS in the
wall-time samples was 23576 versus 22936 KiB. Allocation bytes are cumulative Go
allocations, not live memory, RSS or isolated startup allocations. Every RSS and
allocation gate passed. `summary.json` contains all resource values;
`stage-summary.json` contains separate stage attribution.

## Integrity, concurrency and limits

The candidate's focused store tests passed, including mixed v1/v2 reopen,
recomputed-identity false duplicates, ancestry/segment/text tampering, recovery,
candidate digest/size/source relationships and read snapshots. The new focused
concurrency check used a real independent SQLite writer connection and a pinned
historical reader. Sixteen committed projection changes completed while the
reader continued to observe the earlier canonical snapshot. A later historical
scan rejected the damage, and a repaired scan succeeded.

The reader retained 32 WAL frames with zero checkpointed frames and a 131872-byte
WAL. After reader release, a truncating checkpoint succeeded and WAL size was zero.
These SQL projection changes deliberately test tampering visibility; they are not
a supported sync-throughput benchmark. The bounded check establishes writer
progress and WAL retention/release, not sustained multiwriter behavior or a WAL
improvement over baseline. Returned-trail mutation is covered by the retained
product regression. Full and race suites were not run for the rejected candidate;
the candidate is not certified for release by the focused checks.

The diagnostic is limited to histories of 200, up to 32 distinct representations,
shallow ancestry and synthetic repeated queries. It does not establish behavior
above the 4096-entry reuse cap, deep derivation graphs, sustained writer contention,
large natural corpora or universal performance. The prior study's narrowly passing
small original-policy result remains a limitation; it is not strengthened by this
rejected experiment.

The first diagnostic fixture builder used a different caller identity and created
denied empty histories. Its commands exited successfully but those observations
are invalid for candidate-history scaling. The corrected smoke requires allowed,
nonempty trails and exactly history×candidate_count projected rows. Both attempts
and their inputs are retained separately. The valid comparison was run only once.

## Reproduction and evidence

`raw-results.tar.xz` is a lossless archive. `archive-members.json` binds every member
by size and SHA256. It includes both invalid attempts, corrected smoke and diagnostic,
all comparison rows and command attempts, frozen SQLite seeds, JSONL inputs, scripts,
source/input/binary hashes, CPU profile, focused-test log and worker receipts.
`manifest.json` binds the public files. The candidate patch reconstructs the
measured source without relying on an unpublished commit.

Verify saved observations without rerunning the study:

```sh
python3 results/2026-09-16-history-diversity/analyze.py
python3 tools/verify_results.py
```

To reproduce measurements independently, extract the archive into scratch space.
Decompress `candidate.patch.xz` into scratch space with `xz -dc`, then apply the
resulting patch to a separate checkout of the baseline. The archived
`input/history.go` is a fixture-builder command under the product module and uses
its internal packages; it is not an installed product command. The diagnostic
runner builds the three fixtures and verifies their schemas and candidate counts.
The archived `input/compare.sh` records the exact build and execution sequence.
Its OMP_INPUT and OMP_OUTPUT variables name an input directory (run/, seeds/ and
baseline/baseline.tar) and an empty output directory. Supply the archived input
scripts, the six diagnostic SQLite seeds and a git archive of the baseline at
those locations. Do not put scratch outputs in this checksum-verified result
directory. The scripts need Go, Python3, SQLite support in Python, tar and GNU time;
module downloads must already be available in an offline environment.

Independent reruns are new observations, not replacements for these samples.
Before another candidate, investigate the unresolved history-free regression with
a separately bounded causal diagnostic. Historical canonical decoding and retained
text checks remain measurable costs, but this study does not justify weakening
them or removing either opening pass.
