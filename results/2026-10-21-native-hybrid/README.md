# Native hybrid observations — 2026-10-21

Product [PR83](https://github.com/graydeon/mousa/pull/83), exact public head
`8abe7272e1adaa623478d0f7bcc950594c6d7fea`, tree
`3f3e439f9a81aa9dffcb7c1ca03b414ac3c8aff6`. This is a submitted feature PR,
not a claim of merge or independent acceptance. `build.json` records the clean
anonymous public checkout and actual CGo-free build with exit 0. Each run records
the executable digest and source/tree pins; no executable is exported.

`capture/` and `reproduction/` each passed 34 actual native calls over separate
fresh directory and JSONL stores. The driver uses only native commands, never
SQLite or product internals. Each command starts a new process. Both runs retain
exact argv, stdin, stdout, stderr and exit codes in `commands.json`.

## Observed capability

The synthetic source has one lexical-only passage, one vector-only passage and
one overlapping passage. The overlap ranks second in both branches but wins
fixed equal-weight RRF(k=60): `1/31`, compared with `1/61` for each branch's first
hit. Expected RRF values are independently derived with stdlib rational arithmetic.
Canonical segment-ID ties, original and exact-v1 packing, explicit dedup terms,
partial coverage and source/content pins are checked. A 40-byte budget selects
the 39-byte overlap; lexical-only and vector-only select different items.

The recorded v6 trail preserves producing branch membership/ranks, separate
BM25/cosine, fusion policy/order, coverage, canonical pins, packing and packet
relationships. The runs also observe restart packet stability, vector evidence
when lexical matching is empty, revision exclusion without stale-text release,
unchanged historical producing facts after revision, fresh denial with no
source-derived candidate/coverage facts, and denial of historical inspection.

## Files and reproduction

- `build.json`: actual public head/tree, build command/environment and exit.
- `runner.json`: bounded driver path and SHA-256.
- Each run's `inputs.json`: exact fixture and synthetic values.
- Each `product.json`: producing source/tree, binary digest and Go version.
- Each `commands.json`: unmodified native command inputs/outputs/exits.
- Each `summary.json`: asserted producing space/query-vector, packet/trail IDs and
  branch-versus-hybrid selections. Capture and reproduction have distinct audit IDs.
- `manifest.json`: regular-file membership, byte counts and SHA-256 identities.

Follow [the native example](../../native-hybrid) to build this exact head and run
against new stores. `python3 tools/verify_results.py` checks archived membership
and hashes separately; it does not execute the driver or establish runtime claims.

Absolute temporary directory paths were public source identities from creation.
New directory roots have different canonical pins, so reproduction asserts each
run's ordering and producing relationships, not equality of cross-run bytes.

## Limitations

No embedding model runs. Supplied vectors establish arithmetic/protocol only,
not automatic natural-language semantic search, retrieval quality, semantic truth,
performance, authentication or model-window safety. Text does not prove how the
query vector was generated. This fixture has no equal-byte duplicate passages;
byte-duplicate displacement, zero coverage, corruption and transaction rollback
remain product regression cases, not claims inferred from these observations.
Historical completeness, absent vectors and lexical BM25 cannot be reconstructed
from later index state; hashes bind observations without proving past completeness.
Retired text is not archived. No database, executable, credentials, model or private
data is exported. The vector-only capture at product `345127a7f87b8f9f4497725983b73dce072cd669`
is unchanged and is not relabeled as hybrid evidence. Deferred startup-publication
holds and historical timeout/oversized-archive failures remain unchanged.
