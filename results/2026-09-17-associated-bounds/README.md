# Declared-association processing bound

A legal item with 65,536 short passages made an unbounded declared-association query fail while encoding its trail. This study records the failure and the behavior after limiting each query to 256 considered target passages. The limit is applied during SQL enumeration, not after loading all segments; `target_truncated` records an incomplete target. A small byte budget does not reduce how many target passages the association stage considers.

## Method

`measure.py` creates eight generated corpora within the CLI's default file and total-size limits. Each query uses an independently copied, closed and synced SQLite store. It records process wall time, peak RSS, response facts, omission reasons and a trail-read exit. Ordinary cases have five measured repetitions; `large` and `many-tiny` have three. The `control` has no declaration. The `no-budget` query has enough room for primary evidence but no associated passages. A preceding fixture smoke on `small` and `medium` passed before the bounded run. `protocol.json` identifies the scripts, input rules, binaries and measured source. Raw observations, summaries and worker environments are under `raw/`.

Both runs used the same shared worker host, but the observations are not paired or isolated timing comparisons. The pre-bound source was uncommitted and its full source snapshot was not retained with this result; its binary hash and observations are retained. The bounded product state is the recorded base plus its uncommitted diff. These limitations prevent exact source reconstruction of the pre-bound binary from this directory alone.

## Observations

| Case | Considered-target result | Before: median wall / peak RSS / exits | Bounded: median wall / peak RSS / exits |
|---|---|---|---|
| control | no declaration | 168.64 ms / 24,208 KiB / 5 of 5 pass | 153.40 ms / 24,180 KiB / 5 of 5 pass |
| small | four associated passages | 60.90 ms / 25,336 KiB / 5 of 5 pass | 59.71 ms / 24,180 KiB / 5 of 5 pass |
| medium | four released; 252 budget omissions | 245.11 ms / 25,336 KiB / 5 of 5 pass | 226.76 ms / 24,180 KiB / 5 of 5 pass |
| large | four released; 252 budget omissions and a truncation | 735.94 ms / 26,200 KiB / 3 of 3 pass | 567.88 ms / 24,180 KiB / 3 of 3 pass |
| fanout | four released; four targets over fan-out cap | 1227.68 ms / 26,280 KiB / 5 of 5 pass | 1038.40 ms / 24,712 KiB / 5 of 5 pass |
| no-budget | zero released; 256 budget omissions | 211.01 ms / 25,336 KiB / 5 of 5 pass | 220.59 ms / 24,180 KiB / 5 of 5 pass |
| duplicate | four released; two duplicate omissions | 60.77 ms / 24,208 KiB / 5 of 5 pass | 61.30 ms / 24,180 KiB / 5 of 5 pass |
| many-tiny | 256 released and one truncation | 27,638.13 ms / 364,516 KiB / 0 of 3 pass | 22,072.62 ms / 43,568 KiB / 3 of 3 pass |

The pre-bound `many-tiny` query failed with `sqlite resource_limit: encode record: canonical record size 60801516 exceeds 33554432`; its failed observations have no trail read. All bounded measured queries and their trail reads exited zero. The 65,536-passage item still takes roughly 22 seconds per query on this host: the consideration bound prevents the oversized association record but does not make ingestion, source resolution or query processing constant-time. The result does not establish a general latency improvement.

At most four distinct targets are applied. A per-query consideration counter follows declaration order and document order; when further segments exist the omission is visible. The limit can exclude useful passages in an extreme target even when the byte budget would fit them. The `fanout` record shows three truncation omissions for targets visited after the first exhausted the 256-passage allowance. The bound does not weaken source authorization or imply semantic support.
