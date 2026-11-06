"""Execute or replay the additive, frozen EnterpriseRAG lexical pilot v2."""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import signal
import sqlite3
import subprocess
import tempfile
import threading
import time
import zipfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("enterprise_v1", ROOT.parent / "enterprise-retrieval-pilot/prepare.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
spec = importlib.util.spec_from_file_location("enterprise_metrics", ROOT.parent / "enterprise-retrieval-pilot/sanity.py")
metrics_module = importlib.util.module_from_spec(spec)
# The immutable v1 metric helper imports its sibling prepare module.
import sys
sys.modules["prepare"] = prepare
spec.loader.exec_module(metrics_module)
check, encoded, parsed = prepare.check, prepare.encoded, prepare.parsed


def identity(path):
    return prepare.manifest(path.read_bytes())


def protocol_at(path):
    protocol = parsed(path.read_bytes())
    for name, digest in protocol["helper_sha256"].items():
        check(identity(ROOT.parent / name)["sha256"] == digest, "helper-identity")
    check(identity(ROOT / "run.py")["sha256"] == protocol["controller_sha256"], "controller-identity")
    return protocol


def input_identity(stable):
    return {key: stable[key] for key in ("eligibility", "enrolled", "corpus", "source_documents",
            "gold_physical_documents", "compressed_bytes", "decompressed_bytes", "normalized_text_bytes",
            "selected_documents", "selected_questions")}


def materialize(protocol, cache, directory):
    observed = prepare.prepare(protocol, cache)
    stable = observed["stable"]
    check(stable["status"] == "prepared" and stable["executable_questions"] == 20, "input-not-executable")
    check(prepare.manifest(encoded(input_identity(stable))) == protocol["input_identity"], "frozen-input-identity")
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "qrels").mkdir()
    corpus = []
    for pin in protocol["assets"]:
        if pin["name"].endswith(".zip"):
            with zipfile.ZipFile(cache / pin["name"]) as archive:
                for document in stable["corpus"]:
                    if document["physical_identity"].startswith(pin["name"] + ":"):
                        body = prepare.render(archive.read(document["member"]))
                        check(prepare.manifest(body) == document["rendered"], "rendered-document-identity")
                        corpus.append({"_id": document["item_id"], "title": "", "text": body.decode()})
    by_id = {row["_id"]: row for row in corpus}
    corpus = [by_id[row["item_id"]] for row in stable["corpus"]]
    questions = [{"_id": row["question"]["question_id"], "text": row["question"]["question"]}
                 for row in stable["enrolled"]]
    compact = lambda row: json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"
    (directory / "corpus.jsonl").write_bytes(b"".join(map(compact, corpus)))
    (directory / "queries.jsonl").write_bytes(b"".join(map(compact, questions)))
    gold = {row["question_id"]: {item for items in row["mapping"].values() for item in items}
            for row in stable["outcomes"]}
    (directory / "qrels/test.tsv").write_text("query-id\tcorpus-id\tscore\n" + "".join(
        f"{q['_id']}\t{item}\t1\n" for q in questions for item in sorted(gold[q["_id"]])))
    return observed, corpus, questions, gold


def data_manifest(directory):
    return {name: identity(directory / name) for name in ("corpus.jsonl", "queries.jsonl", "qrels/test.tsv")}


class Commands:
    def __init__(self, work, deadline):
        self.work, self.deadline, self.rows = work, deadline, []

    def run(self, argv, endpoint):
        remaining = self.deadline - time.monotonic()
        check(remaining > 0, "experiment-wall-cap")
        started = time.monotonic()
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = subprocess.Popen(argv, cwd=self.work, stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, start_new_session=True)
            expired = threading.Event()
            def kill():
                expired.set()
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            timer = threading.Timer(remaining, kill)
            timer.start()
            try:
                _, status, usage = os.wait4(process.pid, 0)
                process.returncode = os.waitstatus_to_exitcode(status)
            finally:
                timer.cancel()
            stdout.seek(0)
            stderr.seek(0)
            row = {"argv": argv, "endpoint": endpoint, "exit": process.returncode,
                   "wall_seconds": time.monotonic() - started, "user_seconds": usage.ru_utime,
                   "system_seconds": usage.ru_stime, "peak_rss_kib": usage.ru_maxrss,
                   "experiment_timeout": expired.is_set(), "stdin": "DEVNULL",
                   "stdout": prepare.wire.stream(stdout.read()), "stderr": prepare.wire.stream(stderr.read())}
        self.rows.append(row)
        (self.work / "commands.json").write_bytes(encoded(self.rows))
        return row


