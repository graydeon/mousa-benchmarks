"""Capture MCP token selection and independently count the complete returned context."""
import argparse
import copy
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("retrieval_capture", ROOT.parent / "mcp-retrieval/capture.py")
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
wire, check, equal = shared.wire, shared.check, shared.equal
SOURCE = "synthetic-mcp-tokens"
FIXTURE = {"unicode.md": "Drain 你好 مرحبا café é <|endoftext|>\t\x7f",
           "short.md": "Drain concise", "copy.md": "Drain concise"}
PINS = shared.PINS


def ordinary_encoder(cache):
    os.environ["TIKTOKEN_CACHE_DIR"] = str(cache.resolve())
    import tiktoken
    import tiktoken.load
    equal(importlib.metadata.version("tiktoken"), "0.12.0", "official-reference-version")

    def offline(*unused_args, **unused_kwargs):
        raise ValueError("prepare vocabulary before capture or replay")

    tiktoken.load.read_file = offline
    return tiktoken.get_encoding("o200k_base")


def query_args(mode, packing, space):
    args = {"source": SOURCE, "budget_bytes": 4096, "packing_policy": packing}
    if mode != "lexical":
        args.update(space_id=space, values=[1, 0])
    if mode != "vector":
        args.update(query="Drain", policy="original")
    return args


def schedule(session, space, results, encoder):
    calls = [("initialize", "initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
              "clientInfo": {"name": "mousa-token-capture", "version": "1"}}),
             ("initialized", "notifications/initialized", {}), ("discovery", "tools/list", {})]

    def tool(label, name, args):
        calls.append((label, "tools/call", {"name": name, "arguments": args}))

    for mode in ("lexical", "vector", "hybrid"):
        name = "mousa_query" if mode == "lexical" else "mousa_" + mode + "_query"
        if session == 0:
            for packing in ("original", "exact-v1"):
                key = mode + "/" + packing
                args = query_args(mode, packing, space)
                full = results.get(key + "/full", {})
                n = len(encoder.encode_ordinary(full.get("context", "")))
                for suffix, extra in (("byte", {}), ("full", {"context_tokens": 10000}),
                        ("pressure", {"context_tokens": 240}), ("exact", {"context_tokens": n}),
                        ("short", {"context_tokens": n - 1}),
                        ("reserved", {"context_tokens": 10000, "window_tokens": n + 50,
                                      "prompt_reserve_tokens": 20, "output_reserve_tokens": 31}),
                        ("bytes", {"context_tokens": 10000, "budget_bytes": 1}),
                        ("zero", {"context_tokens": 10000, "window_tokens": 20,
                                  "prompt_reserve_tokens": 10, "output_reserve_tokens": 10})):
                    tool(key + "/" + suffix, name, dict(args, **extra))
                for suffix, extra in (("history-default", {}), ("history-false", {"token_details": False}),
                        ("history-token", {"token_details": True}),
                        ("history-both", {"token_details": True, "retrieval_details": True})):
                    tool(key + "/" + suffix, "mousa_trail", dict(source=SOURCE,
                         trail_id=full.get("trail_id", "PENDING"), **extra))
                tool(key + "/byte-after", name, args)
        else:
            key = mode + "/exact-v1"
            full = results[key + "/full"]
            args = query_args(mode, "exact-v1", space)
            tool(mode + "/token", name, dict(args, context_tokens=10000))
            if session == 1:
                tool(mode + "/byte", name, args)
                tool(mode + "/history-default", "mousa_trail", {"source": SOURCE, "trail_id": full["trail_id"]})
            tool(mode + "/history", "mousa_trail", {"source": SOURCE, "trail_id": full["trail_id"],
                 "token_details": True, "retrieval_details": True})
    if session == 0:
        args = dict(query_args("lexical", "original", space), context_tokens=None)
        tool("invalid-null", "mousa_query", args)
        tool("unconfigured", "mousa_query", dict(args, source="/not/a/configured/source", context_tokens=240))
    return calls


