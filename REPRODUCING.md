# Reproducing comparisons

Use separate checkouts of Mousa and this repository. Record explicit revisions for both. Historical result metadata must not be relabeled after migration.

## CLI and warm-path comparison

From a Mousa checkout, with this repository at ../mousa-benchmarks:

```sh
mkdir -p ../mousa-benchmarks/.runs
CGO_ENABLED=0 go build -trimpath -buildvcs=false -o ../mousa-cli ./cmd/mousa
CGO_ENABLED=0 go build -trimpath -buildvcs=false -o ../mousa-warm ./eval/local
npm ci --prefix ../mousa-benchmarks/comparisons/qmd --ignore-scripts --omit=optional --no-audit --no-fund
python3 eval/local/workflow.py --mousa ../mousa-cli --warm ../mousa-warm --qmd ../mousa-benchmarks/comparisons/qmd/node_modules/@tobilu/qmd/bin/qmd --dependency-lock ../mousa-benchmarks/comparisons/qmd/package-lock.json --documents 24 --repeats 3 --output ../mousa-benchmarks/.runs/workflow-24.json
```

Use runtime versions supported by the selected harness revision. QMD is exercised in lexical mode, not as a complete RAG comparison. Native dependency requirements vary by platform. Install scripts are disabled deliberately; do not enable them automatically to repair installation failures.

The runner hashes the explicitly supplied dependency lockfile. Record this repository's commit alongside the report: the product source manifest no longer includes relocated dependency files. New observations can differ with source revision, hardware, cache state, contention and runtime versions.

## Supersession contract checks

The [supersession archive](results/2026-10-06-supersession-core) freezes an earlier
Mousa commit/tree and expected test names. Check out the exact public commit in
its `protocol.json`, not current main, then run:

```sh
python3 results/2026-10-06-supersession-core/reproduce.py --mousa /path/to/pinned-mousa --output /path/to/new-capture
```

The checkout must be clean and the output directory must not exist. The runner
sets `GOWORK=off`, records that setting in new observations, and rejects failed,
skipped or missing expected tests. It does not isolate every Go environment
setting. The original archive's events, observation and protocol remain unchanged;
they do not certify later product fixes or prove historical workspace isolation.
The run README also explains how to reproduce the two preserved negative cases
in a disposable checkout. No live user store or model is needed.

## Native supersession administration capture

The [administration archive](results/2026-10-07-native-supersession-administration)
freezes one source revision, the synthetic JSONL/declaration/activation inputs and
the expected CLI behavior, then drives only the native CLI against a fresh synthetic
store. Check out the public commit in its `protocol.json`, not current main, then run:

```sh
python3 results/2026-10-07-native-supersession-administration/reproduce.py \
  --mousa /path/to/pinned-mousa --output /path/to/new-capture
```

The checkout must be clean and at the pinned commit and tree, the frozen input hashes
must match, and the output directory must not exist. Add `--work <new-directory>` to
keep the throwaway binary and synthetic stores. The runner sets `GOWORK=off` and
`CGO_ENABLED=0`, hashes the executable without publishing it, writes only
`observed.json` and `assertions.json`, and exits 2 when a precondition fails and 1 when
an assertion fails. It opens no accepted or live store and needs no network, model or
inference service. Its README explains the frozen-input provenance, the exact
assertions and the disposable negative controls.

## Product correctness gate

This remains entirely inside Mousa and requires no companion checkout, Node, QMD, downloaded datasets or inference services:

```sh
CGO_ENABLED=0 go build -o mousa ./cmd/mousa
python3 eval/local/workflow_test.py --mousa ./mousa
```

## BEIR and lifecycle tools

Run cmd/beir, eval/beir and eval/local/lifecycle.py from the Mousa checkout using its revision-specific instructions. These tools share internal product contracts or acceptance helpers. Store suitable comparative results here with both repository revisions and input hashes.

Research summaries stay in Mousa; links to migrated observations are pinned to immutable commits here. Small compatibility golden files stay beside product tests.
