# Corrected lexical supersession and token-budget observations

Both passing runs use public Mousa head `2d13d9f0ef708e7dec89d6a28b5213d96b229c8e`,
tree `0769142839a603323fe1711e69ae19a77962f4c4`, built from a fresh anonymous
checkout with Go 1.27.1 and `CGO_ENABLED=0`. [Build identity](build.json),
[official backend/cache](backend.json) and [driver/fixture/command bindings](protocol.json)
are retained. These are new observations, not renamed earlier captures.

| Run | Native commands | Expected native failures | MCP requests | Raw MCP responses | Clean MCP exits | Whole-context counts | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| Capture | 40 | 2 | 37 | 33 | 4 | 24 | PASS |
| Fresh-store reproduction | 40 | 2 | 37 | 33 | 4 | 24 | PASS |

The [driver](../../token-supersession) uses native sync/export, ordinary queries
and revision-pinned declaration/activation commands, then native queries/history
and configured stdio MCP. It never imports product packages or opens SQLite.
Both packers release the retained twin and successor, not the withheld predecessor.
Directory/JSONL no-history and active queries, normal/recount history, MCP
exact/one-short/reservation boundaries, independent history opt-ins, all-withheld
empty context, deactivation and old producing history remain covered.

## Aggregate-bound regression

Native JSONL sync replaces the predecessor with 65 full-size 4096-byte segments:
266240 bytes, above the unchanged 262144-byte token aggregate admission limit.
Ordinary queries prepare pins; vector export is not used for this oversized source.
Both native/MCP packers return empty context for the all-withheld query, with
65 exclusions and `supersession_excluded`, or select only `boundarysmall survivor`
when that small candidate also matches. The full survivor rendering is 124 ordinary
tokens; empty context is zero. Native normal/recount and MCP history retain all
65 withheld identities, 4096-byte sizes, positive accepted ranks and null proposed
counts. Withheld bytes never appear in returned rendering.

Two nonsuppressed token requests, one per packer, still fail with exit 1, empty
stdout and `mousa: token candidate bytes exceed bound`. They are expected failure
controls, not failed capture attempts. No limit is raised and no lifecycle row
is reclassified. Arbitrary graph ancestry and damaged canonical stores remain
product-local coverage, not claims from this supported-client fixture.

The small fixed-alias full context remains 248 ordinary tokens; exact fit preserves
it. A cap of 247, or equivalent reservations, retains one whole passage at 123 tokens.
Directory header identities vary with the temporary absolute path, so their counts
are rederived rather than frozen across runs. Every returned rendering is rebuilt
from the observed retained pins and fixture text before official counting/hash checks.
The [paired comparison](comparison.json) matches all 21 fixed-alias JSONL/MCP
reference observations, including the eight aggregate-bound contexts.

## Attempts and producing-pin history

An earlier attempt at this corrected product pin completed all 85 client events,
then its runner failed with `KeyError: 'budget_omitted'`: it incorrectly required
MCP-only population/budget fields on the native token response. The failed raw
capture, producing runner and exit/cause receipt remain in `failed-attempt/` in
the raw archive. It is not counted as a passing capture. The corrected runner checks
those fields on MCP and full canonical candidate metadata through native history;
both surfaces still require exact rendering/count/digest, selection and exclusions.
The original traceback remains retained separately; machine-specific paths are
not published. No product error was hidden and no deadline was increased.

The earlier unpublished candidate at companion commit
`a4ce09715a55a12a87a683daeda4660b0040c765` observed defective product head
`346a37944faa3e84adf565f9cb5ece46bebea47a`. Its producing-pin history is recorded in
[protocol.json](protocol.json), and its bytes remain in Git ancestry. It was never
published as accepted evidence and is superseded by these new captures. Every
older public archive/protocol remains byte-identical. The
[original review finding](https://github.com/graydeon/mousa/pull/90#discussion_r4356910265)
and [issue91](https://github.com/graydeon/mousa/issues/91) identify the correction.

## Replay and controls

The lossless [raw archive](raw-captures.tar.gz) contains seven regular files:
the two passing captures and summaries, plus the failed attempt's capture, runner
and receipt. [Member sizes/hashes](raw-members.json) bind uncompressed bytes;
there are no links or database snapshots. Each capture retains scheduled native
arguments/UTF-8 input, exact output/error bytes and exits, raw JSON-RPC requests/
responses and process-tail/error/exit receipts. Runtime operands use explicit
bindings described by the driver. Streams include complete base64 bytes, sizes
and hashes. The outer manifest hashes every result file.

Run with the prepared official venv/cache from the repository root:

```sh
REPLAY=$(mktemp -d)
tar -xzf results/2026-10-24-lexical-token-supersession/raw-captures.tar.gz -C "$REPLAY"
for run in capture reproduction; do
  "$TOKEN_PY" token-supersession/capture.py verify --cache "$TOKEN_CACHE" \
    --output "$REPLAY/$run"
  "$TOKEN_PY" token-supersession/capture.py controls --cache "$TOKEN_CACHE" \
    --output "$REPLAY/$run"
done
python3 tools/verify_results.py
```

Both offline replays and both control runs exit 0. Coherently rehashed changed
requests fail `scheduled-request-bytes`; wrong withheld counts fail `withheld-count`;
wrong historical selection fails `historical-selected`. Compact control receipts
retain mutated-report hashes/detectors; mutated copies are regenerated, not stored.
These are specific consistency detectors, not proof against a malicious producer.

To repeat the fixed-alias comparison:

```sh
python3 - <<'PY'
import json
import tarfile
from pathlib import Path
root = Path("results/2026-10-24-lexical-token-supersession")
with tarfile.open(root / "raw-captures.tar.gz") as archive:
    def observations(run):
        rows = json.load(archive.extractfile(run + "/summary.json"))["reference_counts"]
        return [row for row in rows if not row["label"].startswith("directory/")]
    assert json.dumps(observations("capture"), sort_keys=True) == json.dumps(
        observations("reproduction"), sort_keys=True)
print("PASS: fixed-alias reference rendering observations match")
PY
```

## Limits

Synthetic client/counting evidence only: no semantic quality, model-driven task,
performance or full-window claim. Counts exclude JSON and unknown application/model
framing. MCP exposes producing measurements without recounting; native recount
requires retained selected text. Graph/lifecycle-rejected derivations, corruption,
writer ordering and process cancellation/reaping are separate product-local tests.
Vector/hybrid/association supersession remains unsupported. Startup/export studies
remain deferred with historical failures and pins preserved. Independent review
accepts the final product and companion heads; archive PASS alone is insufficient.
