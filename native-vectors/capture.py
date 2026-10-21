"""Capture synthetic caller-supplied vectors through native Mousa commands."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


HERO = "Shield the specimen cabinet from heat.\n"
DIVERSION = "The tram arrives at noon.\n"
REVISED = "Move the cabinet to the replacement enclosure.\n"
PINS = ("source_id", "segment_id", "representation_id",
        "representation_sha256", "content_sha256")


def encoded(value):
    return json.dumps(value, separators=(",", ":")) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mousa", type=Path, required=True)
    parser.add_argument("--product-source", type=Path, required=True)
    parser.add_argument("--product-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    binary = args.mousa.resolve()

    def git(*arguments):
        return subprocess.check_output(
            ["git", *arguments], cwd=args.product_source, text=True, timeout=30).strip()

    if git("rev-parse", "HEAD") != args.product_head:
        raise ValueError("product checkout does not match the requested public head")
    if git("status", "--porcelain"):
        raise ValueError("product checkout must be clean")
    args.output.mkdir(parents=True, exist_ok=False)
    receipts = []

    def save(name, value):
        (args.output / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    save("product.json", {
        "repository": "https://github.com/graydeon/mousa",
        "head": args.product_head, "tree": git("rev-parse", "HEAD^{tree}"),
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "go_version": subprocess.check_output(["go", "version"], text=True, timeout=30).strip(),
        "build": "GOWORK=off CGO_ENABLED=0 go build -o BINARY ./cmd/mousa",
    })
    fixtures = {"cabinet.md": HERO, "copy.md": HERO, "transit.md": DIVERSION}
    save("inputs.json", {"initial": fixtures, "revised": REVISED,
                         "lexical_label": "frost", "query_values": [1, 0],
                         "scope": "Synthetic vectors; no model execution or retrieval-quality claim."})
    summaries = {}
    # These absolute temporary directory identities are public from creation.
    with tempfile.TemporaryDirectory(prefix="mousa-public-native-vectors-", dir="/tmp") as temporary:
        root = Path(temporary)
        for form in ("jsonl", "directory"):
            store = root / (form + ".sqlite")
            documents = root / "documents"
            selector = ["--source", "synthetic-vector-cabinet"]
            if form == "directory":
                documents.mkdir()
                for name, text in fixtures.items():
                    (documents / name).write_bytes(text.replace("\n", "\r\n").encode())
                selector = [str(documents)]

            def command(name, arguments, stdin="", expected_exit=0):
                argv = [str(binary), "-store", str(store), *arguments]
                result = subprocess.run(argv, input=stdin, text=True, capture_output=True, timeout=30)
                receipts.append({"name": form + "/" + name, "argv": argv, "stdin": stdin,
                                 "stdout": result.stdout, "stderr": result.stderr, "exit": result.returncode})
                save("commands.json", receipts)
                assert len(result.stdout.encode()) <= 1 << 20, "fixture response exceeds 1 MiB"
                assert result.returncode == expected_exit, (name, result.returncode, result.stderr)
                if expected_exit:
                    assert result.stdout == "" and "current passage" in result.stderr
                    return None
                return json.loads(result.stdout)

            initial = "" if form == "directory" else "".join(
                encoded({"id": name, "text": text.replace("\n", "\r\n")})
                for name, text in fixtures.items())
            command("sync", ["sync", *selector], initial)
            lexical = command("lexical-no-overlap", ["query", *selector, "frost"])
            assert lexical["evidence"] == []
            exported = command("inputs", ["vector", "inputs", *selector])
            assert exported["schema"] == "mousa.embedding_inputs.v1"
            assert exported["decision_outcome"] == "allow"
            passages = {p["item"]: p for p in exported["passages"]}
            assert set(passages) == set(fixtures)
            for name, text in fixtures.items():
                assert passages[name]["text"] == text
                assert passages[name]["byte_start"] == 0
                assert passages[name]["byte_end"] == len(text.encode())
                assert passages[name]["content_sha256"] == hashlib.sha256(text.encode()).hexdigest()
            supplied = {
                "schema": "mousa.vector_import.v1",
                "space": {"schema": "mousa.vector_space.v1", "provider": "synthetic",
                          "model": "cabinet-arithmetic", "version": "1", "dimensions": 2,
                          "metric": "cosine"},
                "embeddings": [{**{key: p[key] for key in PINS},
                                "values": [0, 1] if name == "transit.md" else [1, 0]}
                               for name, p in passages.items()],
            }
            imported = command("import", ["vector", "import", *selector], encoded(supplied))
            space = imported["space_id"]
            query = encoded({"schema": "mousa.vector_query.v1", "values": [1, 0]})
            budget = 2 * len(HERO.encode())
            tied = sorted(passages[name]["segment_id"] for name in ("cabinet.md", "copy.md"))
            producing = {}
            for packing in ("original", "exact-v1"):
                arguments = ["query", "--vector-space", space, "--packing-policy", packing,
                             "--budget-bytes", str(budget), *selector]
                selected = command(packing + "/query", arguments, query)
                assert (selected["mode"], selected["eligible"], selected["indexed"], selected["missing"]) == (
                    "vector", 3, 3, 0)
                assert "expression" not in selected and "query_policy" not in selected
                expected_segments = tied if packing == "original" else [tied[0], passages["transit.md"]["segment_id"]]
                assert [p["segment_id"] for p in selected["evidence"]] == expected_segments
                expected_scores = [1, 1] if packing == "original" else [1, 0]
                assert [p["cosine"] for p in selected["evidence"]] == expected_scores
                expected_text = HERO + HERO if packing == "original" else HERO + DIVERSION
                assert "".join(p["text"] for p in selected["evidence"]) == expected_text
                assert selected["used_bytes"] == len(expected_text.encode()) <= budget
                for hit in selected["evidence"]:
                    assert "bm25_score" not in hit
                    assert {key: hit[key] for key in PINS} == {key: passages[hit["item"]][key] for key in PINS}
                history = command(packing + "/trail", ["trail", *selector, selected["trail_id"]])["historical"]
                assert history["schema"] == "mousa.source_trail.v5" and "expression" not in history
                assert history["packet_id"] == selected["packet_id"]
                vector = history["vector"]
                assert vector["space_id"] == space and vector["space"] == supplied["space"]
                assert vector["query_vector_id"] == selected["query_vector_id"]
                assert vector["query_values"] == [1, 0]
                assert [p["segment_id"] for p in vector["candidates"]] == tied + [passages["transit.md"]["segment_id"]]
                assert [p["cosine"] for p in vector["candidates"]] == [1, 1, 0]
                assert [p["segment_id"] for p in history["candidates"] if p["selected"]] == expected_segments
                for candidate in vector["candidates"]:
                    p = next(p for p in passages.values() if p["segment_id"] == candidate["segment_id"])
                    assert {key: candidate[key] for key in PINS} == {key: p[key] for key in PINS}
                producing[packing] = (selected, history, arguments)
            selected, history, arguments = producing["exact-v1"]
            restarted = command("restart", arguments, query)
            assert restarted["packet_id"] == selected["packet_id"]
            assert restarted["decision_id"] != selected["decision_id"]
            assert restarted["trail_id"] != selected["trail_id"]
            retired = producing["original"][0]["evidence"][0]
            if form == "directory":
                (documents / retired["item"]).write_text(REVISED, encoding="utf-8")
                command("revision-sync", ["sync", *selector])
            else:
                command("revision-sync", ["sync", *selector], encoded({"id": retired["item"], "text": REVISED}))
            stale = command("after-revision", arguments, query)
            assert (stale["eligible"], stale["indexed"], stale["missing"]) == (3, 2, 1)
            assert retired["segment_id"] not in [p["segment_id"] for p in stale["evidence"]]
            command("stale-import", ["vector", "import", *selector], encoded(supplied), expected_exit=1)
            after = command("historical-after-revision", ["trail", *selector, selected["trail_id"]])["historical"]
            assert after["vector"] == history["vector"] and after["packet_id"] == history["packet_id"]
            assert next(row for row in after["candidates"] if row["segment_id"] == retired["segment_id"])["indexed_now"] is False
            current = command("new-inputs", ["vector", "inputs", *selector])
            revised = next(p for p in current["passages"] if p["item"] == retired["item"])
            assert revised["text"] == REVISED and revised["representation_id"] != retired["representation_id"]
            summaries[form] = {"space_id": space, "query_vector_id": selected["query_vector_id"],
                               "source_id": retired["source_id"], "retired": {key: retired[key] for key in PINS},
                               "revised": {key: revised[key] for key in PINS},
                               "packets": {key: pair[0]["packet_id"] for key, pair in producing.items()},
                               "trails": {key: pair[0]["trail_id"] for key, pair in producing.items()},
                               "after_revision_coverage": {key: stale[key] for key in ("eligible", "indexed", "missing")}}
    save("summary.json", {"result": "PASS", "calls": len(receipts), "sources": summaries,
                          "scope": "Synthetic native protocol and cosine arithmetic only; no model or quality claim."})
    print(f"PASS: {len(receipts)} native calls; directory and JSONL vector workflows")


if __name__ == "__main__":
    main()
