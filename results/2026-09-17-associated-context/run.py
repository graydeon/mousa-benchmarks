"""Record the declared-association comparison arms for the six frozen backup cases.

The record separates three things that the first published run left conflated:

* `before-default`  the pre-change product binary without declarations,
* `after-default`   the post-change product binary without declarations,
* `after-declared`  the post-change product binary with the fixed declaration file.

Both binaries query the same prepared corpus directory and use a fresh store per arm, so
packet identities are comparable within a run. Packet identities bind the absolute corpus
path, so a rerun under a different path produces the same bytes, evidence and outcomes
under different identities; the exact paths used are recorded in `commands.json`.

Usage:
    run.py --mousa-repo DIR --before BINARY --after BINARY --work DIR --raw DIR

`--raw` receives the recorded responses and `commands.json`; `--work` holds the generated
corpus, per-arm stores and scratch state that is not published. In the recorded run,
`--work` pointed at a scratch directory inside the measurement job.
"""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

CASES = "examples/backup/cases.json"
ASSOCIATIONS = "examples/backup/associations.json"
CONSUMER = "examples/backup/backup.py"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv, log):
    completed = subprocess.run(argv, capture_output=True, text=True)
    log.append({"argv": [str(item) for item in argv], "exit": completed.returncode})
    if completed.returncode != 0:
        raise SystemExit("command failed: " + " ".join(str(item) for item in argv)
                         + "\n" + completed.stderr.strip())
    return completed.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mousa-repo", type=Path, required=True)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True, help="scratch directory for corpus and stores")
    parser.add_argument("--raw", type=Path, required=True, help="recorded responses and commands.json")
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()

    repo = args.mousa_repo.resolve()
    consumer = repo / CONSUMER
    cases = json.loads((repo / CASES).read_text())["cases"]
    declarations = (repo / ASSOCIATIONS).resolve()
    responses = args.raw / "responses"
    responses.mkdir(parents=True, exist_ok=True)
    args.work.mkdir(parents=True, exist_ok=True)
    log = []
    arms = []

    def invoke(binary, store, corpus, case_id, question, budget, declared, arm):
        argv = [sys.executable, str(consumer), "--mousa", str(binary), "--store", str(store),
                "--directory", str(corpus), "retrieve", "--case", case_id,
                "--question", question, "--budget-bytes", str(budget)]
        if declared:
            argv += ["--associations", str(declarations)]
        stdout = run(argv, log)
        response = json.loads(stdout)["packet"]["response"]
        target = responses / f"{case_id}-{arm}.json"
        target.write_text(json.dumps(response, indent=2, sort_keys=True) + "\n")
        hits = response.get("evidence") or []
        arms.append({
            "case": case_id, "arm": arm, "file": str(target.relative_to(args.raw)),
            "query": response["query"], "budget_bytes": response["budget_bytes"],
            "used_bytes": response["used_bytes"], "outcome": response["outcome"],
            "packet_id": response["packet_id"],
            "packing_policy": response.get("packing_policy"),
            "hits": len(hits),
            "associated_hits": sum(hit.get("origin") == "association" for hit in hits),
            "items": sorted({hit["item"] for hit in hits}),
            "budget_omitted": response.get("budget_omitted"),
            "association_omissions": response.get("association_omissions") or [],
        })

    for case in cases:
        corpus = args.work / "corpus" / case["id"] / "docs"
        run([sys.executable, str(consumer), "--mousa", str(args.after),
             "--store", str(args.work / "stores" / case["id"] / "prepare.sqlite"),
             "--directory", str(corpus), "prepare"], log)
        for arm, binary, declared in (("before-default", args.before, False),
                                      ("after-default", args.after, False),
                                      ("after-declared", args.after, True)):
            store = args.work / "stores" / case["id"] / (arm + ".sqlite")
            store.parent.mkdir(parents=True, exist_ok=True)
            run([sys.executable, str(consumer), "--mousa", str(binary), "--store", str(store),
                 "--directory", str(corpus), "sync"], log)
            invoke(binary, store, corpus, case["id"], case["question"], case["budget"], declared, arm)
        followup = case.get("followup")
        if followup:
            store = args.work / "stores" / case["id"] / "after-declared-followup.sqlite"
            store.parent.mkdir(parents=True, exist_ok=True)
            run([sys.executable, str(consumer), "--mousa", str(args.after), "--store", str(store),
                 "--directory", str(corpus), "sync"], log)
            invoke(args.after, store, corpus, case["id"], followup["query"], followup["budget"],
                   True, "after-declared-followup")

    record = {
        "product_before": {"binary_sha256": sha256(args.before)},
        "product_after": {"binary_sha256": sha256(args.after)},
        "corpus_archive_sha256": sha256(repo / "examples/backup/python-docs.tar.xz"),
        "cases_sha256": sha256(repo / CASES),
        "declarations_sha256": sha256(declarations),
        "environment": {"platform": platform.platform(), "python": platform.python_version()},
        "commands": log,
        "arms": arms,
    }
    (args.raw / "commands.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    for arm in arms:
        print(json.dumps(arm, sort_keys=True))


if __name__ == "__main__":
    main()
