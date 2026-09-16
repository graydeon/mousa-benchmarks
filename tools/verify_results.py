"""Check archive integrity without running benchmarks."""
import hashlib
import json
from pathlib import Path
import tarfile

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

for manifest_path in sorted((root / "results").glob("*/manifest.json")):
    run = manifest_path.parent
    report = json.loads(manifest_path.read_text())
    files = report["files"]
    for relative, expected in files.items():
        path = (run / relative).resolve()
        if run not in path.parents or not path.is_file():
            raise SystemExit("Invalid run member: " + relative)
        data = path.read_bytes()
        if len(data) != expected["bytes"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise SystemExit("Run content changed: " + str(path.relative_to(root)))
    actual = {str(path.relative_to(run)) for path in run.rglob("*") if path.is_file()
              and path != manifest_path}
    if actual != set(files):
        raise SystemExit("Run files and manifest disagree: " + run.name)
    print("Verified", len(files), "run files:", run.name)
    fixture_archive = run / "fixtures.tar.gz"
    if fixture_archive.exists():
        expected_inputs = json.loads((run / "protocol.json").read_text())["manifest"]
        found = {}
        with tarfile.open(fixture_archive) as archive:
            for member in archive.getmembers():
                name = member.name.removeprefix("fixtures/")
                if (not member.isfile() or not member.name.startswith("fixtures/")
                        or name not in expected_inputs or name in found or member.size > 1 << 20):
                    raise SystemExit("Invalid fixture member: " + member.name)
                found[name] = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
        if found != expected_inputs:
            raise SystemExit("Frozen fixture bytes changed: " + run.name)
        print("Verified", len(found), "unchanged frozen fixtures")
