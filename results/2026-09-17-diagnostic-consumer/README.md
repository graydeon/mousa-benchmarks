# History-free diagnostic and documentation consumer measurements

## Outcome

**Unresolved cause and insufficient control resolution. The historical-verification
candidate remains rejected. No runtime change is adopted.** The identical-binary
A/A wall-ratio interval extends to 1.1082, crossing the predeclared 10% practical
effect. Neither preserved nor matched-rebuild B/C pairs reproduced the earlier
slowdown. These observations do not establish equivalence, explain the earlier
failure, or authorize adoption.

A separate documentation consumer study completed 25 queries against two pinned
Git manuals. All four development questions returned their expected supporting
passages within 4,096 released-text bytes; the fifth returned explicit insufficient
evidence. This held across five repeated passes. Median end-to-end wall time rose
from 133.18 ms in the first pass to 225.45 ms in the fifth as history accumulated.
These are small, single-host observations, not general answer-quality or performance
claims. No generated answers were evaluated.

## Relationship to preserved failures

The [original rejected comparison](../2026-09-16-history-diversity/) remains
unchanged. Ten of its twelve small/original pairs were slower for the candidate,
with about an 8 ms median paired difference. Matching original build metadata and
zero initial histories do not invalidate that comparison: each current query
writes and reads its own trail through changed code.

The [earlier diagnostic](../2026-09-17-history-free-diagnosis/) stopped during
fixture inspection, before warmups, A/A or B/C observations. Its two setup failures
and later four-binary cleanup smoke remain unchanged. This report is a separately
identified protocol, not a replacement result for either prior study.

Before freezing this diagnostic, an independent full-path pilot rebuilt all six
binaries and exercised two A/A/old/rebuilt blocks, two stage pairs, all resets and
the complete analyzer. Its 32 invocations are retained separately and excluded
from diagnostic estimates. Injected nonzero exit, timeout with partial output,
existing-WAL refusal and truncated-analysis cases all stopped as expected. Failed
calls retained their attempt and working database; successful calls removed the
closed working copy. The pilot completed with exit zero.

## Frozen diagnostic method

`protocol.json` identifies `history-free-diagnostic-v2-20260917`. Source runtime
behavior was not changed. Both arms reconstruct the previously preserved baseline
source plus the exact rejected candidate patch. Full per-file baseline/candidate
hash manifests, binary hashes, Go build metadata and environment are archived.
The public Mousa checkout used to submit the jobs was
`2b379a3c6cc0059d6c05890b44e42fc6e748154a`; source manifests, not that checkout label,
identify the reconstructed experimental arms. The companion base was
`3056cb09c945b84431cc481eee02932ad11a9308`.

The preserved `small-0.sqlite` input SHA-256 is
`0c697debe9d226ce460c9074c719814108284575a0ea686c0f8b73ba0700083b`.
Every invocation starts from a byte-identical copy with zero policy decisions,
source trails and projected trail candidates. Each response must be allowed,
nonempty, have one matched/selected candidate and produce one record in each
of those tables. Stable response fields must agree across all binaries. Request
IDs must be fresh. SQLite immutable inspection is used only after the CLI exits
and after asserting that WAL, SHM and journal sidecars are absent; it is never
used to ignore a live WAL.

The command is `mousa -store work.sqlite query --source scaling
--packing-policy original --budget-bytes 8192 amber`, wrapped by GNU `time`.
There are exactly 24 blocks of three pair types:

1. A/A: the same preserved baseline executable under both arm labels.
2. Preserved original baseline/candidate executables.
3. Baseline/candidate rebuilt together with Go 1.27.1,
   `CGO_ENABLED=0 GOAMD64=v1 GOMAXPROCS=6`, `-trimpath -buildvcs=false`.

Each pair type has 12 AB and 12 BA orders, shuffled with seed 20260917; pair-type
order is shuffled within each block. Twelve warmup invocations and four ordinary
smoke invocations are retained but excluded. Eight separately instrumented balanced
B/C pairs follow. Total: 176 invocations, including 144 uninstrumented comparison
calls and 16 stage calls. No sample extension, matrix expansion or favorable retry
occurred. The worker cap was 1,200 seconds including builds; the job completed in
38.39 seconds according to its worker-side start/end receipt. No observation failed.

Wall time uses monotonic nanoseconds. Process CPU uses high-resolution child
`getrusage` deltas; GNU time's rounded CPU fields are retained but not used for
CPU estimates. Both include the wrapper's process cost. Faults, context switches,
block I/O, UTC/monotonic invocation times, command arguments and pair-boundary
load, pressure and available cgroup/proc counters are retained. Worker and gateway
wall clocks differ; do not combine their timestamps into elapsed durations.

The worker has six vCPUs, a 5.5-core job quota and 8 GiB job memory on a shared
Ryzen 7 2700X host with shared NVMe. Guest scheduling/cgroup counters cannot identify
other host workloads. These are fresh CLI processes with reset database history,
not a claim of physically cold filesystem caches or dedicated-host independence.

## Paired results

Intervals are the frozen 10,000-resample seeded paired-bootstrap 95% descriptive
intervals for the median paired ratio. They assume exchangeable blocks and do not
establish independent hardware trials. A median of paired differences need not
equal the difference between marginal medians.

| Pair | Wall median difference, ms | Wall median ratio | Wall ratio interval | CPU median difference, ms | CPU ratio interval |
| --- | ---: | ---: | --- | ---: | --- |
| A/A | +2.2193 | 1.0533 | 0.9997–1.1082 | +1.5545 | 0.9756–1.1420 |
| Preserved B/C | -0.8714 | 0.9795 | 0.9470–1.0677 | -0.5595 | 0.8954–1.0518 |
| Rebuilt B/C | +0.8243 | 1.0194 | 0.9591–1.0675 | +0.8375 | 0.9482–1.0616 |

