# History-free verification diagnosis

## Outcome

The cause of the historical-verification candidate's history-free slowdown remains
unresolved. The [completed comparison](../2026-09-16-history-diversity) remains
**REJECTED**, with its observations, thresholds and conclusions unchanged. This
investigation does not justify restoring the candidate or starting an adoption
study. Released Mousa behavior is unchanged.

The existing evidence establishes matching toolchains and build settings, empty
historical tables before each invocation, and a modified current-query readback
path. It does not establish that cache initialization, compiler behavior or host
contention caused the regression.

The new diagnostic stopped at its first fixture smoke assertion, before any
control or comparison blocks. The assertion exposed a side effect in the new
Python fixture inspector, not in Mousa. A subsequent cleanup-only smoke check
passes after correction. Its four invocations are correctness evidence, not a
performance comparison. There are **zero completed A/A pairs and zero new timed
B/C pairs**. No uncertainty interval or equivalence claim is available.

## Preserved evidence analysis

The original small, history-free, original-policy median increased from 43.56 to
53.21 ms. Ten of twelve paired candidate observations were slower. The median
paired difference was 7.9694 ms; this is a different statistic from the difference
of arm medians. Individual pairs, execution order and recorded process CPU times
are in `existing-analysis.json`.

The original ordering alternated baseline/candidate and candidate/baseline, with
six pairs of each order. Cells ran sequentially: small before shared before
diverse; zero history before 200; original before exact-v1. Each cell had one
warmup pair, twelve wall-time pairs, one stage pair and one allocation pair.
There was no identical-binary control.

Both original binaries report Go 1.27.1, linux/amd64, GOAMD64=v1, CGO_ENABLED=0,
the same dependency versions and the same recorded build settings. The script
set GOMAXPROCS=6 and used `go build -o OUTPUT ./cmd/mousa`, without `-trimpath`.
Candidate and baseline were built from different source directories. No recorded
metadata discrepancy demonstrates a build defect. Different binary hashes are
expected from different source and build paths; they are not causal evidence.
The exact hashes and `go version -m` metadata are archived; only the executable
path in the metadata header is normalized to its binary name.

The baseline is Mousa `e68be171b6dce5f4ee410aece1a655aa2009b78b`. The candidate is
that source plus the preceding study's exact patch, preserved losslessly in this
archive. The new reconstruction matches all 117 files in the preceding measured
candidate manifest. The current product revision is
`2b379a3c6cc0059d6c05890b44e42fc6e748154a`; the starting benchmark revision is
`38119a99bfc07bf6b49a9a6f71fbcf17d9e84fd0`. Product tests retained after rejection
do not imply full or race verification of the candidate.

### Zero history and current-query work

The frozen small fixture has zero `source_trails`, `source_trail_candidates` and
`policy_decisions`. Its SHA-256 is
`0c697debe9d226ce460c9074c719814108284575a0ea686c0f8b73ba0700083b`.
The original runner copied and hash-checked that same fixture before every call,
then removed the working database and asserted absence of sidecars. It did not
accumulate queries between measured invocations.

Both opening verification passes still execute. `verifySourceTrailRecords`
opens a read transaction, enumerates zero IDs, verifies zero projected candidates
and commits. The candidate introduces an empty `trailVerification` value here,
but its map allocation occurs only inside helper methods called for historical
candidates. Neither historical cache helper is called in the empty scan. The
single stage probes recorded zero historical trail reads, segment reads and
ancestry walks for this case.

The query is not read-only. `queryItems` calls `EvaluateAndTraceLexical`, which
evaluates current authorization, retrieves candidates, packs them, inserts a
trail and canonically reads it back inside the writer transaction. The candidate
changes that call to `getSourceTrail(..., nil)`. Original-policy v1 readback does
not enter `verifyExactTrailContent`; exact-v1 readback does, and uses the changed
segment/source helper path even with nil historical reuse state. An empty
historical scan therefore does not imply that all changed code is unexercised.
This identifies paths to investigate, not a demonstrated performance mechanism.

The successful new smoke verifies zero records before each of four invocations,
an allowed response containing one selected evidence item and one matched
candidate, and exactly one decision, trail and projected candidate afterwards.
Each invocation starts again from the original fixture.

### Timing boundaries and attribution limits

The original Python wall timer surrounds `subprocess.run` of GNU time and Mousa,
including process launch, wrapper overhead and output collection. Fixture copying
and SHA-256 checks precede the timer. JSON validation and cleanup follow it.
GNU time records user/system CPU in hundredths of a second: too coarse to
resolve an approximately 8–10 ms difference reliably. The raw rows lack per-call
wall-clock timestamps, high-resolution child CPU, scheduler counters, pressure
samples and fixture-copy durations. Wall minus those rounded CPU fields is not
a reliable estimate of host contention or wrapper overhead.

Separate stage binaries instrument functions with deferred timing and maintain
nested stage counters. Their process timer begins after initial memory-stat
collection; it excludes runtime startup and final memory-stat collection and
JSON serialization. Instrumentation changes both executable code and runtime
work. The small/original stage probe measured opening at 27.9620 ms for baseline
and 20.4975 ms for candidate, while query time was 10.3754 versus 12.0114 ms.
These are single observations of different binaries, not stage decompositions
of the twelve uninstrumented comparisons. The exact-policy probes also favored
candidate opening. They neither explain nor invalidate the failed guards.

