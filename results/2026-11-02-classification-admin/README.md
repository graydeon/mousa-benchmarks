# Attributed classification administration observations

Two separate fresh-store native client runs use public product
`6d7a4c11ba44f2d5bf49c01a647762641e318f7a`, tree
`51c1cc58493492c960820e88a1123708f6528e05` ([PR100](https://github.com/graydeon/mousa/pull/100)).
The anonymously fetched public tree equals the product's source-bound tested tree.
Build identity and digest are in [build.json](build.json); no executable or database
is exported. The [frozen protocol](protocol.json) binds the producer and existing
strict client/archive helpers. [Reproduction instructions](../../classification-admin)
use only native commands and the Python standard library.

Both capture and reproduction passed 13 native calls, archive behavioral replay and
a freshly hashed returned-label mutation rejected at `assertion-facts-binding`.
The [comparison](comparison.json) exactly matches both canonical assertion documents,
fixed parent/replacement pins and unchanged-selection packet across the fresh stores.
Fresh query request/decision/trail IDs and timing are retained in raw output, not
compared across invocations.

The original assertion is
`8e5c8f274d8049cd64ade729a7d2b17c40d7f49e465986df2b11ba39d64da3f9`;
changing only the label produces
`bda2d4831615e93b9304ab4d00b713ee8313448400379c5f9faf269b70230cc7`.
Put/retry/get canonical bytes match, the original remains unchanged after the
conflicting assertion and invalid-parent refusal, and ordinary retrieval remains
unchanged. After resync replaces the evidence, original readback still names its
original segment and basis representation, not replacement pins or recovered text.

Each run directory has the full content-addressed `capture.json.gz`, readable
`summary.json`, `controls.json` and deliberately invalid `mutated-label.json.gz`.
The shared archive helper checks member/stream hashes before replay. The run
manifest covers all these regular files. The mutation is negative evidence and
must not be treated as a successful capture.

Coverage is **segment subjects with representation basis only**. The product's
local tests separately cover all five subject forms, strict draft input, row/link
idempotence, atomic rollback and damaged canonical/projection/startup errors.
Matching client output does not prove database row/link invariance.

These are synthetic protocol/identity observations, not automatic classification,
authenticated authorship, calibrated confidence, label truth, semantic quality,
performance or model-driven acceptance. Labels do not change indexing, serving
permission, ranking, freshness or supersession. Classification-based filtering/
authorization, secret scanning and automatic inference remain unimplemented.
No MCP administration, SQL inspection, product imports, model calls, database or
binary export, historical archive rewrite or new evaluator is involved.
