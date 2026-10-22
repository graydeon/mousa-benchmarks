# Native token observations after lifecycle outcome correction

Capture and a separate fresh-store reproduction target public Mousa revision
`31a42b9be27499c77d4ce71db149621cc9e7d23d`, tree
`215a2d1292f1a5083e650f4d9735252d8b28cff9`, on open
[PR84](https://github.com/graydeon/mousa/pull/84). This is a published branch,
not a claim of merge or independent acceptance.

[Issue #86](https://github.com/graydeon/mousa/issues/86) corrects the native token
outcome for an authorized nonempty canonical candidate list with zero accepted
candidates: `lifecycle_excluded`, not `budget_omitted`. Denial, selected evidence,
true no-match and accepted byte/token budget omissions keep their established
outcomes. Mixed accepted/rejected budget cases remain budget omissions. The
accepted-only query/history projection from
[issue #85](https://github.com/graydeon/mousa/issues/85) is preserved.

The [original observations](../2026-10-22-native-tokens) retain their `50a1b43`
pin. The [projection-corrected observations](../2026-10-22-native-tokens-corrected)
retain `0d1768c`. Every older result member and manifest remains unchanged.

## Source and method

The clean public source was built with Go 1.27.1 on Linux/amd64, `GOAMD64=v1`,
`GOWORK=off` and `CGO_ENABLED=0`. Build metadata reports the exact revision and
`vcs.modified=false`. `build.json` and both `product.json` files record the
source/tree, build declaration and executable SHA256. No executable, database,
Python environment, vocabulary cache or links are exported.

The unchanged [capture driver](../../native-tokens) calls only public native
commands. It imports no product internals and never opens SQLite. Each execution
creates fresh directory/JSONL stores and records argv, stdin, stdout, stderr and
exit before assertions. Query and separate whole-context reference counting use
official `tiktoken==0.12.0`, `o200k_base`, `encode_ordinary`, with vocabulary
downloads disabled. `backend.json` records Python/package/vocabulary identities;
preparation is separate from capture.

## Observed results

Both driver executions exited 0: **48 native calls and 20 independent whole-context
reference counts per run**. Expected retired-recount failures remain in the raw
receipts. Both source forms cover lexical, supplied-vector and hybrid retrieval
under original/exact-v1 packing. High-cap original selects three passages;
exact-v1 selects two byte-distinct passages; pressure selects one whole passage.
The reference reconstructs the entire cited rendering, including headers and
separators, before counting it.

Hybrid exact-v1 observations:

| Run | Source form | Full rendering tokens (2 passages) | Pressure cap | Pressure rendering tokens (1 passage) |
|---|---|---:|---:|---:|
| Capture | JSONL | 250 | 132 | 117 |
| Reproduction | JSONL | 250 | 132 | 117 |
| Capture | Directory | 254 | 133 | 120 |
| Reproduction | Directory | 251 | 133 | 117 |

Fresh directory roots produce different canonical identities and header token
costs. These are within-run observations, not cross-run identity or timing
goldens. `counts.json` retains complete reference token IDs.

Both runs pass exact-boundary fit, restart packet/context stability, native
history and official retained-text recount. Query/history agree on accepted-only
token facts. Replacing every item excludes stale vectors from current hybrid
selection while preserving old released history. Normal history reports retired
original text unavailable; explicit recount refuses to invent it. Fresh denial
releases no context, evidence, proposed source counts or coverage and hides history.

## Reproduce and verify

Follow the [runtime and exact-head build instructions](../../native-tokens), using
`31a42b9be27499c77d4ce71db149621cc9e7d23d` as `PUBLIC_HEAD`. Run the driver twice
with distinct absent output directories for two separate fresh-store executions.
Verify the stored archive from this repository:

```sh
python3 tools/verify_results.py
```

The existing verifier checks membership, bytes and hashes. It does not prove
behavioral truth or how a binary/tokenizer was executed. `runner.json` records
the unchanged driver digest and actual capture/reproduction exits.

## Limits

These ordinary single-source observations **do not establish the all-rejected
mixed-ancestry outcome or rejected metadata filtering**. The product's real
SQLite ancestry/withdrawal tests and native serializer RED/GREEN regression
establish those internal boundaries for both packers, including normal/recount
history and mixed accepted/rejected budget controls. No public derivation ingress
or copied internal harness is introduced for this archive.

No model, provider, answer generation, semantic truth, retrieval quality,
performance or universal tokenizer-equivalence claim follows. Counts cover only
returned context, not unknown application/model or JSON/tool framing. Reservations
remain caller declarations. Fault/corruption/writer/reservation-boundary product
tests are not companion observations. Startup issue #39 remains deferred with
export disabled; historical failures remain intact.
