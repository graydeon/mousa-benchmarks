"""Capture a small synthetic native lexical/vector fusion example; no model runs."""

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


PINS = ("source_id", "segment_id", "representation_id",
        "representation_sha256", "content_sha256")
FIXTURE = {"overlap.md": "Drain sockets before stopping the host.",
           "vector.md": "Radishes prefer damp soil.",
           "lexical.md": "Drain sockets."}


def encode(value):
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
        return subprocess.check_output(["git", *arguments], cwd=args.product_source,
                                       text=True, timeout=30).strip()

    if git("rev-parse", "HEAD") != args.product_head or git("status", "--porcelain"):
        raise ValueError("capture requires the clean requested product head")
    args.output.mkdir(parents=True, exist_ok=False)

    def save(name, value):
        (args.output / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    save("product.json", {"repository": "https://github.com/graydeon/mousa",
                          "head": args.product_head, "tree": git("rev-parse", "HEAD^{tree}"),
                          "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                          "go_version": subprocess.check_output(["go", "version"], text=True).strip(),
                          "build": "GOWORK=off CGO_ENABLED=0 go build -o BINARY ./cmd/mousa"})
    save("inputs.json", {"initial": FIXTURE, "query_text": "Drain", "query_values": [1, 0],
                         "vectors": {"overlap.md": [0, 1], "vector.md": [1, 0]},
                         "fusion_policy": "rrf-equal-k60-v1", "budget_bytes": 40,
                         "limits": "Synthetic arithmetic/protocol only; no model or quality acceptance."})
    receipts = []
    summaries = {}
    with tempfile.TemporaryDirectory(prefix="mousa-public-hybrid-", dir="/tmp") as temporary:
        root = Path(temporary)
        for form in ("jsonl", "directory"):
            store = root / (form + ".sqlite")
            documents = root / "documents"
            selector = ["--source", "synthetic-native-hybrid"]
            if form == "directory":
                documents.mkdir()
                for name, text in FIXTURE.items():
                    (documents / name).write_text(text, encoding="utf-8")
                selector = [str(documents)]

            def command(name, arguments, stdin=""):
                argv = [str(binary), "-store", str(store), *arguments]
                result = subprocess.run(argv, input=stdin, text=True, capture_output=True, timeout=30)
                receipts.append({"name": form + "/" + name, "argv": argv, "stdin": stdin,
                                 "stdout": result.stdout, "stderr": result.stderr, "exit": result.returncode})
                save("commands.json", receipts)
                assert result.returncode == 0, (name, result.returncode, result.stderr)
                return json.loads(result.stdout)

            initial = "" if form == "directory" else "".join(
                encode({"id": name, "text": text}) for name, text in FIXTURE.items())
            command("sync", ["sync", *selector], initial)
            exported = command("inputs", ["vector", "inputs", *selector])
            passages = {p["item"]: p for p in exported["passages"]}
            assert set(passages) == set(FIXTURE)
            for name, p in passages.items():
                assert p["text"] == FIXTURE[name]
                assert p["content_sha256"] == hashlib.sha256(p["text"].encode()).hexdigest()
            supplied = {"schema": "mousa.vector_import.v1",
                        "space": {"schema": "mousa.vector_space.v1", "provider": "synthetic",
                                  "model": "hybrid-arithmetic", "version": "1", "dimensions": 2,
                                  "metric": "cosine"},
                        "embeddings": [{**{key: p[key] for key in PINS},
                                        "values": [1, 0] if name == "vector.md" else [0, 1]}
                                       for name, p in passages.items() if name != "lexical.md"]}
            imported = command("import", ["vector", "import", *selector], encode(supplied))
            space = imported["space_id"]
            query = encode({"schema": "mousa.vector_query.v1", "values": [1, 0]})
            lexical = command("lexical", ["query", "--budget-bytes", "40", *selector, "Drain"])
            vector = command("vector", ["query", "--vector-space", space, "--budget-bytes", "40", *selector], query)
            assert [p["item"] for p in lexical["evidence"]] == ["lexical.md"]
            assert [p["item"] for p in vector["evidence"]] == ["vector.md"]
            producing = {}
            for packing in ("original", "exact-v1"):
                arguments = ["query", "--hybrid-space", space, "--policy", "dedup",
                             "--packing-policy", packing, "--budget-bytes", "40", *selector, "Drain Drain"]
                selected = command(packing + "/hybrid", arguments, query)
                h = selected["hybrid"]
                assert selected["schema"] == "mousa.hybrid_result.v1" and selected["mode"] == "hybrid"
                assert (h["eligible"], h["indexed"], selected["missing"]) == (3, 2, 1)
                assert h["fusion_policy"] == "rrf-equal-k60-v1" and h["terms"] == ['"drain"']
                assert h["space"] == supplied["space"] and h["space_id"] == space
                candidates = h["candidates"]
                overlap, singles = candidates[0], candidates[1:]
                assert overlap["segment_id"] == passages["overlap.md"]["segment_id"]
                assert overlap["lexical"]["rank"] == 2 and overlap["vector"]["rank"] == 2
                assert overlap["rrf"] == float(Fraction(1, 31))
                assert overlap["vector"]["cosine"] == 0
                assert [c["segment_id"] for c in singles] == sorted(c["segment_id"] for c in singles)
                assert all(c["rrf"] == float(Fraction(1, 61)) for c in singles)
                assert all(("lexical" in c) != ("vector" in c) for c in singles)
                for c in candidates:
                    p = next(p for p in passages.values() if p["segment_id"] == c["segment_id"])
                    assert {key: c[key] for key in PINS} == {key: p[key] for key in PINS}
                assert [p["item"] for p in selected["evidence"]] == ["overlap.md"]
                assert selected["used_bytes"] == 39
                history = command(packing + "/trail", ["trail", *selector, selected["trail_id"]])["historical"]
                assert history["schema"] == "mousa.source_trail.v6" and history["hybrid"] == h
                assert history["packet_id"] == selected["packet_id"]
                assert [c["segment_id"] for c in history["candidates"] if c["selected"]] == [overlap["segment_id"]]
                producing[packing] = (selected, history, arguments)
            selected, history, arguments = producing["exact-v1"]
            restarted = command("restart", arguments, query)
            assert restarted["packet_id"] == selected["packet_id"]
            assert restarted["trail_id"] != selected["trail_id"]
            no_match = command("no-lexical-match", [*arguments[:-1], "nonmatching"], query)
            assert no_match["evidence"][0]["item"] == "vector.md"
            assert all("lexical" not in c for c in no_match["hybrid"]["candidates"])
            revised = "Drain replacement."
            if form == "directory":
                (documents / "overlap.md").write_text(revised, encoding="utf-8")
                command("revision", ["sync", *selector])
            else:
                command("revision", ["sync", *selector], encode({"id": "overlap.md", "text": revised}))
            changed = command("after-revision", arguments, query)
            assert changed["hybrid"]["indexed"] == 1 and changed["missing"] == 2
            assert "before stopping" not in json.dumps(changed)
            after = command("old-history", ["trail", *selector, selected["trail_id"]])["historical"]
            assert after["hybrid"] == history["hybrid"] and after["packet_id"] == history["packet_id"]
            assert next(c for c in after["candidates"] if c["segment_id"] == passages["overlap.md"]["segment_id"])["indexed_now"] is False
            command("deny", ["access", *selector, "deny"])
            denied = command("denied-query", arguments, query)
            assert denied["evidence"] == [] and denied["outcome"] == "policy_excluded"
            assert (denied["hybrid"]["eligible"], denied["hybrid"]["indexed"], denied["missing"]) == (0, 0, 0)
            assert denied["hybrid"]["candidates"] == []
            hidden = command("denied-history", ["trail", *selector, selected["trail_id"]])
            assert "historical" not in hidden
            summaries[form] = {"space_id": space, "query_vector_id": selected["hybrid"]["query_vector_id"],
                               "packets": {key: value[0]["packet_id"] for key, value in producing.items()},
                               "trails": {key: value[0]["trail_id"] for key, value in producing.items()},
                               "lexical_selected": "lexical.md", "vector_selected": "vector.md",
                               "hybrid_selected": "overlap.md", "overlap_rrf": float(Fraction(1, 31))}
    save("summary.json", {"result": "PASS", "calls": len(receipts), "sources": summaries,
                          "limits": "Synthetic native fusion arithmetic/protocol only; no model, quality or timing claim."})
    print(f"PASS: {len(receipts)} native calls; directory and JSONL hybrid retrieval")


if __name__ == "__main__":
    main()
