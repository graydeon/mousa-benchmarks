"""Capture byte-only vector/hybrid supersession through public native/MCP clients."""
import argparse
import copy
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("composition", ROOT.parent / "token-supersession/capture.py")
composition = importlib.util.module_from_spec(spec)
spec.loader.exec_module(composition)
shared, wire = composition.shared, composition.wire
check, equal = shared.check, shared.equal
SOURCE = "synthetic-vector-supersession"
FIXTURE = {"old.md": "Drain legacy", "twin.md": "Drain legacy",
           "new.md": "Separate correction", "peer.md": "Radishes prefer damp soil."}
VALUES = {"old.md": [1, 0], "twin.md": [0, 1], "peer.md": [0.8, 0.6]}


def schedule(results):
    events = []

    def native(label, args, value=""):
        events.append(dict(kind="native", label=label, arguments=args, stdin=value))

    def rpc(label, method, params):
        events.append(dict(kind="rpc", label=label, method=method, params=params))

    def tool(label, name, **args):
        rpc(label, "tools/call", dict(name=name, arguments=dict(source=SOURCE, **args)))

    def start(label):
        events.append(dict(kind="start", label=label, arguments=["mcp", "--caller", "cli", "--source", SOURCE]))
        rpc(label + "/initialize", "initialize", dict(protocolVersion="2025-11-25", capabilities={},
            clientInfo=dict(name="mousa-vector-supersession-capture", version="1")))
        rpc(label + "/initialized", "notifications/initialized", {})
        rpc(label + "/discovery", "tools/list", {})

    native("sync", ["sync", "--source", SOURCE], "".join(wire.encoded(dict(id=k, text=v)).decode() for k, v in FIXTURE.items()))
    native("export", ["vector", "inputs", "--source", SOURCE])
    exported = results.get("export", {})
    supplied = dict(schema="mousa.vector_import.v1", space=dict(schema="mousa.vector_space.v1", provider="synthetic",
        model="arithmetic-only", version="1", dimensions=2, metric="cosine"), embeddings=[
        dict(**{k: p[k] for k in shared.PINS}, values=VALUES[p["item"]])
        for p in exported.get("passages", []) if p["item"] in VALUES])
    native("import", ["vector", "import", "--source", SOURCE], wire.encoded(supplied).decode())
    declaration, active = composition.administration(exported)
    native("declaration", ["supersession", "declaration", "put"], wire.encoded(declaration).decode())
    native("activation", ["supersession", "activation", "put"], wire.encoded(active).decode())
    space = results.get("import", {}).get("space_id", "PENDING")
    query_vector = wire.encoded(dict(schema="mousa.vector_query.v1", values=[1, 0])).decode()
    for mode in ("vector", "hybrid"):
        for packing in ("original", "exact-v1"):
            prefix = "native/" + mode + "/" + packing
            for opt in ("default", "false", "true"):
                args = ["query", "--" + mode + "-space", space, "--packing-policy", packing, "--budget-bytes", "12"]
                if opt != "default":
                    args += ["--supersession=" + opt]
                args += ["--source", SOURCE]
                if mode == "hybrid":
                    args += ["Drain"]
                native(prefix + "/" + opt, args, query_vector)
            native(prefix + "/history", ["trail", "--source", SOURCE, results.get(prefix + "/true", {}).get("trail_id", "PENDING")])
    start("mcp")
    for mode in ("vector", "hybrid"):
        for packing in ("original", "exact-v1"):
            prefix = "mcp/" + mode + "/" + packing
            args = dict(space_id=space, values=[1, 0], budget_bytes=12, packing_policy=packing)
            if mode == "hybrid":
                args.update(query="Drain", policy="original")
            for opt in ("default", "false", "true"):
                query = dict(args)
                if opt != "default":
                    query["supersession"] = opt == "true"
                tool(prefix + "/" + opt, "mousa_" + mode + "_query", **query)
            for sup, details in ((False, False), (True, False), (False, True), (True, True)):
                tool(prefix + "/history-" + str(sup) + "-" + str(details), "mousa_trail",
                     trail_id=results.get(prefix + "/true", {}).get("trail_id", "PENDING"),
                     supersession=sup, retrieval_details=details)
    events.append(dict(kind="stop", label="mcp/stop"))
    native("successor-unavailable", ["sync", "--source", SOURCE], '{"id":"new.md","deleted":true}\n')
    start("unavailable")
    for mode in ("vector", "hybrid"):
        for packing in ("original", "exact-v1"):
            prefix = "unavailable/" + mode + "/" + packing
            args = dict(space_id=space, values=[1, 0], budget_bytes=12, packing_policy=packing, supersession=True)
            if mode == "hybrid":
                args.update(query="Drain", policy="original")
            tool(prefix + "/true", "mousa_" + mode + "_query", **args)
            tool(prefix + "/old-history", "mousa_trail", trail_id=results.get("mcp/" + mode + "/" + packing + "/true", {}).get("trail_id", "PENDING"), supersession=True, retrieval_details=True)
    events.append(dict(kind="stop", label="unavailable/stop"))
    _, inactive = composition.administration(exported, active["id"], False, 2)
    native("deactivate", ["supersession", "activation", "put"], wire.encoded(inactive).decode())
    for mode in ("vector", "hybrid"):
        prefix = "native/" + mode + "/original"
        native("deactivated/" + mode + "/old-history", ["trail", "--source", SOURCE, results.get(prefix + "/true", {}).get("trail_id", "PENDING")])
    return events


