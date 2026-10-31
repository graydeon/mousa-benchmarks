# Byte-packed vector/hybrid supersession observations

Both runs use public Mousa head `a09cce0ba903e3dfaf8a772cfcddd0b2086c73fa`,
tree `020aa6b0764610d4611c6910ae827c2aea50d2ff`, built from a clean anonymous
checkout with Go 1.27.1 and `CGO_ENABLED=0`. This is the public
[product proposal](https://github.com/graydeon/mousa/pull/92), not an accepted
milestone or a relabeled earlier observation. [Build provenance](build.json)
and the [fixed protocol](protocol.json) bind the executable and driver.

| Run | Native commands | MCP requests | Raw MCP responses | Clean MCP exits | Scheduled events | Result |
|---|---:|---:|---:|---:|---:|---|
| Capture | 25 | 42 | 40 | 2 | 71 | PASS |
| Fresh-store reproduction | 25 | 42 | 40 | 2 | 71 | PASS |

The [driver](../../vector-supersession) imports externally supplied synthetic
vectors over native-exported pins, then exercises native JSONL and configured
stdio MCP. It imports no product packages and never opens SQLite. The predecessor
and twin have equal bytes but distinct evidence identities. The successor has no
embedding, does not lexically match and exceeds the 12-byte evidence budget;
its availability cannot gate suppression. A vector-only peer also exceeds that
budget.

For both retrieval modes and packers, omitted/false selects the predecessor;
true withholds it and selects the twin. The twin retains its original producing
rank instead of being reranked to one. Original cosine ranks, hybrid lexical/
vector branch ranks, actual BM25/cosine and independently calculated RRF(k60)
remain recorded. Producing coverage stays four eligible passages and three
vectors before masking. The second session withdraws the successor: fresh
coverage becomes three/three, but enforcement still withholds the predecessor.

Independent MCP history flags expose only the requested recorded consultation or
retrieval facts. Authorized native and MCP inspection retain producing IDs,
positive withheld sizes/ranks and the original four/three coverage after later
withdrawal; native history also remains unchanged after deactivation. Inspection
can append fresh authorization audit evidence. It does not reconstruct old text
or rerun the producing index.

## Replay, comparison and controls

The lossless XZ [raw archive](raw-captures.tar.xz) contains four regular files: both
captures and their summaries. [Member sizes/hashes](raw-members.json) bind every
uncompressed byte. No database, executable, link or absolute/traversal archive
path is included. Streams retain exact bytes, sizes and SHA-256 hashes; all
scheduled commands/requests, outputs, errors, exits and process tails are kept.

Both offline replays and both control runs exit 0. Four coherently rehashed
mutations fail their intended assertions:

- Changed boolean request: `scheduled-request-bytes`.
- Incorrect withheld count: `withheld-count`.
- Wrong selected item: `selected-evidence`.
- Incorrectly selected historical predecessor: `withheld-historical-facts`.

The [capture](capture-controls.json) and [reproduction](reproduction-controls.json)
receipts retain mutated-report hashes and detectors. Mutated copies are regenerated,
not stored. These are specific consistency detectors, not proof against arbitrary
malicious producers.

The [cross-run comparison](comparison.json) matches all 65 result rows after
excluding only enumerated fresh invocation IDs/time fields and the historical
wrapper's per-call IDs. Each run independently checks those IDs against its
producing query/request; raw values remain retained. The first comparison attempt
failed because native sync `elapsed_seconds` was not yet excluded. Its two actual
differences and exit 1 remain in [the attempt receipt](comparison-first-attempt.json).
No capture was rerun, relabeled or changed to obtain the corrected comparison.
Both captures passed on their first attempt.

From the repository root:

```sh
REPLAY=$(mktemp -d)
tar -xf results/2026-10-30-vector-hybrid-supersession/raw-captures.tar.xz -C "$REPLAY"
for run in capture reproduction; do
  python3 vector-supersession/capture.py verify --output "$REPLAY/$run"
  python3 vector-supersession/capture.py controls --output "$REPLAY/$run"
done
python3 vector-supersession/compare.py "$REPLAY/capture" "$REPLAY/reproduction"
python3 tools/verify_results.py
```

For a new public-head capture, follow the [client instructions](../../vector-supersession).
The stored observations require only standard-library Python for replay; no
external tokenizer or model is used in this byte-only slice.

## Limits

Synthetic public-client protocol/arithmetic evidence only. No semantic retrieval
quality, model integration, latency, performance, task-completion, token-window
or historical old-text reconstruction claim follows. Directory, denial,
lifecycle-derived graphs, corruption, source admission, snapshot ordering and
unsupported combinations are separate product regressions, not observations
from this client fixture. Earlier public archives and producing pins remain
byte-identical. Archive integrity or green CI alone is not independent final-head
acceptance of either proposal.
