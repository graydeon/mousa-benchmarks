# Native caller-supplied vector observations — 2026-10-21

Product [PR82](https://github.com/graydeon/mousa/pull/82), public head
`345127a7f87b8f9f4497725983b73dce072cd669`, tree
`31f47f71c4ce4fd37454b456c8aa7177b338825b`. This is a submitted product PR, not a
claim that the feature has merged. The binary was built from a clean anonymous
checkout of that public head with `GOWORK=off CGO_ENABLED=0`; `build.json` records
the actual command, environment and exit. Each observation records the binary digest.

Both `capture/` and `reproduction/` passed 28 actual native commands, each using
fresh directory and JSONL stores. They export normalized passage inputs, import
synthetic supplied vectors, select source-linked evidence with known cosine scores,
read packet/v5 trail bindings, check restart stability, resync a new revision,
observe missing vector coverage, reject stale import and inspect recorded history.
Original packing retains two tied copies; exact-v1 omits the duplicate and uses the
freed byte budget for the zero-score timetable. The lexical label `frost` has no
word overlap and retrieves no evidence. Supplied vectors establish arithmetic and
protocol behavior only; they are not real-model embeddings or a quality sample.

## Retained files

- `build.json`: public source/tree and actual portable build command/result.
- `runner.json`: committed bounded driver path and SHA-256.
- Each observation's `inputs.json`: exact initial/update fixture text and synthetic query.
- Each `product.json`: producing source/tree, binary digest and Go version.
- Each `commands.json`: actual argv, stdin, stdout, stderr and exit for every call,
  including the deliberately rejected stale import.
- Each `summary.json`: producing source/space/query-vector/content pins, packet/trail
  IDs and stale-revision coverage after the driver assertions passed.
- `manifest.json`: regular-file membership, sizes and SHA-256 identities for this run.

The absolute `/tmp/mousa-public-native-vectors-*` directory paths were deliberately
public source identities from creation. Raw receipts retain them without rewriting;
a fresh directory run has different source/segment/embedding/packet/trail identities
and may select a different first tied item. Within-run canonical-ID ordering and
recorded producing bindings are checked. No cross-run byte-identity claim is made.

## Reproduce and verify

Follow [the bounded native example](../../native-vectors). It builds the exact
`build.json` head and drives only public commands; it neither opens SQLite nor
imports product internals. Verify retained files separately with:

```sh
python3 tools/verify_results.py
```

Archive verification checks membership and hashes, not runtime semantics. The
capture does not establish concurrency/corruption rollback, every policy boundary,
authentication, performance, automatic natural-language semantic search, embedding
model quality, semantic truth or model-window safety. Those transaction/lifecycle
regressions remain in the product, and broader retrieval claims need model-specific
evidence. No model calls/downloads/services, database, binary or credentials are
exported. Historical observations and deferred startup-publication failures are unchanged.
