"""Restore the original measured gzip capture after extracting evidence.tar.xz."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", type=Path, help="Extracted evidence directory")
args = parser.parse_args()
inventory = json.loads(Path(__file__).with_name("archive-inventory.json").read_text())
payload = (args.directory / "capture.codec.json").read_bytes()
expected = inventory["members"]["capture.codec.json"]
if len(payload) != expected["bytes"] or hashlib.sha256(payload).hexdigest() != expected["sha256"]:
    raise SystemExit("Capture payload identity mismatch")
restored = gzip.compress(payload, mtime=0)
expected = inventory["capture_restore"]
if len(restored) != expected["bytes"] or hashlib.sha256(restored).hexdigest() != expected["sha256"]:
    raise SystemExit("Gzip encoder does not reproduce the measured capture; use Python 3.13.5")
with (args.directory / "capture.json.gz").open("xb") as output:
    output.write(restored)
print("Restored byte-identical measured capture")
