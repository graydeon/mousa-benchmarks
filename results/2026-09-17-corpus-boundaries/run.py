"""Compare fixed documentation cases with fresh query history in both corpora."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(data):
    return data.removeprefix(b"\xef\xbb\xbf").replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def counts(store):
    if any(Path(str(store) + suffix).exists() for suffix in ("-wal", "-shm")):
        raise ValueError("closed measurement store has sidecars")
    connection = sqlite3.connect(store.as_uri() + "?immutable=1", uri=True)
    try:
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {name: connection.execute('SELECT count(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0]
                for name in tables if not name.startswith("sqlite_")}
    finally:
        connection.close()


def assess(packet, case, manifest, documents, verify_evidence, budget):
    response = packet["response"]
    assert packet["answer"] is None and packet["support"] == "not_assessed"
    spans = {}
    released = 0
    for hit in response["evidence"] or []:
        name = hit["item"]
        released += len(verify_evidence(hit, documents[name]))
        data = normalize(documents[name])
        assert hit["location"] == {
            "path": name, "url": manifest["files"][name]["url"],
            "line_start": data[:hit["byte_start"]].count(b"\n") + 1,
            "line_end": data[:hit["byte_end"] - 1].count(b"\n") + 1}
        spans.setdefault(name, []).append((hit["byte_start"], hit["byte_end"]))
    assert released == response["used_bytes"] and released <= budget
    covered = []
    for required in case["support"]:
        name = required["item"]
        data = normalize(documents.get(name, b""))
        start = data.find(required["text"].encode())
        end = start + len(required["text"].encode())
        cursor = start
        for left, right in sorted(spans.get(name, [])):
            if left <= cursor < right:
                cursor = right
        covered.append(start >= 0 and cursor >= end)
    support = "complete" if covered and all(covered) else "partial" if any(covered) else "absent"
    return {"support": support, "supporting_passages": covered,
            "expected_outcome_met": packet["outcome"] == case["expected_outcome"] if "expected_outcome" in case else None,
            "released_bytes": released, "budget_omitted": response["budget_omitted"],
            "locations_and_ranges_verified": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product", type=Path, required=True)
    parser.add_argument("--mousa", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    product = args.product.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(product / "examples/docs"))
    import docs
    protocol = json.loads((here / "cases.json").read_text())
    original_cases = json.loads((product / "examples/docs/questions.json").read_text())
    cases = [{**case, "support": [{"item": case["item"], "text": text} for text in case["support"]]}
             for case in original_cases["development"]] + protocol["development"]
    archives = {"original": args.original.resolve(), "expanded": product / "examples/docs/git-docs.tar.xz"}
    source_files = sorted(p for p in product.rglob("*") if p.is_file() and not p.is_symlink()
                          and ".git" not in p.parts and "__pycache__" not in p.parts)
    identities = {str(p.relative_to(product)): digest(p) for p in source_files}
    (out / "source-manifest.json").write_text(json.dumps(identities, indent=2) + "\n")
    with tarfile.open(out / "source.tar.gz", "w:gz") as archive:
        for path in source_files:
            archive.add(path, arcname=str(path.relative_to(product)), recursive=False)
    for name, path in archives.items():
        shutil.copyfile(path, out / (name + "-corpus.tar.xz"))
    shutil.copyfile(here / "cases.json", out / "cases.json")
    shutil.copyfile(Path(__file__), out / "run.py")
    shutil.copyfile(product / "examples/docs/questions.json", out / "questions.json")
    identity = {"binary_sha256": digest(args.mousa), "source_manifest_sha256": digest(out / "source-manifest.json"),
                "run_sha256": digest(Path(__file__)), "cases_sha256": digest(here / "cases.json"),
                "mode": "pilot" if args.pilot else "measured", "engine": "unchanged core; original packing; passage-v1",
                "build": subprocess.check_output(["go", "version", "-m", str(args.mousa)], text=True)}
    (out / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    rows = []
    try:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            corpora = {}
            for arm, archive_path in archives.items():
                directory = root / arm
                directory.mkdir()
                with tarfile.open(archive_path) as archive:
                    for member in archive.getmembers():
                        docs.relative_path(member.name)
                        assert member.isfile() and member.size < 1_000_000
                        path = directory / member.name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(archive.extractfile(member).read())
                manifest, documents, _ = docs.load_corpus(directory)
                corpora[arm] = (directory, manifest, documents)
            expanded = corpora["expanded"][2]
            for case in cases:
                for required in case["support"]:
                    assert required["text"].encode() in normalize(expanded[required["item"]]), case["id"]
            repeats = 1 if args.pilot else protocol["repeats"]
            for repeat in range(repeats):
                for index, case in enumerate(cases):
                    arms = ("original", "expanded") if (repeat + index) % 2 == 0 else ("expanded", "original")
                    for arm in arms:
                        directory, manifest, documents = corpora[arm]
                        store = root / f"{repeat}-{index}-{arm}.sqlite"
                        command = [sys.executable, str(product / "examples/docs/docs.py"), "--mousa", str(args.mousa.resolve()),
                                   "--store", str(store), "--directory", str(directory)]
                        sync = subprocess.run([*command, "sync"], capture_output=True, text=True, timeout=60)
                        assert sync.returncode == 0, sync.stderr
                        before = counts(store)
                        assert before["source_trails"] == before["policy_decisions"] == 0
                        cost = root / "cost.txt"
                        started = time.perf_counter_ns()
                        process = subprocess.run(["/usr/bin/time", "-f", "%U %S %M", "-o", str(cost),
                                                  *command, "ask", "--budget-bytes", str(protocol["budget_bytes"]), case["question"]],
                                                 capture_output=True, text=True, timeout=60)
                        wall = (time.perf_counter_ns() - started) / 1e6
                        row = {"repeat": repeat, "case": case["id"], "arm": arm, "wall_ms": wall,
                               "exit": process.returncode, "stdout": process.stdout, "stderr": process.stderr,
                               "cost_user_system_seconds_maxrss_kib": cost.read_text().strip(),
                               "corpus_document_bytes": sum(map(len, documents.values())),
                               "corpus_hashed_bytes": sum((directory / name).stat().st_size for name in manifest["files"]),
                               "document_count": len(documents), "store_bytes": store.stat().st_size,
                               "counts_before": before, "counts_after": counts(store), "sync": json.loads(sync.stdout)}
                        rows.append(row)
                        with (out / "observations.jsonl").open("a") as stream:
                            stream.write(json.dumps(row) + "\n")
                        assert process.returncode == 0, process.stderr
                        assert row["counts_after"]["source_trails"] == row["counts_after"]["policy_decisions"] == 1
                        packet = json.loads(process.stdout)
                        row["assessment"] = assess(packet, case, manifest, documents, docs.verify_evidence, protocol["budget_bytes"])
                    print(f"{identity['mode']}: repeat {repeat + 1}, case {case['id']} complete", flush=True)
        (out / "analysis.json").write_text(json.dumps({"execution": "PASS", "rows": [
            {key: row[key] for key in ("repeat", "case", "arm", "wall_ms", "assessment")} for row in rows]}, indent=2) + "\n")
    except Exception as error:
        (out / "failure.json").write_text(json.dumps({"execution": "FAIL", "error": str(error)}) + "\n")
        raise


if __name__ == "__main__":
    main()