def producing_order(mode, pins):
    vectors = sorted(VALUES, key=lambda name: (-VALUES[name][0], pins[name]["segment_id"]))
    if mode == "vector":
        return vectors, {}, {name: i + 1 for i, name in enumerate(vectors)}
    lexical = sorted(("old.md", "twin.md"), key=lambda name: pins[name]["segment_id"])
    lr = {name: i + 1 for i, name in enumerate(lexical)}
    vr = {name: i + 1 for i, name in enumerate(vectors)}
    fused = sorted(vectors, key=lambda name: (-sum(Fraction(1, 60 + r) for r in (lr.get(name), vr.get(name)) if r), pins[name]["segment_id"]))
    return fused, lr, vr


def query_check(result, label, results):
    parts = label.split("/")
    mode, packing, opt = parts[1:]
    pins = {p["item"]: p for p in results["export"]["passages"]}
    order, lr, vr = producing_order(mode, pins)
    equal(order[0], "old.md", "fixture-predecessor-wins")
    expected = "twin.md" if opt == "true" else "old.md"
    equal([p["item"] for p in result["evidence"]], [expected], "selected-evidence")
    p = result["evidence"][0]
    equal(p["text"], FIXTURE[expected], "selected-text")
    for key in shared.PINS:
        equal(p[key], pins[expected][key], "selected-pin-" + key)
    equal(p["byte_start"], 0, "selected-start")
    equal(p["byte_end"], 12, "selected-end")
    equal(p["rank"], order.index(expected) + 1, "producing-rank")
    equal(result["used_bytes"], 12, "released-bytes")
    equal(result["budget_bytes"], 12, "requested-byte-budget")
    equal(result["outcome"], "evidence", "query-outcome")
    equal(result["packing_policy"], packing, "packing-policy")
    equal(result.get("supersession_excluded"), 1 if opt == "true" else None, "withheld-count")
    if mode == "vector" or parts[0] != "native":
        equal([result["eligible"], result["indexed"], result["missing"]], [3 if parts[0] == "unavailable" else 4, 3, 0 if parts[0] == "unavailable" else 1], "coverage-before-mask")
    if mode == "hybrid" or parts[0] != "native":
        facts = result[mode]
        equal([c["segment_id"] for c in facts["candidates"]], [pins[n]["segment_id"] for n in order], "full-producing-population")
        equal([facts["eligible"], facts["indexed"]], [3 if parts[0] == "unavailable" else 4, 3], "recorded-coverage")
        for name, c in zip(order, facts["candidates"]):
            if mode == "hybrid":
                equal(c.get("lexical", {}).get("rank"), lr.get(name), "lexical-branch-rank")
                equal(c["vector"]["rank"], vr[name], "vector-branch-rank")
                expected_rrf = sum(Fraction(1, 60 + rank) for rank in (lr.get(name), vr[name]) if rank)
                check(abs(c["rrf"] - float(expected_rrf)) <= 1e-16, "RRF-k60")
                equal(c["vector"]["cosine"], VALUES[name][0], "producing-cosine")
            else:
                equal(c["cosine"], VALUES[name][0], "producing-cosine")
        baseline = results.get("mcp/" + mode + "/" + packing + "/default")
        if opt != "default" and baseline and parts[0] != "unavailable":
            equal(facts, baseline[mode], "ranking-not-rerun")
    if opt == "false":
        default = results[label.rsplit("/", 1)[0] + "/default"]
        equal(result["packet_id"], default["packet_id"], "false-packet")
        equal(result["evidence"], default["evidence"], "false-evidence")


