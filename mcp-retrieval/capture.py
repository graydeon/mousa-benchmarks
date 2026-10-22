"""Small synthetic MCP vector/hybrid capture, offline verification and controls."""
import argparse
import copy
from fractions import Fraction
import importlib.util
import json
import math
from pathlib import Path
import os
import select
import re
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("trail_capture", ROOT.parent / "mcp-trail-supersession/run.py")
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
SOURCE = "synthetic-mcp-retrieval"
FIXTURE = {"overlap.md": "Drain sockets before stopping the host.",
           "vector.md": "Radishes prefer damp soil.", "lexical.md": "Drain sockets."}
PINS = ("source_id", "segment_id", "representation_id", "representation_sha256", "content_sha256")


def check(condition, label):
    if not condition:
        raise ValueError(label)


def equal(left, right, label):
    check(wire.same_json(left, right), label)


def read_frame(reader):
    deadline = time.monotonic() + 30
    while b"\n" not in reader.buffer:
        remaining = deadline - time.monotonic()
        check(remaining > 0 and select.select([reader.fd], [], [], remaining)[0], "stdio-read-timeout")
        chunk = os.read(reader.fd, 65536)
        check(bool(chunk), "stdio-unexpected-eof")
        reader.buffer += chunk
        check(len(reader.buffer) <= 8 << 20, "stdio-frame-bound")
    line, delimiter, reader.buffer = reader.buffer.partition(b"\n")
    return line + delimiter


def reject_constant(token):
    raise ValueError("nonfinite-json: " + token)


def parsed(stream):
    import base64
    data = base64.b64decode(stream["base64"], validate=True)
    equal(wire.stream(data), stream, "stream-hash-and-bytes")
    json.loads(data, parse_constant=reject_constant)
    value, duplicates = wire.strict_json(data)
    check(not duplicates and value is not None, "strict-json")
    return value


def identities(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith(("_id", "_sha256")):
                check(type(item) is str and re.fullmatch("[0-9a-f]{64}", item), "canonical-identity-" + key)
            identities(item)
    elif isinstance(value, list):
        for item in value:
            identities(item)


def schedule(space, results):
    calls = [("initialize", "initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
              "clientInfo": {"name": "mousa-retrieval-capture", "version": "1"}}),
             ("initialized", "notifications/initialized", {}), ("discovery", "tools/list", {})]
    for mode in ("vector", "hybrid"):
        for packing in ("default", "original", "exact-v1"):
            label = mode + "/" + packing
            args = {"source": SOURCE, "space_id": space, "values": [1, 0], "budget_bytes": 40}
            if mode == "hybrid":
                args.update(query="Drain", policy="original")
            if packing != "default":
                args["packing_policy"] = packing
            calls.append((label, "tools/call", {"name": "mousa_" + mode + "_query", "arguments": args}))
            for details in (None, False, True):
                inspect = {"source": SOURCE, "trail_id": results.get(label, {}).get("trail_id", "PENDING")}
                if details is not None:
                    inspect["retrieval_details"] = details
                calls.append((label + "/history/" + str(details), "tools/call", {"name": "mousa_trail", "arguments": inspect}))
    args = {"source": SOURCE, "space_id": space, "values": [True, 0], "budget_bytes": 40}
    calls.append(("invalid-number", "tools/call", {"name": "mousa_vector_query", "arguments": args}))
    args = {"source": "/not/a/configured/directory", "space_id": space, "values": [1, 0], "budget_bytes": 40}
    calls.append(("unconfigured", "tools/call", {"name": "mousa_vector_query", "arguments": args}))
    return calls


