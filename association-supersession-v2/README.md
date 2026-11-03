# Empty association compatibility and composed supporting context

This additive producer extends the unchanged `association-supersession` fixture,
composition checks and MCP schedule. It does not replace that producer, its frozen
protocol or any historical result. Each capture requires an explicit frozen
protocol file naming the exact clean product head/tree and runner/helper hashes.
A `local-smoke` protocol records development checks only; corrected-public-head
observations require `publication_state: "public-corrected"` after anonymous
public-head/tree verification. Changing that label cannot establish publication.

The [frozen public protocol](protocol.json) pins corrected product
`b5730d6b311985b730765598baf24b972430bc10`. The
[paired observations and complete reproduction commands](../results/2026-11-03-association-supersession-v2)
record two fresh stores, both offline replays, ten controls and the 29-row comparison.

## Fixed schedule

One fresh store runs 72 native commands and one 13-frame configured MCP session
(12 responses and one notification). The existing 24-command composition workflow
is retained on both native source forms and both packers. Its unchanged MCP
schedule retains both packers, producing history opt-in/opt-out and token-triple
refusal. Exact predecessor suppression, surviving nonmatching support and the
byte-equal unsuppressed twin are checked by the original producing-fact helpers.

The additional 48 native calls cover directory/JSONL, original/exact-v1 and
omitted/false/true supersession with an explicitly empty association flag:

- Each case first runs the same query without an association flag, then binds
  inspection to that call's own producing request/decision/trail/packet IDs.
- Omitted/false plus `--associations=` must succeed and exactly match the baseline's
  complete stable result and property set, including evidence order, packet facts,
  omissions and byte counts. Its own producing history is also inspected.
- True plus an empty flag must return exit 2, empty success stdout and an error,
  both on the existing store and an absent-store path. The absent file must remain
  absent. True without any association flag remains a supported baseline query.

The comparison retains 29 stable producing rows. Only the original helper's
explicit per-call query/authorization identities and evaluation/latency timing are
excluded; all raw values remain recorded and bound within each run. Packet IDs,
evidence bytes/pins/order, omission counts, property sets and safe history facts
remain compared. The synthetic directory path is fixed and exclusively created,
so two sequential fresh-store captures need no source-identity normalization.
Existing paths refuse rather than being overwritten.

## Binding and controls

All native arguments, expected exits, stdin/stdout/stderr and process exits are
retained. MCP frames and send completion use the unchanged strict client/archive
helpers. Replay regenerates the entire attempted call population from fixture
logic and producing results, preserving strict JSON types, not Python's boolean/
number equality. Partial attempts are saved before execution and failures stop;
a partial receipt is not a successful observation.

Five newly rehashed controls must fail their intended semantic detectors:

| Mutation | Detector |
|---|---|
| Wrong expected exit for an explicit false/empty call | `scheduled-empty-expectation` |
| Removing the explicit empty flag from its recorded request/argv | `scheduled-native-request` |
| Changing the inline association request's type | `scheduled-request-bytes` |
| Changing recorded predecessor/successor suppression facts | `history-suppression-binding` |
| Changing selected support with plausible body digests/coordinates | `evidence-content-binding` |

The latter three retain the historical composition mutations and semantic checks.
Their implementation and all helper hashes are frozen by the supplied protocol;
no historical file is modified to point at a corrected product. Mutated archives
are deliberately invalid evidence, never successful captures.

## Running with a frozen protocol

Use an independently confirmed exact clean source checkout and CGo-free executable
matching `product_head`/`product_tree` in the protocol. The runner verifies source
cleanliness and embedded VCS/CGo metadata before capture. For a supplied protocol,
binary and checkout, the complete interface is:

```sh
python3 association-supersession-v2/capture.py capture --protocol "$PROTOCOL" \
  --mousa "$BINARY" --product-source "$PRODUCT" --output /tmp/composed-v2-first
python3 association-supersession-v2/capture.py capture --protocol "$PROTOCOL" \
  --mousa "$BINARY" --product-source "$PRODUCT" --output /tmp/composed-v2-second
python3 association-supersession-v2/capture.py verify --protocol "$PROTOCOL" \
  --capture /tmp/composed-v2-first/capture.json.gz
python3 association-supersession-v2/capture.py verify --protocol "$PROTOCOL" \
  --capture /tmp/composed-v2-second/capture.json.gz
python3 association-supersession-v2/capture.py compare --protocol "$PROTOCOL" \
  --capture /tmp/composed-v2-first/capture.json.gz --other /tmp/composed-v2-second/capture.json.gz
python3 association-supersession-v2/capture.py controls --protocol "$PROTOCOL" \
  --capture /tmp/composed-v2-first/capture.json.gz --output /tmp/composed-v2-controls
```

Use fresh output directories and run captures sequentially. Ordinary byte-only
capture needs no tokenizer backend, model service or inference credentials.
The protocol carries schema `mousa.association_supersession_observations.v2`,
publication state, exact product head/tree, producer SHA-256, helper path/hash map,
complete fixed fixture and `native_commands: 72`. A protocol and captures are
source-bound observations, not authorization or an authenticity signature.

## Limits

These are bounded synthetic protocol/compatibility/selection observations, not
semantic sufficiency, truth inference, authenticated authorship, temporal truth,
universal absence, model quality or performance. No SQL, product internals,
database/binary export or model calls are used. The no-create observation is a
public filesystem boundary, not transaction rollback evidence. Snapshot ordering,
hostile canonical data and internal rollback remain product-test claims. Historical
captures retain their original producing pins; development smoke cannot be relabelled
as corrected-public-head evidence.