## Frozen diagnostic and actual execution

`protocol.json` was written before execution. It proposed only the smallest
failing original-policy case:

- 24 balanced, seeded blocks, each containing identical-binary A/A, preserved
  baseline/candidate and matched rebuilt baseline/candidate pairs.
- Two warmup pairs per comparison type, followed by eight separate stage pairs.
- Matched builds with `-trimpath -buildvcs=false`, unchanged runtime environment,
  recorded source manifests, build metadata and binary hashes.
- High-resolution child resource usage and guest context observations, kept
  separate from instrumented attribution.
- A 1,200-second worker limit, a 30-second per-call limit, and termination on an
  assertion or build failure, without extending samples or retrying for a pass.

Both matched builds and both instrumented builds completed. The first smoke
query returned the expected result and record counts, but cleanup found WAL
sidecars. The run exited 1 after approximately 26.5 seconds. It produced one
smoke observation and no warmup, control, comparison or stage observations.
The stopping rule was applied; the performance experiment was not restarted.

The new `counts` helper initially used `with sqlite3.connect(..., mode=ro)`.
That context manages transactions, not connection closure. A separate
cleanup-only smoke used explicit closure but still failed the sidecar assertion.
Read-only access to a WAL-mode database can create sidecars that remain after
closure. The final helper asserts that no WAL, SHM or journal exists, then uses
an explicitly closed `mode=ro&immutable=1` connection to inspect the closed,
checkpointed file without creating sidecars. It never ignores an existing WAL.
The final cleanup-only smoke passed all four binaries. The two failed attempts,
the successful smoke, and all three script versions are preserved.

These corrections apply only to the new diagnostic. The original comparison
runner did not contain this row-count inspector. The inspector failure therefore
cannot explain the original performance regression. The corrected timed loop
has not been executed; only `--smoke-only` has passed. It must not be described
as a validated performance measurement method.

## Environment and verification

The worker reports six vCPUs, 12 GiB VM memory, an 8 GiB job limit and a 5.5-core
job CPU quota, on a shared AMD Ryzen 7 2700X host with shared NVMe storage.
The guest exposes an EPYC-compatible CPU and Go 1.27.1. No host configuration
was changed. Worker and submission timestamps have different clock offsets;
within-worker elapsed durations, not cross-machine timestamp subtraction, are
used above.

The final smoke retained a guest context snapshot: load averages 0.20/0.20/0.09,
CPU pressure `some avg10=0.00`, and I/O pressure `some avg10=1.64`. These are a
single later snapshot, not context for the historical comparison. The captured
root cgroup CPU counters are not the job's cgroup counters, and the requested
root `memory.current` file was unavailable. They cannot establish absence of
job throttling or physical-host contention. No A/A samples exist to measure the
control's resolution.

| Check | Result |
| --- | --- |
| Exact candidate reconstruction, 117 source hashes | PASS |
| Matched baseline/candidate and separate instrumented builds | PASS |
| Frozen diagnostic fixture smoke | FAIL: inspector-created sidecars |
| Explicit-close-only cleanup smoke | FAIL: sidecars remained |
| Sidecar-safe cleanup smoke, all four uninstrumented binaries | PASS |
| A/A control, B/C comparisons, stage comparisons, bootstrap analysis | NOT RUN |
| Corrected runtime candidate, adoption study, full/race/client candidate checks | NOT RUN: no runtime correction proposed |

The companion archive verification checks bytes and membership, not performance
or causal conclusions. Product runtime, concurrency/tamper regressions, original
packing defaults, opt-in exact-v1 semantics and both opening passes are unchanged.

## Reproduction and remaining question

Run `python3 tools/verify_results.py` from the repository root and
`python3 results/2026-09-17-history-free-diagnosis/verify.py` to verify this archive.
Extract `raw-results.tar.xz` only into scratch space; `archive-members.json`
records every regular member's size and SHA-256. The archive contains the frozen
and corrected runners, build script, instrumentation, exact candidate patch,
fixture, source manifests, raw smoke records and worker receipts. Binary hashes
are public, but executables are not included. The previous study supplies the
original comparison records and its fixture-generation methods.

The build script expects a baseline tar made from the named Mousa revision,
the exact candidate patch, the fixture, original executables, and script inputs.
Set `OMP_INPUT/diagnostic` and `OMP_OUTPUT` to those input and scratch-output
locations. Original non-trimpath executable hashes also depend on original build
paths; a fresh build is not an identical-binary reproduction of the old pair.
The final runner's `--smoke-only` mode is the only corrected mode verified here.
Do not run its timed mode and label it a continuation of this terminated study.
A future experiment would need its own protocol and result record.

The unresolved question is whether the original 8–10 ms small-case shift persists
relative to an identical-binary control, and whether it associates with the
preserved executables, matched source builds, or invocation variability. This
investigation neither reproduced nor ruled out that shift. A successfully
executed controlled experiment could distinguish those associations, but would
still need mechanism evidence before justifying a source correction.

Do not schedule another identical optimization session by default. Retain the
rejected candidate and the documented history-dependent cost. The next product
milestone is a concrete consumer workflow review: determine whether an authorized
query response and its representation/range metadata suffice for a consumer to
save and later verify selected evidence, and specify the missing operation only
if that exercise demonstrates one. General export and cache adoption remain
separate decisions.
