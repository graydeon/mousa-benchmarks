# Mousa benchmarks

Public benchmark results, comparison dependencies, and reproduction guidance for [Mousa](https://github.com/graydeon/mousa).

These are development measurements, including failed experiments and limitations. They do not establish general superiority over other retrieval systems.

## Contents

- [results/2026-09-16](results/2026-09-16): seven unchanged historical JSON reports. The directory date records migration, not collection.
- [results/2026-09-16-exact-packing](results/2026-09-16-exact-packing): matched opt-in exact-content packing measurements, frozen fixtures, individual observations and reproduction script.
- [comparisons/qmd](comparisons/qmd): pinned optional QMD comparison dependencies.
- [migration.json](migration.json): original Mousa commit, original paths, SHA-256 digests and sizes.
- [REPRODUCING.md](REPRODUCING.md): execution and provenance requirements.

Mousa retains product tests, required CLI client acceptance, small compatibility fixtures, BEIR integration and the Go warm-path probe. Go tools import Mousa internal packages; the Python comparison runner shares code with required acceptance. Run those tools from the matching Mousa checkout. This repository does not copy the engine or replace that harness.

## Archived reports

| Report | Scope |
| --- | --- |
| current-items.json | Earlier item lifecycle measurements |
| current-cli.json | Current-query CLI measurements |
| passage-policy.json | Segmentation quality and resource tradeoffs |
| prepared-statements.json | Prepared-statement experiment, not adopted |
| prepared-diagnosis.json | Follow-up diagnosis and limitations |
| workflow-24.json | 24-document evolving workflow |
| workflow-96.json | 96-document evolving workflow |

The [Mousa research report](https://github.com/graydeon/mousa/blob/main/docs/RESEARCH.md) explains methods and limitations. Some historical entries refer to source hashes or experimental artifacts that are not public Git commits. Retaining a report does not imply every historical experiment can be rerun from this repository alone.

Run `python3 tools/verify_results.py` with Python 3.9 or later to check migrated archive membership and each new run's file sizes and hashes. This does not rerun experiments or validate conclusions.

## Adding measurements

Keep archived files unchanged. Add a dated run directory with a manifest identifying the Mousa commit, benchmark repository commit, input hashes, binary and dependency hashes, commands, environment, repetitions, raw observations and failures. Separate warm and cold measurements and disclose shared-host contention. Preserve negative results; do not tune against held-out test data.

Do not commit credentials, private source data, model transcripts, installed dependencies, binaries or local database stores. Check dataset redistribution rights before uploading corpora. For large artifacts, use versioned public archives and checksums instead of growing ordinary source history without bounds.

## License

Migrated files retain Mousa's GNU AGPL v3 license; see [LICENSE](LICENSE). Third-party dependencies retain their respective licenses.
