# EnterpriseRAG lexical pilot v2

[Measured results](../results/2026-11-03-enterprise-retrieval-pilot-v2):
all seven required arms scored 20 questions each; optional QMD retained 20 NOT_RUN
rows after setup failure. The complete first pass and deterministic fresh-store
reproduction finished in 428.855789 seconds under the shared 1,800-second cap.
Native coverage curves, source-bound replay and four rehashed semantic controls
passed. The observations remain subject to independent review and acceptance.

This is a separate 8 MiB experiment, not a revision of the
[v1 failed preparation observation](../enterprise-retrieval-pilot). V1 retains its
4 MiB cap, original producer, native coverage refusal, 160 NOT_RUN outcomes and
zero scored questions. V2 keeps the same 20 question IDs, 500 physical documents,
logical labels, salt, complete rendering and source assets. The input contains
4,970,133 normalized bytes. The cap change was authorized before any enterprise
retrieval scores existed; no question replacement, text truncation, reference
repair or retrieval-driven selection is allowed.

## Frozen execution

`protocol.json` pins the corrected public product commit and binary, the immutable
v1 preparation/metric/stream helpers, and this thin execution controller.
`condition-diff.json` records every protocol difference. Schema and controller
identities distinguish the new experiment; execution and clock descriptions make
previously unused conditions executable without changing the baseline. The
independent input manifest binds enrollment lines, eligibility, physical corpus,
rendering and source counts. Preparation is independently compared with both v1
and the prospective 8 MiB preparation before any enterprise query.

The measured clock begins before first-pass preparation/materialization and covers
all ingestion, six Mousa arms, SQLite FTS5, native report validation and the second
complete pass on fresh writable stores. Both passes share one 1,800-second cap.
Each query retains its 30-second deadline. Build, optional dependency setup and
archive replay are separate. Source caches can be shared only after asset hashes
are verified; dataset and initial index manifests are checked before every reuse.
A run failure remains a typed failure, not an abstention or zero score. Raw command
streams, exit codes, journals and partial ledgers are retained, with no favorable
retry. No provider, embedding, generation, judge or reranker calls are made.

The eight enrolled arms are original/dedup verified rankings (limit 100), each
policy's traced engine packing at 1,024 and 4,096 bytes, whole-document SQLite FTS5,
and optional pinned QMD lexical search. All 20 questions remain enrolled for each
arm, including unavailable routes. Native mode/budget/policy comparisons and
coverage curves use the product commands without asserted coverage replacements.
Candidate rankings remain separate from selected document IDs and used bytes.
The native BEIR journal does not expose numerical candidate scores; those scores
are unavailable, not inferred from ranks. SQLite's returned BM25 scores are retained.

SQLite uses `unicode61 remove_diacritics 2`, OR-connected quoted ASCII alphanumeric
terms, ascending BM25 then physical item ID, and limit 100. This differs from
Mousa's segmented candidates and query preparation. Query timings are warm Go
harness request paths versus in-process raw SQLite execution; they are not a fair
product-performance league table. A QMD cold launcher would be a third endpoint.
The optional package setup uses the existing comparison lockfile, lifecycle
scripts disabled, no global installation or lock changes, and a 300-second/
256 MiB stop threshold. No lexical query is allowed unless setup and its no-model
path are verified.

## Metrics and evidence limits

Reuse v1 binary-label Recall@10/100, binary-gain nDCG@10 and MRR@10 definitions.
Gold labels are the original expected logical IDs mapped to unambiguous physical
items. Unknown relevance is not a proved negative label. Engine-selected gold
coverage at each pack budget is separate from candidate recall and does not prove
semantic support. Replay recomputes per-question metrics and coverage, binds them
to native journals, checks population and fresh-store identities, and checks native
summary values. Controls rehash valid archives before rejecting equal-count wrong
questions, wrong physical mappings, changed rankings and changed packed membership.

EnterpriseRAG-Bench uses generated/simulated-company data. This gold-enriched
500-document development subset removes most official distractors. It is not an
official, full-corpus, held-out, answer-quality, judge or leaderboard result and
supports no general superiority, factual-truth, model-window or long-horizon-memory
claim. Do not compare these metrics with vendor answer-quality scores under other
conditions. API billing is zero; CPU work and electricity are not literally free.
Original source pins, MIT license and attribution are retained in the results and
[v1 source description](../enterprise-retrieval-pilot/README.md#data-and-selection).

## Reproduce

Build a clean anonymous checkout of the exact product revision in `protocol.json`:

```sh
CGO_ENABLED=0 GOAMD64=v1 go build -o /tmp/beir ./cmd/beir
```

From this companion checkout, use owned output directories outside source. Reuse
an existing verified source cache, or use the immutable bounded downloader:

```sh
python3 enterprise-retrieval-pilot/prepare.py download --protocol enterprise-retrieval-pilot-v2/protocol.json --cache /tmp/enterprise-source
python3 enterprise-retrieval-pilot-v2/run.py execute --cache /tmp/enterprise-source --beir /tmp/beir --out /tmp/enterprise-v2
python3 enterprise-retrieval-pilot-v2/run.py replay --cache /tmp/enterprise-source --capture /tmp/enterprise-v2/capture.json.gz --out /tmp/replay.json
python3 enterprise-retrieval-pilot-v2/run.py controls --capture /tmp/enterprise-v2/capture.json.gz --out /tmp/controls.json
python3 tools/verify_results.py
```

A reproduction binary must have the frozen digest, including build metadata and
Go toolchain identity. Recorded build arguments are retained with the results.
The execute command runs one first pass and one independent fresh-store pass;
replay performs no retrieval. No source bodies, binaries, databases or downloaded
dependencies are redistributed. The capture codec is the unchanged v1 pinned
helper; the result manifest binds every published member.

The recorded build does not use `-trimpath`; checkout paths and toolchain changes
can change its raw executable digest. The measured fresh-store reproduction uses
the same frozen binary, not an independently rebuilt bit-identical executable.
A new rebuild with a different digest needs a separately identified protocol copy
with that build's identity recorded before querying; do not rewrite this frozen
protocol or relabel its observations. Offline source-bound replay needs no binary.
