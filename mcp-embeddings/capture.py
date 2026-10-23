"""Capture MCP external-embedding protocol/arithmetic on fresh stores; no model calls."""
import argparse
import copy
from fractions import Fraction
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
SOURCE = "synthetic-mcp-embedding-workflow"
FIXTURE = {"overlap.md": "Drain sockets before stopping the host.",
           "vector.md": "Radishes prefer damp soil.", "lexical.md": "Drain sockets."}
REPLACEMENT = "Replacement revision."


def supplied(exported, version="1"):
    return {"schema": "mousa.vector_import.v1", "space": {
        "schema": "mousa.vector_space.v1", "provider": "synthetic", "model": "arithmetic-only",
        "version": version, "dimensions": 2, "metric": "cosine"}, "embeddings": [
        {**{key: p[key] for key in shared.PINS}, "values": [1, 0] if p["item"] == "vector.md" else [0, 1]}
        for p in exported.get("passages", []) if version != "1" or p["item"] != "lexical.md"]}


def schedule(session, results):
    calls = [("initialize", "initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
              "clientInfo": {"name": "mousa-embedding-capture", "version": "1"}}),
             ("initialized", "notifications/initialized", {}), ("discovery", "tools/list", {})]

    def tool(label, name, args):
        calls.append((label, "tools/call", {"name": name, "arguments": dict(source=SOURCE, **args)}))

    def query(label, mode, packing, imported):
        args = {"space_id": results.get(imported, {}).get("space_id", "PENDING"),
                "values": [1, 0], "budget_bytes": 40, "packing_policy": packing}
        if mode == "hybrid":
            args.update(query="Drain", policy="original")
        tool(label, "mousa_" + mode + "_query", args)

    def history(label, produced):
        tool(label, "mousa_trail", {"trail_id": results.get(produced, {}).get("trail_id", "PENDING"),
                                    "retrieval_details": True})

    initial = supplied(results.get("inputs", {}))
    fresh = supplied(results.get("fresh-inputs", {}), "2")
    if session == 0:
        tool("sync", "mousa_sync", {"items": [{"id": k, "text": v} for k, v in FIXTURE.items()]})
        tool("inputs", "mousa_vector_inputs", {})
        tool("import", "mousa_vector_import", {"import": initial})
        tool("retry", "mousa_vector_import", {"import": initial})
        for mode in ("vector", "hybrid"):
            for packing in ("original", "exact-v1"):
                label = mode + "/" + packing
                query(label, mode, packing, "import")
                history(label + "/history", label)
        conflict = copy.deepcopy(initial)
        if conflict["embeddings"]:
            conflict["embeddings"][0]["values"] = [-1, 0]
        tool("conflict", "mousa_vector_import", {"import": conflict})
        tool("replacement", "mousa_sync", {"items": [{"id": "overlap.md", "text": REPLACEMENT}]})
        stale = copy.deepcopy(initial)
        stale["space"]["version"] = "stale"
        tool("stale", "mousa_vector_import", {"import": stale})
        tool("fresh-inputs", "mousa_vector_inputs", {})
        tool("fresh-import", "mousa_vector_import", {"import": fresh})
        query("fresh-query", "vector", "original", "fresh-import")
        history("old-history", "hybrid/original")
    elif session == 1:
        tool("read-inputs", "mousa_vector_inputs", {})
        readonly = copy.deepcopy(fresh)
        readonly["space"]["version"] = "read-only"
        tool("read-import", "mousa_vector_import", {"import": readonly})
        query("read-query", "vector", "original", "fresh-import")
        history("read-history", "hybrid/original")
    else:
        tool("denied-inputs", "mousa_vector_inputs", {})
        history("denied-history", "hybrid/original")
        admin = copy.deepcopy(fresh)
        admin["space"]["version"] = "denied-admin"
        tool("denied-admin", "mousa_vector_import", {"import": admin})
    return calls


