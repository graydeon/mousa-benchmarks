# Native-MCP project-history development cases

## Result

One 28-document synthetic history was ingested through native stdio MCP and
queried after consumer/server restarts. All 21 required initial passages were
released for the 17 positive cases. The three unsupported questions also
released 13, 13 and 14 passages. Passage coverage, lifecycle correctness and
provenance are separate outcomes; this report supplies no combined accuracy
score or generated-answer result.

After one same-item correction and one explicit item tombstone, the two corrected
passages and two unaffected controls were released. No obsolete representation
or tombstoned item was released in the five post-change queries. Three original
historical trails retained their packet IDs and selected segment/digest/byte
identities. Their inspection returned metadata, not historical text.

Across 25 query observations, 334 passages were released; 309 did not contain a
required frozen supporting span. This classification follows the declared exact
span rule, not a general semantic relevance judgment. There were 64 releases
from the predeclared misleading-near-match items among those 309 passages.
All released hits passed normalized-coordinate, source-revision digest and
content-digest verification. Synthetic authors and URIs are attribution labels,
not authenticated authorship.

## Fixture and protocol

`history.json` is independently authored fiction. It contains decisions with
reasons, separately attributed facts, unrelated lexical near matches, an explicit
correction, an experimental proposal later withdrawn and genuinely absent facts.
The configured native source identity is `memory`; document IDs are explicit
items. The four MCP tools do not expose the internal canonical source ID.
No direct database queries or edits were used for ingestion or retrieval.

`protocol.json` freezes 20 natural-language questions, complete required byte
spans and digests, lifecycle expectations, forbidden obsolete evidence, scoring
rules and a 2,048-byte canonical evidence budget. Questions contain no item IDs
or answer-bearing titles; documents have no titles. These are development cases,
not held-out cases. Every required whole paragraph can fit within the budget;
ranking can still consume that budget with other evidence. No budget was expanded,
question reformulated, measured query repeated or judgment revised after results.

An unmeasured smoke validated the fixture, discovered MCP input/output schemas,
complete receipt capture, normalized-byte verification, correction/tombstone,
restart, original-trail inspection and analyzer branches before measurement.
The measured source archive preserves the actual consumer used, including its
original executable-path behavior. The frozen analyzer digest and consumer digest
are in the protocol; `raw/measured-consumer-source.tar.gz` contains those consumer
inputs and the existing coordinate verifier.

The fixed sequence is:

1. Start the concrete consumer and native server; ingest all 28 explicit items.
2. Close both processes. For each of the 20 questions, start fresh processes,
   query once and close them. Inspect each resulting trail in another fresh process.
3. Apply the frozen correction to `entry-19` and explicit tombstone to `entry-20`
   through `mousa_sync`; close both processes.
4. Restart for the three affected questions and two frozen unaffected controls.
5. Inspect the original three lifecycle trails under fresh authorization.

Every command starts and closes its own consumer and Mousa process, retaining one
isolated store. There were 55 commands, including queries, ingestion, mutation and
trail inspection. An item tombstone deactivates the item; it is not source
withdrawal, secure erasure or a new current-fact interpretation. The current
correction explicitly mentions the former settings; that text is current evidence,
not release of the obsolete representation.

The consumer renders all released passages without selecting additional evidence
or generating an answer. It verifies bytes before adding fixture attribution.
For the multi-document cases, two questions request independent facts. Two others
have relationships explicitly stated in the second required source passage; both
relationship passages were released. Co-retrieval alone is not scored as a link.

## Case-level outcomes

The complete questions, coordinates, packet/trail IDs, digests, latencies and
omission fields are in `protocol.json`, `observations.json` and the raw archive.

| Case | Category | Initial passage coverage | Post-change passage coverage |
| --- | --- | ---: | ---: |
| 01 | Paraphrased save durability | 1/1 | 1/1 control |
| 02 | Paraphrased repeated request | 1/1 | Not repeated |
| 03 | Paraphrased failed replacement | 1/1 | Not repeated |
| 04 | Paraphrased audit attribution | 1/1 | Not repeated |
| 05 | Paraphrased expired login | 1/1 | Not repeated |
| 06 | Paraphrased malformed import | 1/1 | Not repeated |
| 07 | Database decision and reason | 1/1 | 1/1 control |
| 08 | Refresh decision and reason | 1/1 | Not repeated |
| 09 | Paragraph decision and reason | 1/1 | Not repeated |
| 10 | Upgrade decision and reason | 1/1 | Not repeated |
| 11 | Backup and restore, independent facts | 2/2 | Not repeated |
| 12 | Export size and continuation, independent facts | 2/2 | Not repeated |
| 13 | Queue expiration and display, explicit relationship | 2/2 | Not repeated |
| 14 | Attachment gate and retention, explicit relationship | 2/2 | Not repeated |
| 15 | Corrected delivery window | 1/1 | 1/1 current revision |
| 16 | Corrected rehearsal schedule | 1/1 | 1/1 current revision |
| 17 | Withdrawn mobile proposal | 1/1 | No required support; item absent |
| 18 | Absent residency guarantee | No support; 13 passages released | Not repeated |
| 19 | Absent rollback approval | No support; 13 passages released | Not repeated |
| 20 | Absent attachment size | No support; 14 passages released | Not repeated |

