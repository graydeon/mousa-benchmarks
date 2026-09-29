"""Write or refresh one result directory manifest.

The manifest lists every regular file of a result directory except itself, so
`verify_results.py` can detect a file that was added, removed or modified after the run was
recorded. Optional `--product-base` and `--benchmark-base` revisions are carried into the
manifest when supplied.

Usage:
    make_manifest.py results/<run> [--product-base SHA] [--benchmark-base SHA]
"""

import argparse
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="result directory, relative to the repository root")
    parser.add_argument("--product-base", default=None)
    parser.add_argument("--benchmark-base", default=None)
    args = parser.parse_args()
    run = (root / args.run).resolve()
    if root not in run.parents or not run.is_dir():
        raise SystemExit("Run directory outside the repository: " + str(args.run))
    files = {}
    for path in sorted(run.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files[str(path.relative_to(run))] = {
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    manifest = {}
    if args.product_base:
        manifest["product_base"] = args.product_base
    if args.benchmark_base:
        manifest["benchmark_base"] = args.benchmark_base
    manifest["files"] = files
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Wrote", len(files), "members:", args.run)


if __name__ == "__main__":
    main()
