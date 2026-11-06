#!/bin/sh
# Run from the companion repository root after the product is publicly available.
set -eu
: "${PUBLIC_HEAD:?Set the exact published product commit}"
: "${PUBLIC_SOURCE:?Set its clean anonymous checkout directory}"
: "${BINARY:?Set the CGo-free binary built from that checkout}"
: "${PY:?Set the prepared tiktoken 0.12.0 virtualenv interpreter}"
: "${CACHE:?Set the prepared offline tokenizer cache}"
: "${RESULT:?Set a new result directory, not a historical result}"
producer=token-association-supersession/capture.py
mkdir "$RESULT"
"$PY" "$producer" freeze --protocol "$RESULT/protocol.json" \
  --product-source "$PUBLIC_SOURCE" --product-head "$PUBLIC_HEAD"
for run in first second; do
  "$PY" "$producer" capture --protocol "$RESULT/protocol.json" \
    --mousa "$BINARY" --product-source "$PUBLIC_SOURCE" --product-head "$PUBLIC_HEAD" \
    --python "$PY" --cache "$CACHE" --output "$RESULT/$run"
  "$PY" "$producer" verify --protocol "$RESULT/protocol.json" \
    --cache "$CACHE" --output "$RESULT/$run" > "$RESULT/$run/replay.json"
  "$PY" "$producer" controls --protocol "$RESULT/protocol.json" \
    --cache "$CACHE" --output "$RESULT/$run" > "$RESULT/$run/controls.json"
done
"$PY" "$producer" compare --protocol "$RESULT/protocol.json" --cache "$CACHE" \
  --output "$RESULT/first" --other "$RESULT/second" > "$RESULT/comparison.json"
python3 tools/make_manifest.py "$RESULT"
python3 tools/verify_results.py
