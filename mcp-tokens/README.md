# MCP measured context token budgets

This small client uses native commands to prepare a synthetic JSONL source and
supplied vectors, then sends raw newline-delimited JSON-RPC to the real Mousa
stdio server. It imports no product code and never opens SQLite. The existing
MCP retrieval/inspection helpers supply bounded frame reads, strict JSON,
canonical comparisons, stream hashes and the supported schema subset.

## Prepare and reproduce

Use the exact public product head in the dated result's `build.json`, not current
main. Build that clean checkout with the supported Go toolchain:

```sh
GOWORK=off CGO_ENABLED=0 go build -o /tmp/mousa-public-tokens ./cmd/mousa
```

Prepare the official tokenizer separately while network access is available:

```sh
python3 -m venv /tmp/mousa-tokenizer
TOKEN_PY=/tmp/mousa-tokenizer/bin/python
TOKEN_CACHE=/tmp/mousa-token-cache
"$TOKEN_PY" -m pip install 'tiktoken==0.12.0'
TIKTOKEN_CACHE_DIR="$TOKEN_CACHE" "$TOKEN_PY" -c \
  'import tiktoken; print(tiktoken.get_encoding("o200k_base").name)'
```

From this repository, with absent output paths:

```sh
"$TOKEN_PY" mcp-tokens/capture.py capture \
  --mousa /tmp/mousa-public-tokens --product-source /tmp/mousa-public-source \
  --product-head PUBLIC_HEAD --cache "$TOKEN_CACHE" \
  --output /tmp/mousa-token-capture
"$TOKEN_PY" mcp-tokens/capture.py verify \
  --cache "$TOKEN_CACHE" --output /tmp/mousa-token-capture
"$TOKEN_PY" mcp-tokens/capture.py controls \
  --cache "$TOKEN_CACHE" --output /tmp/mousa-token-capture
python3 tools/verify_results.py
```

Replace `PUBLIC_HEAD` with the full recorded product commit. Run capture again
with a different absent output path for an independent fresh-store reproduction.
Use the venv interpreter, not a resolved symlink to the system interpreter:
resolving it can lose the venv package context. The optional `--python` argument
selects the trusted server-side interpreter; its default is the driver's own
interpreter. It is never sent in a tool request. Both driver reference counting
and server execution require the prepared cache; no vocabulary fetch is allowed
during capture or replay. The package installation/preparation commands are
prerequisites, not on-demand query behavior.

## Recorded behavior

Each run retains five native inputs/stdout/stderr/exits, 107 scheduled requests,
104 response frames and three stdio exits. Raw stream records include original
base64 bytes, byte length and SHA256, including LF framing and trailing output.
The fixed source contains one multilingual/special-looking passage and two
byte-equal short passages. All three have explicitly supplied synthetic vectors.
No model or embedding service runs.

All three query modes run under `original` and `exact-v1`. The client independently
reconstructs each selected `mousa.context_text.v1` rendering from exported pins
and fixture bytes, then counts the whole string with official `encode_ordinary`.
It retains reference token IDs for 45 returned contexts per run and checks the
returned count, digest, rendered bytes, selected text/pins/ranges, byte use and
requested budget facts. Full original retains three passages; exact-v1 retains
two. Exact whole-rendering fit succeeds, one-token-short and 240-token pressure
change selection, reservations produce the same effective limit as the short
case, and a one-byte budget or zero remaining window allowance returns empty
context. These are complete rendering counts, not sums of passage estimates.

Default and false token history omit the token member; true returns the safe
recorded v7 view. Independent retrieval details expose producing vector/hybrid
facts only when requested. Trail, packet, decision, selected-candidate and lexical
request/expression relationships bind history to its producing query. Restart and
replacement of every source item preserve the recorded count/digest/ranking facts.
The restarted server has no tokenizer configuration: byte tools still succeed,
while explicit token requests fail with `tokenizer_unavailable`. Fresh denial
releases no evidence, coverage, token candidate facts or historical existence.
Null token input and an unconfigured path-looking alias fail explicitly.

Every raw request is compared byte-for-byte with the regenerated fixed schedule,
including budgets, tools and history targets. Every successful envelope is checked
against the actual discovered closed output schema. Repeated-key/nonfinite JSON
refusals and exact JSON type comparisons reuse the existing helpers. The schema
checker covers the existing bounded subset, not arbitrary JSON Schema.

## Controls and limits

Three controls rebuild copies with coherent stream hashes and matching text and
structured envelopes. An altered returned count must fail
`official-whole-context-count`; altered context with updated digest/byte facts
must fail `returned-context-rendering`; a changed scheduled token cap must fail
`scheduled-request-bytes`. Only deterministic regeneration receipts are stored,
not full mutated copies. `controls` regenerates them from retained observations.

The result establishes synthetic counting/protocol and source-policy behavior,
not semantic quality, model integration, relevance, latency, authentication,
embedding generation or universal tokenizer equivalence. Counts include returned
context headers/separators, not JSON-RPC/tool envelopes or unknown model framing.
Caller reservations do not prove full-window safety. History is a recorded
producing observation, not a new recount; retired text remains unarchived.
Worker fault/cancellation, mixed-ancestry rejection ordering and detailed invalid
input combinations remain product regression evidence rather than claims of this
single-source capture. No database, executable, cache or credential is exported.
Build/binary hashes record observed provenance, not proof a build ran. Old
archives, pins and deferred startup/export failures remain unchanged.
