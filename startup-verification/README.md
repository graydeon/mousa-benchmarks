# Supersession history and fresh-process command cost

**proposed; not executed; requires review before collection**

This is a benchmark protocol, not a product/domain schema, an implemented runner,
or a performance result. [protocol.json](protocol.json) records the proposed
workload, schedule, bounds and receipts. All preparation, behavior, timing,
replay and negative-control cases below are **NOT RUN** in this proposal.
Independent review must accept an immutable version before collection.

## Question and evidence boundary

How does whole fresh-process native command cost vary with source count,
activation events per source and recorded v4 trails per source on a fixed small
synthetic corpus? Measure runtime startup, store opening and verification,
command work, output and process exit together. This is not isolated verification
time, and differences between operations must not be subtracted to estimate it.
No old-versus-new speedup, complexity class, optimization adoption threshold or
capacity guarantee is being tested.

The proposed product is commit `ff80838c607ab8cde5b89376b9a9f44c1deb13cf`, tree
`5c18c9d14248c693759f20c93d47d84da98b691f`. Build one clean checkout with Go
1.27.1 and cached, verified module dependencies, using:

```sh
GOWORK=off CGO_ENABLED=0 GOOS=linux GOARCH=amd64 GOAMD64=v1 \
  go build -trimpath -buildvcs=false -o "$BINARY" ./cmd/mousa
```

Use Linux/amd64 with pidfd support, Python 3.9 or later with `os.pidfd_open`,
`select.poll` and standard-library SQLite, and no inference,
GPU or network during preparation or measurement. Set `GOMAXPROCS=1` for every
native invocation; record the full effective build and execution environments.
A different product, tree, toolchain or platform requires a reviewed amendment
before collection, not a substitution after seeing results.