No required passage was omitted. The analyzer records an observable packing cause
when a required passage digest occurs in unselected candidate metadata; otherwise
it reports that the passage is not in the released candidate metadata. Neither
cause was needed in this measured run. All three negative responses had
`outcome: evidence`; this is lexical availability, not semantic support.

## Failure trace and implementation

The largest observed consumer-visible limitation is unsupported and irrelevant
lexical evidence. Case 20's prepared expression contains literal OR terms for
`what`, `is`, `the`, `maximum`, `attachment`, `size`, `in` and `megabytes`.
It found 28 candidates, omitted 14 for budget and released 14. The history has
attachment publication and retention rules but no attachment-size limit.

The native query path prepares literal terms, OR-joins them, authorizes the fixed
source, ranks FTS5 candidates, verifies canonical ancestry/bytes/lifecycle,
first-fit packs whole passages and releases them with provenance. None of those
stages claims semantic support or performs semantic abstention. The concrete
consumer renders the returned evidence unchanged and explicitly leaves
`answer: null` and `support: not_assessed`. This observation does not establish a
supported-behavior bug or justify embeddings, stopword filtering, a reranker,
semantic judgment or an answering layer. No engine correction was selected.

Review found a separate consumer executable-path bug: converting `./mousa` to a
`Path` removed the slash, so process launch searched `PATH` rather than the local
file. A native failing receipt was retained. The final consumer resolves the
executable path before launching; actual-executable regression and final native
acceptance cover that correction. The original measured results were not repeated
or relabeled. Final verification identity is separate from measured identity.

## Latency and context limits

The initial 20 queries had whole-consumer process median 822.673 ms,
MCP query round-trip median 86.583 ms, server-reported operation median
83.570 ms and initialize median 321.894 ms. The respective sampled maxima
were 986.637, 174.407, 171.492 and 507.086 ms. Initialize starts after process
launch and includes store opening/verification; whole-process timing also
includes interpreter startup, imports, fixture/binary hashing, MCP discovery,
rendering, status, shutdown and output serialization. The consumer's internal
caller timer is retained separately and excludes interpreter startup/imports.

The five post-change observations had whole-process median 1,012.197 ms,
query round-trip median 90.040 ms and initialize median 528.118 ms. These are
sequential observations on a shared host with growing retained history and
additional inspection records, not a before/after performance comparison,
population-tail estimate or startup-regression study. Every outlier is retained.

Initial released evidence was 1,344–2,046 bytes; rendered context was
3,231–5,079 bytes. Attribution and framing are outside the canonical evidence
budget. No verified tokenizer was installed; token counts are NOT RUN.
No whole-model context-safety assertion is made.

## Identities, evidence and reproduction

Product source base: `11c10d3684d074e500f190f00a244f98e976e96f` with the retained
local startup delta and concrete consumer inputs. Companion source base:
`2e06ec80f67e6d90d8cb4cc3711db49cf91d20a9`.
Measured native binary SHA256:
`0f1d0cbb0676ac084462455f5fc21c42650b722d91822f087901e01281ee2d19`.
History SHA256:
`dbbd50b9ab943842a7675d6d5ae82471cf76c1dd9eafc4dd8cdf15fd9154565d`.
Frozen protocol SHA256:
`82068cfd955014c5a1965393d58252cfdb098e607b8c33d38313ab12d8163f7e`.

`raw/measured-evidence.tar.gz` retains exact receipts, stdout, stderr, commands
with exit codes and the complete summary including exact rendered contexts.
`raw/members.json` records member sizes and hashes. `manifest.json` registers
all result files. Validate archive integrity with `python3 tools/verify_results.py`.

To reproduce on Linux with a built Mousa executable and product checkout:

```sh
python3 results/2026-09-30-agent-memory/run.py \
  --consumer ../mousa/examples/memory/memory.py --mousa /absolute/path/to/mousa \
  --history results/2026-09-30-agent-memory/history.json \
  --protocol results/2026-09-30-agent-memory/protocol.json --output /new/isolated/output
```

Reproduction produces a separately identified run, not additional evidence for
the original observations. Use the measured consumer archive for exact consumer
identity; current product source includes the later executable-path correction.
The runner was exercised with the equivalent absolute-path inputs on the retained
native runtime. It does not launch a model or alter any shared store/executable.

Actual agent acceptance and answer-support evaluation are NOT RUN. They require
an operator-started authorized agent session configured for native Mousa MCP
against this isolated history, with exact input context and output retained.
Do not control an existing agent daemon, import credentials or launch a recursive
model session. Deterministic receipts do not establish model-driven usefulness,
semantic memory, exhaustive recall or general agent quality.