def rendering(result, args, passages, encoder):
    pieces = []
    for row in result["evidence"]:
        p = passages[row["segment_id"]]
        for key in ("representation_id", "representation_sha256", "content_sha256", "item", "text"):
            equal(row[key], p[key], "selected-" + key)
        equal([row["byte_start"], row["byte_end"]], [0, len(p["text"].encode())], "selected-range")
        pieces.append(f"[source={p['source_id']} segment={p['segment_id']} sha256={p['content_sha256']}]\n{p['text']}")
    expected = "\n\n".join(pieces)
    equal(result["context"], expected, "returned-context-rendering")
    token = result["token"]
    ids = encoder.encode_ordinary(expected)
    equal(token["measured_tokens"], len(ids), "official-whole-context-count")
    equal(token["rendered_sha256"], wire.sha(expected.encode()), "returned-context-digest")
    equal(token["rendered_bytes"], len(expected.encode()), "rendered-byte-count")
    equal([token["backend"], token["rendering"]],
          ["tiktoken/0.12.0/o200k_base/ordinary", "mousa.context_text.v1"], "backend-rendering-identity")
    budget = {"cap": args["context_tokens"], "window": args.get("window_tokens", 0),
              "prompt_reserve": args.get("prompt_reserve_tokens", 0),
              "output_reserve": args.get("output_reserve_tokens", 0)}
    equal(token["budget"], budget, "requested-budget-facts")
    limit = min(budget["cap"], budget["window"] - budget["prompt_reserve"] - budget["output_reserve"]) if budget["window"] else budget["cap"]
    equal(token["limit"], limit, "effective-token-limit")
    check(len(ids) <= limit, "token-bound")
    used = sum(len(row["text"].encode()) for row in result["evidence"])
    equal(result["used_bytes"], used, "survivor-used-bytes")
    equal(result["budget_bytes"], args["budget_bytes"], "requested-byte-budget")
    check(used <= args["budget_bytes"], "byte-bound")
    expected_keys = {"mode", "backend", "rendering", "source_id", "limit", "budget", "measured_tokens",
                     "rendered_bytes", "rendered_sha256", "candidate_ids", "proposed_tokens"}
    if token["mode"] == "lexical" and token.get("lexical"):
        expected_keys.add("lexical")
    check(set(token) == expected_keys, "safe-token-properties")
    check(len(token["candidate_ids"]) == len(token["proposed_tokens"]), "accepted-correspondence")
    return ids


def stable(result):
    return {k: v for k, v in result.items() if k not in
            ("request_id", "decision_id", "trail_id", "evaluated_at_usec", "latency_micros")}


