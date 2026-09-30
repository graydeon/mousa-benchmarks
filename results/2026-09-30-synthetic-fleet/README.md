# Synthetic fleet: first live harness observations

Eight labeled cases were exercised through each of Codex, OMP and Hermes on the same generated 32-entity corpus, with separate account-owned SQLite stores. This is a development acceptance run, not a matched model comparison.

| Harness | Requested or reported model | Strict case result |
| --- | --- | --- |
| Codex 0.159.2 | Explicit `gpt-6-luna` request; backend ID not exposed | 8 PASS, 0 FAIL |
| OMP 18.4.4 | Native events report `deepseek-flash` | 6 PASS, 2 FAIL |
| Hermes 2026.9.24/package 0.21.5 | Native events report `deepseek-flash` | 7 PASS, 1 FAIL |

OMP failed the sealed-source and unauthorized-write answer contracts (`wrong_facts`, `wrong_outcome`). The database boundary itself passed independent executable checks. Hermes staging facts were correct, but its evidence was an object instead of the required array. The resulting grader exception initially stopped that batch; its CLI exit and wall time were not retained. The recorded case remains FAIL with those fields null. The six remaining cases ran after malformed-evidence handling was corrected. No failed case was rerun to replace its result.

Initial OMP grading incorrectly discarded two query results because their rendered text could not be parsed, despite authoritative structured results in native event details. The final grader uses that structured evidence; owner/schedule and historical-trail cases then passed by regrading the same events, without another inference call. The original grades remain in private receipts.

## Database checks

| Entities | Active fleet items after withdrawal | SQLite bytes after initial build checks |
| --- | --- | --- |
| 32 | 97 | 954,368 |
| 256 | 769 | 4,263,936 |
| 2,048 | 6,145 | 30,896,128 |

All three stores passed actual status, exact retrieval/digest/byte checks, historical selection, absent evidence, sealed-token exclusion and disabled-ingestion checks. The largest import completed but its first MCP startup exceeded the original 60-second response timeout. Verification of the existing store passed with a 300-second timeout; it was not imported again. This is a startup-bound observation, not a failed retrieval-quality result or an optimization claim.

After all live workloads, all three 32-entity account stores passed another actual MCP check: 97 active items, original production content/digest, unavailable sealed-source denial and disabled ingestion. Audit records increase database size; post-run sizes are separate in `observations.json`.

## Pilot and setup failures

Preserved separately from the 24 case observations:

- The first absent-service fixture used multiple searchable words and matched the untrusted note under the engine's OR query semantics. Before freezing the live corpus, its identifier became the absent single token `UNREGISTEREDZZSERVICE`.
- Codex's first pilot disabled its required code-mode host and had no usable MCP tools. A second pilot lacked per-tool noninteractive approval. Both failed; the accepted configuration retains code-mode host and approves only this fixed-source MCP binding. The server still denies ingestion.
- OMP initially waited for inherited stdin until the 330-second runner deadline. The runner now supplies EOF explicitly.
- Hermes initially used a resolved virtualenv interpreter symlink, losing its environment. The executable path now preserves the virtualenv.
- Several Hermes pilots reported an unknown MCP toolset and returned unsupported answers before tools were ready. A transport-proxy attempt supplied no receipts. The accepted adapter uses the native handler and completes native discovery before inference. The earlier uninstrumented invocation is not counted as provenance-verified success.
- A recovery inspection of the large-store timeout expected complete frames where none existed and failed. The successful verification remains a separate receipt.

## Reproduction and limits

See [dataset commands and contracts](../../datasets/synthetic-fleet/README.md). `dataset-manifests.json` binds all three corpus sizes; `protocol.json` records configuration and command templates. `observations.json` contains individual outcomes, tool names, wall times and harness-reported usage, with no model transcripts. Wall time includes harness/MCP startup and shutdown. Token fields and reported cost formats differ by client and are not independent billing measurements.

Executable source: Mousa `96b99f5f808dd4a836547156babda158fa2cd2d1`, SHA-256 `895bd443c95ce614cb5a4399c873c3a674f93f4f996ec1278632c171c0e985e5`. These runs do not test PR44's extension implementation. Benchmark starting revision: `05fbb16ef21bfb98df36cceb6df49831e144da98`; the manifest also binds reproduction script hashes.

There is one observation per case/harness, eight question types and only entity zero as the live target. Bulk records are templated distractors. Codex used schema-constrained responses, whereas the secondary harnesses used a prompted JSON contract; harness configuration, context, caching and startup differ. Some secondary execution overlapped on the shared four-CPU LXC. Do not infer model rankings, latency advantages, real-world retrieval quality, instruction-injection immunity or broad compatibility. Desktop rendering, live OAuth/HTTPS deployment and directory distribution were not tested.
