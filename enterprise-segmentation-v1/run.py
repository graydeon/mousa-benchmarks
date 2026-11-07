"""Collect fixed segmentation arms once and reproduce within one elapsed cap."""
import argparse
from collections import Counter
from pathlib import Path
import hashlib
import platform
import sqlite3
import sys
import time

sys.dont_write_bytecode = True
from prepare import ROOT, base, check, encoded, enroll, materialize, parsed, pilot


def load_contract():
    protocol = parsed((ROOT / "protocol.json").read_bytes())
    enrollment = parsed((ROOT / "enrollment.json").read_bytes())
    check(pilot.identity(ROOT / "enrollment.json") == protocol["enrollment_identity"], "enrollment-identity")
    for name, identity in protocol["helpers"].items():
        check(pilot.identity(ROOT.parent / name) == identity, "helper-identity")
    return protocol, enrollment


def tuple_hash(fields):
    return hashlib.sha256(b"".join(len(field).to_bytes(8, "big") + field for field in fields)).hexdigest()


def validate_segments(segments, data_directory, expected_policy):
    check(expected_policy in ("fixed-v1", "passage-v1"), "segment-policy")
    parameters = hashlib.sha256(b"" if expected_policy == "fixed-v1" else b'{"segmentation":"passage-v1"}').hexdigest()
    source_id = tuple_hash([b"mousa.source.v1", b"beir-eval", b"enterprise-segmentation-v1"])
    corpus = [parsed(line) for line in (data_directory / "corpus.jsonl").read_bytes().splitlines()]
    whitespace = "\t\n\v\f\r \u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"
    documents = {d["_id"]: (d["title"] + "\n" + d["text"]).strip(whitespace).encode() for d in corpus}
    check(len(documents) == len(corpus), "duplicate-corpus-document")
    ids = sorted(documents)
    seen = set()
    for segment in segments:
        observation, artifact, representation, record = (segment[k] for k in ("observation", "artifact", "representation", "record"))
        external = observation["external_observation_id"]
        check(external.startswith("doc-") and external[4:].isdigit(), "observation-document-index")
        index = int(external[4:])
        check(index < len(ids) and external == f"doc-{index}", "observation-document-index")
        check(segment["document_id"] == ids[index], "segment-document-binding")
        check(observation["schema"] == "mousa.observation.v1" and observation["source_id"] == source_id and observation["id"] == tuple_hash([b"mousa.observation.v1", bytes.fromhex(source_id), external.encode()]), "observation-identity")
        check(artifact["schema"] == "mousa.artifact.v1" and artifact["id"] == tuple_hash([b"mousa.artifact.v1", bytes.fromhex(observation["id"]), b"body"]), "artifact-identity")
        content = documents[ids[index]]
        check(artifact["observation_id"] == observation["id"] and artifact["artifact_key"] == "body", "artifact-observation-binding")
        check(artifact["byte_length"] == len(content) and artifact["content_sha256"] == hashlib.sha256(content).hexdigest(), "artifact-source-binding")
        normalized = content.removeprefix(b"\xef\xbb\xbf").replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        normalized.decode("utf-8")
        check(representation["inputs"] == [{"kind": "artifact", "id": artifact["id"]}], "representation-input-binding")
        check(representation["byte_length"] == len(normalized) and representation["content_sha256"] == hashlib.sha256(normalized).hexdigest(), "normalization-binding")
        check(representation["schema"] == "mousa.representation.v1" and representation["processor_id"] == "mousa.text.normalize_utf8" and representation["processor_version"] == "1" and representation["parameters_sha256"] == parameters, "representation-policy-binding")
        check(artifact["media_type"] == representation["media_type"] == "text/plain; charset=utf-8", "representation-media-binding")
        check(representation["id"] == tuple_hash([b"mousa.representation.v1", (1).to_bytes(8, "big"), b"artifact", bytes.fromhex(artifact["id"]),
                                                b"mousa.text.normalize_utf8", b"1", bytes.fromhex(parameters), representation["media_type"].encode(),
                                                bytes.fromhex(representation["content_sha256"])]), "representation-identity")
        start, end = segment["start"], segment["end"]
        check(0 <= start < end <= len(normalized), "segment-slice-bounds")
        normalized[:start].decode("utf-8")
        normalized[start:end].decode("utf-8")
        check(record["id"] == segment["segment_id"] and record["id"] not in seen, "segment-identity-binding")
        seen.add(record["id"])
        check(record["representation_id"] == representation["id"] and record["selector"]["start"] == start and record["selector"]["end"] == end, "segment-selector-binding")
        check(record["content_sha256"] == hashlib.sha256(normalized[start:end]).hexdigest(), "segment-source-slice-binding")
        check(record["schema"] == "mousa.segment.v1" and record["selector"]["schema"] == "mousa.selector.text_byte_range.v1", "segment-schema")
        check(record["id"] == tuple_hash([b"mousa.segment.v1", bytes.fromhex(representation["id"]), b"mousa.selector.text_byte_range.v1",
                                         start.to_bytes(8, "big"), end.to_bytes(8, "big"), bytes.fromhex(record["content_sha256"])]), "segment-canonical-identity")
    by_document = {}
    for segment in segments:
        by_document.setdefault(segment["document_id"], []).append(segment)
    for document_id, content in documents.items():
        normalized = content.removeprefix(b"\xef\xbb\xbf").replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        cursor = 0
        for segment in sorted(by_document.get(document_id, []), key=lambda s: s["start"]):
            check(segment["start"] == cursor and segment["end"] - cursor <= (4096 if expected_policy == "fixed-v1" else 1024), "segment-partition-binding")
            cursor = segment["end"]
        check(cursor == len(normalized), "segment-population-completeness")


