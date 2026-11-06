"""Additive exact-public-head token/association/supersession client capture and replay."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT.parent / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


composition = load("triple_byte_composition", "association-supersession/capture.py")
tokens = load("triple_token_helpers", "token-associations-checked-v2/capture.py")
wire, shared, equal, check = composition.wire, composition.shared, composition.equal, composition.check
HELPERS = ("association-supersession/capture.py", "association-supersession-v2/capture.py",
           "directory-supersession/capture.py", "token-associations-checked-v2/capture.py",
           "mcp-tokens/capture.py", "mcp-retrieval/capture.py", "mcp-trail-supersession/run.py",
           "token-association-supersession/run-public.sh")
composition.DIRECTORY = "/tmp/mousa-public-token-triple-notes"


def implementation():
    return {name: wire.sha((ROOT.parent / name).read_bytes()) for name in HELPERS} | {
        "token-association-supersession/capture.py": wire.sha(Path(__file__).read_bytes())}


def exercise(io, encoder):
    references, rows = [], []
    directory_facts = {}

    def counted(result, label):
        context, token = result["context"], result["token"]
        normalized = [dict(segment_id=p["segment"]["id"], content_sha256=p["segment"]["content_sha256"],
                           text=p["text"]) if "segment" in p else p for p in result["evidence"]]
        rendered = "\n\n".join(tokens.passage(token["source_id"], p) for p in normalized)
        equal(context, rendered, "whole-rendering")
        count = len(encoder.encode_ordinary(context))
        equal(token["measured_tokens"], count, "independent-count")
        equal(token["rendered_sha256"], wire.sha(context.encode()), "rendering-digest")
        equal(token["rendered_bytes"], len(context.encode()), "rendering-bytes")
        check(count <= token["limit"], "token-limit")
        equal(result["used_bytes"], sum(len(p["text"].encode()) for p in result["evidence"]), "byte-accounting")
        references.append(dict(label=label, count=count, sha256=wire.sha(context.encode())))
        return count

    def native(label, args, value="", expected=0, store_slot="STORE"):
        result = io("native", label, arguments=args, stdin=value, expected_exit=expected, store_slot=store_slot)
        if label in ("directory/pins", "directory/declaration", "directory/activation"):
            directory_facts[label.split("/")[1]] = result
        return result

    def session(pins, declaration, activation):
        io("start", "mcp/start", arguments=["mcp", "--caller", "cli", "--source", composition.SOURCE,
            "--tokenizer-python", "TOKEN_PY", "--tokenizer-cache", "TOKEN_CACHE"])
        io("rpc", "initialize", method="initialize", params=dict(protocolVersion="2025-11-25", capabilities={},
            clientInfo=dict(name="token-association-supersession", version="1")))
        io("rpc", "initialized", method="notifications/initialized", params={})
        catalog = io("rpc", "discovery", method="tools/list", params={})
        schemas = {tool["name"]: tool for tool in catalog["tools"]}

        def tool(label, name, args, refusal=False):
            result = io("rpc", label, method="tools/call", params=dict(name=name,
                arguments=dict(source=composition.SOURCE, **args)))
            envelope = result["structuredContent"]
            equal(shared.parsed(wire.stream(result["content"][0]["text"].encode())), envelope, "envelope-equality")
            check(not wire.schema_violations(schemas[name]["outputSchema"], envelope), "closed-output-schema")
            equal(envelope["operation"], name, "operation-binding")
            if refusal:
                equal([result.get("isError"), envelope["error"]["code"]], [True, "invalid_arguments"], "refusal-cause")
                check("result" not in envelope, "refusal-no-result")
                return None
            check(not result.get("isError", False), "tool-success")
            return envelope["result"]

        selector = ["--source", composition.SOURCE]
        for surface in ("native", "mcp"):
            for packing in ("original", "exact-v1"):
                prefix = surface + "/" + packing

                def query(case, cap=4096, supersession=True, associations=True, byte_limit=8192, expression="instruction"):
                    label = prefix + "/" + case
                    args = dict(query=expression, policy="original", budget_bytes=byte_limit,
                                packing_policy=packing, context_tokens=cap)
                    if supersession is not None:
                        args["supersession"] = supersession
                    if associations:
                        args["associations"] = composition.document("")
                    if surface == "mcp":
                        result = tool(label, "mousa_query", args)
                    else:
                        argv = ["query", "--policy", "original", "--packing-policy", packing,
                            "--budget-bytes", str(byte_limit), "--context-tokens", str(cap),
                            "--tokenizer-python", "TOKEN_PY", "--tokenizer-cache", "TOKEN_CACHE"]
                        if supersession is not None:
                            argv += ["--supersession=" + str(supersession).lower()]
                        if associations:
                            argv += ["--associations", "ASSOCIATIONS_jsonl"]
                        result = native(label, [*argv, *selector, expression])
                    counted(result, label)
                    rows.append(dict(label=label, result=composition.stable(result)))
                    return result

                full = query("full")
                composition.facts(full, pins, "", "instruction")
                equal(full["token"]["associations"]["proposed_tokens"][0], None, "suppressed-target-uncounted")
                count = full["token"]["measured_tokens"]
                exact = query("exact", cap=count)
                equal(exact["context"], full["context"], "exact-fit")
                short = query("short", cap=count - 1)
                equal([p["item"] for p in short["evidence"]], ["primary", "twin"], "one-token-short")
                byte_short = query("byte-short", byte_limit=full["used_bytes"] - 1)
                equal([p["item"] for p in byte_short["evidence"]], ["primary", "twin"], "one-byte-short")
                suppressed = query("primary-suppressed", expression="needle")
                composition.facts(suppressed, pins, "", "needle")
                omitted = query("omitted", supersession=None)
                false = query("false", supersession=False)
                equal(composition.stable(omitted), composition.stable(false), "omitted-false-compatibility")
                check(any(p["item"] == "old" for p in false["evidence"]), "optout-retains-old")
                ordinary = query("no-declarations", associations=False)
                equal([p["text"] for p in ordinary["evidence"]], [composition.FIXTURE["primary"]], "no-declaration-primary")
                unfired = query("unfired", cap=1)
                equal(unfired["evidence"], [], "unselected-primary-cannot-fire")
                check("associations" not in unfired["token"], "unfired-no-association-counts")
                for case, producing, version in (("history", exact, 13), ("ordinary-history", ordinary, 8),
                                                 ("unfired-history", unfired, 8)):
                    if surface == "native":
                        history = native(prefix + "/" + case, ["trail", *selector, producing["trail_id"]])
                    else:
                        history = tool(prefix + "/" + case, "mousa_trail", dict(trail_id=producing["trail_id"],
                            supersession=True, token_details=True))
                    h = history["historical"]
                    equal(h["schema"], "mousa.source_trail.v" + str(version), "history-version")
                    equal([h["id"], h["decision_id"], h["packet_id"]],
                        [producing["trail_id"], producing["decision_id"], producing["packet_id"]], "history-producing-ids")
                    if "request_id" in producing:
                        equal(h["request_id"], producing["request_id"], "history-producing-request")
                    equal(h["token"], producing["token"], "history-token")
                    equal(h["supersession"]["activation_id"], activation["id"], "history-activation")
                    equal(h["supersession"]["declaration_id"], declaration["id"], "history-declaration")
                    check(history["authorization_decision_id"] != producing["decision_id"], "fresh-history")
                    if version == 13:
                        equal(h["associated"][0]["omission"], "superseded", "history-target-suppression")
                    rows.append(dict(label=prefix + "/" + case, result=composition.stable(history)))
                if surface == "native":
                    recount = native(prefix + "/recount", ["trail", "--verify-tokens", "--tokenizer-python",
                        "TOKEN_PY", "--tokenizer-cache", "TOKEN_CACHE", *selector, exact["trail_id"]])
                    equal(recount["historical"]["token"], exact["token"], "recount-token")
                    equal(recount["historical"]["token_verification"], "official_recount_verified", "recount-status")
        for budget_mode in ("byte", "token"):
            flags = [] if budget_mode == "byte" else ["--context-tokens", "4096",
                "--tokenizer-python", "TOKEN_PY", "--tokenizer-cache", "TOKEN_CACHE"]
            for mode in ("omitted", "false", "true"):
                prefix = "empty/" + budget_mode + "/" + mode
                flags_mode = flags + ([] if mode == "omitted" else ["--supersession=" + mode])
                baseline = native(prefix + "/absent-flag", ["query", *flags_mode, *selector, "needle"])
                argv = ["query", *flags_mode, "--associations=", *selector, "needle"]
                if mode == "true":
                    native(prefix + "/empty", argv, expected=2)
                    native(prefix + "/absent-store", argv, expected=2, store_slot="ABSENT")
                else:
                    empty = native(prefix + "/empty", argv)
                    equal(composition.stable(empty), composition.stable(baseline), "empty-flag-compatibility")
        for mode in ("vector", "hybrid"):
            args = dict(space_id="a" * 64, values=[1, 0], budget_bytes=8192, context_tokens=4096,
                        supersession=True, associations=composition.document(""))
            if mode == "hybrid":
                args.update(query="instruction", policy="original")
            tool("refusal/" + mode, "mousa_" + mode + "_query", args, refusal=True)
        io("stop", "mcp/stop")
        return []

    def files(form, document):
        return io("file", form, document=document)

    byte_rows = composition.exercise(native, session, files)
    pins = {p["item"]: p for p in directory_facts["pins"]["passages"]}
    for packing in ("original", "exact-v1"):
        prefix = "directory-token/" + packing
        def query(case, cap=4096, byte_limit=8192, expression="instruction"):
            label = prefix + "/" + case
            result = native(label, ["query", "--supersession", "--associations", "ASSOCIATIONS_directory",
                "--packing-policy", packing, "--context-tokens", str(cap), "--budget-bytes", str(byte_limit),
                "--tokenizer-python", "TOKEN_PY", "--tokenizer-cache", "TOKEN_CACHE",
                composition.DIRECTORY, expression])
            counted(result, label)
            rows.append(dict(label=label, result=composition.stable(result)))
            return result
        full = query("full")
        composition.facts(full, pins, ".txt", "instruction")
        exact = query("exact", full["token"]["measured_tokens"], full["used_bytes"])
        equal(exact["context"], full["context"], "directory-exact-fit")
        for case, cap, byte_limit in (("token-short", full["token"]["measured_tokens"] - 1, full["used_bytes"]),
                                     ("byte-short", full["token"]["measured_tokens"], full["used_bytes"] - 1)):
            short = query(case, cap, byte_limit)
            equal([p["item"] for p in short["evidence"]], ["primary.txt", "twin.txt"], "directory-one-short")
        composition.facts(query("primary-suppressed", expression="needle"), pins, ".txt", "needle")
        history = native(prefix + "/recount", ["trail", "--verify-tokens", "--tokenizer-python", "TOKEN_PY",
            "--tokenizer-cache", "TOKEN_CACHE", composition.DIRECTORY, exact["trail_id"]])
        h = history["historical"]
        equal(h["schema"], "mousa.source_trail.v13", "directory-history-version")
        equal([h["id"], h["request_id"], h["decision_id"], h["packet_id"]],
              [exact["trail_id"], exact["request_id"], exact["decision_id"], exact["packet_id"]],
              "directory-history-producing-ids")
        equal(h["token"], exact["token"], "directory-history-token")
        equal(h["token_verification"], "official_recount_verified", "directory-recount")
        equal(h["supersession"]["activation_id"], directory_facts["activation"]["id"], "directory-activation")
        equal(h["supersession"]["declaration_id"], directory_facts["declaration"]["id"], "directory-declaration")
        equal(h["associated"][0]["omission"], "superseded", "directory-target-suppression")
        rows.append(dict(label=prefix + "/recount", result=composition.stable(history)))
    return dict(byte_compatibility=byte_rows, token_rows=rows, independent_counts=references)


class Transcript:
    def __init__(self, report, output=None):
        self.report, self.output, self.index = report, output, 0
        self.process = None

    def save(self):
        if self.output:
            wire.save(self.output / "partial.json", self.report)

    def __call__(self, kind, label, **planned):
        expected = dict(kind=kind, label=label, **planned)
        if self.output:
            event = copy.deepcopy(expected)
            self.report["events"].append(event)
        else:
            check(self.index < len(self.report["events"]), "missing-event")
            event = self.report["events"][self.index]
            for key, value in expected.items():
                equal(event[key], value, "scheduled-" + key)
        self.index += 1
        paths = self.report["paths"]
        if kind == "file":
            path = paths["ASSOCIATIONS_" + label]
            if self.output:
                Path(path).write_bytes(wire.encoded(planned["document"]))
            return "ASSOCIATIONS_" + label
        if kind in ("native", "start"):
            argv = [paths["BINARY"], "-store", paths[planned.get("store_slot", "STORE")],
                    *[paths.get(a, a) for a in planned["arguments"]]]
            if self.output:
                event["argv"] = argv
                self.save()
            equal(event["argv"], argv, "raw-argv")
        if kind == "native":
            if self.output:
                try:
                    result = subprocess.run(argv, input=planned["stdin"].encode(), capture_output=True, timeout=30)
                except subprocess.TimeoutExpired as error:
                    event.update(stdout=wire.stream(error.stdout or b""), stderr=wire.stream(error.stderr or b""),
                                 exit=None, failure="timeout; streams may be partial")
                    self.save()
                    raise
                event.update(stdout=wire.stream(result.stdout), stderr=wire.stream(result.stderr), exit=result.returncode)
                if planned["store_slot"] == "ABSENT":
                    event["store_exists"] = Path(paths["ABSENT"]).exists()
                self.save()
            equal(event["exit"], planned["expected_exit"], "native-exit")
            if planned["expected_exit"]:
                equal(event["stdout"], wire.stream(b""), "refusal-empty-output")
                check(event["stderr"]["bytes"] > 0, "refusal-diagnostic")
                if planned["store_slot"] == "ABSENT":
                    equal(event["store_exists"], False, "empty-preopen-no-store")
                return None
            equal(event["stderr"], wire.stream(b""), "native-stderr")
            return shared.parsed(event["stdout"])
        if kind == "start":
            if self.output:
                self.errors = tempfile.TemporaryFile()
                self.process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errors)
                self.reader = wire.LineReader(self.process.stdout.fileno())
            return None
        if kind == "stop":
            if self.output:
                self.process.stdin.close()
                try:
                    event["exit"] = self.process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    event["exit"] = self.process.wait()
                    raise
                finally:
                    event["stdout_tail"] = wire.stream(self.reader.buffer + self.process.stdout.read())
                    self.errors.seek(0)
                    event["stderr"] = wire.stream(self.errors.read())
                    self.process.stdout.close()
                    self.errors.close()
                    self.process = None
                    self.save()
            equal([event["exit"], event["stdout_tail"], event["stderr"]],
                  [0, wire.stream(b""), wire.stream(b"")], "clean-mcp-exit")
            return None
        request = dict(jsonrpc="2.0", method=planned["method"], params=planned["params"])
        notification = planned["method"] == "notifications/initialized"
        if not notification:
            request["id"] = self.index
        if self.output:
            event["request"] = wire.stream(wire.encoded(request))
            event["send_completed"] = False
            self.save()
            self.process.stdin.write(wire.encoded(request))
            self.process.stdin.flush()
            event["send_completed"] = True
            self.save()
            if not notification:
                event["response"] = wire.stream(shared.read_frame(self.reader))
            self.save()
        equal(event["request"], wire.stream(wire.encoded(request)), "scheduled-request-bytes")
        equal(event["send_completed"], True, "completed-send")
        if notification:
            check("response" not in event, "notification-no-response")
            return None
        response = shared.parsed(event["response"])
        equal([response["jsonrpc"], response["id"]], ["2.0", self.index], "rpc-binding")
        check("error" not in response, "rpc-success")
        return response["result"]


def verify(report, protocol, encoder):
    equal(protocol["implementations"], implementation(), "frozen-implementations")
    equal(protocol["fixture"], composition.FIXTURE, "frozen-fixture")
    equal(report["protocol_sha256"], wire.sha(wire.encoded(protocol)), "protocol-binding")
    equal([report["product"]["head"], report["product"]["tree"]],
          [protocol["product_head"], protocol["product_tree"]], "public-source-binding")
    wire.streams_valid(report)
    transcript = Transcript(report)
    summary = exercise(transcript, encoder)
    equal(transcript.index, len(report["events"]), "complete-events")
    equal(summary, report["summary"], "summary-binding")
    return summary


def controls(report, protocol, encoder, output):
    output.mkdir(exist_ok=False)
    receipts = []
    for name, detector in (("request", "scheduled-request-bytes"), ("count", "independent-count"),
                           ("suppression", "history-target-suppression"), ("text-duplicate", "strict-json")):
        changed = copy.deepcopy(report)
        label = "mcp/original/history" if name == "suppression" else "mcp/original/full"
        event = next(e for e in changed["events"] if e["label"] == label)
        field = "request" if name == "request" else "response"
        value = shared.parsed(event[field])
        if name == "request":
            value["params"]["arguments"]["supersession"] = False
        elif name == "text-duplicate":
            text = value["result"]["content"][0]["text"]
            value["result"]["content"][0]["text"] = '{"schema":"conflicting-duplicate",' + text.lstrip()[1:]
        else:
            envelope = value["result"]["structuredContent"]
            if name == "count":
                envelope["result"]["token"]["measured_tokens"] += 1
            else:
                envelope["result"]["historical"]["associated"][0]["omission"] = "duplicate"
            value["result"]["content"][0]["text"] = wire.canonical(envelope)
        event[field] = wire.stream(wire.encoded(value))
        wire.save(output / (name + ".json"), changed)
        try:
            verify(changed, protocol, encoder)
        except ValueError as error:
            equal(str(error), detector, "intended-control-detector")
            receipts.append(dict(control=name, detector=detector, rehashed_sha256=wire.sha(wire.encoded(changed))))
        else:
            raise ValueError("control-accepted")
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("freeze", "capture", "verify", "compare", "controls"))
    for name in ("protocol", "output", "other", "mousa", "product-source", "python", "cache"):
        parser.add_argument("--" + name, type=Path, required=name == "protocol")
    parser.add_argument("--product-head")
    args = parser.parse_args()
    if args.mode in ("freeze", "capture"):
        def git(*argv):
            return subprocess.check_output(["git", "-C", str(args.product_source), *argv], text=True, timeout=30).strip()
        head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
        equal(head, args.product_head, "requested-public-head")
        equal(git("status", "--porcelain"), "", "clean-source")
        if args.mode == "freeze":
            check(not args.protocol.exists(), "new-protocol-only")
            wire.save(args.protocol, dict(product_head=head, product_tree=tree,
                implementations=implementation(), fixture=composition.FIXTURE,
                status="exact-public-head-client-protocol"))
            return
    protocol = json.loads(args.protocol.read_text())
    encoder = tokens.tokens.ordinary_encoder(args.cache)
    if args.mode == "capture":
        equal([head, tree], [protocol["product_head"], protocol["product_tree"]], "capture-public-head")
        metadata = subprocess.check_output(["go", "version", "-m", str(args.mousa)], text=True, timeout=30)
        check("vcs.revision=" + head in metadata and "vcs.modified=false" in metadata and "CGO_ENABLED=0" in metadata,
              "public-binary-metadata")
        args.output.mkdir(parents=True, exist_ok=False)
        directory = Path(composition.DIRECTORY)
        directory.mkdir(exist_ok=False)
        with tempfile.TemporaryDirectory(prefix="mousa-public-token-triple-") as temporary:
            root = Path(temporary)
            paths = dict(BINARY=str(args.mousa.absolute()), STORE=str(root / "evidence.sqlite"),
                ABSENT=str(root / "absent.sqlite"),
                TOKEN_PY=str(args.python.absolute()), TOKEN_CACHE=str(args.cache.absolute()),
                ASSOCIATIONS_jsonl=str(root / "jsonl.json"), ASSOCIATIONS_directory=str(root / "directory.json"))
            report = dict(protocol_sha256=wire.sha(wire.encoded(protocol)), paths=paths, events=[],
                product=dict(head=head, tree=tree, binary_sha256=wire.sha(args.mousa.read_bytes()), build_metadata=metadata))
            transcript = Transcript(report, args.output)
            try:
                for name, text in composition.FIXTURE.items():
                    (directory / (name + ".txt")).write_text(text, encoding="utf-8")
                report["summary"] = exercise(transcript, encoder)
                verify(report, protocol, encoder)
                wire.save(args.output / "capture.json", report)
                wire.save(args.output / "summary.json", report["summary"])
                (args.output / "partial.json").unlink()
            finally:
                if transcript.process is not None:
                    transcript.process.kill()
                    report["aborted_exit"] = transcript.process.wait()
                    transcript.errors.seek(0)
                    report["aborted_stderr"] = wire.stream(transcript.errors.read())
                    report["aborted_stdout"] = wire.stream(transcript.reader.buffer + transcript.process.stdout.read())
                    transcript.process.stdout.close()
                    transcript.errors.close()
                    transcript.save()
                shutil.rmtree(directory)
        return
    report = json.loads((args.output / "capture.json").read_text())
    summary = verify(report, protocol, encoder)
    equal(summary, json.loads((args.output / "summary.json").read_text()), "saved-summary")
    if args.mode == "controls":
        print(json.dumps(controls(report, protocol, encoder, args.output / "controls")))
    elif args.mode == "compare":
        other = json.loads((args.other / "capture.json").read_text())
        equal(summary, verify(other, protocol, encoder), "two-store-stability")
        print(json.dumps(dict(result="PASS", independent_stores=2, packet_ids_retained=True)))
    else:
        print(json.dumps(dict(result="PASS", events=len(report["events"]), independent_counts=summary["independent_counts"])))


if __name__ == "__main__":
    main()
