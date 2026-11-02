# Native attributed classification assertions

This standard-library client exercises `classification put` and `classification get`
against a temporary store created through native JSONL sync. It records caller-supplied
labels using existing immutable classification storage; it does not run a classifier,
verify a label's truth or change evidence selection. Source builds containing the
commands are required. No tagged release is claimed.

## Reproduce

Use Git, Go 1.25 or newer and Python 3, from this repository root. Use absent checkout,
binary and output paths. The protocol pins the exact public product head/tree, the
runner and the unchanged strict client/archive helpers.

```sh
PRODUCT_HEAD=$(python3 -c 'import json; print(json.load(open("classification-admin/protocol.json"))["product_head"])')
git clone https://github.com/graydeon/mousa.git /tmp/mousa-classification-source
git -C /tmp/mousa-classification-source checkout --detach "$PRODUCT_HEAD"
(cd /tmp/mousa-classification-source && GOWORK=off CGO_ENABLED=0 GOAMD64=v1 go build -o /tmp/mousa-public-classification-admin ./cmd/mousa)
python3 classification-admin/capture.py capture \
  --mousa /tmp/mousa-public-classification-admin \
  --product-source /tmp/mousa-classification-source \
  --output /tmp/mousa-classification-capture
python3 classification-admin/capture.py verify --capture /tmp/mousa-classification-capture/capture.json.gz
python3 classification-admin/capture.py controls \
  --capture /tmp/mousa-classification-capture/capture.json.gz \
  --output /tmp/mousa-classification-capture
```

Run `capture` again with an absent second output path, then compare both fresh-store
captures. The source label, item, synthetic text, timestamp and assertion facts are
fixed, so canonical assertion documents/IDs and evidence pins are compared exactly:

```sh
python3 classification-admin/capture.py capture \
  --mousa /tmp/mousa-public-classification-admin \
  --product-source /tmp/mousa-classification-source \
  --output /tmp/mousa-classification-reproduction
python3 classification-admin/capture.py compare \
  --capture /tmp/mousa-classification-capture/capture.json.gz \
  --other /tmp/mousa-classification-reproduction/capture.json.gz
python3 tools/verify_results.py
```

Query request, decision and trail identities, evaluation times and diagnostic timings
are invocation-specific; they are not cross-run comparison targets. JSONL source
identity does not depend on the public temporary store path. Capture verifies clean
source, exact head/tree and CGo-free binary VCS metadata before running the workflow.

## Checked behavior

The 13-command workflow syncs one synthetic item, queries a real passage and submits
a `mousa.classification_input.v1` draft with its segment as subject and representation
as basis. It checks explicit facts in the returned canonical classification.v1 record,
exact put/retry/get bytes, changed assertion identity, unchanged original readback and
unchanged ordinary retrieval evidence/packet. A missing source parent must return
exit 1 with a typed conflict and no success JSON; the existing assertion stays readable.
Resync then replaces the evidence revision. The old assertion retains its original
segment and basis representation, distinct from the replacement pins.

This small capture exercises **segment subjects and representation basis only**.
Product-local tests cover strict input/all five typed subjects, row/link idempotence,
transaction rollback, canonical damage and startup classification. Matching repeated
client output alone does not prove unchanged database row/link counts.

Each archive retains actual arguments/argv, stdin, stdout, stderr, exits and producing
identities. Strict shared helpers check stream bytes/hashes, closed scheduled requests,
JSON objects and exact exit/error expectations. The existing content-addressed archive
helper retains all raw streams; the run manifest separately hashes every public file.
No binary or database is exported. Replaying the saved archive checks protocol behavior
without opening a store or executing the binary. The archive verifier checks file
membership/hashes, not behavior; run `capture.py verify` for behavioral replay.

The negative control changes the returned label, recomputes its stream hash and writes
a freshly hashed archive. Replay must reject it at `assertion-facts-binding`, not merely
an outer hash mismatch. The deliberately invalid control archive is labeled separately
from successful captures.

## Scope

Attribution is not authenticated authorship, calibrated probability, policy authority
or factual truth. Conflicting assertions coexist; no newest/confident winner or validity
interval is inferred. Revision pins do not reconstruct retired text or label replacement
evidence. Source-level assertions, although supported by the product, would name a stable
identity rather than automatic approval of future content.

Labels do not change indexing, serving permission, ranking, freshness or supersession.
Classification-based filtering/authorization, secret scanning and automatic inference
remain unimplemented. No MCP administration, SQL reads/mutations, product imports, export,
model/answer/judge calls, historical archive rewrite or performance/semantic campaign is
part of this capture.