The [current capability contract](https://github.com/graydeon/mousa/blob/ff80838c607ab8cde5b89376b9a9f44c1deb13cf/docs/CAPABILITIES.md#supersession-core-boundary)
and [startup source](https://github.com/graydeon/mousa/blob/ff80838c607ab8cde5b89376b9a9f44c1deb13cf/internal/sqlite/open.go)
establish feasibility, not timings. Declaration get uses `OpenReadOnly`, one
read-only verification path without migration. On an existing current-schema
store, status uses `Open`: read-only preflight followed by writable migration/open
verification, including the writable FTS integrity check. Both inspect stored
history, but their checks and command work differ. This study excludes migrations.

The older [packing scalability](../results/2026-09-16-packing-scalability) and
[rejected historical-scan reuse](../results/2026-09-16-history-diversity) studies
used different source, trail versions and workloads. The latter failed small-case
latency guards despite large-history improvements; contention was not established
as the cause. The product's
[16,384-document startup study](https://github.com/graydeon/mousa/blob/ff80838c607ab8cde5b89376b9a9f44c1deb13cf/docs/RESEARCH.md#startup-verification-at-16384-documents)
includes a distinct schema/index comparison and a rejected acceleration candidate.
Do not pool those host measurements with this study or repeat those comparisons.
The PR75 inspection observation stays pinned to
`5ffa0286b35ecf84b36abe53d029a78075c02b86`, not this later documentation baseline.

## Fixtures and preparation

The Cartesian product has 20 fixtures. A fixture key is `s{S}-e{E}-t{T}`.

| Dimension | Values | Meaning |
|---|---|---|
| S | 1, 8 | Total independent synthetic sources in one store |
| E | 0, 1, 17, 65, 257 | Activation events per source |
| T | 0, 1 | Recorded `mousa.source_trail.v4` trails per source |

Within each S block, source labels are `fixture/startup/00` through the first S
zero-padded indices. Every source has exactly these two JSONL records, in order,
with UTF-8 LF line endings and no other content or revisions:

```jsonl
{"id":"predecessor","text":"amber predecessor evidence"}
{"id":"successor","text":"amber successor evidence"}
```

Prepare with `mousa -store STORE sync --source LABEL` and that stdin. Use the
native fixed-v1 default explicitly as `sync --source LABEL --segment-policy fixed-v1`.
No deletions, withdrawals, associations, explicit access changes or extra sources.
Each source has one declaration pinning those two exact item representations,
with author `fixture-author` and basis `synthetic startup fixture`. Put it with
`mousa -store STORE supersession declaration put`; verify canonical output and
readback. Source/content/revision/declaration bytes are held fixed across E and T
within S; identities remain source-isolated even when text is equal.

Derive inputs using the maintained
[declaration codec](https://github.com/graydeon/mousa/blob/ff80838c607ab8cde5b89376b9a9f44c1deb13cf/internal/mousa/supersession.go)
and [activation codec](https://github.com/graydeon/mousa/blob/ff80838c607ab8cde5b89376b9a9f44c1deb13cf/internal/mousa/supersession_activation.go).
Source identity uses namespace `mousa-jsonl` and the external label. Identity tuples
use length-delimited fields, raw identity bytes and their schema domain, not JSON
text hashing. A declaration binds source, both item/revision pins, author and basis.
An activation binds source, expected predecessor and selected declaration; null is
an empty tuple field. Actor/time/reason do not make a new activation identity.
A preparation-only helper may adapt the reviewed derivation in
[prepare.py](../mcp-trail-supersession/prepare.py), including native revision
construction, but must verify derived identities against actual native-created
records and canonical output. Measured commands contain no helper or internal API.
No direct SQL fabrication of valid production history is allowed.

For each source in ascending index order, append E native
`supersession activation put` calls. Event 1 is a root selecting the declaration;
even events deactivate with an explicit null declaration; later odd events
reactivate it. Each event names the exact previous event. Use actor ID
`fixture-actor`, actor version `1`, reason `synthetic startup transition`, and
`occurred_at_usec = 1700000000000000 + event_index` (one-based).
Every positive E is odd, so all positive histories end at the same selected
declaration. The predecessor hash changes each transition; this is a valid rooted
chain, not repeated idempotent writes. E=0 means no events and no state projection,
not a deactivation. Check both actual row count S×E and every chain's length/tip.

After all events, when T=1, invoke once per source:

```sh
mousa -store STORE query --source LABEL --policy original \
  --packing-policy original --budget-bytes 8192 --supersession amber
```

Require allow, exactly two matched candidates, v4 and consulted=true. At E=0,
activation/declaration are null and both candidates are selected; at positive E,
the tip and declaration match, the predecessor is withheld, the successor is
selected, and `supersession_excluded` is 1. Require exactly S×T trails and their
candidate projections and decision parents. No denied/empty substitute trails.
Native fresh request IDs and times are retained; independently regenerated stores
need not have identical whole-file hashes. Freeze each prepared store's actual
bytes and canonical digests before scheduling. This is deterministic construction
and validation, not a promise of byte-identical random native identities across
captures. T=0 has no query-created decisions or trails.

Check current schema, required objects, SQLite integrity and foreign keys, exact
source/item/declaration/event/state/trail/candidate cardinalities, canonical
identities, source ancestry, native declaration get, status and activation state
before timing. E=0 state returns the documented not-found, not a successful active
projection. Preparation failure invalidates that fixture and stops collection;
retain its inputs/receipts and mark the whole unstarted schedule NOT RUN.

Use Python SQLite's backup API from the quiescent prepared database into a new
snapshot, close all connections, checkpoint the destination with `wal_checkpoint(TRUNCATE)`
and close it. Require no nonempty WAL, successful integrity checks and identical
logical/canonical state before freezing its hash. Never copy a live main file
without committed WAL. Before every warmup or trial, copy this closed coherent
snapshot into a new disposable directory, verify its bytes, and record absent or
present `-wal`, `-shm` and journal sizes. Preparation, backup/checkpoint, copies,
hashing and invariant checks are outside the command timer and separately logged.
Never reuse a command's modified store as the next trial's input.

Fixed S and T let E vary history while content and declarations stay fixed.
Nevertheless bytes, index pages, locality, chain identities and v4 references
change with history. T=1 adds decisions/candidates and references that fixture's
final tip (or no history). Changing S also changes content, declarations and total
history. These are declared workload contrasts, not isolated causal estimates of
one verifier routine. Report actual bytes; never call store size constant.

## Operations and correctness gates

Only source 00 is targeted; opening still checks the full store. The frozen
schedule expands these argv arrays with `./bin/mousa`, `trial/store.sqlite` and
the prepared declaration ID, from one scratch root. Stdin is empty and immediately
closed for both operations. Replace the disposable `trial` directory between calls.

| Operation | Exact native command | Expected result |
|---|---|---|
| declaration-get | `mousa -store STORE supersession declaration get DECLARATION_00` | Exit 0; stdout byte-identical to the prepared canonical declaration; empty stderr |
| status | `mousa -store STORE status --source fixture/startup/00` | Exit 0; empty stderr; exactly `{"source":"fixture/startup/00","collection_state":"active","observations":2,"active_items":2,"needs_recovery":false}` as parsed JSON |

Get takes the canonical declaration ID, not `--source`. Status needs the external
source label, not the hashed SourceID or an omitted source. Validate status with
strict duplicate-key rejection and JSON-type-preserving canonical comparison;
object key order/whitespace are irrelevant. Retain its original bytes. Validate
get byte for byte without adding/removing a newline. A usage error, missing record,
absent source report, startup refusal or other failure is not a valid success
sample and cannot be treated as a faster command.

Before and after every invocation, snapshot all SQLite user tables/schema and
ordered typed row values through a read-only connection that sees committed WAL.
Record per-table counts, logical digests, canonical record digests and file sizes/
hashes before any cleanup/checkpoint. Encode a row as compact UTF-8 JSON arrays of
`[type,value]` fields in schema column order: null has null value; integer uses a
decimal string; real uses its IEEE-754 binary64 big-endian hex; text uses UTF-8 hex;
blob uses raw hex. Sort encoded row bytes lexicographically, retaining duplicates.
Hash their LF-delimited stream per table; retain schema SQL and column metadata.
Require no logical change, especially to immutable declarations/events, activation state,
items, decisions and trails. Get must preserve the main database file byte for byte. SQLite WAL readers
may create or update WAL/SHM bookkeeping even with `mode=ro` and query-only
enforcement; record sidecar presence, sizes and hashes for both operations rather
than treating reader sidecars as a canonical mutation. No main-file change by get
or logical/canonical change by either operation is permitted. Writable status may
also have FTS integrity-check physical effects; record them separately. Preserve
the product's actual open mode: do not substitute immutable SQLite, suppress
sidecars, delete them before observation or normalize unknown logical writes away. No audit-row append is expected from either operation. Compare seed
bytes and baseline counts/digests again after the schedule to detect accidental
seed mutation. Main-file invariance and logical equality are distinct from observed sidecar lifecycle;
a read-only open is not a guarantee that every filesystem byte remains unchanged.

## Frozen schedule and host prerequisites

Process-cold, ordinary OS cache: every invocation executes a new public binary.
This is not cold-page-cache or cold-disk measurement. Copying and validation warm
pages. Do not evict caches, tune the host globally or use privileged operations.
Run sequentially with no concurrent build, backup, test, inference or other study.
Before collection, require 60 seconds with aggregate CPU busy below 10%, CPU steal
below 1%, and available memory at least 2 GiB at every one-second observation.
CPU busy is the `/proc/stat` total delta minus idle and iowait, divided by total;
steal uses the steal delta over that same total (exclude double-counted guest fields).
If this prerequisite fails, retain the host record and do not start collection.
Record kernel, CPU model/features/count, RAM, filesystem/storage, container/cgroup
limits and throttling, load, governors if readable, Go/Python/SQLite versions,
module verification, build flags and environment. These prerequisites cannot prove
exclusive host ownership.

There are 40 fixture/operation cells, 80 warmups and 400 recorded trials. Freeze
`schedule.json` and its SHA-256 before any warmup. Define seed
`mousa-startup-v1`. For warmup rounds 0 and 1, then measured rounds 0 through 9,
include every cell once; sort each round by ascending SHA-256 of the UTF-8 string
`mousa-startup-v1|PHASE|ROUND|S|E|T|OP`, with decimal integers without padding,
PHASE `warmup` or `measured`, and OP `declaration-get` or `status`. Break hash ties
by the full string's byte order. This defines seeded interleaving without depending
on a language's pseudorandom generator. Save the expanded order, ordinal, cell,
round, argv, stdin digest, seed identity and expected output identity per entry.
Warmups use the same reset/gates as trials, but supply no reported timing metric.

Sample host `/proc/stat`, `/proc/loadavg`, `/proc/meminfo` and available cgroup
CPU/I/O pressure and throttling counters every second through the measured phase;
record missing optional counters explicitly. Record sampler overhead and exact
sampler source. Flag intervals violating the idle prerequisite or showing new
throttling, but retain them and do not discard/rerun observations. On operator
interruption, suspension, sampler failure or detected concurrent workload, stop,
retain the partial attempt and mark remaining entries NOT RUN. Do not resume it
or replace it with favorable repeats. Any later authorized attempt is a separately
identified capture with the failed/partial attempt still preserved.

## Metrics, limits and failure policy

For each recorded command, use `time.monotonic_ns()` immediately before child
creation and immediately after its exit is reaped. This includes spawn, execution,
stdout/stderr writes to regular files and close/exit; it excludes subsequent
validation, copies and hashing. Record timestamp endpoints and duration in ns.
Use one direct `fork`/`exec` child and open its pidfd before waiting. Register
the pidfd with `select.poll` for exit readiness; pidfd readiness wakes the parent
immediately, without a fixed sleep or polling interval gating exit notification.
On readiness call blocking `wait4(pid, 0)` exactly once for that child and take
the end timestamp immediately after it returns. No `WNOHANG`/sleep reaping loop
or silent fallback is permitted. Missing or denied pidfd support fails preflight
before preparation or collection; changing the mechanism requires an amendment.

Request poll waits of at most 1 millisecond, shortened to zero when a command or
phase deadline has arrived. Recheck both deadlines immediately before and after
every poll return. Check workspace usage before spawn and every 100 milliseconds
while running, using accounted fixed workspace bytes plus live trial/output sizes;
a due storage check must not postpone a ready child's reap. Keep the host sampler
at its separate one-second cadence. Record poll start/end/requested timeout,
readiness observation, wait4 return, deadline checks, storage-check times and any
detection/termination delay. Scheduler delay can exceed requested waits: report
actual delay and resource-bound overshoot, not a hard real-time guarantee. These
monitoring cadences are fixed; their overhead remains part of whole-command cost.
Planned controls must check immediate readiness wakeup with a control-only 1,000-millisecond
poll timeout (measured commands still use at most 1 millisecond) and bind monitoring/cancellation records to these rules.

Preserve the exact child's `rusage.ru_utime` and `ru_stime` in
seconds, and Linux `ru_maxrss` in KiB (1024 bytes), including zero/resolution limits.
Do not use cumulative `getrusage(RUSAGE_CHILDREN)` differences or the wrapper's
historic maximum RSS. No shell/time subprocess or build participates in the child
measurement. This binary is not expected to spawn descendants; unexpected ones
invalidate the sample and are terminated with its process group. RSS is peak
resident memory, not Go allocations, heap size or simultaneous process-tree sum.
Go allocation counts remain unmeasured and unclaimed.

| Bound | Proposed value | Treatment |
|---|---|---|
| Timed command deadline | 10 seconds from pre-spawn monotonic timestamp | At deadline SIGTERM process group, after 1 second SIGKILL if needed, reap; record timeout and actual termination delay |
| Measured-phase cap | 1,800 seconds | Includes trial resets, checks and host sampling, but not preparation or the 80 warmups; cancel active child as above |
| Artifact/storage budget | 2 GiB (2,147,483,648 bytes) | Combined live workspace, fixtures, receipts, failed attempts and packaging; record per-phase use separately |

Keep one disposable trial copy at a time. Check storage before each copy/spawn and
while the child runs; reserve 16 MiB within the budget for failure receipts. Stop
before exceeding the budget, cancel the child if necessary and preserve existing
raw evidence. The bounds are stopping rules, not capacity promises. In particular,
400×10 seconds exceeds 30 minutes even before reset/check overhead: the phase cap
intentionally permits an incomplete schedule. Do not shorten the workload or raise
limits based on observed cost. Preparation/warmup time and peak storage are logged
separately; they are not startup samples or hidden measured-phase time.

A timeout is right-censored at 10 seconds, not a completed 10-second success;
retain actual wall/CPU/RSS through reaping separately. A phase/storage/interruption
cancellation has its own censor threshold/reason. Stop the attempt on the first
failed gate, timeout, infrastructure error or cancellation. Preserve the failing
entry and mark every remaining scheduled entry NOT RUN with a reason. Do not drop
slow cases, trim outliers, silently skip cells, impute successes or retry a cell.
An older/newer/foreign schema refusal is a startup-schema failure, separately from
canonical/output/invariant correctness failures and from successful performance
observations. A failed preparation has no performance observation. Publish partial
coverage, not a complete study; no universal latency tail claims follow even from
a complete ten-trial cell.

## Receipts, analysis and controls

Every invocation, including preparation/warmups/controls, retains exact argv,
working-directory mapping, stdin bytes and digest, stdout/stderr bytes and digests,
exit code or signal, phase/ordinal and UTC observation times, binary/build/environment
identities, protocol/schedule/fixture/preparation hashes, and pre/post snapshots.
For trials add monotonic endpoints, CPU/RSS and termination/censoring details.
Run native invocations with the fixed relative paths above so exact public argv
and streams need no path rewriting. Record cwd as the scratch-root-relative path;
keep its machine-specific absolute location only in local operational metadata.
Use an explicit environment without secrets or private path values; retain all
effective values, including locale, timezone and HOME relative to the scratch root.

A future verifier must reconstruct the frozen schedule, require exactly one receipt
per attempted entry, require explicit NOT RUN records for the remainder, and bind
argv/stdin/fixture/output to that entry, not merely to self-reported match fields.
It re-derives counts, chains, canonical expectations, exits, durations and summaries
from raw receipts; stored `passed` booleans or a summary are not evidence. Strict
JSON parsing rejects repeated keys and preserves JSON types. Hashes establish byte
identity, not truthful execution or immunity to coordinated fabrication.

The following unfilled outputs are fixed in advance; no data are supplied here:

- `coverage.csv`: every cell, expected/attempted/success/failure/censored/NOT RUN
  counts and attempt status, with warmups separate.
- `samples.csv`: every recorded ordinal, S/E/T/operation, round, timestamps,
  wall ns, user/system seconds, max RSS KiB, exit, censor reason and contention flags;
  associated wait/monitor records retain requested intervals and actual delay.
- `fixtures.csv`: every fixture's actual source/item/representation/declaration/
  event/state/v4-trail/candidate/decision counts, canonical digests, main/WAL/SHM/
  journal bytes and snapshot hash; pre/post differences listed separately.
- `summary.csv`: per cell successful n, median/min/max wall, user CPU, system CPU
  and RSS, plus failure/censor/NOT RUN counts. Median for even n is the arithmetic
  mean of the two central sorted values. Partial cells remain labeled incomplete.
- `observations.svg`: individual wall observations against events per source,
  faceted by S/T/operation, with censored entries marked at their thresholds.
- `resources.svg`: separate CPU and RSS panels with individual observations,
  same facets and event axis. No percentile/p95/p99 or universal-tail estimates.

Each future table/plot is derived from raw samples, never hand-entered conclusions.
Do not pool source counts, trail counts or operations. Descriptive median/range
and individual observations do not establish asymptotic complexity or causation.

Before collection, implement these acceptance cases; every row is **NOT RUN**:

| Case | Required detector/acceptance |
|---|---|
| Clean pins and valid preparation | Source/tree/binary/protocol match; 20 valid fixtures and all native gates |
| Complete valid receipts | 80 warmups and 400 trials match order, cells, outputs and unchanged logical state |
| Wrong product commit, tree, binary, protocol (four mutations) | Preflight rejects each mismatched identity before collection |
| Missing, duplicated, skipped or reordered sample (four mutations) | Replay rejects exact schedule coverage/ordinal binding, even after rehashing |
| Mislabeled E/cardinality | Replay recomputes chain and per-source counts, rejects relabeled fixture |
| Forged successful receipt | Change a recorded failure exit to 0 and set passed=true, rehash; replay still rejects raw output/invariant/schedule mismatch |
| Broken canonical output | Alter declaration bytes or status JSON type, rehash; replay rejects canonical/output gate |
| Real forbidden write | Disposable wrapper executes the real binary, then commits an extra SQLite table/row while forwarding successful output/exit; capture and replay reject schema/logical-state change |
| Startup-schema refusal | Disposable copy with foreign application_id: both commands exit nonzero without successful payload or repair; classified outside success timings |
| Deadline, cap, storage and interruption | Controlled wrapper/harness injections exercise cancellation/reaping, raw retention and NOT RUN remainder, outside measured trials |
| Exit and monitor mechanics | A controlled child exit wakes a control-only 1,000ms pidfd poll without waiting out that timeout; missing support rejects preflight; replay rejects changed mechanism/cadence or missing wait/deadline/storage records |
| Read-only physical boundary | Main-file or logical changes fail; any WAL/SHM sidecar lifecycle is retained separately for get and status without switching the product open mode |
| Ordinary controls | Untouched replay and harmless JSON key-order change for status pass; declaration byte-order changes do not |

Controls never modify the accepted binary or production history. SQL damage/write
is only in explicitly labeled disposable negative-control stores. Regenerate
mutated receipts deterministically from the retained attempt, rehash every affected
member, and publish the mutation specification, exact false condition and detector,
not many duplicated archives. A successful forged receipt control is a specific
consistency test, not proof that an offline analyzer can detect arbitrary forged
execution. The real write control supplies an actual observable write, separate
from a recorded boolean mutation. Startup refusal does not prove live rollback.

## Provenance and bounded publication

Capture clean product and companion commits/trees, exact build command, module
identities/verification, toolchain/environment, binary SHA-256, accepted protocol
commit and byte hash, fixture/input/preparation and frozen-schedule hashes, UTC
start/end times, and exact runner/helper/analyzer/control/sampler source bytes.
Record dirty-source refusal. The capture identifies source available at capture
time; later result publication and eventual merge commits/trees are separate
metadata. Do not require a capture to know its eventual commit ID or relabel it
when documentation or runner code later changes.

The later proposed layout is one additive `results/YYYY-MM-DD-startup-verification/`
with README, protocol copy, product/build/capture pins, schedule, summary tables,
plots, controls receipt list, manifest and `capture.tar.gz` plus
`archive-members.json`. The archive retains raw invocations/streams, inputs,
preparation receipts, logical snapshots, host records, failures and exact tool
sources losslessly. Local databases and binaries remain outside Git; record their
hashes and reconstruct fixtures from native preparation receipts. Every archive
member is a bounded regular file with relative non-traversing name, size and
SHA-256; reject links and duplicates. Limit each member to 32 MiB and compressed
capture to 4 MiB. Reserve at most 6 MiB total new blob content and require the
whole publication patch and changed blobs each below 8 MiB, measured before
submission. No dependency, workflow or publication-control exceptions are planned.
If lossless evidence cannot fit, preserve it locally and stop for review of a
separate publication proposal; do not discard observations to fit. The 2-GiB
workspace budget and much smaller public-package bound serve different purposes.
Pilots, controls, aborted attempts and measured data have distinct phase/attempt
IDs; none is silently promoted into another. No timed pilot selects these dimensions.

The shared `python3 tools/verify_results.py` checks registered archive bytes and
membership, not measured conclusions or this proposal's semantics. A later runner
must verify raw receipts independently and register the dated result manifest
using existing conventions. This design adds no result directory or archive.

## Implementation handoff and review

Proposed later files: `startup-verification/prepare.py`, `run.py`, `analyze.py`,
`controls.py` and behavioral `test_protocol.py`, plus the one dated result directory
and concise index links. Use standard-library facilities and existing archive tools;
no new dependencies or engine changes. The following commands are proposed
interfaces, **not commands available in this design PR**:

```sh
python3 startup-verification/prepare.py --source "$PRODUCT" --binary "$BINARY" --protocol "$PROTOCOL" --output "$PREP"
python3 startup-verification/run.py smoke --prepared "$PREP" --output "$SMOKE"
python3 startup-verification/controls.py --prepared "$PREP" --output "$CONTROLS"
python3 startup-verification/run.py capture --prepared "$PREP" --output "$CAPTURE"
python3 startup-verification/analyze.py verify "$CAPTURE"
python3 startup-verification/analyze.py summarize "$CAPTURE" --output "$REPORT"
python3 tools/verify_results.py
```

One bounded later implementation/capture slice must:

1. Pin the accepted immutable protocol; implement preparation and strict receipts.
2. Exercise all acceptance rows with unmeasured smoke/control invocations; freeze
   schedule and complete source/provenance receipts before collection.
3. Collect once under fixed bounds, retaining failures and incomplete coverage;
   never alter protocol/workload after outcomes.
4. Replay from raw receipts, derive all outputs, run rehashed and actual-write
   controls, measure publication size and publish the additive bounded evidence.

Review must decide whether to accept the proposed product/toolchain pin, final-tip
v4 reference strategy, whole-process operations, seeded schedule, idle thresholds,
stop-on-first-failure policy, incomplete-schedule cap and publication bounds.
These are concrete proposed choices, not runtime options for an implementer to
resolve after seeing data. Any change requires a reviewed protocol amendment before
collection. Independent review is pending; self-review of this design is not
ratification. Query latency, persistent MCP throughput, semantic/retrieval quality,
GPU/inference, authentication, native-host acceptance, live stores and optimization
remain out of scope. No behavior, timing or negative-control result is claimed.
