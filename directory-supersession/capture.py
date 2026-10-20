"""Capture one synthetic directory supersession workflow through native commands."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def identity(*fields):
    digest = hashlib.sha256()
    for field in fields:
        value = field.encode("utf-8") if isinstance(field, str) else field
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mousa", type=Path, required=True)
    parser.add_argument("--product-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    binary = args.mousa.absolute()
    args.output.mkdir(parents=True, exist_ok=False)
    receipts = []

    def save(name, value):
        (args.output / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def revision(ref):
        return subprocess.check_output(
            ["git", "rev-parse", ref], cwd=args.product_source, text=True).strip()

    save("product.json", {
        "repository": "https://github.com/graydeon/mousa",
        "head": revision("HEAD"), "tree": revision("HEAD^{tree}"),
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "go_version": subprocess.check_output(["go", "version"], text=True).strip(),
    })
    # The temporary absolute path is deliberately public source identity from creation.
    with tempfile.TemporaryDirectory(prefix="mousa-public-directory-supersession-", dir="/tmp") as temporary:
        root = Path(temporary) / "documents"
        root.mkdir()
        store = Path(temporary) / "store.sqlite"
        text = "cedar directory evidence"
        fixtures = {"old.md": text, "new.txt": text}
        save("inputs.json", {"initial": fixtures, "updated_predecessor_text": text + " revised"})
        for name, content in fixtures.items():
            (root / name).write_text(content, encoding="utf-8")

        def command(name, *arguments, record=None):
            stdin = "" if record is None else json.dumps(record, separators=(",", ":")) + "\n"
            argv = [str(binary), "-store", str(store), *map(str, arguments)]
            result = subprocess.run(argv, input=stdin, text=True, capture_output=True, timeout=30)
            receipts.append({"name": name, "argv": argv, "stdin": stdin,
                             "stdout": result.stdout, "stderr": result.stderr, "exit": result.returncode})
            save("commands.json", receipts)
            if result.returncode != 0:
                raise RuntimeError(f"{name} exited {result.returncode}: {result.stderr}")
            return json.loads(result.stdout)

        def query(name, mode=None, packing="original", budget=8192):
            flags = ["query", "--packing-policy", packing, "--budget-bytes", str(budget)]
            if mode is not None:
                flags.append("--supersession=" + mode)
            return command(name, *flags, root, "cedar")

        command("initial-sync", "sync", root)
        baseline = query("baseline")
        assert len(baseline["evidence"]) == 2
        no_history = query("no-history", "true")
        assert no_history["packet_id"] == baseline["packet_id"]
        assert no_history["supersession_excluded"] == 0
        predecessor, successor = baseline["evidence"]
        source = identity("mousa.source.v1", "mousa-local", os.path.abspath(root))
        declaration = dict(
            schema="mousa.supersession_declaration.v1", source_id=source,
            predecessor_item_id=predecessor["item"],
            predecessor_representation_id=predecessor["representation_id"],
            successor_item_id=successor["item"],
            successor_representation_id=successor["representation_id"],
            author="example.operator", basis="explicit directory replacement")
        declaration["id"] = identity(
            declaration["schema"], bytes.fromhex(source), predecessor["item"],
            bytes.fromhex(predecessor["representation_id"]), successor["item"],
            bytes.fromhex(successor["representation_id"]), declaration["author"], declaration["basis"])
        assert command("declaration", "supersession", "declaration", "put", record=declaration) == declaration
        declared = query("declaration-alone", "true")
        assert declared["packet_id"] == baseline["packet_id"]
        assert declared["supersession_excluded"] == 0
        activation = dict(
            schema="mousa.supersession_activation.v1", source_id=source,
            expected_previous_activation_id=None, declaration_id=declaration["id"],
            actor_id="example.operator", actor_version="1", occurred_at_usec=1,
            reason="explicit directory replacement")
        activation["id"] = identity(activation["schema"], bytes.fromhex(source), b"", bytes.fromhex(declaration["id"]))
        assert command("activation", "supersession", "activation", "put", record=activation) == activation
        state = command("activation-state", "supersession", "activation", "state", source)
        assert state == dict(source_id=source, current_activation_id=activation["id"], active_declaration_id=declaration["id"])
        producing = []
        for packing in ("original", "exact-v1"):
            default = query(packing + "-default", packing=packing, budget=len(text))
            disabled = query(packing + "-false", "false", packing, len(text))
            assert default["evidence"] == disabled["evidence"]
            assert "supersession_excluded" not in default and "supersession_excluded" not in disabled
            assert default["evidence"][0]["segment_id"] == predecessor["segment_id"]
            selected = query(packing + "-true", "true", packing, len(text))
            assert selected["supersession_excluded"] == 1
            assert selected["matched_candidates"] == 2 and selected["budget_omitted"] == 0
            assert selected["used_bytes"] == len(text)
            assert [hit["segment_id"] for hit in selected["evidence"]] == [successor["segment_id"]]
            assert selected["evidence"][0]["rank"] == 2
            trail = command(packing + "-trail", "trail", root, selected["trail_id"])["historical"]
            assert trail["schema"] == "mousa.source_trail.v4"
            member = trail["supersession"]
            assert member["consulted"] is True and member["activation_id"] == activation["id"]
            assert member["declaration_id"] == declaration["id"]
            assert member["dispositions"] == [dict(
                selection="superseded", segment_id=predecessor["segment_id"],
                content_sha256=predecessor["content_sha256"], declaration_id=declaration["id"],
                **{key: declaration[key] for key in (
                    "predecessor_item_id", "predecessor_representation_id",
                    "successor_item_id", "successor_representation_id")})]
            rows = {row["segment_id"]: row for row in trail["candidates"]}
            assert rows[predecessor["segment_id"]]["selected"] is False
            assert rows[successor["segment_id"]]["selected"] is True
            assert rows[predecessor["segment_id"]]["text_bytes"] == len(text)
            producing.append((packing, selected["trail_id"], member))
        (root / predecessor["item"]).write_text(text + " revised", encoding="utf-8")
        command("revision-sync", "sync", root)
        revised = query("revised-true", "true")
        assert revised["supersession_excluded"] == 0
        revised_pins = {hit["item"]: hit["representation_id"] for hit in revised["evidence"]}
        assert set(revised_pins) == set(fixtures)
        assert revised_pins[predecessor["item"]] != predecessor["representation_id"]
        assert revised_pins[successor["item"]] == successor["representation_id"]
        for packing, trail_id, member in producing:
            historical = command(packing + "-historical-after-resync", "trail", root, trail_id)["historical"]
            assert historical["supersession"] == member
            old = next(row for row in historical["candidates"] if row["segment_id"] == predecessor["segment_id"])
            assert old["indexed_now"] is False
        save("summary.json", {"result": "PASS", "source_id": source,
                              "declaration_id": declaration["id"], "activation_id": activation["id"],
                              "predecessor": predecessor, "successor": successor,
                              "revised_representations": revised_pins,
                              "scope": "Synthetic native behavior only; no semantic, quality or performance claim."})
    print("PASS: directory opt-in, producing trail pins and revision update")


if __name__ == "__main__":
    main()
