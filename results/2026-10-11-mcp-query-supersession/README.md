# MCP query supersession acceptance

Superseded 2026-10-12 by
[`results/2026-10-12-mcp-query-supersession-strict-binding`](../2026-10-12-mcp-query-supersession-strict-binding),
which parses every generated frame strictly and compares values with their JSON types preserved.
This directory is the first revision of the same capture: its archives, counts and receipts are
retained unchanged as that revision's observation. Its runner compared a recorded request only
with its own match metadata, so a request rewritten to the opposite value was accepted after the
stream and manifest were recomputed; it compared values with Python object equality, so a nested
`true` rewritten as `1` compared equal; and it parsed generated frames with the standard decoder,
so a repeated object key kept its last value. It detected none of those, and its `oneOf` check
accepted value `1` against overlapping `integer` and `number` branches. This archive's own
`run.py` and `protocol.json` members are therefore the bytes to replay it
with — the committed runner has changed since — for example
`python3 <extract>/capture/run.py verify <extract>/capture`. Two discovery-comparison
sentences below are corrected to state what that runner actually compared, parsed JSON
definitions rather than raw bytes; the rest describes that revision as it was captured.

Synthetic stdio MCP client acceptance against [Mousa PR 69](https://github.com/graydeon/mousa/pull/69),
not a main-branch, native-CLI or performance result. Product public commit
`7ae0d8768e7cd203c48478412b493e1255c97b11`, tree `2b8b14f76e0907f3ca3fd5dc8c33934567e61d14`.
That commit implements the optional `supersession` query input and the declared
`supersession_excluded` result count on the existing `mousa_query` tool; it is not claimed
merged or available on main.

The standalone [stdlib runner](../../mcp-query-supersession/run.py) imports no product
internals, contains no identity codec and drives the explicitly supplied executable over
newline-delimited JSON-RPC stdio in separate processes. Collection at
`2026-10-11T23:50:25.872972+00:00` used committed companion execution head
`452a6b4ec8b5b99542de89ebb0b8921a73504625`, tree `901064af2f72a1a57e8968dea4cfe44069d4007a`.
The pilot that froze the expectations ran at the same committed head; neither checkpoint is
relabeled as the later publication commit.

## Observed results

| Check | Actual result |
|---|---|
| Passing pilot, complete replay and freeze | Exit 0; only actual observed packet/evidence/candidate selections frozen (39 cases) |
| Capture and fresh independent-store reproduction | Both exit 0; each contains 129 recorded steps - 40 `tools/call`, 21 protocol requests, 11 notifications, 11 server starts and stops, 23 native preparation commands and one external damage statement - 2307 assertions, 0 failed assertions |
| Complete replay of both captures | Both exit 0 |
| Discovery | In every one of the 11 sessions the four tools are discovered, `mousa_sync`, `mousa_status` and `mousa_trail` are equal, as complete parsed JSON definitions, to the frozen pre-query baseline, and the `mousa_query` definition delta is exactly the two frozen additions with nothing removed or changed |
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
| Ten mutated archives plus a directly recorded false condition | Every control rejected for its named reason: damaged frozen input, wrong count expectation (`changed:active-original:query-opted:count`), wrong default property set (`changed:no-history:query-omitted:result-keys`), inverted assertion, omitted assertion, injected undeclared response field, forged read-bracket fingerprint (`changed:no-history:status:unchanged-all-tables`), a fabricated success where the damaged call must fail, a failed build receipt and a damaged build stream |
| Published companion-tree reproduction | Not part of this collection; repeat from the clean published tree as described below |

Each native command, MCP call and rejected input has its own complete logical SQLite
fingerprint before and after, including WAL-visible rows. Reads and rejections leave every
table unchanged; queries and trail inspections change only authorization-audit and trail
tables; the external damage statement is recorded with its own before/after state. The
injected table is dropped again after the measured violation so a later startup failure
cannot become the detector's failure cause.

Withheld candidates keep their accepted rank and canonical size in the recorded trail while
being absent from the released evidence, which reports no text for them. Expected packet,
evidence and candidate values were frozen only from a passing, replay-verified pilot; fresh
request, decision and trail identities and the recorded trail's own identities stay in each
step receipt rather than becoming cross-run goldens, and the runner asserts them against the
call that produced them.

## Preparation and build provenance

`preparation-verification.json` is separate preparation evidence for this pin: one native
sync of the frozen items into a throwaway store, read back with a read-only SQLite connection
and compared with the independently derived protocol pins (observation, artifact,
representation, segment and active-item identities per item, plus the declaration readback,
activation canonical bytes and the verified activation projection). The helper that derives
those identities is preparation only; the client runner contains no identity derivation and
never calls it.

`baseline-discovery.json` records the pre-query tool definitions: a second binary built from
the accepted pre-query public commit `015dc1aa9f054b4b809a5d893b023afc4e378ba1` (tree
`63a1dd4156644e29904365870b4568c4847e9478`, executable
`19f122f9ca29e3cb0de29bc87a3f7ebca89668b0cd8a456328eaa60858618cf4`) answering
`initialize` and `tools/list` on the same fixture, with its own sync, request and response
bytes. Its three unchanged tool definitions are compared as complete parsed JSON definitions;
the raw baseline bytes and each session's own `tools/list` bytes are retained in their
receipts. The `mousa_query`
delta is frozen in the protocol and asserted in every session rather than presented as an
observation of the tested binary.

`product-pin.json` records the actual public source/tree, successful build argv, streams,
`CGO_ENABLED=0`, `GOWORK=off` and `go version go1.27.1 linux/amd64`. Executable SHA-256:
`d41954a65181189df0bdc1bf6e906823e966dd9f309f429d9f964fecbe748235`. Build argv is
`go build -trimpath -buildvcs=false -o <binary> ./cmd/mousa`, run from `<product>`. The
supplied build receipt is preparation provenance, not a build performed by the runner.

Runner SHA-256: `dee97cab75e8146199fd9fd7ca8a9d8d8de9a2875303f90067d05a2cb37b6eff`.
Protocol SHA-256: `ab59640df705a0bb76f2e2897d3135f98150db8121d044e10121cba2747383df`.
Frozen expectations SHA-256: `d51eee17269cd87c68fa9964f82f1cca695e2cec3e4e4ccd59833e7c6371de2e`.

The runner's schema check is a documented subset: type, const, enum, pattern, numeric and
length bounds, `properties`, `required`, `additionalProperties`, `items` and `oneOf`. Formats,
`$ref`/`$defs`, `allOf`/`anyOf`/`not`, `unevaluatedProperties`, `patternProperties` and
dependencies are not implemented, and every schema this build discovers is inline and needs
only the supported subset.

## Archive layout and replay

The archives contain regular files only, relative paths with no traversal, and complete member
identities in `archive-members.json`. `manifest.json` covers every outer member except itself.
Historical results and the shared verifier are unchanged.

- `capture.tar.gz`, `fresh-reproduction.tar.gz`, `pilot.tar.gz`: complete accepted
  observations, raw wire bytes, assertions, frozen fixtures and copied runner/protocol.
- `forbidden-write.tar.gz`: the complete controlled failure, including both control statements.
- `negative-*.tar.gz` and `negative-controls.json`: the ten deliberately mutated copies plus
  the directly recorded false condition.

For example, in a disposable environment, extract the accepted capture and verify it using
this repository's unchanged runner and protocol bytes:

```sh
mkdir /tmp/mcp-replay
tar -xzf results/2026-10-11-mcp-query-supersession/capture.tar.gz -C /tmp/mcp-replay
python3 mcp-query-supersession/run.py verify /tmp/mcp-replay/capture
python3 tools/verify_results.py
```

The shared archive verifier checks outer membership and hashes, not MCP conclusions or every
compressed member. `archive-members.json` supplies each compressed member's identity; the
runner's `verify` validates the extracted capture, the recorded wire bytes and provenance and
regenerates the scheduled assertions. A negative archive or the forbidden-write archive must
reject with exit 2.

For a fresh reproduction, use a clean product checkout at the exact public pin, the recorded
binary and build receipt, and a clean committed companion checkout, with a new output path
outside either checkout:

```sh
python3 mcp-query-supersession/run.py capture \
  --source "$PRODUCT" --binary "$BINARY" \
  --pin results/2026-10-11-mcp-query-supersession/product-pin.json \
  --expectations mcp-query-supersession/expectations.json \
  --output /tmp/mcp-new
python3 mcp-query-supersession/run.py verify /tmp/mcp-new
```

Repeat from the clean published companion head after publication. The archive's collection
checkpoint and later published-tree receipts are distinct; no PR is claimed merged.

## Limits

Synthetic client-boundary behavior only: no semantic truth, retrieval quality, ranking
quality, latency, throughput, memory, authentication or native-host acceptance. Opted-in
trail inspection is not implemented and is not claimed. The `mousa_trail` argument rejection
and the filtered v4 response are observed; the recorded native-only member is not disclosed.

The tool-level trailing-data rule is unreachable through a valid JSON-RPC frame: the runner
observes the framing-level rejection instead and records that difference. An oversized inbound
frame (> 2 MiB) is not exercised here.

Corrupting the store while the server holds it open proves a call-level refusal with no
commit, not rollback of an in-flight transaction, and concurrency, backup and physical
store-file integrity remain product-local evidence. Matching source and binary pins do not
prove a reproducible build on another toolchain. This archive does not certify the product
implementation; it records what one pinned executable answered over stdio.
