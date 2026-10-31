# Vector/hybrid tokens with explicit supersession — 2026-10-31

Two independent fresh-store native/stdio MCP runs use public Mousa PR94 head
`27235e85984b2e2f222c31f0c090aa85de844ce7`, tree
`046280c0ceea69947d0cfc0e72386b2949104903`. The product was freshly built from a
clean anonymous checkout at that exact head; its public tree equals the locally
tested product tree. This is submitted synthetic protocol/counting evidence,
not independent final-head product acceptance or a released-version claim.

Each run records 115 events: 49 native commands, 62 MCP requests, 60 raw responses
and two clean process exits. Both vector/hybrid modes and original/exact-v1
packers cover default/false versus enforced changed context, exact-fit and
one-token-short allowances, released-byte pressure, reservations/zero allowance,
a byte-equal withheld twin and all-withheld outcome precedence. The successor
has no embedding and is later unavailable; it is never fetched as fallback.
All 68 returned contexts per run were independently encoded with official
`tiktoken==0.12.0`, `o200k_base`, `encode_ordinary`, and hashed as complete UTF-8
renderings including provenance headers and separators.

Both live captures, both live replays, eight rehashed controls and the fresh-store
comparison exit 0. All 109 result rows match after only the explicitly enumerated
per-invocation identity/time and historical wrapper-ID exclusions. Raw values
remain retained and within-run producing identities are checked before filtering.
Archived replays repeat both verifiers, all eight controls and the comparison:
all exit 0. `archive-verification.json` records 18 regular members with exact
membership and hashes; `raw-captures.tar.xz` is a 109448-byte lossless archive.
No canonical database, executable or interpreter/cache installation is exported.

The frozen schedule reuses existing vector, token, wire, strict-JSON/schema and
counting helpers. Native normal history and official recount retain producing
v10 facts. MCP supersession/token/retrieval projections remain independent and
run no recount. Restart and later deactivation do not reinterpret producing
selection. Retired selected text is unavailable for recount rather than archived.
Producing cosine/branch ranks, RRF(k60) and pre-mask coverage are unchanged.

## Reproduce and replay

Follow the [client instructions](../../vector-token-supersession) with `build.json`'s
exact public head. The runner and comparator are bound by `protocol.json` hashes.
Prepare the official offline interpreter/cache before running; no query installs
packages, downloads vocabulary, creates embeddings or calls a model.

Extract the archive into a new local directory using a tar reader that rejects
absolute/traversal paths and nonregular members. Compare every member against
`raw-members.json` before replay. With `ARCHIVE_OUTPUT` naming that directory:

```sh
"$TOKEN_PY" vector-token-supersession/capture.py verify \
  --cache "$TOKEN_CACHE" --output "$ARCHIVE_OUTPUT/capture"
"$TOKEN_PY" vector-token-supersession/capture.py controls \
  --cache "$TOKEN_CACHE" --output "$ARCHIVE_OUTPUT/capture"
"$TOKEN_PY" vector-token-supersession/capture.py verify \
  --cache "$TOKEN_CACHE" --output "$ARCHIVE_OUTPUT/reproduction"
"$TOKEN_PY" vector-token-supersession/capture.py controls \
  --cache "$TOKEN_CACHE" --output "$ARCHIVE_OUTPUT/reproduction"
"$TOKEN_PY" vector-token-supersession/compare.py \
  "$ARCHIVE_OUTPUT/capture" "$ARCHIVE_OUTPUT/reproduction" --cache "$TOKEN_CACHE"
python3 tools/verify_results.py
```

The repository verifier checks outer file integrity, not protocol conclusions or
whether a compiler/client actually executed. Hashes do not independently prove
execution. Raw argv receipts use declared local path substitutions; actual local
argv maps remain outside the public archive. Other arguments and all wire bytes
are unchanged. Rehashed request/count/selection/history controls must fail their
exact named detectors; they are consistency checks, not arbitrary-adversary proof.

## Failures and limits

No final-public-head capture/replay/control/comparison failed. Four earlier
preparation invocations failed: abbreviated source-head input, a missing client
receipt ID, changing pilot runner bytes during an in-flight pilot, and an incorrect
expectation that MCP exposes native recount-verification metadata. These were
corrected before freezing this protocol. Their partial preparation receipts remain
separate; none were relabeled as observations of this public head.

Current authorization/denial/source masking, directory selectors, source admission,
atomic imports, graph/content corruption, transaction ordering and worker
failure/cancellation are product-local tests, not claims from this public-client
fixture. Synthetic supplied vectors/counts do not establish semantic truth,
retrieval quality, latency, throughput, complete provider/model-window safety or
retired-text reconstruction. Earlier public files and producing pins are unchanged.
