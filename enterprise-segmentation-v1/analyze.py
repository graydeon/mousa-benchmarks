"""Replay source-bound metrics and populations without running retrieval."""
import argparse
import base64
from collections import Counter
import copy
import hashlib
import json
import math
import re
from pathlib import Path
import tempfile

from run import artifact_fields, arm_boundary, base, check, encoded, enroll, ledger, load_contract, materialize, pilot, scored, tuple_hash, validate_segments


def configuration(policy, budget, manifests, count):
    check(policy in ("fixed-v1", "passage-v1"), "segmentation-policy-binding")
    parameters = b"" if policy == "fixed-v1" else b'{"segmentation":"passage-v1"}'
    segmentation = {"policy": policy, "processor_id": "mousa.text.normalize_utf8",
                    "processor_version": "1", "parameters_sha256": hashlib.sha256(parameters).hexdigest()}
    content = {field: manifests[name]["sha256"] for field, name in
               (("corpus_sha256", "corpus.jsonl"), ("queries_sha256", "queries.jsonl"), ("qrels_sha256", "qrels/test.tsv"))}
    identity = "{" + " ".join(segmentation.values()) + "}"
    fields = ["mousa-beir-run", identity, "enterprise-segmentation-v1", "traced", "100",
              str(budget), "original", "500", str(count), "0", *content.values()]
    namespace = "run-" + hashlib.sha256("\0".join(fields).encode()).hexdigest()[:12]
    return {"dataset": "enterprise-segmentation-v1", "mode": "traced", "expression_policy": "original",
            "limit": 100, "budget_bytes": budget, "corpus_documents": 500, "judged_queries": count,
            "segmentation": segmentation, "content": content, "request_namespace": namespace}


def validate_stream(value):
    check(type(value) is dict and set(value) == {"bytes", "sha256", "base64", "text"}, "stream-schema")
    check(type(value["bytes"]) is int and value["bytes"] >= 0
          and all(type(value[key]) is str for key in ("sha256", "base64", "text")), "stream-schema")
    base.wire.streams_valid(value)
    return base64.b64decode(value["base64"], validate=True)


def nonnegative(value):
    return type(value) in (int, float) and value >= 0 and (type(value) is int or math.isfinite(value))


