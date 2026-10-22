# MCP vector/hybrid retrieval observations

Product [PR87](https://github.com/graydeon/mousa/pull/87), public head
`c452b63bc57d9b3e557472f4a248c2ba96c38c54`, tree
`9548aad339f51f9be899381691cd9f052faccefc`. Both required CI jobs passed on that
head before this isolated public-source build. See `build.json` for build,
binary and toolchain identities, and `runner.json` for driver/helper/baseline pins.
This is submitted feature evidence, not a claim of merge or independent acceptance.

## Observed results

Capture and separate fresh-store reproduction each passed five public native
preparation/change commands and three stdio sessions, with 43 scheduled request
frames, 40 response frames and three successful process exits. They use only
synthetic caller-supplied vectors and the configured JSONL source. Omitted packing,
explicit original and exact-v1 packing selected the independently expected
cosine winner `vector.md`; hybrid selected `overlap.md`, whose branch ranks 2/2
yield `2/62 = 1/31`, above either single-branch score `1/61`.

The driver validates actual selected text/digest/coordinates, candidate pins,
cosine and branch ranks/fusion, canonical ties, partial coverage, default packing,
and producing decision/trail/packet relationships. Omitted/false history excludes
retrieval facts; true returns the producing v5/v6 facts. Restart and a later source
revision change current coverage from eligible/indexed/missing 3/2/1 to 3/1/2
without rewriting old ranking facts. Fresh source denial returns no evidence,
coverage, candidates or historical payload. Bool-as-number and unconfigured
path-looking source requests have precise refusal codes, without fallback.

Raw scheduled requests are regenerated and checked byte-for-byte, including
history targets obtained from their producing query. Strict JSON parsing reports
duplicate keys and rejects nonfinite constants. Canonical comparison distinguishes
JSON types at every depth. Wire responses are checked against their actual
discovered output schemas, using the existing bounded validator with exactly-one
`oneOf` semantics. The three legacy sync/status/query definitions match accepted
main after changing only their configured source enum to this fixture alias.
No broader schema compatibility claim is made for the intentionally extended trail
or the new tools.

Both runs' negative controls pass: a coherently rehashed response with the wrong
selected item fails `selected-evidence`, and a rehashed generated request changed
to `[true,0]` fails `scheduled-request-bytes`. Only compact control receipts are
stored; the driver regenerates the mutated copies deterministically. These are
semantic detectors, not failures caused by stale stream hashes.

## Replay and reproduce

From the companion repository root:

```sh
python3 mcp-retrieval/capture.py verify --output results/2026-10-22-mcp-retrieval/capture
python3 mcp-retrieval/capture.py verify --output results/2026-10-22-mcp-retrieval/reproduction
python3 mcp-retrieval/capture.py controls --output results/2026-10-22-mcp-retrieval/capture
python3 tools/verify_results.py
```

For a new execution, follow [the driver instructions](../../mcp-retrieval/README.md)
and build this exact public product head in a clean checkout. Use an absent output
path. Independent stores have fresh audit/trail identities; each run binds its
own recorded identities rather than treating them as cross-run byte goldens.

## Boundaries

This establishes synthetic arithmetic/protocol and authorization behavior at the
client boundary, not semantic retrieval quality, a model integration, ANN,
automatic embedding generation, latency or model-window safety. The small fixture
has no byte-equal copies; duplicate displacement/budget skips, malformed-boundary
matrices and native-created v7 safe history are product regressions, not inferred
from this capture. MCP token execution/metadata is not enabled.

Historical BM25 and completeness are recorded producing observations; today's
index cannot prove past completeness or absence. Retired text is unarchived. Raw
traffic retains explicit source text and public synthetic labels only. No SQLite,
binary, vocabulary cache, credential or model is exported. Hashes bind archived
bytes and reported build inputs, not proof of a build or historical truth. Every
older native/vector/hybrid/token/MCP archive remains unchanged at its own pin.
