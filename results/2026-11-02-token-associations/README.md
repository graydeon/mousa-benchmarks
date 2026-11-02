# Measured declared-context client observations

Two independent fresh stores exercise native directory/JSONL and configured
stdio MCP queries against [Mousa PR98](https://github.com/graydeon/mousa/pull/98),
public head `4ef4c7cae40b9ee69af23c077ed683768349ba7f`, tree
`0b45cb99da76be6011d5a61d72d6c0aa2fa5b45a`. The executable was built from that
exact clean anonymous checkout with CGo disabled. `build.json` records its digest
and VCS build metadata; no executable or database is exported.

Each run retains 70 scheduled events: 39 native commands, 27 MCP requests,
25 raw responses and two clean process exits. Official offline
`tiktoken==0.12.0` / `o200k_base` independently counts and hashes 39 complete
returned renderings per run, including empty and denied contexts.

## Observed selection and counts

The fixture's matching instruction recommends a connection context manager for
backup. Its declared, nonmatching qualification says the manager does not close
the connection. A distinct item supplies byte-equal qualification text. These
are synthetic supplied notes, not authenticated authorship or proof of an answer.

Both packers produce the following exact/one-short behavior. Token counts cover
provenance headers, exact passage bytes and separators, not a sum of passage
counts or the surrounding JSON/MCP envelope.

| Surface | Exact cap and returned tokens | One-short cap | One-short returned tokens |
| --- | ---: | ---: | ---: |
| Native directory | 251 | 250 | 127 |
| Native JSONL and configured MCP | 245 | 244 | 127 |

At exact fit, both primary and supporting note survive. One token below the
complete rendering, the supporting note is omitted with reason `tokens` and
primary text remains unchanged. A primary fitting bytes but not tokens does not
trigger expansion. The source ID is part of the counted header, so directory
and JSONL counts need not match.

`original` uses original term policy; `exact-v1` uses dedup term policy. Both
packers are observed on all three interfaces, but this is not their full policy
cross-product. Ordinary/unfired controls, distinct-segment byte duplicates,
primary/associated proposed-count alignment, null uncounted duplicate counts,
producing v11 history, native retained-text recount and independent MCP token
inspection are checked. Supersession/vector/hybrid associations refuse. Fresh
native/MCP denial releases no evidence or historical payload. Actual tools/list
supersession descriptions advertise byte and measured-token support without
advertising vector/hybrid associations.

## Replay and archive

See the [client instructions](../../token-associations) for the prepared official
tokenizer, source build and capture/replay commands. `runner.json` and the frozen
[protocol](../../token-associations/protocol.json) bind the runner and imported
strict wire/schema helpers. `commands.json` records actual command exits and
output hashes, with private executable/store/interpreter/cache paths substituted.

`raw-captures.tar.gz` contains exactly seven bounded regular JSON members: each
run's raw capture, summary and negative-control receipts, plus the stable
comparison. `protocol.json` registers member sizes/hashes; `manifest.json`
registers every outer file. Verify both layers before extraction. The existing
`python3 tools/verify_results.py` checks archive membership and hashes, not the
protocol conclusions. No links, private argv map, cache, interpreter, database
or binary is included.

Both live and extracted-archive replays pass. Changed declaration requests,
associated proposed counts and attributed authors are coherently rehashed and
fail their intended detectors in each run. The six control receipts identify
regenerated synthetic mutations, not additional product executions. The
63-row fresh-store comparison retains source/segment/packet/access-binding and
selection/count/provenance facts while explicitly excluding per-call producing
IDs, access-activation IDs, timing and store-size samples. Raw identities remain
bound within each producing/history pair before those comparison exclusions.

One pre-freeze pilot assertion incorrectly expected every unsupported-field
error to name associations. The verifier now checks closed input schemas and
validity of the other arguments instead of pinning error wording. A pilot
comparison also exposed per-call access-activation IDs; their exclusion is
explicit, with denial activation and access binding still checked. No final
capture failed, and no product defect is inferred from these harness corrections.

## Limits

These are submitted protocol/selection/counting observations, not independent
acceptance or evidence of semantic sufficiency, recall, completeness, truth,
authenticated authorship, performance or universal model-window safety. No model,
provider, embedding or evaluator calls occurred. Product-local canonical,
corruption, graph, admission-bound, snapshot and counter-fault tests are separate;
this archive does not claim to observe them independently. Earlier result bytes,
source pins and startup/export collection holds remain unchanged.
