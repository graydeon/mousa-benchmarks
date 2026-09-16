"""Check archive integrity without running benchmarks."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "migration.json").read_text())
expected = set()
for entry in manifest["files"]:
    relative = entry["path"]
    path = (root / relative).resolve()
    if root not in path.parents or relative in expected:
        raise SystemExit("Invalid or duplicate manifest path: " + relative)
    expected.add(relative)
    data = path.read_bytes()
    json.loads(data)
    if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise SystemExit("Archived content changed: " + relative)
actual = {str(p.relative_to(root)) for directory in ("results/2026-09-16", "comparisons/qmd")
          for p in (root / directory).glob("*.json")}
if actual != expected:
    raise SystemExit("Archive files and migration manifest disagree")
print("Verified", len(expected), "unchanged migrated JSON files")