def outcome(arm, question, ranking, gold, selected=None, used=None, scores=None):
    ranking = ranking or []
    check(len(ranking) == len(set(ranking)), "duplicate-ranked-document")
    return {"arm": arm, "question_id": question, "status": "SCORED", "attempts": 1,
            "ranking": ranking, "scores": scores,
            "score_endpoint": "native SQLite BM25" if scores is not None else "not exposed by cmd/beir journal",
            "metrics": metrics_module.metrics(ranking, gold), "selected": selected,
            "used_bytes": used, "packed_coverage": None if selected is None else len(set(selected) & gold) / len(gold)}


def one_pass(label, protocol, cache, work, binary, deadline):
    directory = work / label
    directory.mkdir()
    prep, corpus, questions, gold = materialize(protocol, cache, directory / "data")
    expected_data = data_manifest(directory / "data")
    commands = Commands(directory, deadline)
    results, native = [], {}
    def checkpoint():
        observed = {(row["arm"],row["question_id"]):row for row in results}
        ledger = [observed.get((arm,qid), {"arm":arm,"question_id":qid,"status":"NOT_RUN",
                  "reason":"execution not reached","attempts":0,"metrics":None,"packed_coverage":None})
                  for arm in prepare.ARMS for qid in protocol["question_ids"]]
        (directory / "progress.json").write_bytes(encoded({"preparation":prep,"outcomes":ledger}))
    checkpoint()
    first_manifest = None
    all_ids = {row["_id"] for row in corpus}
    for policy in ("original", "dedup"):
        for mode, budget in (("verified", 1024), ("traced", 1024), ("traced", 4096)):
            check(data_manifest(directory / "data") == expected_data, "reuse-data-identity")
            if first_manifest is not None:
                check(identity(directory / "original-verified-1024.json.manifest.json") == first_manifest,
                      "reuse-index-manifest")
            name = f"{policy}-{mode}-{budget}.json"
            arm = f"mousa-{policy}-" + (mode if mode == "verified" else f"traced-{budget}")
            argv = [os.path.relpath(binary, directory), "-data", "data", "-dataset", "enterprise-v2",
                    "-out", name, "-mode", mode, "-policy", policy, "-limit", "100",
                    "-budget", str(budget), "-query-timeout", "30s"]
            if first_manifest is not None:
                argv.append("-reuse")
            attempt = commands.run(argv, "warm Go harness; process includes open/index/query/report/close")
            journal = directory / (name + ".jsonl")
            rows = [parsed(line) for line in journal.read_bytes().splitlines()] if journal.exists() else []
            report_path = directory / name
            if attempt["exit"] == 0:
                check([row["QueryID"] for row in rows] == protocol["question_ids"], "enrollment-identity")
                report = parsed(report_path.read_bytes())
                check([row["query_id"] for row in report["queries"]] == protocol["question_ids"], "native-query-population")
                native[name] = {"report": report, "journal": rows,
                                "manifest": parsed((directory / (name + ".manifest.json")).read_bytes())}
                if first_manifest is None:
                    first_manifest = identity(directory / (name + ".manifest.json"))
                arm_rows = []
                for row, reported in zip(rows, report["queries"]):
                    check(set(row["RankedDocIDs"] or []) <= all_ids, "ranking-document-identity")
                    selected = (row["SelectedDocIDs"] or []) if mode == "traced" else None
                    scored = outcome(arm, row["QueryID"], row["RankedDocIDs"], gold[row["QueryID"]],
                                     selected, row["UsedBytes"] if selected is not None else None)
                    if selected is not None:
                        check(set(selected) <= all_ids, "packed-document-identity")
                        cov = reported["pack_coverage"]
                        check(cov["gold_coverage"] == scored["packed_coverage"] and cov["selected_docs"] == len(selected)
                              and cov["used_bytes"] == row["UsedBytes"], "native-query-coverage")
                    arm_rows.append(scored)
                for key in ("recall_at_100", "binary_ndcg_at_10", "mrr_at_10"):
                    check(math.isclose(sum(row["metrics"][key] for row in arm_rows) / 20, report["aggregate"][key], abs_tol=1e-12), "native-metric-" + key)
                if mode == "traced":
                    cov = report["aggregate"]["pack_coverage"]
                    used = sum(row["used_bytes"] for row in arm_rows) // 20
                    check(cov["queries"] == 20 and math.isclose(cov["gold_coverage"],sum(row["packed_coverage"] for row in arm_rows)/20)
                          and cov["selected_docs"] == sum(len(row["selected"]) for row in arm_rows)//20
                          and cov["used_bytes"] == used and cov["utilisation"] == used/budget, "native-aggregate-coverage")
                results.extend(arm_rows)
            else:
                # A completed journal prefix is retained as evidence, not promoted to a successful arm.
                native[name] = {"partial_journal": rows, "exit": attempt["exit"]}
                results.extend({"arm": arm, "question_id": q, "status": "TIMEOUT" if attempt["experiment_timeout"] else "RUN_FAILED",
                                "attempts": 1, "metrics": None, "packed_coverage": None} for q in protocol["question_ids"])
            checkpoint()
    for policy in ("original", "dedup"):
        for report_mode, axis, pair in (
            ("compare", "mode", f"{policy}-verified-1024.json,{policy}-traced-1024.json"),
            ("compare", "budget", f"{policy}-traced-1024.json,{policy}-traced-4096.json"),
            ("coverage", None, f"{policy}-traced-1024.json,{policy}-traced-4096.json")):
            name = f"{policy}-{axis or 'coverage'}.json"
            argv = [os.path.relpath(binary,directory), "-report", report_mode, "-reports", pair, "-out", name]
            if axis:
                argv += ["-axis",axis]
            attempt = commands.run(argv, "native report validation; no retrieval")
            check(attempt["exit"] == 0, "native-report-refusal")
            report = parsed((directory / name).read_bytes())
            if report_mode == "compare":
                check(report["rankings_identical"], "native-ranking-identity")
            else:
                check([point["gold_coverage"] for point in report["points"]] == [native[f"{policy}-traced-{b}.json"]["report"]["aggregate"]["pack_coverage"]["gold_coverage"] for b in (1024,4096)], "native-curve-binding")
            native[name] = report
    attempt = commands.run([os.path.relpath(binary,directory),"-report","compare","-axis","policy","-reports",
                            "original-verified-1024.json,dedup-verified-1024.json","-out","policy.json"], "native policy comparison; no retrieval")
    check(attempt["exit"] == 0, "native-policy-refusal")
    native["policy.json"] = parsed((directory / "policy.json").read_bytes())
    check(data_manifest(directory / "data") == expected_data, "sqlite-data-identity")
    sqlite_start = time.monotonic()
    before = resource.getrusage(resource.RUSAGE_SELF)
    connection = sqlite3.connect(directory / "reference.sqlite")
    connection.execute("CREATE VIRTUAL TABLE search USING fts5(item_id UNINDEXED,body, tokenize='unicode61 remove_diacritics 2')")
    connection.executemany("INSERT INTO search VALUES(?,?)", ((row["_id"],row["text"]) for row in corpus))
    connection.commit()
    sqlite_ingest = time.monotonic() - sqlite_start
    sqlite_queries = []
    for question in questions:
        check(time.monotonic() < deadline, "experiment-wall-cap")
        expression = " OR ".join('"' + term + '"' for term in re.findall(r"[A-Za-z0-9]+", question["text"].lower()))
        query_deadline = min(deadline,time.monotonic()+30)
        connection.set_progress_handler(lambda: int(time.monotonic() > query_deadline),100)
        started = time.monotonic()
        rows = connection.execute("SELECT item_id,bm25(search) FROM search WHERE search MATCH ? ORDER BY bm25(search),item_id LIMIT 100",(expression,)).fetchall()
        sqlite_queries.append({"question_id":question["_id"],"expression":expression,"rows":rows,"wall_seconds":time.monotonic()-started})
        results.append(outcome("sqlite-fts5",question["_id"],[row[0] for row in rows],gold[question["_id"]],scores=[row[1] for row in rows]))
        checkpoint()
    connection.close()
    after = resource.getrusage(resource.RUSAGE_SELF)
    sqlite_resource = {"endpoint":"in-process stdlib SQLite FTS5; query only, no process startup", "version":sqlite3.sqlite_version,
                       "ingestion_seconds":sqlite_ingest,"total_seconds":time.monotonic()-sqlite_start,
                       "user_seconds":after.ru_utime-before.ru_utime,"system_seconds":after.ru_stime-before.ru_stime,
                       "process_peak_rss_kib":after.ru_maxrss}
    results.extend({"arm":"qmd-search","question_id":qid,"status":"NOT_RUN","attempts":0,
                    "reason":protocol["qmd_status"],"metrics":None,"packed_coverage":None} for qid in protocol["question_ids"])
    checkpoint()
    check(len(results)==160, "terminal-arm-population")
    stores = {p.name:p.stat().st_size for p in directory.glob("*.sqlite*")}
    return {"preparation":prep,"data_manifest":expected_data,"native":native,"sqlite_queries":sqlite_queries,
            "sqlite_resources":sqlite_resource,"commands":commands.rows,"outcomes":results,"store_bytes":stores}


