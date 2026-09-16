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

## Product correctness gate

This remains entirely inside Mousa and requires no companion checkout, Node, QMD, downloaded datasets or inference services:

```sh
CGO_ENABLED=0 go build -o mousa ./cmd/mousa
python3 eval/local/workflow_test.py --mousa ./mousa
```

## BEIR and lifecycle tools

Run cmd/beir, eval/beir and eval/local/lifecycle.py from the Mousa checkout using its revision-specific instructions. These tools share internal product contracts or acceptance helpers. Store suitable comparative results here with both repository revisions and input hashes.

Research summaries stay in Mousa; links to migrated observations are pinned to immutable commits here. Small compatibility golden files stay beside product tests.
