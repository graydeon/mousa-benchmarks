# Reproducing comparisons

Use separate checkouts of Mousa and this repository. Record explicit revisions for both. Historical result metadata must not be relabeled after migration.

## Segmentation comparison

The [measured result](results/2026-11-07-enterprise-segmentation-v1) contains
160 scored rows: the original 20 questions × two segment policies × two byte
budgets × two passes. Collection completed in 1,382.203 seconds; source-bound
replay and a separate recorded-consistency audit passed. The original 500
physical documents and all 4,970,133 normalized bytes are unchanged. Expression
policy and packing remain `original`, with candidate limit 100. Passage-v1
improved packed gold-document coverage but lost rank on two questions and
coverage on one question at 1,024 bytes; see the result's per-question and
resource tables. No default changes.

### Replay the segmentation evidence

From the companion repository root, set `CACHE` to the enterprise pilot's
existing source cache. It must contain the pinned assets required by
`enterprise-segmentation-v1/prepare.py`; replay materializes the same inputs
without downloading assets or running retrieval. Extract the lossless archive
into a new directory, then use the existing analyzer:

```sh
mkdir segmentation-evidence
cat results/2026-11-07-enterprise-segmentation-v1/evidence.tar.xz.part00 results/2026-11-07-enterprise-segmentation-v1/evidence.tar.xz.part01 results/2026-11-07-enterprise-segmentation-v1/evidence.tar.xz.part02 | tar -xJf - -C segmentation-evidence
python3 results/2026-11-07-enterprise-segmentation-v1/restore_capture.py segmentation-evidence
python3 enterprise-segmentation-v1/analyze.py replay --cache "$CACHE" --capture segmentation-evidence/capture.json.gz --out segmentation-replay.json
python3 enterprise-segmentation-v1/analyze.py controls --cache "$CACHE" --capture segmentation-evidence/capture.json.gz --out segmentation-controls.json
```

The archive contains `capture.codec.json`, `raw/` and build/execution provenance;
the inventory records every member identity. The restore step recompresses the
exact object-table payload and requires the original measured gzip SHA-256.
It was exercised with Python 3.13.5; incompatible gzip encoders fail closed.
No capture content is changed. Use the analyzer to decode the restored capture.
Output paths must be new. Replay should report `REPLAY_VALID`; inspect typed
populations and reproduction rows, not just the process exit. Extraction and
byte-exact restoration were verified separately from the original collection.
The three ordered archive parts are each below 2 MiB. Their concatenation and
every regular member have recorded sizes and SHA-256 hashes in the inventory.

### Collect the segmentation comparison

Build `cmd/beir` from a clean anonymous checkout of public product commit
`a65d9fea1ce5d903e0c672d4cea62e6ce6272654`, tree
`7cae64f2eb975b9beb2edaadc7923a40547eae60`. The recorded build used
`go build -o beir ./cmd/beir`, Go 1.27.1, linux/amd64 and `CGO_ENABLED=0`;
binary metadata reports `vcs.modified=false`. The measured binary was
13,227,595 bytes, SHA-256
`56d8c58d71e42badb57f95c74d00c3a0bf4a0c71fd1822fa85b665ef72865408`.
A rebuild's byte identity can depend on its build environment.

Set `BEIR` to the absolute path of the built binary. Supply a JSON publication
receipt with `public_head`, `public_tree`, and `binary_identity` containing
`sha256` and `bytes` for that binary. This receipt records provenance; it does
not authenticate execution. From the companion repository root:

```sh
python3 enterprise-segmentation-v1/prepare.py --cache "$CACHE" --out enrollment-check.json
cmp enterprise-segmentation-v1/enrollment.json enrollment-check.json
python3 enterprise-segmentation-v1/run.py --cache "$CACHE" --beir "$BEIR" --publication publication.json --out collection
python3 enterprise-segmentation-v1/analyze.py replay --cache "$CACHE" --capture collection/capture.json.gz --out analysis.json
python3 enterprise-segmentation-v1/analyze.py controls --cache "$CACHE" --capture collection/capture.json.gz --out controls.json
```

Use a new collection directory and preserve every attempt and partial capture.
The schedule creates a fresh store per pass and segment policy, then reuses
that store only for the 4,096-byte budget. Reproduction repeats the same
questions; it is not a held-out population. Zero additional questions meet the
frozen full-gold, source/category and unambiguous-version criteria.
Confirmation remains `UNMET_ELIGIBLE20`; do not shrink the required 20.

One 1,800-second collection cap covers materialization, ingest/rebuild, queries
and capture work. Query timeout is 30 seconds; normalized text is bounded by
8 MiB, with inherited source/cache/member bounds. There are no retries, model
calls, downloads or QMD setup. Final capture serialization may finish after the
deadline. Preparation failures remain arm-level failures; unattempted questions
remain `NOT_RUN`. A journal prefix survives a truncated report, and an unknown
interruption is not relabeled as a query timeout.

