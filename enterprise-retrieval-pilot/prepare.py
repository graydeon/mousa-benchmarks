"""Reproduce the fixed EnterpriseRAG pilot enrollment and fail closed on its bounds."""
import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import stat
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pilot_wire", ROOT.parent / "mcp-trail-supersession/run.py")
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
SALT = b"mousa-enterprise-pilot-v1\0"
ARMS = [f"mousa-{policy}-{mode}" for policy in ("original", "dedup")
        for mode in ("verified", "traced-1024", "traced-4096")] + ["sqlite-fts5", "qmd-search"]


def check(condition, detector):
    if not condition:
        raise ValueError(detector)


def parsed(raw):
    value, duplicates = wire.strict_json(raw)
    check(not duplicates, "duplicate-json-key")
    # The shared parser reports duplicate keys; reject nonfinite numbers too.
    json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite-json")))
    return value


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode()


def ordered(identity):
    return hashlib.sha256(SALT + identity.encode("utf-8")).hexdigest(), identity


def manifest(raw):
    return wire.manifest(raw)


def physical_id(identity):
    return "p_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


def render(raw):
    text = raw.decode("utf-8", errors="strict")
    # Match Go strings.TrimSpace, not Python's additional C0 separators.
    whitespace = "\t\n\v\f\r \u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"
    text = text.strip(whitespace)
    # Source .txt already starts with its title. BEIR receives title="", text=rendered.
    # NormalizeUTF8Text removes a leading BOM and folds CRLF/CR without other rewriting.
    if text.startswith("\ufeff"):
        text = text[1:]
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def download(protocol, cache):
    cache.mkdir(parents=True, exist_ok=False)
    total = 0
    receipts = []
    for pin in protocol["assets"]:
        check(total + pin["size"] <= protocol["compressed_cap_bytes"], "compressed-bound")
        started = time.monotonic()
        digest, count = hashlib.sha256(), 0
        with urllib.request.urlopen(pin["browser_download_url"], timeout=60) as response, (cache / pin["name"]).open("xb") as output:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                count += len(chunk)
                total += len(chunk)
                check(count <= pin["size"] and total <= protocol["compressed_cap_bytes"], "download-stream-bound")
                output.write(chunk)
                digest.update(chunk)
        check(count == pin["size"] and digest.hexdigest() == pin["sha256"], "asset-identity")
        receipts.append({"name": pin["name"], "bytes": count, "sha256": digest.hexdigest(),
                         "wall_seconds": time.monotonic() - started})
    return receipts


