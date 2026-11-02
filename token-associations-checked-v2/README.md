# Measured declared context after checked aggregate admission

This version repeats the original fixed client schedule against the public
product correction for checked v11 aggregate byte admission. The original
[producer and protocol](../token-associations) remain unchanged and replay their
original product pin. This producer is byte-identical; only its sibling frozen
protocol selects the corrected public head/tree. Compare the two corrected runs
only after each passes replay under this protocol. No cross-pin equality is claimed.
Normal finite captures do not exercise hostile canonical overflow records; those
boundaries remain product-local Validate/Decode regressions.

This client exercises native directory/JSONL and configured stdio MCP queries
against one exact public Mousa source head. It reuses the existing strict JSON,
wire, schema and official offline tokenizer helpers. It imports no product code,
opens no canonical database and calls no model, embedding producer or evaluator.

The fixture has one matching backup instruction, a nonmatching connection-closure
qualification and a byte-equal qualification in a distinct item. The declaration
is caller attribution, not authenticated authorship, an access grant or proof
that the note answers a question. Both packers run on all three interfaces:
`original` uses the original term policy and `exact-v1` uses dedup term policy.
This is not the full cross-product of term policies and packers; that matrix and
canonical/graph/corruption/snapshot/worker-fault cases remain product-local tests.

The schedule checks ordinary/unfired token controls, a complete associated
rendering, exact fit, one token below it without displacing primary evidence,
a primary that fails tokens despite fitting bytes, duplicate handling, producing
v11 history, native retained-text recount and independently filtered MCP token
details. Unsupported supersession/vector/hybrid associations refuse; fresh native
and MCP denial returns no evidence or historical payload. The two actual discovered
vector/hybrid supersession descriptions are checked for byte and measured-token
support, without advertising vector/hybrid associations.

## Capture

Prepare official `tiktoken==0.12.0` and the `o200k_base` cache before invoking the
client. Queries and reference encoding are offline and never install/download.
Set `TOKEN_PY` to the prepared venv interpreter and `TOKEN_CACHE` to its cache.
Keep a venv interpreter's path rather than resolving its executable symlink.

Build from `protocol.json`'s exact public product head:

```sh
PRODUCT_HEAD=$(python3 -c 'import json; print(json.load(open("token-associations-checked-v2/protocol.json"))["product_head"])')
git clone https://github.com/graydeon/mousa.git mousa-source
git -C mousa-source checkout --detach "$PRODUCT_HEAD"
BINARY="$(pwd)/mousa-public"
GOWORK=off CGO_ENABLED=0 go -C mousa-source build -o "$BINARY" ./cmd/mousa
"$TOKEN_PY" token-associations-checked-v2/capture.py capture --mousa "$BINARY" \
  --product-source mousa-source --product-head "$PRODUCT_HEAD" \
  --python "$TOKEN_PY" --cache "$TOKEN_CACHE" --output capture
"$TOKEN_PY" token-associations-checked-v2/capture.py capture --mousa "$BINARY" \
  --product-source mousa-source --product-head "$PRODUCT_HEAD" \
  --python "$TOKEN_PY" --cache "$TOKEN_CACHE" --output reproduction
```

Each capture creates an independent temporary store. Directory source identities
also bind the absolute root, so the runner uses the same new, owned
`mousa-token-associations-fixture` directory beneath the platform's temporary root
for both sequential runs. It must not already exist. The runner removes only the
directory it created. The recorded directory source label is retained, not rewritten;
comparisons require the same root. Raw command/wire bytes, stdin, stdout, stderr
and exits are saved incrementally. Path substitutions name binary/store/interpreter/
cache/declaration paths; the actual argv map is private and excluded from export.
No store, executable, interpreter or vocabulary cache belongs in a public archive.

## Replay and controls

```sh
"$TOKEN_PY" token-associations-checked-v2/capture.py verify --cache "$TOKEN_CACHE" --output capture
"$TOKEN_PY" token-associations-checked-v2/capture.py controls --cache "$TOKEN_CACHE" --output capture
"$TOKEN_PY" token-associations-checked-v2/capture.py verify --cache "$TOKEN_CACHE" --output reproduction
"$TOKEN_PY" token-associations-checked-v2/capture.py controls --cache "$TOKEN_CACHE" --output reproduction
"$TOKEN_PY" token-associations-checked-v2/capture.py compare --cache "$TOKEN_CACHE" \
  --output capture --other reproduction
python3 tools/verify_results.py
```

Replay asserts scheduled bytes, request/response IDs, discovered closed output
schemas, exact selected fixture text/digests/ranges, declaration provenance,
primary versus associated count alignment and complete rendering counts/hashes.
Proposed counts are independently encoded whole contexts, not sums of passage
counts. Null counts remain null for uncounted duplicates. Within-run historical
identities bind to the query that produced them before comparison removes only
explicit per-call identity/time fields, access-activation identities and sync
store-size samples. Source, segment, packet, access binding and all
selection/count/provenance facts remain compared.

Controls regenerate changed copies from each archived capture, repair stream
hashes and text/structured envelopes, and require their intended detectors:
changed declaration request → `scheduled-request-bytes`; changed associated
proposed count → `associated-proposed-count`; changed attributed author →
`association-provenance`. Stored control receipts contain regenerated copy hashes,
not additional independently observed product runs. The protocol freezes this
runner and its three imported helper implementations. Replay is internal
consistency evidence, not proof of execution or authenticity against an arbitrary
coordinated rewrite.

The result archive's outer manifest and member hashes must be verified before
extraction/replay. The repository archive verifier checks bounded regular members
and hashes, not protocol conclusions. Synthetic counting/selection does not
establish semantic sufficiency, recall, completeness, truth, authenticated
authorship, performance or universal model-window safety. No generation or judging
runs, and earlier public result bytes/pins remain unchanged.
