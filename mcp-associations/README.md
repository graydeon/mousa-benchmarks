# MCP declared supporting context

This standard-library stdio client demonstrates a caller-supplied supporting note
through lexical `mousa_query`. A synthetic backup instruction matches `backup`;
a separate connection-closure qualification does not. Without declarations the
client receives primary evidence alone. Inline declarations add independently
attributed supporting evidence and producing v3 history. No product imports,
SQLite access, model, answer generator, judge or external service is used.

## Build and reproduce

Use a clean anonymous checkout at the exact public product head in the dated
result's `build.json`, not an unpinned main or local-only binary. In that checkout:

```sh
GOWORK=off CGO_ENABLED=0 go build -o /tmp/mousa-associations ./cmd/mousa
```

From this repository, use absent output directories and replace `PUBLIC_HEAD`
with the full recorded product revision:

```sh
python3 mcp-associations/capture.py capture \
  --mousa /tmp/mousa-associations --product-source /tmp/mousa-public-source \
  --product-head PUBLIC_HEAD --output /tmp/association-capture
python3 mcp-associations/capture.py verify --output /tmp/association-capture
python3 mcp-associations/capture.py controls --output /tmp/association-capture
python3 mcp-associations/capture.py capture \
  --mousa /tmp/mousa-associations --product-source /tmp/mousa-public-source \
  --product-head PUBLIC_HEAD --output /tmp/association-reproduction
python3 mcp-associations/capture.py compare \
  --output /tmp/association-capture --other /tmp/association-reproduction
python3 tools/verify_results.py
```

The archived result README gives its extraction and replay commands. Each capture
creates its own temporary store; only the native `access --source notes deny`
command prepares the final fresh-denial session. All ingestion, deletion,
queries and history inspection use MCP. Two later sessions lack ingestion
permission; retrieval/history remain separately authorized.

## Frozen observations

`protocol.json` pins fixture, declaration, runner and the 39-request/36-response
schedule. Generated wire bytes are compared with that schedule, including fresh
producing trail IDs substituted into historical requests. Three process exits,
raw base64 request/response bytes, hashes, lengths, stderr and trailing stdout
are retained. The existing retrieval/trail helpers supply strict duplicate-key
parsing, canonical JSON equality, bounded frame reads and the documented closed
JSON Schema subset; no general benchmark framework is added.

Both term policies and both packers select the primary instruction first, then
the supporting note with its own segment/representation/content pins, byte
coordinates, origin and caller attribution, without lexical rank or BM25.
The primary passage is unchanged within an unchanged index. Deleting a target
can change BM25 through corpus statistics, so later primary comparisons preserve
provenance/text but do not incorrectly freeze its earlier score.

The schedule covers omitted and explicit-false defaults, an unfired declaration,
primary-priority byte omission, an unselected primary, exact-content duplicate
omission, depth one, missing and inactive targets, invalid null/empty documents,
supersession/token/reservation/vector refusal and fresh query/history denial.
Discovery matches the accepted pre-feature executable after removing exactly
one new query input property; the other seven definitions and query outputs
are unchanged. Producing v3 facts are bound within each call; after deletion,
historical selection remains true while `indexed_now` is false. Fresh history
uses a distinct authorization decision. Denial returns no historical payload.

Comparison excludes only enumerated per-call identities/timing, historical
producing identities and sync store-size samples; all remaining properties are
compared. Packet identities remain retained and bound to their producing call,
not assumed equal across requests. Normal authorization may append audit rows.
This client does not inspect database tables and makes no zero-write claim.
The product's store-boundary tests, not this capture, establish no partial
producing state on structural argument failures and exhaustive fan-out/passage
bounds. Same-source ownership and strict nested/byte limits are also covered by
product regressions rather than inferred from this small client schedule.

## Mutation controls and limits

Two independently regenerated, rehashed mutations must fail intended assertions:
changing a declaration target in a request fails `scheduled-request-bytes`;
changing an associated content digest, while updating the matching text envelope
and response hashes, fails `evidence-content-digest`. These are semantic binding
checks beyond archive integrity. Only deterministic control receipts are stored;
`controls` reconstructs the mutated copies, not independent archived captures.

A caller-declared note is an alternative supplied evidence path, not a discovered
relationship, authenticated author, access grant or proof that context answers
a question. Matching, packing, generation and judging are distinct; only the
first two and protocol/provenance are exercised. No claim of semantic sufficiency,
recall, completeness, truth, long-horizon memory reliability, latency or host
integration follows. Replay proves internal consistency, not authenticity against
a producer able to fabricate the entire capture. Build hashes record observed
identity, not a cryptographic proof of compilation. No database, binary, secret,
cache or historical archive is exported or rewritten. Token/supersession and
vector/hybrid association composition remains unsupported.
