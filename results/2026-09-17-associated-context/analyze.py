"""Derive the corrected comparison record from the recorded raw responses.

`run.py` writes one CLI response per arm under `responses/` and the exact commands and
artifact hashes under `commands.json`. This script derives every published number from
those files and fails when the recorded arms do not support their labels:

* an arm recorded as declaration-enabled must carry an association stage, or be a case in
  which no primary passage was selected and the declaration therefore cannot fire;
* the default-path arms must agree between the pre-change and post-change binary;
* a declared arm must not displace any primary passage;
* released bytes must equal the sum of the released passages and stay inside the budget.

Usage:
    analyze.py --dir results/2026-09-17-associated-context
"""

import argparse
import json
from pathlib import Path

QUALIFICATION_NOTE = "closes the connection"
DEFAULT_COMPARABLE = ("packet_id", "used_bytes", "budget_bytes", "outcome", "matched_candidates",
                      "budget_omitted", "lifecycle_excluded", "packing_policy", "expression")
HIT_PROJECTION = ("item", "representation_sha256", "byte_start", "byte_end", "segment_policy",
                  "content_sha256", "rank", "score", "byte_length", "origin")


def projection(response, fields):
    return {field: response.get(field) for field in fields}


def hits(response, origin=None):
    released = response.get("evidence") or []
    return [hit for hit in released if origin is None or hit.get("origin") == origin]


def hit_signature(selected):
    return [{**projection(hit, HIT_PROJECTION), "origin": hit.get("origin", "lexical")}
            for hit in selected]


def summarize(response):
    released = hits(response)
    associated = hits(response, "association")
    return {
        "query": response["query"],
        "budget_bytes": response["budget_bytes"],
        "used_bytes": response["used_bytes"],
        "outcome": response["outcome"],
        "packet_id": response["packet_id"],
        "packing_policy": response.get("packing_policy"),
        "matched_candidates": response["matched_candidates"],
        "budget_omitted": response.get("budget_omitted"),
        "lifecycle_excluded": response.get("lifecycle_excluded"),
        "released_hits": len(released),
        "released_items": sorted({hit["item"] for hit in released}),
        "associated_hits": len(associated),
        "associated_bytes": sum(hit["byte_length"] for hit in associated),
        "association_omissions": response.get("association_omissions") or [],
        "qualification_note_released": any(QUALIFICATION_NOTE in (hit.get("text") or "") for hit in released),
    }


def load(directory, case_id, arm):
    path = directory / "raw" / "responses" / f"{case_id}-{arm}.json"
    if not path.is_file():
        raise SystemExit("missing recorded response: " + str(path))
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    directory = args.dir.resolve()
    commands = json.loads((directory / "raw" / "commands.json").read_text())
    arms = commands["arms"]
    cases = sorted({arm["case"] for arm in arms})

    report = {"cases": {}, "assertions": []}
    failures = []

    def check(condition, message):
        record = {"assertion": message, "result": "pass" if condition else "fail"}
        report["assertions"].append(record)
        if not condition:
            failures.append(message)

    for case_id in cases:
        before = load(directory, case_id, "before-default")
        current = load(directory, case_id, "after-default")
        declared = load(directory, case_id, "after-declared")
        default_same = projection(before, DEFAULT_COMPARABLE) == projection(current, DEFAULT_COMPARABLE)
        default_evidence_same = hit_signature(hits(before)) == hit_signature(hits(current))
        for response in (before, current, declared):
            released = hits(response)
            check(response["used_bytes"] == sum(hit["byte_length"] for hit in released),
                  f"{case_id}: released bytes equal the released passages")
            check(response["used_bytes"] <= response["budget_bytes"],
                  f"{case_id}: released bytes stay inside the budget")
        check(default_same, f"{case_id}: default-path response fields are unchanged")
        check(default_evidence_same, f"{case_id}: default-path released passages are unchanged")

        current_primary = hit_signature(hits(current))
        declared_primary = hit_signature(hits(declared, "lexical"))
        check(declared_primary[:len(current_primary)] == current_primary,
              f"{case_id}: declaration displaced no primary passage")
        if hits(current):
            check(declared.get("packing_policy") == "original"
                  and (len(hits(declared, "association")) > 0 or declared.get("association_omissions")),
                  f"{case_id}: declaration-enabled arm carries an association stage")
        else:
            check(declared["packet_id"] == current["packet_id"] and not declared.get("packing_policy"),
                  f"{case_id}: declaration cannot fire without a selected primary passage")

        entry = {
            "before_default": summarize(before),
            "after_default": summarize(current),
            "after_declared": summarize(declared),
            "default_path_identical": default_same and default_evidence_same,
            "added_bytes": declared["used_bytes"] - current["used_bytes"],
            "added_hits": len(hits(declared)) - len(hits(current)),
        }
        followup = load(directory, case_id, "after-declared-followup") if (directory / "raw" / "responses" / f"{case_id}-after-declared-followup.json").is_file() else None
        if followup is not None:
            entry["after_declared_followup"] = summarize(followup)
        report["cases"][case_id] = entry

    (directory / "raw" / "comparison-arms.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    totals = {"cases": len(cases), "added_bytes": sum(entry["added_bytes"] for entry in report["cases"].values()),
              "added_hits": sum(entry["added_hits"] for entry in report["cases"].values())}
    print(json.dumps(totals, sort_keys=True))
    for record in report["assertions"]:
        if record["result"] == "fail":
            print("FAIL:", record["assertion"])
    for arm in arms:
        print(json.dumps({key: arm[key] for key in ("case", "arm", "used_bytes", "packing_policy",
                                                    "hits", "associated_hits")}, sort_keys=True))
    if failures:
        raise SystemExit(f"{len(failures)} assertion(s) failed")
    print(f"all {len(report['assertions'])} assertions passed")


if __name__ == "__main__":
    main()
