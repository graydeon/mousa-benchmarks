"""Capture supplied-vector supersession with independently counted whole contexts."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("vector_capture", ROOT.parent / "vector-supersession/capture.py")
vectors = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vectors)
composition, shared, wire = vectors.composition, vectors.shared, vectors.wire
check, equal = shared.check, shared.equal
SOURCE, FIXTURE, VALUES = vectors.SOURCE, vectors.FIXTURE, vectors.VALUES


def schedule(results, encoder):
    events = []

    def native(label, args, value=""):
        events.append(dict(kind="native", label=label, arguments=args, stdin=value))

    def rpc(label, method, params):
        events.append(dict(kind="rpc", label=label, method=method, params=params))

    def tool(label, name, args):
        rpc(label, "tools/call", dict(name=name, arguments=dict(source=SOURCE, **args)))

    def start(label):
        events.append(dict(kind="start", label=label, arguments=["mcp", "--caller", "cli", "--source", SOURCE,
            "--tokenizer-python", "TOKEN_PY", "--tokenizer-cache", "TOKEN_CACHE"]))
        rpc(label+"/initialize", "initialize", dict(protocolVersion="2025-11-25", capabilities={},
            clientInfo=dict(name="vector-token-supersession-capture", version="1")))
        rpc(label+"/initialized", "notifications/initialized", {})
        rpc(label+"/discovery", "tools/list", {})

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
    value = wire.encoded(dict(schema="mousa.vector_query.v1", values=[1, 0])).decode()
    for surface in ("native", "mcp"):
        if surface == "mcp":
            start("mcp")
        for mode in ("vector", "hybrid"):
            for packing in ("original", "exact-v1"):
                prefix = "/".join((surface, mode, packing))
                true = results.get(prefix+"/true", {})
                n = len(encoder.encode_ordinary(true.get("context", ""))) or 1
                cases = (("default", None, 4096, 12, None), ("false", False, 4096, 12, None),
                         ("true", True, 4096, 12, None), ("exact", True, n, 12, None),
                         ("pressure", True, max(1, n-1), 12, None), ("bytes", True, 4096, 1, None),
                         ("reserved", True, 4096, 12, n+12), ("zero", True, 4096, 12, 12))
                for suffix, sup, cap, byte_budget, window in cases:
                    if surface == "native":
                        args = ["query", "--"+mode+"-space", space, "--packing-policy", packing,
                            "--budget-bytes", str(byte_budget), "--context-tokens", str(cap),
                            "--tokenizer-python", "TOKEN_PY", "--tokenizer-cache", "TOKEN_CACHE"]
                        if sup is not None:
                            args += ["--supersession="+str(sup).lower()]
                        if window is not None:
                            args += ["--context-window", str(window), "--prompt-reserve", "5", "--output-reserve", "7"]
                        args += ["--source", SOURCE]
                        if mode == "hybrid":
                            args += ["Drain"]
                        native(prefix+"/"+suffix, args, value)
                    else:
                        args = dict(space_id=space, values=[1, 0], packing_policy=packing, budget_bytes=byte_budget, context_tokens=cap)
                        if mode == "hybrid":
                            args.update(query="Drain", policy="original")
                        if sup is not None:
                            args["supersession"] = sup
                        if window is not None:
                            args.update(window_tokens=window, prompt_reserve_tokens=5, output_reserve_tokens=7)
                        tool(prefix+"/"+suffix, "mousa_"+mode+"_query", args)
                trail = results.get(prefix+"/true", {}).get("trail_id", "PENDING")
                if surface == "native":
                    native(prefix+"/history", ["trail", "--source", SOURCE, trail])
                    native(prefix+"/recount", ["trail", "--verify-tokens", "--tokenizer-python", "TOKEN_PY",
                        "--tokenizer-cache", "TOKEN_CACHE", "--source", SOURCE, trail])
                else:
                    for suffix, flags in (("default", {}), ("supersession", dict(supersession=True)),
                        ("token", dict(token_details=True)), ("all", dict(supersession=True, token_details=True, retrieval_details=True))):
                        tool(prefix+"/history-"+suffix, "mousa_trail", dict(trail_id=trail, **flags))
        if surface == "mcp":
            events.append(dict(kind="stop", label="mcp/stop"))
    native("retire-survivors", ["sync", "--source", SOURCE],
        ''.join(wire.encoded(dict(id=name, deleted=True)).decode() for name in ("twin.md", "peer.md", "new.md")))
    start("restart")
    for mode in ("vector", "hybrid"):
        for packing in ("original", "exact-v1"):
            args = dict(space_id=space, values=[1, 0], budget_bytes=1, context_tokens=1, supersession=True, packing_policy=packing)
            if mode == "hybrid":
                args.update(query="Drain", policy="original")
            tool("all-withheld/"+mode+"/"+packing+"/true", "mousa_"+mode+"_query", args)
            tool("restart/"+mode+"/"+packing+"/history-all", "mousa_trail", dict(
                trail_id=results.get("mcp/"+mode+"/"+packing+"/true", {}).get("trail_id", "PENDING"),
                supersession=True, token_details=True, retrieval_details=True))
    events.append(dict(kind="stop", label="restart/stop"))
    _, inactive = composition.administration(exported, active["id"], False, 2)
    native("deactivate", ["supersession", "activation", "put"], wire.encoded(inactive).decode())
    for mode in ("vector", "hybrid"):
        native("deactivated/"+mode+"/original/history", ["trail", "--source", SOURCE,
            results.get("native/"+mode+"/original/true", {}).get("trail_id", "PENDING")])
    return events


def query_check(result, label, results, encoder, references):
    surface, mode, packing, case = label.split("/")
    pins = {p["item"]: p for p in results["export"]["passages"]}
    order, lr, vr = vectors.producing_order(mode, pins)
    equal(order[0], "old.md", "fixture-predecessor-wins")
    all_withheld = surface == "all-withheld"
    empty = all_withheld or case in ("pressure", "bytes", "zero")
    name = "old.md" if case in ("default", "false") else "twin.md"
    expected_ids = [] if empty else [pins[name]["segment_id"]]
    evidence = result["evidence"]
    ids = [p["segment"]["id"] if surface == "native" else p["segment_id"] for p in evidence]
    equal(ids, expected_ids, "selected-evidence")
    pieces = []
    for row in evidence:
        p = pins[name]
        equal(row["text"], FIXTURE[name], "selected-text")
        equal(row["rank"], order.index(name)+1, "producing-rank")
        pieces.append(f"[source={p['source_id']} segment={p['segment_id']} sha256={p['content_sha256']}]\n{p['text']}")
    text = "\n\n".join(pieces)
    equal(result["context"], text, "complete-context-rendering")
    token = result["token"]
    count = len(encoder.encode_ordinary(text))
    equal(token["measured_tokens"], count, "whole-context-count")
    equal(token["rendered_bytes"], len(text.encode()), "rendered-bytes")
    equal(token["rendered_sha256"], wire.sha(text.encode()), "rendering-digest")
    equal(token["backend"], "tiktoken/0.12.0/o200k_base/ordinary", "official-backend")
    equal(token["rendering"], "mousa.context_text.v1", "versioned-rendering")
    budget = token["budget"]
    limit = min(budget["cap"], budget["window"]-budget["prompt_reserve"]-budget["output_reserve"]) if budget["window"] else budget["cap"]
    equal(token["limit"], limit, "reservation-arithmetic")
    check(count <= limit, "measured-cap")
    equal(result["used_bytes"], 0 if empty else 12, "released-byte-accounting")
    equal(result["outcome"], "supersession_excluded" if all_withheld else "budget_omitted" if empty else "evidence", "outcome-precedence")
    enforced = case not in ("default", "false")
    equal(result.get("supersession_excluded"), 1 if enforced else None, "withheld-count")
    facts = result[mode]
    expected_order = ["old.md"] if all_withheld else order
    equal([c["segment_id"] for c in facts["candidates"]], [pins[n]["segment_id"] for n in expected_order], "full-producing-population")
    equal([facts["eligible"], facts["indexed"]], [1,1] if all_withheld else [4,3], "pre-mask-coverage")
    equal(token["candidate_ids"], [pins[n]["segment_id"] for n in expected_order], "accepted-token-alignment")
    if enforced:
        equal(token["proposed_tokens"][0], None, "withheld-null-count")
    for n, c in zip(expected_order, facts["candidates"]):
        if mode == "vector":
            equal(c["cosine"], VALUES[n][0], "cosine")
        elif not all_withheld:
            equal(c.get("lexical", {}).get("rank"), lr.get(n), "lexical-rank")
            equal(c["vector"]["rank"], vr[n], "vector-rank")
            expected_rrf = sum(1/(60+r) for r in (lr.get(n), vr[n]) if r)
            check(abs(c["rrf"]-expected_rrf) <= 1e-16, "RRF-k60")
    if not all_withheld:
        ordinary = results.get("/".join((surface,mode,packing,"default")))
        if ordinary:
            equal(facts, ordinary[mode], "unchanged-producing-facts")
        if case == "false":
            equal(result["packet_id"], ordinary["packet_id"], "false-packet")
            equal(token, ordinary["token"], "false-token")
        if case in ("exact", "reserved"):
            equal(result["context"], results["/".join((surface,mode,packing,"true"))]["context"], "exact-fit-context")
    references.append(dict(label=label, tokens=count, bytes=len(text.encode()), sha256=wire.sha(text.encode())))


def history_check(result, event, results):
    surface, mode, packing, suffix = event["label"].split("/")
    origin = "mcp" if surface == "restart" else "native" if surface == "deactivated" else surface
    produced = results["/".join((origin, mode, packing, "true"))]
    h = result["historical"]
    equal([h["id"], h["packet_id"], h["decision_id"]], [produced["trail_id"], produced["packet_id"], produced["decision_id"]], "historical-producing-identity")
    equal(h["schema"], "mousa.source_trail.v10", "historical-version")
    args = event.get("params", {}).get("arguments", {})
    native = event["kind"] == "native"
    sup, token, retrieval = native or args.get("supersession",False), native or args.get("token_details",False), native or args.get("retrieval_details",False)
    equal("supersession" in h, bool(sup), "supersession-opt-in")
    equal(h.get("token"), produced["token"] if token else None, "token-opt-in")
    equal(h.get(mode), produced[mode] if retrieval else None, "retrieval-opt-in")
    if sup:
        declaration, active = composition.administration(results["export"])
        equal([h["supersession"]["consulted"],h["supersession"]["activation_id"],h["supersession"]["declaration_id"]], [True, active["id"],declaration["id"]], "recorded-consultation")
        row = h["supersession"]["dispositions"][0]
        c = next(c for c in h["candidates"] if c["segment_id"] == row["segment_id"])
        equal([c["rank"],c["text_bytes"],c["selected"]], [1,12,False], "withheld-history")
        for key in ("predecessor_item_id","predecessor_representation_id","successor_item_id","successor_representation_id"):
            equal(row[key], declaration[key], "recorded-declaration-pin")
    if native:
        equal(h["token_verification"], "official_recount_verified" if suffix == "recount" else "retired_text_unavailable" if surface == "deactivated" else "retained_digest_verified_count_recorded", "history-verification-limit")
    else:
        check("token_verification" not in h, "no-mcp-recount-member")


def verify(report, encoder):
    equal(report["runner_sha256"], wire.sha(Path(__file__).read_bytes()), "runner-binding")
    check(len(report["product"]["head"]) == 40 and len(report["product"]["tree"]) == 40, "product-binding")
    equal(len(report["events"]), len(schedule({}, encoder)), "complete-schedule")
    results, references, catalog = {}, [], None
    for i, event in enumerate(report["events"]):
        planned = schedule(results, encoder)[i]
        for key, value in planned.items():
            equal(event.get(key), value, "scheduled-"+key)
        kind, label = event["kind"], event["label"]
        if kind in ("native", "start"):
            equal(event["argv"], ["BINARY", "-store", "STORE", *planned["arguments"]], "scheduled-argv")
        if kind == "start":
            continue
        if kind == "stop":
            equal([event["exit"],event["stdout_tail"],event["stderr"]], [0,wire.stream(b""),wire.stream(b"")], "clean-shutdown")
            continue
        if kind == "rpc":
            request = dict(jsonrpc="2.0",method=planned["method"],params=planned["params"])
            if planned["method"] != "notifications/initialized":
                request["id"] = i+1
            equal(event["request"],wire.stream(wire.encoded(request)),"scheduled-request-bytes")
            if planned["method"] == "notifications/initialized":
                check("response" not in event,"notification-no-response")
                continue
        result = composition.result_from(event)
        if kind == "rpc":
            if event["method"] == "initialize":
                equal(result["protocolVersion"],"2025-11-25","protocol-version")
                continue
            if event["method"] == "tools/list":
                found = {t["name"]:t for t in result["tools"]}
                equal(len(found),8,"discovered-tools")
                if catalog is not None:
                    equal(found,catalog,"restart-discovery")
                catalog = found
                continue
            envelope = result["structuredContent"]
            check(not result.get("isError",False),"tool-success")
            equal(json.loads(result["content"][0]["text"]),envelope,"text-structured-equality")
            check(not wire.schema_violations(catalog[event["params"]["name"]]["outputSchema"],envelope),"closed-output-schema")
            equal([envelope["schema"],envelope["operation"],envelope["source"]],["mousa.mcp_result.v1",event["params"]["name"],SOURCE],"envelope-binding")
            result = envelope["result"]
        if label == "export":
            equal({p["item"]:p["text"] for p in result["passages"]},FIXTURE,"exported-fixture")
        if kind == "native" and event["arguments"][0] == "supersession":
            equal(result,json.loads(event["stdin"]),"administration-readback")
        if "context" in result:
            query_check(result,label,results,encoder,references)
        if "historical" in result:
            history_check(result,event,results)
        results[label] = result
    return dict(result="PASS",product=report["product"],events=len(report["events"]),reference_counts=references,
        limits="Synthetic public-client protocol/counting only; internal graph, corruption, concurrency and faults remain product-local. No semantic, performance or complete-window claim.")


def capture(args, encoder):
    def git(*argv):
        return subprocess.check_output(["git","-C",str(args.product_source),*argv],text=True,timeout=30).strip()
    equal(git("rev-parse","HEAD"),args.product_head,"exact-public-head")
    equal(git("status","--porcelain"),"","clean-public-source")
    args.output.mkdir(parents=True,exist_ok=False)
    report = dict(product=dict(head=args.product_head,tree=git("rev-parse","HEAD^{tree}"),binary_sha256=wire.sha(args.mousa.read_bytes()),
        build="GOWORK=off CGO_ENABLED=0 go build -o BINARY ./cmd/mousa"),runner_sha256=wire.sha(Path(__file__).read_bytes()),events=[])
    results, process = {}, None
    substitutions = {"TOKEN_PY":str(args.python.absolute()),"TOKEN_CACHE":str(args.cache.absolute())}
    actual_argv = []
    with tempfile.TemporaryDirectory(prefix="mousa-public-vector-token-") as temporary:
        store = str(Path(temporary)/"evidence.sqlite")
        try:
            for i in range(len(schedule(results,encoder))):
                event = copy.deepcopy(schedule(results,encoder)[i])
                report["events"].append(event)
                kind,label = event["kind"],event["label"]
                if kind in ("native","start"):
                    argv = [str(args.mousa.absolute()),"-store",store,*[substitutions.get(a,a) for a in event["arguments"]]]
                    event["argv"] = ["BINARY","-store","STORE",*event["arguments"]]
                    actual_argv.append(dict(label=label, argv=argv))
                    wire.save(args.output/"private-argv.json", actual_argv)
                if kind == "native":
                    r = subprocess.run(argv,input=event["stdin"].encode(),capture_output=True,timeout=30)
                    event.update(stdout=wire.stream(r.stdout),stderr=wire.stream(r.stderr),exit=r.returncode)
                    results[label] = composition.result_from(event)
                elif kind == "start":
                    errors = tempfile.TemporaryFile()
                    process = subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors)
                    reader = wire.LineReader(process.stdout.fileno())
                elif kind == "stop":
                    process.stdin.close()
                    event["exit"] = process.wait(timeout=30)
                    event["stdout_tail"] = wire.stream(reader.buffer+process.stdout.read())
                    process.stdout.close()
                    errors.seek(0)
                    event["stderr"] = wire.stream(errors.read())
                    errors.close()
                    process = None
                else:
                    message = dict(jsonrpc="2.0",method=event["method"],params=event["params"])
                    if event["method"] != "notifications/initialized":
                        event["id"] = i+1
                        message["id"] = i+1
                    data = wire.encoded(message)
                    event["request"] = wire.stream(data)
                    process.stdin.write(data)
                    process.stdin.flush()
                    if "id" in message:
                        event["response"] = wire.stream(shared.read_frame(reader))
                        result = composition.result_from(event)
                        if event["method"] == "tools/call":
                            results[label] = result["structuredContent"]["result"]
                wire.save(args.output/"capture.json",report)
        finally:
            if process is not None:
                process.kill()
                process.wait()
                errors.close()
            wire.save(args.output/"capture.json",report)
    summary = verify(report,encoder)
    wire.save(args.output/"summary.json",summary)
    print(json.dumps(summary))


def controls(report,encoder):
    receipts = []
    for name,label,detector in (("request","mcp/vector/original/true","scheduled-request-bytes"),
        ("count","mcp/vector/original/true","whole-context-count"),
        ("selection","mcp/hybrid/exact-v1/true","selected-evidence"),
        ("history","mcp/vector/original/history-all","withheld-history")):
        changed = copy.deepcopy(report)
        event = next(e for e in changed["events"] if e["label"] == label)
        if name == "request":
            request = shared.parsed(event["request"])
            request["params"]["arguments"]["supersession"] = False
            event["request"] = wire.stream(wire.encoded(request))
        else:
            response = shared.parsed(event["response"])
            payload = response["result"]
            result = payload["structuredContent"]["result"]
            if name == "count":
                result["token"]["measured_tokens"] += 1
            elif name == "selection":
                result["evidence"][0]["segment_id"] = "00"*32
            else:
                result["historical"]["candidates"][0]["selected"] = True
            payload["content"][0]["text"] = wire.canonical(payload["structuredContent"])
            event["response"] = wire.stream(wire.encoded(response))
        try:
            verify(changed,encoder)
        except ValueError as error:
            equal(str(error),detector,"intended-control-detector")
            receipts.append(dict(control=name,result="PASS",detector=str(error),rehashed_capture_sha256=wire.sha(wire.encoded(changed))))
        else:
            raise ValueError("negative-control-accepted")
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("capture","verify","controls"))
    for name in ("mousa","product-source","output","python","cache"):
        parser.add_argument("--"+name,type=Path,required=name in ("output","cache"))
    parser.add_argument("--product-head")
    args = parser.parse_args()
    encoder = composition.tokens.ordinary_encoder(args.cache)
    if args.mode == "capture":
        capture(args,encoder)
    else:
        report = json.loads((args.output/"capture.json").read_text())
        summary = verify(report,encoder)
        equal(json.loads((args.output/"summary.json").read_text()),summary,"summary-binding")
        print(json.dumps(controls(report,encoder) if args.mode == "controls" else summary))


if __name__ == "__main__":
    main()
