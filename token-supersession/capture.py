"""Capture native/MCP lexical supersession with independently counted token contexts."""

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "token_capture", ROOT.parent / "mcp-tokens/capture.py"
)
tokens = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tokens)
shared, wire, check, equal = tokens.shared, tokens.wire, tokens.check, tokens.equal
SOURCE = "synthetic-token-supersession"
FIXTURE = {
    "old.md": "Drain legacy",
    "twin.md": "Drain legacy",
    "new.md": "Drain correction",
}
BOUNDARY_BLOCK = "boundaryold " + "x" * 4084
BOUNDARY_FIXTURE = {
    "old.md": BOUNDARY_BLOCK * 65,
    "new.md": "boundarynew successor",
    "twin.md": "boundarysmall survivor",
}


def boundary_pins(results):
    source = identity("mousa.source.v1", "mousa-jsonl", SOURCE)
    return [
        dict(p, source_id=source)
        for name in ("old", "new", "survivor")
        for p in results.get("boundary/" + name + "-pin", {}).get("evidence", [])
    ]


def identity(*fields):
    digest = hashlib.sha256()
    for field in fields:
        value = field.encode() if isinstance(field, str) else field
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
    return digest.hexdigest()


def administration(exported, previous=None, enabled=True, time=1):
    pins = {p["item"]: p for p in exported.get("passages", [])}
    old, new = pins.get("old.md", {}), pins.get("new.md", {})
    sid, pred, succ = (
        old.get("source_id", "00" * 32),
        old.get("representation_id", "00" * 32),
        new.get("representation_id", "00" * 32),
    )
    declaration = dict(
        schema="mousa.supersession_declaration.v1",
        source_id=sid,
        predecessor_item_id="old.md",
        predecessor_representation_id=pred,
        successor_item_id="new.md",
        successor_representation_id=succ,
        author="example.operator",
        basis="new.md explicitly replaces old.md",
    )
    declaration["id"] = identity(
        declaration["schema"],
        bytes.fromhex(sid),
        "old.md",
        bytes.fromhex(pred),
        "new.md",
        bytes.fromhex(succ),
        declaration["author"],
        declaration["basis"],
    )
    activation = dict(
        schema="mousa.supersession_activation.v1",
        source_id=sid,
        expected_previous_activation_id=previous,
        declaration_id=declaration["id"] if enabled else None,
        actor_id="example.operator",
        actor_version="1",
        occurred_at_usec=time,
        reason="explicit selection",
    )
    activation["id"] = identity(
        activation["schema"],
        bytes.fromhex(sid),
        bytes.fromhex(previous) if previous else b"",
        bytes.fromhex(declaration["id"]) if enabled else b"",
    )
    return declaration, activation


def off_id(results):
    _, active = administration(results.get("jsonl/export", {}))
    return administration(results.get("jsonl/export", {}), active["id"], False, 2)[1][
        "id"
    ]


