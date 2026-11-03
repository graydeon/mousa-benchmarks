# EnterpriseRAG lexical pilot — incomplete at preparation

**No enterprise retrieval-quality or packing comparison was completed.** The fixed
selection violates the text cap. Both independent-cache preparation passes return
`preparation_bound_failure` (exit 2); no enterprise ingestion or query was attempted.
The failure is not an empty retrieval result and is not scored as zero.

## Population and bound

| Preparation fact | Actual |
|---|---:|
| Public Confluence source documents audited | 5,189 |
| Eligible basic / semantic questions | 19 / 15 |
| Enrolled basic / semantic questions | 10 / 10 |
| Selected documents / gold physical documents | 500 / 20 |
| Selected normalized UTF-8 text bytes | 4,970,133 |
| Allowed normalized text bytes | 4,194,304 |
| Excess bytes | 775,829 |
| Resolved selected labels / ambiguous / missing | 20 / 0 / 0 |
| Executable / scored questions | 0 / 0 |
| Score denominator | 0 |
| Per-question, per-arm terminal outcomes retained | 160 |

The [per-question results](per-question.json) name every actual question ID,
original expected logical ID, physical item mapping and terminal arm outcome.
[summary.json](summary.json) is the machine-readable disposition. Exact selected
question lines, all 500 question eligibility decisions, 500 corpus members,
original source member ranges and raw/rendered byte identities are in
[preparation.json.gz](preparation.json.gz). The separate
[reproduction.json.gz](reproduction.json.gz) has identical stable preparation facts;
only timing differs. No label/version collision was observed for these selected
questions. That does not establish uniqueness throughout the full benchmark.

## Quality and packing results

| Enterprise arm | Candidate quality | Packed gold coverage | Terminal status |
|---|---|---|---|
| Mousa original: verified; traced 1024/4096 | Unavailable | Unavailable | NOT RUN: preparation bound |
| Mousa dedup: verified; traced 1024/4096 | Unavailable | Unavailable | NOT RUN: preparation bound |
| SQLite FTS5 BM25 | Unavailable | Not a packing arm | NOT RUN: preparation bound |
| QMD lexical search, optional | Unavailable | Not a packing arm | NOT RUN: preparation bound; setup not attempted |

There are no paired Recall@10/100, binary nDCG@10, MRR@10 or packed coverage numbers
to compare. No raw enterprise ranking, score or evidence-selection output exists.
The largest observed loss stage is **preparation**, blocking the entire enrolled
population before retrieval. The concrete development implication is to reconcile
the fixed 500-document enrollment with the 4 MiB limit in a separately approved,
refrozen protocol. This attempt neither raises the cap nor substitutes fewer or
smaller documents. It is inconclusive about retrieval quality or packing policy.

## Execution and resource evidence

| Endpoint | Wall seconds | User CPU seconds | System CPU seconds | Peak RSS KiB | Exit |
|---|---:|---:|---:|---:|---:|
| Cold preparation, first cache | 3.000669 | 2.862893 | 0.136025 | 50,480 | 2 |
| Cold preparation, independent cache | 3.089102 | 2.955570 | 0.129985 | 72,544 | 2 |

[Resource receipts](preparation-resources.json) and
[reproduction receipt](reproduction-resources.json) describe the measured endpoint:
archive reads, decompression, enrollment, rendering and the bound check. No index
or retrieval work is included. Replay/source verification, builds and downloads
are separate. `timeout 1800s` bounded each preparation process; no cap was extended.
Fresh-store retrieval reproduction is NOT RUN because no corpus was admissible.
It must not be inferred from the independent-cache preparation reproduction.

The three source assets total 24,202,130 bytes per download, with 51,191,526 bytes
of text decompressed in memory. An initial fetch and a separate committed-downloader
check plus source metadata/question correspondence downloads used 49,361,018 HTTP
body bytes, below 64 MiB. Three owned cache copies retain 72,606,390 regular-file
bytes, below 512 MiB; no source archive was extracted. [Source metadata](source-metadata.json)
pins sizes, SHA256, release asset IDs and URLs. No full corpus or large Parquet was
fetched. The source license text is [retained](source-license.txt).

[build.json](build.json) pins the anonymously checked-out product commit/tree,
CGo-free binary SHA256, compiler and dependency metadata. The build completed
successfully before the pilot; its 4.45-second tool wall observation is not query
latency, and build CPU/RSS were not captured. [environment.json](environment.json)
records CPU, OS, Python, SQLite and cache disk accounting. No enterprise query
latency exists. Warm native harness, cold launcher and raw SQLite timings from the
synthetic checks are not interchangeable end-to-end performance endpoints.

API calls and billing: **0**. No embeddings, model-backed retrieval, answer
generation, judge, paid compute or GPU was used. QMD dependency preparation used
0 seconds and 0 bytes because the global preparation failure already blocked its
input. Local compute and electricity are not literally free.

## Separate synthetic checks and observed helper failure

[synthetic-sanity.json.gz](synthetic-sanity.json.gz) preserves both development
attempts, their raw commands/exits/stdout/stderr, toy inputs, reports, journals and
manifest files. These two-document/two-query observations are **not enterprise
pilot results**. The first attempt stopped when native coverage reporting returned
exit 1. The corrected client observation retained that refusal explicitly and
completed six Mousa query arms, native policy/mode/budget ranking comparisons,
actual engine small/larger-budget selections and an independent SQLite FTS5 query.
No product code or output report was patched.

At product `db03c841c0491ac505be8289e08fa60f78eae738`, the native coverage helper
refuses the binary's own traced output: per-question `pack_coverage` exists but
aggregate `pack_coverage` is absent. The minimal reproduction is the synthetic
`sanity.py` command in the [instructions](../../enterprise-retrieval-pilot).
The two failing coverage commands and input reports are retained for independent
product triage. This does not explain the separate enterprise corpus-cap failure.
An unavailable `/usr/bin/time` launcher also returned 127 before any preparation
process started; measurement used the standard-library process resource receipt
instead. No infrastructure repair was attempted.

Four hand-computed metric/rendering fixture tests passed. Four
[rehashed semantic controls](controls.json) passed: changed question enrollment
with equal counts, wrong logical/physical mapping, changed ranking and changed
packed evidence all loaded with valid recomputed archive/member hashes, then
failed the intended semantic detector. Ranking/packing controls are synthetic
sanity checks only. Source-bound verification regenerated the exact frozen
preparation population, mappings, membership and terminal outcomes successfully.

## Scope and reproduction

Use the [frozen protocol](protocol.json) and
[adapter instructions](../../enterprise-retrieval-pilot). Both compressed captures
use the unchanged shared lossless object/archive helper with per-member SHA256;
[archive inventory](archive-inventory.json) records encoded sizes and member counts.
The root [manifest](manifest.json) registers every public result file. `python3
tools/verify_results.py` checks those hashes; the source-bound `prepare.py verify`
and `checks.py` commands check semantic preparation and synthetic controls.

EnterpriseRAG-Bench is a generated/simulated enterprise dataset. This gold-enriched
reduced corpus deliberately removes most full-benchmark distractors and would
generally be easier than the official benchmark. This incomplete attempt is not
a full-corpus evaluation, answer/judge evaluation, held-out confirmation,
leaderboard submission or vendor-system equivalence claim. No policy or
architecture recommendation follows. Reserve fresh untouched data and preregister
a comparison before confirmatory claims. Historical results and producers remain
byte-identical; no product, dependency, lockfile or workflow changed.
