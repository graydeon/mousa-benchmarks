"""Check saved citations, caller coverage and fixed outcomes separately."""

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--product", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.product / "examples/backup"))
    import backup
    identity = json.loads((args.run / "identity.json").read_bytes())
    source_archive = args.run / "source.tar.gz"
    if source_archive.exists():
        if hashlib.sha256(source_archive.read_bytes()).hexdigest() != identity["source_archive_sha256"]:
            raise ValueError("source archive changed")
        source_hashes = {}
        with tarfile.open(source_archive) as archive:
            for member in archive:
                path = Path(member.name)
                if not member.isfile() or path.is_absolute() or ".." in path.parts or member.name in source_hashes:
                    raise ValueError("invalid source archive member")
                source_hashes[member.name] = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
    else:
        # Published deltas reconstruct member bytes, not the original gzip header.
        source_hashes = {str(p.relative_to(args.product)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in args.product.rglob("*") if p.is_file()
                         and ".git" not in p.parts and "__pycache__" not in p.parts}
    if source_hashes != identity["source_files"]:
        raise ValueError("source snapshot manifest mismatch")
    for name in ("examples/backup/backup.py", "examples/backup/cases.json", "examples/docs/docs.py", "eval/local/workflow.py"):
        if hashlib.sha256((args.product / name).read_bytes()).hexdigest() != source_hashes[name]:
            raise ValueError("reanalysis uses different consumer source: " + name)
    rows = json.loads((args.run / "rows.json").read_bytes())
    expected = {case["id"]: case for case in backup.CASES["cases"]}
    if [row["case"] for row in rows] != list(expected):
        raise ValueError("fixed case membership or order changed")
    for row in rows:
        work = args.run / row["case"]
        if row["execution"] != "PASS":
            raise ValueError("preserved execution failure: " + row["case"])
        commands = json.loads((work / "commands.json").read_bytes())
        if any(command["exit_code"] for command in commands):
            raise ValueError("execution report disagrees with command exits")
        stages = [("initial", "assessment", "initial-decision")]
        if "followup" in expected[row["case"]]:
            stages.append(("followup", "final-assessment", "final-decision"))
        for packet_name, assessment_name, decision_name in stages:
            raw = (work / (packet_name + ".json")).read_bytes()
            assessment = json.loads((work / (assessment_name + ".json")).read_bytes())
            checked = backup.assess(raw, assessment, work / "corpus")
            reported = json.loads((work / (decision_name + ".json")).read_bytes())
            reported.pop("elapsed_ms")
            if reported != checked:
                raise ValueError("saved decision differs from verified caller review")
        case = expected[row["case"]]
        final_expected = case.get("followup", {}).get("expected", case["expected"])
        if row["initial_decision"] != case["expected"] or row["final_decision"] != final_expected:
            raise ValueError("decision expectation missed: " + row["case"])
        if (row["final_decision"] == "covered") != all(f["judgment"] == "supported" for f in row["final_coverage"].values()):
            raise ValueError("coverage is not completeness")
    summary = {"execution": "PASS", "citation_consistency": "PASS", "cases": len(rows),
               "measured_phase": identity["phase"], "queries": sum(1 + r["followup_count"] for r in rows),
               "whole_consumer_median_ms": statistics.median(r["whole_consumer_ms"] for r in rows),
               "released_bytes_total": sum(r["released_bytes"] for r in rows),
               "outcomes": [{key: row[key] for key in ("case", "initial_decision", "final_decision", "unresolved_facts",
                            "followup_count", "followup_changed_decision", "reviewed_failure_categories")} for row in rows],
               "limitation": "Six development cases; curated judgments, no assessor accuracy; partial-case mechanism missed its original context hypothesis and observed budget omission instead."}
    (args.run / "analysis.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
