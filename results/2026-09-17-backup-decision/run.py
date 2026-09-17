"""Run six fixed backup-decision cases with explicit curated caller reviews."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def bind_review(review, packets):
    facts = []
    for key, judgment in review.items():
        references = []
        for coordinate in judgment["references"]:
            response = packets[coordinate["packet"]]["response"]
            matches = [hit for hit in response["evidence"] or [] if all(
                hit[field] == coordinate[field] for field in ("item", "byte_start", "byte_end"))]
            if len(matches) != 1:
                raise ValueError("Curated reference not returned: " + json.dumps(coordinate))
            references.append({"packet_id": response["packet_id"], "segment_id": matches[0]["segment_id"]})
        facts.append({"id": key, "judgment": judgment["judgment"], "reason": judgment["reason"], "references": references})
    return facts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product", type=Path, required=True)
    parser.add_argument("--mousa", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("pilot", "measured"), required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    product = args.product.resolve()
    methods = Path(__file__).resolve().parent
    protocol = json.loads((methods / "protocol.json").read_bytes())
    cases_raw = (product / "examples/backup/cases.json").read_bytes()
    review_raw = (methods / "reviews.json").read_bytes()
    if sha(cases_raw) != protocol["cases_sha256"] or sha(review_raw) != protocol["reviews_sha256"]:
        raise ValueError("Frozen inputs changed")
    if sha((product / "examples/backup/python-docs.tar.xz").read_bytes()) != protocol["corpus_archive_sha256"]:
        raise ValueError("Corpus archive changed")
    cases = json.loads(cases_raw)["cases"]
    reviews = json.loads(review_raw)["cases"]
    source_manifest = {}
    with tarfile.open(args.output / "source.tar.gz", "w:gz") as archive:
        for path in sorted(product.rglob("*")):
            if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if path.is_symlink():
                raise ValueError("Source snapshot contains a link")
            data = path.read_bytes()
            name = str(path.relative_to(product))
            source_manifest[name] = sha(data)
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
    save(args.output / "identity.json", {"phase": args.phase, "product_base": protocol["product_base"],
         "benchmark_base": protocol["benchmark_base"], "source_files": source_manifest,
         "source_archive_sha256": sha((args.output / "source.tar.gz").read_bytes()),
         "binary_sha256": sha(args.mousa.read_bytes()), "build_flags": "CGO_ENABLED=0 go build",
         "methods": {p.name: sha(p.read_bytes()) for p in methods.iterdir() if p.is_file()},
         "uid": os.getuid(), "gid": os.getgid(), "python": sys.version,
         "go_build": subprocess.check_output(["go", "version", "-m", str(args.mousa)], text=True)})
    rows = []
    for case in cases:
        work = args.output / case["id"]
        work.mkdir()
        directory = work / "corpus"
        store = work / "store.sqlite"
        prefix = [sys.executable, str(product / "examples/backup/backup.py"), "--mousa", str(args.mousa),
                  "--store", str(store), "--directory", str(directory)]
        commands = []

        def call(name, arguments):
            started = time.perf_counter_ns()
            process = subprocess.run(prefix + arguments, capture_output=True, timeout=60)
            elapsed = (time.perf_counter_ns() - started) / 1e6
            (work / (name + ".json")).write_bytes(process.stdout)
            (work / (name + ".stderr")).write_bytes(process.stderr)
            commands.append({"name": name, "arguments": arguments, "exit_code": process.returncode, "wall_ms": elapsed})
            save(work / "commands.json", commands)
            if process.returncode:
                raise RuntimeError(process.stderr.decode())
            return json.loads(process.stdout)

        row = {"case": case["id"], "phase": args.phase, "execution": "FAIL"}
        rows.append(row)
        try:
            call("prepare", ["prepare"])
            call("sync", ["sync"])
            manifest = json.loads((directory / "corpus.json").read_bytes())
            row["document_bytes"] = sum((directory / p).stat().st_size for p in manifest["documents"])
            row["documents"] = len(manifest["documents"])
            row["store_bytes_before"] = store.stat().st_size
            row["query_history_before"] = 0
            started = time.perf_counter_ns()
            initial = call("initial", ["retrieve", "--case", case["id"]])
            packets = [initial["packet"]]
            assessment = call("template", ["template", "--packet", str(work / "initial.json"), "--caller", "Curated development reviewer"])
            assessment["facts"] = bind_review(reviews[case["id"]]["initial"], packets)
            if "followup" in case:
                choice = case["followup"]
                assessment["next_retrieval"] = {"fact": choice["fact"], "question": choice["query"], "budget_bytes": choice["budget"]}
            save(work / "assessment.json", assessment)
            initial_decision = call("initial-decision", ["assess", "--packet", str(work / "initial.json"), "--assessment", str(work / "assessment.json")])
            final_decision = initial_decision
            if "followup" in case:
                followup = call("followup", ["followup", "--packet", str(work / "initial.json"), "--assessment", str(work / "assessment.json")])
                packets.append(followup["packet"])
                final_assessment = call("final-template", ["template", "--packet", str(work / "followup.json"), "--caller", "Curated development reviewer"])
                final_assessment["facts"] = bind_review(reviews[case["id"]]["final"], packets)
                save(work / "final-assessment.json", final_assessment)
                final_decision = call("final-decision", ["assess", "--packet", str(work / "followup.json"), "--assessment", str(work / "final-assessment.json")])
            row.update({"execution": "PASS", "whole_consumer_ms": (time.perf_counter_ns() - started) / 1e6,
                        "initial_decision": initial_decision["decision"], "final_decision": final_decision["decision"],
                        "initial_coverage": initial_decision["coverage"], "final_coverage": final_decision["coverage"],
                        "citation_consistency": final_decision["citation_consistency"],
                        "unresolved_facts": final_decision["unresolved_facts"], "followup_count": len(packets) - 1,
                        "followup_changed_decision": initial_decision["decision"] != final_decision["decision"],
                        "released_bytes": final_decision["released_bytes"], "query_history_after": len(packets),
                        "store_bytes_after": store.stat().st_size,
                        "returned_segments": [len(p["response"]["evidence"] or []) for p in packets],
                        "budget_omitted": [p["response"].get("budget_omitted", 0) for p in packets],
                        "reviewed_failure_categories": protocol["categories"][case["id"]]})
        except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as error:
            row["error"] = str(error)
        save(args.output / "rows.json", rows)
        print(case["id"], row["execution"], row.get("initial_decision"), row.get("final_decision"), flush=True)
    return int(any(row["execution"] != "PASS" for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
