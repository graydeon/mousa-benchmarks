# Long-horizon persistent retrieval

Measure whether early facts remain retrievable after a larger chronological corpus, later corrections, withdrawals and a process restart. This separates storage/retrieval retention from a model's context window. It is a known-key retrieval benchmark, not a semantic-memory or conversational reasoning benchmark.

## Corpus and horizon

The stdlib generator creates fictional project decisions with team and recovery-code facts. SHA-256 inputs determine stable lookup keys and revision values. There are no model calls, private corpora, external datasets or real credentials. Generated data and tools use this repository's AGPL-3.0-only license.

Default configuration: 16,384 distinct documents across 100 logical ingestion epochs. Twelve fixed targets span early, quarter, middle, three-quarter and final positions. The oldest target has 16,383 later distinct documents. Larger reproducible profiles are 100,000 and 1,000,000 documents. Generator output and successful executable testing are reported separately.

The history includes two replacements of one early record and a final tombstone for another. Three controls require the latest revision, no withdrawn evidence, and no evidence for a never-observed key. Before the replacements, the runner saves a real query packet/trail; after the restart it verifies the original historical selection metadata. Source Trails do not release historical text, so this is not a claim that superseded text is retrievable.

| File | Contents |
| --- | --- |
| `events.jsonl` | Ordered epochs and item upserts/tombstones |
| `tasks.json` | Target ages, current evidence byte/digest labels and initial snapshot label |
| `manifest.json` | Seed, scale, epochs and input sizes/SHA-256 digests |
| `example/` | Small 64-document/eight-epoch reproduction fixture |

Epochs are logical ingestion batches, not elapsed years or completed model conversations. Most records are distractors with similar templates and distinct keys. Targets are public development labels, not held-out questions. Dates, years of retention, semantic recall and universal memory capacity cannot be inferred from this fixture.

## Run the actual executable

Requires Python 3.9 or later and a Mousa executable with the four core stdio MCP tools. Use an account-owned fresh store/output directory. These are command templates; replace the executable and work paths.

```sh
python3 datasets/long-horizon/generate.py --out /private/horizon-16384 --documents 16384 --epochs 100
python3 datasets/long-horizon/run.py --mousa /path/to/mousa --dataset /private/horizon-16384 --store /private/horizon-16384.sqlite --out /private/horizon-16384-run
```

For larger profiles, change `--documents` to `100000` or `1000000`. Do not change the seed or targets after inspecting responses. The generator requires at least 64 documents, four epochs, and at least one document per epoch. Existing output directories and stores are refused.

The runner starts a native MCP server authorized to ingest only the synthetic `memory` source. Each request contains at most 128 records, the tested server's limit. Epoch-end status checks require the expected active-item count and no recovery need. After ingestion, 15 cases run against the live process. The writer shuts down; a new read-only-source MCP process opens the same store and repeats those cases. Restart startup is measured separately. This is process-cold, not OS-cache-cold: no host cache flush is performed.

Every positive response must select the expected item and exact digest/byte coordinates, and its released UTF-8 bytes must match that digest. The correction cannot pass with the original revision. Negative cases require empty evidence. Status and original packet/trail selection are also checked. The report retains all epoch times, individual query times, startup, database size, source/input/runner hashes and process exits. Missing or failed execution is not a PASS.

`summary.json` and `mcp-receipts.jsonl` are private output artifacts. No provider credentials or model request is involved. Keep SQLite stores and expanded corpora out of ordinary source history. Publish sanitized observations and manifests; retain failed pilot receipts separately.

## Interpretation

A passing run supports a narrow statement: the sampled early known-key facts survived the measured number of later documents/epochs, corrections and process restart with exact provenance. It does not measure recall across every document. Warm and restarted queries are repeated observations of 15 cases, not 30 independent cases. The query release budget is 4,096 bytes; the entire corpus is not placed into a model prompt.

[September 30 results](../../results/2026-09-30-long-horizon/) distinguish tested capacity from generated profiles. There is no model-answer accuracy, multi-session conversation test, matched retrieval competitor, multi-year soak or latency advantage claim. Larger tested scales and independently phrased questions are needed before broader long-horizon marketing claims.
