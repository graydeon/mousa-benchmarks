# MCP caller-supplied vector and hybrid retrieval

This standard-library Python driver prepares synthetic embeddings through public
native sync/vector commands, then speaks newline-delimited JSON-RPC directly to
the built Mousa executable. It imports no product package and never opens SQLite.
The existing historical-inspection runner supplies its bounded schema, strict
JSON comparison and stream-hash helpers; no new general verification framework
or dependency is added.

## Reproduce

Read the exact public product head from the dated result's `build.json`. Build
that clean anonymous checkout, not current main:

```sh
GOWORK=off CGO_ENABLED=0 go build -o /tmp/mousa-public-mcp ./cmd/mousa
```

From this repository, run with an absent output directory:

```sh
python3 mcp-retrieval/capture.py capture \
  --mousa /tmp/mousa-public-mcp \
  --product-source /tmp/mousa-public-source \
  --product-head PUBLIC_HEAD \
  --output /tmp/mousa-mcp-reproduction
python3 mcp-retrieval/capture.py verify --output /tmp/mousa-mcp-reproduction
python3 mcp-retrieval/capture.py controls --output /tmp/mousa-mcp-reproduction
python3 tools/verify_results.py
```

Use the actual full commit ID for `PUBLIC_HEAD`. Each capture creates a fresh
store and starts three stdio sessions. It retains five native preparation/change
command inputs, stdout, stderr and actual exits, plus 43 scheduled request frames,
40 raw response frames, all process exits and any trailing stdout/stderr. Stream
records keep original base64 bytes, lengths and SHA-256, including LF framing.
The capture and separate reproduction use independent fresh stores.

## Expected client behavior

The configured JSONL source contains three passages:

| Item | Text | Lexical rank for `Drain` | Vector rank for `[1,0]` |
|---|---|---|---|
| `overlap.md` | Drain sockets before stopping the host. | 2 | 2, cosine 0 |
| `vector.md` | Radishes prefer damp soil. | Absent | 1, cosine 1 |
| `lexical.md` | Drain sockets. | 1 | Absent: unembedded |

With a 40-byte budget, vector retrieval selects `vector.md`; hybrid selects the
39-byte overlap. The independent expectation uses rational arithmetic: `2/62`
beats `1/61`. The driver validates every hybrid candidate's branch membership,
ranks, cosine, RRF and canonical pins, canonical-ID ties, selected text/digest/
coordinates and producing decision/trail/packet bindings. Actual BM25 is recorded
and must be numeric/finite; it is not recomputed from later index contents.

Omitted, explicit original and exact-v1 packing all run, with default packet
identity checked against original. This small capture has no exact-content
copies; duplicate and budget-skip edge cases remain product regression coverage.
Discovery/output validation uses the existing bounded schema subset, including
exactly-one `oneOf`, not a general JSON Schema implementation. Legacy sync/status/
query definitions are compared with accepted-main discovery, changing only their
configured source enum from the baseline fixture to this fixture's exact alias.
The baseline keeps the original four definitions and their bytes. The trail's
intentional optional schema growth and two added tools are not legacy equality
claims; their wire responses are validated against actual discovery.

Default and false history omit vector/hybrid facts; true returns recorded producing
facts. Restart and a later replacement revision remove stale current vectors but
leave opted-in old history unchanged. A fresh deny releases no evidence, source
coverage, candidate scores or historical existence. The driver also observes
bool-as-number rejection and a path-looking unconfigured alias refusal. Every
request, including history targets obtained from its producing query, is compared
byte-for-byte with the independently regenerated schedule; canonical JSON
comparison distinguishes booleans, integers and floats at every depth.

Two negative controls regenerate copies with coherent stream hashes: an incorrect
selected item with matching text/structured envelopes must fail `selected-evidence`,
and a query vector changed to `[true,0]` must fail `scheduled-request-bytes`.
Only control receipts are stored; `controls` deterministically rebuilds those
mutations from the retained capture, not from a stale digest.

## Limits

These are synthetic arithmetic/protocol and authorization observations, not
semantic relevance, embedding-model integration, ANN, automatic generation,
latency, authentication or model-window-safety evidence. External embedding
generation/import remains operator work. MCP accepts query values only for exact
configured JSONL aliases. It exposes neither tokenizer paths nor token-budget
execution/metadata. Product regressions separately cover native-created v5/v6/v7
inspection, strict malformed input boundaries and both packers' duplicate skips.

Historical completeness and missing-vector absence are producing observations;
hashes cannot prove them retrospectively. Retired passage bytes remain unarchived.
Stable JSONL pins are comparable for this fixed source, but per-call audit/trail
identities differ; each run verifies its own producing relationships. No database,
binary, cache, model or credential is exported. Build and binary hashes record
observed provenance; they do not cryptographically prove a build. Old native,
MCP, token and startup archives remain at their historical pins.
