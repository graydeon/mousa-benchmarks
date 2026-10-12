# MCP query supersession capture protocol

Status: pilot, capture and fresh-store reproduction pass against the public product pin
recorded in the result directory
[`results/2026-10-12-mcp-query-supersession-strict-binding`](../results/2026-10-12-mcp-query-supersession-strict-binding).
That pin is the head of product PR 69 and is not claimed merged or available on main. The two
earlier directories, [`results/2026-10-12-mcp-query-supersession`](../results/2026-10-12-mcp-query-supersession)
and [`results/2026-10-11-mcp-query-supersession`](../results/2026-10-11-mcp-query-supersession),
are retained unchanged with dated notes: the first compared recorded requests with their own
match metadata only, and both compared values with Python object equality and parsed generated
frames with the standard decoder, so a nested `true` rewritten as `1` compared equal and a
repeated object key kept its last value. Each of those archives is replayed with the runner copy
inside it.

`run.py` uses Python 3.9 or later and the standard library only. It speaks
newline-delimited JSON-RPC 2.0 over stdio to an explicitly supplied Mousa executable -
the transport the published local stdio MCP interface uses - drives the real
`initialize` / `notifications/initialized` / `tools/list` / `tools/call` lifecycle in
separate processes, and records the exact wire bytes. It builds no product code, imports
no product internals, contains no product identity codec and uses no SDK test utility or
mock. The executable is the observation engine.

## Boundary and cases

Each scenario drives one stdio server process against one disposable HTTP-free store.
Preparation and lifecycle transitions use the published native CLI (`sync`,
`supersession declaration put`, `supersession activation put`, `access`), are recorded
with their actual argv, stdin, stdout, stderr, exit and complete logical SQLite
fingerprint, and stay separate from the MCP observations they prepare.

| Scenario | What is observed |
|---|---|
| `fresh-store` | Starting the server against an absent store path creates and migrates it before any call; a rejected-input call changes no table |
| `no-history` | Discovery; omitted and explicit `false` are stable-equal and omit the count; `true` reports `0`, keeps the default packet and evidence, and adds `packing_policy`; `mousa_status` still works; the strict input rejections; `supersession` on sync/status/trail is rejected; `mousa_trail` inspects the recorded v4 trail with no supersession member and no evidence text |
| `active-original` | With an active declaration: omitted/`false` keep the default property set and release the predecessor; `true` withholds exactly the pinned predecessor, reports `1`, releases only the other two items, and reports `packing_policy: original`; a 28-byte budget shows the withheld candidate consumes no budget; the filtered trail keeps the recorded selection; a restart repeats the stable selection with fresh identities |
| `active-exact-v1` | The same calls under `exact-v1`: the byte-equal survivor is released while the withheld predecessor is not treated as a duplicate seed, `duplicate_omitted` is `0` for the opted call and `1` for the default call, and the restart is stable |
| `deactivated` | An activation selecting no declaration releases every candidate, reports `0`, and keeps the default packet |
| `successor-withdrawn` | A withdrawn successor revision does not re-enable the predecessor and manufactures no replacement evidence |
| `denied` | A source-scoped deny binding leaves an opted-in call with empty evidence, count `0`, no administrative identity and a denied trail with no historical payload |
| `damaged-events` | Deleting the activation event rows under a surviving projection makes the opted-in call fail closed with `integrity` and commit nothing, while the default query keeps working |
| `malformed` | A line carrying data after the JSON-RPC object terminates the session with a bounded diagnostic on stderr and no response |

Stable comparisons exclude the per-call identities and timing: `request_id`,
`decision_id`, `trail_id`, `evaluated_at_usec` and `latency_micros` on a query result,
`authorization_decision_id` and `trail_id` on a trail inspection wrapper, and the recorded
`id`, `request_id` and `decision_id` inside that wrapper's `historical` member, which
identify the trail this run recorded. Every other property is compared, including packet
identity, released text and coordinates, digests, selection flags, packing policy, counts,
authorization outcome and the recorded candidates. Raw values of the excluded fields are
retained and validated against the run's own call: the inspected trail identity, its
recorded request, decision and packet identities and the recorded expression, budget and
selection are all asserted equal to the query that produced them.

