"""Tiny synthetic adapter smoke; these observations are never enterprise pilot scores."""
import argparse
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time

import prepare


def metrics(ranking, gold):
    prepare.check(bool(gold), "unscorable-empty-gold")
    # Routes normalize to the first occurrence of each document before cutoffs.
    ranking = list(dict.fromkeys(ranking))
    ideal = sum(1 / math.log2(i + 2) for i in range(min(10, len(gold))))
    return {"recall_at_10": len(set(ranking[:10]) & gold) / len(gold),
            "recall_at_100": len(set(ranking[:100]) & gold) / len(gold),
            "binary_ndcg_at_10": sum(1 / math.log2(i + 2) for i, d in enumerate(ranking[:10]) if d in gold) / ideal,
            "mrr_at_10": next((1 / (i + 1) for i, d in enumerate(ranking[:10]) if d in gold), 0)}


def stable_rows(directory):
    result = {}
    for path in sorted(directory.glob("*.json.jsonl")):
        result[path.name] = [{key: value for key, value in prepare.parsed(line).items()
                              if key not in ("LatencyMicros", "SearchMicros", "PreprocessMicros")}
                             for line in path.read_bytes().splitlines()]
    return result

def compare_rows(left, right):
    prepare.check(set(left) == set(right), "sanity-arm-population")
    for name in left:
        prepare.check([r["QueryID"] for r in left[name]] == [r["QueryID"] for r in right[name]], "sanity-enrollment")
        prepare.check([r["RankedDocIDs"] for r in left[name]] == [r["RankedDocIDs"] for r in right[name]], "ranking-binding")
        prepare.check([(r["SelectedDocIDs"], r["UsedBytes"]) for r in left[name]]
                      == [(r["SelectedDocIDs"], r["UsedBytes"]) for r in right[name]], "packed-binding")
    prepare.check(prepare.wire.same_json(left, right), "stable-query-binding")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--beir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    work = args.out.resolve()
    work.mkdir(parents=True, exist_ok=False)
    data = work / "data"
    (data / "qrels").mkdir(parents=True)
    corpus = {"d-a": "needle " * 220, "d-b": "needle orchard soil"}
    queries = {"toy-q1": "needle needle", "toy-q2": "orchard"}
    gold = {"toy-q1": {"d-a"}, "toy-q2": {"d-b"}}
    (data / "corpus.jsonl").write_bytes(b"".join(prepare.encoded({"_id": k, "title": "", "text": v}).replace(b"\n", b" ") + b"\n" for k, v in corpus.items()))
    (data / "queries.jsonl").write_bytes(b"".join(prepare.encoded({"_id": k, "text": v}).replace(b"\n", b" ") + b"\n" for k, v in queries.items()))
    (data / "qrels/test.tsv").write_text("query-id\tcorpus-id\tscore\n" + "".join(f"{q}\t{d}\t1\n" for q in queries for d in sorted(gold[q])))
    before = {str(p.relative_to(data)): prepare.manifest(p.read_bytes()) for p in data.rglob("*") if p.is_file()}
    binary = os.path.relpath(args.beir.resolve(), work)
    commands = []
    def run(arguments, expected_exit=0):
        command = [binary, *arguments]
        started = time.monotonic()
        result = subprocess.run(command, cwd=work, capture_output=True, timeout=120, check=False)
        commands.append({"argv": command, "exit": result.returncode, "wall_seconds": time.monotonic() - started,
                         "stdout": prepare.wire.stream(result.stdout), "stderr": prepare.wire.stream(result.stderr)})
        (work / "commands.json").write_bytes(prepare.encoded(commands))
        prepare.check(result.returncode == expected_exit, "sanity-command-exit")
        return result

    indexed = None
    for policy in ("original", "dedup"):
        for mode, budget in (("verified", 1024), ("traced", 1024), ("traced", 4096)):
            name = f"{policy}-{mode}-{budget}.json"
            argv = ["-data", "data", "-dataset", "toy-adapter-sanity", "-out", name,
                    "-mode", mode, "-policy", policy, "-limit", "100", "-budget", str(budget), "-query-timeout", "30s"]
            if indexed is not None:
                current = {str(p.relative_to(data)): prepare.manifest(p.read_bytes()) for p in data.rglob("*") if p.is_file()}
                prepare.check(current == before, "reuse-corpus-manifest")
                prepare.check(prepare.parsed((work / "original-verified-1024.json.manifest.json").read_bytes()) == indexed, "reuse-index-manifest")
                argv.append("-reuse")
            run(argv)
            if indexed is None:
                indexed = prepare.parsed((work / (name + ".manifest.json")).read_bytes())
        run(["-report", "compare", "-reports", f"{policy}-verified-1024.json,{policy}-traced-1024.json", "-axis", "mode", "-out", f"{policy}-mode-comparison.json"])
        run(["-report", "compare", "-reports", f"{policy}-traced-1024.json,{policy}-traced-4096.json", "-axis", "budget", "-out", f"{policy}-budget-comparison.json"])
        refusal = run(["-report", "coverage", "-reports", f"{policy}-traced-1024.json,{policy}-traced-4096.json", "-out", f"{policy}-coverage.json"], expected_exit=1)
        prepare.check(b"without pack coverage" in refusal.stderr, "native-coverage-refusal")
    run(["-report", "compare", "-reports", "original-verified-1024.json,dedup-verified-1024.json", "-axis", "policy", "-out", "policy-comparison.json"])
    connection = sqlite3.connect(work / "reference.sqlite")
    connection.execute("CREATE VIRTUAL TABLE search USING fts5(item_id UNINDEXED,body, tokenize='unicode61 remove_diacritics 2')")
    for item, body in corpus.items():
        connection.execute("INSERT INTO search VALUES(?,?)", (item, prepare.render(body.encode()).decode()))
    connection.commit()
    baseline = []
    for qid, query in queries.items():
        expression = " OR ".join('"' + term + '"' for term in re.findall(r"[A-Za-z0-9]+", query.lower()))
        deadline = time.monotonic() + 30
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 100)
        started = time.monotonic()
        rows = connection.execute("SELECT item_id,bm25(search) FROM search WHERE search MATCH ? ORDER BY bm25(search),item_id LIMIT 100", (expression,)).fetchall()
        ranking = list(dict.fromkeys(r[0] for r in rows))
        baseline.append({"question_id": qid, "expression": expression, "rows": rows,
                         "wall_seconds": time.monotonic() - started, "metrics": metrics(ranking, gold[qid])})
    connection.close()
    (work / "sqlite.json").write_bytes(prepare.encoded({"sqlite_version": sqlite3.sqlite_version, "results": baseline}))
    rows = stable_rows(work)
    for name, results in rows.items():
        prepare.check([r["QueryID"] for r in results] == list(queries), "sanity-enrollment")
        report = prepare.parsed((work / name.removesuffix(".jsonl")).read_bytes())
        scores = []
        for result, reported in zip(results, report["queries"]):
            scores.append(metrics(result["RankedDocIDs"] or [], gold[result["QueryID"]]))
            prepare.check(reported["query_id"] == result["QueryID"], "metric-reference-query")
        for key in ("recall_at_100", "binary_ndcg_at_10", "mrr_at_10"):
            prepare.check(math.isclose(sum(score[key] for score in scores) / len(scores),
                                       report["aggregate"][key]), "metric-reference-" + key)
        if "traced-1024" in name:
            prepare.check(results[0]["SelectedDocIDs"] == ["d-b"] and results[0]["UsedBytes"] == 19, "engine-oversized-omission")
        if "traced-4096" in name:
            prepare.check(set(results[0]["SelectedDocIDs"]) == {"d-a", "d-b"}, "engine-larger-budget")
    (work / "stable.json").write_bytes(prepare.encoded(rows))
    print("PASS synthetic adapter: six Mousa arms, ranking comparisons, SQLite FTS5; native coverage helper REFUSED (exit1); no enterprise query executed")


if __name__ == "__main__":
    main()
