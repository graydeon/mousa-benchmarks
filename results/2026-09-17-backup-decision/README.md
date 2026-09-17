# Caller-reviewed SQLite backup decisions

A caller can use the executable Mousa backup example to decide whether retrieved
passages cover a Python 3.13.7 backup checklist, whether one targeted retrieval is
warranted, or whether the task remains unresolved. The software checks local
packet/reference consistency. The named caller supplies semantic judgments.
`answer: null` and `support: not_assessed` remain unchanged in retrieval output.

This is development evidence from six fixed cases over two unmodified public
CPython documentation excerpts. It is not held-out evaluation, assessor accuracy,
a general answerability result, or a performance comparison. No automatic semantic
assessor, provider or answer generator participated.

## Task, corpus and review rubric

The caller is preparing an operational checklist for `sqlite3.Connection.backup`.
The full checklist requires four facts, including their qualifications:

1. Backup works while other clients or the same connection access the database.
2. `pages` limits pages per step; zero or negative copies the database in one step.
3. A progress callback receives integer status, remaining pages and total pages
   for each iteration.
4. The connection context manager commits or rolls back transactions but does not
   close connections; the backup example closes source and target explicitly.

A separate task asks for a maximum completion time under concurrent writes.
Neither bounded excerpt supplies that guarantee. This absence finding comes from
review of the complete included excerpts, not from the engine or an empty result.
It makes no claim about all Python or SQLite documentation.

