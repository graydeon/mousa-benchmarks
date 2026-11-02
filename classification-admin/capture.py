"""Capture and replay native attributed assertions; no database inspection or inference."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("retrieval_capture", ROOT.parent / "mcp-retrieval/capture.py")
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
wire, check, equal = shared.wire, shared.check, shared.equal
SOURCE = "synthetic-classification-admin"
INITIAL = "cedar synthetic evidence; this fixture does not establish a true label"
REVISED = "cedar replacement evidence; prior revision labels do not relabel this segment"


def exercise(command):
    command("sync", ["sync", "--source", SOURCE], wire.encoded(dict(id="doc", text=INITIAL)).decode())
    query = ["query", "--source", SOURCE, "cedar"]
    before, _ = command("before", query)
    equal(len(before["evidence"]), 1, "one-initial-passage")
    pin = before["evidence"][0]
    draft = dict(schema="mousa.classification_input.v1",
                 subject=dict(kind="segment", id=pin["segment_id"]),
                 taxonomy="example.caller-review", taxonomy_version="1",
                 label="synthetic-caller-reviewed", asserter_id="example.caller",
                 asserter_version="1", basis=[dict(kind="representation", id=pin["representation_id"])],
                 asserted_at_usec=1, confidence_ppm=0)

    def put(label, value):
        record, raw = command(label, ["classification", "put"], wire.encoded(value).decode())
        check(type(record["id"]) is str and re.fullmatch("[0-9a-f]{64}", record["id"]), "classification-id")
        expected = dict(value, schema="mousa.classification.v1", id=record["id"])
        equal(record, expected, "assertion-facts-binding")
        return record, raw

    original, raw = put("put", draft)
    retry, retry_raw = put("retry", draft)
    equal(retry, original, "retry-record")
    equal(retry_raw, raw, "retry-canonical-bytes")
    read, read_raw = command("get", ["classification", "get", original["id"]])
    equal(read, original, "get-record")
    equal(read_raw, raw, "get-canonical-bytes")
    changed_draft = dict(draft, label="synthetic-disputed")
    changed, _ = put("changed", changed_draft)
    check(changed["id"] != original["id"], "changed-identity")
    _, old_raw = command("old-after-change", ["classification", "get", original["id"]])
    equal(old_raw, raw, "immutable-original")
    after, _ = command("after", query)
    equal(after["packet_id"], before["packet_id"], "selection-packet-unchanged")
    equal(after["evidence"], before["evidence"], "selection-evidence-unchanged")
    invalid = dict(draft, subject=dict(kind="source", id="a" * 64))
    command("invalid-parent", ["classification", "put"], wire.encoded(invalid).decode(), error="sqlite conflict")
    _, after_error = command("old-after-error", ["classification", "get", original["id"]])
    equal(after_error, raw, "original-after-refusal")
    command("resync", ["sync", "--source", SOURCE], wire.encoded(dict(id="doc", text=REVISED)).decode())
    replacement, _ = command("replacement", query)
    equal(len(replacement["evidence"]), 1, "one-replacement-passage")
    new_pin = replacement["evidence"][0]
    check(new_pin["segment_id"] != pin["segment_id"], "replacement-segment")
    check(new_pin["representation_id"] != pin["representation_id"], "replacement-representation")
    retired, retired_raw = command("retired-readback", ["classification", "get", original["id"]])
    equal(retired_raw, raw, "retired-canonical-bytes")
    equal(retired["subject"], draft["subject"], "retired-subject-pin")
    equal(retired["basis"], draft["basis"], "retired-basis-pin")
    return dict(original=original, changed=changed, original_canonical=raw,
                before_packet_id=before["packet_id"], replacement_segment_id=new_pin["segment_id"],
                replacement_representation_id=new_pin["representation_id"],
                exercised_subjects=["segment"], exercised_basis=["representation"])


def protocol():
    value = json.loads((ROOT / "protocol.json").read_text())
    equal(wire.sha(Path(__file__).read_bytes()), value["runner_sha256"], "frozen-runner")
    for relative, digest in value["helpers"].items():
        equal(wire.sha((ROOT.parent / relative).read_bytes()), digest, "frozen-helper")
    return value


def result(event, error):
    equal(event["exit"], 1 if error else 0, "native-exit")
    check(event["stdout"]["bytes"] <= 1 << 20 and event["stderr"]["bytes"] <= 1 << 20, "stream-bound")
    if error:
        equal(event["stdout"], wire.stream(b""), "refusal-no-success-json")
        check(error in event["stderr"]["text"], "native-error")
        return None, ""
    equal(event["stderr"], wire.stream(b""), "native-success-stderr")
    value = shared.parsed(event["stdout"])
    check(type(value) is dict, "native-object")
    return value, event["stdout"]["text"]


def verify(report):
    frozen = protocol()
    equal(report["protocol_sha256"], wire.sha((ROOT / "protocol.json").read_bytes()), "protocol-binding")
    equal(report["product"]["head"], frozen["product_head"], "public-head-binding")
    equal(report["product"]["tree"], frozen["product_tree"], "public-tree-binding")
    wire.streams_valid(report)
    index = 0

    def replay(label, arguments, value="", error=None):
        nonlocal index
        check(index < len(report["events"]), "missing-command")
        event = report["events"][index]
        index += 1
        equal(event["label"], label, "scheduled-label")
        equal(event["arguments"], arguments, "scheduled-arguments")
        equal(event["argv"][3:], arguments, "recorded-argv")
        equal(event["stdin"], wire.stream(value.encode()), "scheduled-input")
        return result(event, error)

    summary = exercise(replay)
    equal(index, len(report["events"]), "extra-command")
    equal(summary, report["summary"], "summary-binding")
    return summary


def capture(args):
    frozen = protocol()

    def git(*argv):
        return subprocess.check_output(["git", "-C", str(args.product_source), *argv], text=True, timeout=30).strip()

    equal(git("rev-parse", "HEAD"), frozen["product_head"], "exact-public-head")
    equal(git("rev-parse", "HEAD^{tree}"), frozen["product_tree"], "exact-public-tree")
    equal(git("status", "--porcelain"), "", "clean-product")
    version = subprocess.check_output(["go", "version", "-m", str(args.mousa.resolve())], text=True, timeout=30)
    check("vcs.revision=" + frozen["product_head"] in version and "vcs.modified=false" in version,
          "public-binary-vcs")
    check("CGO_ENABLED=0" in version, "cgo-free-binary")
    report = dict(protocol_sha256=wire.sha((ROOT / "protocol.json").read_bytes()),
                  product=dict(head=frozen["product_head"], tree=frozen["product_tree"],
                               binary_sha256=wire.sha(args.mousa.read_bytes()), build_metadata=version), events=[])
    args.output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="mousa-public-classification-admin-", dir="/tmp") as temporary:
        def command(label, arguments, value="", error=None):
            argv = [str(args.mousa.resolve()), "-store", str(Path(temporary) / "evidence.sqlite"), *arguments]
            completed = subprocess.run(argv, input=value.encode(), capture_output=True, timeout=30)
            event = dict(label=label, arguments=arguments, argv=argv, stdin=wire.stream(value.encode()),
                         stdout=wire.stream(completed.stdout), stderr=wire.stream(completed.stderr), exit=completed.returncode)
            report["events"].append(event)
            wire.save(args.output / "partial.json", report)
            return result(event, error)

        report["summary"] = exercise(command)
    verify(report)
    wire.write_capture(args.output / "capture.json.gz", report)
    wire.save(args.output / "summary.json", report["summary"])
    (args.output / "partial.json").unlink()
    return report


def controls(report, output):
    mutated = copy.deepcopy(report)
    event = next(event for event in mutated["events"] if event["label"] == "put")
    value = shared.parsed(event["stdout"])
    value["label"] = "synthetic-mutated-returned-label"
    event["stdout"] = wire.stream(wire.encoded(value))
    path = output / "mutated-label.json.gz"
    wire.write_capture(path, mutated)
    try:
        verify(wire.load_capture(path))
    except ValueError as error:
        equal(str(error), "assertion-facts-binding", "intended-binding-detector")
    else:
        raise ValueError("mutated label passed")
    receipt = dict(result="PASS", mutation="returned label with recomputed stream/member/archive hashes",
                   detector="assertion-facts-binding", scope="Mutation is intentionally invalid protocol evidence.")
    wire.save(output / "controls.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["capture", "verify", "controls", "compare"])
    parser.add_argument("--mousa", type=Path)
    parser.add_argument("--product-source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--other", type=Path)
    args = parser.parse_args()
    if args.mode == "capture":
        if not all((args.mousa, args.product_source, args.output)):
            parser.error("capture requires --mousa, --product-source and --output")
        report = capture(args)
        print(json.dumps(dict(result="PASS", commands=len(report["events"]))))
        return
    if not args.capture:
        parser.error("--capture is required")
    report = wire.load_capture(args.capture)
    first = verify(report)
    if args.mode == "controls":
        if not args.output:
            parser.error("controls requires --output")
        print(json.dumps(controls(report, args.output)))
    elif args.mode == "compare":
        if not args.other:
            parser.error("compare requires --other")
        second = verify(wire.load_capture(args.other))
        equal(first, second, "fresh-store-stable-canonical-and-pins")
        print(json.dumps(dict(result="PASS", scope="Canonical assertions, fixed evidence pins and selection packet; query request/decision/trail IDs and timing are invocation-specific.")))
    else:
        print(json.dumps(dict(result="PASS", commands=len(report["events"]))))


if __name__ == "__main__":
    main()