The tool-level trailing-data rule of `decodeMCPArguments` is unreachable through a valid
JSON-RPC frame. The runner observes the framing-level rejection instead and records that
difference rather than claiming the decoder case.

## Discovery and the pre-query baseline

Every session records `tools/list`. The runner compares the `mousa_sync`, `mousa_status`
and `mousa_trail` definitions, as complete parsed JSON definitions, with the frozen
pre-query baseline in `protocol.json`, which was captured from a second binary built at the
accepted pre-query public commit, and it compares the `mousa_query` definition against the
same baseline through a structural delta that must equal the frozen delta (one added input
property `supersession` and one added declared result property `supersession_excluded`,
nothing removed or changed). Equality here is over the parsed definitions, not over the raw
response bytes: each session's exact `tools/list` request and response bytes are recorded
and retained as receipts, and they differ from the separate baseline session's bytes. The
raw baseline receipt is published separately in the result directory as
`baseline-discovery.json`.

## Fixture preparation and identity construction

`protocol.json` freezes every input member's SHA-256, the source identity, one revision
identity per item (observation, artifact, representation and segment), the declaration
identity and both activation identities. The synthetic JSONL items, declaration and
activation records are prepared by `prepare.py`, which is *preparation, not evidence*:
it derives the canonical identities with independent standard-library code and then
verifies them against the product itself - native `sync` followed by read-only SQLite
row checks, plus byte-for-byte comparison of the `supersession declaration put` and
`activation put` canonical output. `run.py` never imports it and contains no identity
derivation; it compares observed values with the frozen pins.

The fixture is a three-item source: `predecessor` and `duplicate` carry byte-equal text
and `successor` a different text. The active declaration pins the predecessor
representation to the successor representation. The two byte-equal items are the
survivor case for `exact-v1`; which of them ranks first is an observed result, frozen
only from a passing pilot.

## Fingerprints and receipts

Every native command, every MCP call and every rejected input has its own complete
logical SQLite fingerprint immediately before and after: schema, every table and column,
every row and committed WAL-visible state, hashed in one read snapshot. Reads and
rejections must leave every table unchanged; queries and trail inspections may change
only the authorization-audit and trail tables. This is logical state evidence, not a
main-file hash or a physical sidecar-integrity claim, and it does not detect a transient
write rolled back before the after snapshot.

Each step records symbolic argv, complete request and response bytes with SHA-256,
base64 and text, the actual exit and the step's own fingerprints. Every step also carries
the schedule it was produced from, and each recorded receipt is asserted back against that
schedule: a prepared command's argv and stdin, a protocol or notification frame's JSON-RPC
version, method and parameters, a tool call's `tools/call` method, tool name and argument
object, and the response identity against the request that produced it. A generated frame is
parsed with a strict decoder whose object hook reports a repeated key at any depth, so a
duplicated argument, tool name or top-level key cannot disappear into the last of its values,
and its top-level keys must be exactly `jsonrpc`, `id`, `method` and `params` while its
per-call integer identity stays an integer. A frame the schedule spelled out as raw bytes,
including the duplicate-key and trailing-data boundaries, is compared as those exact bytes
rather than reparsed, so parsing cannot erase the boundary under test. Comparisons that decide
whether a replay is accepted - every reconstructed assertion, the assertion list and the
selections - are made over canonical JSON, so a nested `true` is not `1`, `false` is not `0`,
`4096` is not `4096.0`, `null` is not `"null"`, a container type is not another, and object
property order stays irrelevant. `verify` re-checks membership, digests, the committed runner
and protocol bytes, the input hashes, the product pin, the recorded companion head and tree,
stream integrity and the regenerated assertions: it replays the recorded step stream offline
and requires the regenerated assertions and selections to equal the recorded ones and, for a
capture, all assertions to pass. Assertions record the observed value, the expected value and
the outcome; a false boolean stays false and fails. Omitting or editing an assertion, changing a
command, rewriting a recorded request into a neighbouring operation, changing a recorded JSON
type, repeating a key inside a generated frame, damaging the build receipt or forging a
successful response is rejected even when a negative control recomputes the member manifest.

This is integrity and internal-consistency checking. It is not a signature, and it does
not stop a party from fabricating an entire coherent capture and replacing its trusted
runner and protocol.

## Publication and reproduction sequence

