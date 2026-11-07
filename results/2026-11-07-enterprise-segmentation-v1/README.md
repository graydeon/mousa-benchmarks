# Enterprise segmentation comparison

## Result and recommendation

Collection completed with **160/160 scored rows** in **1,382.2033718456514 seconds**, below the 1,800-second collection cap. All eight arm processes exited 0; no query failures, timeouts, retries or unattempted rows were recorded. Source-bound replay returned `REPLAY_VALID`, and the separate audit returned `INDEPENDENT_CHECK_VALID`. All 80 paired reproduction comparisons matched rankings, selected segments, candidate records, used bytes and metrics.

For this frozen corpus only, passage-v1 is recommended when increased packed gold-document coverage is worth the extra ingest and retrieval work and the question-specific ranking losses below. This is not a default change or a general recommendation. Confirmation remains **UNMET_ELIGIBLE20**: zero additional questions were eligible. Repeating the original questions does not supply held-out evidence.

The population remains the original **20 questions, 500 physical documents and 4,970,133 normalized text bytes**. Both policies use expression policy `original`, original byte packing, candidate limit 100 and budgets of 1,024 and 4,096 bytes. Each pass starts a fresh store per segmentation policy; only the second budget reuses that store. No model, embedding, network or QMD work was included.

## Aggregate quality

Values are means over the original 20 questions. Both passes produced the same quality values. Candidate metrics measure document ranking before packing; coverage measures whether a gold document contributed a selected segment, not whether the answer was present.

| Policy | Budget bytes | Recall@10 | Recall@100 | Binary nDCG@10 | MRR@10 | Packed gold-document coverage | Mean used bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed-v1 | 1,024 | 0.90 | 1.00 | 0.799357 | 0.766667 | 0.10 | 345.85 |
| passage-v1 | 1,024 | 0.95 | 1.00 | 0.854867 | 0.826786 | 0.80 | 963.15 |
| fixed-v1 | 4,096 | 0.90 | 1.00 | 0.799357 | 0.766667 | 0.70 | 4,096.00 |
| passage-v1 | 4,096 | 0.95 | 1.00 | 0.854867 | 0.826786 | 0.85 | 4,017.40 |

At 1,024 bytes, passage-v1 gained coverage on 15 questions and lost it on one: a net gain of 14/20, or 70 percentage points. At 4,096 bytes it gained coverage on three questions with no cross-policy losses: a net gain of 15 percentage points. Recall@100 was already complete for both policies; the coverage gains are not additional candidate-document recall.

## Per-question changes

Each question has one gold physical document. Rank is its one-based position in the candidate document ranking and is the same at both budgets. Each coverage cell is fixed-v1 → passage-v1; 1 means a gold-document segment was selected, and 0 means none was selected. These values reproduced in the second pass.

| Question | Gold rank, fixed → passage | Coverage at 1,024 bytes | Coverage at 4,096 bytes |
| --- | ---: | ---: | ---: |
| qst_0102 | 1 → 1 | 0 → 1 | 1 → 1 |
| qst_0174 | 1 → 1 | 1 → 1 | 1 → 1 |
| qst_0104 | 1 → 1 | 0 → 1 | 1 → 1 |
| qst_0021 | 1 → 1 | 0 → 1 | 1 → 1 |
| qst_0011 | 1 → 1 | 0 → 1 | 1 → 1 |
| qst_0022 | 1 → 1 | 0 → 1 | 1 → 1 |
| qst_0040 | 1 → 1 | 0 → 1 | 1 → 1 |
| qst_0118 | 1 → 1 | 0 → 1 | 1 → 1 |
| qst_0142 | 1 → 1 | 0 → 1 | 1 → 1 |
| qst_0117 | 1 → 1 | 0 → 1 | 1 → 1 |
| qst_0236 | 1 → 1 | 0 → 1 | 1 → 1 |
| qst_0234 | 13 → 11 | 0 → 0 | 0 → 0 |
| qst_0183 | 1 → 1 | 0 → 1 | 1 → 1 |
| qst_0197 | 2 → 7 | 0 → 0 | 0 → 0 |
| qst_0259 | 1 → 1 | 0 → 1 | 1 → 1 |
| qst_0190 | 3 → 1 | 0 → 1 | 0 → 1 |
| qst_0294 | 1 → 1 | 0 → 1 | 1 → 1 |
| qst_0252 | 6 → 1 | 0 → 1 | 0 → 1 |
| qst_0248 | 3 → 4 | 0 → 0 | 0 → 1 |
| qst_0221 | 35 → 7 | 1 → 0 | 0 → 0 |

