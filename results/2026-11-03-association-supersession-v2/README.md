# Corrected empty-association and supporting-context observations

Two independent fresh-store public-client runs use corrected product
`b5730d6b311985b730765598baf24b972430bc10`, tree `05966cd8d06a619dc1d4198a41863f8bb77a9320`
([PR101](https://github.com/graydeon/mousa/pull/101), [issue102](https://github.com/graydeon/mousa/issues/102)).
Anonymous checkout confirmed public/tested tree equality. [build.json](build.json)
records the clean public-head CGo-free build, embedded revision and executable digest;
no executable or database is exported. [protocol.json](protocol.json) freezes the
additive v2 producer and unchanged strict client/stream/archive helpers.

Each store passed 72 native commands and 13 configured MCP frames (12 responses,
one notification). Both native directory/JSONL forms and original/exact-v1 packers
exercise omitted/false/true supersession with an explicitly empty association flag.
Omitted/false succeeds and matches the corresponding absent-flag query's complete
stable output/property set, evidence order, packet facts and omissions. Each history
inspection binds to its own producing request/decision/trail/packet identities.
True plus empty refuses with exit2 and no success stdout on existing and absent
stores; the absent file stays absent. True without an association flag succeeds.

The retained composition workflow checks exact primary/associated predecessor
suppression, selected-primary-only declaration firing, surviving nonmatching support,
the unsuppressed equal-body twin, both packers, producing v12 history and configured
MCP consultation opt-in/opt-out. The token triple remains refused. Attribution does
not establish semantic sufficiency; replacement is explicit, not truth inference.

## Replay and controls

Both archived captures replay successfully. [comparison.json](comparison.json)
passes 29 stable producing rows. Only the helper's explicit per-call query/
authorization identities and evaluation/latency timing are excluded; all remain
raw and bound to their producing calls. Packet/evidence/administration pins, body
bytes, coordinates, order, scores, omissions and safe history facts remain compared.
The fixed, exclusively created directory fixture avoids source-identity normalization.

Five rehashed controls per run fail their intended semantic detector:

| Mutation | Detector |
|---|---|
| Wrong explicit-false empty-call expected exit | `scheduled-empty-expectation` |
| Removing the explicit empty flag from request/argv | `scheduled-native-request` |
| Changing the inline association request/type | `scheduled-request-bytes` |
| Changing recorded predecessor/successor suppression facts | `history-suppression-binding` |
| Changing selected support with plausible content hashes/coordinates | `evidence-content-binding` |

The deliberately invalid archives and exact receipts are retained under each
`controls` directory. Each successful capture retains all raw argv/stdin/stdout/
stderr/exits, argument/file bytes, strict typed request/response populations, MCP
send completion and producing pins. These two captures had no unexpected failed
live attempt or retry; expected refusals are retained, not filtered out. Partial
attempt persistence is a safeguard, not an exercised timeout/rollback claim.

The original [producer/protocol](../../association-supersession) and
[observations](../2026-11-02-association-supersession) remain byte-identical at
`360026649d73810115a604f36f9b6df6b251a657`. They establish their nonempty-file
workflow, not the corrected empty boundary. Development smoke is not relabelled as
public evidence, and no cross-pin equality is claimed.

## Reproduce

From this benchmark repository's root, use Git, Go1.25 or newer and Python3's
standard library. The recorded binary used Go1.27.1. Run captures sequentially;
the fixed directory fixture must not already exist. These commands create fresh
stores and use the exact public product pin:

```sh
work=$(mktemp -d /tmp/mousa-composed-v2.XXXXXX)
git clone https://github.com/graydeon/mousa.git "$work/product"
git -C "$work/product" checkout --detach b5730d6b311985b730765598baf24b972430bc10
(cd "$work/product" && CGO_ENABLED=0 GOAMD64=v1 go build -o "$work/mousa" ./cmd/mousa)
protocol=association-supersession-v2/protocol.json
python3 association-supersession-v2/capture.py capture --protocol "$protocol" \
  --mousa "$work/mousa" --product-source "$work/product" --output "$work/first"
python3 association-supersession-v2/capture.py capture --protocol "$protocol" \
  --mousa "$work/mousa" --product-source "$work/product" --output "$work/second"
for run in first second; do
  python3 association-supersession-v2/capture.py verify --protocol "$protocol" \
    --capture "$work/$run/capture.json.gz"
  python3 association-supersession-v2/capture.py controls --protocol "$protocol" \
    --capture "$work/$run/capture.json.gz" --output "$work/$run/controls"
done
python3 association-supersession-v2/capture.py compare --protocol "$protocol" \
  --capture "$work/first/capture.json.gz" --other "$work/second/capture.json.gz"
```

The retained captures, separate reproduction, offline replays, controls and comparison
above passed with these same pinned interfaces. `python3 tools/verify_results.py`
checks the registered archive membership and hashes; semantic replay is separate.
The archive's protocol copy is byte-identical to the producer's frozen protocol.

## Limits

These are bounded synthetic protocol/compatibility/selection observations, not
semantic sufficiency, authenticated authorship, temporal truth, universal absence,
model quality, performance or model-driven acceptance. Ordinary clients do not
establish internal snapshot/rollback/hostile-canonical behavior; those remain
product-local tests. No SQL, product imports, model calls, tokenizer requirement,
binary/database export, historical rewrite or startup-study collection is involved.
Token triples and vector/hybrid associations remain unsupported.

The product's three former14m race-gate timeouts remain recorded separately.
Its final source-bound check uses an explicit25m per-package race budget and30m
outer allowance, with unchanged coverage, fixtures, assertions and race/checkptr.
That is test execution time, not a product performance acceptance threshold.
