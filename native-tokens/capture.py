"""Capture native token selection and independently count its exact rendered context."""

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


PINS = ("source_id", "segment_id", "representation_id",
        "representation_sha256", "content_sha256")
FIXTURE = {
    "unicode.md": "amber 你好 مرحبا café é <|endoftext|>\t\x7f\n",
    "short.md": "amber concise",
    "copy.md": "amber concise",
}
BACKEND = "tiktoken/0.12.0/o200k_base/ordinary"


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mousa", type=Path, required=True)
    parser.add_argument("--product-source", type=Path, required=True)
    parser.add_argument("--product-head", required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    binary = args.mousa.absolute()
    python, cache = str(args.python.absolute()), str(args.cache.absolute())

    def git(*arguments):
        return subprocess.check_output(["git", *arguments], cwd=args.product_source,
                                       text=True, timeout=30).strip()

    if git("rev-parse", "HEAD") != args.product_head or git("status", "--porcelain"):
        raise ValueError("capture requires the clean requested public product head")
    args.output.mkdir(parents=True, exist_ok=False)

    def save(name, value):
        (args.output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")

    os.environ["TIKTOKEN_CACHE_DIR"] = cache
    import tiktoken
    import tiktoken.load

    if importlib.metadata.version("tiktoken") != "0.12.0":
        raise ValueError("reference counting requires official tiktoken==0.12.0")

    def no_download(*unused_args, **unused_kwargs):
        raise RuntimeError("prepare the vocabulary before capture")

    tiktoken.load.read_file = no_download
    encoder = tiktoken.get_encoding("o200k_base")
    query_backend = subprocess.run(
        [python, "-I", "-c", "import sys,json,importlib.metadata; print(json.dumps({'python':sys.version,'tiktoken':importlib.metadata.version('tiktoken')}))"],
        text=True, capture_output=True, timeout=10, check=True)
    backend = {"query_runtime": json.loads(query_backend.stdout),
               "reference_python": sys.version, "encoding": encoder.name,
               "encoding_method": "encode_ordinary", "version": "0.12.0",
               "cache_files": {p.name: {"bytes": p.stat().st_size,
                                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                               for p in sorted(Path(cache).iterdir()) if p.is_file()}}
    assert backend["query_runtime"]["tiktoken"] == "0.12.0"
    save("backend.json", backend)
    save("product.json", {"repository": "https://github.com/graydeon/mousa",
                          "head": args.product_head, "tree": git("rev-parse", "HEAD^{tree}"),
                          "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                          "go_version": subprocess.check_output(["go", "version"], text=True).strip(),
                          "build": "GOWORK=off CGO_ENABLED=0 go build -o BINARY ./cmd/mousa"})
    save("inputs.json", {"initial": FIXTURE, "query_text": "amber", "query_values": [1, 0],
                         "cap_policy": "full=10000; pressure=max independent single-passage rendering count",
                         "budget_bytes": 8192, "limits": "Synthetic counting/protocol only; no model or quality claim."})
    receipts, counts = [], []
    summaries = {}
    with tempfile.TemporaryDirectory(prefix="mousa-native-tokens-", dir="/tmp") as temporary:
        root = Path(temporary)
        for form in ("jsonl", "directory"):
            store = root / (form + ".sqlite")
            documents = root / "documents"
            selector = ["--source", "synthetic-native-tokens"]
            if form == "directory":
                documents.mkdir()
                for name, text in FIXTURE.items():
                    (documents / name).write_text(text, encoding="utf-8")
                selector = [str(documents)]

            def command(name, arguments, stdin="", expect_failure=False):
                argv = [str(binary), "-store", str(store), *arguments]
                result = subprocess.run(argv, input=stdin, text=True, capture_output=True, timeout=25)
                receipts.append({"name": form + "/" + name, "argv": argv, "stdin": stdin,
                                 "stdout": result.stdout, "stderr": result.stderr, "exit": result.returncode})
                save("commands.json", receipts)
                if expect_failure:
                    assert result.returncode != 0 and result.stdout == "", (name, result.stdout, result.stderr)
                    return result.stderr
                assert result.returncode == 0, (name, result.returncode, result.stderr)
                return json.loads(result.stdout)

            initial = "" if form == "directory" else "".join(
                encode({"id": name, "text": text}) for name, text in FIXTURE.items())
            command("sync", ["sync", *selector], initial)
            exported = command("inputs", ["vector", "inputs", *selector])
            passages = {p["segment_id"]: p for p in exported["passages"]}
            assert sorted(p["text"] for p in passages.values()) == sorted(FIXTURE.values())
            pressure_cap = max(len(encoder.encode_ordinary(
                f"[source={p['source_id']} segment={p['segment_id']} sha256={p['content_sha256']}]\n{p['text']}"))
                for p in passages.values())
            supplied = {"schema": "mousa.vector_import.v1",
                        "space": {"schema": "mousa.vector_space.v1", "provider": "synthetic",
                                  "model": "token-counting", "version": "1", "dimensions": 2,
                                  "metric": "cosine"},
                        "embeddings": [{**{key: p[key] for key in PINS}, "values": [1, 0]}
                                       for p in passages.values()]}
            space = command("import", ["vector", "import", *selector], encode(supplied))["space_id"]
            vector = encode({"schema": "mousa.vector_query.v1", "values": [1, 0]})
            byte_only = command("byte-only", ["query", *selector, "amber"])
            assert len(byte_only["evidence"]) == 3

            def inspect_rendering(name, response, cap, expected_passages=None):
                assert response["schema"] == "mousa.token_result.v1"
                token = response["token"]
                assert token["backend"] == BACKEND and token["rendering"] == "mousa.context_text.v1"
                selected = response["evidence"]
                if expected_passages is not None:
                    assert len(selected) == expected_passages, name
                pieces = []
                for row in selected:
                    segment = row["segment"]
                    p = passages[segment["id"]]
                    assert segment["representation_id"] == p["representation_id"]
                    assert segment["content_sha256"] == p["content_sha256"]
                    assert row["text"] == p["text"]
                    pieces.append(f"[source={p['source_id']} segment={p['segment_id']} sha256={p['content_sha256']}]\n{p['text']}")
                expected = "\n\n".join(pieces)
                assert response["context"] == expected
                ids = encoder.encode_ordinary(expected)
                assert token["measured_tokens"] == len(ids) <= cap
                assert token["rendered_bytes"] == len(expected.encode())
                assert token["rendered_sha256"] == hashlib.sha256(expected.encode()).hexdigest()
                assert response["used_bytes"] == sum(len(row["text"].encode()) for row in selected)
                counts.append({"name": form + "/" + name, "cap": cap, "count": len(ids),
                               "reference_ids": ids, "selected_segments": [r["segment"]["id"] for r in selected]})
                save("counts.json", counts)
                return len(ids)

            producing = {}
            runtime = ["--tokenizer-python", python, "--tokenizer-cache", cache]
            for mode in ("lexical", "vector", "hybrid"):
                for packing in ("original", "exact-v1"):
                    arguments = ["query", "--context-tokens", "10000", *runtime, "--packing-policy", packing]
                    stdin = ""
                    if mode != "lexical":
                        arguments += ["--" + mode + "-space", space]
                        stdin = vector
                    arguments += selector
                    if mode != "vector":
                        arguments += ["amber"]
                    name = mode + "/" + packing
                    full = command(name, arguments, stdin)
                    count = inspect_rendering(name, full, 10000, 3 if packing == "original" else 2)
                    if packing == "exact-v1":
                        pressure_args = [*arguments]
                        pressure_args[2] = str(pressure_cap)
                        pressure = command(name + "/pressure", pressure_args, stdin)
                        inspect_rendering(name + "/pressure", pressure, pressure_cap, 1)
                        assert pressure["context"] != full["context"]
                    producing[(mode, packing)] = (full, arguments, stdin, count)
            full, arguments, stdin, count = producing[("hybrid", "exact-v1")]
            history = command("history", ["trail", *selector, full["trail_id"]])["historical"]
            assert history["schema"] == "mousa.source_trail.v7" and history["token"] == full["token"]
            assert history["hybrid"] == full["hybrid"] and history["packet_id"] == full["packet_id"]
            restarted = command("restart", arguments, stdin)
            assert restarted["packet_id"] == full["packet_id"] and restarted["context"] == full["context"]
            exact_args = [*arguments]
            exact_args[2] = str(count)
            exact = command("exact-boundary", exact_args, stdin)
            inspect_rendering("exact-boundary", exact, count, 2)
            verified = command("recount", ["trail", "--verify-tokens", *runtime, *selector, full["trail_id"]])
            assert verified["historical"]["token_verification"] == "official_recount_verified"
            # Every old selected byte becomes unavailable; no replacement is invented for history.
            if form == "directory":
                for name in FIXTURE:
                    (documents / name).write_text("amber replacement", encoding="utf-8")
                command("revision", ["sync", *selector])
            else:
                command("revision", ["sync", *selector], "".join(
                    encode({"id": name, "text": "amber replacement"}) for name in FIXTURE))
            changed = command("current-revision", arguments, stdin)
            assert changed["hybrid"]["indexed"] == 0 and "你好" not in changed["context"]
            old = command("old-history", ["trail", *selector, full["trail_id"]])["historical"]
            assert old["token"] == history["token"] and old["token_verification"] == "retired_text_unavailable"
            error = command("retired-recount", ["trail", "--verify-tokens", *runtime, *selector, full["trail_id"]], expect_failure=True)
            assert "retired" in error
            command("deny", ["access", *selector, "deny"])
            denied = command("denied-query", arguments, stdin)
            assert denied["context"] == "" and denied["evidence"] == []
            assert denied["token"]["measured_tokens"] == 0 and denied["token"]["proposed_tokens"] == []
            assert denied["hybrid"]["eligible"] == denied["hybrid"]["indexed"] == 0
            hidden = command("denied-history", ["trail", *selector, full["trail_id"]])
            assert "historical" not in hidden
            summaries[form] = {"full_hybrid_exact_tokens": count, "exact_boundary": True,
                               "both_packers_all_modes": True, "pressure_changes_selection": True,
                               "restart_history_recount": True, "retired_recount_refused": True,
                               "current_stale_vectors_excluded": True, "denial_hides_facts": True}
    save("summary.json", {"native_calls": len(receipts), "counted_contexts": len(counts),
                          "source_forms": summaries, "scope": "Native protocol/counting only; no performance or model-quality claim."})
    print(f"PASS: {len(receipts)} native calls, {len(counts)} independent whole-context token checks")


if __name__ == "__main__":
    main()
