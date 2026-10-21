# Native hybrid lexical/vector example

This stdlib Python driver invokes the Mousa executable only. It imports synthetic
caller-supplied vectors, combines them with lexical matches through
`query --hybrid-space`, and inspects the actual v6 producing trail. It does not
open SQLite or import product internals. No model or network service runs.

## Reproduce

Read the exact public product head from the dated result's `build.json`. In a
clean anonymous checkout of that head, build the executable with:

```sh
GOWORK=off CGO_ENABLED=0 go build -o /tmp/mousa-public-hybrid ./cmd/mousa
```

From this repository, use the clean checkout path and its exact head:

```sh
python3 native-hybrid/capture.py \
  --mousa /tmp/mousa-public-hybrid \
  --product-source /tmp/mousa-public-product \
  --product-head PUBLIC_HEAD \
  --output /tmp/mousa-hybrid-reproduction
python3 tools/verify_results.py
```

`--output` must not exist. A fresh run uses fresh stores; each individual command
also starts a new process and reopens its store. The driver writes the command
receipts before asserting outcomes, so an unexpected result is retained rather
than converted into a passing summary. The supplied binary must be built from
the named source: its digest is recorded, not cryptographic proof of its build.

## Expected behavior

Both directory and JSONL sources contain these exact passages:

| Item | Text | Lexical rank for `Drain` | Vector rank for `[1,0]` |
|---|---|---|---|
| `overlap.md` | Drain sockets before stopping the host. | 2 | 2 (cosine 0) |
| `lexical.md` | Drain sockets. | 1 | Absent: no embedding imported |
| `vector.md` | Radishes prefer damp soil. | Absent: no lexical match | 1 (cosine 1) |

Equal-weight RRF(k=60) gives the overlap `2/62 = 1/31`, and each single-branch hit
`1/61`. Canonical segment ID breaks the single-branch tie. The overlap therefore
wins the fused order despite losing to each branch's first hit. With a 40-byte
budget, lexical-only selects `lexical.md`, vector-only selects `vector.md`, and
hybrid selects the 39-byte `overlap.md`. The driver derives expected RRF using
stdlib rational arithmetic, checks both branch ranks and separate scores, exact
source/content pins, selection, history and canonical ties.

Both original and exact-v1 packers run over the fused order. This small fixture
has no equal-byte copies; duplicate displacement/budget-skip coverage remains in
the product regressions, not inferred from this capture. The lexical term policy
is explicit dedup with `Drain Drain`, yielding one quoted term.

The driver also checks restart packet stability, a valid lexical no-match with
vector evidence, partial vector coverage, stale embedding exclusion after resync,
unchanged historical producing branch/fusion facts, fresh denial without passage
or source-derived coverage disclosure, and denied historical inspection. Each
capture makes 34 native calls across the two source forms.

## Recorded limits

These are synthetic protocol/arithmetic observations, not embedding-model
execution, natural-language semantic search, retrieval quality, semantic truth,
performance, authentication or model-window safety. Query text does not prove how
a supplied vector was generated. The producing run checks matching completeness
on this known small fixture; hashes cannot prove historical index completeness or
missing-vector absence in general. Historical lexical BM25 cannot be recomputed
from a later changed corpus, and retired text is not archived.

Directory identities contain intentionally public absolute temporary paths. A
fresh run has different source/segment/embedding/packet/trail identities; the
within-run rank and producing relationships are asserted without a cross-run
byte-identity claim. JSONL identities are stable for the fixed external label,
but audit decisions/trails still differ between calls. Raw inputs, stdout,
stderr and exit codes remain unmodified. No database, executable, credentials,
model or private data is exported. The earlier vector-only capture retains its
historical product pin and does not become hybrid evidence.
