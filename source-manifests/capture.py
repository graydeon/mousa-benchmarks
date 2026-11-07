"""Additive exact-public-head source-manifest capture, independent replay and controls."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

import canonical

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("manifest_existing_helpers", ROOT.parent / "mcp-classifications/capture.py")
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
base, wire, equal, check = previous.base, previous.wire, previous.equal, previous.check
SOURCE = "synthetic-source-manifests"
FIXTURE = {"doc": "\ufeffcedar <indexed> café\r\n", "empty": ""}


def implementation():
    return previous.implementation() | {"source-manifests/" + name: wire.sha((ROOT / name).read_bytes())
                                        for name in ("capture.py", "canonical.py", "run-public.sh")}

class Transcript(base.Transcript):
    def __call__(self, kind, label, **planned):
        if kind != "manifest-native":
            return super().__call__(kind, label, **planned)
        expected = dict(kind=kind, label=label, **planned)
        paths = self.report["paths"]
        argv = [paths["BINARY"], "-store", paths["STORE"], *planned["arguments"]]
        if self.output:
            event = dict(expected, argv=argv)
            self.report["events"].append(event)
            self.save()
            try:
                result = subprocess.run(argv, input=b"", capture_output=True, timeout=30)
            except subprocess.TimeoutExpired as error:
                event.update(stdout=wire.stream(error.stdout or b""), stderr=wire.stream(error.stderr or b""),
                             exit=None, failure="timeout; streams may be partial")
                self.save()
                raise
            event.update(stdout=wire.stream(result.stdout), stderr=wire.stream(result.stderr), exit=result.returncode)
            self.save()
        else:
            check(self.index < len(self.report["events"]), "missing-event")
            event = self.report["events"][self.index]
            for key, value in expected.items():
                equal(event[key], value, "scheduled-" + key)
        self.index += 1
        equal(event["argv"], argv, "raw-argv")
        equal(event["exit"], planned["expected_exit"], "native-exit")
        check(event["stderr"]["bytes"] > 0, "native-refusal-diagnostic")
        return previous.shared.parsed(event["stdout"])



def exercise(io):
    rows = []
    schemas = {}

    def start(label, ingest=False):
        arguments = ["mcp", "--caller", "cli", "--source", SOURCE]
        if ingest:
            arguments += ["--ingest-source", SOURCE]
        io("start", label + "/start", arguments=arguments)
        io("rpc", label + "/initialize", method="initialize", params=dict(protocolVersion="2025-11-25", capabilities={}, clientInfo=dict(name="source-manifests", version="1")))
        io("rpc", label + "/initialized", method="notifications/initialized", params={})
        catalog = io("rpc", label + "/discovery", method="tools/list", params={})
        schemas.update((tool["name"], tool) for tool in catalog["tools"])
        equal(sorted(schemas), sorted(previous.TOOLS | {"mousa_source_manifest"}), "tool-discovery")

    def tool(label, name, arguments=None):
        response = io("rpc", label, method="tools/call", params=dict(name=name, arguments=dict(source=SOURCE, **(arguments or {}))))
        envelope = response["structuredContent"]
        equal(previous.strict_loads(response["content"][0]["text"]), envelope, "envelope-equality")
        equal([envelope["operation"], envelope["source"]], [name, SOURCE], "source-operation-binding")
        check(not response.get("isError", False), "tool-success")
        check(not wire.schema_violations(schemas[name]["outputSchema"], envelope), "closed-output-schema")
        return envelope["result"]

    def inspect(label, texts, policy="fixed-v1", expectation=None, denied=False):
        arguments = {} if expectation is None else dict(expected_manifest_id=expectation)
        result = tool(label, "mousa_source_manifest", arguments)
        equal(result["decision_outcome"], "deny" if denied else "allow", "authorization")
        if denied:
            equal(sorted(result), ["decision_id", "decision_outcome", "decision_reasons"], "denied-masking")
            return None
        expected, inventory = canonical.expected(SOURCE, texts, policy)
        equal(result["manifest"], expected, "independent-current-inventory")
        equal(result["manifest"]["id"], canonical.manifest_id(result["manifest"]), "canonical-manifest-id")
        if expectation is None:
            check("matches" not in result, "export-omits-match")
        else:
            check(type(result.get("matches")) is bool, "explicit-match-boolean")
            equal(result["matches"], expectation == expected["id"], "expected-id-binding")
        rows.append(dict(label=label, manifest=expected, inventory=inventory,
                         **({} if expectation is None else dict(matches=result["matches"]))))
        return expected

    def sync(label, texts, policy="fixed-v1"):
        tool(label, "mousa_sync", dict(items=[dict(id=item, text=text) for item, text in texts.items()], segment_policy=policy))

    start("writer", True)
    sync("sync", FIXTURE)
    first = inspect("export", FIXTURE)
    inspect("match", FIXTURE, expectation=first["id"])
    sync("permuted-retry", dict(reversed(list(FIXTURE.items()))))
    inspect("retry", FIXTURE, expectation=first["id"])
    sync("omission", {"doc": FIXTURE["doc"]})
    inspect("omission-preserved", FIXTURE, expectation=first["id"])
    revised = dict(FIXTURE, doc="cedar revised")
    sync("revision", revised)
    inspect("mismatch", revised, expectation=first["id"])
    sync("passage", revised, "passage-v1")
    passage = inspect("segmentation", revised, "passage-v1", first["id"])
    native_mismatch = io("manifest-native", "native-mismatch",
                         arguments=["manifest", "--source", SOURCE, "--expect", first["id"]], expected_exit=1)
    equal(native_mismatch["manifest"], canonical.expected(SOURCE, revised, "passage-v1")[0], "native-current-inventory")
    equal(native_mismatch["matches"], False, "native-mismatch")
    tool("delete", "mousa_sync", dict(items=[dict(id="doc", deleted=True)], segment_policy="passage-v1"))
    inspect("deleted", {"empty": ""}, "passage-v1", passage["id"])
    sync("restore", FIXTURE)
    inspect("restored", FIXTURE, expectation=first["id"])
    io("stop", "writer/stop")
    native = io("native", "native-export", arguments=["manifest", "--source", SOURCE], stdin="", expected_exit=0, store_slot="STORE")
    equal(native["manifest"], first, "native-mcp-equality")
    native = io("native", "native-match", arguments=["manifest", "--source", SOURCE, "--expect", first["id"]], stdin="", expected_exit=0, store_slot="STORE")
    equal(native["matches"], True, "native-match")
    start("reader")
    inspect("reader-match", FIXTURE, expectation=first["id"])
    io("stop", "reader/stop")
    io("native", "deny-policy", arguments=["access", "--source", SOURCE, "deny"], stdin="", expected_exit=0, store_slot="STORE")
    start("denied")
    inspect("denied-check", FIXTURE, expectation=first["id"], denied=True)
    inspect("denied-export", FIXTURE, denied=True)
    io("stop", "denied/stop")
    native_denied = io("manifest-native", "native-denied",
                       arguments=["manifest", "--source", SOURCE, "--expect", first["id"]], expected_exit=1)
    equal(sorted(native_denied), ["decision_id", "decision_outcome", "decision_reasons"], "native-denied-masking")
    return dict(rows=rows, boundary="Small native/stdio JSONL observations only; no hostile storage, concurrency, HTTP, performance, semantic quality or action-completion claim.")


def verify(report, protocol):
    equal(protocol["implementations"], implementation(), "frozen-implementations")
    equal(protocol["golden"], canonical.expected(SOURCE, FIXTURE)[0], "independent-golden")
    equal(report["protocol_sha256"], wire.sha(wire.encoded(protocol)), "protocol-binding")
    equal([report["product"]["head"], report["product"]["tree"]], [protocol["product_head"], protocol["product_tree"]], "public-source-binding")
    wire.streams_valid(report)
    transcript = Transcript(report)
    summary = exercise(transcript)
    equal(transcript.index, len(report["events"]), "complete-events")
    equal(summary, report["summary"], "summary-binding")
    return summary


def controls(report, protocol):
    receipts = []
    for name, label, detector in (("current-pin", "export", "independent-current-inventory"),
                                  ("inventory-digest", "export", "independent-current-inventory"),
                                  ("expected-binding", "mismatch", "expected-id-binding"),
                                  ("denied-disclosure", "denied-check", "denied-masking")):
        changed = copy.deepcopy(report)
        event = next(event for event in changed["events"] if event["label"] == label)
        value = previous.shared.parsed(event["response"])
        envelope = value["result"]["structuredContent"]
        result = envelope["result"]
        if name in ("current-pin", "inventory-digest"):
            item = result["manifest"]["items"][0]
            item["representation_id" if name == "current-pin" else "segments_sha256"] = "a" * 64
            result["manifest"]["id"] = canonical.manifest_id(result["manifest"])
        elif name == "expected-binding":
            result["matches"] = True
        else:
            result["manifest"] = canonical.expected(SOURCE, FIXTURE)[0]
        value["result"]["content"][0]["text"] = wire.canonical(envelope)
        event["response"] = wire.stream(wire.encoded(value))
        try:
            verify(changed, protocol)
        except ValueError as error:
            equal(str(error), detector, "intended-control-detector")
            receipts.append(dict(control=name, detector=detector, rehashed_sha256=wire.sha(wire.encoded(changed))))
        else:
            raise ValueError("control-accepted")
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("freeze", "capture", "verify", "compare", "controls"))
    for name in ("protocol", "output", "other", "mousa", "product-source"):
        parser.add_argument("--" + name, type=Path, required=name == "protocol")
    parser.add_argument("--product-head")
    args = parser.parse_args()
    if args.mode in ("freeze", "capture"):
        def git(*arguments):
            return subprocess.check_output(["git", "-C", str(args.product_source), *arguments], text=True, timeout=30).strip()
        head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
        equal(head, args.product_head, "requested-public-head")
        equal(git("status", "--porcelain"), "", "clean-source")
        if args.mode == "freeze":
            check(not args.protocol.exists(), "new-protocol-only")
            wire.save(args.protocol, dict(product_head=head, product_tree=tree, implementations=implementation(),
                                         fixture=FIXTURE, golden=canonical.expected(SOURCE, FIXTURE)[0],
                                         status="exact-public-head-client-protocol"))
            return
    protocol = previous.strict_loads(args.protocol.read_bytes())
    if args.mode == "capture":
        equal([head, tree], [protocol["product_head"], protocol["product_tree"]], "capture-public-head")
        metadata = subprocess.check_output(["go", "version", "-m", str(args.mousa)], text=True, timeout=30)
        check("vcs.revision=" + head in metadata and "vcs.modified=false" in metadata and "CGO_ENABLED=0" in metadata, "public-binary-metadata")
        args.output.mkdir(parents=True, exist_ok=False)
        with tempfile.TemporaryDirectory(prefix="mousa-public-manifest-") as temporary:
            report = dict(protocol_sha256=wire.sha(wire.encoded(protocol)), paths=dict(BINARY=str(args.mousa.resolve()), STORE=str(Path(temporary) / "evidence.sqlite")), events=[], product=dict(head=head, tree=tree, binary_sha256=wire.sha(args.mousa.read_bytes()), build_metadata=metadata))
            transcript = Transcript(report, args.output)
            try:
                report["summary"] = exercise(transcript)
                verify(report, protocol)
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
        return
    report = previous.strict_loads((args.output / "capture.json").read_bytes())
    summary = verify(report, protocol)
    equal(summary, previous.strict_loads((args.output / "summary.json").read_bytes()), "saved-summary")
    if args.mode == "controls":
        print(json.dumps(controls(report, protocol)))
    elif args.mode == "compare":
        equal(summary, verify(previous.strict_loads((args.other / "capture.json").read_bytes()), protocol), "two-store-stability")
        print(json.dumps(dict(result="PASS", independent_stores=2)))
    else:
        print(json.dumps(dict(result="PASS", events=len(report["events"]))))


if __name__ == "__main__":
    main()
