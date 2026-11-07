# Current-source manifest client observations

Two fresh stores passed the frozen native/stdio client schedule against public
Mousa commit `09bc71f5c278014587ef7f63d6eab54d996f0495`, tree
`f5d24d7c59fe200830660c35d4597a4854762d7f`. Each capture retains 38 scheduled
events and nine stable manifest rows. Both replays, all four rehashed controls per
capture, and the fresh-store comparison passed. This records protocol and content
identity behavior, not independent milestone acceptance or a tagged release.

The exact anonymous public checkout was clean. Its CGo-free Go 1.27.1 binary has
SHA-256 `5aae733bfd86b079d5c9e88669a08981ef7a6153ac4bed21050928f38c1cf8b9`;
complete build metadata is retained in each `capture.json`. Both stores used this
same binary; independently bit-identical builds are not claimed. Producer source
was committed at `5f5d6b2f3e3e775a46e167b91eb1292623772713`; the protocol also binds
every reused producer/helper file by digest.

## Observations

The fixture uses alias `synthetic-source-manifests`, one short BOM/CRLF/UTF-8
text item and one empty item. Independent Python recipes derive the canonical
source, observation, artifact, representation and segment pins, ordered segment
inventory digests and full manifest IDs. The initial golden manifest ID is
`fe3caadbd884679fd6b6372a1f53d272c51e8b089cc77cedc26eccd040b02de3`.

- Reversed-order retries and JSONL omission preserve the indexed fingerprint.
- Revision, fixed-v1 to passage-v1 replacement, and explicit deletion change it.
- Restoring identical pins restores the original fingerprint.
- Native and MCP exports agree. Expected match/mismatch is explicit; native
  mismatch exits 1 while MCP mismatch remains an ordinary structured result.
- Read-only configured MCP permission suffices. Denied export/check returns only
  decision metadata; native denial exits 1 with its diagnostic retained.

The four controls rehash a changed current pin, changed inventory digest, flipped
expectation result or denied disclosure. Each fails its named semantic detector,
not merely a stale outer hash. Controls are regenerated; only compact receipts
are stored, not mass-mutated copies. The preliminary producer smoke exposed an
incorrect independent observation-key spelling; it was corrected to the existing
adapter's double-hex spelling before this protocol and these captures were frozen.

## Reproduce and inspect

See [producer instructions](../../source-manifests) and
[reproduction guidance](../../REPRODUCING.md#current-source-manifests). Raw requests,
responses, native arguments/streams/exits, build identity, independent inventory
rows and controls remain directly readable in `first/` and `second/`. The run
manifest hashes every retained regular member; no store, binary, credential,
symlink or cache is included. Run `python3 tools/verify_results.py` for archive
integrity and the producer's `verify`, `controls` and `compare` modes for semantic
replay.

A fixed JSONL alias preserves source identity across stores. Different directory
roots cannot reproduce the same source ID just by holding identical text. This
fixture independently derives one short segment per nonempty item, not the full
passage-segmentation algorithm. It does not establish hostile-store, cancellation,
concurrency or HTTP properties; those remain product regression-test evidence.
A match is an indexed-snapshot check, not a live-filesystem scan, completed-work
record, future-query lease, semantic-truth certificate or model-window guarantee.
No performance, enterprise/QMD, embedding, generation, judging or held-out quality
campaign was run. Earlier producer, protocol, result bytes and source pins are
unchanged.