def store_facts(path, previous, data_directory, policy):
    corpus_ids = sorted(parsed(line)["_id"] for line in (data_directory / "corpus.jsonl").read_bytes().splitlines())
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        segments = []
        for sid, start, end, raw, rep_raw, artifact_raw, observation_raw in db.execute(
                "SELECT hex(s.id),s.selector_start,s.selector_end,s.record_json,r.record_json,a.record_json,o.record_json "
                "FROM segments s JOIN representations r ON r.id=s.representation_id "
                "JOIN representation_inputs i ON i.representation_id=r.id AND i.input_kind='artifact' "
                "JOIN artifacts a ON a.id=i.artifact_id JOIN observations o ON o.id=a.observation_id ORDER BY s.id"):
            observation = parsed(observation_raw)
            external = observation["external_observation_id"]
            check(external.startswith("doc-") and external[4:].isdigit(), "observation-document-index")
            index = int(external[4:])
            check(index < len(corpus_ids), "observation-document-index")
            segments.append({"segment_id": sid.lower(), "document_id": corpus_ids[index],
                             "start": int.from_bytes(start, "big"), "end": int.from_bytes(end, "big"),
                             "record": parsed(raw), "representation": parsed(rep_raw),
                             "artifact": parsed(artifact_raw), "observation": observation})
        check(len(segments) == db.execute("SELECT count(*) FROM segments").fetchone()[0], "segment-ancestry-completeness")
        validate_segments(segments, data_directory, policy)
        trails = {}
        for tid, request, decision, request_id, raw in db.execute("SELECT hex(t.id),d.external_request_id,hex(t.decision_id),hex(d.request_id),t.record_json FROM source_trails t JOIN policy_decisions d ON t.decision_id=d.id"):
            if tid not in previous:
                qid = request.rsplit("-query-", 1)[1].rsplit("-", 1)[0]
                check(qid not in trails, "duplicate-query-trail")
                candidates = [{"segment_id": sid.lower(), "ordinal": ordinal, "rank": rank, "disposition": disposition, "selected": bool(selected)} for sid, ordinal, rank, disposition, selected in db.execute("SELECT hex(segment_id),ordinal,final_rank,disposition,selected FROM source_trail_candidates WHERE trail_id=? ORDER BY ordinal", (bytes.fromhex(tid),))]
                trails[qid] = {"id": tid.lower(), "record": parsed(raw), "candidates": candidates,
                               "external_request_id": request, "decision_id": decision.lower(), "request_id": request_id.lower()}
        all_ids = {row[0] for row in db.execute("SELECT hex(id) FROM source_trails")}
    return {"segments": segments, "size_distribution": dict(Counter(str(s["end"]-s["start"]) for s in segments)), "trails": trails}, all_ids