Replay binds native content/configuration, canonical source slices, trail
selections and document metrics. Controls mutate input identity, segmentation
identity and packed selections. These checks establish recorded consistency,
not historical execution authenticity or an independent implementation of the
segmentation algorithm. Compare candidate rank/recall separately from packed
gold-document coverage. CPU and RSS cover whole child-process endpoints, not
isolated query costs. Gold-document identity is not semantic sufficiency;
unknown relevance is not negative. No monotonicity, answer-quality,
independent-company or leaderboard claim follows. Historical failed 4 MiB
preparation, measured 8 MiB v2, QMD failure/overshoot and source pins remain
unchanged.


## MCP source-scoped classifications

Run the additive producer only against the exact published product commit from a
clean anonymous checkout. These commands are instructions, not capture results:

```sh
export PUBLIC_HEAD=EXACT_PUBLIC_PRODUCT_COMMIT
work=$(mktemp -d /tmp/mousa-classifications-public.XXXXXX)
git -c credential.helper= clone https://github.com/graydeon/mousa.git "$work/product"
git -C "$work/product" checkout --detach "$PUBLIC_HEAD"
(cd "$work/product" && GOWORK=off CGO_ENABLED=0 GOAMD64=v1 go build -o "$work/mousa" ./cmd/mousa)
export PUBLIC_SOURCE="$work/product" BINARY="$work/mousa"
export RESULT=results/NEW-mcp-classifications
python3 -m unittest discover -s mcp-classifications -p 'test_*.py'
sh mcp-classifications/run-public.sh
```

Run from this repository root. No tokenizer or optional inference backend is needed:
the workflow makes byte-budget queries and reports zero independent token counts.
The runner freezes implementation hashes and the public head/tree, retains exact
scheduled request/response frames and native policy setup outputs/exits, captures
two fresh stores, replays both, compares stable producing facts and regenerates
ten rehashed controls. Controls alter scheduled input, source binding,
authorization, label, confidence, ordered basis, returned identity, query pins,
boolean coercion and duplicate embedded JSON. Pure regression tests distinguish
explicit integer confidence 0 from omission, null, boolean, string and float.

The main workflow uses only MCP sync/export/put/retry/get/query for classification.
Native `access` is separately recorded policy setup, not classification support.
It exercises segment subjects, ordered representation/source basis, exact retries,
separately versioned assertions, reader/ingestion-only/admin-only permissions,
foreign scoped reads, denial with no payload and unchanged retrieval. It does not
claim all-subject, HTTP principal/scope, concurrency or damaged-store coverage;
those require product tests. Native cross-source storage is not MCP cross-source
support. No semantic correctness, factual truth or calibration is measured.

Failure preserves partial capture bytes; use a new result path rather than
overwriting evidence. After successful captures, the runner creates `manifest.json`
with `tools/make_manifest.py` and checks all registered results. Review the actual
receipts and add their public identities/results to the evidence overview only
after capture. Do not register an empty or prospective result directory.


## MCP source-scoped supersession administration

The additive `mcp-supersession-admin/capture.py` producer reuses the prior strict
outer/embedded JSON and scheduled-request replay infrastructure without changing
historical producers, protocols or results. Freeze and capture only after product
publication, against a clean anonymous checkout of its exact public commit:

```sh
export PUBLIC_HEAD=EXACT_PUBLIC_PRODUCT_COMMIT
work=$(mktemp -d /tmp/mousa-admin-public.XXXXXX)
git -c credential.helper= clone https://github.com/graydeon/mousa.git "$work/product"
git -C "$work/product" checkout --detach "$PUBLIC_HEAD"
(cd "$work/product" && GOWORK=off CGO_ENABLED=0 GOAMD64=v1 go build -o "$work/mousa" ./cmd/mousa)
export PUBLIC_SOURCE="$work/product" BINARY="$work/mousa"
export PY=/path/to/prepared/venv/bin/python CACHE=/path/to/prepared/tokenizer-cache
export RESULT=results/NEW-mcp-supersession-admin
sh mcp-supersession-admin/run-public.sh
```

Run from this repository root. Preserve the virtualenv interpreter path and
prepare official `tiktoken==0.12.0` with the offline `o200k_base` cache. The reused
driver reserves `/tmp/mousa-public-admin-unused-notes` and refuses a collision.
The new runner performs two fresh-store captures, strict replay, stable comparison,
rehashed semantic controls and manifest registration. It retains actual raw frames,
native policy argv/stdin/outputs/exits, MCP shutdown and producing identities.
Failure preserves the partial capture; use a new result directory for another run.
Preparation alone is not capture evidence or a passed result.

