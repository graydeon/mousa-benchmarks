# Long-horizon known-key retention: 16,384 documents

The actual Mousa core MCP server ingested 16,384 distinct synthetic project memories over 100 ordered epochs, applied two replacements and one withdrawal, and passed all 15 labeled retrieval cases both before and after a process restart. The earliest sampled fact survived 16,383 later distinct documents with exact released bytes and provenance. Final active items: 16,383.

This establishes sampled persistent known-key retention at the measured scale. It does not establish semantic-memory accuracy, multi-year durability or million-document database capacity.

## Observations

| Measure | Observed result |
| --- | --- |
| Distinct documents / ingestion events | 16,384 / 16,387 |
| Logical epochs | 100 |
| Unique retrieval cases | 15: twelve retention targets, latest correction, withdrawal and never-observed key |
| Warm observations | 15 PASS, 0 FAIL |
| Restarted observations | 15 PASS, 0 FAIL |
| Original historical packet/selection after replacement and restart | PASS |
| Epoch ingestion plus status-check wall time, summed | 698.098 seconds |
| Process-restart initialization | 377.699 seconds |
| Warm query median / p95 | 590.437 / 645.277 ms |
| Restarted query median / p95 | 397.374 / 702.749 ms |
| Store bytes after checks and shutdown | 66,584,576 |
| Writer and reader process exits | 0 / 0 |

Query timings are end-to-end stdio RPC round trips, not isolated FTS execution time. The per-mode p95 uses nearest rank on 15 observations and is therefore the maximum of that mode's samples. Restart initialization is measured separately from query latency. OS page caches were not flushed. Epoch times include native ingestion and the epoch-end source-status check, not just engine-reported ingestion time. These observations come from one shared-container run; no matched performance comparison or latency advantage is established.

The 377.699-second restart is a material cold-start limit. Passing retention does not justify describing this build as providing instant memory access after restart or extrapolating its capacity/performance to larger stores. No optimization was made to hide this result.

## Generated versus tested scale

| Profile | Generated input bytes, events file | Actual database test |
| --- | --- | --- |
| 64 documents / eight epochs | 22,017 | Passing protocol smoke, not capacity evidence |
| 16,384 documents / 100 epochs | 5,409,915 | PASS, measured run above |
| 100,000 documents / 100 epochs | 33,003,195 | NOT RUN |
| 1,000,000 documents / 100 epochs | 330,003,195 | NOT RUN |

All four profiles were generated with seed `20260930`. `dataset-manifests.json` records their exact bytes and digests. Larger generators do not prove the server can ingest, reopen or query those scales within practical resource limits. Expanded corpora and stores are not committed.

## Methods and retained failures

Use the [dataset protocol and commands](../../datasets/long-horizon/README.md). The native MCP writer was bound only to the synthetic memory source, with ingestion enabled for setup. After shutdown, a separate process reopened the store without ingestion permission. Twelve stable keys span corpus age cohorts; the controls distinguish latest from superseded values, withdrawn from active evidence, and absent from known records. The query release budget remains 4,096 bytes.

The initial pre-correction query's packet/trail was inspected after the final correction and restart. Its selected segment/digest/byte-length metadata and packet ID still matched. This is historical metadata verification, not release of superseded text.

Pilot failures are retained separately: the first 64-document attempt expected a nonexistent `completed_items` success field; the next expected item/byte-coordinate fields in metadata-only historical candidates. Both were runner contract errors corrected against actual replies. The first large attempt exceeded the native MCP limit of 128 records per sync request and stopped before ingestion. The accepted runner uses 128-record batches; the passing larger run used a fresh store. No failed retrieval case was discarded or relabelled.

Mousa source: `96b99f5f808dd4a836547156babda158fa2cd2d1`; executable SHA-256 `895bd443c95ce614cb5a4399c873c3a674f93f4f996ec1278632c171c0e985e5`. Benchmark starting source: `6cdba1b935809e3d757bb990972bb0d0aefd8660`. `protocol.json` binds the exact generator/runner hashes and environment; `observations.json` retains every epoch/query observation, startup, source state and process exit. `metrics.json` is the descriptive projection above. No model/provider call occurred.

These are templated, public, known-key fixtures. Warm/restarted repeats are 30 observations of 15 cases, not independent questions. There is no semantic paraphrase, conversational-session or exhaustive per-document recall measurement. Suitable claims must state the measured scale, sampled tasks and startup limitation; stronger long-horizon marketing needs larger actual stores and separate retrieval-quality evidence.

Age comparisons use only `retention-*` cases. Control rows are not age-stratified samples: the withdrawal control's `introduced_epoch` field records the withdrawal epoch (99), not its original insertion. Its `intervening_documents` is null. The exact byte/digest and lifecycle checks do not depend on that control-stage metadata.
