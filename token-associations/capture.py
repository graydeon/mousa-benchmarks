"""Capture declared lexical context under measured token budgets; no model calls."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("token_capture", ROOT.parent / "mcp-tokens/capture.py")
tokens = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tokens)
shared, wire = tokens.shared, tokens.wire
check, equal = shared.check, shared.equal
SOURCE = "token-association-notes"
FIXTURE = {
    "backup.md": "Run the backup inside the connection context manager.",
    "closure.md": "The context manager does not close the connection; close it explicitly.",
    "copy.md": "The context manager does not close the connection; close it explicitly.",
}
DECLARATION = dict(from_item="backup.md", to_item="closure.md",
                   basis="connection cleanup qualification", author="example.maintainer")
DIRECTORY = Path(tempfile.gettempdir()) / "mousa-token-associations-fixture"


def document(*rows):
    return dict(schema="mousa.association_declarations.v1", associations=list(rows))


def schedule(results, encoder):
    events = []

    def native(label, arguments, value="", error=None):
        event = dict(kind="native", label=label, arguments=arguments, stdin=value)
        if error:
            event["expected_error"] = error
        events.append(event)

    def rpc(label, method, params):
        events.append(dict(kind="rpc", label=label, method=method, params=params))

    def tool(label, name, arguments):
        rpc(label, "tools/call", dict(name=name, arguments=dict(source=SOURCE, **arguments)))

    def start(label):
        events.append(dict(kind="start", label=label, arguments=["mcp", "--caller", "cli", "--source", SOURCE,
            "--tokenizer-python", "TOKEN_PY", "--tokenizer-cache", "TOKEN_CACHE"]))
        rpc(label + "/initialize", "initialize", dict(protocolVersion="2025-11-25", capabilities={},
            clientInfo=dict(name="token-association-capture", version="1")))
        rpc(label + "/initialized", "notifications/initialized", {})
        rpc(label + "/discovery", "tools/list", {})

    native("directory/sync", ["sync", "DIRECTORY"])
    native("jsonl/sync", ["sync", "--source", SOURCE],
           "".join(wire.encoded(dict(id=k, text=v)).decode() for k, v in FIXTURE.items()))
    for surface in ("directory", "jsonl", "mcp"):
        if surface == "mcp":
            start("mcp")
        selector = ["DIRECTORY"] if surface == "directory" else ["--source", SOURCE]

        def query(label, packing, cap, declaration="main", policy="original", supersession=None):
            if surface == "mcp":
                args = dict(query="backup", policy=policy, packing_policy=packing,
                            budget_bytes=8192, context_tokens=cap)
                if declaration == "main":
                    args["associations"] = document(DECLARATION)
                elif declaration == "duplicate":
                    args["associations"] = document(DECLARATION, dict(DECLARATION, to_item="copy.md"))
                elif declaration == "unfired":
                    args["associations"] = document(dict(DECLARATION, from_item="unselected"))
                if supersession is not None:
                    args["supersession"] = supersession
                tool(label, "mousa_query", args)
            else:
                args = ["query", "--budget-bytes", "8192", "--context-tokens", str(cap),
                        "--policy", policy, "--packing-policy", packing,
                        "--tokenizer-python", "TOKEN_PY", "--tokenizer-cache", "TOKEN_CACHE"]
                if declaration:
                    args += ["--associations", {"main": "DECLARATIONS", "duplicate": "DUPLICATES", "unfired": "UNFIRED"}[declaration]]
                if supersession is not None:
                    args += ["--supersession=" + str(supersession).lower()]
                native(label, [*args, *selector, "backup"])

        query(surface + "/ordinary", "original", 4096, None)
        query(surface + "/unfired", "original", 4096, "unfired")
        for packing in ("original", "exact-v1"):
            prefix = surface + "/" + packing
            policy = "original" if packing == "original" else "dedup"
            full = results.get(prefix + "/full", {})
            count = len(encoder.encode_ordinary(full.get("context", ""))) or 1
            for case, cap, declaration in (("full", 4096, "main"), ("exact", count, "main"),
                    ("short", max(1, count - 1), "main"), ("primary-omitted", 1, "main"),
                    ("duplicate", 4096, "duplicate")):
                query(prefix + "/" + case, packing, cap, declaration, policy,
                      False if case == "exact" else None)
            producing = results.get(prefix + "/exact", {}).get("trail_id", "PENDING")
            if surface == "mcp":
                tool(prefix + "/history", "mousa_trail", dict(trail_id=producing))
                tool(prefix + "/history-token", "mousa_trail", dict(trail_id=producing, token_details=True))
            else:
                native(prefix + "/history", ["trail", *selector, producing])
                native(prefix + "/recount", ["trail", "--verify-tokens", "--tokenizer-python", "TOKEN_PY",
                    "--tokenizer-cache", "TOKEN_CACHE", *selector, producing])
        if surface == "mcp":
            tool("refusal/supersession", "mousa_query", dict(query="backup", policy="original", budget_bytes=8192,
                 context_tokens=4096, associations=document(DECLARATION), supersession=True))
            for mode in ("vector", "hybrid"):
                args = dict(space_id="a" * 64, values=[1, 0], budget_bytes=8192,
                            context_tokens=4096, associations=document(DECLARATION))
                if mode == "hybrid":
                    args.update(query="backup", policy="original")
                tool("refusal/" + mode, "mousa_" + mode + "_query", args)
            events.append(dict(kind="stop", label="mcp/stop"))
    native("refusal/native", ["query", "--associations", "DECLARATIONS", "--context-tokens", "4096",
           "--supersession", "--source", SOURCE, "backup"], error="token associations require lexical retrieval without supersession")
    for surface, selector in (("directory", ["DIRECTORY"]), ("jsonl", ["--source", SOURCE])):
        native(surface + "/deny-access", ["access", *selector, "deny"])
        native(surface + "/denied", ["query", "--associations", "DECLARATIONS", "--context-tokens", "4096",
            "--tokenizer-python", "TOKEN_PY", "--tokenizer-cache", "TOKEN_CACHE", *selector, "backup"])
    start("denied")
    tool("mcp/denied", "mousa_query", dict(query="backup", policy="original", budget_bytes=8192,
         context_tokens=4096, associations=document(DECLARATION)))
    tool("mcp/denied-history", "mousa_trail", dict(
         trail_id=results.get("mcp/original/exact", {}).get("trail_id", "PENDING"), token_details=True))
    events.append(dict(kind="stop", label="denied/stop"))
    return events


def result_from(event):
    if event["kind"] == "native":
        if "expected_error" in event:
            equal(event["exit"], 2, "native-refusal-exit")
            equal(event["stdout"], wire.stream(b""), "native-refusal-no-result")
            error = event["stderr"]
            import base64
            data = base64.b64decode(error["base64"], validate=True)
            equal(wire.stream(data), error, "refusal-stream-binding")
            check(event["expected_error"] in data.decode(), "native-refusal-cause")
            return None
        equal(event["exit"], 0, "native-success-exit")
        equal(event["stderr"], wire.stream(b""), "native-no-stderr")
        return shared.parsed(event["stdout"])
    response = shared.parsed(event["response"])
    equal([response.get("id"), response.get("jsonrpc")], [event["id"], "2.0"], "response-request-binding")
    check("result" in response and "error" not in response, "rpc-success")
    return response["result"]


def passage(source, row):
    return f"[source={source} segment={row['segment_id']} sha256={row['content_sha256']}]\n{row['text']}"


def query_check(result, label, results, encoder, references):
    shared.identities(result)
    surface, *parts = label.split("/")
    case = parts[-1]
    evidence, token = result["evidence"], result["token"]
    if case == "denied":
        equal(result["decision_outcome"], "deny", "fresh-query-denial")
        equal(evidence, [], "denial-no-evidence")
        equal(result.get("association_omissions"), None, "denial-no-association-facts")
    else:
        equal(result["decision_outcome"], "allow", "query-authorization")
    normalized = []
    for row in evidence:
        if "segment" in row:
            segment = row["segment"]
            normalized.append(dict(segment_id=segment["id"], content_sha256=segment["content_sha256"], text=row["text"]))
        else:
            name = row["item"]
            equal(row["text"], FIXTURE[name], "selected-text")
            equal(row["content_sha256"], wire.sha(FIXTURE[name].encode()), "evidence-content-digest")
            equal(row["representation_sha256"], row["content_sha256"], "whole-item-representation")
            equal([row["byte_start"], row["byte_end"], row["byte_length"]],
                  [0, len(FIXTURE[name].encode()), len(FIXTURE[name].encode())], "evidence-coordinates")
            if name != "backup.md":
                equal(row["origin"], "association", "associated-origin")
                equal(row["association"], dict(DECLARATION, to_item=name), "association-provenance")
                check("rank" not in row and "bm25_score" not in row, "no-associated-lexical-rank")
            else:
                equal([row["origin"], row["rank"]], ["lexical", 1], "primary-rank")
            shared.identities({key: row[key] for key in ("segment_id", "representation_id", "content_sha256")})
            normalized.append(row)
    context = "\n\n".join(passage(token["source_id"], row) for row in normalized)
    equal(result["context"], context, "complete-context-rendering")
    count = len(encoder.encode_ordinary(context))
    equal(token["measured_tokens"], count, "whole-context-count")
    equal(token["rendered_bytes"], len(context.encode()), "rendered-bytes")
    equal(token["rendered_sha256"], wire.sha(context.encode()), "rendering-digest")
    equal([token["backend"], token["rendering"], token["mode"]],
          ["tiktoken/0.12.0/o200k_base/ordinary", "mousa.context_text.v1", "lexical"], "token-contract")
    equal(token["limit"], token["budget"]["cap"], "cap-accounting")
    check(count <= token["limit"], "measured-cap")
    equal(result["used_bytes"], sum(len(p["text"].encode()) for p in evidence), "body-byte-accounting")
    if case == "denied":
        equal([token["candidate_ids"], token["proposed_tokens"]], [[], []], "denial-no-primary-facts")
        check("associations" not in token, "denial-no-associated-counts")
    elif case in ("ordinary", "unfired"):
        equal(len(evidence), 1, "ordinary-primary-only")
        equal(normalized[0]["text"], FIXTURE["backup.md"], "ordinary-primary-text")
        equal(token["proposed_tokens"], [count], "ordinary-proposed-count")
        check("associations" not in token, "unfired-no-stage")
        if case == "unfired":
            ordinary = results[surface + "/ordinary"]
            equal([result["context"], result["packet_id"], token],
                  [ordinary["context"], ordinary["packet_id"], ordinary["token"]], "unfired-ordinary-binding")
    else:
        packing = parts[0]
        full = result if case == "full" else results[surface + "/" + packing + "/full"]
        pins = {row["item"]: row for row in full["evidence"]}
        primary = passage(token["source_id"], pins["backup.md"])
        primary_count = len(encoder.encode_ordinary(primary))
        equal(token["candidate_ids"], [pins["backup.md"]["segment_id"]], "accepted-primary-alignment")
        equal(token["proposed_tokens"], [primary_count], "primary-proposed-count")
        equal([f["rank"] for f in token["lexical"]], [1], "primary-lexical-alignment")
        if case == "primary-omitted":
            equal(evidence, [], "token-omitted-primary")
            check("associations" not in token and "association_omissions" not in result, "unselected-primary-no-expansion")
        else:
            expected = ["backup.md", "closure.md"]
            if case == "short":
                expected = ["backup.md"]
                equal(result["association_omissions"], [dict(from_item="backup.md", to_item="closure.md",
                    reason="tokens", segment_id=pins["closure.md"]["segment_id"])], "support-token-omission")
            elif case == "duplicate" and packing == "original":
                expected.append("copy.md")
            equal([p["item"] for p in evidence], expected, "selected-evidence")
            associated_ids = [pins["closure.md"]["segment_id"]]
            proposed = [len(encoder.encode_ordinary(primary + "\n\n" + passage(token["source_id"], pins["closure.md"])))]
            if case == "duplicate":
                # The earlier original-packer query supplies the omitted copy's pin.
                copy_pin = results.get(surface + "/copy-pin", {})
                if packing == "original":
                    copy_pin = next(p for p in evidence if p["item"] == "copy.md")
                associated_ids.append(copy_pin["segment_id"])
                proposed.append(None if packing == "exact-v1" else count)
            equal(token["associations"]["associated_ids"], associated_ids, "associated-identity-alignment")
            equal(token["associations"]["proposed_tokens"], proposed, "associated-proposed-count")
            if case == "duplicate" and packing == "exact-v1":
                equal(result["association_omissions"], [dict(from_item="backup.md", to_item="copy.md", reason="duplicate",
                      segment_id=associated_ids[1])], "associated-duplicate-omission")
            if case == "exact":
                equal(result["context"], full["context"], "exact-fit-context")
            if surface == "mcp":
                native = results["jsonl/" + packing + "/full"]
                equal(token["source_id"], native["token"]["source_id"], "configured-source-binding")
    references.append(dict(label=label, tokens=count, bytes=len(context.encode()), sha256=wire.sha(context.encode())))


def history_check(result, event, results):
    surface, packing, suffix = event["label"].split("/")
    producing = results[surface + "/" + packing + "/exact"]
    history = result["historical"]
    equal([history["id"], history["request_id"], history["decision_id"], history["packet_id"]],
          [producing["trail_id"], producing["request_id"], producing["decision_id"], producing["packet_id"]], "historical-producing-identity")
    equal(history["schema"], "mousa.source_trail.v11", "historical-version")
    check(result["authorization_decision_id"] != producing["decision_id"], "fresh-history-authorization")
    with_tokens = surface != "mcp" or suffix == "history-token"
    equal(history.get("token"), producing["token"] if with_tokens else None, "independent-token-opt-in")
    equal(len(history["candidates"]), 1, "historical-primary-count")
    equal(len(history["associated"]), 1, "historical-associated-count")
    row = history["associated"][0]
    equal([row["segment_id"], row["selected"], row["text_bytes"]],
          [producing["evidence"][1]["segment_id"], True, len(FIXTURE["closure.md"].encode())], "historical-associated-selection")
    for key, value in DECLARATION.items():
        equal(row[key], value, "historical-declaration")
    check("rank" not in row and "bm25_score" not in row, "history-no-associated-rank")
    if surface != "mcp":
        equal(history["token_verification"], "official_recount_verified" if suffix == "recount" else
              "retained_digest_verified_count_recorded", "native-history-verification")
    else:
        check("token_verification" not in history, "no-mcp-recount")


def verify(report, encoder):
    protocol = json.loads((ROOT / "protocol.json").read_text())
    equal(protocol["runner_sha256"], wire.sha(Path(__file__).read_bytes()), "frozen-runner")
    equal(report["runner_sha256"], protocol["runner_sha256"], "runner-binding")
    equal(report["protocol_sha256"], wire.sha((ROOT / "protocol.json").read_bytes()), "protocol-binding")
    equal([report["product"]["head"], report["product"]["tree"]],
          [protocol["product_head"], protocol["product_tree"]], "exact-product-binding")
    equal([protocol["fixture"], protocol["declaration"]], [FIXTURE, DECLARATION], "frozen-inputs")
    helpers = {name: wire.sha((ROOT.parent / name).read_bytes()) for name in
               ("mcp-tokens/capture.py", "mcp-retrieval/capture.py", "mcp-trail-supersession/run.py")}
    equal(protocol["helpers"], helpers, "frozen-helper-implementations")
    equal(len(report["events"]), len(schedule({}, encoder)), "complete-schedule")
    results, references, catalog = {}, [], None
    counts = dict(native=0, requests=0, responses=0, process_exits=0)
    for index, event in enumerate(report["events"]):
        planned = schedule(results, encoder)[index]
        for key, value in planned.items():
            equal(event.get(key), value, "scheduled-" + key)
        kind, label = event["kind"], event["label"]
        if kind in ("native", "start"):
            equal(event["argv"], ["BINARY", "-store", "STORE", *planned["arguments"]], "scheduled-argv")
        if kind == "start":
            continue
        if kind == "stop":
            equal([event["exit"], event["stdout_tail"], event["stderr"]],
                  [0, wire.stream(b""), wire.stream(b"")], "clean-shutdown")
            counts["process_exits"] += 1
            continue
        if kind == "rpc":
            counts["requests"] += 1
            request = dict(jsonrpc="2.0", method=event["method"], params=event["params"])
            if event["method"] != "notifications/initialized":
                request["id"] = index + 1
                equal(event["id"], index + 1, "request-id")
            equal(event["request"], wire.stream(wire.encoded(request)), "scheduled-request-bytes")
            if event["method"] == "notifications/initialized":
                check("response" not in event, "notification-no-response")
                continue
            counts["responses"] += 1
        else:
            counts["native"] += 1
        result = result_from(event)
        if result is None:
            continue
        if kind == "rpc":
            if event["method"] == "initialize":
                equal(result["protocolVersion"], "2025-11-25", "protocol-version")
                continue
            if event["method"] == "tools/list":
                found = {t["name"]: t for t in result["tools"]}
                equal(len(found), 8, "discovered-tools")
                equal(found, catalog if catalog is not None else found, "restart-discovery")
                catalog = found
                for name in ("mousa_vector_query", "mousa_hybrid_query"):
                    description = found[name]["inputSchema"]["properties"]["supersession"]["description"]
                    check("byte and measured token budgets" in description and "byte budgets only" not in description, "issue96-discovery")
                continue
            envelope = result["structuredContent"]
            equal(shared.parsed(wire.stream(result["content"][0]["text"].encode())), envelope, "text-structured-equality")
            name = event["params"]["name"]
            check(not wire.schema_violations(catalog[name]["outputSchema"], envelope), "closed-output-schema")
            equal([envelope["schema"], envelope["operation"]], ["mousa.mcp_result.v1", name], "tool-envelope-binding")
            if label.startswith("refusal/"):
                equal([result.get("isError"), envelope["error"]["code"]], [True, "invalid_arguments"], "precise-refusal")
                check("result" not in envelope, "refusal-no-success")
                if name != "mousa_query":
                    schema = catalog[name]["inputSchema"]
                    arguments = dict(event["params"]["arguments"])
                    arguments.pop("associations")
                    check("associations" not in schema["properties"], "semantic-associations-unsupported")
                    check(not wire.schema_violations(schema, arguments), "other-refusal-arguments-valid")
                continue
            check(not result.get("isError", False) and "error" not in envelope, "tool-success")
            equal(envelope["source"], SOURCE, "configured-source")
            result = envelope["result"]
        if "context" in result:
            query_check(result, label, results, encoder, references)
        if label == "mcp/denied-history":
            equal(result["authorization_outcome"], "deny", "fresh-history-denial")
            check("historical" not in result, "denied-history-no-payload")
        elif "historical" in result:
            history_check(result, event, results)
        if label.endswith("/deny-access"):
            shared.identities(result)
            equal([result["effect"], result["changed"]], ["deny", True], "access-denial-activation")
            equal(result["source"], str(DIRECTORY) if label.startswith("directory/") else SOURCE, "access-source")
        if label.endswith("/ordinary"):
            check(result["token"]["candidate_ids"], "ordinary-primary-identity")
        if label.endswith("/original/duplicate"):
            results[label.split("/")[0] + "/copy-pin"] = result["evidence"][2]
        results[label] = result
    return dict(result="PASS", product=report["product"], events=len(report["events"]), **counts,
                reference_counts=references, limits="Synthetic protocol/counting only. No semantic sufficiency, authenticated authorship, performance or full model-window guarantee; product-local graph/corruption/snapshot/fault cases are separate.")


def capture(args, encoder):
    def git(*argv):
        return subprocess.check_output(["git", "-C", str(args.product_source), *argv], text=True, timeout=30).strip()
    equal(git("rev-parse", "HEAD"), args.product_head, "exact-public-head")
    equal(git("status", "--porcelain"), "", "clean-public-source")
    args.output.mkdir(parents=True, exist_ok=False)
    DIRECTORY.mkdir(exist_ok=False)
    report = dict(product=dict(head=args.product_head, tree=git("rev-parse", "HEAD^{tree}"),
        binary_sha256=wire.sha(args.mousa.read_bytes()), build="GOWORK=off CGO_ENABLED=0 go build -o BINARY ./cmd/mousa"),
        runner_sha256=wire.sha(Path(__file__).read_bytes()), protocol_sha256=wire.sha((ROOT / "protocol.json").read_bytes()), events=[])
    results, process, actual_argv = {}, None, []
    with tempfile.TemporaryDirectory(prefix="mousa-public-token-associations-") as temporary:
        root = Path(temporary)
        substitutions = dict(TOKEN_PY=str(args.python.absolute()), TOKEN_CACHE=str(args.cache.absolute()), DIRECTORY=str(DIRECTORY))
        for name, value in FIXTURE.items():
            (DIRECTORY / name).write_text(value, encoding="utf-8")
        for name, value in (("DECLARATIONS", document(DECLARATION)),
                ("DUPLICATES", document(DECLARATION, dict(DECLARATION, to_item="copy.md"))),
                ("UNFIRED", document(dict(DECLARATION, from_item="unselected")))):
            path = root / (name + ".json")
            path.write_text(wire.canonical(value), encoding="utf-8")
            substitutions[name] = str(path)
        store = str(root / "evidence.sqlite")
        try:
            for index in range(len(schedule(results, encoder))):
                event = copy.deepcopy(schedule(results, encoder)[index])
                report["events"].append(event)
                kind, label = event["kind"], event["label"]
                if kind in ("native", "start"):
                    argv = [str(args.mousa.absolute()), "-store", store,
                            *[substitutions.get(a, a) for a in event["arguments"]]]
                    event["argv"] = ["BINARY", "-store", "STORE", *event["arguments"]]
                    actual_argv.append(dict(label=label, argv=argv))
                    wire.save(args.output / "private-argv.json", actual_argv)
                if kind == "native":
                    completed = subprocess.run(argv, input=event["stdin"].encode(), capture_output=True, timeout=30)
                    event.update(stdout=wire.stream(completed.stdout), stderr=wire.stream(completed.stderr), exit=completed.returncode)
                    result = result_from(event)
                    if result is not None:
                        results[label] = result
                        if label.endswith("/original/duplicate"):
                            results[label.split("/")[0] + "/copy-pin"] = result["evidence"][2]
                elif kind == "start":
                    errors = tempfile.TemporaryFile()
                    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors)
                    reader = wire.LineReader(process.stdout.fileno())
                elif kind == "stop":
                    process.stdin.close()
                    event["exit"] = process.wait(timeout=30)
                    event["stdout_tail"] = wire.stream(reader.buffer + process.stdout.read())
                    process.stdout.close()
                    errors.seek(0)
                    event["stderr"] = wire.stream(errors.read())
                    errors.close()
                    process = None
                else:
                    message = dict(jsonrpc="2.0", method=event["method"], params=event["params"])
                    if event["method"] != "notifications/initialized":
                        event["id"] = index + 1
                        message["id"] = index + 1
                    data = wire.encoded(message)
                    event["request"] = wire.stream(data)
                    process.stdin.write(data)
                    process.stdin.flush()
                    if "id" in message:
                        event["response"] = wire.stream(shared.read_frame(reader))
                        response = result_from(event)
                        if event["method"] == "tools/call" and "result" in response.get("structuredContent", {}):
                            result = response["structuredContent"]["result"]
                            results[label] = result
                            if label.endswith("/original/duplicate"):
                                results[label.split("/")[0] + "/copy-pin"] = result["evidence"][2]
                wire.save(args.output / "capture.json", report)
        finally:
            if process is not None:
                process.kill()
                exit_code = process.wait()
                errors.seek(0)
                report["aborted_process"] = dict(exit=exit_code, stderr=wire.stream(errors.read()),
                    stdout_tail=wire.stream(reader.buffer + process.stdout.read()))
                process.stdout.close()
                errors.close()
            shutil.rmtree(DIRECTORY)
            wire.save(args.output / "capture.json", report)
    summary = verify(report, encoder)
    wire.save(args.output / "summary.json", summary)
    print(json.dumps(summary))


def controls(report, encoder):
    receipts = []
    for name, detector in (("request", "scheduled-request-bytes"),
            ("proposed-count", "associated-proposed-count"), ("provenance", "association-provenance")):
        changed = copy.deepcopy(report)
        event = next(e for e in changed["events"] if e["label"] == "mcp/original/exact")
        if name == "request":
            request = shared.parsed(event["request"])
            request["params"]["arguments"]["associations"]["associations"][0]["to_item"] = "copy.md"
            event["request"] = wire.stream(wire.encoded(request))
        else:
            response = shared.parsed(event["response"])
            payload = response["result"]
            result = payload["structuredContent"]["result"]
            if name == "proposed-count":
                result["token"]["associations"]["proposed_tokens"][0] += 1
            else:
                result["evidence"][1]["association"]["author"] = "changed attribution"
            payload["content"][0]["text"] = wire.canonical(payload["structuredContent"])
            event["response"] = wire.stream(wire.encoded(response))
        try:
            verify(changed, encoder)
        except ValueError as error:
            equal(str(error), detector, "intended-control-detector")
            receipts.append(dict(control=name, result="PASS", detector=str(error),
                                 rehashed_capture_sha256=wire.sha(wire.encoded(changed))))
        else:
            raise ValueError("negative-control-accepted")
    return receipts


def comparison_rows(report):
    rows = []
    for event in report["events"]:
        if event["kind"] in ("start", "stop") or event.get("method") == "notifications/initialized":
            continue
        value = result_from(event)
        if value is None:
            continue
        if event["kind"] == "rpc" and event["method"] == "tools/call":
            value = value["structuredContent"]
            if "result" in value:
                value = value["result"]
        value = copy.deepcopy(value)
        for key in ("request_id", "decision_id", "trail_id", "authorization_decision_id", "evaluated_at_usec",
                    "elapsed_seconds", "latency_micros", "store_bytes"):
            value.pop(key, None)
        if event["label"].endswith("/deny-access"):
            value.pop("activation_id", None)
        if "historical" in value:
            for key in ("id", "request_id", "decision_id"):
                value["historical"].pop(key, None)
        rows.append(dict(label=event["label"], result=value))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "verify", "controls", "compare"))
    for name in ("mousa", "product-source", "python", "cache", "output", "other"):
        parser.add_argument("--" + name, type=Path, required=name in ("cache", "output"))
    parser.add_argument("--product-head")
    args = parser.parse_args()
    encoder = tokens.ordinary_encoder(args.cache)
    if args.mode == "capture":
        capture(args, encoder)
        return
    report = json.loads((args.output / "capture.json").read_text())
    summary = verify(report, encoder)
    equal(json.loads((args.output / "summary.json").read_text()), summary, "summary-binding")
    if args.mode == "controls":
        result = controls(report, encoder)
    elif args.mode == "compare":
        other = json.loads((args.other / "capture.json").read_text())
        verify(other, encoder)
        left, right = comparison_rows(report), comparison_rows(other)
        equal(left, right, "fresh-store-stable-results")
        result = dict(result="PASS", compared_rows=len(left), packet_identities_retained=True,
            exclusions="Per-call request/decision/trail/authorization identities and evaluation/elapsed/latency time, sync store_bytes; historical id/request/decision; access activation_id. Raw producing identities remain bound within each run.")
    else:
        result = summary
    print(json.dumps(result))


if __name__ == "__main__":
    main()