The aggregate ranking improvement includes two regressions: qst_0197 fell from rank 2 to 7, and qst_0248 fell from 3 to 4. Four questions improved rank; 14 were unchanged. qst_0234 improved from 13 to 11 but remained outside the top ten and uncovered. qst_0221 improved from 35 to 7 but lost its 1,024-byte packed coverage. Rank and packing are separate outcomes. Increasing the fixed-v1 budget also lost qst_0221's coverage, from 1 to 0; neither segmentation nor budget increases imply monotonic coverage.

## Work and resources

Fixed-v1 produced 1,495 segments; passage-v1 produced 7,557, about 5.05 times as many, over the same normalized bytes. Native ingest indexing time was 152.644/156.044 seconds for fixed-v1 and 426.812/417.017 seconds for passage-v1 in the first/reproduction passes. The second budget reports zero native indexing seconds because it reuses the store; opening and mapping it still costs work.

| Pass | Policy | Budget bytes | Process wall s | Native indexing s | User CPU s | System CPU s | Peak RSS KiB | Mean journal query ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| First | fixed-v1 | 1,024 | 161.154 | 152.644 | 13.925 | 3.260 | 65,592 | 349.101 |
| First | fixed-v1 | 4,096 | 12.044 | 0 | 10.153 | 1.428 | 99,040 | 321.599 |
| First | passage-v1 | 1,024 | 437.658 | 426.812 | 27.965 | 7.121 | 129,120 | 456.666 |
| First | passage-v1 | 4,096 | 19.250 | 0 | 16.634 | 1.805 | 242,028 | 425.820 |
| Reproduction | fixed-v1 | 1,024 | 167.571 | 156.044 | 13.561 | 2.905 | 292,152 | 313.807 |
| Reproduction | fixed-v1 | 4,096 | 14.483 | 0 | 9.397 | 1.355 | 305,984 | 463.021 |
| Reproduction | passage-v1 | 1,024 | 433.307 | 417.017 | 28.121 | 7.321 | 320,508 | 428.918 |
| Reproduction | passage-v1 | 4,096 | 18.542 | 0 | 16.528 | 1.693 | 363,872 | 403.353 |

Passage-v1 used more process CPU and ingest wall time in both passes. Its mean query time was higher in three of four matched comparisons, but lower at 4,096 bytes in reproduction. This small repeated run does not establish a stable latency ratio. Process wall/CPU/RSS cover open, ingest or rebuild, queries, reporting and close, not isolated query execution. RSS varies substantially across passes; these endpoints are not query-memory attribution or a controlled capacity study. Collection wall includes work outside the eight measured child processes.

The enclosing collection command took 1,398.602 seconds including final serialization, also below the cap. The producer records collection wall immediately before writing its final checkpoint. Peak RSS comes from each child's `os.wait4` process-lifetime endpoint, not isolated query memory. The increasing scheduled endpoints do not establish a policy-only memory multiplier.

## Public source and build