def schedule(results, encoder):
    events = []

    def native(label, form, args, value=None, expected_error=None):
        events.append(
            dict(
                kind="native",
                label=label,
                form=form,
                arguments=args,
                stdin="" if value is None else value,
            )
        )
        if expected_error is not None:
            events[-1]["expected_error"] = expected_error

    def rpc(label, method, params):
        events.append(dict(kind="rpc", label=label, method=method, params=params))

    def tool(label, name, **args):
        rpc(
            label,
            "tools/call",
            {"name": name, "arguments": dict(source=SOURCE, **args)},
        )

    def start(label):
        events.append(
            dict(
                kind="start",
                label=label,
                arguments=[
                    "mcp",
                    "--caller",
                    "cli",
                    "--source",
                    SOURCE,
                    "--tokenizer-python",
                    "TOKEN_PY",
                    "--tokenizer-cache",
                    "TOKEN_CACHE",
                ],
            )
        )
        rpc(
            label + "/initialize",
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "combined-token-capture", "version": "1"},
            },
        )
        rpc(label + "/initialized", "notifications/initialized", {})
        rpc(label + "/discovery", "tools/list", {})

    def stop(label):
        events.append(dict(kind="stop", label=label))

    for form in ("directory", "jsonl"):
        selector = ["DIRECTORY"] if form == "directory" else ["--source", SOURCE]
        if form == "directory":
            native(form + "/sync", form, ["sync", *selector])
        else:
            native(
                form + "/sync",
                form,
                ["sync", *selector],
                "".join(
                    wire.canonical(dict(id=k, text=v)) + "\n"
                    for k, v in FIXTURE.items()
                ),
            )
        native(form + "/export", form, ["vector", "inputs", *selector])
        query = [
            "query",
            "--context-tokens",
            "4096",
            "--tokenizer-python",
            "TOKEN_PY",
            "--tokenizer-cache",
            "TOKEN_CACHE",
        ]
        native(
            form + "/no-history", form, [*query, "--supersession", *selector, "Drain"]
        )
        declaration, activation = administration(results.get(form + "/export", {}))
        native(
            form + "/declaration",
            form,
            ["supersession", "declaration", "put"],
            wire.canonical(declaration),
        )
        native(
            form + "/activation",
            form,
            ["supersession", "activation", "put"],
            wire.canonical(activation),
        )
        for packing in ("original", "exact-v1"):
            label = form + "/" + packing
            native(
                label + "/active",
                form,
                [
                    *query,
                    "--supersession",
                    "--packing-policy",
                    packing,
                    *selector,
                    "Drain",
                ],
            )
            produced = results.get(label + "/active", {})
            native(
                label + "/history",
                form,
                ["trail", *selector, produced.get("trail_id", "PENDING")],
            )
            native(
                label + "/recount",
                form,
                [
                    "trail",
                    "--verify-tokens",
                    "--tokenizer-python",
                    "TOKEN_PY",
                    "--tokenizer-cache",
                    "TOKEN_CACHE",
                    *selector,
                    produced.get("trail_id", "PENDING"),
                ],
            )
    start("active")
    for packing in ("original", "exact-v1"):
        label = "mcp/" + packing
        args = dict(
            query="Drain",
            policy="original",
            budget_bytes=4096,
            context_tokens=4096,
            supersession=True,
            packing_policy=packing,
        )
        tool(label + "/full", "mousa_query", **args)
        produced = results.get(label + "/full", {})
        count = len(encoder.encode_ordinary(produced.get("context", ""))) or 1
        for suffix, extra in (
            ("exact", dict(context_tokens=count)),
            ("short", dict(context_tokens=count - 1)),
            (
                "reserved",
                dict(
                    window_tokens=count + 50,
                    prompt_reserve_tokens=20,
                    output_reserve_tokens=31,
                ),
            ),
        ):
            tool(label + "/" + suffix, "mousa_query", **dict(args, **extra))
        for suffix, extra in (
            ("default", {}),
            ("token", dict(token_details=True)),
            ("supersession", dict(supersession=True)),
            ("both", dict(token_details=True, supersession=True)),
        ):
            tool(
                label + "/history-" + suffix,
                "mousa_trail",
                trail_id=produced.get("trail_id", "PENDING"),
                **extra,
            )
    stop("active-exit")
    native(
        "jsonl/remove-survivors",
        "jsonl",
        ["sync", "--source", SOURCE],
        '{"id":"twin.md","deleted":true}\n{"id":"new.md","deleted":true}\n',
    )
    start("withheld")
    tool(
        "mcp/all-withheld",
        "mousa_query",
        query="legacy",
        policy="original",
        budget_bytes=1,
        context_tokens=1,
        supersession=True,
    )
    stop("withheld-exit")
    _, active = administration(results.get("jsonl/export", {}))
    _, off = administration(results.get("jsonl/export", {}), active["id"], False, 2)
    native(
        "jsonl/deactivate",
        "jsonl",
        ["supersession", "activation", "put"],
        wire.canonical(off),
    )
    start("deactivated")
    tool(
        "mcp/deactivated",
        "mousa_query",
        query="legacy",
        policy="original",
        budget_bytes=4096,
        context_tokens=4096,
        supersession=True,
    )
    tool(
        "mcp/old-history",
        "mousa_trail",
        trail_id=results.get("mcp/original/full", {}).get("trail_id", "PENDING"),
        supersession=True,
        token_details=True,
    )
    stop("deactivated-exit")
    native(
        "boundary/sync",
        "jsonl",
        ["sync", "--source", SOURCE],
        "".join(
            wire.canonical(dict(id=k, text=v)) + "\n"
            for k, v in BOUNDARY_FIXTURE.items()
        ),
    )
    for name, query_text in (
        ("old", "boundaryold"),
        ("new", "boundarynew"),
        ("survivor", "boundarysmall"),
    ):
        native(
            "boundary/" + name + "-pin",
            "jsonl",
            ["query", "--source", SOURCE, query_text],
        )
    declaration, activation = administration(
        {"passages": boundary_pins(results)}, off["id"], True, 3
    )
    native(
        "boundary/declaration",
        "jsonl",
        ["supersession", "declaration", "put"],
        wire.canonical(declaration),
    )
    native(
        "boundary/activation",
        "jsonl",
        ["supersession", "activation", "put"],
        wire.canonical(activation),
    )
    query = [
        "query",
        "--context-tokens",
        "4096",
        "--tokenizer-python",
        "TOKEN_PY",
        "--tokenizer-cache",
        "TOKEN_CACHE",
    ]
    for packing in ("original", "exact-v1"):
        native(
            "boundary/" + packing + "/nonsuppressed",
            "jsonl",
            [*query, "--packing-policy", packing, "--source", SOURCE, "boundaryold"],
            expected_error="mousa: token candidate bytes exceed bound\n",
        )
        for mode, text in (
            ("empty", "boundaryold"),
            ("survivor", "boundaryold boundarysmall"),
        ):
            label = "boundary/native/" + packing + "/" + mode
            native(
                label,
                "jsonl",
                [
                    *query,
                    "--supersession",
                    "--packing-policy",
                    packing,
                    "--source",
                    SOURCE,
                    text,
                ],
            )
        produced = results.get("boundary/native/" + packing + "/survivor", {})
        for suffix, flags in (
            ("history", []),
            (
                "recount",
                [
                    "--verify-tokens",
                    "--tokenizer-python",
                    "TOKEN_PY",
                    "--tokenizer-cache",
                    "TOKEN_CACHE",
                ],
            ),
        ):
            native(
                "boundary/native/" + packing + "/" + suffix,
                "jsonl",
                [
                    "trail",
                    *flags,
                    "--source",
                    SOURCE,
                    produced.get("trail_id", "PENDING"),
                ],
            )
    start("boundary")
    for packing in ("original", "exact-v1"):
        for mode, text in (
            ("empty", "boundaryold"),
            ("survivor", "boundaryold boundarysmall"),
        ):
            tool(
                "boundary/mcp/" + packing + "/" + mode,
                "mousa_query",
                query=text,
                policy="original",
                budget_bytes=4096,
                context_tokens=4096,
                supersession=True,
                packing_policy=packing,
            )
        tool(
            "boundary/mcp/" + packing + "/history",
            "mousa_trail",
            trail_id=results.get("boundary/mcp/" + packing + "/survivor", {}).get(
                "trail_id", "PENDING"
            ),
            supersession=True,
            token_details=True,
        )
    stop("boundary-exit")
    return events


