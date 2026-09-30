# Synthetic fleet workloads

Generate fictional maintenance schedules, owners and rollback codes, then build a local Mousa database and answer labeled questions through real CLI harnesses. All corpus text and labels are generated from templates and SHA-256 inputs. No private corpus, real organization, credential or external dataset is included. Files use this repository's AGPL-3.0-only license.

## Dataset

`example/` contains the reproducible 32-entity dataset with seed `20260930`. Each entity has production, staging, owner and obsolete records. Setup imports the obsolete records and then withdraws them. An additional imported note contains an instruction-injection string. A separate `sealed` source contains a fictional token and is not bound to benchmark MCP connections.

| File | Purpose |
| --- | --- |
| `fleet.jsonl` | Initial records, including obsolete records and the untrusted note |
| `withdrawals.jsonl` | Tombstones for obsolete records |
| `sealed.jsonl` | Separate-source isolation fixture |
| `tasks.jsonl` | Five positive and three negative cases, expected facts, byte/digest labels and tool requirements |
| `manifest.json` | Seed, counts, license, byte sizes and SHA-256 digests |

The generator hashes `fleet-v1:SEED:INDEX` to select weekday, UTC time, owner and rollback values. It does not call a model or network service. Generation is deterministic, with UTF-8 JSON Lines and LF endings. New output directories are required; existing datasets and databases are not overwritten.

The eight cases check production/staging distinction, joining owner and schedule evidence, historical packet/trail binding, collection status, abstention, unavailable-source handling and disabled ingestion. Questions target entity zero; increasing entity count adds templated distractors, not independent questions. Labels are public development fixtures, not held-out evaluation data. These workloads do not represent real-world document diversity.

## Build and verify

Requires Python 3.9 or later and a Mousa executable with the four core MCP tools. Commands below are usage examples; substitute your own executable and private work directory.

```sh
python3 datasets/synthetic-fleet/generate.py --out /tmp/fleet-256 --entities 256 --seed 20260930
python3 datasets/synthetic-fleet/build.py --mousa /path/to/mousa --dataset /tmp/fleet-256 --store /tmp/fleet-256.sqlite --report /tmp/fleet-256-build.json
```

`build.py` verifies input hashes, imports both sources, withdraws obsolete records, and exercises the actual MCP server. Checks include active-item count, exact selected bytes and digests, historical selection, absent evidence, unavailable-source denial, ingestion denial and unchanged content after denied ingestion. `--verify-only` checks an existing database without importing again. Retrieval still writes audit records. The per-response timeout defaults to 300 seconds, including database startup.

Do not commit generated SQLite stores, binary executables or private reports. Larger corpora can be reproduced with `--entities 2048` without committing their expanded JSON Lines.

## Live harnesses

Provider access must already be configured in the harness account. Model requests can incur charges. Each harness uses its own store and a new private output directory. Only source `fleet` is bound; ingestion remains disabled. Output includes prompts, native events and tool receipts, so keep it private.

```sh
python3 datasets/synthetic-fleet/run_codex.py --codex /path/to/codex --mousa /path/to/mousa --dataset datasets/synthetic-fleet/example --store /private/fleet.sqlite --out /private/codex-run --model gpt-6-luna
python3 datasets/synthetic-fleet/run_secondary.py --harness omp --executable /path/to/omp --mousa /path/to/mousa --dataset datasets/synthetic-fleet/example --store /private/omp-fleet.sqlite --out /private/omp-run
python3 datasets/synthetic-fleet/run_secondary.py --harness hermes --executable /path/to/hermes/.venv/bin/python --mousa /path/to/mousa --dataset datasets/synthetic-fleet/example --store /private/hermes-fleet.sqlite --out /private/hermes-run
```

Use `--case CASE_ID` repeatedly for a bounded subset. Codex defaults to `gpt-6-luna`; OMP and Hermes retain their configured models. Codex requests schema-constrained JSON. The secondary harnesses receive the same answer-field contract in their prompt, without provider-side schema enforcement. This difference precludes a matched model-quality comparison.

The tested versions are Codex 0.159.2, OMP 18.4.4 and Hermes 2026.9.24/package 0.21.5. Codex requires its complete release package and code-mode host. Its fixed-source MCP tools receive explicit noninteractive approval; server-side ingestion denial remains authoritative. Shell, browser and delegation features are disabled, while the read-only sandbox setting remains enabled.

OMP uses a process-specific project MCP binding, closes piped stdin and waits for MCP readiness. Hermes uses `hermes_entry.py`: a process-local configuration overlay disables memory/profile use, binds the same native MCP server, completes native discovery before inference, and records native handler arguments/results. It does not rewrite global configuration or replace provider/tool implementations. The adapter uses Hermes internal APIs and is version-specific. Explicit readiness avoids the observed oneshot/background-discovery race; unready pilot attempts remain failures, not accepted observations.

Grading requires exact outcomes/facts, complete evidence references, matching source/item/digest/byte labels, references actually released by tools, required calls and query-bound historical packet/trail IDs. Malformed answer/evidence shapes fail rather than terminate the batch. A denied answer may be correct without attempting a forbidden operation; independent executable checks establish the actual source/write boundary. `score_native.py` can regrade retained secondary invocations without another model call.

[September 30 observations](../../results/2026-09-30-synthetic-fleet/) record one observation per case and harness, startup failures and database sizes. No desktop rendering, PR44 extension behavior, general quality ranking or latency advantage is established.
