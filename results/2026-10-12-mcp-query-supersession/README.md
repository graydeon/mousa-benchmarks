# MCP query supersession acceptance

Synthetic stdio MCP client acceptance against [Mousa PR 69](https://github.com/graydeon/mousa/pull/69),
not a main-branch, native-CLI or performance result. Product public commit
`7ae0d8768e7cd203c48478412b493e1255c97b11`, tree `2b8b14f76e0907f3ca3fd5dc8c33934567e61d14`.
That commit implements the optional `supersession` query input and the declared
`supersession_excluded` result count on the existing `mousa_query` tool; it is not claimed
merged or available on main.

This is the second revision of this capture. The first,
[`results/2026-10-11-mcp-query-supersession`](../2026-10-11-mcp-query-supersession), is
retained unchanged with a dated note; its runner compared each recorded request only with
its own independent match metadata, so a rewritten request survived rehashing of the
stream and manifest. This revision binds every recorded receipt to the scheduled
operation and rejects exactly-one `oneOf` violations, so the assertion counts and both
frozen expectation and runner identities differ while every stable selection is
unchanged.

The standalone [stdlib runner](../../mcp-query-supersession/run.py) imports no product
internals, contains no identity codec and drives the explicitly supplied executable over
newline-delimited JSON-RPC stdio in separate processes. The pilot documented here is the
one that froze `expectations.json`; it ran at committed companion head
`52f54bba17545f6d6007b0d68e42d0888959be99`, tree
`f2638d7d618e0ec743b7d428426de6231f1b2a89`. The capture, fresh independent-store
reproduction and forbidden-write control ran at committed companion head
`82b1a8030888b81e0e550be59ff1014c6307e6d0`, tree
`01c62faf0d66fd9b34323ef047a056e7fe4761cc`, whose only change from the pilot's head is the
frozen expectations file itself; neither checkpoint is relabeled as the later publication
commit.

## Observed results

| Check | Actual result |
|---|---|
| Passing pilot, complete replay and freeze | Exit 0; only actual observed packet/evidence/candidate selections frozen (39 cases) |
| Capture and fresh independent-store reproduction | Both exit 0; each contains 129 recorded steps - 40 `tools/call`, 21 protocol requests, 11 notifications, 11 server starts, 11 startup brackets, 11 server stops, 23 native preparation commands and one external damage statement - 2721 assertions, 0 failed assertions |
| Complete replay of both captures | Both exit 0 |
| Recorded request bound to the scheduled operation | 414 request-binding assertions added and none removed against the first revision; every recorded frame, prepared command, notification and response identity is asserted against the schedule that produced it |
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
| Fifteen mutated archives plus a directly recorded false condition | Every control rejected for its named reason: damaged frozen input, wrong count expectation (`changed:active-original:query-opted:count`), wrong default property set (`changed:no-history:query-omitted:result-keys`), inverted assertion, omitted assertion, injected undeclared response field, forged read-bracket fingerprint (`changed:no-history:status:unchanged-all-tables`), a fabricated success where the damaged call must fail, a failed build receipt, a damaged build stream, and five request rewrites |
| Request rewrites | Each of the five rewrites keeps the scheduled match metadata, the observed response and every other receipt as captured, and each is rejected by its own request-binding assertion: a flipped `supersession` boolean and a replaced `query` by `changed:active-original:query-opted:request-params` and `changed:no-history:query-omitted:request-params`, a replaced tool name by `changed:no-history:status:request-params`, a replaced method by `changed:no-history:query-false:request-method`, and a rewritten raw duplicate-key frame by `changed:no-history:boundary-duplicate:request-scheduled-bytes` |
| Focused runner regressions | `self-check` exit 0: one matching `oneOf` branch accepted, zero and two matching branches rejected for the `oneOf` reason, a boolean is not a number, and a closed object still rejects an undeclared property |
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
call that produced them. The 39 stable selections are identical to the first revision's; the
per-run fingerprints, decision identities and trail identities are not, by construction.

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
bytes. Its three unchanged tool definitions are equal to the tested build's as complete
parsed JSON definitions; the `mousa_query` delta is frozen in the protocol and asserted in
every session rather than presented as an observation of the tested binary. Those raw
baseline bytes and every session's own raw `tools/list` bytes are retained in their
receipts; the comparison is over the parsed definitions.

`product-pin.json` records the actual public source/tree, successful build argv, streams,
`CGO_ENABLED=0`, `GOWORK=off` and `go version go1.27.1 linux/amd64`. Executable SHA-256:
`d41954a65181189df0bdc1bf6e906823e966dd9f309f429d9f964fecbe748235`. Build argv is
`go build -trimpath -buildvcs=false -o <binary> ./cmd/mousa`, run from `<product>`. The
supplied build receipt is preparation provenance, not a build performed by the runner.

Runner SHA-256: `d5ec45d7ea9f482fa1e37be38d15323694e52fbf4fdc109661dd2ab76a1132b4`.
Protocol SHA-256: `ab59640df705a0bb76f2e2897d3135f98150db8121d044e10121cba2747383df`
(unchanged from the first revision; this revision adds no frozen protocol byte).
Frozen expectations SHA-256: `d6105241fbad8fb6bb937852eb50513350a5954d24e2595e82757bd95078d343`.

The runner's schema check is a documented subset: type, const, enum, pattern, numeric and
length bounds, `properties`, `required`, `additionalProperties`, `items` and `oneOf`, where
`oneOf` requires exactly one matching branch. Formats, `$ref`/`$defs`, `allOf`/`anyOf`/`not`,
`unevaluatedProperties`, `patternProperties` and dependencies are not implemented, and every
schema this build discovers is inline and needs only the supported subset. The envelope's own
separate payload-exclusive check is asserted independently of that subset.

## Archive layout and replay

The archives contain regular files only, relative paths with no traversal, and complete member
identities in `archive-members.json` (19 archives, 226 members). `manifest.json` covers every
outer member except itself. Historical results and the shared verifier are unchanged.

- `capture.tar.gz`, `fresh-reproduction.tar.gz`, `pilot.tar.gz`: complete accepted
  observations, raw wire bytes, assertions, frozen fixtures and copied runner/protocol.
- `forbidden-write.tar.gz`: the complete controlled failure, including both control statements.
- `negative-*.tar.gz` and `negative-controls.json`: the fifteen deliberately mutated copies
  plus the directly recorded false condition, each with the assertion verification reported
  as its reason; the five request rewrites also record the binding assertion expected to
  detect them.
- `self-check.json`: the focused runner regression receipt.

For example, in a disposable environment, extract the accepted capture and verify it using
this repository's unchanged runner and protocol bytes:

```sh
mkdir /tmp/mcp-replay
tar -xzf results/2026-10-12-mcp-query-supersession/capture.tar.gz -C /tmp/mcp-replay
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
  --pin results/2026-10-12-mcp-query-supersession/product-pin.json \
  --expectations mcp-query-supersession/expectations.json \
  --output /tmp/mcp-new
python3 mcp-query-supersession/run.py verify /tmp/mcp-new
```

Repeat from the clean published companion head after publication. The archive's collection
checkpoints and later published-tree receipts are distinct; no PR is claimed merged.

## Limits

Synthetic client-boundary behavior only: no semantic truth, retrieval quality, ranking
quality, latency, throughput, memory, authentication or native-host acceptance. Opted-in
trail inspection is not implemented and is not claimed. The `mousa_trail` argument rejection
and the filtered v4 response are observed; the recorded native-only member is not disclosed.

Request binding proves that each recorded receipt is the operation the schedule requested; it
is internal consistency evidence about this capture, not a claim that the product rejects any
particular request. The first revision's own archive detected neither this defect nor the
`oneOf` defect; its recorded observations are retained as that revision's observations.

The tool-level trailing-data rule is unreachable through a valid JSON-RPC frame: the runner
observes the framing-level rejection instead and records that difference. An oversized inbound
frame (> 2 MiB) is not exercised here.

Corrupting the store while the server holds it open proves a call-level refusal with no
commit, not rollback of an in-flight transaction, and concurrency, backup and physical
store-file integrity remain product-local evidence. Matching source and binary pins do not
prove a reproducible build on another toolchain. This archive does not certify the product
implementation; it records what one pinned executable answered over stdio.