def ledger(enrollment):
    return [{"pass": label, "policy": policy, "budget": budget,
             "population": q["population"], "question_id": q["question"]["question_id"],
             "status": "NOT_RUN", "reason": "execution not reached", "attempts": [],
             "metrics": None, "packed_coverage": None}
            for label in ("first", "reproduction") for policy in ("fixed-v1", "passage-v1")
            for budget in (1024, 4096) for q in enrollment["questions"]]


def scored(row, journal, trail, segments, gold):
    record = trail["record"]
    check(record["schema"] == "mousa.source_trail.v1" and "packing_policy" not in record, "canonical-original-packing")
    check(set(record) == {"schema", "id", "request_id", "decision_id", "outcome", "expression", "budget_bytes", "used_bytes", "packet_id", "candidates"}, "canonical-trail-fields")
    check(record["outcome"] == "allow" and record["budget_bytes"] == row["budget"], "canonical-budget-binding")
    check(record["id"] == trail["id"].lower() and record["decision_id"] == trail["decision_id"] and record["request_id"] == trail["request_id"], "canonical-trail-projections")
    canonical = record["candidates"] or []
    check(len(canonical) == len(trail["candidates"]), "canonical-candidate-count")
    check(len({c["segment_id"] for c in canonical}) == len(canonical), "canonical-duplicate-candidate")
    by_id = {s["segment_id"]: s for s in segments}
    selections, rank, used = [], 0, 0
    packet_fields = [b"mousa.context_packet.v1", row["budget"].to_bytes(8, "big")]
    fields = [record["schema"].encode(), bytes.fromhex(record["request_id"]), bytes.fromhex(record["decision_id"]),
              record["outcome"].encode(), record["expression"].encode(), row["budget"].to_bytes(8, "big"),
              record["used_bytes"].to_bytes(8, "big"), bytes.fromhex(record["packet_id"])]
    for ordinal, (candidate, projection) in enumerate(zip(canonical, trail["candidates"])):
        check(set(candidate) == {"segment_id", "content_sha256", "final_rank", "text_bytes", "disposition", "reasons", "selected"}, "canonical-candidate-fields")
        check(projection == {"segment_id": candidate["segment_id"], "ordinal": ordinal, "rank": candidate["final_rank"],
                             "disposition": candidate["disposition"], "selected": candidate["selected"]}, "canonical-candidate-projection")
        segment = by_id[candidate["segment_id"]]
        check(candidate["content_sha256"] == segment["record"]["content_sha256"], "canonical-candidate-content")
        accepted = candidate["disposition"] == "accepted"
        check(candidate["disposition"] in ("accepted", "rejected"), "canonical-disposition")
        if accepted:
            rank += 1
        size = segment["end"] - segment["start"] if accepted else 0
        check(candidate["final_rank"] == (rank if accepted else 0) and candidate["text_bytes"] == size, "canonical-rank-size")
        selected = accepted and size <= row["budget"] - used
        check(type(candidate["selected"]) is bool and candidate["selected"] == selected, "canonical-original-selection")
        if selected:
            used += size
            packet_fields.extend([bytes.fromhex(candidate["segment_id"]), bytes.fromhex(candidate["content_sha256"]),
                                  candidate["final_rank"].to_bytes(8, "big"), size.to_bytes(8, "big")])
        fields.extend([b"candidate", bytes.fromhex(candidate["segment_id"]), bytes.fromhex(candidate["content_sha256"]),
                       candidate["final_rank"].to_bytes(8, "big"), size.to_bytes(8, "big"), candidate["disposition"].encode(),
                       bytes([int(selected)]) + bytes(7)])
        fields.extend(reason.encode() for reason in candidate["reasons"] or [])
        fields.append(b"end")
        selections.append(dict(projection, document_id=segment["document_id"], start=segment["start"], end=segment["end"], text_bytes=size))
    packet_fields.append(used.to_bytes(8, "big"))
    check(tuple_hash(packet_fields) == record["packet_id"] and tuple_hash(fields) == record["id"], "canonical-packing-identity")
    ranking = list(dict.fromkeys(c["document_id"] for c in selections if c["disposition"] == "accepted"))
    selected = list(dict.fromkeys(c["document_id"] for c in selections if c["selected"]))
    check(ranking == (journal["RankedDocIDs"] or []) and selected == (journal["SelectedDocIDs"] or []), "canonical-document-ranking-selection")
    check(used == record["used_bytes"] == journal["UsedBytes"] and used <= row["budget"], "packed-byte-binding")
    return dict(row, status="SCORED", reason=None, ranking=ranking, selected=selected,
                candidates=selections, omitted_documents=[d for d in ranking if d not in selected],
                disposition_counts=dict(Counter(c["disposition"] + ("-selected" if c["selected"] else "-omitted") for c in selections)),
                used_bytes=used, unused_bytes=row["budget"]-used,
                metrics=pilot.metrics_module.metrics(ranking, gold), packed_coverage=len(set(selected)&gold)/len(gold),
                query_work={k: v for k,v in journal.items() if "Micros" in k})


