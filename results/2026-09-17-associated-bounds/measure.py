"""Measure declared-association processing bounds and costs on bounded development fixtures.

The unit measured is one `mousa query` process, invoked the way the documentation consumers
invoke it (the query subcommand with a store, a directory root, an optional declaration file
and an explicit byte budget). Each measured launch reports its wall time, its own peak RSS, and
the facts derived from the response and from the recorded trail.

Fixtures are generated here, so every size, budget and declaration in the record is explicit.
Fixtures stay inside the documented default limits of the CLI (`--max-file-bytes` 1 MiB per
file, `--max-bytes` 64 MiB in total). The `large` target is a 1 MiB-class item of 1,000
passages, and `many-tiny` reaches the per-item passage cap (65,536 passages) with declaration
fields at their documented maximum length, which is the largest legal association stage a
default configuration can reach. Results are descriptive for the shared worker host, not a
comparison between machines.

Usage:
    measure.py --mousa BINARY --out DIR [--repetitions 5] [--large-repetitions 3]
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

TINY_BLOCK = "# a\n\n"
PASSAGE_PAYLOAD = 960
MAX_BASIS = 512
MAX_AUTHOR = 128


def payload_block(index):
    head = f"# P{index}\n\n"
    body = f"beta payload {index} " + "x" * (PASSAGE_PAYLOAD - len(head))
    return head + body + "\n\n"


def primary_text():
    return ("# Primary\n\nalpha procedure step one.\n\n"
            "# More\n\nalpha procedure step two.\n\n")


def declaration_file(path, pairs, maximum_fields=False):
    basis = "The procedure requires the qualification recorded in the declared target. "
    author = "bounds fixture maintainer"
    if maximum_fields:
        basis = (basis * (MAX_BASIS // len(basis) + 1))[:MAX_BASIS]
        author = (author * (MAX_AUTHOR // len(author) + 1))[:MAX_AUTHOR]
    path.write_text(json.dumps({"schema": "mousa.association_declarations.v1",
                                "associations": [
                                    {"from_item": from_item, "to_item": to_item,
                                     "basis": basis, "author": author}
                                    for from_item, to_item in pairs]}, indent=2) + "\n")


def build_cases(root):
    cases = {}

    def corpus(name, files):
        directory = root / name / "docs"
        directory.mkdir(parents=True)
        for filename, text in files.items():
            (directory / filename).write_text(text)
        return directory

    spelled = ("small", "medium", "large", "many-tiny", "fanout", "duplicate", "no-budget", "control")
    corpora = {
        "small": {"primary.md": primary_text(),
                  "target.md": "".join(payload_block(i) for i in range(4))},
        "medium": {"primary.md": primary_text(),
                   "target.md": "".join(payload_block(i) for i in range(256))},
        "large": {"primary.md": primary_text(),
                  "target.md": "".join(payload_block(i) for i in range(1000))},
        "many-tiny": {"primary.md": primary_text(), "target.md": TINY_BLOCK * 65536},
        "fanout": {"primary.md": primary_text()},
        "duplicate": {"primary.md": primary_text(),
                      "target.md": primary_text() + "".join(payload_block(i) for i in range(8))},
        "no-budget": {"primary.md": primary_text(),
                      "target.md": "".join(payload_block(i) for i in range(256))},
        "control": {"primary.md": primary_text(),
                    "target.md": "".join(payload_block(i) for i in range(256))},
    }
    for index in range(8):
        corpora["fanout"][f"target{index}.md"] = "".join(payload_block(i) for i in range(256))
    for name in spelled:
        directory = corpus(name, corpora[name])
        declarations = root / name / "declarations.json"
        if name == "fanout":
            declaration_file(declarations, [("primary.md", f"target{index}.md") for index in range(8)])
        else:
            declaration_file(declarations, [("primary.md", "target.md")],
                             maximum_fields=(name == "many-tiny"))
        cases[name] = {"directory": directory, "declarations": declarations}
    cases["control"]["declared"] = False
    return cases


def run_once(argv):
    """Run one process, returning its exit code, wall time and its own peak RSS."""
    with tempfile.TemporaryFile("w+") as out, tempfile.TemporaryFile("w+") as err:
        started = time.perf_counter()
        process = subprocess.Popen(argv, stdout=out, stderr=err, text=True)
        _, status, usage = os.wait4(process.pid, 0)
        wall_ms = (time.perf_counter() - started) * 1000.0
        out.seek(0)
        err.seek(0)
        return {"exit": os.waitstatus_to_exitcode(status), "wall_ms": wall_ms,
                "max_rss_kib": usage.ru_maxrss, "user_s": usage.ru_utime,
                "system_s": usage.ru_stime, "stdout": out.read(), "stderr": err.read()}


def facts(output):
    response = json.loads(output)
    hits = response.get("evidence") or []
    associated = [hit for hit in hits if hit.get("origin") == "association"]
    reasons = {}
    for omission in response.get("association_omissions") or []:
        reasons[omission["reason"]] = reasons.get(omission["reason"], 0) + 1
    return {"trail_id": response["trail_id"], "packet_id": response["packet_id"],
            "outcome": response["outcome"], "used_bytes": response["used_bytes"],
            "budget_bytes": response["budget_bytes"],
            "matched_candidates": response["matched_candidates"],
            "released_hits": len(hits), "associated_hits": len(associated),
            "associated_bytes": sum(hit["byte_length"] for hit in associated),
            "budget_omitted": response.get("budget_omitted"),
            "association_omission_reasons": reasons}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mousa", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--large-repetitions", type=int, default=3)
    parser.add_argument("--cases", default="", help="comma-separated subset of fixture names")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    fixtures = args.out / "fixtures"
    fixtures.mkdir(exist_ok=True)
    cases = build_cases(fixtures)
    if args.cases:
        selected = args.cases.split(",")
        unknown = [name for name in selected if name not in cases]
        if unknown:
            raise SystemExit("unknown fixture names: " + ", ".join(unknown))
        cases = {name: entry for name, entry in cases.items() if name in selected}
    binary = str(args.mousa.resolve())
    observations = []
    stores = args.out / "stores"
    stores.mkdir(exist_ok=True)

    def clone_store(case_name, tag):
        """Every observation queries its own copy of the closed synced store, so each measured
        launch opens the same workload instead of one store that accumulates earlier trails."""
        source = stores / f"{case_name}.sqlite"
        target = stores / f"{case_name}-{tag}.sqlite"
        for suffix in ("", "-wal", "-shm"):
            stale = Path(str(target) + suffix)
            if stale.exists():
                stale.unlink()
        shutil.copyfile(source, target)
        return target

    def query(case_name, budget, declared, tag):
        entry = cases[case_name]
        store = clone_store(case_name, tag)
        argv = [binary, "-store", str(store), "query", "--budget-bytes", str(budget)]
        if declared:
            argv += ["--associations", str(entry["declarations"])]
        argv += [str(entry["directory"]), "alpha"]
        measurement = run_once(argv)
        record = {"case": case_name, "tag": tag, "argv": argv, "exit": measurement["exit"],
                  "wall_ms": measurement["wall_ms"], "max_rss_kib": measurement["max_rss_kib"],
                  "user_s": measurement["user_s"], "system_s": measurement["system_s"],
                  "store_bytes": store.stat().st_size}
        if measurement["exit"] == 0:
            record.update(facts(measurement["stdout"]))
            inspection = run_once([binary, "-store", str(store), "trail",
                                   str(entry["directory"]), record["trail_id"]])
            record["trail_inspection_exit"] = inspection["exit"]
            record["trail_inspection_bytes"] = len(inspection["stdout"])
            record["trail_inspection_wall_ms"] = inspection["wall_ms"]
            if inspection["exit"] != 0:
                record["trail_inspection_stderr"] = inspection["stderr"].strip()[:400]
        else:
            record["stderr"] = measurement["stderr"].strip()[:400]
        observations.append(record)
        return record

    for case_name in sorted(cases):
        declared = cases[case_name].get("declared", True)
        sync_argv = [binary, "-store", str(stores / f"{case_name}.sqlite"),
                     "sync", "--segment-policy", "passage-v1",
                     str(cases[case_name]["directory"])]
        sync = run_once(sync_argv)
        observations.append({"case": case_name, "tag": "sync", "argv": sync_argv,
                             "exit": sync["exit"], "wall_ms": sync["wall_ms"],
                             "max_rss_kib": sync["max_rss_kib"],
                             "stderr": sync["stderr"].strip()[:200]})
        if sync["exit"] != 0:
            raise SystemExit(f"sync failed for {case_name}: {sync['stderr'].strip()[:400]}")
        query(case_name, 1 << 22, False, "warmup")
        primary_only = query(case_name, 1 << 22, False, "primary-only")
        budget = primary_only["used_bytes"] if case_name == "no-budget" else 4096
        if case_name != "control":
            query(case_name, 1 << 22, declared, "declared-unbounded")
        repetitions = args.large_repetitions if case_name in ("many-tiny", "large") else args.repetitions
        for index in range(repetitions):
            query(case_name, budget, declared, f"measured-{index}")

    (args.out / "observations.jsonl").write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in observations))

    summary = {}
    for record in observations:
        if not record["tag"].startswith("measured"):
            continue
        entry = summary.setdefault(record["case"], {"wall_ms": [], "max_rss_kib": [], "exits": [],
                                                    "trail_inspection_bytes": [], "associated_hits": [],
                                                    "omission_reasons": [], "used_bytes": [],
                                                    "trail_inspection_exits": []})
        entry["wall_ms"].append(record["wall_ms"])
        entry["max_rss_kib"].append(record["max_rss_kib"])
        entry["exits"].append(record["exit"])
        if record["exit"] == 0:
            entry["trail_inspection_exits"].append(record["trail_inspection_exit"])
            entry["trail_inspection_bytes"].append(record["trail_inspection_bytes"])
            entry["associated_hits"].append(record["associated_hits"])
            entry["used_bytes"].append(record["used_bytes"])
            entry["omission_reasons"].append(record["association_omission_reasons"])
    for entry in summary.values():
        entry["wall_ms_median"] = statistics.median(entry["wall_ms"])
        entry["wall_ms_min"] = min(entry["wall_ms"])
        entry["wall_ms_max"] = max(entry["wall_ms"])
        entry["max_rss_kib_max"] = max(entry["max_rss_kib"])
        entry["trail_inspection_bytes_max"] = max(entry["trail_inspection_bytes"] or [0])
    environment = {
        "runner": "omp-worker", "vcpus": os.cpu_count(), "platform": platform.platform(),
        "python": platform.python_version(),
        "binary_sha256": hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
        "repetitions": {"default": args.repetitions, "large": args.large_repetitions},
        "fixture_passage_payload_bytes": PASSAGE_PAYLOAD,
        "note": "Shared worker host; latency is descriptive, not a dedicated-host benchmark.",
    }
    (args.out / "environment.json").write_text(json.dumps(environment, indent=2, sort_keys=True) + "\n")
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({name: {"wall_ms_median": round(entry["wall_ms_median"], 1),
                             "wall_ms_max": round(entry["wall_ms_max"], 1),
                             "max_rss_kib_max": entry["max_rss_kib_max"],
                             "trail_inspection_bytes_max": entry["trail_inspection_bytes_max"],
                             "exits": entry["exits"]} for name, entry in sorted(summary.items())},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
