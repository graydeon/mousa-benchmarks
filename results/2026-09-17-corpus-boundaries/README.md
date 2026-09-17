# Referenced documentation coverage

Adding three pinned Git documentation fragments made four fixed questions fully
supported by correctly attributed passages under a 4,096-byte text budget. The
original corpus provided no declared support for three of them and only parent
context for the fourth. This is a source-coverage improvement, not a new retrieval
algorithm. No core engine, ranking, packing or verification behavior changed.

## Inputs and method

The product base is [Mousa 4d0ec962](https://github.com/graydeon/mousa/tree/4d0ec962eae5e80c2d63069471ae509cef91cf3e).
The comparison repository base is ead52d67feb0a8b658b1d85c58cac0ca7d54f813.
Both corpora use Git 2.51.0 revision
`c44beea485f0f2feaf460e2ac87fdd5608d63cf0`. The original has git-restore and
git-switch; the expanded corpus adds these separately attributed files:

- `Documentation/diff-context-options.adoc`: context options and defaults.
- `Documentation/includes/cmd-config-section-all.adoc`: configuration applicability preface.
- `Documentation/config/checkout.adoc`: remote selection and parallel checkout configuration.

The exact upstream bytes, per-file hashes, URLs and COPYING license are in both
archived manifests. The fragments have no further includes. Unresolved linked
manuals remain git, git-add, git-branch, git-checkout, git-config, git-reset,
git-submodule, git-worktree and gitglossary. This is not AsciiDoc rendering; no
fragment text is attributed to parent coordinates. Documents in a directory share
one source authorization domain.

`cases.json` fixes six new naturally worded development cases, exact supporting
excerpts and the completeness rubric. It was written before querying the new
material. The original five product cases are preserved byte-for-byte. A separate
22-query pilot exercised every case and both corpora, then an independent verifier
recomputed coverage and checked sources, coordinates and zero-to-one history
transitions. Pilot outcomes were inspected; no queries, rubric, consumer retrieval
logic or input bytes were tuned afterward. These are prospectively fixed
development cases, not held-out evaluation. A product acceptance test was added
for the observed parent/fragment attribution behavior before measured collection.

The accepted run contains 44 queries: 11 cases × two corpora × two repetitions.
Every query starts with a newly synchronized store, zero trails and zero policy
decisions. Arm order alternates by case and repetition. Both arms use the same
binary and consumer, passage-v1 segmentation, original packing and a 4,096-byte
budget. Every query creates exactly one trail and one policy decision. Repetition
is not additional independent quality evidence. No misses, failures or outliers
were discarded; the pilot remains separate from the accepted observations.

Execution, support coverage and answerability are distinct. Complete means all
predeclared excerpts are covered by returned byte ranges in their own documents;
partial means some; absent means none. This limited rubric does not prove that
all qualifications needed for an arbitrary answer are present. For the two
unsupported cases, review of the complete bounded corpus found no requested
support. Their lexical matches do not count as answers. The wrapper retains
`answer: null` and `support: not_assessed` on every response.

## Results

Execution passed for all 44 measured queries. All returned representation digests,
segment ranges, source URLs, line coordinates and released-byte totals verified.
Coverage and released bytes were identical across the two repetitions.

| Case | Original support | Expanded support | Released bytes, original → expanded | Budget omissions, original → expanded |
|---|---|---|---:|---:|
| Restore default source | Complete | Complete | 4074 → 4074 | 13 → 17 |
| Restore overlay | Complete | Complete | 4089 → 3833 | 7 → 8 |
| Switch detached inspection | Complete | Complete | 3946 → 3867 | 13 → 17 |
| Switch orphan files | Complete | Complete | 3912 → 3842 | 13 → 17 |
| Synthetic no-match | Absent, expected | Absent, expected | 0 → 0 | 0 → 0 |
| Restore diff context lines and setting | Absent | Complete | 3855 → 3997 | 14 → 17 |
| Interactive restore and nearby hunks | Partial | Complete | 3989 → 3945 | 13 → 18 |
| Checkout worker count | Absent | Complete | 4074 → 4070 | 13 → 16 |
| Parallel checkout threshold and overhead | Absent | Complete | 3978 → 3833 | 13 → 17 |
| Memory per checkout worker | Absent | Absent | 3945 → 3994 | 13 → 15 |
| Recovery of discarded uncommitted changes | Absent | Absent | 4055 → 4063 | 13 → 16 |

The new evidence establishes `diff.context`/three lines, inter-hunk context and
`diff.interHunkContext`/zero, the sequential worker default/logical-core behavior,
and the 100-file parallelization threshold with its subprocess-overhead rationale.
The interactive-restore case returns the parent's applicability passage **and**
the diff fragment under separate locations. All four declared supported extension
cases are reachable without keyword rewriting or parent-text injection. The
configuration preface is retained for provenance/context; no separate usefulness
claim is made for that short document.

Both realistic unsupported questions returned `evidence_available` in both arms.
The passages do not give a megabyte-per-worker memory allowance or a procedure to
recover discarded uncommitted contents. This is an observed consumer limitation:
lexical evidence availability is not support assessment. The synthetic no-match
case alone would not expose it. There are no remaining partial cases among the
four declared supported extension cases, but many other candidates were omitted
by budget, and linked manuals and full rendered context remain out of scope.

## Observed cost

Linux amd64 worker, Go 1.27.1, CGO disabled, GOAMD64=v1, GOMAXPROCS=6; six virtual
CPUs, 12 GiB VM memory, job quota 5.5 CPUs/8 GiB. The AMD host was shared, not a
dedicated benchmark machine. Each arm has 22 observations. These are descriptive
small-run measurements, not population tails or a performance adoption study.

| Quantity | Original | Expanded |
|---|---:|---:|
| Documents / current representations / segments | 2 / 2 / 18 | 5 / 5 / 23 |
| Document bytes | 15,969 | 18,615 |
| Bytes read and hashed from manifest files per ask, including COPYING | 34,734 | 37,380 |
| Outer query median | 145.17 ms | 156.39 ms |
| Observed outer minimum–maximum | 114.32–152.79 ms | 132.38–171.77 ms |
| Median user + system CPU, 10 ms resolution | 0.13 s | 0.15 s |
| Maximum process-tree max-RSS statistic | 23,684 KiB | 23,772 KiB |
| Store bytes after one query | 462,848–466,944 | 471,040–475,136 |

Outer timing includes Python startup, full manifest reads/hashes, the actual CLI,
range verification and JSON output, plus the small `/usr/bin/time` wrapper. It
excludes preparation, synchronization, build and the independent post-run verifier.
The RSS statistic is GNU time's maximum, not a sum of simultaneously resident
parent/child memory. Raw user/system/RSS values, inner consumer timing and all table
counts are retained per call. The manifest byte totals exclude reading corpus.json
itself. No separate causal estimate of hashing cost is made.

A small released-text budget does not bound total query work. This run adds only
2,646 document bytes and five segments, and starts every query without prior
history. It does not measure accumulated-history scaling, cold filesystem caches,
large corpora or isolated manifest-hashing overhead. No cache optimization or
historical-verification candidate was adopted or reevaluated.

## Evidence identity and reproduction

`raw.tar.xz` retains all pilot and measured observations, analyses, manifests,
protocols, build information and collection-time source identities.
`archive-members.json` binds its 20 regular-file members. Source snapshots are
stored as exact changed-file overlays on product base 4d0ec962; unchanged source,
including large images, is recovered from that public base rather than duplicated.
The complete source-manifest hashes verify reconstruction. Full collected source
snapshots were captured before packaging; this storage change does not alter any
observation or timing identity.

Measured binary SHA-256:
`eb4d5c28266706338ac36ec9634b36b2a3fcf67f4591bac787071d193fa0b8be`.
Measured source-manifest SHA-256:
`47ec193cdcbdae1e75b62e46ce8fe49bae5f46e9dffd23347a8c3a83c7b1947c`.
Pilot has its own identity and binary hash. Final-release documentation and checks
are separate from these measurements; later documentation changes do not relabel
the timed source. `manifest.json` checks published file hashes, not usefulness or
performance conclusions.

From a complete product checkout containing the recorded base, export that base
with `git archive --format=tar.gz -o /tmp/mousa-base.tar.gz 4d0ec962eae5e80c2d63069471ae509cef91cf3e`.
Extract raw.tar.xz into a fresh scratch directory, then run:

```sh
python3 verify.py /tmp/corpus-evidence/pilot --base-source /tmp/mousa-base.tar.gz
python3 verify.py /tmp/corpus-evidence/measured --base-source /tmp/mousa-base.tar.gz
```

To collect a new run, reconstruct the product tree from the base plus the measured
source overlay and verify all hashes. Build `./cmd/mousa` with the recorded Go
configuration, then run `run.py --product PRODUCT --mousa BINARY --original
ORIGINAL_CORPUS_ARCHIVE --output NEW_DIRECTORY`. Add `--pilot` for one repetition.
Use the full product checkout so the existing process and coordinate helpers remain
the single implementation. New measurements have new identities; they do not
replace this record.
