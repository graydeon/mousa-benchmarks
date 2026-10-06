# Supersession declaration and activation contract checks

This record captures the pinned Mousa product regression tests for strict declaration codecs, revision-pinned SQLite persistence, immutable activation events, current projections, transition conflicts, read-only behavior, migration verification and tamper rejection. It is contract evidence from the product tests, not a held-out benchmark or a semantic-quality study.

`protocol.json` freezes the source tree, command and 35 expected top-level test names before capture. The commit is the published source commit with that tree. `go-test-events.jsonl` is raw Go test output; `observed.json` separates top-level tests from nested subtests. Timings in Go output are incidental and do not support a performance comparison.

## Reproduction

Obtain a clean checkout of the public Mousa commit recorded in `protocol.json`, install Go and its declared dependencies, then run:

```sh
python3 reproduce.py --mousa /path/to/mousa --output /path/to/new-capture
```

The runner rejects a dirty checkout, a different commit/tree, missing expected tests, skipped tests or failures. The output directory must not already exist. Tests use real temporary SQLite files; no accepted user store is opened.

## Preserved negative cases

Two regressions failed before the fixes in the pinned source: replacing an activation silently accepted a corrupt current projection, and a missing current row with retained history was reported as absent rather than an integrity failure. `before-fix-regression-output.txt` retains those observed failures. `before-fix.patch` reverses only the two production fixes while preserving the regression tests. It describes a reproducible pre-fix implementation, not a previously released public commit.

To repeat the negative cases, use a disposable checkout of the pinned product commit, apply `before-fix.patch` with `git apply --unidiff-zero`, and run:

```sh
go test ./internal/sqlite -run '^(TestSupersessionActivationRejectsCorruptStateBeforeReplacement|TestSupersessionActivationMissingStateIsIntegrityFailure)$' -count=1
```

Expected exit: 1, with both named tests failing. Discard that disposable checkout afterward. The positive capture uses the unmodified pinned source.

## Limits

Retrieval enforcement and CLI/MCP administration are absent. This record does not demonstrate client-origin activation, semantic contradiction resolution, authorization of actor labels, native-host acceptance, startup scan cost or full-window memory quality. Codec authorship labels remain untrusted. Passing product tests are not independent quality samples.

`manifest.json` binds every archive member by size and SHA-256. Existing historical archives are unchanged.

## Reproduction environment correction — 2026-10-06

The runner now sets `GOWORK=off` for Go subprocesses and records that setting in new observations, so parent `go.work` files and an inherited `GOWORK` cannot override the pinned module's dependencies. The original captured events, observation and frozen protocol are unchanged; the original observation did not record a workspace setting and must not be read as proof of environment isolation. This correction applies to new reproduction runs. It does not isolate every possible Go environment override or replace dependency verification.
