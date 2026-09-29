# Git switch parent follow-up under 512 content tokens

**Result: required citation pair does not fit.** An explicit follow-up retrieves the `git-switch` parent passage containing `include::config/checkout.adoc[]`. The original query retrieves the `checkout.defaultRemote` definition in a separate packet. Rendering those two complete passages with the original question and pinned citation URLs takes **513 `o200k_base` tokens**, one above the prospectively fixed 512-token content limit. The original failed packet and Source Trail remain unchanged; this follow-up has independent packet and trail identities. No caller policy or token cap was changed after this observation.

## Frozen method

`protocol.json` fixes the two questions, Git 2.51.0 revision `c44beea485f0f2feaf460e2ac87fdd5608d63cf0`, archive, manifest and affected file SHA-256 digests, 4,096-byte original-policy follow-up query, expected normalized byte coordinates, `tiktoken==0.12.0/o200k_base`, prompt layout, selection and acceptance. Its pre-query SHA-256 is `25d7972a38ceda5cc9a7118ec874fbb8ec4be6af1c376c0e0d6d8e5c53092913`. The original result is [preserved separately](../2026-09-29-switch-default-remote/). The frozen combined presentation requires the original packet's whole rank-2 fragment followed by the follow-up's whole parent passage, with no unrelated citation.

The parent passage is `Documentation/git-switch.adoc` lines 256–285, normalized bytes 8280–8902; it contains the literal directive on line 276, bytes 8762–8793. The original fragment is `Documentation/config/checkout.adoc` lines 1–19, bytes 0–845. Both use separate revision-pinned URLs in the manifest. Every retrieved hit was checked against its pinned file SHA-256, normalized byte slice, segment digest, normalized line range and URL. The directive bytes and manifest include edge were checked independently. A relationship annotation alone is not a citation to the directive.

## Passage accounting

Trial cost includes instructions, the question, URLs, line ranges, whole text and previously selected passages with consecutive citation numbering. `observation.json` records all normalized byte ranges, text-token costs and retrieved rank for both packets. The follow-up packs 3,985 evidence bytes and reports 17 budget omissions. The original packs 3,785 bytes and reports 18 budget omissions.

| Packet / rank | Passage | Bytes | Text tokens | Trial tokens | Greedy 512-token rendering |
| --- | --- | ---: | ---: | ---: | --- |
| Original 1 | switch `--guess`, lines 90–116 | 921 | 242 | 346 | selected |
| Original 2 | checkout defaultRemote, lines 1–19 | 845 | 209 | 602 | omitted |
| Original 3 | other checkout settings, lines 20–38 | 929 | 211 | 604 | omitted |
| Original 4 | switch tracking, lines 158–179 | 930 | 255 | 647 | omitted |
| Original 5 | generic configuration preface, lines 1–3 | 160 | 34 | 430 | selected |
| Follow-up 1 | switch CONFIGURATION parent, lines 256–285 | 622 | 154 | 253 | selected |
| Follow-up 2 | switch `--guess`, lines 90–116 | 921 | 242 | 542 | omitted |
| Follow-up 3 | restore options, lines 28–54 | 932 | 256 | 557 | omitted |
| Follow-up 4 | restore pathspec, lines 129–156 | 978 | 261 | 561 | omitted |
| Follow-up 5 | generic configuration preface, lines 1–3 | 160 | 34 | 337 | selected |
| Follow-up 11 | diff fragment, lines 1–10 | 372 | 107 | 492 | selected |

The follow-up renders parent plus unrelated preface and diff fragment at 492 tokens; it does not retrieve the checkout fragment. The original renders switch `--guess` plus unrelated preface at 430 tokens, omitting the checkout definition and lacking the parent. Explicit caller assembly of original rank 2 alone costs 313 tokens; with follow-up rank 1 it costs 513. Retrieval of the missing parent therefore resolves the source-discovery miss but **not** the frozen citation-pair requirement. The two independent prompts must not be mistaken for a single supported citation pair.

Reproduce from the corresponding Mousa documentation example tree: build `./cmd/mousa` with `CGO_ENABLED=0`, `prepare` the bundled archive into an empty directory, `sync` its declared documents into a fresh store, then `ask --budget-bytes 4096 --context-tokens 512` using the frozen follow-up question. `observation.json` records the captured follow-up packet and trail IDs and the complete packet digest. Source-root-bound IDs and timings may differ. Neither generated-answer quality nor whole-model context is measured: raw JSON, message framing, tool schemas, output reservation and downstream tokenizer behavior are outside this content bound.