def prepare(protocol, cache):
    started = time.monotonic()
    source_bytes = 0
    for pin in protocol["assets"]:
        raw = (cache / pin["name"]).read_bytes()
        check(len(raw) == pin["size"] and manifest(raw)["sha256"] == pin["sha256"], "asset-identity")
        source_bytes += len(raw)
    check(source_bytes <= protocol["compressed_cap_bytes"], "compressed-bound")
    question_lines = (cache / "questions.jsonl").read_bytes().splitlines(keepends=True)
    questions, decisions, seen = [], [], set()
    for line_number, line in enumerate(question_lines, 1):
        question = parsed(line)
        qid = question["question_id"]
        check(qid not in seen, "duplicate-question-id")
        seen.add(qid)
        category_ok = question["question_type"] in ("basic", "semantic")
        source_ok = question["source_types"] == ["confluence"]
        labels_ok = bool(question["expected_doc_ids"])
        eligible = category_ok and source_ok and labels_ok
        decisions.append({"question_id": qid, "line": line_number, "category_ok": category_ok,
                          "confluence_only": source_ok, "has_labels": labels_ok, "eligible": eligible,
                          "line_identity": manifest(line)})
        if eligible:
            questions.append({"question": question, "raw_line": wire.stream(line), "line": line_number})
    counts = {category: sum(q["question"]["question_type"] == category for q in questions)
              for category in ("basic", "semantic")}
    check(counts == protocol["eligible_counts"], "eligibility-snapshot-mismatch")
    enrolled = []
    for category in ("basic", "semantic"):
        candidates = sorted((q for q in questions if q["question"]["question_type"] == category),
                            key=lambda q: ordered(q["question"]["question_id"]))
        check(len(candidates) >= 10, "insufficient-eligible-cases")
        enrolled.extend(candidates[:10])
    selected_ids = [q["question"]["question_id"] for q in enrolled]
    check(selected_ids == protocol["question_ids"], "enrollment-identity")
    for decision in decisions:
        decision["selected"] = decision["question_id"] in selected_ids
    docs, decompressed = [], 0
    for pin in protocol["assets"]:
        if not pin["name"].endswith(".zip"):
            continue
        with zipfile.ZipFile(cache / pin["name"]) as archive:
            paths = set()
            for member in archive.infolist():
                path = PurePosixPath(member.filename)
                mode = member.external_attr >> 16
                check(not path.is_absolute() and ".." not in path.parts and "\\" not in member.filename
                      and str(path) == member.filename and member.filename not in paths
                      and not member.is_dir() and stat.S_IFMT(mode) in (0, stat.S_IFREG), "unsafe-archive-member")
                paths.add(member.filename)
                check(member.file_size <= 16 << 20, "source-member-bound")
                decompressed += member.file_size
                check(decompressed + source_bytes <= protocol["source_cache_cap_bytes"], "source-cache-bound")
                # Read regular members as data only; never extract paths or execute contents.
                with archive.open(member) as source:
                    raw = source.read(member.file_size + 1)
                check(len(raw) == member.file_size, "source-member-size")
                identity = pin["name"] + ":" + member.filename
                label = re.fullmatch(r"confluence/(dsid_[0-9a-f]+)__[^/]+\.txt", member.filename)
                check(label is not None, "unsupported-body-representation")
                row = {"physical_identity": identity, "item_id": physical_id(identity),
                       "logical_id": label[1], "asset_sha256": pin["sha256"],
                       "member": member.filename, "raw": manifest(raw)}
                try:
                    rendered = render(raw)
                    row.update(rendered=manifest(rendered), preparation="ready",
                               title=raw.decode("utf-8").splitlines()[0],
                               original_body={"format": "utf8-text", "member": member.filename,
                                              "start_byte": 0, "end_byte": len(raw)})
                except UnicodeDecodeError:
                    row.update(preparation="decoding_failure")
                docs.append(row)
    expected = {label for q in enrolled for label in q["question"]["expected_doc_ids"]}
    gold = [d for d in docs if d["logical_id"] in expected]
    # Retain every physical version, even when a label is unscorable.
    selected = sorted(gold, key=lambda d: d["physical_identity"])
    remaining = sorted((d for d in docs if d["logical_id"] not in expected),
                       key=lambda d: ordered(d["physical_identity"]))
    selected.extend(remaining[:max(0, protocol["document_cap"] - len(selected))])
    total_text = sum(d.get("rendered", {}).get("bytes", 0) for d in selected)
    bound_failed = len(selected) > protocol["document_cap"] or total_text > protocol["text_cap_bytes"]
    global_status = "preparation_bound_failure" if bound_failed else "prepared"
    outcomes = []
    for enrolled_question in enrolled:
        q = enrolled_question["question"]
        mappings = {label: [d["item_id"] for d in gold if d["logical_id"] == label]
                    for label in q["expected_doc_ids"]}
        versions = {label: {d["raw"]["sha256"] for d in gold if d["logical_id"] == label}
                    for label in q["expected_doc_ids"]}
        if any(not ids for ids in mappings.values()):
            identity_status = "missing_evidence"
        elif any(len(hashes) > 1 for hashes in versions.values()):
            identity_status = "unscorable_identity_ambiguity"
        elif any(d["preparation"] != "ready" for d in gold if d["logical_id"] in mappings):
            identity_status = "decoding_failure"
        else:
            identity_status = "resolved"
        status = global_status if bound_failed else identity_status
        outcomes.append({"question_id": q["question_id"], "category": q["question_type"],
                         "expected_doc_ids": q["expected_doc_ids"], "mapping": mappings,
                         "identity_status": identity_status, "terminal_outcome": status,
                         "arms": [{"arm": arm, "status": "NOT_RUN", "reason": status,
                                   "attempts": [], "metrics": None, "packed_coverage": None}
                                  for arm in ARMS]})
    stable = {"schema": "mousa.enterprise_preparation.v1", "status": global_status,
              "eligibility": decisions, "eligible_counts": counts, "enrolled": enrolled,
              "corpus": selected, "source_documents": len(docs), "gold_physical_documents": len(gold),
              "compressed_bytes": source_bytes, "decompressed_bytes": decompressed,
              "normalized_text_bytes": total_text, "text_cap_bytes": protocol["text_cap_bytes"],
              "selected_documents": len(selected), "selected_questions": len(enrolled),
              "executable_questions": 0 if bound_failed else sum(o["identity_status"] == "resolved" for o in outcomes),
              "scored_questions": 0, "score_denominator": 0, "outcomes": outcomes}
    return {"stable": stable, "wall_seconds": time.monotonic() - started}


def verify(observed, expected):
    left, right = observed["stable"], expected["stable"]
    check([q["question"]["question_id"] for q in left["enrolled"]]
          == [q["question"]["question_id"] for q in right["enrolled"]], "enrollment-identity")
    check(wire.same_json([o["mapping"] for o in left["outcomes"]],
                         [o["mapping"] for o in right["outcomes"]]), "logical-physical-mapping")
    check(wire.same_json(left, right), "preparation-reproduction")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("download", "prepare", "verify"))
    parser.add_argument("--protocol", type=Path, default=ROOT / "protocol.json")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--capture", type=Path)
    args = parser.parse_args()
    protocol = parsed(args.protocol.read_bytes())
    if args.mode == "download":
        print(json.dumps(download(protocol, args.cache), indent=2))
        return 0
    observed = prepare(protocol, args.cache)
    if args.mode == "verify":
        check(args.capture is not None, "capture-required")
        verify(wire.load_capture(args.capture), observed)
        print("PASS: exact enrollment, physical mappings, corpus bytes and terminal outcomes reproduced")
        return 0
    check(args.out is not None and not args.out.exists(), "new-output-required")
    wire.write_capture(args.out, observed)
    print(json.dumps({k: v for k, v in observed["stable"].items()
                      if k not in ("eligibility", "enrolled", "corpus", "outcomes")}, indent=2))
    return 2 if observed["stable"]["status"] == "preparation_bound_failure" else 0


if __name__ == "__main__":
    raise SystemExit(main())
