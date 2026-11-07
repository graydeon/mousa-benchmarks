#!/bin/sh
# Run from the companion root only after anonymous exact-public source readback.
set -eu
: "${PUBLIC_HEAD:?Set the exact published product commit}"
: "${PUBLIC_SOURCE:?Set its clean anonymous checkout directory}"
: "${BINARY:?Set its CGo-free binary built outside that checkout}"
: "${RESULT:?Set a new result directory}"
producer=source-manifests/capture.py
mkdir "$RESULT"
python3 "$producer" freeze --protocol "$RESULT/protocol.json" --product-source "$PUBLIC_SOURCE" --product-head "$PUBLIC_HEAD"
for run in first second; do
  python3 "$producer" capture --protocol "$RESULT/protocol.json" --mousa "$BINARY" --product-source "$PUBLIC_SOURCE" --product-head "$PUBLIC_HEAD" --output "$RESULT/$run"
  python3 "$producer" verify --protocol "$RESULT/protocol.json" --output "$RESULT/$run" > "$RESULT/$run/replay.json"
  python3 "$producer" controls --protocol "$RESULT/protocol.json" --output "$RESULT/$run" > "$RESULT/$run/controls.json"
done
python3 "$producer" compare --protocol "$RESULT/protocol.json" --output "$RESULT/first" --other "$RESULT/second" > "$RESULT/comparison.json"
python3 tools/make_manifest.py "$RESULT" --product-base "$PUBLIC_HEAD"
python3 tools/verify_results.py
