# MCP historical supersession inspection

This standalone Python standard-library client captures native commands, real stdio MCP traffic and logical SQLite state from synthetic stores. It imports no Mousa package and does not mock responses. It targets the corrected [PR75](https://github.com/graydeon/mousa/pull/75) public commit `5ffa0286b35ecf84b36abe53d029a78075c02b86`, tree `c73fb12a9ccdc6df65ad998a3039255a43dc6ad1`. Publication of that commit is not a claim that the PR is merged.

## Protocol and boundaries

`protocol.json` fixes the ordered commands, request arguments, expected errors, permitted state changes, discovery definitions, fixture hashes and stable historical selections. Discovery negotiates MCP `2025-11-25`. The query-only baseline is product commit `eb18d775f6e86ef18dd4bba5eaefdde003b2cd4d`; its native build and actual discovery receipt are in `baseline-discovery.json`. Only the trail input/result schemas grow. Query, sync and status definitions compare unchanged as complete JSON values. Schema validation rejects undeclared result fields and requires exactly one matching `oneOf` branch.

The schedule covers both `original` and `exact-v1` packing policies:

- Authorized v4 active consultation, verified no history, deactivation and recorded unconsulted denial. True returns the producing trail's stored member, also compared with native inspection. Omitted and false retain filtered historical properties.
- Inspection after replacement, deactivation, content changes and restart. Producing trail, request, decision and packet identities remain bound to the original native query. Only fresh authorization wrapper fields and verified live `indexed_now` values may differ within a historical comparison. Unknown response fields are not discarded.
- Native-created v1, v2 and v3 trails. The v3 fixture uses the native JSONL sync and strict association declaration interface, not manufactured record bytes. Association projection and producing identities are checked; no input mode fabricates a supersession member.
- Successful fresh authorization denial, including damaged history. It releases no historical payload. One fresh decision and its exact input children are allowed; the returned authorization ID, source, outcome and reasons must identify those rows. Access changes are separate commands.
- Unknown and foreign IDs, rejected null/string/numeric/duplicate/unknown/non-object arguments, and sync/status rejection of the option. The invalid raw framing case is a process framing observation, not a reachable tool-argument error.
- Canonically source-bound v4 candidate, segment, activation, declaration and record damage, plus own/foreign orphaned decision parents and unknown IDs. The already-open scoped orphan boundary is `not_found`, not `integrity`: the parent was needed to establish source ownership. Fresh-open startup rejects that damage as integrity. Denial precedes historical lookup. All damage is out-of-band, FK-disabled and confined to independent synthetic stores.

Every command has before/after SQLite snapshots. The read transaction observes committed WAL state and retains the schema, user version, column order and every row of every table, with SQLite value types preserved. Inspection checks remove only the response-bound decision and its verified input children before comparing the complete remaining state. This is a logical committed-state check, not proof of general physical integrity or a claim based on the main database file's byte hash. Live-open refusal, fresh-open startup refusal and error-transaction noncommit are distinct observations.

Generated requests are bound to the schedule both as recorded metadata and as actual wire frames. Comparisons preserve JSON types, so `true` is not `1` and `false` is not `0`. Repeated generated-frame keys are rejected recursively. Intentional malformed argument frames retain exact bytes. Raw response bytes, notifications, native input/output, process exits and command state are retained.

## Build and reproduce

Use Linux, Python 3 with its SQLite module, Git and Go `1.27.1`. Build from a clean anonymous checkout. The frozen binary receipt uses the default Go VCS stamping; keep the checkout clean and use the exact source commit and toolchain.

```sh
git clone https://github.com/graydeon/mousa.git /tmp/mousa-inspection-source
git -C /tmp/mousa-inspection-source checkout --detach 5ffa0286b35ecf84b36abe53d029a78075c02b86
(cd /tmp/mousa-inspection-source && GOWORK=off CGO_ENABLED=0 go build -trimpath -o /tmp/mousa-inspection ./cmd/mousa)
sha256sum /tmp/mousa-inspection
python3 -m unittest discover -s mcp-trail-supersession -p 'test_*.py' -v
python3 mcp-trail-supersession/run.py capture --binary /tmp/mousa-inspection --work /tmp/inspection-store-a --output /tmp/inspection-a.json.gz
python3 mcp-trail-supersession/run.py capture --binary /tmp/mousa-inspection --work /tmp/inspection-store-b --output /tmp/inspection-b.json.gz
python3 mcp-trail-supersession/run.py replay --output /tmp/inspection-a.json.gz
python3 mcp-trail-supersession/run.py replay --output /tmp/inspection-b.json.gz
python3 mcp-trail-supersession/compare.py /tmp/inspection-a.json.gz /tmp/inspection-b.json.gz
python3 mcp-trail-supersession/controls.py --capture /tmp/inspection-a.json.gz --output /tmp/inspection-controls
```

Each work/control directory must not already exist. The executable must match SHA-256 `0bae5af810a4b6a6821724f6e7b49441e8f016a71df385581d827a4398455988`; the runner refuses a different binary rather than silently relabeling a new build as this observation. `build.json` records the clean product head/tree, separate capture-time companion head/tree, Go version, build arguments, environment, exit and output digests. A different platform/toolchain requires separately pinned evidence, not an edit to these historical receipts.

The preparation-only `prepare.py` copy is pinned to companion commit `2f419c47be796f6e647997e120fe5a364351e9ce`. `preparation.json` records canonical identity checks against native output. The observation runner uses checked-in bytes and verifies native declaration/activation output; it does not use that codec to manufacture tool replies or legacy trails.

## Archive and controls

The [published observations](../results/2026-10-13-mcp-trail-supersession) contain two independent frozen captures, command receipts, a real forbidden-write capture, pilot records and a member manifest. Each capture is a lossless gzip-compressed indexed object graph. Every object/array node has a SHA-256 digest; the loader verifies all nodes, reachability and embedded raw-stream hashes. Deduplication reduces repeated full-database snapshots without dropping rows, assertions or traffic. `run.load_capture(path)` reconstructs the complete JSON observation with `records`, `assertions` and `selections`.

Mutated control archives are regenerated instead of shipping a full duplicate for each mutation. `controls.py` breaks shared object aliases, changes one targeted value, rehashes streams and every archive member, then invokes the offline replay command. Its receipts preserve the actual exit and named semantic, request-binding, schema or recorded-assertion detector. A stale member hash is not the intended failure. Ordinary round-trip and object-key-order controls must pass. Numeric boolean substitutions and coherent metadata-plus-wire rewriting must fail.

`compare.py` separately compares the two captures' stable selections and all denied wrappers. It excludes only the fresh authorization ID and echoed requested trail ID from denial comparisons, retaining every other field and value. This checks that own, foreign, unknown and damaged-history denial observations do not disclose different existence information.

The real forbidden-write control is separate from these mutations:

```sh
python3 mcp-trail-supersession/run.py capture --binary /tmp/mousa-inspection --work /tmp/inspection-forbidden-store --output /tmp/inspection-forbidden.json.gz --forbidden-write
python3 mcp-trail-supersession/run.py replay --output /tmp/inspection-forbidden.json.gz
```

Both commands must exit 1 at an inspection's `only-bound-authorization-write` detector. The capture actually commits an extra table and row inside that one inspection bracket. Do not use this option on a real store.

## Limits

These are synthetic client-boundary observations. They do not establish semantic truth, retrieval quality, performance, authentication, production-scale behavior or native-host acceptance. Fresh authorization writes are expected and are not repair. The archive verifies committed logical state, not every physical SQLite failure mode. The unscoped internal canonical-reader regression belongs to the product tests; this independent client observes native startup verification and live-open MCP separately without importing product internals. Earlier query/native archives retain their original pins, counts and conclusions.