def compare(left,right):
    check([r["question_id"] for r in left["outcomes"]] == [r["question_id"] for r in right["outcomes"]], "enrollment-identity")
    check(prepare.wire.same_json([r["mapping"] for r in left["preparation"]["stable"]["outcomes"]],
                                 [r["mapping"] for r in right["preparation"]["stable"]["outcomes"]]), "logical-physical-mapping")
    check([(r.get("ranking"),r.get("scores")) for r in left["outcomes"]] == [(r.get("ranking"),r.get("scores")) for r in right["outcomes"]], "ranking-binding")
    check([(r.get("selected"),r.get("used_bytes")) for r in left["outcomes"]] == [(r.get("selected"),r.get("used_bytes")) for r in right["outcomes"]], "packed-binding")
    check(prepare.wire.same_json(left["outcomes"],right["outcomes"]), "outcome-reproduction")
    check(left["data_manifest"] == right["data_manifest"], "dataset-reproduction")
    prepare.verify(left["preparation"],right["preparation"])
    for name in left["native"]:
        if "journal" in left["native"][name]:
            strip = lambda rows: [{k:v for k,v in row.items() if k not in ("LatencyMicros","SearchMicros","PreprocessMicros")} for row in rows]
            check(prepare.wire.same_json(strip(left["native"][name]["journal"]),strip(right["native"][name]["journal"])), "native-stable-reproduction")