All replacement operations use MCP: sync/export/import, exact declaration pins,
declare/retry, activate/current retry, status, stale/metadata/foreign-source refusal,
deactivate and reactivate. Reader, ingestion-only and admin-only sessions distinguish
the startup permissions. Native `access` supplies the separate denied-read policy
fixture; it does not administer replacement records. Status denial must disclose
only decision metadata despite a successful authorized write. Lexical/vector/hybrid
support uses both packers and byte/token budgets, including unembedded byte-equal
old/twin support, independent full-render counts and retained history after
deactivation. Controls alter expectations, source binding, unauthorized refusals,
hidden status state and query suppression with refreshed stream hashes.

This stdio capture does not exercise HTTP authentication, concurrent writers or
damaged hidden storage; those product tests remain separate evidence. It makes no
semantic, authorship, performance or model-window claim. Historical capture limits
below describe their own pinned versions, not current source capabilities.

## Lexical token association supersession

The [paired public-head observations](results/2026-11-06-token-association-supersession)
passed both captures, replay, controls and stable comparison. Their result guide
contains offline replay commands. Historical producers, protocols and results
remain unchanged. For new collection, select an exact public product commit and
build from a clean anonymous checkout, not an unpublished working tree:

```sh
export PUBLIC_HEAD=EXACT_PUBLIC_PRODUCT_COMMIT
work=$(mktemp -d /tmp/mousa-token-triple-public.XXXXXX)
git -c credential.helper= clone https://github.com/graydeon/mousa.git "$work/product"
git -C "$work/product" checkout --detach "$PUBLIC_HEAD"
(cd "$work/product" && GOWORK=off CGO_ENABLED=0 GOAMD64=v1 go build -o "$work/mousa" ./cmd/mousa)
export PUBLIC_SOURCE="$work/product" BINARY="$work/mousa"
export PY=/path/to/prepared/venv/bin/python CACHE=/path/to/prepared/tokenizer-cache
export RESULT=results/NEW-token-association-supersession
sh token-association-supersession/run-public.sh
```

Run from this companion repository root, sequentially and separately from product
verification. Keep the virtualenv interpreter path; do not resolve its symlink to
a system Python. It must provide official tiktoken 0.12.0 and the prepared
o200k_base cache. Reference counting forbids vocabulary downloads.
The fixed `/tmp/mousa-public-token-triple-notes` fixture must not already exist;
the producer refuses a collision rather than deleting another owner's directory.
The runner creates the new result directory and frozen exact-head protocol only
when invoked; it records no fabricated pre-publication product pin.

Each pass creates its own writable store. Native directory/JSONL byte-pair checks
reuse the historical composition fixture; native directory/JSONL and configured MCP token
triples exercise both packers, primary and target suppression, exact fit, one-token
and one-byte misses, omitted/false compatibility, no-declaration v8, v13 history
and native recount. Empty CLI association flags retain omitted/false no-op behavior;
true rejects in byte/token modes before creating an absent store. Vector/hybrid
associations remain precise MCP invalid-argument refusals.

Raw native argv/stdin/stdout/stderr/exits, MCP request/response frames and shutdown,
exact producing identities and independent whole-render counts are retained.
Stable comparison excludes only the reused helper's per-call query/authorization
identities and evaluation/latency times; packet/content/administration identities
remain compared. Replay regenerates the schedule and validates source-bound fixture,
history and count facts. Rehashed request/count/suppression and embedded-text
duplicate-key controls must fail their named detector, not a stale stream hash.

The runner writes replay/control/comparison receipts and registers the new run
with `tools/make_manifest.py`, then calls `python3 tools/verify_results.py`.
On failure, preserve `partial.json`, logs and the incomplete run; do not overwrite
it or count it as a passed capture. Register retained failure artifacts separately
before the archive gate. No executable or SQLite store is exported.
These synthetic client observations do not establish semantic sufficiency,
authenticated authorship, model-window fit, performance or internal transaction
race/cancellation behavior. No enterprise campaign, generation or judging runs.


## EnterpriseRAG pilot v2: measured retrieval and packing

Use the [separate frozen 8 MiB controller](enterprise-retrieval-pilot-v2) and
[actual result archive](results/2026-11-03-enterprise-retrieval-pilot-v2).
Build its exact corrected public product head and run the execute command once:
it includes the first pass and an independent fresh-store reproduction under
one 30-minute measured cap. Both use the same 20 questions and full 500-document
rendering as v1. Replay verifies pinned source bytes and recalculates metrics
without querying; controls regenerate four valid rehashed semantic mutations.
Seven required arms scored all 20 questions; optional QMD is NOT_RUN after the
retained bounded setup failure. V1 below keeps its original cap and failure.
Numeric native candidate scores are not exposed by the BEIR journal; raw ordered
rankings and selected identities/bytes are preserved separately. SQLite returned
scores are retained. No generation, embeddings, judges or paid APIs are used.


## EnterpriseRAG pilot preparation failure