def validate_provenance(capture):
    publication = capture.get("publication")
    check(type(publication) is dict, "publication-required")
    check(all(type(publication.get(field)) is str and re.fullmatch(r"[0-9a-fA-F]{40}", publication[field])
              for field in ("public_head", "public_tree")), "public-source-identity")
    binary = publication.get("binary_identity")
    check(type(binary) is dict and set(binary) == {"sha256", "bytes"}
          and type(binary["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", binary["sha256"])
          and type(binary["bytes"]) is int and binary["bytes"] > 0, "published-binary-identity")
    check(nonnegative(capture["collection_wall_seconds"]), "collection-wall-metric")
    for attempt in capture["attempts"]:
        check(nonnegative(attempt["wall_seconds"]), "attempt-wall-metric")
        for field in ("user_seconds", "system_seconds", "peak_rss_kib"):
            check(field in attempt and (attempt[field] is None or nonnegative(attempt[field])), "attempt-resource-metric")
        check(type(attempt["exit"]) is int and type(attempt["experiment_timeout"]) is bool, "attempt-status-schema")
        check(type(attempt["argv"]) is list and all(type(arg) is str for arg in attempt["argv"]), "argv-schema")
        validate_stream(attempt["stdout"])
        validate_stream(attempt["stderr"])


def analyze(capture, enrollment, manifests, data_directory):
    protocol, frozen = load_contract()
    validate_provenance(capture)
    check(capture["protocol"] == protocol and capture["enrollment"] == frozen == enrollment, "enrollment-binding")
    expected = ledger(enrollment)
    keys = ("pass", "policy", "budget", "population", "question_id")
    check([tuple(r[k] for k in keys) for r in capture["outcomes"]] == [tuple(r[k] for k in keys) for r in expected], "terminal-population")
    gold = {q["question"]["question_id"]: set(q["gold"]) for q in enrollment["questions"]}
    check(capture["schema"] == "mousa.enterprise_segmentation.capture.v1", "capture-schema")
    check(capture["model_calls"] == capture["network_calls"] == 0, "collection-scope")
    complete = (all(r["status"] == "SCORED" for r in capture["outcomes"])
                and all(arm["boundary"]["status"] == "COMPLETE" and "failure" not in arm
                        for arm in capture["arms"].values()))
    check(capture["status"] == ("COMPLETE" if complete else "INCOMPLETE"), "capture-status")
    arm_keys = list(dict.fromkeys(f'{r["pass"]}/{r["policy"]}/{r["budget"]}' for r in expected))
    check(set(capture["arms"]) <= set(arm_keys), "arm-population")
    attempted = [key for key in arm_keys if key in capture["arms"]]
    check([capture["arms"][key]["attempt"] for key in attempted] == list(range(len(capture["attempts"]))), "attempt-population")
    for key in attempted:
        arm = capture["arms"][key]
        check("failure" not in arm, "unverifiable-arm-failure")
        label, policy, budget_text = key.split("/")
        budget = int(budget_text)
        attempt = capture["attempts"][arm["attempt"]]
        check(arm["data_manifest"] == manifests, "data-binding")
        config = configuration(policy, budget, manifests, len(gold))
        argv = ["-data", "data", "-dataset", config["dataset"], "-out", f"{budget}.json",
                "-mode", "traced", "-policy", "original", "-segment-policy", policy,
                "-limit", "100", "-budget", str(budget), "-query-timeout", "30s"]
        if budget == 4096:
            earlier = f"{label}/{policy}/1024"
            check(earlier in capture["arms"] and capture["arms"][earlier]["boundary"]["status"] == "COMPLETE"
                  and "failure" not in capture["arms"][earlier]
                  and all(r["status"] == "SCORED" for r in capture["outcomes"]
                          if (r["pass"], r["policy"], r["budget"]) == (label, policy, 1024)), "reuse-attempt-binding")
            argv.append("-reuse")
        check(len(attempt["argv"]) > 1 and attempt["argv"][1:] == argv, "argv-binding")
        for field in ("report", "manifest"):
            if field not in arm:
                continue
            native = arm[field]
            check(native["content"] == config["content"], "native-content-binding")
            check(native["segmentation"] == config["segmentation"], "segmentation-policy-binding")
            check(native["request_namespace"] == config["request_namespace"], "request-namespace-binding")
            check(all(native[name] == value for name, value in config.items()), "native-configuration-binding")
        if "manifest" in arm:
            check(arm["manifest"]["query_timeout"] == 30_000_000_000, "native-timeout-binding")
        if "report" in arm:
            check(arm["report"]["query_limit"] == 0, "native-population")
            check([q["query_id"] for q in arm["report"]["queries"]] == list(gold), "native-population")
        rows = [r for r in capture["outcomes"] if f'{r["pass"]}/{r["policy"]}/{r["budget"]}' == key]
        prefix = [entry["QueryID"] for entry in arm["journal"]]
        check(prefix == list(gold)[:len(prefix)], "native-journal-prefix")
        raw = {field: validate_stream(arm[field + "_raw"]) if field + "_raw" in arm else None
               for field in ("journal", "report", "manifest")}
        artifacts = artifact_fields(raw["journal"], raw["report"], raw["manifest"])
        artifact_keys = {"journal_present", "journal", "artifact_errors", "journal_raw", "journal_tail",
                         "report_raw", "report", "manifest_raw", "manifest"}
        check(base.wire.same_json({field: arm[field] for field in artifact_keys if field in arm}, artifacts),
              "native-artifact-binding")
        if "journal_tail" in arm:
            validate_stream(arm["journal_tail"])
        boundary = arm_boundary(artifacts, attempt, list(gold))
        check(arm["boundary"] == boundary, "arm-boundary-binding")
        for index, row in enumerate(rows):
            if index < len(prefix):
                status = "SCORED"
            elif row["question_id"] == boundary["failed_query_id"]:
                status = boundary["failed_query_status"]
            else:
                status = "NOT_RUN"
            check(row["status"] == status, "terminal-attempt-status")
            check(row["attempts"] == ([] if status == "NOT_RUN" else [arm["attempt"]]), "attempt-binding")
        if "store" in arm:
            validate_segments(arm["store"]["segments"], data_directory, policy)
            check(set(prefix) <= set(arm["store"]["trails"]) <= set(list(gold)[:len(prefix)+1]), "trail-population")
            for qid, trail in arm["store"]["trails"].items():
                index = list(gold).index(qid)
                check(trail["external_request_id"] == f'{config["request_namespace"]}-query-{qid}-{index}', "request-namespace-binding")
                source_id = tuple_hash([b"mousa.source.v1", b"beir-eval", b"enterprise-segmentation-v1"])
                request_id = tuple_hash([b"mousa.policy_evaluation_request.v1", b"source.retrieve",
                                         b"beir-eval.caller", b"harness", trail["external_request_id"].encode(),
                                         b"beir-eval.purpose", b"ranking", bytes.fromhex(source_id), (1).to_bytes(8, "big")])
                check(trail["request_id"] == request_id, "canonical-request-binding")
            check(arm["store"]["size_distribution"] == dict(Counter(str(s["end"]-s["start"]) for s in arm["store"]["segments"])), "segment-distribution")
    for row in capture["outcomes"]:
        check(row["status"] in ("SCORED", "NOT_RUN", "TIMEOUT", "RUN_FAILED"), "typed-status")
        check((row["status"] == "NOT_RUN") == (not row["attempts"]), "attempt-binding")
        key = f'{row["pass"]}/{row["policy"]}/{row["budget"]}'
        if key not in capture["arms"]:
            check(row["status"] == "NOT_RUN" and row["attempts"] == [], "attempt-binding")
        if row["status"] != "SCORED":
            check(row["metrics"] is None and row["packed_coverage"] is None, "failure-not-zero")
            continue
        arm = capture["arms"][f'{row["pass"]}/{row["policy"]}/{row["budget"]}']
        check(arm["data_manifest"] == manifests, "data-binding")
        check(row["attempts"] == [arm["attempt"]], "successful-attempt-binding")
        raw = next(r for r in arm["journal"] if r["QueryID"] == row["question_id"])
        observed = scored(row, raw, arm["store"]["trails"][row["question_id"]], arm["store"]["segments"], gold[row["question_id"]])
        check(row == observed, "metric-selection-binding")
        if "report" in arm:
            native = next(r for r in arm["report"]["queries"] if r["query_id"] == row["question_id"])
            check((native["ranked_doc_ids"] or []) == row["ranking"] and native["pack_coverage"]["gold_coverage"] == row["packed_coverage"] and native["pack_coverage"]["used_bytes"] == row["used_bytes"], "native-score-binding")
    summaries = []
    for label in ("first", "reproduction"):
        for population in ("original20", "heldout20"):
            for policy in ("fixed-v1", "passage-v1"):
                for budget in (1024, 4096):
                    rows = [r for r in capture["outcomes"] if (r["pass"],r["population"],r["policy"],r["budget"]) == (label,population,policy,budget)]
                    complete = [r for r in rows if r["status"] == "SCORED"]
                    summaries.append({"pass": label, "population": population, "policy": policy, "budget": budget,
                                      "enrolled": len(rows), "statuses": dict(Counter(r["status"] for r in rows)),
                                      "metrics": {k: sum(r["metrics"][k] for r in complete)/len(complete) for k in complete[0]["metrics"]} if complete else None,
                                      "packed_coverage": sum(r["packed_coverage"] for r in complete)/len(complete) if complete else None,
                                      "mean_query_micros": sum(r["query_work"]["LatencyMicros"] for r in complete)/len(complete) if complete else None})
    first = [r for r in capture["outcomes"] if r["pass"] == "first"]
    second = [r for r in capture["outcomes"] if r["pass"] == "reproduction"]
    reproduction = []
    for left, right in zip(first, second):
        comparable = left["status"] == right["status"] == "SCORED"
        reproduction.append({"policy": left["policy"], "budget": left["budget"], "question_id": left["question_id"],
                             "status": "MATCH" if comparable and all(left[k] == right[k] for k in ("ranking", "selected", "candidates", "used_bytes", "metrics", "packed_coverage")) else "MISMATCH" if comparable else "NOT_COMPARABLE"})
    return {"status": "REPLAY_VALID", "confirmation": enrollment["confirmation"], "summaries": summaries,
            "reproduction": reproduction, "collection_wall_seconds": capture["collection_wall_seconds"],
            "arm_work": {key: {"indexing_seconds": arm.get("report", {}).get("indexing_seconds"),
                                "boundary": arm["boundary"],
                                "process": capture["attempts"][arm["attempt"]]} for key,arm in capture["arms"].items()},
            "limitations": ["Question-held-out shared gold-enriched corpus, not independent company validation.",
                            "Document gold is a coarse proxy, not semantic sufficiency; unknown relevance is not negative.",
                            "No monotonicity promise. CPU/RSS are process endpoints, not attributed query totals.",
                            "Replay verifies recorded consistency, not historical execution authenticity.",
                            "Publication identities and wall/CPU/RSS measurements are unauthenticated recorded claims.",
                            "Segment partition checks do not independently authenticate the segmentation algorithm."]}


def controls(capture, enrollment, manifests, data_directory):
    analyze(capture, enrollment, manifests, data_directory)
    eligible = [index for index, row in enumerate(capture["outcomes"]) if row["status"] == "SCORED"
                and capture["arms"][f'{row["pass"]}/{row["policy"]}/{row["budget"]}']["boundary"]["status"] == "COMPLETE"
                and "report" in capture["arms"][f'{row["pass"]}/{row["policy"]}/{row["budget"]}']
                and capture["arms"][f'{row["pass"]}/{row["policy"]}/{row["budget"]}']["store"]["trails"][row["question_id"]]["candidates"]]
    check(eligible, "controls-need-complete-scored-arm")
    receipts = []
    for name in ("wrong-population", "wrong-segmentation", "altered-packed-selection"):
        changed = copy.deepcopy(capture)
        row = changed["outcomes"][eligible[0]]
        arm = changed["arms"][f'{row["pass"]}/{row["policy"]}/{row["budget"]}']
        if name == "wrong-population":
            forged = hashlib.sha256(b"different corpus with the same document count").hexdigest()
            for field in ("report", "manifest"):
                arm[field]["content"]["corpus_sha256"] = forged
            detector = "native-content-binding"
        elif name == "wrong-segmentation":
            other = "passage-v1" if row["policy"] == "fixed-v1" else "fixed-v1"
            identity = configuration(other, row["budget"], manifests, len(enrollment["questions"]))["segmentation"]
            for field in ("report", "manifest"):
                arm[field]["segmentation"] = copy.deepcopy(identity)
            detector = "segmentation-policy-binding"
        else:
            check(arm["store"]["trails"][row["question_id"]]["candidates"], "control-needs-candidates")
            candidate = arm["store"]["trails"][row["question_id"]]["candidates"][0]
            candidate["selected"] = not candidate["selected"]
            row["candidates"][0]["selected"] = candidate["selected"]
            selected = list(dict.fromkeys(c["document_id"] for c in row["candidates"] if c["selected"]))
            row["selected"] = selected
            journal = next(entry for entry in arm["journal"] if entry["QueryID"] == row["question_id"])
            journal["SelectedDocIDs"] = selected
            detector = "canonical-candidate-projection"
        for field in ("report", "manifest"):
            arm[field + "_raw"] = base.wire.stream(encoded(arm[field]))
        arm["journal_raw"] = base.wire.stream(
            b"".join((json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n").encode()
                     for entry in arm["journal"]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"control.json.gz"
            base.wire.write_capture(path, changed)
            try:
                analyze(base.wire.load_capture(path), enrollment, manifests, data_directory)
            except ValueError as error:
                check(str(error) == detector, "wrong-control-detector")
                receipts.append({"control": name, "detector": detector, "rehashed_archive": pilot.identity(path)})
            else:
                raise ValueError("control-not-rejected")
    return receipts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("replay", "controls"))
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    enrollment = enroll(args.cache)
    capture = base.wire.load_capture(args.capture)
    with tempfile.TemporaryDirectory() as directory:
        data_directory = Path(directory)/"data"
        materialize(args.cache, data_directory, enrollment)
        manifests = pilot.data_manifest(data_directory)
        result = analyze(capture, enrollment, manifests, data_directory) if args.mode == "replay" else controls(capture, enrollment, manifests, data_directory)
    with args.out.open("xb") as output:
        output.write(encoded(result))