def verify(report):
    equal(len(report["sessions"]), 3, "session-count")
    equal(report["runner_sha256"], wire.sha(Path(__file__).read_bytes()), "runner-binding")
    check(len(report["product"]["head"]) == 40 and len(report["product"]["tree"]) == 40, "product-identity")
    results, catalog = {}, None
    requests, responses = 0, 0
    failures = {"conflict": "conflict", "stale": "invalid_record", "read-import": "ingestion_not_permitted"}
    for si, session in enumerate(report["sessions"]):
        equal(session["writable"], si != 1, "startup-write-permission")
        startup = ["mcp", "--caller", "cli", "--source", SOURCE]
        if si != 1:
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
            equal(response.get("id"), index + 1, "response-request-binding")
            equal(response.get("jsonrpc"), "2.0", "response-protocol")
            check("result" in response and "error" not in response, "rpc-success")
            payload = response["result"]
            if method == "initialize":
                equal(payload["protocolVersion"], "2025-11-25", "protocol-version")
                continue
            if method == "tools/list":
                tools = {t["name"]: t for t in payload["tools"]}
                equal(sorted(tools), sorted(("mousa_sync", "mousa_status", "mousa_query", "mousa_trail",
                      "mousa_vector_query", "mousa_hybrid_query", "mousa_vector_inputs", "mousa_vector_import")), "tool-set")
                if catalog is None:
                    catalog = tools
                equal(tools, catalog, "restart-discovery")
                annotations = tools["mousa_vector_import"]["annotations"]
                equal([annotations["readOnlyHint"], annotations["destructiveHint"], annotations["idempotentHint"]],
                      [False, True, True], "truthful-write-hints")
                continue
            tool, args = params["name"], params["arguments"]
            envelope = payload["structuredContent"]
            check(not wire.schema_violations(catalog[tool]["outputSchema"], envelope), "discovered-output-schema")
            equal(json.loads(payload["content"][0]["text"]), envelope, "text-structured-equality")
            equal([envelope["schema"], envelope["operation"], envelope["source"]],
                  ["mousa.mcp_result.v1", tool, SOURCE], "tool-envelope-binding")
            if label in failures:
                equal(payload.get("isError"), True, "expected-tool-error")
                equal(envelope["error"]["code"], failures[label], "precise-refusal")
                check("result" not in envelope, "refusal-no-success")
                continue
            check(not payload.get("isError", False) and "error" not in envelope, "expected-tool-success")
            result = envelope["result"]
            results[label] = result
            if tool == "mousa_vector_inputs":
                if label == "denied-inputs":
                    equal(result["decision_outcome"], "deny", "export-denial")
                    equal(result["passages"], [], "denial-no-passage-facts")
                    continue
                equal(result["decision_outcome"], "allow", "authorized-export")
                expected_fixture = dict(FIXTURE)
                if label != "inputs":
                    expected_fixture["overlap.md"] = REPLACEMENT
                equal([p["item"] for p in result["passages"]], sorted(expected_fixture), "export-item-order")
                for p in result["passages"]:
                    equal(p["text"], expected_fixture[p["item"]], "export-normalized-bytes")
                    equal([p["byte_start"], p["byte_end"]], [0, len(p["text"].encode())], "export-byte-range")
                    equal(p["content_sha256"], wire.sha(p["text"].encode()), "export-content-pin")
                    shared.identities({key: p[key] for key in shared.PINS})
                if label == "read-inputs":
                    equal(result["passages"], results["fresh-inputs"]["passages"], "stable-current-pins")
                    check(result["decision_id"] != results["fresh-inputs"]["decision_id"], "fresh-decision")
            elif tool == "mousa_vector_import":
                equal(result["imported"], len(args["import"]["embeddings"]), "accepted-submitted-count")
                # Canonical descriptor bytes use this field order and a final LF.
                descriptor = (json.dumps(args["import"]["space"], separators=(",", ":")) + "\n").encode()
                equal(result["space_id"], wire.sha(descriptor), "canonical-space-identity")
                if label == "retry":
                    equal(result, results["import"], "immutable-retry-identity")
            elif tool in ("mousa_vector_query", "mousa_hybrid_query"):
                equal(result["space_id"], args["space_id"], "query-import-space-binding")
                mode = "vector" if tool == "mousa_vector_query" else "hybrid"
                first = result["evidence"][0]
                equal(first["item"], "vector.md" if mode == "vector" else "overlap.md", "known-ranking")
                if mode == "vector":
                    equal(first["cosine"], 1, "known-cosine")
                else:
                    equal([first["lexical"]["rank"], first["vector"]["rank"]], [2, 2], "known-branch-ranks")
                    check(abs(first["rrf"] - float(Fraction(2, 62))) < 1e-16, "known-RRF")
                producing = results["fresh-inputs" if label in ("fresh-query", "read-query") else "inputs"]
                pins = {p["item"]: p for p in producing["passages"]}
                for e in result["evidence"]:
                    equal({k: e[k] for k in shared.PINS}, {k: pins[e["item"]][k] for k in shared.PINS}, "query-export-pins")
                if label == "read-query":
                    equal(result["vector"], results["fresh-query"]["vector"], "restart-producing-embeddings")
            elif tool == "mousa_trail":
                if label == "denied-history":
                    check("historical" not in result, "denial-no-history")
                    equal(result["authorization_outcome"], "deny", "history-denial")
                    continue
                produced = label.removesuffix("/history") if label.endswith("/history") else "hybrid/original"
                q = results[produced]
                h = result["historical"]
                equal([h["id"], h["packet_id"], h["decision_id"]], [q["trail_id"], q["packet_id"], q["decision_id"]], "producing-history-identities")
                equal(h[q["mode"]], q[q["mode"]], "historical-producing-facts")
    equal([r["arguments"] for r in report["native"]], [["access", "--source", SOURCE, "deny"]], "native-policy-only")
    for row in report["native"]:
        equal(row["exit"], 0, "native-policy-exit")
        equal(row["stdin"], wire.stream(b""), "native-no-input")
        shared.parsed(row["stdout"])
        equal(row["stderr"], wire.stream(b""), "native-policy-stderr")
    return {"result": "PASS", "requests": requests, "responses": responses, "process_exits": 3,
            "product_head": report["product"]["head"], "product_tree": report["product"]["tree"],
            "limits": "Arithmetic/protocol only; no semantic/model/performance/window claim. Wire replay is internal consistency, not proof against a malicious producer."}