def verify(report, encoder):
    native = report["native"]
    equal([r["name"] for r in native], ["sync", "inputs", "import", "revision", "deny"], "native-schedule")
    for row in native:
        equal(row["exit"], 0, "native-exit")
        equal(row["stderr"], wire.stream(b""), "native-stderr")
    initial = b"".join(wire.encoded({"id": k, "text": v}) for k, v in FIXTURE.items())
    equal(native[0]["stdin"], wire.stream(initial), "native-fixture-input")
    exported = shared.parsed(native[1]["stdout"])
    passages = {p["segment_id"]: p for p in exported["passages"]}
    equal(sorted(p["item"] for p in passages.values()), sorted(FIXTURE), "exported-fixture")
    for p in passages.values():
        equal(p["text"], FIXTURE[p["item"]], "exported-text")
        equal(p["content_sha256"], wire.sha(p["text"].encode()), "exported-digest")
    supplied = {"schema": "mousa.vector_import.v1", "space": {"schema": "mousa.vector_space.v1",
                "provider": "synthetic", "model": "mcp-token-counting", "version": "1", "dimensions": 2, "metric": "cosine"},
                "embeddings": [{**{k: p[k] for k in PINS}, "values": [1, 0]} for p in exported["passages"]]}
    equal(shared.parsed(native[2]["stdin"]), supplied, "supplied-vector-pins")
    equal(native[3]["stdin"], wire.stream(b"".join(wire.encoded({"id": k, "text": "Drain replacement."}) for k in FIXTURE)), "replacement-input")
    for row, expected in zip(native, (["sync", "--source", SOURCE], ["vector", "inputs", "--source", SOURCE],
            ["vector", "import", "--source", SOURCE], ["sync", "--source", SOURCE], ["access", "--source", SOURCE, "deny"]), strict=True):
        equal(row["arguments"], expected, "native-command-binding")
    space = shared.parsed(native[2]["stdout"])["space_id"]
    results, references, discovered = {}, {}, None
    equal(len(report["sessions"]), 3, "scheduled-session-count")
    for si, session in enumerate(report["sessions"]):
        equal(session["tokenizer_configured"], si != 1, "startup-only-backend")
        equal(session["exit"], 0, "stdio-exit")
        equal(session["stderr"], wire.stream(b""), "stdio-stderr")
        equal(session["stdout_tail"], wire.stream(b""), "stdio-no-extra-frames")
        equal(len(session["frames"]), len(schedule(si, space, results, encoder)), "scheduled-frame-count")
        schemas = {}
        for index, event in enumerate(session["frames"]):
            label, method, params = schedule(si, space, results, encoder)[index]
            equal(event["label"], label, "scheduled-label")
            request = {"jsonrpc": "2.0", "method": method, "params": params}
            if method != "notifications/initialized":
                request["id"] = index + 1
            equal(event["request"], wire.stream(wire.encoded(request)), "scheduled-request-bytes")
            if method == "notifications/initialized":
                check("response" not in event, "notification-no-response")
                continue
            response = shared.parsed(event["response"])
            equal(response.get("id"), index + 1, "response-request-id")
            equal(response.get("jsonrpc"), "2.0", "response-protocol")
            payload = response["result"]
            if method == "initialize":
                equal(payload["protocolVersion"], "2025-11-25", "protocol-version")
                continue
            if method == "tools/list":
                schemas = {t["name"]: t for t in payload["tools"]}
                equal(sorted(schemas), sorted(["mousa_sync", "mousa_status", "mousa_query", "mousa_trail", "mousa_vector_query", "mousa_hybrid_query"]), "discovered-tools")
                if discovered is None:
                    discovered = schemas
                else:
                    equal(schemas, discovered, "restart-discovery")
                continue
            tool, args = params["name"], params["arguments"]
            envelope = payload["structuredContent"]
            shared.identities(envelope)
            check(not wire.schema_violations(schemas[tool]["outputSchema"], envelope), "closed-output-schema")
            equal(json.loads(payload["content"][0]["text"]), envelope, "text-structured-equality")
            equal(envelope["operation"], tool, "tool-operation-binding")
            failure = "invalid_arguments" if label == "invalid-null" else "source_not_permitted" if label == "unconfigured" else "tokenizer_unavailable" if si == 1 and label.endswith("/token") else None
            if failure:
                equal(payload["isError"], True, "expected-tool-error")
                equal(envelope["error"]["code"], failure, "precise-tool-error")
                check("result" not in envelope, "error-no-success-payload")
                continue
            check(not wire.schema_violations(schemas[tool]["inputSchema"], args), "declared-input-schema")
            check(not payload.get("isError", False), "successful-tool")
            equal(envelope["source"], SOURCE, "source-binding")
            result = envelope["result"]
            if si == 0:
                results[label] = result
            if tool == "mousa_trail":
                if si == 2:
                    check("historical" not in result, "denied-no-historical-existence")
                    continue
                key = label.rsplit("/", 1)[0] if si == 0 else label.split("/")[0] + "/exact-v1"
                produced = results[key + "/full"]
                h = result["historical"]
                for key, origin in (("id", "trail_id"), ("decision_id", "decision_id"), ("packet_id", "packet_id")):
                    equal(h[key], produced[origin], "producing-history-" + key)
                if "request_id" in produced:
                    equal(h["request_id"], produced["request_id"], "producing-query-request")
                    equal(h["expression"], produced["expression"], "producing-query-expression")
                equal([r["segment_id"] for r in h["candidates"] if r["selected"]],
                      [r["segment_id"] for r in produced["evidence"]], "recorded-selected-correspondence")
                if args.get("token_details"):
                    equal(h["token"], produced["token"], "recorded-token-view")
                else:
                    check("token" not in h, "default-token-history-hidden")
                mode = produced["token"]["mode"]
                if args.get("retrieval_details") and mode != "lexical":
                    equal(h[mode], produced[mode], "independent-retrieval-history")
                else:
                    check("vector" not in h and "hybrid" not in h, "default-retrieval-history-hidden")
                check("token_verification" not in h, "history-no-recount")
                if si == 0 and label.endswith("history-false"):
                    equal(h, results[label.rsplit("/", 1)[0] + "/history-default"]["historical"], "false-default-history")
                continue
            if "context_tokens" not in args:
                check("context" not in result and "token" not in result, "byte-only-property-set")
                if si == 0 and label.endswith("byte-after"):
                    equal(stable(result), stable(results[label.rsplit("/", 1)[0] + "/byte"]), "omitted-token-compatibility")
                continue
            if si == 2:
                equal(result["context"], "", "denied-context")
                equal(result["evidence"], [], "denied-evidence")
                equal(result["token"]["candidate_ids"], [], "denied-token-candidates")
                if "eligible" in result:
                    equal([result[k] for k in ("eligible", "indexed", "missing")], [0, 0, 0], "denied-coverage")
            references[str(si) + "/" + label] = rendering(result, args, passages, encoder)
            if si == 0:
                key, suffix = label.rsplit("/", 1)
                if suffix == "full":
                    equal(len(result["evidence"]), 2 if args["packing_policy"] == "exact-v1" else 3, "duplicate-packing")
                if suffix == "exact":
                    equal(result["context"], results[key + "/full"]["context"], "whole-rendering-boundary-fit")
                if suffix in ("short", "pressure"):
                    check(result["context"] != results[key + "/full"]["context"], "token-pressure-changes-selection")
                if suffix == "reserved":
                    equal(result["context"], results[key + "/short"]["context"], "reservation-effective-boundary")
                if suffix in ("bytes", "zero"):
                    equal(result["context"], "", "empty-budget-context")
    if "reference_ids" in report:
        equal(report["reference_ids"], references, "independent-reference-ids")
    return {"result": "PASS", "product_head": report["product"]["head"], "stdio_sessions": 3,
            "scheduled_requests": sum(len(s["frames"]) for s in report["sessions"]),
            "counted_contexts": len(references), "limits": "Synthetic whole-context counting/protocol only; no model, semantic quality or window-safety claim."}, references


