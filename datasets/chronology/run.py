"""Run frozen chronology through the maintained consumer and real native binary."""

import argparse
import importlib.util
import json
import os
import signal
from pathlib import Path
import subprocess
import sys

from generate import digest, save


def member(path):
    return {"bytes": path.stat().st_size, "sha256": digest(path.read_bytes())}


def verify_inputs(dataset):
    manifest = json.loads((dataset / "manifest.json").read_text())
    expected = set(manifest["files"]) | {"manifest.json"}
    if {p.name for p in dataset.iterdir()} != expected:
        raise ValueError("dataset membership mismatch")
    for name, identity in manifest["files"].items():
        if Path(name).name != name or (dataset / name).is_symlink() or member(dataset / name) != identity:
            raise ValueError("dataset identity mismatch: " + name)
    plan = json.loads((dataset / "scenario.json").read_text())
    if plan["schema"] != "mousa.chronology_scenario.v1":
        raise ValueError("unsupported scenario")
    if not plan.get("histories") or any(path not in manifest["files"] for path in plan["histories"].values()):
        raise ValueError("history references must name registered input members")
    return plan


def source_identity(root):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
    names = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"]).decode().split("\0")
    consumed = [name for name in names if name and (name.endswith(".go") or name in ("go.mod", "go.sum", "examples/memory/memory.py", "eval/local/workflow.py")) and (root / name).is_file()]
    return {"commit": git("rev-parse", "HEAD"), "tree": git("rev-parse", "HEAD^{tree}"),
            "dirty": bool(git("status", "--porcelain")), "files": {name: member(root / name) for name in sorted(consumed)}}


def run(binary, source, dataset, store, out, timeout):
    plan = verify_inputs(dataset)
    if any(Path(str(store) + suffix).exists() for suffix in ("", "-wal", "-shm")):
        raise ValueError("refusing existing store")
    consumer = source / "examples/memory/memory.py"
    spec = importlib.util.spec_from_file_location("chronology_consumer", consumer)
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    histories = {name: native.load_history(dataset / path)[0] for name, path in plan["histories"].items()}
    out.mkdir(parents=True, exist_ok=False)
    (out / "inputs").mkdir()
    for p in dataset.iterdir():
        (out / "inputs" / p.name).write_bytes(p.read_bytes())
    report = {"schema": "mousa.chronology_run.v1", "status": "INCOMPLETE", "assertion_status": "NOT RUN",
              "agent_acceptance": "NOT RUN", "binary": member(binary), "source": source_identity(source),
              "runner": member(Path(__file__)), "analyzer": member(Path(__file__).with_name("analyze.py")),
              "companion_commit": subprocess.check_output(["git", "-C", str(Path(__file__).resolve().parents[2]), "rev-parse", "HEAD"], text=True).strip(),
              "invocation": sys.argv[1:], "operations": [], "saved_queries": {}}
    def persist():
        save(out / "summary.json", report)
        files = {str(p.relative_to(out)): member(p) for p in sorted(out.rglob("*")) if p.is_file() and p.name != "members.json"}
        save(out / "members.json", {"schema": "mousa.chronology_members.v1", "files": files})
    def invoke(label, source_name, command, kind, expected):
        number = len(report["operations"])
        prefix = f"{number:03d}-{label}"
        receipt = out / (prefix + ".jsonl")
        argv = [sys.executable, str(consumer), "--mousa", str(binary), "--store", str(store),
                "--history", str(dataset / plan["histories"][source_name]), "--receipts", str(receipt), "--timeout", str(timeout), *command]
        op = {"id": label, "kind": kind, "source_name": source_name, "source": histories[source_name]["source"],
              "argv": argv, "expected": expected, "receipt": receipt.name,
              "stdout": prefix + ".stdout.json", "stderr": prefix + ".stderr", "exit_code": None}
        report["operations"].append(op)
        persist()
        timed_out = False
        with subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True) as process:
            try:
                stdout, stderr = process.communicate(timeout=timeout * 8 + 40)
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = process.communicate()
            op["exit_code"] = process.returncode
        (out / op["stdout"]).write_bytes(stdout)
        (out / op["stderr"]).write_bytes(stderr)
        if timed_out:
            op["runner_error"] = "consumer deadline exceeded; owned process group killed"
        persist()
        if timed_out:
            raise TimeoutError(op["runner_error"])
        actual = json.loads(stdout)
        if op["exit_code"] != 0 or actual["status"] != "PASS":
            raise RuntimeError("consumer failed: " + label)
        return number, actual
    def prefix_failure(step):
        number = len(report["operations"])
        receipt = out / f"{number:03d}-{step['id']}.jsonl"
        op = {"id": step["id"], "kind": "native-prefix", "source_name": step["source"], "source": histories[step["source"]]["source"],
              "expected": step, "receipt": receipt.name, "stdout": f"{number:03d}-{step['id']}.stdout.json", "exit_code": None}
        report["operations"].append(op)
        actual = {"status": "INCOMPLETE", "operation_status": "NOT RUN", "capture_complete": False}
        persist()
        with receipt.open("x") as receipts:
            client = native.Client(binary, store, receipts, True, timeout, op["source"])
            op["argv"] = client.argv
            try:
                client.initialize()
                try:
                    client.call("mousa_sync", {"source": op["source"], "segment_policy": "passage-v1", "items": step["native_items"]})
                except native.NativeError as error:
                    actual["native_error"] = error.content
                    actual["operation_status"] = "FAIL"
                    actual["status"] = "FAIL"
                else:
                    raise RuntimeError("expected invalid-item failure")
            finally:
                actual["capture_complete"] = client.capture_complete
                actual["process"] = client.close()
                save(out / op["stdout"], actual)
                op["native_process_exit_code"] = actual["process"]["exit_code"]
                persist()
    persist()
    try:
        for step in plan["steps"]:
            if "native_items" in step:
                prefix_failure(step)
            else:
                invoke(step["id"], step["source"], step["command"], "epoch", step)
            invoke(step["id"] + "-status", step["source"], ["status"], "status", {"active_items": step["active_items"]})
            number, query = invoke(step["id"] + "-query", step["source"], ["ask", step["query"], "--budget-bytes", "2048"], "lifecycle-query", {"required": step["required"], "exact_selection": True})
            if step.get("save_trail"):
                report["saved_queries"][step["id"]] = number
        for label, number in report["saved_queries"].items():
            op = report["operations"][number]
            query = json.loads((out / op["stdout"]).read_text())
            invoke(label + "-historical", op["source_name"], ["inspect", query["result"]["trail_id"]], "historical", {"query_operation": number})
        for case in plan["cases"]:
            for mode in plan["modes"]:
                command = ["ask", case["query"], "--budget-bytes", str(case["budget_bytes"]), "--policy", mode["policy"], "--packing-policy", mode["packing_policy"]]
                label = case["id"] + "-" + mode["policy"] + "-" + mode["packing_policy"]
                number, query = invoke(label, case["source"], command, "comparison", {**case, **mode})
                invoke(label + "-trail", case["source"], ["inspect", query["result"]["trail_id"]],
                       "comparison-trail", {"query_operation": number})
        report["status"] = "COMPLETE"
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        report["runner_error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        persist()
    from analyze import analyze
    analysis = analyze(out)
    report["assertion_status"] = analysis["assertion_status"]
    persist()
    return analysis


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mousa", "source", "dataset", "store", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    result = run(args.mousa.resolve(strict=True), args.source.resolve(strict=True), args.dataset.resolve(strict=True), args.store.resolve(), args.out.resolve(), args.timeout)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["assertion_status"] == "PASS" else 1)
