# Lexical token budgets, declared support and supersession

Two fresh writable stores completed the native directory/JSONL and configured stdio
MCP workflow against public Mousa
[`889fe11f54798e8b1409bbcdd40a67e5f5dd4d42`](https://github.com/graydeon/mousa/commit/889fe11f54798e8b1409bbcdd40a67e5f5dd4d42)
([PR106](https://github.com/graydeon/mousa/pull/106), open for independent acceptance
at capture). Its tree is `0b36603b69d5ba8298aa8fbcb7b2bd5b78a5b4c3`.
The executable was built from a clean anonymous checkout of that exact public head
with Go1.27.1, `CGO_ENABLED=0` and `GOAMD64=v1`; its SHA256 is
`9ee5456ed4a341b6e2939f59f797ccb722d45d11ac30152eb2c7c51294eec44d`.
This is not evidence from an unpublished local product revision or an earlier binary.

## Observed results

| Check | First store | Second store |
|---|---:|---:|
| Native commands, with scheduled exit assertions | 76 PASS | 76 PASS |
| MCP frames, including one notification | 29 PASS | 29 PASS |
| Independently counted complete returned contexts | 46 PASS | 46 PASS |
| Rehashed semantic controls rejected at named detector | 4 PASS | 4 PASS |
| Offline schedule/content replay | PASS | PASS |

Both passes used the same frozen executable and protocol. Comparison passed all
60 stable token/history rows and eight byte-compatibility rows. Only enumerated
per-call request/decision/trail identities and timing fields are excluded from
cross-store comparison. Raw values remain retained and producing history IDs
are checked against their own query; packet IDs remain compared. The second
store is a fresh-state reproduction of the same synthetic cases, not additional
independent retrieval-quality evidence.

The schedule exercises both original/exact-v1 packing policies:

- Native directory/JSONL and MCP token triples with suppressed primary and target
  predecessors, surviving support, exact token fit and one-token/one-byte misses.
- Whole-render reconstruction from evidence and an independent official
  `tiktoken==0.12.0` `o200k_base.encode_ordinary` count, digest and rendered-byte
  check. Headers and separators count; body bytes remain separately budgeted.
- V13 producing history, native retained-text recount, unfired/no-association v8,
  omitted/false supersession equality and uncurated predecessor retention.
- Existing byte-only composition on both source forms, explicit empty CLI flag
  compatibility versus pre-open rejection, and vector/hybrid MCP association refusal.

Controls change the scheduled supersession request, returned token count,
recorded target suppression and an embedded text-envelope duplicate key.
After recomputing stream bytes/hashes, they fail `scheduled-request-bytes`,
`independent-count`, `history-target-suppression` and `strict-json`, not an outer
archive digest check. Each deliberately invalid control copy and receipt is retained.
Both outer frames and their embedded textual JSON envelopes reject duplicate keys.

## Retained files and replay

`protocol.json` freezes product head/tree, fixture and producer/helper hashes.
`raw-captures.tar.gz` contains twelve regular files: both full captures, summaries and
eight invalid control copies. `archive-members.json` records exact uncompressed
member sizes and SHA256 values. No database, executable, dependency, cache, symlink
or credential is exported. Synthetic `/tmp` identities were chosen before capture;
raw argv/frames/outputs/exits are not rewritten. Local interpreter/cache aliases
still refer to the prepared venv and official vocabulary, not a system-Python
substitution.

Prepare the official backend/cache as described in the product usage guide. From
this repository, use a new extraction directory:

```sh
REPLAY=$(mktemp -d)
tar -xzf results/2026-11-06-token-association-supersession/raw-captures.tar.gz -C "$REPLAY"
PROTOCOL=results/2026-11-06-token-association-supersession/protocol.json
for run in first second; do
  "$TOKEN_PY" token-association-supersession/capture.py verify \
    --protocol "$PROTOCOL" --cache "$TOKEN_CACHE" --output "$REPLAY/$run"
done
"$TOKEN_PY" token-association-supersession/capture.py compare \
  --protocol "$PROTOCOL" --cache "$TOKEN_CACHE" \
  --output "$REPLAY/first" --other "$REPLAY/second"
```

To regenerate controls without overwriting retained invalid copies, copy just the
capture and summary into a fresh scratch directory:

```sh
CONTROLS=$(mktemp -d)
cp "$REPLAY/first/capture.json" "$REPLAY/first/summary.json" "$CONTROLS/"
"$TOKEN_PY" token-association-supersession/capture.py controls \
  --protocol "$PROTOCOL" --cache "$TOKEN_CACHE" --output "$CONTROLS"
python3 tools/verify_results.py
```

The archive verifier checks registered bytes/hashes; the producer replay additionally
checks the finite schedule and semantic bindings. Neither authenticates historical
execution, proves all conceivable tampering detectable, nor replaces canonical
store integrity or writer-snapshot product tests. Retained counts are producer
facts; replay independently recounts exact contexts with the prepared backend.

For new collection, use the [sequential runner](../../token-association-supersession/run-public.sh)
with a clean exact-public-head checkout and matching CGo-free executable. The
fixed synthetic directory must not exist before capture; captures run sequentially.
The runner refuses existing output/protocol paths. Do not relabel a new head as
these observations.

## Limits

This is a bounded synthetic interface/selection/counting capture, not answer
quality, relevance, factual truth, authenticated authorship, performance or model
window safety. Unknown final application prompts and tool/JSON framing are outside
the counted context. Relationships are declared input, not access grants. Internal
canonical corruption, cancellation rollback and concurrent writer properties are
product-test evidence, not inferred from these client receipts.

All historical producers, protocols and result directories remain unchanged,
including earlier token-triple refusals at their original product heads and the
failed4MiB/measured8MiB enterprise observations. No enterprise retrieval campaign,
QMD setup retry, embedding/generation/judge API or model-quality experiment ran.