def capture(args):
    binary, source = args.mousa.resolve(), args.product_source.resolve()
    def git(*arguments):
        return subprocess.check_output(["git", "-C", str(source), *arguments], text=True).strip()
    equal(git("rev-parse", "HEAD"), args.product_head, "exact-public-head")
    equal(git("status", "--porcelain"), "", "clean-product-source")
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"product": {"head": args.product_head, "tree": git("rev-parse", "HEAD^{tree}"),
              "binary_sha256": wire.sha(binary.read_bytes()), "build": "GOWORK=off CGO_ENABLED=0 go build -o BINARY ./cmd/mousa"},
              "runner_sha256": wire.sha(Path(__file__).read_bytes()), "native": [], "sessions": []}
    def save():
        wire.save(args.output / "capture.json", report)
    results = {}
    with tempfile.TemporaryDirectory(prefix="mousa-mcp-embeddings-") as temporary:
        store = Path(temporary) / "evidence.sqlite"
        for si in range(3):
            if si == 2:
                arguments = ["access", "--source", SOURCE, "deny"]
                r = subprocess.run([str(binary), "-store", str(store), *arguments], input=b"", capture_output=True, timeout=30)
                report["native"].append({"arguments": arguments, "stdin": wire.stream(b""),
                    "stdout": wire.stream(r.stdout), "stderr": wire.stream(r.stderr), "exit": r.returncode})
            argv = [str(binary), "-store", str(store), "mcp", "--caller", "cli", "--source", SOURCE]
            if si != 1:
                argv += ["--ingest-source", SOURCE]
            session = {"writable": si != 1, "arguments": argv[3:], "frames": []}
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
    for name, detector in (("changed-import-values", "scheduled-request-bytes"),
                           ("fabricated-readonly-success", "expected-tool-error")):
        changed = copy.deepcopy(report)
        si, label = (0, "import") if name == "changed-import-values" else (1, "read-import")
        event = next(e for e in changed["sessions"][si]["frames"] if e["label"] == label)
        if si == 0:
            request = shared.parsed(event["request"])
            request["params"]["arguments"]["import"]["embeddings"][0]["values"] = [1, 0]
            event["request"] = wire.stream(wire.encoded(request))
        else:
            response = shared.parsed(event["response"])
            payload = response["result"]
            payload["isError"] = False
            envelope = payload["structuredContent"]
            del envelope["error"]
            readonly = supplied(shared.parsed(next(e for e in changed["sessions"][0]["frames"] if e["label"] == "fresh-inputs")["response"])["result"]["structuredContent"]["result"], "read-only")
            descriptor = (json.dumps(readonly["space"], separators=(",", ":")) + "\n").encode()
            envelope["result"] = {"schema": "mousa.vector_import_result.v1", "space_id": wire.sha(descriptor), "imported": 3}
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
        summary = verify(report)
        equal(json.loads((args.output / "summary.json").read_text()), summary, "summary-binding")
        print(json.dumps(controls(report) if args.mode == "controls" else summary))


if __name__ == "__main__":
    main()
