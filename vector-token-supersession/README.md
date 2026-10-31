# Vector/hybrid token budgets with supersession

This client observes native JSONL queries and configured stdio MCP aliases. It
imports no product packages and never opens SQLite. Synthetic two-dimensional
vectors establish cosine/RRF arithmetic, not embedding-model quality. No model,
provider, dependency installation or vocabulary download runs during capture.
The prepared official tiktoken 0.12.0/o200k_base ordinary encoder is required.

The fixture reuses the byte-only vector-supersession source: an exact predecessor,
a byte-equal twin, a nonmatching successor with no embedding, and a larger peer.
A 12-byte released-text budget retains the predecessor ordinarily and the twin
under enforcement. Both retrieval modes and packers exercise omitted/false/true,
whole-rendering exact fit/one-token-short, byte pressure, reservations and zero
remaining allowance. The count covers the exact returned provenance headers,
separators and passage bytes, not a sum of independent passage estimates.
Producing branch ranks, RRF(k60), candidate populations and coverage are checked
without reranking. Withheld candidates retain positive sizes/ranks and null
proposed counts, and do not seed duplicate retention.

Native normal history and explicit official recount use producing v10 selection.
MCP supersession, token-details and retrieval-details projections are independently
requested. After the successor and survivors become unavailable, a fresh server
checks all-withheld outcome precedence and the original producing history. Native
history is read after deactivation. Retired text remains unarchived; its historical
count is a producer observation, not a successful new recount.

## Capture from a public head

Build a clean anonymous checkout at the result's exact product head/tree, separate
from the implementation checkout. From this repository root:

```sh
GOWORK=off CGO_ENABLED=0 go -C "$PRODUCT" build -o "$BINARY" ./cmd/mousa
"$TOKEN_PY" vector-token-supersession/capture.py capture \
  --mousa "$BINARY" --product-source "$PRODUCT" --product-head "$HEAD" \
  --python "$TOKEN_PY" --cache "$TOKEN_CACHE" --output "$OUTPUT"
```

`TOKEN_PY` names an already prepared interpreter, preserving its virtual-environment
path, and `TOKEN_CACHE` names its offline vocabulary cache. Every operand is local;
use a new absent output directory for each attempt. Repeat into a separate fresh
store. No canonical database or binary is exported.

The capture records every scheduled argument, stdin/stdout/stderr/exit and exact
JSON-RPC request/response stream with lengths and hashes. `BINARY`, `STORE`,
`TOKEN_PY` and `TOKEN_CACHE` are explicit local path substitutions in argv receipts;
the remaining arguments and all protocol bytes are retained unchanged.
`private-argv.json` retains actual local paths and is excluded from public archives.
Each failed attempt keeps its partial report and is not counted as successful.

## Replay, controls and fresh-store comparison

```sh
"$TOKEN_PY" vector-token-supersession/capture.py verify \
  --cache "$TOKEN_CACHE" --output "$OUTPUT"
"$TOKEN_PY" vector-token-supersession/capture.py controls \
  --cache "$TOKEN_CACHE" --output "$OUTPUT"
"$TOKEN_PY" vector-token-supersession/compare.py "$LEFT" "$RIGHT" \
  --cache "$TOKEN_CACHE"
python3 tools/verify_results.py
```

Replay reconstructs the complete schedule from earlier observed pins, checks raw
request bytes, strict JSON types, discovered closed output schemas, text/structured
equality, source/selection/history bindings and independently counted contexts.
Controls coherently rehash a changed request, wrong measured count, wrong selected
pin and wrongly selected historical predecessor. Each must fail its exact intended
detector. Compact receipts bind mutated-report hashes; copies are regenerated,
not stored. These are bounded consistency checks, not arbitrary-adversary proof.

The comparator first verifies each complete run, then compares every result value
except enumerated per-invocation identity/time fields and historical wrapper IDs.
Raw values and within-run producing identity checks remain in both captures.
Archives use bounded regular members and per-member hashes; the repository verifier
checks archive integrity, not product conclusions or whether commands actually ran.

Directory selectors, current-authorization denial/source masking, full-source
admission, imports, internal graph/content corruption, transaction ordering and
worker faults/cancellation remain product-local acceptance checks. This fixture
makes no semantic-quality, latency, throughput, full-model-window safety or
retired-text reconstruction claim. Earlier public archives and pins are unchanged.
