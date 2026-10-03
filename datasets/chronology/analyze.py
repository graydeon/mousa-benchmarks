"""Validate raw membership and mechanically account for frozen evidence labels."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


class IncompleteCapture(ValueError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def contained(root, name):
    path = PurePosixPath(name)
    if not name or path.is_absolute() or any(p in (".", "..") for p in path.parts) or str(path) != name:
        raise ValueError("unsafe member reference")
    target = root / name
    if target.is_symlink() or not target.is_file() or any(p.is_symlink() for p in target.parents if p != root.parent):
        raise ValueError("member must be a contained regular file")
    return target


def validate_members(root):
    manifest = json.loads((root / "members.json").read_text())
    if manifest.get("schema") != "mousa.chronology_members.v1" or not manifest.get("files"):
        raise ValueError("unsupported or empty member manifest")
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p != root / "members.json"}
    if actual != set(manifest["files"]):
        raise ValueError("raw membership mismatch")
    for name, identity in manifest["files"].items():
        data = contained(root, name).read_bytes()
        if {"bytes": len(data), "sha256": sha(data)} != identity:
            raise ValueError("raw identity mismatch: " + name)


def normalized(text):
    return text.encode().removeprefix(b"\xef\xbb\xbf").replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def native_results(root, operation):
    events = [json.loads(line) for line in contained(root, operation["receipt"]).read_text().splitlines()]
    requests, results = {}, []
    for event in events:
        message = event["message"]
        if event["direction"] == "request":
            if "id" in message:
                if message["id"] in requests:
                    raise ValueError("repeated request identity")
                requests[message["id"]] = message
        elif event["direction"] == "response":
            if event.get("began_before_request"):
                continue
            request = requests.pop(message.get("id"), None)
            if request is None:
                continue
            if request["method"] != "tools/call":
                continue
            envelope = message["result"]
            content = envelope["structuredContent"]
            blocks = envelope["content"]
            args = request["params"]["arguments"]
            if len(blocks) != 1 or blocks[0]["type"] != "text" or json.loads(blocks[0]["text"]) != content:
                raise ValueError("native result disagreement")
            if content["schema"] != "mousa.mcp_result.v1" or content["source"] != operation["source"] or args["source"] != operation["source"] or content["operation"] != request["params"]["name"]:
                raise ValueError("native source/operation identity mismatch")
            if bool(envelope.get("isError")) != ("error" in content):
                raise ValueError("native error shape mismatch")
            results.append((request["params"]["name"], args, content))
        else:
            raise ValueError("unknown receipt direction")
    if requests:
        raise IncompleteCapture("incomplete request capture")
    return results


def covers(hit, label):
    return (hit["item"] == label["item"] and hit["representation_sha256"] == label["representation_sha256"] and
            hit["byte_start"] <= label["byte_start"] and hit["byte_end"] >= label["byte_end"])


def account(report, expected, revisions):
    result, rendered = report["result"], report["rendered"]
    hits = result["evidence"]
    passages = rendered["passages"]
    if [p["evidence"] for p in passages] != hits:
        raise ValueError("rendered/native selection mismatch")
    for hit, passage in zip(hits, passages):
        key = (hit["item"], hit["representation_sha256"])
        row = revisions.get(key)
        if row is None:
            raise ValueError("unknown released revision")
        data = normalized(row["text"])
        start, end = hit["byte_start"], hit["byte_end"]
        if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(data):
            raise ValueError("invalid evidence range")
        selected = data[start:end]
        if selected.decode() != hit["text"] or len(selected) != hit["byte_length"] or sha(selected) != hit["content_sha256"] or sha(data) != hit["representation_sha256"]:
            raise ValueError("released byte/digest mismatch")
        if passage["source"] != result["source"] or passage["attribution"] != {k: row[k] for k in ("id", "author", "date", "uri")}:
            raise ValueError("revision attribution mismatch")
    context = rendered["context"].encode()
    if len(context) != rendered["context_bytes"] or sha(context) != rendered["context_sha256"]:
        raise ValueError("rendered context identity mismatch")
    labels = expected["required"]
    covered = sum(any(covers(hit, label) for hit in hits) for label in labels)
    required_passages = sum(any(covers(hit, label) for label in labels) for hit in hits)
    used = sum(len(hit["text"].encode()) for hit in hits)
    if used != result["used_bytes"] or used > result["budget_bytes"]:
        raise ValueError("evidence byte budget disagreement")
    return {"required_spans": len(labels), "covered_spans": covered, "released_passages": len(hits),
            "required_passages": required_passages, "irrelevant_passages": len(hits) - required_passages,
            "evidence_bytes": used, "rendered_context_bytes": len(context),
            "selected": [{k: hit[k] for k in ("item", "representation_id", "representation_sha256", "segment_id", "byte_start", "byte_end")} for hit in hits],
            "budget_omitted": result.get("budget_omitted"), "duplicate_omitted": result.get("duplicate_omitted", 0)}


def analyze(root):
    validate_members(root)
    run = json.loads(contained(root, "summary.json").read_text())
    plan = json.loads(contained(root, "inputs/scenario.json").read_text())
    manifest = json.loads(contained(root, "inputs/manifest.json").read_text())
    for name, identity in manifest["files"].items():
        data = contained(root, "inputs/" + name).read_bytes()
        if {"bytes": len(data), "sha256": sha(data)} != identity:
            raise ValueError("frozen input identity mismatch")
    revisions, histories = {}, {}
    for name, path in plan["histories"].items():
        h = json.loads(contained(root, "inputs/" + path).read_text())
        histories[name] = h
        revisions[name] = {(row["id"], sha(normalized(row["text"]))): row for row in h["revisions"]}
    expected_ops, saved, final_state = [], [], {}
    for step in plan["steps"]:
        source = step["source"]
        if "native_items" in step:
            items = step["native_items"]
            kind = "native-prefix"
            committed = items[:step["native_error"]["completed_items"]]
        else:
            h = histories[source]
            rows = {r["revision"]: r for r in h["revisions"]}
            epoch = next(e for e in h["epochs"] if e["epoch"] == step["command"][1])
            items = [{"id": o["id"], "deleted": True} if o.get("deleted") else {"id": o["id"], "text": rows[o["revision"]]["text"]} for o in epoch["operations"]]
            kind = "epoch"
            committed = items
        for item in committed:
            final_state[(source, item["id"])] = None if item.get("deleted") else sha(normalized(item["text"]))
        expected_ops.append((step["id"], kind, source, step, {"source": histories[source]["source"], "items": items, "segment_policy": "passage-v1"}))
        expected_ops.append((step["id"] + "-status", "status", source, {"active_items": step["active_items"]}, {"source": histories[source]["source"]}))
        number = len(expected_ops)
        expected_ops.append((step["id"] + "-query", "lifecycle-query", source, {"required": step["required"], "exact_selection": True},
                             {"source": histories[source]["source"], "query": step["query"], "policy": "original", "packing_policy": "original", "budget_bytes": 2048}))
        if step.get("save_trail"):
            saved.append((step["id"], source, number))
    for label, source, number in saved:
        expected_ops.append((label + "-historical", "historical", source, {"query_operation": number}, None))
    for case in plan["cases"]:
        for mode in plan["modes"]:
            label = case["id"] + "-" + mode["policy"] + "-" + mode["packing_policy"]
            number = len(expected_ops)
            expected_ops.append((label, "comparison", case["source"], {**case, **mode},
                                 {"source": histories[case["source"]]["source"], "query": case["query"], "budget_bytes": case["budget_bytes"], **mode}))
            expected_ops.append((label + "-trail", "comparison-trail", case["source"], {"query_operation": number}, None))
    failures, missing, comparisons, lifecycle = [], [], [], []
    actual_reports = {}
    for number, op in enumerate(run["operations"]):
        try:
            if number >= len(expected_ops):
                raise ValueError("unexpected extra operation")
            label, kind, source_name, expectation, arguments = expected_ops[number]
            if (op["id"], op["kind"], op["source_name"], op["expected"]) != (label, kind, source_name, expectation) or op["source"] != histories[source_name]["source"]:
                raise ValueError("operation order or frozen expectation mismatch")
            actual = json.loads(contained(root, op["stdout"]).read_text())
            results = native_results(root, op)
            if not results:
                raise IncompleteCapture("missing native operation")
            tool_name = {"epoch": "mousa_sync", "native-prefix": "mousa_sync", "status": "mousa_status",
                         "lifecycle-query": "mousa_query", "comparison": "mousa_query",
                         "historical": "mousa_trail", "comparison-trail": "mousa_trail"}[kind]
            if arguments is None:
                query = actual_reports[expectation["query_operation"]]["result"]
                arguments = {"source": op["source"], "trail_id": query["trail_id"]}
            if results[0][0] != tool_name or results[0][1] != arguments:
                raise ValueError("native invocation differs from frozen operation")
            actual_reports[number] = actual
            if not actual.get("capture_complete"):
                raise IncompleteCapture("incomplete consumer capture")
            if actual["process"]["exit_code"] != 0 or actual["process"].get("forced") or actual["process"].get("cleanup_errors"):
                raise ValueError("failed native teardown")
            if op["kind"] == "native-prefix":
                if actual.get("operation_status") != "FAIL" or len(results) != 1 or results[0][2] != actual["native_error"]:
                    raise ValueError("missing retained native failure")
                if actual["native_error"]["error"] != {**op["expected"]["native_error"], "message": actual["native_error"]["error"]["message"]}:
                    raise ValueError("wrong committed-prefix error")
                lifecycle.append({"operation": number, "id": op["id"], "assertion": "PASS", "native_operation": "FAIL", "error": actual["native_error"]["error"]})
                continue
            if op["exit_code"] != 0 or actual["status"] != "PASS" or actual["operation_status"] != "PASS":
                raise ValueError("consumer operation failed")
            if actual["source"] != op["source"] or actual["binary_sha256"] != run["binary"]["sha256"] or actual["history_sha256"] != manifest["files"][plan["histories"][op["source_name"]]]["sha256"]:
                raise ValueError("consumer input identity mismatch")
            primary = results[0]
            if primary[2].get("result") != actual["result"]:
                raise ValueError("report differs from raw native result")
            if len(results) != 2 or results[1][0] != "mousa_status" or results[1][1] != {"source": op["source"]} or results[1][2].get("result") != actual["source_status"]:
                raise ValueError("source status differs from raw native result")
            if op["kind"] == "epoch":
                for action in ("added", "updated", "restored", "deleted", "absent", "unchanged"):
                    if actual["result"].get(action, []) != op["expected"]["outcome"].get(action, []):
                        raise ValueError("wrong lifecycle action: " + action)
            elif op["kind"] == "status":
                if actual["result"]["active_items"] != op["expected"]["active_items"] or actual["result"]["needs_recovery"]:
                    raise ValueError("wrong current source state")
            elif op["kind"] in ("lifecycle-query", "comparison"):
                args, result = primary[1], actual["result"]
                if result["query"] != args["query"] or result["query_policy"] != args["policy"] or result.get("packing_policy", "original") != args["packing_policy"] or result["budget_bytes"] != args["budget_bytes"]:
                    raise ValueError("query policy identity mismatch")
                accounting = account(actual, op["expected"], revisions[op["source_name"]])
                if op["kind"] == "lifecycle-query" and (accounting["covered_spans"] != accounting["required_spans"] or accounting["irrelevant_passages"]):
                    raise ValueError("wrong current lifecycle selection")
                if op["kind"] == "comparison":
                    comparisons.append({"operation": number, "case": op["expected"]["id"], "source": op["source"], "policy": args["policy"], "packing_policy": args["packing_policy"], "budget_bytes": args["budget_bytes"], **accounting})
            elif op["kind"] in ("historical", "comparison-trail"):
                original = actual_reports[op["expected"]["query_operation"]]["result"]
                historical = actual["result"]["historical"]
                if actual["result"]["authorization_outcome"] != "allow" or actual["result"]["authorization_decision_id"] == original["decision_id"]:
                    raise ValueError("historical selection lacks fresh authorization")
                if historical["budget_bytes"] != original["budget_bytes"] or historical["used_bytes"] != original["used_bytes"] or historical.get("packing_policy", "original") != original.get("packing_policy", "original"):
                    raise ValueError("historical policy/accounting mismatch")
                selected = [(r["segment_id"], r["content_sha256"], r["text_bytes"]) for r in historical["candidates"] if r["selected"]]
                before = [(r["segment_id"], r["content_sha256"], len(r["text"].encode())) for r in original["evidence"]]
                if historical["packet_id"] != original["packet_id"] or selected != before:
                    raise ValueError("historical selection rewritten")
                if any("text" in row for row in historical["candidates"]):
                    raise ValueError("historical inspection unexpectedly released text")
                if kind == "historical":
                    for row, hit in zip((r for r in historical["candidates"] if r["selected"]), original["evidence"]):
                        indexed = final_state.get((source_name, hit["item"])) == hit["representation_sha256"]
                        if row["indexed_now"] != indexed:
                            raise ValueError("historical/current activation disagreement")
                else:
                    omissions = [{k: r[k] for k in ("segment_id", "content_sha256", "text_bytes", "omission", "duplicate_of") if k in r} for r in historical["candidates"] if not r["selected"]]
                    comparisons[-1]["omitted_candidates"] = omissions
                    budget = sum(r.get("omission", "budget") == "budget" for r in omissions)
                    duplicate = sum(r.get("omission") == "duplicate" for r in omissions)
                    if budget != original["budget_omitted"] or duplicate != original.get("duplicate_omitted", 0):
                        raise ValueError("omission accounting disagreement")
            lifecycle.append({"operation": number, "id": op["id"], "assertion": "PASS"})
        except (IncompleteCapture, OSError, KeyError, json.JSONDecodeError) as error:
            missing.append({"operation": number, "id": op["id"], "reason": str(error)})
        except ValueError as error:
            failures.append({"operation": number, "id": op["id"], "reason": str(error)})
    expected_count = len(expected_ops)
    complete = run["status"] == "COMPLETE" and len(run["operations"]) == expected_count and not missing
    return {"schema": "mousa.chronology_analysis.v1", "run_status": run["status"],
            "assertion_status": "INCOMPLETE" if not complete else "FAIL" if failures else "PASS",
            "operations_observed": len(run["operations"]), "operations_expected": expected_count,
            "failures": failures, "missing_evidence": missing, "lifecycle": lifecycle, "comparisons": comparisons,
            "agent_acceptance": "NOT RUN", "semantic_support": "NOT RUN", "timing_claim": "NOT RUN"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    try:
        result = analyze(parser.parse_args().run)
    except (OSError, ValueError, KeyError) as error:
        result = {"schema": "mousa.chronology_analysis.v1", "assertion_status": "INVALID_EVIDENCE",
                  "error": {"type": type(error).__name__, "message": str(error)},
                  "agent_acceptance": "NOT RUN"}
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["assertion_status"] == "PASS" else 1)