Use a clean product checkout at the recorded public head and tree, its built executable,
and a clean committed companion checkout. Output paths stay outside both checkouts.

```sh
RUNNER=mcp-query-supersession/run.py
python3 "$RUNNER" pilot --source "$PRODUCT" --binary "$BINARY" --pin "$PIN" \
  --output /tmp/mcp-pilot
python3 "$RUNNER" verify /tmp/mcp-pilot
python3 "$RUNNER" freeze /tmp/mcp-pilot --output /tmp/mcp-expectations.json
python3 "$RUNNER" capture --source "$PRODUCT" --binary "$BINARY" --pin "$PIN" \
  --expectations mcp-query-supersession/expectations.json --output /tmp/mcp-capture
python3 "$RUNNER" verify /tmp/mcp-capture
python3 "$RUNNER" capture --source "$PRODUCT" --binary "$BINARY" --pin "$PIN" \
  --expectations mcp-query-supersession/expectations.json --output /tmp/mcp-reproduction
python3 "$RUNNER" verify /tmp/mcp-reproduction
python3 "$RUNNER" negative-controls /tmp/mcp-capture --output /tmp/mcp-negatives
python3 "$RUNNER" self-check --output /tmp/mcp-self-check.json
python3 "$RUNNER" forbidden-write --source "$PRODUCT" --binary "$BINARY" --pin "$PIN" \
  --output /tmp/mcp-forbidden
```

Expected exits are 0 for a passing pilot, capture, reproduction, verify, freeze,
negative-controls and self-check run, 1 for the injected forbidden-write capture, and 2 when
verifying that failed capture or violating a precondition. `forbidden-write` runs the same
schedule with one external table injection inside one read-only bracket, so the bracket's
`unchanged-all-tables` assertion is false; the injected table is dropped again afterwards
so a later startup failure cannot become the detector's failure cause. `negative-controls`
produces deliberately mutated copies - a damaged frozen input, a wrong count expectation,
a wrong default property set, an inverted assertion, an omitted assertion, an undeclared
response field, a forged fingerprint, a fabricated success after damage, a failed build
receipt, a damaged build stream and ten request rewrites - and requires `verify` to reject
each one for its named reason. The ten rewrites are a flipped boolean, `true` as `1`, `false`
as `0`, `4096` as `4096.0`, a repeated `supersession` key inside `params.arguments`, a
repeated top-level `method` key, a replaced query, a replaced tool name, a replaced method
and a rewritten raw boundary frame. Each request rewrite leaves the scheduled match metadata,
the observed response and every other receipt as captured and must be rejected by the
binding assertion recorded as its expected detector, which is checked as an exact entry of
the reported difference list rather than as a substring.
`self-check` runs the runner's own focused standard-library regressions - exactly one
matching `oneOf` branch, the closed-object and type rules, the canonical-JSON type cases and
a repeated key reported at the top level and inside a nested argument object - and exits 2 on
a failure.

`package` assembles the published result directory from the capture directories plus the
preparation, baseline, controller-command and self-check receipts; it stores the four
observations as complete archives and the control receipt list, and refuses a control list
that does not name every control exactly once or records any of them as accepted. The mutated
copies themselves are not stored: each is a full copy of one capture, twenty-four of them
measure above the publication bound, and `negative-controls` regenerates every copy from the
stored capture deterministically. `manifest` rewrites one archive directory's member manifest.
The result directory's `archive-members.json` identifies every compressed member and
`manifest.json` every outer file.

For offline replay of a published archive, extract it into a new directory and pass the
extracted capture directory to `verify`.

## Limits

- Synthetic client-boundary behavior only: no semantic truth, retrieval quality, ranking
  quality, latency, throughput, memory, authentication or native-host acceptance.
- The pre-query baseline is a build of a different public commit used only to compare
  discovered definitions; it is never presented as an observation of the tested pin.
- Opted-in trail inspection is not implemented and is not claimed; the runner observes
  the argument being rejected and the native-only member being filtered.
- Corrupting a store while the server holds it open proves a call-level refusal and no
  commit, not transaction rollback of an in-flight write; concurrency and physical
  store-file integrity remain product-local evidence.
- Matching source and binary pins do not prove a reproducible build on another toolchain.
