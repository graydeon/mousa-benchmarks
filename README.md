# Mousa benchmarks

Public benchmark results, comparison dependencies, and reproduction guidance for [Mousa](https://github.com/graydeon/mousa).

These are development measurements, including failed experiments and limitations. They do not establish general superiority over other retrieval systems.

The [supersession startup study tools](startup-verification) implement the accepted
CPU-only fresh-process protocol, native preparation, unmeasured smoke checks and
receipt replay. **Measured collection NOT RUN**; implementation review precedes
any separately authorized capture. Smoke and control timings are not performance results.
Public startup evidence export currently fails closed. The
[public evidence contract proposal](startup-verification/PUBLIC_EVIDENCE_PROPOSAL.md)
for the full v2 format is **PROPOSED / NOT IMPLEMENTED / NOT RATIFIED**.
An isolated [candidate row codec](startup-verification/PUBLIC_EVIDENCE_PROPOSAL.md#scoped-candidate-row-structural-contract-only)
implements structural validation only, not public eligibility or replay.
Neither authorizes export or collection. The retained native smoke is 39/40
with a ten-second censored failure; its complete archive exceeds the frozen 4 MiB cap. The
[revision checks and retained holds](startup-verification/README.md#revision-checks-and-retained-holds)
remain unchanged.

Host sampling now includes final seed checks and storage accounting, with owned
sampler cleanup and partial-receipt persistence when those checks fail or are
interrupted. Synthetic producer controls check finalization coverage; they do
not replace native acceptance or the collection/publication holds.

## Current evidence boundary

The [native token-packing example](native-tokens) selects whole passages against
the exact returned rendered context, using an optional prepared official
`tiktoken==0.12.0`/`o200k_base` backend. Its
[corrected-public-head capture and fresh-store reproduction](results/2026-10-22-native-tokens-corrected)
each record 48 native calls and 20 independent whole-rendering token checks,
covering directory/JSONL lexical, vector and hybrid modes with both packers,
token pressure, v7 history/recount and fresh denial. Counts cover returned
context only, not unknown application/model framing; no quality or performance
claim follows. Older captures and startup holds remain unchanged.
The [original capture](results/2026-10-22-native-tokens) retains its `50a1b43`
pin and bytes as historical observations. Neither single-source fixture proves
mixed-ancestry lifecycle filtering: issue #85's graph case is covered by product
regressions, while the corrected capture checks ordinary native compatibility.

The [native hybrid example](native-hybrid) combines lexical and supplied-vector
branches with equal-weight RRF(k=60). Its
[capture and independent fresh-store reproduction](results/2026-10-21-native-hybrid)
show an overlapping second-ranked passage displacing either branch's first hit,
both byte packers, explicit coverage and v6 history under fresh access.
Synthetic vectors establish arithmetic/protocol behavior only; no model or
retrieval-quality claim follows. The earlier vector-only capture keeps its own pin.

The [native caller-supplied vector example](native-vectors) demonstrates directory
and JSONL input export/import, exact cosine ordering, both byte-packing policies,
v5 trail/packet readback and stale-revision exclusion. The
[capture and fresh-store reproduction](results/2026-10-21-native-vectors) retain
the exact public product/build pins and raw native command receipts. Constructed
vectors prove protocol/ranking arithmetic only; no model, semantic-quality,
performance or model-window claim is made.

The [directory supersession example and observations](directory-supersession)
demonstrate ordinary Markdown/text directory queries with explicit native declaration
and activation, unchanged default/false selection, both packing policies, producing
v4 trail pins and a predecessor revision update. One capture and one fresh-store
reproduction target public Mousa PR80; this is native capability evidence, not
semantic-quality or performance acceptance.

The [native enforcement archive](results/2026-10-11-native-supersession-enforcement-corrected)
records independent subprocess acceptance under both packing policies against
[Mousa PR61](https://github.com/graydeon/mousa/pull/61), corrected public commit
`e0837750bc8972d6fc7ebffc86a8fba05a0ee1f4`, tree `be4e7d8c5a9bfa4ebb8c650660a75f0b8ac41c4b`.
It includes exact-pin withholding, unchanged defaults, transitions, stale pins, survivor
packing, historical reads, fresh-store reproduction, the invalid-expression exit/store
boundary matrix and negative controls. That tested PR is not claimed merged or available
on main. It is synthetic behavior evidence, not a performance, semantic-memory,
retrieval-quality or authentication result. The earlier
[pre-correction capture](results/2026-10-11-native-supersession-enforcement) against
PR61's previous head `bbf73a91788aac3aeb29ac0e6c74153d32363f14` is retained unchanged as
that observation; its 44 frozen selection cases are identical to the corrected pin's.

The [MCP query supersession archive](results/2026-10-12-mcp-query-supersession-schedule-binding)
records independent stdio MCP client acceptance of the query opt-in against
[Mousa PR69](https://github.com/graydeon/mousa/pull/69) public commit
`7ae0d8768e7cd203c48478412b493e1255c97b11`, tree `2b8b14f76e0907f3ca3fd5dc8c33934567e61d14`.
A standalone standard-library runner speaks newline-delimited JSON-RPC over the real
stdio lifecycle and observes tool discovery against a pre-query baseline, omitted
versus explicit `false` equality, true withholding the exact pinned predecessor with
the declared count under both packing policies, budget and duplicate accounting, no
history, deactivation, a withdrawn successor, source denial, damaged activation
events, restart stability, the strict input boundary and the still-filtered
`mousa_trail` response. Every recorded receipt is asserted back against the schedule
that produced it, including each request's method, tool name and argument object,
the raw bytes of the deliberately unparseable frames, the absence of any repeated
object key in a generated frame and the JSON type of every compared value, and
`oneOf` requires exactly one matching branch. That PR is not claimed merged or
available on main. It is
synthetic client-boundary evidence, not semantic, retrieval-quality, performance or
authentication acceptance. Opted-in trail inspection was not implemented at that pin.

The [MCP historical inspection archive](results/2026-10-13-mcp-trail-supersession)
targets corrected [Mousa PR75](https://github.com/graydeon/mousa/pull/75) public commit
`5ffa0286b35ecf84b36abe53d029a78075c02b86`, tree `c73fb12a9ccdc6df65ad998a3039255a43dc6ad1`.
Its [standalone stdlib runner](mcp-trail-supersession) checks recorded v4 members,
native-created legacy history, fresh authorization audit writes, source-masked
orphan refusals and per-command logical SQLite state through real native/stdio
interfaces. It preserves the earlier query and native observations unchanged.
The inspection archive is synthetic client-boundary evidence, not a semantic,
performance, authentication or native-host acceptance result.

The prior [administration archive](results/2026-10-07-native-supersession-administration)
records declaration/activation lifecycle and an unchanged query baseline at its
own pinned revision. It remains administration-only evidence, not later enforcement.
The [tested capability matrix](https://github.com/graydeon/mousa/blob/e0837750bc8972d6fc7ebffc86a8fba05a0ee1f4/docs/CAPABILITIES.md#supersession-core-boundary)
distinguishes those boundaries.

The earlier supersession archive contains pinned product contract checks for
revision-bound declarations, immutable storage and activation history.

The [native enforcement protocol](native-supersession-enforcement) supplies the
standalone standard-library runner, independently verified synthetic fixture
construction and actual observed packet/stable-trail expectations. Each read or
rejected write has its own complete logical SQLite fingerprint, including WAL-visible
state; queries' legitimate audit writes are separated from administration/index changes.
Startup refusal is not already-open transaction rollback or snapshot-ordering proof.

Later product fixes do not change historical result identities or test counts.
Use each run's recorded source and protocol. The historical supersession runners force
`GOWORK=off` for new reproductions; the older archived observation did not
record workspace configuration. See that run README's dated correction.

## Contents

- [results/2026-09-16](results/2026-09-16): seven unchanged historical JSON reports. The directory date records migration, not collection.
- [results/2026-09-16-exact-packing](results/2026-09-16-exact-packing): matched opt-in exact-content packing measurements, frozen fixtures, individual observations and reproduction script.
- [results/2026-09-16-packing-scalability](results/2026-09-16-packing-scalability): exact-packing stage costs, 0/10/100-trail histories, snapshot-scoped ancestry reuse, allocations and all paired observations.
- [results/2026-09-16-history-diversity](results/2026-09-16-history-diversity): rejected historical-scan reuse candidate; large-history gains failed small-case latency and tail guards.
- [results/2026-09-17-history-free-diagnosis](results/2026-09-17-history-free-diagnosis): source/build analysis of the rejected historical-verification candidate, a terminated diagnostic and fixture-inspection smoke corrections. No new performance comparison or adoption.
- [results/2026-09-17-backup-decision](results/2026-09-17-backup-decision): caller-reviewed SQLite backup checklist, fixed supported/partial/unresolved cases, one-attempt follow-ups and whole-consumer costs.
- [results/2026-09-17-diagnostic-consumer](results/2026-09-17-diagnostic-consumer): inconclusive controlled follow-up on the rejected candidate and separate Git documentation consumer observations.
- [results/2026-09-17-corpus-boundaries](results/2026-09-17-corpus-boundaries): fixed Git documentation questions before and after adding separately attributed referenced fragments, including unsupported cases.
- [results/2026-09-17-associated-context](results/2026-09-17-associated-context): corrected three-arm declared-association comparison; the superseded mislabelled record is retained.
- [results/2026-09-17-associated-bounds](results/2026-09-17-associated-bounds): oversized-record failure and bounded target-passage enumeration; shared-host timings are descriptive.
- [results/2026-09-29-context-512](results/2026-09-29-context-512): one pinned Git interactive-hunk question comparing source-attributed prompt layouts under a 512-token rendered-content cap; no model answer or latency measurement.
- [results/2026-09-29-switch-default-remote](results/2026-09-29-switch-default-remote): a distinct Git switch configuration question misses the required parent passage and omits the retrieved fragment at 512 rendered-content tokens.
- [datasets/synthetic-fleet](datasets/synthetic-fleet): wholly generated corpora, labeled workloads, sample input and real CLI/database reproduction tools.
- [results/2026-09-30-synthetic-fleet](results/2026-09-30-synthetic-fleet): first live Codex/OMP/Hermes observations, generated database sizes and retained failures.
- [datasets/long-horizon](datasets/long-horizon): chronological persistent-memory fixtures with larger corpus profiles, revisions, withdrawal and process-restart checks.
- [results/2026-09-30-long-horizon](results/2026-09-30-long-horizon): known-key retention measurements; generated scale is distinct from tested database capacity.
- [results/2026-09-30-agent-memory](results/2026-09-30-agent-memory): native-MCP project-history passage coverage, correction/tombstone/restart checks, irrelevant evidence and exact measured receipts; no generated-answer or agent-acceptance result.
- [datasets/chronology](datasets/chronology): two named sources, explicit revision epochs, native prefix failures and receipt-bound query/packing comparisons.
- [results/2026-10-02-chronology](results/2026-10-02-chronology): frozen lifecycle acceptance, exact-span accounting, omissions and preserved negative observations; no model-quality or timing claim.
- [results/2026-10-06-supersession-core](results/2026-10-06-supersession-core): pinned declaration/persistence/activation contract tests and preserved integrity failures; no enforcement or semantic-quality claim.
- [results/2026-10-07-native-supersession-administration](results/2026-10-07-native-supersession-administration): native CLI capture of the declaration/activation lifecycle, rejections, read-only store behavior and an unchanged query baseline; no suppression, quality or timing claim.
- [native-supersession-enforcement](native-supersession-enforcement): independent native enforcement runner, frozen inputs and observed packet/trail selections.
- [results/2026-10-11-native-supersession-enforcement-corrected](results/2026-10-11-native-supersession-enforcement-corrected): paired native acceptance at PR61's corrected public tree, complete bounded captures, the invalid-expression boundary matrix, retained failures and negative controls; no performance claim.
- [results/2026-10-11-native-supersession-enforcement](results/2026-10-11-native-supersession-enforcement): the earlier pre-correction capture at PR61's previous head, retained unchanged as that observation.
- [mcp-query-supersession](mcp-query-supersession): independent stdio MCP client runner, frozen protocol, synthetic fixture and pre-query discovery baseline for the query supersession opt-in.
- [results/2026-10-12-mcp-query-supersession-schedule-binding](results/2026-10-12-mcp-query-supersession-schedule-binding): stdio MCP client acceptance of the query opt-in at PR69's public tree, with two independent captures, every recorded request bound to its scheduled operation, strict generated-frame parsing that rejects a repeated key at any depth, JSON-type-preserving comparisons at the frozen schedule and wire boundaries, exactly-one `oneOf` checking, the strict input boundary, restart, damaged-state refusal, forbidden-write and twenty mutated-capture controls with the directly recorded false condition; no performance or semantic claim.
- [results/2026-10-12-mcp-query-supersession](results/2026-10-12-mcp-query-supersession): the second revision of that capture, retained with a dated note; its runner bound requests to the schedule and rejected overlapping branches, but nested `true` compared equal to `1` and a repeated generated key kept its last value.
- [results/2026-10-11-mcp-query-supersession](results/2026-10-11-mcp-query-supersession): the first revision of that capture, retained with a dated note; its runner compared recorded requests with their own match metadata only, its `oneOf` check accepted overlapping branches, and it shared both later comparison holes.
- [comparisons/qmd](comparisons/qmd): pinned optional QMD comparison dependencies.
- [migration.json](migration.json): original Mousa commit, original paths, SHA-256 digests and sizes.
- [REPRODUCING.md](REPRODUCING.md): execution and provenance requirements.

Mousa retains product tests, required CLI client acceptance, small compatibility fixtures, BEIR integration and the Go warm-path probe. Go tools import Mousa internal packages; the Python comparison runner shares code with required acceptance. Run those tools from the matching Mousa checkout. This repository does not copy the engine or replace that harness.

## Archived reports

| Report | Scope |
| --- | --- |
| current-items.json | Earlier item lifecycle measurements |
| current-cli.json | Current-query CLI measurements |
| passage-policy.json | Segmentation quality and resource tradeoffs |
| prepared-statements.json | Prepared-statement experiment, not adopted |
| prepared-diagnosis.json | Follow-up diagnosis and limitations |
| workflow-24.json | 24-document evolving workflow |
| workflow-96.json | 96-document evolving workflow |

The [Mousa research report](https://github.com/graydeon/mousa/blob/main/docs/RESEARCH.md) explains methods and limitations. Some historical entries refer to source hashes or experimental artifacts that are not public Git commits. Retaining a report does not imply every historical experiment can be rerun from this repository alone.

Run `python3 tools/verify_results.py` with Python 3.9 or later to check migrated archive membership and each new run's file sizes and hashes. This does not rerun experiments or validate conclusions.

## Adding measurements

Keep archived files unchanged. Add a dated run directory with a manifest identifying the Mousa commit, benchmark repository commit, input hashes, binary and dependency hashes, commands, environment, repetitions, raw observations and failures. Separate warm and cold measurements and disclose shared-host contention. Preserve negative results; do not tune against held-out test data.

Do not commit credentials, private source data, model transcripts, installed dependencies, binaries or local database stores. Check dataset redistribution rights before uploading corpora. For large artifacts, use versioned public archives and checksums instead of growing ordinary source history without bounds.

## License

Migrated files retain Mousa's GNU AGPL v3 license; see [LICENSE](LICENSE). Third-party dependencies retain their respective licenses.
