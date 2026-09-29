"""Record both citation layouts against one verified Git documentation query."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import tiktoken

HERE = Path(__file__).resolve().parent
PROTOCOL = json.loads((HERE / "protocol.json").read_text())


def baseline_prompt(question, evidence):
    return ("Use only the cited Git 2.51.0 passages. If evidence is insufficient, say so.\n"
            "Question: " + question + "\nEvidence:\n" + "".join(
                f'[{index}] {hit["item"]} {hit["location"]["url"]} '
                f'lines {hit["location"]["line_start"]}-{hit["location"]["line_end"]}\n'
                f'{hit["text"]}\n' for index, hit in enumerate(evidence, 1)))


def projection(prompt, question, hits, encoding, limit):
    selected, omitted = [], []
    for hit in hits:
        trial = prompt(question, [*selected, hit])
        if len(encoding.encode(trial, disallowed_special=())) <= limit:
            selected.append(hit)
        else:
            omitted.append(hit)
    text = prompt(question, selected)
    return {"selected_segment_ids": [h["segment_id"] for h in selected],
            "omitted_segment_ids": [h["segment_id"] for h in omitted],
            "tokens": len(encoding.encode(text, disallowed_special=())),
            "sha256": hashlib.sha256(text.encode()).hexdigest(), "text": text}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", type=Path, required=True)
    parser.add_argument("--mousa", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new directory for replay observations")
    args = parser.parse_args()
    sys.path.insert(0, str(args.product.resolve() / "examples" / "docs"))
    import docs
    assert tiktoken.__version__ == "0.12.0"
    encoding = tiktoken.get_encoding("o200k_base")
    archive = args.product / "examples" / "docs" / "git-docs.tar.xz"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == PROTOCOL["archive_sha256"]
    with tempfile.TemporaryDirectory(prefix="mousa-context-512-") as root:
        directory = Path(root) / "corpus"
        store = Path(root) / "store.sqlite"
        docs.prepare(directory, archive)
        manifest, documents, manifest_sha = docs.load_corpus(directory)
        assert manifest_sha == PROTOCOL["corpus_manifest_sha256"]
        assert manifest["revision"] == PROTOCOL["git_revision"]
        for name, digest in PROTOCOL["verified_file_sha256"].items():
            assert hashlib.sha256(documents[name]).hexdigest() == digest
        docs.sync(args.mousa.resolve(), store, directory, 30)
        packet = docs.ask(args.mousa.resolve(), store, directory, PROTOCOL["question"], 4096, 30)
        response = packet["response"]
        hits = response["evidence"]
        assert [[h["item"], h["byte_start"], h["byte_end"],
                 hashlib.sha256(h["text"].encode()).hexdigest()] for h in hits] == PROTOCOL["passage_content_order"]
        assert response["used_bytes"] == 3945
        edge = PROTOCOL["expected_parent_directive"]
        assert any(rel["from_item"] == edge["parent"] and rel["to_item"] == edge["child"]
                   and all(rel["directive"][field] == edge[field] for field in
                           ("text", "byte_start", "byte_end"))
                   and rel["directive"]["line_start"] == edge["line"]
                   for rel in packet["include_relationships"])
        assert all(docs.verify_evidence(hit, documents[hit["item"]]) == hit["text"].encode()
                   for hit in hits)
        assert all(h["location"]["url"] == manifest["files"][h["item"]]["url"]
                   for h in hits)
        old = projection(baseline_prompt, PROTOCOL["question"], hits, encoding, 512)
        new = docs.project_context(packet, 512)
        assert old["selected_segment_ids"] == [hits[0]["segment_id"], hits[2]["segment_id"]]
        assert new["selected_segment_ids"] == [h["segment_id"] for h in hits[:2]]
        assert new["omitted_segment_ids"] == [h["segment_id"] for h in hits[2:]]
        assert new["tokens"] <= 512
        assert new["source_packet_id"] == response["packet_id"]
        assert all(h["text"] in new["text"] for h in hits[:2])
        assert all(h["text"] not in new["text"] for h in hits[2:])
        assert "include::diff-context-options.adoc[]" in new["text"]
        for index, hit in enumerate(hits[:2], 1):
            loc = hit["location"]
            assert f'[{index}] {loc["url"]} lines {loc["line_start"]}-{loc["line_end"]}\n' in new["text"]
        old_two = baseline_prompt(PROTOCOL["question"], hits[:2])
        rows = [{"rank": h["rank"], "segment_id": h["segment_id"], "item": h["item"],
                 "source_url": h["location"]["url"], "line_start": h["location"]["line_start"],
                 "line_end": h["location"]["line_end"], "byte_start": h["byte_start"],
                 "byte_end": h["byte_end"], "text_sha256": hashlib.sha256(h["text"].encode()).hexdigest(),
                 "old_selected": h["segment_id"] in old["selected_segment_ids"],
                 "new_selected": h["segment_id"] in new["selected_segment_ids"]} for h in hits]
        observation = {"packet_id": response["packet_id"], "trail_id": response["trail_id"],
                       "evidence_bytes": response["used_bytes"], "rows": rows,
                       "baseline": old, "revised": new,
                       "baseline_two_tokens": len(encoding.encode(old_two, disallowed_special=())),
                       "full_revised_tokens": len(encoding.encode(docs.render_prompt(PROTOCOL["question"], hits), disallowed_special=())),
                       "loss": "Revised rendering excludes ranks 3-5: both git-switch passages and a later git-restore passage. The byte packet still contains all five."}
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "packet.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
        (args.output / "observation.json").write_text(json.dumps(observation, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps({"old_tokens": old["tokens"], "new_tokens": new["tokens"],
                          "old_ranks": [h["rank"] for h in hits if h["segment_id"] in old["selected_segment_ids"]],
                          "new_ranks": [h["rank"] for h in hits if h["segment_id"] in new["selected_segment_ids"]],
                          "packet_id": response["packet_id"], "trail_id": response["trail_id"]}))


if __name__ == "__main__":
    main()