def controls(capture):
    original = prepare.wire.load_capture(capture)
    receipts = []
    for name,detector in (("wrong-question-same-count","enrollment-identity"),("wrong-physical-mapping","logical-physical-mapping"),
                          ("changed-ranking","ranking-binding"),("changed-packed-membership","packed-binding")):
        changed = copy.deepcopy(original["first"])
        if detector == "enrollment-identity":
            changed["outcomes"][0]["question_id"] = "wrong-question"
        elif detector == "logical-physical-mapping":
            mapping = changed["preparation"]["stable"]["outcomes"][0]["mapping"]
            mapping[next(iter(mapping))] = ["wrong-physical-item"]
        elif detector == "ranking-binding":
            changed["outcomes"][0]["ranking"] = ["wrong-ranked-item"] + changed["outcomes"][0]["ranking"][1:]
        else:
            row = next(row for row in changed["outcomes"] if row.get("selected") is not None)
            row["selected"] = ["wrong-packed-item"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "control.json.gz"
            prepare.wire.write_capture(path, changed)
            loaded = prepare.wire.load_capture(path)
            try:
                compare(loaded, original["first"])
            except ValueError as error:
                check(str(error)==detector,"wrong-control-detector")
                receipts.append({"control":name,"detector":detector,"rehashed_archive":identity(path),"archive_integrity_passed":True})
            else:
                raise ValueError("control-not-rejected")
    return receipts


def summarize(rows):
    summaries = {}
    for arm in prepare.ARMS:
        enrolled = [row for row in rows if row["arm"]==arm]
        scored = [row for row in enrolled if row["status"]=="SCORED"]
        summaries[arm] = {"enrolled":len(enrolled),"executed":sum(row["attempts"]>0 for row in enrolled),"scored":len(scored),
                          "metrics":{key:sum(row["metrics"][key] for row in scored)/len(scored) for key in scored[0]["metrics"]} if scored else None,
                          "packed_coverage":sum(row["packed_coverage"] for row in scored)/len(scored) if scored and scored[0]["packed_coverage"] is not None else None}
    return summaries


def validate_scores(captured, protocol):
    for label in ("first","reproduction"):
        run = captured[label]
        gold = {row["question_id"]: {item for values in row["mapping"].values() for item in values}
                for row in run["preparation"]["stable"]["outcomes"]}
        expected = [(arm,qid) for arm in prepare.ARMS for qid in protocol["question_ids"]]
        check([(row["arm"],row["question_id"]) for row in run["outcomes"]] == expected, "terminal-arm-population")
        for row in run["outcomes"]:
            if row["status"] != "SCORED":
                check(row["metrics"] is None and row["packed_coverage"] is None, "failure-not-zero")
                continue
            check(prepare.wire.same_json(row["metrics"],metrics_module.metrics(row["ranking"],gold[row["question_id"]])), "independent-metric-binding")
            if row["selected"] is not None:
                check(row["packed_coverage"] == len(set(row["selected"]) & gold[row["question_id"]])/len(gold[row["question_id"]]), "independent-packed-binding")
            if row["arm"].startswith("mousa-"):
                _,policy,mode,*budget = row["arm"].split("-")
                name = f"{policy}-{mode}-{budget[0] if budget else '1024'}.json"
                raw = next(q for q in run["native"][name]["journal"] if q["QueryID"]==row["question_id"])
                check((raw["RankedDocIDs"] or []) == row["ranking"], "native-ranking-binding")
                if mode == "traced":
                    check((raw["SelectedDocIDs"] or []) == row["selected"] and raw["UsedBytes"]==row["used_bytes"], "native-packed-binding")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("execute","replay","controls"))
    parser.add_argument("--protocol",type=Path,default=ROOT/"protocol.json")
    parser.add_argument("--cache",type=Path)
    parser.add_argument("--beir",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--capture",type=Path)
    args = parser.parse_args()
    protocol = protocol_at(args.protocol)
    if args.mode == "controls":
        args.out.write_bytes(encoded(controls(args.capture)))
        return
    if args.mode == "replay":
        captured = prepare.wire.load_capture(args.capture)
        check(prepare.wire.same_json(captured["protocol"],protocol), "protocol-binding")
        with tempfile.TemporaryDirectory() as directory:
            observed, _, _, _ = materialize(protocol,args.cache,Path(directory)/"data")
            check(data_manifest(Path(directory)/"data")==captured["first"]["data_manifest"],"dataset-reproduction")
        prepare.verify(captured["first"]["preparation"],observed)
        validate_scores(captured,protocol)
        compare(captured["first"],captured["reproduction"])
        check(summarize(captured["first"]["outcomes"])==captured["summary"],"summary-binding")
        args.out.write_bytes(encoded({"status":"PASS","scope":"source-bound preparation, deterministic fresh stores and per-question summary replay; no retrieval"}))
        return
    work = args.out.resolve()
    work.mkdir(parents=True,exist_ok=False)
    binary = args.beir.resolve()
    check(identity(binary)==protocol["binary_identity"],"binary-identity")
    started = time.monotonic()
    receipt = {"schema":"mousa.enterprise_pilot_v2.capture","protocol":protocol,"protocol_identity":identity(args.protocol),
               "environment":{"python":sys.version,"sqlite":sqlite3.sqlite_version,"platform":platform.platform(),"cpu_count":os.cpu_count()},
               "paid_api_calls":0,"model_calls":0,"billing_usd":0,"started_unix":time.time()}
    try:
        receipt["first"] = one_pass("first",protocol,args.cache,work,binary,started+1800)
        receipt["reproduction"] = one_pass("reproduction",protocol,args.cache,work,binary,started+1800)
        compare(receipt["first"],receipt["reproduction"])
        validate_scores(receipt,protocol)
        receipt["summary"] = summarize(receipt["first"]["outcomes"])
        receipt["status"] = "COMPLETE_REQUIRED_ARMS_OPTIONAL_NOT_RUN"
    except Exception as error:
        receipt["status"] = "INCOMPLETE"
        receipt["failure"] = str(error)
        for label in ("first","reproduction"):
            progress = work / label / "progress.json"
            if label not in receipt and progress.exists():
                receipt[label] = parsed(progress.read_bytes())
        raise
    finally:
        receipt["measured_wall_seconds"] = time.monotonic()-started
        prepare.wire.write_capture(work/"capture.json.gz",receipt)
        (work/"status.json").write_bytes(encoded({k:v for k,v in receipt.items() if k not in ("first","reproduction","protocol")}))
    print(json.dumps(receipt["summary"],indent=2))


if __name__ == "__main__":
    main()
