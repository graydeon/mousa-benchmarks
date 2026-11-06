# Vector and hybrid declared supporting context

Two fresh-store runs passed against public product commit
[`62b725213ce8613a1b824d2e07a305721531fb76`](https://github.com/graydeon/mousa/commit/62b725213ce8613a1b824d2e07a305721531fb76),
tree `b36107a4e7c0e27694c9821382a8f7af02aad8a3`.
The binary was built with `CGO_ENABLED=0` from a clean anonymous checkout of that
exact head. Each raw capture retains its binary SHA256 and `go version -m`
metadata. This is an open-PR source observation, not a tagged release or independent
feature acceptance.

## Observed workflows

The fixture has five synthetic items and two caller-supplied two-dimensional
vectors. Native directory/JSONL and configured stdio MCP queries use vector and
hybrid retrieval, original/exact-v1 packing, byte/token budgets and omitted,
false or true supersession. Native export/import and MCP export/import supply
current normalized source pins; embedding generation is external.

Each run retains 149 scheduled events and 120 stable comparison rows. Its 48 token
contexts were reconstructed from primary and supporting evidence and independently
counted with official `tiktoken==0.12.0`, `o200k_base`, `encode_ordinary` using the
prepared offline cache. Counts cover the complete exact returned rendering,
including headers and separators. Native retained-text recount checks recorded
history separately. No counting process calls a model or network service.

Named assertions verify:

- Primary evidence, cosine/BM25/branch ranks and RRF facts match association-free
  controls. Coverage remains five eligible passages and two indexed vectors.
- Declared nonmatching support has no embedding and appears separately with
  association attribution, without invented retrieval ranks.
- Explicit supersession withholds the exact old support pin before duplicate or
  budget accounting. The byte-equal twin remains eligible.
- Omitted and false supersession preserve equivalent stable results.
- Producing v14/v15 history, packet IDs, safe token facts and native recount agree.
- Returned byte totals, whole-context rendering, digest and independent counts agree.

Both stored replays and the two-store stable comparison passed. Comparison removes
request-specific authorization/trail identities but retains packet IDs. The same
binary and fixed directory-source identity were used for both runs; this is not
independent-build reproducibility or two independent quality populations.

## Semantic and parsing controls

Each capture has five passing controls. Four mutate count, support attribution,
recorded suppression or embedded duplicate JSON keys, then rehash the affected
streams and documents. Replay rejects each at its named detector. The fifth writes
an outer protocol document with conflicting duplicate `product_head` keys and
checks rejection by the same strict loader used for protocol/capture/summary and
comparison input. Mutated files and detector receipts are retained in the archive.

The additive entry point scopes strict outer loading to this producer. Historical
producers and observations are unchanged. During preparation, the support-membership
assertion initially passed Python sets to a canonical-JSON comparison; it was changed
to sorted JSON arrays before protocol freeze. Static review also identified inherited
permissive outer loading; the strict adapter and outer duplicate control were installed
before capture. Neither preparation failure is a public-binary execution failure.
Both frozen captures completed on their first attempt.
The first gzip package exceeded the publication limit of 2 MiB per file. The same
18 members were repackaged losslessly as a 152,160-byte xz archive, and every member
hash was checked again. No capture was repeated or observation removed.

## Files and replay

`protocol.json` freezes the product head/tree, fixture and all imported producer
hashes. `raw-captures.tar.xz` losslessly contains 18 regular files under `first/`
and `second/`: complete raw argv, stdin/stdout/stderr/exits and MCP frames, producing
IDs, summaries, replay receipts, control receipts and mutation documents.
`archive-members.json` lists exact member byte lengths and SHA256 digests. Every
member was extracted and verified before packaging. The result manifest binds the
archive and all outer receipts; it does not authenticate the original execution.

Replay with the prepared offline environment from the repository root:

```sh
RESULT=results/2026-11-06-vector-hybrid-associations
REPLAY=$(mktemp -d)
tar -xJf "$RESULT/raw-captures.tar.xz" -C "$REPLAY"
"$PY" retrieval-associations/capture.py verify --protocol "$RESULT/protocol.json" \
  --cache "$CACHE" --output "$REPLAY/first"
"$PY" retrieval-associations/capture.py verify --protocol "$RESULT/protocol.json" \
  --cache "$CACHE" --output "$REPLAY/second"
"$PY" retrieval-associations/capture.py compare --protocol "$RESULT/protocol.json" \
  --cache "$CACHE" --output "$REPLAY/first" --other "$REPLAY/second"
python3 tools/verify_results.py
```

For a new live capture, use [the documented launcher](../../REPRODUCING.md#vectorhybrid-declared-support)
with a new result directory. Do not overwrite these records. The launcher retains
uncompressed results; this stored run was packaged losslessly afterward.

## Limits

Synthetic vectors establish protocol and arithmetic, not semantic sufficiency,
authenticated authorship, answer quality, performance or model-window safety.
Declarations are supplied assertions, not access grants. The stable comparison and
rehashed controls establish stored consistency, not authenticated historical
execution or universal tamper detection. Product regressions cover additional
malformed input, budget, lifecycle and canonical boundaries; this small public
capture does not duplicate the full suite. No provider, paid inference, enterprise
rerun, QMD retry or packing-policy change was performed. Earlier research results,
failed conditions, producer bytes and public product pins retain their original meaning.