def artifact_fields(journal_bytes, report_bytes, manifest_bytes):
    native = {"journal_present": journal_bytes is not None, "journal": [], "artifact_errors": {}}
    if journal_bytes is not None:
        native["journal_raw"] = base.wire.stream(journal_bytes)
        lines = journal_bytes.splitlines(keepends=True)
        for line in lines:
            if not line.endswith(b"\n"):
                native["journal_tail"] = base.wire.stream(line)
                native["artifact_errors"]["journal"] = "truncated"
                break
            try:
                entry = parsed(line)
                check(isinstance(entry, dict) and isinstance(entry.get("QueryID"), str), "journal-row-shape")
            except (ValueError, TypeError):
                native["artifact_errors"]["journal"] = "malformed"
                break
            native["journal"].append(entry)
    for field, raw in (("report", report_bytes), ("manifest", manifest_bytes)):
        if raw is None:
            continue
        native[field + "_raw"] = base.wire.stream(raw)
        try:
            value = parsed(raw)
            check(isinstance(value, dict), "artifact-object")
        except (ValueError, TypeError):
            native["artifact_errors"][field] = "malformed"
        else:
            native[field] = value
    return native


def arm_boundary(native, attempt, expected):
    prefix = [entry["QueryID"] for entry in native["journal"]]
    check(prefix == expected[:len(prefix)], "native-journal-prefix")
    boundary = {"status": "COMPLETE", "reason": None, "failed_query_id": None, "failed_query_status": None}
    if attempt["exit"] != 0:
        if not native["journal_present"]:
            boundary.update(status="PREPARATION_FAILED", reason="native process failed before query journal creation")
            return boundary
        if len(prefix) < len(expected) and "journal" not in native["artifact_errors"]:
            qid = expected[len(prefix)]
            diagnostics = attempt["stderr"]["text"].splitlines()
            timeout = any(line.startswith(f"beir: query {qid} exceeded its request deadline: ") for line in diagnostics)
            failed = timeout or any(line.startswith((f"beir: query {qid}: ", f"beir: search {qid} (")) for line in diagnostics)
            if failed:
                boundary.update(status="QUERY_FAILED", reason="native diagnostic identifies first unjournaled query failure",
                                failed_query_id=qid, failed_query_status="TIMEOUT" if timeout else "RUN_FAILED")
                return boundary
        boundary.update(status="INTERRUPTED", reason="native process failed with unobserved query/report boundary")
    elif native["artifact_errors"] or not native["journal_present"] or prefix != expected or any(
            field not in native for field in ("report", "manifest")):
        boundary.update(status="ARTIFACT_FAILED", reason="native success lacks complete readable journal/report/manifest")
    return boundary