def history_check(result, event, results):
    label = event["label"]
    parts = label.split("/")
    mode = parts[1]
    packing = parts[2] if parts[0] != "deactivated" else "original"
    surface = "mcp" if parts[0] == "unavailable" else "native" if parts[0] == "deactivated" else parts[0]
    produced = results[surface + "/" + mode + "/" + packing + "/true"]
    h = result["historical"]
    equal(h["id"], produced["trail_id"], "historical-id")
    equal(h["decision_id"], produced["decision_id"], "historical-decision")
    equal(h["packet_id"], produced["packet_id"], "historical-packet")
    equal(h["schema"], "mousa.source_trail.v9", "historical-version")
    args = event.get("params", {}).get("arguments", {})
    sup = event["kind"] == "native" or args.get("supersession", False)
    details = event["kind"] == "native" or args.get("retrieval_details", False)
    equal("supersession" in h, sup, "supersession-history-opt-in")
    equal(mode in h, details, "retrieval-history-opt-in")
    declaration, activation = composition.administration(results["export"])
    if sup:
        s = h["supersession"]
        equal([s["consulted"], s["activation_id"], s["declaration_id"]], [True, activation["id"], declaration["id"]], "recorded-consultation")
        equal(len(s["dispositions"]), 1, "recorded-withheld-count")
        row = s["dispositions"][0]
        for key in ("predecessor_item_id", "predecessor_representation_id", "successor_item_id", "successor_representation_id"):
            equal(row[key], declaration[key], "recorded-declaration-pin")
        candidate = next(c for c in h["candidates"] if c["segment_id"] == row["segment_id"])
        equal([candidate["rank"], candidate["text_bytes"], candidate["selected"]], [1, 12, False], "withheld-historical-facts")
    if details and (surface == "mcp" or mode == "hybrid"):
        equal(h[mode], produced[mode], "recorded-producing-facts")
    if details:
        pins = {p["item"]: p for p in results["export"]["passages"]}
        order, _, _ = producing_order(mode, pins)
        equal([c["segment_id"] for c in h[mode]["candidates"]], [pins[n]["segment_id"] for n in order], "historical-full-population")
        equal([h[mode]["eligible"], h[mode]["indexed"]], [4, 3], "historical-producing-coverage")
        equal(len(h["candidates"]), 3, "historical-candidate-population")
        for name, row in zip(order, h["candidates"]):
            equal(row["segment_id"], pins[name]["segment_id"], "historical-candidate-pin")
            equal(row["text_bytes"], len(FIXTURE[name].encode()), "historical-canonical-size")
            equal(row["selected"], name == "twin.md", "historical-selected-survivor")


def verify(report):
    equal(report["runner_sha256"], wire.sha(Path(__file__).read_bytes()), "runner-binding")
    check(len(report["product"]["head"]) == 40 and len(report["product"]["tree"]) == 40, "product-binding")
    equal(len(report["events"]), len(schedule({})), "complete-schedule")
    results, catalog = {}, None
    for i, event in enumerate(report["events"]):
        planned = schedule(results)[i]
        for key, value in planned.items():
            equal(event.get(key), value, "scheduled-" + key)
        kind, label = event["kind"], event["label"]
        if kind == "start":
            continue
        if kind == "stop":
            equal([event["exit"], event["stdout_tail"], event["stderr"]], [0, wire.stream(b""), wire.stream(b"")], "clean-mcp-shutdown")
            continue
        if kind == "rpc":
            request = dict(jsonrpc="2.0", method=planned["method"], params=planned["params"])
            if planned["method"] != "notifications/initialized":
                request["id"] = i + 1
            equal(event["request"], wire.stream(wire.encoded(request)), "scheduled-request-bytes")
            if planned["method"] == "notifications/initialized":
                check("response" not in event, "notification-no-response")
                continue
        result = composition.result_from(event)
        if kind == "rpc":
            if event["method"] == "initialize":
                equal(result["protocolVersion"], "2025-11-25", "protocol-version")
                continue
            if event["method"] == "tools/list":
                found = {t["name"]: t for t in result["tools"]}
                equal(len(found), 8, "discovered-tools")
                if catalog is not None:
                    equal(found, catalog, "restart-discovery")
                catalog = found
                for mode in ("vector", "hybrid"):
                    equal(found["mousa_" + mode + "_query"]["inputSchema"]["properties"]["supersession"]["type"], "boolean", "declared-boolean")
                continue
            envelope = result["structuredContent"]
            check(not result.get("isError", False), "tool-success")
            equal(json.loads(result["content"][0]["text"]), envelope, "text-structured-equality")
            check(not wire.schema_violations(catalog[event["params"]["name"]]["outputSchema"], envelope), "closed-output-schema")
            equal([envelope["schema"], envelope["operation"], envelope["source"]], ["mousa.mcp_result.v1", event["params"]["name"], SOURCE], "envelope-binding")
            result = envelope["result"]
        if label == "export":
            equal({p["item"]: p["text"] for p in result["passages"]}, FIXTURE, "exported-fixture")
            for p in result["passages"]:
                equal(p["content_sha256"], wire.sha(p["text"].encode()), "export-digest")
                shared.identities({k: p[k] for k in shared.PINS})
        if kind == "native" and event["arguments"][0] == "supersession":
            equal(result, json.loads(event["stdin"]), "administration-readback")
        if "evidence" in result:
            query_check(result, label, results)
        if "historical" in result:
            history_check(result, event, results)
        results[label] = result
    return dict(result="PASS", product=report["product"], events=len(report["events"]),
                limits="Synthetic public-client protocol/arithmetic only; no SQLite access, model, semantic-quality, performance or historical old-text reconstruction claim.")