def capture(args, encoder):
    binary = args.mousa.resolve()
    def git(*command):
        return subprocess.check_output(["git", *command], cwd=args.product_source, text=True, timeout=30).strip()
    equal(git("rev-parse", "HEAD"), args.product_head, "requested-public-head")
    equal(git("status", "--porcelain"), "", "clean-public-source")
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"product": {"head": args.product_head, "tree": git("rev-parse", "HEAD^{tree}"),
              "binary_sha256": wire.sha(binary.read_bytes()), "build": "GOWORK=off CGO_ENABLED=0 go build -o BINARY ./cmd/mousa"},
              "reference_backend": {"version": "0.12.0", "encoding": encoder.name, "method": "encode_ordinary"}, "native": [], "sessions": []}
    def save():
        wire.save(args.output / "capture.json", report)
    with tempfile.TemporaryDirectory(prefix="mousa-mcp-tokens-", dir="/tmp") as temporary:
        store = Path(temporary) / "evidence.sqlite"
        def native(name, arguments, data=b""):
            p = subprocess.run([str(binary), "-store", str(store), *arguments], input=data, capture_output=True, timeout=30)
            report["native"].append({"name": name, "arguments": arguments, "stdin": wire.stream(data),
                                     "stdout": wire.stream(p.stdout), "stderr": wire.stream(p.stderr), "exit": p.returncode})
            save()
            equal(p.returncode, 0, "native-preparation-exit")
            return json.loads(p.stdout)
        native("sync", ["sync", "--source", SOURCE], b"".join(wire.encoded({"id": k, "text": v}) for k, v in FIXTURE.items()))
        exported = native("inputs", ["vector", "inputs", "--source", SOURCE])
        supplied = {"schema": "mousa.vector_import.v1", "space": {"schema": "mousa.vector_space.v1", "provider": "synthetic", "model": "mcp-token-counting", "version": "1", "dimensions": 2, "metric": "cosine"},
                    "embeddings": [{**{k: p[k] for k in PINS}, "values": [1, 0]} for p in exported["passages"]]}
        space = native("import", ["vector", "import", "--source", SOURCE], wire.encoded(supplied))["space_id"]
        results = {}
        for si in range(3):
            if si == 1:
                native("revision", ["sync", "--source", SOURCE], b"".join(wire.encoded({"id": k, "text": "Drain replacement."}) for k in FIXTURE))
            if si == 2:
                native("deny", ["access", "--source", SOURCE, "deny"])
            session = {"tokenizer_configured": si != 1, "frames": []}
            report["sessions"].append(session)
            argv = [str(binary), "-store", str(store), "mcp", "--caller", "cli", "--source", SOURCE]
            if si != 1:
                argv += ["--tokenizer-python", str(args.python.absolute()), "--tokenizer-cache", str(args.cache.resolve())]
            with tempfile.TemporaryFile() as errors:
                process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors)
                reader = wire.LineReader(process.stdout.fileno())
                try:
                    for index in range(len(schedule(si, space, results, encoder))):
                        label, method, params = schedule(si, space, results, encoder)[index]
                        message = {"jsonrpc": "2.0", "method": method, "params": params}
                        if method != "notifications/initialized":
                            message["id"] = index + 1
                        data = wire.encoded(message)
                        event = {"label": label, "request": wire.stream(data)}
                        session["frames"].append(event)
                        process.stdin.write(data)
                        process.stdin.flush()
                        if method != "notifications/initialized":
                            raw = shared.read_frame(reader)
                            event["response"] = wire.stream(raw)
                            decoded = json.loads(raw)
                            if si == 0 and method == "tools/call":
                                content = decoded["result"]["structuredContent"]
                                if "result" in content:
                                    results[label] = content["result"]
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
    summary, references = verify(report, encoder)
    report["reference_ids"] = references
    save()
    wire.save(args.output / "summary.json", summary)
    print(json.dumps(summary))


