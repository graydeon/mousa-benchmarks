# Git interactive-hunk citation layout under 512 rendered-content tokens

The pinned Git 2.51.0 question can retain both the answer-bearing `diff-context-options.adoc` fragment and its `git-restore.adoc` parent passage under the 512-token rendered-content limit. The caller removes a redundant document path from each citation header; the full revision-pinned source URL still identifies the path, and the line range and passage text remain intact. This is one development question. No model answer, independent answerability assessment or full model-window accounting was performed.

## Fixed input and method

`protocol.json` records the exact question, Git revision and archive/file hashes, baseline Mousa tree, byte budget, tokenizer, original prompt layout, expected citation directive and pre-edit protocol hash. The original source path used for the historical segment IDs differs from this run's temporary path; segment IDs bind source identity. `run.py` therefore verifies the same five passage contents, ranks and normalized byte coordinates, then compares both layouts on **one** verified packet. `docs.ask` checks normalized source ranges and hashes before projection. The protocol's parent include is confirmed by the literal `include::diff-context-options.adoc[]` at line 53 and its declared manifest edge, not lexical similarity alone. The script checks the corpus files' pinned hashes, the cited URLs, full passage text and observed citation ranges.

The original layout puts both the path and full URL in each numbered citation header. The revised layout keeps the URL and lines but removes the repeated path. Both greedily try whole retrieved passages in rank order and skip any candidate that would exceed the cap. The baseline layout is reproduced from the source code at the pinned baseline commit; the revised layout calls the product's `project_context` on that same query result. Nothing rewrites the canonical byte-packed response or stored trail.

The tested Python caller change is recorded in local product commit `0a4182a1c97356cfb286b50265987e43f48da5e9` (tree `c9a120c2472416a0df9c0b11fa86087309380357`). The CLI executable used in the observation has SHA-256 `1a2f8b32867f50cbdb4f4d0e89abd18f2331829cc85c0bb5cf551f1962ac9a54`; the caller change modifies no Go files.

Run from a complete pair of checkouts with a built Mousa binary and `tiktoken==0.12.0` installed. Supply a new output directory outside this run so a replay cannot replace archived observations:

```sh
python3 results/2026-09-29-context-512/run.py --product /path/to/mousa --mousa /path/to/mousa-binary --output /path/to/new-replay-directory
python3 tools/verify_results.py
```

The recorded run passed with the installed Python 3.13 environment and the pinned `o200k_base` encoding. A first attempt failed before recording observations because it compared historical source-path-bound segment IDs to fresh IDs. The protocol retains those historical IDs as a provenance note and verifies rank/content/coordinates instead; that failure did not measure the projection.

## Raw observation

`raw/packet.json` contains the verified five-row CLI packet and its original packet/trail IDs. `raw/observation.json` contains both complete rendered texts, text digests, per-row source URLs, normalized lines and bytes, segment IDs, selections and omissions. `manifest.json` binds the run files by byte length and SHA-256. The raw packet's source path is a temporary directory specific to this run; replay produces different source-derived IDs.

| Passage rank, source lines | Baseline 512 | Revised 512 |
| --- | --- | --- |
| 1: `diff-context-options.adoc`, 1–10 | selected | selected |
| 2: `git-restore.adoc`, 28–54 | omitted | selected |
| 3: `git-switch.adoc`, 215–255 | selected | omitted |
| 4: `git-restore.adoc`, 85–110 | omitted | omitted |
| 5: `git-switch.adoc`, 139–157 | omitted | omitted |

The original selection uses 507 tokens; the revised selection uses 511. The original layout would require 524 tokens to render ranks 1 and 2 together. The full revised prompt with all five passages requires 1,324 tokens. Both selections come from the same 3,945-byte byte-packed evidence response, packet ID and trail ID. The revised projection loses rank 4's separate `git-restore` evidence and both `git-switch` passages; the full raw packet retains them. The fragment includes the `diff.interHunkContext` default and the parent passage contains the `--patch` explanation and include directive. The script checks passage preservation and applicability coordinates, not whether a model can answer correctly.

The 512 limit applies only to `context.text`: instruction, question, numbered source headers and selected passage texts. JSON packaging, caller/system/tool framing, other model tokens and output reservation are excluded. Neither this result nor the prior 544-token observation sets a whole-window ceiling or establishes general retrieval quality. No timing or resource comparison was run.
