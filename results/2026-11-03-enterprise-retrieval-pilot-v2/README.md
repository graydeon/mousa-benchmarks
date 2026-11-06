# EnterpriseRAG lexical pilot v2: required arms completed

One frozen 8 MiB pilot and an independent fresh-store reproduction completed in
428.855789 seconds under the shared 1,800-second experiment cap. Each pass retained
all 20 questions and 160 terminal arm outcomes: 140 scored observations across
seven required arms, plus 20 optional QMD NOT_RUN rows. There were no enterprise
query retries, preparation substitutions or scored failures. The two passes have
identical rankings, metrics, selected document identities, used bytes and stable
native journal facts. Timings and physical store sizes are retained separately.
These observations are published for independent review, not accepted product or
benchmark milestones. The reproduction repeats the same 20 questions; it is not
40 independent questions or 280 independent quality cases.

Product: [`d226394319955f36f52d0414ff446f0f5e63c8b0`](https://github.com/graydeon/mousa/pull/105),
tree `0851d56512ceab1546ab4c2b502391073b81c5a9`. A clean anonymous checkout built
CGo-free with Go 1.27.1 and `GOAMD64=v1`; its tree equals the locally tested product
tree. The native producer/consumer corrections address
[graydeon/mousa#103](https://github.com/graydeon/mousa/issues/103) and
[graydeon/mousa#104](https://github.com/graydeon/mousa/issues/104).
No benchmark report aggregate was fabricated to bypass those defects.

## Conditions and immutable v1

The selected input is exactly 20 questions, 500 physical documents and 4,970,133
normalized UTF-8 bytes. V2 changes the normalized-text ceiling from 4,194,304 to
8,388,608 bytes before any enterprise query. Original source asset hashes,
question lines, labels, 10 basic + 10 semantic enrollment, salt, full rendering,
physical/logical mapping and document selection are unchanged. Independent
preparation matched both v1 and the prospective 8 MiB preparation. The input
identity manifest is `15283db546c9208f7ba4ce6b2e597dc6d106762528751d9b5c5d39b2aa9aa8ff`.
It explicitly includes eligibility, enrolled lines, selected corpus and source
counts; it is a new serialization of those identity facts, not a claim to be the
prospective check's differently scoped digest.

[protocol.json](protocol.json), [condition-diff.json](condition-diff.json) and
[freeze-receipt.json](freeze-receipt.json) bind the pre-query cap, corrected public
product/build, controller and unchanged helper identities. The entire
[v1 failed preparation result](../2026-11-03-enterprise-retrieval-pilot) and its
producer/protocol bytes remain unchanged: 4 MiB refusal, 160 NOT_RUN rows and no
retrieval scores. V2 does not relabel that failure or change product admission.

Source cache size is 24,202,130 bytes; no source redownload was needed for v2.
Only the pinned two Confluence slices and questions are used, not the full
500,000+ document corpus or large Parquet. The selected bodies already contain
their titles; corpus `title` is empty, with full rendered `text` for every route.
Source bodies, databases, binaries and dependencies are not redistributed.

## Candidate quality

Each displayed route scored all 20 questions. Original and dedup traced arms at
both budgets also scored 20 each; their full candidate rankings match the
corresponding verified arm under native mode/budget comparisons. The
[per-question ledger](per-question.json) retains all eight arm denominators;
`capture.json.gz` retains complete rankings and returned SQLite scores.

| Candidate route | Scored / enrolled | Recall@10 | Recall@100 | Binary nDCG@10 | MRR@10 |
|---|---:|---:|---:|---:|---:|
| Mousa original, verified | 20 / 20 | 0.900000 | 1.000000 | 0.799357 | 0.766667 |
| Mousa dedup, verified | 20 / 20 | 0.900000 | 1.000000 | 0.799357 | 0.766667 |
| SQLite FTS5, whole documents | 20 / 20 | 0.900000 | 1.000000 | 0.737622 | 0.687698 |
| QMD native lexical | 0 / 20 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

Original and dedup have equal measured aggregate scores, not identical full
rankings: six queries differ in returned order (`qst_0102`, `qst_0104`, `qst_0021`,
`qst_0022`, `qst_0259`, `qst_0190`). Their gold ranks and aggregate metrics happen
to agree here. The native policy comparison records `rankings_identical=false`;
that is a valid experimental result, not a command failure.

SQLite 3.46.1 uses whole-document `unicode61 remove_diacritics 2`, quoted ASCII
alphanumeric OR terms, ascending BM25 then physical ID and limit 100. Mousa uses
its existing segmented candidate retrieval, expression preparation and limit 100.
These are different routes, not an equal-feature causal ablation. The BEIR native
journal returns ranked IDs but no numeric BM25 scores; those scores are marked
unavailable rather than reconstructed from ranks. SQLite returned scores are saved.

## Actual engine packing

Each row scored all 20 questions. Candidate rankings remain separate from actual
selected document IDs and used bytes. Native coverage commands succeeded on their
own produced reports at both budgets for both policies. Independent per-question
calculations match the native aggregates and curve output.

| Policy | Budget bytes | Gold-document coverage | Actual mean selected docs | Native integer mean selected docs | Native mean used bytes | Native utilisation |
|---|---:|---:|---:|---:|---:|---:|
| original | 1,024 | 0.100000 | 0.45 | 0 | 345 | 0.336914 |
| original | 4,096 | 0.700000 | 1.00 | 1 | 4,096 | 1.000000 |
| dedup | 1,024 | 0.100000 | 0.55 | 0 | 443 | 0.432617 |
| dedup | 4,096 | 0.700000 | 1.00 | 1 | 4,096 | 1.000000 |

Native selected-doc and used-byte means are integers rounded down, preserving the
product reporting convention. Zero mean selected docs does not mean every packet
was empty. Original selected 9 document occurrences and used 6,917 bytes across
20 small-budget queries; dedup selected 11 and used 8,877. At 4,096 bytes each
policy used 81,920 bytes in total. Selected document coverage does not establish
that selected passages support the question.

## Per-question diagnostic

Full per-question Recall@10/100, binary nDCG@10, MRR@10, selected IDs and byte facts
are in the ledger; complete native reports/journals and SQLite rows are in the
capture. This table shows the first gold-document candidate rank and the actual
original-policy gold coverage; dedup coverage is identical for these questions.

| Question | Original gold rank | Dedup gold rank | SQLite gold rank | Coverage 1,024 | Coverage 4,096 |
|---|---:|---:|---:|---:|---:|
| qst_0102 | 1 | 1 | 1 | 0.0 | 1.0 |
| qst_0174 | 1 | 1 | 1 | 1.0 | 1.0 |
| qst_0104 | 1 | 1 | 2 | 0.0 | 1.0 |
| qst_0021 | 1 | 1 | 1 | 0.0 | 1.0 |
| qst_0011 | 1 | 1 | 1 | 0.0 | 1.0 |
| qst_0022 | 1 | 1 | 1 | 0.0 | 1.0 |
| qst_0040 | 1 | 1 | 1 | 0.0 | 1.0 |
| qst_0118 | 1 | 1 | 1 | 0.0 | 1.0 |
| qst_0142 | 1 | 1 | 2 | 0.0 | 1.0 |
| qst_0117 | 1 | 1 | 1 | 0.0 | 1.0 |
| qst_0236 | 1 | 1 | 1 | 0.0 | 1.0 |
| qst_0234 | 13 | 13 | 9 | 0.0 | 0.0 |
| qst_0183 | 1 | 1 | 1 | 0.0 | 1.0 |
| qst_0197 | 2 | 2 | 26 | 0.0 | 0.0 |
| qst_0259 | 1 | 1 | 1 | 0.0 | 1.0 |
| qst_0190 | 3 | 3 | 3 | 0.0 | 0.0 |
| qst_0294 | 1 | 1 | 1 | 0.0 | 1.0 |
| qst_0252 | 6 | 6 | 7 | 0.0 | 0.0 |
| qst_0248 | 3 | 3 | 6 | 0.0 | 0.0 |
| qst_0221 | 35 | 35 | 22 | 1.0 | 0.0 |

The largest observed loss stage is packing: candidate Recall@100 is 1.0, while
1 KiB packed coverage loses 0.90 and 4 KiB loses 0.30 of mean gold-document
coverage. `qst_0221` loses coverage at the larger budget; a greedy selection need
not retain a smaller-budget packet's membership. No software defect is inferred
from these scores. The concrete next development implication is to inspect
existing candidate passage sizes and budget/selection dispositions on these lost
gold documents before proposing retrieval or packing changes. No defaults,
segmentation, ranking policy or architecture is changed by this pilot.

## Resources and optional-route failure

CPU-only Linux x86-64, eight exposed logical CPUs, Intel Xeon L5640 at 2.27 GHz.
Build/setup/replay time is separate from the measured experiment. CGo-free build:
4.383566 seconds wall, 12.966833 user + 1.166411 system CPU seconds, peak process
RSS 185,172 KiB. Binary digest and VCS metadata are in `build.json` and
`binary-metadata.txt.gz`; actual flags are in `beir-help.txt.gz`. Both are lossless
gzip streams of the original executable output, including its whitespace.

| Measured endpoint | First pass | Fresh-store reproduction |
|---|---:|---:|
| Source preparation wall seconds | 2.453541 | 2.545385 |
| Native ingestion wall seconds | 144.936989 | 130.619496 |
| Native process wall subtotal seconds, 13 invocations | 208.273574 | 208.837649 |
| Native process user CPU seconds | 62.529965 | 61.591033 |
| Native process system CPU seconds | 9.421454 | 9.845081 |
| Maximum native child peak RSS KiB | 58,692 | 82,692 |
| SQLite ingestion seconds | 1.333456 | 0.892914 |
| Raw SQLite median query milliseconds | 25.790616 | 24.860457 |
| Closed Mousa store bytes | 14,307,328 | 14,299,136 |
| Closed SQLite store bytes | 8,450,048 | 8,450,048 |

The controller's lifetime peak RSS at the SQLite observation was 488,888 KiB;
it includes preparation/materialization and is not SQLite-only RSS. Peaks are not
summed simultaneous process-tree memory. Native CPU subtotals and SQLite CPU
receipts are measured; full controller CPU and setup CPU/RSS were not captured.
Native query timing in the raw report is the warm Go request path, including
preprocessing and store work; process timing also includes index/open/output/close.
Raw SQLite query timing excludes process startup. These are not a fair latency
league table. Physical store-byte differences are not retrieval differences.

QMD setup used the existing pinned comparison lock with `npm ci --ignore-scripts`.
It was killed at the 256 MiB disk threshold after 10.021522 seconds, exit -9, with
275,718,864 bytes observed due to sampling overshoot. This is a retained failed
setup, not a claim the hard size cap held or that QMD search failed. No lifecycle
script, model download, embedding, model-backed query or lexical query ran; no
retry or dependency repair followed. All 20 QMD rows are NOT_RUN with null metrics.
`qmd-setup.json` preserves the command, empty stdout/stderr, lock and failure facts.
API calls and billing were zero; local CPU/electricity is not literally free.

## Replay, controls and limitations

See the [controller commands](../../enterprise-retrieval-pilot-v2#reproduce).
The execute command runs both complete fresh-store passes within one clock.
Source-bound replay rebuilds the exact dataset manifest from pinned cache bytes,
checks enrollment/mappings, independently recalculates metrics/coverage, binds
native journals and compares deterministic fresh-store facts. Replay performs no
retrieval. Four regenerated controls load valid, rehashed outer archives before
rejecting wrong same-count question IDs, wrong physical mappings, changed rankings
and changed packed membership at their intended semantic detectors. Their compact
receipts are stored in `controls.json`; mutated copies are regenerated, not stored.
The unchanged shared archive codec checks stream and interned-member hashes;
`manifest.json` binds every file in this directory. Root archive verification is
not a substitute for semantic replay. Historical files and failed attempts remain.

EnterpriseRAG-Bench is generated/simulated-company data. This gold-enriched reduced
500-document development corpus removes most official distractors and is easier
than the full official task. Original expected labels are not proof of semantic
support, complete judgments or factual truth; unjudged documents are not asserted
negative labels. These are not official/full-corpus/held-out/answer-quality/judge/
leaderboard results, a general superiority claim, model-window safety or long-horizon
memory evidence. Do not compare with vendor answer-quality scores under different
conditions. Attribution and exact public source pins are retained in
`source-metadata.json` and `source-license.txt`: EnterpriseRAG-Bench, Yuhong Sun,
Joachim Rahmfeld, Chris Weaver, Roshan Desai, Wenxi Huang and Mark H. Butler (2026),
[arXiv:2605.05253](https://arxiv.org/abs/2605.05253), MIT copyright 2026 DanswerAI, Inc.

Exact native report, journal, manifest and command bytes are also retained in
`native-raw.tar.gz`, with all 52 regular members hashed in `archive-inventory.json`.