def result_from(event):
    if event["kind"] == "native":
        if "expected_error" in event:
            equal(event["exit"], 1, "expected-native-error-exit")
            equal(event["stdout"], wire.stream(b""), "expected-native-error-stdout")
            equal(
                event["stderr"],
                wire.stream(event["expected_error"].encode()),
                "expected-native-error",
            )
            return {"error": event["expected_error"]}
        equal(event["exit"], 0, "native-exit")
        equal(event["stderr"], wire.stream(b""), "native-stderr")
        return shared.parsed(event["stdout"])
    response = shared.parsed(event["response"])
    equal(response.get("id"), event["id"], "response-request-id")
    equal(response.get("jsonrpc"), "2.0", "response-protocol")
    check("result" in response and "error" not in response, "rpc-success")
    return response["result"]


def check_query(result, label, results, encoder, references):
    form = "directory" if label.startswith("directory/") else "jsonl"
    boundary = label.startswith("boundary/")
    exported = (
        {"passages": boundary_pins(results)} if boundary else results[form + "/export"]
    )
    pins = {p["segment_id"]: p for p in exported["passages"]}
    ids = []
    for row in result["evidence"]:
        sid = row["segment"]["id"] if "segment" in row else row["segment_id"]
        equal(row["text"], pins[sid]["text"], "selected-text")
        ids.append(sid)
    text = "\n\n".join(
        f"[source={pins[sid]['source_id']} segment={sid} sha256={pins[sid]['content_sha256']}]\n{pins[sid]['text']}"
        for sid in ids
    )
    equal(result["context"], text, "whole-rendering")
    count = len(encoder.encode_ordinary(text))
    token = result["token"]
    equal(token["measured_tokens"], count, "reference-count")
    equal(token["rendered_bytes"], len(text.encode()), "rendered-bytes")
    equal(token["rendered_sha256"], wire.sha(text.encode()), "rendered-digest")
    check(count <= token["limit"], "token-limit")
    equal(
        result["used_bytes"],
        sum(len(pins[sid]["text"].encode()) for sid in ids),
        "released-bytes",
    )
    check(result["used_bytes"] <= result["budget_bytes"], "byte-limit")
    references.append(
        dict(
            label=label,
            tokens=count,
            ordinary_token_ids=encoder.encode_ordinary(text),
            rendered_sha256=wire.sha(text.encode()),
        )
    )
    nohistory = label.endswith("/no-history")
    disabled = label == "mcp/deactivated"
    equal(
        result["supersession_excluded"],
        65 if boundary else 0 if nohistory or disabled else 1,
        "withheld-count",
    )
    old = next(p["segment_id"] for p in exported["passages"] if p["item"] == "old.md")
    if not nohistory and not disabled:
        check(old not in ids, "withheld-selection")
    if boundary:
        equal(
            [pins[sid]["item"] for sid in ids],
            ["twin.md"] if label.endswith("/survivor") else [],
            "boundary-survivor-items",
        )
        equal(
            result["outcome"],
            "evidence" if ids else "supersession_excluded",
            "boundary-outcome",
        )
        if "/mcp/" in label:
            equal(result["budget_omitted"], 0, "boundary-not-budget")
            equal(result["matched_candidates"], 66 if ids else 65, "boundary-population")
    if label.endswith(("/active", "/full", "/exact")):
        equal(
            sorted(pins[sid]["item"] for sid in ids),
            ["new.md", "twin.md"],
            "survivor-items",
        )
    if label == "mcp/all-withheld":
        equal(result["outcome"], "supersession_excluded", "all-withheld-outcome")
        equal(
            [result["context"], result["budget_omitted"]],
            ["", 0],
            "all-withheld-not-budget",
        )
    if label.endswith(("/short", "/reserved")):
        full = results[label.rsplit("/", 1)[0] + "/full"]
        check(text != full["context"], "whole-rendering-pressure")
        if label.endswith("/reserved"):
            equal(
                text,
                results[label.rsplit("/", 1)[0] + "/short"]["context"],
                "reservation-boundary",
            )


