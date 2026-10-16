# MCP historical inspection observations — 2026-10-13

Two independent fresh-store captures target Mousa public commit `5ffa0286b35ecf84b36abe53d029a78075c02b86`, tree `c73fb12a9ccdc6df65ad998a3039255a43dc6ad1` ([PR75](https://github.com/graydeon/mousa/pull/75)). The product was built from a clean anonymous checkout with Go `1.27.1`, `GOWORK=off`, `CGO_ENABLED=0` and `go build -trimpath`. Its executable SHA-256 is `0bae5af810a4b6a6821724f6e7b49441e8f016a71df385581d827a4398455988`. Build output and source receipts are in the [protocol surface](../../mcp-trail-supersession/build.json).

The companion capture-time HEAD was `2f419c47be796f6e647997e120fe5a364351e9ce`, tree `422fe7106535c6646dfea2eb69db3adea9b52fbd`. This is separate from the later evidence commit containing this directory. Runner and fixture hashes are pinned; neither capture is relabeled as a run of that later companion commit.

## Results

| Observation | Steps | Assertions | Historical selections | Command exit |
| --- | ---: | ---: | ---: | ---: |
| Frozen capture A | 268 | 5,314 | 60 | 0 |
| Frozen capture B | 268 | 5,314 | 60 | 0 |
| Offline replay A | 268 | 5,314 | 60 | 0 |
| Offline replay B | 268 | 5,314 | 60 | 0 |

Counts come from command receipts, not from independent quality cases. Each schedule includes 93 native commands, 135 JSON-RPC requests, 10 notifications, 10 server starts/stops, 3 raw boundary frames and 7 isolated damage operations. It includes 60 successful historical inspections, 18 successful denied inspections and 39 expected tool-error calls. Raw framing failure is separate from tool argument rejection.

`comparison.json` records exact equality of all 60 stable historical selections between stores. Producing identities are checked against each capture's own native query and stored trail before only the declared fresh identities are excluded from the cross-store comparison. The supplemental `compare.py` check also compares all 18 denied wrappers in each store, excluding only the new authorization ID and echoed requested trail ID. Own, foreign, unknown and damaged-history denial responses expose the same remaining fields and values. This supplemental comparison is reported separately from the frozen per-capture assertion count.

The real forbidden-write capture and its offline replay both exit 1 at `orphan-deny-unknown-true:only-bound-authorization-write`. An extra table and row are actually committed inside that one inspection bracket. This is a detector control, not a product failure. `capture-commands.json` and `replay-commands.json` preserve actual outputs and exits.

## What is observed

The frozen matrix checks v4 active, no-history, deactivation and recorded unconsulted-denial members under both packing policies, including reads after later lifecycle changes and restart. True returns the producing record's member. Omitted and false retain filtered historical properties. Native-created v1/v2/v3 trails fabricate no member; the v3 association projection is checked through the real native declaration/query interface.

Successful authorization denial writes exactly the returned decision and its required input children. Every existing row and all other tables remain unchanged. Unknown/foreign/integrity tool errors commit no changes. An already-open source-scoped inspector masks orphaned decision parents as `not_found`; fresh-open native startup rejects the damaged store as integrity. These boundaries are not a blanket write-free-failure claim or a proposed storage change.

Discovery compares the complete unchanged query/sync/status definitions against a separately built query-only baseline. Tool replies are checked against discovered closed schemas. Request metadata and wire frames are bound with JSON-type-preserving equality, recursive duplicate-key detection and exact bytes for intentional malformed frames. `oneOf` requires exactly one branch. Identity fields are lowercase 64-hex with the discovered nullability.

## Replay and controls

From the repository root:

```sh
python3 tools/verify_results.py
python3 mcp-trail-supersession/run.py replay --output results/2026-10-13-mcp-trail-supersession/capture-a.json.gz
python3 mcp-trail-supersession/run.py replay --output results/2026-10-13-mcp-trail-supersession/capture-b.json.gz
python3 mcp-trail-supersession/compare.py results/2026-10-13-mcp-trail-supersession/capture-a.json.gz results/2026-10-13-mcp-trail-supersession/capture-b.json.gz
python3 mcp-trail-supersession/controls.py --capture results/2026-10-13-mcp-trail-supersession/capture-a.json.gz --output /tmp/inspection-regenerated-controls
```

The control output directory must be new. `controls.json` lists each actual exit and detector for contradictory inputs, numeric boolean substitutes, coherent metadata-and-wire rewriting, repeated generated keys, historical member/identity/association mutations, undeclared output fields, wrong v3-member and denial-write expectations, a recorded false assertion and changed intentional raw bytes. Passing round-trip and object-key-order controls remain included. Mutated archives are regenerated and fully rehashed; stale hashes are not the intended detectors. Fresh capture and real forbidden-write instructions are in the [runner guide](../../mcp-trail-supersession).

`manifest.json` registers every file here. The shared archive verifier remains unchanged and checks those outer file hashes. The standalone replay additionally verifies every indexed archive node and raw stream, then reruns the actual semantic assertions. Full logical SQLite snapshots include committed WAL changes; no claim rests on a main-file byte hash.

## Pilot and superseded observations

`pilot/` contains the final ordinary pilot's source, original protocol, fixtures, observation and replay/control receipts. It replays independently:

```sh
python3 results/2026-10-13-mcp-trail-supersession/pilot/run.py replay --output results/2026-10-13-mcp-trail-supersession/pilot/observation.json.gz
```

`development.json` distinguishes earlier failures. The first framing attempt waited on an incomplete opening-object frame; `framing-pilot.json` records actual EOF-on-close versus invalid-character behavior. The non-object argument pilot incorrectly expected a JSON-RPC error; the product returned its `invalid_arguments` tool envelope. Its full failed observation is retained losslessly in `pilot-nonobject-failure.json.gz`, with the original digest and failure receipt. It predates the frozen runner and is archival evidence, not final-protocol acceptance.

`superseded-frozen.json.xz` retains the first frozen source surface, two passing captures and an incomplete forbidden-write control. That control inserted an extra table too early: the inspection invariant failed correctly, but subsequent native startup rejected the changed schema and prevented schedule completion. The corrected protocol identifies the final successful denied-inspection bracket; it was piloted before the final pair was captured. The normal command schedule and historical expectations did not change. None of those earlier captures is relabeled as the final pair.

All compressed observations use the same lossless indexed object-graph format. To inspect a failed gzip observation, import `run.py` from `mcp-trail-supersession` and call `load_capture(Path(...))`; it validates node/stream hashes and reconstructs ordinary JSON values. The superseded bundle uses XZ compression to reduce transport size without changing any indexed graph bytes. Convert that container before loading it:

```sh
python3 -c "import gzip,lzma,pathlib; p=pathlib.Path('results/2026-10-13-mcp-trail-supersession/superseded-frozen.json.xz'); pathlib.Path('/tmp/superseded-frozen.json.gz').write_bytes(gzip.compress(lzma.decompress(p.read_bytes()),mtime=0))"
```

`compression.json` records the original/container/expanded digests and byte-equality check. The reconstructed bundle has `surface` (relative path to original file text), `captures` (complete expanded observations) and `commands`. Its source and captures can be reconstructed in a fresh directory with `write_capture` for independent old-protocol replay. There are no links, external archive members or product-package imports. Regenerated control copies avoid duplicating large unchanged snapshots in every published mutation.

## Limits

These observations concern synthetic native/stdio client behavior and committed logical SQLite state. They do not measure semantic truth, retrieval quality, performance, authentication, production-scale operation or native-host acceptance. They do not establish general physical database integrity. Internal unscoped canonical-reader coverage remains a separate product regression; this independent runner observes live-open MCP and fresh-open native startup without importing product internals. Product PR publication is not merge or independent review approval. Earlier query/native archives, their pins and their counts are unchanged.