def controls(report, encoder):
    receipts = []
    for name, detector in (("altered-count", "official-whole-context-count"),
                           ("altered-context", "returned-context-rendering"),
                           ("changed-scheduled-token-budget", "scheduled-request-bytes")):
        changed = copy.deepcopy(report)
        event = next(e for e in changed["sessions"][0]["frames"] if e["label"] == "hybrid/exact-v1/full")
        if name == "changed-scheduled-token-budget":
            request = shared.parsed(event["request"])
            request["params"]["arguments"]["context_tokens"] = 9999
            event["request"] = wire.stream(wire.encoded(request))
        else:
            response = shared.parsed(event["response"])
            payload = response["result"]
            result = payload["structuredContent"]["result"]
            if name == "altered-count":
                result["token"]["measured_tokens"] += 1
            else:
                result["context"] += "\n"
                result["token"]["rendered_sha256"] = wire.sha(result["context"].encode())
                result["token"]["rendered_bytes"] += 1
            payload["content"][0]["text"] = wire.canonical(payload["structuredContent"])
            event["response"] = wire.stream(wire.encoded(response))
        try:
            verify(changed, encoder)
        except ValueError as error:
            equal(str(error), detector, "control-intended-detector")
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
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    encoder = ordinary_encoder(args.cache)
    if args.mode == "capture":
        capture(args, encoder)
    else:
        report = json.loads((args.output / "capture.json").read_text())
        summary, _ = verify(report, encoder)
        equal(json.loads((args.output / "summary.json").read_text()), summary, "summary-binding")
        if args.mode == "controls":
            print(json.dumps(controls(report, encoder)))
        else:
            print(json.dumps(summary))


if __name__ == "__main__":
    main()