def verify(report, encoder):
    equal(
        report["runner_sha256"], wire.sha(Path(__file__).read_bytes()), "runner-binding"
    )
    check(
        len(report["product"]["head"]) == 40 and len(report["product"]["tree"]) == 40,
        "product-binding",
    )
    results, references, catalog = {}, [], None
    equal(len(report["events"]), len(schedule(results, encoder)), "schedule-length")
    for i, event in enumerate(report["events"]):
        expected = schedule(results, encoder)[i]
        for key, value in expected.items():
            equal(event.get(key), value, "scheduled-" + key)
        kind, label = event["kind"], event["label"]
        if kind == "start":
            continue
        if kind == "stop":
            equal(event["exit"], 0, "mcp-exit")
            equal(event["stdout_tail"], wire.stream(b""), "mcp-no-extra-bytes")
            equal(event["stderr"], wire.stream(b""), "mcp-stderr")
            continue
        if kind == "rpc":
            request = dict(
                jsonrpc="2.0", method=expected["method"], params=expected["params"]
            )
            if expected["method"] != "notifications/initialized":
                request["id"] = i + 1
            equal(
                event["request"],
                wire.stream(wire.encoded(request)),
                "scheduled-request-bytes",
            )
            if expected["method"] == "notifications/initialized":
                check("response" not in event, "notification-no-response")
                continue
        result = result_from(event)
        if kind == "rpc":
            method = event["method"]
            if method == "initialize":
                equal(result["protocolVersion"], "2025-11-25", "protocol-version")
                continue
            if method == "tools/list":
                found = {t["name"]: t for t in result["tools"]}
                if catalog is None:
                    catalog = found
                equal(found, catalog, "restart-discovery")
                continue
            envelope = result["structuredContent"]
            check(not result.get("isError", False), "tool-success")
            equal(
                json.loads(result["content"][0]["text"]),
                envelope,
                "text-structured-equality",
            )
            check(
                not wire.schema_violations(
                    catalog[event["params"]["name"]]["outputSchema"], envelope
                ),
                "declared-output-schema",
            )
            equal(
                [envelope["schema"], envelope["operation"], envelope["source"]],
                ["mousa.mcp_result.v1", event["params"]["name"], SOURCE],
                "envelope-binding",
            )
            result = envelope["result"]
        if label.endswith("/export"):
            equal(
                {p["item"]: p["text"] for p in result["passages"]},
                FIXTURE,
                "exported-fixture",
            )
            for passage in result["passages"]:
                equal(
                    passage["content_sha256"],
                    wire.sha(passage["text"].encode()),
                    "export-content-digest",
                )
                shared.identities({key: passage[key] for key in shared.PINS})
        if kind == "native" and event["arguments"][0] == "supersession":
            equal(result, json.loads(event["stdin"]), "administration-readback")
        results[label] = result
        if label.startswith("boundary/") and label.endswith("-pin"):
            item = {"old": "old.md", "new": "new.md", "survivor": "twin.md"}[
                label.split("/")[1].removesuffix("-pin")
            ]
            for p in result["evidence"]:
                equal(p["item"], item, "boundary-pin-item")
                equal(
                    p["text"],
                    BOUNDARY_FIXTURE[item][p["byte_start"] : p["byte_end"]],
                    "boundary-pin-text",
                )
                equal(
                    p["content_sha256"],
                    wire.sha(p["text"].encode()),
                    "boundary-pin-digest",
                )
        if "context" in result:
            check_query(result, label, results, encoder, references)
        if "historical" in result:
            h = result["historical"]
            produced_label = (
                (label.rsplit("/", 1)[0] + "/active")
                if kind == "native"
                else label.split("/history-")[0] + "/full"
            )
            if label == "mcp/old-history":
                produced_label = "mcp/original/full"
            boundary = label.startswith("boundary/")
            if boundary:
                produced_label = label.rsplit("/", 1)[0] + "/survivor"
            produced = results[produced_label]
            equal(h["id"], produced["trail_id"], "historical-trail")
            equal(h["packet_id"], produced["packet_id"], "historical-packet")
            equal(h["schema"], "mousa.source_trail.v8", "historical-version")
            details = event.get("params", {}).get("arguments", {})
            show_token = kind == "native" or details.get("token_details", False)
            show_sup = kind == "native" or details.get("supersession", False)
            equal(
                h.get("token"),
                produced["token"] if show_token else None,
                "historical-token-opt-in",
            )
            form = "directory" if label.startswith("directory/") else "jsonl"
            declaration, activation = (
                administration(
                    {"passages": boundary_pins(results)}, off_id(results), True, 3
                )
                if boundary
                else administration(results[form + "/export"])
            )
            if show_sup:
                sup = h["supersession"]
                equal(
                    [sup["consulted"], sup["activation_id"], sup["declaration_id"]],
                    [True, activation["id"], declaration["id"]],
                    "historical-producing-consultation",
                )
                equal(
                    len(sup["dispositions"]),
                    65 if boundary else 1,
                    "historical-withheld-rows",
                )
                row = sup["dispositions"][0]
                for key in (
                    "predecessor_item_id",
                    "predecessor_representation_id",
                    "successor_item_id",
                    "successor_representation_id",
                ):
                    equal(row[key], declaration[key], "historical-pin")
                candidate = next(
                    c for c in h["candidates"] if c["segment_id"] == row["segment_id"]
                )
                check(
                    candidate["text_bytes"] > 0 and candidate["rank"] > 0,
                    "withheld-positive-metadata",
                )
                equal(candidate["selected"], False, "historical-selected")
                if boundary:
                    withheld = {r["segment_id"] for r in sup["dispositions"]}
                    equal(len(withheld), 65, "boundary-withheld-identities")
                    equal(len(h["candidates"]), 66, "boundary-historical-population")
                    proposed = dict(
                        zip(h["token"]["candidate_ids"], h["token"]["proposed_tokens"])
                    )
                    for c in h["candidates"]:
                        if c["segment_id"] in withheld:
                            equal(c["text_bytes"], 4096, "boundary-canonical-size")
                            check(c["rank"] > 0, "boundary-accepted-rank")
                            equal(c["selected"], False, "historical-selected")
                            equal(
                                proposed[c["segment_id"]], None, "boundary-null-count"
                            )
            else:
                check("supersession" not in h, "historical-supersession-opt-out")
            if label.endswith("/recount"):
                equal(
                    h["token_verification"],
                    "official_recount_verified",
                    "native-recount",
                )
            if label == "mcp/old-history":
                check(
                    all(not c["indexed_now"] for c in h["candidates"] if c["selected"]),
                    "retired-selected-history",
                )
    return dict(
        result="PASS",
        product=report["product"],
        events=len(report["events"]),
        reference_counts=references,
        limits="Synthetic client/counting evidence only; graph, corruption, concurrency and process faults are separate product tests. No semantic/performance/window claim.",
    )


