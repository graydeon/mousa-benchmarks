# Corrected native token release observations

Capture and a separate fresh-store reproduction target public Mousa revision
`0d1768c1f83c178b0a714d0bebb6d6738d70812d`, tree
`d6fac4d76eb2ecb97cae5ae97ebe62a52c7d09a0`, on the open
[PR84 branch](https://github.com/graydeon/mousa/pull/84). This is a public branch
revision, not a claim of merge or acceptance. It corrects the token release
projection described in [issue #85](https://github.com/graydeon/mousa/issues/85).

The [original result](../2026-10-22-native-tokens) remains pinned to
`50a1b43267177b8ea0fa690d4fae8a3c06c032d8`. Its capture, reproduction,
counts, metadata and manifests are unchanged historical observations, not
relabeled correction evidence.

## Source and method

The exact clean public source was built with Go 1.27.1, Linux/amd64,
`GOAMD64=v1`, `GOWORK=off` and `CGO_ENABLED=0`. Build metadata reports the named
revision and `vcs.modified=false`. `build.json` and each run's `product.json`
record source/tree/build declarations and executable SHA256. No executable,
database, Python environment, cache or links are exported.

The unchanged [capture driver](../../native-tokens) invokes only existing public
native commands. It neither imports product internals nor opens SQLite. Both
runs create separate fresh directory/JSONL stores and record every argv, input,
stdout, stderr and exit. Query and independent whole-context reference counting
use official `tiktoken==0.12.0`, `o200k_base`, `encode_ordinary`. Runtime and
vocabulary identities are retained in each `backend.json`; vocabulary downloads
are disabled during the run. Preparation remains separate.

## Observed results

Both driver executions exited 0: **48 native calls and 20 independently counted
whole contexts per run**. Expected retired-recount command failures remain in
the raw receipts. Both source forms exercise lexical, supplied-vector and hybrid
retrieval with original/exact-v1 packing. The byte-only and original high-cap
queries select three passages; exact-v1 selects two byte-distinct passages.
Pressure selects one whole passage rather than trimming it. Counts include the
complete independently reconstructed provenance headers and separators.

Hybrid exact-v1 observations:

| Run | Source form | Full rendering tokens (2 passages) | Pressure cap | Pressure rendering tokens (1 passage) |
|---|---|---:|---:|---:|
| Capture | JSONL | 250 | 132 | 117 |
| Reproduction | JSONL | 250 | 132 | 117 |
| Capture | Directory | 245 | 128 | 116 |
| Reproduction | Directory | 260 | 138 | 121 |

Directory roots and canonical identities differ between fresh runs; their header
token costs can differ. These are within-run relationships, not cross-run
identity or timing goldens. Exact reference token IDs are retained in `counts.json`.

Both runs pass exact-boundary fit, restart context/packet stability, normal native
history and official retained-text recount. Query/history agree on the released
token view. The corrected view includes accepted `candidate_ids` aligned with
proposed counts and, in lexical mode, compact accepted-order lexical facts;
it is not the full canonical producing record. Accepted unselected duplicate
metadata remains legitimate. All fixtures here have single-source ancestry.

Replacing every item excludes stale vectors from current hybrid selection and
preserves old released history. Normal history reports retired original text
unavailable; explicit recount refuses rather than inventing bytes. Fresh deny
returns no context, evidence, proposed source counts or coverage and hides history.

## Reproduce and verify

Follow the [exact-head build/runtime instructions](../../native-tokens), replacing
`PUBLIC_HEAD` with `0d1768c1f83c178b0a714d0bebb6d6738d70812d` and using an absent
output directory. Run the driver twice with separate output directories for the
two fresh-store observations. The archive check is:

```sh
python3 tools/verify_results.py
```

The existing manifest verifier checks file membership, bytes and hashes. It does
not establish behavioral truth or cryptographic proof of a build/tokenizer run.
The driver establishes the finite native counting relationships above. Its
unchanged source digest and both execution exits are recorded in `runner.json`.

## Limits

This capture validates ordinary native compatibility after the correction. It
**does not establish mixed-ancestry lifecycle filtering**: current public ingestion
commands cannot construct arbitrary multi-source derivations. The product's real
SQLite/official-backend regression and native serializer regression establish
that internal graph release boundary; no copied internal harness, database export
or new public ingress is introduced here. Original single-source receipts do not
prove the corrected graph case either.

No model, provider service, answer generation, relevance, semantic truth,
performance or universal tokenizer equivalence claim follows. Only returned
context is counted, not unknown application/model or JSON/tool framing.
Reservations remain caller declarations. Product fault, corruption, writer and
reservation-boundary regressions are not companion observations. Startup issue
#39 remains deferred with export disabled; all historical failures remain intact.
