# Git switch citation-anchor layout at 512 content tokens

**Result: the required pair still misses.** Replacing `URL lines first-last` with the GitHub line-anchor form `URL#Lfirst-Llast` does not reduce the complete two-passage rendering: both the original and proposed headers cost **513 `o200k_base` tokens**, exceeding the prospectively fixed 512-token rendered-content limit. No caller layout or limit was changed after observation. This is a saved-packet replay of two earlier independent queries, not a new retrieval or an answer-quality measurement.

## Frozen method and identity

`protocol.json` was frozen before projection at SHA-256 `7d242a7db9a72286767f46e44eaab4e7a8c059ed810ded81afea627b1dcf2bce`. It fixes the exact header substitution, the original question and separate parent-follow-up question, citation order (original rank 2 then follow-up rank 1), Git 2.51.0 revision `c44beea485f0f2feaf460e2ac87fdd5608d63cf0`, source archive/manifest/file digests, 4,096-byte original query policy, `tiktoken==0.12.0/o200k_base`, 512-token limit, coordinates and acceptance. The [original failed run](../2026-09-29-switch-default-remote/) and [separate parent follow-up](../2026-09-29-switch-parent-followup/) remain unchanged.

The replay read documentation-consumer source at local Mousa revision `ad3276d364fad43562891d614d19bd6c8340faca` (tree `bac2b1f77d2ff425147e4ddc07309241e8e442e3`, clean) and started from companion revision `15dcc24c927e5a8df9e940a97e82d12c58b29538` (tree `e8ad45ca1964ae978cb70f261d42b5ca0a9e9520`, clean). Earlier packets were produced with binary SHA-256 `5c7236ffdbe340a276d61609b5aaeb873f28ef737fcd9682db9b49fe312014eb`; this replay executes no Mousa binary. The fixed source archive and corpus manifest SHA-256 values are `6b7cb47de2a083e15301b8bb94f903f00022a12284fd0ad8732f0e811ee68ce9` and `6b058ba6db48468c12592d38d1565b2211b36f00b657fb565bc744f073554ef2`. Tokenizer dependency: `tiktoken==0.12.0` with `o200k_base`; the verifier asserted the installed version before counting. The frozen protocol records individual normalized source file hashes.

The original question is “When git switch finds a branch on multiple remotes, how does checkout.defaultRemote=origin resolve it, and is that setting included in the git-switch manual?” Its local-root packet ID is `ba9306fcdd538883668d13b5fa6502f325a55182ca8c223c35de9f3e2ab9188a` and trail ID is `7eb40dc24cbcb578f234f568e1cee8a7e449e0c60d69026705faf30687c96cfd`. The independent follow-up asks “In the git-switch manual CONFIGURATION section, which literal include::config/checkout.adoc[] directive includes the checkout.defaultRemote configuration fragment?” Its packet ID is `80e2e5210e2cb8f94bfd252d0eb8d0df42a0f8c55201076e52828b5513a1c9d6` and trail ID is `939ce80ca9adcc1b33f18d5030756dff8f59103dffea9e403fdaedaf4260dba8`. Packet hashes and citation-to-query/segment mappings are in `observation.json`. These IDs bind the original local source root; another root produces different IDs.

Every one of the 11 retrieved passages was checked against the hashed normalized file, exact passage bytes and digest, revision-pinned URL, zero-based end-exclusive byte coordinates and one-based normalized line coordinates. The parent `Documentation/git-switch.adoc` passage spans lines 256–285, bytes 8280–8902, and contains literal `include::config/checkout.adoc[]` at line 276, bytes 8762–8793. The intact `Documentation/config/checkout.adoc` fragment spans lines 1–19, bytes 0–845. The rendered citation anchors preserve both source coordinates, without flattening the include relationship or modifying either canonical packet or Source Trail.

## Whole-passage accounting

Trial tokens count instructions, each packet's own question, URLs, headers, whole text and previously selected hits with consecutive numbering. Rows and segment IDs are in `observation.json`.

| Packet / rank | Passage and normalized lines | Bytes | Text tokens | Trial tokens | Independent 512-token projection |
| --- | --- | ---: | ---: | ---: | --- |
| Original 1 | switch `--guess`, 90–116 | 921 | 242 | 346 | selected |
| Original 2 | checkout defaultRemote, 1–19 | 845 | 209 | 602 | omitted |
| Original 3 | other checkout settings, 20–38 | 929 | 211 | 604 | omitted |
| Original 4 | switch tracking, 158–179 | 930 | 255 | 647 | omitted |
| Original 5 | generic configuration preface, 1–3 | 160 | 34 | 430 | selected |
| Follow-up 1 | switch CONFIGURATION parent, 256–285 | 622 | 154 | 253 | selected |
| Follow-up 2 | switch `--guess`, 90–116 | 921 | 242 | 542 | omitted |
| Follow-up 3 | restore options, 28–54 | 932 | 256 | 557 | omitted |
| Follow-up 4 | restore pathspec, 129–156 | 978 | 261 | 561 | omitted |
| Follow-up 5 | generic configuration preface, 1–3 | 160 | 34 | 337 | selected |
| Follow-up 11 | diff fragment, 1–10 | 372 | 107 | 492 | selected |

The original packet packs 3,785 evidence bytes, reports 18 budget omissions, and projects switch `--guess` plus an unrelated preface (430 tokens), losing the checkout definition and never retrieving the parent. The follow-up packs 3,985 bytes, reports 17 budget omissions, and projects parent plus generic preface and unrelated diff fragment (492 tokens), but does not retrieve the checkout fragment. Separate assembly of original rank 2 and follow-up rank 1 would exclude unrelated passages, yet costs 513 tokens with the original question; the intact pair cannot be presented under the frozen 512-token limit. An independent projection is not a combined packet or a supported answer.

Reproduce the projection with the unchanged saved packets identified by `observation.json`, the bundled `examples/docs/git-docs.tar.xz` corpus at the pinned source revision, and the frozen layout in `protocol.json`. Verify full source and passage SHA-256, normalized bytes/lines and URLs before counting with pinned `tiktoken`. The content bound excludes raw JSON, model/API message framing, tool schemas and output reservation. Neither token fit nor valid coordinates establish semantic support or a whole-model-window guarantee.
