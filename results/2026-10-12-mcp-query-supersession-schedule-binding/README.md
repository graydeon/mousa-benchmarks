# MCP query supersession acceptance — frozen schedule binding

Synthetic stdio client evidence at Mousa PR69 commit `7ae0d8768e7cd203c48478412b493e1255c97b11`, tree `2b8b14f76e0907f3ca3fd5dc8c33934567e61d14`. This capture retains the product pin and the 39 frozen selection cases.

The final runner compares recorded metadata with the frozen schedule using canonical JSON as well as binding wire requests to that metadata. The preceding strict-binding revision still used Python equality at the first boundary: changing both metadata and wire from `true` to `1`, with matching recorded assertion receipts and recomputed hashes, could verify successfully. The focused regression rejects `true` → `1`, `false` → `0`, and `4096` → `4096.0`, while allowing object-key reordering. It fails on the preceding public head and passes on the corrected runner; `schedule-regression.json` records the boundary and source hash.

| Evidence | Observed result |
|---|---|
| Pilot, capture and fresh independent-store reproduction | 129 steps, 2847 assertions, no failures each |
| Stable selection cases | 39; identical between capture and reproduction |
| Archived replays | All accepted observations verify successfully |
| Generated negative controls | All 21 reject, with their expected detectors |
| Forbidden write | Capture exits 1 with the unchanged-all-tables assertion failing; replay exits 2 |
| Frozen schedule regression | Two tests pass, including three typed substitutions and key-order control |

The four complete observation archives contain their own runner, protocol, provenance and member hashes. The 21 mutated controls are regenerated from the accepted capture; their receipts are stored rather than duplicating complete archives. The earlier result directories remain historical observations of their own runners. Capture-time companion commit `7dc1e85abe2c9cffce17415301eadcf00d3d1e7c` precedes the commit adding this evidence directory. Original contributor Jah-yee's PR28 commit is retained in that history.

## Reproduce

Use the pinned product checkout and binary with the repository's `mcp-query-supersession/run.py capture`, then `verify`, as described in [REPRODUCING](../../REPRODUCING.md). Offline replay uses the runner copied inside each observation archive. Run `python3 mcp-query-supersession/test_request_schedule.py` for the focused schedule regression and `python3 tools/verify_results.py` for archive integrity.

## Limits

Synthetic client-boundary behavior only: no semantic truth, retrieval quality, ranking quality, performance, authentication or native-host acceptance. Opted-in trail inspection is unimplemented. Oversized frames over 2 MiB and concurrency are untested. Call-level refusal does not prove transaction rollback or physical store integrity. Matching source and binary pins do not establish a reproducible build on another toolchain. Preparation and discovery baseline receipts retain their original provenance.
