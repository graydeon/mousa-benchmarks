# Declared supporting context over MCP

Two separate fresh-store stdio runs at public Mousa head
`aa91c50ef362b8864ff15c678fc64e5a727a9d8b`, tree
`571472f17d952af11325542e21bc1e231863faba`, built from a clean anonymous
checkout. Product [PR95](https://github.com/graydeon/mousa/pull/95) is open for
review; these observations do not establish merge, independent acceptance or
released availability. After merge, a source build containing the change can
accept the inline input; older binaries still reject it.

Each run records 39 requests, 36 responses, three clean MCP process exits and
one native source-denial preparation command. Both replays and two coherently
rehashed controls per run PASS (exit 0). All 30 tool-result rows match after
explicit per-call identity/timing and sync store-size exclusions. Producing
trail/packet/request/decision identities are retained and bound within each run,
not assumed equal across fresh requests. The runnable product stdio example
also passes with the same public-head binary.

## What the client observed

An ordinary `backup` query selects the synthetic instruction alone. The supplied
connection-closure declaration adds a qualification that does not match the
query, with independent provenance, association origin, author and basis and no
lexical rank/BM25. Both term policies and both byte packers work. Primary evidence
is unchanged before index mutation. Default/explicit-false and unfired requests
preserve ordinary stable results; unfired original history keeps legacy v1
projection. Depth one, missing/inactive targets, primary-priority budget and
exact-content duplicate omissions are visible. Null/empty declarations and
supersession/token/reservation/vector combinations refuse as invalid arguments.

V3 history binds the selected association to its producing query under a new
current authorization decision. After deletion, historical selection remains
recorded while `indexed_now` is false. Read-only startup needs no ingestion
permission to retrieve; the final source denial releases neither query evidence
nor historical facts. Normal authorization audit writes are allowed. This client
does not open SQLite or assert all tables are unchanged; product regressions
cover structural no-partial-state, same-source ownership, exhaustive core bounds
and nested/byte validation independently.

## Archive and replay

`raw-captures.tar.gz` contains seven bounded regular members: both complete raw
captures, their summaries and mutation-control receipts, plus the comparison.
`protocol.json` enumerates every member's size and SHA256; the repository verifier
checks those before extraction. `build.json` records exact source/binary/build
identity; `runner.json` binds the driver, frozen schedule, accepted discovery
baseline and reused strict wire/schema helpers. No database or binary is exported.

From this repository:

```sh
python3 tools/verify_results.py
mkdir /tmp/mousa-association-archive
tar -xzf results/2026-10-31-mcp-associations/raw-captures.tar.gz -C /tmp/mousa-association-archive
python3 mcp-associations/capture.py verify --output /tmp/mousa-association-archive/capture
python3 mcp-associations/capture.py controls --output /tmp/mousa-association-archive/capture
python3 mcp-associations/capture.py verify --output /tmp/mousa-association-archive/reproduction
python3 mcp-associations/capture.py controls --output /tmp/mousa-association-archive/reproduction
python3 mcp-associations/capture.py compare --output /tmp/mousa-association-archive/capture --other /tmp/mousa-association-archive/reproduction
```

See the [client instructions](../../mcp-associations/README.md) for a new capture.
Commands must run from the companion revision containing these exact runner bytes.
The changed-declaration control fails `scheduled-request-bytes`; changing an
associated digest while repairing the text envelope and stream hashes fails
`evidence-content-digest`. Controls are deterministic regeneration receipts,
not separately archived mutated copies. They test assertions beyond file hashes.

## Retained limits and failures

One pre-freeze local-source pilot failed because its assertion froze primary
BM25 across a target deletion that changes corpus statistics. The corrected
assertion retains exact comparison before deletion and compares primary
provenance/text afterward. A transient edit syntax error was corrected before
execution. These preparation failures were retained separately and are not
product or final-public-head failures. Both final captures, live/archived replays,
controls and comparison pass. Historical archives and pins remain unchanged.

This is an alternative caller-supplied evidence path, not a discovered relation,
authenticated authorship, access grant or proof of semantic sufficiency. No
answer generator or judge runs. Matching/packing/provenance observations do not
establish recall, completeness, truth, long-horizon memory reliability, latency,
model-window safety or actual-host integration. Replay establishes internal
consistency, not authenticity against a fabricator of the entire capture. Hashes
record observed identities, not cryptographic proof a build or process ran.
Deferred startup/export and semantic/temporal experiments remain deferred.