Follow the [pinned source and reproduction commands](enterprise-retrieval-pilot).
The [executed archive](results/2026-11-03-enterprise-retrieval-pilot) preserves all
20 enrolled question IDs, original labels, physical mappings, the complete
500-document membership and per-arm NOT RUN outcomes. Reproduce the bound failure,
not a smaller substitute corpus: 4,970,133 normalized text bytes exceed 4,194,304.
No enterprise index or retrieval store was created. The independent-cache
reproduction compares exact stable preparation facts; it is not a fresh-store
retrieval reproduction. The separate two-document synthetic sanity exercises the
existing binary and SQLite FTS5 without being counted as benchmark evidence.
Root archive verification checks file hashes; source-bound semantic replay and
rehashed controls use the commands in the pilot instructions.


## Native attributed classification administration

Use the [bounded client instructions](classification-admin) and exact public
head/tree in its protocol. Capture twice on separate temporary JSONL stores, replay
the saved streams, regenerate the rehashed returned-label mutation and compare the
canonical assertions and fixed evidence pins exactly. Query request/decision/trail
identities and timing are invocation-specific and are excluded from that comparison.
The [paired archive](results/2026-11-02-classification-admin) retains each producing
record and the intended `assertion-facts-binding` rejection.

Only segment subjects and representation basis are exercised publicly here.
Product tests establish all typed forms, strict draft input, row/link idempotence,
atomic rollback and canonical damage/startup behavior. Repeated matching client
output is not a database invariance proof. No product imports, SQL reads, binary or
database export, inference, secret scanning, classification-based authorization,
semantic/performance campaign or historical archive rewrite is involved.


## Measured declared supporting context after checked admission

