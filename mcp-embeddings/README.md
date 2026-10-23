# MCP external-embedding workflow

This standard-library client completes sync, current passage export, external
hand-assigned vector import, query and historical inspection through the real
stdio MCP tools. It imports no product code, opens no SQLite store and calls no
embedding provider. The existing MCP retrieval helpers supply strict JSON,
bounded frame reads, canonical comparisons, stream hashes and the supported
closed-schema subset; this is not a general benchmark framework.

## Build and run

Build a clean checkout at the full public product head recorded in the dated
result's `build.json`, not an unpinned main checkout:

```sh
GOWORK=off CGO_ENABLED=0 go build -o /tmp/mousa-public-embeddings ./cmd/mousa
```

From this repository, with absent output directories:

```sh
python3 mcp-embeddings/capture.py capture \
  --mousa /tmp/mousa-public-embeddings --product-source /tmp/mousa-public-source \
  --product-head PUBLIC_HEAD --output /tmp/mousa-embedding-capture
python3 mcp-embeddings/capture.py verify --output /tmp/mousa-embedding-capture
python3 mcp-embeddings/capture.py controls --output /tmp/mousa-embedding-capture
python3 tools/verify_results.py
```

Replace `PUBLIC_HEAD` with the complete recorded identity. Repeat capture with a
different absent output directory for a separate fresh-store reproduction.
No optional Python packages, tokenizer or network model service are needed.

## Recorded workflow

Each run retains 35 requests, 32 responses and three process exit statuses. Raw
stream records retain base64 bytes, SHA256, lengths and LF framing, including
stderr and unexpected trailing stdout. The sole native command sets source
retrieval denial for the final control session; native vector export/import are
never used. Sync, replacement, export and embedding import use MCP.

The fixture assigns arithmetic-only vectors to two of three current passages.
Export checks exact normalized text, byte ranges and digests, then import retains
every source/segment/representation/content pin. The declared space's canonical
bytes include a final LF; its SHA256 is checked independently. The accepted
submitted count includes exact retries and is not called a newly inserted count.
An immutable conflict refuses; a mixed stale batch after replacement refuses;
a fresh export and complete import succeeds. This is not an external snapshot
lease. Both packers return the known cosine winner and the overlapping
second-ranked passage that wins equal-weight RRF(k60). Producing query/space/pin,
trail/packet/decision and historical branch relationships are bound to the
responses that produced them, including after replacement and process restart.

A read-only startup permits export but refuses import. Fresh retrieval denial
withholds export and historical facts while separately granted administrative
import remains permitted. The product's source-bound local HTTP fixture, not
this stdio capture, checks the additional HTTP write-scope runtime gate and
actual insertion state. Atomic database rollback/row identity, withdrawn sources,
foreign-source batches, codec/frame size boundaries and optional token compatibility
remain product regression evidence, not claims established by this one fixture.

Every request is compared byte-for-byte with a regenerated schedule. Successful
and refused tool envelopes are validated against actual discovered closed output
schemas. The helper checks only its documented JSON Schema subset, not arbitrary
schemas. Independent history opt-ins and existing tool behavior remain unchanged.

## Negative controls and limits

Two controls regenerate coherent copies with recalculated stream hashes. Changed
import values fail `scheduled-request-bytes`. A fabricated read-only success uses
a valid canonical space ID/count and matching text/structured envelopes but fails
`expected-tool-error`. Only deterministic regeneration receipts are archived;
`controls` reconstructs the copies from retained observations.

This proves bounded protocol/ranking arithmetic and permission observations,
not semantic quality, embedding-model integration, latency, HTTP authentication,
model-window safety or universal input compatibility. Retry wire success does
not independently prove database row counts. Replay establishes internal
consistency, not authenticity against an adversary able to fabricate the whole
capture. Build/binary hashes record observed identity, not proof a build ran.
No database, executable, secret or cache is exported. Earlier capture bytes and
pins, including deferred startup/export failures, remain unchanged.