The corpus contains 3,970 document bytes in `backup.rst` and `context.rst`, extracted
without rewriting from CPython 3.13.7 revision
[`bcee1c322115c581da27600f2ae55e5439c027eb`](https://github.com/python/cpython/tree/bcee1c322115c581da27600f2ae55e5439c027eb).
The manifest preserves the full upstream file hash, exact excerpt byte offsets,
starting lines, immutable links, document hashes and Python license attribution.
LICENSE is retained but not indexed. No additional documents or rewritten source
were added after inspecting retrieval results. Deterministic consumer boundary
tests use separately labeled original text, not these usefulness observations.

## Fixed method

`cases.json` in each captured product source fixes the six initial questions,
required facts, budgets, expected decisions and two follow-up questions before
retrieval. `inspection/cases-before-retrieval.json` preserves the initial case set.
An inspection run collected six initial packets. The caller then reviewed the
returned passages and authored `reviews.json`. Its coordinates instantiate
references to passages already returned; they never select passages for retrieval,
change a query or inject missing support. These are curated demonstration
assessments, not an automatic assessor's predictions.

The complete fixture/run/analyze pipeline then passed a separate pilot. One
measured run followed: six fresh stores, one repetition per case, eight queries
including exactly two follow-ups. No query, corpus or byte budget was retuned to
obtain a desired result. All original, partial and unsupported outcomes remain.
Repeated pilot and measured cases are repeated observations, not additional
independent quality evidence.

The caller review binds the exact saved JSON SHA-256 and references existing
packet/segment IDs. Follow-up retains the original query, exact original saved
JSON and requesting assessment. It targets one explicitly missing fact and has
a one-attempt budget. A new review assesses both packets without silently carrying
forward the old judgments. All required facts must be `supported` for `covered`.
Missing, partial, unsupported and contradictory judgments do not count as support.

## Results

All eight measured queries executed successfully, and all saved citations,
normalized source coordinates, hashes, references and accounting checks passed.
Those consistency results are separate from completeness under the declared
caller rubric.

| Fixed case | Initial caller coverage | Decision before → after follow-up | Follow-ups | Released bytes | Whole-consumer ms |
|---|---|---|---:|---:|---:|
| Complete checklist | 4/4 supported across multiple passages | covered → covered | 0 | 3,397 | 341.80 |
| Partial-query hypothesis, budget 180 | 0/2 assessed; no passage returned | unresolved → unresolved | 0 | 0 | 329.03 |
| Backup-only checklist | 3/4 supported; closure qualification partial | retrieve → covered, 4/4 | 1 | 4,321 | 637.56 |
| Completion-time guarantee | 0/1 supported; deadline absent | unresolved → unresolved | 0 | 2,163 | 335.43 |
| Deadline follow-up | 0/1 supported before and after | retrieve → unresolved | 1 | 4,326 | 648.49 |
| One-byte checklist budget | 0/4 assessed; no passage returned | unresolved → unresolved | 0 | 0 | 300.89 |

The 180-byte case missed its predeclared mechanism: it was intended to expose
partial applicability context, but its matching passage did not fit. It remains
a byte-budget omission, not a successful partial-context example. The backup-only
case independently demonstrates partial coverage: the returned example closes
connections, but the context-manager qualification was not retrieved. The fixed
follow-up `context manager neither closes connection` returned that qualification
and changed the caller-assessed task to covered.

The deadline follow-up returned passages about the interval between backup
attempts, not a maximum completion time. Its decision changed from `retrieve` to
`unresolved` because the attempt was consumed, not because coverage improved.
These lexical matches illustrate why `evidence_available` and released bytes do
not establish semantic support.

### Observed failure categories and actions

- **Support absent from the bounded corpus:** the completion-time guarantee.
  Stop after the declared budget. Another query cannot create a guarantee missing
  from these excerpts; seek another authority or leave the task unresolved.
- **Support present but not retrieved:** the context-manager qualification is in
  `context.rst`, but the initial `backup` query does not return it. One explicit
  query directed at the missing fact recovers it.
- **Necessary applicability context missing:** the backup example's explicit
  `close()` calls do not alone establish the context manager's cleanup semantics.
  Mark closure partial until its explanatory note is returned and reviewed.
- **Support omitted by the byte budget:** budgets 180 and 1 return no passage.
  The larger fixed case shows that the requested facts exist; the runtime still
  does not infer unreturned support merely from a budget-omission count.

The next product investment suggested by this run is **context completeness**:
help a caller retrieve an associated applicability note alongside a procedure
without treating a lexical match as a complete checklist. This evidence does not
justify another annotation database, corpus expansion campaign, performance
optimization or automatic semantic-abstention model.

## Costs and measurement limits

Whole-consumer time starts immediately before initial retrieval and ends after
the final assessment. It includes Python startup, CLI execution, packet writes,
verification, template creation and deterministic fixture binding. It excludes
build, corpus preparation and sync, and excludes human reading/authoring time.
It is not end-to-end human task latency. Six measured observations have a median
338.62 ms; single-query cases span 300.89–341.80 ms and the two follow-up cases
span 637.56–648.49 ms. Total released bytes are 14,207, counting each query's
release, including repeated text in follow-ups.

Each store starts with zero query trails and ends with one or two, as recorded
by the fixed invocation sequence. These are protocol counts, not a historical
scaling study. All measured stores were 430,080 bytes before and after retrieval.
Documents and corpus bytes are recorded separately from returned segment counts.
The shared-host Linux x86-64 environment used Go 1.27.1 and a six-vCPU EPYC-compatible
VM with a 5.5-core job quota. These timings are descriptive; there is no baseline
comparison, cache control, confidence interval or universal latency claim.

Offline packet checking does not establish current authorization or source state.
Consumer regressions cover updated sources, denied/withdrawn new retrievals,
retained historical output, missing references and equal text from distinct
sources. Saved judgments neither grant access nor erase already released bytes.
The local CLI, saved manifest/files and caller identity declaration are trusted.
Checksums do not authenticate a complete rewriting of data and metadata, and
structural validation cannot detect every incorrect semantic judgment.

## Source identities and reproduction

Product base: `32c31217b7dc0f699e4dbbb17d4020d960c5a288`.
Companion base: `bd9a63c6cb5ccbb4e1c3f91f22a1afd4ec420c97`.
Pilot and measured identities are separate in `raw.tar.xz`; each records every
captured source file hash, binary hash/build metadata, method/input hashes and
collection ownership. Full source snapshots were captured before the queries.
For distribution, source deltas reconstruct those exact member bytes from the
public product base, without duplicating unchanged image assets. Original gzip
container bytes, compiled binaries and local database stores are not distributed;
their capture hashes remain recorded. Packets, judgments, command outputs and all
observations are retained. No timings are relabeled as final-release measurements.

`methods-collected/` preserves the exact run/analyze code used for collection.
The published analyzer adds only a source-delta reconstruction verification path;
it does not change observed decisions or timing records. Product release
navigation/documentation can differ from captured source; use the archived source
manifest and delta for an exact reproduction. `manifest.json` checks public file
membership/hashes; `archive-members.json` checks every raw regular-file member.

From a separate Mousa checkout, create the base archive:

```sh
git archive 32c31217b7dc0f699e4dbbb17d4020d960c5a288 > /tmp/mousa-base.tar
```

From this repository, verify hashes, reconstruct both captured source trees and
reassess every saved packet against its corpus snapshot:

```sh
python3 tools/verify_results.py
PYTHONDONTWRITEBYTECODE=1 python3 results/2026-09-17-backup-decision/verify.py --base-source /tmp/mousa-base.tar
```

For a new run, use a reconstructed captured source tree, build its CLI, and pass
it explicitly. The runner refuses existing output directories and changed frozen
corpus/case/review hashes. New timings are a new run, not replacements for these
observations.

```sh
CGO_ENABLED=0 go build -o /tmp/mousa ./cmd/mousa
python3 /path/to/mousa-benchmarks/results/2026-09-17-backup-decision/run.py --product "$PWD" --mousa /tmp/mousa --output /tmp/backup-run --phase measured
python3 /path/to/mousa-benchmarks/results/2026-09-17-backup-decision/analyze.py /tmp/backup-run --product "$PWD"
```
