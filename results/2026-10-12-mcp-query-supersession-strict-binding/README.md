# MCP query supersession acceptance — strict JSON binding

Synthetic stdio MCP client acceptance against [Mousa PR
69](https://github.com/graydeon/mousa/pull/69), not a main-branch, native-CLI or performance
result. Product public commit `7ae0d8768e7cd203c48478412b493e1255c97b11`, tree
`2b8b14f76e0907f3ca3fd5dc8c33934567e61d14`. That commit implements the optional `supersession`
query input and the declared `supersession_excluded` result count on the existing `mousa_query`
tool; it is not claimed merged or available on main.

This is the third revision of this capture. The first,
[`results/2026-10-11-mcp-query-supersession`](../2026-10-11-mcp-query-supersession), and the
second, [`results/2026-10-12-mcp-query-supersession`](../2026-10-12-mcp-query-supersession), are
retained unchanged with dated notes. Both revisions compared a recorded value with its scheduled
value using Python object equality, which treats a nested `true` and `1` as equal, and both parsed
a generated frame with the standard decoder, which keeps the last of two identical object keys and
reports nothing: in either revision a receipt that expressed a product-rejected input still
verified at exit 0. This revision parses every generated frame with a strict decoder that reports a
repeated key at any depth, asserts the frame's exact top-level key set, and compares every
reconstructed assertion and every selection as canonical JSON, so boolean, number, string, null,
array and object stay distinct while object property order stays irrelevant. The 39 stable
selections and every frozen protocol byte are unchanged; the assertion counts are not.

The standalone [stdlib runner](../../mcp-query-supersession/run.py) imports no product internals,
contains no identity codec and drives the explicitly supplied executable over newline-delimited
JSON-RPC stdio in separate processes. The pilot documented here is the one that froze
`expectations.json`; it ran at committed companion head
`f69748f9b8e222e82737e5343a71a88a24a0bad5`, tree
`9a87f226cb24dbfca60b67edf6415b896c5dea1b`, and the frozen expectations were committed next. The
capture, the fresh independent-store reproduction and the forbidden-write control ran at committed
companion head `b1c00fb471dd282a9b46cc840dc69b9073d17190`, tree
`09a9f3072851744eef9540892302f9c34dc94236`, whose only change from the pilot's head is the frozen
expectations file itself; neither checkpoint is relabeled as the later publication commit.

## Observed results

| Check | Actual result |
|---|---|
| Passing pilot, complete replay and freeze | Exit 0; 2846 assertions, only actual observed packet/evidence/candidate selections frozen (39 cases) |
| Capture and fresh independent-store reproduction | Both exit 0; each contains 129 recorded steps - 40 `tools/call`, 21 protocol requests, 11 notifications, 11 server starts, 11 startup brackets, 11 server stops, 23 native preparation commands and one external damage statement - 2847 assertions, 0 failed assertions |
| Complete replay of both captures | Both exit 0 |
| Recorded request bound to the scheduled operation | 520 assertions carry a recorded frame or prepared command back to the schedule (126 more than the second revision, none removed: one exact top-level key set and one repeated-key report for each of the 63 generated frames) |
| Strict generated-frame binding | Every generated frame is parsed with a decoder that reports a repeated object key at any depth, so a duplicated argument, tool name or top-level key cannot disappear; its top-level keys must be exactly `jsonrpc`, `id`, `method` and `params`, and its integer request identity stays an integer |
| JSON types preserved in comparisons | Every reconstructed assertion, the assertion list, the selections and the discovery delta compare as canonical JSON, so nested `true` against `1`, `false` against `0`, `4096` against `4096.0`, `null` against `"null"` and a container against another container type are all differences; object property order remains irrelevant |
| Discovery | In every one of the 11 sessions the four tools are discovered; the `mousa_sync`, `mousa_status` and `mousa_trail` definitions are equal, as complete parsed JSON definitions, to the frozen pre-query baseline, and the `mousa_query` definition delta is exactly the two frozen additions with nothing removed or changed |
| Omitted versus explicit false | Stable-equal in every scenario: same result property set (20 keys), same packet, same released evidence, no `supersession_excluded`, no `packing_policy` |
| Opted-in with no activation history | `supersession_excluded` is `0`, `packing_policy` is `original`, all three items are released, and the packet identity equals the default query's |
| Active declaration, `original` packing | Withheld candidate is exactly the pinned predecessor, count `1`, only the other two items released; the same call under a 28-byte budget releases the byte-equal survivor and reports `budget_omitted: 0`, so the withheld text consumed no budget |
| Active declaration, `exact-v1` packing | Count `1`, `duplicate_omitted: 0` for the opted call against `1` for the default call at the same budget, and the byte-equal survivor is released: the withheld predecessor did not seed the duplicate set |
| `mousa_trail` on an opted-in query | Succeeds, reports the recorded selection and no `supersession` member, no evidence text and no `text` property; `supersession` on the argument is still `invalid_arguments` |
| Deactivation and withdrawn successor | Deactivation releases everything with count `0` and the default packet; a withdrawn successor revision still withholds the predecessor and manufactures no replacement evidence |
| Denied configured source | Empty evidence, `used_bytes` `0`, count `0`, `decision_outcome` `deny` with reason `policy_deny`, and no activation or declaration identity in the response; the recorded trail is denied with no historical payload |
| Damaged activation events under a surviving projection | The opted-in call fails closed with code `integrity` and message `current activation event is missing`, commits nothing and repairs nothing; the default query on the same store keeps working |
| Store-open boundary | Starting the server against an absent store path creates and migrates it before any call; a rejected-input call then changes no table |
| Strict input boundary | `null`, `"true"`, `1`, `0`, a repeated name, an unknown name alongside the opt-in and non-object arguments are all `invalid_arguments` with no `result`; `supersession` on `mousa_sync`, `mousa_status` and `mousa_trail` is rejected the same way |
| Restart | Repeating the opted-in call in a new process keeps the stable selection, packet, released evidence and counts with fresh request, decision and trail identities |
| Injected forbidden write | Capture exit 1; its only failed assertion is `no-history:status:unchanged-all-tables`; replay of that capture exits 2 |
| Twenty mutated captures plus a directly recorded false condition | Every control rejected for its named reason: damaged frozen input, wrong count expectation (`changed:active-original:query-opted:count`), wrong default property set (`changed:no-history:query-omitted:result-keys`), inverted assertion, omitted assertion, injected undeclared response field, forged read-bracket fingerprint (`changed:no-history:status:unchanged-all-tables`), a fabricated success where the damaged call must fail, a failed build receipt, a damaged build stream, and ten request rewrites |
| Request rewrites | Each of the ten rewrites keeps the scheduled match metadata, the observed response and every other receipt as captured, and each is rejected by its own binding assertion: a flipped `supersession` boolean, `supersession` `true` rewritten as `1`, `false` rewritten as `0`, and `budget_bytes` `4096` rewritten as `4096.0` by `changed:active-original:query-opted:request-params` or `changed:no-history:query-false:request-params`; a repeated `supersession` key inside `params.arguments` and a repeated top-level `method` key by `changed:active-original:query-opted:request-no-repeated-keys` and `changed:no-history:query-omitted:request-no-repeated-keys`; a replaced `query` by `changed:no-history:query-omitted:request-params`; a replaced tool name by `changed:no-history:status:request-params`; a replaced method by `changed:no-history:query-false:request-method`; and a rewritten raw duplicate-key frame by `changed:no-history:boundary-duplicate:request-scheduled-bytes` |
| Focused runner regressions | `self-check` exit 0 over 16 cases: one matching `oneOf` branch accepted, zero and two matching branches rejected for the `oneOf` reason, a boolean is not a number, a closed object still rejects an undeclared property, and the JSON cases pin `true` against `1`, `false` against `0`, `4096` against `4096.0`, `null` against `"null"`, an array against an object, order-irrelevant object properties, a nested type difference, and a repeated key reported at the top level, inside a nested argument object, and not reported for a clean frame |
| Published companion-tree reproduction | Repeat from the clean published tree as described below; the collection checkpoints above are the committed companion heads, not the published snapshot |

Each native command, MCP call and rejected input has its own complete logical SQLite fingerprint
before and after, including WAL-visible rows. Reads and rejections leave every table unchanged;
queries and trail inspections change only authorization-audit and trail tables; the external
damage statement is recorded with its own before/after state. The injected table is dropped again
after the measured violation so a later startup failure cannot become the detector's failure
cause.

Withheld candidates keep their accepted rank and canonical size in the recorded trail while being
absent from the released evidence, which reports no text for them. Expected packet, evidence and
candidate values were frozen only from a passing, replay-verified pilot; fresh request, decision
and trail identities and the recorded trail's own identities stay in each step receipt rather than
becoming cross-run goldens, and the runner asserts them against the call that produced them. The 39
stable selections are identical to both earlier revisions'; the per-run fingerprints, decision
identities and trail identities are not, by construction.

## Preparation and build provenance

`preparation-verification.json` is separate preparation evidence for this pin: one native sync of
the frozen items into a throwaway store, read back with a read-only SQLite connection and compared
with the independently derived protocol pins (observation, artifact, representation, segment and
active-item identities per item, plus the declaration readback, activation canonical bytes and the
verified activation projection). The helper that derives those identities is preparation only; the
client runner contains no identity derivation and never calls it.

`baseline-discovery.json` records the pre-query tool definitions: a second binary built from the
accepted pre-query public commit `015dc1aa9f054b4b809a5d893b023afc4e378ba1` (tree
`63a1dd4156644e29904365870b4568c4847e9478`, executable
`19f122f9ca29e3cb0de29bc87a3f7ebca89668b0cd8a456328eaa60858618cf4`) answering `initialize` and
`tools/list` on the same fixture, with its own sync, request and response bytes. Its three
unchanged tool definitions are equal to the tested build's as complete parsed JSON definitions; the
`mousa_query` delta is frozen in the protocol and asserted in every session rather than presented
as an observation of the tested binary. Those raw baseline bytes and every session's own raw
`tools/list` bytes are retained in their receipts; the comparison is over the parsed definitions.

`product-pin.json` records the actual public source/tree, successful build argv, streams,
`CGO_ENABLED=0`, `GOWORK=off` and `go version go1.27.1 linux/amd64`. Executable SHA-256:
`d41954a65181189df0bdc1bf6e906823e966dd9f309f429d9f964fecbe748235`. Build argv is
`go build -trimpath -buildvcs=false -o <binary> ./cmd/mousa`, run from `<product>`. The supplied
build receipt is preparation provenance, not a build performed by the runner.

Runner SHA-256: `3581de60daf0ec5f7ccf14ce65c40e09c351dbd48bd9f62fc60df65ceacf1fd1`.
Protocol SHA-256: `ab59640df705a0bb76f2e2897d3135f98150db8121d044e10121cba2747383df` (unchanged
from both earlier revisions; this revision adds no frozen protocol byte).
Frozen expectations SHA-256: `0745b5fc905dcece7fd841995f96cec763f4e1e36796a8062a1c2177d011bdfe`.

The runner's schema check is a documented subset: type, const, enum, pattern, numeric and length
bounds, `properties`, `required`, `additionalProperties`, `items` and `oneOf`, where `oneOf`
requires exactly one matching branch. Formats, `$ref`/`$defs`, `allOf`/`anyOf`/`not`,
`unevaluatedProperties`, `patternProperties` and dependencies are not implemented, and every schema
this build discovers is inline and needs only the supported subset. The envelope's own separate
payload-exclusive check is asserted independently of that subset. The strict frame parser is the
standard library's decoder with a repeated-key hook on every object; it is not a general JSON
dialect check and it rejects nothing a conforming encoder emits.

## Archive layout and replay

The archives contain regular files only, relative paths with no traversal, and complete member
identities in `archive-members.json` (4 archives, 46 members). `manifest.json` covers every outer
member except itself. Historical results and the shared verifier are unchanged.

- `capture.tar.gz`, `fresh-reproduction.tar.gz`, `pilot.tar.gz`: complete accepted observations,
  raw wire bytes, assertions, frozen fixtures and copied runner/protocol.
- `forbidden-write.tar.gz`: the complete controlled failure, including both control statements.
- `negative-controls.json`: the receipt for the directly recorded false condition and for the
  twenty mutated captures. Each entry names the control, the verification reason that rejected it
  and, for the ten request rewrites, the binding assertion that had to be the one to reject it.
  The mutated copies themselves are not stored: each is a full copy of one capture, storing
  twenty-four of them measures above the publication bound this repository is held to, so the
  stored capture plus this list is the record and the runner regenerates every copy from it
  deterministically. The command below reproduces all twenty-one outcomes.
- `self-check.json`: the focused runner regression receipt.
- `commands.json`: the controller commands, their arguments, exit codes and streams, with symbolic
  paths; `archive-members.json`, `summary.json`, `expectations.json`, `product-pin.json`,
  `preparation-verification.json` and `baseline-discovery.json` carry the membership, collection,
  frozen-selection and provenance receipts.

The pilot was produced by `run.py pilot --binary <binary> --source <product> --pin <pin> --output
<work>/mcp-pilot` at the pilot head above, before the frozen expectations it fixed were committed.

For example, in a disposable environment, extract the accepted capture and verify it using this
repository's unchanged runner and protocol bytes, then regenerate and check every control:

```sh
mkdir /tmp/mcp-replay
tar -xzf results/2026-10-12-mcp-query-supersession-strict-binding/capture.tar.gz -C /tmp/mcp-replay
python3 mcp-query-supersession/run.py verify /tmp/mcp-replay/capture
python3 mcp-query-supersession/run.py negative-controls /tmp/mcp-replay/capture --output /tmp/mcp-negatives
python3 tools/verify_results.py
```

The shared archive verifier checks outer membership and hashes, not MCP conclusions or every
compressed member. `archive-members.json` supplies each compressed member's identity; the runner's
`verify` validates the extracted capture, the recorded wire bytes and provenance and regenerates
the scheduled assertions. The forbidden-write archive must reject with exit 2. `negative-controls`
exits 0 only when all twenty-one controls are rejected, each for the reason recorded in
`negative-controls.json`; compare its `negative-controls.json` with the stored one.

For a fresh reproduction, use a clean product checkout at the exact public pin, the recorded binary
and build receipt, and a clean committed companion checkout, with a new output path outside either
checkout:

```sh
python3 mcp-query-supersession/run.py capture \
  --source "$PRODUCT" --binary "$BINARY" \
  --pin results/2026-10-12-mcp-query-supersession-strict-binding/product-pin.json \
  --expectations mcp-query-supersession/expectations.json \
  --output /tmp/mcp-new
python3 mcp-query-supersession/run.py verify /tmp/mcp-new
```

Repeat from the clean published companion head after publication. The archive's collection
checkpoints and later published-tree receipts are distinct; no PR is claimed merged.

## Limits

Synthetic client-boundary behavior only: no semantic truth, retrieval quality, ranking quality,
latency, throughput, memory, authentication or native-host acceptance. Opted-in trail inspection is
not implemented and is not claimed. The `mousa_trail` argument rejection and the filtered v4
response are observed; the recorded native-only member is not disclosed.

Request binding proves that each recorded receipt is the operation the schedule requested, and the
strict parse proves that no repeated key and no changed JSON type can hide inside one. Both are
internal consistency evidence about this capture, not a claim that the product rejects any
particular request; the product-side rejection of `1`, `0`, a repeated `supersession` name and
`"true"` is a separate recorded observation of the tested binary. The first and second revisions'
own archives detected neither this defect nor the `oneOf` defect; their recorded observations are
retained as those revisions' observations and are replayed with the runner copy inside each of
them.

Storing the twenty mutated copies as the earlier revisions did is what the compact layout replaces;
this revision's control record therefore depends on the stored capture and the committed runner
rather than on twenty archived copies, and the historical directories keep theirs.

The tool-level trailing-data rule is unreachable through a valid JSON-RPC frame: the runner observes
the framing-level rejection instead and records that difference. An oversized inbound frame
(> 2 MiB) is not exercised here.

Corrupting the store while the server holds it open proves a call-level refusal with no commit, not
rollback of an in-flight transaction, and concurrency, backup and physical store-file integrity
remain product-local evidence. Matching source and binary pins do not prove a reproducible build on
another toolchain. This archive does not certify the product implementation; it records what one
pinned executable answered over stdio.
