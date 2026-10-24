# Lexical supersession with measured token packing

The [paired public-head observations](../results/2026-10-24-lexical-token-supersession)
retain both captures, reference token IDs/counts, stream bytes and mutation receipts.
This small synthetic client capture combines exact pinned-predecessor withholding
with whole-context token budgets. It uses native directory/JSONL queries and
configured JSONL stdio MCP, with both packers. Source preparation uses normal
sync/export and native declaration/activation commands; the client never imports
product packages or opens SQLite.

## Reproduce

Use the exact public product head and tree in the paired result's `build.json`.
Build that clean checkout with Go 1.25 or newer:

```sh
GOWORK=off CGO_ENABLED=0 go build -o "$BINARY" ./cmd/mousa
```

Prepare an external isolated Python environment with official `tiktoken==0.12.0`
and the `o200k_base` vocabulary cache as documented in Mousa's usage guide. Both
product and reference counting use ordinary-text encoding. Capture/replay refuses
to download a missing cache. Run the driver with the prepared venv interpreter;
preserve its path rather than resolving its symlink outside the venv.

```sh
"$TOKEN_PY" token-supersession/capture.py capture \
  --mousa "$BINARY" --product-source "$PRODUCT" --product-head "$PUBLIC_HEAD" \
  --python "$TOKEN_PY" --cache "$TOKEN_CACHE" --output /tmp/combined-capture
"$TOKEN_PY" token-supersession/capture.py verify \
  --cache "$TOKEN_CACHE" --output /tmp/combined-capture
"$TOKEN_PY" token-supersession/capture.py controls \
  --cache "$TOKEN_CACHE" --output /tmp/combined-capture
```

Repeat `capture` with another absent output path for a separate fresh-store
reproduction. The schedule is regenerated from previously observed responses;
every native argument/input and JSON-RPC request is checked against that schedule.
The existing wire helpers retain exact base64 output/response bytes, byte sizes,
hashes and process exits. Native input is exact UTF-8 text. `BINARY`, `STORE`,
`DIRECTORY`, `TOKEN_PY` and `TOKEN_CACHE` are explicit runtime operand bindings,
not shell commands. Directory source/header identities vary with the temporary
absolute path; reference counts are rederived within each run, not frozen across
unrelated paths. JSONL uses one fixed source alias and fixture.

The capture records no-history and active queries, native normal/recount history,
whole-rendering exact/one-short/reservation boundaries, byte-equal withheld versus
retained candidates, independent MCP history opt-ins, all-withheld empty context
with the successor withdrawn, explicit deactivation and old producing history
after current selected text is retired. Positive withheld size/rank remains
inspectable. Rendering is reconstructed from exported pins and fixture bytes,
then independently counted and hashed; a withheld duplicate cannot substitute
for the actual retained twin's header.

The final schedule additionally syncs 65 × 4096-byte predecessor segments through
native JSONL administration. Ordinary query responses supply revision pins without
using vector export for this oversized source. Both packers then return
empty or small-survivor contexts through native/MCP, preserving all 65 recorded
withheld identities, positive sizes/ranks and null proposed counts. Native normal
history/recount and MCP recorded history check the producing selection after reopen.
Two equivalent nonsuppressed token requests must fail at the unchanged aggregate
bound, with exit 1, empty stdout and the exact expected error.

`controls` regenerates coherently rehashed changed-request, wrong-withheld-count
and wrong-historical-selection copies, synchronizes text/structured envelopes,
and requires each named detector. Only compact control receipts are archived;
mutated copies are reproducible from the stored capture, not separately retained.
Replay checks internal consistency, not proof against a malicious producer.

## Limits

Counts cover complete returned context, including headers/separators, not JSON
or unknown application/model framing. Recorded historical counts are producing
observations; MCP does not recount. Native recount needs retained selected text.
The fixture is ordinary single-source public administration/client behavior;
arbitrary graph ancestry, lifecycle rejection filtering, canonical corruption,
transaction ordering and process failure/cancellation/reaping belong to separate
product-local tests. They are not claimed capture coverage. Vector/hybrid and
association supersession remain unsupported. No model, semantic-quality,
performance or full-window-safety claim follows. Existing archives are unchanged.