def tail_schedule(space, results):
    args = {"source": SOURCE, "space_id": space, "values": [1, 0], "budget_bytes": 40}
    calls = [("initialize", "initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
              "clientInfo": {"name": "mousa-retrieval-capture", "version": "1"}}),
             ("initialized", "notifications/initialized", {}), ("discovery", "tools/list", {})]
    for mode in ("vector", "hybrid"):
        query = dict(args)
        if mode == "hybrid":
            query.update(query="Drain", policy="original")
        calls.append((mode, "tools/call", {"name": "mousa_" + mode + "_query", "arguments": query}))
        calls.append((mode + "/old-history", "tools/call", {"name": "mousa_trail", "arguments": {
            "source": SOURCE, "trail_id": results[mode + "/exact-v1"]["trail_id"], "retrieval_details": True}}))
    return calls


def verify(report):
    equal(len(report["sessions"]), 3, "scheduled-session-count")
    check(bool(wire.schema_violations({"oneOf": [{"type": "integer"}, {"type": "number"}]}, 1)), "schema-exactly-one-control")
    native = report["native"]
    equal([r["name"] for r in native], ["sync", "inputs", "import", "revision", "deny"], "native-schedule")
    for row in native:
        equal(row["exit"], 0, "native-exit")
    equal(native[0]["stdin"], "".join(wire.encoded({"id": k, "text": v}).decode() for k, v in FIXTURE.items()), "fixture-input")
    equal(native[0]["arguments"], ["sync", "--source", SOURCE], "sync-selector")
    equal(native[1]["arguments"], ["vector", "inputs", "--source", SOURCE], "export-selector")
    exported = json.loads(native[1]["stdout"])
    passages = {p["item"]: p for p in exported["passages"]}
    equal(sorted(passages), sorted(FIXTURE), "export-items")
    for name, p in passages.items():
        equal(p["text"], FIXTURE[name], "export-text")
        equal(p["content_sha256"], wire.sha(FIXTURE[name].encode()), "export-digest")
    supplied = {"schema": "mousa.vector_import.v1", "space": {"schema": "mousa.vector_space.v1", "provider": "synthetic",
        "model": "mcp-arithmetic", "version": "1", "dimensions": 2, "metric": "cosine"},
        "embeddings": [{**{key: p[key] for key in PINS}, "values": [1, 0] if p["item"] == "vector.md" else [0, 1]}
                       for name, p in passages.items() if name != "lexical.md"]}
    equal(json.loads(native[2]["stdin"]), supplied, "import-pins-values")
    equal(native[2]["arguments"], ["vector", "import", "--source", SOURCE], "import-selector")
    equal(native[3]["stdin"], wire.encoded({"id": "overlap.md", "text": "Replacement revision."}).decode(), "revision-input")
    equal(native[3]["arguments"], ["sync", "--source", SOURCE], "revision-selector")
    equal(native[4]["arguments"], ["access", "--source", SOURCE, "deny"], "deny-selector")
    space = json.loads(native[2]["stdout"])["space_id"]
    results, discovered = {}, None
    for session_index, session in enumerate(report["sessions"]):
        equal(session["exit"], 0, "stdio-exit")
        equal(session["stdout_tail"], wire.stream(b""), "stdio-no-extra-frames")
        equal(session["stderr"], "", "stdio-stderr")
        count = len(schedule(space, results)) if session_index == 0 else len(tail_schedule(space, results))
        equal(len(session["frames"]), count, "scheduled-frame-count")
        schemas = {}
        for index, event in enumerate(session["frames"]):
            planned = schedule(space, results) if session_index == 0 else tail_schedule(space, results)
            label, method, params = planned[index]
            equal(event["label"], label, "schedule-label")
            request = {"jsonrpc": "2.0", "method": method, "params": params}
            if method != "notifications/initialized":
                request["id"] = index + 1
            # Byte equality binds raw requests to the independently regenerated schedule.
            equal(event["request"], wire.stream(wire.encoded(request)), "scheduled-request-bytes")
            if method == "notifications/initialized":
                check("response" not in event, "notification-has-no-response")
                continue
            response = parsed(event["response"])
            equal(response.get("id"), index + 1, "response-request-id")
            equal(response.get("jsonrpc"), "2.0", "response-protocol")
            check("result" in response and "error" not in response, "rpc-result")
            payload = response["result"]
            if method == "initialize":
                equal(payload["protocolVersion"], "2025-11-25", "negotiated-protocol")
                continue
            if method == "tools/list":
                schemas = {t["name"]: t for t in payload["tools"]}
                equal(sorted(schemas), sorted(["mousa_sync", "mousa_status", "mousa_query", "mousa_trail", "mousa_vector_query", "mousa_hybrid_query"]), "discovered-tools")
                if discovered is None:
                    discovered = schemas
                else:
                    equal(schemas, discovered, "restart-discovery")
                baseline = json.loads((ROOT / "baseline-discovery.json").read_text())
                for name in ("mousa_sync", "mousa_status", "mousa_query"):
                    baseline[name]["inputSchema"]["properties"]["source"]["enum"] = [SOURCE]
                    equal(schemas[name], baseline[name], "legacy-definition-" + name)
                continue
            tool, args = params["name"], params["arguments"]
            envelope = payload["structuredContent"]
            identities(envelope)
            check(not wire.schema_violations(schemas[tool]["outputSchema"], envelope), "discovered-output-schema")
            equal(json.loads(payload["content"][0]["text"]), envelope, "text-structured-equality")
            equal(envelope["operation"], tool, "operation-binding")
            if label in ("invalid-number", "unconfigured"):
                equal(payload["isError"], True, "expected-tool-error")
                equal(envelope["error"]["code"], "invalid_arguments" if label == "invalid-number" else "source_not_permitted", "precise-boundary-error")
                check("result" not in envelope, "error-no-result")
                continue
            check(not wire.schema_violations(schemas[tool]["inputSchema"], args), "discovered-input-schema")
            check(payload.get("isError", False) is False, "successful-tool")
            equal(envelope["source"], SOURCE, "source-binding")
            result = envelope["result"]
            results[(str(session_index) + "/" if session_index else "") + label] = result
            if session_index == 2:
                if tool == "mousa_trail":
                    check("historical" not in result, "denied-no-history")
                else:
                    equal(result["evidence"], [], "denied-no-evidence")
                    equal([result[k] for k in ("eligible", "indexed", "missing")], [0, 0, 0], "denied-no-coverage")
                    equal(result[result["mode"]]["candidates"], [], "denied-no-candidates")
                continue
            if tool == "mousa_trail":
                h = result["historical"]
                producing_label = label.split("/history/")[0] if session_index == 0 else label.split("/")[0] + "/exact-v1"
                producing = results[producing_label]
                equal(result["trail_id"], producing["trail_id"], "history-target")
                for key, origin in (("id", "trail_id"), ("decision_id", "decision_id"), ("packet_id", "packet_id")):
                    equal(h[key], producing[origin], "producing-history-" + key)
                mode = producing["mode"]
                if args.get("retrieval_details") is True:
                    equal(h[mode], producing[mode], "recorded-ranking-facts")
                else:
                    check("vector" not in h and "hybrid" not in h, "default-history-property-set")
                check("token" not in h, "no-token-metadata")
                continue
            mode = result["mode"]
            equal(result["space_id"], space, "query-space")
            equal(result["packing_policy"], args.get("packing_policy", "original"), "packing-default")
            equal(result["budget_bytes"], 40, "query-budget")
            facts = result[mode]
            equal(facts["space_id"], space, "facts-space")
            equal(facts["query_vector_id"], result["query_vector_id"], "query-vector-binding")
            equal([result[k] for k in ("eligible", "indexed", "missing")], [3, 2, 1] if session_index == 0 else [3, 1, 2], "current-coverage")
            if session_index == 1:
                check("before stopping" not in json.dumps(result), "no-stale-evidence")
                equal([p["item"] for p in result["evidence"]], ["lexical.md", "vector.md"] if mode == "hybrid" else ["vector.md"], "revised-selection")
                continue
            expected = "vector.md" if mode == "vector" else "overlap.md"
            equal([p["item"] for p in result["evidence"]], [expected], "selected-evidence")
            first = result["evidence"][0]
            for key in PINS:
                equal(first[key], passages[expected][key], "selected-pin-" + key)
            equal(first["text"], FIXTURE[expected], "selected-text")
            equal([first["byte_start"], first["byte_end"], result["used_bytes"]], [0, len(FIXTURE[expected].encode()), len(FIXTURE[expected].encode())], "selected-coordinates-budget")
            if mode == "vector":
                equal(first["cosine"], 1, "selected-cosine")
                equal([c["segment_id"] for c in facts["candidates"]], [passages[k]["segment_id"] for k in ("vector.md", "overlap.md")], "cosine-order")
                equal([c["cosine"] for c in facts["candidates"]], [1, 0], "all-cosines")
            else:
                equal(facts["fusion_policy"], "rrf-equal-k60-v1", "fusion-policy")
                equal([first["lexical"]["rank"], first["vector"]["rank"]], [2, 2], "overlap-branch-ranks")
                equal(first["rrf"], float(Fraction(1, 31)), "overlap-fusion")
                equal([c["segment_id"] for c in facts["candidates"]][1:], sorted(passages[k]["segment_id"] for k in ("lexical.md", "vector.md")), "fusion-ties")
                expected_ranks = {"overlap.md": (2, 2), "lexical.md": (1, 0), "vector.md": (0, 1)}
                for c in facts["candidates"]:
                    name = next(k for k, p in passages.items() if p["segment_id"] == c["segment_id"])
                    lr, vr = expected_ranks[name]
                    equal(c.get("lexical", {}).get("rank", 0), lr, "candidate-lexical-rank")
                    equal(c.get("vector", {}).get("rank", 0), vr, "candidate-vector-rank")
                    equal(c["rrf"], float((Fraction(1, 60 + lr) if lr else 0) + (Fraction(1, 60 + vr) if vr else 0)), "candidate-fusion")
                    if lr:
                        check(type(c["lexical"]["bm25"]) in (int, float) and math.isfinite(c["lexical"]["bm25"]), "actual-bm25-number")
                    if vr:
                        equal(c["vector"]["cosine"], 1 if name == "vector.md" else 0, "candidate-cosine")
                    for key in PINS:
                        equal(c[key], passages[name][key], "candidate-pin-" + key)
            if label.endswith("/original"):
                equal(result["packet_id"], results[mode + "/default"]["packet_id"], "default-packet")
    return {"result": "PASS", "stdio_sessions": 3, "scheduled_frames": sum(len(s["frames"]) for s in report["sessions"]),
            "product_head": report["product"]["head"], "limits": "Synthetic arithmetic/protocol and authorization only; no semantic quality or performance claim."}


