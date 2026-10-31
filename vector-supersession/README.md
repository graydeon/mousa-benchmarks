# Byte-packed vector/hybrid supersession client

This standard-library Python driver observes the public native executable and
configured stdio MCP. It imports no product packages and never opens SQLite.
Embeddings are supplied two-dimensional arithmetic fixtures; no model runs.

The fixed JSONL source contains a predecessor, a byte-equal twin, a nonmatching
successor with no embedding, and a larger vector-only peer. The 12-byte budget
admits the predecessor ordinarily. Explicit enforcement selects the twin without
reranking or changing producing coverage. Both packers and retrieval modes run
through native and MCP clients, including omitted/false/true inputs. Independent
MCP supersession/retrieval-details inspection flags release recorded members only.
A second server session checks selection after the successor is withdrawn, plus
old producing history. Native history is read again after deactivation.

## Capture

Use the exact public product head/tree in the paired result's `build.json`.
Build that clean anonymous checkout separately; do not use a product working tree
or substitute a local implementation build. From this repository root:

```sh
GOWORK=off CGO_ENABLED=0 go -C "$PRODUCT" build -o "$BINARY" ./cmd/mousa
python3 vector-supersession/capture.py capture --mousa "$BINARY" \
  --product-source "$PRODUCT" --product-head "$HEAD" --output "$OUTPUT"
```

`PRODUCT`, `BINARY`, `HEAD` and `OUTPUT` are explicit local operands. Use a new,
absent output directory for each capture. Repeat against a separate fresh store;
the driver creates and removes it internally. The output retains every scheduled
native argument/input/output/error/exit and every raw JSON-RPC request/response,
including discovery and clean process-exit/tail receipts. Failed attempts retain
their partial capture and must not be counted as successful observations.

## Offline replay and negative controls

```sh
python3 vector-supersession/capture.py verify --output "$OUTPUT"
python3 vector-supersession/capture.py controls --output "$OUTPUT"
python3 tools/verify_results.py
```

Compare two independently captured stores with the explicit ID/time exclusions:

```sh
python3 vector-supersession/compare.py "$LEFT" "$RIGHT"
```

`LEFT` and `RIGHT` are capture output directories. The comparator first verifies
each complete run, then compares every result property except the enumerated
fresh invocation identity/time fields and historical wrapper IDs. Raw values
remain in both captures and their within-run bindings are checked before filtering.

Replay regenerates the request schedule from earlier observed pins and binds raw
request bytes, stream sizes/hashes, strict JSON types, discovered closed output
schemas and text/structured equality. It checks exact evidence pins/text/ranges,
original cosine/branch/fused ranks, independently calculated RRF(k60), honest
coverage and recorded consultation/history identity. It does not rerun retrieval
to verify history. The raw observations retain actual BM25/cosine values.

Controls coherently rehash a changed opt-in request, incorrect withheld count,
wrong selected item and incorrectly selected historical predecessor. The exact
intended detectors must reject each mutation. Compact receipts bind the mutated
report hashes; the mutated copies are regenerated, not stored. These controls
establish specific consistency checks, not resistance to an arbitrary malicious
producer. Hashes alone do not prove a build or command ran.

No latency, semantic/model quality, task-completion, token-window or old-text
reconstruction claim follows. Directory, denial, lifecycle-derived graphs,
corruption, snapshot ordering and unsupported-combination regressions remain
separate product tests, not observations from this client fixture. Older public
captures retain their exact files and producing revisions.
