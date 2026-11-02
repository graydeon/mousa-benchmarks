"""Capture/replay byte-only lexical support with explicit supersession, without SQL or models."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT.parent / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shared = load("retrieval_capture", "mcp-retrieval/capture.py")
identity = load("directory_capture", "directory-supersession/capture.py").identity
wire, check, equal = shared.wire, shared.check, shared.equal
SOURCE = "synthetic-composed-support"
DIRECTORY = "/tmp/mousa-public-composed-notes"
FIXTURE = {"old": "needle obsolete qualification", "primary": "needle retained instruction",
           "twin": "needle obsolete qualification", "support": "Nonmatching caller-declared qualification.",
           "new": "Explicit replacement attribution."}


def document(suffix):
    return dict(schema="mousa.association_declarations.v1", associations=[
        dict(from_item="primary" + suffix, to_item=item + suffix,
             basis="Caller-declared qualification, not semantic sufficiency", author="example.maintainer")
        for item in ("old", "twin", "support")] + [dict(from_item="old" + suffix,
        to_item="new" + suffix, basis="Withheld primary cannot fire", author="example.maintainer")])


def facts(result, pins, suffix, expression):
    equal(result["decision_outcome"], "allow", "query-authorization")
    equal(result["outcome"], "evidence", "query-outcome")
    equal(result["supersession_excluded"], 1 if expression == "needle" else 0, "primary-suppression-binding")
    evidence = result["evidence"]
    lexical = [p for p in evidence if p["origin"] == "lexical"]
    expected_primary = {"primary" + suffix, "twin" + suffix} if expression == "needle" else {"primary" + suffix}
    equal(sorted(p["item"] for p in lexical), sorted(expected_primary), "primary-selection-binding")
    expected_support = ["support" + suffix] if expression == "needle" else ["twin" + suffix, "support" + suffix]
    equal([p["item"] for p in evidence[len(lexical):]], expected_support, "support-selection-binding")
    equal(len(evidence), len(expected_primary) + len(expected_support), "complete-selected-population")
    for passage in evidence:
        item = passage["item"]
        text = FIXTURE[item.removesuffix(suffix) if suffix else item]
        equal([passage["text"], passage["content_sha256"], passage["representation_sha256"],
               passage["byte_start"], passage["byte_end"], passage["byte_length"]],
              [text, wire.sha(text.encode()), wire.sha(text.encode()), 0, len(text.encode()), len(text.encode())],
              "evidence-content-binding")
        equal([passage["segment_id"], passage["representation_id"]],
              [pins[item]["segment_id"], pins[item]["representation_id"]], "evidence-pin-binding")
        if passage["origin"] == "association":
            declaration = next(d for d in document(suffix)["associations"] if d["to_item"] == item)
            equal(passage["association"], declaration, "selected-attribution-binding")
            check("rank" not in passage and "bm25_score" not in passage, "support-not-lexical")
    equal(result["used_bytes"], sum(len(p["text"].encode()) for p in evidence), "retained-byte-accounting")
    omissions = [dict(from_item="primary" + suffix, to_item="old" + suffix,
                      reason="superseded", segment_id=pins["old" + suffix]["segment_id"])]
    if expression == "needle":
        omissions.append(dict(from_item="primary" + suffix, to_item="twin" + suffix,
                              reason="duplicate", segment_id=pins["twin" + suffix]["segment_id"]))
    equal(result["association_omissions"], omissions, "associated-suppression-binding")
    shared.identities({k: result[k] for k in ("request_id", "decision_id", "trail_id", "packet_id")})


def history_facts(result, query, pins, declaration, activation, suffix, expression, opted=True):
    equal(result["authorization_outcome"], "allow", "history-authorization")
    check(result["authorization_decision_id"] != query["decision_id"], "fresh-history-decision")
    h = result["historical"]
    equal([h["id"], h["request_id"], h["decision_id"], h["packet_id"]],
          [query["trail_id"], query["request_id"], query["decision_id"], query["packet_id"]], "producing-history-binding")
    equal(h["schema"], "mousa.source_trail.v12", "composed-version")
    if opted:
        dispositions = []
        if expression == "needle":
            dispositions = [dict(selection="superseded", segment_id=pins["old" + suffix]["segment_id"],
                content_sha256=pins["old" + suffix]["content_sha256"], declaration_id=declaration["id"],
                **{k: declaration[k] for k in ("predecessor_item_id", "predecessor_representation_id",
                                              "successor_item_id", "successor_representation_id")})]
        equal(h["supersession"], dict(consulted=True, activation_id=activation["id"],
              declaration_id=declaration["id"], dispositions=dispositions), "history-suppression-binding")
    else:
        check("supersession" not in h, "omitted-inspection-property-set")
    expected = []
    for index, item in enumerate(("old", "twin", "support")):
        d = document(suffix)["associations"][index]
        pin = pins[item + suffix]
        row = dict(segment_id=pin["segment_id"], content_sha256=pin["content_sha256"],
                   text_bytes=len(FIXTURE[item].encode()), selected=item != "old", indexed_now=True, **d)
        if item == "old":
            row["omission"] = "superseded"
        if item == "twin" and expression == "needle":
            row.update(selected=False, omission="duplicate", duplicate_of=pin["segment_id"])
        expected.append(row)
    equal(h["associated"], expected, "history-associated-selection-binding")
    check("association_omissions" not in h, "no-fabricated-target-omissions")


def stable(value):
    value = copy.deepcopy(value)
    for key in ("request_id", "decision_id", "trail_id", "evaluated_at_usec", "latency_micros", "authorization_decision_id"):
        value.pop(key, None)
    if "historical" in value:
        for key in ("id", "request_id", "decision_id"):
            value["historical"].pop(key, None)
    return value


def exercise(native, session, files):
    summaries, jsonl = [], None
    for form in ("jsonl", "directory"):
        suffix = ".txt" if form == "directory" else ""
        selector = [DIRECTORY] if suffix else ["--source", SOURCE]
        initial = "" if suffix else "".join(wire.encoded(dict(id=k, text=v)).decode() for k, v in FIXTURE.items())
        native(form + "/sync", ["sync", *selector], initial)
        exported = native(form + "/pins", ["vector", "inputs", *selector])
        equal(len(exported["passages"]), len(FIXTURE), "complete-exported-population")
        pins = {p["item"]: p for p in exported["passages"]}
        equal(sorted(pins), sorted(k + suffix for k in FIXTURE), "complete-pin-population")
        for item, text in FIXTURE.items():
            equal(pins[item + suffix]["text"], text, "exported-fixture-binding")
            pin = pins[item + suffix]
            equal([pin["content_sha256"], pin["representation_sha256"], pin["byte_start"], pin["byte_end"]],
                  [wire.sha(text.encode()), wire.sha(text.encode()), 0, len(text.encode())], "exported-content-binding")
            shared.identities({k: pin[k] for k in ("source_id", "segment_id", "representation_id")})
        old, new = "old" + suffix, "new" + suffix
        sid = pins[old]["source_id"]
        declaration = dict(schema="mousa.supersession_declaration.v1", source_id=sid,
            predecessor_item_id=old, predecessor_representation_id=pins[old]["representation_id"],
            successor_item_id=new, successor_representation_id=pins[new]["representation_id"],
            author="example.maintainer", basis="Explicit replacement, not inferred truth")
        declaration["id"] = identity(declaration["schema"], bytes.fromhex(sid), old,
            bytes.fromhex(declaration["predecessor_representation_id"]), new,
            bytes.fromhex(declaration["successor_representation_id"]), declaration["author"], declaration["basis"])
        equal(native(form + "/declaration", ["supersession", "declaration", "put"], wire.encoded(declaration).decode()), declaration, "declaration-binding")
        activation = dict(schema="mousa.supersession_activation.v1", source_id=sid,
            expected_previous_activation_id=None, declaration_id=declaration["id"], actor_id="example.maintainer",
            actor_version="1", occurred_at_usec=1, reason="Explicit replacement")
        activation["id"] = identity(activation["schema"], bytes.fromhex(sid), b"", bytes.fromhex(declaration["id"]))
        equal(native(form + "/activation", ["supersession", "activation", "put"], wire.encoded(activation).decode()), activation, "activation-binding")
        path = files(form, document(suffix))
        for packing in ("original", "exact-v1"):
            for expression in ("instruction", "needle"):
                label = form + "/" + packing + "/" + expression
                query = native(label, ["query", "--supersession", "--associations", path,
                    "--packing-policy", packing, *selector, expression])
                facts(query, pins, suffix, expression)
                history = native(label + "/history", ["trail", *selector, query["trail_id"]])
                history_facts(history, query, pins, declaration, activation, suffix, expression)
                summaries.append(dict(label=label, query=stable(query), history=stable(history)))
        if not suffix:
            jsonl = (pins, declaration, activation)
    summaries.extend(session(*jsonl))
    return summaries


def schedule(results):
    calls = [("initialize", "initialize", dict(protocolVersion="2025-11-25", capabilities={}, clientInfo=dict(name="mousa-composed-capture", version="1"))),
             ("initialized", "notifications/initialized", {}), ("discovery", "tools/list", {})]
    for packing in ("original", "exact-v1"):
        for expression in ("instruction", "needle"):
            label = packing + "/" + expression
            query = dict(source=SOURCE, query=expression, policy="original", budget_bytes=8192,
                         packing_policy=packing, supersession=True, associations=document(""))
            calls.append((label, "tools/call", dict(name="mousa_query", arguments=query)))
            calls.append((label + "/history", "tools/call", dict(name="mousa_trail", arguments=dict(
                source=SOURCE, trail_id=results.get(label, {}).get("trail_id", "PENDING"), supersession=True))))
    calls.append(("hidden-history", "tools/call", dict(name="mousa_trail", arguments=dict(
        source=SOURCE, trail_id=results.get("original/instruction", {}).get("trail_id", "PENDING")))))
    calls.append(("token-triple", "tools/call", dict(name="mousa_query", arguments=dict(source=SOURCE,
        query="instruction", policy="original", budget_bytes=8192, context_tokens=4096, supersession=True, associations=document("")))))
    return calls


def replay_session(session, pins, declaration, activation):
    equal(session["arguments"], ["mcp", "--caller", "cli", "--source", SOURCE], "mcp-startup")
    equal(session["exit"], 0, "mcp-exit")
    equal(session["stderr"], wire.stream(b""), "mcp-stderr")
    equal(session["stdout_tail"], wire.stream(b""), "mcp-tail")
    results, summaries, catalog = {}, [], None
    equal(len(session["frames"]), len(schedule(results)), "complete-mcp-population")
    for i, event in enumerate(session["frames"]):
        label, method, params = schedule(results)[i]
        equal(event["label"], label, "scheduled-label")
        message = dict(jsonrpc="2.0", method=method, params=params)
        if method != "notifications/initialized":
            message["id"] = i + 1
        equal(event["request"], wire.stream(wire.encoded(message)), "scheduled-request-bytes")
        equal(event["send_completed"], True, "complete-request-send")
        if method == "notifications/initialized":
            check("response" not in event, "notification-no-response")
            continue
        response = shared.parsed(event["response"])
        equal([response.get("id"), response.get("jsonrpc")], [i + 1, "2.0"], "rpc-request-binding")
        check("result" in response and "error" not in response, "rpc-success")
        payload = response["result"]
        if method == "initialize":
            equal(payload["protocolVersion"], "2025-11-25", "protocol-version")
            continue
        if method == "tools/list":
            catalog = {t["name"]: t for t in payload["tools"]}
            equal(len(payload["tools"]), 8, "complete-tool-population")
            equal(sorted(catalog), sorted(("mousa_sync", "mousa_status", "mousa_query", "mousa_trail",
                  "mousa_vector_inputs", "mousa_vector_import", "mousa_vector_query", "mousa_hybrid_query")), "existing-tool-population")
            continue
        tool = params["name"]
        envelope = payload["structuredContent"]
        check(not wire.schema_violations(catalog[tool]["outputSchema"], envelope), "closed-discovered-output")
        text, duplicates = wire.strict_json(payload["content"][0]["text"].encode())
        check(not duplicates, "strict-text-envelope")
        equal(text, envelope, "text-structured-equality")
        equal([envelope["schema"], envelope["operation"]], ["mousa.mcp_result.v1", tool], "tool-envelope")
        if label == "token-triple":
            equal(payload.get("isError"), True, "triple-refusal")
            equal(envelope["error"]["code"], "invalid_arguments", "triple-error-code")
            check("result" not in envelope, "refusal-no-result")
            continue
        equal(envelope["source"], SOURCE, "configured-source")
        check(not payload.get("isError", False) and "error" not in envelope, "tool-success")
        result = envelope["result"]
        results[label] = result
        if tool == "mousa_query":
            facts(result, pins, "", params["arguments"]["query"])
        else:
            producing = "original/instruction" if label == "hidden-history" else label.removesuffix("/history")
            history_facts(result, results[producing], pins, declaration, activation, "",
                          producing.split("/")[-1], label != "hidden-history")
        summaries.append(dict(label="mcp/" + label, result=stable(result)))
    return summaries


def protocol():
    frozen = json.loads((ROOT / "protocol.json").read_text())
    equal(frozen["runner_sha256"], wire.sha(Path(__file__).read_bytes()), "frozen-runner")
    for path, digest in frozen["helpers"].items():
        equal(wire.sha((ROOT.parent / path).read_bytes()), digest, "frozen-helper")
    equal(frozen["fixture"], FIXTURE, "frozen-fixture")
    return frozen


def verify(report):
    frozen = protocol()
    equal(report["protocol_sha256"], wire.sha((ROOT / "protocol.json").read_bytes()), "protocol-binding")
    equal([report["product"]["head"], report["product"]["tree"]], [frozen["product_head"], frozen["product_tree"]], "public-product-binding")
    wire.streams_valid(report)
    check(type(report["workspace"]) is str and re.fullmatch(r"/tmp/mousa-public-composed-[A-Za-z0-9_-]+", report["workspace"]), "workspace-form")
    equal(report["fixture"], FIXTURE, "complete-fixture-input")
    index, file_forms = 0, []

    def native(label, arguments, value=""):
        nonlocal index
        check(index < len(report["native"]), "missing-native-attempt")
        event = report["native"][index]
        index += 1
        equal([event["label"], event["arguments"]], [label, arguments], "native-schedule")
        equal(event["argv"], [report["product"]["binary_path"], "-store", report["workspace"] + "/evidence.sqlite", *arguments], "native-argv")
        equal(event["stdin"], wire.stream(value.encode()), "native-stdin-binding")
        equal(event["exit"], 0, "native-exit")
        equal(event["stderr"], wire.stream(b""), "native-stderr")
        return shared.parsed(event["stdout"])

    def files(form, doc):
        file_forms.append(form)
        equal(report["association_files"][form], wire.stream(wire.encoded(doc)), "association-file-binding")
        return report["workspace"] + "/" + form + "-associations.json"

    equal(len(report["sessions"]), 1, "complete-session-population")
    equal(report["sessions"][0]["argv"], [report["product"]["binary_path"], "-store", report["workspace"] + "/evidence.sqlite", "mcp", "--caller", "cli", "--source", SOURCE], "mcp-argv")
    summaries = exercise(native, lambda *pins: replay_session(report["sessions"][0], *pins), files)
    equal(index, len(report["native"]), "complete-native-population")
    equal(sorted(report["association_files"]), sorted(file_forms), "complete-association-file-population")
    equal(summaries, report["summary"], "summary-binding")
    return summaries


def capture(args):
    frozen = protocol()
    def git(*argv):
        return subprocess.check_output(["git", "-C", str(args.product_source), *argv], text=True, timeout=30).strip()
    equal([git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")], [frozen["product_head"], frozen["product_tree"]], "exact-public-source")
    equal(git("status", "--porcelain"), "", "clean-product")
    binary = args.mousa.resolve()
    version = subprocess.check_output(["go", "version", "-m", str(binary)], text=True, timeout=30)
    check("vcs.revision=" + frozen["product_head"] in version and "vcs.modified=false" in version and "CGO_ENABLED=0" in version, "exact-public-binary")
    args.output.mkdir(parents=True, exist_ok=False)
    report = dict(protocol_sha256=wire.sha((ROOT / "protocol.json").read_bytes()), fixture=FIXTURE,
        product=dict(head=frozen["product_head"], tree=frozen["product_tree"], binary_path=str(binary),
                     binary_sha256=wire.sha(binary.read_bytes()), build_metadata=version), native=[], sessions=[], association_files={})
    def save():
        wire.save(args.output / "partial.json", report)
    directory = Path(DIRECTORY)
    directory.mkdir(exist_ok=False)
    try:
        for item, text in FIXTURE.items():
            (directory / (item + ".txt")).write_text(text, encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="mousa-public-composed-", dir="/tmp") as temporary:
            report["workspace"] = temporary
            prefix = [str(binary), "-store", temporary + "/evidence.sqlite"]
            def native(label, arguments, value=""):
                event = dict(label=label, arguments=arguments, argv=[*prefix, *arguments], stdin=wire.stream(value.encode()))
                report["native"].append(event)
                save()
                try:
                    r = subprocess.run(event["argv"], input=value.encode(), capture_output=True, timeout=30)
                except subprocess.TimeoutExpired as error:
                    event.update(stdout=wire.stream(error.stdout or b""), stderr=wire.stream(error.stderr or b""),
                                 exit=None, failure="timeout; retained streams may be partial")
                    save()
                    raise
                event.update(stdout=wire.stream(r.stdout), stderr=wire.stream(r.stderr), exit=r.returncode)
                save()
                equal(r.returncode, 0, "capture-native-exit")
                return shared.parsed(event["stdout"])
            def files(form, doc):
                data = wire.encoded(doc)
                report["association_files"][form] = wire.stream(data)
                path = Path(temporary) / (form + "-associations.json")
                path.write_bytes(data)
                return str(path)
            def session(*pins):
                arguments = ["mcp", "--caller", "cli", "--source", SOURCE]
                recorded = dict(arguments=arguments, argv=[*prefix, *arguments], frames=[])
                report["sessions"].append(recorded)
                results = {}
                with tempfile.TemporaryFile() as errors:
                    process = subprocess.Popen(recorded["argv"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors)
                    reader = wire.LineReader(process.stdout.fileno())
                    try:
                        for i in range(len(schedule(results))):
                            label, method, params = schedule(results)[i]
                            message = dict(jsonrpc="2.0", method=method, params=params)
                            if method != "notifications/initialized":
                                message["id"] = i + 1
                            data = wire.encoded(message)
                            event = dict(label=label, request=wire.stream(data), send_completed=False)
                            recorded["frames"].append(event)
                            save()
                            process.stdin.write(data)
                            process.stdin.flush()
                            event["send_completed"] = True
                            save()
                            if method != "notifications/initialized":
                                event["response"] = wire.stream(shared.read_frame(reader))
                                response = shared.parsed(event["response"])
                                result = response.get("result", {}).get("structuredContent", {}).get("result")
                                if result is not None:
                                    results[label] = result
                            save()
                    finally:
                        process.stdin.close()
                        try:
                            recorded["exit"] = process.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            recorded["exit"] = process.wait()
                            raise
                        finally:
                            recorded["stdout_tail"] = wire.stream(reader.buffer + process.stdout.read())
                            process.stdout.close()
                            errors.seek(0)
                            recorded["stderr"] = wire.stream(errors.read())
                            save()
                return replay_session(recorded, *pins)
            report["summary"] = exercise(native, session, files)
        verify(report)
        wire.write_capture(args.output / "capture.json.gz", report)
        wire.save(args.output / "summary.json", report["summary"])
        (args.output / "partial.json").unlink()
    finally:
        shutil.rmtree(directory)
    return report


def controls(report, output):
    receipts = []
    for name, detector in (("association-request", "scheduled-request-bytes"),
                           ("suppression-facts", "history-suppression-binding"),
                           ("selected-support", "evidence-content-binding")):
        changed = copy.deepcopy(report)
        label = "original/needle/history" if name == "suppression-facts" else "original/instruction"
        event = next(e for e in changed["sessions"][0]["frames"] if e["label"] == label)
        if name == "association-request":
            value = shared.parsed(event["request"])
            value["params"]["arguments"]["associations"]["associations"][0]["basis"] = True
            event["request"] = wire.stream(wire.encoded(value))
        else:
            value = shared.parsed(event["response"])
            envelope = value["result"]["structuredContent"]
            if name == "suppression-facts":
                envelope["result"]["historical"]["supersession"]["dispositions"][0]["successor_item_id"] = "unrelated"
            else:
                passage = envelope["result"]["evidence"][-1]
                passage["text"] = "Mutated plausible qualification."
                passage["content_sha256"] = passage["representation_sha256"] = wire.sha(passage["text"].encode())
                passage["byte_end"] = passage["byte_length"] = len(passage["text"].encode())
            value["result"]["content"][0]["text"] = wire.canonical(envelope)
            event["response"] = wire.stream(wire.encoded(value))
        path = output / (name + ".json.gz")
        wire.write_capture(path, changed)
        try:
            verify(wire.load_capture(path))
        except ValueError as error:
            equal(str(error), detector, "intended-semantic-detector")
            receipts.append(dict(control=name, detector=detector, result="PASS", archive_sha256=wire.sha(path.read_bytes())))
        else:
            raise ValueError("rehashed-control-accepted")
    wire.save(output / "controls.json", receipts)
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "verify", "controls", "compare"))
    parser.add_argument("--mousa", type=Path)
    parser.add_argument("--product-source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--other", type=Path)
    args = parser.parse_args()
    if args.mode == "capture":
        report = capture(args)
        print(json.dumps(dict(result="PASS", native_commands=len(report["native"]), mcp_frames=len(report["sessions"][0]["frames"]))))
        return
    report = wire.load_capture(args.capture)
    summary = verify(report)
    if args.mode == "controls":
        args.output.mkdir(parents=True, exist_ok=True)
        print(json.dumps(controls(report, args.output)))
    elif args.mode == "compare":
        equal(summary, verify(wire.load_capture(args.other)), "paired-stable-producing-facts")
        print(json.dumps(dict(result="PASS", stable_rows=len(summary), excluded="Only per-call identities and evaluation/latency timing; packet and evidence/administration pins retained.")))
    else:
        print(json.dumps(dict(result="PASS", native_commands=len(report["native"]), mcp_frames=len(report["sessions"][0]["frames"]))))


if __name__ == "__main__":
    main()
