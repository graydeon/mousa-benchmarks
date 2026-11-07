"""Offline independent audit; no benchmark imports, retrieval, or source writes."""
import argparse
import base64
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import zipfile


def require(value, label):
    if not value:
        raise ValueError(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(raw):
    return {"bytes": len(raw), "sha256": sha(raw)}


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def parse(raw):
    def bad(value):
        raise ValueError("nonfinite JSON: " + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)


def unpack(path):
    packed = parse(gzip.decompress(path.read_bytes()))
    objects, hashes = packed["objects"], packed["member_sha256"]
    require(len(objects) == len(hashes), "archive count")
    expanded, active = {}, set()
    def expand(value):
        if not isinstance(value, list):
            return value
        require(len(value) == 2 and value[0] == "@" and type(value[1]) is int, "archive reference")
        index = value[1]
        require(0 <= index < len(objects) and index not in active, "archive cycle/index")
        if index in expanded:
            return expanded[index]
        active.add(index)
        node = objects[index]
        raw = (json.dumps(node, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
        require(sha(raw) == hashes[index], "archive member hash")
        kind, content = node
        require(kind in ("object", "array"), "archive node")
        result = pairs((k, expand(v)) for k, v in content) if kind == "object" else [expand(v) for v in content]
        expanded[index] = result
        active.remove(index)
        return result
    result = expand(packed["root"])
    require(len(expanded) == len(objects), "unreferenced archive object")
    return result


def stream(value):
    require(set(value) == {"bytes", "sha256", "base64", "text"}, "stream schema")
    raw = base64.b64decode(value["base64"], validate=True)
    require(identity(raw) == {k: value[k] for k in ("bytes", "sha256")} and raw.decode("utf-8", "replace") == value["text"], "stream identity")
    return raw


SPACE = "\t\n\v\f\r \u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"


def sources(cache, enrollment):
    versions, bodies = {}, {}
    for asset in enrollment["assets"]:
        path = cache / asset["name"]
        require(identity(path.read_bytes()) == {"bytes": asset["size"], "sha256": asset["sha256"]}, "source asset pin")
        if not path.name.endswith(".zip"):
            continue
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                require(member.file_size <= 16 << 20, "source member bound")
                raw = archive.read(member)
                physical = asset["name"] + ":" + member.filename
                item = "p_" + sha(physical.encode())
                logical = member.filename.split("/")[-1].split("__")[0]
                versions.setdefault(logical, []).append((item, sha(raw)))
                bodies[item] = raw
    corpus_ids = {d["item_id"] for d in enrollment["corpus"]}
    require(len(corpus_ids) == 500, "corpus population")
    decisions, questions, eligible = [], {}, []
    for line in (cache / "questions.jsonl").read_bytes().splitlines(keepends=True):
        q = parse(line)
        qid = q["question_id"]
        require(qid not in questions, "duplicate source question")
        questions[qid] = q
        labels = q["expected_doc_ids"]
        if qid in enrollment["original20"]:
            reason = "original20"
        elif q["question_type"] not in ("basic", "semantic") or q["source_types"] != ["confluence"] or not labels:
            reason = "ineligible-source-category-labels"
        elif any(not versions.get(label) or not {i for i, _ in versions[label]} <= corpus_ids for label in labels):
            reason = "gold-not-wholly-in-frozen-corpus"
        elif any(len({h for _, h in versions[label]}) != 1 for label in labels):
            reason = "ambiguous-physical-versions"
        else:
            reason = "eligible"
            eligible.append(qid)
        decisions.append({"question_id": qid, "reason": reason, "line_identity": identity(line)})
    require(decisions == enrollment["decisions"], "source enrollment decisions")
    require(dict(Counter(d["reason"] for d in decisions)) == enrollment["eligibility_counts"], "eligibility counts")
    eligible.sort(key=lambda q: (sha((enrollment["seed"] + q).encode()), q))
    require(enrollment["heldout20"] == (eligible[:20] if len(eligible) >= 20 else []), "heldout selection")
    expected_questions = []
    for population in ("original20", "heldout20"):
        for qid in enrollment[population]:
            q = questions[qid]
            gold = sorted({i for label in q["expected_doc_ids"] for i, _ in versions[label]})
            expected_questions.append({"population": population, "question": q, "gold": gold})
    require(expected_questions == enrollment["questions"], "question/gold population")
    documents, normalized = [], {}
    for d in enrollment["corpus"]:
        raw = bodies[d["item_id"]]
        require(identity(raw) == d["raw"], "document raw pin")
        text = raw.decode().strip(SPACE).removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
        require(identity(text.encode()) == d["rendered"], "document rendered pin")
        documents.append({"_id": d["item_id"], "title": "", "text": text})
        normalized[d["item_id"]] = text.strip(SPACE).removeprefix("\ufeff").encode()
    require(sum(d["rendered"]["bytes"] for d in enrollment["corpus"]) == enrollment["normalized_text_bytes"] == 4970133, "normalized source bytes")
    inputs = {
        "corpus.jsonl": b"".join((json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n").encode() for d in documents),
        "queries.jsonl": "".join(json.dumps({"_id": q["question"]["question_id"], "text": q["question"]["question"]}, ensure_ascii=False) + "\n" for q in expected_questions).encode(),
        "qrels/test.tsv": ("query-id\tcorpus-id\tscore\n" + "".join(f'{q["question"]["question_id"]}\t{d}\t1\n' for q in expected_questions for d in q["gold"])).encode(),
    }
    return {name: identity(raw) for name, raw in inputs.items()}, normalized


def metrics(ranking, gold):
    ranking = list(dict.fromkeys(ranking))
    require(bool(gold), "empty gold")
    hits = [i for i, doc in enumerate(ranking[:10], 1) if doc in gold]
    return {"recall_at_10": len(set(ranking[:10]) & gold) / len(gold),
            "recall_at_100": len(set(ranking[:100]) & gold) / len(gold),
            "binary_ndcg_at_10": sum(1 / math.log2(i + 1) for i in hits) / sum(1 / math.log2(i + 1) for i in range(1, min(10, len(gold)) + 1)),
            "mrr_at_10": 1 / hits[0] if hits else 0}


def audit(args):
    root = args.repo / "enterprise-segmentation-v1"
    protocol = parse((root / "protocol.json").read_bytes())
    raw_enrollment = (root / "enrollment.json").read_bytes()
    require(identity(raw_enrollment) == protocol["enrollment_identity"], "frozen enrollment pin")
    for name, pin in protocol["helpers"].items():
        require(identity((args.repo / name).read_bytes()) == pin, "frozen helper: " + name)
    enrollment = parse(raw_enrollment)
    c = unpack(args.capture)
    require(c["protocol"] == protocol and c["enrollment"] == enrollment, "capture frozen contracts")
    require(c["schema"] == "mousa.enterprise_segmentation.capture.v1" and c["model_calls"] == c["network_calls"] == 0, "capture scope")
    require(c["publication"]["public_head"] == args.public_head and c["publication"]["public_tree"] == args.public_tree, "public source identity")
    require(c["publication"]["binary_identity"] == identity(args.binary.read_bytes()), "public binary identity")
    manifests, documents = sources(args.cache, enrollment)
    questions = enrollment["questions"]
    qids = [q["question"]["question_id"] for q in questions]
    require(len(qids) == 20 and enrollment["confirmation"] == "UNMET_ELIGIBLE20" and not enrollment["heldout20"], "frozen development population")
    gold = {q["question"]["question_id"]: set(q["gold"]) for q in questions}
    expected = [(p, s, b, q["population"], q["question"]["question_id"]) for p in ("first", "reproduction") for s in ("fixed-v1", "passage-v1") for b in (1024, 4096) for q in questions]
    require([tuple(r[k] for k in ("pass", "policy", "budget", "population", "question_id")) for r in c["outcomes"]] == expected, "ordered terminal population")
    keys = list(dict.fromkeys(f"{p}/{s}/{b}" for p, s, b, _, _ in expected))
    require(set(c["arms"]) <= set(keys), "extra arms")
    require([c["arms"][k]["attempt"] for k in keys if k in c["arms"]] == list(range(len(c["attempts"]))), "attempt population/order")
    summaries, scores = [], {}
    for key in keys:
        p, policy, budget_text = key.split("/")
        budget = int(budget_text)
        rows = [r for r in c["outcomes"] if (r["pass"], r["policy"], r["budget"]) == (p, policy, budget)]
        arm = c["arms"].get(key)
        if arm is None:
            require(all(r["status"] == "NOT_RUN" and r["attempts"] == [] for r in rows), "unattempted arm")
        else:
            require("failure" not in arm, "arm cannot be fully independently validated: " + key)
            attempt = c["attempts"][arm["attempt"]]
            require(arm["data_manifest"] == manifests, "effective data manifests")
            argv = ["-data", "data", "-dataset", "enterprise-segmentation-v1", "-out", f"{budget}.json", "-mode", "traced", "-policy", "original", "-segment-policy", policy, "-limit", "100", "-budget", str(budget), "-query-timeout", "30s"]
            if budget == 4096:
                previous = c["arms"][f"{p}/{policy}/1024"]
                require(previous["boundary"]["status"] == "COMPLETE" and "failure" not in previous, "reuse predecessor")
                argv.append("-reuse")
            require(attempt["argv"][1:] == argv, "effective argv")
            for field in ("wall_seconds", "user_seconds", "system_seconds", "peak_rss_kib"):
                value = attempt[field]
                require((value is None and field != "wall_seconds") or (type(value) in (int, float) and math.isfinite(value) and value >= 0), "resource metric")
            stream(attempt["stdout"])
            stderr = stream(attempt["stderr"]).decode("utf-8", "replace")
            journal, errors = [], {}
            if "journal_raw" in arm:
                for line in stream(arm["journal_raw"]).splitlines(keepends=True):
                    if not line.endswith(b"\n"):
                        errors["journal"] = "truncated"
                        require(stream(arm["journal_tail"]) == line, "journal tail")
                        break
                    try:
                        entry = parse(line)
                        require(isinstance(entry, dict) and isinstance(entry.get("QueryID"), str), "journal row")
                    except (ValueError, TypeError):
                        errors["journal"] = "malformed"
                        break
                    journal.append(entry)
            require(journal == arm["journal"] and arm["journal_present"] == ("journal_raw" in arm), "journal raw binding")
            prefix = [j["QueryID"] for j in journal]
            require(prefix == qids[:len(prefix)], "journal ordered population")
            segmentation = {"policy": policy, "processor_id": "mousa.text.normalize_utf8", "processor_version": "1", "parameters_sha256": sha(b"" if policy == "fixed-v1" else b'{"segmentation":"passage-v1"}')}
            content = {field: manifests[name]["sha256"] for field, name in (("corpus_sha256", "corpus.jsonl"), ("queries_sha256", "queries.jsonl"), ("qrels_sha256", "qrels/test.tsv"))}
            fields = ["mousa-beir-run", "{" + " ".join(segmentation.values()) + "}", "enterprise-segmentation-v1", "traced", "100", str(budget), "original", "500", str(len(qids)), "0", *content.values()]
            namespace = "run-" + sha("\0".join(fields).encode())[:12]
            config = dict(dataset="enterprise-segmentation-v1", mode="traced", expression_policy="original", limit=100, budget_bytes=budget, corpus_documents=500, judged_queries=len(qids), segmentation=segmentation, content=content, request_namespace=namespace)
            for field in ("report", "manifest"):
                if field + "_raw" not in arm:
                    require(field not in arm, "native missing raw")
                    continue
                try:
                    native = parse(stream(arm[field + "_raw"]))
                    require(isinstance(native, dict), "native object")
                except (ValueError, TypeError):
                    errors[field] = "malformed"
                    require(field not in arm, "malformed native projection")
                    continue
                require(native == arm[field] and all(native[k] == v for k, v in config.items()), "native effective configuration")
                if field == "manifest":
                    require(native["query_timeout"] == 30_000_000_000, "native timeout")
                else:
                    require(native["query_limit"] == 0 and [r["query_id"] for r in native["queries"]] == qids, "report population")
            require(errors == arm["artifact_errors"], "artifact errors")
            failed_id, failed_status = None, None
            boundary = "COMPLETE"
            if attempt["exit"] != 0:
                boundary = "PREPARATION_FAILED" if not arm["journal_present"] else "INTERRUPTED"
                if arm["journal_present"] and len(prefix) < len(qids) and "journal" not in errors:
                    qid = qids[len(prefix)]
                    timeout = any(line.startswith(f"beir: query {qid} exceeded its request deadline: ") for line in stderr.splitlines())
                    failure = timeout or any(line.startswith((f"beir: query {qid}: ", f"beir: search {qid} (")) for line in stderr.splitlines())
                    if failure:
                        boundary, failed_id, failed_status = "QUERY_FAILED", qid, "TIMEOUT" if timeout else "RUN_FAILED"
            elif errors or not arm["journal_present"] or prefix != qids or any(f not in arm for f in ("report", "manifest")):
                boundary = "ARTIFACT_FAILED"
            require((arm["boundary"]["status"], arm["boundary"]["failed_query_id"], arm["boundary"]["failed_query_status"]) == (boundary, failed_id, failed_status), "failure attribution")
            segments = arm.get("store", {}).get("segments", [])
            by_id = {s["segment_id"]: s for s in segments}
            require(len(by_id) == len(segments), "duplicate segment")
            if "store" in arm:
                require(arm["store"]["size_distribution"] == dict(Counter(str(s["end"] - s["start"]) for s in segments)), "size distribution")
                partitions = {}
                for s in segments:
                    body = documents[s["document_id"]]
                    start, end = s["start"], s["end"]
                    require(0 <= start < end <= len(body), "segment bounds")
                    body[:start].decode()
                    body[start:end].decode()
                    require(sha(body[start:end]) == s["record"]["content_sha256"], "source segment bytes")
                    partitions.setdefault(s["document_id"], []).append((start, end))
                require(set(partitions) == set(documents), "segment document population")
                for doc, ranges in partitions.items():
                    cursor = 0
                    for start, end in sorted(ranges):
                        require(start == cursor and end - start <= (4096 if policy == "fixed-v1" else 1024), "segment partition")
                        cursor = end
                    require(cursor == len(documents[doc]), "segment completeness")
                trails = arm["store"]["trails"]
                require(set(prefix) <= set(trails) <= set(qids[:len(prefix) + 1]), "trail population")
                for qid, trail in trails.items():
                    require(trail["external_request_id"] == f"{namespace}-query-{qid}-{qids.index(qid)}", "request namespace")
            for index, row in enumerate(rows):
                status = "SCORED" if index < len(prefix) else failed_status if row["question_id"] == failed_id else "NOT_RUN"
                require(row["status"] == status and row["attempts"] == ([] if status == "NOT_RUN" else [arm["attempt"]]), "row attempt/status")
                if status != "SCORED":
                    continue
                qid = row["question_id"]
                record = arm["store"]["trails"][qid]["record"]
                require(record["budget_bytes"] == budget and "packing_policy" not in record, "packing contract")
                selections, used, rank = [], 0, 0
                for ordinal, candidate in enumerate(record["candidates"] or []):
                    s = by_id[candidate["segment_id"]]
                    accepted = candidate["disposition"] == "accepted"
                    require(candidate["disposition"] in ("accepted", "rejected"), "candidate disposition")
                    rank += int(accepted)
                    size = s["end"] - s["start"] if accepted else 0
                    selected = accepted and used + size <= budget
                    require(candidate["selected"] is selected and candidate["text_bytes"] == size and candidate["final_rank"] == (rank if accepted else 0), "original greedy packing")
                    require(candidate["content_sha256"] == s["record"]["content_sha256"], "candidate content")
                    used += size if selected else 0
                    selections.append(dict(segment_id=candidate["segment_id"], ordinal=ordinal, rank=candidate["final_rank"], disposition=candidate["disposition"], selected=selected, document_id=s["document_id"], start=s["start"], end=s["end"], text_bytes=size))
                ranking = list(dict.fromkeys(s["document_id"] for s in selections if s["disposition"] == "accepted"))
                selected = list(dict.fromkeys(s["document_id"] for s in selections if s["selected"]))
                values = metrics(ranking, gold[qid])
                coverage = len(set(selected) & gold[qid]) / len(gold[qid])
                require(row["metrics"] == values and row["packed_coverage"] == coverage, "independent metrics")
                require(row["ranking"] == ranking == (journal[index]["RankedDocIDs"] or []) and row["selected"] == selected == (journal[index]["SelectedDocIDs"] or []), "ranking/selection")
                require(row["candidates"] == selections and row["used_bytes"] == used == record["used_bytes"] == journal[index]["UsedBytes"] and row["unused_bytes"] == budget - used, "packing projections")
                require(row["omitted_documents"] == [d for d in ranking if d not in selected] and row["disposition_counts"] == dict(Counter(s["disposition"] + ("-selected" if s["selected"] else "-omitted") for s in selections)), "omissions/dispositions")
                require(row["query_work"] == {k: v for k, v in journal[index].items() if "Micros" in k}, "query work")
                scores[(p, policy, budget, qid)] = dict(metrics=values, packed_coverage=coverage, ranking=ranking, selected=selected, candidates=selections, used_bytes=used)
        for row in rows:
            require(row["status"] in ("SCORED", "NOT_RUN", "TIMEOUT", "RUN_FAILED"), "typed terminal status")
            if row["status"] != "SCORED":
                require(row["metrics"] is None and row["packed_coverage"] is None, "missing is not zero")
        scored = [scores[(p, policy, budget, r["question_id"])] for r in rows if r["status"] == "SCORED"]
        summaries.append(dict(arm=key, enrolled=len(rows), statuses=dict(Counter(r["status"] for r in rows)), metrics={k: sum(r["metrics"][k] for r in scored) / len(scored) for k in scored[0]["metrics"]} if scored else None, packed_coverage=sum(r["packed_coverage"] for r in scored) / len(scored) if scored else None))
    complete = len(scores) == len(expected) and all(a["boundary"]["status"] == "COMPLETE" and "failure" not in a for a in c["arms"].values())
    require(c["status"] == ("COMPLETE" if complete else "INCOMPLETE"), "overall status")
    reproduction = []
    for policy in ("fixed-v1", "passage-v1"):
        for budget in (1024, 4096):
            for qid in qids:
                left, right = (scores.get((p, policy, budget, qid)) for p in ("first", "reproduction"))
                reproduction.append(dict(policy=policy, budget=budget, question_id=qid, status="NOT_COMPARABLE" if left is None or right is None else "MATCH" if left == right else "MISMATCH"))
    return dict(status="INDEPENDENT_CHECK_VALID", capture_identity=identity(args.capture.read_bytes()), collection_status=c["status"], confirmation=enrollment["confirmation"], eligible_counts=enrollment["eligibility_counts"], terminal_rows=len(expected), scored_rows=len(scores), summaries=summaries, reproduction=reproduction, effective_inputs=manifests, collection_wall_seconds=c["collection_wall_seconds"], process_resources=[{k: a[k] for k in ("wall_seconds", "user_seconds", "system_seconds", "peak_rss_kib", "exit", "experiment_timeout")} for a in c["attempts"]], limitations=["Independent recorded-consistency audit, not execution authentication.", "Canonical identities require the separate frozen source-bound replay; this checker independently validates source slices, metrics, population, effective inputs and original packing.", "Fresh-store execution and wall cap enforcement require retained collection/build provenance; distinct pass names are not proof.", "No eligible heldout cohort; doc-ID coverage is not semantic sufficiency."])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--public-head", default="a65d9fea1ce5d903e0c672d4cea62e6ce6272654")
    parser.add_argument("--public-tree", default="7cae64f2eb975b9beb2edaadc7923a40547eae60")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args)
    with args.out.open("x") as output:
        json.dump(result, output, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        output.write("\n")
    print(result["status"])
