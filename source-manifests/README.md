# Current-source manifest client capture

This producer records native and stdio MCP observations of current indexed JSONL
content. It exports a manifest, checks an expected ID, retries with reversed input
order, omits an item, changes a revision and segmentation policy, deletes/restores
an item, and checks authorized and denied native/MCP reads. The fixed alias gives
two independent temporary stores the same source identity. Directory roots are
not normalized into equality.

## New capture

Use a clean anonymous checkout of the exact public product commit containing the
manifest operation. Build a CGo-free binary outside that checkout. From this
repository root:

```sh
export PUBLIC_HEAD=EXACT_PUBLIC_PRODUCT_COMMIT
export PUBLIC_SOURCE=/path/to/clean/product-checkout
export BINARY=/path/to/cgo-free-mousa
export RESULT=results/NEW-source-manifests
sh source-manifests/run-public.sh
```

The launcher creates a new directory, freezes the source/tree and producer hashes,
runs two fresh-store captures, verifies each, applies four rehashed controls,
compares stable manifest facts, and registers every regular result member with
`tools/make_manifest.py`. It requires Python 3.9+ and Go build metadata. No model,
embedding producer, tokenizer, QMD or paid API is used. Failed captures retain
`partial.json`; choose another directory rather than overwrite an attempt.

`canonical.py` independently derives the source, observation, artifact,
representation and segment pins and the manifest/inventory digests. The local
adapter observation key retains its existing double-hex raw-digest spelling:
`item/ITEM@HEX(UTF8(LOWERCASE_SHA256_HEX))`. The fixture includes BOM/CRLF, UTF-8,
HTML characters and empty content, but only one short segment per nonempty item.
This is not an independent implementation of the general passage segmenter.

## Replay and controls

```sh
RESULT=results/RECORDED-source-manifests
python3 source-manifests/capture.py verify --protocol "$RESULT/protocol.json" --output "$RESULT/first"
python3 source-manifests/capture.py verify --protocol "$RESULT/protocol.json" --output "$RESULT/second"
python3 source-manifests/capture.py controls --protocol "$RESULT/protocol.json" --output "$RESULT/first"
python3 source-manifests/capture.py compare --protocol "$RESULT/protocol.json" --output "$RESULT/first" --other "$RESULT/second"
python3 tools/verify_results.py
```

The controls change a returned current pin, segment-inventory digest, expectation
result or denied disclosure, rehash the affected stream and manifest where
applicable, and require the named semantic check to reject it. The published
receipts identify the regenerated mutations; mass-mutated archives are not stored.
Replay proves consistency of retained bytes and the scheduled requests, not
authenticated historical execution or protection against every possible mutation.

The native mismatch and denial paths retain exit 1 and their diagnostic streams;
authorized export/check retain exit 0. MCP mismatch remains a structured result.
A match describes indexed state in one inspection snapshot, not unsynchronized
input files, completed work, query stability or a lease on later operations.
Hostile storage, cancellation, concurrency and HTTP are product-test claims, not
claims established by these ordinary native/stdio observations. No performance,
semantic quality, held-out confirmation or release acceptance is inferred.
