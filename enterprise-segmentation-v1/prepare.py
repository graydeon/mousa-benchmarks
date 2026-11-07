"""Freeze metadata-only enrollment; never execute retrieval or fetch sources."""
import argparse
from collections import Counter
import hashlib
import importlib.util
from pathlib import Path
import sys
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pilot_v2", ROOT.parent / "enterprise-retrieval-pilot-v2/run.py")
pilot = importlib.util.module_from_spec(spec)
_preparing_module = sys.modules.get("prepare")
spec.loader.exec_module(pilot)
if _preparing_module is not None:
    sys.modules["prepare"] = _preparing_module
base = pilot.prepare
check, encoded, parsed = base.check, base.encoded, base.parsed
SEED = "mousa-enterprise-segmentation-v1-heldout\0"


def enroll(cache):
    protocol = pilot.protocol_at(ROOT.parent / "enterprise-retrieval-pilot-v2/protocol.json")
    stable = base.prepare(protocol, cache)["stable"]
    check(base.manifest(encoded(pilot.input_identity(stable))) == protocol["input_identity"], "original-input-identity")
    check(stable["normalized_text_bytes"] == 4970133 and len(stable["corpus"]) == 500, "original-corpus")
    original = protocol["question_ids"]
    documents = stable["corpus"]
    # Inspect every cached physical version, not merely versions selected into the corpus.
    versions = {}
    for pin in protocol["assets"]:
        if pin["name"].endswith(".zip"):
            with zipfile.ZipFile(cache / pin["name"]) as archive:
                for member in archive.namelist():
                    logical = member.split("/")[-1].split("__")[0]
                    versions.setdefault(logical, []).append((base.physical_id(pin["name"] + ":" + member), base.manifest(archive.read(member))["sha256"]))
    corpus_ids = {d["item_id"] for d in documents}
    decisions, eligible, questions = [], [], {}
    for line in (cache / "questions.jsonl").read_bytes().splitlines(keepends=True):
        q = parsed(line)
        qid = q["question_id"]
        questions[qid] = q
        labels = q["expected_doc_ids"]
        mapping = {label: [item for item, _ in versions.get(label, [])] for label in labels}
        if qid in original:
            reason = "original20"
        elif q["question_type"] not in ("basic", "semantic") or q["source_types"] != ["confluence"] or not labels:
            reason = "ineligible-source-category-labels"
        elif any(not items or not set(items) <= corpus_ids for items in mapping.values()):
            reason = "gold-not-wholly-in-frozen-corpus"
        elif any(len({digest for _, digest in versions[label]}) != 1 for label in labels):
            reason = "ambiguous-physical-versions"
        else:
            reason = "eligible"
            eligible.append(qid)
        decisions.append({"question_id": qid, "reason": reason, "line_identity": base.manifest(line)})
    eligible.sort(key=lambda qid: (hashlib.sha256((SEED + qid).encode()).hexdigest(), qid))
    heldout = eligible[:20] if len(eligible) >= 20 else []
    rows = []
    for population, ids in (("original20", original), ("heldout20", heldout)):
        for qid in ids:
            q = questions[qid]
            rows.append({"population": population, "question": q, "gold": sorted({item for label in q["expected_doc_ids"] for item, _ in versions[label]})})
    return {"schema": "mousa.enterprise_segmentation.enrollment.v1", "seed": SEED,
            "original20": original, "heldout20": heldout, "confirmation": "ENROLLED" if heldout else "UNMET_ELIGIBLE20",
            "eligibility_counts": dict(Counter(d["reason"] for d in decisions)), "decisions": decisions,
            "questions": rows, "corpus": documents, "normalized_text_bytes": stable["normalized_text_bytes"],
            "original_input_identity": protocol["input_identity"], "assets": protocol["assets"]}


def materialize(cache, directory, enrollment):
    protocol = pilot.protocol_at(ROOT.parent / "enterprise-retrieval-pilot-v2/protocol.json")
    pilot.materialize(protocol, cache, directory)
    import json
    rows = enrollment["questions"]
    (directory / "queries.jsonl").write_text("".join(json.dumps({"_id": r["question"]["question_id"], "text": r["question"]["question"]}, ensure_ascii=False) + "\n" for r in rows))
    (directory / "qrels/test.tsv").write_text("query-id\tcorpus-id\tscore\n" + "".join(f'{r["question"]["question_id"]}\t{doc}\t1\n' for r in rows for doc in r["gold"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = enroll(args.cache)
    with args.out.open("xb") as output:
        output.write(encoded(result))
    print(encoded({k: result[k] for k in ("confirmation", "eligibility_counts", "original20", "heldout20")}).decode())
