"""Exact-public-head MCP administration capture using the frozen strict replay driver."""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("admin_replay_base",
    ROOT.parent / "token-association-supersession/capture.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
wire, shared, equal, check = base.wire, base.shared, base.equal, base.check
composition = base.composition
composition.DIRECTORY = "/tmp/mousa-public-admin-unused-notes"
original_implementation = base.implementation
SOURCE, PEER = composition.SOURCE, "synthetic-admin-peer"


def implementation():
    return original_implementation() | {
        "mcp-supersession-admin/capture.py": wire.sha(Path(__file__).read_bytes()),
        "mcp-supersession-admin/run-public.sh": wire.sha((ROOT / "run-public.sh").read_bytes())}


def strict_loads(text):
    return shared.parsed(wire.stream(text.encode() if isinstance(text, str) else text))


def exercise(io, encoder):
    rows, references = [], []
    schemas = {}

    def start(label, ingest=False, admin=False):
        arguments = ["mcp", "--caller", "cli", "--source", SOURCE, "--source", PEER,
            "--tokenizer-python", "TOKEN_PY", "--tokenizer-cache", "TOKEN_CACHE"]
        for enabled, flag in ((ingest, "--ingest-source"), (admin, "--supersession-admin-source")):
            if enabled:
                arguments += [flag, SOURCE, flag, PEER]
        io("start", label + "/start", arguments=arguments)
        io("rpc", label + "/initialize", method="initialize", params=dict(
            protocolVersion="2025-11-25", capabilities={},
            clientInfo=dict(name="mcp-supersession-admin", version="1")))
        io("rpc", label + "/initialized", method="notifications/initialized", params={})
        catalog = io("rpc", label + "/discovery", method="tools/list", params={})
        schemas.clear()
        schemas.update((tool["name"], tool) for tool in catalog["tools"])
        equal(sorted(schemas), sorted({"mousa_sync", "mousa_status", "mousa_query", "mousa_trail",
            "mousa_vector_query", "mousa_hybrid_query", "mousa_vector_inputs", "mousa_vector_import",
            "mousa_supersession_declare", "mousa_supersession_activate", "mousa_supersession_status"}),
            "discovery-tool-set")

    def tool(label, name, arguments=None, source=SOURCE, error=None):
        response = io("rpc", label, method="tools/call", params=dict(name=name,
            arguments=dict(source=source, **(arguments or {}))))
        envelope = response["structuredContent"]
        equal(shared.parsed(wire.stream(response["content"][0]["text"].encode())), envelope, "envelope-equality")
        equal([envelope["operation"], envelope["source"]], [name, source], "source-operation-binding")
        if error:
            equal([response.get("isError"), envelope.get("error", {}).get("code")], [True, error], "refusal-cause")
            check("result" not in envelope, "refusal-no-result")
        else:
            check(not response.get("isError", False), "tool-success")
        check(not wire.schema_violations(schemas[name]["outputSchema"], envelope), "closed-output-schema")
        return envelope.get("result")

    def status(label, state, activation=None, declaration=None):
        result = tool(label, "mousa_supersession_status")
        equal(result["decision_outcome"], "allow", "status-authorization")
        equal(result["current"], dict(state=state, activation=activation, declaration=declaration), "current-state")
        return result

    def draft(previous, declaration, timestamp):
        return dict(schema="mousa.supersession_activation_input.v1",
            expected_previous_activation_id=previous, declaration_id=declaration,
            actor_id="example.operator", actor_version="1", occurred_at_usec=timestamp, reason=None)

    def activate(label, supplied, error=None, source=SOURCE):
        result = tool(label, "mousa_supersession_activate", dict(activation=supplied), source=source, error=error)
        if error:
            return None
        canonical = dict(supplied, schema="mousa.supersession_activation.v1", source_id=sid)
        canonical["id"] = composition.identity(canonical["schema"], bytes.fromhex(sid),
            bytes.fromhex(supplied["expected_previous_activation_id"]) if supplied["expected_previous_activation_id"] else b"",
            bytes.fromhex(supplied["declaration_id"]) if supplied["declaration_id"] else b"")
        equal(result, dict(activation=canonical), "accepted-activation")
        return canonical

    def counted(result, label):
        context, token = result["context"], result["token"]
        passages = result["evidence"] + result.get("associated_evidence", [])
        equal(context, "\n\n".join(base.tokens.passage(token["source_id"], p) for p in passages), "whole-rendering")
        count = len(encoder.encode_ordinary(context))
        equal(token["measured_tokens"], count, "independent-count")
        equal(token["rendered_sha256"], wire.sha(context.encode()), "rendering-digest")
        equal(token["rendered_bytes"], len(context.encode()), "rendering-bytes")
        check(count <= token["limit"], "token-limit")
        references.append(dict(label=label, count=count, sha256=wire.sha(context.encode())))

    def evidence_facts(result):
        passages = result["evidence"] + result.get("associated_evidence", [])
        for passage in passages:
            item = passage["item"]
            check(item in pins, "evidence-pin-binding")
            text = composition.FIXTURE[item]
            equal([passage["text"], passage["content_sha256"], passage["representation_sha256"],
                   passage["byte_start"], passage["byte_end"]],
                  [text, wire.sha(text.encode()), wire.sha(text.encode()), 0,
                   len(text.encode())], "evidence-content-binding")
            if "byte_length" in passage:
                equal(passage["byte_length"], len(text.encode()), "evidence-content-binding")
            equal([passage["segment_id"], passage["representation_id"]],
                  [pins[item]["segment_id"], pins[item]["representation_id"]], "evidence-pin-binding")
        equal(result["used_bytes"], sum(len(p["text"].encode()) for p in passages), "retained-byte-accounting")

    start("ingest", ingest=True)
    tool("sync", "mousa_sync", dict(items=[dict(id=k, text=v) for k, v in composition.FIXTURE.items()]))
    tool("peer-sync", "mousa_sync", dict(items=[dict(id=k, text=v) for k, v in composition.FIXTURE.items()]), source=PEER)
    exported = tool("pins", "mousa_vector_inputs")
    pins = {p["item"]: p for p in exported["passages"]}
    equal(sorted(pins), sorted(composition.FIXTURE), "complete-source-population")
    sid = pins["old"]["source_id"]
    for item, pin in pins.items():
        text = composition.FIXTURE[item]
        equal([pin["text"], pin["content_sha256"], pin["representation_sha256"],
               pin["byte_start"], pin["byte_end"]],
              [text, wire.sha(text.encode()), wire.sha(text.encode()), 0,
               len(text.encode())], "exported-fixture-binding")
    declaration_draft = dict(schema="mousa.supersession_declaration_input.v1",
        predecessor_item_id="old", predecessor_representation_id=pins["old"]["representation_id"],
        successor_item_id="new", successor_representation_id=pins["new"]["representation_id"],
        author="example.operator", basis="Explicit replacement, not inferred truth")
    fields = ("source_id", "segment_id", "representation_id", "representation_sha256", "content_sha256")
    supplied = dict(schema="mousa.vector_import.v1", space=dict(schema="mousa.vector_space.v1",
        provider="synthetic", model="arithmetic-only", version="1", dimensions=2, metric="cosine"),
        embeddings=[dict(**{k: pins[item][k] for k in fields}, values=values)
            for item, values in (("primary", [1, 0]), ("new", [0, 1]))])
    imported = tool("import", "mousa_vector_import", {"import": supplied})
    tool("ingestion-only-refusal", "mousa_supersession_declare", dict(declaration=declaration_draft),
        error="supersession_admin_not_permitted")
    status("initial-status", "no_history")
    io("stop", "ingest/stop")
    start("reader")
    tool("reader-refusal", "mousa_supersession_declare", dict(declaration=declaration_draft),
        error="supersession_admin_not_permitted")
    status("reader-status", "no_history")
    io("stop", "reader/stop")
    start("admin", admin=True)
    tool("admin-no-ingestion", "mousa_sync", dict(items=[dict(id="forbidden", text="not ingested")]),
        error="ingestion_not_permitted")
    tool("unconfigured", "mousa_supersession_declare", dict(declaration=declaration_draft),
        source="unconfigured", error="source_not_permitted")
    declaration = tool("declare", "mousa_supersession_declare", dict(declaration=declaration_draft))["declaration"]
    expected = dict(declaration_draft, schema="mousa.supersession_declaration.v1", source_id=sid)
    expected["id"] = composition.identity(expected["schema"], bytes.fromhex(sid), "old",
        bytes.fromhex(expected["predecessor_representation_id"]), "new",
        bytes.fromhex(expected["successor_representation_id"]), expected["author"], expected["basis"])
    equal(declaration, expected, "accepted-declaration")
    equal(tool("declare-retry", "mousa_supersession_declare", dict(declaration=declaration_draft)),
          dict(declaration=declaration), "declaration-retry")
    tool("foreign-pins", "mousa_supersession_declare", dict(declaration=declaration_draft), source=PEER, error="integrity")
    initial_draft = draft(None, declaration["id"], 1)
    initial = activate("activate", initial_draft)
    equal(activate("current-retry", initial_draft), initial, "activation-retry")
    activate("metadata-conflict", dict(initial_draft, actor_id="changed"), error="conflict")
    activate("foreign-declaration", initial_draft, source=PEER, error="conflict")
    status("active-status", "active", initial, declaration)
    document = composition.document("")
    histories = []
    for mode in ("lexical", "vector", "hybrid"):
        for packing in ("original", "exact-v1"):
            for measured in (False, True):
                prefix = "/".join((mode, packing, "token" if measured else "byte"))
                arguments = dict(budget_bytes=8192, packing_policy=packing, associations=document)
                if mode != "vector":
                    arguments.update(query="instruction", policy="original")
                if mode != "lexical":
                    arguments.update(space_id=imported["space_id"], values=[1, 0])
                if measured:
                    arguments["context_tokens"] = 4096
                name = "mousa_query" if mode == "lexical" else "mousa_" + mode + "_query"
                omitted = tool(prefix + "/omitted", name, arguments)
                disabled = tool(prefix + "/false", name, dict(arguments, supersession=False))
                equal(composition.stable(omitted), composition.stable(disabled), "omitted-false-compatibility")
                full = tool(prefix + "/active", name, dict(arguments, supersession=True))
                support = full.get("associated_evidence", [p for p in full["evidence"] if p.get("origin") == "association"])
                equal([p["item"] for p in support], ["twin", "support"], "query-suppression")
                equal(full["association_omissions"][0]["reason"], "superseded", "query-suppression")
                check(all(p["segment_id"] not in {e["segment_id"] for e in supplied["embeddings"]}
                          for p in support), "unembedded-support")
                for result in (omitted, disabled, full):
                    evidence_facts(result)
                if measured:
                    for case, result in (("omitted", omitted), ("false", disabled), ("active", full)):
                        counted(result, prefix + "/" + case)
                history_args = dict(trail_id=full["trail_id"], supersession=True,
                    retrieval_details=True, token_details=measured)
                history = tool(prefix + "/history", "mousa_trail", history_args)
                h = history["historical"]
                equal([h["id"], h["decision_id"], h["packet_id"]],
                    [full["trail_id"], full["decision_id"], full["packet_id"]], "producing-identities")
                if "request_id" in full:
                    equal(h["request_id"], full["request_id"], "producing-request")
                equal(h["supersession"]["activation_id"], initial["id"], "producing-activation")
                equal(h["associated"][0]["omission"], "superseded", "history-suppression")
                selected_support = [row for row in h["associated"] if row["selected"]]
                equal([row["segment_id"] for row in selected_support],
                      [p["segment_id"] for p in support], "history-selected-support")
                for row in h["associated"]:
                    pin = pins[row["to_item"]]
                    equal([row["segment_id"], row["content_sha256"], row["text_bytes"]],
                          [pin["segment_id"], pin["content_sha256"], len(composition.FIXTURE[row["to_item"]].encode())],
                          "history-associated-pin-binding")
                version = ("13" if measured else "12") if mode == "lexical" else ("15" if measured else "14")
                equal(h["schema"], "mousa.source_trail.v" + version, "history-version")
                histories.append((prefix, history_args, h))
                rows.append(dict(label=prefix, result=composition.stable(full), history=composition.stable(history)))
    inactive = activate("deactivate", draft(initial["id"], None, 2))
    activate("older-retry", initial_draft, error="conflict")
    activate("stale-expectation", draft(initial["id"], declaration["id"], 3), error="conflict")
    status("deactivated-status", "deactivated", inactive)
    after = tool("after-deactivation", "mousa_query", dict(query="instruction", policy="original",
        budget_bytes=8192, packing_policy="exact-v1", associations=document, supersession=True))
    equal([p["item"] for p in after["evidence"]], ["primary", "old", "support"], "deactivation-selection")
    evidence_facts(after)
    for prefix, arguments, historical in histories:
        retained = tool(prefix + "/retained", "mousa_trail", arguments)
        equal(retained["historical"], historical, "retained-producing-history")
    io("stop", "admin/stop")
    # Policy setup is a separate native operator action; replacement remains MCP-only.
    io("native", "deny-policy", arguments=["access", "--source", SOURCE, "deny"], stdin="", expected_exit=0, store_slot="STORE")
    start("denied-admin", admin=True)
    reactivated = activate("denied-read-reactivation", draft(inactive["id"], declaration["id"], 4))
    denied = tool("denied-status", "mousa_supersession_status")
    equal(sorted(denied), sorted(["decision_id", "decision_outcome", "decision_reasons"]), "hidden-status-state")
    equal(denied["decision_outcome"], "deny", "denied-status-outcome")
    exported = tool("denied-export", "mousa_vector_inputs")
    equal([exported["decision_outcome"], exported["passages"]], ["deny", []], "admin-no-read-grant")
    io("stop", "denied-admin/stop")
    io("native", "allow-policy", arguments=["access", "--source", SOURCE, "allow"], stdin="", expected_exit=0, store_slot="STORE")
    start("final-reader")
    status("reactivated-status", "active", reactivated, declaration)
    io("stop", "final-reader/stop")
    return dict(rows=rows, independent_counts=references,
        assertions=["mcp-only-replacement", "separate-write-permissions", "exact-retries", "stale-conflicts",
                    "hidden-status-state", "query-suppression", "retained-producing-history", "whole-rendering"])


def controls(report, protocol, encoder, output):
    output.mkdir(exist_ok=False)
    receipts = []
    for name, label, detector in (
            ("expectation", "deactivate", "scheduled-request-bytes"),
            ("source", "unconfigured", "source-operation-binding"),
            ("unauthorized", "ingestion-only-refusal", "refusal-cause"),
            ("hidden-state", "denied-status", "hidden-status-state"),
            ("suppression", "vector/original/byte/active", "query-suppression"),
            ("wrong-text", "vector/original/byte/active", "evidence-content-binding"),
            ("wrong-pin", "vector/original/byte/active", "evidence-pin-binding")):
        changed = copy.deepcopy(report)
        event = next(e for e in changed["events"] if e["label"] == label)
        field = "request" if name == "expectation" else "response"
        value = shared.parsed(event[field])
        if name == "expectation":
            value["params"]["arguments"]["activation"]["expected_previous_activation_id"] = None
        else:
            envelope = value["result"]["structuredContent"]
            if name == "source":
                envelope["source"] = SOURCE
            elif name == "unauthorized":
                envelope["error"]["code"] = "conflict"
            elif name == "hidden-state":
                envelope["result"]["current"] = dict(state="no_history", activation=None, declaration=None)
            elif name == "wrong-text":
                envelope["result"]["evidence"][0]["text"] = "Substituted evidence."
            elif name == "wrong-pin":
                envelope["result"]["evidence"][0]["representation_id"] = "a" * 64
            else:
                envelope["result"]["associated_evidence"][0]["item"] = "old"
            value["result"]["content"][0]["text"] = wire.canonical(envelope)
        event[field] = wire.stream(wire.encoded(value))
        wire.save(output / (name + ".json"), changed)
        try:
            base.verify(changed, protocol, encoder)
        except ValueError as error:
            equal(str(error), detector, "intended-control-detector")
            receipts.append(dict(control=name, detector=detector, rehashed_sha256=wire.sha(wire.encoded(changed))))
        else:
            raise ValueError("control-accepted")
    return receipts


base.implementation = implementation
base.exercise = exercise
base.controls = controls
base.json = SimpleNamespace(loads=strict_loads, dumps=base.json.dumps)

if __name__ == "__main__":
    base.main()
