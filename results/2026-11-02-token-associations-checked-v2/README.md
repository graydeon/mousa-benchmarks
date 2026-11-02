# Declared-context observations after checked aggregate admission

Two independent fresh stores exercise native directory/JSONL and configured
stdio MCP against [Mousa PR98](https://github.com/graydeon/mousa/pull/98), public
head `56783cc8e5d64315bf7527bfe423ef69330a74f5`, tree
`e059f03874153d43d0bbea7342cd5e394353e2bb`. The executable was built from that
exact clean anonymous checkout with CGo disabled and GOAMD64=v1. `build.json`
records its digest, actual command and VCS build metadata.

This is an additive corrected-pin capture after the product's checked aggregate
byte-admission correction. The [original archive](../2026-11-02-token-associations)
and [original producer/protocol](../../token-associations) retain their bytes and
`4ef4c7c` product pin. The [versioned producer](../../token-associations-checked-v2)
is byte-identical to the original and reuses the same frozen helpers; its own
protocol binds the corrected head/tree. No cross-pin equality is claimed.

## Observations

Each run retains 70 scheduled events: 39 native commands, 27 MCP requests,
25 raw responses and two clean process exits. Official offline
`tiktoken==0.12.0` / `o200k_base` independently counts and hashes 39 complete
returned renderings per run, including empty and denied contexts. The fixed
owned temporary directory root is the same in both sequential runs, because
native directory source identities bind the absolute root.

The synthetic fixture has a matching backup instruction, a nonmatching declared
connection-closure qualification and byte-equal qualification text in a distinct
item. Both packers show these whole-rendering boundaries:

| Surface | Exact cap and returned tokens | One-short cap | One-short returned tokens |
| --- | ---: | ---: | ---: |
| Native directory | 251 | 250 | 127 |
| Native JSONL and configured MCP | 245 | 244 | 127 |

Exact fit retains primary and supporting text; one token short omits the note
with reason `tokens` without displacing primary evidence. Counts include exact
headers, text and separators, not a sum of passage counts or JSON envelopes.
`original` uses original term policy; `exact-v1` uses dedup term policy. This is
not their full policy cross-product.

The schedule also checks ordinary/unfired controls, byte duplicates,
primary-trigger ordering, separate primary/associated proposed-count alignment,
null duplicate counts, producing v11 history, native retained-text recount and
independent MCP token inspection. Supersession/vector/hybrid associations refuse;
fresh native/MCP denial releases no evidence or historical payload. Actual
discovered supersession descriptions advertise byte and measured-token support
without advertising vector/hybrid associations.

## Replay and controls

Both live and extracted-archive replays pass under the corrected-pin protocol.
The 63-row fresh-store comparison retains source, segment, packet, access binding
and selection/count/provenance facts. It excludes only the enumerated per-call
producing identities, access-activation IDs, timing and store-size samples after
binding each history to its producing query. Raw observations are not rewritten.

Three coherently rehashed controls per run alter the declaration request,
associated proposed count or attributed author. Each fails its intended detector;
archived control receipts reproduce exactly. These six receipts are synthetic
mutations, not additional observed product runs. `commands.json` records actual
command exits and output hashes with executable/interpreter/cache/source paths
substituted.

`raw-captures.tar.gz` contains exactly seven bounded regular JSON members: raw
capture, summary and negative-control receipts for each run, plus comparison.
`protocol.json` registers every archive member's size/hash; `manifest.json`
registers every outer file. Verify both layers before extraction. The repository
archive verifier checks membership and hashes, not protocol conclusions. See the
[client instructions](../../token-associations-checked-v2) for capture/replay.
No database, binary, cache, interpreter or private argv map is exported.

## Limits

Normal finite captures do not prove the hostile-record aggregate overflow
invariant; identity-recomputed canonical Validate/Decode boundary regressions
remain product-local. These are submitted protocol/selection/counting
observations, not independent acceptance, semantic sufficiency, recall,
completeness, truth, authenticated authorship, performance or universal
model-window safety. Caller attribution is not authenticated authorship. No
model, provider, embedding or evaluator calls occurred. Historical results,
negative observations and startup/export holds remain unchanged.
