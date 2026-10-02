#!/usr/bin/env python3
"""Run and score one fixed native-MCP project-history development protocol."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def validate(protocol, history):
    documents = {d["id"]: d["text"] for d in history["documents"]}
    corrected = dict(documents)
    for change in history["changes"]:
        if "text" in change:
            corrected[change["id"]] = change["text"]
        else:
            del corrected[change["id"]]
    if len(protocol["cases"]) != 20 or len({c["id"] for c in protocol["cases"]}) != 20:
        raise ValueError("protocol requires 20 distinct cases")
    counts = {category: sum(c["category"] == category for c in protocol["cases"])
              for category in ("recall", "decision", "multi", "lifecycle", "negative")}
    if counts != {"recall": 6, "decision": 4, "multi": 4, "lifecycle": 3, "negative": 3}:
        raise ValueError("case distribution mismatch")
    for case in protocol["cases"]:
        if any(item in case["question"] for item in documents):
            raise ValueError("question leaks a synthetic identifier")
        for phase in (case, case.get("after", {})):
            for field in ("required", "forbidden"):
                for span in phase.get(field, []):
                    revisions = [documents.get(span["item"]), corrected.get(span["item"])]
                    matching = [t for t in revisions if t is not None and
                                hashlib.sha256(t.encode()).hexdigest() == span["representation_sha256"]]
                    if not matching or matching[0].encode()[span["byte_start"]:span["byte_end"]] != span["text"].encode():
                        raise ValueError("required span does not match a source revision")
                    if hashlib.sha256(span["text"].encode()).hexdigest() != span["sha256"]:
                        raise ValueError("span digest mismatch")
    return documents, corrected


def contains(hit, span):
    return (hit["item"] == span["item"] and hit["representation_sha256"] == span["representation_sha256"]
            and hit["byte_start"] <= span["byte_start"] < span["byte_end"] <= hit["byte_end"]
            and hit["text"].encode()[span["byte_start"]-hit["byte_start"]:span["byte_end"]-hit["byte_start"]] == span["text"].encode())


def score(case, observation, trail, protocol, documents, phase):
    expected = case["after"] if phase == "after" and "after" in case else case
    result = observation["result"]
    hits = result["evidence"]
    requirements = expected["required"]
    covered = [any(contains(hit, span) for hit in hits) for span in requirements]
    candidates = trail["result"]["historical"]["candidates"]
    omissions = []
    for span, found in zip(requirements, covered):
        if found:
            continue
        # Only whole paragraph suffixes actually present in the normalized revision qualify.
        text = documents[span["item"]].encode()
        start, end = span["byte_start"], span["byte_end"]
        digests = {hashlib.sha256(text[start:end]).hexdigest()}
        while end < len(text) and text[end:end+1] in (b"\n", b"\r", b" ", b"\t"):
            end += 1
            digests.add(hashlib.sha256(text[start:end]).hexdigest())
        matched = [c for c in candidates if c["content_sha256"] in digests]
        cause = "not_in_released_candidate_metadata"
        if matched and not any(c["selected"] for c in matched):
            cause = "candidate_found_but_not_packed_within_frozen_budget"
        omissions.append({"span": span, "cause": cause, "candidate_metadata": matched})
    irrelevant = [hit for hit in hits if not any(contains(hit, span) for span in requirements)]
    forbidden = [hit for hit in hits if any(contains(hit, span) for span in expected["forbidden"])]
    relationship = case.get("relationship_span")
    if result["used_bytes"] != sum(len(hit["text"].encode()) for hit in hits) or result["used_bytes"] > protocol["budget_bytes"]:
        raise ValueError("released byte accounting mismatch")
    selected = [(c["segment_id"], c["content_sha256"], c["text_bytes"]) for c in candidates if c["selected"]]
    released = [(h["segment_id"], h["content_sha256"], h["byte_length"]) for h in hits]
    if selected != released or trail["result"]["historical"]["packet_id"] != result["packet_id"]:
        raise ValueError("trail selection does not match packet")
    return {"case": case["id"], "phase": phase, "category": case["category"], "question": case["question"],
            "required_passages": len(requirements), "covered_passages": sum(covered), "coverage": covered,
            "all_required_released": bool(requirements) and all(covered), "omitted": omissions,
            "forbidden_released": forbidden, "irrelevant": irrelevant,
            "misleading_near_matches": [h for h in irrelevant if h["item"] in protocol["near_matches"]],
            "relationship_supported": any(contains(h, relationship) for h in hits) if relationship else None,
            "source": result["source"], "packet_id": result["packet_id"], "trail_id": result["trail_id"],
            "evidence": hits, "provenance": "PASS", "outcome": result["outcome"],
            "released_bytes": result["used_bytes"], "context_bytes": observation["rendered"]["context_bytes"],
            "context_sha256": observation["rendered"]["context_sha256"], "tokens": "NOT RUN: no verified tokenizer installed",
            "caller_seconds": observation["caller_seconds"], "whole_process_seconds": observation["whole_process_seconds"],
            "operation_seconds": observation["operation_seconds"], "server_operation_seconds": result["latency_micros"] / 1e6,
            "initialize_seconds": observation["initialize_seconds"], "matched_candidates": result["matched_candidates"],
            "budget_omitted": result["budget_omitted"], "expression": result["expression"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--mousa", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_bytes())
    history = json.loads(args.history.read_bytes())
    documents, corrected = validate(protocol, history)
    args.output.mkdir(mode=0o700, exist_ok=False)
    store = args.output / "memory.sqlite"
    observations = {}
    command_rows = []
    def invoke(label, command):
        argv = [sys.executable, str(args.consumer), "--mousa", str(args.mousa), "--store", str(store),
                "--history", str(args.history), "--receipts", str(args.output / (label + "-receipts.jsonl")), *command]
        started = time.monotonic()
        completed = subprocess.run(argv, capture_output=True, timeout=120)
        elapsed = time.monotonic() - started
        (args.output / (label + "-stdout.json")).write_bytes(completed.stdout)
        (args.output / (label + "-stderr.txt")).write_bytes(completed.stderr)
        command_rows.append({"label": label, "argv": argv, "exit_code": completed.returncode,
                             "whole_process_seconds": elapsed})
        (args.output / "commands.json").write_text(json.dumps(command_rows, indent=2) + "\n")
        if completed.returncode:
            raise RuntimeError(f"{label} exited {completed.returncode}")
        result = json.loads(completed.stdout)
        if result["status"] != "PASS" or result["process"]["forced"]:
            raise ValueError("consumer failed")
        result["whole_process_seconds"] = elapsed
        observations[label] = result
        return result
    invoke("ingest", ["ingest"])
    scores = []
    for case in protocol["cases"]:
        label = "before-" + case["id"]
        result = invoke(label, ["ask", case["question"], "--budget-bytes", str(protocol["budget_bytes"])])
        trail = invoke(label + "-trail", ["inspect", result["result"]["trail_id"]])
        scores.append(score(case, result, trail, protocol, documents, "before"))
    invoke("change", ["change"])
    for case in protocol["cases"]:
        if "after" not in case and case["id"] not in protocol["controls"]:
            continue
        label = "after-" + case["id"]
        result = invoke(label, ["ask", case["question"], "--budget-bytes", str(protocol["budget_bytes"])])
        trail = invoke(label + "-trail", ["inspect", result["result"]["trail_id"]])
        scores.append(score(case, result, trail, protocol, corrected, "after"))
    historical = []
    for case in protocol["cases"]:
        if "after" not in case:
            continue
        old = observations["before-" + case["id"]]["result"]
        trail = invoke("historical-" + case["id"], ["inspect", old["trail_id"]])["result"]
        selected = [(c["segment_id"], c["content_sha256"], c["text_bytes"]) for c in trail["historical"]["candidates"] if c["selected"]]
        released = [(h["segment_id"], h["content_sha256"], h["byte_length"]) for h in old["evidence"]]
        if selected != released or trail["historical"]["packet_id"] != old["packet_id"]:
            raise ValueError("lifecycle changed original historical selection")
        historical.append({"case": case["id"], "packet_unchanged": True, "selection_unchanged": True,
                           "authorization_outcome": trail["authorization_outcome"], "candidates": trail["historical"]["candidates"]})
    stale = [h for score_row in scores if score_row["phase"] == "after" for h in score_row["evidence"]
             if h["item"] == "entry-20" or (h["item"] == "entry-19" and
                h["representation_sha256"] != history["changes"][0]["sha256"])]
    summary = {"execution": "PASS", "agent_acceptance": "NOT RUN", "cases": scores,
               "historical": historical, "stale_or_deleted_current_evidence": stale,
               "observations": observations, "protocol_sha256": hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
               "history_sha256": hashlib.sha256(args.history.read_bytes()).hexdigest(),
               "binary_sha256": hashlib.sha256(args.mousa.read_bytes()).hexdigest(),
               "store_sha256": hashlib.sha256(store.read_bytes()).hexdigest()}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("execution", "agent_acceptance", "protocol_sha256", "history_sha256", "binary_sha256")}), flush=True)


if __name__ == "__main__":
    main()