def capture(args):
    def git(*argv):
        return subprocess.check_output(["git", "-C", str(args.product_source), *argv], text=True, timeout=30).strip()
    equal(git("rev-parse", "HEAD"), args.product_head, "exact-public-head")
    equal(git("status", "--porcelain"), "", "clean-public-source")
    args.output.mkdir(parents=True, exist_ok=False)
    report = dict(product=dict(head=args.product_head, tree=git("rev-parse", "HEAD^{tree}"),
        binary_sha256=wire.sha(args.mousa.read_bytes()), build="GOWORK=off CGO_ENABLED=0 go build -o BINARY ./cmd/mousa"),
        runner_sha256=wire.sha(Path(__file__).read_bytes()), events=[])
    results, process = {}, None
    with tempfile.TemporaryDirectory(prefix="mousa-public-vector-supersession-") as temporary:
        store = str(Path(temporary) / "evidence.sqlite")
        try:
            for i in range(len(schedule(results))):
                event = copy.deepcopy(schedule(results)[i])
                report["events"].append(event)
                kind, label = event["kind"], event["label"]
                if kind == "native":
                    r = subprocess.run([str(args.mousa), "-store", store, *event["arguments"]], input=event["stdin"].encode(), capture_output=True, timeout=30)
                    event.update(stdout=wire.stream(r.stdout), stderr=wire.stream(r.stderr), exit=r.returncode)
                    results[label] = composition.result_from(event)
                elif kind == "start":
                    errors = tempfile.TemporaryFile()
                    process = subprocess.Popen([str(args.mousa), "-store", store, *event["arguments"]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors)
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
                        message["id"] = i + 1
                        event["id"] = i + 1
                    data = wire.encoded(message)
                    event["request"] = wire.stream(data)
                    process.stdin.write(data)
                    process.stdin.flush()
                    if "id" in message:
                        event["response"] = wire.stream(shared.read_frame(reader))
                        result = composition.result_from(event)
                        if event["method"] == "tools/call":
                            results[label] = result["structuredContent"]["result"]
                wire.save(args.output / "capture.json", report)
        finally:
            if process is not None:
                process.kill()
                process.wait()
                errors.close()
            wire.save(args.output / "capture.json", report)
    summary = verify(report)
    wire.save(args.output / "summary.json", summary)
    print(json.dumps(summary))


def controls(report):
    receipts = []
    for name, label, detector in (("changed-request", "mcp/vector/original/true", "scheduled-request-bytes"),
                                  ("wrong-count", "mcp/vector/original/true", "withheld-count"),
                                  ("wrong-selection", "mcp/hybrid/exact-v1/true", "selected-evidence"),
                                  ("wrong-history", "mcp/vector/original/history-True-True", "withheld-historical-facts")):
        changed = copy.deepcopy(report)
        event = next(e for e in changed["events"] if e["label"] == label)
        if name == "changed-request":
            request = shared.parsed(event["request"])
            request["params"]["arguments"]["supersession"] = False
            event["request"] = wire.stream(wire.encoded(request))
        else:
            response = shared.parsed(event["response"])
            payload = response["result"]
            result = payload["structuredContent"]["result"]
            if name == "wrong-count":
                result["supersession_excluded"] = 0
            elif name == "wrong-selection":
                result["evidence"][0]["item"] = "old.md"
            else:
                h = result["historical"]
                sid = h["supersession"]["dispositions"][0]["segment_id"]
                next(c for c in h["candidates"] if c["segment_id"] == sid)["selected"] = True
            payload["content"][0]["text"] = wire.canonical(payload["structuredContent"])
            event["response"] = wire.stream(wire.encoded(response))
        try:
            verify(changed)
        except ValueError as error:
            equal(str(error), detector, "intended-control-detector")
            receipts.append(dict(control=name, result="PASS", detector=str(error), rehashed_capture_sha256=wire.sha(wire.encoded(changed))))
        else:
            raise ValueError("negative-control-accepted")
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "verify", "controls"))
    for name in ("mousa", "product-source", "output"):
        parser.add_argument("--" + name, type=Path, required=name == "output")
    parser.add_argument("--product-head")
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
