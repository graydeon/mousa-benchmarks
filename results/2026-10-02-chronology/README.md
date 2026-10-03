# Named-source chronology and native mode comparison

The frozen release completed all 84 planned operations: 16 lifecycle steps,
16 fresh status checks, 16 lifecycle queries, four saved historical inspections,
16 mode queries and 16 matching trail inspections. All mechanical assertions
passed. The deliberately invalid native sync remains an operation FAIL with
one committed item and failure at item two; its expected-failure assertion is
PASS. Current source counts finish at nine alpha items and one beta item.
No native core change was required.

Measured product source: local commit `107e8785e3addc4a58d259289d4da6bb25801537`,
tree `b6f4a655327ff64bf7744734159e1a221e326d0f`, clean at capture. This is a
local source identity, not an assertion that the commit is public. Exact source
members are in `source.tar.xz`; their hashes are in `protocol.json` and the run
summary. The native binary was built from the unchanged Go source at
`caecfb6073c6299a8333f41bb87ef41cbb49641e` with Go 1.27.1, CGO disabled and
GOAMD64 v1. Later documentation/publication commits are not relabeled as the
measured source. The binary SHA-256 is recorded, not a promise that rebuilding
with different VCS/toolchain metadata yields byte-identical executables.

## Mechanically derived observations

Four independently authored cases have four mode observations each. Required
span coverage means full containment of frozen normalized source byte ranges;
it is not semantic answer correctness. `0/0` means no required span label, not
abstention or support. Evidence bytes and rendered context bytes are different
units. The consumer releases no generated answer.

| Case | Query policy | Packing | Required spans covered | Evidence bytes | Context bytes | Released passages | Irrelevant passages | Budget omitted | Duplicate omitted |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| packing | original | original | 0/1 | 22 | 515 | 2 | 2 | 1 | 0 |
| packing | original | exact-v1 | 1/1 | 33 | 532 | 2 | 1 | 0 | 1 |
| packing | dedup | original | 0/1 | 22 | 515 | 2 | 2 | 1 | 0 |
| packing | dedup | exact-v1 | 1/1 | 33 | 532 | 2 | 1 | 0 | 1 |
| unicode | original | original | 1/1 | 32 | 347 | 1 | 0 | 0 | 0 |
| unicode | original | exact-v1 | 1/1 | 32 | 347 | 1 | 0 | 0 | 0 |
| unicode | dedup | original | 1/1 | 32 | 347 | 1 | 0 | 0 | 0 |
| unicode | dedup | exact-v1 | 1/1 | 32 | 347 | 1 | 0 | 0 | 0 |
| small-budget | original | original | 0/1 | 0 | 128 | 0 | 0 | 1 | 0 |
| small-budget | original | exact-v1 | 0/1 | 0 | 128 | 0 | 0 | 1 | 0 |
| small-budget | dedup | original | 0/1 | 0 | 128 | 0 | 0 | 1 | 0 |
| small-budget | dedup | exact-v1 | 0/1 | 0 | 128 | 0 | 0 | 1 | 0 |
| near-match | original | original | 0/0 | 26 | 356 | 1 | 1 | 0 | 0 |
| near-match | original | exact-v1 | 0/0 | 26 | 356 | 1 | 1 | 0 | 0 |
| near-match | dedup | original | 0/0 | 26 | 356 | 1 | 1 | 0 | 0 |
| near-match | dedup | exact-v1 | 0/0 | 26 | 356 | 1 | 1 | 0 | 0 |

Exact packing retained the required repair span in this duplicate-content case;
original packing selected two irrelevant copies and omitted it. Both query
policies had the same observed coverage here. The multibyte passage was released
at 64 bytes but entirely omitted at one byte. Every near-match arm released a
lexical passage despite having no required span. Across the 16 observations,
6 of 12 required-span observations were covered and 10 of 16 released passages
were irrelevant to the frozen labels. These are repeated observations of four
cases, not sixteen independent quality cases or an answer-harm rate. No policy
was tuned against these results, and neither default was changed.

Selected source/item/representation identities and actual omission metadata are
in `analysis.json`. Original trails expose no explicit omission reason; exact
trails expose budget/duplicate reasons and duplicate relationships. All 16 query
packets agreed with their inspected trails. Four older selections retained their
original packet/segment identities under fresh authorization; their `indexed_now`
flags agreed with final activation, including the explicitly reverted original.
Inspection released no historical text. Synthetic author/date/URI labels do not
establish authenticated authorship.

## Preserved failures and evidence

- `failed-smoke.tar.xz` and `failed-smoke-analysis.json` retain the first unmeasured
  pipeline smoke. Three assertions failed because its draft expected action
  labels incorrectly used removed/unchanged/added for delete/repeated-delete/
  restore. The authoritative native contract uses deleted/absent/restored.
  Corrected prospective labels were frozen before release acceptance. This was
  a scenario-definition defect, not a Go defect or policy optimization.
- `incomplete-run.tar.xz` and `incomplete-run-analysis.json` retain a real native
  startup failure with a nonexistent store parent. One operation was attempted;
  later operations did not run. Missing initialization capture is INCOMPLETE,
  not lifecycle PASS. The analysis uses the final analyzer; the captured run
  retains its earlier runner/analyzer hashes.
- A separate consumer normalization regression found that passing already
  normalized input to the existing verifier stripped a second leading BOM.
  The consumer now supplies raw revision text to the verifier. A real native
  query failed before and passed after; its permanent double-BOM regression
  and ordinary normalization/attribution tests passed. Native normalization and
  validation were not weakened.

The archives contain regular contained members only. `protocol.json` records
every member size and hash; the repository manifest binds the archive bytes.
Native decoded JSON request/response members are unchanged. Public stdout
projections omit local invocation/server argv and operational tracebacks,
recording original member hashes and omitted fields. Original local captures
remain separate; public projections are not represented as original stdout.
Source and binary/input identities, native outcomes, exit codes, committed-prefix
counts and rendered evidence remain available. Hashes prove internal consistency,
not authenticity against wholesale rewriting. Earlier smoke source hashes are
retained; only the final release source snapshot is supplied here.

## Reproduce and verify

See [the runnable fixture workflow](../../datasets/chronology/README.md).
To inspect this captured release, extract only the regular contained archive
members into a new scratch directory, then run:

```sh
python3 datasets/chronology/analyze.py /tmp/chronology-capture/release
python3 datasets/chronology/analyze_test.py --run /tmp/chronology-capture/release
python3 tools/verify_results.py
```

These checks passed on the captured release and public projection. The archive
verifier checks outer membership/hashes and every registered tar member; the
analyzer additionally checks frozen operation order, native/report agreement,
normalized bytes/attribution, budget accounting and current/historical selection.
Integrity regressions reject omitted/substituted members, missing responses,
reordered epochs and fabricated success reports. Neither checksum verification
nor these deterministic scenarios establish successful model-driven use.

Native-host/model-driven acceptance, semantic answering, authenticated origin,
verified tokenizer/full-window safety and performance claims remain NOT RUN.
The frozen September 30 project-history result directory is unchanged.