def execute(args):
    protocol, enrollment = load_contract()
    check(enroll(args.cache) == enrollment, "source-enrollment-binding")
    publication = parsed(args.publication.read_bytes())
    check(publication["binary_identity"] == pilot.identity(args.beir), "published-binary-identity")
    check(len(publication["public_head"]) == 40 and len(publication["public_tree"]) == 40, "public-source-identity")
    work = args.out.resolve()
    work.mkdir(parents=True, exist_ok=False)
    capture = {"schema": "mousa.enterprise_segmentation.capture.v1", "protocol": protocol,
               "enrollment": enrollment, "publication": publication, "outcomes": ledger(enrollment),
               "arms": {}, "attempts": [], "environment": {"python": sys.version, "platform": platform.platform()},
               "started_unix": time.time(), "model_calls": 0, "network_calls": 0}
    gold = {q["question"]["question_id"]: set(q["gold"]) for q in enrollment["questions"]}
    started = time.monotonic()
    def checkpoint():
        capture["collection_wall_seconds"] = time.monotonic()-started
        base.wire.write_capture(work / "capture.json.gz", capture)
    checkpoint()
    try:
        for label in ("first", "reproduction"):
            for policy in ("fixed-v1", "passage-v1"):
                directory = work / label / policy
                directory.mkdir(parents=True)
                if time.monotonic()-started >= protocol["collection_cap_seconds"]:
                    continue
                materialize(args.cache, directory / "data", enrollment)
                commands = pilot.Commands(directory, started + protocol["collection_cap_seconds"])
                previous, reusable = set(), False
                for budget in (1024, 4096):
                    if time.monotonic()-started >= protocol["collection_cap_seconds"]:
                        break
                    key = f"{label}/{policy}/{budget}"
                    rows = [r for r in capture["outcomes"] if (r["pass"],r["policy"],r["budget"]) == (label,policy,budget)]
                    name = f"{budget}.json"
                    argv = [str(args.beir.resolve()), "-data", "data", "-dataset", "enterprise-segmentation-v1", "-out", name,
                            "-mode", "traced", "-policy", "original", "-segment-policy", policy,
                            "-limit", "100", "-budget", str(budget), "-query-timeout", "30s"]
                    if reusable:
                        argv.append("-reuse")
                    attempt = commands.run(argv, "process open/ingest-or-rebuild/query/report/close; child CPU and peak RSS")
                    attempt_id = len(capture["attempts"])
                    capture["attempts"].append(attempt)
                    native = {"data_manifest": pilot.data_manifest(directory / "data"), "attempt": attempt_id}
                    capture["arms"][key] = native
                    failure_stage = "artifacts"
                    try:
                        journal_path = directory / (name + ".jsonl")
                        journal_bytes = journal_path.read_bytes() if journal_path.exists() else None
                        native.update(artifact_fields(journal_bytes, None, None))
                        checkpoint()
                        for suffix, field in (("", "report"), (".manifest.json", "manifest")):
                            path = directory / (name + suffix)
                            if path.exists():
                                raw = path.read_bytes()
                                fields = artifact_fields(None, raw if field == "report" else None,
                                                         raw if field == "manifest" else None)
                                native["artifact_errors"].update(fields["artifact_errors"])
                                native[field + "_raw"] = fields[field + "_raw"]
                                if field in fields:
                                    native[field] = fields[field]
                        expected = [row["question_id"] for row in rows]
                        native["boundary"] = arm_boundary(native, attempt, expected)
                        boundary = native["boundary"]
                        if boundary["failed_query_id"] is not None:
                            failed = rows[len(native["journal"])]
                            failed.update(attempts=[attempt_id], status=boundary["failed_query_status"],
                                          reason=boundary["reason"])
                        for row in rows[:len(native["journal"])]:
                            row.update(attempts=[attempt_id], status="RUN_FAILED", reason="completed journal row could not be scored")
                        failure_stage = "store"
                        if native["journal"] or attempt["exit"] == 0:
                            native["store"], previous = store_facts(directory / "enterprise-segmentation-v1.sqlite", previous, directory / "data", policy)
                        failure_stage = "scoring"
                        for row, journal in zip(rows, native["journal"]):
                            row.update(scored(row, journal, native["store"]["trails"][row["question_id"]], native["store"]["segments"], gold[row["question_id"]]))
                        if boundary["status"] == "COMPLETE":
                            failure_stage = "artifacts"
                            check(native["report"]["segmentation"]["policy"] == policy, "segmentation-policy-binding")
                            reusable = True
                    except Exception as error:
                        native["failure"] = str(error)
                        native["failure_stage"] = failure_stage
                    checkpoint()
                    if "failure" in native or native["boundary"]["status"] != "COMPLETE":
                        break
    except Exception as error:
        capture["failure"] = str(error)
    finally:
        capture["status"] = "COMPLETE" if all(r["status"] == "SCORED" for r in capture["outcomes"]) and all(
            "failure" not in arm and arm.get("boundary", {}).get("status") == "COMPLETE"
            for arm in capture["arms"].values()) else "INCOMPLETE"
        checkpoint()
    print(encoded({"status": capture["status"], "confirmation": enrollment["confirmation"], "wall_seconds": capture["collection_wall_seconds"]}).decode())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--beir", type=Path, required=True)
    parser.add_argument("--publication", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    execute(parser.parse_args())