- Product commit: [`a65d9fea1ce5d903e0c672d4cea62e6ce6272654`](https://github.com/graydeon/mousa/commit/a65d9fea1ce5d903e0c672d4cea62e6ce6272654).
- Product tree: `7cae64f2eb975b9beb2edaadc7923a40547eae60`.
- Build: `go build -o beir ./cmd/beir`, exit 0, from the clean public source checkout. Go 1.27.1; linux/amd64; `CGO_ENABLED=0`; binary metadata records the commit above and `vcs.modified=false`.
- Binary: 13,227,595 bytes; SHA-256 `56d8c58d71e42badb57f95c74d00c3a0bf4a0c71fd1822fa85b665ef72865408`.
- Capture environment: Linux x86_64, kernel 6.12.111+deb13-amd64, glibc 2.41, Python 3.13.5.

Publication receipts and binary metadata record source/build provenance; they do not authenticate execution. A different build environment can produce different binary bytes.

## Evidence and replay

`evidence.tar.xz` losslessly retains the exact decompressed capture payload as `capture.codec.json`, native files under `raw/`, and build/execution provenance. `restore_capture.py` reconstructs the original gzip bytes and refuses any mismatch with their SHA-256; this was verified with Python 3.13.5. This transport representation fits the publication bound without changing or truncating the measured capture. The inventory records all member identities. Native journals, reports, manifests, process streams, segment source offsets/sizes, candidate dispositions, selections and omissions are retained. The capture uses the existing object-table codec, not an ordinary expanded JSON object.

The 3,050,264-byte archive is split into three ordered `evidence.tar.xz.partNN` files, each below 2 MiB. Concatenation is byte-identical to the verified archive; the inventory binds both the parts and the whole stream. Splitting changes no member bytes.

The measured `capture.json.gz` is 6,276,811 bytes with SHA-256 `d85e92ba5f647f0425a0f4f8643f2cd8c9e094a1b5ef7590e7557db0c8202d05`. `analysis.json` contains source-bound replay results; `independent-check.json` contains the separate audit. The latter reports 160 terminal and scored rows and the unchanged eligibility dispositions: 20 original questions, 466 ineligible source/category labels and 14 whose gold is not wholly in the frozen corpus.

The archive contains 45 regular members totaling the bytes declared in `archive-inventory.json`; every name, size and SHA-256 was verified without extraction. All three regenerated rehashed controls failed their intended detectors: wrong population (`native-content-binding`), wrong segmentation (`segmentation-policy-binding`) and altered packed selection (`canonical-candidate-projection`). `controls.json` retains their identities; control copies are deterministically regenerated, not shipped.

From the companion repository root, with `CACHE` pointing to the pinned enterprise source cache:

```sh
mkdir segmentation-evidence
cat results/2026-11-07-enterprise-segmentation-v1/evidence.tar.xz.part00 results/2026-11-07-enterprise-segmentation-v1/evidence.tar.xz.part01 results/2026-11-07-enterprise-segmentation-v1/evidence.tar.xz.part02 | tar -xJf - -C segmentation-evidence
python3 results/2026-11-07-enterprise-segmentation-v1/restore_capture.py segmentation-evidence
python3 enterprise-segmentation-v1/analyze.py replay --cache "$CACHE" --capture segmentation-evidence/capture.json.gz --out segmentation-replay.json
python3 enterprise-segmentation-v1/analyze.py controls --cache "$CACHE" --capture segmentation-evidence/capture.json.gz --out segmentation-controls.json
python3 results/2026-11-07-enterprise-segmentation-v1/independent_check.py --repo . --cache "$CACHE" --capture segmentation-evidence/capture.json.gz --binary "$BEIR" --out segmentation-independent.json
```

These are extraction/replay instructions, not a new collection. Use new output paths. The recorded source-bound replay and regenerated controls commands exited 0. Archive extraction and the published independent checker were exercised together against the extracted capture and exited 0. The checker requires the measured binary identity, not merely a newly built binary from the same source. See [the reproduction procedure](../../REPRODUCING.md#segmentation-comparison) for collection instructions and input requirements.

## Bounds and limitations

The collection retained the 8 MiB normalized-text cap, 30-second per-query timeout, one 1,800-second collection deadline and inherited compressed asset, cache and member bounds. It made no retries or replacements. The frozen protocol's `PREPARED_NOT_MEASURED` status describes the pre-collection contract; the capture and analysis record the measured outcome without rewriting that historical contract.

This is a small, gold-enriched, shared frozen corpus, not independent-company validation or an official leaderboard. Zero eligible new questions means no held-out confirmation; the required 20-question cohort was not reduced. Document labels are a coarse proxy: selected gold-document bytes do not prove answer-bearing evidence or semantic sufficiency, and unjudged relevance is not negative. No answer-quality or monotonicity claim follows.

Replay checks input identities, configuration, canonical source slices, UTF-8 partitions, policy-specific size bounds, trail selections and recomputed metrics. The independent checker adds separate recorded-consistency checks; canonical identities still depend on the frozen source-bound replay. Neither checker independently reimplements the segmentation algorithm, authenticates historical execution, or proves fresh-store execution from pass names alone. Timing, CPU/RSS and supplied publication identities remain recorded claims.

Historical failed 4 MiB preparation, measured 8 MiB enterprise v2 results, QMD failure/overshoot and all original source pins remain unchanged. This result adds a segmentation comparison; it does not relabel or replace those observations.
