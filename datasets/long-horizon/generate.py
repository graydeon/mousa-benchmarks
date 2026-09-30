"""Generate chronological fictional memory with distant facts and lifecycle changes."""

import argparse
import hashlib
import json
from pathlib import Path


def record(seed, index, revision=0):
    digest = hashlib.sha256(f"horizon-v1:{seed}:{index}:{revision}".encode()).hexdigest()
    key = "MEMORY" + hashlib.sha256(f"key:{seed}:{index}".encode()).hexdigest()[:24].upper()
    text = f"{key} project memory. Assigned team is TEAM{digest[:12].upper()}; recovery code is CODE{digest[12:28].upper()}. Revision {revision}. This fictional project records a maintenance decision, its responsible team and its recovery procedure. Other project decisions do not supersede this record."
    return {"id": f"memory-{index:09d}", "text": text}, key


def label(row):
    data = row["text"].encode()
    return {"item": row["id"], "content_sha256": hashlib.sha256(data).hexdigest(), "byte_start": 0, "byte_end": len(data)}


def generate(output, documents=16384, epochs=100, seed=20260930):
    if documents < 64 or epochs < 4 or documents < epochs:
        raise ValueError("require at least 64 documents, 4 epochs and one document per epoch")
    output.mkdir(parents=True, exist_ok=False)
    targets = sorted({0, 2, 3, 4, 5, 6, 7, 8, documents // 4, documents // 2, 3 * documents // 4, documents - 1})
    cases = []
    for index in targets:
        row, key = record(seed, index)
        cases.append({"id": f"retention-{index}", "query": key, "introduced_epoch": index * epochs // documents, "intervening_documents": documents - index - 1, "expected": [label(row)]})
    changed, change_key = record(seed, 9, 2)
    _, withdrawn_key = record(seed, 1)
    cases.extend([
        {"id": "latest-correction", "query": change_key, "introduced_epoch": 9 * epochs // documents, "expected": [label(changed)]},
        {"id": "withdrawn-memory", "query": withdrawn_key, "introduced_epoch": epochs - 1, "expected": []},
        {"id": "never-observed", "query": "UNOBSERVEDZZMEMORY", "introduced_epoch": None, "expected": []},
    ])
    with (output / "events.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        for epoch in range(epochs):
            start = (epoch * documents + epochs - 1) // epochs
            end = ((epoch + 1) * documents + epochs - 1) // epochs
            rows = [record(seed, index)[0] for index in range(start, end)]
            if epoch == epochs // 2:
                rows.append(record(seed, 9, 1)[0])
            if epoch == epochs - 1:
                rows.extend([changed, {"id": "memory-000000001", "deleted": True}])
            stream.write(json.dumps({"epoch": epoch, "items": rows}, sort_keys=True) + "\n")
    initial, initial_key = record(seed, 9)
    plan = {"schema": "mousa.long_horizon.v1", "seed": seed, "documents": documents, "epochs": epochs, "ingest_events": documents + 3, "active_items": documents - 1, "source": "memory", "synthetic_only": True, "license": "AGPL-3.0-only", "initial_snapshot": {"query": initial_key, "expected": [label(initial)]}, "cases": cases}
    (output / "tasks.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    manifest = {"schema": plan["schema"], "seed": seed, "documents": documents, "epochs": epochs, "files": {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(output.iterdir())}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--documents", type=int, default=16384)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260930)
    args = parser.parse_args()
    print(json.dumps(generate(args.out, args.documents, args.epochs, args.seed), indent=2))


if __name__ == "__main__":
    main()
