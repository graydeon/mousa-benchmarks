"""Capture declared supporting context over stdio MCP without product imports or models."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("retrieval_capture", ROOT.parent / "mcp-retrieval/capture.py")
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
wire, equal, check = shared.wire, shared.equal, shared.check
SOURCE = "notes"
FIXTURE = {"backup": "Run the backup inside the connection context manager.",
           "closure": "The context manager does not close the connection; close it explicitly.",
           "duplicate": "The context manager does not close the connection; close it explicitly.",
           "next": "A further note is not followed transitively."}
DECLARATION = {"from_item": "backup", "to_item": "closure",
               "basis": "connection cleanup qualification", "author": "example.maintainer"}


def declarations(*rows):
    return {"schema": "mousa.association_declarations.v1", "associations": list(rows)}


def schedule(session, results):
    calls = [("initialize", "initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
              "clientInfo": {"name": "mousa-association-capture", "version": "1"}}),
             ("initialized", "notifications/initialized", {}), ("discovery", "tools/list", {})]

    def tool(label, name, args):
        calls.append((label, "tools/call", {"name": name, "arguments": dict(source=SOURCE, **args)}))

    def query(label, policy="original", packing=None, document=None, budget=8192, **extra):
        args = dict(query="backup", policy=policy, budget_bytes=budget, **extra)
        if packing is not None:
            args["packing_policy"] = packing
        if document is not None:
            args["associations"] = document
        tool(label, "mousa_query", args)

    def history(label, producing):
        tool(label, "mousa_trail", {"trail_id": results.get(producing, {}).get("trail_id", "PENDING")})

    if session == 0:
        tool("sync", "mousa_sync", {"items": [{"id": k, "text": v} for k, v in FIXTURE.items()]})
        query("ordinary")
        query("explicit-false", supersession=False)
        query("unfired", document=declarations(dict(DECLARATION, from_item="unselected")))
        history("unfired-history", "unfired")
        for policy in ("original", "dedup"):
            for packing in ("original", "exact-v1"):
                label = policy + "/" + packing
                query(label, policy, packing, declarations(DECLARATION), supersession=False)
                history(label + "/history", label)
        query("budget", document=declarations(DECLARATION), budget=len(FIXTURE["backup"].encode()))
        query("unselected", document=declarations(DECLARATION), budget=1)
        query("depth-one", document=declarations(DECLARATION, dict(DECLARATION, from_item="closure", to_item="next")))
        query("duplicate", packing="exact-v1", document=declarations(DECLARATION, dict(DECLARATION, to_item="duplicate")))
        query("missing", document=declarations(dict(DECLARATION, to_item="absent")))
        tool("delete", "mousa_sync", {"items": [{"id": "closure", "deleted": True}]})
        query("inactive", document=declarations(DECLARATION))
        tool("null", "mousa_query", {"query": "backup", "policy": "original", "budget_bytes": 8192, "associations": None})
        query("empty", document=declarations())
        query("supersession-refusal", document=declarations(DECLARATION), supersession=True)
        query("token-refusal", document=declarations(DECLARATION), context_tokens=100)
        query("reservation-refusal", document=declarations(DECLARATION), window_tokens=0)
        tool("vector-refusal", "mousa_vector_query", {"space_id": "a" * 64, "values": [1, 0], "budget_bytes": 8192, "associations": declarations(DECLARATION)})
    elif session == 1:
        query("read-only", document=declarations(dict(DECLARATION, to_item="duplicate")))
        history("read-history", "original/original")
    else:
        query("denied", document=declarations(DECLARATION))
        history("denied-history", "original/original")
    return calls


def stable(result):
    value = copy.deepcopy(result)
    for key in ("request_id", "decision_id", "trail_id", "evaluated_at_usec", "latency_micros"):
        value.pop(key, None)
    return value


def verify(report):
    protocol = json.loads((ROOT / "protocol.json").read_text())
    equal(protocol["runner_sha256"], wire.sha(Path(__file__).read_bytes()), "frozen-runner")
    equal(report["runner_sha256"], protocol["runner_sha256"], "runner-binding")
    equal(report["protocol_sha256"], wire.sha((ROOT / "protocol.json").read_bytes()), "protocol-binding")
    equal(protocol["fixture"], FIXTURE, "frozen-fixture")
    equal(protocol["declaration"], DECLARATION, "frozen-declaration")
    equal(len(report["sessions"]), 3, "session-count")
    check(len(report["product"]["head"]) == 40 and len(report["product"]["tree"]) == 40, "product-identity")
    baseline = {t["name"]: t for t in json.loads((ROOT / "baseline-discovery.json").read_text())["tools"]}
    results, catalog = {}, None
    requests, responses = 0, 0
    refused = {"null", "empty", "supersession-refusal", "token-refusal", "reservation-refusal", "vector-refusal"}
    for si, session in enumerate(report["sessions"]):
        startup = ["mcp", "--caller", "cli", "--source", SOURCE]
        if si == 0:
            startup += ["--ingest-source", SOURCE]
        equal(session["arguments"], startup, "startup-arguments")
        equal(session["exit"], 0, "stdio-exit")
        equal(session["stdout_tail"], wire.stream(b""), "stdio-no-extra-bytes")
        equal(session["stderr"], wire.stream(b""), "stdio-stderr")
        equal(len(session["frames"]), len(schedule(si, results)), "frame-count")
        for index, event in enumerate(session["frames"]):
            label, method, params = schedule(si, results)[index]
            equal(event["label"], label, "schedule-label")
            expected = {"jsonrpc": "2.0", "method": method, "params": params}
            if method != "notifications/initialized":
                expected["id"] = index + 1
            equal(event["request"], wire.stream(wire.encoded(expected)), "scheduled-request-bytes")
            requests += 1
            if method == "notifications/initialized":
                check("response" not in event, "notification-no-response")
                continue
            response = shared.parsed(event["response"])
            responses += 1
            equal([response.get("id"), response.get("jsonrpc")], [index + 1, "2.0"], "response-request-binding")
            check("result" in response and "error" not in response, "rpc-success")
            payload = response["result"]
            if method == "initialize":
                equal(payload["protocolVersion"], "2025-11-25", "protocol-version")
                continue
            if method == "tools/list":
                tools = {t["name"]: t for t in payload["tools"]}
                if catalog is None:
                    catalog = tools
                equal(tools, catalog, "restart-discovery")
                old_shape = copy.deepcopy(tools)
                check("associations" in old_shape["mousa_query"]["inputSchema"]["properties"], "declared-query-input")
                del old_shape["mousa_query"]["inputSchema"]["properties"]["associations"]
                equal(old_shape, baseline, "only-query-input-grows")
                continue
            tool = params["name"]
            envelope = payload["structuredContent"]
            check(not wire.schema_violations(catalog[tool]["outputSchema"], envelope), "discovered-output-schema")
            equal(json.loads(payload["content"][0]["text"]), envelope, "text-structured-equality")
            equal([envelope["schema"], envelope["operation"]], ["mousa.mcp_result.v1", tool], "tool-envelope-binding")
            if label in refused:
                equal(payload.get("isError"), True, "expected-tool-error")
                equal(envelope["error"]["code"], "invalid_arguments", "precise-refusal")
                check("result" not in envelope, "refusal-no-success")
                continue
            equal(envelope["source"], SOURCE, "tool-source")
            check(not payload.get("isError", False) and "error" not in envelope, "expected-tool-success")
            result = envelope["result"]
            results[label] = result
            if tool == "mousa_sync":
                equal(result["total_items"], 4 if label == "sync" else 1, "sync-record-count")
            elif tool == "mousa_query":
                for key in ("request_id", "decision_id", "trail_id", "packet_id"):
                    shared.identities({key: result[key]})
                if label == "denied":
                    equal(result["decision_outcome"], "deny", "fresh-query-denial")
                    equal(result["evidence"], [], "denial-no-evidence")
                    check("association_omissions" not in result, "denial-no-association-facts")
                    continue
                equal(result["decision_outcome"], "allow", "query-authorization")
                evidence = result["evidence"]
                targets = ["backup"]
                if label in {"original/original", "original/exact-v1", "dedup/original", "dedup/exact-v1", "depth-one", "duplicate", "read-only"}:
                    targets += ["duplicate" if label == "read-only" else "closure"]
                elif label == "unselected":
                    targets = []
                equal([e["item"] for e in evidence], targets, "selected-items")
                for e in evidence:
                    text = FIXTURE[e["item"]]
                    equal(e["text"], text, "evidence-source-bytes")
                    equal([e["byte_start"], e["byte_end"], e["byte_length"]], [0, len(text.encode()), len(text.encode())], "evidence-byte-range")
                    equal(e["content_sha256"], wire.sha(text.encode()), "evidence-content-digest")
                    equal(e["representation_sha256"], e["content_sha256"], "whole-fixture-representation")
                    for key in ("segment_id", "representation_id"):
                        shared.identities({key: e[key]})
                    if e["item"] == "backup":
                        equal(e["origin"], "lexical", "primary-origin")
                        if label not in ("inactive", "read-only"):
                            equal(e, results["ordinary"]["evidence"][0], "primary-unchanged")
                        else:
                            equal({k: v for k, v in e.items() if k not in ("rank", "bm25_score")},
                                  {k: v for k, v in results["ordinary"]["evidence"][0].items() if k not in ("rank", "bm25_score")},
                                  "primary-provenance-after-index-change")
                    else:
                        equal(e["origin"], "association", "associated-origin")
                        equal(e["association"], dict(DECLARATION, to_item=e["item"]), "associated-attribution")
                        check("rank" not in e and "bm25_score" not in e, "no-associated-lexical-score")
                        check(e["segment_id"] != evidence[0]["segment_id"] and e["representation_id"] != evidence[0]["representation_id"], "own-associated-provenance")
                equal(result["used_bytes"], sum(len(e["text"].encode()) for e in evidence), "selected-byte-accounting")
                if label in ("explicit-false", "unfired"):
                    equal(stable(result), stable(results["ordinary"]), "default-unfired-compatibility")
                reasons = {"budget": "budget", "duplicate": "duplicate", "missing": "target_unknown", "inactive": "target_inactive"}
                if label in reasons:
                    omission = result["association_omissions"]
                    equal(len(omission), 1, "one-association-omission")
                    equal(omission[0]["reason"], reasons[label], "association-omission-reason")
            elif tool == "mousa_trail":
                shared.identities({"authorization_decision_id": result["authorization_decision_id"]})
                if label == "denied-history":
                    equal(result["authorization_outcome"], "deny", "fresh-history-denial")
                    check("historical" not in result, "denial-no-history")
                    continue
                equal(result["authorization_outcome"], "allow", "fresh-history-authorization")
                producing = "unfired" if label == "unfired-history" else "original/original" if label == "read-history" else label.removesuffix("/history")
                q, h = results[producing], result["historical"]
                equal([h["id"], h["request_id"], h["decision_id"], h["packet_id"]], [q["trail_id"], q["request_id"], q["decision_id"], q["packet_id"]], "producing-history-identities")
                check(result["authorization_decision_id"] != q["decision_id"], "independent-inspection-authorization")
                if label == "unfired-history":
                    check("schema" not in h and "associated" not in h, "unfired-v1-history")
                    continue
                equal(h["schema"], "mousa.source_trail.v3", "v3-association-history")
                equal(len(h["associated"]), 1, "recorded-associated-count")
                row, passage = h["associated"][0], q["evidence"][1]
                equal({k: row[k] for k in DECLARATION}, DECLARATION, "historical-attribution")
                equal([row["segment_id"], row["content_sha256"], row["text_bytes"], row["selected"]], [passage["segment_id"], passage["content_sha256"], passage["byte_length"], True], "historical-associated-provenance")
                equal(row["indexed_now"], label != "read-history", "current-index-not-historical-selection")
    equal([r["arguments"] for r in report["native"]], [["access", "--source", SOURCE, "deny"]], "native-policy-only")
    for row in report["native"]:
        equal(row["exit"], 0, "native-policy-exit")
        equal(row["stdin"], wire.stream(b""), "native-no-input")
        shared.parsed(row["stdout"])
        equal(row["stderr"], wire.stream(b""), "native-policy-stderr")
    equal([requests, responses], protocol["request_response_counts"], "frozen-schedule-counts")
    return {"result": "PASS", "requests": requests, "responses": responses, "process_exits": 3,
            "product_head": report["product"]["head"], "product_tree": report["product"]["tree"],
            "limits": "Synthetic protocol/selection only; no semantic, performance or authenticated-author claim. Replay proves internal consistency, not authenticity."}


def capture(args):
    binary, source = args.mousa.resolve(), args.product_source.resolve()
    def git(*arguments):
        return subprocess.check_output(["git", "-C", str(source), *arguments], text=True).strip()
    equal(git("rev-parse", "HEAD"), args.product_head, "exact-public-head")
    equal(git("status", "--porcelain"), "", "clean-product-source")
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"product": {"head": args.product_head, "tree": git("rev-parse", "HEAD^{tree}"),
              "binary_sha256": wire.sha(binary.read_bytes()), "build": "GOWORK=off CGO_ENABLED=0 go build -o BINARY ./cmd/mousa"},
              "runner_sha256": wire.sha(Path(__file__).read_bytes()),
              "protocol_sha256": wire.sha((ROOT / "protocol.json").read_bytes()), "native": [], "sessions": []}
    def save():
        wire.save(args.output / "capture.json", report)
    results = {}
    with tempfile.TemporaryDirectory(prefix="mousa-mcp-associations-") as temporary:
        store = Path(temporary) / "evidence.sqlite"
        for si in range(3):
            if si == 2:
                arguments = ["access", "--source", SOURCE, "deny"]
                r = subprocess.run([str(binary), "-store", str(store), *arguments], input=b"", capture_output=True, timeout=30)
                report["native"].append({"arguments": arguments, "stdin": wire.stream(b""),
                    "stdout": wire.stream(r.stdout), "stderr": wire.stream(r.stderr), "exit": r.returncode})
            argv = [str(binary), "-store", str(store), "mcp", "--caller", "cli", "--source", SOURCE]
            if si == 0:
                argv += ["--ingest-source", SOURCE]
            session = {"arguments": argv[3:], "frames": []}
            report["sessions"].append(session)
            with tempfile.TemporaryFile() as errors:
                process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors)
                reader = wire.LineReader(process.stdout.fileno())
                try:
                    for index in range(len(schedule(si, results))):
                        label, method, params = schedule(si, results)[index]
                        message = {"jsonrpc": "2.0", "method": method, "params": params}
                        if method != "notifications/initialized":
                            message["id"] = index + 1
                        data = wire.encoded(message)
                        event = {"label": label, "request": wire.stream(data)}
                        session["frames"].append(event)
                        process.stdin.write(data)
                        process.stdin.flush()
                        if method != "notifications/initialized":
                            event["response"] = wire.stream(shared.read_frame(reader))
                            response = shared.parsed(event["response"])
                            if method == "tools/call" and "result" in response.get("result", {}).get("structuredContent", {}):
                                results[label] = response["result"]["structuredContent"]["result"]
                        save()
                finally:
                    process.stdin.close()
                    try:
                        session["exit"] = process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        session["exit"] = process.wait()
                        raise
                    finally:
                        session["stdout_tail"] = wire.stream(reader.buffer + process.stdout.read())
                        process.stdout.close()
                        errors.seek(0)
                        session["stderr"] = wire.stream(errors.read())
                        save()
    summary = verify(report)
    wire.save(args.output / "summary.json", summary)
    print(json.dumps(summary))


def controls(report):
    receipts = []
    for name, detector in (("changed-declaration-request", "scheduled-request-bytes"),
                           ("changed-associated-provenance", "evidence-content-digest")):
        changed = copy.deepcopy(report)
        event = next(e for e in changed["sessions"][0]["frames"] if e["label"] == "original/original")
        if name == "changed-declaration-request":
            request = shared.parsed(event["request"])
            request["params"]["arguments"]["associations"]["associations"][0]["to_item"] = "next"
            event["request"] = wire.stream(wire.encoded(request))
        else:
            response = shared.parsed(event["response"])
            payload = response["result"]
            envelope = payload["structuredContent"]
            envelope["result"]["evidence"][1]["content_sha256"] = "0" * 64
            payload["content"][0]["text"] = wire.canonical(envelope)
            event["response"] = wire.stream(wire.encoded(response))
        try:
            verify(changed)
        except ValueError as error:
            equal(str(error), detector, "intended-control-detector")
            receipts.append({"control": name, "result": "PASS", "detector": str(error),
                             "rehashed_capture_sha256": wire.sha(wire.encoded(changed))})
        else:
            raise ValueError("negative-control-accepted")
    return receipts


def compare(left, right):
    rows = []
    for report in (left, right):
        verify(report)
        values = []
        for session in report["sessions"]:
            for event in session["frames"]:
                if "response" not in event:
                    continue
                response = shared.parsed(event["response"])["result"]
                if "structuredContent" not in response:
                    continue
                envelope = copy.deepcopy(response["structuredContent"])
                if "result" in envelope:
                    value = envelope["result"]
                    for key in ("request_id", "decision_id", "trail_id", "packet_id", "authorization_decision_id", "evaluated_at_usec", "latency_micros", "elapsed_seconds"):
                        value.pop(key, None)
                    if "historical" in value:
                        for key in ("id", "request_id", "decision_id", "packet_id"):
                            value["historical"].pop(key, None)
                    value.pop("store_bytes", None)
                values.append({"label": event["label"], "envelope": envelope})
        rows.append(values)
    equal(*rows, "fresh-store-stable-results")
    return {"result": "PASS", "compared_rows": len(rows[0]),
            "exclusions": "Per-call request/decision/trail/packet/authorization identities and evaluation/latency/elapsed timing; sync store_bytes. History id/request/decision/packet. All producing identities bound within each run."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "verify", "controls", "compare"))
    parser.add_argument("--mousa", type=Path)
    parser.add_argument("--product-source", type=Path)
    parser.add_argument("--product-head")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--other", type=Path)
    args = parser.parse_args()
    if args.mode == "capture":
        capture(args)
    else:
        report = json.loads((args.output / "capture.json").read_text())
        summary = verify(report)
        equal(json.loads((args.output / "summary.json").read_text()), summary, "summary-binding")
        result = controls(report) if args.mode == "controls" else compare(report, json.loads((args.other / "capture.json").read_text())) if args.mode == "compare" else summary
        print(json.dumps(result))


if __name__ == "__main__":
    main()