def capture(args):
    binary = args.mousa.resolve()
    def git(*cmd):
        return subprocess.check_output(["git", *cmd], cwd=args.product_source, text=True, timeout=30).strip()
    equal(git("rev-parse", "HEAD"), args.product_head, "requested-public-head")
    equal(git("status", "--porcelain"), "", "clean-product-source")
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"product": {"head": args.product_head, "tree": git("rev-parse", "HEAD^{tree}"),
              "binary_sha256": wire.sha(binary.read_bytes()), "build": "GOWORK=off CGO_ENABLED=0 go build -o BINARY ./cmd/mousa"}, "native": [], "sessions": []}
    def save():
        wire.save(args.output / "capture.json", report)
    with tempfile.TemporaryDirectory(prefix="mousa-public-mcp-", dir="/tmp") as temporary:
        store = Path(temporary) / "evidence.sqlite"
        def native(name, arguments, stdin=""):
            result = subprocess.run([str(binary), "-store", str(store), *arguments], input=stdin, text=True, capture_output=True, timeout=30)
            report["native"].append({"name": name, "arguments": arguments, "stdin": stdin, "stdout": result.stdout, "stderr": result.stderr, "exit": result.returncode})
            save()
            equal(result.returncode, 0, "native-call")
            return json.loads(result.stdout)
        native("sync", ["sync", "--source", SOURCE], "".join(wire.encoded({"id": k, "text": v}).decode() for k, v in FIXTURE.items()))
        exported = native("inputs", ["vector", "inputs", "--source", SOURCE])
        supplied = {"schema": "mousa.vector_import.v1", "space": {"schema": "mousa.vector_space.v1", "provider": "synthetic", "model": "mcp-arithmetic", "version": "1", "dimensions": 2, "metric": "cosine"},
                    "embeddings": [{**{key: p[key] for key in PINS}, "values": [1, 0] if p["item"] == "vector.md" else [0, 1]} for p in exported["passages"] if p["item"] != "lexical.md"]}
        space = native("import", ["vector", "import", "--source", SOURCE], wire.encoded(supplied).decode())["space_id"]
        results = {}
        for session_index in range(3):
            if session_index == 1:
                native("revision", ["sync", "--source", SOURCE], wire.encoded({"id": "overlap.md", "text": "Replacement revision."}).decode())
            if session_index == 2:
                native("deny", ["access", "--source", SOURCE, "deny"])
            session = {"frames": []}
            report["sessions"].append(session)
            with tempfile.TemporaryFile() as errors:
                process = subprocess.Popen([str(binary), "-store", str(store), "mcp", "--caller", "cli", "--source", SOURCE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors)
                reader = wire.LineReader(process.stdout.fileno())
                try:
                    count = len(schedule(space, results)) if session_index == 0 else len(tail_schedule(space, results))
                    for index in range(count):
                        planned = schedule(space, results) if session_index == 0 else tail_schedule(space, results)
                        label, method, params = planned[index]
                        message = {"jsonrpc": "2.0", "method": method, "params": params}
                        if method != "notifications/initialized":
                            message["id"] = index + 1
                        data = wire.encoded(message)
                        event = {"label": label, "request": wire.stream(data)}
                        session["frames"].append(event)
                        process.stdin.write(data)
                        process.stdin.flush()
                        if method != "notifications/initialized":
                            response = read_frame(reader)
                            event["response"] = wire.stream(response)
                            decoded = json.loads(response)
                            if method == "tools/call" and "result" in decoded.get("result", {}).get("structuredContent", {}):
                                results[label] = decoded["result"]["structuredContent"]["result"]
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
                        session["stderr"] = errors.read().decode()
                        save()
    summary = verify(report)
    wire.save(args.output / "summary.json", summary)
    print(json.dumps(summary))


def controls(report):
    receipts = []
    for name in ("wrong-selected-evidence", "bool-query-number"):
        changed = copy.deepcopy(report)
        event = next(e for e in changed["sessions"][0]["frames"] if e["label"] == "vector/default")
        if name == "wrong-selected-evidence":
            response = parsed(event["response"])
            payload = response["result"]
            payload["structuredContent"]["result"]["evidence"][0]["item"] = "overlap.md"
            payload["content"][0]["text"] = wire.canonical(payload["structuredContent"])
            event["response"] = wire.stream(wire.encoded(response))
            expected = "selected-evidence"
        else:
            request = parsed(event["request"])
            request["params"]["arguments"]["values"] = [True, 0]
            event["request"] = wire.stream(wire.encoded(request))
            expected = "scheduled-request-bytes"
        try:
            verify(changed)
        except ValueError as error:
            equal(str(error), expected, "control-intended-detector")
            receipts.append({"control": name, "result": "PASS", "detector": str(error), "rehashed_capture_sha256": wire.sha(wire.encoded(changed))})
        else:
            raise ValueError("negative-control-accepted")
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "verify", "controls"))
    parser.add_argument("--mousa", type=Path)
    parser.add_argument("--product-source", type=Path)
    parser.add_argument("--product-head")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "capture":
        capture(args)
    else:
        report = json.loads((args.output / "capture.json").read_text())
        if args.mode == "verify":
            summary = verify(report)
            equal(json.loads((args.output / "summary.json").read_text()), summary, "summary-binding")
            print(json.dumps(summary))
        else:
            verify(report)
            print(json.dumps(controls(report)))


if __name__ == "__main__":
    main()
