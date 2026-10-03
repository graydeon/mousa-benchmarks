"""Write independently authored small lifecycle inputs and prospective labels."""

import argparse
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def generate(out):
    out.mkdir(parents=True, exist_ok=False)
    def revision(label, item, text, author):
        return {"revision": label, "id": item, "text": text, "sha256": digest(text.encode()),
                "author": author, "date": "synthetic-" + label, "uri": "synthetic://chronology/" + label}
    alpha = [revision("original", "shared", "beacon route uses copper.\n", "Ada"),
             revision("correction-one", "shared", "beacon route uses silver.\n", "Bea"),
             revision("correction-two", "shared", "beacon route uses cobalt.\n", "Cy"),
             revision("restored", "shared", "beacon route uses jade.\n", "Dee"),
             revision("keeper", "keeper", "anchor omitted items remain active.\n", "Eli"),
             revision("unicode", "unicode", "\ufeffrune café 雪 🐚\r\nsecond line\r", "Fay"),
             revision("empty", "empty", "", "Gus"),
             revision("prefix", "prefix", "prefix committed before invalid item.\n", "Hal"),
             revision("repair", "repair", "repair explicitly supplied later.\n", "Ivy"),
             revision("copy-a", "copy-a", "amber amber", "Jay"),
             revision("copy-b", "copy-b", "amber amber", "Kay"),
             revision("required", "required", "amber repair code ZX17", "Lou")]
    beta = [revision("beta-original", "shared", "beacon beta uses linen.\n", "Moe"),
            revision("beta-corrected", "shared", "beacon beta uses cotton.\n", "Nia")]
    histories = {"alpha": {"schema": "mousa-project-history-v2", "source": "chronicle-alpha", "revisions": alpha, "epochs": []},
                 "beta": {"schema": "mousa-project-history-v2", "source": "chronicle-beta", "revisions": beta, "epochs": []}}
    def op(label):
        row = next(r for r in alpha + beta if r["revision"] == label)
        return {"id": row["id"], "revision": label}
    steps = []
    def epoch(source, label, operations, outcome, active, selected, query="beacon", save_trail=False):
        histories[source]["epochs"].append({"epoch": label, "operations": operations})
        steps.append({"id": label, "source": source, "command": ["apply", label], "outcome": outcome,
                      "active_items": active, "query": query, "selected_revisions": selected, "save_trail": save_trail})
    epoch("alpha", "01-create", [op("original"), op("keeper")], {"added": ["shared", "keeper"]}, 2, ["original"], save_trail=True)
    epoch("beta", "02-beta-create", [op("beta-original")], {"added": ["shared"]}, 1, ["beta-original"], save_trail=True)
    epoch("alpha", "03-exact-replay", [op("original"), op("keeper")], {"unchanged": ["shared", "keeper"]}, 2, ["original"])
    epoch("alpha", "04-first-correction", [op("correction-one")], {"updated": ["shared"]}, 2, ["correction-one"], save_trail=True)
    epoch("alpha", "05-second-correction", [op("correction-two")], {"updated": ["shared"]}, 2, ["correction-two"])
    epoch("alpha", "06-omission", [op("unicode")], {"added": ["unicode"]}, 3, ["keeper"], "anchor")
    epoch("alpha", "07-delete", [{"id": "shared", "deleted": True}], {"deleted": ["shared"]}, 2, [])
    epoch("alpha", "08-repeat-delete", [{"id": "shared", "deleted": True}], {"absent": ["shared"]}, 2, [])
    epoch("alpha", "09-restore", [op("restored")], {"restored": ["shared"]}, 3, ["restored"], save_trail=True)
    epoch("alpha", "10-explicit-revert", [op("original")], {"updated": ["shared"]}, 3, ["original"])
    epoch("alpha", "11-empty-content", [op("empty")], {"added": ["empty"]}, 4, ["unicode"], "rune")
    epoch("beta", "12-beta-correction", [op("beta-corrected")], {"updated": ["shared"]}, 1, ["beta-corrected"])
    steps.append({"id": "13-native-prefix", "source": "alpha", "native_items": [{"id": "prefix", "text": alpha[7]["text"]}, {"id": "", "text": "invalid"}],
                  "native_error": {"code": "invalid_item", "completed_items": 1, "failed_item": 2},
                  "active_items": 5, "query": "prefix", "selected_revisions": ["prefix"]})
    epoch("alpha", "14-explicit-repair", [op("prefix"), op("repair")], {"unchanged": ["prefix"], "added": ["repair"]}, 6, ["prefix"], "prefix")
    epoch("alpha", "15-duplicate-packing", [op("copy-a"), op("copy-b"), op("required")], {"added": ["copy-a", "copy-b", "required"]}, 9, ["required"], "ZX17")
    epoch("alpha", "16-final-replay", [op("original")], {"unchanged": ["shared"]}, 9, ["original"])
    for name, h in histories.items():
        save(out / (name + ".json"), h)
    def span(label):
        row = next(r for r in alpha + beta if r["revision"] == label)
        data = row["text"].encode().removeprefix(b"\xef\xbb\xbf").replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        return {"item": row["id"], "representation_sha256": digest(data), "byte_start": 0, "byte_end": len(data),
                "author": row["author"], "date": row["date"], "uri": row["uri"]}
    for step in steps:
        step["required"] = [span(label) for label in step.pop("selected_revisions")]
    cases = [{"id": "packing", "source": "alpha", "query": "amber amber", "budget_bytes": 33, "required": [span("required")]},
             {"id": "unicode", "source": "alpha", "query": "rune rune", "budget_bytes": 64, "required": [span("unicode")]},
             {"id": "small-budget", "source": "alpha", "query": "rune", "budget_bytes": 1, "required": [span("unicode")]},
             {"id": "near-match", "source": "alpha", "query": "beacon quantum schedule", "budget_bytes": 64, "required": []}]
    plan = {"schema": "mousa.chronology_scenario.v1", "synthetic_only": True, "license": "AGPL-3.0-only",
            "histories": {name: name + ".json" for name in histories}, "steps": steps, "cases": cases,
            "modes": [{"policy": p, "packing_policy": k} for p in ("original", "dedup") for k in ("original", "exact-v1")]}
    save(out / "scenario.json", plan)
    save(out / "manifest.json", {"schema": plan["schema"], "files": {p.name: {"bytes": p.stat().st_size, "sha256": digest(p.read_bytes())} for p in sorted(out.iterdir())}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    generate(parser.parse_args().out)
