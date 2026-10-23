# MCP external-embedding workflow — 2026-10-23

Capture and separate fresh-store reproduction both PASS against [Mousa PR89](https://github.com/graydeon/mousa/pull/89), exact public head `62cb1eb8e1e947894447b338c75f467977560943`, tree `1718bf3b6380637108d8cc92de4fab606efa755c`. This is an additive result directory; older captures/pins stay unchanged.

## Reproduce

Follow [the client instructions](../../mcp-embeddings/README.md). Build the clean exact product checkout using `build.json`, then run `capture` twice with separate absent output paths. No native vector export/import or SQLite inspection is used. A native access command sets retrieval denial only for the final control session. Replay each retained run:

```sh
python3 mcp-embeddings/capture.py verify --output results/2026-10-23-mcp-embedding-workflow/capture
python3 mcp-embeddings/capture.py verify --output results/2026-10-23-mcp-embedding-workflow/reproduction
python3 mcp-embeddings/capture.py controls --output results/2026-10-23-mcp-embedding-workflow/capture
python3 mcp-embeddings/capture.py controls --output results/2026-10-23-mcp-embedding-workflow/reproduction
python3 tools/verify_results.py
```

Both runs retain 35 scheduled requests, 32 response frames and three successful process exits. Each raw stream retains exact base64 bytes, length and SHA256, LF framing, stderr and trailing stdout. `runner.json` pins the driver and the unchanged strict JSON/schema/schedule helpers. The `manifest.json` binds all result members; no executable, database, cache or secret is exported.

## Observations

The writable process syncs the fixture, exports exact normalized passage bytes/pins, imports hand-assigned arithmetic-only vectors and retries exactly. Both original and exact-v1 packers choose the cosine winner `vector.md`; hybrid chooses `overlap.md`, second in each branch, with RRF `2/62`. History binds the actual producing trail, packet, decision, space and branch facts, without reranking after replacement.

Changed immutable values refuse with `conflict`. A mixed stale batch following source replacement refuses with `invalid_record`. A fresh export/import succeeds. A read-only process exports but refuses import with `ingestion_not_permitted`; existing producing embeddings remain queryable after restart. Fresh policy denial returns no passage facts or history, while explicit administrative import still succeeds. All tool envelopes satisfy their actual discovered closed output schema.

## Controls and evidence limits

Changed import values with repaired request stream hashes fail `scheduled-request-bytes`. A fabricated read-only success with coherent schema, canonical space ID/count, text/structured envelope and stream hashes fails `expected-tool-error`. The receipts retain detector names and complete modified-capture hashes; controls regenerate copies rather than archive redundant mutated captures.

The two runs have independent fresh stores and volatile decision/trail identities; each run binds its own producing identities rather than comparing them across runs. Replay establishes schedule/observation consistency, not authenticity against an adversary able to fabricate every observation. Retry wire success does not independently establish unchanged database rows. Atomic row rollback, foreign pins, withdrawn sources, exact codec/frame boundaries, runtime HTTP write scopes and token compatibility are product regression evidence, not established by this stdio fixture.

This is synthetic protocol/cosine/RRF arithmetic, not semantic quality, model integration, performance or model-window safety. Embedding generation remains external; exact pins and the space declaration must survive that computation. No external snapshot lease is promised. No optional runtime packages or provider network calls are used. Historical startup/export failures remain deferred and unchanged.