def capture(args, encoder):
    source = args.product_source.absolute()

    def git(*argv):
        return subprocess.check_output(
            ["git", "-C", str(source), *argv], text=True
        ).strip()

    equal(git("rev-parse", "HEAD"), args.product_head, "exact-public-head")
    equal(git("status", "--porcelain"), "", "clean-public-source")
    args.output.mkdir(parents=True, exist_ok=False)
    report = dict(
        product=dict(
            head=args.product_head,
            tree=git("rev-parse", "HEAD^{tree}"),
            binary_sha256=wire.sha(args.mousa.read_bytes()),
            build="GOWORK=off CGO_ENABLED=0 go build -o BINARY ./cmd/mousa",
        ),
        runner_sha256=wire.sha(Path(__file__).read_bytes()),
        events=[],
    )
    results = {}
    with tempfile.TemporaryDirectory(prefix="mousa-composition-") as temporary:
        directory = Path(temporary) / "documents"
        directory.mkdir()
        for name, text in FIXTURE.items():
            (directory / name).write_text(text)
        stores = {
            form: str(Path(temporary) / (form + ".sqlite"))
            for form in ("directory", "jsonl")
        }
        substitutions = {
            "DIRECTORY": str(directory),
            "TOKEN_PY": str(args.python.absolute()),
            "TOKEN_CACHE": str(args.cache.absolute()),
        }
        process = None
        try:
            for i in range(len(schedule(results, encoder))):
                event = copy.deepcopy(schedule(results, encoder)[i])
                report["events"].append(event)
                kind, label = event["kind"], event["label"]
                if kind == "native":
                    argv = [
                        str(args.mousa.absolute()),
                        "-store",
                        stores[event["form"]],
                        *[substitutions.get(v, v) for v in event["arguments"]],
                    ]
                    r = subprocess.run(
                        argv,
                        input=event["stdin"].encode(),
                        capture_output=True,
                        timeout=30,
                    )
                    event.update(
                        stdout=wire.stream(r.stdout),
                        stderr=wire.stream(r.stderr),
                        exit=r.returncode,
                    )
                    results[label] = result_from(event)
                elif kind == "start":
                    errors = tempfile.TemporaryFile()
                    argv = [
                        str(args.mousa.absolute()),
                        "-store",
                        stores["jsonl"],
                        *[substitutions.get(v, v) for v in event["arguments"]],
                    ]
                    process = subprocess.Popen(
                        argv,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=errors,
                    )
                    reader = wire.LineReader(process.stdout.fileno())
                elif kind == "stop":
                    process.stdin.close()
                    event["exit"] = process.wait(timeout=30)
                    event["stdout_tail"] = wire.stream(
                        reader.buffer + process.stdout.read()
                    )
                    process.stdout.close()
                    errors.seek(0)
                    event["stderr"] = wire.stream(errors.read())
                    errors.close()
                    process = None
                else:
                    message = dict(
                        jsonrpc="2.0", method=event["method"], params=event["params"]
                    )
                    if event["method"] != "notifications/initialized":
                        message["id"] = i + 1
                        event["id"] = i + 1
                    data = wire.encoded(message)
                    event["request"] = wire.stream(data)
                    process.stdin.write(data)
                    process.stdin.flush()
                    if "id" in message:
                        event["response"] = wire.stream(shared.read_frame(reader))
                        result = result_from(event)
                        if event["method"] == "tools/call":
                            results[label] = result["structuredContent"]["result"]
                wire.save(args.output / "capture.json", report)
        finally:
            if process is not None:
                process.kill()
                process.wait()
                errors.close()
    summary = verify(report, encoder)
    wire.save(args.output / "summary.json", summary)
    print(json.dumps(summary))


