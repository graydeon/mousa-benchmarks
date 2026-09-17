"""Verify archived sources, input bytes, query ranges and declared coverage."""

import argparse
import json
from pathlib import Path
import sys
import tarfile
import tempfile

import run


def unpack(path, target):
    with tarfile.open(path) as archive:
        seen = set()
        for member in archive.getmembers():
            relative = Path(member.name)
            if ((not member.isfile() and not member.isdir()) or relative.is_absolute() or ".." in relative.parts
                    or member.name in seen or member.size > 8_000_000):
                raise ValueError("invalid archive member: " + member.name)
            seen.add(member.name)
            output = target / relative
            if member.isdir():
                output.mkdir(parents=True, exist_ok=True)
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(archive.extractfile(member).read())


def verify(directory, base_source=None):
    identity = json.loads((directory / "identity.json").read_text())
    assert run.digest(directory / "source-manifest.json") == identity["source_manifest_sha256"]
    assert run.digest(directory / "run.py") == identity["run_sha256"]
    assert run.digest(directory / "cases.json") == identity["cases_sha256"]
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "source"
        if (directory / "source.tar.gz").exists():
            unpack(directory / "source.tar.gz", source)
        else:
            if base_source is None:
                raise ValueError("source delta requires --base-source archive of the recorded product base")
            unpack(base_source, source)
            unpack(directory / "source-delta.tar.gz", source)
        expected = json.loads((directory / "source-manifest.json").read_text())
        actual = {str(p.relative_to(source)): run.digest(p) for p in source.rglob("*") if p.is_file()}
        assert actual == expected
        sys.path.insert(0, str(source / "examples/docs"))
        import docs
        corpora = {}
        for arm in ("original", "expanded"):
            corpus = root / arm
            unpack(directory / (arm + "-corpus.tar.xz"), corpus)
            manifest, documents, _ = docs.load_corpus(corpus)
            corpora[arm] = (manifest, documents)
        assert (directory / "expanded-corpus.tar.xz").read_bytes() == (source / "examples/docs/git-docs.tar.xz").read_bytes()
        assert (directory / "questions.json").read_bytes() == (source / "examples/docs/questions.json").read_bytes()
        protocol = json.loads((directory / "cases.json").read_text())
        old = json.loads((directory / "questions.json").read_text())
        cases = [{**case, "support": [{"item": case["item"], "text": text} for text in case["support"]]}
                 for case in old["development"]] + protocol["development"]
        by_id = {case["id"]: case for case in cases}
        for case in cases:
            for passage in case["support"]:
                assert passage["text"].encode() in run.normalize(corpora["expanded"][1][passage["item"]])
        rows = [json.loads(line) for line in (directory / "observations.jsonl").read_text().splitlines()]
        repeats = 1 if identity["mode"] == "pilot" else protocol["repeats"]
        schedule = [(repeat, case["id"], arm) for repeat in range(repeats) for index, case in enumerate(cases)
                    for arm in (("original", "expanded") if (repeat + index) % 2 == 0 else ("expanded", "original"))]
        assert [(r["repeat"], r["case"], r["arm"]) for r in rows] == schedule
        analysis = []
        requests = set()
        for row in rows:
            assert row["exit"] == 0
            assert row["counts_before"]["source_trails"] == row["counts_before"]["policy_decisions"] == 0
            assert row["counts_after"]["source_trails"] == row["counts_after"]["policy_decisions"] == 1
            packet = json.loads(row["stdout"])
            assert packet["response"]["query"] == by_id[row["case"]]["question"]
            assert packet["response"]["budget_bytes"] == protocol["budget_bytes"]
            assert packet["response"]["decision_outcome"] == "allow"
            assert packet["response"]["request_id"] not in requests
            requests.add(packet["response"]["request_id"])
            manifest, documents = corpora[row["arm"]]
            assert row["document_count"] == len(documents)
            assert row["corpus_document_bytes"] == sum(map(len, documents.values()))
            assessment = run.assess(packet, by_id[row["case"]], manifest, documents, docs.verify_evidence, protocol["budget_bytes"])
            analysis.append({**{key: row[key] for key in ("repeat", "case", "arm", "wall_ms")}, "assessment": assessment})
        assert json.loads((directory / "analysis.json").read_text()) == {"execution": "PASS", "rows": analysis}
        print("Verified", identity["mode"], len(rows), "queries, source snapshot, input hashes, coordinates and support rubric")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--base-source", type=Path)
    args = parser.parse_args()
    verify(args.directory.resolve(), args.base_source)
