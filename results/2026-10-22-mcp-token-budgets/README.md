# MCP measured token-budget observations

Product: [Mousa PR88](https://github.com/graydeon/mousa/pull/88), exact public head
`e8829151bc1e57619c1b09a9414e29d7c6729efa`, tree
`22e23931fbab87830e6871c9ee6e22602beafd40`. This is an open-PR observation, not a
claim that the capability is merged. `build.json` records the independently built
public-head binary. `runner.json` binds the capture and reused wire helpers.
No historical archive or pin is replaced.

The [driver and reproduction commands](../../mcp-tokens) use an explicitly prepared
official `tiktoken==0.12.0`, `o200k_base`, ordinary-text backend. One capture and
one independent fresh-store reproduction each retain:

| Observation | Per run |
|---|---:|
| Native preparation/replacement/deny commands | 5 |
| Stdio sessions with actual exits | 3 |
| Scheduled request frames | 107 |
| Raw response frames | 104 |
| Whole returned contexts independently counted | 45 |
| Rehashed controls rejected at intended detectors | 3 |

The reference token IDs match across the two fixed-JSONL runs. Audit/trail IDs
are per-call values, not cross-run goldens; each run verifies its own producing
relationships. Stream records retain original base64 bytes, lengths, hashes,
framing and any trailing stdout/stderr. Both runs exited successfully, and
separate replay and controls exited zero. `negative-controls.json` contains
regeneration receipts, not copies of the mutated observations.

## Checked behavior

- Lexical, supplied-vector and hybrid tools with original/exact-v1 packing:
  selected fixture bytes, canonical pins, coordinates, exact returned rendering,
  official whole-context count/reference IDs, digest and byte accounting.
- Whole-rendering exact fit, one-token-short and fixed pressure change selection.
  Reservations constrain the same survivors as the equivalent explicit cap.
  Existing byte limits still apply; zero remaining declared allowance is valid.
  Original retains three passages; exact-v1 retains two byte-distinct passages.
- Omitted token arguments preserve byte-only property sets and stable selection.
  Omitted/false token history hides its member. Token-only history remains
  independent of retrieval-details history.
- Restart without tokenizer configuration permits byte tools but explicitly
  refuses token execution. Source replacement preserves producing v7 token facts,
  selected-candidate correspondence and recorded ranking without a recount.
- Fresh denial releases no evidence, coverage, token candidate facts or historical
  existence. Null token input and an unconfigured path-looking source alias fail.
- Rehashed count alteration fails `official-whole-context-count`. Altered context
  with adjusted digest/byte facts fails `returned-context-rendering`. A changed
  scheduled token budget fails `scheduled-request-bytes`.

## Replay these retained observations

Prepare `TOKEN_PY` and `TOKEN_CACHE` as documented in the driver instructions.
From this repository:

```sh
"$TOKEN_PY" mcp-tokens/capture.py verify --cache "$TOKEN_CACHE" \
  --output results/2026-10-22-mcp-token-budgets/capture
"$TOKEN_PY" mcp-tokens/capture.py controls --cache "$TOKEN_CACHE" \
  --output results/2026-10-22-mcp-token-budgets/capture
"$TOKEN_PY" mcp-tokens/capture.py verify --cache "$TOKEN_CACHE" \
  --output results/2026-10-22-mcp-token-budgets/reproduction
"$TOKEN_PY" mcp-tokens/capture.py controls --cache "$TOKEN_CACHE" \
  --output results/2026-10-22-mcp-token-budgets/reproduction
python3 tools/verify_results.py
```

The archive verifier checks registered bytes, not execution or token correctness;
the separate replay performs behavioral checks with the official reference.
Capture again at an absent output path to exercise the public executable and a
new store. The existing schema helper covers its documented subset only.

## Limits

Synthetic counting/protocol and authorization only: no model integration,
semantic quality, relevance, performance, general tokenizer compatibility or
model-window safety. Counts include context headers/separators, not protocol
or unknown client/model framing. Reservations are caller declarations.
Historical counts are producing observations; MCP does not recount old text.
Retired text remains unarchived. Single-source observations do not establish
mixed-ancestry lifecycle ordering, all-rejected outcomes or worker cancellation
rollback; those remain product regressions. No database, binary, vocabulary,
credentials or external embedding-generation outputs are archived. Hashes bind
observed bytes and reported provenance; they do not prove a build/tokenizer ran.
Old archives and the deferred startup/export failures remain unchanged.