def controls(report, encoder):
    receipts = []
    for name, detector in (
        ("changed-request", "scheduled-request-bytes"),
        ("wrong-withheld-count", "withheld-count"),
        ("wrong-withheld-selection", "historical-selected"),
    ):
        changed = copy.deepcopy(report)
        label = (
            "mcp/original/history-both"
            if name == "wrong-withheld-selection"
            else "mcp/original/full"
        )
        event = next(e for e in changed["events"] if e["label"] == label)
        if name == "changed-request":
            request = shared.parsed(event["request"])
            request["params"]["arguments"]["query"] = "different request"
            event["request"] = wire.stream(wire.encoded(request))
        else:
            response = shared.parsed(event["response"])
            payload = response["result"]
            envelope = payload["structuredContent"]
            if name == "wrong-withheld-count":
                envelope["result"]["supersession_excluded"] = 0
            else:
                h = envelope["result"]["historical"]
                sid = h["supersession"]["dispositions"][0]["segment_id"]
                next(c for c in h["candidates"] if c["segment_id"] == sid)[
                    "selected"
                ] = True
            payload["content"][0]["text"] = wire.canonical(envelope)
            event["response"] = wire.stream(wire.encoded(response))
        try:
            verify(changed, encoder)
        except ValueError as error:
            equal(str(error), detector, "intended-control-detector")
            receipts.append(
                dict(
                    control=name,
                    detector=str(error),
                    result="PASS",
                    rehashed_capture_sha256=wire.sha(wire.encoded(changed)),
                )
            )
        else:
            raise ValueError("negative-control-accepted")
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "verify", "controls"))
    for name in ("mousa", "product-source", "python", "cache", "output"):
        parser.add_argument(
            "--" + name, type=Path, required=name in ("cache", "output")
        )
    parser.add_argument("--product-head")
    args = parser.parse_args()
    encoder = tokens.ordinary_encoder(args.cache)
    if args.mode == "capture":
        capture(args, encoder)
    else:
        report = json.loads((args.output / "capture.json").read_text())
        summary = verify(report, encoder)
        equal(
            json.loads((args.output / "summary.json").read_text()),
            summary,
            "summary-binding",
        )
        print(
            json.dumps(
                controls(report, encoder) if args.mode == "controls" else summary
            )
        )


if __name__ == "__main__":
    main()
