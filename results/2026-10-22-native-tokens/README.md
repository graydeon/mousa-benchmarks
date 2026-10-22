# Native token-aware context packing observations

Capture and fresh-store reproduction target public [Mousa PR84](https://github.com/graydeon/mousa/pull/84),
head `50a1b43267177b8ea0fa690d4fae8a3c06c032d8`, tree
`bb768111ad3fb4a153f4219c9bf98dd0c53977db`. This records an open PR's public
head, not an assertion that it is merged or on main. Earlier vector, hybrid and
consumer-only token archives retain their exact producing pins.

## Source, build and backend

The clean public checkout was built with Go 1.27.1, Linux/amd64, `GOAMD64=v1` and
`CGO_ENABLED=0`. Build metadata reported the exact public VCS revision and
`vcs.modified=false`. The executable SHA256 is
`3549d1e7942aad8ad1c8fbb2353e8541165d63f0637938290836b119b64ae194`.
The build declaration and per-run pins are retained in `build.json` and each
run's `product.json`; the binary itself is not exported.

Query and independent reference counting use Python 3.13.5 and official
`tiktoken==0.12.0`, `o200k_base`, `encode_ordinary`. The explicitly prepared
vocabulary file is 3,613,922 bytes with SHA256
`446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`.
Per-run `backend.json` records runtime/encoding/cache identities. The queries
and reference counter refuse vocabulary download; preparation is separate.
No environment, cache, database, executable, model or secret data is exported.

## Results

Each run completed 48 native calls and 20 independent whole-rendering checks,
exit 0. Both source forms exercised lexical, vector-only and hybrid retrieval
with both original/exact-v1 packers. The byte-only query selected all 3 passages;
original token packing also selected 3 with the high cap, and exact-v1 selected
2 byte-distinct passages. Token pressure selected 1 whole passage, not a trim of a
returned packet. Independent ordinary-text token IDs and exact counts are
retained for every counted context in `counts.json`.

Hybrid exact-v1 observations:

| Run | Source form | Full rendering tokens (2 passages) | Pressure cap | Pressure rendering tokens (1 passage) |
|---|---|---:|---:|---:|
| Capture | JSONL | 250 | 132 | 117 |
| Reproduction | JSONL | 250 | 132 | 117 |
| Capture | Directory | 243 | 128 | 114 |
| Reproduction | Directory | 249 | 132 | 116 |

Directory roots and their canonical identities differ across fresh runs, so
provenance header token costs can differ. These are within-run exact counts,
not cross-run identity/timing goldens. All counts include complete headers and
separators; released-text byte accounting excludes them.

Both runs also passed exact-boundary fit, restart packet/context stability,
authorized v7 producing-history inspection and explicit retained-text recount.
Resyncing every item excluded all stale vectors from current hybrid retrieval
without changing producing history. Retired original text remained unarchived:
normal history reported that limitation, and explicit recount refused with an
error and empty successful stdout. Fresh deny returned no context, evidence,
proposed source counts or hybrid coverage and hid historical metadata.

Raw `commands.json` members preserve every native argv, input, stdout, stderr
and exit, including the expected retired-recount failures. Public temporary
runtime/cache aliases and directory roots are intentionally visible; no links
are exported. Driver completion exits and its source digest are in `runner.json`.

## Reproduce and verify

Follow the [driver preparation and exact-head instructions](../../native-tokens).
Use the recorded public head rather than a newer main and absent output paths.
The capture/reproduction use different fresh stores and roots with the same
pinned official backend. Run:

```sh
python3 tools/verify_results.py
```

The existing archive verifier checks registered file membership/hashes, not the
truth of behavioral claims or proof of a build/tokenizer execution. The driver
independently reconstructs expected selected rendering from exported pins and
fixture bytes, then counts it directly with the official package. No product
code is imported and no SQLite database is opened by the driver.

## Limits

This is a small synthetic native protocol/counting demonstration, not a startup,
latency, retrieval-quality, semantic truth, model-execution or answer-quality
study. The named encoding is not claimed to match an unverified model. Counts
cover the exact returned context, not arbitrary application, JSON/tool or final
model prompt framing. Caller-declared reservations are not authenticated
model-window guarantees. Product process-fault, reservation/overflow, writer and
corruption regressions are not relabeled as companion observations. Startup
issue #39 publication holds and all earlier negative observations are unchanged.

At this product pin, mixed-ancestry lifecycle-rejected candidates can retain
aligned rank/BM25 and proposed-count-slot facts in native token history even
though the ordinary candidate view omits them. That path is not covered by
these single-source ancestry fixtures; the observations do not validate its
filtering. Whole-source deny in this capture still discloses no context or
source-derived candidate/coverage facts.
