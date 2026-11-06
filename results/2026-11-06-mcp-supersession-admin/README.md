# MCP source-scoped replacement administration

Two fresh SQLite stores exercised a CGo-free build from the clean anonymous product checkout at `0d433832ca531703ffc61be3299e9dd496495afb` (product PR109). Its tree matches the tested product tree. This is additive stdio protocol evidence, not a release, semantic-quality, performance or authenticated-client claim.

Each capture retains 114 scheduled events, 12 stable mode/packer/budget rows, 18 independent complete-context token counts and seven rehashed controls. Both stored replays and cross-store comparison pass. The archive contains 24 regular members, with sizes and SHA-256 hashes in `archive-members.json`; the outer manifest binds the archive and accompanying reports.

## Exercised behavior

The MCP client syncs two configured sources, exports revision pins, imports synthetic vectors, declares and selects a replacement, inspects current state, deactivates with the explicit expected event and reactivates. All replacement administration uses MCP. Ingestion-only and read-only startup refuse administration; admin-only startup refuses ingestion. A native operator policy action separately denies retrieval, after which an administrative activation succeeds while status returns decision metadata only and export withholds passages. Native policy setup is not claimed as MCP policy administration.

Declaration retries and current-event retries return identical canonical records. Metadata conflicts, foreign pins/declarations, older-event retries, stale expectations and unconfigured aliases refuse. Status records no-history, active, deactivated and reactivated states. The schedule queries lexical/vector/hybrid retrieval under both packers and byte/token budgets, checks omitted/false compatibility, unembedded old/twin supporting evidence, suppression, explicit deactivation and retained producing history. Returned text, digests, coordinates and revision/segment pins are bound to the fixture/export; history support is bound to the released selection. Independent token counts cover the complete returned rendering, not separate passage counts.

Controls alter activation expectation, response source, unauthorized error, denied status state, query suppression, returned text and returned representation identity. Request/response stream hashes and embedded envelopes are recomputed. Each control must fail at its named detector; both original and modified raw frames are archived. These controls demonstrate the checked invariants, not universal tamper resistance.

## Replay

From this repository root with an offline `tiktoken==0.12.0` virtualenv and prepared `o200k_base` cache:

```sh
result=results/2026-11-06-mcp-supersession-admin
mkdir /tmp/mousa-admin-replay
tar -xJf "$result/raw-captures.tar.xz" -C /tmp/mousa-admin-replay
python3 tools/verify_results.py
/path/to/venv/bin/python mcp-supersession-admin/capture.py verify \
  --protocol "$result/protocol.json" --cache /path/to/cache \
  --output /tmp/mousa-admin-replay/first
/path/to/venv/bin/python mcp-supersession-admin/capture.py verify \
  --protocol "$result/protocol.json" --cache /path/to/cache \
  --output /tmp/mousa-admin-replay/second
/path/to/venv/bin/python mcp-supersession-admin/capture.py compare \
  --protocol "$result/protocol.json" --cache /path/to/cache \
  --output /tmp/mousa-admin-replay/first --other /tmp/mousa-admin-replay/second
```

To regenerate controls, remove neither stored capture nor reports: use a copy of a capture directory without its `controls` subdirectory, then run the producer's `controls` mode against that copy. `REPRODUCING.md` describes fresh exact-public-head collection. Use a new result directory inside this repository for `run-public.sh`; its final manifest step rejects external output directories.

## Limits and retained failures

HTTP bearer validation, concurrent writers and deliberately corrupted hidden-state tests are separate product regression evidence; this stdio capture did not execute those cases. No provider credentials, live deployment, model inference, enterprise/QMD rerun or paid benchmark was used. Synthetic vectors establish arithmetic/protocol behavior only. Author, actor, basis, reason and timestamps remain caller assertions; activation does not establish factual truth or freshness.

An initial preparation attempt failed because the capture expected `byte_length` on exported passages, which expose start/end coordinates instead. The corrected capture uses the actual transport shapes and checks byte length where supplied. Both completed captures/replays/controls then passed, but the wrapper's final manifest command rejected an external output directory. The completed bytes were retained and packaged here without recollection or relabeling; the in-repository manifest and archive gate passed separately. Earlier published producers, protocols, observations and source pins remain unchanged.
