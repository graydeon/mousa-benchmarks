"""Replayable empty-flag compatibility and composed lexical clients; historical files stay unchanged."""
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
spec = importlib.util.spec_from_file_location("composition_v1", ROOT.parent / "association-supersession/capture.py")
composition = importlib.util.module_from_spec(spec)
spec.loader.exec_module(composition)
wire, shared, equal, check = composition.wire, composition.shared, composition.equal, composition.check


def protocol(path):
    frozen = shared.parsed(wire.stream(path.read_bytes()))
    equal(frozen["runner_sha256"], wire.sha(Path(__file__).read_bytes()), "frozen-v2-runner")
    for relative, digest in frozen["helpers"].items():
        equal(wire.sha((ROOT.parent / relative).read_bytes()), digest, "frozen-helper")
    equal(frozen["fixture"], composition.FIXTURE, "frozen-fixture")
    check(frozen["publication_state"] in ("local-smoke", "public-corrected"), "explicit-publication-state")
    return frozen


def producing_history(history, query):
    equal(history["authorization_outcome"], "allow", "boundary-history-authorization")
    h = history["historical"]
    equal([h["id"], h["request_id"], h["decision_id"], h["packet_id"]],
          [query["trail_id"], query["request_id"], query["decision_id"], query["packet_id"]], "boundary-producing-binding")
    check(history["authorization_decision_id"] != query["decision_id"], "boundary-fresh-history")
    check("associated" not in h and "association_omissions" not in h, "boundary-no-support-stage")


def exercise(native, session, files):
    rows = composition.exercise(native, session, files)
    for form in ("jsonl", "directory"):
        selector = ["--source", composition.SOURCE] if form == "jsonl" else [composition.DIRECTORY]
        for packing in ("original", "exact-v1"):
            for mode in ("omitted", "false", "true"):
                label = "empty/" + form + "/" + packing + "/" + mode
                args = ["query", "--packing-policy", packing]
                if mode != "omitted":
                    args += ["--supersession=" + mode]
                baseline = native(label + "/absent-flag", [*args, *selector, "needle"])
                history = native(label + "/baseline-history", ["trail", *selector, baseline["trail_id"]])
                producing_history(history, baseline)
                empty_args = [*args, "--associations=", *selector, "needle"]
                if mode == "true":
                    native(label + "/empty-flag", empty_args, expected_exit=2)
                    native(label + "/absent-store", empty_args, expected_exit=2, store_slot="absent")
                    rows.append(dict(label=label, query=composition.stable(baseline), history=composition.stable(history), empty_exit=2))
                    continue
                selected = native(label + "/empty-flag", empty_args)
                for key in ("request_id", "decision_id", "trail_id"):
                    check(baseline[key] != selected[key], "boundary-fresh-query-" + key)
                equal(composition.stable(selected), composition.stable(baseline), "empty-stable-property-binding")
                inspected = native(label + "/empty-history", ["trail", *selector, selected["trail_id"]])
                producing_history(inspected, selected)
                rows.append(dict(label=label, query=composition.stable(selected), history=composition.stable(inspected), empty_exit=0))
    return rows


def verify(report, protocol_path):
    frozen = protocol(protocol_path)
    equal(report["protocol_sha256"], wire.sha(protocol_path.read_bytes()), "protocol-binding")
    equal([report["product"]["head"], report["product"]["tree"], report["publication_state"]],
          [frozen["product_head"], frozen["product_tree"], frozen["publication_state"]], "product-pin-binding")
    wire.streams_valid(report)
    check(type(report["workspace"]) is str and re.fullmatch(r"/tmp/mousa-public-composed-v2-[A-Za-z0-9_-]+", report["workspace"]), "workspace-form")
    equal(report["fixture"], composition.FIXTURE, "complete-fixture")
    index, file_forms = 0, []
    prefix = [report["product"]["binary_path"], "-store"]

    def native(label, arguments, value="", expected_exit=0, store_slot="main"):
        nonlocal index
        check(index < len(report["native"]), "missing-native-attempt")
        event = report["native"][index]
        index += 1
        equal([event["label"], event["arguments"], event["store_slot"]], [label, arguments, store_slot], "scheduled-native-request")
        equal(event["expected_exit"], expected_exit, "scheduled-empty-expectation")
        equal(event["argv"], [*prefix, report["workspace"] + "/" + store_slot + ".sqlite", *arguments], "native-argv")
        equal(event["stdin"], wire.stream(value.encode()), "native-stdin")
        equal(event["exit"], expected_exit, "native-exit")
        if expected_exit:
            equal(event["stdout"], wire.stream(b""), "empty-refusal-no-success")
            check(event["stderr"]["bytes"] > 0, "empty-refusal-error")
            if store_slot == "absent":
                equal(event["store_exists"], False, "empty-preopen-no-create")
            return None
        equal(event["stderr"], wire.stream(b""), "native-success-stderr")
        return shared.parsed(event["stdout"])

    def files(form, document):
        file_forms.append(form)
        equal(report["association_files"][form], wire.stream(wire.encoded(document)), "association-file-binding")
        return report["workspace"] + "/" + form + "-associations.json"

    equal(len(report["sessions"]), 1, "complete-session-population")
    session = report["sessions"][0]
    equal(session["argv"], [*prefix, report["workspace"] + "/main.sqlite", "mcp", "--caller", "cli", "--source", composition.SOURCE], "mcp-argv")
    rows = exercise(native, lambda *pins: composition.replay_session(session, *pins), files)
    equal(index, len(report["native"]), "complete-native-population")
    equal(index, frozen["native_commands"], "frozen-native-population")
    equal(sorted(report["association_files"]), sorted(file_forms), "complete-association-files")
    equal(rows, report["summary"], "summary-binding")
    return rows


