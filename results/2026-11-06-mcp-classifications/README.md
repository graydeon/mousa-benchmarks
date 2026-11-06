# MCP source-scoped classification administration

Two fresh SQLite stores exercised a CGo-free binary built from an anonymous clean checkout of product `a942fed6e12db051324ddac96ecdbf5f4c51d788` ([PR110](https://github.com/graydeon/mousa/pull/110)). Public and tested product trees match `e5a4daa11100a17d76a2d0385ad94a67598d2e93`. These are stdio protocol observations, not release acceptance, classification accuracy, calibrated confidence or retrieval-quality measurements.

Both captures pass replay and stable cross-store comparison. Each retains 41 scheduled events and ten rehashed semantic controls. No token query runs: independent complete-context token counts are zero. The lossless archive contains 28 regular members totaling 17,792,714 bytes; `archive-members.json` records every size and SHA-256 hash. The outer manifest binds the compressed archive, protocol and reports.

## Exercised behavior

The client uses MCP sync/export to obtain source, representation and segment pins, submits a segment classification with ordered representation/source basis and explicit confidence 0, retries it, fetches it, appends a separately versioned assertion and fetches both. Canonical classification IDs are derived independently. Byte-query producing facts and evidence remain unchanged.

Ingestion-only and read-only clients cannot write classifications; classification-admin-only cannot ingest. Get works without administration permission. A foreign-source read returns `not_found`. Separately recorded native `access` setup denies retrieval: the explicit classification write grant still accepts an exact retry, while known and unknown classification gets contain decision metadata only. Native policy setup is not MCP classification or policy administration.

Strict replay binds scheduled requests, response IDs, outer and embedded JSON, source/operation, fixture text and returned pins. Controls recompute stream hashes after changing a scheduled request, response source, authorization, label, confidence, ordered basis, returned classification ID, query segment pin, boolean confidence or duplicate embedded key. Each fails at its named semantic detector. Pure tests distinguish explicit integer zero from omission, null, booleans, strings and floats. These controls establish the checked invariants, not universal tamper resistance.

## Replay

From this repository root:

```sh
result=results/2026-11-06-mcp-classifications
mkdir /tmp/mousa-classification-replay
tar -xJf "$result/raw-captures.tar.xz" -C /tmp/mousa-classification-replay
python3 tools/verify_results.py
python3 mcp-classifications/capture.py verify --protocol "$result/protocol.json" --output /tmp/mousa-classification-replay/first
python3 mcp-classifications/capture.py verify --protocol "$result/protocol.json" --output /tmp/mousa-classification-replay/second
python3 mcp-classifications/capture.py compare --protocol "$result/protocol.json" --output /tmp/mousa-classification-replay/first --other /tmp/mousa-classification-replay/second
```

To regenerate controls, copy one extracted capture directory without its `controls` directory and run the producer's `controls` mode on that new copy. Compare its receipt with the corresponding stored `first-controls.json` or `second-controls.json`. Fresh collection instructions are in [REPRODUCING](../../REPRODUCING.md#mcp-source-scoped-classifications).

## Limits and retained failures

This public workflow covers segment subjects with representation/source basis. Product SQLite tests separately cover all five kinds, historical/withdrawn/never-indexed parents, mixed roots, corruption, rollback and competing writers. Product HTTP tests separately exercise validated-principal and read/write scopes. None of those is inferred from these stdio captures. Native cross-source classifications remain outside this MCP slice. Labels do not establish factual truth, authenticate their asserter, grant access or label replacement revisions.

Review found that the initial producer passed Python sets to a JSON equality helper; this was corrected to sorted lists before real capture. A complete local committed-tree smoke passed before the two fresh exact-public-head runs. Local smoke is not relabeled as public-head evidence. Product preparation retained corrected test-fixture/discovery failures, an example's absent byte-query context-field assumption, a missing documentation command argument and a nonofficial-interpreter optional skip; final focused checks, examples, official documentation checks and full grant commands passed. Historical producers, protocols, results and source pins are unchanged. No model inference, paid API, enterprise/QMD campaign or deployment was performed.
