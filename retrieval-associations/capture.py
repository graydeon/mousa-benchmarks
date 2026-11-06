"""Additive v14/v15 capture; freeze only against the exact anonymous public head."""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("retrieval_support_base",
    ROOT.parent / "token-association-supersession/capture.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
wire, shared, equal, check = base.wire, base.shared, base.equal, base.check
composition = base.composition
composition.DIRECTORY = "/tmp/mousa-public-retrieval-support-notes"
original_implementation = base.implementation


def implementation():
    return original_implementation() | {
        "retrieval-associations/capture.py": wire.sha(Path(__file__).read_bytes()),
        "retrieval-associations/run-public.sh": wire.sha((ROOT / "run-public.sh").read_bytes())}


def strict_loads(text):
    return shared.parsed(wire.stream(text.encode() if isinstance(text, str) else text))


def exercise(io, encoder):
    rows, references = [], []

    def native(label, args, value=""):
        return io("native", label, arguments=args, stdin=value, expected_exit=0, store_slot="STORE")

    def counted(result, label):
        context, token = result["context"], result["token"]
        passages = result["evidence"] + result.get("associated_evidence", [])
        normalized = [dict(segment_id=p["segment"]["id"], content_sha256=p["segment"]["content_sha256"],
                           text=p["text"]) if "segment" in p else p for p in passages]
        equal(context, "\n\n".join(base.tokens.passage(token["source_id"], p) for p in normalized), "whole-rendering")
        count = len(encoder.encode_ordinary(context))
        equal(token["measured_tokens"], count, "independent-count")
        equal(token["rendered_sha256"], wire.sha(context.encode()), "rendering-digest")
        equal(token["rendered_bytes"], len(context.encode()), "rendering-bytes")
        check(count <= token["limit"], "token-limit")
        references.append(dict(label=label, count=count, sha256=wire.sha(context.encode())))

    for form in ("jsonl", "directory"):
        suffix = ".txt" if form == "directory" else ""
        selector = [composition.DIRECTORY] if suffix else ["--source", composition.SOURCE]
        schemas = {}
        if form == "jsonl":
            io("start", "mcp/start", arguments=["mcp", "--caller", "cli", "--source", composition.SOURCE,
                "--ingest-source", composition.SOURCE, "--tokenizer-python", "TOKEN_PY", "--tokenizer-cache", "TOKEN_CACHE"])
            io("rpc", "initialize", method="initialize", params=dict(protocolVersion="2025-11-25", capabilities={},
                clientInfo=dict(name="retrieval-associations", version="1")))
            io("rpc", "initialized", method="notifications/initialized", params={})
            catalog = io("rpc", "discovery", method="tools/list", params={})
            schemas = {t["name"]: t for t in catalog["tools"]}

        def tool(label, name, arguments):
            result = io("rpc", label, method="tools/call", params=dict(name=name,
                arguments=dict(source=composition.SOURCE, **arguments)))
            envelope = result["structuredContent"]
            equal(shared.parsed(wire.stream(result["content"][0]["text"].encode())), envelope, "envelope-equality")
            check(not wire.schema_violations(schemas[name]["outputSchema"], envelope), "closed-output-schema")
            equal(envelope["operation"], name, "operation-binding")
            check(not result.get("isError", False), "tool-success")
            return envelope["result"]

        if form == "jsonl":
            tool("jsonl/sync", "mousa_sync", dict(items=[dict(id=k, text=v) for k, v in composition.FIXTURE.items()]))
            exported = tool("jsonl/pins", "mousa_vector_inputs", {})
        else:
            native("directory/sync", ["sync", *selector])
            exported = native("directory/pins", ["vector", "inputs", *selector])
        pins = {p["item"]: p for p in exported["passages"]}
        equal(sorted(pins), sorted(k + suffix for k in composition.FIXTURE), "complete-source-population")
        fields = ("source_id", "segment_id", "representation_id", "representation_sha256", "content_sha256")
        supplied = dict(schema="mousa.vector_import.v1", space=dict(schema="mousa.vector_space.v1",
            provider="synthetic", model="arithmetic-only", version="1", dimensions=2, metric="cosine"),
            embeddings=[dict(**{k: pins[item + suffix][k] for k in fields}, values=values)
                for item, values in (("primary", [1, 0]), ("new", [0, 1]))])
        if form == "jsonl":
            imported = tool("jsonl/import", "mousa_vector_import", {"import": supplied})
        else:
            imported = native("directory/import", ["vector", "import", *selector], wire.encoded(supplied).decode())
        old, new = "old" + suffix, "new" + suffix
        sid = pins[old]["source_id"]
        declaration = dict(schema="mousa.supersession_declaration.v1", source_id=sid,
            predecessor_item_id=old, predecessor_representation_id=pins[old]["representation_id"],
            successor_item_id=new, successor_representation_id=pins[new]["representation_id"],
            author="example.maintainer", basis="Explicit replacement, not inferred truth")
        declaration["id"] = composition.identity(declaration["schema"], bytes.fromhex(sid), old,
            bytes.fromhex(declaration["predecessor_representation_id"]), new,
            bytes.fromhex(declaration["successor_representation_id"]), declaration["author"], declaration["basis"])
        native(form + "/declaration", ["supersession", "declaration", "put"], wire.encoded(declaration).decode())
        activation = dict(schema="mousa.supersession_activation.v1", source_id=sid,
            expected_previous_activation_id=None, declaration_id=declaration["id"], actor_id="example.maintainer",
            actor_version="1", occurred_at_usec=1, reason="Explicit replacement")
        activation["id"] = composition.identity(activation["schema"], bytes.fromhex(sid), b"", bytes.fromhex(declaration["id"]))
        native(form + "/activation", ["supersession", "activation", "put"], wire.encoded(activation).decode())
        document = composition.document(suffix)
        path = io("file", form, document=document)
        for surface in (("native", "mcp") if form == "jsonl" else ("native",)):
            for mode in ("vector", "hybrid"):
                for packing in ("original", "exact-v1"):
                    for measured in (False, True):
                        prefix = "/".join((form, surface, mode, packing, "token" if measured else "byte"))
                        flags = ["--context-tokens", "4096", "--tokenizer-python", "TOKEN_PY",
                                 "--tokenizer-cache", "TOKEN_CACHE"] if measured else []

                        def query(case, support=True, supersession=True):
                            label = prefix + "/" + case
                            if surface == "mcp":
                                arguments = dict(space_id=imported["space_id"], values=[1, 0],
                                    budget_bytes=8192, packing_policy=packing)
                                if supersession is not None:
                                    arguments["supersession"] = supersession
                                if mode == "hybrid":
                                    arguments.update(query="instruction", policy="original")
                                if measured:
                                    arguments["context_tokens"] = 4096
                                if support:
                                    arguments["associations"] = document
                                result = tool(label, "mousa_" + mode + "_query", arguments)
                            else:
                                args = ["query", "--" + mode + "-space", imported["space_id"],
                                    "--packing-policy", packing, "--budget-bytes", "8192", *flags]
                                if supersession is not None:
                                    args += ["--supersession=" + str(supersession).lower()]
                                if support:
                                    args += ["--associations", path]
                                result = native(label, [*args, *selector, *(["instruction"] if mode == "hybrid" else [])],
                                    '{"schema":"mousa.vector_query.v1","values":[1,0]}')
                            if measured:
                                counted(result, label)
                            rows.append(dict(label=label, result=composition.stable(result)))
                            return result

                        baseline = query("baseline", support=False)
                        full = query("full")
                        equal(full["evidence"], baseline["evidence"], "primary-rank-preservation")
                        retrieval = full[mode] if mode in full else full
                        baseline_retrieval = baseline[mode] if mode in baseline else baseline
                        for field in ("eligible", "indexed", "query_vector_id"):
                            equal(retrieval[field], baseline_retrieval[field], "retrieval-rank-coverage-preservation")
                        if mode in full:
                            equal(full[mode], baseline[mode], "retrieval-rank-coverage-preservation")
                        support = full["associated_evidence"]
                        equal(sorted(p["item"] for p in support), sorted(("twin" + suffix, "support" + suffix)), "unembedded-support")
                        embedded = {p["segment_id"] for p in supplied["embeddings"]}
                        check(all(p["segment_id"] not in embedded for p in support), "unembedded-support-pins")
                        check(all(p["origin"] == "association" and "rank" not in p and "bm25_score" not in p
                                  for p in support), "support-no-invented-ranks")
                        equal(full["used_bytes"], sum(len(p["text"].encode()) for p in full["evidence"] + support), "byte-accounting")
                        equal(full["association_omissions"][0]["reason"], "superseded", "target-suppression")
                        omitted = query("omitted", supersession=None)
                        disabled = query("false", supersession=False)
                        equal(composition.stable(omitted), composition.stable(disabled), "omitted-false-compatibility")
                        if surface == "mcp":
                            history = tool(prefix + "/history", "mousa_trail", dict(trail_id=full["trail_id"],
                                retrieval_details=True, token_details=measured, supersession=True))
                        else:
                            history = native(prefix + "/history", ["trail", *selector, full["trail_id"]])
                        h = history["historical"]
                        equal([retrieval["eligible"], retrieval["indexed"]], [5, 2], "full-source-coverage")
                        equal(h["schema"], "mousa.source_trail.v" + ("15" if measured else "14"), "history-version")
                        if mode in full:
                            equal(h[mode], full[mode], "history-retrieval")
                        else:
                            for field in ("eligible", "indexed", "query_vector_id"):
                                equal(h[mode][field], full[field], "history-retrieval")
                        equal(h["packet_id"], full["packet_id"], "producing-packet")
                        equal(h["associated"][0]["omission"], "superseded", "history-target-suppression")
                        rows.append(dict(label=prefix + "/history", result=composition.stable(history)))
                        if measured:
                            recount = native(prefix + "/recount", ["trail", "--verify-tokens", *flags[2:], *selector, full["trail_id"]])
                            equal(recount["historical"]["token_verification"], "official_recount_verified", "native-recount")
                            equal(recount["historical"]["token"], full["token"], "recount-facts")
        if form == "jsonl":
            io("stop", "mcp/stop")
    return dict(rows=rows, independent_counts=references,
        assertions=["primary-rank-preservation", "retrieval-rank-coverage-preservation", "unembedded-support",
                    "whole-rendering", "native-recount", "omitted-false-compatibility"])


def controls(report, protocol, encoder, output):
    output.mkdir(exist_ok=False)
    receipts = []
    for name, detector in (("count", "independent-count"), ("support", "unembedded-support"),
                           ("history", "history-target-suppression"), ("duplicate", "strict-json")):
        changed = copy.deepcopy(report)
        label = "jsonl/mcp/vector/original/token/" + ("history" if name == "history" else "full")
        event = next(e for e in changed["events"] if e["label"] == label)
        value = shared.parsed(event["response"])
        envelope = value["result"]["structuredContent"]
        if name == "count":
            envelope["result"]["token"]["measured_tokens"] += 1
        elif name == "support":
            envelope["result"]["associated_evidence"][0]["item"] = "invented"
        elif name == "history":
            envelope["result"]["historical"]["associated"][0]["omission"] = "duplicate"
        value["result"]["content"][0]["text"] = wire.canonical(envelope)
        if name == "duplicate":
            value["result"]["content"][0]["text"] = '{"schema":"duplicate",' + wire.canonical(envelope).lstrip()[1:]
        event["response"] = wire.stream(wire.encoded(value))
        wire.save(output / (name + ".json"), changed)
        try:
            base.verify(changed, protocol, encoder)
        except ValueError as error:
            equal(str(error), detector, "intended-control-detector")
            receipts.append(dict(control=name, detector=detector, rehashed_sha256=wire.sha(wire.encoded(changed))))
        else:
            raise ValueError("control-accepted")
    malformed = '{"product_head":"conflicting",' + wire.canonical(protocol).lstrip()[1:]
    (output / "outer-duplicate.json").write_text(malformed, encoding="utf-8")
    try:
        strict_loads(malformed)
    except ValueError as error:
        equal(str(error), "strict-json", "outer-duplicate-detector")
        receipts.append(dict(control="outer-duplicate", detector="strict-json",
                             rehashed_sha256=wire.sha(malformed.encode())))
    else:
        raise ValueError("outer-duplicate-accepted")
    return receipts


base.implementation = implementation
base.exercise = exercise
base.controls = controls
# Scope strict loading to this additive entry point; frozen producers are unchanged.
base.json = SimpleNamespace(loads=strict_loads, dumps=base.json.dumps)

if __name__ == "__main__":
    base.main()
