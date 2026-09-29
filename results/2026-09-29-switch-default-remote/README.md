# Git switch configuration citation under 512 content tokens

The fixed question asks how `checkout.defaultRemote=origin` resolves a branch found on multiple remotes and whether the configuration setting is included in the Git switch manual. The current byte-packed response does **not** contain a passage covering the manual's direct include directive. The 512-token projection also omits the retrieved `checkout.defaultRemote` fragment. This case fails the stated requirement to present both fragment and parent; the selected switch `--guess` passage describes disambiguation but does not establish the include relationship by itself.

## Input and method

`protocol.json` fixes the exact question, Git 2.51.0 revision `c44beea485f0f2feaf460e2ac87fdd5608d63cf0`, source file and archive digests, Mousa source tree, 4,096-byte query, `tiktoken==0.12.0` with `o200k_base`, 512-token rendered-content cap, prompt layout and acceptance. Its pre-query protocol digest identifies the question and criteria frozen before retrieval. The observed retrieval order was appended after the first query and before any source change. A second run using `/tmp/mousa-switch-default-remote-corpus` produced the same ranked text and normalized coordinates with new source-root-bound identities; `raw/packet.json` is that second complete response. Neither checkout was modified to affect retrieval or projection.

The corpus manifest declares `Documentation/git-switch.adoc` includes `Documentation/config/checkout.adoc`. In the hashed parent the literal `include::config/checkout.adoc[]` spans normalized bytes 8762–8793 on line 276. The caller's direct include relationship reports that coordinate, and all five retrieved passages were checked against normalized source bytes, digests and line ranges. The directive is *not inside* any retrieved switch passage; relationship metadata is not a cited parent passage.

## Observation

| Rank | Source lines | Passage bytes | Text tokens | Trial prompt tokens | Rendered at 512 |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | `git-switch.adoc` 90–116, `--guess` | 921 | 242 | 346 | yes |
| 2 | `config/checkout.adoc` 1–19, `checkout.defaultRemote` | 845 | 209 | 602 | no |
| 3 | `config/checkout.adoc` 20–38, other settings | 929 | 211 | 604 | no |
| 4 | `git-switch.adoc` 158–179, tracking | 930 | 255 | 647 | no |
| 5 | `includes/cmd-config-section-all.adoc` 1–3, configuration preface | 160 | 34 | 430 | yes |

The fixed response packs 3,785 evidence bytes and reports 18 budget omissions. The base instructions/question cost 57 tokens, all five passages cost 1,245 tokens in the stated layout, and the selected ranks 1 and 5 cost 430. Trial counts include previously selected rows with consecutive citation numbering. Rank 2 alone costs 313 prompt tokens, but it does not fit after rank 1. Rank 5 fits yet its generic preface is not the `config/checkout.adoc` directive. The parent CONFIGURATION passage at lines 271–276 is absent from the packet altogether. The raw JSON retains all five packed hits, their source URLs, packet and Source Trail IDs; the projection changes neither.

`raw/observation.json` retains per-rank coordinates, tokens, IDs, selection and lost-evidence classification. `manifest.json` verifies sizes and SHA-256 digests of all run members. To reproduce, build Mousa from the pinned tree, use `examples/docs/docs.py prepare` and `sync` with the bundled archive into a new empty corpus/store, then run `ask --budget-bytes 4096 --context-tokens 512` with the protocol question and `tiktoken==0.12.0`. Source-root-bound identities and timing can differ. Check the literal directive against the pinned source rather than inferring inclusion from shared terms.

No correction was made: a renderer cannot select a parent passage missing from the fixed packet while preserving that packet. A separate, explicit caller query or a changed retrieval request would be a new protocol and needs its own acceptance check. No generated answer, semantic-support estimate, whole-model-window limit, latency comparison or resource measurement follows from this observation. JSON packaging, caller/system/tool framing and output reservation are outside the content-only cap.