The controls cannot resolve the full declared practical effect. Neither source-
associated regression nor a build-associated difference is established. The
preserved and rebuilt intervals overlap the control; their differing point
estimates are not a causal explanation. The old rejected result remains evidence,
not an outlier to delete.

Separate stage probes report a +4.2502 ms median paired inclusive opening
difference, -0.5828 ms for `queryItems`, and -0.0610 ms for its nested
`traceLexical/getSourceTrail`. Instrumentation changes execution and these eight
pairs cannot substitute for uninstrumented evidence or establish cache/compiler
mechanisms. Stage paths and inclusive/exclusive distributions remain in the raw
analysis. No compiler, cache-overhead or host-contention cause is inferred.

## Concrete documentation consumer

The consumer is an executable example under Mousa `examples/docs`, using the
existing CLI and `eval/local/workflow.py` normalized-range verifier. The caller
is a developer or application asking about Git working-tree operations. Inputs
are a pinned local corpus, store, question and released-text byte budget. Output
is verified passage text, source identity, normalized byte and line locations,
and an upstream URL, with `answer: null` and `support: not_assessed`.

The corpus is the unmodified `Documentation/git-restore.adoc` and
`Documentation/git-switch.adoc` at Git 2.51.0 commit
`c44beea485f0f2feaf460e2ac87fdd5608d63cf0`: 15,969 source bytes in total.
The archive retains the upstream GPL-2.0-only `COPYING` and attribution. AsciiDoc
includes and referenced manuals are not expanded. Corpus and consumer file hashes
bind the measured inputs; the maintained implementation and corpus are owned by
Mousa. Raw packets and the exact measured consumer source are retained as
measurement data. After measurement, the released example additionally normalizes
dot-dot directory aliases and its acceptance suite runs through required client
verification. Those final checks are separate from this frozen timing sequence;
the measured source hash is not presented as the final released source hash.

`questions.json` was fixed before the first retrieval. These are development
questions, with no held-out set or keyword tuning:

| Question | Required support | First-pass released bytes | Covered |
| --- | --- | ---: | --- |
| Where does git restore get contents by default? | HEAD with staged, otherwise index | 4074 | yes |
| What does restore overlay mode do? | Never removes; default is no-overlay | 4089 | yes |
| How do I switch to a commit for inspection and discardable experiments? | detach and its description | 3946 | yes |
| What happens to tracked files with switch orphan? | New unborn branch; tracked files removed | 3912 | yes |
| frobnicatequantum | Explicit insufficient evidence, no citations | 0 | yes |

The no-match token is a narrow insufficient-evidence check, not a realistic
answerability evaluation. An unrelated lexical match can still produce passages;
the consumer does not fabricate an answer or declare semantic support. Supporting
passage coverage is distinct from synthetic correctness fixtures and from general
answer quality. No competitor comparison was run.

Three real-CLI acceptance tests passed: bundled-corpus use; synthetic update,
deactivation, budget, denial, withdrawal and saved/current boundaries; and source
isolation plus changed-byte/link refusal. They check normalized Unicode/BOM/CRLF
locations, refuse stale bytes before assigning new citations, and distinguish a
saved authorized response from current access and activation. The tests do not
claim saved files are erased on denial or that text-free history restores old text.

Exactly five passes of the same five questions ran against one store without
resetting history. Outer wall time includes Python startup, file verification,
CLI execution, packet construction and stdout parsing. Per-packet inner timing
is also retained. No throughput, p99 or sustained-concurrency claim follows.

| Pass | Prior queries at start | Median wall ms | Maximum wall ms | Expected cases covered |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0 | 133.18 | 156.34 | 5/5 |
| 2 | 5 | 159.82 | 169.53 | 5/5 |
| 3 | 10 | 171.68 | 178.82 | 5/5 |
| 4 | 15 | 220.51 | 247.96 | 5/5 |
| 5 | 20 | 225.45 | 238.77 | 5/5 |

History and execution order are confounded in this single sequence; the increase
is an observed accumulated-history workflow cost, not a causal per-trail estimate.
There is no concurrent-user or long-lived-service measurement. Further product work
should address a demonstrated consumer limitation rather than automatically repeat
this diagnostic.

## Verify and reproduce

Run `python3 tools/verify_results.py` from the companion root, then
`python3 results/2026-09-17-diagnostic-consumer/verify.py`. The first validates the
published run manifest. The second checks lossless archive member hashes, separate
pilot/diagnostic counts, paired summary arithmetic, fixture identity, successful
receipts and consumer byte accounting. Archive checks do not rerun the experiment.

`raw-results.tar.xz` retains all attempted observations, pilot failure-injection
receipts, contexts, schedules, source/build manifests, stage results, full analysis,
consumer responses and command logs. `archive-members.json` pins every member.
The embedded rejected patch is preserved byte-for-byte inside the lossless archive,
not reformatted to satisfy patch whitespace checks. Old studies are untouched.

The diagnostic runner, analyzer and instrumentation are beside this report.
`receipts/timed.sh` records the build procedure; the archived protocol pins all
input hashes. Exact preserved executables and the original source tar are retained
with the measurement artifacts, not distributed here. Their hashes are archived;
without those exact inputs a fresh run is a new rebuild experiment, not a replay
of the preserved-binary comparison. The fixture and candidate patch are included.
Use the independently validated pilot before any newly authorized timing study.

To reproduce the consumer at a new identified checkout, build Mousa and run
`python3 examples/docs/docs_test.py --mousa ./mousa`, then
`python3 examples/docs/evaluate.py --mousa ./mousa --output docs-results.json`.
Retain that new output separately. The frozen source/input hashes distinguish
this recorded run from later examples or environments.