Use the [versioned corrected-pin client](token-associations-checked-v2) and
the [corrected archive's exact public head/tree](results/2026-11-02-token-associations-checked-v2/build.json).
Build from that clean anonymous source. With the prepared official offline
tokenizer/cache, capture twice on fresh stores using the fixed directory root,
then replay each run, regenerate its three rehashed controls and compare the
63 stable rows. Each run independently checks 39 complete rendering counts/hashes,
native directory/JSONL and configured MCP, both packers, documented term-policy
coverage, exact/short notes, producing history/recount, refusal and fresh denial.
Verify outer and archive-member hashes before replaying extracted observations.

The [original client](token-associations) and
[original archive](results/2026-11-02-token-associations) retain their own product
pin and frozen bytes. Replay each version with its own protocol; the corrected
comparison covers only its two runs. Normal captures do not establish hostile
canonical overflow rejection, semantic sufficiency, authenticated authorship,
performance or universal model-window safety.

## MCP declared supporting context

Follow the [standard-library client instructions](mcp-associations) using the
exact public product head/tree in [the paired archive](results/2026-10-31-mcp-associations/build.json).
Build from that clean anonymous source, then capture twice on separate fresh
stores. Replay regenerates the fixed stdio schedule and binds producing
identities, closed schemas, primary/supporting provenance and v3 history under
fresh authorization. Both packers/term policies, default/unfired declarations,
omissions and validation refusals are included. Rehashed declaration-request
and associated-content-digest controls must fail their intended assertions,
not just archive hashes. Compare only after each run's independent replay;
enumerated fresh-ID/timing exclusions are retained in the comparison receipt.
Normal authorization may write audit evidence; this client opens no SQLite
tables and makes no all-table-unchanged assertion. Run the archive verifier
separately. This is protocol/selection evidence, not an answer-quality, recall,
completeness, truth, long-horizon reliability or performance experiment.

## Vector/hybrid supersession with measured token budgets

Use the [token-composition client instructions](vector-token-supersession) and
the [paired archive's exact public head/tree](results/2026-10-31-vector-hybrid-token-supersession/build.json).
Build a clean anonymous product checkout and run two separate fresh stores with
the prepared official offline encoder/cache. Each fixed schedule includes both
modes/packers, omitted/false/enforced changed context, complete-rendering exact
fit/pressure, reservations/zero allowance, byte pressure, withheld twins,
all-withheld outcomes and producing history/recount.

Replay each archived capture with the bound driver, regenerate four rehashed
request/count/selection/history controls per run, and compare complete results
using only the explicit fresh-ID/time exclusions. Verify bounded regular archive
membership and every member hash before extraction; run the repository verifier
separately. No canonical database/binary is exported. Directory, denial,
source-admission/import, internal graph/corruption/concurrency and worker-fault
acceptance remain product-local, not client-capture claims. No semantic quality,
performance or universal model-window guarantee follows.


## Byte-packed vector/hybrid supersession

Follow the [standard-library client instructions](vector-supersession) using the
exact public product head/tree in [the paired archive](results/2026-10-30-vector-hybrid-supersession/build.json).
Build a clean anonymous product checkout, then capture twice against separate
fresh stores. Native JSONL preparation, both query modes/packers, MCP independent
history flags, successor withdrawal and old recorded history are scheduled.
Replay binds every argument/input and raw JSON-RPC request to the regenerated
schedule, verifies discovered closed output schemas, producing ranks/coverage,
exact released pins/text and recorded consultation. Four coherently rehashed
request/count/selection/history controls must fail their intended detectors.
The archive retains both complete runs, their summaries and the first failed
cross-run comparison receipt. Normalize only the ID/time fields listed in
`comparison.json`; preserve all remaining properties and raw observations.
Run `python3 tools/verify_results.py` separately. No tokenizer, model, semantic
quality, performance or old-text reconstruction claim is part of this byte slice.


## Lexical supersession with whole-context token budgets

Use the [combined client instructions](token-supersession) and exact public head/
tree in [the paired archive](results/2026-10-24-lexical-token-supersession/build.json).
Prepare the external official tokenizer/cache, build the clean public product
checkout, and run `capture` twice against separate fresh stores. Replay binds
native arguments/inputs and raw JSON-RPC requests to the regenerated schedule,
reconstructs survivor rendering from actual retained pins, independently counts
it, and checks recorded history after withdrawal/deactivation. `controls` must
reject the rehashed changed request, wrong withheld count and wrong historical
selection. Run the exact archive verifier separately. Directory header identities
vary with the temporary absolute path; fixed-alias JSONL rendering observations
are compared across the two runs. This is synthetic client/counting evidence,
not graph/corruption/concurrency coverage, model integration or quality/performance.
The schedule also replaces a predecessor with 65 full-size segments (266240 bytes)
through native JSONL sync, prepares pins through ordinary queries, and checks
native/MCP empty and small-survivor context under both packers. Equivalent
nonsuppressed requests retain the aggregate-limit failure. No embedding export
is used for the oversized source. One earlier runner assertion failure and its
raw client events remain recorded separately from the two passing captures.

## MCP external embedding export/import

The [MCP embedding client instructions](mcp-embeddings) build the exact public
product head in [the paired archive](results/2026-10-23-mcp-embedding-workflow/build.json).
Run the standard-library driver twice with distinct absent output paths for
separate fresh stores. The measured workflow syncs/exports/imports/queries through
MCP; native vector preparation and SQLite access are not used. Replay binds raw
request bytes to the regenerated schedule, checks discovered output schemas and
known cosine/RRF/history identities, and verifies retry/stale/write-permission
outcomes. `controls` must reject changed import values and a fabricated read-only
success after stream hashes/envelopes are repaired. Run the archive verifier
separately. No model, semantic quality, performance or token-window claim follows.

## MCP measured whole-context token budgets

The [MCP token client instructions](mcp-tokens) build the exact public product head
in [the paired archive](results/2026-10-22-mcp-token-budgets/build.json) and prepare
official `tiktoken==0.12.0` / `o200k_base` explicitly. Run the driver with that
venv interpreter and prepared cache. Capture and fresh-store reproduction retain
raw stdio streams/exits, native preparation and independent whole-context
reference token IDs. Replay validates selected rendering/count/digest, budget
binding, omitted defaults and producing history; three coherently rehashed
controls check altered count/context and changed scheduled token cap. Run the
existing archive verifier separately. No model, quality or window-safety claim.

## MCP supplied-vector and hybrid queries

The [MCP retrieval instructions](mcp-retrieval) build the exact public product head
in [the paired archive](results/2026-10-22-mcp-retrieval/build.json), prepare embeddings
with native commands, then negotiate and call stdio MCP without product imports
or SQLite access. Use fresh output paths for independent stores. Replay `verify`
checks scheduled request bytes, strict JSON types, discovered closed schemas,
selected evidence and recorded producing history; `controls` regenerates coherently
rehashed incorrect response/request cases and requires their intended detector.
Run the exact archive verifier separately. These synthetic observations do not
measure semantic retrieval quality, models, latency or token-window safety.


## Native token-aware context packing

The [token example instructions](native-tokens) prepare an isolated official
Python tokenizer/cache explicitly, then build the exact public product head in
[the paired capture](results/2026-10-22-native-tokens/build.json). The driver
executes native directory/JSONL lexical/vector/hybrid queries under both packers,
reconstructs the selected rendering from exported pins and fixture bytes, and
independently counts the entire context with `encode_ordinary`. It records raw
reference token IDs, digests, released bytes and 48 native command receipts per
run. Capture and reproduction use fresh stores; volatile directory pins and
header token costs are not cross-run goldens. The driver calls no model and does
not open SQLite itself. Run the existing archive verifier separately; hashes
are integrity evidence, not proof a tokenizer or build ran.

## Native hybrid lexical/vector retrieval

The [hybrid example](native-hybrid) builds the exact public head recorded in
[the paired capture](results/2026-10-21-native-hybrid/build.json), then runs a
small stdlib driver against fresh directory and JSONL stores. It compares real
lexical-only, vector-only and fused selection, independently derives fixed RRF
values with rational arithmetic, and checks both packers, restart, partial
coverage, revision exclusion, producing v6 history and fresh denial. Capture and
reproduction each retain all 34 command inputs/outputs/exits. This is not a model
or quality study. Run `python3 tools/verify_results.py` separately for archived
file integrity; hashes do not prove the driver's behavioral claims.

## Native caller-supplied vectors

The [vector example instructions](native-vectors) build the exact public product
head recorded in [the capture](results/2026-10-21-native-vectors/build.json), then
run a bounded stdlib driver against fresh directory and JSONL stores. It exercises
native input export, synthetic vector import, exact cosine queries, both packing
policies, packet/trail readback, restart and stale-revision exclusion. It neither
opens SQLite nor runs a model. Use absent output paths and preserve producing-run
identities; a new directory root has different canonical pins. Archive verification
checks file hashes separately from the driver's runtime behavior assertions.

## Startup runner validation

The [supersession startup tools](startup-verification/README.md#tools-and-implementation-review)
implement the accepted [PR31 protocol](https://github.com/graydeon/mousa-benchmarks/pull/31).
Use `prepare.py`, `run.py smoke`, `controls.py` and `analyze.py verify` for native
fixture and receipt checks without collection. Keep outputs outside source
checkouts and use the exact product/protocol/toolchain pins in that document.
**Measured collection NOT RUN**. A later capture needs independent final-head
runner review and separate authorization; unmeasured checks establish no startup-cost result.
For this revision, use bounded unit/sampler/temporary-SQLite controls and offline
receipt mutations; do not repeat full preparation or smoke to replace the retained
failure. `analyze.py pack` refuses all public evidence export pending review of
the complete-provenance boundary. The original 39/40 native smoke and oversized
archive remain failed observations, not corrected-source acceptance. See the
[retained holds and proposed amendments](startup-verification/README.md#revision-checks-and-retained-holds).


## MCP historical inspection

The [inspection protocol and instructions](mcp-trail-supersession) describe the
clean public product checkout, exact Go build, binary pin, two fresh-store captures,
offline replay and rehashed semantic controls. The
[observation archive](results/2026-10-13-mcp-trail-supersession) retains raw traffic,
process exits and complete logical SQLite snapshots in a lossless indexed format.
Use its corrected PR75 commit, not current main or the older query-only pin.
Denied inspection legitimately commits a fresh authorization decision; orphaned
decision parents remain source-masked at an already-open scoped boundary.

## CLI and warm-path comparison

From a Mousa checkout, with this repository at ../mousa-benchmarks:

```sh
mkdir -p ../mousa-benchmarks/.runs
CGO_ENABLED=0 go build -trimpath -buildvcs=false -o ../mousa-cli ./cmd/mousa
CGO_ENABLED=0 go build -trimpath -buildvcs=false -o ../mousa-warm ./eval/local
npm ci --prefix ../mousa-benchmarks/comparisons/qmd --ignore-scripts --omit=optional --no-audit --no-fund
python3 eval/local/workflow.py --mousa ../mousa-cli --warm ../mousa-warm --qmd ../mousa-benchmarks/comparisons/qmd/node_modules/@tobilu/qmd/bin/qmd --dependency-lock ../mousa-benchmarks/comparisons/qmd/package-lock.json --documents 24 --repeats 3 --output ../mousa-benchmarks/.runs/workflow-24.json
```

Use runtime versions supported by the selected harness revision. QMD is exercised in lexical mode, not as a complete RAG comparison. Native dependency requirements vary by platform. Install scripts are disabled deliberately; do not enable them automatically to repair installation failures.

The runner hashes the explicitly supplied dependency lockfile. Record this repository's commit alongside the report: the product source manifest no longer includes relocated dependency files. New observations can differ with source revision, hardware, cache state, contention and runtime versions.

## Supersession contract checks

The [supersession archive](results/2026-10-06-supersession-core) freezes an earlier
Mousa commit/tree and expected test names. Check out the exact public commit in
its `protocol.json`, not current main, then run:

```sh
python3 results/2026-10-06-supersession-core/reproduce.py --mousa /path/to/pinned-mousa --output /path/to/new-capture
```

The checkout must be clean and the output directory must not exist. The runner
sets `GOWORK=off`, records that setting in new observations, and rejects failed,
skipped or missing expected tests. It does not isolate every Go environment
setting. The original archive's events, observation and protocol remain unchanged;
they do not certify later product fixes or prove historical workspace isolation.
The run README also explains how to reproduce the two preserved negative cases
in a disposable checkout. No live user store or model is needed.

## Native supersession administration capture

The [administration archive](results/2026-10-07-native-supersession-administration)
freezes one source revision, the synthetic JSONL/declaration/activation inputs and
the expected CLI behavior, then drives only the native CLI against a fresh synthetic
store. Check out the public commit in its `protocol.json`, not current main, then run:

```sh
python3 results/2026-10-07-native-supersession-administration/reproduce.py \
  --mousa /path/to/pinned-mousa --output /path/to/new-capture
```

The checkout must be clean and at the pinned commit and tree, the frozen input hashes
must match, and the output directory must not exist. Add `--work <new-directory>` to
keep the throwaway binary and synthetic stores. The runner sets `GOWORK=off` and
`CGO_ENABLED=0`, hashes the executable without publishing it, writes only
`observed.json` and `assertions.json`, and exits 2 when a precondition fails and 1 when
an assertion fails. It opens no accepted or live store and needs no network, model or
inference service. Its README explains the frozen-input provenance, the exact
assertions and the disposable negative controls.

## Native supersession enforcement protocol

The [enforcement protocol](native-supersession-enforcement/README.md) and its
[native archive](results/2026-10-11-native-supersession-enforcement-corrected) pin actual
observations against [Mousa PR61](https://github.com/graydeon/mousa/pull/61) public
head `e0837750bc8972d6fc7ebffc86a8fba05a0ee1f4` (tree
`be4e7d8c5a9bfa4ebb8c650660a75f0b8ac41c4b`), not main.
Use its exact public head/tree and the executable/build receipt in `product-pin.json`.
The standalone stdlib runner and independently verified fixtures are committed.
Keep new output paths outside clean product and companion checkouts.

```sh
python3 native-supersession-enforcement/run.py capture \
  --source "$PRODUCT" --binary "$BINARY" \
  --pin results/2026-10-11-native-supersession-enforcement-corrected/product-pin.json \
  --expectations native-supersession-enforcement/expectations.json \
  --output /tmp/enforcement-new
python3 native-supersession-enforcement/run.py verify /tmp/enforcement-new
```

The original committed-tree capture and a fresh independent-store reproduction
both passed; the archive records their actual controller exits, complete native
receipts and negative controls. Repeat from the clean published companion tree
after publication; collection and publication execution pins are distinct.
For offline replay, extract `capture.tar.gz` into a new directory and pass its
`capture` directory to `verify`. The shared `tools/verify_results.py` checks outer
archive hashes, not native conclusions; `archive-members.json` identifies every
regular compressed member.

Expected packet and stable selection values were frozen only after a verified
actual pilot. Fresh request/decision/trail identities and evaluation timestamps are
retained individually, not reused as cross-run goldens. Every read/rejection has
all-table logical SQLite fingerprints including committed WAL-visible state;
query and trail audit writes are separated from immutable administration/index state.

Startup corruption refusal is not transaction rollback evidence. The protocol
does not claim native synchronized snapshot ordering, per-candidate lifecycle
injection, semantic correctness, authenticated authorship or performance.
Historical result bytes and the shared archive verifier remain unchanged.

## MCP query supersession protocol

The [MCP query supersession protocol](mcp-query-supersession/README.md) and its
[archive](results/2026-10-12-mcp-query-supersession-schedule-binding) pin stdio MCP client
observations against [Mousa PR69](https://github.com/graydeon/mousa/pull/69) public head
`7ae0d8768e7cd203c48478412b493e1255c97b11` (tree
`2b8b14f76e0907f3ca3fd5dc8c33934567e61d14`), not main.
Use its exact public head/tree and the executable/build receipt in `product-pin.json`.
The standalone stdlib runner, the frozen fixture, the protocol and the pre-query discovery
baseline are committed. Keep new output paths outside clean product and companion checkouts.

```sh
python3 mcp-query-supersession/run.py capture \
  --source "$PRODUCT" --binary "$BINARY" \
  --pin results/2026-10-12-mcp-query-supersession-schedule-binding/product-pin.json \
  --expectations mcp-query-supersession/expectations.json \
  --output /tmp/mcp-query-new
python3 mcp-query-supersession/run.py verify /tmp/mcp-query-new
```

The committed-tree capture and a fresh independent-store reproduction both passed; the
archive records their actual controller exits, complete wire receipts, fingerprints and
negative controls. Repeat from the clean published companion tree after publication; the
collection and publication execution pins are distinct. For offline replay, extract
`capture.tar.gz` into a new directory and pass its `capture` directory to `verify`. The
shared `tools/verify_results.py` checks outer archive hashes, not MCP conclusions;
`archive-members.json` identifies every regular compressed member.

Selection equality is over complete parsed JSON tool definitions and over recorded result
values, not over raw bytes: every session's exact request and response bytes are retained
as its own receipt. Each receipt is asserted back against the schedule that produced it, so
a recorded request must be the scheduled method, tool name and argument object, a raw
boundary frame must be its exact scheduled bytes, and a prepared command must carry its
scheduled argv and stdin. A generated frame is parsed with a decoder that reports a repeated
object key at any depth, and the comparisons that decide whether a replay is accepted are
made over canonical JSON, so a nested boolean is not a number, an integer is not a float and a
repeated key cannot hide behind the last of its values. The [second
revision](results/2026-10-12-mcp-query-supersession) and the [first
revision](results/2026-10-11-mcp-query-supersession) archives predate parts of that binding and
are replayed with the runner copy inside each of them; the accepted directory stores its four
observations as complete archives and the control receipt list, and regenerates each mutated
copy from the stored capture.

Expected packet, evidence and candidate values were frozen only after a verified actual
pilot. Fresh request, decision and trail identities and the recorded trail's own identities
stay in each step receipt; they are not cross-run goldens. Every read or rejection has an
all-table logical SQLite fingerprint including committed WAL-visible state, and query and
inspection audit writes are separated from immutable administration and index state.
Startup refusal on an absent path is store creation, not transaction rollback evidence.
The protocol does not claim semantic correctness, authentication, latency, concurrency or
performance, and opted-in trail inspection remains unimplemented.

## Supersession-safe lexical supporting context

The [bounded client schedule](association-supersession) uses public native
directory/JSONL commands and configured stdio MCP with explicit byte-only
supersession plus caller-declared associations. Its frozen protocol binds the
exact clean public product head/tree and existing strict stream/archive helpers.
Reproduction uses two fresh stores, offline replay and exact stable producing-fact
comparison; three rehashed controls reject changed requests, suppression facts
and selected support at named semantic detectors. Raw argv, stdin/stdout/stderr,
process exits, complete request populations and actual responses are retained.

Follow the linked instructions for sequential captures: the synthetic directory
path is fixed to preserve exact source/revision identity, created exclusively and
removed only by its owner. No SQL, product-package imports, tokenizer backend,
model calls, database/binary export or startup-study collection is involved.
Internal snapshot/rollback/canonical-damage properties are not public-client claims.

## Product correctness gate

This remains entirely inside Mousa and requires no companion checkout, Node, QMD, downloaded datasets or inference services:

```sh
CGO_ENABLED=0 go build -o mousa ./cmd/mousa
python3 eval/local/workflow_test.py --mousa ./mousa
```

## BEIR and lifecycle tools

Run cmd/beir, eval/beir and eval/local/lifecycle.py from the Mousa checkout using its revision-specific instructions. These tools share internal product contracts or acceptance helpers. Store suitable comparative results here with both repository revisions and input hashes.

Research summaries stay in Mousa; links to migrated observations are pinned to immutable commits here. Small compatibility golden files stay beside product tests.

## Vector/hybrid declared support

The additive `retrieval-associations/capture.py` producer completed
[paired observations](results/2026-11-06-vector-hybrid-associations) against public
product `62b725213ce8613a1b824d2e07a305721531fb76`. New captures require the exact
anonymous public head and a clean CGo-free binary built from it. A local working
tree or historical lexical capture pin is not a substitute.

From this repository root, with the prepared offline tiktoken 0.12.0 environment:

```sh
export PUBLIC_HEAD=62b725213ce8613a1b824d2e07a305721531fb76
export PUBLIC_SOURCE=/path/to/clean/anonymous/product-checkout
export BINARY=/path/to/binary-built-from-that-checkout
export PY=/path/to/prepared/venv/bin/python
export CACHE=/path/to/prepared/tokenizer-cache
export RESULT=results/NEW-vector-hybrid-associations
sh retrieval-associations/run-public.sh
```

The launcher freezes a new protocol, runs two sequential fresh-store captures,
replays both, runs rehashed count/support/history/strict-JSON controls, compares
stable observations while retaining packet IDs, and registers every result
member using the existing manifest helper. Capture retains raw native argv,
stdin/stdout/stderr/exits and MCP frames, including actual producing IDs.
Do not run captures concurrently: the fixed directory fixture preserves source
identity between independent runs. Failed attempts retain `partial.json`; choose
a new result directory for a new attempt rather than replacing failed evidence.

The matrix covers native directory and JSONL plus configured MCP export/import,
vector/hybrid queries, original/exact-v1, byte/token budgets and omitted/false/true
supersession. Named checks compare primary evidence and retrieval ranks/coverage
against association-free queries and verify authorized unembedded support.
Independent counts reconstruct and count the entire returned context; native
retained-text recount is separate from MCP's recorded detail projection.

For the published losslessly packaged capture, extract into a temporary directory
and replay without modifying the registered result:

```sh
RESULT=results/2026-11-06-vector-hybrid-associations
REPLAY=$(mktemp -d)
tar -xJf "$RESULT/raw-captures.tar.xz" -C "$REPLAY"
"$PY" retrieval-associations/capture.py verify --protocol "$RESULT/protocol.json" \
  --cache "$CACHE" --output "$REPLAY/first"
"$PY" retrieval-associations/capture.py verify --protocol "$RESULT/protocol.json" \
  --cache "$CACHE" --output "$REPLAY/second"
"$PY" retrieval-associations/capture.py compare --protocol "$RESULT/protocol.json" \
  --cache "$CACHE" --output "$REPLAY/first" --other "$REPLAY/second"
python3 tools/verify_results.py
```

These synthetic values establish protocol and arithmetic, not semantic sufficiency,
retrieval quality, authenticated authorship or model-window safety. Replay checks
stored consistency, not authenticated historical execution or universal tamper
proof. Existing producers, protocols, pins, failed attempts and research results
remain unchanged; this capture does not repeat or supersede the development pilot.
