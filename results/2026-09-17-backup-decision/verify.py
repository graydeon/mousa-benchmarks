"""Reconstruct captured sources and verify every archived observation."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

# Reuse the preceding documentation study's bounded regular-file unpacker.
previous = Path(__file__).resolve().parents[1] / "2026-09-17-corpus-boundaries"
sys.path.insert(0, str(previous))
spec = importlib.util.spec_from_file_location("corpus_archive", previous / "verify.py")
corpus_archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(corpus_archive)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-source", type=Path, required=True,
                        help="git archive of the protocol's product base")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    expected = json.loads((here / "archive-members.json").read_bytes())
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        corpus_archive.unpack(here / "raw.tar.xz", root)
        actual = {str(path.relative_to(root)): {"bytes": path.stat().st_size,
                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                  for path in root.rglob("*") if path.is_file()}
        if actual != expected:
            raise ValueError("archived member content or membership changed")
        for phase in ("pilot", "measured"):
            source = root / (phase + "-source")
            corpus_archive.unpack(args.base_source, source)
            corpus_archive.unpack(root / phase / "source-delta.tar.gz", source)
            subprocess.run([sys.executable, str(here / "analyze.py"), str(root / phase),
                            "--product", str(source)], check=True, timeout=120)
    print("Verified all archived members and both exact-source reanalyses")


if __name__ == "__main__":
    main()
