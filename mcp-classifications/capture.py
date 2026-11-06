"""Additive exact-public-head MCP classification capture and strict replay."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("classification_replay_base", ROOT.parent / "token-association-supersession/capture.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
wire, shared, equal, check = base.wire, base.shared, base.equal, base.check
SOURCE, PEER = "synthetic-mcp-classifications", "synthetic-classification-peer"
TEXT = "cedar synthetic evidence; no factual review or classifier is involved"
TOOLS = {"mousa_sync", "mousa_status", "mousa_query", "mousa_trail", "mousa_vector_query", "mousa_hybrid_query", "mousa_vector_inputs", "mousa_vector_import", "mousa_supersession_declare", "mousa_supersession_activate", "mousa_supersession_status", "mousa_classification_put", "mousa_classification_get"}


def strict_loads(text):
    return shared.parsed(wire.stream(text.encode() if isinstance(text, str) else text))


def canonical(draft):
    check(type(draft.get("confidence_ppm")) is int, "confidence-integer")
    check(0 <= draft["confidence_ppm"] <= 1000000, "confidence-range")
    check(type(draft.get("asserted_at_usec")) is int, "timestamp-integer")
    fields = ["mousa.classification.v1", draft["subject"]["kind"], bytes.fromhex(draft["subject"]["id"])]
    fields += [draft[k] for k in ("taxonomy", "taxonomy_version", "label", "asserter_id", "asserter_version")]
    fields += [draft[k].to_bytes(8, "big") for k in ("asserted_at_usec", "confidence_ppm")]
    fields += [len(draft["basis"]).to_bytes(8, "big")]
    for entry in draft["basis"]:
        fields += [entry["kind"], bytes.fromhex(entry["id"])]
    return dict(draft, schema="mousa.classification.v1", id=base.composition.identity(*fields))


def accepted(record, draft):
    check(type(record.get("confidence_ppm")) is int, "confidence-integer")
    equal(wire.canonical(record), wire.canonical(canonical(draft)), "canonical-assertion-binding")
    return record


def exercise(io):
    schemas = {}

    def start(label, ingest=False, admin=False):
        argv = ["mcp", "--caller", "cli", "--source", SOURCE, "--source", PEER]
        for enabled, flag in ((ingest, "--ingest-source"), (admin, "--classification-admin-source")):
            if enabled:
                argv += [flag, SOURCE, flag, PEER]
        io("start", label + "/start", arguments=argv)
        io("rpc", label + "/initialize", method="initialize", params=dict(protocolVersion="2025-11-25", capabilities={}, clientInfo=dict(name="mcp-classifications", version="1")))
        io("rpc", label + "/initialized", method="notifications/initialized", params={})
        catalog = io("rpc", label + "/discovery", method="tools/list", params={})
        equal(len(catalog["tools"]), 13, "discovery-count")
        schemas.update((t["name"], t) for t in catalog["tools"])
        equal(sorted(schemas), sorted(TOOLS), "discovery-tools")

    def tool(label, name, arguments=None, source=SOURCE, error=None):
        response = io("rpc", label, method="tools/call", params=dict(name=name, arguments=dict(source=source, **(arguments or {}))))
        envelope = response["structuredContent"]
        equal(strict_loads(response["content"][0]["text"]), envelope, "envelope-equality")
        equal([envelope["operation"], envelope["source"]], [name, source], "source-operation-binding")
        if error:
            equal([response.get("isError"), envelope.get("error", {}).get("code")], [True, error], "refusal-cause")
            check("result" not in envelope, "refusal-no-result")
        else:
            check(not response.get("isError", False), "tool-success")
        return envelope.get("result")

    def put(label, draft):
        return accepted(tool(label, "mousa_classification_put", dict(classification=draft))["classification"], draft)

    def get(label, record, denied=False, source=SOURCE, error=None):
        result = tool(label, "mousa_classification_get", dict(classification_id=record["id"]), source=source, error=error)
        if error:
            return
        equal(result["decision_outcome"], "deny" if denied else "allow", "get-authorization")
        check(isinstance(result["decision_id"], str) and len(result["decision_id"]) == 64, "decision-id")
        if denied:
            equal(sorted(result), sorted({"decision_id", "decision_outcome", "decision_reasons"}), "denied-no-payload")
        else:
            check(type(result["classification"].get("confidence_ppm")) is int, "confidence-integer")
            equal(result["classification"], record, "get-record-binding")

    query = dict(query="cedar", policy="original", budget_bytes=8192)
    start("ingest", ingest=True)
    tool("sync", "mousa_sync", dict(items=[dict(id="doc", text=TEXT)]))
    tool("peer-sync", "mousa_sync", dict(items=[dict(id="doc", text=TEXT)]), source=PEER)
    exported = tool("export", "mousa_vector_inputs")
    equal(exported["decision_outcome"], "allow", "export-authorization")
    equal(len(exported["passages"]), 1, "one-exported-pin")
    pin = exported["passages"][0]
    equal([pin["item"], pin["text"], pin["content_sha256"], pin["representation_sha256"], pin["byte_start"], pin["byte_end"]], ["doc", TEXT, wire.sha(TEXT.encode()), wire.sha(TEXT.encode()), 0, len(TEXT.encode())], "export-content-binding")
    before = tool("before", "mousa_query", query)
    evidence = before["evidence"][0]
    equal([evidence[k] for k in ("segment_id", "representation_id", "text")], [pin[k] for k in ("segment_id", "representation_id", "text")], "query-pin-binding")
    draft = dict(schema="mousa.classification_input.v1", subject=dict(kind="segment", id=pin["segment_id"]), taxonomy="example.caller-review", taxonomy_version="1", label="synthetic-caller-reviewed", asserter_id="example.caller", asserter_version="1", asserted_at_usec=1, confidence_ppm=0, basis=[dict(kind="representation", id=pin["representation_id"]), dict(kind="source", id=pin["source_id"])])
    tool("ingest-refusal", "mousa_classification_put", dict(classification=draft), error="classification_admin_not_permitted")
    io("stop", "ingest/stop")
    start("admin", admin=True)
    tool("admin-no-ingestion", "mousa_sync", dict(items=[dict(id="forbidden", text="not stored")]), error="ingestion_not_permitted")
    tool("unconfigured", "mousa_classification_put", dict(classification=draft), source="unconfigured", error="source_not_permitted")
    first = put("put", draft)
    equal(put("retry", draft), first, "exact-retry")
    get("get", first)
    second = put("second", dict(draft, asserter_version="2", label="synthetic-disputed", asserted_at_usec=2))
    check(first["id"] != second["id"], "distinct-assertion")
    get("first-retained", first)
    get("second-get", second)
    get("foreign-get", first, source=PEER, error="not_found")
    after = tool("after", "mousa_query", query)
    stable = base.composition.stable
    equal(stable(before), stable(after), "unchanged-query")
    io("stop", "admin/stop")
    start("reader")
    get("reader-get", first)
    tool("reader-refusal", "mousa_classification_put", dict(classification=draft), error="classification_admin_not_permitted")
    io("stop", "reader/stop")
    # Native policy administration is setup only, never classification administration.
    io("native", "deny-policy", arguments=["access", "--source", SOURCE, "deny"], stdin="", expected_exit=0, store_slot="STORE")
    start("denied-admin", admin=True)
    equal(put("denied-put-retry", draft), first, "admin-independent-of-read")
    get("denied-get", first, denied=True)
    get("denied-unknown", dict(id="a" * 64), denied=True)
    io("stop", "denied-admin/stop")
    return dict(first=first, second=second, pins=pin, query=stable(before), independent_counts=[], boundary="Segment subject with ordered representation/source basis; stdio only, no token queries or semantic assessment.")


def implementation():
    return base.implementation() | {"mcp-classifications/" + name: wire.sha((ROOT / name).read_bytes()) for name in ("capture.py", "run-public.sh", "test_capture.py")}


def verify(report, protocol):
    equal(protocol["implementations"], implementation(), "frozen-implementations")
    equal(report["protocol_sha256"], wire.sha(wire.encoded(protocol)), "protocol-binding")
    equal([report["product"]["head"], report["product"]["tree"]], [protocol["product_head"], protocol["product_tree"]], "public-source-binding")
    wire.streams_valid(report)
    transcript = base.Transcript(report)
    summary = exercise(transcript)
    equal(transcript.index, len(report["events"]), "complete-events")
    equal(summary, report["summary"], "summary-binding")
    return summary


def controls(report, protocol, output):
    output.mkdir(exist_ok=False)
    receipts = []
    cases = [("request", "put", "scheduled-request-bytes"), ("scope", "foreign-get", "source-operation-binding"), ("authorization", "denied-get", "get-authorization"), ("label", "put", "canonical-assertion-binding"), ("confidence", "put", "canonical-assertion-binding"), ("basis", "put", "canonical-assertion-binding"), ("id", "put", "canonical-assertion-binding"), ("pin", "before", "query-pin-binding"), ("confidence-bool", "put", "confidence-integer"), ("duplicate", "put", "strict-json")]
    for name, label, detector in cases:
        changed = copy.deepcopy(report)
        event = next(e for e in changed["events"] if e["label"] == label)
        field = "request" if name == "request" else "response"
        value = shared.parsed(event[field])
        if name == "request":
            value["params"]["arguments"]["classification"]["confidence_ppm"] = 1
        else:
            envelope = value["result"]["structuredContent"]
            if name == "scope":
                envelope["source"] = SOURCE
            elif name == "authorization":
                envelope["result"]["decision_outcome"] = "allow"
            elif name == "pin":
                envelope["result"]["evidence"][0]["segment_id"] = "a" * 64
            elif name != "duplicate":
                record = envelope["result"]["classification"]
                if name == "label":
                    record["label"] = "substituted"
                elif name == "basis":
                    record["basis"].reverse()
                elif name == "id":
                    record["id"] = "a" * 64
                else:
                    record["confidence_ppm"] = False if name == "confidence-bool" else 1
            value["result"]["content"][0]["text"] = wire.canonical(envelope)
            if name == "duplicate":
                value["result"]["content"][0]["text"] = '{"schema":"duplicate",' + value["result"]["content"][0]["text"][1:]
        event[field] = wire.stream(wire.encoded(value))
        wire.save(output / (name + ".json"), changed)
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
        def git(*argv):
            return subprocess.check_output(["git", "-C", str(args.product_source), *argv], text=True, timeout=30).strip()
        head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
        equal(head, args.product_head, "requested-public-head")
        equal(git("status", "--porcelain"), "", "clean-source")
        if args.mode == "freeze":
            check(not args.protocol.exists(), "new-protocol-only")
            wire.save(args.protocol, dict(product_head=head, product_tree=tree, implementations=implementation(), fixture=TEXT, status="exact-public-head-client-protocol"))
            return
    protocol = strict_loads(args.protocol.read_bytes())
    if args.mode == "capture":
        equal([head, tree], [protocol["product_head"], protocol["product_tree"]], "capture-public-head")
        metadata = subprocess.check_output(["go", "version", "-m", str(args.mousa)], text=True, timeout=30)
        check("vcs.revision=" + head in metadata and "vcs.modified=false" in metadata and "CGO_ENABLED=0" in metadata, "public-binary-metadata")
        args.output.mkdir(parents=True, exist_ok=False)
        with tempfile.TemporaryDirectory(prefix="mousa-public-classifications-") as temporary:
            report = dict(protocol_sha256=wire.sha(wire.encoded(protocol)), paths=dict(BINARY=str(args.mousa.resolve()), STORE=str(Path(temporary) / "evidence.sqlite")), events=[], product=dict(head=head, tree=tree, binary_sha256=wire.sha(args.mousa.read_bytes()), build_metadata=metadata))
            transcript = base.Transcript(report, args.output)
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
    report = strict_loads((args.output / "capture.json").read_bytes())
    summary = verify(report, protocol)
    equal(summary, strict_loads((args.output / "summary.json").read_bytes()), "saved-summary")
    if args.mode == "controls":
        print(json.dumps(controls(report, protocol, args.output / "controls")))
    elif args.mode == "compare":
        equal(summary, verify(strict_loads((args.other / "capture.json").read_bytes()), protocol), "two-store-stability")
        print(json.dumps(dict(result="PASS", independent_stores=2, independent_counts=0)))
    else:
        print(json.dumps(dict(result="PASS", events=len(report["events"]), independent_counts=0)))


if __name__ == "__main__":
    main()