def capture(args):
    frozen = protocol(args.protocol)
    def git(*arguments):
        return subprocess.check_output(["git", "-C", str(args.product_source), *arguments], text=True, timeout=30).strip()
    equal([git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")], [frozen["product_head"], frozen["product_tree"]], "exact-clean-source")
    equal(git("status", "--porcelain"), "", "clean-source")
    binary = args.mousa.resolve()
    metadata = subprocess.check_output(["go", "version", "-m", str(binary)], text=True, timeout=30)
    check("vcs.revision=" + frozen["product_head"] in metadata and "vcs.modified=false" in metadata and "CGO_ENABLED=0" in metadata, "exact-binary")
    args.output.mkdir(parents=True, exist_ok=False)
    report = dict(protocol_sha256=wire.sha(args.protocol.read_bytes()), publication_state=frozen["publication_state"],
        fixture=composition.FIXTURE, product=dict(head=frozen["product_head"], tree=frozen["product_tree"],
        binary_path=str(binary), binary_sha256=wire.sha(binary.read_bytes()), build_metadata=metadata), native=[], sessions=[], association_files={})
    def save():
        wire.save(args.output / "partial.json", report)
    directory = Path(composition.DIRECTORY)
    directory.mkdir(exist_ok=False)
    try:
        for item, text in composition.FIXTURE.items():
            (directory / (item + ".txt")).write_text(text, encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="mousa-public-composed-v2-", dir="/tmp") as temporary:
            report["workspace"] = temporary
            def native(label, arguments, value="", expected_exit=0, store_slot="main"):
                store = Path(temporary) / (store_slot + ".sqlite")
                event = dict(label=label, arguments=arguments, store_slot=store_slot, expected_exit=expected_exit,
                             argv=[str(binary), "-store", str(store), *arguments], stdin=wire.stream(value.encode()))
                report["native"].append(event)
                save()
                try:
                    completed = subprocess.run(event["argv"], input=value.encode(), capture_output=True, timeout=30)
                except subprocess.TimeoutExpired as error:
                    event.update(stdout=wire.stream(error.stdout or b""), stderr=wire.stream(error.stderr or b""), exit=None, failure="timeout; streams may be partial")
                    save()
                    raise
                event.update(stdout=wire.stream(completed.stdout), stderr=wire.stream(completed.stderr), exit=completed.returncode)
                if store_slot == "absent":
                    event["store_exists"] = store.exists()
                save()
                equal(completed.returncode, expected_exit, "capture-native-exit")
                return None if expected_exit else shared.parsed(event["stdout"])
            def files(form, document):
                data = wire.encoded(document)
                report["association_files"][form] = wire.stream(data)
                path = Path(temporary) / (form + "-associations.json")
                path.write_bytes(data)
                return str(path)
            def session(*pins):
                arguments = ["mcp", "--caller", "cli", "--source", composition.SOURCE]
                recorded = dict(arguments=arguments, argv=[str(binary), "-store", temporary + "/main.sqlite", *arguments], frames=[])
                report["sessions"].append(recorded)
                results = {}
                with tempfile.TemporaryFile() as errors:
                    process = subprocess.Popen(recorded["argv"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors)
                    reader = wire.LineReader(process.stdout.fileno())
                    try:
                        for i in range(len(composition.schedule(results))):
                            label, method, params = composition.schedule(results)[i]
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
                return composition.replay_session(recorded, *pins)
            report["summary"] = exercise(native, session, files)
        verify(report, args.protocol)
        wire.write_capture(args.output / "capture.json.gz", report)
        wire.save(args.output / "summary.json", report["summary"])
        (args.output / "partial.json").unlink()
    finally:
        shutil.rmtree(directory)
    return report


def controls(report, protocol_path, output):
    receipts = []
    cases = (("empty-expectation", "scheduled-empty-expectation"), ("empty-request", "scheduled-native-request"),
             ("association-request", "scheduled-request-bytes"), ("suppression-facts", "history-suppression-binding"),
             ("selected-support", "evidence-content-binding"))
    for name, detector in cases:
        changed = copy.deepcopy(report)
        if name.startswith("empty-"):
            event = next(e for e in changed["native"] if e["label"] == "empty/jsonl/original/false/empty-flag")
            if name == "empty-expectation":
                event["expected_exit"] = 2
            else:
                event["arguments"].remove("--associations=")
                event["argv"].remove("--associations=")
        else:
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
            verify(wire.load_capture(path), protocol_path)
        except ValueError as error:
            equal(str(error), detector, "intended-control-detector")
            receipts.append(dict(control=name, detector=detector, result="PASS", archive_sha256=wire.sha(path.read_bytes())))
        else:
            raise ValueError("rehashed-control-accepted")
    wire.save(output / "controls.json", receipts)
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "verify", "compare", "controls"))
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--mousa", type=Path)
    parser.add_argument("--product-source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--other", type=Path)
    args = parser.parse_args()
    if args.mode == "capture":
        report = capture(args)
        print(json.dumps(dict(result="PASS", publication_state=report["publication_state"], native_commands=len(report["native"]), mcp_frames=len(report["sessions"][0]["frames"]))))
        return
    report = wire.load_capture(args.capture)
    rows = verify(report, args.protocol)
    if args.mode == "controls":
        args.output.mkdir(parents=True, exist_ok=True)
        print(json.dumps(controls(report, args.protocol, args.output)))
    elif args.mode == "compare":
        equal(rows, verify(wire.load_capture(args.other), args.protocol), "paired-stable-producing-facts")
        print(json.dumps(dict(result="PASS", stable_rows=len(rows))))
    else:
        print(json.dumps(dict(result="PASS", publication_state=report["publication_state"], native_commands=len(report["native"]))))


if __name__ == "__main__":
    main()
