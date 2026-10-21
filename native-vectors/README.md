# Native caller-supplied vector example

`capture.py` drives only the public Mousa executable. It uses fresh directory and
JSONL sources, exports authorized normalized inputs, imports synthetic vectors,
queries by vector and reads the producing packet/trail metadata. It never opens
SQLite or imports internal Go packages. Python 3 is the bounded example driver,
not a Mousa runtime dependency.

The [capture and fresh-store reproduction](../results/2026-10-21-native-vectors)
record the exact public product head/tree, build command, binary digest, source
inputs and all native argv/stdin/stdout/stderr/exit receipts. Use the product pin in
that result's `build.json`, not current main or a historical supersession capture.
The product PR is submitted for review, not claimed merged.

## Reproduce

From this repository, with Git, Go 1.25 or newer and Python 3, use absent checkout,
binary and output paths:

```sh
PRODUCT_HEAD=$(python3 -c 'import json; print(json.load(open("results/2026-10-21-native-vectors/build.json"))["head"])')
git clone https://github.com/graydeon/mousa.git /tmp/mousa-vector-example-source
git -C /tmp/mousa-vector-example-source checkout --detach "$PRODUCT_HEAD"
(cd /tmp/mousa-vector-example-source && GOWORK=off CGO_ENABLED=0 go build -o /tmp/mousa-vector-example ./cmd/mousa)
python3 native-vectors/capture.py \
  --mousa /tmp/mousa-vector-example \
  --product-source /tmp/mousa-vector-example-source \
  --product-head "$PRODUCT_HEAD" \
  --output /tmp/mousa-vector-example-receipts
python3 tools/verify_results.py
```

The product checkout must be clean and match `--product-head`. No provider,
credentials, model download, inference service, GPU or non-stdlib Python package
is needed. Go builds need the product's existing module dependencies. Each native
subprocess has a 30-second timeout; this fixed three-item fixture rejects a response
above 1 MiB. The driver saves each command receipt before checking its result, so
failed observations remain inspectable rather than being replaced with success.

## Observed behavior

The fixture has two independently identified copies of `Shield the specimen
cabinet from heat.` and one tram timetable. Input uses CRLF; export returns the
exact normalized LF bytes, source/segment/representation/content pins and ranges.
Lexical `frost` has no overlap and returns no evidence. Constructed vectors `[1,0]`
for the cabinet passages and `[0,1]` for the timetable produce known cosine scores
of one and zero for query `[1,0]`. The word label does not authenticate the query
vector's meaning or a model's execution.

With a two-cabinet-passage byte budget:

- Original packing selects both tied cabinet copies in canonical segment-ID order.
- Exact-v1 keeps the first copy, omits its byte-equal duplicate and uses the freed
  budget for the zero-score timetable. Zero scores are eligible; there is no
  semantic threshold or hybrid ranking.
- Native v5 history binds the declared descriptor, space/query-vector identities,
  query values, all candidate/embedding/source/content pins, scores, order,
  selected flags and packet identity. A second query reopens the store and preserves
  the packet, without reusing decision/trail identities.
- Updating the first cabinet item and resyncing leaves three eligible current
  passages but only two indexed in the declared space. The old segment is never
  released, stale import rejects, and fresh export reports new content pins.
  Inspection of the original trail preserves its vector facts and marks the
  retired segment as no longer indexed.

Directory roots use deliberately public `/tmp/mousa-public-native-vectors-*`
paths from creation. Their exact identities remain in raw receipts; they are not
redacted or rewritten. Each reproduction has a different directory source and
therefore different canonical IDs and potentially a different first tied item.
Compare producing-run relationships and expected bytes/order, not raw cross-run
identity equality. JSONL uses the fixed declared source label; request/decision/
trail IDs and capture times remain invocation-specific there too.

## Limits

These are synthetic protocol/ranking observations and a separate fresh-store
reproduction, not model quality, automatic natural-language semantic search,
semantic truth, performance, authentication or model-window acceptance. The
capture does not prove corrupt-store rollback, concurrent snapshot ordering or
all denial/withdrawal boundaries; those are product regressions. It runs no
hybrid, ANN, association/supersession combination or MCP vector query.

The shared archive verifier checks retained regular-file membership, sizes and
hashes, not runtime semantics; reproduction reruns the native behavior checks.
No database, binary, credentials or model artifacts are exported. Earlier captures
and deferred startup-publication failures remain unchanged.
